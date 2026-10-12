"""Open a DRAFT pull request for an approved Scribe proposal. The only thing in the crew that touches GitHub.

Guard rails, all enforced here and not just in the caller:
- Needs a token the operator deliberately configured (``CREW_GITHUB_TOKEN`` or ``CREW_GITHUB_TOKEN_FILE``).
  No token means ``not_configured`` and nothing is sent. The token is never logged or returned.
- Only the one configured repo (``CREW_GITHUB_REPO``), a brand-new branch cut from the base branch.
- Only docs allow-list paths, markdown only, create-only (a file that already exists is left untouched).
- Always ``draft: true``. It never merges, never pushes to the base branch, never edits an existing file.
- Idempotent: the branch name is derived from the run, so a retry finds the same branch and the same PR.
- Never raises: every failure is a short, secret-free status the run records honestly.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from typing import Any, Optional

import httpx

from app.crew.redaction import redact_text
from app.crew.scribe import path_allowed

logger = logging.getLogger(__name__)

API = "https://api.github.com"
DEFAULT_REPO = "welshDog/HyperCode-V2.4"
DEFAULT_BASE = "main"
TIMEOUT_S = 15.0
_REPO_OK = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_OK = re.compile(r"^crew/[A-Za-z0-9._-]+$")


def _token() -> str:
    token = (os.getenv("CREW_GITHUB_TOKEN") or "").strip()
    path = os.getenv("CREW_GITHUB_TOKEN_FILE")
    if not token and path:
        try:
            with open(path, encoding="utf-8") as fh:
                token = fh.read().strip()
        except OSError:
            token = ""
    return token


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, **extra}


def _safe(text: str) -> str:
    return redact_text(text)[:200]


async def open_draft_pr(
    proposal: dict[str, Any], *, transport: Optional[httpx.AsyncBaseTransport] = None
) -> dict[str, Any]:
    """Returns ``{"status": "opened"|"exists"|"not_configured"|"refused"|"error", "url"?, "detail"?}``."""
    token = _token()
    if not token:
        return _result("not_configured", detail="no GitHub token is configured; the draft stays in this run")
    repo = os.getenv("CREW_GITHUB_REPO", DEFAULT_REPO)
    base = os.getenv("CREW_GITHUB_BASE", DEFAULT_BASE)
    pr: dict[str, Any] = proposal["pr"] if isinstance(proposal.get("pr"), dict) else {}
    branch = str(pr.get("branch", ""))
    files: list[Any] = proposal["files"] if isinstance(proposal.get("files"), list) else []
    if not _REPO_OK.match(repo) or not _BRANCH_OK.match(branch) or pr.get("draft") is not True or not files:
        return _result("refused", detail="proposal or configuration is not one the publisher accepts")
    if not all(isinstance(f, dict) and path_allowed(str(f.get("path"))) for f in files):
        return _result("refused", detail="a file is outside the docs allow-list")

    headers = {
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "hypercode-crew-scribe",
    }
    try:
        async with httpx.AsyncClient(base_url=API, headers=headers, timeout=TIMEOUT_S, transport=transport) as c:
            head = await c.get(f"/repos/{repo}/git/ref/heads/{base}")
            if head.status_code != 200:
                return _result("error", detail=f"could not read base branch ({head.status_code})")
            sha = head.json()["object"]["sha"]

            ref = await c.post(f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": sha})
            if ref.status_code not in (201, 422):  # 422 = the branch already exists: a retry, carry on
                return _result("error", detail=f"could not create branch ({ref.status_code})")

            for f in files:
                put = await c.put(
                    f"/repos/{repo}/contents/{f['path']}",
                    json={
                        "message": f"docs: crew handover draft ({f['path'].rsplit('/', 1)[-1]})",
                        "content": base64.b64encode(f["content"].encode("utf-8")).decode("ascii"),
                        "branch": branch,
                    },
                )
                if put.status_code not in (201, 422):  # 422 = already there (retry); never overwritten
                    return _result("error", detail=f"could not add {f['path']} ({put.status_code})")

            owner = repo.split("/", 1)[0]
            found = await c.get(f"/repos/{repo}/pulls", params={"head": f"{owner}:{branch}", "state": "all"})
            if found.status_code == 200 and found.json():
                return _result("exists", url=str(found.json()[0].get("html_url", "")))
            made = await c.post(
                f"/repos/{repo}/pulls",
                json={"title": str(pr.get("title", ""))[:200], "head": branch, "base": base,
                      "body": str(pr.get("body", ""))[:4000], "draft": True},
            )
            if made.status_code != 201:
                return _result("error", detail=f"could not open the pull request ({made.status_code})")
            return _result("opened", url=str(made.json().get("html_url", "")))
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("crew publish failed: %s", type(exc).__name__)
        return _result("error", detail=_safe(f"GitHub call failed: {type(exc).__name__}"))
