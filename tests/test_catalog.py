from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from monster_creator.archetypes import load_archetypes
from monster_creator.catalog import (
    MONSTER_TYPES, QUOTAS, choose_world, coverage, default_designs, plan, validate_catalog, validate_designs,
)
from monster_creator.roster_designs import PROPOSED_HYBRIDS, ROSTER_DESIGNS
from monster_creator.verdant import VERDANT_DESIGNS


@pytest.fixture
def archetypes():
    return load_archetypes(Path(__file__).resolve().parents[1])


@pytest.fixture
def catalog():
    labels = ("Grass", "Water", "Fire", "Air", "Electric", "Ice", "Light", "Dark", "Poison", "Psychic",
              "Land", "Dragonic", "Mythic", "Metal", "Crystal", "Wood", "Glass", "Hybrid", "Tech")
    worlds = [
        ("verdant-reach", "grass"), ("terra-crown-badlands", "land"), ("tideglass-coast", "water"),
        ("emberfall-peaks", "fire"), ("zephyr-heights", "air"), ("cedarheart-grove", "wood"),
        ("frostveil-expanse", "ice"), ("stormforge-reach", "electric"), ("venomfen-marsh", "poison"),
        ("steelcrest-citadel", "metal"), ("clearpane-terraces", "glass"), ("sapphire-spires", "crystal"),
        ("neonvault-sanctum", "tech"), ("dawnspire-sanctuary", "light"), ("umbral-hollow", "dark"),
        ("astral-reverie", "psychic"), ("dragonspire-aerie", "dragonic"), ("mythveil-gardens", "mythic"),
        ("emberfrost-rift", "hybrid"), ("prismtide-lagoon", "hybrid"), ("stormroot-wilds", "hybrid"),
        ("twinfold-confluence", "hybrid"), ("psionic-crystal-nexus", "hybrid"),
        ("eclipse-eternum", "hybrid"), ("aevareth-origin-realm", "hybrid"),
    ]
    components = {"psionic-crystal-nexus": ["psychic", "crystal"], "eclipse-eternum": ["light", "dark"],
                  "aevareth-origin-realm": [label.lower() for label in labels if label != "Hybrid"]}
    snapshot = {
        "schemaVersion": 1,
        "source": {"revision": None, "sha256": "fixture"},
        "elements": [{"id": label.lower(), "gameElement": label, "value": i,
                      "assetKey": {"Grass": "land", "Land": "terra"}.get(label, label.lower())}
                     for i, label in enumerate(labels)],
        "worlds": [{"id": home, "displayName": home.replace("-", " ").title(), "element": element,
                    "endless": home == "aevareth-origin-realm", "components": components.get(home, []),
                    "encounterPool": []} for home, element in worlds],
        "families": [],
    }
    for world in snapshot["worlds"]:
        home = world["id"]
        existing = {"Wild": 1, "Legendary": 0, "Guardian": int(not world["endless"])} if home in ROSTER_DESIGNS else QUOTAS
        for category, count in existing.items():
            for index in range(count):
                family_id = f"{home}-{category.lower()}-{index}"
                if home == "verdant-reach":
                    offset = list(QUOTAS).index(category)
                    preceding = sum(list(QUOTAS.values())[:offset])
                    family_id = list(VERDANT_DESIGNS)[preceding + index]
                snapshot["families"].append({
                    "familyId": family_id, "worldId": home, "element": world["element"], "displayName": family_id,
                    "identitySource": "canonical.png", "description": "A fixture design.", "retired": False,
                    "monsterType": MONSTER_TYPES[category],
                    "stages": [{"stage": stage, "name": family_id, "title": str(stage), "ready": True}
                               for stage in range(1, 4)],
                })
                if category == "Wild":
                    world["encounterPool"].append(family_id)
    return validate_catalog(snapshot)


def test_complete_world_roster_and_distinct_proposals(catalog, archetypes):
    designs = default_designs(catalog, archetypes)
    report = coverage(catalog, designs)
    assert report["worldCount"] == 25
    assert report["elementCount"] == 19
    assert report["targets"] == {"Wild": 125, "Legendary": 25, "Guardian": 25}
    assert report["existingDedicatedFamilies"] == 104
    assert report["plannedFamilies"] == 175
    assert report["maximumSprites"] == 525
    assert report["missingDesignSlots"] == 0
    assert Counter(row["category"] for row in designs) == {"Wild": 56, "Legendary": 14, "Guardian": 1}
    assert {row["archetypeId"] for row in designs} <= archetypes.keys()
    assert len({row["archetypeId"] for row in designs}) < len({row["description"] for row in designs}) == len(designs)
    assert {row["id"] for row in report["worlds"] if row["componentsUnspecified"]} == set(PROPOSED_HYBRIDS)
    assert all(row["plannedFamilies"] == QUOTAS for row in report["worlds"])
    assert set(report["worlds"][-1]["components"]) == {row["id"] for row in catalog["elements"]} - {"hybrid"}
    assert report["worlds"][-1]["existingFamilies"] == {"Wild": 1, "Legendary": 0, "Guardian": 0}
    asset_keys = {row["id"]: row["assetKey"] for row in catalog["elements"]}
    assert (asset_keys["grass"], asset_keys["land"]) == ("land", "terra")


def test_verdant_catalog_keeps_legacy_families_out_of_generation(catalog, archetypes):
    world = choose_world(catalog, "Verdant Reach")
    assert choose_world(catalog, "1") == world
    before = deepcopy(catalog)
    roster = plan(catalog, [world], default_designs(catalog, archetypes), archetypes)
    assert roster["families"] == []
    assert set(roster["worlds"][0]["existingFamiliesWithoutDraftBrief"]) == set(VERDANT_DESIGNS)
    assert {row["status"] for row in roster["worlds"][0]["legacyArchetypeReview"].values()} == {"requires-migration-plan"}
    assert roster["worlds"][0]["existingFamilies"] == QUOTAS
    assert catalog == before


def test_missing_slots_are_reported(catalog):
    report = coverage(catalog)
    assert report["missingDesignSlots"] == 71
    assert report["worlds"][-1]["missingDesignSlots"] == {"Wild": 4, "Legendary": 1, "Guardian": 1}


def test_incorrect_hybrid_and_incomplete_endless_fail(catalog, archetypes):
    bad_catalog = deepcopy(catalog)
    bad_catalog["worlds"][-1]["components"].remove("grass")
    with pytest.raises(ValueError, match="Endless"):
        validate_catalog(bad_catalog)
    assert choose_world(catalog, "Psionic Crystal Nexus")["components"] == ["psychic", "crystal"]
    proposal = next(row for row in default_designs(catalog, archetypes) if row["familyId"] == "nacreseer")
    assert validate_designs(catalog, [proposal], archetypes) == [proposal]
    with pytest.raises(ValueError, match="Wrong world hybrid"):
        validate_designs(catalog, [{**proposal, "elements": ["psychic", "glass"]}], archetypes)


def test_duplicate_excess_and_fourth_stage_fail(catalog, archetypes):
    proposal = default_designs(catalog, archetypes)[0]
    with pytest.raises(ValueError, match="conflicts"):
        validate_designs(catalog, [proposal, proposal], archetypes)
    with pytest.raises(ValueError, match="Duplicate family concept"):
        validate_designs(catalog, [proposal, {**proposal, "familyId": "similar", "displayName": "Similar"}], archetypes)
    with pytest.raises(ValueError, match="exceeds"):
        validate_designs(catalog, [{**proposal, "worldId": "verdant-reach", "elements": ["grass"], "gameElement": "Grass"}],
                         archetypes)
    with pytest.raises(ValueError, match="one to three"):
        validate_designs(catalog, [{**proposal, "stages": [*proposal["stages"], {"stage": 4}]}], archetypes)


def test_archetype_policy_and_lineage_cannot_be_bypassed(catalog, archetypes):
    assert set(archetypes) == {"fox", "rabbit", "cat", "eagle", "phoenix", "dragon", "butterfly", "gecko", "bear",
                              "manta_ray", "jellyfish", "ghost", "knight", "sorcerer", "magician"}
    proposal = default_designs(catalog, archetypes)[0]
    for archetype_id in archetypes:
        assert validate_designs(catalog, [{**proposal, "archetypeId": archetype_id}], archetypes)
    for invalid in (None, "tortoise", ["fox", "rabbit"]):
        with pytest.raises(ValueError, match="one approved archetypeId"):
            validate_designs(catalog, [{**proposal, "archetypeId": invalid}], archetypes)
    with pytest.raises(ValueError, match="identityAnchors"):
        validate_designs(catalog, [{**proposal, "identityAnchors": " "}], archetypes)
    for changes, match in (({"archetypeId": "eagle"}, "changes the family archetype"),
                           ({"transitionRationale": None}, "distinct transitionRationale"),
                           ({"description": proposal["stages"][0]["description"].upper()}, "distinct visual design")):
        first, second, third = proposal["stages"]
        with pytest.raises(ValueError, match=match):
            validate_designs(catalog, [{**proposal, "stages": [first, {**second, **changes}, third]}], archetypes)
