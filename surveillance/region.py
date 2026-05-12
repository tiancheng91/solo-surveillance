from __future__ import annotations

import numpy as np


def crop_to_region(
    frame: np.ndarray,
    region: tuple[float, float, float, float] | None,
) -> np.ndarray:
    """Crop frame to normalized region [x1, y1, x2, y2] (0-1 range).

    Returns the original frame unchanged if region is None.
    """
    if region is None:
        return frame
    x1, y1, x2, y2 = region
    h, w = frame.shape[:2]
    px1, py1 = int(x1 * w), int(y1 * h)
    px2, py2 = int(x2 * w), int(y2 * h)
    px1, py1 = max(0, px1), max(0, py1)
    px2, py2 = min(w, px2), min(h, py2)
    if px2 <= px1 or py2 <= py1:
        return frame
    return frame[py1:py2, px1:px2]
