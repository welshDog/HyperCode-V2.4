# Docker Scout CVE Baseline - 2026-09-07

> First-party `docker scout` baseline of the images running / built on this box.
> Companion to `scripts/docker-scout-audit.ps1` (which scans the pushed v2.4.2 registry tags).

| Field | Value |
|---|---|
| Generated | 2026-09-07 19:22:49 +01:00 |
| Scout | version: v1.24.0 (go1.26.3 - windows/amd64) |
| Host | WSL2 / Docker Desktop |

## Summary

| Image | Size (MB) | CRITICAL | HIGH | MEDIUM | LOW | Status |
|---|---:|---:|---:|---:|---:|---|
| hypercode-core | 506 | 4 | 53 | 35 | 61 | CRITICAL |
| healer-agent | 449 | 2 | 14 | 27 | 57 | CRITICAL |
| safety-shepherd | 117 | 2 | 19 | 51 | 76 | CRITICAL |
| hyper-brain | 95 | 1 | 9 | 27 | 58 | CRITICAL |
| hyperhealth-worker | 80 | 2 | 24 | 30 | 66 | CRITICAL |
| hypercode-mcp-server | 63 | 2 | 20 | 16 | 44 | CRITICAL |
| agent-mcp-bridge | 62 | 0 | 2 | 8 | 25 | HIGH |
| memstream | 52 | 3 | 27 | 25 | 64 | CRITICAL |
| postgres | 105 | 5 | 38 | 27 | 7 | CRITICAL |
| redis | 36 | 3 | 18 | 6 | 2 | CRITICAL |

**Totals across scanned images: CRITICAL 24 | HIGH 224**

## Image digests (for comparable re-scan)

- **hypercode-core** `hypercode-core@sha256:24bf0a976a620a8b4993185b789f939a89977d7c5b38d053f87d547a1f7bcc49`
- **healer-agent** `hypercode-v24-healer-agent@sha256:1382b0520d261e205a223a6b1cd8ba01dcfa89843023124c6610a23839fa974e`
- **safety-shepherd** `safety-shepherd@sha256:8f6a6982a30bbe8ecdd5434f596b09919e767f9926103906aff8dd6983a995a2`
- **hyper-brain** `hypercode-v24-hyper-brain@sha256:266a84bfd0444b0fc7f7791cf9718d04070c8542b66b112cd78d0736d12d5b73`
- **hyperhealth-worker** `hypercode-v20-hyperhealth-worker@sha256:e41fac4ae15486d3688ff5d1ce47814db8df716b3319827b2a13f5ce76f06f56`
- **hypercode-mcp-server** `hypercode-v24-hypercode-mcp-server@sha256:137a934a4093f56fb19b52a34f0f472b7df3a0af478a207b941493021917316c`
- **agent-mcp-bridge** `hypercode-v24-agent-mcp-bridge@sha256:0e8693ac26e2883c53334d668fd48036b46e0b8f6aef66d129452d0829d9ccfb`
- **memstream** `hypercode-memstream@sha256:a72f59a3d94c929e099cfaf3419e2dda8a4681fa982974f0c8ec9fce82e62fd5`
- **postgres** `postgres@sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`
- **redis** `redis@sha256:09160599abd229764c0fb44cb6be640294e1d360a54b19985ab4843dcf2d90f1`

## Analysis — where the CVEs actually are

Two clusters, and both are mostly a **base-image / rebuild problem**, not app code.
This baseline supersedes the "0 known vulns" note (2026-06-27) — that is stale.

### 1. Stale base images (the bulk of it)

`docker scout quickview` reports what a base bump alone would clear:

| Image(s) | Current base | Fix | Base CVEs cleared |
|---|---|---|---|
| `memstream` | `python:3.9-slim` | → `python:3.12-slim` | **3C / 26H → 0C / 1H** (biggest single win) |
| `hyper-brain`, `hypercode-mcp-server` | `python:3.11-slim` | → `python:3.12-slim` (or `3.14`) | 2C / 11H → 0C / 1-3H |
| `hypercode-core`, `healer-agent`, `hyperhealth-worker`, `safety-shepherd` | `python:3.11/3.12-slim` | `docker pull` + rebuild ("refreshed base"), then → `3.14-slim` | ~1-2C / 4-11H → 0C / 1H |
| `postgres:16-alpine`, `redis:8-alpine` | `alpine:3` (3.23) | `docker pull` to get the rebuilt official image; openssl fix is `3.5.8-r0` | 3C / 15H → 0C / 0H once upstream rebuilds land |

Most agents haven't been rebuilt since their base was pulled — a plain
`docker pull python:3.12-slim` + `--no-cache` rebuild clears the "refreshed base
image" column (mostly HIGH/MEDIUM). Moving the `FROM` minor (3.9→3.12, 3.11→3.12,
3.12→3.14) clears the CRITICALs.

**Counter-example:** `agent-mcp-bridge` is the only near-clean image (0C / 2H) —
it was rebuilt for the v5 bake a few days ago. Rebuilding on a current base works.

### 2. App-dependency CVEs (mostly `hypercode-core`)

Independent of the base — need `requirements.txt` bumps:

| Package | In image | Has | Fix | Severity |
|---|---|---|---|---|
| `gitpython` | hypercode-core | 3.1.50 | **3.1.59** | 1 CRITICAL + ~20 HIGH — highest-value single bump |
| `chromadb` | hypercode-core, memstream | 1.0.15 | **not fixed** (2 criticals, code-injection) | 2 CRITICAL — no patch; mitigate by network isolation / access control |
| `mcp` | hypercode-core, hypercode-mcp-server | 1.26.0 | **1.28.1** | 3 HIGH (auth bypass, ws origin) — coordinate: `mcp` pinning caused the Sept prod outage |
| `openssl` (Debian layer) | hypercode-core | 3.5.6-1~deb13u2 | **3.5.7-1~deb13u2** | 1 CRITICAL + 3 HIGH — comes with a base refresh |
| `cryptography` 46.0.7, `tornado` 6.5.5, `starlette` 0.49.1, `aiohttp` 3.13.4, `pyjwt` 2.12.0, `pyarrow` 21.0.0, `python-multipart` 0.0.27, `msgpack` 1.1.2 | hypercode-core | one minor behind each | current | ~1-3 HIGH each |

### Suggested order (effort → impact)

1. `requirements.txt`: `gitpython>=3.1.59`, `mcp>=1.28.1` (mind the outage history), then the rest of the one-behind list. Rebuild `hypercode-core`. Biggest CVE drop for least work.
2. `memstream/Dockerfile`: `python:3.9-slim` → `python:3.12-slim`. One line, clears 3C/26H.
3. `docker pull python:3.11-slim python:3.12-slim` + `--no-cache` rebuild the agent fleet on the next build cycle.
4. `docker pull postgres:16-alpine redis:8-alpine` to pick up upstream Alpine rebuilds.
5. `chromadb`: no fix — confirm it's not reachable off the internal network.

Re-run `.\scripts\docker-scout-baseline.ps1` after each and diff the digests + counts above.

## Per-image detail

### hypercode-core

- ref: `hypercode-core:latest`
- digest: `hypercode-core@sha256:24bf0a976a620a8b4993185b789f939a89977d7c5b38d053f87d547a1f7bcc49`
- size: 506 MB

```
    v SBOM of image already cached, 523 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  hypercode-core:latest  │    4C    53H    35M    61L     2?  
   digest             │  24bf0a976a62           │                                    
 Base image           │  python:3.12-slim       │    1C     4H     9M    33L     2?  
 Refreshed base image │  python:3.12-slim       │    0C     1H     6M    25L         
                      │                         │    -1     -3     -3     -8     -2  
 Updated base image   │  python:3.14-slim       │    0C     4H     2M    24L         
                      │                         │    -1            -7     -9     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (33%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 v      │ Default non-root user                          │                             
 !      │ Copyleft licensed packages found               │    463 packages             
 !      │ Fixable critical or high vulnerabilities found │    2C    49H     0M     0L  
 !      │ High-profile vulnerabilities found             │    0C     0H     1M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-core:latest
    View vulnerabilities → docker scout cves hypercode-core:latest
    View base image update recommendations → docker scout recommendations hypercode-core:latest
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-core:latest

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 523 packages indexed
    x Detected 19 vulnerable packages with a total of 57 vulnerabilities


## Overview

                   │       Analyzed Image        
───────────────────┼─────────────────────────────
 Target            │  hypercode-core:latest      
   digest          │  24bf0a976a62               
   platform        │ linux/amd64                 
   vulnerabilities │    4C    53H     0M     0L  
   size            │ 530 MB                      
   packages        │ 523                         


## Packages and Vulnerabilities

   2C     2H     0M     0L  chromadb 1.0.15
pkg:pypi/chromadb@1.0.15

    x CRITICAL CVE-2026-45833 [Improper Control of Generation of Code ('Code Injection')]
      https://scout.docker.com/v/CVE-2026-45833?s=github&n=chromadb&t=pypi&vr=%3E%3D0.4.17%2C%3C%3D1.5.9
      Affected range : >=0.4.17                                                        
                     : <=1.5.9                                                         
      Fixed version  : not fixed                                                       
      CVSS Score     : 9.4                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H 
    
    x CRITICAL CVE-2026-45829 [Improper Control of Generation of Code ('Code Injection')]
      https://scout.docker.com/v/CVE-2026-45829?s=github&n=chromadb&t=pypi&vr=%3E%3D1.0.0%2C%3C%3D1.5.9
      Affected range : >=1.0.0                                                             
                     : <=1.5.9                                                             
      Fixed version  : not fixed                                                           
      CVSS Score     : 9.3                                                                 
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H/E:P 
    
    x HIGH CVE-2026-45831 [Incorrect Authorization]
      https://scout.docker.com/v/CVE-2026-45831?s=github&n=chromadb&t=pypi&vr=%3E%3D0.5.0%2C%3C%3D1.5.9
      Affected range : >=0.5.0                                                         
                     : <=1.5.9                                                         
      Fixed version  : not fixed                                                       
      CVSS Score     : 8.8                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N 
    
    x HIGH CVE-2026-45830 [Incorrect Privilege Assignment]
      https://scout.docker.com/v/CVE-2026-45830?s=github&n=chromadb&t=pypi&vr=%3E%3D0.4.17%2C%3C%3D1.5.9
      Affected range : >=0.4.17                                                        
                     : <=1.5.9                                                         
      Fixed version  : not fixed                                                       
      CVSS Score     : 8.8                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N 
    

   1C    20H     0M     0L  gitpython 3.1.50
pkg:pypi/gitpython@3.1.50

    x CRITICAL CVE-2026-78676
      https://scout.docker.com/v/CVE-2026-78676?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.59
      Affected range : <3.1.59                                                         
      Fixed version  : 3.1.59                                                          
      CVSS Score     : 9.3                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-wvpp-8hx9-p66j [Improper Neutralization of Argument Delimiters in a Command ('Argument Injection')]
      https://scout.docker.com/v/GHSA-wvpp-8hx9-p66j?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.57
      Affected range : <=3.1.57                                     
      Fixed version  : 3.1.58                                       
      CVSS Score     : 8.8                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-r9mr-m37c-5fr3 [Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')]
      https://scout.docker.com/v/GHSA-r9mr-m37c-5fr3?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.53
      Affected range : <=3.1.53                                     
      Fixed version  : 3.1.54                                       
      CVSS Score     : 8.8                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-jm78-9fvv-mhgr [Improper Neutralization of Special Elements in Output Used by a Downstream Component ('Injection')]
      https://scout.docker.com/v/GHSA-jm78-9fvv-mhgr?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.57
      Affected range : <=3.1.57                                     
      Fixed version  : 3.1.58                                       
      CVSS Score     : 8.8                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-2f96-g7mh-g2hx [Incomplete List of Disallowed Inputs]
      https://scout.docker.com/v/GHSA-2f96-g7mh-g2hx?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.50
      Affected range : <=3.1.50                                     
      Fixed version  : 3.1.51                                       
      CVSS Score     : 8.8                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-v396-v7q4-x2qj [Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')]
      https://scout.docker.com/v/GHSA-v396-v7q4-x2qj?s=github&n=gitpython&t=pypi&vr=%3D3.1.50
      Affected range : =3.1.50                                                         
      Fixed version  : 3.1.51                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-78677
      https://scout.docker.com/v/CVE-2026-78677?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.59
      Affected range : <3.1.59                                                         
      Fixed version  : 3.1.59                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-76221
      https://scout.docker.com/v/CVE-2026-76221?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.58
      Affected range : <3.1.58                                                         
      Fixed version  : 3.1.58                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-956x-8gvw-wg5v [Improper Neutralization of Special Elements used in a Command ('Command Injection')]
      https://scout.docker.com/v/GHSA-956x-8gvw-wg5v?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.50
      Affected range : <=3.1.50                                     
      Fixed version  : 3.1.51                                       
      CVSS Score     : 8.4                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH CVE-2026-76222
      https://scout.docker.com/v/CVE-2026-76222?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.58
      Affected range : <3.1.58                                                         
      Fixed version  : 3.1.58                                                          
      CVSS Score     : 8.4                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:H/VA:L/SC:N/SI:H/SA:L 
    
    x HIGH GHSA-hmq2-w58f-27jc [Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')]
      https://scout.docker.com/v/GHSA-hmq2-w58f-27jc?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.57
      Affected range : <=3.1.57                                     
      Fixed version  : 3.1.58                                       
      CVSS Score     : 8.2                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:N/I:H/A:L 
    
    x HIGH GHSA-fjr4-x663-mwxc [Improper Neutralization of Argument Delimiters in a Command ('Argument Injection')]
      https://scout.docker.com/v/GHSA-fjr4-x663-mwxc?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.53
      Affected range : <=3.1.53                                     
      Fixed version  : 3.1.54                                       
      CVSS Score     : 8.1                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H 
    
    x HIGH GHSA-4gmw-gg2m-w46p [Improper Neutralization of Argument Delimiters in a Command ('Argument Injection')]
      https://scout.docker.com/v/GHSA-4gmw-gg2m-w46p?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.57
      Affected range : <=3.1.57                                     
      Fixed version  : 3.1.58                                       
      CVSS Score     : 8.1                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H 
    
    x HIGH GHSA-3f7w-8rr8-f37f [Exposure of Sensitive Information to an Unauthorized Actor]
      https://scout.docker.com/v/GHSA-3f7w-8rr8-f37f?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.56
      Affected range : <=3.1.56                                     
      Fixed version  : 3.1.57                                       
      CVSS Score     : 8.1                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H 
    
    x HIGH CVE-2026-78675
      https://scout.docker.com/v/CVE-2026-78675?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.59
      Affected range : <3.1.59                                      
      Fixed version  : 3.1.59                                       
      CVSS Score     : 7.8                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-rwj8-pgh3-r573 [Exposure of Sensitive Information to an Unauthorized Actor]
      https://scout.docker.com/v/GHSA-rwj8-pgh3-r573?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.51
      Affected range : <=3.1.51                                     
      Fixed version  : 3.1.52                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    
    x HIGH GHSA-9rj7-rf2p-w77r [Improper Neutralization of Argument Delimiters in a Command ('Argument Injection')]
      https://scout.docker.com/v/GHSA-9rj7-rf2p-w77r?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.57
      Affected range : <=3.1.57                                     
      Fixed version  : 3.1.58                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH GHSA-94p4-4cq8-9g67 [Exposure of Sensitive Information to an Unauthorized Actor]
      https://scout.docker.com/v/GHSA-94p4-4cq8-9g67?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.53
      Affected range : <=3.1.53                                     
      Fixed version  : 3.1.55                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    
    x HIGH GHSA-6p8h-3wgx-97gf [Incomplete List of Disallowed Inputs]
      https://scout.docker.com/v/GHSA-6p8h-3wgx-97gf?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.53
      Affected range : <=3.1.53                                     
      Fixed version  : 3.1.54                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H 
    
    x HIGH CVE-2026-78678
      https://scout.docker.com/v/CVE-2026-78678?s=pypa&n=gitpython&t=pypi&vr=%3C3.1.59
      Affected range : <3.1.59                                                         
      Fixed version  : 3.1.59                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-3rp5-jjmw-4wv2 [Improper Neutralization of Special Elements in Output Used by a Downstream Component ('Injection')]
      https://scout.docker.com/v/GHSA-3rp5-jjmw-4wv2?s=github&n=gitpython&t=pypi&vr=%3C%3D3.1.52
      Affected range : <=3.1.52                                     
      Fixed version  : 3.1.53                                       
      CVSS Score     : 7.0                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:H/PR:N/UI:R/S:U/C:H/I:H/A:H 
    

   1C     3H     0M     0L  openssl 3.5.6-1~deb13u2
pkg:deb/debian/openssl@3.5.6-1~deb13u2?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    

   0C     3H     0M     0L  cryptography 46.0.7
pkg:pypi/cryptography@46.0.7

    x HIGH CVE-2026-69249 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-69249?s=github&n=cryptography&t=pypi&vr=%3E%3D42.0.0%2C%3C%3D48.0.0
      Affected range : >=42.0.0                                                        
                     : <=48.0.0                                                        
      Fixed version  : 49.0.0                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-69247 [Observable Timing Discrepancy]
      https://scout.docker.com/v/CVE-2026-69247?s=github&n=cryptography&t=pypi&vr=%3E%3D44.0.0%2C%3C50.0.0
      Affected range : >=44.0.0                                                        
                     : <50.0.0                                                         
      Fixed version  : 50.0.0                                                          
      CVSS Score     : 8.2                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-537c-gmf6-5ccf [Out-of-bounds Read]
      https://scout.docker.com/v/GHSA-537c-gmf6-5ccf?s=github&n=cryptography&t=pypi&vr=%3E%3D0.5.0%2C%3C48.0.1
      Affected range : >=0.5.0                                      
                     : <48.0.1                                      
      Fixed version  : 48.0.1                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     3H     0M     0L  tornado 6.5.5
pkg:pypi/tornado@6.5.5

    x HIGH CVE-2026-49853 [Exposure of Sensitive Information to an Unauthorized Actor]
      https://scout.docker.com/v/CVE-2026-49853?s=github&n=tornado&t=pypi&vr=%3C6.5.6
      Affected range : <6.5.6                                       
      Fixed version  : 6.5.6                                        
      CVSS Score     : 7.7                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N 
    
    x HIGH CVE-2026-82397 [Improper Validation of Specified Quantity in Input]
      https://scout.docker.com/v/CVE-2026-82397?s=github&n=tornado&t=pypi&vr=%3C%3D6.5.7
      Affected range : <=6.5.7                                      
      Fixed version  : 6.5.8                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-49855 [Improper Handling of Highly Compressed Data (Data Amplification)]
      https://scout.docker.com/v/CVE-2026-49855?s=github&n=tornado&t=pypi&vr=%3C6.5.6
      Affected range : <6.5.6                                       
      Fixed version  : 6.5.6                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     3H     0M     0L  mcp 1.26.0
pkg:pypi/mcp@1.26.0

    x HIGH CVE-2026-59950 [Missing Origin Validation in WebSockets]
      https://scout.docker.com/v/CVE-2026-59950?s=github&n=mcp&t=pypi&vr=%3C1.28.1
      Affected range : <1.28.1                                                         
      Fixed version  : 1.28.1                                                          
      CVSS Score     : 7.6                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-52870 [Missing Authorization]
      https://scout.docker.com/v/CVE-2026-52870?s=github&n=mcp&t=pypi&vr=%3E%3D1.23.0%2C%3C%3D1.27.1
      Affected range : >=1.23.0                                     
                     : <=1.27.1                                     
      Fixed version  : 1.27.2                                       
      CVSS Score     : 7.6                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:L 
    
    x HIGH CVE-2026-52869 [Authorization Bypass Through User-Controlled Key]
      https://scout.docker.com/v/CVE-2026-52869?s=github&n=mcp&t=pypi&vr=%3C%3D1.27.1
      Affected range : <=1.27.1                                     
      Fixed version  : 1.27.2                                       
      CVSS Score     : 7.1                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:L 
    

   0C     3H     0M     0L  pyasn1 0.6.3
pkg:pypi/pyasn1@0.6.3

    x HIGH CVE-2026-59886 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-59886?s=github&n=pyasn1&t=pypi&vr=%3C%3D0.6.3
      Affected range : <=0.6.3                                      
      Fixed version  : 0.6.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-59885 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-59885?s=github&n=pyasn1&t=pypi&vr=%3C%3D0.6.3
      Affected range : <=0.6.3                                      
      Fixed version  : 0.6.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-59884 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-59884?s=github&n=pyasn1&t=pypi&vr=%3C0.6.4
      Affected range : <0.6.4                                       
      Fixed version  : 0.6.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     2H     0M     0L  msgpack 1.1.2
pkg:pypi/msgpack@1.1.2

    x HIGH GHSA-6v7p-g79w-8964 [Use After Free]
      https://scout.docker.com/v/GHSA-6v7p-g79w-8964?s=github&n=msgpack&t=pypi&vr=%3C%3D1.2.0
      Affected range : <=1.2.0                                      
      Fixed version  : 1.2.1                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-57585
      https://scout.docker.com/v/CVE-2026-57585?s=pypa&n=msgpack&t=pypi&vr=%3C1.2.1
      Affected range : <1.2.1                                       
      Fixed version  : 1.2.1                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     2H     0M     0L  soupsieve 2.7
pkg:pypi/soupsieve@2.7

    x HIGH CVE-2026-49477 [Inefficient Regular Expression Complexity]
      https://scout.docker.com/v/CVE-2026-49477?s=github&n=soupsieve&t=pypi&vr=%3C%3D2.8.3
      Affected range : <=2.8.3                                      
      Fixed version  : 2.8.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-49476 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-49476?s=github&n=soupsieve&t=pypi&vr=%3C%3D2.8.3
      Affected range : <=2.8.3                                      
      Fixed version  : 2.8.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     2H     0M     0L  starlette 0.49.1
pkg:pypi/starlette@0.49.1

    x HIGH CVE-2026-54283 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-54283?s=github&n=starlette&t=pypi&vr=%3E%3D0.4.1%2C%3C1.3.1
      Affected range : >=0.4.1                                      
                     : <1.3.1                                       
      Fixed version  : 1.3.1                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-48818 [Server-Side Request Forgery (SSRF)]
      https://scout.docker.com/v/CVE-2026-48818?s=github&n=starlette&t=pypi&vr=%3C1.1.0
      Affected range : <1.1.0                                       
      Fixed version  : 1.1.0                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    

   0C     2H     0M     0L  python-engineio 4.12.2
pkg:pypi/python-engineio@4.12.2

    x HIGH CVE-2026-48809 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-48809?s=github&n=python-engineio&t=pypi&vr=%3C%3D4.13.1
      Affected range : <=4.13.1                                     
      Fixed version  : 4.13.2                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-48802 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-48802?s=github&n=python-engineio&t=pypi&vr=%3C%3D4.13.1
      Affected range : <=4.13.1                                     
      Fixed version  : 4.13.2                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     1H     0M     0L  python-socketio 5.14.0
pkg:pypi/python-socketio@5.14.0

    x HIGH CVE-2026-48804 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-48804?s=github&n=python-socketio&t=pypi&vr=%3C%3D5.16.1
      Affected range : <=5.16.1                                     
      Fixed version  : 5.16.2                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     1H     0M     0L  aiohttp 3.13.4
pkg:pypi/aiohttp@3.13.4

    x HIGH CVE-2026-69244 [Out-of-bounds Read]
      https://scout.docker.com/v/CVE-2026-69244?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.14.2
      Affected range : <=3.14.2                                                        
      Fixed version  : 3.14.3                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    

   0C     1H     0M     0L  ecdsa 0.19.2
pkg:pypi/ecdsa@0.19.2

    x HIGH CVE-2024-23342 [Observable Discrepancy]
      https://scout.docker.com/v/CVE-2024-23342?s=github&n=ecdsa&t=pypi&vr=%3E%3D0
      Affected range : >=0                                          
      Fixed version  : not fixed                                    
      CVSS Score     : 7.4                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N 
    

   0C     1H     0M     0L  python-multipart 0.0.27
pkg:pypi/python-multipart@0.0.27

    x HIGH CVE-2026-53539 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-53539?s=github&n=python-multipart&t=pypi&vr=%3C0.0.30
      Affected range : <0.0.30                                      
      Fixed version  : 0.0.30                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     1H     0M     0L  click 8.2.1
pkg:pypi/click@8.2.1

    x HIGH CVE-2026-7246

What's next:
    View base image update recommendations → docker scout recommendations hypercode-core:latest

      https://scout.docker.com/v/CVE-2026-7246?s=pypa&n=click&t=pypi&vr=%3C8.3.3
      Affected range : <8.3.3                                       
      Fixed version  : 8.3.3                                        
      CVSS Score     : 7.2                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:C/C:H/I:H/A:H 
    

   0C     1H     0M     0L  pyjwt 2.12.0
pkg:pypi/pyjwt@2.12.0

    x HIGH CVE-2026-48526 [Improper Authentication]
      https://scout.docker.com/v/CVE-2026-48526?s=github&n=pyjwt&t=pypi&vr=%3C2.13.0
      Affected range : <2.13.0                                      
      Fixed version  : 2.13.0                                       
      CVSS Score     : 7.4                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N 
    

   0C     1H     0M     0L  pyarrow 21.0.0
pkg:pypi/pyarrow@21.0.0

    x HIGH CVE-2026-25087 [Use After Free]
      https://scout.docker.com/v/CVE-2026-25087?s=github&n=pyarrow&t=pypi&vr=%3E%3D15.0.0%2C%3C23.0.1
      Affected range : >=15.0.0                                     
                     : <23.0.1                                      
      Fixed version  : 23.0.1                                       
      CVSS Score     : 7.0                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:H 
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    


57 vulnerabilities found in 19 packages
  CRITICAL  4  
  HIGH      53 
  MEDIUM    0  
  LOW       0  

```
</details>

### healer-agent

- ref: `hypercode-v24-healer-agent`
- digest: `hypercode-v24-healer-agent@sha256:1382b0520d261e205a223a6b1cd8ba01dcfa89843023124c6610a23839fa974e`
- size: 449 MB

```
    v SBOM of image already cached, 262 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  hypercode-v24-healer-agent:latest  │    2C    14H    27M    57L    16?  
   digest             │  1382b0520d26                       │                                    
 Base image           │  python:3.11-slim                   │    1C     6H    10M    34L     2?  
 Refreshed base image │  python:3.11-slim                   │    0C     3H     7M    25L         
                      │                                     │    -1     -3     -3     -9     -2  
 Updated base image   │  python:3.14-slim                   │    0C     4H     2M    24L         
                      │                                     │    -1     -2     -8    -10     -2  

Policy status  FAILED  (4/7 policies met)
Health score  C  (56%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 v      │ Default non-root user                          │                             
 !      │ Copyleft licensed packages found               │    564 packages             
 !      │ Fixable critical or high vulnerabilities found │    2C    13H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-v24-healer-agent
    View vulnerabilities → docker scout cves hypercode-v24-healer-agent
    View base image update recommendations → docker scout recommendations hypercode-v24-healer-agent
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-v24-healer-agent

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 262 packages indexed
    x Detected 7 vulnerable packages with a total of 16 vulnerabilities


## Overview

                   │           Analyzed Image            
───────────────────┼─────────────────────────────────────
 Target            │  hypercode-v24-healer-agent:latest  
   digest          │  1382b0520d26                       
   platform        │ linux/amd64                         
   vulnerabilities │    2C    14H     0M     0L          
   size            │ 471 MB                              
   packages        │ 262                                 


## Packages and Vulnerabilities

   1C     5H     0M     0L  stdlib 1.26.4
pkg:golang/stdlib@1.26.4

    x CRITICAL CVE-2026-39821
      https://scout.docker.com/v/CVE-2026-39821?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56862
      https://scout.docker.com/v/CVE-2026-56862?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56859
      https://scout.docker.com/v/CVE-2026-56859?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56853
      https://scout.docker.com/v/CVE-2026-56853?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-46600
      https://scout.docker.com/v/CVE-2026-46600?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-33818
      https://scout.docker.com/v/CVE-2026-33818?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    

   1C     3H     0M     0L  openssl 3.5.6-1~deb13u2
pkg:deb/debian/openssl@3.5.6-1~deb13u2?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    

   0C     2H     0M     0L  curl 8.14.1-2+deb13u3
pkg:deb/debian/curl@8.14.1-2%2Bdeb13u3?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-6276
      https://scout.docker.com/v/CVE-2026-6276?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    
    x HIGH CVE-2026-5773
      https://scout.docker.com/v/CVE-2026-5773?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091

What's next:
    View base image update recommendations → docker scout recommendations hypercode-v24-healer-agent:latest

      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    

   0C     1H     0M     0L  expat 2.7.1-2
pkg:deb/debian/expat@2.7.1-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-59375
      https://scout.docker.com/v/CVE-2025-59375?s=debian&n=expat&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.8.2-1%7Edeb13u1
      Affected range : <2.8.2-1~deb13u1 
      Fixed version  : 2.8.2-1~deb13u1  
    

   0C     1H     0M     0L  aiohttp 3.14.1
pkg:pypi/aiohttp@3.14.1

    x HIGH CVE-2026-69244 [Out-of-bounds Read]
      https://scout.docker.com/v/CVE-2026-69244?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.14.2
      Affected range : <=3.14.2                                                        
      Fixed version  : 3.14.3                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    

   0C     1H     0M     0L  libtasn1-6 4.20.0-2
pkg:deb/debian/libtasn1-6@4.20.0-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-13151
      https://scout.docker.com/v/CVE-2025-13151?s=debian&n=libtasn1-6&ns=debian&t=deb&osn=debian&osv=13&vr=%3C4.20.0-2%2Bdeb13u1
      Affected range : <4.20.0-2+deb13u1 
      Fixed version  : 4.20.0-2+deb13u1  
    


16 vulnerabilities found in 7 packages
  CRITICAL  2  
  HIGH      14 
  MEDIUM    0  
  LOW       0  

```
</details>

### safety-shepherd

- ref: `safety-shepherd:latest`
- digest: `safety-shepherd@sha256:8f6a6982a30bbe8ecdd5434f596b09919e767f9926103906aff8dd6983a995a2`
- size: 117 MB

```
    v SBOM of image already cached, 260 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  safety-shepherd:latest  │    2C    19H    51M    76L    16?  
   digest             │  8f6a6982a30b            │                                    
 Base image           │  python:3.12-slim        │    1C     4H     9M    34L     2?  
 Refreshed base image │  python:3.12-slim        │    0C     1H     6M    25L         
                      │                          │    -1     -3     -3     -9     -2  
 Updated base image   │  python:3.14-slim        │    0C     4H     2M    24L         
                      │                          │    -1            -7    -10     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (33%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 v      │ Default non-root user                          │                             
 !      │ Copyleft licensed packages found               │    602 packages             
 !      │ Fixable critical or high vulnerabilities found │    2C    18H     0M     0L  
 !      │ High-profile vulnerabilities found             │    0C     0H     1M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy safety-shepherd:latest
    View vulnerabilities → docker scout cves safety-shepherd:latest
    View base image update recommendations → docker scout recommendations safety-shepherd:latest
    Compare with the latest in the registry → docker scout compare --to-latest safety-shepherd:latest

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 260 packages indexed
    x Detected 8 vulnerable packages with a total of 21 vulnerabilities


## Overview

                   │       Analyzed Image        
───────────────────┼─────────────────────────────
 Target            │  safety-shepherd:latest     
   digest          │  8f6a6982a30b               
   platform        │ linux/amd64                 
   vulnerabilities │    2C    19H     0M     0L  
   size            │ 122 MB                      
   packages        │ 260                         


## Packages and Vulnerabilities

   1C     5H     0M     0L  stdlib 1.26.4
pkg:golang/stdlib@1.26.4

    x CRITICAL CVE-2026-39821
      https://scout.docker.com/v/CVE-2026-39821?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56862
      https://scout.docker.com/v/CVE-2026-56862?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56859
      https://scout.docker.com/v/CVE-2026-56859?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-56853
      https://scout.docker.com/v/CVE-2026-56853?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-46600
      https://scout.docker.com/v/CVE-2026-46600?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    
    x HIGH CVE-2026-33818
      https://scout.docker.com/v/CVE-2026-33818?s=golang&n=stdlib&t=golang&vr=%3E%3D1.26.0-0%2C%3C1.26.6
      Affected range : >=1.26.0-0 
                     : <1.26.6    
      Fixed version  : 1.26.6     
    

   1C     3H     0M     0L  openssl 3.5.6-1~deb13u2
pkg:deb/debian/openssl@3.5.6-1~deb13u2?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    

   0C     3H     0M     0L  aiohttp 3.9.3
pkg:pypi/aiohttp@3.9.3

    x HIGH CVE-2025-69223 [Improper Handling of Highly Compressed Data (Data Amplification)]
      https://scout.docker.com/v/CVE-2025-69223?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.13.2
      Affected range : <=3.13.2                                     
      Fixed version  : 3.13.3                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2024-30251 [Loop with Unreachable Exit Condition ('Infinite Loop')]
      https://scout.docker.com/v/CVE-2024-30251?s=github&n=aiohttp&t=pypi&vr=%3C3.9.4
      Affected range : <3.9.4                                       
      Fixed version  : 3.9.4                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-69244 [Out-of-bounds Read]
      https://scout.docker.com/v/CVE-2026-69244?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.14.2
      Affected range : <=3.14.2                                                        
      Fixed version  : 3.14.3                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    

   0C     3H     0M     0L  starlette 0.36.3
pkg:pypi/starlette@0.36.3

    x HIGH CVE-2024-47874 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2024-47874?s=github&n=starlette&t=pypi&vr=%3C0.40.0
      Affected range : <0.40.0                                                         
      Fixed version  : 0.40.0                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-54283 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-54283?s=github&n=starlette&t=pypi&vr=%3E%3D0.4.1%2C%3C1.3.1
      Affected range : >=0.4.1                                      
                     : <1.3.1                                       
      Fixed version  : 1.3.1                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-48818 [Server-Side Request Forgery (SSRF)]
      https://scout.docker.com/v/CVE-2026-48818?s=github&n=starlette&t=pypi&vr=%3C1.1.0

      Affected range : <1.1.0                                       
      Fixed version  : 1.1.0                                        
      CVSS Score     : 7.5                                          
What's next:
    View base image update recommendations → docker scout recommendations safety-shepherd:latest

      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    

   0C     2H     0M     0L  curl 8.14.1-2+deb13u3
pkg:deb/debian/curl@8.14.1-2%2Bdeb13u3?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-6276
      https://scout.docker.com/v/CVE-2026-6276?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    
    x HIGH CVE-2026-5773
      https://scout.docker.com/v/CVE-2026-5773?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    

   0C     1H     0M     0L  libtasn1-6 4.20.0-2
pkg:deb/debian/libtasn1-6@4.20.0-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-13151
      https://scout.docker.com/v/CVE-2025-13151?s=debian&n=libtasn1-6&ns=debian&t=deb&osn=debian&osv=13&vr=%3C4.20.0-2%2Bdeb13u1
      Affected range : <4.20.0-2+deb13u1 
      Fixed version  : 4.20.0-2+deb13u1  
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    

   0C     1H     0M     0L  expat 2.7.1-2
pkg:deb/debian/expat@2.7.1-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-59375
      https://scout.docker.com/v/CVE-2025-59375?s=debian&n=expat&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.8.2-1%7Edeb13u1
      Affected range : <2.8.2-1~deb13u1 
      Fixed version  : 2.8.2-1~deb13u1  
    


21 vulnerabilities found in 8 packages
  CRITICAL  2  
  HIGH      19 
  MEDIUM    0  
  LOW       0  

```
</details>

### hyper-brain

- ref: `hypercode-v24-hyper-brain`
- digest: `hypercode-v24-hyper-brain@sha256:266a84bfd0444b0fc7f7791cf9718d04070c8542b66b112cd78d0736d12d5b73`
- size: 95 MB

```
    v SBOM of image already cached, 214 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  hypercode-v24-hyper-brain:latest  │    1C     9H    27M    58L    14?  
   digest             │  266a84bfd044                      │                                    
 Base image           │  python:3.12-slim                  │    1C     4H     9M    34L     2?  
 Refreshed base image │  python:3.12-slim                  │    0C     1H     6M    25L         
                      │                                    │    -1     -3     -3     -9     -2  
 Updated base image   │  python:3.14-slim                  │    0C     4H     2M    24L         
                      │                                    │    -1            -7    -10     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    497 packages             
 !      │ Fixable critical or high vulnerabilities found │    1C     8H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-v24-hyper-brain
    View vulnerabilities → docker scout cves hypercode-v24-hyper-brain
    View base image update recommendations → docker scout recommendations hypercode-v24-hyper-brain
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-v24-hyper-brain

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 214 packages indexed
    x Detected 6 vulnerable packages with a total of 10 vulnerabilities



## Overview

                   │           Analyzed Image           
What's next:
───────────────────┼────────────────────────────────────
 Target            │  hypercode-v24-hyper-brain:latest  
   digest          │  266a84bfd044                      
   platform        │ linux/amd64                        
   vulnerabilities │    1C     9H     0M     0L         
   size            │ 100 MB                             
   packages        │ 214                                


## Packages and Vulnerabilities

   1C     3H     0M     0L  openssl 3.5.6-1~deb13u2
    View base image update recommendations → docker scout recommendations hypercode-v24-hyper-brain:latest
pkg:deb/debian/openssl@3.5.6-1~deb13u2?os_distro=trixie&os_name=debian&os_version=13


    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    

   0C     2H     0M     0L  curl 8.14.1-2+deb13u3
pkg:deb/debian/curl@8.14.1-2%2Bdeb13u3?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-6276
      https://scout.docker.com/v/CVE-2026-6276?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    
    x HIGH CVE-2026-5773
      https://scout.docker.com/v/CVE-2026-5773?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    

   0C     1H     0M     0L  expat 2.7.1-2
pkg:deb/debian/expat@2.7.1-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-59375
      https://scout.docker.com/v/CVE-2025-59375?s=debian&n=expat&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.8.2-1%7Edeb13u1
      Affected range : <2.8.2-1~deb13u1 
      Fixed version  : 2.8.2-1~deb13u1  
    

   0C     1H     0M     0L  libtasn1-6 4.20.0-2
pkg:deb/debian/libtasn1-6@4.20.0-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-13151
      https://scout.docker.com/v/CVE-2025-13151?s=debian&n=libtasn1-6&ns=debian&t=deb&osn=debian&osv=13&vr=%3C4.20.0-2%2Bdeb13u1
      Affected range : <4.20.0-2+deb13u1 
      Fixed version  : 4.20.0-2+deb13u1  
    

   0C     1H     0M     0L  aiohttp 3.14.1
pkg:pypi/aiohttp@3.14.1

    x HIGH CVE-2026-69244 [Out-of-bounds Read]
      https://scout.docker.com/v/CVE-2026-69244?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.14.2
      Affected range : <=3.14.2                                                        
      Fixed version  : 3.14.3                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    


10 vulnerabilities found in 6 packages
  CRITICAL  1 
  HIGH      9 
  MEDIUM    0 
  LOW       0 

```
</details>

### hyperhealth-worker

- ref: `hypercode-v20-hyperhealth-worker`
- digest: `hypercode-v20-hyperhealth-worker@sha256:e41fac4ae15486d3688ff5d1ce47814db8df716b3319827b2a13f5ce76f06f56`
- size: 80 MB

```
    v SBOM of image already cached, 225 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  hypercode-v20-hyperhealth-worker:latest  │    2C    24H    30M    66L     2?  
   digest             │  e41fac4ae154                             │                                    
 Base image           │  python:3.11-slim                         │    2C    11H    13M    40L     2?  
 Refreshed base image │  python:3.11-slim                         │    0C     3H     7M    25L         
                      │                                           │    -2     -8     -6    -15     -2  
 Updated base image   │  python:3.12-slim                         │    0C     1H     6M    25L         
                      │                                           │    -2    -10     -7    -15     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (33%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 v      │ Default non-root user                          │                             
 !      │ Copyleft licensed packages found               │    456 packages             
 !      │ Fixable critical or high vulnerabilities found │    2C    23H     0M     0L  
 !      │ High-profile vulnerabilities found             │    0C     0H     1M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-v20-hyperhealth-worker
    View vulnerabilities → docker scout cves hypercode-v20-hyperhealth-worker
    View base image update recommendations → docker scout recommendations hypercode-v20-hyperhealth-worker
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-v20-hyperhealth-worker

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 225 packages indexed
    x Detected 11 vulnerable packages with a total of 26 vulnerabilities


## Overview

                   │              Analyzed Image               
───────────────────┼───────────────────────────────────────────
 Target            │  hypercode-v20-hyperhealth-worker:latest  
   digest          │  e41fac4ae154                             
   platform        │ linux/amd64                               
   vulnerabilities │    2C    24H     0M     0L                
   size            │ 84 MB                                     
   packages        │ 225                                       


## Packages and Vulnerabilities

   2C     8H     0M     0L  openssl 3.5.6-1~deb13u1
pkg:deb/debian/openssl@3.5.6-1~deb13u1?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x CRITICAL CVE-2026-34182
      https://scout.docker.com/v/CVE-2026-34182?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-45447
      https://scout.docker.com/v/CVE-2026-45447?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-7383
      https://scout.docker.com/v/CVE-2026-7383?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-9076
      https://scout.docker.com/v/CVE-2026-9076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-45445
      https://scout.docker.com/v/CVE-2026-45445?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-34180
      https://scout.docker.com/v/CVE-2026-34180?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    

   0C     3H     0M     0L  starlette 0.40.0
pkg:pypi/starlette@0.40.0

    x HIGH CVE-2026-54283 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-54283?s=github&n=starlette&t=pypi&vr=%3E%3D0.4.1%2C%3C1.3.1
      Affected range : >=0.4.1                                      
                     : <1.3.1                                       
      Fixed version  : 1.3.1                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-48818 [Server-Side Request Forgery (SSRF)]
      https://scout.docker.com/v/CVE-2026-48818?s=github&n=starlette&t=pypi&vr=%3C1.1.0
      Affected range : <1.1.0                                       
      Fixed version  : 1.1.0                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    
    x HIGH CVE-2025-62727 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2025-62727?s=github&n=starlette&t=pypi&vr=%3E%3D0.39.0%2C%3C%3D0.49.0
      Affected range : >=0.39.0                                     
                     : <=0.49.0                                     
      Fixed version  : 0.49.1                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     3H     0M     0L  cryptography 43.0.3
pkg:pypi/cryptography@43.0.3

    x HIGH CVE-2026-69249 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-69249?s=github&n=cryptography&t=pypi&vr=%3E%3D42.0.0%2C%3C%3D48.0.0
      Affected range : >=42.0.0                                                        
                     : <=48.0.0                                                        
      Fixed version  : 49.0.0                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-26007 [Insufficient Verification of Data Authenticity]
      https://scout.docker.com/v/CVE-2026-26007?s=github&n=cryptography&t=pypi&vr=%3C%3D46.0.4
      Affected range : <=46.0.4                                                        
      Fixed version  : 46.0.5                                                          
      CVSS Score     : 8.2                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:H/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-537c-gmf6-5ccf [Out-of-bounds Read]
      https://scout.docker.com/v/GHSA-537c-gmf6-5ccf?s=github&n=cryptography&t=pypi&vr=%3E%3D0.5.0%2C%3C48.0.1
      Affected range : >=0.5.0                                      
                     : <48.0.1                                      
      Fixed version  : 48.0.1                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     2H     0M     0L  curl 8.14.1-2+deb13u3
pkg:deb/debian/curl@8.14.1-2%2Bdeb13u3?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-6276
      https://scout.docker.com/v/CVE-2026-6276?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    
    x HIGH CVE-2026-5773
      https://scout.docker.com/v/CVE-2026-5773?s=debian&n=curl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C8.14.1-2%2Bdeb13u4
      Affected range : <8.14.1-2+deb13u4 
      Fixed version  : 8.14.1-2+deb13u4  
    

   0C     2H     0M     0L  python-multipart 0.0.24
pkg:pypi/python-multipart@0.0.24

    x HIGH CVE-2026-53539 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-53539?s=github&n=python-multipart&t=pypi&vr=%3C0.0.30
      Affected range : <0.0.30                                      
      Fixed version  : 0.0.30                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-42561 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-42561?s=github&n=python-multipart&t=pypi&vr=%3C0.0.27
      Affected range : <0.0.27                                      
      Fixed version  : 0.0.27                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     1H     0M     0L  libtasn1-6 4.20.0-2

What's next:
    View base image update recommendations → docker scout recommendations hypercode-v20-hyperhealth-worker:latest

pkg:deb/debian/libtasn1-6@4.20.0-2?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-13151
      https://scout.docker.com/v/CVE-2025-13151?s=debian&n=libtasn1-6&ns=debian&t=deb&osn=debian&osv=13&vr=%3C4.20.0-2%2Bdeb13u1
      Affected range : <4.20.0-2+deb13u1 
      Fixed version  : 4.20.0-2+deb13u1  
    

   0C     1H     0M     0L  wheel 0.45.1
pkg:pypi/wheel@0.45.1

    x HIGH CVE-2026-24049 [Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')]
      https://scout.docker.com/v/CVE-2026-24049?s=github&n=wheel&t=pypi&vr=%3E%3D0.40.0%2C%3C%3D0.46.1
      Affected range : >=0.40.0                                     
                     : <=0.46.1                                     
      Fixed version  : 0.46.2                                       
      CVSS Score     : 7.1                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:H 
    

   0C     1H     0M     0L  pyopenssl 24.2.1
pkg:pypi/pyopenssl@24.2.1

    x HIGH CVE-2026-27459 [Buffer Copy without Checking Size of Input ('Classic Buffer Overflow')]
      https://scout.docker.com/v/CVE-2026-27459?s=github&n=pyopenssl&t=pypi&vr=%3E%3D22.0.0%2C%3C26.0.0
      Affected range : >=22.0.0                                                            
                     : <26.0.0                                                             
      Fixed version  : 26.0.0                                                              
      CVSS Score     : 7.2                                                                 
      CVSS Vector    : CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:U 
    

   0C     1H     0M     0L  jaraco-context 5.3.0
pkg:pypi/jaraco-context@5.3.0

    x HIGH CVE-2026-23949
      https://scout.docker.com/v/CVE-2026-23949?s=pypa&n=jaraco-context&t=pypi&vr=%3E%3D5.2.0%2C%3C6.1.0
      Affected range : >=5.2.0                                      
                     : <6.1.0                                       
      Fixed version  : 6.1.0                                        
      CVSS Score     : 8.6                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N 
    

   0C     1H     0M     0L  libssh2 1.11.1-1
pkg:deb/debian/libssh2@1.11.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2025-15661
      https://scout.docker.com/v/CVE-2025-15661?s=debian&n=libssh2&ns=debian&t=deb&osn=debian&osv=13&vr=%3C1.11.1-1%2Bdeb13u1
      Affected range : <1.11.1-1+deb13u1 
      Fixed version  : 1.11.1-1+deb13u1  
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    


26 vulnerabilities found in 11 packages
  CRITICAL  2  
  HIGH      24 
  MEDIUM    0  
  LOW       0  

```
</details>

### hypercode-mcp-server

- ref: `hypercode-v24-hypercode-mcp-server`
- digest: `hypercode-v24-hypercode-mcp-server@sha256:137a934a4093f56fb19b52a34f0f472b7df3a0af478a207b941493021917316c`
- size: 63 MB

```
    ...Storing image for indexing
    v Image stored for indexing
    ...Indexing
    v Indexed 180 packages
    ! failed to delete temporary image archive C:\Users\Lyndz\AppData\Local\Temp\docker-scout\sha256\137a934a4093f56fb19b52a34f0f472b7df3a0af478a207b941493021917316c\9278ff73-33ee-4f46-a929-cd1442254ac0: unlinkat C:\Users\Lyndz\AppData\Local\Temp\docker-scout\sha256\137a934a4093f56fb19b52a34f0f472b7df3a0af478a207b941493021917316c\9278ff73-33ee-4f46-a929-cd1442254ac0: The process cannot access the file because it is being used by another process.    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  hypercode-v24-hypercode-mcp-server:latest  │    2C    20H    16M    44L     2?  
   digest             │  137a934a4093                               │                                    
 Base image           │  python:3.11-slim                           │    2C    11H    13M    40L     2?  
 Refreshed base image │  python:3.11-slim                           │    0C     3H     7M    25L         
                      │                                             │    -2     -8     -6    -15     -2  
 Updated base image   │  python:3.12-slim                           │    0C     1H     6M    25L         
                      │                                             │    -2    -10     -7    -15     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    365 packages             
 !      │ Fixable critical or high vulnerabilities found │    2C    19H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-v24-hypercode-mcp-server
    View vulnerabilities → docker scout cves hypercode-v24-hypercode-mcp-server
    View base image update recommendations → docker scout recommendations hypercode-v24-hypercode-mcp-server
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-v24-hypercode-mcp-server

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 180 packages indexed
    x Detected 8 vulnerable packages with a total of 22 vulnerabilities


## Overview

                   │               Analyzed Image                
───────────────────┼─────────────────────────────────────────────
 Target            │  hypercode-v24-hypercode-mcp-server:latest  
   digest          │  137a934a4093                               
   platform        │ linux/amd64                                 
   vulnerabilities │    2C    20H     0M     0L                  
   size            │ 66 MB                                       
   packages        │ 180                                         


## Packages and Vulnerabilities

   2C     8H     0M     0L  openssl 3.5.6-1~deb13u1
pkg:deb/debian/openssl@3.5.6-1~deb13u1?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x CRITICAL CVE-2026-34182
      https://scout.docker.com/v/CVE-2026-34182?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-45447
      https://scout.docker.com/v/CVE-2026-45447?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-7383
      https://scout.docker.com/v/CVE-2026-7383?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-9076
      https://scout.docker.com/v/CVE-2026-9076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-45445
      https://scout.docker.com/v/CVE-2026-45445?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-34180
      https://scout.docker.com/v/CVE-2026-34180?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    

   0C     3H     0M     0L  cryptography 48.0.0
pkg:pypi/cryptography@48.0.0

    x HIGH CVE-2026-69249 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-69249?s=github&n=cryptography&t=pypi&vr=%3E%3D42.0.0%2C%3C%3D48.0.0
      Affected range : >=42.0.0                                                        
                     : <=48.0.0                                                        
      Fixed version  : 49.0.0                                                          
      CVSS Score     : 8.7                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-69247 [Observable Timing Discrepancy]
      https://scout.docker.com/v/CVE-2026-69247?s=github&n=cryptography&t=pypi&vr=%3E%3D44.0.0%2C%3C50.0.0
      Affected range : >=44.0.0                                                        
                     : <50.0.0                                                         
      Fixed version  : 50.0.0                                                          
      CVSS Score     : 8.2                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH GHSA-537c-gmf6-5ccf [Out-of-bounds Read]
      https://scout.docker.com/v/GHSA-537c-gmf6-5ccf?s=github&n=cryptography&t=pypi&vr=%3E%3D0.5.0%2C%3C48.0.1
      Affected range : >=0.5.0                                      
                     : <48.0.1                                      
      Fixed version  : 48.0.1                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     3H     0M     0L  mcp 1.27.1
pkg:pypi/mcp@1.27.1

    x HIGH CVE-2026-59950 [Missing Origin Validation in WebSockets]
      https://scout.docker.com/v/CVE-2026-59950?s=github&n=mcp&t=pypi&vr=%3C1.28.1
      Affected range : <1.28.1                                                         
      Fixed version  : 1.28.1                                                          
      CVSS Score     : 7.6                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N 
    
    x HIGH CVE-2026-52870 [Missing Authorization]
      https://scout.docker.com/v/CVE-2026-52870?s=github&n=mcp&t=pypi&vr=%3E%3D1.23.0%2C%3C%3D1.27.1
      Affected range : >=1.23.0                                     
                     : <=1.27.1                                     
      Fixed version  : 1.27.2                                       
      CVSS Score     : 7.6                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:L 
    
    x HIGH CVE-2026-52869 [Authorization Bypass Through User-Controlled Key]
      https://scout.docker.com/v/CVE-2026-52869?s=github&n=mcp&t=pypi&vr=%3C%3D1.27.1
      Affected range : <=1.27.1                                     
      Fixed version  : 1.27.2                                       
      CVSS Score     : 7.1                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:L 
    

   0C     2H     0M     0L  starlette 1.0.1
pkg:pypi/starlette@1.0.1

    x HIGH CVE-2026-54283 [Allocation of Resources Without Limits or Throttling]
      https://scout.docker.com/v/CVE-2026-54283?s=github&n=starlette&t=pypi&vr=%3E%3D0.4.1%2C%3C1.3.1
      Affected range : >=0.4.1                                      
                     : <1.3.1                                       
      Fixed version  : 1.3.1                                        
      CVSS Score     : 7.5                                          

What's next:
    View base image update recommendations → docker scout recommendations hypercode-v24-hypercode-mcp-server:latest

      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    
    x HIGH CVE-2026-48818 [Server-Side Request Forgery (SSRF)]
      https://scout.docker.com/v/CVE-2026-48818?s=github&n=starlette&t=pypi&vr=%3C1.1.0
      Affected range : <1.1.0                                       
      Fixed version  : 1.1.0                                        
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N 
    

   0C     1H     0M     0L  jaraco-context 5.3.0
pkg:pypi/jaraco-context@5.3.0

    x HIGH CVE-2026-23949
      https://scout.docker.com/v/CVE-2026-23949?s=pypa&n=jaraco-context&t=pypi&vr=%3E%3D5.2.0%2C%3C6.1.0
      Affected range : >=5.2.0                                      
                     : <6.1.0                                       
      Fixed version  : 6.1.0                                        
      CVSS Score     : 8.6                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N 
    

   0C     1H     0M     0L  wheel 0.45.1
pkg:pypi/wheel@0.45.1

    x HIGH CVE-2026-24049 [Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')]
      https://scout.docker.com/v/CVE-2026-24049?s=github&n=wheel&t=pypi&vr=%3E%3D0.40.0%2C%3C%3D0.46.1
      Affected range : >=0.40.0                                     
                     : <=0.46.1                                     
      Fixed version  : 0.46.2                                       
      CVSS Score     : 7.1                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:H 
    

   0C     1H     0M     0L  python-multipart 0.0.29
pkg:pypi/python-multipart@0.0.29

    x HIGH CVE-2026-53539 [Uncontrolled Resource Consumption]
      https://scout.docker.com/v/CVE-2026-53539?s=github&n=python-multipart&t=pypi&vr=%3C0.0.30
      Affected range : <0.0.30                                      
      Fixed version  : 0.0.30                                       
      CVSS Score     : 7.5                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H 
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    


22 vulnerabilities found in 8 packages
  CRITICAL  2  
  HIGH      20 
  MEDIUM    0  
  LOW       0  

```
</details>

### agent-mcp-bridge

- ref: `hypercode-v24-agent-mcp-bridge`
- digest: `hypercode-v24-agent-mcp-bridge@sha256:0e8693ac26e2883c53334d668fd48036b46e0b8f6aef66d129452d0829d9ccfb`
- size: 62 MB

```
    v SBOM of image already cached, 154 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target     │  hypercode-v24-agent-mcp-bridge:latest  │    0C     2H     8M    25L  
   digest   │  0e8693ac26e2                           │                             
 Base image │  python:3.12-slim                       │    0C     1H     6M    25L  

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    364 packages             
 !      │ Fixable critical or high vulnerabilities found │    0C     1H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-v24-agent-mcp-bridge
    View vulnerabilities → docker scout cves hypercode-v24-agent-mcp-bridge
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-v24-agent-mcp-bridge

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 154 packages indexed
    x Detected 2 vulnerable packages with a total of 2 vulnerabilities


What's next:
    View base image update recommendations → docker scout recommendations hypercode-v24-agent-mcp-bridge:latest


## Overview

                   │             Analyzed Image              
───────────────────┼─────────────────────────────────────────
 Target            │  hypercode-v24-agent-mcp-bridge:latest  
   digest          │  0e8693ac26e2                           
   platform        │ linux/amd64                             
   vulnerabilities │    0C     2H     0M     0L              
   size            │ 65 MB                                   
   packages        │ 154                                     


## Packages and Vulnerabilities

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    

   0C     1H     0M     0L  aiohttp 3.14.1
pkg:pypi/aiohttp@3.14.1

    x HIGH CVE-2026-69244 [Out-of-bounds Read]
      https://scout.docker.com/v/CVE-2026-69244?s=github&n=aiohttp&t=pypi&vr=%3C%3D3.14.2
      Affected range : <=3.14.2                                                        
      Fixed version  : 3.14.3                                                          
      CVSS Score     : 7.1                                                             
      CVSS Vector    : CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N 
    


2 vulnerabilities found in 2 packages
  CRITICAL  0 
  HIGH      2 
  MEDIUM    0 
  LOW       0 

```
</details>

### memstream

- ref: `hypercode-memstream:latest`
- digest: `hypercode-memstream@sha256:a72f59a3d94c929e099cfaf3419e2dda8a4681fa982974f0c8ec9fce82e62fd5`
- size: 52 MB

```
    v SBOM of image already cached, 196 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target             │  hypercode-memstream:latest  │    3C    27H    25M    64L     2?  
   digest           │  a72f59a3d94c                │                                    
 Base image         │  python:3.9-slim             │    3C    26H    25M    46L     2?  
 Updated base image │  python:3.12-slim            │    0C     1H     6M    25L         
                    │                              │    -3    -25    -19    -21     -2  

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    465 packages             
 !      │ Fixable critical or high vulnerabilities found │    3C    26H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy hypercode-memstream:latest
    View vulnerabilities → docker scout cves hypercode-memstream:latest
    View base image update recommendations → docker scout recommendations hypercode-memstream:latest
    Compare with the latest in the registry → docker scout compare --to-latest hypercode-memstream:latest

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 196 packages indexed
    x Detected 7 vulnerable packages with a total of 30 vulnerabilities


## Overview

                   │        Analyzed Image        
───────────────────┼──────────────────────────────
 Target            │  hypercode-memstream:latest  
   digest          │  a72f59a3d94c                
   platform        │ linux/amd64                  
   vulnerabilities │    3C    27H     0M     0L   
   size            │ 54 MB                        
   packages        │ 196                          


## Packages and Vulnerabilities

   3C    17H     0M     0L  openssl 3.5.1-1+deb13u1
pkg:deb/debian/openssl@3.5.1-1%2Bdeb13u1?os_distro=trixie&os_name=debian&os_version=13

    x CRITICAL CVE-2026-31789
      https://scout.docker.com/v/CVE-2026-31789?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x CRITICAL CVE-2026-34182
      https://scout.docker.com/v/CVE-2026-34182?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-45447
      https://scout.docker.com/v/CVE-2026-45447?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2025-15467
      https://scout.docker.com/v/CVE-2025-15467?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.4-1%7Edeb13u2
      Affected range : <3.5.4-1~deb13u2 
      Fixed version  : 3.5.4-1~deb13u2  
    
    x HIGH CVE-2026-7383
      https://scout.docker.com/v/CVE-2026-7383?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-28387
      https://scout.docker.com/v/CVE-2026-28387?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x HIGH CVE-2026-9076
      https://scout.docker.com/v/CVE-2026-9076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.7-1%7Edeb13u2
      Affected range : <3.5.7-1~deb13u2 
      Fixed version  : 3.5.7-1~deb13u2  
    
    x HIGH CVE-2026-45445
      https://scout.docker.com/v/CVE-2026-45445?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-34180
      https://scout.docker.com/v/CVE-2026-34180?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.6-1%7Edeb13u2
      Affected range : <3.5.6-1~deb13u2 
      Fixed version  : 3.5.6-1~deb13u2  
    
    x HIGH CVE-2026-31790
      https://scout.docker.com/v/CVE-2026-31790?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x HIGH CVE-2026-28390
      https://scout.docker.com/v/CVE-2026-28390?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x HIGH CVE-2026-28389
      https://scout.docker.com/v/CVE-2026-28389?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x HIGH CVE-2026-28388
      https://scout.docker.com/v/CVE-2026-28388?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.5-1%7Edeb13u2
      Affected range : <3.5.5-1~deb13u2 
      Fixed version  : 3.5.5-1~deb13u2  
    
    x HIGH CVE-2025-69421
      https://scout.docker.com/v/CVE-2025-69421?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.4-1%7Edeb13u2
      Affected range : <3.5.4-1~deb13u2 
      Fixed version  : 3.5.4-1~deb13u2  
    
    x HIGH CVE-2025-69420
      https://scout.docker.com/v/CVE-2025-69420?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.4-1%7Edeb13u2
      Affected range : <3.5.4-1~deb13u2 
      Fixed version  : 3.5.4-1~deb13u2  
    
    x HIGH CVE-2025-69419
      https://scout.docker.com/v/CVE-2025-69419?s=debian&n=openssl&ns=debian&t=deb&osn=debian&osv=13&vr=%3C3.5.4-1%7Edeb13u2
      Affected range : <3.5.4-1~deb13u2 
      Fixed version  : 3.5.4-1~deb13u2  
    

   0C     5H     0M     0L  glibc 2.41-12
pkg:deb/debian/glibc@2.41-12?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-0861
      https://scout.docker.com/v/CVE-2026-0861?s=debian&n=glibc&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.41-12%2Bdeb13u2
      Affected range : <2.41-12+deb13u2 
      Fixed version  : 2.41-12+deb13u2  
    
    x HIGH CVE-2026-4437
      https://scout.docker.com/v/CVE-2026-4437?s=debian&n=glibc&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.41-12%2Bdeb13u3
      Affected range : <2.41-12+deb13u3 
      Fixed version  : 2.41-12+deb13u3  
    
    x HIGH CVE-2026-4046
      https://scout.docker.com/v/CVE-2026-4046?s=debian&n=glibc&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.41-12%2Bdeb13u3
      Affected range : <2.41-12+deb13u3 
      Fixed version  : 2.41-12+deb13u3  
    
    x HIGH CVE-2026-0915
      https://scout.docker.com/v/CVE-2026-0915?s=debian&n=glibc&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.41-12%2Bdeb13u2
      Affected range : <2.41-12+deb13u2 
      Fixed version  : 2.41-12+deb13u2  
    
    x HIGH CVE-2025-15281
      https://scout.docker.com/v/CVE-2025-15281?s=debian&n=glibc&ns=debian&t=deb&osn=debian&osv=13&vr=%3C2.41-12%2Bdeb13u2
      Affected range : <2.41-12+deb13u2 
      Fixed version  : 2.41-12+deb13u2  
    

   0C     1H     0M     0L  wheel 0.45.1
pkg:pypi/wheel@0.45.1

    x HIGH CVE-2026-24049 [Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')]
      https://scout.docker.com/v/CVE-2026-24049?s=github&n=wheel&t=pypi&vr=%3E%3D0.40.0%2C%3C%3D0.46.1
      Affected range : >=0.40.0                                     
                     : <=0.46.1                                     
      Fixed version  : 0.46.2                                       
      CVSS Score     : 7.1                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:H 
    

   0C     1H     0M     0L  zlib 1:1.3.dfsg+really1.3.1-1
pkg:deb/debian/zlib@1%3A1.3.dfsg%2Breally1.3.1-1?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-85091
      https://scout.docker.com/v/CVE-2026-85091?s=debian&n=zlib&ns=debian&t=deb&osn=debian&osv=13&vr=%3E0
      Affected range : >0        
      Fixed version  : not fixed 
    

   0C     1H     0M     0L  dpkg 1.22.21
pkg:deb/debian/dpkg@1.22.21?os_distro=trixie&os_name=debian&os_version=13

    x HIGH CVE-2026-2219
      https://scout.docker.com/v/CVE-2026-2219?s=debian&n=dpkg&ns=debian&t=deb&osn=debian&osv=13&vr=%3C1.22.22
      Affected range : <1.22.22 
      Fixed version  : 1.22.22  
    

   0C     1H     0M     0L  jaraco-context 5.3.0
pkg:pypi/jaraco-context@5.3.0

    x HIGH CVE-2026-23949
      https://scout.docker.com/v/CVE-2026-23949?s=pypa&n=jaraco-context&t=pypi&vr=%3E%3D5.2.0%2C%3C6.1.0
      Affected range : >=5.2.0                                      
                     : <6.1.0                                       
      Fixed version  : 6.1.0                                        
      CVSS Score     : 8.6                                          
      CVSS Vector    : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N 
    

   0C     1H     0M     0L  click 8.1.8
pkg:pypi/click@8.1.8

    x HIGH CVE-2026-7246
      https://scout.docker.com/v/CVE-2026-7246?s=pypa&n=click&t=pypi&vr=%3C8.3.3
      Affected range : <8.3.3                                       
      Fixed version  : 8.3.3                                        
      CVSS Score     : 7.2                                          
      CVSS Vector    : CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:C/C:H/I:H/A:H 
    


30 vulnerabilities found in 7 packages
  CRITICAL  3  
  HIGH      27 
  MEDIUM    0  
  LOW       0  


What's next:
    View base image update recommendations → docker scout recommendations hypercode-memstream:latest

```
</details>

### postgres

- ref: `postgres:16-alpine`
- digest: `postgres@sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`
- size: 105 MB

```
    v SBOM of image already cached, 66 packages indexed
    v 4 exceptions obtained
    v 4 exceptions obtained
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  postgres:16-alpine  │    5C    38H    27M     7L     5?  
   digest             │  16bc17c64a57        │                                    
 Base image           │  alpine:3            │    3C    15H     6M     2L         
 Refreshed base image │  alpine:3            │    2C     7H     1M     0L         
                      │                      │    -1     -8     -5     -2         
 Updated base image   │  alpine:3.21         │    0C     0H     1M     0L         
                      │                      │    -3    -15     -5     -2         

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    33 packages              
 !      │ Fixable critical or high vulnerabilities found │    5C    38H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy postgres:16-alpine
    View vulnerabilities → docker scout cves postgres:16-alpine
    View base image update recommendations → docker scout recommendations postgres:16-alpine
    Compare with the latest in the registry → docker scout compare --to-latest postgres:16-alpine

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 66 packages indexed
    v 4 exceptions obtained
    x Detected 3 vulnerable packages with a total of 43 vulnerabilities


## Overview

                   │       Analyzed Image        
───────────────────┼─────────────────────────────
 Target            │  postgres:16-alpine         
   digest          │  16bc17c64a57               
   platform        │ linux/amd64                 
   vulnerabilities │    5C    38H     0M     0L  
   size            │ 110 MB                      
   packages        │ 66                          


## Packages and Vulnerabilities

   3C    15H     0M     0L  openssl 3.5.6-r0
pkg:apk/alpine/openssl@3.5.6-r0?os_name=alpine&os_version=3.23

    x CRITICAL CVE-2026-63073
      https://scout.docker.com/v/CVE-2026-63073?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x CRITICAL CVE-2026-34182
      https://scout.docker.com/v/CVE-2026-34182?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-45447
      https://scout.docker.com/v/CVE-2026-45447?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-7383
      https://scout.docker.com/v/CVE-2026-7383?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-9076
      https://scout.docker.com/v/CVE-2026-9076?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-63075
      https://scout.docker.com/v/CVE-2026-63075?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-45445
      https://scout.docker.com/v/CVE-2026-45445?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-42764
      https://scout.docker.com/v/CVE-2026-42764?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-34183
      https://scout.docker.com/v/CVE-2026-34183?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-34180
      https://scout.docker.com/v/CVE-2026-34180?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-18798
      https://scout.docker.com/v/CVE-2026-18798?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-14457
      https://scout.docker.com/v/CVE-2026-14457?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-14456
      https://scout.docker.com/v/CVE-2026-14456?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-34181
      https://scout.docker.com/v/CVE-2026-34181?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    

   2C    20H     0M     0L  stdlib 1.24.6
pkg:golang/stdlib@1.24.6

    x CRITICAL CVE-2025-68121
      https://scout.docker.com/v/CVE-2025-68121?s=golang&n=stdlib&t=golang&vr=%3C1.24.13
      Affected range : <1.24.13 
      Fixed version  : 1.24.13  
    
    x CRITICAL CVE-2026-39821
      https://scout.docker.com/v/CVE-2026-39821?s=golang&n=stdlib&t=golang&vr=%3C1.25.13
      Affected range : <1.25.13 
      Fixed version  : 1.25.13  
    
    x HIGH CVE-2026-56862
      https://scout.docker.com/v/CVE-2026-56862?s=golang&n=stdlib&t=golang&vr=%3C1.25.13
      Affected range : <1.25.13 
      Fixed version  : 1.25.13  
    
    x HIGH CVE-2026-56859
      https://scout.docker.com/v/CVE-2026-56859?s=golang&n=stdlib&t=golang&vr=%3C1.25.13
      Affected range : <1.25.13 
      Fixed version  : 1.25.13  
    
    x HIGH CVE-2026-56853
      https://scout.docker.com/v/CVE-2026-56853?s=golang&n=stdlib&t=golang&vr=%3C1.25.13
      Affected range : <1.25.13 
      Fixed version  : 1.25.13  
    
    x HIGH CVE-2026-42504
      https://scout.docker.com/v/CVE-2026-42504?s=golang&n=stdlib&t=golang&vr=%3C1.25.11
      Affected range : <1.25.11 
      Fixed version  : 1.25.11  
    
    x HIGH CVE-2026-42499
      https://scout.docker.com/v/CVE-2026-42499?s=golang&n=stdlib&t=golang&vr=%3C1.25.10
      Affected range : <1.25.10 
      Fixed version  : 1.25.10  
    
    x HIGH CVE-2026-39836
      https://scout.docker.com/v/CVE-2026-39836?s=golang&n=stdlib&t=golang&vr=%3C1.25.10
      Affected range : <1.25.10 
      Fixed version  : 1.25.10  
    
    x HIGH CVE-2026-39820
      https://scout.docker.com/v/CVE-2026-39820?s=golang&n=stdlib&t=golang&vr=%3C1.25.10
      Affected range : <1.25.10 
      Fixed version  : 1.25.10  
    
    x HIGH CVE-2026-33818
      https://scout.docker.com/v/CVE-2026-33818?s=golang&n=stdlib&t=golang&vr=%3C1.25.13
      Affected range : <1.25.13 
      Fixed version  : 1.25.13  
    
    x HIGH CVE-2026-33814
      https://scout.docker.com/v/CVE-2026-33814?s=golang&n=stdlib&t=golang&vr=%3C1.25.10
      Affected range : <1.25.10 
      Fixed version  : 1.25.10  
    
    x HIGH CVE-2026-33811
      https://scout.docker.com/v/CVE-2026-33811?s=golang&n=stdlib&t=golang&vr=%3C1.25.10
      Affected range : <1.25.10 
      Fixed version  : 1.25.10  
    
    x HIGH CVE-2026-32283
      https://scout.docker.com/v/CVE-2026-32283?s=golang&n=stdlib&t=golang&vr=%3C1.25.9
      Affected range : <1.25.9 
      Fixed version  : 1.25.9  
    
    x HIGH CVE-2026-32281
      https://scout.docker.com/v/CVE-2026-32281?s=golang&n=stdlib&t=golang&vr=%3C1.25.9
      Affected range : <1.25.9 
      Fixed version  : 1.25.9  
    
    x HIGH CVE-2026-32280
      https://scout.docker.com/v/CVE-2026-32280?s=golang&n=stdlib&t=golang&vr=%3C1.25.9
      Affected range : <1.25.9 
      Fixed version  : 1.25.9  
    
    x HIGH CVE-2026-25679
      https://scout.docker.com/v/CVE-2026-25679?s=golang&n=stdlib&t=golang&vr=%3C1.25.8
      Affected range : <1.25.8 
      Fixed version  : 1.25.8  
    
    x HIGH CVE-2025-61729
      https://scout.docker.com/v/CVE-2025-61729?s=golang&n=stdlib&t=golang&vr=%3C1.24.11
      Affected range : <1.24.11 
      Fixed version  : 1.24.11  
    
    x HIGH CVE-2025-61726
      https://scout.docker.com/v/CVE-2025-61726?s=golang&n=stdlib&t=golang&vr=%3C1.24.12
      Affected range : <1.24.12 
      Fixed version  : 1.24.12  
    
    x HIGH CVE-2025-61725
      https://scout.docker.com/v/CVE-2025-61725?s=golang&n=stdlib&t=golang&vr=%3C1.24.8
      Affected range : <1.24.8 
      Fixed version  : 1.24.8  
    
    x HIGH CVE-2025-61723
      https://scout.docker.com/v/CVE-2025-61723?s=golang&n=stdlib&t=golang&vr=%3C1.24.8
      Affected range : <1.24.8 
      Fixed version  : 1.24.8  
    
    x HIGH CVE-2025-58188
      https://scout.docker.com/v/CVE-2025-58188?s=golang&n=stdlib&t=golang&vr=%3C1.24.8
      Affected range : <1.24.8 
      Fixed version  : 1.24.8  
    
    x HIGH CVE-2025-58187
      https://scout.docker.com/v/CVE-2025-58187?s=golang&n=stdlib&t=golang&vr=%3C1.24.9
      Affected range : <1.24.9 
      Fixed version  : 1.24.9  
    

   0C     3H     0M     0L  util-linux 2.41.4-r0
pkg:apk/alpine/util-linux@2.41.4-r0?os_name=alpine&os_version=3.23

    x HIGH CVE-2026-76642
      https://scout.docker.com/v/CVE-2026-76642?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r0
      Affected range : <2.41.6-r0 
      Fixed version  : 2.41.6-r0  
    
    x HIGH CVE-2026-78408
      https://scout.docker.com/v/CVE-2026-78408?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r1
      Affected range : <2.41.6-r1 
      Fixed version  : 2.41.6-r0  
    
    x HIGH CVE-2026-78410
      https://scout.docker.com/v/CVE-2026-78410?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r0
      Affected range : <2.41.6-r0 
      Fixed version  : 2.41.6-r0  
    


43 vulnerabilities found in 3 packages
  CRITICAL  5  
  HIGH      38 
  MEDIUM    0  
  LOW       0  


What's next:
    View base image update recommendations → docker scout recommendations postgres:16-alpine

```
</details>

### redis

- ref: `redis:8-alpine`
- digest: `redis@sha256:09160599abd229764c0fb44cb6be640294e1d360a54b19985ab4843dcf2d90f1`
- size: 36 MB

```
    v SBOM of image already cached, 29 packages indexed
    ...Evaluating policies
    v Policy evaluation completed

    i Base image was auto-detected. To get more accurate results, build images with max-mode provenance attestations.
      Review https://docs.docker.com/build/attestations/slsa-provenance/ for more information.

 Target               │  redis:8-alpine  │    3C    18H     6M     2L     3?  
   digest             │  09160599abd2    │                                    
 Base image           │  alpine:3        │    3C    15H     6M     2L         
 Refreshed base image │  alpine:3        │    2C     7H     1M     0L         
                      │                  │    -1     -8     -5     -2         
 Updated base image   │  alpine:3.21     │    0C     0H     1M     0L         
                      │                  │    -3    -15     -5     -2         

Policy status  FAILED  (3/7 policies met)
Health score  D  (50%)

 Status │                     Policy                     │           Results           
────────┼────────────────────────────────────────────────┼─────────────────────────────
 !      │ Image runs as the root user                    │                             
 !      │ Copyleft licensed packages found               │    22 packages              
 !      │ Fixable critical or high vulnerabilities found │    3C    18H     0M     0L  
 v      │ No high-profile vulnerabilities                │    0C     0H     0M     0L  
 v      │ No outdated base images                        │                             
 v      │ No unapproved base images                      │    0 deviations             
 !      │ Required supply chain attestations missing     │    2 deviations             

What's next:
    View policy violations → docker scout policy redis:8-alpine
    View vulnerabilities → docker scout cves redis:8-alpine
    View base image update recommendations → docker scout recommendations redis:8-alpine
    Compare with the latest in the registry → docker scout compare --to-latest redis:8-alpine

```

<details><summary>critical + high CVEs</summary>

```
    v SBOM of image already cached, 29 packages indexed
    x Detected 2 vulnerable packages with a total of 21 vulnerabilities


## Overview

                   │       Analyzed Image        
───────────────────┼─────────────────────────────
 Target            │  redis:8-alpine             
   digest          │  09160599abd2               
   platform        │ linux/amd64                 
   vulnerabilities │    3C    18H     0M     0L  
   size            │ 38 MB                       
   packages        │ 29                          


## Packages and Vulnerabilities

   3C    15H     0M     0L  openssl 3.5.6-r0
pkg:apk/alpine/openssl@3.5.6-r0?os_name=alpine&os_version=3.23

    x CRITICAL CVE-2026-63073
      https://scout.docker.com/v/CVE-2026-63073?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x CRITICAL CVE-2026-75803
      https://scout.docker.com/v/CVE-2026-75803?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x CRITICAL CVE-2026-34182
      https://scout.docker.com/v/CVE-2026-34182?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-45447
      https://scout.docker.com/v/CVE-2026-45447?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-7383
      https://scout.docker.com/v/CVE-2026-7383?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-9076
      https://scout.docker.com/v/CVE-2026-9076?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-63076
      https://scout.docker.com/v/CVE-2026-63076?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-63075
      https://scout.docker.com/v/CVE-2026-63075?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-63072
      https://scout.docker.com/v/CVE-2026-63072?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-54874
      https://scout.docker.com/v/CVE-2026-54874?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-45445
      https://scout.docker.com/v/CVE-2026-45445?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-42764
      https://scout.docker.com/v/CVE-2026-42764?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-34183
      https://scout.docker.com/v/CVE-2026-34183?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-34180
      https://scout.docker.com/v/CVE-2026-34180?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    
    x HIGH CVE-2026-18798
      https://scout.docker.com/v/CVE-2026-18798?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-14457
      https://scout.docker.com/v/CVE-2026-14457?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0

What's next:
    View base image update recommendations → docker scout recommendations redis:8-alpine

      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-14456
      https://scout.docker.com/v/CVE-2026-14456?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.8-r0
      Affected range : <3.5.8-r0 
      Fixed version  : 3.5.8-r0  
    
    x HIGH CVE-2026-34181
      https://scout.docker.com/v/CVE-2026-34181?s=alpine&n=openssl&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C3.5.7-r0
      Affected range : <3.5.7-r0 
      Fixed version  : 3.5.7-r0  
    

   0C     3H     0M     0L  util-linux 2.41.4-r0
pkg:apk/alpine/util-linux@2.41.4-r0?os_name=alpine&os_version=3.23

    x HIGH CVE-2026-76642
      https://scout.docker.com/v/CVE-2026-76642?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r0
      Affected range : <2.41.6-r0 
      Fixed version  : 2.41.6-r0  
    
    x HIGH CVE-2026-78408
      https://scout.docker.com/v/CVE-2026-78408?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r1
      Affected range : <2.41.6-r1 
      Fixed version  : 2.41.6-r0  
    
    x HIGH CVE-2026-78410
      https://scout.docker.com/v/CVE-2026-78410?s=alpine&n=util-linux&ns=alpine&t=apk&osn=alpine&osv=3.23&vr=%3C2.41.6-r0
      Affected range : <2.41.6-r0 
      Fixed version  : 2.41.6-r0  
    


21 vulnerabilities found in 2 packages
  CRITICAL  3  
  HIGH      18 
  MEDIUM    0  
  LOW       0  

```
</details>

## Next

- `docker scout recommendations <ref>` for base-image bump guidance on the worst offenders.
- Re-run after any base-image change and diff the digests + counts above.

