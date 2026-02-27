"""
Run all 4 PDF parsing strategies in parallel and compare results.

Usage:
    # Run against the synthetic fixture (auto-created if missing):
    python tests/pdf_strategies/run_all.py

    # Run against a real protocol PDF:
    python tests/pdf_strategies/run_all.py path/to/protocol.pdf

    # Run only specific strategies (comma-separated: s1,s2,s3,s4):
    python tests/pdf_strategies/run_all.py path/to/protocol.pdf --only s2,s3

    # Skip a strategy:
    python tests/pdf_strategies/run_all.py --skip s4

    # Save results to JSON:
    python tests/pdf_strategies/run_all.py --out results.json

Requirements:
    ANTHROPIC_API_KEY  — required for S1, S2, S4
    GEMINI_API_KEY     — required for S3
    unstructured[pdf]  — required for S4 (pip install "unstructured[pdf]")
    google-generativeai — required for S3 (pip install google-generativeai)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from tests.pdf_strategies.evaluator import print_comparison_table, score
from tests.pdf_strategies.result import StrategyResult
from tests.pdf_strategies.strategies.s1_pymupdf import PyMuPDFStrategy
from tests.pdf_strategies.strategies.s2_claude import ClaudeVisionStrategy
from tests.pdf_strategies.strategies.s3_gemini import GeminiStrategy
from tests.pdf_strategies.strategies.s4_unstructured import UnstructuredStrategy

ALL_STRATEGIES = {
    "s1": PyMuPDFStrategy(),
    "s2": ClaudeVisionStrategy(),
    "s3": GeminiStrategy(),
    "s4": UnstructuredStrategy(),
}

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_SYNTHETIC_PDF = _FIXTURES_DIR / "synthetic_protocol.pdf"


def _ensure_synthetic_fixture() -> Path:
    """Create a synthetic clinical trial protocol PDF if it doesn't exist."""
    _FIXTURES_DIR.mkdir(exist_ok=True)
    if _SYNTHETIC_PDF.exists():
        return _SYNTHETIC_PDF

    try:
        from tests.pdf_strategies.fixtures.make_synthetic import create_synthetic_protocol
        create_synthetic_protocol(_SYNTHETIC_PDF)
        print(f"Created synthetic fixture: {_SYNTHETIC_PDF}")
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not create synthetic fixture: {exc}")
        raise SystemExit(1) from exc

    return _SYNTHETIC_PDF


def _load_env() -> None:
    """Load .env from project root if present."""
    env_path = Path(__file__).parents[2] / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            # Manual fallback
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def run_strategies(
    pdf_path: Path,
    strategies: dict,
) -> list[StrategyResult]:
    """Run all strategies in parallel and return results sorted by name."""
    results: list[StrategyResult] = []

    print(f"\nRunning {len(strategies)} strategies on: {pdf_path.name}")
    print(f"File size: {pdf_path.stat().st_size / 1024:.1f} KB\n")

    with ThreadPoolExecutor(max_workers=len(strategies)) as executor:
        futures = {
            executor.submit(strategy.run, pdf_path): name
            for name, strategy in strategies.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                result = StrategyResult(
                    strategy_name=ALL_STRATEGIES[name].name,
                    pdf_name=pdf_path.name,
                    success=False,
                    error=str(exc),
                )
            status = "OK" if result.success else f"FAILED: {result.error}"
            print(f"  {result.strategy_name:<20} {status}")
            results.append(result)

    return sorted(results, key=lambda r: r.strategy_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare PDF parsing strategies")
    parser.add_argument("pdf", nargs="?", help="Path to protocol PDF (default: synthetic fixture)")
    parser.add_argument("--only", help="Comma-separated strategies to run (s1,s2,s3,s4)")
    parser.add_argument("--skip", help="Comma-separated strategies to skip")
    parser.add_argument("--out", help="Save full results to this JSON file")
    args = parser.parse_args()

    _load_env()

    pdf_path = Path(args.pdf) if args.pdf else _ensure_synthetic_fixture()
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    # Select strategies
    selected = dict(ALL_STRATEGIES)
    if args.only:
        keys = {k.strip().lower() for k in args.only.split(",")}
        selected = {k: v for k, v in selected.items() if k in keys}
    if args.skip:
        keys = {k.strip().lower() for k in args.skip.split(",")}
        selected = {k: v for k, v in selected.items() if k not in keys}

    if not selected:
        print("No strategies selected. Use --only or remove --skip.")
        sys.exit(1)

    t_start = time.perf_counter()
    results = run_strategies(pdf_path, selected)
    wall_time = time.perf_counter() - t_start

    print(f"\nTotal wall time: {wall_time:.1f}s  (strategies ran in parallel)")

    print_comparison_table(results)

    # Save to JSON if requested
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps([asdict(r) for r in results], indent=2))
        print(f"Results saved to: {out_path}")

    # Exit with non-zero if all strategies failed
    if not any(r.success for r in results):
        sys.exit(1)

    # Print winner
    successful = [r for r in results if r.success]
    if successful:
        best = max(successful, key=score)
        print(f"Best strategy: {best.strategy_name}  (score: {score(best):.1f}/100)\n")


if __name__ == "__main__":
    main()
