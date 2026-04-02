from pathlib import Path
import fitz
import pytesseract
from PIL import Image
import io


def extract_text(pdf_path: Path) -> str:
    """
    Single entry point:
    - Handles both text PDFs and scanned PDFs
    """

    doc = fitz.open(str(pdf_path))

    # --- Step 1: Detect if scanned ---
    is_scanned = True
    for page in doc:
        if page.get_text().strip():
            is_scanned = False
            break

    # --- Step 2: Route ---
    if is_scanned:
        text = _extract_scanned(doc)
    else:
        text = _extract_digital(doc)

    doc.close()
    return text


# -------------------------------
# DIGITAL PDF (your existing logic)
# -------------------------------
def _extract_digital(doc) -> str:
    full_text = []

    for page in doc:
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

            line_strings = []
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
                line_strings.append(" ".join(line_parts))

            full_text.append("\n".join(line_strings))

    return "\n\n".join(full_text)


# -------------------------------
# SCANNED PDF (OCR)
# -------------------------------
def _extract_scanned(doc) -> str:
    full_text = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        text = pytesseract.image_to_string(img)

        full_text.append(f"\n--- Page {i+1} ---\n{text}")

    return "\n".join(full_text)