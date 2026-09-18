"""Verification pipeline: RawImage → scored, categorized, deduplicated Photo (docs/CONTRACT.md §6)."""

from app.services.pipeline.dedupe import Deduplicator
from app.services.pipeline.scoring import CampusContext, score
from app.services.pipeline.vision import batch_vision_check, vision_check

__all__ = ["CampusContext", "Deduplicator", "score", "vision_check", "batch_vision_check"]
