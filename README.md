# 🐍 Șarpele Român

A Romanian-themed Snake game deployed on k3s with PostgreSQL leaderboard.

## Stack
- **Frontend:** Vanilla HTML/CSS/JS (Canvas API)
- **Backend:** Python FastAPI
- **Database:** PostgreSQL 16 (StatefulSet + NFS PVC)
- **Infrastructure:** k3s, Helm, Terraform, Ansible
- **CI/CD:** GitHub Actions (self-hosted runner)

## Romanian Foods & Effects

| Food | Points | Effect |
|------|--------|--------|
| 🌭 Mici | 10 | None |
| 🌽 Mămăligă | 5 | Grow x3 segments |
| 🥬 Sarmale | 20 | None |
| 🥃 Palincă | 15 | Speed boost 5s |
| 🍰 Cozonac | 25 | Slow down 4s |
| 🥨 Covrigi | 8 | None |
| 🫙 Zacuscă | 30 | Ghost mode 3s (walk through walls) |
| 🍩 Gogoși | 12 | Shrink 2 segments |

## Deploy to k3s

```bash
# Apply PostgreSQL
kubectl apply -f k8s/postgres.yaml

# Wait for DB to be ready
kubectl wait --for=condition=ready pod \
  -l app=postgres -n snake-ro --timeout=60s

# Apply app
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods -n snake-ro
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /api/scores | Submit score |
| GET | /api/scores | Get leaderboard |
| GET | /api/scores/stats | Global stats |

## Project Structure

```
snake-ro/
├── frontend/
│   └── index.html       — complete game (single file)
├── backend/
│   ├── main.py          — FastAPI app
│   └── requirements.txt
├── k8s/
│   ├── postgres.yaml    — StatefulSet + PVC + Secret
│   └── deployment.yaml  — Deployment + Service + Ingress
├── .github/workflows/
│   └── deploy.yml       — CI/CD pipeline
└── Dockerfile           — builds frontend + backend together
```
