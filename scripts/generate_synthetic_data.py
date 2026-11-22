#!/usr/bin/env python3
"""CLI Script: Generate Reproducible Five-City Synthetic Energy & Market Data.

Usage:
    python scripts/generate_synthetic_data.py [--demo | --full] [--seed 42] [--overwrite]
"""

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.data.synthetic_generator import SyntheticDataGenerator


def parse_args():
    parser = argparse.ArgumentParser(
        description="VOLT Synthetic Five-City Data Pipeline Generator"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Deterministic random seed (default: 42)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2022-01-01",
        help="Start date YYYY-MM-DD (default: 2022-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-12-31 23:00:00",
        help="End date YYYY-MM-DD HH:MM:SS (default: 2026-12-31 23:00:00)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic",
        help="Directory to save generated datasets (default: data/synthetic)",
    )
    parser.add_argument(
        "--configs-dir",
        type=str,
        default="configs",
        help="Path to configuration directory (default: configs)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate small 14-day dataset sample for fast verification/testing",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate complete 5-year dataset (2022-01-01 to 2026-12-31, 219,120 cluster-hours)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=True,
        help="Overwrite existing synthetic data in destination directory",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    demo_mode = args.demo and not args.full

    print("=" * 70)
    print("VOLT: Synthetic Data Generation Pipeline (Phase 2)")
    print(f"Mode: {'DEMO (14 Days)' if demo_mode else 'FULL (5 Years / 43,824 Hours per Cluster)'}")
    print(f"Random Seed: {args.seed}")
    print(f"Output Directory: {args.output_dir}")
    print("Provenance: Strictly SYNTHETIC (Preserves 1,200 MW & 600 MWh Case Facts)")
    print("=" * 70)

    start_time = time.time()
    generator = SyntheticDataGenerator(
        seed=args.seed,
        start_date=args.start_date,
        end_date=args.end_date,
        configs_dir=Path(args.configs_dir),
    )

    try:
        manifest = generator.generate_all(
            output_dir=Path(args.output_dir),
            demo_mode=demo_mode,
            overwrite=args.overwrite,
        )
        elapsed = time.time() - start_time
        print(f"\nGeneration completed successfully in {elapsed:.2f}s!")
        print("\nGenerated Datasets:")
        for fname, info in manifest["files"].items():
            print(f"  • {fname}: {info['row_count']:,} rows ({info['size_bytes'] / 1024:.1f} KB, SHA-256: {info['sha256'][:12]}...)")
        print(f"\nManifest saved to: {Path(args.output_dir) / 'data_manifest.json'}")
    except Exception as e:
        print(f"\nError generating synthetic data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
