# Monthly Compliance Checklist (Reusable)

**Instance:** HyperCode Grafana Stack
**Date:** _______________
**Auditor:** _______________

| Category | Check Item | Threshold | Status (Pass/Fail) | Notes |
|---|---|---|---|---|
| **Storage** | Prometheus TSDB Size | < 5GB | [ ] | Current: ____ GB |
| **Storage** | Loki Chunk Store | < 5GB | [ ] | Current: ____ GB |
| **Performance** | Active Series Count | < 100k | [ ] | Current: ____ |
| **Grafana** | Dashboard Count | < 500 | [ ] | Current: ____ |
| **Grafana** | Annotation Count | < 1000 | [ ] | **Action needed if high** |
| **Security** | Public Dashboards | Disabled | [ ] | Check `[auth.anonymous]` |
| **Security** | Users/API Keys | Reviewed | [ ] | Remove unused keys |
| **Backups** | Dashboards Exported | Yes | [ ] | JSON export done |
| **Backups** | Alert Rules Exported | Yes | [ ] | YAML/JSON export done |
| **System** | Docker Container Health | Up > 99% | [ ] | Check `docker ps` |

*Run the `grafana_quota_check.sh` script to populate the values.*

***

## Sign-off
**Auditor Signature:** ____________________
**Next Audit Due:** ____________________
