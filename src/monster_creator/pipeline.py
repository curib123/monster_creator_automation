"""Durable local checkpoints for planning, generation, review and Unity export."""

from collections import Counter
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory

from PIL import Image

from .archetypes import canonical_text, load_archetypes, validate_design_line
from .qa import (PROCESSING_VERSION, REVIEW_POLICY_VERSION, RUBRIC, comparison, lineup_comparison,
                 lineup_result, lineup_rules, normalize, stage_checks, visual_result)
from .style import PROMPT_VERSION, compile_prompt, verify_master


MAX_ATTEMPTS = 10


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Refusing to overwrite different artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as temp:
        draft = Path(temp) / path.name
        draft.write_bytes(data)
        os.replace(draft, path)


def verified_bytes(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError(f"Artifact hash changed: {path}")
    return data


def require_text(record: dict, fields) -> None:
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Missing or empty {field}")


def validate_family(family: dict, archetypes: dict) -> None:
    if not isinstance(family, dict):
        raise ValueError("Each family must be a JSON object")
    require_text(family, ("familyId", "displayName", "description", "worldId", "gameElement", "category"))
    family_id = family["familyId"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", family_id) or re.fullmatch(
        r"con|prn|aux|nul|com[0-9]|lpt[0-9]", family_id
    ):
        raise ValueError("familyId must be a filesystem-safe lowercase identifier")
    category_types = {"Wild": "Common", "Legendary": "Legendary", "Guardian": "AncientGuardian"}
    if family["category"] not in category_types or category_types[family["category"]] != family.get("monsterType"):
        raise ValueError("Category must match its game type: Wild/Common, Legendary/Legendary, or Guardian/AncientGuardian")
    if type(family.get("isNewFamily")) is not bool:
        raise ValueError("isNewFamily must explicitly describe the catalog mapping")
    if "concept" in family:
        require_text(family, ("concept",))
    elements = family.get("elements")
    if not isinstance(elements, list) or not elements or any(
        not isinstance(element, str) or not element.strip() for element in elements
    ) or len(elements) != len(set(elements)):
        raise ValueError("elements must contain distinct canonical element IDs")
    validate_design_line(family, archetypes)


def latest(job: dict, stage: int) -> dict | None:
    if not 1 <= stage <= len(job["stages"]):
        raise ValueError(f"Stage {stage} is outside this job's brief")
    attempts = job["stages"][stage - 1]
    return attempts[-1] if attempts else None


def phase(job: dict, stage: int) -> str:
    attempt = latest(job, stage)
    if attempt is None:
        return "pending"
    if attempt["status"] in ("rejected", "provider_failed"):
        return "exhausted" if attempt["number"] >= attempt_limit(job, stage) else "pending"
    return attempt["status"]


def attempt_limit(job: dict, stage: int) -> int:
    return job["maxAttempts"] + len(job.get("retryExtensions", {}).get(str(stage), ()))


class Workflow:
    def __init__(self, repo: Path, workspace: Path):
        self.repo = repo.resolve()
        self.workspace = workspace.resolve()

    def archetypes(self) -> dict:
        return load_archetypes(self.repo)

    @contextmanager
    def checkpoint(self, *, read_only: bool = False):
        database = self.workspace / "jobs" / "checkpoints.sqlite3"
        if read_only and not database.exists():
            yield {}
            return
        if not read_only:
            database.parent.mkdir(parents=True, exist_ok=True)
        location = database.as_uri() + "?mode=ro" if read_only else database
        with closing(sqlite3.connect(location, uri=read_only, timeout=30)) as connection, connection:
            if not read_only:
                connection.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, record TEXT NOT NULL)")
                connection.execute("BEGIN IMMEDIATE")
            elif not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone():
                yield {}
                return
            previous = dict(connection.execute("SELECT id, record FROM jobs"))
            jobs = {key: json.loads(value) for key, value in previous.items()}
            yield jobs
            if read_only:
                return
            for key, value in jobs.items():
                record = json_bytes(value).decode("utf-8")
                if record != previous.get(key):
                    connection.execute("INSERT OR REPLACE INTO jobs VALUES (?, ?)", (key, record))

    def prepare(self, source: Path, max_attempts: int, size: int) -> dict:
        if not 1 <= max_attempts <= MAX_ATTEMPTS or size not in (512, 1024, 2048):
            raise ValueError(f"Prepare requires 1–{MAX_ATTEMPTS} attempts and a 512, 1024, or 2048 pixel canvas")
        plans = read_json(source)
        plans = plans.get("families", [plans]) if isinstance(plans, dict) else plans
        if not isinstance(plans, list) or not plans:
            raise ValueError("No families found in the supplied brief")
        archetypes = self.archetypes()
        for family in plans:
            validate_family(family, archetypes)
        mass_batch = len(plans) > 7 or len({family["worldId"] for family in plans}) > 1
        style = read_json(self.repo / "references" / "style_manifest.json")
        seen = set()
        with self.checkpoint() as jobs:
            names = {job["brief"]["displayName"].casefold(): key for key, job in jobs.items()}
            concepts = {}
            for key, job in jobs.items():
                brief = job["brief"]
                concept = brief.get("concept")
                if not isinstance(concept, str) or not concept.strip():
                    concept = brief["description"]
                concepts[canonical_text(concept)] = key
            for family in plans:
                key = family["familyId"]
                name = family["displayName"].casefold()
                concept = canonical_text(family.get("concept") or family["description"])
                if key in seen:
                    raise ValueError(f"Duplicate production family: {key}")
                if name in names and names[name] != key:
                    raise ValueError(f"Another production family already uses the name {family['displayName']}")
                if concept in concepts and concepts[concept] != key:
                    raise ValueError(f"The family concept for {key} duplicates {concepts[concept]}")
                seen.add(key)
                names[name] = key
                concepts[concept] = key
                definition = {"brief": family, "size": size, "maxAttempts": max_attempts, "promptVersion": PROMPT_VERSION,
                              "referenceSha256": style["sha256"], "styleVersion": style["version"]}
                if key in jobs:
                    if any(jobs[key][field] != value for field, value in definition.items()):
                        raise ValueError(f"The checkpoint already locks a different brief or configuration for {key}")
                    if mass_batch:
                        jobs[key]["massBatch"] = True
                    continue
                jobs[key] = {**definition, "created": stamp(), "stages": [[] for _ in family["stages"]],
                             "massBatch": mass_batch}
        return {"jobs": [family["familyId"] for family in plans],
                "plannedStages": sum(len(family["stages"]) for family in plans)}

    @staticmethod
    def selected(jobs: dict, job_id: str | None) -> dict:
        if job_id is None:
            return jobs
        if job_id not in jobs:
            raise ValueError(f"Unknown job: {job_id}")
        return {job_id: jobs[job_id]}

    @staticmethod
    def require_job_master(job: dict, master: dict) -> None:
        if (master["sha256"], master["version"]) != (job["referenceSha256"], job["styleVersion"]):
            raise ValueError("The job locks a different master hash or style version")

    def master(self, job: dict) -> dict:
        master = verify_master(self.repo)
        self.require_job_master(job, master)
        return master

    def artifact(self, job_id: str, stage: int, attempt: int, name: str) -> Path:
        return self.workspace / "output" / "drafts" / job_id / f"s{stage:02d}" / f"attempt-{attempt}" / name

    @staticmethod
    def require_current_brief(job: dict, archetypes: dict) -> None:
        if job["promptVersion"] != PROMPT_VERSION:
            raise ValueError("This job is pinned to a different prompt version and needs a current brief")
        validate_family(job["brief"], archetypes)

    def handoff(self, job_id: str, job: dict, stage: int, master: dict | None, mass: bool, archetypes: dict) -> dict:
        previous = latest(job, stage)
        if previous and previous["status"] == "requested":
            return {**previous["handoff"], "recovery": True}
        attempt = len(job["stages"][stage - 1]) + 1
        family_reference = None
        for earlier in reversed(range(1, stage)):
            accepted = latest(job, earlier)
            if accepted and accepted["status"] in ("visual_pass", "approved"):
                path = self.artifact(job_id, earlier, accepted["number"], "sprite.png")
                digest = accepted["technical"]["sha256"]
                verified_bytes(path, digest)
                family_reference = {"path": str(path), "sha256": digest}
                break
        feedback = previous.get("reason") if previous else None
        extensions = job.get("retryExtensions", {}).get(str(stage), ())
        if extensions and extensions[-1]["maxAttempts"] == attempt:
            feedback = f"{feedback}\n\nCorrection for this additional attempt: {extensions[-1]['reason']}"
        prompt = compile_prompt(job["brief"], stage, archetypes, feedback)
        return {"job": job_id, "stage": stage, "attempt": attempt,
                "requestId": f"{job_id}:s{stage:02d}:a{attempt}", "prompt": prompt, "promptVersion": job["promptVersion"],
                "reference": str(self.repo / master["reference_path"]) if master else None,
                "referenceSha256": job["referenceSha256"], "familyReference": family_reference,
                "recovery": False, "massAuthorizationRequired": mass}

    @staticmethod
    def has_prior_review(job: dict, stage: int) -> bool:
        return stage == 1 or phase(job, stage - 1) in ("visual_pass", "approved")

    @staticmethod
    def needs_mass_authorization(jobs: dict, job: dict) -> bool:
        return job["massBatch"] or (not any(job["stages"]) and sum(bool(any(other["stages"])) for other in jobs.values()) >= 7)

    def resume(self, job_id: str | None, limit: int, world_id: str | None = None, rejected_only: bool = False) -> dict:
        eligible, requests = [], []
        blockers, brief_blockers = {}, {}
        with self.checkpoint(read_only=True) as jobs:
            archetypes = self.archetypes()
            try:
                verified = verify_master(self.repo)
                missing = None
            except (ValueError, OSError) as error:
                verified, missing = None, str(error)
            for key, job in self.selected(jobs, job_id).items():
                if world_id is not None and world_id != job["brief"]["worldId"]:
                    continue
                next_stages = [number for number in range(1, len(job["stages"]) + 1)
                               if phase(job, number) in ("pending", "requested")]
                if rejected_only:
                    next_stages = [number for number in next_stages
                                   if any(previous["status"] == "rejected" for previous in job["stages"][number - 1])]
                if not next_stages:
                    continue
                if missing:
                    blockers[key] = missing
                else:
                    try:
                        self.require_job_master(job, verified)
                    except ValueError as error:
                        blockers[key] = str(error)
                try:
                    self.require_current_brief(job, archetypes)
                except ValueError as error:
                    brief_blockers[key] = str(error)
                    continue
                for stage in next_stages:
                    prior_review = self.has_prior_review(job, stage)
                    priority = (not prior_review, phase(job, stage) != "requested")
                    eligible.append((priority, key, stage, prior_review))
            for _, key, stage, prior_review in sorted(eligible)[:limit]:
                master = None if key in blockers else verified
                job = jobs[key]
                request = self.handoff(key, job, stage, master, self.needs_mass_authorization(jobs, job), archetypes)
                requests.append({**request, "reference": request["reference"] if master else None,
                                 "ready": master is not None and prior_review, "needsPriorStageReview": not prior_review})
        return {"requests": requests, "masterBlockers": blockers, "briefBlockers": brief_blockers}

    def request(self, job_id: str, stage: int, authorization: str | None) -> dict:
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            archetypes = self.archetypes()
            self.require_current_brief(job, archetypes)
            current = phase(job, stage)
            if current not in ("pending", "requested"):
                raise ValueError(f"Stage {stage} cannot start generation from {current}")
            master = self.master(job)
            if not self.has_prior_review(job, stage):
                raise ValueError("Review the previous stage before generating the next family stage")
            mass = self.needs_mass_authorization(jobs, job)
            handoff = self.handoff(job_id, job, stage, master, mass, archetypes)
            if current == "pending":
                if mass and (not authorization or not authorization.strip()):
                    raise ValueError("Owner authorization is required to start a mass-production batch")
                job["massBatch"] = mass
                job["stages"][stage - 1].append({"number": handoff["attempt"], "status": "requested",
                                                 "handoff": handoff, "started": stamp(),
                                                 "batchAuthorization": authorization})
        return handoff

    @staticmethod
    def inflight(job: dict, stage: int, number: int) -> dict:
        target = latest(job, stage)
        if not target or target["number"] != number:
            raise ValueError("The attempt is absent from the latest checkpoint")
        return target

    def fail(self, job_id: str, stage: int, number: int, reason: str) -> dict:
        require_text({"reason": reason}, ("reason",))
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            target = self.inflight(job, stage, number)
            if target["status"] != "requested":
                raise ValueError("Only an in-flight generation request can fail")
            target.update(status="provider_failed", reason=reason, finished=stamp())
            return {"stage": stage, "status": phase(job, stage), "reason": reason}

    def extend_retry(self, job_id: str, stage: int, reason: str) -> dict:
        require_text({"reason": reason}, ("reason",))
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            if phase(job, stage) != "exhausted":
                raise ValueError("Only an exhausted stage can receive a retry extension")
            previous_limit = attempt_limit(job, stage)
            if previous_limit >= MAX_ATTEMPTS:
                raise ValueError(f"Stage {stage} reached the maximum of {MAX_ATTEMPTS} total attempts")
            extension = {"previousLimit": previous_limit, "maxAttempts": previous_limit + 1,
                         "reason": reason.strip(), "extendedAt": stamp()}
            job.setdefault("retryExtensions", {}).setdefault(str(stage), []).append(extension)
            return {"job": job_id, "stage": stage, "status": phase(job, stage), **extension}

    def ingest(self, job_id: str, stage: int, number: int, source: Path, receipt_path: Path) -> dict:
        if source.stat().st_size > 80 * 1024 * 1024:
            raise ValueError("Source PNG exceeds the 80 MiB input limit")
        original, receipt = source.read_bytes(), read_json(receipt_path)
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            self.require_current_brief(job, self.archetypes())
            master = self.master(job)
            target = self.inflight(job, stage, number)
            handoff = target["handoff"]
            if not isinstance(receipt, dict) or receipt.get("provider") not in ("codex-image-tool", "manual"):
                raise ValueError("A Codex image tool or manual provider receipt is required")
            if (receipt.get("request_id") != handoff["requestId"] or
                receipt.get("reference_sha256") != master["sha256"] or receipt.get("used_reference") is not True):
                raise ValueError("Provider receipt must attest to actual conditioning on the locked request reference")
            if handoff["familyReference"] and receipt.get("family_reference_sha256") != handoff["familyReference"]["sha256"]:
                raise ValueError("Provider receipt must include the supplied family reference hash")
            raw_hash = sha256(original).hexdigest()
            if target["status"] != "requested":
                if target.get("sourceSha256") == raw_hash and target.get("receipt") == receipt:
                    return {**target, "nextPhase": phase(job, stage)}
                raise ValueError("The attempt has already been resolved")
            write_once(self.artifact(job_id, stage, number, "raw.png"), original)
            write_once(self.artifact(job_id, stage, number, "provenance.json"), json_bytes(receipt))
            target.update(sourceSha256=raw_hash, receipt=receipt, finished=stamp())
            self.check_sprite(jobs, job_id, stage, target, original)
            return {**target, "nextPhase": phase(job, stage)}

    def check_sprite(self, jobs: dict, job_id: str, stage: int, target: dict, original: bytes) -> None:
        job = jobs[job_id]
        target.update(processingVersion=PROCESSING_VERSION, technicalChecked=stamp())
        try:
            stage_spec = job["brief"]["stages"][stage - 1]
            png, technical = normalize(original, job["size"], stage, len(job["stages"]),
                                       stage_spec.get("anchor", job["brief"].get("anchor")) == "floating")
            raw_hash = target["sourceSha256"]
            # Check decoded normalized content as well as file hashes.
            duplicates = any(
                previous.get("sourceSha256") == raw_hash or
                previous.get("technical", {}).get("pixelSha256") == technical["pixelSha256"]
                for other in jobs.values() for attempts in other["stages"] for previous in attempts
                if previous is not target
            )
            if duplicates or raw_hash == job["referenceSha256"]:
                raise ValueError("Artwork duplicates a prior sprite or the master reference")
        except (ValueError, OSError, Image.DecompressionBombError) as error:
            target.update(status="rejected", reason=f"Technical rejection: {error}")
        else:
            write_once(self.artifact(job_id, stage, target["number"], "sprite.png"), png)
            target.pop("reason", None)
            target.update(status="technical_pass", technical=technical)

    def reprocess(self, job_id: str, stage: int, number: int) -> dict:
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            self.master(job)
            target = self.inflight(job, stage, number)
            version = target.get("processingVersion", 1)
            if target["status"] != "rejected" or "visual" in target or "sourceSha256" not in target:
                raise ValueError("Only the latest technical rejection can be reprocessed")
            if version >= PROCESSING_VERSION:
                raise ValueError("The last technical review already used this processing version")
            original = verified_bytes(self.artifact(job_id, stage, number, "raw.png"), target["sourceSha256"])
            receipt = json_bytes(target["receipt"])
            verified_bytes(self.artifact(job_id, stage, number, "provenance.json"), sha256(receipt).hexdigest())
            target.setdefault("technicalHistory", []).append({"status": "rejected", "reason": target["reason"],
                                                               "processingVersion": version,
                                                               "checked": target.get("technicalChecked", target["finished"])})
            self.check_sprite(jobs, job_id, stage, target, original)
            return {**target, "nextPhase": phase(job, stage)}

    def review(self, job_id: str, stage: int | None) -> dict:
        candidates = []
        lineup = None
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            master = self.master(job)
            for number in [stage] if stage is not None else range(1, len(job["stages"]) + 1):
                attempt = latest(job, number)
                if not attempt or "technical" not in attempt:
                    continue
                revision = attempt["number"]
                sprite = self.artifact(job_id, number, revision, "sprite.png")
                verified_bytes(sprite, attempt["technical"]["sha256"])
                preview = self.artifact(job_id, number, revision, f"comparison-v{REVIEW_POLICY_VERSION}.png")
                if "comparisonSha256" in attempt:
                    verified_bytes(preview, attempt["comparisonSha256"])
                else:
                    data = comparison(self.repo / master["reference_path"], sprite)
                    write_once(preview, data)
                    attempt["comparisonSha256"] = sha256(data).hexdigest()
                template = {"sha256": attempt["technical"]["sha256"], "referenceSha256": master["sha256"],
                            "comparisonSha256": attempt["comparisonSha256"], "reviewPolicyVersion": REVIEW_POLICY_VERSION,
                            "reviewer": "", "notes": "", "scores": dict.fromkeys(RUBRIC),
                            **dict.fromkeys(stage_checks(number))}
                candidates.append({"stage": number, "status": attempt["status"], "sprite": str(sprite),
                                   "preview": str(preview), "reviewTemplate": template})
            if stage is None and all(phase(job, number) in ("visual_pass", "approved")
                                     for number in range(1, len(job["stages"]) + 1)):
                scope = self.lineup_scope(job_id, job, master)
                evidence = job.get("lineupPreview", {})
                if all(evidence.get(field) == value for field, value in scope.items()):
                    digest = evidence["comparisonSha256"]
                    preview = self.lineup_preview(job_id, digest)
                    verified_bytes(preview, digest)
                else:
                    sprites = [Path(item["sprite"]) for item in candidates]
                    data = lineup_comparison(self.repo / master["reference_path"], sprites)
                    digest = sha256(data).hexdigest()
                    preview = self.lineup_preview(job_id, digest)
                    write_once(preview, data)
                    evidence = job["lineupPreview"] = {**scope, "comparisonSha256": digest}
                dimensions, checks = lineup_rules(len(scope["stageSha256"]))
                template = {**evidence, "reviewer": "", "notes": "", "scores": dict.fromkeys(dimensions),
                            "revisionStages": [], **dict.fromkeys(checks)}
                lineup = {"preview": str(preview), "reviewTemplate": template}
        return {"job": job_id, "master": str(self.repo / master["reference_path"]), "candidates": candidates, "lineup": lineup}

    def stage_comparison_hash(self, job_id: str, stage: int, attempt: dict) -> str:
        digest = attempt.get("comparisonSha256")
        if not digest:
            raise ValueError("Prepare the comparison with review before recording visual evidence")
        preview = self.artifact(job_id, stage, attempt["number"], f"comparison-v{REVIEW_POLICY_VERSION}.png")
        verified_bytes(preview, digest)
        return digest

    def record_review(self, job_id: str, stage: int, report_path: Path) -> dict:
        report = read_json(report_path)
        if not isinstance(report, dict):
            raise ValueError("Visual evidence must be a JSON object")
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            master = self.master(job)
            attempt = latest(job, stage)
            if not attempt or attempt["status"] != "technical_pass":
                raise ValueError("The latest stage must have a pending visual review")
            digest = attempt["technical"]["sha256"]
            verified_bytes(self.artifact(job_id, stage, attempt["number"], "sprite.png"), digest)
            result = visual_result(report, digest, master["sha256"], self.stage_comparison_hash(job_id, stage, attempt), stage)
            result["reviewed"] = stamp()
            if result["passed"]:
                attempt.update(status="visual_pass", visual=result)
            else:
                failed = [field for field in stage_checks(stage) if not result[field]]
                feedback = f"Visual rejection, weighted score {result['score']:.2f}. "
                if failed:
                    feedback += f"Failed checks: {', '.join(failed)}. "
                attempt.update(status="rejected", reason=feedback + result["notes"], visual=result)
            return {"stage": stage, "status": attempt["status"], "nextPhase": phase(job, stage), "result": result}

    def lineup_scope(self, job_id: str, job: dict, master: dict) -> dict:
        stage_hashes = {}
        for stage in range(1, len(job["stages"]) + 1):
            attempt = latest(job, stage)
            if not attempt or attempt["status"] not in ("visual_pass", "approved"):
                raise ValueError("All planned stages must pass visual review before lineup review and owner approval")
            stage_hashes[str(stage)] = self.passed_stage_review(job_id, stage, attempt, master)
        return {"stageSha256": stage_hashes, "referenceSha256": master["sha256"],
                "archetypeId": job["brief"]["archetypeId"], "reviewPolicyVersion": REVIEW_POLICY_VERSION}

    def passed_stage_review(self, job_id: str, stage: int, attempt: dict, master: dict) -> str:
        digest, report = attempt["technical"]["sha256"], attempt["visual"]
        verified_bytes(self.artifact(job_id, stage, attempt["number"], "sprite.png"), digest)
        result = visual_result({**report, "reviewer": report["visualReviewer"]}, digest, master["sha256"],
                               self.stage_comparison_hash(job_id, stage, attempt), stage)
        if not result["passed"] or any(report.get(field) != value for field, value in result.items()):
            raise ValueError(f"Stage {stage} requires a passing review under the current visual policy")
        return digest

    def lineup_preview(self, job_id: str, digest: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid lineup comparison SHA-256")
        return self.workspace / "output" / "drafts" / job_id / f"lineup-{digest}.png"

    def lineup_evidence(self, job_id: str, job: dict, master: dict) -> dict:
        scope = self.lineup_scope(job_id, job, master)
        evidence = job.get("lineupPreview", {})
        if any(evidence.get(field) != value for field, value in scope.items()):
            raise ValueError("Run review for the entire family to prepare the current lineup comparison")
        verified_bytes(self.lineup_preview(job_id, evidence["comparisonSha256"]), evidence["comparisonSha256"])
        return evidence

    def record_lineup(self, job_id: str, report_path: Path) -> dict:
        report = read_json(report_path)
        if not isinstance(report, dict):
            raise ValueError("Lineup evidence must be a JSON object")
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            master = self.master(job)
            reviews = job.setdefault("lineupReviews", [])
            if reviews and reviews[-1]["passed"]:
                raise ValueError("The passing lineup review is immutable")
            result = lineup_result(report, self.lineup_evidence(job_id, job, master))
            result["reviewed"] = stamp()
            reviews.append(result)
            for stage in result["revisionStages"]:
                failed = latest(job, stage)
                failed.update(status="rejected", reason=f"Whole-family visual rejection: {result['notes']}")
            return {"job": job_id, "result": result}

    def passed_lineup(self, job_id: str, job: dict, master: dict) -> dict:
        reviews = job.get("lineupReviews", [])
        if not reviews or not reviews[-1]["passed"]:
            raise ValueError("A passing whole-family lineup review is required before owner approval and export")
        report = reviews[-1]
        evidence = self.lineup_evidence(job_id, job, master)
        result = lineup_result(report, evidence)
        if not result["passed"] or any(report.get(field) != value for field, value in result.items()):
            raise ValueError("The passing lineup review must match the current stage images and visual policy")
        return report

    def approve(self, job_id: str, owner: str, authorization: str) -> dict:
        decision = {"reviewer": owner, "authorization": authorization}
        require_text(decision, ("reviewer", "authorization"))
        with self.checkpoint() as jobs:
            job = self.selected(jobs, job_id)[job_id]
            master = self.master(job)
            validate_family(job["brief"], self.archetypes())
            lineup = self.passed_lineup(job_id, job, master)
            decision["familyReviewSha256"] = sha256(json_bytes(lineup)).hexdigest()
            for stage in range(1, len(job["stages"]) + 1):
                attempt = latest(job, stage)
                if attempt.get("approval") and any(attempt["approval"].get(field) != value for field, value in decision.items()):
                    raise ValueError("The existing owner's decision is immutable")
                if attempt["status"] == "visual_pass":
                    attempt.update(status="approved", approval={**decision, "approvedAt": stamp()})
            return {"job": job_id, "approvedStages": len(job["stages"])}

    @staticmethod
    def revision_reason(job: dict, style: dict) -> str | None:
        if (style["sha256"], style["version"]) != (job["referenceSha256"], job["styleVersion"]):
            return "Master artwork changed. Review retained artwork against the current master and revise before production."
        records = [attempts[-1] for attempts in job["stages"] if attempts]
        if any("visual" in record and record["visual"].get("reviewPolicyVersion") != REVIEW_POLICY_VERSION
               for record in records):
            return "A stage review predates the current visual quality gate."
        reviews = job.get("lineupReviews", [])
        if any(record["status"] == "approved" for record in records) and (
            not reviews or reviews[-1].get("reviewPolicyVersion") != REVIEW_POLICY_VERSION
        ):
            return "Owner approval predates the required whole-family review."
        return None

    def status(self, job_id: str | None, world_id: str | None = None, validate: bool = False) -> dict:
        families, totals, worlds = {}, Counter(), {}
        master = None
        with self.checkpoint(read_only=True) as jobs:
            style = read_json(self.repo / "references" / "style_manifest.json") if jobs else None
            for key, job in self.selected(jobs, job_id).items():
                world = job["brief"]["worldId"]
                if world_id is not None and world_id != world:
                    continue
                category = job["brief"]["monsterType"]
                category_totals = worlds.setdefault(world, {}).setdefault(category, Counter())
                category_totals["plannedFamilies"] += 1
                stages = []
                revision_reason = self.revision_reason(job, style)
                reviews = job.get("lineupReviews", [])
                for stage in range(1, len(job["stages"]) + 1):
                    record = latest(job, stage) or {}
                    prior_phase = phase(job, stage)
                    status = "revision_required" if revision_reason and "sourceSha256" in record else prior_phase
                    totals[status] += 1
                    generated = any("sourceSha256" in item for item in job["stages"][stage - 1])
                    category_totals.update({"plannedStages": 1, "generatedStages": int(generated),
                                            "approvedStages": int(status == "approved"),
                                            "exportedStages": int(bool(record.get("exports")))})
                    if validate and "technical" in record:
                        if status in ("approved", "visual_pass"):
                            master = master or verify_master(self.repo)
                            self.passed_stage_review(key, stage, record, master)
                        else:
                            verified_bytes(self.artifact(key, stage, record["number"], "sprite.png"), record["technical"]["sha256"])
                    stages.append({"stage": stage, "status": status, "attempts": record.get("number", 0),
                                   "maxAttempts": attempt_limit(job, stage),
                                   "retryExtensions": job.get("retryExtensions", {}).get(str(stage), []),
                                   "reason": record.get("reason"), "score": record.get("visual", {}).get("score"),
                                   "exports": record.get("exports", []), "generated": generated})
                    if status != prior_phase:
                        stages[-1]["checkpointStatus"] = prior_phase
                families[key] = {"worldId": world, "monsterType": category, "stages": stages}
                if revision_reason:
                    families[key]["revisionRequired"] = revision_reason
                if reviews:
                    families[key]["lineupReview"] = reviews[-1]
                if validate and not revision_reason and reviews and reviews[-1]["passed"]:
                    master = master or verify_master(self.repo)
                    self.passed_lineup(key, job, master)
        return {"totals": dict(totals), "worlds": worlds, "jobs": families}

    def export(self, job_id: str | None) -> dict:
        with self.checkpoint() as jobs:
            files, sprites, families, revisions = {}, {}, [], []
            master, skipped = None, {}
            style = read_json(self.repo / "references" / "style_manifest.json") if jobs else None
            for key, job in self.selected(jobs, job_id).items():
                revision_reason = self.revision_reason(job, style)
                if revision_reason:
                    if job_id is not None:
                        raise ValueError(f"Unity export requires revision: {revision_reason}")
                    skipped[key] = revision_reason
                    continue
                if any(phase(job, index) != "approved" for index in range(1, len(job["stages"]) + 1)):
                    if job_id is not None:
                        raise ValueError("Unity export requires owner approval for every planned stage")
                    continue
                master = master or verify_master(self.repo)
                self.require_job_master(job, master)
                brief = job["brief"]
                validate_family(brief, self.archetypes())
                lineup = self.passed_lineup(key, job, master)
                lineup_hash = sha256(json_bytes(lineup)).hexdigest()
                family = {field: brief[field] for field in ("familyId", "displayName", "description", "worldId",
                                                           "gameElement", "monsterType", "isNewFamily", "learnsetElement",
                                                           "archetypeId")
                          if field in brief}
                preview = f"reviews/{key}-lineup.png"
                comparison_hash = lineup["comparisonSha256"]
                files[preview] = verified_bytes(self.lineup_preview(key, comparison_hash), comparison_hash)
                family.update(lineupReview=lineup, lineupPreviewPath=preview)
                family["stages"] = []
                for spec in brief["stages"]:
                    stage = spec["stage"]
                    attempt = latest(job, stage)
                    if attempt["approval"].get("familyReviewSha256") != lineup_hash:
                        raise ValueError("Owner approval must identify the exact passing lineup review")
                    technical = attempt["technical"]
                    name = f"{key}_s{stage:02d}"
                    path, review_path = f"sprites/{name}.png", f"reviews/{name}.json"
                    sprites[path] = (self.artifact(key, stage, attempt["number"], "sprite.png"), technical["sha256"])
                    files[review_path] = json_bytes({**attempt["visual"], **attempt["approval"], "approved": True, "stage": stage,
                                                     "width": technical["width"], "height": technical["height"]})
                    family["stages"].append({"stage": stage, "name": spec["name"], "title": spec["title"],
                                             "path": path, "reviewPath": review_path,
                                             "reviewSha256": sha256(files[review_path]).hexdigest(),
                                             **{field: technical[field] for field in ("sha256", "pivot", "bounds")}})
                    revisions.append(attempt)
                families.append(family)
            if not families:
                raise ValueError("No owner-approved families to export")
            manifest = {"schemaVersion": 1, "styleVersion": master["version"], "reviewPolicyVersion": REVIEW_POLICY_VERSION,
                        "referenceSha256": master["sha256"], "families": sorted(families, key=lambda item: item["familyId"])}
            files["manifest.json"] = json_bytes(manifest)
            parent = self.workspace / "output" / "unity"
            parent.mkdir(parents=True, exist_ok=True)
            tag = sha256(files["manifest.json"]).hexdigest()[:16]
            package = parent / f"{job_id or 'batch'}-{tag}"
            if package.exists():
                for name, data in files.items():
                    verified_bytes(package / name, sha256(data).hexdigest())
                for name, (source, digest) in sprites.items():
                    verified_bytes(source, digest)
                    verified_bytes(package / name, digest)
            else:
                with TemporaryDirectory(dir=parent) as temp:
                    staging = Path(temp) / "package"
                    for name, data in files.items():
                        write_once(staging / name, data)
                    for name, (source, digest) in sprites.items():
                        write_once(staging / name, verified_bytes(source, digest))
                    staging.rename(package)
            for attempt in revisions:
                packages = attempt.setdefault("exports", [])
                if package.name not in packages:
                    packages.append(package.name)
            result = {"manifest": str(package / "manifest.json"), "families": len(families), "stages": len(revisions)}
            if skipped:
                result["skippedRevisionRequired"] = skipped
            return result
