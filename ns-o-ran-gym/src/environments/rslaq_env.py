from typing_extensions import override
import numpy as np
import uuid
import time
import subprocess
import selectors
import fcntl
import csv
import os
import glob
from posix_ipc import Semaphore, O_CREAT
from nsoran.ns_env import NsOranEnv
from nsoran.action_controller import ActionController
from nsoran.datalake import SQLiteDatabaseAPI
from gymnasium import spaces

SLICE_NAMES = {1: "eMBB", 2: "URLLC", 3: "MTC"}

SLA_TARGETS = {
    1: {
        "outage_kpis": {"min_throughput_mbps": 10.0},
        "soft_kpis": {"max_throughput_mbps": 15.0},
    },
    2: {
        "outage_kpis": {"max_bfs_pct": 3.0},
    },
    3: {},
}

SLA_WEIGHTS = {1: 0.33, 2: 0.40, 3: 0.27}
P_STA_WEIGHTS = np.array([0.33, 0.40, 0.27])

MAX_BTX = 200000.0
MAX_TDP = 1000.0
SCHEDULER_COST = 1


class RslaqEnv(NsOranEnv):
    """
    RSLAQ DRL Environment for O-RAN QoS xApp.

    State (Eq. 1): per-slice [btx, bfs, rsh, tdp] -> 3 slices x 4 features, normalized to [0,1]
    Action: per-slice PRB allocation (dedicated%, min%, max%) -> 3 slices x 3 params
    Reward (Eq. 8-19): SLA-aware with outage/soft KPI violations and r_opt optimization
    """

    def __init__(
        self,
        ns3_path: str,
        scenario_configuration: dict,
        output_folder: str,
        optimized: bool = False,
        sla_weights: dict | None = None,
    ):
        scenario_configuration.setdefault("simId", [""])
        scenario_configuration.setdefault("indicationPeriodicity", [10])
        scenario_configuration.setdefault("scenario", ["normal"])
        scenario_configuration.setdefault("seed", [1])
        scenario_configuration.setdefault("appStart", [0.5])
        scenario_configuration.setdefault("simTime", [4])

        super().__init__(
            ns3_path=ns3_path,
            scenario="rslaq-simulation-mac-slicing",
            scenario_configuration=scenario_configuration,
            output_folder=output_folder,
            optimized=optimized,
            skip_configuration=True,
            control_header=["timestamp", "sliceId", "dedicatedPRB", "minPRB", "maxPRB"],
            log_file="RslaqActions.txt",
            control_file="rslaq_actions_for_ns3.csv",
        )

        self.num_slices = 3
        self.num_ues = scenario_configuration.get("ues", [3])[0]

        if sla_weights is not None:
            global SLA_WEIGHTS
            SLA_WEIGHTS = sla_weights

        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.num_slices, 4),
            dtype=np.float64,
        )

        self.action_space = spaces.Box(
            low=0.0,
            high=100.0,
            shape=(self.num_slices, 3),
            dtype=np.float64,
        )

        self.kpm_data = {}
        self.prev_kpm_data = {}
        self.observations = np.zeros((self.num_slices, 4))
        self.slice_ue_data: dict[int, list[dict]] = {}
        self.num_steps = 0

    def start_sim(self):
        if self.is_open:
            raise ValueError(
                "The environment is open and a new start_sim has been called."
            )

        self.is_open = True

        sim_uuid = str(uuid.uuid4())
        self.scenario_configuration["simId"] = [sim_uuid]

        parameters = self.scenario_configuration

        flat_params = {}
        for k, v in parameters.items():
            if isinstance(v, list) and len(v) == 1:
                flat_params[k] = v[0]
            else:
                flat_params[k] = v

        self.sim_result = {"params": {}, "meta": {}}
        self.sim_result["params"].update(flat_params)

        command = [self.script_executable] + [
            f"--{param}={value}" for param, value in flat_params.items()
        ]

        self.sim_result["meta"]["id"] = sim_uuid
        self.sim_path = os.path.join(self.output_folder, sim_uuid)
        os.makedirs(self.sim_path)

        self.action_controller = ActionController(
            self.sim_path, self.log_file, self.control_file, self.control_header
        )
        self.datalake = SQLiteDatabaseAPI(
            self.sim_path, num_ues_gnb=self.num_ues, debug=False
        )
        self._init_datalake_usecase()

        nameMetricsReadySemaphore = "/sem_metrics_" + sim_uuid
        nameControlSemaphore = "/sem_control_" + sim_uuid
        self.metricsReadySemaphore = Semaphore(
            nameMetricsReadySemaphore, O_CREAT, mode=0o660, initial_value=0
        )
        self.controlSemaphore = Semaphore(
            nameControlSemaphore, O_CREAT, mode=0o660, initial_value=0
        )
        self.last_timestamp = 0

        self.sim_result["meta"]["start_time"] = time.time()
        self.sim_process = subprocess.Popen(
            command,
            cwd=self.sim_path,
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.selector = selectors.DefaultSelector()
        self._set_nonblocking(self.sim_process.stdout)
        self._set_nonblocking(self.sim_process.stderr)
        self.selector.register(self.sim_process.stdout, selectors.EVENT_READ)
        self.selector.register(self.sim_process.stderr, selectors.EVENT_READ)

    @override
    def _compute_action(self, action) -> list[tuple]:
        actions = []
        for slice_idx in range(self.num_slices):
            dedicated = float(action[slice_idx][0])
            actions.append((slice_idx, dedicated, dedicated, 100.0))

        total_ded = sum(a[1] for a in actions)
        if total_ded > 100.0:
            scale = 100.0 / total_ded
            actions = [(s, d * scale, d * scale, x) for s, d, _, x in actions]

        return actions

    @override
    def _get_obs(self):
        return self.observations

    @override
    def _compute_reward(self) -> float:
        slice_metrics: dict[int, dict] = {}
        for slice_idx in range(self.num_slices):
            slice_id = slice_idx + 1
            ues = self.slice_ue_data.get(slice_id, [])
            if ues:
                thr_values = [ue["throughputMbps"] for ue in ues]
                bfs_values = [ue["plr"] for ue in ues]
                slice_metrics[slice_id] = {
                    "mean_thr": float(np.mean(thr_values)),
                    "max_plr": float(max(bfs_values)),
                    "num_ues": len(ues),
                }
            else:
                slice_metrics[slice_id] = {
                    "mean_thr": 0.0,
                    "max_plr": 100.0,
                    "num_ues": 0,
                }

        ues_embb = self.slice_ue_data.get(1, [])
        n_embb = max(len(ues_embb), 1)
        h1 = sum(ue["throughputMbps"] for ue in ues_embb) / n_embb / 15.0

        h2 = np.exp(-slice_metrics[2]["max_plr"] / 100.0)

        ues_mtc = self.slice_ue_data.get(3, [])
        n_mtc = max(len(ues_mtc), 1)
        h3 = sum(ue["throughputMbps"] for ue in ues_mtc) / n_mtc / 10.0

        r_opt = (
            SLA_WEIGHTS[1] * h1
            + SLA_WEIGHTS[2] * h2
            + SLA_WEIGHTS[3] * h3
            + 1.0 / SCHEDULER_COST
        )

        phi: dict[int, float] = {}
        if slice_metrics[1]["num_ues"] > 0 and (
            slice_metrics[1]["mean_thr"]
            < SLA_TARGETS[1]["outage_kpis"]["min_throughput_mbps"]
        ):
            phi[1] = 1.0
        if (
            slice_metrics[2]["num_ues"] > 0
            and slice_metrics[2]["max_plr"]
            > SLA_TARGETS[2]["outage_kpis"]["max_bfs_pct"]
        ):
            any_received = any(
                ue["plr"] < 100.0 for ue in self.slice_ue_data.get(2, [])
            )
            if any_received:
                phi[2] = 1.0

        rho: dict[int, float] = {}
        if slice_metrics[1]["num_ues"] > 0 and (
            slice_metrics[1]["mean_thr"]
            > SLA_TARGETS[1]["soft_kpis"]["max_throughput_mbps"]
        ):
            rho[1] = 1.0

        sum_phi = sum(phi.values())
        sum_rho = sum(rho.values())

        if sum_phi > 0:
            outage_penalty = -sum(
                phi.get(j, 0.0) * SLA_WEIGHTS[j] for j in range(1, self.num_slices + 1)
            )
            return outage_penalty

        if sum_rho > 0:
            return float(r_opt) * 0.5

        return float(r_opt)

    @override
    def _init_datalake_usecase(self):
        pass

    @override
    def _fill_datalake_usecase(self):
        kpm_files = glob.glob(os.path.join(self.sim_path, "rslaq-kpms.txt"))
        if not kpm_files:
            return

        latest_rows = {}
        with open(kpm_files[0], "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = int(row["timestamp"])
                ue_imsi = int(row["ueImsi"])
                if ts >= self.last_timestamp:
                    latest_rows[ue_imsi] = row
                    self.last_timestamp = ts

        slice_agg: dict[int, dict] = {}
        slice_ue: dict[int, list[dict]] = {}

        for ue_imsi, row in latest_rows.items():
            slice_id = int(row["sliceId"])
            if slice_id not in slice_agg:
                slice_agg[slice_id] = {
                    "btx": 0,
                    "plr_sum": 0.0,
                    "rsh_sum": 0.0,
                    "tdp": 0,
                    "count": 0,
                }
            if slice_id not in slice_ue:
                slice_ue[slice_id] = []

            btx = float(row["txBytes"])
            plr = float(row["plr"])
            rsh = float(row["resourceSharePct"])
            tdp = float(row["lostPackets"])
            thr = float(row["throughputMbps"])

            sd = slice_agg[slice_id]
            sd["btx"] += btx
            sd["plr_sum"] += plr
            sd["rsh_sum"] += rsh
            sd["tdp"] += tdp
            sd["count"] += 1

            slice_ue[slice_id].append({"throughputMbps": thr, "plr": plr})

        self.slice_ue_data = slice_ue

        for slice_idx in range(self.num_slices):
            slice_id = slice_idx + 1
            if slice_id in slice_agg and slice_agg[slice_id]["count"] > 0:
                sd = slice_agg[slice_id]
                n = sd["count"]
                self.observations[slice_idx] = [
                    min(sd["btx"] / MAX_BTX, 1.0),
                    sd["plr_sum"] / n / 100.0,
                    sd["rsh_sum"] / n / 100.0,
                    min(sd["tdp"] / MAX_TDP, 1.0),
                ]
            else:
                self.observations[slice_idx] = [0.0, 0.0, 0.0, 0.0]
