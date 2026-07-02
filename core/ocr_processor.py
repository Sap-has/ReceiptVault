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

_ocr = None   # module-level cache; None means "not yet initialised"


def _get_ocr():
    """Return the shared PaddleOCR instance, creating it on first call."""
    global _ocr
    if _ocr is None:
        try:
            from paddleocr import PaddleOCR  # noqa: PLC0415 (lazy import is intentional)
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Run:\n"
                "  pip install paddleocr paddlepaddle\n"
                "or re-run the launch script so it can install dependencies."
            ) from exc

        # PP-OCRv6_medium – Configured for Maximum Accuracy on Receipts.
        # Speed and memory usage are deprioritized in favor of handling 
        # faded ink, crumpled paper, skewed angles, and poor lighting.
        _ocr = PaddleOCR(
            # Default on Jul 2, 2026 is PP-OCRvy_medium
            ocr_version="PP-OCRv6",
            lang="en",
            
            # --- 1. Geometric & Document Preprocessing ---
            # Corrects upside-down or rotated images
            use_doc_orientation_classify=True,
            # Corrects curved/crumpled receipts (vital for handheld photos)
            use_doc_unwarping=True,
            # Detects and corrects individual text lines that are skewed
            use_textline_orientation=True,

            # --- 2. High-Fidelity Detection Limits ---
            # Default is 960. Receipts are often long; a higher limit prevents 
            # downscaling that destroys small or fine printed text.
            det_limit_side_len=2048,

            # --- 3. Thresholding for Faded/Thermal Ink ---
            # Lowering the binarization threshold (default 0.3) helps capture 
            # faint, faded ink on thermal paper in poor lighting.
            det_db_thresh=0.2,
            # Lowering the box threshold (default 0.6) prevents discarding 
            # bounding boxes that are faint/low-contrast.
            det_db_box_thresh=0.3,
            # Slightly expand bounding boxes (default ~1.5) to prevent edge 
            # characters (like the last digit of a price) from being clipped.
            det_db_unclip_ratio=1.8,

            enable_mkldnn=False, # Kept getting issues, this worked
        )
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
        self.date_str = date_str          # mm/dd/yyyy string for the UI field
        self.raw_lines: list[str] = raw_lines or []

    def __repr__(self) -> str:
        return (
            f"OCRResult(vendor={self.vendor!r}, price={self.price!r}, "
            f"date_str={self.date_str!r}, lines={len(self.raw_lines)})"
        )


def scan_receipt(image_path: str) -> OCRResult:
    """
    Run PP-OCRv6 on *image_path* and return an OCRResult with the best
    guesses at vendor, price, and date.

    Raises RuntimeError if PaddleOCR is not installed.
    Raises FileNotFoundError if the image file does not exist.
    """
    import os
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    ocr = _get_ocr()
    result = ocr.ocr(image_path)

    if not result:
        return _parse_receipt_lines([])

    # PaddleOCR can return a single object/dict or a list depending on version
    res_data = result[0] if isinstance(result, list) else result
    if not res_data:
        return _parse_receipt_lines([])
    
    # Convert custom Paddle objects to dict if necessary
    if not isinstance(res_data, (dict, list)) and hasattr(res_data, '__dict__'):
        res_data = res_data.__dict__

    boxes: list[tuple[int, int, str]] = []   # (y_min, x_min, text) for sorting

    # -- Strategy 1: Dictionary Output (Newer PaddleX / PP-OCRv6) --
    if isinstance(res_data, dict) or hasattr(res_data, 'keys'):
        # Fallbacks for various PaddleOCR dictionary keys
        polys = res_data.get('dt_polys', res_data.get('res', res_data.get('boxes', [])))
        texts = res_data.get('rec_texts', res_data.get('rec_text', res_data.get('texts', [])))
        
        if polys and texts:
            # Pair coordinates and text together
            for poly, text_info in zip(polys, texts):
                text = text_info[0] if isinstance(text_info, (list, tuple)) else text_info
                if text and str(text).strip():
                    try:
                        x_min, y_min = int(poly[0][0]), int(poly[0][1])
                    except (IndexError, TypeError, ValueError):
                        x_min, y_min = 0, 0
                    boxes.append((y_min, x_min, str(text).strip()))
    
    # -- Strategy 2: Classic Nested List Output --
    elif isinstance(res_data, list):
        for line_data in res_data:
            if not line_data or len(line_data) < 2:
                continue
            
            # Robust indexing avoids unpacking errors completely
            box_coords = line_data[0]
            text_info = line_data[1]
            
            # Safely get text whether it has a confidence score attached or not
            text = text_info[0] if isinstance(text_info, (list, tuple)) else text_info
            
            if text and str(text).strip():
                try:
                    x_min, y_min = int(box_coords[0][0]), int(box_coords[0][1])
                except (IndexError, TypeError, ValueError):
                    x_min, y_min = 0, 0
                boxes.append((y_min, x_min, str(text).strip()))
    

    # Sort top-to-bottom, left-to-right (y primary, x secondary)
    boxes.sort(key=lambda b: (b[0], b[1]))
    lines = [b[2] for b in boxes]

    return _parse_receipt_lines(lines)


# ---------------------------------------------------------------------------
# Receipt field parsing heuristics
# ---------------------------------------------------------------------------
# These operate on a flat list of text lines (sorted top-to-bottom) extracted
# from the receipt.  They use simple regexes; no ML required at this step.

# ── Date patterns ──────────────────────────────────────────────────────────
# Covers most receipt date formats:
#   01/15/2024   01-15-2024   01.15.2024   01/15/24
#   2024-01-15   2024/01/15   Jan 15 2024  January 15, 2024  15 Jan 2024
_DATE_PATTERNS = [
    # MM/DD/YYYY or MM-DD-YYYY or MM.DD.YYYY (with optional 2-digit year)
    (r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4}|\d{2})\b', "MDY"),
    # YYYY-MM-DD or YYYY/MM/DD (ISO-ish)
    (r'\b(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b',     "YMD"),
    # Month-name formats:  Jan 15 2024 / 15 Jan 2024 / January 15, 2024
    (r'\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b',      "MoNY"),  # Jan 15 2024
    (r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b',        "DMoY"),  # 15 Jan 2024
]

_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    # Full names
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}

# ── Price patterns ─────────────────────────────────────────────────────────
# Matches things like:  $12.34  12.34  $ 12.34  USD 12.34  TOTAL 12.34
# Prefer lines that also contain "total" / "amount" / "subtotal" / "due"
_PRICE_PATTERN = re.compile(r'(?:\$|USD|GBP|EUR|CAD|AUD)?\s*(\d{1,5}[\.,]\d{2})\b')
_TOTAL_KEYWORDS = re.compile(
    r'\b(total|subtotal|sub[- ]total|amount|due|balance|grand|sum)\b',
    re.IGNORECASE
)

# ── Vendor heuristics ──────────────────────────────────────────────────────
# Heuristic: the vendor name is usually in the first 1-3 lines of a receipt,
# typically printed in all-caps and without digits.  Lines that look like
# an address (contain street abbreviations or zip-like numbers) are skipped.
_ADDRESS_RE = re.compile(
    r'\b(st\.?|ave\.?|blvd\.?|rd\.?|dr\.?|hwy\.?|suite|ste\.?|floor|fl\.?|\d{5}'
    r'|street|avenue|boulevard|road|drive|highway|lane|ln\.?|way|court|ct\.?'
    r'|place|pl\.?|circle|pkwy\.?|parkway)\b',
    re.IGNORECASE
)
_PHONE_RE   = re.compile(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}')
_URL_RE     = re.compile(r'(www\.|https?://|\.com|\.org|\.net)', re.IGNORECASE)

# Ignore common receipt header fluff/marketing that aren't vendor names
_FLUFF_RE   = re.compile(
    r'\b(give us|welcome to|thank you|thanks for|visit us|take our survey|'
    r'tell us|save money|live better|your cashier|store #|receipt|'
    r'customer copy|duplicate|how was your|feedback|returns)\b',
    re.IGNORECASE
)


def _try_parse_date(line: str) -> Optional[date]:
    """Try every date pattern against *line*; return a date object or None."""
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
    """
    Extract vendor, price, and date from a sorted list of OCR text lines.
    Returns an OCRResult; any field that can't be found is left empty.
    """
    vendor = ""
    price  = ""
    date_s = ""

    # ── 1. Date: scan all lines, prefer the first match ───────────────────
    for line in lines:
        d = _try_parse_date(line)
        if d is not None:
            date_s = d.strftime("%m/%d/%Y")
            break

    # ── 2. Price: prefer a "total" line; fall back to the largest amount ──
    best_total: Optional[float] = None
    best_total_str = ""
    largest: Optional[float] = None
    largest_str = ""

    for line in lines:
        m = _PRICE_PATTERN.search(line)
        if not m:
            continue
        raw = m.group(1).replace(",", ".")  # handle European comma-decimal
        try:
            val = float(raw)
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

    # ── 3. Vendor: look at the first few lines, skip noise ────────────────
    candidate_lines = lines[:6]   # receipts almost always show the store name first
    for line in candidate_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip phone numbers, URLs, addresses, and very short tokens
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
        # Skip pure-number lines (order numbers, ZIP codes, barcodes)
        if re.match(r'^[\d\s\-]+$', stripped):
            continue
        # Skip lines that look like a price on their own
        if _PRICE_PATTERN.fullmatch(stripped) or re.match(r'^\$?\s*\d+\.\d{2}$', stripped):
            continue
        # Skip lines that look like a date (they contain recognisable date patterns)
        if _try_parse_date(stripped) is not None:
            continue
        # Looks like a vendor name
        vendor = stripped
        break

    return OCRResult(vendor=vendor, price=price, date_str=date_s, raw_lines=lines)


# ---------------------------------------------------------------------------
# Utility: convert between the DB's YYYY-MM-DD and the UI's mm/dd/yyyy
# ---------------------------------------------------------------------------

def to_db_date(mmddyyyy: str) -> str:
    """
    Convert a user-entered 'mm/dd/yyyy' string to 'YYYY-MM-DD' for the DB.
    Raises ValueError if the input is invalid.
    """
    try:
        d = datetime.strptime(mmddyyyy.strip(), "%m/%d/%Y")
        return d.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Date must be in mm/dd/yyyy format, got: {mmddyyyy!r}")


def from_db_date(yyyymmdd: str) -> str:
    """
    Convert a DB 'YYYY-MM-DD' string to 'mm/dd/yyyy' for display.
    Returns the original string unchanged if it can't be parsed.
    """
    try:
        d = datetime.strptime(yyyymmdd.strip(), "%Y-%m-%d")
        return d.strftime("%m/%d/%Y")
    except ValueError:
        return yyyymmdd