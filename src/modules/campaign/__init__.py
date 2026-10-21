"""Campaign module — single-player obstacle-clearing progression.

Manages 100 campaign levels with escalating obstacles, checkpoint
rewards, and regression mechanics. Board generation uses the board
service's obstacle placement; move processing reuses the full
cascade pipeline.

Exports:
    CampaignService: Concrete service implementation.
    LevelLoader: Campaign level definitions cache.
"""

from src.modules.campaign.level_loader import LevelLoader
from src.modules.campaign.service import CampaignService

__all__ = [
    "CampaignService",
    "LevelLoader",
]
