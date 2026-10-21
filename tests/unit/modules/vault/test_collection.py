"""Unit tests for vault collection tracking helpers.

Tests the pure ``calculate_collection_progress`` function.
"""

from __future__ import annotations

import pytest

from src.modules.vault.collection import calculate_collection_progress


class TestCalculateCollectionProgress:
    """Tests for ``calculate_collection_progress``."""

    def test_empty_set_all_owned(self) -> None:
        """Empty set (0 type IDs) counts as complete."""
        progress = calculate_collection_progress(
            owned_type_ids=[],
            set_type_ids=[],
            set_name="Empty Set",
            artifact_set="empty",
        )
        assert progress.is_complete is True
        assert progress.completion_percent == 100.0
        assert progress.total_in_set == 0
        assert progress.owned_count == 0

    def test_no_owned_items(self) -> None:
        """Player owns nothing from the set."""
        progress = calculate_collection_progress(
            owned_type_ids=[],
            set_type_ids=["a", "b", "c"],
            set_name="Fire Set",
            artifact_set="fire",
        )
        assert progress.is_complete is False
        assert progress.owned_count == 0
        assert progress.total_in_set == 3
        assert progress.completion_percent == 0.0
        assert len(progress.missing_type_ids) == 3
        assert len(progress.owned_type_ids) == 0

    def test_partial_progress(self) -> None:
        """Player owns some but not all items in the set."""
        progress = calculate_collection_progress(
            owned_type_ids=["a", "c"],
            set_type_ids=["a", "b", "c", "d"],
            set_name="Water Set",
            artifact_set="water",
        )
        assert progress.is_complete is False
        assert progress.owned_count == 2
        assert progress.total_in_set == 4
        assert progress.completion_percent == 50.0
        assert sorted(progress.owned_type_ids) == ["a", "c"]
        assert sorted(progress.missing_type_ids) == ["b", "d"]

    def test_complete_set(self) -> None:
        """Player owns all items in the set."""
        progress = calculate_collection_progress(
            owned_type_ids=["x", "y", "z"],
            set_type_ids=["x", "y", "z"],
            set_name="Earth Set",
            artifact_set="earth",
        )
        assert progress.is_complete is True
        assert progress.owned_count == 3
        assert progress.total_in_set == 3
        assert progress.completion_percent == 100.0
        assert len(progress.missing_type_ids) == 0

    def test_extra_owned_items_ignored(self) -> None:
        """Owned items not in the set are ignored."""
        progress = calculate_collection_progress(
            owned_type_ids=["a", "b", "c", "extra1", "extra2"],
            set_type_ids=["a", "b", "c"],
            set_name="Wind Set",
            artifact_set="wind",
        )
        assert progress.is_complete is True
        assert progress.owned_count == 3
        assert progress.total_in_set == 3
        assert "extra1" not in progress.owned_type_ids
        assert "extra2" not in progress.owned_type_ids

    def test_duplicate_owned_type_ids(self) -> None:
        """Duplicate owned IDs are deduplicated (set operation)."""
        progress = calculate_collection_progress(
            owned_type_ids=["a", "a", "b", "b"],
            set_type_ids=["a", "b", "c"],
            set_name="Ice Set",
            artifact_set="ice",
        )
        assert progress.owned_count == 2
        assert progress.total_in_set == 3
        assert sorted(progress.missing_type_ids) == ["c"]

    def test_set_name_and_artifact_set_stored(self) -> None:
        """The set_name and artifact_set fields are correctly stored."""
        progress = calculate_collection_progress(
            owned_type_ids=[],
            set_type_ids=["a"],
            set_name="Thunder Collection",
            artifact_set="thunder_v1",
        )
        assert progress.set_name == "Thunder Collection"
        assert progress.artifact_set == "thunder_v1"

    def test_single_item_set_complete(self) -> None:
        """Single-item set that is complete."""
        progress = calculate_collection_progress(
            owned_type_ids=["only"],
            set_type_ids=["only"],
            set_name="Singleton",
            artifact_set="single",
        )
        assert progress.is_complete is True
        assert progress.completion_percent == 100.0

    def test_single_item_set_missing(self) -> None:
        """Single-item set that is not yet owned."""
        progress = calculate_collection_progress(
            owned_type_ids=[],
            set_type_ids=["only"],
            set_name="Singleton",
            artifact_set="single",
        )
        assert progress.is_complete is False
        assert progress.completion_percent == 0.0
        assert progress.missing_type_ids == ["only"]

    def test_large_set_partial(self) -> None:
        """Large set with partial completion."""
        set_ids = [f"item_{i}" for i in range(100)]
        owned = [f"item_{i}" for i in range(33)]

        progress = calculate_collection_progress(
            owned_type_ids=owned,
            set_type_ids=set_ids,
            set_name="Mega Set",
            artifact_set="mega",
        )
        assert progress.owned_count == 33
        assert progress.total_in_set == 100
        assert progress.completion_percent == 33.0
        assert len(progress.missing_type_ids) == 67
