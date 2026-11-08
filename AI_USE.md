# AI Use Statement and Methodology Disclosure

## 1. Overview of AI Tools Utilized
During the execution of this Cloud Computing Assignment Mini Project (Knowledge Distillation and Deployment of a Lightweight Command-Parsing Language Model on a Local Cloud), the following AI tools and models were used:

1. **Phi-3.5-mini-instruct (3.8 Billion Parameters)**
   - **Provider / Runtime**: Served locally via Ollama.
   - **Role**: Teacher model for sequence-level knowledge distillation.
   - **Hyperparameters**: Temperature = 0.0, Seed = 42, deterministic decoding.
   - **Task**: Generating gold-standard pseudo-labels (intent classification and slot extraction) for 3,000 commands drawn from the SLURP dataset pool.

2. **Antigravity (Google DeepMind Coding Assistant / Gemini 3.8 Flash)**
   - **Role**: Architectural scaffolding, test-driven development, Docker and Kubernetes manifest generation, mathematical verification of subnet masks, and documentation synthesis.

---

## 2. Tasks and Concrete Uses

| Task / Domain | Specific Purpose | Prompts & Workflow |
| :--- | :--- | :--- |
| **Task 1: Teacher Prompt & Sharding** | Formulating the system prompt for 4-key JSON schema and structuring parallel worker logic. | Directed the LLM to output strictly four keys (`intent`, `date`, `time`, `place`) and adhere to exact substring preservation. |
| **Task 2: Student Distillation** | Scaffolding PyTorch / Hugging Face training script (`Pythia-70M`) with fixed random seed and reproducible loss logging. | Verified causal language modeling tokenization and sequence masking (`Command: <text>\nJSON: <reply>`). |
| **Task 3: Containerized Service** | Writing FastAPI endpoints (`/parse`, `/healthz`, `/readyz`), dynamic response headers (`X-Model-Version`, `X-Served-By`), and Dockerfile. | Configured CPU-only wheels (`--index-url https://download.pytorch.org/whl/cpu`) to keep image below 2 GB. |
| **Task 4: Kubernetes Manifests** | Formulating Deployments, Services, Traefik Ingress, and HPA definitions. | Enforced CPU and memory requests/limits, liveness/readiness probes, and secret injection. |
| **Task 5: Subnetting & Stateless NACLs** | Validating binary calculations for variable-length subnet masks (VLSM) and first-match rule ordering in `nacl.json`. | Cross-checked host capacities ($2^{32-\text{prefix}} - 2$) and verified NACL logic with `nacl_sim.py`. |
| **Task 6: CI/CD Pipeline** | Constructing GitHub Actions workflow with 5 stages (linting, tests, release download, quality gate, secret scan). | Enforced `--min-validity 95` exit code handling and Gitleaks integration. |

---

## 3. Verification and Validation Procedures
Every output produced or influenced by AI was systematically checked and verified through automated validation scripts and standard testing tools:

1. **Deterministic Testing of Network Rules**:
   - The NACL configuration (`network/nacl.json`) generated with AI was independently checked using `python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check`.
   - Verified 100.0% accuracy across all sample packets and manually audited boundary IP matching for the `198.51.100.0/24` abusive block.

2. **Mathematical Verification of Subnet Allocations**:
   - Manually recalculated CIDR block boundaries, network addresses, broadcast addresses, and usable host counts. Verified that all four subnets (`/22`, `/24`, `/25`, `/27`) fit contiguously within `10.20.0.0/16` without overlap.

3. **Schema Compliance & Model Evaluation**:
   - Ran `tools/score.py` against `data/validation.jsonl` on all teacher and student outputs. Verified that the quality gate accurately passed valid 4-key predictions and rejected malformed outputs.
   - Tested failure conditions by running `score.py` against untrained model outputs to confirm that the pipeline properly fails with exit code 1 when validity drops below 95%.

4. **Unit and Endpoint Testing**:
   - Implemented 5 automated test cases in `tests/test_service.py` verifying status codes, required header injection, fault injection (`FAULT_INJECT=1`), and JSON schema validation.

5. **Security and Secret Auditing**:
   - Audited the entire repository using Gitleaks and git diff inspection to confirm that no credentials, API keys, or secrets are committed.

