"""SQL result grading functions.

Adapted from ReViSQL (tinker_cookbook/recipes/sql_rl/grader.py).
Compares execution results of predicted vs. gold SQL using multiple
matching strategies: multiset, set, list, subset.
"""


def remove_empty_rows(result):
    return [row for row in result if any(
        col is not None and str(col).strip() != "" for col in row
    )]


def grade_basic(result1, result2):
    if len(result1) == 0:
        return len(result2) == 0
    if len(result2) == 0:
        return False
    return len(result1[0]) == len(result2[0])


def grade_single_number(num1, num2):
    try:
        float1, float2 = float(num1), float(num2)
        return abs((float1 - float2) / float1) < 1e-2
    except Exception:
        return False


def grade_multiset(result1, result2):
    if len(result1) != len(result2):
        return False, {"message": "Number of rows do not match"}
    sorted_r1 = [tuple(sorted(str(r) for r in row)) for row in result1]
    sorted_r2 = [tuple(sorted(str(r) for r in row)) for row in result2]
    if sorted(sorted_r1) != sorted(sorted_r2):
        return False, {"message": "Results do not match as multisets"}
    return True, {"message": "Results match as multisets"}


def grade_set(result1, result2):
    sorted_r1 = [tuple(sorted(str(r) for r in row)) for row in result1]
    sorted_r2 = [tuple(sorted(str(r) for r in row)) for row in result2]
    if set(sorted_r1) != set(sorted_r2):
        return False, {"message": "Results do not match as sets"}
    return True, {"message": "Results match as sets"}


def grade_subset(all_results, matching_results,
                 strict_row_count=None, minimum_row_count=None):
    matching_results = list(set(matching_results))
    assert strict_row_count is None or minimum_row_count is None
    if strict_row_count is not None and len(matching_results) != strict_row_count:
        return False, {"message": f"Row count {len(matching_results)} != required {strict_row_count}"}
    if minimum_row_count is not None and len(matching_results) < minimum_row_count:
        return False, {"message": f"Row count {len(matching_results)} < required {minimum_row_count}"}
    set_all = {tuple(sorted(str(r) for r in row)) for row in all_results}
    set_match = {tuple(sorted(str(r) for r in row)) for row in matching_results}
    if not set_match.issubset(set_all):
        return False, {"message": "Not all matching rows are in the full result set"}
    return True, {"message": "Subset check passed"}


def grade_list(result1, result2):
    if len(result1) != len(result2):
        return False, {"message": "Number of rows do not match"}
    sorted_r1 = [tuple(sorted(str(r) for r in row)) for row in result1]
    sorted_r2 = [tuple(sorted(str(r) for r in row)) for row in result2]
    if sorted_r1 != sorted_r2:
        return False, {"message": "Results do not match in order"}
    return True, {"message": "Results match in order"}


def grade(ground_truth_result, generated_result, grading_method="multiset"):
    """Compare two SQL result sets using the specified grading method.

    Returns (is_correct: bool, info: dict).
    """
    ground_truth_result = remove_empty_rows(ground_truth_result)
    generated_result = remove_empty_rows(generated_result)

    if not grade_basic(ground_truth_result, generated_result):
        return False, {"message": "Column count mismatch"}

    if (len(ground_truth_result) == 1 and len(ground_truth_result[0]) == 1
            and len(generated_result) == 1 and len(generated_result[0]) == 1):
        if grade_single_number(ground_truth_result[0][0], generated_result[0][0]):
            return True, {"message": "Single number matches within tolerance"}

    if "multiset" in grading_method:
        return grade_multiset(ground_truth_result, generated_result)
    elif "subset" in grading_method:
        _, method, row_count = grading_method.split(",")
        if method == "=":
            return grade_subset(ground_truth_result, generated_result,
                                strict_row_count=int(row_count))
        elif method == ">=":
            return grade_subset(ground_truth_result, generated_result,
                                minimum_row_count=int(row_count))
        return False, {"message": f"Unknown subset method: {method}"}
    elif "list" in grading_method:
        return grade_list(ground_truth_result, generated_result)
    elif "set" in grading_method:
        return grade_set(ground_truth_result, generated_result)
    return False, {"message": f"Unknown grading method: {grading_method}"}
