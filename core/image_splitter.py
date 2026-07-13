import cv2
import numpy as np
import os
import tempfile

def _order_points(pts):
    """Order coordinates: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def _four_point_transform(image, pts):
    """Apply a perspective transform to obtain a top-down, flattened view."""
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

def extract_receipts(image_path: str) -> list[str]:
    """
    Detects individual receipts in an image, isolates them, and returns a 
    list of file paths to the newly cropped temporary images.
    """
    image = cv2.imread(image_path)
    if image is None:
        return [image_path]

    orig = image.copy()
    
    # Scale down for faster and more consistent edge detection thresholds
    ratio = image.shape[0] / 800.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 800))

    # Grayscale, blur, and edge detection
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)

    # Morphological closing to bridge gaps in print/paper edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # Find boundaries
    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    extracted_paths = []
    # Ignore anything smaller than 5% of the total image area
    min_area = (resized.shape[0] * resized.shape[1]) * 0.05 

    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            # Flawless 4-point document found; perform perspective warp
            pts = approx.reshape(4, 2) * ratio
            cropped = _four_point_transform(orig, pts)
        else:
            # Irregular shape found; fall back to a padded bounding box
            x, y, w, h = cv2.boundingRect(c)
            x, y, w, h = int(x * ratio), int(y * ratio), int(w * ratio), int(h * ratio)
            
            pad = 20
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(orig.shape[1], x + w + pad), min(orig.shape[0], y + h + pad)
            cropped = orig[y1:y2, x1:x2]

        # Save segment to temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        cv2.imwrite(temp_path, cropped)
        extracted_paths.append(temp_path)

    # Fallback to the original image if no documents were identified
    if not extracted_paths:
        return [image_path]

    return extracted_paths