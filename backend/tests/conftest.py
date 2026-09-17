import os

# Tests never load the CLIP model; vision verdicts are passed to score() directly (tests/pipeline/test_vision.py).
os.environ["VISION_ENABLED"] = "0"
