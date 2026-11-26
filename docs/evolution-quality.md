# Evolution quality and production gate

## Archetype and progression

Each family has one canonical archetype ID from
[`config/species.yaml`](../config/species.yaml).
The approved archetypes are Fox, Rabbit, Cat, Eagle, Phoenix, Dragon,
Butterfly, Gecko, Bear, Manta Ray, Jellyfish, Ghost, Knight, Sorcerer, and
Magician. The same archetype can support multiple original families through
distinct silhouettes, proportions, materials, markings and evolutionary
structures. Elemental hybrids still have one base archetype.

Plan the whole family before drawing. Give it visible shared identity anchors
and write the anatomical cause, elemental maturation and silhouette change
for each transition. Keep recurring face cues, markings or appendage structure
visible through the line.

| Stage | What to design and review |
| --- | --- |
| 1 | A cute and charming form with stable anatomy, soft proportions, an expressive face or focal feature, and one clear elemental cue. |
| 2 | A recognizable juvenile with purposefully developed joints, stance or appendages, better-balanced proportions, and element-specific structures growing from Stage 1. |
| 3 | An elegant and satisfying adult with a cleaner, relatively slimmer silhouette, confident pose, mature anatomy and purposeful material refinement. Keep natural species mass and structures, such as a bear's chest and broad paws, a manta's broad fins, or a jellyfish's bell and tentacles. |

Scaling, recoloring, or adding incidental armor, spikes, accessories or
floating effects fails progression. Keep approved one- and two-stage
assignments within their explicit lengths. A two-stage line still needs a
meaningful transition.

## Review against the locked master

Run the technical checks on each sprite. Then open the verified master, the
full-resolution candidates, and the light and dark preview panels. Check
the entire body, facing, transparency and edge treatment as well as facial
finish, material texture, linework, shading, elemental expression, silhouette,
proportions and anatomy. Look for clipping, extra limbs, clutter, fake alpha,
text, recognizable third-party designs, and the wrong view. See
[the art bible](art-bible.md) for the exact reference cues.

Complete each current stage report from `review --job ID --stage N` and
submit it with `record-review --job ID --stage N --report FILE`. Give
specific observations about the sprites you saw. The stage gate requires
a weighted score of at least 9/10, at least 8/10 in each dimension, and
a pass on every required visual check. Score style fidelity (25%),
aesthetic polish (20%), evolution continuity (20%), elemental expression
(15%), archetype anatomy (10%), and silhouette usability (10%).

When each current stage passes, run `review --job ID` and inspect the family
comparison. Evaluate aesthetics, silhouette and proportions, cleanliness,
and how the line retains identity while developing its anatomy and element.
Score progression and meaningful differentiation for multiple stages and
final-form refinement for a three-stage line. Submit the completed hash-bound
template using `record-lineup --job ID --report FILE`. The applicable
dimensions count equally toward a minimum 9/10, each must score at least
8/10, and every hard check must pass. A high numerical score cannot clear
awkward anatomy, confusing identity, an illogical transition, or an
unsatisfying final form. Genuine judgments come from the actual images.

Specify `revisionStages` in a failed lineup report to identify the stages
that need another attempt. Preserve the earlier files and review history.
Inspect the complete new lineup when those stages pass. A current lineup
pass and the owner's explicit approval of the matching family revision are
required before export. Use the Aevareth reviewed-family import procedure
for any authorized integration.

## Older files

Use `status` or `validate` in the original workspace to locate jobs with
superseded reference or policy evidence. A historical pass persists in
its original record. It gives no production approval under the current
standard. Visually audit actual earlier sprites against the new master,
mark mismatches for revision, and keep the files, old receipts and existing
game assets. Prepare approved new work against the current lock in a separate
workspace so it can be reviewed on its own evidence.
