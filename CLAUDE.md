# rl-sql

GRPO text-to-SQL fine-tuning project for Qwen3-8B on RHOAI.

## Project structure

- `notebooks/` — Four Jupyter notebooks (data prep, training, eval, deploy)
- `reward/` — Python package for SQL execution rewards during GRPO training
- `manifests/` — Kubernetes/KServe deployment manifests (LLMInferenceService)
- `data/` — Generated training data (NNDSS pairs); BIRD-Platinum lives in /home/mike/git/ReViSQL/data/
- `scripts/` — Helper scripts for BIRD DB download and PVC upload

## Related repos

- `/home/mike/git/ReViSQL/` — Paper source code and BIRD-Platinum dataset
- `/home/mike/git/red-hat-ai-examples/examples/fine-tuning/` — GRPO Ray and LoRA Ray notebook templates
- `/home/mike/git/mcp-for-public-health/` — NNDSS Trino lakehouse and agent
- `/home/mike/git/data-agent-template/` — Target data agent to wire the fine-tuned model into

## Key decisions

- Training Hub `lora_grpo()` with verl backend for distributed GRPO on Ray
- H200 MIG 3g.71gb slices (71GB VRAM each)
- Two-phase: SFT warmup on cleaned BIRD data, then GRPO with execution rewards
- Reward function executes SQL against SQLite (BIRD) and Trino (NNDSS)
- Deploy via llm-d LLMInferenceService, not plain vLLM
- Evaluate with EvalHub (lm-evaluation-harness, guidellm)
