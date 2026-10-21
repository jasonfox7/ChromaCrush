"""Special gems module -- pure, synchronous effect calculation."""

from src.modules.special_gems.protocols import SpecialGemsServiceProtocol
from src.modules.special_gems.service import SpecialGemsService
from src.modules.special_gems.types import (
    SPECIAL_GEM_TYPES,
    FusionEffect,
    FusionType,
    SpecialGemEffect,
)

__all__ = [
    "SpecialGemsService",
    "SpecialGemsServiceProtocol",
    "SpecialGemEffect",
    "FusionEffect",
    "FusionType",
    "SPECIAL_GEM_TYPES",
]
