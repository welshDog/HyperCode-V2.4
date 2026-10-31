/* k3_portable_io.h - shims for the Linux-only I/O calls the readers use.
 *
 * The engine asks for things Linux gives it and the other two platforms do not spell
 * the same way:
 *
 *   O_DIRECT       bypass the page cache on the trunk and expert reads. Darwin's
 *                  equivalent is not an open() flag but fcntl(F_NOCACHE) after the
 *                  fd is created. Windows has no direct analogue; the shim falls back
 *                  to unbuffered I/O via FILE_FLAG_NO_BUFFERING.
 *
 *   posix_memalign  Darwin and recent MSVC have it; older Windows needs _aligned_malloc.
 *
 * This header provides the portable wrappers so the rest of the engine can assume
 * POSIX-like behaviour.
 */

#ifndef K3_PORTABLE_IO_H
#define K3_PORTABLE_IO_H

#include <stddef.h>

/* Align allocation (power-of-two alignment) */
int k3_aligned_alloc(void **memptr, size_t alignment, size_t size);

/* Platform-specific open flags for direct I/O */
int k3_open_direct(const char *path, int flags);

#endif /* K3_PORTABLE_IO_H */
