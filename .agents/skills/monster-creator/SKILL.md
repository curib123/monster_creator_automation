---
name: monster-creator
description: Plan, generate, review, resume, export, or import original elemental monster evolution sprites for Aevareth using its game catalog and locked master artwork.
---

Use the automation checkout for `monster-creator` commands. When invoked from
Aevareth, locate the sibling `monster_creator_automation` checkout. Read its
`AGENTS.md`, `PLAN.md`, [art bible](../../../docs/art-bible.md), and
[evolution quality gate](../../../docs/evolution-quality.md). Follow the
[command examples](../../../README.md) and the game's `docs/monster-batches.md`
for the reviewed-family Unity handoff.

## Plan and resume

- Synchronize the saved Aevareth catalog and match the requested world,
  elements, family or category to its actual IDs. Prepare only the requested
  briefs. Choose one canonical archetype from `config/species.yaml` for every
  draft. Preserve inherited IDs and artwork. Flag an incompatible or
  ambiguous inherited family for revision rather than assigning it a new
  archetype without a visual assessment.
- Preserve stage identities and home worlds. Record missing roster slots,
  ambiguous hybrid components and authored gameplay constraints. Each world
  has five Wild, one Legendary and one Guardian slots. An ad hoc design can
  remain a draft when the world is full.
- Write a cohesive lineup before generation. Carry identity anchors through
  each stage. Give every transition an anatomical reason, an elemental
  maturation cue and a better-balanced silhouette. Aim for a cute Stage 1,
  distinct developing Stage 2, and streamlined, archetype-appropriate Stage 3.
  Use one to three stages for each brief.
- Prepare briefs once in the active checkpoint workspace. Use `resume` to
  recover in-flight work and inspect pending requests before using the image
  tool again. For a world audit, check the saved game manifest and separately
  run `validate --world ID` for candidate checkpoints. Record coverage and
  visual findings from the actual images.

## Generate and review

- Run `doctor` and use the exact verified master as an image input. For each
  reserved stage attempt, use the compiled prompt and any requested family
  reference. In Codex CLI, use `-i` to attach an image at launch. Confirm
  actual image input use before recording provenance. A reference-capable
  manual handoff can keep work pending when the built-in tool is unavailable.
  Paid use requires a separate approved budget.
- Use the emitted request ID and verified reference hashes for ingestion.
  Persist each raw output and receipt before continuing. Open the full
  lineup and inspect every sprite at its original resolution against the
  locked master and on light and dark backgrounds. Record observations and
  scores under the current visual gate. Reject a broken lineage, visual style
  drift, false alpha, confusing archetype, wrong-facing pose, or weak final
  form even when other dimensions score well.
- Retry only the failing stages within the job's limit and reevaluate the
  complete lineup. With explicit continuation of an exhausted stage, use
  `extend-retry` with a specific corrective approach, up to 10 total attempts
  for that stage. Inspect each new result before continuing.
- Present candidates to the owner for explicit whole-family visual approval
  before exporting. Keep pilot drafts outside the production pipeline until
  that decision. Obtain separate authorization for mass production and for
  replacing existing game art. Validate any authorized export with the
  game's existing reviewed-family importer.
