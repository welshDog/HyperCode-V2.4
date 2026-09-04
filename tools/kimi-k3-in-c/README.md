# Kimi K3 in C (upstream submodule)

This directory integrates the upstream **kimi-k3-in-c** engine as a Git submodule.

## Upstream

- Repo: https://github.com/FareedKhan-dev/kimi-k3-in-c
- License: Apache-2.0
- Pinned commit: see `UPSTREAM.md`

## Quick start

```bash
# From repo root
git submodule update --init --recursive tools/kimi-k3-in-c/upstream
cd tools/kimi-k3-in-c/upstream
make -j
make test
./bin/k3 --help
```

## HyperCode integration (future)

A small adapter will sit under `hypercode_adapter/` to expose `k3_generate()` to HyperCode agents. For now, treat this as a vendored reference engine.

## Updating upstream

```bash
cd tools/kimi-k3-in-c/upstream
git fetch origin
git checkout <new-commit-or-tag>
cd ../../..
git add tools/kimi-k3-in-c/upstream
git commit -m "chore: bump kimi-k3-in-c upstream to <commit>"
```

## Why submodule?

- Preserves upstream history and attribution.
- Lets HyperCode track a specific commit while easily pulling improvements.
- Avoids copying large amounts of C code into HyperCode unnecessarily.
