"""Read the saved Aevareth catalog and plan dedicated artwork rosters."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from .roster_designs import ORIGIN_ELEMENTS, PROPOSED_HYBRIDS, ROSTER_DESIGNS
from .verdant import VERDANT_DESIGNS

PROJECT = Path("Assets/_Aevareth_Monster_Realm")
QUOTAS = {"Wild": 5, "Legendary": 1, "Guardian": 1}
MONSTER_TYPES = {"Wild": "Common", "Legendary": "Legendary", "Guardian": "AncientGuardian"}
GUID = r"guid: ([0-9a-f]{32})"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def field(source, name):
    match = re.search(rf"^  {name}:[ \t]*([^\n]*)", source, re.M)
    require(match is not None, f"Missing Unity field {name}")
    value = match[1].strip()
    if value.startswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def object_list(source, name):
    match = re.search(rf"^  {name}:[^\n]*\n((?:  - [^\n]*\n)*)", source, re.M)
    require(match is not None, f"Missing Unity object array {name}")
    guids = re.findall(GUID, match[1])
    require(len(guids) == len(match[1].splitlines()), f"Unresolved Unity reference in {name}")
    return guids


def clr_enum(source, name):
    match = re.search(rf"\benum {name}\s*{{([^}}]+)}}", source, re.S)
    require(match is not None, f"Missing {name} enum")
    values = {}
    for entry in match[1].strip().rstrip(",").split(","):
        pair = re.fullmatch(r"\s*(\w+)\s*=\s*(\d+)\s*", entry)
        require(pair is not None, f"Unsupported value in {name}: {entry.strip()}")
        require(int(pair[2]) not in values, f"Duplicate serialized value in {name}: {pair[2]}")
        values[int(pair[2])] = pair[1]
    return values


def unique(rows, key, kind):
    pairs = [(row[key], row) for row in rows]
    result = dict(pairs)
    require(len(result) == len(pairs), f"Duplicate {kind} {key}")
    return result


def checkout_catalog(root):
    root = Path(root).resolve()
    files = {}

    def read(path):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        files[relative] = hashlib.sha256(data).hexdigest()
        return data.decode("utf-8-sig").replace("\r\n", "\n")

    def find_assets(directory):
        indexed = {}
        for path in sorted(directory.rglob("*.asset")):
            source = read(path)
            metadata = read(path.with_suffix(".asset.meta"))
            match = re.search(r"^" + GUID + "$", metadata, re.M)
            require(match and match[1] not in indexed, f"Missing or duplicate asset GUID: {path}")
            indexed[match[1]] = (path, source)
        return indexed

    project = root / PROJECT
    adventure = project / "Data/Adventure"
    definition_code = read(project / "Runtime/Adventure/Monsters/MonsterDefinition.cs")
    element_code = read(project / "Runtime/Adventure/World/Elements.cs")
    values = clr_enum(definition_code, "MapElement")
    types = clr_enum(definition_code, "MonsterType")
    effectiveness = json.loads(read(project / "Resources/Aevareth/Adventure/ElementEffectiveness.json"))
    require({row["element"] for row in effectiveness["elements"]} == set(values.values()),
            "MapElement enum and element registry disagree")
    asset_key = re.search(r"public static string AssetKey\b.+?\n        }", element_code, re.S)
    require(asset_key and "element.ToString().ToLowerInvariant()" in asset_key[0],
            "Elements.AssetKey no longer uses the supported mapping")
    aliases = dict(re.findall(r'MapElement\.(\w+)\s*\?\s*"([a-z0-9-]+)"', asset_key[0]))
    elements = [
        {"id": name.lower(), "gameElement": name, "assetKey": aliases.get(name, name.lower()), "value": number}
        for number, name in sorted(values.items())
    ]
    elements_by_id = unique(elements, "id", "element")

    catalog = read(project / "Resources/Aevareth/Adventure/RealmAdventureCatalog.asset")
    map_assets = find_assets(adventure / "Maps")
    monster_assets = find_assets(adventure / "Monsters")
    definitions = {}
    for guid, (path, source) in monster_assets.items():
        family_id = field(source, "Id")
        require(re.fullmatch(SLUG, family_id) is not None, f"Invalid family ID in {path}: {family_id}")
        description = re.search(r"^  FamilyDescription:[^\S\n]*([^\n]*(?:\n    [^\n]*)*)", source, re.M)
        retired = re.search(r"^  IsRetired: 1\s*$", source, re.M) is not None
        definitions[guid] = {
            "familyId": family_id,
            "displayName": field(source, "DisplayName"),
            "description": " ".join(description[1].split()) if description else "",
            "element": values[int(field(source, "Element"))].lower(),
            "monsterType": types[int(field(source, "Type"))],
            "retired": retired,
            "definitionAsset": path.relative_to(root).as_posix(),
        }
    by_family = unique(definitions.values(), "familyId", "MonsterDefinition")
    worlds = []
    for guid in object_list(catalog, "Worlds"):
        require(guid in map_assets, f"Catalog world GUID does not resolve: {guid}")
        path, source = map_assets[guid]
        raw_components = bytes.fromhex(field(source, "ConvergingElements"))
        require(len(raw_components) % 4 == 0, f"Invalid packed ConvergingElements in {path}")
        components = [values[number].lower() for (number,) in struct.iter_unpack("<i", raw_components)]
        pool = object_list(source, "EncounterPool")
        require(all(ref in definitions for ref in pool), f"Unresolved family in encounter pool: {path}")
        worlds.append({
            "id": field(source, "Id"),
            "displayName": field(source, "DisplayName"),
            "element": values[int(field(source, "Element"))].lower(),
            "components": components,
            "endless": field(source, "IsEndless") == "1",
            "encounterPool": [definitions[ref]["familyId"] for ref in pool],
            "mapAsset": path.relative_to(root).as_posix(),
        })

    manifest_path = project / "Art/Monsters/manifest.json"
    manifest = json.loads(read(manifest_path))
    rows = unique(manifest["monsters"], "id", "art family")
    files_missing = []
    families = []
    for family_id, definition in by_family.items():
        row = rows.get(family_id, {})
        asset_key = elements_by_id[definition["element"]]["assetKey"]
        require(not row or row["element"] == asset_key, f"Artwork element differs from MonsterDefinition: {family_id}")
        stages = []
        for stage in row.get("stages", []):
            path = stage["assets"].get("canonical") or stage["assets"]["front"]
            target = (root / path).resolve()
            require(target.is_relative_to(project / "Art/Monsters"), f"Noncanonical sprite path for {family_id}: {path}")
            exists = target.is_file()
            if not exists:
                files_missing.append(path)
            stages.append({
                "stage": stage["stage"],
                "name": stage["name"],
                "title": stage["title"],
                "asset": path,
                "ready": bool(stage.get("ready", False) and exists),
                "sha256": stage.get("inspection", {}).get("canonical", {}).get("sha256"),
            })
        families.append({
            **definition,
            "worldId": row.get("guardianWorldId") or row.get("worldId"),
            "identitySource": row.get("identitySource"),
            "stages": stages,
        })
    require(set(rows).issubset(by_family), f"Manifest families without MonsterDefinitions: {sorted(set(rows) - set(by_family))}")

    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    snapshot = {
        "schemaVersion": 1,
        "source": {
            "revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        },
        "elements": elements,
        "worlds": worlds,
        "families": families,
        "missingSpriteFiles": files_missing,
    }
    validate_catalog(snapshot)
    return snapshot


def validate_catalog(catalog):
    require(catalog.get("schemaVersion") == 1, "Unsupported catalog schema")
    elements = unique(catalog["elements"], "id", "element")
    unique(catalog["elements"], "value", "element")
    unique(catalog["elements"], "assetKey", "element")
    worlds = unique(catalog["worlds"], "id", "world")
    families = unique(catalog["families"], "familyId", "family")
    require(len(elements) == 19 and {"grass", "land", "hybrid"} <= elements.keys(),
            "Expected the 19 Aevareth classifications including Grass, Land, and Hybrid")
    require(len(worlds) == 25 and [w["endless"] for w in worlds.values()] == [False] * 24 + [True],
            "Expected 24 campaign worlds followed by one endless world")
    for world in worlds.values():
        world_id = world["id"]
        components = world["components"]
        require(world["element"] in elements, f"Unknown world element: {world_id}")
        require(len(components) == len(set(components)) and set(components) <= elements.keys() - {"hybrid"},
                f"Invalid hybrid components: {world_id}")
        require(not components or (world["element"] == "hybrid" and len(components) >= 2),
                f"Invalid hybrid world: {world_id}")
        require(not world["endless"] or (world["element"] == "hybrid" and set(components) == elements.keys() - {"hybrid"}),
                f"Endless world must include every individual element: {world_id}")
        require(set(world["encounterPool"]) <= families.keys(), f"Unknown family in encounter pool: {world_id}")
    for family in families.values():
        require(family["element"] in elements, f"Unknown family element: {family['familyId']}")
        require(not family["worldId"] or family["worldId"] in worlds, f"Unknown family world: {family['familyId']}")
    return catalog


def home_assignments(catalog):
    habitats = defaultdict(list)
    element_worlds = defaultdict(list)
    for world in catalog["worlds"]:
        for family_id in world["encounterPool"]:
            habitats[family_id].append(world["id"])
        if world["element"] != "hybrid":
            element_worlds[world["element"]].append(world["id"])
    assigned = defaultdict(list)
    unassigned = []
    for family in catalog["families"]:
        category = next((key for key, kind in MONSTER_TYPES.items() if kind == family["monsterType"]), None)
        if not category or family["retired"]:
            continue
        home = family["worldId"]
        source = "manifest"
        if not home:
            candidates = habitats[family["familyId"]] or element_worlds[family["element"]]
            source = "encounter pool" if habitats[family["familyId"]] else "unique element world"
            home = candidates[0] if len(candidates) == 1 else None
        if home:
            assigned[home].append({**family, "category": category, "worldId": home, "worldSource": source})
        else:
            unassigned.append(family["familyId"])
    return assigned, unassigned


def coverage(catalog, designs=()):
    assigned, unassigned = home_assignments(catalog)
    new_by_world = defaultdict(list)
    for design in designs:
        new_by_world[design["worldId"]].append(design)
    worlds = []
    for world in catalog["worlds"]:
        home = world["id"]
        existing = assigned[home]
        new = new_by_world[home]
        counts = Counter(row["category"] for row in existing)
        proposed = Counter(row["category"] for row in new)
        existing_ids = {row["familyId"] for row in existing}
        existing_stages = sum(len(row["stages"]) for row in existing)
        components_unspecified = world["element"] == "hybrid" and not world["components"]
        worlds.append({
            **world,
            "roster": [{"familyId": row["familyId"], "category": row["category"],
                        "worldSource": row["worldSource"], "readyStages": sum(stage["ready"] for stage in row["stages"])}
                       for row in existing],
            "plannedNewFamilies": [row["familyId"] for row in new],
            "eligibleReusedFamilies": [family for family in world["encounterPool"] if family not in existing_ids],
            "existingFamilies": dict.fromkeys(QUOTAS, 0) | dict(counts),
            "plannedFamilies": {category: counts[category] + proposed[category] for category in QUOTAS},
            "existingStages": existing_stages,
            "plannedStages": existing_stages + sum(len(row["stages"]) for row in new),
            "missingExistingFamilies": {category: max(0, quota - counts[category]) for category, quota in QUOTAS.items()},
            "missingDesignSlots": {category: max(0, quota - counts[category] - proposed[category])
                                   for category, quota in QUOTAS.items()},
            "excessFamilies": {category: max(0, counts[category] + proposed[category] - quota)
                               for category, quota in QUOTAS.items()},
            "componentsUnspecified": components_unspecified,
            "proposedComponents": sorted({element for row in new for element in row["elements"]})
            if components_unspecified else [],
        })
    return {
        "source": catalog["source"],
        "worldCount": len(worlds),
        "elementCount": len(catalog["elements"]),
        "targets": {category: quota * len(worlds) for category, quota in QUOTAS.items()},
        "targetFamilies": sum(QUOTAS.values()) * len(worlds),
        "maximumSprites": 3 * sum(QUOTAS.values()) * len(worlds),
        "existingCatalogFamilies": len(catalog["families"]),
        "existingDedicatedFamilies": sum(sum(row["existingFamilies"].values()) for row in worlds),
        "existingReadySprites": sum(stage["ready"] for family in catalog["families"] for stage in family["stages"]),
        "plannedNewFamilies": len(designs),
        "plannedFamilies": sum(sum(row["plannedFamilies"].values()) for row in worlds),
        "plannedStages": sum(row["plannedStages"] for row in worlds),
        "missingDesignSlots": sum(sum(row["missingDesignSlots"].values()) for row in worlds),
        "missingSpriteFiles": catalog.get("missingSpriteFiles", []),
        "unassignedFamilies": unassigned,
        "worlds": worlds,
    }


def choose_world(catalog, selector):
    matches = [row for index, row in enumerate(catalog["worlds"], 1)
               if selector.casefold() in {row["id"].casefold(), row["displayName"].casefold(), str(index)}]
    require(len(matches) == 1, f"Unknown or ambiguous world: {selector}")
    return matches[0]


def default_designs(catalog):
    assigned, _ = home_assignments(catalog)
    elements = {row["id"]: row["gameElement"] for row in catalog["elements"]}
    proposals = []
    for world in catalog["worlds"]:
        home = world["id"]
        counts = Counter(row["category"] for row in assigned[home])
        choices = dict(zip(QUOTAS, ROSTER_DESIGNS.get(home, ())))
        for category, candidates in choices.items():
            candidates = candidates if category == "Wild" else (candidates,)
            open_count = QUOTAS[category] - counts[category]
            for name, species, motif, *beats in candidates:
                family_id = name.lower()
                if open_count <= 0 or any(row["familyId"] == family_id for row in assigned[home]):
                    continue
                open_count -= 1
                components = world["components"] or PROPOSED_HYBRIDS.get(home) or [world["element"]]
                component_source = "proposed" if world["element"] == "hybrid" and not world["components"] else "catalog"
                if world["endless"]:
                    components = ORIGIN_ELEMENTS[name]
                if components == ["hybrid"]:
                    raise ValueError(f"Supply explicit proposed hybrid components for {home}")
                element = "hybrid" if len(components) > 1 else components[0]
                proposals.append({
                    "familyId": family_id,
                    "displayName": name,
                    "description": motif,
                    "species": species,
                    "worldId": home,
                    "category": category,
                    "gameElement": elements[element],
                    "monsterType": MONSTER_TYPES[category],
                    "isNewFamily": True,
                    "elements": list(components),
                    "componentSource": component_source,
                    "stages": [{"stage": number, "name": name, "title": title,
                                "description": f"Show {beat}. {motif}"}
                               for number, (title, beat) in enumerate(zip(("Young", "Growing", "Mature"), beats, strict=True), 1)],
                })
    return validate_designs(catalog, proposals)


def validate_designs(catalog, designs):
    ids = {row["familyId"] for row in catalog["families"]}
    names = {row["displayName"].casefold() for row in catalog["families"]}
    elements = {row["id"]: row["gameElement"] for row in catalog["elements"]}
    worlds = unique(catalog["worlds"], "id", "world")
    assigned, _ = home_assignments(catalog)
    counts = {home: Counter(row["category"] for row in rows) for home, rows in assigned.items()}
    for design in designs:
        family_id = design["familyId"]
        name = design["displayName"].casefold()
        require(family_id not in ids and re.fullmatch(SLUG, family_id) is not None and name not in names,
                f"New family ID or name conflicts with the catalog: {family_id}")
        home = design["worldId"]
        require(home in worlds, f"Unknown world for {family_id}: {home}")
        category = design["category"]
        require(category in QUOTAS and design["monsterType"] == MONSTER_TYPES[category] and design["isNewFamily"] is True,
                f"Invalid production category for {family_id}")
        count = counts.setdefault(home, Counter())
        count[category] += 1
        require(count[category] <= QUOTAS[category], f"{home} exceeds its {category} quota")

        world = worlds[home]
        supplied = design["elements"]
        element = next((key for key, label in elements.items() if label == design["gameElement"]), None)
        require(supplied and len(supplied) == len(set(supplied)) and set(supplied) <= elements.keys() - {"hybrid"},
                f"Unknown, repeated, or missing elements: {family_id}")
        require((element == "hybrid" and len(supplied) >= 2) or supplied == [element],
                f"Element components disagree with the Unity classification: {family_id}")
        if world["element"] != "hybrid":
            require(supplied == [world["element"]], f"Wrong world element: {family_id}")
        elif world["endless"]:
            require(set(supplied) <= set(world["components"]), f"Element outside the convergence: {family_id}")
        else:
            require(element == "hybrid" and (not world["components"] or set(supplied) == set(world["components"])),
                    f"Wrong world hybrid: {family_id}")
        stages = design["stages"]
        require(1 <= len(stages) <= 3 and [row["stage"] for row in stages] == list(range(1, len(stages) + 1)),
                f"Expected one to three sequential stages: {family_id}")
        require(all(isinstance(design[key], str) and design[key].strip() for key in ("description", "species"))
                and all(all(isinstance(row[key], str) and row[key].strip() for key in ("name", "title", "description"))
                        for row in stages), f"Missing visual design brief: {family_id}")
        ids.add(family_id)
        names.add(name)
    return designs


def existing_brief(row, world, elements):
    family_id = row["familyId"]
    if family_id not in VERDANT_DESIGNS:
        return None
    species, design, notes = VERDANT_DESIGNS[family_id]
    stages = row["stages"]
    require(len(stages) == len(notes), f"Existing stage count changed for {family_id}")
    return {
        "familyId": family_id,
        "displayName": row["displayName"],
        "description": row["description"],
        "worldId": world["id"],
        "gameElement": elements[row["element"]],
        "category": row["category"],
        "monsterType": row["monsterType"],
        "isNewFamily": False,
        "species": species,
        "elements": world["components"] or [row["element"]],
        "design": design,
        "stages": [{**{key: stage[key] for key in ("stage", "name", "title")},
                    "description": note,
                    **({"anchor": "floating"} if (family_id == "kodorei" or family_id == "leafkit" and stage["stage"] == 3) else {})}
                   for stage, note in zip(stages, notes, strict=True)],
        "existingStages": stages,
        "identitySource": row["identitySource"],
    }


def plan(catalog, worlds, designs):
    validate_designs(catalog, designs)
    assigned, _ = home_assignments(catalog)
    elements = {row["id"]: row["gameElement"] for row in catalog["elements"]}
    report = coverage(catalog, designs)
    coverage_by_world = {row["id"]: row for row in report["worlds"]}
    jobs = []
    families = []
    for world in worlds:
        home = world["id"]
        approved = []
        for existing in assigned[home]:
            brief = existing_brief(existing, world, elements)
            if brief is not None:
                families.append(brief)
            else:
                approved.append(existing["familyId"])
        additions = [row for row in designs if row["worldId"] == home]
        families.extend(additions)
        jobs.append({
            "worldId": home,
            "existingFamiliesWithoutDraftBrief": approved,
            "familyIds": [row["familyId"] for row in families if row["worldId"] == home],
            "existingFamilies": coverage_by_world[home]["existingFamilies"],
            "plannedFamilies": coverage_by_world[home]["plannedFamilies"],
            "missingDesignSlots": coverage_by_world[home]["missingDesignSlots"],
            "excessFamilies": coverage_by_world[home]["excessFamilies"],
        })
    return {"schemaVersion": 1, "source": catalog["source"], "worlds": jobs, "families": families}


def catalog_source(args):
    snapshot = checkout_catalog(args.game) if args.game else validate_catalog(load_json(args.input))
    path = save_json(args.output, snapshot)
    report = coverage(snapshot)
    return {"catalog": str(path), **{key: report[key] for key in (
        "source", "worldCount", "elementCount", "existingCatalogFamilies",
        "existingDedicatedFamilies", "existingReadySprites", "missingDesignSlots", "missingSpriteFiles",
    )}}


def read_designs(args, catalog):
    if args.designs is None:
        return default_designs(catalog)
    data = load_json(args.designs)
    return validate_designs(catalog, data["families"] if isinstance(data, dict) else data)


def catalog_coverage(args):
    catalog = validate_catalog(load_json(args.catalog))
    report = coverage(catalog, read_designs(args, catalog))
    if args.output:
        save_json(args.output, report)
    return report


def catalog_plan(args):
    catalog = validate_catalog(load_json(args.catalog))
    worlds = catalog["worlds"] if args.all else [choose_world(catalog, args.world)]
    roster = plan(catalog, worlds, read_designs(args, catalog))
    require(not args.require_complete or all(not any(row["missingDesignSlots"].values()) and
                                            not any(row["excessFamilies"].values()) for row in roster["worlds"]),
            "Roster coverage is incomplete; inspect catalog coverage for missing or excess families")
    path = save_json(args.output, roster)
    return {"plan": str(path), "worlds": roster["worlds"], "draftFamilies": len(roster["families"]),
            "draftSprites": sum(len(family["stages"]) for family in roster["families"])}


def add_commands(subparsers):
    catalog = subparsers.add_parser("catalog", help="Synchronize and plan the Aevareth monster roster")
    commands = catalog.add_subparsers(required=True)
    sync = commands.add_parser("sync", help="Read the local Unity checkout or a saved JSON catalog")
    sources = sync.add_mutually_exclusive_group(required=True)
    sources.add_argument("--game", type=Path)
    sources.add_argument("--input", type=Path)
    sync.add_argument("--output", type=Path, required=True)
    sync.set_defaults(handler=catalog_source)

    report = commands.add_parser("coverage", help="Report existing families and missing categories")
    report.add_argument("--catalog", required=True, type=Path)
    report.add_argument("--designs", type=Path, help="Explicit briefs in place of the bundled open-slot proposals")
    report.add_argument("--output", type=Path)
    report.set_defaults(handler=catalog_coverage)

    planner = commands.add_parser("plan", help="Compile existing and proposed artwork briefs")
    planner.add_argument("--catalog", required=True, type=Path)
    planner.add_argument("--designs", type=Path, help="Explicit briefs in place of the bundled open-slot proposals")
    selection = planner.add_mutually_exclusive_group(required=True)
    selection.add_argument("--world", help="World ID, display name, or campaign order number")
    selection.add_argument("--all", action="store_true")
    planner.add_argument("--output", required=True, type=Path)
    planner.add_argument("--require-complete", action="store_true")
    planner.set_defaults(handler=catalog_plan)
