# Monster Creator Automation — Implementation Plan

Status: design specification only; implementation pending. This is a standalone, reusable asset factory, not a game or a web app. Build CLI-first in Python 3.11+ (or a newer supported version), with Pillow, Pydantic, pytest, and a pluggable image-generation backend. No Unity dependency in the core.

## 1. Non-negotiable visual contract
- Master reference: references/master_style.png, the user-approved water/fire sheet with all six creatures facing left. The owner must add this image before real generation; do not substitute arbitrary images. Record its SHA-256, style version, and rights provenance. Never silently change it.
- Match the reference's visual language: cute, expressive anime fantasy game creatures, large luminous eyes where biologically appropriate, rounded readable silhouettes, clean tapered colored outlines, layered smooth cel shading, saturated but controlled color, glossy elemental highlights, fine purposeful detail, soft cream accents where appropriate, professional sprite polish. Keep consistent light direction, contrast, line weights and rendering finish. Target close stylistic consistency, not a promise of pixel-perfect replication.
- Canonical pose: left-facing front three-quarter view (roughly 30–45 degrees toward viewer from side profile), nose/beak/front oriented screen-left, near eye and a portion of far side visible as anatomy allows. Match reference orientation; no right-facing, rear, top-down, straight front, extreme perspective or turnaround. For non-faced creatures define a leading anatomical feature. Mirroring is allowed only if it preserves intended asymmetric anatomy, lighting and markings; otherwise regenerate.
- Each family has exactly 3 stages by default and never more than 3; explicit stage counts 1 or 2 are supported. Stage 1 baby: round, adorable, simple; stage 2 adolescent: developed anatomy and elemental features; stage 3 final: majestic, mature, distinctive but still charming. Preserve species lineage, eye style, palette, signature markings, recurring motifs and meaningful anatomical continuity. No arbitrary species swaps or stage 4/5.
- Unique species across families: mammals, birds, reptiles, amphibians, fish, insects, arachnids, mollusks, crustaceans, plants/fungi, mythical or original fantasy organisms. Do not make every species a fox or dragon. Keep species-specific anatomy readable, e.g. insects with appropriate body segments/limbs, fish with fins, birds with wings, and crabs with claws. Fantastical changes must be intentional and documented.
- Elemental features should be integrated into anatomy and reflect physical properties, not just a recolor or generic floating aura. Keep permanent effects compact for readable battle silhouettes. Avoid heavy ground FX, opaque backgrounds, baked shadows, labels, frames, logos, UI, watermarks, cropped limbs, extra characters, duplicated limbs and fake checkerboards.
- True transparent RGBA PNG, one full-body creature per export, adequate padding, no text. Default source generation at high supported resolution; normalized Unity export 1024x1024 by default, optional 512/2048, no distortion or fake upscaling claims. Preserve aspect ratio; common family scale and pivot policy. Maintain visual growth across stages; hovering creatures use documented floating anchors, not invented legs. Separate optional family preview sheet from individual sprites.

## Aevareth integration: 25-world scope (required)

The initial target is the user's 25-world game: 24 campaign worlds and one final endless convergence world. World count and element count are distinct. Treat the local game repository/catalog as the authoritative source for world IDs, canonical element IDs, asset keys, hybrid components, and campaign/endless flags; never assume one world equals one element. Support the full catalog including single elements, multi-element hybrid worlds (including Psychic + Crystal and Light + Dark), and all-element convergence. Grass and Land must remain separate identities, and asset keys must be imported rather than guessed.

Add a read-only catalog importer accepting a local game checkout or explicitly supplied JSON manifest. Prefer the game’s authoritative adventure catalog and element registry; preserve IDs, ordering, element-component arrays, asset keys, and source revision/hash. Do not publish private source files or automatically write into the game repository. Generate a local coverage report of all 25 worlds with eligible monster families, missing designs, duplicate checks and planned counts; distinguish campaign worlds from endless world. The endless world must have its own seven dedicated families and may additionally reuse approved compatible families; do not require every monster to contain every element. Support future additions via data configuration. Apply the explicitly requested family quotas below; do not hard-code game progression or other rarity mechanics. Require all 25 worlds to resolve before declaring the Aevareth integration complete; if local catalog is unavailable, report the import as pending. Extend offline tests with a synthetic 25-world fixture, hybrid-component validation, distinct Grass/Land handling, and endless-world coverage. Preserve the maximum three-stage evolution and locked left-facing artwork style regardless of world.

## Mandatory monster population per world

Each of the 25 worlds (including the final endless world) must have exactly seven dedicated, unique monster families in its planned roster: five Wild, one Legendary, and one Guardian. Across 25 worlds this is 125 Wild + 25 Legendary + 25 Guardian = 175 families. Default to three evolution stages for all categories, never exceeding three, yielding a maximum of 525 individual stage sprites (375 Wild, 75 Legendary, 75 Guardian). Explicitly requested shorter lines may reduce the sprite count, not the required family count. Additional encounter reuse in the endless world does not count toward its seven dedicated families. Do not add Shop/Rare as a required roster category or alter the game itself.

Each family's canonical home world and category are immutable registry fields unless explicitly migrated; support stable family IDs, no duplicate family assignments across world quotas, element/component compatibility, and diverse species and silhouettes. The world roster planner should emit 25 world jobs, each with 5 Wild, 1 Legendary, 1 Guardian family briefs and stage counts; generate in resumable approved-budget batches rather than one giant paid call. Report planned/generated/approved/exported counts per world/category, missing slots, and duplicate families. Validate exact quotas and total family counts before claiming full coverage. Test the full roster fixture, missing/extra/duplicate family cases, hybrid compatibility, and the 3-stage limit. Wild monsters are cute and adventurous, Legendary monsters rare and mystical, Guardians majestic protectors; use distinctive anatomy, motifs and silhouettes rather than just size, palette or glow, while keeping the same master art style and left-facing three-quarter pose. Do not invent capture or battle mechanics in this art repository. Existing game IDs and approved art should be audited and preserved when mapping the roster; report mismatches without modifying the game.

## 2. Element and species catalog
Use configuration rather than hard-coded element counts. Seed examples (not a claim about any game's actual catalog):
- grass/nature: foliage, vines, bark, flowers, seed pods; deer, caterpillar, mantis
- land/earth: stone plates, clay, sand, minerals; armadillo, beetle, mole
- water: flowing translucent fins, droplets, wave-like markings; otter, axolotl, ray, seahorse
- fire: ember fur, flame crests, heat gradients, charred accents; fox, salamander, lion, moth
- air: cloudlike tufts, feather vanes, wind ribbons; owl, hummingbird, dragonfly
- electric: conductive quills, branching sparks, charged markings; hare, eel, firefly
- ice: frost crystals, translucent cold plates, pale facets; snow hare, seal, arctic bird
- dark: deep indigo, shadow membranes, restrained void accents; bat, raven, scorpion
- light: warm ivory/gold, radiant feather edges, prism glints; dove, moth, stag
- poison: venom glands, iridescence, warning markings, spore sacs; frog, viper, spider
- psychic: orbit motifs, thought-wave markings, violet/rose accents; octopus, cat, jellyfish
- crystal: faceted mineral growth and refracted light; gecko, beetle, snail
Support arbitrary single/hybrid elements, configurable primary/secondary palette and features, and documented blend logic. Hybrid species must express both elements without visual clutter. Import the actual game taxonomy via an explicit user-provided manifest instead of assuming these examples are exhaustive. Track species/silhouette diversity, avoid duplicate families and name collisions.

## 3. Proposed repository layout
    AGENTS.md
    PLAN.md
    README.md
    pyproject.toml
    .env.example
    .gitignore
    .agents/skills/monster-creator/SKILL.md
    references/master_style.png
    references/style_manifest.json
    config/style.yaml
    config/elements.yaml
    config/species.yaml
    schemas/family.schema.json
    prompts/family.md
    prompts/stage.md
    prompts/review.md
    src/monster_creator/{cli,catalog,prompting,pipeline,providers,qa,export,registry}.py
    tests/
    jobs/
    output/{drafts,approved,rejected,previews,unity}/
    docs/{art-bible,provenance,usage}.md

## 4. Workflow and architecture
1. Accept family request: element(s), species, concept, stage count (1–3), optional palette/traits, batch size and budget. Validate inputs, assign stable family ID, reserve unique concept and name in registry.
2. Create a family design brief with stage progression, anatomy, palette, distinctive motifs, left-facing pose, style reference and negative constraints. Save as JSON plus compiled prompts. Plan-only mode works offline.
3. Generate a coherent concept sheet for requested stages using approved master reference; if supported, generate individual stages using the master plus approved same-family concept/stage references. Never crop a grid blindly if details overlap. Preserve continuity between stages; prefer individual high-quality images for final export. A backend that supports reference-image inputs is required.
4. Use a provider interface with manual/Codex image-tool handoff and optional OpenAI Images API adapter. Codex is the orchestrator; check whether its current environment actually exposes image generation before using it. If not, use a separately configured, authorized API backend or manual image imports. Check official API docs for current model, sizes, transparency and editing options; no fabricated command or API. Never automate the ChatGPT website, bypass usage limits, or hardcode keys. API usage may be billed separately. Allow mock backend for tests only; never label mock outputs as generated art.
5. Persist raw images, request metadata, model identifier, reference hash, prompt version, request IDs, seed if available, actual costs if available and human review history. Resume idempotently after interruptions. Use bounded retries, rate limit handling, per-job request/token/cost ceilings, and explicit cost/batch opt-in before paid calls. Fail clearly if no provider/credentials; no endless loops.
6. Normalize RGBA via Pillow, measure alpha and bounds, preserve antialiasing, remove only confirmed background artifacts, avoid damaging translucent elemental features. Pad without stretching; calculate documented anchor, bounds and scale. Generate clean preview sheets and light/dark checkerboard QA previews only.
7. Run deterministic QA and visual QA separately. Deterministic: stage count, filename/ID uniqueness, valid dimensions and alpha channel, nonempty sprite, transparent border/padding, no clipping, file hashes, manifest completeness, duplicate hash detection. Visual: facing direction, anatomy, silhouette, no labels/watermark, element identity, stage continuity, style match, aesthetics, possible third-party resemblance. Use vision-assisted review if available, but require human approval for production; automated scores are advisory. No approval on missing visual evidence.
8. Retry failed stages only, use same reference and family brief, preserve accepted siblings. Keep rejected versions outside exports; version all accepted assets. Export only approved assets and never overwrite previous approvals silently.
9. Unity export: one front-left sprite per stage, Sprite (2D and UI), alpha transparency, consistent documented pivot; optionally create right-facing at runtime via flipX when asymmetric lighting/design allows. Output JSON manifest for import tooling and optional atlas; do not touch another game repo automatically. No back-view assets. Export filenames e.g. water_axolotl_001_s01.png, s02.png, s03.png. No animations in MVP.
10. Legal/provenance: use only owner-approved or properly licensed reference inputs; no prompts referencing named protected characters/franchises, logos, exact signature designs, or third-party asset copying. Review potentially similar designs and names, record source/provider terms and review decisions. Keep code license separate from image rights. Neither AI generation nor redesign guarantees copyright ownership, exclusivity or non-infringement. Do not publish unapproved art or secrets.

## 5. Proposed CLI (implement, then document actual commands)
    monster-creator init
    monster-creator doctor
    monster-creator plan --element water --species axolotl --stages 3
    monster-creator generate --element fire --species moth --stages 3 --max-cost <budget>
    monster-creator batch --manifest jobs/monsters.yaml --max-cost <budget>
    monster-creator import --job <id> --path <files>
    monster-creator validate --job <id>
    monster-creator review --job <id>
    monster-creator approve --job <id> --reviewer <name>
    monster-creator export --job <id> --format unity
    monster-creator resume --job <id>

Commands are a proposed interface, not working features yet. Support dry run, per-job resume, no paid requests by default in CI, structured logs and nonzero exit codes on hard failures.

## 6. Quality rubric
Score each stage/family 0–10 for style fidelity (25%), aesthetic polish/cuteness (20%), evolution continuity (20%), elemental expression (15%), species/anatomy originality (10%), sprite usability (10%). Target weighted 9/10; no category below 8, and hard constraints always pass. Scores are reviewer judgments rather than guarantees. Stage 3 must face left; any wrong-facing asset, missing stage, fake transparency, clipping, or unresolved IP concern blocks approval.

## 7. Implementation milestones and acceptance
- M0: audit repo, document official provider capabilities, install dependencies, owner adds master reference, freeze style contract.
- M1: config/schema, CLI, plan compiler, registry, reproducible job manifests, mock backend, unit tests.
- M2: provider adapters, manual handoff, budget guards, resume/retry, provenance.
- M3: sprite processing, technical/visual QA, review/approval, previews, Unity export.
- M4: pilot 3 different families (e.g. water axolotl, fire moth, electric hare), three stages each; review all 9 real sprites side-by-side against master. Include an insect with correct anatomy and test a hybrid request. Do not silently spend money; real generation depends on tool availability and authorized budget.
- M5: reusable Codex skill, docs, CI offline tests, safe batch pipeline and integration guide. CI must not make paid calls or commit generated images automatically.
- Acceptance: install and run CLI; deterministic mock pipeline tests pass; invalid stage 4 rejected; transparency and orientation QA examples documented; approved outputs export without alteration; resume does not duplicate calls; costs bounded; real pilot status reported honestly; no false success if reference/provider missing.
- Final handoff: README with setup, examples, provider choice, art bible, tests and results, limits, remaining blockers; commit logical changes, never force push or change unrelated projects. Keep PLAN.md progress and decisions current.
