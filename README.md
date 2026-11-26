# Monster Creator Automation

Create original one-to-three-stage monster families using Aevareth's saved
catalog and the current owner-approved artwork. This checkout owns the art
workflow. The game checkout owns Unity assets, encounter rules and saves.

## Set up the neighboring checkouts

Keep `aevareth_monster` and `monster_creator_automation` under the same parent.
From the automation checkout, install the Python 3.11+ CLI:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
$mc = (Resolve-Path .\.venv\Scripts\monster-creator.exe).Path
& $mc --help
& $mc doctor
```

From the game checkout, start Codex and ask it to use the
[monster-creator skill](.agents/skills/monster-creator/SKILL.md) for a family,
world or existing job:

```powershell
codex -C . --add-dir ../monster_creator_automation
```

## Verify the master

The repository includes the exact owner-supplied
`master_style_three_elements_stages_1-3.png` at
`references/master_style.png`. Version 2.0.0 is a 1054 × 1427 RGBA PNG
with 1,846,900 bytes. Its SHA-256 is
`09d5843a8660ef8200f2e171e8cab8a17d6048b37de31ea745a3cb10006ce6ba`.
The [style manifest](references/style_manifest.json) records the lock, and
the [art bible](docs/art-bible.md) explains the visual criteria.
Run `doctor` before generation. If the file is missing, restore the exact
tracked file or install the owner-supplied original with
`python -m monster_creator.style install PATH`. A changed file requires
resolving the mismatch before generation.

Use the Codex built-in image tool when the current session has it. Attach
the actual master and any requested family reference. The CLI handles
checkpoints, prompts and file processing. The skill controls image tool calls.
Use an actual reference-based manual handoff when necessary. A paid image API
requires separate authorization and a budget.

## Plan and prepare

Run the catalog commands from the automation checkout:

```powershell
& $mc catalog sync --game ../aevareth_monster --output jobs/aevareth-catalog.json
& $mc catalog coverage --catalog jobs/aevareth-catalog.json
& $mc catalog plan --catalog jobs/aevareth-catalog.json --world 'Cedarheart Grove' --output jobs/cedarheart-grove.json
```

Coverage tracks five Wild, one Legendary and one Guardian per world across
25 worlds. The ceiling is 175 unique families and 525 sprites. It reports
inherited families, proposals and game-data gaps. Inherited family IDs and
sprites are retained. Incompatible or unclassified inherited designs need
visual assessment and an approved current brief before regeneration.

Each new brief has one `archetypeId` from
[`config/species.yaml`](config/species.yaml), shared `identityAnchors`, and a
`transitionRationale` for each stage after Stage 1. Describe the change in
anatomy, elemental maturity and silhouette. The catalog plan shows the other
world, element, family and stage fields used by `prepare`.

For a pilot, save the selected family row from a catalog plan or a complete
ad hoc brief as `jobs/pilot-family.json`, then run:

```powershell
& $mc --workspace jobs/pilot-style-2 prepare --brief jobs/pilot-family.json
& $mc --workspace jobs/pilot-style-2 status
& $mc --workspace jobs/pilot-style-2 resume --limit 1
```

Use the same `--workspace` throughout a job. Older jobs remain pinned to
their original master and prompt. Use `status` or `validate` to identify
superseded evidence in such jobs, and use a fresh workspace for new art.
For a world audit, compare saved art with the current master and run
`validate --world ID` in the intended candidate workspace. An empty
checkpoint result means the workspace has no candidates for that world.

For a complete offline coverage check, replace `--world` with `--all
--require-complete` to compile all 25 worlds. Mass generation requires
both owner approval of the pilot artwork and separate batch authorization.
Record the authorization with `request --authorization TEXT`.

## Generate and review

1. Run `resume` for pending or in-flight work. Reserve with
   `request --job ID --stage N` before calling the image tool. Attach the
   verified master and any prior-stage reference listed in the request.
   Keep the returned PNG, then call
   `ingest --job ID --stage N --attempt N --image FILE --receipt FILE`.
   The receipt records `provider` (`codex-image-tool` or `manual`),
   `request_id`, `used_reference: true`, and `reference_sha256`. Include
   `family_reference_sha256` when required and retain any reported model,
   provider request ID and cost.
2. Recover an in-flight request using its original attempt. Record confirmed
   provider failures with `fail --job ID --stage N --attempt N --reason TEXT`.
   `reprocess --job ID --stage N --attempt N` reruns the latest technical
   rejection against the saved raw image after a processor correction.
   `extend-retry --job ID --stage N --reason TEXT` allows one further
   attempt for an exhausted stage, up to 10 attempts total for that stage.
3. Run `review --job ID --stage N` and inspect each candidate against the
   locked master at full resolution and on light and dark backgrounds.
   Complete the report and run `record-review --job ID --stage N --report FILE`.
   All visual checks must pass. The weighted stage score must reach 9/10,
   with each dimension scoring at least 8/10.
4. Run `review --job ID` when the current stages pass. Inspect the complete
   lineup, fill its template, and run `record-lineup --job ID --report FILE`.
   Evaluate the family against the [evolution quality gate](docs/evolution-quality.md).
   A rejected lineup can send its identified `revisionStages` back for
   bounded retries. Reevaluate the full lineup after changes.

After the owner explicitly approves the current whole-family artwork, record
the decision with `approve --job ID --owner NAME --authorization TEXT`
and run `export --job ID`. The portable package includes sprites, pivots,
hashes, provenance and review evidence. Use the game's
`docs/monster-batches.md` reviewed-family handoff to validate an authorized
Unity import. Replacing existing production sprites needs the owner's
separate authorization.

## Run the offline tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The [implementation plan](PLAN.md) records scope and rollout criteria.
