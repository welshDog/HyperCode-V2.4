/* k3_st.c - safetensors reader for the real Kimi K3 checkpoint.
 *
 * WHY A HAND-WRITTEN SCANNER INSTEAD OF json.h
 *   A safetensors header is machine generated with a rigid shape: one flat object whose
 *   values are all small objects with exactly three known keys. Building a general DOM
 *   for it costs an allocation per node across 78 MB of JSON and 497,220 tensors, for
 *   no benefit. The scanner below walks the text once and writes straight into the
 *   index struct.
 *
 * This stub marks where the real parser lives in the upstream repo.
 */

#include <stddef.h>

void k3_st_stub(void) {
    /* no-op */
}
