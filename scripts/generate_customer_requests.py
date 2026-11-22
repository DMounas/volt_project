"""VOLT - Customer Request Disaggregation & Reconciliation Pipeline.

Disaggregates hourly aggregate cluster demand into individual, typed customer sessions:
- Fast charging sessions (15 - 60 kWh)
- Battery swapping transactions with discrete integer packs
- Reconciles energy demand per city, hour, and modality within numerical tolerance (<= 0.05%)
- Calculates flexibility envelopes and reason codes
- Outputs reproducible CSV/JSON dataset and reconciliation report
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd

# Add repository root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.customer.envelope import FlexibilityEnvelopeEngine
from engine.customer.synthetic_requests import SyntheticRequestDisaggregator


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Disaggregate aggregate load into customer requests.")
    parser.add_argument("--demo", action="store_true", default=True, help="Run in bounded demo mode (default: True)")
    parser.add_argument("--full", action="store_true", help="Run full multi-year generation")
    parser.add_argument("--max-hours", type=int, default=12, help="Hours per cluster in demo mode (default: 12)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory")

    args = parser.parse_args()
    demo_mode = not args.full

    out_dir = Path(args.output_dir)
    hourly_path = out_dir / "cluster_hourly.csv.gz"
    if not hourly_path.exists():
        raise FileNotFoundError(f"Source aggregate data not found at {hourly_path}")

    print(f"Loading hourly source demand from {hourly_path}...")
    hourly_df = pd.read_csv(hourly_path)
    print(f"Loaded {len(hourly_df):,} hourly cluster records.")

    print(f"Starting request disaggregation (demo_mode={demo_mode}, max_hours={args.max_hours}, seed={args.seed})...")
    disaggregator = SyntheticRequestDisaggregator(
        seed=args.seed,
        pack_capacity_kwh=2.25,
        reconciliation_tolerance_pct=0.05,
    )
    requests, recon_df = disaggregator.disaggregate_hourly_demand(
        hourly_df=hourly_df,
        demo_mode=demo_mode,
        max_hours=args.max_hours,
    )

    print(f"Generated {len(requests):,} individual customer requests.")

    # Convert requests to DataFrame
    req_dicts = [r.model_dump(mode="json") for r in requests]
    requests_df = pd.DataFrame(req_dicts)

    # Compute flexibility envelopes
    envelope_engine = FlexibilityEnvelopeEngine()
    env_dicts = [envelope_engine.compute_envelope(r).model_dump(mode="json") for r in requests]
    envelopes_df = pd.DataFrame(env_dicts)

    # Save to disk
    req_file = out_dir / "customer_requests_disaggregated.csv.gz"
    recon_file = out_dir / "customer_reconciliation_report.csv"
    env_file = out_dir / "customer_flexibility_envelopes.csv.gz"

    requests_df.to_csv(req_file, index=False, compression="gzip")
    recon_df.to_csv(recon_file, index=False)
    envelopes_df.to_csv(env_file, index=False, compression="gzip")

    req_hash = compute_sha256(req_file)
    recon_hash = compute_sha256(recon_file)

    print("\n================ RECONCILIATION SUMMARY ================")
    print(f"Total cluster-hour blocks reconciled: {len(recon_df):,}")
    fc_recon = recon_df[recon_df["modality"] == "FAST_CHARGE"]
    swap_recon = recon_df[recon_df["modality"] == "BATTERY_SWAP"]

    fc_pass = (fc_recon["reconciled"].sum() / len(fc_recon)) * 100.0 if len(fc_recon) > 0 else 100.0
    swap_pack_pass = (swap_recon["pack_reconciled"].sum() / len(swap_recon)) * 100.0 if len(swap_recon) > 0 else 100.0
    swap_pass = (swap_recon["reconciled"].sum() / len(swap_recon)) * 100.0 if len(swap_recon) > 0 else 100.0

    print(f"Fast-Charging MWh Pass Rate (<=0.05% error): {fc_pass:.2f}%")
    print(f"Battery Swapping Integer Pack Ledger Pass Rate (exact 0-pack diff): {swap_pack_pass:.2f}%")
    print(f"Battery Swapping Overall Reconciled Rate (ledger exact + residual <=1.125 kWh): {swap_pass:.2f}%")
    print(f"Max Fast-Charge Disaggregation Error: {fc_recon['error_pct'].max():.4f}%")
    print(f"Max Swap Quantization Energy Residual: {abs(swap_recon['quantization_residual_kwh']).max():.4f} kWh")
    print("========================================================\n")

    print(f"Saved customer requests: {req_file} (SHA-256: {req_hash})")
    print(f"Saved reconciliation report: {recon_file} (SHA-256: {recon_hash})")
    print(f"Saved flexibility envelopes: {env_file}")

    # Update manifest if present
    manifest_path = out_dir / "data_manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        if "files" in manifest:
            manifest["files"]["customer_requests_disaggregated.csv.gz"] = {
                "path": "customer_requests_disaggregated.csv.gz",
                "row_count": len(requests_df),
                "size_bytes": req_file.stat().st_size,
                "sha256": req_hash,
                "description": "Disaggregated individual fast-charging and battery swap requests with flexibility envelopes",
                "records": len(requests_df),
                "provenance": "SYNTHETIC",
                "reconciliation_passed": bool(fc_pass >= 99.9 and swap_pass >= 99.9),
            }
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        print("Updated data_manifest.json.")


if __name__ == "__main__":
    main()
