"""Synthetic fixtures exercise gates and package format without generating or approving production art."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from monster_creator.cli import main
from monster_creator import pipeline, qa
from monster_creator.pipeline import Workflow, json_bytes, read_json
from monster_creator.qa import RUBRIC, VISUAL_CHECKS


@pytest.fixture
def workflow(tmp_path):
    references = tmp_path / "references"
    references.mkdir()
    master = references / "master_style.png"
    save_fixture(master, "pink")
    lock = {"reference_path": "references/master_style.png", "version": "test", "mode": "RGBA",
            "original_filename": "test-only-master.png", "width": 320, "height": 320,
            "bytes": master.stat().st_size, "sha256": sha256(master.read_bytes()).hexdigest(),
            "require_exact_hash": True, "alpha_range": [0, 255]}
    (references / "style_manifest.json").write_bytes(json_bytes(lock))
    return Workflow(tmp_path, tmp_path)


def save_fixture(path, color, background=(0, 0, 0, 0)):
    image = Image.new("RGBA", (320, 320), background)
    ImageDraw.Draw(image).ellipse((50, 50, 266, 266), fill=color)
    image.save(path)


def family(stages=1, family_id="test_moth", world="test-world"):
    return {"familyId": family_id, "displayName": family_id, "description": "Test-only design",
            "worldId": world, "category": "Wild", "gameElement": "Fire", "monsterType": "Common",
            "isNewFamily": True, "species": "moth", "elements": ["fire"], "concept": "Test fixture",
            "stages": [{"stage": stage, "name": f"Fixture {stage}", "title": "Test",
                        "description": f"QA fixture for stage {stage}"} for stage in range(1, stages + 1)]}


def write_json(workflow, name, value):
    path = workflow.workspace / name
    path.write_bytes(json_bytes(value))
    return path


def prepare(workflow, brief=None, attempts=3):
    path = write_json(workflow, "brief.json", brief or family())
    return workflow.prepare(path, attempts, 1024)


def provider_result(workflow, request, color, background=(0, 0, 0, 0)):
    source = workflow.workspace / "provider-fixture.png"
    save_fixture(source, color, background)
    receipt = {"provider": "manual", "request_id": request["requestId"],
               "reference_sha256": request["referenceSha256"], "used_reference": True}
    if request["familyReference"]:
        receipt["family_reference_sha256"] = request["familyReference"]["sha256"]
    return source, write_json(workflow, "provider-receipt.json", receipt)


def ingest(workflow, request, color, background=(0, 0, 0, 0)):
    source, receipt = provider_result(workflow, request, color, background)
    return workflow.ingest(request["job"], request["stage"], request["attempt"], source, receipt)


def evaluate_fixture(workflow, stage, **changes):
    candidate = workflow.review("test_moth", stage)["candidates"][0]
    assert Path(candidate["preview"]).is_file()
    report = {**candidate["reviewTemplate"], "reviewer": "QA fixture", "notes": "Test evidence only.",
              "scores": dict.fromkeys(RUBRIC, 9), **dict.fromkeys(VISUAL_CHECKS, True), **changes}
    return workflow.record_review("test_moth", stage, write_json(workflow, "test-review.json", report))


def test_empty_status_and_resume_leave_no_checkpoint_files(workflow):
    workspace = workflow.workspace / "unstarted workspace"
    empty = Workflow(workflow.repo, workspace)
    assert empty.status(None) == {"totals": {}, "worlds": {}, "jobs": {}}
    assert empty.status(None, "test-world", validate=True)["jobs"] == {}
    assert empty.resume(None, 1)["requests"] == []
    assert not workspace.exists()


def test_prepare_with_missing_master_stays_offline_and_is_idempotent(workflow, capsys):
    workflow.repo.joinpath("references/master_style.png").unlink()
    assert prepare(workflow, family(3)) == prepare(workflow, family(3))
    pending = workflow.resume("test_moth", 3)
    assert len(pending["requests"]) == 3
    assert all(not request["ready"] and request["reference"] is None for request in pending["requests"])
    assert all("Left-facing front three-quarter" in request["prompt"] for request in pending["requests"])
    assert "missing" in pending["masterBlockers"]["test_moth"]
    with pytest.raises(ValueError, match="missing"):
        workflow.request("test_moth", 1, None)
    assert main(["--repo", str(workflow.repo), "doctor"]) == 1
    assert "SHA-256" in capsys.readouterr().err
    with pytest.raises(ValueError, match="different brief"):
        prepare(workflow, family(2))
    with pytest.raises(ValueError, match="one to three"):
        prepare(workflow, family(4))


def test_checkpoint_is_single_request_under_concurrency_and_has_bounded_retries(workflow):
    prepare(workflow, attempts=2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        requests = list(executor.map(lambda _: workflow.request("test_moth", 1, None), range(2)))
    assert {request["requestId"] for request in requests} == {"test_moth:s01:a1"}
    assert {request["recovery"] for request in requests} == {False, True}
    assert workflow.resume("test_moth", 1)["requests"][0]["recovery"] is True
    source, receipt = provider_result(workflow, requests[0], "blue")
    write_json(workflow, receipt.name, {**read_json(receipt), "used_reference": False})
    with pytest.raises(ValueError, match="actual conditioning"):
        workflow.ingest("test_moth", 1, 1, source, receipt)
    assert workflow.fail("test_moth", 1, 1, "Test provider stopped")["status"] == "pending"
    request = workflow.request("test_moth", 1, None)
    assert request["attempt"] == 2 and "Test provider stopped" in request["prompt"]
    output = ingest(workflow, request, "yellow", background="red")
    assert output["status"] == "rejected" and "fully transparent" in output["reason"]
    assert workflow.status(None)["totals"] == {"exhausted": 1}
    with pytest.raises(ValueError, match="exhausted"):
        workflow.request("test_moth", 1, None)


def test_extend_retry_reopens_one_exhausted_stage_and_preserves_its_evidence(workflow, capsys):
    prepare(workflow, family(2), attempts=1)
    request = workflow.request("test_moth", 1, None)
    with pytest.raises(ValueError, match="exhausted stage"):
        workflow.extend_retry("test_moth", 1, "Wait until this request finishes.")
    rejected = ingest(workflow, request, "yellow", background="red")
    assert rejected["nextPhase"] == "exhausted"
    raw = workflow.artifact("test_moth", 1, 1, "raw.png")
    proof = workflow.artifact("test_moth", 1, 1, "provenance.json")
    original_raw, original_proof = raw.read_bytes(), proof.read_bytes()

    correction = "Leave a clean alpha-zero background around the full creature."
    assert main(["--repo", str(workflow.repo), "extend-retry", "--job", "test_moth", "--stage", "1",
                 "--reason", correction]) == 0
    assert '"maxAttempts": 2' in capsys.readouterr().out
    with pytest.raises(ValueError, match="exhausted stage"):
        workflow.extend_retry("test_moth", 1, correction)
    assert prepare(workflow, family(2), attempts=1)["plannedStages"] == 2
    with pytest.raises(ValueError, match="different brief or configuration"):
        prepare(workflow, family(2), attempts=2)

    stages = workflow.status("test_moth")["jobs"]["test_moth"]["stages"]
    assert [item["maxAttempts"] for item in stages] == [2, 1]
    assert stages[0]["retryExtensions"][0]["reason"] == correction
    assert stages[1]["retryExtensions"] == []
    pending = workflow.resume("test_moth", 1, rejected_only=True)["requests"][0]
    assert pending["requestId"] == "test_moth:s01:a2"
    assert correction in pending["prompt"] and rejected["reason"] in pending["prompt"]
    assert workflow.request("test_moth", 1, None)["requestId"] == pending["requestId"]
    assert raw.read_bytes() == original_raw and proof.read_bytes() == original_proof


def test_extend_retry_respects_absolute_attempt_limit(workflow):
    prepare(workflow, attempts=pipeline.MAX_ATTEMPTS - 1)
    for number in range(1, pipeline.MAX_ATTEMPTS):
        workflow.request("test_moth", 1, None)
        workflow.fail("test_moth", 1, number, "Fixture provider failure")
    workflow.extend_retry("test_moth", 1, "Retry once after the fixture provider recovers.")
    assert workflow.request("test_moth", 1, None)["attempt"] == pipeline.MAX_ATTEMPTS
    assert workflow.fail("test_moth", 1, pipeline.MAX_ATTEMPTS, "Fixture provider failure")["status"] == "exhausted"
    with pytest.raises(ValueError, match="maximum of 10 total attempts"):
        workflow.extend_retry("test_moth", 1, "Another retry")


def test_fixture_review_retry_owner_approval_and_export_are_hash_bound(workflow):
    prepare(workflow, family(2))
    with pytest.raises(ValueError, match="previous stage"):
        workflow.request("test_moth", 2, None)
    first = workflow.request("test_moth", 1, None)
    assert ingest(workflow, first, "blue")["status"] == "technical_pass"
    failed = evaluate_fixture(workflow, 1, facingReviewed=False, scores=dict.fromkeys(RUBRIC, 10))
    assert failed["status"] == "rejected"
    assert [request["stage"] for request in workflow.resume("test_moth", 2, rejected_only=True)["requests"]] == [1]
    next_attempt = workflow.request("test_moth", 1, None)
    assert "facingReviewed" in next_attempt["prompt"]
    first = ingest(workflow, next_attempt, "orange")
    assert ingest(workflow, next_attempt, "orange") == first
    assert evaluate_fixture(workflow, 1)["status"] == "visual_pass"

    second = workflow.request("test_moth", 2, None)
    assert second["familyReference"]["sha256"] == first["technical"]["sha256"]
    assert ingest(workflow, second, "orange")["status"] == "rejected"
    second = workflow.request("test_moth", 2, None)
    assert ingest(workflow, second, "lime")["status"] == "technical_pass"
    assert evaluate_fixture(workflow, 2)["status"] == "visual_pass"
    with pytest.raises(ValueError, match="owner approval"):
        workflow.export("test_moth")
    assert workflow.approve("test_moth", "Fixture owner", "Test package only.")["approvedStages"] == 2
    package = workflow.export("test_moth")
    assert package == workflow.export("test_moth")
    manifest_path = Path(package["manifest"])
    manifest = read_json(manifest_path)
    assert manifest["schemaVersion"] == 1 and len(manifest["families"][0]["stages"]) == 2
    for stage in manifest["families"][0]["stages"]:
        sprite, review = (manifest_path.parent / stage[field] for field in ("path", "reviewPath"))
        assert stage["sha256"] == sha256(sprite.read_bytes()).hexdigest()
        assert stage["reviewSha256"] == sha256(review.read_bytes()).hexdigest()
        proof = read_json(review)
        assert proof["approved"] is True and proof["score"] == 9
        assert proof["reviewer"] == "Fixture owner" and proof["sha256"] == stage["sha256"]
        assert proof["referenceSha256"] == manifest["referenceSha256"]
        assert all(proof[field] for field in VISUAL_CHECKS)
    progress = workflow.status(None, "test-world")["worlds"]["test-world"]["Common"]
    assert progress == {"plannedFamilies": 1, "plannedStages": 2, "generatedStages": 2,
                        "approvedStages": 2, "exportedStages": 2}
    sprite.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash changed"):
        workflow.export("test_moth")


def test_mass_prepare_is_offline_and_generation_requires_explicit_authorization(workflow):
    prepare(workflow, {"families": [family(), family(family_id="test_next", world="next-world")]})
    with pytest.raises(ValueError, match="Owner authorization"):
        workflow.request("test_moth", 1, None)
    assert workflow.request("test_moth", 1, "Fixture authorization")["attempt"] == 1


def test_incremental_preparation_cannot_skip_workspace_pilot_boundary(workflow):
    for number in range(7):
        family_id = f"fixture_{number}"
        prepare(workflow, family(family_id=family_id))
        workflow.request(family_id, 1, None)
    prepare(workflow, family(family_id="additional_family"))
    assert workflow.resume("additional_family", 1)["requests"][0]["massAuthorizationRequired"] is True
    with pytest.raises(ValueError, match="Owner authorization"):
        workflow.request("additional_family", 1, None)


def test_alpha_noise_recheck_retains_source_and_rejection_while_real_clip_fails(workflow, monkeypatch):
    prepare(workflow, [family(), family(family_id="test_clipped")])
    request = workflow.request("test_moth", 1, None)
    source, receipt = provider_result(workflow, request, "green")
    with Image.open(source) as image:
        image.putpixel((0, 160), (240, 190, 10, 8))
        image.save(source)
    original = source.read_bytes()
    with monkeypatch.context() as legacy:
        legacy.setattr(qa, "ALPHA_NOISE_MAX", 0)
        legacy.setattr(pipeline, "PROCESSING_VERSION", 1)
        rejected = workflow.ingest("test_moth", 1, 1, source, receipt)
        assert rejected["status"] == "rejected"
        with pytest.raises(ValueError, match="already used"):
            workflow.reprocess("test_moth", 1, 1)
    checked = workflow.reprocess("test_moth", 1, 1)
    assert checked["processingVersion"] == pipeline.PROCESSING_VERSION and checked["status"] == "technical_pass"
    assert checked["technicalHistory"][0]["reason"] == rejected["reason"]
    assert checked["handoff"]["requestId"] == request["requestId"]
    assert workflow.artifact("test_moth", 1, 1, "raw.png").read_bytes() == original
    assert workflow.artifact("test_moth", 1, 1, "provenance.json").read_bytes() == receipt.read_bytes()

    second_request = workflow.request("test_clipped", 1, None)
    source, receipt = provider_result(workflow, second_request, "red")
    with Image.open(source) as image:
        ImageDraw.Draw(image).rectangle((0, 50, 50, 200), fill=(230, 30, 20, 128))
        image.save(source)
    clipped = workflow.ingest("test_clipped", 1, 1, source, receipt)
    assert clipped["status"] == "rejected" and "touches the edge" in clipped["reason"]


def test_almost_opaque_subject_keeps_its_alpha_without_admitting_ghosts(workflow):
    prepare(workflow, [family(), family(family_id="test_ghost")])
    for job, opacity, expected in (("test_moth", 254, "technical_pass"), ("test_ghost", 249, "rejected")):
        request = workflow.request(job, 1, None)
        source, receipt = provider_result(workflow, request, (50, 150, 220, opacity))
        candidate = workflow.ingest(job, 1, 1, source, receipt)
        assert candidate["status"] == expected
    with Image.open(workflow.artifact("test_moth", 1, 1, "sprite.png")) as sprite:
        assert sprite.getchannel("A").getextrema() == (0, 254)
