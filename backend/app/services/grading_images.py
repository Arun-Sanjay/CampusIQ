"""Image/PDF rasterization helpers for the AI auto-grader (PyMuPDF, no Pillow).

The single place that knows about pixels — keeps the base64 size risk contained.
Answer-sheet pages are rendered/downscaled here so every image handed to Claude
vision stays under the per-image byte cap (see claude_client.MAX_IMAGE_BYTES).
"""
from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF (already a dependency, used by text_extraction.py)

logger = logging.getLogger(__name__)

DEFAULT_DPI = 150  # sweet spot for handwriting legibility vs base64 size
MAX_LONG_EDGE_PX = 2200


def pdf_to_page_images(
    pdf: str | Path | bytes,
    *,
    dpi: int = DEFAULT_DPI,
    max_long_edge_px: int = MAX_LONG_EDGE_PX,
) -> list[bytes]:
    """Render each PDF page to a PNG byte string, downscaled to a bounded size.

    ``pdf`` may be a filesystem path or raw PDF bytes (uploaded files)."""
    out: list[bytes] = []
    if isinstance(pdf, (bytes, bytearray)):
        doc = fitz.open(stream=bytes(pdf), filetype="pdf")
    else:
        doc = fitz.open(str(pdf))
    try:
        zoom = dpi / 72.0
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            long_edge = max(pix.width, pix.height)
            if long_edge > max_long_edge_px:
                scale = max_long_edge_px / long_edge
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom * scale, zoom * scale))
            out.append(pix.tobytes("png"))
    finally:
        doc.close()
    return out


def normalize_image_bytes(raw: bytes, *, max_long_edge_px: int = MAX_LONG_EDGE_PX) -> bytes:
    """Re-encode an uploaded image to PNG, downscaled if its long edge exceeds the
    cap. Returns the original bytes unchanged if anything goes wrong (best-effort).
    """
    try:
        doc = fitz.open(stream=raw, filetype="image")
        try:
            page = doc[0]
            pix = page.get_pixmap()
            long_edge = max(pix.width, pix.height)
            if long_edge > max_long_edge_px:
                scale = max_long_edge_px / long_edge
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            return pix.tobytes("png")
        finally:
            doc.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("normalize_image_bytes failed, using raw: %s", e)
        return raw


def chunk_pages(pages: list, pages_per_student: int) -> list[list]:
    """Split a flat page list into fixed-size per-student bundles.

    Used for fixed-format answer booklets where every student's script is the
    same number of pages. ``pages_per_student <= 0`` → one bundle of everything.
    """
    if pages_per_student <= 0:
        return [list(pages)]
    return [pages[i : i + pages_per_student] for i in range(0, len(pages), pages_per_student)]
