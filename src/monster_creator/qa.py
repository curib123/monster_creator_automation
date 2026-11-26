"""Technical sprite checks and evidence for the separate visual review."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


PIVOT = (0.5, 0.06)
PROCESSING_VERSION = 3
ALPHA_NOISE_MAX = 8  # Matches the existing Aevareth monster sprite extraction policy.
RUBRIC = {
    "styleFidelity": 25,
    "aestheticPolish": 20,
    "evolutionContinuity": 20,
    "elementalExpression": 15,
    "speciesAnatomyOriginality": 10,
    "spriteUsability": 10,
}
VISUAL_CHECKS = (
    "identityReviewed", "anatomyReviewed", "facingReviewed", "progressionReviewed",
    "lightBackgroundReviewed", "darkBackgroundReviewed", "textureReviewed",
    "styleReviewed", "elementReviewed", "fullSilhouetteReviewed",
    "noTextReviewed", "originalityReviewed",
)


def normalize(source: bytes, size: int, stage: int, count: int, floating: bool) -> tuple[bytes, dict]:
    with Image.open(BytesIO(source)) as image:
        if image.format != "PNG" or image.mode != "RGBA" or image.n_frames != 1:
            raise ValueError("Expected a single, true RGBA PNG")
        if min(image.size) < 256 or max(image.size) > 4096:
            raise ValueError("Source dimensions must be between 256 and 4096 pixels")
        alpha = image.getchannel("A")
        minimum, maximum = alpha.getextrema()
        if minimum != 0 or maximum < 250:
            raise ValueError("PNG must have fully transparent pixels and a solid subject")
        alpha = alpha.point(lambda value: 0 if value <= ALPHA_NOISE_MAX else value)
        image.putalpha(alpha)
        bounds = alpha.getbbox()
        width, height = image.size
        left, top, right, bottom = bounds
        if min(left, top, image.width - right, image.height - bottom) < max(2, min(image.size) // 100):
            raise ValueError("Artwork touches the edge or has insufficient clear padding")
        if max(right - left, bottom - top) < 128:
            raise ValueError("Subject is too small for a game sprite")
        subject = image.crop(bounds)

    # An increasing maximum footprint gives families room to grow without inventing pixels.
    footprint = (0.82,) if count == 1 else ((0.72, 0.86) if count == 2 else (0.68, 0.77, 0.86))
    subject.thumbnail((int(size * footprint[stage - 1]),) * 2, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size))
    ground = round(size * (1 - (0.12 if floating else PIVOT[1])))
    canvas.paste(subject, ((size - subject.width) // 2, ground - subject.height))
    stream = BytesIO()
    canvas.save(stream, format="PNG")
    png = stream.getvalue()
    return png, {
        "width": size, "height": size, "bounds": list(canvas.getbbox()),
        "pivot": list(PIVOT), "sha256": sha256(png).hexdigest(),
        "pixelSha256": sha256(canvas.tobytes()).hexdigest(),
        "sourceWidth": width, "sourceHeight": height,
        "sourceBounds": list(bounds), "alphaNoiseThreshold": ALPHA_NOISE_MAX,
    }


def visual_result(report: dict, technical: dict, reference_hash: str) -> dict:
    if report.get("sha256") != technical["sha256"] or report.get("referenceSha256") != reference_hash:
        raise ValueError("Visual evidence must identify the exact sprite and master SHA-256")
    for field in ("reviewer", "notes"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            raise ValueError(f"Visual evidence requires {field}")
    if any(type(report.get(field)) is not bool for field in VISUAL_CHECKS):
        raise ValueError("Visual evidence must explicitly evaluate every visual check")
    scores = report.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(RUBRIC) or any(
        type(score) not in (int, float) or not 0 <= score <= 10 for score in scores.values()
    ):
        raise ValueError("Visual evidence must score every rubric dimension from 0 to 10")
    score = sum(RUBRIC[field] * scores[field] for field in RUBRIC) / 100
    passed = score >= 9 and min(scores.values()) >= 8 and all(report[field] for field in VISUAL_CHECKS)
    return {"sha256": technical["sha256"], "referenceSha256": reference_hash,
            "visualReviewer": report["reviewer"], "notes": report["notes"], "scores": scores,
            "score": score, "passed": passed, **{field: report[field] for field in VISUAL_CHECKS}}


def comparison(master: Path, sprite: Path) -> bytes:
    panel_width, panel_height = 640, 480
    sheet = Image.new("RGB", (3 * panel_width, panel_height + 36), "#333333")
    labels = ((master, "Locked master", "#d7d9dc"),
              (sprite, "Candidate on light", "#f3f3f3"), (sprite, "Candidate on dark", "#252a36"))
    draw = ImageDraw.Draw(sheet)
    for index, (path, label, color) in enumerate(labels):
        with Image.open(path) as source:
            art = source.convert("RGBA")
        art.thumbnail((panel_width - 16, panel_height - 16), Image.Resampling.LANCZOS)
        panel = Image.new("RGBA", (panel_width, panel_height), color)
        panel.alpha_composite(art, ((panel_width - art.width) // 2, (panel_height - art.height) // 2))
        sheet.paste(panel, (index * panel_width, 36))
        draw.text((index * panel_width + 12, 12), label, fill="white")
    stream = BytesIO()
    sheet.save(stream, format="PNG")
    return stream.getvalue()
