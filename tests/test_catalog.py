from collections import Counter
from copy import deepcopy

import pytest

from monster_creator.catalog import (
    MONSTER_TYPES, QUOTAS, choose_world, coverage, default_designs, plan, validate_catalog, validate_designs,
)
from monster_creator.roster_designs import PROPOSED_HYBRIDS, ROSTER_DESIGNS
from monster_creator.verdant import VERDANT_DESIGNS


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


def test_complete_world_roster_and_distinct_proposals(catalog):
    designs = default_designs(catalog)
    report = coverage(catalog, designs)
    assert report["worldCount"] == 25
    assert report["elementCount"] == 19
    assert report["targets"] == {"Wild": 125, "Legendary": 25, "Guardian": 25}
    assert report["existingDedicatedFamilies"] == 104
    assert report["plannedFamilies"] == 175
    assert report["maximumSprites"] == 525
    assert report["missingDesignSlots"] == 0
    assert Counter(row["category"] for row in designs) == {"Wild": 56, "Legendary": 14, "Guardian": 1}
    assert len({row["species"] for row in designs}) == len(designs)
    assert {row["id"] for row in report["worlds"] if row["componentsUnspecified"]} == set(PROPOSED_HYBRIDS)
    assert all(row["plannedFamilies"] == QUOTAS for row in report["worlds"])
    assert set(report["worlds"][-1]["components"]) == {row["id"] for row in catalog["elements"]} - {"hybrid"}
    assert report["worlds"][-1]["existingFamilies"] == {"Wild": 1, "Legendary": 0, "Guardian": 0}
    asset_keys = {row["id"]: row["assetKey"] for row in catalog["elements"]}
    assert (asset_keys["grass"], asset_keys["land"]) == ("land", "terra")


def test_verdant_reuses_every_saved_family_and_stage_identity(catalog):
    world = choose_world(catalog, "Verdant Reach")
    assert choose_world(catalog, "1") == world
    roster = plan(catalog, [world], default_designs(catalog))
    assert {row["familyId"] for row in roster["families"]} == set(VERDANT_DESIGNS)
    assert sum(len(row["stages"]) for row in roster["families"]) == 21
    assert all(row["gameElement"] == "Grass" and row["isNewFamily"] is False for row in roster["families"])
    assert roster["worlds"][0]["existingFamilies"] == QUOTAS


def test_missing_slots_are_reported(catalog):
    report = coverage(catalog)
    assert report["missingDesignSlots"] == 71
    assert report["worlds"][-1]["missingDesignSlots"] == {"Wild": 4, "Legendary": 1, "Guardian": 1}


def test_incorrect_hybrid_and_incomplete_endless_fail(catalog):
    bad_catalog = deepcopy(catalog)
    bad_catalog["worlds"][-1]["components"].remove("grass")
    with pytest.raises(ValueError, match="Endless"):
        validate_catalog(bad_catalog)
    assert choose_world(catalog, "Psionic Crystal Nexus")["components"] == ["psychic", "crystal"]
    proposal = next(row for row in default_designs(catalog) if row["familyId"] == "nacreseer")
    assert validate_designs(catalog, [proposal]) == [proposal]
    with pytest.raises(ValueError, match="Wrong world hybrid"):
        validate_designs(catalog, [{**proposal, "elements": ["psychic", "glass"]}])


def test_duplicate_excess_and_fourth_stage_fail(catalog):
    proposal = default_designs(catalog)[0]
    with pytest.raises(ValueError, match="conflicts"):
        validate_designs(catalog, [proposal, proposal])
    with pytest.raises(ValueError, match="exceeds"):
        validate_designs(catalog, [{**proposal, "worldId": "verdant-reach", "elements": ["grass"], "gameElement": "Grass"}])
    with pytest.raises(ValueError, match="one to three"):
        validate_designs(catalog, [{**proposal, "stages": [*proposal["stages"], {"stage": 4}]}])
