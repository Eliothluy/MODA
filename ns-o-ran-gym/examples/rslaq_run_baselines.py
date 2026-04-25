import subprocess
import os
import csv
import json
import time

NS3_PATH = "/home/eliothluy/Documentos/artigo_jussi/ns-3-dev"
BINARY = os.path.join(NS3_PATH, "build/scratch/ns3.46-rslaq-simulation-fixed-default")
OUTPUT_BASE = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results_baselines"
SCHEDULERS = [
    ("rr", "RR"),
    ("pf", "PF"),
    ("maxcqi", "MAXCQI"),
]
SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]
SCHED_FILE_MAP = {"rr": "RR", "pf": "PF", "maxcqi": "MAXCQI"}
NUM_SEEDS = 3


def run_single(scheduler_arg, scheduler_file, scenario, seed, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        BINARY,
        f"--scheduler={scheduler_arg}",
        f"--scenario={scenario}",
        f"--seed={seed}",
        "--simTime=4",
        "--appStart=0.5",
        f"--outputDir={output_dir}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return None
    ue_csv = os.path.join(output_dir, f"rslaq_{scenario}_{scheduler_file}_ue.csv")
    if os.path.exists(ue_csv):
        return ue_csv
    return None


def collect_all_data():
    all_data = {}
    total = len(SCHEDULERS) * len(SCENARIOS) * NUM_SEEDS
    done = 0

    for sched_arg, sched_file in SCHEDULERS:
        for sc in SCENARIOS:
            key = f"{sc}_{sched_arg}"
            embb_thr = []
            mtc_thr = []
            urllc_plr = []

            for seed in range(1, NUM_SEEDS + 1):
                out_dir = os.path.join(OUTPUT_BASE, sched_arg, sc, f"seed_{seed}")
                ue_csv = run_single(sched_arg, sched_file, sc, seed, out_dir)
                done += 1

                if ue_csv is None:
                    print(f"  [{done}/{total}] FAIL {sched_arg}/{sc}/seed_{seed}")
                    continue

                with open(ue_csv) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        slice_name = row.get("slice", "").strip().lower()
                        thr = float(row.get("throughput_mbps", 0))
                        plr_raw = float(row.get("plr", 0))
                        plr_pct = plr_raw * 100.0

                        if slice_name == "embb":
                            embb_thr.append(thr)
                        elif slice_name == "urllc":
                            urllc_plr.append(plr_pct)
                        elif slice_name == "mtc":
                            mtc_thr.append(thr)

                if done % 15 == 0:
                    print(f"  [{done}/{total}] {sched_arg}/{sc}/seed_{seed}")

            all_data[key] = {
                "embb_thr": embb_thr,
                "mtc_thr": mtc_thr,
                "urllc_plr": urllc_plr,
            }
            n_e = len(embb_thr)
            n_u = len(urllc_plr)
            n_m = len(mtc_thr)
            print(f"  DONE {key:35s}: eMBB={n_e}, URLLC={n_u}, MTC={n_m}")

    return all_data


def main():
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    start = time.time()
    total = len(SCHEDULERS) * len(SCENARIOS) * NUM_SEEDS
    print(f"Running {total} baseline simulations")
    print()

    all_data = collect_all_data()

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed / 60:.1f} min")

    out_file = os.path.join(OUTPUT_BASE, "baseline_cdf_data.json")
    with open(out_file, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"Data saved to {out_file}")


if __name__ == "__main__":
    main()
