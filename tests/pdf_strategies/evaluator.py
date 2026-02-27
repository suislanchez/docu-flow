"""
Evaluates and compares StrategyResult objects across all 4 strategies.

Scoring (no ground truth needed — scores on observable output quality):
  - section_found + confidence  → 35 pts
  - criteria count (≥ 5 = full, scaled)  → 30 pts
  - top_8 populated (all 8 present)       → 20 pts
  - criteria have source_page citations   → 10 pts
  - success (no errors)                   →  5 pts
  Total: 100 pts

The Rich table shows all strategies side-by-side with color coding.
"""

from __future__ import annotations

from tests.pdf_strategies.result import StrategyResult


def score(result: StrategyResult) -> float:
    """Return a 0–100 quality score for *result*."""
    if not result.success:
        return 0.0

    pts = 0.0

    # Section detection (35 pts)
    if result.section_found:
        pts += 20.0
        pts += min(15.0, result.section_confidence * 15.0)

    # Criteria count (30 pts) — 10+ criteria = full score
    if result.total_criteria > 0:
        pts += min(30.0, result.total_criteria * 3.0)

    # Top-8 populated (20 pts)
    n_top8 = len(result.top_8_disqualifiers)
    pts += min(20.0, n_top8 * 2.5)

    # Source page citations on criteria (10 pts)
    if result.criteria:
        cited = sum(1 for c in result.criteria if c.source_page is not None)
        pts += (cited / len(result.criteria)) * 10.0

    # No errors (5 pts)
    if result.error is None:
        pts += 5.0

    return round(pts, 1)


def print_comparison_table(results: list[StrategyResult]) -> None:
    """Print a Rich comparison table to stdout."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        _print_rich(results, Console(), box)
    except ImportError:
        _print_plain(results)


def _print_rich(results: list[StrategyResult], console, box) -> None:
    from rich.table import Table
    from rich.text import Text

    table = Table(
        title="PDF Strategy Comparison",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold cyan",
    )

    table.add_column("Metric", style="bold", min_width=22)
    for r in results:
        table.add_column(r.strategy_name, min_width=16, justify="center")

    scores = [score(r) for r in results]
    best_score = max(scores) if scores else 0

    def _color_bool(val: bool) -> Text:
        return Text("YES", style="green bold") if val else Text("no", style="red")

    def _color_score(s: float) -> Text:
        color = "green bold" if s >= 70 else ("yellow" if s >= 40 else "red")
        return Text(f"{s:.1f}/100", style=color)

    def _color_count(n: int) -> Text:
        color = "green" if n >= 10 else ("yellow" if n >= 5 else "red")
        return Text(str(n), style=color)

    def _color_cost(c: float) -> Text:
        color = "green" if c < 0.10 else ("yellow" if c < 1.00 else "red")
        return Text(f"${c:.4f}", style=color)

    def _color_latency(s: float) -> Text:
        color = "green" if s < 15 else ("yellow" if s < 60 else "red")
        return Text(f"{s:.1f}s", style=color)

    table.add_row("Overall score", *[_color_score(s) for s in scores])
    table.add_row("Success", *[_color_bool(r.success) for r in results])
    table.add_row("Error", *[Text(r.error or "—", style="red" if r.error else "dim") for r in results])
    table.add_row("Section found", *[_color_bool(r.section_found) for r in results])
    table.add_row("Section confidence", *[Text(f"{r.section_confidence:.2f}") for r in results])
    table.add_row("Section name", *[Text(r.section_name or "—", style="dim") for r in results])
    table.add_row("Section pages", *[Text(str(r.section_pages or "—")) for r in results])
    table.add_row("Total criteria", *[_color_count(r.total_criteria) for r in results])
    table.add_row("  Inclusion", *[Text(str(r.inclusion_count)) for r in results])
    table.add_row("  Exclusion", *[Text(str(r.exclusion_count)) for r in results])
    table.add_row("Top-8 disqualifiers", *[_color_count(len(r.top_8_disqualifiers)) for r in results])
    table.add_row("Criteria with page cites", *[
        Text(f"{sum(1 for c in r.criteria if c.source_page is not None)}/{r.total_criteria}")
        for r in results
    ])
    table.add_row("Latency", *[_color_latency(r.latency_seconds) for r in results])
    table.add_row("Est. cost", *[_color_cost(r.estimated_cost_usd) for r in results])

    console.print()
    console.print(table)
    console.print()

    # Top-8 disqualifiers for the best-scoring strategy
    best_result = results[scores.index(best_score)]
    if best_result.top_8_disqualifiers:
        top8_table = Table(
            title=f"Top-8 Disqualifiers ({best_result.strategy_name}  —  best score {best_score:.0f}/100)",
            box=box.SIMPLE,
            title_style="bold green",
        )
        top8_table.add_column("Rank", width=6, justify="center")
        top8_table.add_column("Power", width=12)
        top8_table.add_column("Criterion text", min_width=50)
        top8_table.add_column("Reasoning", min_width=40)

        power_colors = {"very_high": "red bold", "high": "yellow", "medium": "cyan", "low": "dim"}
        for d in sorted(best_result.top_8_disqualifiers, key=lambda x: x.rank, reverse=True):
            color = power_colors.get(d.disqualification_power, "white")
            top8_table.add_row(
                Text(str(d.rank), style="bold"),
                Text(d.disqualification_power, style=color),
                Text(d.criterion_text[:120] + ("…" if len(d.criterion_text) > 120 else "")),
                Text(d.reasoning[:100] + ("…" if len(d.reasoning) > 100 else ""), style="dim"),
            )
        console.print(top8_table)
        console.print()


def _print_plain(results: list[StrategyResult]) -> None:
    print("\n" + "=" * 80)
    print("PDF STRATEGY COMPARISON")
    print("=" * 80)
    headers = ["Metric"] + [r.strategy_name for r in results]
    print("  ".join(f"{h:<20}" for h in headers))
    print("-" * 80)

    rows = [
        ("Score", [f"{score(r):.1f}/100" for r in results]),
        ("Success", [str(r.success) for r in results]),
        ("Section found", [str(r.section_found) for r in results]),
        ("Criteria count", [str(r.total_criteria) for r in results]),
        ("Top-8 count", [str(len(r.top_8_disqualifiers)) for r in results]),
        ("Latency (s)", [f"{r.latency_seconds:.1f}" for r in results]),
        ("Cost ($)", [f"${r.estimated_cost_usd:.4f}" for r in results]),
    ]
    for label, values in rows:
        print("  ".join(f"{v:<20}" for v in [label] + values))

    print("=" * 80 + "\n")
