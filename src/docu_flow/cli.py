"""
Simple CLI for running the pipeline locally.

Usage:
    docu-flow process path/to/protocol.pdf
    docu-flow screen path/to/protocol.pdf --patient '{"age": 35, "diagnoses": ["T2DM"]}'
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def app() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="docu-flow",
        description="Clinical trial eligibility screening",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # process sub-command
    p_process = sub.add_parser("process", help="Extract criteria from a protocol PDF")
    p_process.add_argument("pdf", type=Path, help="Path to the protocol PDF")
    p_process.add_argument("--top-n", type=int, default=8, help="Number of top disqualifiers")
    p_process.add_argument("--output", type=Path, help="Write JSON output to this file")

    # screen sub-command
    p_screen = sub.add_parser("screen", help="Screen a patient against a protocol PDF")
    p_screen.add_argument("pdf", type=Path, help="Path to the protocol PDF")
    p_screen.add_argument("--patient", required=True, help="JSON string of patient data")
    p_screen.add_argument("--patient-id", default="cli_patient")

    args = parser.parse_args()

    if args.command == "process":
        _cmd_process(args)
    elif args.command == "screen":
        _cmd_screen(args)


def _cmd_process(args) -> None:
    from docu_flow.config import settings
    from docu_flow.logging import configure_logging
    from docu_flow.pipeline.orchestrator import run_protocol_pipeline

    configure_logging()
    settings.ensure_dirs()

    console.print(f"[bold]Processing:[/bold] {args.pdf}")
    extracted = run_protocol_pipeline(args.pdf, top_n_disqualifiers=args.top_n)

    table = Table(title=f"Top {args.top_n} Disqualifiers — {extracted.protocol_title or args.pdf.name}")
    table.add_column("#", style="dim")
    table.add_column("Power", style="bold red")
    table.add_column("Criterion text")
    table.add_column("Page", justify="right")

    for i, c in enumerate(extracted.top_disqualifiers, 1):
        table.add_row(
            str(i),
            c.disqualification_power.value,
            c.text[:120] + ("…" if len(c.text) > 120 else ""),
            str(c.source_page or "?"),
        )

    console.print(table)
    console.print(f"\nTotal criteria extracted: {len(extracted.criteria)}")

    if args.output:
        args.output.write_text(extracted.model_dump_json(indent=2))
        console.print(f"[green]JSON written to {args.output}[/green]")


def _cmd_screen(args) -> None:
    from docu_flow.config import settings
    from docu_flow.logging import configure_logging
    from docu_flow.pipeline.orchestrator import run_protocol_pipeline, run_screening_pipeline
    from docu_flow.schemas.criteria import ScreeningRequest, ScreeningDecision

    configure_logging()
    settings.ensure_dirs()

    try:
        patient_data = json.loads(args.patient)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid --patient JSON: {exc}[/red]")
        sys.exit(1)

    console.print(f"[bold]Processing protocol:[/bold] {args.pdf}")
    extracted = run_protocol_pipeline(args.pdf)

    request = ScreeningRequest(
        patient_id=args.patient_id,
        protocol_id=str(args.pdf),
        patient_data=patient_data,
    )

    result = run_screening_pipeline(request, extracted)

    color = {
        ScreeningDecision.DISQUALIFIED: "red",
        ScreeningDecision.PASSED_PRESCREEN: "green",
        ScreeningDecision.ESCALATE: "yellow",
    }[result.decision]

    console.print(f"\nDecision: [{color}]{result.decision.value.upper()}[/{color}]")
    console.print(f"Confidence: {result.confidence:.0%}")

    if result.failed_criteria:
        console.print("\n[bold red]Failed criteria:[/bold red]")
        for f in result.failed_criteria:
            console.print(f"  • [{f.criterion.id}] {f.reason}")

    if result.escalation_reason:
        console.print(f"\n[yellow]Escalation reason:[/yellow] {result.escalation_reason}")
