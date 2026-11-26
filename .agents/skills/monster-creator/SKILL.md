---
name: monster-creator
description: Plan, generate, review, resume, export, or import original elemental monster evolution sprites for Aevareth using its game catalog and locked master artwork.
---

Use the automation checkout as the working directory for `monster-creator` commands. When invoked from Aevareth, locate the sibling `monster_creator_automation` checkout. Read its `AGENTS.md`, `PLAN.md`, and `docs/art-bible.md`. Use the [production commands](../../../README.md) for exact inputs and the Aevareth `docs/monster-batches.md` handoff for Unity.

## Plan and resume

- Synchronize the saved Aevareth catalog, then match the requested world, element combination, family or category to its actual IDs. Prepare only the requested briefs. For ad hoc designs, plan a distinct species and lineage with useful differences between stages. Use a compatible world for draft context. A full roster leaves the new concept as a separate draft until an art production slot is authorized.
- Preserve existing family IDs, stage identities and assigned worlds. Surface missing roster slots, ambiguous hybrid components and authored gameplay constraints. Track five Wild, one Legendary and one Guardian per world in the plan, with one to three stages per family.
- Prepare the family briefs once in the active checkpoint workspace. Use `resume` to read pending requests and recover any in-flight attempt before asking the provider again. For validation, resolve the world in the catalog, check the existing game sprites against the canonical manifest, and separately run `validate --world ID` for candidate checkpoints. Report zero candidate jobs or missing evidence explicitly. A catalog or byte check alone does not establish visual quality.

## Generate and review

- Run `doctor` before requesting imagery. The exact owner-approved master must pass its SHA-256 and PNG checks. If it is missing, keep the briefs and checkpoints and report the missing file.
- Use the built-in Codex image-generation tool, one call for each requested stage attempt. Load the verified master as an actual tool input and attach any previously accepted family reference supplied by the request. In Codex CLI, initial attachments are available through `-i`. Use the compiled prompt and request true PNG transparency. Confirm the image tool actually received the references before recording provenance. When the built-in tool is unavailable, leave a manual reference-based handoff pending. An external paid provider requires separate authorization.
- Use the emitted request ID and verified reference hashes for ingestion. Persist each raw image and receipt before continuing. Open the visual comparison and inspect the full-resolution sprite, the master and neighboring family stages. Record specific observations and a truthful rubric score for facing, anatomy, elemental identity, linework, shading, texture and evolution continuity. An opaque export, wrong-facing sprite, anatomy error, elemental mismatch, style drift or score below the gate requires revision. Use the next attempt only for that stage and stop at the job's attempt limit.
- Keep visually passing candidates available for owner review. Record approval only from the owner's explicit decision. Export only approved work. Before a mass run or replacement of any production art, obtain the owner's explicit authorization for that action. Validate the export through the game's existing reviewed-family importer before any authorized import.
