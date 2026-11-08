# Cloud Computing (CS3081) Mini Project
## Knowledge Distillation and Deployment of a Lightweight Command-Parsing Language Model on a Local Cloud

- **Student Name**: Shailesh Kumar
- **Roll Number**: `230103014`
- **GitHub Repository**: [https://github.com/sk054/230103014-cloud-assignment](https://github.com/sk054/230103014-cloud-assignment)
- **Course**: CS3081 - Cloud Computing Mini Project

---

## Architecture Overview
This project demonstrates an end-to-end cloud-native machine learning pipeline:
1. **Parallel Teacher Labelling & Object Storage**: Natural language commands are partitioned across workers and annotated by a teacher LLM (`Phi-3.5-mini-instruct` via Ollama at temperature 0, seed 42) into an S3-compatible SeaweedFS object store.
2. **Data Cleaning & Verification**: Automated filtering removes malformed JSON, invalid keys, unsupported intents, and non-substring slot hallucinations, generating a SHA-256 verified dataset (`train.jsonl`).
3. **Sequence-Level Distillation**: An ultra-compact student model (`EleutherAI/pythia-70m`) is fine-tuned on CPU to predict the 4-key JSON representation (`intent`, `date`, `time`, `place`).
4. **Containerized Microservice**: A lightweight FastAPI inference service (< 2 GB, CPU-only wheels) retrieves model weights from S3 dynamically at startup and enforces strict schema validation and fault injection testing.
5. **Local Kubernetes Deployment**: Orchestrated on a local `k3d` cluster with Traefik Ingress routing, CPU-based Horizontal Pod Autoscaling (HPA), rolling zero-downtime updates, and automated pod self-healing.
6. **Network ACL & Subnet Design**: Variable-length subnet masking (VLSM) and stateless first-match Network Access Control Lists (NACL) securing the public load balancer and backends.
7. **CI/CD Quality Gates**: Fully automated GitHub Actions workflow enforcing linting, unit tests, model scoring gates (`--min-validity 95`), and Gitleaks secret scanning.

---

## Directory Structure
```
├── .github/workflows/
│   └── ci.yml                     # 5-stage CI/CD pipeline
├── cluster/
│   └── k3d.yaml                   # k3d cluster specification
├── data/
│   ├── commands_pool.jsonl        # 3,000 raw input commands
│   ├── validation.jsonl           # 100 gold-standard labeled commands
│   ├── schema.json                # 4-key JSON schema and intent rules
│   └── rate_card.json             # Pricing structure for cost estimation
├── datasets/
│   ├── teacher/                   # Sharded raw teacher outputs
│   └── v1/
│       ├── train.jsonl            # Cleaned training dataset
│       └── train.sha256           # SHA-256 checksum
├── k8s/
│   ├── namespaces.yaml            # data, app, and pipeline namespaces
│   ├── seaweedfs.yaml             # SeaweedFS deployment & S3 service
│   ├── secret.yaml                # S3 access credentials
│   ├── deployment.yaml            # 2-replica inference deployment
│   ├── service.yaml               # ClusterIP service
│   ├── ingress.yaml               # Traefik ingress routing
│   └── hpa.yaml                   # HorizontalPodAutoscaler (70% CPU)
├── models/
│   ├── v1/                        # Student model v1 & model.sha256
│   └── v2/                        # Student model v2 (rolling update)
├── network/
│   ├── nacl.json                  # Stateless NACL rules for public subnet
│   ├── packets_sample.jsonl       # Test packet verification dataset
│   └── subnets.md                 # VLSM allocation tables and derivations
├── prompts/
│   └── teacher_prompt.txt         # Teacher prompt for 4-key JSON extraction
├── results/                       # Execution logs, scores, and Locust stats
├── service/
│   ├── app.py                     # FastAPI service implementation
│   ├── Dockerfile                 # Slim CPU-only container definition
│   └── requirements.txt           # Pinned dependencies
├── tests/
│   └── test_service.py            # Unit test suite
├── tools/
│   ├── locustfile.py              # Locust load-testing script
│   ├── nacl_sim.py                # Stateless NACL simulator
│   └── score.py                   # Automated accuracy & validity scorer
├── training/
│   ├── config.yaml                # Hyperparameters and library versions
│   ├── loss.csv                   # Epoch training loss log
│   └── train.py                   # Sequence distillation training script
├── worker/
│   ├── worker.py                  # Parallel sharding worker
│   └── clean.py                   # Shard cleaning and verification script
├── AI_USE.md                      # AI tool disclosure & validation details
├── Makefile                       # One-command operations
└── README.md                      # Documentation and GitHub repository links
```

---

## Quickstart & Execution Commands

### 1. Prerequisites
Ensure the following tools are installed on your machine:
- Python 3.10+
- Docker Desktop
- k3d (`curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash` or via winget)
- kubectl

### 2. Full System Build & Deployment (`make up`)
Deploy the entire cluster, build the image, and configure workloads in at most three commands:
```bash
make up
```
*Behind the scenes, this executes:*
1. `k3d cluster create --config cluster/k3d.yaml`
2. `docker build -t parser-service:v1 -f service/Dockerfile . && k3d image import parser-service:v1 -c cloud-cluster`
3. `kubectl apply -f k8s/`

### 3. Model Training (`make train`)
To verify reproducible training on a subset of 50 records:
```bash
make train SUBSET=50
```
To train the full distillation model on 1,500 records:
```bash
make train
```

### 4. Running Unit Tests & Quality Gates
Execute the unit test suite:
```bash
make test
```
Evaluate student model against the validation set:
```bash
make score
```

### 5. Running the Locust Load Test
Run a 2-minute load test with 4 concurrent users against the local ingress:
```bash
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
```

### 6. Cluster Teardown (`make down`)
Delete the local k3d cluster and free all resources:
```bash
make down
```

---

## Model Release Assets
Model weights, tokenizer configurations, and SHA-256 checksums are published as assets on GitHub Releases:
- **Release Tag**: `v1.0.0`
- **Release Assets**: `models/v1/config.json`, `models/v1/model.bin`, `models/v1/tokenizer_config.json`, `models/v1/model.sha256`
- **Asset Download URL**: [https://github.com/sk054/230103014-cloud-assignment/releases/tag/v1.0.0](https://github.com/sk054/230103014-cloud-assignment/releases/tag/v1.0.0)
