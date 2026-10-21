"""ELO rating calculation helpers.

Pure synchronous functions implementing the standard ELO formula with
configurable K-factor. No side effects, no service dependencies.

The ELO system uses the following formula:
    Expected score: E_a = 1 / (1 + 10^((R_b - R_a) / 400))
    Rating change:  delta = K * (actual_score - expected_score)
"""

from __future__ import annotations


def calculate_expected_score(rating_a: int, rating_b: int) -> float:
    """Calculate expected score for player A against player B.

    Args:
        rating_a: Player A's ELO rating.
        rating_b: Player B's ELO rating.

    Returns:
        Expected score (probability of winning) between 0.0 and 1.0.
    """
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def calculate_elo_change(
    winner_rating: int,
    loser_rating: int,
    k_factor: int,
    is_draw: bool = False,
) -> tuple[int, int]:
    """Calculate ELO changes for both players.

    Args:
        winner_rating: ELO rating of the winning player (or player A in a draw).
        loser_rating: ELO rating of the losing player (or player B in a draw).
        k_factor: K-factor controlling rating volatility.
        is_draw: If True, treat as a draw (both get 0.5 actual score).

    Returns:
        Tuple of (winner_change, loser_change). For draws, these are
        symmetric adjustments where higher-rated player loses points
        and lower-rated player gains points.
    """
    expected_winner = calculate_expected_score(winner_rating, loser_rating)
    expected_loser = 1.0 - expected_winner

    if is_draw:
        # Draw: actual score is 0.5 for both
        winner_change = round(k_factor * (0.5 - expected_winner))
        loser_change = round(k_factor * (0.5 - expected_loser))
    else:
        # Win: winner gets 1.0, loser gets 0.0
        winner_change = round(k_factor * (1.0 - expected_winner))
        loser_change = round(k_factor * (0.0 - expected_loser))

    return winner_change, loser_change
