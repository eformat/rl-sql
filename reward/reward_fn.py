"""GRPO reward function for text-to-SQL training.

Scores model-generated SQL by executing it and comparing results to gold SQL.
Supports two backends: SQLite (for BIRD examples) and Trino (for NNDSS examples).

Reward values:
   1.0  execution result matches gold (via grade())
   0.0  execution failure or wrong results
  -1.0  no parseable SQL in response
"""

import os
import re
import logging

from reward.grader import grade
from reward.sql_executor import execute_sql

logger = logging.getLogger(__name__)

_THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)
_SOLUTION_PATTERN = re.compile(r"<solution>(.*?)</solution>", re.DOTALL)
_CODE_BLOCK_PATTERN = re.compile(r"```(?:sql)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)
_SELECT_PATTERN = re.compile(r"(SELECT\s+.+?)(?:;|\Z)", re.DOTALL | re.IGNORECASE)

BIRD_DB_ROOT = os.environ.get(
    "BIRD_DB_ROOT", "/opt/app-root/src/shared/text2sql/bird_databases"
)


def extract_sql(response: str) -> str | None:
    """Extract SQL from a model response, handling various output formats."""
    text = _THINK_PATTERN.sub("", response).strip()

    match = _SOLUTION_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    match = _CODE_BLOCK_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    match = _SELECT_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    return None


def compute_reward(prompt: str, response: str, metadata: dict) -> float:
    """Score a model-generated SQL response.

    Args:
        prompt: The input prompt (schema + question).
        response: The model's full response text.
        metadata: Dict with keys:
            - gold_sql (str): The ground-truth SQL query.
            - db_type (str): "bird" or "nndss".
            - grading_method (str): "set", "multiset", "list", or "subset,...".
            - db_id (str): BIRD database ID (only for db_type="bird").

    Returns:
        Reward float: 1.0 (correct), 0.0 (wrong/error), -1.0 (unparseable).
    """
    gold_sql = metadata.get("gold_sql", "")
    db_type = metadata.get("db_type", "bird")
    grading_method = metadata.get("grading_method", "set")
    db_id = metadata.get("db_id")

    generated_sql = extract_sql(response)
    if not generated_sql:
        return -1.0

    gold_results, gold_err = execute_sql(
        gold_sql, db_type=db_type, db_id=db_id, bird_db_root=BIRD_DB_ROOT,
    )
    if gold_err:
        logger.warning("Gold SQL execution failed: %s", gold_err)
        return 0.0

    gen_results, gen_err = execute_sql(
        generated_sql, db_type=db_type, db_id=db_id, bird_db_root=BIRD_DB_ROOT,
    )
    if gen_err:
        return 0.0

    is_correct, info = grade(
        list(gold_results), list(gen_results), grading_method=grading_method,
    )
    return 1.0 if is_correct else 0.0
