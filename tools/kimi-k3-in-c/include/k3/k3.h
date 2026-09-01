/* SPDX-License-Identifier: Apache-2.0 */
/*
 * k3.h, Kimi K3 inference engine: public configuration and core types.
 *
 * OVERVIEW
 *   Kimi K3 is a 2.78-trillion-parameter mixture-of-experts model. This engine runs it
 *   on a single CPU by treating memory as a dial rather than a floor:
 *   - 93 layers, 896 experts, 16 active per token
 *   - 1M-token context window
 *   - MXFP4 quantised experts streamed from disk
 *
 * MEMORY MODEL
 *   The engine keeps two resident regions:
 *     1) trunk: dense layers (weights used every token)
 *     2) expert cache: a working set of recently-used experts
 *   All other experts are streamed from NVMe on demand.
 *
 * USAGE
 *   Build: make -j
 *   Test:  make test
 *   Run:   ./bin/k3 --help
 */

#ifndef K3_K3_H
#define K3_K3_H

#include <stddef.h>
#include <stdint.h>

/* Opaque engine handle */
typedef struct K3Engine K3Engine;

/* Runtime config (memory budget, presets, etc.) */
typedef struct K3Cfg K3Cfg;

/* Create/destroy engine */
K3Engine *k3_engine_create(const K3Cfg *cfg);
void k3_engine_destroy(K3Engine *eng);

/* Inference: token IDs in, token IDs out */
int k3_generate(K3Engine *eng, const uint32_t *input_ids, size_t input_len,
                uint32_t *output_ids, size_t output_max_len, size_t *out_len);

#endif /* K3_K3_H */
