"""Technical sprite checks and evidence for the separate visual review."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


PIVOT = (0.5, 0.06)
PROCESSING_VERSION = 3
REVIEW_POLICY_VERSION = 2
ALPHA_NOISE_MAX = 8  # Matches the existing Aevareth monster sprite extraction policy.
RUBRIC = {
    "styleFidelity": 25,
    "aestheticPolish": 20,
    "evolutionContinuity": 20,
    "elementalExpression": 15,
    "archetypeAnatomy": 10,
    "silhouetteUsability": 10,
}
VISUAL_CHECKS = (
    "identityReviewed", "anatomyReviewed", "facingReviewed", "progressionReviewed",
    "lightBackgroundReviewed", "darkBackgroundReviewed", "textureReviewed",
    "styleReviewed", "elementReviewed", "fullSilhouetteReviewed",
    "noTextReviewed", "originalityReviewed", "archetypeReviewed", "aestheticsReviewed",
    "transparencyReviewed",
)
FINAL_CHECK = "finalFormRefinementReviewed"


def stage_checks(stage: int) -> tuple[str, ...]:
    return VISUAL_CHECKS + ((FINAL_CHECK,) if stage == 3 else ())


def lineup_rules(count: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    dimensions = ("aesthetics", "anatomyAndSilhouette", "cleanliness")
    checks = ("archetypeCoherent", "elementIntegrated", "aestheticallyCoherent")
    if count >= 2:
        dimensions += ("evolutionLogic", "identityContinuity", "stageDifferentiation")
        checks += ("naturalDevelopment", "purposefulStageChanges")
    if count == 3:
        dimensions += ("finalFormRefinement",)
        checks += (FINAL_CHECK,)
    return dimensions, checks


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


def evaluate_scores(report: dict, dimensions, checks) -> tuple[dict, dict]:
    for field in ("reviewer", "notes"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            raise ValueError(f"Visual evidence requires {field}")
    if any(type(report.get(field)) is not bool for field in checks):
        raise ValueError("Visual evidence must explicitly evaluate every visual check")
    scores = report.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(dimensions) or any(
        type(score) not in (int, float) or not 0 <= score <= 10 for score in scores.values()
    ):
        raise ValueError("Visual evidence must score every rubric dimension from 0 to 10")
    return scores, {field: report[field] for field in checks}


def visual_result(report: dict, sprite_hash: str, reference_hash: str, comparison_hash: str, stage: int) -> dict:
    evidence = {"sha256": sprite_hash, "referenceSha256": reference_hash, "comparisonSha256": comparison_hash,
                "reviewPolicyVersion": REVIEW_POLICY_VERSION}
    if any(report.get(field) != value for field, value in evidence.items()):
        raise ValueError("Visual evidence must identify the exact sprite, master and comparison for the current policy")
    scores, checks = evaluate_scores(report, RUBRIC, stage_checks(stage))
    score = sum(RUBRIC[field] * scores[field] for field in RUBRIC) / 100
    passed = score >= 9 and min(scores.values()) >= 8 and all(checks.values())
    return {**evidence, "visualReviewer": report["reviewer"], "notes": report["notes"], "scores": scores,
            "score": score, "passed": passed, **checks}


def lineup_result(report: dict, evidence: dict) -> dict:
    if any(report.get(field) != value for field, value in evidence.items()):
        raise ValueError("Lineup evidence must identify the exact current stage images, master and comparison")
    count = len(evidence["stageSha256"])
    dimensions, flags = lineup_rules(count)
    scores, checks = evaluate_scores(report, dimensions, flags)
    score = sum(scores.values()) / len(scores)
    passed = score >= 9 and min(scores.values()) >= 8 and all(checks.values())
    revisions = report.get("revisionStages")
    if (not isinstance(revisions, list)
            or any(type(stage) is not int or not 1 <= stage <= count for stage in revisions)
            or len(set(revisions)) != len(revisions)):
        raise ValueError("revisionStages must contain distinct stage numbers within the lineup")
    if (passed and revisions) or (not passed and not revisions):
        raise ValueError("Use revisionStages to identify affected stages only for a rejected lineup")
    return {**evidence, "reviewer": report["reviewer"], "notes": report["notes"], "scores": scores,
            "score": score, "passed": passed, "revisionStages": revisions, **checks}


def comparison(master: Path, sprite: Path) -> bytes:
    return _comparison_panels(((master, "Locked master", "#d7d9dc"), (sprite, "Candidate on light", "#f3f3f3"),
                               (sprite, "Candidate on dark", "#252a36")))


def lineup_comparison(master: Path, sprites: list[Path]) -> bytes:
    return _comparison_panels([(master, "Locked master", "#d7d9dc")] + [
        (sprite, f"Stage {stage}", "#d7d9dc") for stage, sprite in enumerate(sprites, 1)
    ])


def _comparison_panels(panels) -> bytes:
    panel_width, panel_height = 640, 480
    sheet = Image.new("RGB", (len(panels) * panel_width, panel_height + 36), "#333333")
    draw = ImageDraw.Draw(sheet)
    for index, (path, label, color) in enumerate(panels):
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
