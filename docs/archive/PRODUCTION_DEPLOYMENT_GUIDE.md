# Production Deployment Guide

## 🔐 Security Setup (REQUIRED)

### 1. Create Secret Files

```bash
mkdir -p secrets
chmod 700 secrets

# Generate strong secrets
openssl rand -base64 32 > secrets/PERPLEXITY_API_KEY.txt
openssl rand -base64 32 > secrets/hypercode_jwt_secret.txt
openssl rand -base64 32 > secrets/postgres_password.txt
openssl rand -base64 32 > secrets/grafana_admin_password.txt

# Set your actual PERPLEXITY API key
echo "YOUR_ACTUAL_API_KEY" > secrets/PERPLEXITY_API_KEY.txt

chmod 600 secrets/*.txt
```

### 2. Update .gitignore

```bash
echo "secrets/*.txt" >> .gitignore
echo "!secrets/.gitkeep" >> .gitignore
```

## 🚀 Deployment Steps

### 1. Review Configuration

- Verify all paths in docker-compose.prod.yml match your structure
- Update resource limits based on your infrastructure
- Configure backup schedules for volumes

### 2. Network Configuration

The production setup uses 3 isolated networks:
- **frontend-net**: Public-facing services
- **backend-net**: Application services (internal)
- **data-net**: Database layer (internal)

### 3. Deploy Services

```bash
# Deploy production stack
docker compose -f docker-compose.prod.yml up -d

# Check service health
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

## 🔒 Security Changes Made

### Critical Fixes

1. **Secrets Management**
   - All API keys moved to Docker secrets
   - No hardcoded credentials in compose file
   - Secrets stored in separate files (not in git)

2. **Container Hardening**
   - `no-new-privileges` on all containers
   - Dropped all capabilities, added only required ones
   - Read-only root filesystem where possible
   - Non-root users for infrastructure services

3. **Network Segmentation**
   - Frontend network for public services
   - Backend network (internal) for application logic
   - Data network (internal) for databases
   - Services only connected to required networks

4. **Port Binding**
   - All ports bound to localhost (127.0.0.1)
   - Use reverse proxy (nginx/traefik) with TLS for public access
   - No direct external exposure

5. **Docker Socket**
   - Removed from devops-engineer (security risk)
   - Use Docker-in-Docker or remote API with TLS if needed

### Operational Improvements

1. **Resource Management**
   - Set both limits AND reservations
   - Prevents resource starvation
   - Enables proper scheduling

2. **Health Checks**
   - Added to all agent services
   - Proper startup periods
   - Restart policies configured

3. **Logging**
   - JSON file driver with rotation
   - Max 10MB per file, 3 files retained
   - Prevents disk space exhaustion

4. **Image Versions**
   - All images pinned to specific versions
   - Prevents unexpected updates
   - Reproducible deployments

## 🔧 Reverse Proxy Setup

### Nginx Example (recommended)

```nginx
# /etc/nginx/sites-available/hypercode

upstream hypercode_core {
    server 127.0.0.1:8000;
}

upstream hypercode_dashboard {
    server 127.0.0.1:8088;
}

server {
    listen 443 ssl http2;
    server_name hypercode.example.com;

    ssl_certificate /etc/letsencrypt/live/hypercode.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hypercode.example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://hypercode_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://hypercode_core;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running AI requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name hypercode.example.com;
    return 301 https://$server_name$request_uri;
}
```

## 📊 Monitoring Access

Access monitoring tools through reverse proxy with authentication:

- **Grafana**: https://monitoring.example.com/grafana
- **Prometheus**: https://monitoring.example.com/prometheus
- **Jaeger**: https://monitoring.example.com/jaeger

## 💾 Backup Strategy

### Database Backups

```bash
# Create backup script
cat > backup_postgres.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec postgres pg_dump -U postgres hypercode | \
  gzip > "$BACKUP_DIR/hypercode_$TIMESTAMP.sql.gz"

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup_postgres.sh

# Schedule with cron
crontab -e
# Add: 0 2 * * * /path/to/backup_postgres.sh
```

### Volume Backups

```bash
# Backup all volumes
docker run --rm \
  -v hypercode_redis-data:/data/redis:ro \
  -v hypercode_postgres-data:/data/postgres:ro \
  -v hypercode_grafana-data:/data/grafana:ro \
  -v /backups:/backup \
  alpine \
  tar czf /backup/volumes_$(date +%Y%m%d).tar.gz /data
```

## 🔍 Health Monitoring

### Check All Services

```bash
# Quick health check
docker compose -f docker-compose.prod.yml ps

# Detailed health status
docker inspect --format='{{.Name}}: {{.State.Health.Status}}' \
  $(docker ps -q)

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f hypercode-core
```

### Automated Monitoring

Consider setting up:
- Prometheus alerts for service failures
- Grafana dashboards for resource usage
- Log aggregation (ELK/Loki)
- Uptime monitoring (UptimeRobot, Pingdom)

## 🔄 Updates and Maintenance

### Rolling Updates

```bash
# Update specific service
docker compose -f docker-compose.prod.yml pull frontend-specialist
docker compose -f docker-compose.prod.yml up -d --no-deps frontend-specialist

# Update all services
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Maintenance Mode

```bash
# Stop services gracefully
docker compose -f docker-compose.prod.yml stop

# Start services
docker compose -f docker-compose.prod.yml start

# Restart specific service
docker compose -f docker-compose.prod.yml restart redis
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs service-name

# Check resource constraints
docker stats

# Verify secrets exist
ls -la secrets/
```

### Database Connection Issues

```bash
# Test postgres connectivity
docker exec postgres psql -U postgres -c "SELECT 1"

# Test redis connectivity
docker exec redis redis-cli ping
```

### Permission Issues

```bash
# Fix volume permissions
docker compose -f docker-compose.prod.yml down
docker volume rm hypercode_data-name
docker compose -f docker-compose.prod.yml up -d
```

## 📈 Scaling Considerations

### Horizontal Scaling

For production scale, consider:

1. **Docker Swarm** or **Kubernetes** for orchestration
2. **Load balancers** for agent services
3. **Redis Cluster** for distributed caching
4. **PostgreSQL replication** for read replicas
5. **Separate monitoring cluster**

### Vertical Scaling

Adjust resource limits in compose file:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
    reservations:
      cpus: '2.0'
      memory: 4G
```

## 🔐 Security Checklist

- [ ] All secrets in separate files (not in compose/env)
- [ ] Secrets files have 600 permissions
- [ ] Services run as non-root where possible
- [ ] All capabilities dropped except required
- [ ] Ports bound to localhost only
- [ ] Reverse proxy with TLS configured
- [ ] Firewall rules configured
- [ ] Regular security updates scheduled
- [ ] Backup and restore tested
- [ ] Monitoring and alerting active
- [ ] Log retention policy defined
- [ ] Incident response plan documented

## 🆘 Emergency Procedures

### Complete System Failure

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Restore from backup
./restore_backup.sh

# Start services
docker compose -f docker-compose.prod.yml up -d
```

### Data Corruption

```bash
# Stop affected service
docker compose -f docker-compose.prod.yml stop postgres

# Restore volume from backup
docker volume rm hypercode_postgres-data
docker volume create hypercode_postgres-data
# Restore backup to volume

# Start service
docker compose -f docker-compose.prod.yml start postgres
```

## 📞 Support

For issues:
1. Check logs: `docker compose logs -f`
2. Review health checks: `docker ps`
3. Check resource usage: `docker stats`
4. Consult troubleshooting section above
