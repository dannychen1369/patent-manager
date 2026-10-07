"""Text extraction for uploaded patent documents.

Strategy: try PyMuPDF's native text layer first (fast, exact, works for
text-based PDFs). If a page has no usable text layer (scanned PDF) or the
file is a plain image, fall back to local OCR via RapidOCR.
"""
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np

_ocr_engine = None

MIN_CHARS_PER_PAGE = 20  # below this, assume the page has no real text layer

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_engine = RapidOCR()
    return _ocr_engine


def _ocr_pixmap(pix: "fitz.Pixmap") -> str:
    engine = _get_ocr_engine()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    result, _ = engine(img)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def _ocr_image_file(path: Path) -> str:
    engine = _get_ocr_engine()
    result, _ = engine(str(path))
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in IMAGE_SUFFIXES:
        return _ocr_image_file(path)

    if suffix != ".pdf":
        raise ValueError(f"不支持的文件类型: {suffix}")

    doc = fitz.open(path)
    pages_text = []
    for page in doc:
        text = page.get_text().strip()
        if len(text) < MIN_CHARS_PER_PAGE:
            pix = page.get_pixmap(dpi=200)
            text = _ocr_pixmap(pix).strip()
        pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)
