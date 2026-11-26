# Monster Creator Automation plan

This repository owns the Python 3.11+ artwork workflow. Codex orchestrates a
reference-capable image tool. Aevareth owns its saved monster catalog, gameplay,
and reviewed-family Unity importer. The [README](README.md) documents the
commands implemented here.

## Artwork and evolution

Reference version 2.0.0 is the exact owner-supplied
`master_style_three_elements_stages_1-3.png` at `references/master_style.png`.
Its [manifest](references/style_manifest.json) locks the file and its metadata.
The [art bible](docs/art-bible.md) translates the reference's material finish,
layered lighting, expressive faces, and stage proportions into a practical
sprite standard. Production uses verified image conditioning.

Every original family declares one of the 15 archetypes in
[`config/species.yaml`](config/species.yaml). A family's distinct anatomy,
proportions, markings, visual motifs, and elemental materials support its
recognizable base identity. Default to three stages and accept one or two
explicitly scoped stages. Keep early forms charming and simple, middle forms
meaningfully developed, and third forms streamlined with natural anatomy.
Describe what develops, why it develops, and which identity cues carry across
stages. Each sprite shows a complete body in left-facing front three-quarter
view on a transparent RGBA PNG canvas.

## Aevareth roster

Read Aevareth's saved data locally for world IDs, elemental component IDs,
Unity asset keys, and source revision. Preserve Grass and Land as distinct
elements. Support mixed worlds, including Psychic + Crystal and Light + Dark,
and a convergence world with a separate endless flag. Keep the catalog
read-only and surface gaps in saved data.

| Scope | Wild | Legendary | Guardian | Total families |
| --- | ---: | ---: | ---: | ---: |
| Each world | 5 | 1 | 1 | 7 |
| All 25 worlds | 125 | 25 | 25 | 175 |

The 24 campaign worlds and one endless convergence world each receive seven
dedicated families. The maximum is 525 sprites, and shorter lines reduce
sprite count only. Reused encounters in the endless world do not fill its
dedicated slots. Keep stable family IDs, stage identities, category assignments,
and world mappings. Track proposed roster coverage independently of finished art
and game encounter availability. Keep unclassified or incompatible inherited
art in the catalog and report it for review before making any replacement.

## Production workflow

1. Synchronize the catalog, check world quotas, and prepare a focused family
   brief. Save the approved archetype, shared identity cues, elemental design,
   and individual developmental rationale for each later stage.
2. Run the master check. Reserve a durable attempt, export the compiled
   prompt and image references to the tool, and retain the raw response with
   the provider receipt. Use a manual reference-based handoff if needed.
   Keep request IDs and reported model/cost data. A paid provider requires an
   authorized budget.
3. Run Pillow checks and normalize aspect ratio, padding and pivot. Preserve
   alpha antialiasing and intentional translucency. Use 1024-pixel exports
   by default (512 and 2048 are also supported), and follow the game's
   canvas requirements before Unity import.
4. Inspect every candidate against the master and the complete lineup. Apply
   the [quality gate](docs/evolution-quality.md), with a minimum of 9/10 overall,
   8/10 per applicable dimension and a pass on all hard visual checks.
5. Resume interrupted attempts by request ID. Keep raw and rejected history and
   retry the affected stages within their budgets. Recheck the lineup after
   any change. Keep work pinned to the reference and prompt versions that
   produced it. Mark superseded evidence and incompatible artwork for revision.
6. Record the owner's explicit approval of the current lineup, then export the
   approved PNGs, pivots, hashes and evidence. Aevareth's explicit import
   workflow handles validated adoption. Obtain separate authorization before
   replacing existing artwork or starting mass generation.

## Validation and rollout

- Run the offline fixtures in `tests/` and the CLI master check. Fixtures
  exercise catalog/roster constraints, prompt rules, resume and retry,
  transparency, review receipts and export without making image tool calls.
- Reassess prior generated candidate art against reference 2.0.0 without
  rewriting historical receipts or replacing existing game files.
- Generate a small pilot with the new master when a reference-capable tool
  is available. Present the pilot for owner visual approval before planning
  any production run. Report image generation and visual approval as
  independent results.
