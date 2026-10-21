"""Unit tests for the vault raid engine.

Tests pure functions for raid probability, artifact selection, and
cooldown logic. No mocks needed -- these are pure functions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.modules.vault.raid_engine import (
    RARITY_WEIGHTS,
    calculate_raid_success,
    is_raid_on_cooldown,
    select_raid_target_artifact,
)

# ---------------------------------------------------------------------------
# Helper dataclass for artifact records
# ---------------------------------------------------------------------------


@dataclass
class FakeArtifact:
    """Minimal artifact record for testing."""

    id: str
    rarity: str


# ---------------------------------------------------------------------------
# Tests — calculate_raid_success
# ---------------------------------------------------------------------------


class TestCalculateRaidSuccess:
    """Tests for ``calculate_raid_success``."""

    def test_always_succeeds_with_chance_1(self) -> None:
        """With base_chance=1.0, raid always succeeds for non-legendary."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.5):
            assert calculate_raid_success(1.0, "common", 0.5) is True

    def test_always_fails_with_chance_0(self) -> None:
        """With base_chance=0.0, raid always fails."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.0):
            # random() returns 0.0, which is not < 0.0
            assert calculate_raid_success(0.0, "common", 0.5) is False

    def test_success_at_boundary(self) -> None:
        """Raid succeeds when random value is below base chance."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.69):
            assert calculate_raid_success(0.7, "common", 0.5) is True

    def test_failure_at_boundary(self) -> None:
        """Raid fails when random value equals or exceeds base chance."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.7):
            assert calculate_raid_success(0.7, "common", 0.5) is False

    def test_legendary_reduces_chance(self) -> None:
        """Legendary modifier reduces the effective chance."""
        # 0.7 * 0.5 = 0.35 effective chance
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.36):
            assert calculate_raid_success(0.7, "legendary", 0.5) is False

    def test_legendary_still_can_succeed(self) -> None:
        """Legendary raid can still succeed with low random value."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.2):
            assert calculate_raid_success(0.7, "legendary", 0.5) is True

    def test_rare_no_modifier(self) -> None:
        """Non-legendary rarities do not get modified."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.5):
            assert calculate_raid_success(0.7, "rare", 0.5) is True

    def test_epic_no_modifier(self) -> None:
        """Epic rarity does not get modified."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.5):
            assert calculate_raid_success(0.7, "epic", 0.5) is True

    def test_unknown_rarity_no_modifier(self) -> None:
        """Unknown rarity strings are treated like non-legendary."""
        with patch("src.modules.vault.raid_engine.random.random", return_value=0.5):
            assert calculate_raid_success(0.7, "mythical", 0.5) is True


# ---------------------------------------------------------------------------
# Tests — select_raid_target_artifact
# ---------------------------------------------------------------------------


class TestSelectRaidTargetArtifact:
    """Tests for ``select_raid_target_artifact``."""

    def test_empty_list_returns_none(self) -> None:
        """Empty artifact list returns None."""
        assert select_raid_target_artifact([]) is None

    def test_single_item_always_selected(self) -> None:
        """A single artifact is always selected."""
        artifact = FakeArtifact(id="a1", rarity="common")
        result = select_raid_target_artifact([artifact], rng=random.Random(42))
        assert result is artifact

    def test_weighted_selection_is_deterministic_with_seed(self) -> None:
        """Same seed produces same selection."""
        artifacts = [
            FakeArtifact(id="c1", rarity="common"),
            FakeArtifact(id="r1", rarity="rare"),
            FakeArtifact(id="e1", rarity="epic"),
            FakeArtifact(id="l1", rarity="legendary"),
        ]
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        result1 = select_raid_target_artifact(artifacts, rng=rng1)
        result2 = select_raid_target_artifact(artifacts, rng=rng2)

        assert result1.id == result2.id

    def test_common_weighted_more_than_legendary(self) -> None:
        """Common artifacts are selected more frequently than legendary.

        Run many trials to verify weighting is applied.
        """
        artifacts = [
            FakeArtifact(id="c1", rarity="common"),
            FakeArtifact(id="l1", rarity="legendary"),
        ]

        counts: dict[str, int] = {"c1": 0, "l1": 0}
        rng = random.Random(123)
        trials = 1000

        for _ in range(trials):
            result = select_raid_target_artifact(artifacts, rng=rng)
            counts[result.id] += 1

        # Common weight=4, legendary weight=1, so common should be ~80%
        assert counts["c1"] > counts["l1"] * 2

    def test_all_rarities_have_correct_weights(self) -> None:
        """Verify the rarity weight constants."""
        assert RARITY_WEIGHTS["common"] == 4
        assert RARITY_WEIGHTS["rare"] == 3
        assert RARITY_WEIGHTS["epic"] == 2
        assert RARITY_WEIGHTS["legendary"] == 1

    def test_unknown_rarity_gets_weight_1(self) -> None:
        """Unknown rarity defaults to weight 1."""
        artifacts = [
            FakeArtifact(id="u1", rarity="unknown"),
        ]
        result = select_raid_target_artifact(artifacts, rng=random.Random(42))
        assert result.id == "u1"

    def test_uses_system_random_when_no_rng(self) -> None:
        """When no RNG is provided, system random is used."""
        artifacts = [FakeArtifact(id="a1", rarity="common")]
        result = select_raid_target_artifact(artifacts)
        assert result is not None


# ---------------------------------------------------------------------------
# Tests — is_raid_on_cooldown
# ---------------------------------------------------------------------------


class TestIsRaidOnCooldown:
    """Tests for ``is_raid_on_cooldown``."""

    def test_none_timestamp_no_cooldown(self) -> None:
        """No previous raid means no cooldown."""
        on_cooldown, expires = is_raid_on_cooldown(None, 24)
        assert on_cooldown is False
        assert expires is None

    def test_expired_cooldown(self) -> None:
        """Cooldown is not active if enough time has passed."""
        past = datetime.now(timezone.utc) - timedelta(hours=25)
        on_cooldown, expires = is_raid_on_cooldown(past, 24)
        assert on_cooldown is False
        assert expires is None

    def test_active_cooldown(self) -> None:
        """Cooldown is active if not enough time has passed."""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        on_cooldown, expires = is_raid_on_cooldown(recent, 24)
        assert on_cooldown is True
        assert expires is not None
        # Expires should be ~23 hours from now
        assert expires > datetime.now(timezone.utc)

    def test_cooldown_just_expired(self) -> None:
        """Cooldown at exact boundary is not active."""
        exact = datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)
        on_cooldown, expires = is_raid_on_cooldown(exact, 24)
        assert on_cooldown is False

    def test_cooldown_just_started(self) -> None:
        """Cooldown that just started is active."""
        just_now = datetime.now(timezone.utc) - timedelta(seconds=1)
        on_cooldown, expires = is_raid_on_cooldown(just_now, 24)
        assert on_cooldown is True
        assert expires is not None

    def test_zero_hour_cooldown(self) -> None:
        """Zero-hour cooldown means any past raid is expired."""
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        on_cooldown, expires = is_raid_on_cooldown(past, 0)
        assert on_cooldown is False

    def test_cooldown_expires_at_correct_time(self) -> None:
        """The cooldown expiration timestamp is correct."""
        ts = datetime.now(timezone.utc) - timedelta(hours=10)
        on_cooldown, expires = is_raid_on_cooldown(ts, 24)
        assert on_cooldown is True
        expected_expires = ts + timedelta(hours=24)
        # Allow 1 second tolerance
        assert abs((expires - expected_expires).total_seconds()) < 1


# ---------------------------------------------------------------------------
# Tests — check_raid_protection (CardModifierEngine)
# ---------------------------------------------------------------------------


class TestCheckRaidProtection:
    """Tests for ``CardModifierEngine.check_raid_protection``."""

    def _make_engine(self, cards):
        from src.modules.cards.modifier_engine import CardModifierEngine

        return CardModifierEngine(cards)

    def _make_card(self, **kwargs):
        from src.modules.cards.modifier_types import CardModifierDef

        defaults = {
            "card_id": 1,
            "name": "Test Card",
            "trigger": "on_raid",
            "effect": "raid_protection",
            "effect_params": {},
            "trigger_condition": None,
            "tags": [],
        }
        defaults.update(kwargs)
        return CardModifierDef(**defaults)

    def test_no_cards_no_protection(self) -> None:
        """Empty engine provides no raid protection."""
        engine = self._make_engine([])
        blocked, applied = engine.check_raid_protection()
        assert blocked is False
        assert applied == []

    def test_full_protection_always_blocks(self) -> None:
        """Eternal Guardian (raid_protection) always blocks."""
        card = self._make_card(
            card_id=55,
            name="Eternal Guardian",
            effect="raid_protection",
            effect_params={"full_protection": True},
        )
        engine = self._make_engine([card])
        blocked, applied = engine.check_raid_protection(seed=0)
        assert blocked is True
        assert len(applied) == 1
        assert applied[0].card_name == "Eternal Guardian"
        assert applied[0].hook == "raid_protection"

    def test_full_protection_blocks_with_any_seed(self) -> None:
        """Full protection blocks regardless of RNG seed."""
        card = self._make_card(
            card_id=55,
            name="Eternal Guardian",
            effect="raid_protection",
            effect_params={"full_protection": True},
        )
        engine = self._make_engine([card])
        for seed in [0, 42, 99999, 1234567]:
            blocked, _ = engine.check_raid_protection(seed=seed)
            assert blocked is True

    def test_raid_block_succeeds_on_lucky_roll(self) -> None:
        """Resilient Shield blocks when roll is below block_chance."""
        card = self._make_card(
            card_id=30,
            name="Resilient Shield",
            effect="raid_block",
            effect_params={"block_chance": 0.50},
        )
        engine = self._make_engine([card])
        # Find a seed that produces a roll < 500 (50%).
        # LCG: (seed * 1103515245 + 12345) & 0x7FFFFFFF, then % 1000.
        # seed=0: (0 + 12345) & 0x7FFFFFFF = 12345, 12345 % 1000 = 345 < 500 → blocks
        blocked, applied = engine.check_raid_protection(seed=0)
        assert blocked is True
        assert applied[0].card_name == "Resilient Shield"

    def test_raid_block_fails_on_unlucky_roll(self) -> None:
        """Resilient Shield fails when roll exceeds block_chance."""
        card = self._make_card(
            card_id=30,
            name="Resilient Shield",
            effect="raid_block",
            effect_params={"block_chance": 0.50},
        )
        engine = self._make_engine([card])
        # seed=1: (1103515245 + 12345) & 0x7FFFFFFF = 1103527590, % 1000 = 590 >= 500 → fails
        blocked, applied = engine.check_raid_protection(seed=1)
        assert blocked is False
        assert applied == []

    def test_full_protection_takes_priority_over_block(self) -> None:
        """If both raid_protection and raid_block are equipped, full protection wins."""
        full = self._make_card(
            card_id=55,
            name="Eternal Guardian",
            effect="raid_protection",
            effect_params={"full_protection": True},
        )
        partial = self._make_card(
            card_id=30,
            name="Resilient Shield",
            effect="raid_block",
            effect_params={"block_chance": 0.50},
        )
        engine = self._make_engine([full, partial])
        blocked, applied = engine.check_raid_protection(seed=1)
        assert blocked is True
        assert applied[0].card_name == "Eternal Guardian"

    def test_unrelated_cards_no_protection(self) -> None:
        """Cards with other effects don't provide raid protection."""
        card = self._make_card(
            card_id=1,
            name="Some Other Card",
            effect="spawn_bias",
            effect_params={"gem_color": 1},
        )
        engine = self._make_engine([card])
        blocked, applied = engine.check_raid_protection()
        assert blocked is False
