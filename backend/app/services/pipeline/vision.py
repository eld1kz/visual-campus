"""Local OpenCLIP visual filtering, batched and bounded by the profile deadline."""

import asyncio
import io
import time
from pathlib import Path

import httpx
from PIL import Image

from app.config import settings
from app.models import Photo, RawImage

BATCH_SIZE = 8
DOWNLOAD_CONCURRENCY = 8
MODEL_NAME = "ViT-B-32"
HF_SNAPSHOT = Path.home() / ".cache/huggingface/hub/models--laion--CLIP-ViT-B-32-laion2B-s34B-b79K/snapshots"

PROMPTS = [
    ("campus", True, "a photo of a university campus building or outdoor campus grounds"),
    ("libraries", True, "a photo of a library reading room with shelves and desks"),
    ("classrooms", True, "a photo of a classroom or university lecture hall"),
    ("dorms", True, "a photo of a student dormitory building or dorm room"),
    (None, False, "a portrait or group photo of people posing"),
    (None, False, "a ceremony conference speech or crowded event"),
    (None, False, "a close up photo of a car sign document poster book or logo"),
    (None, False, "an engraving drawing scan historical document or artwork"),
    (None, False, "a close up photo of an object specimen experiment food or laboratory equipment"),
]

_model = None
_preprocess = None
_text_features = None
_cache: dict[str, tuple[float, str | None, int, str | None, tuple[float, ...]]] = {}
_model_lock: asyncio.Lock | None = None


def _weights_path() -> Path | None:
    if not HF_SNAPSHOT.exists():
        return None
    return next(HF_SNAPSHOT.glob("*/open_clip_model.safetensors"), None)


def _load_model():
    global _model, _preprocess, _text_features
    if _model is not None:
        return _model, _preprocess, _text_features
    path = _weights_path()
    if path is None:
        raise FileNotFoundError("OpenCLIP weights are not cached")
    import open_clip
    import torch

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=str(path))
    model.eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    with torch.inference_mode():
        text_features = model.encode_text(tokenizer([prompt for _, _, prompt in PROMPTS]))
        text_features /= text_features.norm(dim=-1, keepdim=True)
    _model, _preprocess, _text_features = model, preprocess, text_features
    return _model, _preprocess, _text_features


def _classify(contents: list[bytes]) -> list[tuple[str | None, int, str | None, tuple[float, ...]] | None]:
    import torch

    model, preprocess, text_features = _load_model()
    tensors, positions = [], []
    results: list[tuple[str | None, int, str | None, tuple[float, ...]] | None] = [None] * len(contents)
    for index, content in enumerate(contents):
        try:
            with Image.open(io.BytesIO(content)) as image:
                tensors.append(preprocess(image.convert("RGB")))
                positions.append(index)
        except Exception:
            continue
    if not tensors:
        return results
    with torch.inference_mode():
        image_features = model.encode_image(torch.stack(tensors))
        image_features /= image_features.norm(dim=-1, keepdim=True)
        similarities = image_features @ text_features.T
    for pos, row, embedding in zip(positions, similarities, image_features):
        positive_index = int(row[:4].argmax())
        negative_index = 4 + int(row[4:].argmax())
        positive, negative = float(row[positive_index]), float(row[negative_index])
        if negative > positive + 0.015:
            verdict = ("Visual check: likely not a campus place", -30, None)
        elif positive > negative + 0.015:
            category = PROMPTS[positive_index][0]
            verdict = ("Visual check: campus place", 12, category if category != "campus" else None)
        else:
            verdict = ("Visual check: scene is ambiguous", 0, None)
        results[pos] = (*verdict, tuple(float(value) for value in embedding.tolist()))
    return results


def embedding_for_url(url: str) -> tuple[float, ...] | None:
    cached = _cache.get(url)
    return cached[4] if cached and time.monotonic() - cached[0] < 7 * 86400 else None


async def batch_vision_check(
    items: list[tuple[RawImage, Photo]], client: httpx.AsyncClient, budget_s: float
) -> dict[str, RawImage]:
    if not settings.vision_enabled or budget_s <= 1:
        return {}
    candidates = [(raw, photo) for raw, photo in items if raw.thumb_url or raw.full_url][
        : settings.vision_max_candidates
    ]
    if not candidates:
        return {}
    global _model_lock
    if _model_lock is None:
        _model_lock = asyncio.Lock()
    deadline = time.monotonic() + budget_s
    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)

    async def download(raw: RawImage) -> bytes | None:
        cached = _cache.get(raw.full_url)
        if cached and time.monotonic() - cached[0] < 7 * 86400:
            return b""
        try:
            async with semaphore:
                response = await client.get(
                    raw.thumb_url or raw.full_url,
                    timeout=min(3.0, max(0.5, deadline - time.monotonic())),
                )
            response.raise_for_status()
            return response.content
        except Exception:
            return None

    updated: dict[str, RawImage] = {}
    async with _model_lock:
        for start in range(0, len(candidates), BATCH_SIZE):
            if time.monotonic() >= deadline - 0.5:
                break
            chunk = candidates[start:start + BATCH_SIZE]
            contents = await asyncio.gather(*(download(raw) for raw, _ in chunk))
            positions, new_contents = [], []
            for index, ((raw, _), content) in enumerate(zip(chunk, contents)):
                cached = _cache.get(raw.full_url)
                if content == b"" and cached:
                    _, label, weight, category, _ = cached
                    updated[raw.id] = raw.model_copy(update={
                        "vision_checked": True, "vision_label": label,
                        "vision_weight": weight, "vision_category": category,
                    })
                elif content:
                    positions.append(index)
                    new_contents.append(content)
            if new_contents:
                classified = await asyncio.to_thread(_classify, new_contents)
                for chunk_index, result in zip(positions, classified):
                    if result is None:
                        continue
                    raw = chunk[chunk_index][0]
                    label, weight, category, embedding = result
                    _cache[raw.full_url] = (time.monotonic(), label, weight, category, embedding)
                    updated[raw.id] = raw.model_copy(update={
                        "vision_checked": True, "vision_label": label,
                        "vision_weight": weight, "vision_category": category,
                    })
    return updated


async def vision_check(raw: RawImage, photo: Photo) -> Photo:
    """Compatibility entry point; a network-free single check leaves the photo unchanged."""
    return photo
