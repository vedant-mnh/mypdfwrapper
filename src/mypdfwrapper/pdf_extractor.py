from pathlib import Path
import fitz
import pytesseract
from PIL import Image
import io


def extract_text(pdf_path: Path) -> str:
    """
    Handles:
    - Digital PDFs
    - Scanned PDFs
    - Mixed PDFs (page-level routing)
    """

    doc = fitz.open(str(pdf_path))
    full_text = []

    for i, page in enumerate(doc):

        # --- Detect per page ---
        page_text = page.get_text().strip()

        if page_text:
            # DIGITAL PAGE
            text = _extract_digital_page(page)
        else:
            # SCANNED PAGE
            text = _extract_scanned_page(page)

        full_text.append(f"\n--- Page {i+1} ---\n{text}")

    doc.close()
    return "\n".join(full_text)


# -------------------------------
# DIGITAL PDF (your existing logic)
# -------------------------------
def _extract_digital_page(page) -> str:
    page_text = []

    uri_rects = []
    for link in page.get_links():
        if link.get("kind") == fitz.LINK_URI:
            uri = link.get("uri", "").strip()
            if uri:
                uri_rects.append((fitz.Rect(link["from"]), uri))

    blocks = page.get_text(
        "blocks",
        flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_LIGATURES
    )
    blocks = sorted(blocks, key=lambda b: (round(b[1] / 10), b[0]))

    for block in blocks:
        if block[6] != 0:
            continue

        block_text = block[4].strip()
        if not block_text:
            continue

        block_rect = fitz.Rect(block[:4])
        words = sorted(
            page.get_text("words", clip=block_rect),
            key=lambda w: (w[5], w[6], w[7])
        )

        line_map = {}
        for x0, y0, x1, y1, word, block_no, line_no, word_no in words:
            line_map.setdefault((block_no, line_no), []).append(
                (word_no, word, fitz.Rect(x0, y0, x1, y1))
            )

        for key in sorted(line_map.keys()):
            line_parts = []
            for word_no, word, word_rect in sorted(line_map[key], key=lambda x: x[0]):
                matched_uris = [
                    uri for lrect, uri in uri_rects if word_rect.intersects(lrect)
                ]
                if matched_uris:
                    line_parts.append(word + "[" + ", ".join(dict.fromkeys(matched_uris)) + "]")
                else:
                    line_parts.append(word)

            page_text.append(" ".join(line_parts))

    return "\n".join(page_text)


# -------------------------------
# SCANNED PDF (OCR)
# -------------------------------
def _extract_scanned_page(page) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    return pytesseract.image_to_string(img)