import cv2
import numpy as np
from PIL import Image
from deskew import determine_skew
from scipy.ndimage import rotate as scipy_rotate


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def _perspective_crop(image_bgr: np.ndarray, quad: np.ndarray) -> np.ndarray:
    rect = _order_points(quad)
    tl, tr, br, bl = rect
    out_w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    out_h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image_bgr, transform, (out_w, out_h))


def _deskew(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    angle = determine_skew(gray)
    if angle is None or abs(angle) < _MIN_SKEW_ANGLE:
        return image_bgr
    rotated = scipy_rotate(image_bgr, angle, reshape=False, cval=255)
    return np.clip(rotated, 0, 255).astype(np.uint8)


_MAX_INPUT_DIM = 1500  # resize large phone photos before heavy OpenCV ops; tune here if needed
_MIN_SKEW_ANGLE = 0.5  # degrees; smaller rotations are ignored
_QUAD_VERTEX_COUNT = 4


def detect_and_normalise(image: Image.Image) -> Image.Image:
    """Detect document boundary, perspective-correct, and deskew.

    Falls back to deskew-only if no clear document quad is found.
    Returns the original image unchanged if no transformation is needed.
    """
    image_bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    h, w = image_bgr.shape[:2]
    resized = False
    if max(h, w) > _MAX_INPUT_DIM:
        ratio = _MAX_INPUT_DIM / max(h, w)
        image_bgr = cv2.resize(image_bgr, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)
        resized = True

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_area = image_bgr.shape[0] * image_bgr.shape[1]
    best_quad: np.ndarray | None = None
    best_area = 0.0

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == _QUAD_VERTEX_COUNT:
            area = float(cv2.contourArea(contour))
            if area > img_area * 0.15 and area > best_area:
                best_area = area
                best_quad = approx.reshape(4, 2).astype(np.float32)

    if best_quad is not None:
        cropped = _perspective_crop(image_bgr, best_quad)
        result_bgr = _deskew(cropped)
        return Image.fromarray(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB))

    deskewed = _deskew(image_bgr)
    if np.array_equal(deskewed, image_bgr):
        return Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)) if resized else image
    return Image.fromarray(cv2.cvtColor(deskewed, cv2.COLOR_BGR2RGB))
