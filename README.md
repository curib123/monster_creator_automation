# Monster Creator Automation

A planned reusable Codex-driven asset factory for original cute elemental monsters: one to three evolution stages, left-facing three-quarter poses, consistent premium anime fantasy artwork, transparent PNG exports.

**Current status:** planning documents only. No generation CLI or provider integration has been implemented yet.

## Get started in Codex

Clone the repository:

```sh
git clone https://github.com/curib123/monster_creator_automation.git
cd monster_creator_automation
```

Save the owner-approved water/fire artwork as `references/master_style.png`. This file is not included yet. Open the repository in Codex and instruct:

> Read AGENTS.md and PLAN.md and implement the complete monster creator automation system. Follow the locked art direction, maximum three-stage evolution, left-facing pose, and transparent sprite requirements. Implement offline tests first, verify real generation capability and only generate paid assets after authorization. Update the plan as you progress.

See [PLAN.md](PLAN.md) for architecture, element examples, proposed CLI, quality rubric and acceptance tests, and [the reusable skill](.agents/skills/monster-creator/SKILL.md) for future asset requests.

## Future usage

After implementation, request a family by element and species, e.g. "Create a water manta ray family, three stages, using the locked master reference." Review the result before exporting. The system must not change approved assets silently or claim guaranteed legal clearance.

Official references: https://developers.openai.com/api/docs/guides/image-generation and https://developers.openai.com/learn/codex.

**25-world integration:** Support 24 campaign worlds and one endless convergence world. Read the authoritative local game catalog and element registry, preserve distinct element IDs and asset keys, support hybrids and report coverage for every world. See PLAN.md. Never hard-code a one-world-per-element assumption.

**Mandatory world roster:** Exactly 5 Wild + 1 Legendary + 1 Guardian dedicated unique families per world, including the endless world. For 25 worlds: 125 Wild, 25 Legendary, 25 Guardian = 175 families; default 3 stages and maximum 3, up to 525 individual transparent sprites. Track quotas and category-specific design briefs; no duplicates across dedicated rosters. See PLAN.md. Do not assume generation is complete without approved outputs.

**Locked artwork reference:** The owner approved `Aqua and Flame Evolution Line(1).png` as the mandatory final artwork/style/texture target. Read `docs/art-bible.md` and verify `references/master_style.png` against `references/style_manifest.json` before generation. Use actual reference-image conditioning and compare all outputs visually to the master; reject style drift. The original PNG is still pending installation. Do not claim exact match or legal clearance automatically.

## Mandatory archetype and evolution contract

Only the following 15 base archetypes are permitted: Fox, Rabbit, Cat, Eagle, Phoenix, Dragon, Butterfly, Gecko, Bear, Manta Ray, Jellyfish, Ghost, Knight, Sorcerer, Magician. Each family must declare exactly one canonical archetype ID from config/species.yaml. No other species, arbitrary hybrids of base archetypes, or unapproved fantasy organisms. Elemental hybrids are allowed without changing the underlying archetype. All Wild, Legendary and Guardian families across all 25 worlds obey this rule. Archetypes necessarily repeat across 175 families; distinguish them by original silhouettes, proportions, poses within the fixed viewing angle, markings, materials, elemental anatomy and purposeful motifs. No duplicate family concepts. Existing out-of-scope families require an explicit migration plan, not silent deletion or reassignment.

Design a complete coherent family before generating individual stages. For each transition document the developmental reason, concrete silhouette/anatomy changes, elemental maturation, retained identity anchors, and how the stage is visually more satisfying. Scaling, recoloring, adding generic spikes/armor/aura/accessories, or merely enhancing the previous sprite is insufficient. Keep recognizable base anatomy, facial identity, elemental palette and signature motifs. Stage 1: cute, simple, soft and charming. Stage 2: meaningful developmental transition with new proportions, anatomy or elemental structures. Stage 3: the most beautiful, satisfying, enhanced and elegant final form, with a slimmer, cleaner, more streamlined silhouette, balanced proportions and intentional details. Slimness is relative to the archetype: do not make bears emaciated, rays narrow beyond recognition, or ghosts/humanoid creatures anatomically nonsensical. Maintain natural species-specific shape. Do not introduce a mandatory third stage to explicitly approved one- or two-stage lines; maximum three remains absolute.

Review the complete evolution lineup side-by-side against the locked master artwork before approval. Independently score evolution logic, continuity, meaningful stage differentiation, silhouette/proportions, aesthetics, cleanliness, and final-form payoff (when applicable) from 0–10. Require at least 9/10 overall for evolution and at least 8/10 in every applicable dimension; hard visual gates override numerical scores. Reject any weird, awkward, nonsensical, ugly, cluttered, disproportionate, broken-anatomy, repetitive, or unsatisfying family; reject later stages that are worse than earlier ones or are merely enlarged/decorated copies. Require actual visual evidence and explicit human family approval before production, export or Unity integration. Keep failed families in drafts/rejected, revise only affected stages if possible, re-review the entire lineage, never bypass gates to meet a quota. See docs/evolution-quality.md and config/species.yaml.
