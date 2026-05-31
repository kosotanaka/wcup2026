"""
Scoring logic for FIFA World Cup 2026 prediction app.

Group stage (per match):
- Exact score (home AND away both correct): 3 pts
- Correct result only (W/D/L direction): 1 pt
- Wrong: 0 pt

Knockout stage (per match):
- Exact 90-min score: 3 pts
- Correct 90-min result (W or draw): 1 pt
- Predicted ET correctly (yes/no): +1 pt
- Predicted PK correctly (yes/no): +1 pt
- Max per KO match: 5 pts
"""


def get_result_direction(home, away):
    """Return 'H', 'D', or 'A' based on scores."""
    if home > away:
        return "H"
    elif home < away:
        return "A"
    else:
        return "D"


def score_group_match(prediction: dict, result: dict) -> int:
    """
    Score a group stage match.
    prediction: {"home": int, "away": int}
    result: {"home": int, "away": int}
    Returns points (0, 1, or 3).
    """
    if result is None:
        return 0
    ph, pa = prediction.get("home"), prediction.get("away")
    rh, ra = result.get("home"), result.get("away")
    if ph is None or pa is None or rh is None or ra is None:
        return 0

    if ph == rh and pa == ra:
        return 3
    elif get_result_direction(ph, pa) == get_result_direction(rh, ra):
        return 1
    return 0


def score_knockout_match(prediction: dict, result: dict) -> int:
    """
    Score a knockout stage match.
    prediction: {"home": int, "away": int, "et": bool, "pk": bool}
    result: {"home": int, "away": int, "et": bool, "pk": bool}
    Returns points (0-5).
    """
    if result is None:
        return 0
    ph, pa = prediction.get("home"), prediction.get("away")
    rh, ra = result.get("home"), result.get("away")
    if ph is None or pa is None or rh is None or ra is None:
        return 0

    pts = 0
    if ph == rh and pa == ra:
        pts += 3
    elif get_result_direction(ph, pa) == get_result_direction(rh, ra):
        pts += 1

    p_et = prediction.get("et")
    r_et = result.get("et")
    if p_et is not None and r_et is not None and p_et == r_et:
        pts += 1

    p_pk = prediction.get("pk")
    r_pk = result.get("pk")
    if p_pk is not None and r_pk is not None and p_pk == r_pk:
        pts += 1

    return pts


def score_match(match_id: str, prediction: dict, result: dict) -> int:
    """Score any match based on its ID prefix."""
    if match_id.startswith("GS"):
        return score_group_match(prediction, result)
    else:
        return score_knockout_match(prediction, result)


def compute_total_score(user_predictions: dict, results: dict) -> int:
    """
    user_predictions: {"GS001": {"home": 2, "away": 1}, ...}
    results: {"GS001": {"home": 2, "away": 1}, ...}
    Returns total points.
    """
    total = 0
    for match_id, pred in user_predictions.items():
        result = results.get(match_id)
        if result:
            total += score_match(match_id, pred, result)
    return total


def compute_per_match_scores(user_predictions: dict, results: dict) -> dict:
    """Returns {match_id: points} for all matches with results."""
    scores = {}
    for match_id, pred in user_predictions.items():
        result = results.get(match_id)
        if result:
            scores[match_id] = score_match(match_id, pred, result)
    return scores
