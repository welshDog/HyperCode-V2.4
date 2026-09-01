# Kimi K3 in C (minimal core)

Portable C99 inference engine for Moonshot AI's Kimi K3 (2.8T MoE). Runs on a single CPU with ~8 GB RAM by streaming experts from disk. No BLAS, no GPU, no big framework.

## Build

```bash
cd tools/kimi-k3-in-c
make -j
```

Requires: C99 compiler + OpenMP (GCC ≥9 or Clang ≥10).

## Test

```bash
make test
```

Runs the engine against a tiny reference model (same tensor graph as K3). No checkpoint needed.

## Run inference

You need a Kimi K3 checkpoint and a packed trunk file. See the upstream repo for download/pack scripts:
https://github.com/FareedKhan-dev/kimi-k3-in-c

Example (adjust paths and preset):

```bash
./bin/k3 ~/k3model --trunk ~/k3trunk --preset laptop \
  --tok ~/k3model \
  --prompt "The capital of France is" --gen 8 --incremental
```

## Presets (trunk / expert-cache, GB)

- `ultra` 2.50 / 0.31 → ~3 GB (very slow, proof-of-life on 8 GB)
- `laptop` 3.00 / 1.00 → ~8.2 GB peak RSS
- `desktop` 16.00 / 10.00 → ~31.9 GB
- `workstation` 60.00 / 30.00 → ~95.5 GB
- `server` 110.00 / 13.00 → ~128 GB (fast per-token on big RAM)
- `max` 110.00 / 109.00 → ~224 GB

Run `./bin/k3 --list-presets` to see all options.

## Notes

- Base model inference only (no chat template).
- Use `--incremental` for multi-token generation (keeps KV cache + recurrent state).
- Keep trunk on fast local NVMe for best throughput.

Upstream: https://github.com/FareedKhan-dev/kimi-k3-in-c
