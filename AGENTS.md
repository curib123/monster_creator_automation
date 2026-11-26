# Instructions for Codex

Read [PLAN.md](PLAN.md), the [art bible](docs/art-bible.md), and the
[review requirements](docs/evolution-quality.md) before changing the workflow
or making artwork. Follow the [monster-creator skill](.agents/skills/monster-creator/SKILL.md)
for asset jobs.

- Verify the owner-approved `references/master_style.png` against
  `references/style_manifest.json` before production. Use the exact PNG as an
  image input and compare every candidate visually with it. A missing or
  changed file blocks generation and approval. An owner-authorized reference
  update must update the lock and the artwork together.
- Use one canonical approved archetype from `config/species.yaml` per family.
  Create original designs with natural anatomy and a purposeful progression
  across one to three stages. Each production sprite is a full-body,
  left-facing front three-quarter RGBA PNG with transparent background.
- Read the authoritative Aevareth catalog. Preserve world, element, family
  and stage identities. Plan five Wild, one Legendary and one Guardian in
  each of 25 worlds, for 175 distinct families and up to 525 stage sprites.
  Retain existing artwork and report incompatible inherited designs for review.
- Use a real reference-capable and authorized image tool or a manual handoff.
  Confirm the provider received the input. Keep request provenance, immutable
  attempts and bounded retries. A paid backend requires an authorized budget.
  Keep credentials out of Git.
- Require technical checks and an actual visual evaluation of each stage and
  the complete family against the current master. Export only after the
  owner's explicit family approval. Obtain separate authorization for mass
  production or replacement of existing production art. Use the game's
  reviewed-family import handoff for any authorized Unity update.
- Keep implementation and documentation current. Run offline tests, report
  unresolved gaps and keep unrelated game files and checkpoint history intact.
