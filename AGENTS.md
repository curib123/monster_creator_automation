# Instructions for Codex

Read PLAN.md before implementing or generating any monster. Treat its visual contract as mandatory. The root repository is a reusable monster asset factory.

- Maximum 3 evolution stages, default 3; all left-facing front three-quarter view. Keep individual transparent RGBA sprites and same family visual identity.
- Use references/master_style.png as the locked owner-approved artwork reference. If missing, fail clearly for real generation and continue offline implementation/testing; never substitute another style.
- Vary animal, insect, plant and fantasy anatomy and elemental properties. Preserve the master rendering language; do not reproduce third-party characters.
- Use a real authorized image-generation tool/API or manual handoff; do not fabricate outputs or claim mock art is production. Verify the current provider capabilities in official docs. Do not automate website usage or circumvent limits.
- Do not spend money without an explicit budget and authorization. Never commit credentials. Keep rejected assets out of exports. Human visual approval required.
- Read .agents/skills/monster-creator/SKILL.md for asset jobs. Keep PLAN.md current; run tests and report blockers. Do not modify unrelated game repositories or overwrite approved assets without approval.

**25-world integration:** Support 24 campaign worlds and one endless convergence world. Read the authoritative local game catalog and element registry, preserve distinct element IDs and asset keys, support hybrids and report coverage for every world. See PLAN.md. Never hard-code a one-world-per-element assumption.

**Mandatory world roster:** Exactly 5 Wild + 1 Legendary + 1 Guardian dedicated unique families per world, including the endless world. For 25 worlds: 125 Wild, 25 Legendary, 25 Guardian = 175 families; default 3 stages and maximum 3, up to 525 individual transparent sprites. Track quotas and category-specific design briefs; no duplicates across dedicated rosters. See PLAN.md. Do not assume generation is complete without approved outputs.
