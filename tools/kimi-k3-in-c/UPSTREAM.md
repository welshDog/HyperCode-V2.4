# Upstream: kimi-k3-in-c

- **URL:** https://github.com/FareedKhan-dev/kimi-k3-in-c
- **License:** Apache-2.0
- **Pinned commit:** `ff11dce858a2eb8a781224facdffd33a1fa48d25` (v1.0.0 release)
- **Why this commit:** First verified end-to-end release with fused matmul kernels, `--preset auto`, chunk-union prefill, conversation resume, and speculative decode. Byte-identical output preserved. [cite:12]

## How to initialize

```bash
git submodule update --init --recursive tools/kimi-k3-in-c/upstream
```

## How to update

```bash
cd tools/kimi-k3-in-c/upstream
git fetch origin
git checkout <new-commit-or-tag>
cd ../../..
git add tools/kimi-k3-in-c/upstream
git commit -m "chore: bump kimi-k3-in-c upstream to <commit>"
```

## Attribution

This project includes code from `FareedKhan-dev/kimi-k3-in-c`, licensed under Apache-2.0.
See the upstream `LICENSE` file in `upstream/`.
