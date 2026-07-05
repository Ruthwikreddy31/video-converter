import os
from typing import Dict, Any
from app.services.ffmpeg_service import (
    generate_thumbnail,
    generate_preview_frame,
    get_crop_filter_for_format,
)


FORMATS = {
    "scope": {"ratio": 2.39, "label": "Scope (2.39:1)"},
    "digital_imax": {"ratio": 1.90, "label": "Digital IMAX (1.90:1)"},
    "full_imax": {"ratio": 1.43, "label": "Full IMAX (1.43:1)"},
}


def generate_all_previews(
    video_path: str,
    video_id: str,
    video_info: Dict[str, Any],
    previews_dir: str
) -> Dict[str, str]:
    """Generate preview frames for all formats. Never raises — logs and skips on failure."""
    previews = {}
    width = video_info["width"]
    height = video_info["height"]

    os.makedirs(previews_dir, exist_ok=True)

    # Original thumbnail
    original_path = os.path.join(previews_dir, f"{video_id}_original.jpg")
    try:
        if generate_thumbnail(video_path, original_path, timestamp=5.0):
            previews["original"] = f"/previews/{video_id}_original.jpg"
    except Exception as e:
        print(f"[preview] original thumbnail failed: {e}")

    # Format previews — always CROP to reach the target ratio, matching the
    # real conversion logic in convert_video(). Padding (adding black bars)
    # was previously used when the source was narrower than the target, but
    # that made previews for Scope/Digital IMAX/Full IMAX look nearly
    # identical to the original — just the same frame with thin sidebars.
    # get_crop_filter_for_format() already branches correctly: it crops
    # top/bottom when going WIDER than the source, and crops sides when
    # going NARROWER — there is no pad case needed.
    for format_key, format_data in FORMATS.items():
        target_ratio = format_data["ratio"]
        preview_path = os.path.join(previews_dir, f"{video_id}_{format_key}.jpg")

        try:
            crop_filter = get_crop_filter_for_format(width, height, target_ratio)["filter"]
            if generate_preview_frame(video_path, preview_path, crop_filter):
                previews[format_key] = f"/previews/{video_id}_{format_key}.jpg"
        except Exception as e:
            print(f"[preview] {format_key} preview failed: {e}")
            continue

    return previews
