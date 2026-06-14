# Infrastructure and Deployment Configurations

This folder contains container definitions, orchestration configs, and configurations for deploying the Cognitive Voice Platform to staging or production environments.

---

## 🐋 Docker Orchestration

We use Docker to unify development, testing, and production builds. The environment is described in the root [docker-compose.yml](file:///Users/pranjalsingh/.gemini/antigravity-ide/scratch/cognitive-voice-platform/docker-compose.yml).

### Folder Layout
```
infrastructure/
├── README.md                   # This documentation
├── docker/
│   ├── backend.Dockerfile      # Backend API and ASR execution configuration
│   ├── frontend.Dockerfile     # Next.js web application server build configuration
│   └── postgres.Dockerfile     # Database setup container
└── k8s/                        # Future Kubernetes YAML placeholders
```

### Build Instructions
To build and run all services in the background:
```bash
docker-compose up -d --build
```

---

## ⚙️ Service Ports & Architecture

*   **Frontend**: Port `3000` (Next.js Node server)
*   **Backend REST API**: Port `8000` (FastAPI Uvicorn server)
*   **Database**: Port `5432` (PostgreSQL)

For production staging, place an Nginx reverse proxy or an ALB (Application Load Balancer) in front of the services to manage TLS termination and routing.
