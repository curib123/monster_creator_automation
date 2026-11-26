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

After implementation, request a family by element and species, e.g. "Create a water axolotl family, three stages, using the locked master reference." Review the result before exporting. The system must not change approved assets silently or claim guaranteed legal clearance.

Official references: https://developers.openai.com/api/docs/guides/image-generation and https://developers.openai.com/learn/codex.

**25-world integration:** Support 24 campaign worlds and one endless convergence world. Read the authoritative local game catalog and element registry, preserve distinct element IDs and asset keys, support hybrids and report coverage for every world. See PLAN.md. Never hard-code a one-world-per-element assumption.

**Mandatory world roster:** Exactly 5 Wild + 1 Legendary + 1 Guardian dedicated unique families per world, including the endless world. For 25 worlds: 125 Wild, 25 Legendary, 25 Guardian = 175 families; default 3 stages and maximum 3, up to 525 individual transparent sprites. Track quotas and category-specific design briefs; no duplicates across dedicated rosters. See PLAN.md. Do not assume generation is complete without approved outputs.

**Locked artwork reference:** The owner approved `Aqua and Flame Evolution Line(1).png` as the mandatory final artwork/style/texture target. Read `docs/art-bible.md` and verify `references/master_style.png` against `references/style_manifest.json` before generation. Use actual reference-image conditioning and compare all outputs visually to the master; reject style drift. The original PNG is still pending installation. Do not claim exact match or legal clearance automatically.
