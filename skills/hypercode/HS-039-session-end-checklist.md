# HS-039 — Session End Checklist

> **Extracted from:** `CLAUDE.md §11` · HyperCode-V2.4
> **Run this at the end of EVERY session, no exceptions.**

---

## The Checklist

- [ ] All code: lint + type-check + build green
- [ ] All changes pushed to GitHub — **nothing is done until committed**
- [ ] New `docs/SESSION_REPORT_[DATE].md` created + pushed
- [ ] `NEXT_SESSION_HANDOVER_[DATE].md` written — open gates + first task
- [ ] Tell Lyndz the first task for next session (one sentence)
- [ ] Celebrate the wins 🎉

## Why This Matters

- Prevents "I thought we did that" confusion next session
- The handover doc = Lyndz's brain save file 💾
- Uncommitted = doesn't exist

## Quick Commands

```bash
# Type-check (course)
npx tsc --noEmit && npx eslint && npm run build

# Push everything
git add -A && git commit -m "docs: session end report [DATE]" && git push

# Session report location
docs/SESSION_REPORT_YYYY-MM-DD.md
```

---

> 🔑 Session end = gate. Nothing leaves until this checklist is green.
