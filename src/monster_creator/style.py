"""Verify the approved binary and compile repeatable sprite prompts."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image


REFERENCE = Path("references/master_style.png")
PROMPT_VERSION = "1.0.0"


def _manifest(repo: Path) -> dict:
    manifest = json.loads((repo / "references/style_manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("reference_path") != REFERENCE.as_posix()
            or manifest.get("require_exact_hash") is not True
            or not re.fullmatch(r"[0-9a-f]{64}", manifest.get("sha256", ""))
            or not manifest.get("version")):
        raise ValueError("The repository's master artwork lock is invalid.")
    return manifest


def _verified_bytes(source: Path, manifest: dict) -> bytes:
    if source.stat().st_size != manifest["bytes"]:
        raise ValueError(f"Master artwork size does not match the lock: {source}")
    data = source.read_bytes()
    if len(data) != manifest["bytes"] or sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError(f"Master artwork SHA-256 does not match the lock: {source}")
    with Image.open(BytesIO(data)) as image:
        if (image.format != "PNG" or image.mode != manifest["mode"]
                or image.size != (manifest["width"], manifest["height"])
                or list(image.getchannel("A").getextrema()) != manifest["alpha_range"]):
            raise ValueError(f"Master artwork PNG metadata does not match the lock: {source}")
    return data


def verify_master(repo: Path) -> dict:
    manifest = _manifest(repo)
    target = repo / REFERENCE
    if not target.is_file():
        raise ValueError(
            f"Locked master artwork is missing: {target}. "
            f"Install the original {manifest['original_filename']} (SHA-256 {manifest['sha256']})."
        )
    _verified_bytes(target, manifest)
    return manifest


def install_master(repo: Path, source: Path) -> dict:
    manifest = _manifest(repo)
    target = repo / REFERENCE
    data = _verified_bytes(source, manifest)
    if not target.exists():
        with target.open("xb") as output:
            output.write(data)
    return verify_master(repo)


def compile_prompt(family: dict, stage: int, feedback: str | None = None) -> str:
    stages = family["stages"]
    current = next((item for item in stages if item["stage"] == stage), None)
    if current is None:
        raise ValueError(f"Stage {stage} is not defined for {family['familyId']}.")
    lineup = "\n".join(
        f"- Stage {item['stage']} | {item['name']}: {item['description']}" for item in stages
    )
    design = family.get("design", "")
    if not isinstance(design, str):
        design = json.dumps(design, ensure_ascii=False, sort_keys=True)
    concept = family.get("concept") or family["description"]

    prompt = f"""Create one full-body Aevareth game monster sprite, stage {stage} of {len(stages)}.
Use the attached, locked Aqua and Flame Evolution Line master image as actual visual conditioning.
Match its premium cute 2D anime fantasy rendering, smooth detailed surface textures, layered cel shadows with
gradient transitions, vibrant controlled elemental colors, glossy highlights, expressive faces, coherent lighting,
and clean tapered colored outlines. Translate the rendering into this species without copying reference anatomy.
Use any attached prior family stage to maintain markings, anatomy, palette and lineage.

Family: {family['displayName']} | {family['category']} | {', '.join(family['elements'])}
Species: {family['species']}
Concept: {concept}
Family design: {design}
Evolution lineup for continuity only:
{lineup}
Draw only stage {stage}, {current['name']}: {current['description']}

Left-facing front three-quarter view. Aim the nose, beak or anatomical leading feature toward screen-left,
with the near side and a natural glimpse of the far side visible. Keep plausible species-specific anatomy, intentional
limb placement and a clean complete silhouette. Build the elemental materials and restrained natural effects into
the creature. Keep the subject centered with clear padding on all sides, paws or floating base aligned consistently.
Deliver one truly transparent RGBA PNG with clean antialiased edges and intentional translucent details.
Exclude backgrounds, fake checkerboards, ground shadows, borders, letters, watermarks, extra figures, cropped body
parts, duplicate limbs and recognizable protected third-party designs."""
    if feedback:
        prompt += f"\n\nCorrect this issue from the previous attempt: {feedback}"
    return prompt


def main() -> None:
    parser = argparse.ArgumentParser(description="Install and verify the exact approved master artwork.")
    parser.add_argument("action", choices=("verify", "install"))
    parser.add_argument("source", nargs="?", type=Path)
    args = parser.parse_args()
    if (args.action == "install") != (args.source is not None):
        parser.error("install requires the path to the exact owner-approved original.")
    try:
        manifest = install_master(Path.cwd(), args.source) if args.source else verify_master(Path.cwd())
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps({"reference": str((Path.cwd() / REFERENCE).resolve()), "sha256": manifest["sha256"]}))


if __name__ == "__main__":
    main()
