# rl-sql — GRPO Text-to-SQL Fine-Tuning

Fine-tune Qwen3-8B for text-to-SQL using GRPO (Group Relative Policy Optimization) with execution-based rewards, inspired by [ReViSQL](https://thinkingmachines.ai/news/putting-task-expertise-into-rl).

Trains on [BIRD-Platinum](https://github.com/ThinkingMachinesLab/ReViSQL) (2,064 expert-verified text-to-SQL pairs) plus domain-specific NNDSS public health data, with SQL execution rewards verified against both SQLite (BIRD) and Trino (NNDSS).

## Architecture

```
BIRD-Platinum (2,064 pairs)  ──┐
                                ├──> SFT Warmup ──> GRPO RL ──> Merge LoRA ──> Deploy
NNDSS Trino pairs (~300)     ──┘         │              │                        │
                                    Qwen3-8B       Execution         LLMInferenceService
                                    + LoRA r=32    Rewards               (llm-d)
                                                  SQLite + Trino            │
                                                                    Data Agent Template
```

## Notebooks

| # | Notebook | Purpose |
|---|----------|---------|
| 1 | `01_data_preparation.ipynb` | Load BIRD-Platinum, generate NNDSS pairs, upload to PVC |
| 2 | `02_grpo_text2sql-rayjob.ipynb` | Two-phase training: SFT warmup then GRPO RL on Ray |
| 3 | `03_evaluation.ipynb` | BIRD dev + NNDSS eval + EvalHub benchmarks |
| 4 | `04_deploy_and_integrate.ipynb` | Deploy with llm-d, wire into data agent |

## Requirements

- RHOAI 3.5+ with Ray, KServe, and llm-d components enabled
- H200 MIG slices (`nvidia.com/mig-3g.71gb` recommended for training and serving)
- EvalHub for standardized benchmarking
- `oc`, `helm`, `mc` (MinIO client) CLIs for Trino deployment

## Quick Start

### 1. Deploy Trino with NNDSS data

The repo includes everything needed to stand up a Trino Iceberg lakehouse with Australian disease surveillance data (NNDSS). This provides the execution backend for RL reward validation during GRPO training.

```bash
./deploy/deploy-trino.sh
```

This deploys MinIO (S3 storage), Trino (Iceberg catalog via Nessie), and loads three tables:

| Table | Rows | Description |
|-------|------|-------------|
| `lakehouse.nndss.notifications` | ~500 | Annual disease notifications (4 diseases, 2008-2025, by state) |
| `lakehouse.nndss.population` | 144 | ABS estimated resident population (2008-2025, by state) |
| `lakehouse.nndss.fortnightly_notifications` | ~5,000 | Fortnightly notifications (73 diseases, 2024-2026, by state) |

Port-forward for notebook access:
```bash
oc port-forward svc/trino 8090:8080 -n rl-sql
```

### 2. Download BIRD SQLite databases

```bash
./scripts/download_bird_dbs.sh
```

### 3. Upload to PVC

From an RHOAI workbench where the shared PVC is mounted:
```bash
./scripts/upload_to_pvc.sh /opt/app-root/src/shared
```

### 4. Run the notebooks in order

## Reward Function

The `reward/` module provides execution-based SQL grading adapted from [ReViSQL](https://github.com/ThinkingMachinesLab/ReViSQL):

- `grader.py` — Result comparison (multiset, set, list, subset methods)
- `sql_executor.py` — Dual-backend execution (SQLite for BIRD, Trino for NNDSS)
- `reward_fn.py` — GRPO reward entry point
- `nndss_schema.py` — NNDSS table definitions and metadata

## Deployment

The fine-tuned model is deployed via llm-d `LLMInferenceService` on a MIG 3g.71gb slice. See `manifests/` for the CR templates.

## Repository Layout

```
rl-sql/
  notebooks/                   # Jupyter notebooks (data prep → train → eval → deploy)
  reward/                      # SQL execution reward module for GRPO training
  manifests/                   # LLMInferenceService + MaaS deployment CRs
  data/                        # BIRD-Platinum parquet, DDL schemas, generated NNDSS pairs
  deploy/
    deploy-trino.sh            # One-command Trino + NNDSS data setup
    trino-chart/               # Trino Helm chart (Iceberg on MinIO/Nessie)
    scripts/                   # Data loading scripts (notifications, population, fortnightly)
    nndss-data/                # NNDSS source data (4 annual + 50 fortnightly Excel files)
  scripts/                     # BIRD database download + PVC upload helpers
```

## Data Sources

- [BIRD-Platinum](https://github.com/ThinkingMachinesLab/ReViSQL/tree/main/data) — 2,064 expert-verified text-to-SQL training pairs
- [NNDSS](https://www.health.gov.au/topics/communicable-diseases/nndss) — Australian disease surveillance data in Trino/Iceberg
