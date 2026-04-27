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

# SLA Targets para a função de recompensa
SLA_TARGETS = {
    1: {"min_throughput_mbps": 100.0},   # eMBB: foco em throughput
    2: {"max_delay_ms": 5.0},             # URLLC: foco em latência ultra-baixa
    3: {"max_buffer_pct": 1.0},           # MTC: foco em entrega (proxy via lostPackets)
}

# Pesos de importância para a recompensa total
ALPHA = 1.0 / 3.0
BETA = 1.0 / 3.0
GAMMA = 1.0 / 3.0

# P_STA decomposition: 50% estático + 50% dinâmico do agente
P_STA_WEIGHTS = np.array([0.33, 0.40, 0.27])
P_STA = P_STA_WEIGHTS * 0.5  # [0.165, 0.200, 0.135]

# Constantes de normalização do observation space
MAX_THR = 150.0       # Mbps
MAX_BTX = 200000.0    # bytes
MAX_PLR = 100.0       # %
MAX_TDP = 1000.0      # packets
MAX_RSH = 100.0       # %

SCHEDULER_COST = 1
CRITICAL_OVERFLOW_THRESHOLD = 5000  # penalidade severa se total_dropped > threshold


class RslaqEnv(NsOranEnv):
    """
    RSLAQ DRL Environment for O-RAN QoS xApp.

    State: per-slice [throughput_mbps, txBytes, plr, resourceSharePct, lostPackets]
           -> 3 slices x 5 features, normalized to [0,1]
    Action: 3 continuous values in [-1, 1] -> softmax -> p_opt (50% dinâmico)
            -> p_final = P_STA + p_opt * 0.5
    Reward: SLA-aware com R_eMBB (throughput), R_URLLC (delay), R_MTC (buffer)
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
        scenario_configuration.setdefault("periodMs", [10])
        scenario_configuration.setdefault("scenario", ["normal"])
        scenario_configuration.setdefault("seed", [1])
        scenario_configuration.setdefault("appStart", [0.5])
        scenario_configuration.setdefault("simTime", [4])

        super().__init__(
            ns3_path=ns3_path,
            scenario="rslaq-sim",  # <-- nome correto do executável
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

        # Observation space: 3 slices x 5 features
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.num_slices, 5),
            dtype=np.float64,
        )

        # Action space: 3 continuous values [-1, 1] -> softmax -> p_opt
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(3,),
            dtype=np.float64,
        )

        self.kpm_data = {}
        self.prev_kpm_data = {}
        self.observations = np.zeros((self.num_slices, 5))
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
        """
        Converte ação contínua do agente (3 valores em [-1,1]) para
        dedicatedPRB por slice usando Softmax + P_STA decomposition.

        P_final = P_STA + softmax(action) * 0.5
        """
        raw = np.array(action[:3], dtype=np.float64).flatten()

        # Softmax com estabilidade numérica
        exp_a = np.exp(raw - np.max(raw))
        p_opt = exp_a / exp_a.sum()
        p_opt *= 0.5  # agente controla 50%

        p_final = P_STA + p_opt

        # Renormalizar para somar 1.0
        p_final /= p_final.sum()

        actions = []
        for slice_idx in range(self.num_slices):
            dedicated = float(p_final[slice_idx] * 100.0)
            actions.append((slice_idx, dedicated, dedicated, 100.0))

        return actions

    @override
    def _get_obs(self):
        return self.observations

    @override
    def _compute_reward(self) -> float:
        """
        Reward function conforme especificação RSLAQ:

        R_eMBB = max(0, throughput_eMBB / SLA_eMBB)
        R_URLLC = 1.0 se delay <= SLA; exp(-(delay - SLA)) caso contrário
        R_MTC   = 1.0 - (buffer / max_buffer)

        R_total = alpha*R_eMBB + beta*R_URLLC + gamma*R_MTC

        Penalidade -10 se buffer overflow maciço.
        """
        # Coletar métricas por slice
        slice_metrics: dict[int, dict] = {}
        for slice_idx in range(self.num_slices):
            slice_id = slice_idx + 1
            ues = self.slice_ue_data.get(slice_id, [])
            if ues:
                thr_values = [ue["throughputMbps"] for ue in ues]
                plr_values = [ue["plr"] for ue in ues]
                slice_metrics[slice_id] = {
                    "mean_thr": float(np.mean(thr_values)),
                    "max_plr": float(max(plr_values)),
                    "num_ues": len(ues),
                }
            else:
                slice_metrics[slice_id] = {
                    "mean_thr": 0.0,
                    "max_plr": 100.0,
                    "num_ues": 0,
                }

        # R_eMBB: throughput normalizado pelo SLA (clipagem em 0)
        embb_thr = slice_metrics[1]["mean_thr"]
        r_embb = max(0.0, embb_thr / SLA_TARGETS[1]["min_throughput_mbps"])

        # R_URLLC: penalização exponencial de delay (proxy: max_plr como proxy de congestionamento)
        # Nota: o KPM não tem delay direto; usamos max_plr como proxy de qualidade de serviço
        urllc_plr = slice_metrics[2]["max_plr"]
        # Mapeamos PLR para um "delay virtual": PLR alto = delay alto
        virtual_delay = urllc_plr * 0.5  # heurística: 3% PLR ~ 1.5ms delay virtual
        if virtual_delay <= SLA_TARGETS[2]["max_delay_ms"]:
            r_urllc = 1.0
        else:
            r_urllc = np.exp(-(virtual_delay - SLA_TARGETS[2]["max_delay_ms"]))

        # R_MTC: penalização por acúmulo de pacotes (proxy: lostPackets / max_buffer)
        ues_mtc = self.slice_ue_data.get(3, [])
        total_mtc_dropped = sum(ue.get("lostPackets", 0) for ue in ues_mtc)
        r_mtc = 1.0 - min(total_mtc_dropped / MAX_TDP, 1.0)

        # Recompensa total ponderada
        reward = ALPHA * r_embb + BETA * r_urllc + GAMMA * r_mtc

        # Penalidade severa por buffer overflow maciço
        total_dropped = sum(
            ue.get("lostPackets", 0)
            for slice_id in self.slice_ue_data
            for ue in self.slice_ue_data[slice_id]
        )
        if total_dropped > CRITICAL_OVERFLOW_THRESHOLD:
            reward -= 10.0

        return float(reward)

    @override
    def _init_datalake_usecase(self):
        pass

    @override
    def _fill_datalake_usecase(self):
        """
        Lê rslaq-kpms.txt e agrega métricas por slice em observations[3][5].

        Features: [throughput_mbps/MAX_THR, txBytes/MAX_BTX, plr/MAX_PLR,
                   resourceSharePct/MAX_RSH, lostPackets/MAX_TDP]
        """
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
                    "thr_sum": 0.0,
                    "btx": 0,
                    "plr_sum": 0.0,
                    "rsh_sum": 0.0,
                    "tdp": 0,
                    "count": 0,
                }
            if slice_id not in slice_ue:
                slice_ue[slice_id] = []

            thr = float(row.get("throughputMbps", 0.0))
            btx = float(row.get("txBytes", 0.0))
            plr = float(row.get("plr", 0.0))
            rsh = float(row.get("resourceSharePct", 0.0))
            tdp = float(row.get("lostPackets", 0.0))

            sd = slice_agg[slice_id]
            sd["thr_sum"] += thr
            sd["btx"] += btx
            sd["plr_sum"] += plr
            sd["rsh_sum"] += rsh
            sd["tdp"] += tdp
            sd["count"] += 1

            slice_ue[slice_id].append({
                "throughputMbps": thr,
                "plr": plr,
                "lostPackets": tdp,
            })

        self.slice_ue_data = slice_ue

        for slice_idx in range(self.num_slices):
            slice_id = slice_idx + 1
            if slice_id in slice_agg and slice_agg[slice_id]["count"] > 0:
                sd = slice_agg[slice_id]
                n = sd["count"]
                self.observations[slice_idx] = [
                    min(sd["thr_sum"] / n / MAX_THR, 1.0),
                    min(sd["btx"] / MAX_BTX, 1.0),
                    sd["plr_sum"] / n / MAX_PLR,
                    sd["rsh_sum"] / n / MAX_RSH,
                    min(sd["tdp"] / MAX_TDP, 1.0),
                ]
            else:
                self.observations[slice_idx] = [0.0, 0.0, 0.0, 0.0, 0.0]
