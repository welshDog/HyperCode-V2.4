# Security Hardening Checklist

## Before any internal endpoint goes live

- [ ] Endpoint requires encrypted envelope (not plaintext JSON)
- [ ] `kid` authorised for this endpoint/channel
- [ ] Anti-replay Redis check in place
- [ ] `ts` window enforced (±60s)
- [ ] `aad` binds to method + path
- [ ] No secrets in code or `.env` committed to git
- [ ] `detect-secrets scan` passes clean

## Key Management

- [ ] Each agent has unique `kid` + key
- [ ] Keys stored in Docker secrets / K8s Secrets (not `.env` in prod)
- [ ] `JWT_SECRET` overridden from default `dev-secret-key`
- [ ] `HYPERSYNC_MASTER_KEY` generated and set
- [ ] Old `kid` values retired after rotation

## Redis Security

- [ ] Replay cache keys have TTL set
- [ ] Nonce keys bounded (auto-expire)
- [ ] No plaintext agent messages on sensitive channels
- [ ] `AgentMessage.to_redis_payload()` wraps with encrypted envelope
