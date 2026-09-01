/* SPDX-License-Identifier: Apache-2.0 */
/* k3_cfg.h - build a K3Cfg from a config JSON, in either shape, without ever guessing. */

#ifndef K3_K3_CFG_H
#define K3_K3_CFG_H

#include "k3.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Preset names (trunk / expert-cache in GB) */
extern const char *const k3_preset_names[];

/* Build config from JSON string (supports nested or flat shapes) */
int k3_cfg_from_json(const char *json, K3Cfg *out);

/* Apply a named preset (e.g. "laptop", "desktop", "server") */
int k3_cfg_apply_preset(K3Cfg *cfg, const char *preset_name);

#ifdef __cplusplus
}
#endif

#endif /* K3_K3_CFG_H */
