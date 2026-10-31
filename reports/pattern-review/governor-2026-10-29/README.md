# Pattern review: `governor` (2026-10-29)

The approval trail for the first Pattern Foundry packet. Archived here because it was
produced in a temporary session folder. No secrets: names, digests and structural metadata only.

| File | What it is |
|---|---|
| `governor_inventory.json` | Inventory of `agents/governor` (**schema 1**, produced 2026-10-29). |
| `governor_approval.json` | Human approval `governor-2026-10-29-lyndz` (approved by Lyndz, 2026-10-29T19:53:01Z), bound to the inventory digest `1eb7dc76aab5cf03…`. |
| `governor_packet.json` | The review packet built from the two files above: 2 candidates, `pending_human_review`, synthesis and execution **not** authorised. |

## Status

- **Decisions: none recorded.** The packet is still waiting for a human accept / reject / defer per candidate
  (use the dashboard `/pattern-review` page, which exports a decision record, or write one by hand).
- The approval is a local record, not a cryptographic identity. It authorises building a *review packet*
  only. It never authorises synthesis or execution.

## Re-checking this packet

The packet is reproducible. From the repo root:

```
python -c "import json,sys; sys.path.insert(0,'scripts'); import pattern_review as p; d='reports/pattern-review/governor-2026-10-29/'; i=json.load(open(d+'governor_inventory.json')); a=json.load(open(d+'governor_approval.json')); print(p.build_review(i,a)==json.load(open(d+'governor_packet.json')))"
```

It should print `True`. To check the inventory against the live source, re-run
`python scripts/architecture_inventory.py agents/governor` and compare the manifest hashes.
(A schema 1 inventory only has `sha256`, which is a hash of the *extracted metadata*, not of the file.)

## Schema 2 (current tooling)

`architecture_inventory.py` now emits schema 2: `metadata_sha256` plus `content_sha256` (the file with
CRLF normalised to LF, so you can hash the real file and compare; withheld when the file looks
secret-bearing), compose hardening flags, and a bounded AST scan of Python modules (routes, risky imports).
`pattern_review.py` still accepts schema 1, so this approval remains valid.

A schema 2 inventory has a **different digest**, so it needs a **new approval**. This one cannot be reused.
That is the gate working as designed. Re-run the inventory, review it, create a new approval file, then build
the packet. Keep the resulting folder next to this one.
