# Monster Creator Automation

Produce original one-to-three-stage monster families using Aevareth's saved catalog
and the owner-approved artwork. This checkout holds the reusable art workflow.
The game checkout owns Unity assets, encounter rules and saves.

## Set up the neighboring checkouts

Keep `aevareth_monster` and `monster_creator_automation` under the same parent.
From the automation checkout, install the Python 3.11+ CLI:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
$mc = (Resolve-Path .\.venv\Scripts\monster-creator.exe).Path
& $mc --help
```

From the game checkout, start Codex and say “Use monster-creator to prepare
Verdant Reach” or “Resume monster production.” The game instructions route
the request to this repository's [Codex skill](.agents/skills/monster-creator/SKILL.md).

```powershell
codex -C . --add-dir ../monster_creator_automation
```

## Verify the master and provider

On the automation side, install the exact owner-supplied original
`Aqua and Flame Evolution Line.png`:

```powershell
.\.venv\Scripts\python.exe -m monster_creator.style install 'C:/path/to/Aqua and Flame Evolution Line.png'
& $mc doctor
```

The installer checks the byte count, SHA-256 and PNG metadata against
[the committed lock](references/style_manifest.json). The expected digest is
`55f0908d04367b514acc53a3bdb89a25322829cfd1885ac907beb17f4f245cb0`.
Read [the art bible](docs/art-bible.md) for visual criteria.

Use the signed-in Codex built-in image tool. On November 26, 2026, Codex CLI
0.167.0 used an attached geometric test image via `-i`, and wrote a 1254 × 1254
RGBA PNG. Inspection found the requested edit, retained reference features,
and alpha from 0 to 255. The diagnostic used the ChatGPT session.
See the
[OpenAI Codex announcement](https://openai.com/index/codex-for-almost-everything/)
and the [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

## Plan a world or a batch

Run the following from the automation checkout:

```powershell
& $mc catalog sync --game ../aevareth_monster --output jobs/aevareth-catalog.json
& $mc catalog coverage --catalog jobs/aevareth-catalog.json
& $mc catalog plan --catalog jobs/aevareth-catalog.json --world 'Verdant Reach' --output jobs/verdant-reach.json
& $mc --workspace jobs/pilot-verdant-1-1 prepare --brief jobs/verdant-reach.json
& $mc --workspace jobs/pilot-verdant-1-1 status
& $mc --workspace jobs/pilot-verdant-1-1 resume --limit 1
```

Verdant Reach's seven briefs reuse the current five Wild, one Legendary and one
Guardian IDs and their 21 stage identities. The templates and prompts can be
prepared while the master is pending. Coverage distinguishes inherited families,
planned slots and game-data gaps. The checked-in plan fills 175 slots with
104 existing dedicated families and 71 proposals. The 525-stage ceiling
includes retained artwork. Four legacy Hybrid worlds have no saved element
components. Their proposed design pairings are labeled in coverage.

Use the same `--workspace` for pilot commands throughout the job. For a world
validation, resolve its ID with the catalog, check its saved art against
the game manifest, and use `validate --world ID` for the candidate checkpoints.
An empty checkpoint result means the workspace has no candidates for that world.

After owner approval to begin mass generation, prepare the full plan:

```powershell
& $mc catalog plan --catalog jobs/aevareth-catalog.json --all --require-complete --output jobs/aevareth-production.json
& $mc --workspace jobs/aevareth-production prepare --brief jobs/aevareth-production.json
```

The batch requests require `--authorization TEXT` at reservation. Review the
retained families and pilot results before starting another workspace.

## Generate, review and export

Use the skill to work through the pending jobs. The CLI returns the next prompt,
master and optional prior family-stage reference. Reserve the attempt with
`request --job ID --stage N` immediately before tool use. Pass the master as
an actual input to the built-in tool. Save the returned PNG and provider receipt,
then run `ingest --job ID --stage N --attempt N --image FILE --receipt FILE`.
The receipt records `provider` (`codex-image-tool` or `manual`), `request_id`,
`used_reference: true`, and `reference_sha256`. If a prior stage was required,
include `family_reference_sha256`. Include the provider request ID, model and cost
when reported. The CLI does local processing and the Codex skill controls image
tool calls.

For a confirmed failed request use `fail --job ID --stage N --attempt N --reason TEXT`.
If a technical check is corrected, `reprocess --job ID --stage N --attempt N`
can rerun it against the latest rejected raw image and receipt. It preserves
the prior result and makes no new provider call.
After interruption, recover in-flight output using its existing attempt before
reserving another. Use `review --job ID` to build comparisons and review forms,
then `record-review --job ID --stage N --report FILE`. Inspect each candidate
against the master and its family at full resolution and on light and dark
backgrounds. All visual checks must pass, the weighted score must be at least
9/10, and every rubric dimension must score at least 8/10. The tool keeps rejected
attempts for audit and queues stages with remaining attempts.

After the owner explicitly approves the candidate artwork, record the decision
with `approve --job ID --owner NAME --authorization TEXT` and run
`export --job ID`. The portable package preserves sprite hashes, pivot,
provenance and review evidence. Follow the Aevareth
`docs/monster-batches.md` handoff to validate it in the existing Unity importer.
Owner authorization for replacing production pixels is a separate import input.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The [implementation plan](PLAN.md) records the initial scope and open work.
