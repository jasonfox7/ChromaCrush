"""Collection tracking helpers.

Pure function for calculating artifact set completion progress.
No database access or service dependencies.
"""

from __future__ import annotations

from src.modules.vault.dto import CollectionProgress


def calculate_collection_progress(
    owned_type_ids: list[str],
    set_type_ids: list[str],
    set_name: str,
    artifact_set: str,
) -> CollectionProgress:
    """Calculate progress toward completing an artifact set.

    Args:
        owned_type_ids: Type IDs the player owns (may include IDs
            outside this set -- they are filtered out).
        set_type_ids: All type IDs that belong to the set.
        set_name: Display name of the set.
        artifact_set: Set identifier key.

    Returns:
        CollectionProgress instance with owned/missing breakdowns.
    """
    owned_set = set(owned_type_ids)
    total_set = set(set_type_ids)

    owned_in_set = owned_set & total_set
    missing = total_set - owned_set

    return CollectionProgress(
        artifact_set=artifact_set,
        set_name=set_name,
        total_in_set=len(total_set),
        owned_count=len(owned_in_set),
        owned_type_ids=sorted(owned_in_set),
        missing_type_ids=sorted(missing),
    )
