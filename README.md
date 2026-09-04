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
- Trino lakehouse with NNDSS data (from [mcp-for-public-health](https://github.com/red-hat-data-services/mcp-for-public-health))
- EvalHub for standardized benchmarking

## Quick Start

1. Clone this repo into an RHOAI workbench
2. Run `scripts/download_bird_dbs.sh` to fetch BIRD SQLite databases
3. Run `scripts/upload_to_pvc.sh` to stage data on the shared PVC
4. Work through the notebooks in order

## Reward Function

The `reward/` module provides execution-based SQL grading adapted from [ReViSQL](https://github.com/ThinkingMachinesLab/ReViSQL):

- `grader.py` — Result comparison (multiset, set, list, subset methods)
- `sql_executor.py` — Dual-backend execution (SQLite for BIRD, Trino for NNDSS)
- `reward_fn.py` — GRPO reward entry point
- `nndss_schema.py` — NNDSS table definitions and metadata

## Deployment

The fine-tuned model is deployed via llm-d `LLMInferenceService` on a MIG 3g.71gb slice. See `manifests/` for the CR templates.

## Data Sources

- [BIRD-Platinum](https://github.com/ThinkingMachinesLab/ReViSQL/tree/main/data) — 2,064 expert-verified text-to-SQL training pairs
- [NNDSS](https://www.health.gov.au/topics/communicable-diseases/nndss) — Australian disease surveillance data in Trino/Iceberg
