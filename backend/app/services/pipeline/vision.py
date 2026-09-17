"""Optional visual check by a model.

No model client is wired in yet (and there is no LLM_API_KEY), so this is a safe no-op: the photo comes
back unchanged and nothing is invented. A future model must append a `vision` evidence with a moderate
weight and recompute via `scoring.finalize`, which keeps the honest-uncertainty cap: vision alone never
lifts a photo above `unconfirmed`.
"""

from app.models import Photo, RawImage


async def vision_check(raw: RawImage, photo: Photo) -> Photo:
    return photo
