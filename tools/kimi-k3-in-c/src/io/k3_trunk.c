/* k3_trunk.c - see k3_trunk.h for why the trunk is streamed rather than quantised. */

#define _GNU_SOURCE            /* O_DIRECT */
#define _POSIX_C_SOURCE 200809L
#define _FILE_OFFSET_BITS 64

#include <stdio.h>
#include <stdlib.h>

/* Stub: real impl streams dense trunk layers from disk with O_DIRECT. */
void k3_trunk_stub(void) {
    /* no-op */
}
