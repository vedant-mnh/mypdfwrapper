from pathlib import Path
import fitz


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
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
                line_map.setdefault((block_no, line_no), []).append((word_no, word, fitz.Rect(x0, y0, x1, y1)))

            line_strings = []
            for key in sorted(line_map.keys()):
                line_parts = []
                for word_no, word, word_rect in sorted(line_map[key], key=lambda x: x[0]):
                    matched_uris = [uri for lrect, uri in uri_rects if word_rect.intersects(lrect)]
                    if matched_uris:
                        line_parts.append(word + "[" + ", ".join(dict.fromkeys(matched_uris)) + "]")
                    else:
                        line_parts.append(word)
                line_strings.append(" ".join(line_parts))

            full_text.append("\n".join(line_strings))

    doc.close()
    return "\n\n".join(full_text)