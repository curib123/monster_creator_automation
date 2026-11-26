"""Command line entry point for the local artwork factory."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .catalog import add_commands as add_catalog_commands
from .pipeline import MAX_ATTEMPTS, Workflow
from .style import verify_master


def integer_between(low: int, high: int):
    def value(raw: str):
        number = int(raw)
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f"must be an integer from {low} to {high}")
        return number
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Automation checkout with the locked art reference")
    parser.add_argument("--workspace", type=Path, help="Checkpoint and artifact folder (defaults to --repo)")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create immutable family checkpoints from an offline JSON brief")
    prepare.add_argument("--brief", required=True, type=Path)
    prepare.add_argument("--max-attempts", type=integer_between(1, MAX_ATTEMPTS), default=3)
    prepare.add_argument("--size", type=int, choices=(512, 1024, 2048), default=1024)
    prepare.set_defaults(run=lambda workflow, args: workflow.prepare(args.brief, args.max_attempts, args.size))
    doctor = commands.add_parser("doctor", help="Verify the exact owner-approved artwork and metadata")
    doctor.set_defaults(run=lambda workflow, args: {"master": verify_master(workflow.repo),
                                                    "providerMode": "Codex built-in or manual reference-conditioned handoff"})

    resume = commands.add_parser("resume", help="Read offline prompts, ready stages and interrupted request IDs")
    resume.add_argument("--job")
    resume.add_argument("--world", help="Filter by canonical world ID")
    resume.add_argument("--rejected-only", action="store_true", help="Select revisions with a prior QA rejection")
    resume.add_argument("--limit", type=integer_between(1, 525), default=1)
    resume.set_defaults(run=lambda workflow, args: workflow.resume(args.job, args.limit, args.world, args.rejected_only))
    request = commands.add_parser("request", help="Reserve a durable attempt before handing it to the provider")
    request.add_argument("--authorization", help="Owner's explicit authorization for a mass batch")
    request.set_defaults(run=lambda workflow, args: workflow.request(args.job, args.stage, args.authorization))
    fail = commands.add_parser("fail", help="Record a confirmed provider error and release the stage for a bounded retry")
    fail.add_argument("--reason", required=True)
    fail.set_defaults(run=lambda workflow, args: workflow.fail(args.job, args.stage, args.attempt, args.reason))
    extend = commands.add_parser("extend-retry", help="Record one additional retry for one exhausted stage")
    extend.add_argument("--reason", required=True)
    extend.set_defaults(run=lambda workflow, args: workflow.extend_retry(args.job, args.stage, args.reason))
    ingest = commands.add_parser("ingest", help="Record the real provider result and run deterministic sprite QA")
    ingest.add_argument("--image", type=Path, required=True)
    ingest.add_argument("--receipt", type=Path, required=True)
    ingest.set_defaults(run=lambda workflow, args: workflow.ingest(args.job, args.stage, args.attempt, args.image, args.receipt))
    reprocess = commands.add_parser("reprocess", help="Recheck a technical rejection from immutable raw bytes after a processor update")
    reprocess.set_defaults(run=lambda workflow, args: workflow.reprocess(args.job, args.stage, args.attempt))
    review = commands.add_parser("review", help="Create side-by-side light and dark comparison evidence and a review template")
    review.add_argument("--stage", type=integer_between(1, 3))
    review.set_defaults(run=lambda workflow, args: workflow.review(args.job, args.stage))
    record = commands.add_parser("record-review", help="Run visual quality gates on a completed visual evaluation")
    record.add_argument("--report", type=Path, required=True)
    record.set_defaults(run=lambda workflow, args: workflow.record_review(args.job, args.stage, args.report))
    approve = commands.add_parser("approve", help="Record the owner's explicit approval of all visually accepted stages")
    approve.add_argument("--owner", required=True)
    approve.add_argument("--authorization", required=True)
    approve.set_defaults(run=lambda workflow, args: workflow.approve(args.job, args.owner, args.authorization))
    for command in (request, fail, extend, ingest, reprocess, review, record, approve):
        command.add_argument("--job", required=True)
    for command in (request, fail, extend, ingest, reprocess, record):
        command.add_argument("--stage", required=True, type=integer_between(1, 3))
    for command in (fail, ingest, reprocess):
        command.add_argument("--attempt", required=True, type=integer_between(1, MAX_ATTEMPTS))

    status = commands.add_parser("status", help="Report production progress by family, stage and world")
    status.add_argument("--job")
    status.add_argument("--world", help="Filter by canonical world ID")
    status.set_defaults(run=lambda workflow, args: workflow.status(args.job, args.world))
    validate = commands.add_parser("validate", help="Check the integrity of normalized artwork in the checkpoint")
    validate.add_argument("--job")
    validate.add_argument("--world", help="Filter by canonical world ID")
    validate.set_defaults(run=lambda workflow, args: workflow.status(args.job, args.world, validate=True))
    export = commands.add_parser("export", help="Create a versioned Unity package of owner-approved families")
    export.add_argument("--job")
    export.set_defaults(run=lambda workflow, args: workflow.export(args.job))
    add_catalog_commands(commands)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if hasattr(args, "handler"):
            result = args.handler(args)
        else:
            result = args.run(Workflow(args.repo, args.workspace or args.repo), args)
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
