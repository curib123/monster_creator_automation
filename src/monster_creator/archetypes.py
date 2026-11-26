"""Load the approved anatomy policy and validate a family design line."""

import json
from pathlib import Path


def load_archetypes(repo: Path) -> dict:
    # JSON is a YAML subset and keeps the checked-in policy dependency-free.
    policy = json.loads((repo / "config/species.yaml").read_text(encoding="utf-8"))
    rows = policy["archetypes"]
    archetypes = {row["id"]: row for row in rows}
    if policy.get("allow_unlisted") is not False or len(rows) != 15 or len(archetypes) != 15:
        raise ValueError("Expected exactly 15 distinct approved archetypes in config/species.yaml")
    return archetypes


def canonical_text(text: str) -> str:
    return " ".join(text.casefold().split())


def validate_design_line(family: dict, archetypes: dict) -> dict:
    family_id = family["familyId"]
    archetype = family.get("archetypeId")
    if not isinstance(archetype, str) or archetype not in archetypes:
        raise ValueError(f"{family_id} requires one approved archetypeId from config/species.yaml")
    anchors = family.get("identityAnchors")
    if not isinstance(anchors, str) or not anchors.strip():
        raise ValueError(f"{family_id} requires recognizable identityAnchors across the lineage")
    stages = family.get("stages")
    if not isinstance(stages, list) or not 1 <= len(stages) <= 3:
        raise ValueError(f"Expected one to three stages for {family_id}")
    descriptions, transitions = set(), set()
    for number, stage in enumerate(stages, 1):
        if not isinstance(stage, dict) or type(stage.get("stage")) is not int or stage["stage"] != number:
            raise ValueError(f"Stages must be numbered consecutively from 1 for {family_id}")
        if stage.get("archetypeId", archetype) != archetype:
            raise ValueError(f"Stage {number} changes the family archetype for {family_id}")
        for field in ("name", "title", "description"):
            if not isinstance(stage.get(field), str) or not stage[field].strip():
                raise ValueError(f"Missing or empty {field} for {family_id} stage {number}")
        description = canonical_text(stage["description"])
        if description in descriptions:
            raise ValueError(f"Stage {number} must have a distinct visual design for {family_id}")
        descriptions.add(description)
        if number > 1:
            reason = stage.get("transitionRationale")
            if not isinstance(reason, str) or not reason.strip() or canonical_text(reason) in transitions:
                raise ValueError(f"Stage {number} requires a distinct transitionRationale for {family_id}")
            transitions.add(canonical_text(reason))
    return archetypes[archetype]
