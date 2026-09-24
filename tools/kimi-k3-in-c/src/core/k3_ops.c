/* k3_ops.c - the numeric core of the Kimi K3 engine.
 *
 * Every routine here is gated on a JSON fixture under tests/fixtures/ops/, generated
 * by tools/emit_fixtures.py from the pure-torch reference. Per-op fixtures exist
 * alongside the full-model oracle because the oracle is pass-or-fail: it proves the
 * stack is wrong without indicating which of ~40 kernels is responsible.
 *
 * This stub file marks where the real kernels live in the upstream repo.
 */

#include <stddef.h>
#include <stdint.h>

/* Stub: real impl includes MXFP4 dequant, MoE routing, attention, etc. */
void k3_ops_stub(void) {
    /* no-op */
}
