"""RapidOCR (PaddleOCR text models on ONNX Runtime) with the same contract as win_ocr: one PNG
path per stdin line, one JSON line per image: {"words": [{"text","x","y","w","h","line","score"}]}.

Runs in its own venv (rapidocr 3.x), so the harness venv is untouched:
    <ocr-venv>/Scripts/python.exe -I scripts/adobe_observed_truth/rapid_ocr_server.py [setup]
`setup` picks the PaddleOCR models (see SETUPS; models download once from RapidAI's model
repository). Each recognised text line is split into words with boxes shared out by length.
"""

from __future__ import annotations

import json
import sys

# name -> (detection version, detection size, recognition version, recognition size, language)
SETUPS = {
    "v4-mobile": ("PP-OCRv4", "mobile", "PP-OCRv4", "mobile", "ch"),
    "v4-server": ("PP-OCRv4", "server", "PP-OCRv4", "server", "ch"),
    "v5-server": ("PP-OCRv5", "server", "PP-OCRv5", "server", "ch"),
    "v5-server-en": ("PP-OCRv5", "server", "PP-OCRv5", "mobile", "en"),
    "v5-mobile-en": ("PP-OCRv5", "mobile", "PP-OCRv5", "mobile", "en"),
    "v6-small": ("PP-OCRv6", "small", "PP-OCRv6", "small", "ch"),
    "v6-medium": ("PP-OCRv6", "medium", "PP-OCRv6", "medium", "ch"),
}
# Scored on an exact 40-dialog key (strict words, close-button glyph aside): v6-small 96.9% read /
# 96.9% right and it finds lone digits in fields; v4-mobile 95.4% / 97.5%; v6-medium 97.9% but
# 12 s per field read (v6-small 1.6 s).
DEFAULT_SETUP = "v6-small"


def engine(setup: str):
    from rapidocr import LangDet, LangRec, ModelType, OCRVersion, RapidOCR

    det_version, det_size, rec_version, rec_size, language = SETUPS[setup]
    version = {"PP-OCRv4": OCRVersion.PPOCRV4, "PP-OCRv5": OCRVersion.PPOCRV5, "PP-OCRv6": OCRVersion.PPOCRV6}
    size = {"mobile": ModelType.MOBILE, "server": ModelType.SERVER, "small": ModelType.SMALL, "medium": ModelType.MEDIUM}
    return RapidOCR(
        params={
            "Det.ocr_version": version[det_version],
            "Det.model_type": size[det_size],
            "Det.lang_type": LangDet.CH,
            "Rec.ocr_version": version[rec_version],
            "Rec.model_type": size[rec_size],
            "Rec.lang_type": LangRec.EN if language == "en" else LangRec.CH,
            "Global.log_level": "error",
        }
    )


def words_of(result) -> list[dict]:
    words = []
    if result is None or result.boxes is None:
        return words
    for index, (box, text, score) in enumerate(zip(result.boxes, result.txts, result.scores, strict=False)):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        total = max(1, len(text))
        cursor = 0
        for part in text.split():
            start = text.index(part, cursor)
            cursor = start + len(part)
            words.append(
                {
                    "text": part,
                    "x": round(x0 + (x1 - x0) * start / total),
                    "y": round(y0),
                    "w": round((x1 - x0) * len(part) / total),
                    "h": round(y1 - y0),
                    "line": index,
                    "score": round(float(score), 3),
                }
            )
    return words


def main() -> None:
    reader = engine(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SETUP)
    for raw in sys.stdin:
        path = raw.strip()
        if not path:
            continue
        try:
            answer = {"words": words_of(reader(path)), "error": None}
        except Exception as error:  # noqa: BLE001 - reported per image
            answer = {"words": [], "error": str(error)}
        print(json.dumps(answer), flush=True)


if __name__ == "__main__":
    main()
