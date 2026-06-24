# Deployment

## VM requirement

- Ubuntu 22.04 or 24.04
- 4 vCPU
- 16 GB RAM
- 160 GB SSD
- Docker
- Docker Compose

## Start

```bash
cd infra
docker compose up -d
```

## Check API

```bash
curl http://localhost:8000/health
```

## Before public launch

- Change all default passwords
- Add HTTPS
- Add firewall
- Add database backups
- Add admin authentication
- Add environment secret manager
