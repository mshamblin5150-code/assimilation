"""PyMuPDF's OCR (Tesseract inside MuPDF) with the same contract as win_ocr and
rapid_ocr_server: one PNG path per stdin line, one JSON line per image:
{"words": [{"text","x","y","w","h","line"}], "error": null}.

Needs Tesseract's language data where TESSDATA_PREFIX points (scoop install tesseract, plus
eng.traineddata from tesseract-ocr/tessdata_best).
"""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    import pymupdf

    tessdata = os.environ.get("TESSDATA_PREFIX")
    for raw in sys.stdin:
        path = raw.strip()
        if not path:
            continue
        try:
            image = pymupdf.open(path)
            pdf = pymupdf.open("pdf", image.convert_to_pdf())
            page = pdf[0]
            # The PDF page is the image at 72 dpi: one point per pixel, so boxes are pixels.
            textpage = page.get_textpage_ocr(language="eng", dpi=72, full=True, tessdata=tessdata)
            words = [
                {
                    "text": text,
                    "x": round(x0),
                    "y": round(y0),
                    "w": round(x1 - x0),
                    "h": round(y1 - y0),
                    "line": line,
                }
                for x0, y0, x1, y1, text, _block, line, _word in page.get_text("words", textpage=textpage)
            ]
            answer = {"words": words, "error": None}
        except Exception as error:  # noqa: BLE001 - reported per image
            answer = {"words": [], "error": str(error)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
