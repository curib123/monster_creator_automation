from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from monster_creator.archetypes import load_archetypes
from monster_creator.style import compile_prompt, install_master, verify_master


def test_tracked_master_matches_manifest():
    verify_master(Path(__file__).resolve().parents[1])


def test_master_install_requires_original_bytes(tmp_path):
    references = tmp_path / "references"
    references.mkdir()
    source = tmp_path / "original.png"
    image = Image.new("RGBA", (4, 4))
    image.putpixel((1, 1), (160, 60, 240, 255))
    image.save(source)
    original = source.read_bytes()
    manifest = {
        "reference_path": "references/master_style.png",
        "original_filename": "original.png", "require_exact_hash": True, "version": "1.0.0",
        "sha256": sha256(original).hexdigest(), "bytes": len(original),
        "width": 4, "height": 4, "format": "PNG", "mode": "RGBA", "alpha_range": [0, 255],
    }
    (references / "style_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    target = references / "master_style.png"
    with pytest.raises(ValueError, match="missing"):
        verify_master(tmp_path)
    source.write_bytes(original[:-1] + b"X")
    with pytest.raises(ValueError, match="SHA-256"):
        install_master(tmp_path, source)
    assert not target.exists()
    source.write_bytes(original)
    assert install_master(tmp_path, source) == manifest
    assert target.read_bytes() == original
    target.write_bytes(original[:-1] + b"X")
    with pytest.raises(ValueError, match="SHA-256"):
        install_master(tmp_path, source)
    assert target.read_bytes() != original


def test_stage_prompt_preserves_hybrid_and_continuity():
    archetypes = load_archetypes(Path(__file__).resolve().parents[1])
    family = {
        "familyId": "braidwing", "displayName": "Braidwing", "category": "Wild",
        "elements": ["Psychic", "Crystal"], "archetypeId": "butterfly", "concept": "Prism silk",
        "identityAnchors": "Amber wings and curled antennae.",
        "design": {"motif": "braided veins"},
        "stages": [
            {"stage": 1, "name": "Twillarva", "title": "Young", "description": "Soft winged butterfly"},
            {"stage": 2, "name": "Braidwing", "title": "Growing", "description": "Open amber wings",
             "transitionRationale": "Expanding wings support longer glides."},
        ],
    }
    prompt = compile_prompt(family, 2, archetypes, "Make the head visibly face left.")
    assert all(part in prompt for part in (
        "Psychic, Crystal", "braided veins", "Twillarva", "Draw only stage 2", "transparent RGBA",
        "actual visual conditioning", "Make the head visibly face left.", "Butterfly (butterfly)",
        "Amber wings and curled antennae", "Expanding wings support longer glides",
        "master_style_three_elements_stages_1-3.png",
    ))
    with pytest.raises(ValueError, match="Stage 3"):
        compile_prompt(family, 3, archetypes)
