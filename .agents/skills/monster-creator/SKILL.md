---
name: monster-creator
description: Plan, generate, validate, review, and export original cute elemental monster families with one to three left-facing stages in the repository's locked anime fantasy artwork style.
---

Read root AGENTS.md and PLAN.md. Use the reference image at references/master_style.png, not third-party franchise examples. Inspect and use the implemented CLI if present; if absent, implement from PLAN.md before claiming automation works.

## Workflow
1. Parse element(s), species, concept, count (default 3 stages, maximum 3), and budget. For unspecified species choose an unused, visually appropriate creature; choose a coherent original family concept.
2. Create a stable family brief: species anatomy, element-specific material and palette, shared markings, left-facing three-quarter pose, and progressively developed stages.
3. Compile prompts with locked reference, cute polished 2D anime fantasy rendering, full body, transparent background, no text or panels. Stage 1 simple baby, stage 2 developed, stage 3 majestic final. Use approved family images to maintain lineage when the backend supports reference input.
4. Check actual image tool availability and cost authorization. If unavailable, emit prompts and a pending job for manual import. Do not fabricate sprites. Retain request provenance.
5. Validate each stage's alpha, bounds, padding, count, anatomy, facing, art consistency, elemental readability and visual originality. Do not accept wrong-facing images. Retry only failed stages within budget.
6. Produce a preview for owner review. On explicit approval export individual RGBA PNGs, manifest, pivots and hashes using stable names. Keep rejected files and approved revisions separate.
7. Report generated vs pending counts, QA results, costs if known, file locations and blockers. Never imply legal clearance or exact style matching is guaranteed.

**25-world integration:** Support 24 campaign worlds and one endless convergence world. Read the authoritative local game catalog and element registry, preserve distinct element IDs and asset keys, support hybrids and report coverage for every world. See PLAN.md. Never hard-code a one-world-per-element assumption.

**Mandatory world roster:** Exactly 5 Wild + 1 Legendary + 1 Guardian dedicated unique families per world, including the endless world. For 25 worlds: 125 Wild, 25 Legendary, 25 Guardian = 175 families; default 3 stages and maximum 3, up to 525 individual transparent sprites. Track quotas and category-specific design briefs; no duplicates across dedicated rosters. See PLAN.md. Do not assume generation is complete without approved outputs.
