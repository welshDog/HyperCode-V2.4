import argparse
import os
import sys
import subprocess
import time
import ast
import hashlib
import re
import json
from pathlib import Path

def _run(cmd, cwd=None, timeout=60):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def run_fast_tests(base):
    cores = Path(base) / "THE HYPERCODE" / "hypercode-core"
    eng = Path(base) / "THE HYPERCODE" / "hypercode-engine"
    rc1, out1, err1 = _run([sys.executable, "-m", "pytest", "tests/unit", "-q", "-o", "addopts=", "--timeout=25"], cwd=str(cores))
    rc2, out2, err2 = _run([sys.executable, "-m", "pytest", "tests/unit", "-q", "-o", "addopts=", "--timeout=25"], cwd=str(eng))
    return {
        "core": {"rc": rc1, "out": out1, "err": err1},
        "engine": {"rc": rc2, "out": out2, "err": err2},
    }

def _normalize_source(text):
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.startswith("import ") or s.startswith("from "):
            continue
        lines.append(s)
    return "\n".join(lines)

def _strip_comments_js(text: str) -> str:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text

def _strip_comments_cpp(text: str) -> str:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"^#.*", "", text, flags=re.M)
    return text

def _strip_comments_java(text: str) -> str:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text

def _normalize_by_lang(text: str, ext: str) -> str:
    e = ext.lower()
    if e.endswith(".py"):
        return _normalize_source(text)
    if e.endswith((".js", ".jsx", ".ts", ".tsx")):
        t = _strip_comments_js(text)
        lines = []
        for ln in t.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("import ") or s.startswith("export "):
                continue
            lines.append(s)
        return "\n".join(lines)
    if e.endswith((".cpp", ".hpp", ".cc", ".cxx")):
        t = _strip_comments_cpp(text)
        lines = []
        for ln in t.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("#"):
                continue
            lines.append(s)
        return "\n".join(lines)
    if e.endswith(".java"):
        t = _strip_comments_java(text)
        lines = []
        for ln in t.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("import ") or s.startswith("package "):
                continue
            lines.append(s)
        return "\n".join(lines)
    return _normalize_source(text)

def _file_fingerprint(path, min_lines: int, min_similarity: float):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return None
    norm = _normalize_by_lang(text, Path(path).suffix)
    if not norm:
        return None
    lines = norm.splitlines()
    if len(lines) < min_lines:
        return None
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return h, len(lines), norm

def _func_fingerprints(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return []
    try:
        tree = ast.parse(text)
    except Exception:
        return []
    fps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body_dump = ast.dump(ast.Module(body=node.body, type_ignores=[]), annotate_fields=False, include_attributes=False)
            h = hashlib.sha256(body_dump.encode("utf-8")).hexdigest()
            fps.append((node.name, h))
    return fps

def _func_fingerprints_text(text: str, lang: str) -> list:
    items = []
    if lang in ("js", "ts"):
        for m in re.finditer(r"function\s+(\w+)\s*\([^)]*\)\s*\{", text):
            start = m.end() - 1
            name = m.group(1)
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{': depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        block = text[start:i+1]
                        h = hashlib.sha256(block.encode("utf-8")).hexdigest()
                        items.append((name, h))
                        break
    if lang in ("cpp", "java"):
        for m in re.finditer(r"\b(\w+)\s*\([^)]*\)\s*\{", text):
            start = m.end() - 1
            name = m.group(1)
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{': depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        block = text[start:i+1]
                        h = hashlib.sha256(block.encode("utf-8")).hexdigest()
                        items.append((name, h))
                        break
    return items

def detect_duplicates(paths, min_lines: int, top: int, min_similarity: float, exts: tuple):
    files = []
    for p in paths:
        for fp in Path(p).rglob("*"):
            if fp.suffix.lower() in exts:
                files.append(str(fp))
    file_map = {}
    file_norms = {}
    total_lines = 0
    for f in files:
        fp = _file_fingerprint(f, min_lines, min_similarity)
        if not fp:
            continue
        h, ln, norm = fp
        total_lines += ln
        file_map.setdefault(h, []).append((f, ln))
        file_norms[f] = (ln, norm)
    file_dupes = []
    for h, items in file_map.items():
        if len(items) > 1:
            file_dupes.append(items)
    # similarity-based grouping (percentage threshold)
    similar_groups = []
    if min_similarity > 0:
        vec = list(file_norms.items())
        for i in range(len(vec)):
            fi, (lni, ni) = vec[i]
            grp = [(fi, lni)]
            for j in range(i+1, len(vec)):
                fj, (lnj, nj) = vec[j]
                import difflib
                r = difflib.SequenceMatcher(None, ni, nj).ratio()
                if r >= min_similarity:
                    grp.append((fj, lnj))
            if len(grp) > 1:
                similar_groups.append(grp)
    func_map = {}
    for f in files:
        if f.endswith(".py"):
            for name, h in _func_fingerprints(f):
                func_map.setdefault(h, []).append((f, name))
        else:
            text = Path(f).read_text(encoding="utf-8")
            lang = "js" if Path(f).suffix.lower() in (".js", ".jsx", ".ts", ".tsx") else (
                "cpp" if Path(f).suffix.lower() in (".cpp", ".hpp", ".cc", ".cxx") else (
                    "java" if Path(f).suffix.lower() == ".java" else ""
                )
            )
            for name, h in _func_fingerprints_text(text, lang):
                func_map.setdefault(h, []).append((f, name))
    func_dupes = []
    for h, items in func_map.items():
        if len(items) > 1:
            func_dupes.append(items)
    # compute duplicate percentage (approx): sum lines of duplicates beyond first / total lines
    dup_lines = 0
    for grp in file_dupes:
        grp_sorted = sorted(grp, key=lambda x: -x[1])
        for _, ln in grp_sorted[1:]:
            dup_lines += ln
    dup_percent = (dup_lines / max(total_lines, 1)) * 100.0
    # apply top limit
    file_dupes = file_dupes[:top]
    func_dupes = func_dupes[:top]
    similar_groups = similar_groups[:top]
    return file_dupes, func_dupes, similar_groups, dup_percent, total_lines

def _load_config(config_path: str):
    cfg = {}
    p = Path(config_path)
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    return cfg

def _validate_args(args):
    if args.top < 1 or args.top > 100:
        raise SystemExit("--top must be between 1 and 100")
    if args.min_lines < 1:
        raise SystemExit("--min-lines must be >= 1")
    if args.min_similarity < 0 or args.min_similarity > 1:
        raise SystemExit("--min-similarity must be between 0 and 1")
    return True

def _list_files(paths, exts):
    out = []
    for p in paths:
        for f in Path(p).rglob("*"):
            if f.is_file() and f.suffix.lower() in exts:
                out.append(str(f))
    return out

def watch_loop(args, paths, exts):
    files = _list_files(paths, exts)
    mtimes = {f: os.path.getmtime(f) for f in files}
    print(f"[watch] monitoring {len(files)} files; press Ctrl+C to stop")
    pending = False
    last_change = 0.0
    try:
        while True:
            time.sleep(0.2)
            changed = False
            for f in files:
                try:
                    m = os.path.getmtime(f)
                except FileNotFoundError:
                    m = 0
                if mtimes.get(f, 0) != m:
                    mtimes[f] = m
                    changed = True
            if changed:
                pending = True
                last_change = time.time()
            if pending and (time.time() - last_change) >= args.debounce:
                pending = False
                run_once(args)
    except KeyboardInterrupt:
        print("[watch] stopped")

def run_once(args):
    base = args.base
    results = run_fast_tests(base)
    core_ok = results["core"]["rc"] == 0
    eng_ok = results["engine"]["rc"] == 0
    paths = [
        str(Path(base) / "THE HYPERCODE" / "hypercode-core" / "app"),
        str(Path(base) / "THE HYPERCODE" / "hypercode-engine" / "hypercode_engine"),
    ]
    exts = tuple(e.lower() for e in args.exts)
    file_dupes, func_dupes, similar_groups, dup_percent, total_lines = detect_duplicates(paths, args.min_lines, args.top, args.min_similarity, exts)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    summary = {
        "timestamp": ts,
        "core_ok": core_ok,
        "engine_ok": eng_ok,
        "duplicate_percent": round(dup_percent, 3),
        "total_lines": total_lines,
        "file_duplicates": file_dupes,
        "function_duplicates": func_dupes,
        "similar_groups": similar_groups,
    }
    if args.output == "json":
        print(json.dumps(summary, indent=2))
    elif args.output == "xml":
        def xml_escape(s):
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        print(f"<summary timestamp=\"{ts}\" dup_percent=\"{round(dup_percent,3)}\">")
        print(f"  <tests core=\"{core_ok}\" engine=\"{eng_ok}\" />")
        print(f"  <total_lines>{total_lines}</total_lines>")
        print("</summary>")
    else:
        print("Lean Review Summary")
        print(f"[{ts}] Core Tests: {'OK' if core_ok else 'FAIL'}")
        print(f"[{ts}] Engine Tests: {'OK' if eng_ok else 'FAIL'}")
        print(f"Duplicate Percent: {round(dup_percent,3)}% (threshold {args.max_dup_percent}%)")
        print(f"File Duplicates: {len(file_dupes)} groups")
        for grp in file_dupes[:args.top]:
            print("GROUP:")
            for f, ln in grp:
                print(f"{f} ({ln} lines)")
        print(f"Function Duplicates: {len(func_dupes)} groups")
        for grp in func_dupes[:args.top]:
            print("GROUP:")
            for f, name in grp:
                print(f"{name} -> {f}")
        if similar_groups:
            print(f"Similarity Groups: {len(similar_groups)}")
    return 0 if core_ok and eng_ok and (dup_percent <= args.max_dup_percent) else 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--debounce", type=float, default=0.5)
    parser.add_argument("--min-lines", type=int, default=5)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--min-similarity", type=float, default=0.0)
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / ".duplicaterrc"))
    parser.add_argument("--output", choices=["plain", "json", "xml"], default="plain")
    parser.add_argument("--max-dup-percent", type=float, default=5.0)
    parser.add_argument("--exts", nargs="*", default=[".py", ".js", ".jsx", ".ts", ".tsx", ".cpp", ".hpp", ".cc", ".cxx", ".java"])
    args = parser.parse_args()
    cfg = _load_config(args.config)
    for k in ("min_lines", "top", "min_similarity", "max_dup_percent"):
        if k in cfg:
            setattr(args, k.replace("_", "-"), cfg[k])
    _validate_args(args)
    t0 = time.time()
    if args.watch:
        paths = [
            str(Path(args.base) / "THE HYPERCODE" / "hypercode-core" / "app"),
            str(Path(args.base) / "THE HYPERCODE" / "hypercode-engine" / "hypercode_engine"),
        ]
        watch_loop(args, paths, tuple(e.lower() for e in args.exts))
        return 0
    rc = run_once(args)
    print(f"Duration: {round(time.time() - t0, 3)}s")
    return rc

if __name__ == "__main__":
    sys.exit(main())
