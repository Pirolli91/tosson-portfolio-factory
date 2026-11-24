"""64-bit perceptual difference hash (dHash) using Pillow only (no numpy/ML)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def compute_dhash(image_path: Path | str, hash_size: int = 8) -> str:
    """Compute a 64-bit (for hash_size=8) dHash hex digest using Pillow.

    Steps:
    1. Convert image to 8-bit grayscale (`L`).
    2. Resize to `(hash_size + 1, hash_size)` -> `(9, 8)`.
    3. Compare adjacent horizontal pixels `left > right` across all 8 rows.
    """
    path = Path(image_path)
    with Image.open(path) as img:
        gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        if hasattr(gray, "get_flattened_data"):
            pixels = list(gray.get_flattened_data())
        else:  # pragma: no cover - Pillow < 12 fallback
            pixels = list(gray.getdata())

    width = hash_size + 1
    bits = 0
    for row in range(hash_size):
        row_offset = row * width
        for col in range(hash_size):
            left = pixels[row_offset + col]
            right = pixels[row_offset + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)

    hex_width = (hash_size * hash_size) // 4
    return f"{bits:0{hex_width}x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Return bit-level Hamming distance between two hex dHash strings."""
    if len(hash_a) != len(hash_b):
        raise ValueError(f"Hash lengths differ: {len(hash_a)} vs {len(hash_b)}")
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()
