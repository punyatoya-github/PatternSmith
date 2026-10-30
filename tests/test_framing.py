import pytest

from app.services.imaging.framing import ASPECT_PRESETS, MAX_ZOOM, compute_crop_box


def _ratio(box, w, h):
    return ((box.right - box.left) * w) / ((box.bottom - box.top) * h)


def test_whole_photo_is_the_full_image():
    box = compute_crop_box(300, 200)
    assert (box.left, box.top, box.right, box.bottom) == (0, 0, 1, 1)


@pytest.mark.parametrize("size", [(200, 100), (100, 200), (300, 300), (1600, 900)])
@pytest.mark.parametrize("aspect", [a for a in ASPECT_PRESETS.values() if a])
def test_frame_has_the_requested_shape_and_stays_inside(size, aspect):
    w, h = size
    box = compute_crop_box(w, h, aspect, zoom=1.0)
    assert _ratio(box, w, h) == pytest.approx(aspect)
    assert 0 <= box.left < box.right <= 1 and 0 <= box.top < box.bottom <= 1


def test_square_from_landscape_is_centered_by_default():
    box = compute_crop_box(200, 100, aspect=1.0)
    assert (box.left, box.right) == pytest.approx((0.25, 0.75))
    assert (box.top, box.bottom) == (0, 1)


def test_zoom_shrinks_the_frame():
    full = compute_crop_box(200, 100, 1.0, zoom=1)
    zoomed = compute_crop_box(200, 100, 1.0, zoom=2)
    assert (zoomed.right - zoomed.left) == pytest.approx((full.right - full.left) / 2)
    assert (zoomed.bottom - zoomed.top) == pytest.approx((full.bottom - full.top) / 2)


def test_pan_moves_the_frame_to_the_edges_without_leaving_the_photo():
    left = compute_crop_box(200, 100, 1.0, zoom=2, pan_x=0, pan_y=0)
    right = compute_crop_box(200, 100, 1.0, zoom=2, pan_x=1, pan_y=1)
    assert (left.left, left.top) == (0, 0)
    assert right.right == pytest.approx(1) and right.bottom == pytest.approx(1)


def test_inputs_are_clamped():
    box = compute_crop_box(200, 100, 1.0, zoom=999, pan_x=-5, pan_y=7)
    assert (box.right - box.left) == pytest.approx(0.5 / MAX_ZOOM)
    assert box.left == 0 and box.bottom == pytest.approx(1)
    assert compute_crop_box(200, 100, 1.0, zoom=0.1) == compute_crop_box(200, 100, 1.0, zoom=1)


def test_bad_sizes_rejected():
    with pytest.raises(ValueError):
        compute_crop_box(0, 100)
    with pytest.raises(ValueError):
        compute_crop_box(100, 100, aspect=-1)
