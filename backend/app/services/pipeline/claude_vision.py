"""Batched Claude visual check for the photos whose tier a visual verdict can still change.

It runs in parallel with OpenCLIP and its verdicts are applied after it. Claude looks at the borderline candidates: photos just below
a tier threshold (typically 44-59 points, "Not visually checked" or inconclusive) with at least one positive place
signal. A confident Claude verdict replaces the OpenCLIP one; any failure leaves the OpenCLIP result in place.
"""

import asyncio
import base64
import io
import json
import logging
import time

import anthropic
import httpx
from PIL import Image

from app.config import settings
from app.models import Photo, RawImage

logger = logging.getLogger("visual_campus.claude_vision")

MODEL = "claude-haiku-4-5"  # fastest and cheapest; Haiku 4.5 takes no `effort` setting
BATCH_SIZE = 5  # images per request
PARALLEL_REQUESTS = 16
MAX_SIDE_PX = 512  # ~350 input tokens per image
DOWNLOAD_CONCURRENCY = 12
MIN_CONFIDENCE = 44  # below this even a positive verdict cannot reach "likely"

W_POSITIVE = 16  # Claude is far more reliable than OpenCLIP (+12)
W_NEGATIVE = -20
POSITIVE_FROM = 70  # model's own confidence needed to count as a verdict
VETO_FROM = 90  # "not a photo" (chart, logo, screenshot, document) this sure: never above unconfirmed

LABELS = ["campus_place", "building_interior", "people_or_event", "object_or_sample", "not_a_photo", "unrelated_place"]
CATEGORIES = ["campus", "dorms", "classrooms", "libraries", "city"]
SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "label": {"type": "string", "enum": LABELS},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "confidence": {"type": "integer"},
                },
                "required": ["i", "label", "category", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}
PROMPT = (
    "You check photos for a university campus guide about {name}. For each numbered image decide what it shows:\n"
    "- campus_place: buildings, grounds, streets, entrances, sports fields or views of a university campus\n"
    "- building_interior: a room inside a university building (lecture hall, library, lab room, dorm room, lobby)\n"
    "- people_or_event: people are the subject (portraits, ceremonies, meetings, group photos)\n"
    "- object_or_sample: a close-up object, specimen, equipment, food, animal or plant\n"
    "- not_a_photo: logo, chart, map, screenshot, document, poster, drawing\n"
    "- unrelated_place: a real place that is clearly not a university campus (nature, shops, a highway)\n"
    "category: campus, dorms, classrooms (lecture halls, labs, teaching buildings), libraries, or city (off-campus "
    "town views). confidence: 0-100, how sure you are of the label. You cannot tell which university it is from the "
    "image alone; judge only whether it shows a campus place. Return one result per image, i = image number."
)

_client: anthropic.AsyncAnthropic | None = None
_cache: dict[str, tuple[float, dict]] = {}  # full_url -> (time, verdict)


def candidates(items: list[tuple[RawImage, Photo]], limit: int) -> list[tuple[RawImage, Photo]]:
    """Photos a visual verdict can still move across a tier: borderline, with a positive place signal."""
    picked = []
    for raw, photo in items:
        if raw.vision_veto or not (raw.thumb_url or raw.full_url) or photo.confidence < MIN_CONFIDENCE:
            continue
        if raw.vision_label == "campus_place" and photo.tier == "verified":
            continue  # nothing left to gain
        if not any(e.type in ("geo", "category", "text") and e.weight > 0 for e in photo.evidence):
            continue
        picked.append((raw, photo))
    picked.sort(key=lambda pair: (pair[1].freshness == "2024_plus", pair[1].confidence), reverse=True)
    return picked[:limit]


def apply(raw: RawImage, verdict: dict) -> RawImage:
    """Map one Claude result onto the shared vision fields; a low-confidence answer means inconclusive."""
    label, sure = verdict["label"], verdict["confidence"]
    category = verdict["category"] if verdict["category"] in ("classrooms", "libraries") else None
    if label in ("campus_place", "building_interior") and sure >= POSITIVE_FROM:
        update = {"vision_label": "campus_place", "vision_weight": W_POSITIVE, "vision_veto": False,
                  "vision_category": category}
    elif label not in ("campus_place", "building_interior") and sure >= POSITIVE_FROM:
        update = {"vision_label": "not_campus_place", "vision_weight": W_NEGATIVE,
                  "vision_veto": label == "not_a_photo" and sure >= VETO_FROM, "vision_category": None}
    else:
        update = {"vision_label": "inconclusive", "vision_weight": 0, "vision_veto": False, "vision_category": None}
    return raw.model_copy(update={"vision_checked": True, "vision_source": "claude", **update})


def _jpeg(content: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image = image.convert("RGB")
            image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=80)
    except Exception:
        return None
    return base64.standard_b64encode(out.getvalue()).decode()


async def _ask(images: list[str], name: str) -> list[dict]:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key, max_retries=0)
    content: list[dict] = []
    for index, data in enumerate(images, start=1):
        content.append({"type": "text", "text": f"Image {index}:"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    content.append({"type": "text", "text": PROMPT.format(name=name)})
    response = await _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Claude vision stopped: {response.stop_reason}")
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)["results"]


async def claude_vision_check(
    items: list[tuple[RawImage, Photo]], name: str, client: httpx.AsyncClient, budget_s: float, limit: int
) -> dict[str, RawImage]:
    if not settings.llm_api_key or budget_s <= 2 or limit <= 0:
        return {}
    picked = candidates(items, limit)
    if not picked:
        return {}
    deadline = time.monotonic() + budget_s
    updated: dict[str, RawImage] = {}
    todo: list[RawImage] = []
    for raw, _ in picked:
        cached = _cache.get(raw.full_url)
        if cached and time.monotonic() - cached[0] < 7 * 86400:
            updated[raw.id] = apply(raw, cached[1])
        else:
            todo.append(raw)

    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)

    async def download(raw: RawImage) -> str | None:
        try:
            async with semaphore:
                response = await client.get(raw.thumb_url or raw.full_url,
                                            timeout=min(3.0, max(0.5, deadline - time.monotonic() - 3)))
            response.raise_for_status()
        except Exception:
            return None
        return await asyncio.to_thread(_jpeg, response.content)

    images = await asyncio.gather(*(download(raw) for raw in todo))
    ready = [(raw, data) for raw, data in zip(todo, images) if data]
    batches = [ready[start:start + BATCH_SIZE] for start in range(0, len(ready), BATCH_SIZE)]
    request_slots = asyncio.Semaphore(PARALLEL_REQUESTS)

    async def run(batch: list[tuple[RawImage, str]]) -> None:
        async with request_slots:
            left = deadline - time.monotonic()
            if left < 2:
                return
            try:
                results = await asyncio.wait_for(_ask([data for _, data in batch], name), timeout=left)
            except Exception as exc:  # the OpenCLIP verdict stays
                logger.warning("Claude vision batch of %d failed: %s", len(batch), exc)
                return
        for result in results:
            index = result.get("i", 0) - 1
            if 0 <= index < len(batch):
                raw = batch[index][0]
                _cache[raw.full_url] = (time.monotonic(), result)
                updated[raw.id] = apply(raw, result)

    await asyncio.gather(*(run(batch) for batch in batches))
    logger.info("claude_vision candidates=%d downloaded=%d checked=%d in %.1f s",
                len(picked), len(ready), len(updated), budget_s - (deadline - time.monotonic()))
    return updated
