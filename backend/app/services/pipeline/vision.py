"""Visual check with a local CLIP model (open_clip, CPU): is the thumbnail a photo of a place or of something else?

Zero-shot: the image is compared with text prompts for places (building exterior, campus grounds, library reading
room, …) and non-places (portrait, car, document, engraving, object close-up, …). The share of probability that
falls on place prompts is `place_prob`. On a hand-labeled set of 101 Commons files (Cambridge, SNU, Nazarbayev)
0.5 kept 28/30 places and let through 4/71 non-places.

No network: the model weights are downloaded once by open_clip and cached. If open_clip/torch are missing or
VISION_ENABLED=0, `classify` returns None for every image and scoring works on metadata alone.
"""

import asyncio
import io
import logging
import threading
from dataclasses import dataclass

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
BATCH = 32

# key → (prompt, kind). No "dormitory" prompt: on real profiles it matched any plain building (punts on the Cam,
# a sports club), so dorms stay a metadata/text category.
PROMPTS: dict[str, tuple[str, str]] = {
    "building": ("a photo of a university building exterior", "place"),
    "campus": ("a photo of a campus with buildings, trees and paths", "place"),
    "aerial": ("an aerial photo of a university campus", "place"),
    "gate": ("a photo of a university main gate or entrance", "place"),
    "library": ("a photo of a library reading room", "place"),
    "classroom": ("a photo of a lecture hall or classroom", "place"),
    "sport": ("a photo of a sports stadium or gym", "place"),
    "interior": ("a photo of a large atrium or hallway inside a building", "place"),
    "cafeteria": ("a photo of a university cafeteria", "place"),
    "portrait": ("a portrait photo of a person", "other"),
    "event": ("a photo of people at a meeting, lecture or ceremony", "other"),
    "group": ("a group photo of people", "other"),
    "car": ("a photo of a car", "other"),
    "sign": ("a photo of a sign, plaque or text", "other"),
    "document": ("a photo of a document, book or manuscript", "other"),
    "artwork": ("an old engraving, drawing or painting", "other"),
    "chart": ("a chart, diagram or screenshot", "other"),
    "object": ("a close-up photo of an object", "other"),
    "statue": ("a photo of a statue or sculpture", "other"),
    "nature": ("a close-up photo of an insect, animal or plant", "other"),
    "lab_people": ("a photo of scientists working in a laboratory", "other"),
    "lab_equipment": ("a photo of laboratory equipment", "other"),
    "logo": ("a logo", "other"),
}
_KEYS = list(PROMPTS)
_PLACE = [i for i, k in enumerate(_KEYS) if PROMPTS[k][1] == "place"]


@dataclass(frozen=True)
class VisionResult:
    place_prob: float  # 0..1: probability mass on place prompts
    top: str  # key of the most likely prompt


class _Clip:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._model = None

    def _load(self) -> bool:
        with self._lock:
            if self._loaded:
                return self._model is not None
            self._loaded = True
            try:
                import open_clip
                import torch

                model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED)
                model.eval()
                tokenizer = open_clip.get_tokenizer(MODEL)
                with torch.no_grad():
                    text = model.encode_text(tokenizer([PROMPTS[k][0] for k in _KEYS]))
                    text /= text.norm(dim=-1, keepdim=True)
                self._model, self._preprocess, self._text, self._torch = model, preprocess, text, torch
                logger.info("CLIP %s/%s loaded", MODEL, PRETRAINED)
            except Exception:  # noqa: BLE001 — no model means metadata-only scoring, never a broken profile
                logger.exception("CLIP model unavailable; photos are scored without a visual check")
            return self._model is not None

    def classify(self, contents: list[bytes]) -> list[VisionResult | None]:
        if not contents or not self._load():
            return [None] * len(contents)
        tensors, index = [], []
        for i, content in enumerate(contents):
            try:
                with Image.open(io.BytesIO(content)) as image:
                    tensors.append(self._preprocess(image.convert("RGB")))
                index.append(i)
            except Exception:  # noqa: BLE001 — unreadable image: no verdict for it
                continue
        results: list[VisionResult | None] = [None] * len(contents)
        torch = self._torch
        for start in range(0, len(tensors), BATCH):
            with torch.no_grad():
                features = self._model.encode_image(torch.stack(tensors[start:start + BATCH]))
                features /= features.norm(dim=-1, keepdim=True)
                probs = (100.0 * features @ self._text.T).softmax(dim=-1)
            for row, i in zip(probs, index[start:start + BATCH]):
                results[i] = VisionResult(place_prob=round(float(row[_PLACE].sum()), 3), top=_KEYS[int(row.argmax())])
        return results


_clip = _Clip()
_semaphore = asyncio.Semaphore(1)  # one inference at a time: torch already uses all cores


async def classify(contents: list[bytes]) -> list[VisionResult | None]:
    """Verdicts in the same order as `contents`; None where the image could not be judged."""
    if not settings.vision_enabled:
        return [None] * len(contents)
    async with _semaphore:
        return await asyncio.to_thread(_clip.classify, contents)


async def warm_up() -> None:
    """Load the model in the background at startup, so the first profile does not wait ~5–20 s."""
    if settings.vision_enabled:
        await asyncio.to_thread(_clip._load)  # noqa: SLF001
