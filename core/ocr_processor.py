"""
core/ocr_processor.py - PaddleOCR (PP-OCRv6) wrapper for ReceiptVault.

Keeps all OCR-specific code in one place so:
  - A PaddleOCR import failure only disables the Scan tab, not the whole GUI.
  - The receipt-field parsing heuristics (vendor / price / date regexes) are
    testable independently of the GUI event loop.
  - Both the web and GUI layers can import this the same way.

OCR model is loaded lazily on first call to scan_receipt() so that startup
time is not penalised on users who never scan a receipt.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy OCR engine  (imported only on first scan, guarded so the rest of the
# app keeps working even when paddleocr / paddlepaddle are not installed)
# ---------------------------------------------------------------------------

_ocr = None           
_ocr_device = None     

def _resolve_device() -> str:
    try:
        import paddle  # noqa: PLC0415 
    except ImportError:
        return "cpu"

    try:
        if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            return "gpu:0"
    except Exception:
        pass
    return "cpu"

def get_device_info() -> dict:
    device = _ocr_device if _ocr is not None else _resolve_device()
    return {
        "device": device,
        "using_gpu": device.startswith("gpu"),
        "initialized": _ocr is not None,
    }

def _get_ocr():
    global _ocr, _ocr_device
    if _ocr is None:
        try:
            from paddleocr import PaddleOCR  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Run:\n"
                "  pip install paddleocr paddlepaddle\n"
                "or re-run the launch script so it can install dependencies."
            ) from exc

        def _build(device: str):
            return PaddleOCR(
                ocr_version="PP-OCRv6",
                lang="en",
                device=device,
                use_doc_orientation_classify=True,
                use_doc_unwarping=True,
                use_textline_orientation=True,
                det_limit_side_len=2048,
                det_db_thresh=0.2,
                det_db_box_thresh=0.3,
                det_db_unclip_ratio=1.8,
                enable_mkldnn=False, 
            )

        device = _resolve_device()
        try:
            _ocr = _build(device)
            _ocr_device = device
        except Exception as exc:
            if device == "cpu":
                raise
            print(
                f"[ocr_processor] Could not start PaddleOCR on {device} "
                f"({exc!r}); falling back to CPU."
            )
            _ocr = _build("cpu")
            _ocr_device = "cpu"

        label = "NVIDIA GPU" if _ocr_device.startswith("gpu") else "CPU"
        print(f"[ocr_processor] OCR engine ready - running on {_ocr_device} ({label}).")
    return _ocr

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class OCRResult:
    """Parsed fields extracted from a single receipt image."""

    def __init__(
        self,
        vendor: str = "",
        price: str = "",
        date_str: str = "",
        raw_lines: list[str] | None = None,
    ):
        self.vendor = vendor
        self.price = price
        self.date_str = date_str          
        self.raw_lines: list[str] = raw_lines or []

    def __repr__(self) -> str:
        return (
            f"OCRResult(vendor={self.vendor!r}, price={self.price!r}, "
            f"date_str={self.date_str!r}, lines={len(self.raw_lines)})"
        )

def scan_receipt(image_path: str) -> OCRResult:
    import os
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    ocr = _get_ocr()
    result = ocr.ocr(image_path)

    if not result:
        return _parse_receipt_lines([])

    res_data = result[0] if isinstance(result, list) else result
    if not res_data:
        return _parse_receipt_lines([])
    
    if not isinstance(res_data, (dict, list)) and hasattr(res_data, '__dict__'):
        res_data = res_data.__dict__

    boxes: list[tuple[int, int, str]] = []  

    if isinstance(res_data, dict) or hasattr(res_data, 'keys'):
        polys = res_data.get('dt_polys', res_data.get('res', res_data.get('boxes', [])))
        texts = res_data.get('rec_texts', res_data.get('rec_text', res_data.get('texts', [])))
        
        if polys and texts:
            for poly, text_info in zip(polys, texts):
                text = text_info[0] if isinstance(text_info, (list, tuple)) else text_info
                if text and str(text).strip():
                    try:
                        x_min, y_min = int(poly[0][0]), int(poly[0][1])
                    except (IndexError, TypeError, ValueError):
                        x_min, y_min = 0, 0
                    boxes.append((y_min, x_min, str(text).strip()))
    
    elif isinstance(res_data, list):
        for line_data in res_data:
            if not line_data or len(line_data) < 2:
                continue
            
            box_coords = line_data[0]
            text_info = line_data[1]
            text = text_info[0] if isinstance(text_info, (list, tuple)) else text_info
            
            if text and str(text).strip():
                try:
                    x_min, y_min = int(box_coords[0][0]), int(box_coords[0][1])
                except (IndexError, TypeError, ValueError):
                    x_min, y_min = 0, 0
                boxes.append((y_min, x_min, str(text).strip()))
    
    boxes.sort(key=lambda b: (b[0], b[1]))
    lines = [b[2] for b in boxes]

    return _parse_receipt_lines(lines)

# ---------------------------------------------------------------------------
# Receipt field parsing heuristics
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    (r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4}|\d{2})\b', "MDY"),
    (r'\b(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b',     "YMD"),
    (r'\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b',      "MoNY"),
    (r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b',        "DMoY"),
]

_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}

# ── Price patterns ─────────────────────────────────────────────────────────
# Matches things like:  $12.34  12.34  $ 12.34  USD 12.34  TOTAL 1,234.56
# Now securely handles separated format (1,234.56) and unseparated (1234.56).
_PRICE_PATTERN = re.compile(r'(?:\$|USD|GBP|EUR|CAD|AUD)?\s*(\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|\d+[.,]\d{2})\b')

_TOTAL_KEYWORDS = re.compile(
    r'\b(total|subtotal|sub[- ]total|amount|due|balance|grand|sum)\b',
    re.IGNORECASE
)

# ── Vendor heuristics ──────────────────────────────────────────────────────
# \d{5} was removed from _ADDRESS_RE to prevent accidental vendor truncations.
_ADDRESS_RE = re.compile(
    r'\b(st\.?|ave\.?|blvd\.?|rd\.?|dr\.?|hwy\.?|suite|ste\.?|floor|fl\.?'
    r'|street|avenue|boulevard|road|drive|highway|lane|ln\.?|way|court|ct\.?'
    r'|place|pl\.?|circle|pkwy\.?|parkway)\b',
    re.IGNORECASE
)
_PHONE_RE   = re.compile(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}')
_URL_RE     = re.compile(r'(www\.|https?://|\.com|\.org|\.net)', re.IGNORECASE)

_FLUFF_RE   = re.compile(
    r'\b(give us|welcome to|thank you|thanks for|visit us|take our survey|'
    r'tell us|save money|live better|your cashier|store #|receipt|'
    r'customer copy|duplicate|how was your|feedback|returns)\b',
    re.IGNORECASE
)

def _try_parse_date(line: str) -> Optional[date]:
    for pattern, fmt in _DATE_PATTERNS:
        m = re.search(pattern, line, re.IGNORECASE)
        if not m:
            continue
        g = m.groups()
        try:
            if fmt == "MDY":
                mo, dy, yr = int(g[0]), int(g[1]), int(g[2])
                if yr < 100:
                    yr += 2000
                return date(yr, mo, dy)
            elif fmt == "YMD":
                yr, mo, dy = int(g[0]), int(g[1]), int(g[2])
                return date(yr, mo, dy)
            elif fmt == "MoNY":
                mo = _MONTH_NAMES.get(g[0].lower()[:3])
                if mo is None:
                    continue
                return date(int(g[2]), mo, int(g[1]))
            elif fmt == "DMoY":
                mo = _MONTH_NAMES.get(g[1].lower()[:3])
                if mo is None:
                    continue
                return date(int(g[2]), mo, int(g[0]))
        except ValueError:
            continue
    return None

def _parse_receipt_lines(lines: list[str]) -> OCRResult:
    vendor = ""
    price  = ""
    date_s = ""

    # ── 1. Date ───────────────────────────────────────────────────────────
    for line in lines:
        d = _try_parse_date(line)
        if d is not None:
            date_s = d.strftime("%m/%d/%Y")
            break

    # ── 2. Price ──────────────────────────────────────────────────────────
    best_total: Optional[float] = None
    best_total_str = ""
    largest: Optional[float] = None
    largest_str = ""

    for line in lines:
        m = _PRICE_PATTERN.search(line)
        if not m:
            continue
        
        raw = m.group(1)
        # Strip all thousands separators out securely before throwing to float()
        clean_str = re.sub(r'[.,]', '', raw[:-3]) + '.' + raw[-2:]
        try:
            val = float(clean_str)
        except ValueError:
            continue
            
        if val <= 0:
            continue
        if _TOTAL_KEYWORDS.search(line):
            if best_total is None or val > best_total:
                best_total = val
                best_total_str = f"{val:.2f}"
        if largest is None or val > largest:
            largest = val
            largest_str = f"{val:.2f}"

    price = best_total_str or largest_str

    # ── 3. Vendor ─────────────────────────────────────────────────────────
    candidate_lines = lines[:6]   
    for line in candidate_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 3:
            continue
        if _PHONE_RE.search(stripped):
            continue
        if _URL_RE.search(stripped):
            continue
        if _ADDRESS_RE.search(stripped):
            continue
        if _FLUFF_RE.search(stripped):
            continue
        if re.match(r'^[\d\s\-]+$', stripped):
            continue
        if _PRICE_PATTERN.fullmatch(stripped) or re.match(r'^\$?\s*\d+\.\d{2}$', stripped):
            continue
        if _try_parse_date(stripped) is not None:
            continue
        vendor = stripped
        break

    return OCRResult(vendor=vendor, price=price, date_str=date_s, raw_lines=lines)

# ---------------------------------------------------------------------------
# Utility: convert between the DB's YYYY-MM-DD and the UI's mm/dd/yyyy
# ---------------------------------------------------------------------------

def to_db_date(mmddyyyy: str) -> str:
    try:
        d = datetime.strptime(mmddyyyy.strip(), "%m/%d/%Y")
        return d.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Date must be in mm/dd/yyyy format, got: {mmddyyyy!r}")

def from_db_date(yyyymmdd: str) -> str:
    try:
        d = datetime.strptime(yyyymmdd.strip(), "%Y-%m-%d")
        return d.strftime("%m/%d/%Y")
    except ValueError:
        return yyyymmdd