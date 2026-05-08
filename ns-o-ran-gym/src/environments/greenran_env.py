from typing_extensions import override
import numpy as np
import uuid
import time
import subprocess
import selectors
import fcntl
import os
import glob
import warnings
from collections import deque
from posix_ipc import Semaphore, O_CREAT
from nsoran.ns_env import NsOranEnv
from nsoran.action_controller import ActionController
from nsoran.datalake import SQLiteDatabaseAPI
from gymnasium import spaces

from .greenran_slice_ids import (
    get_num_slices,
    normalize_slice_id,
    slice_name,
)
from .greenran_action_spaces import (
    build_discrete_action_table,
    continuous_action_to_prb,
    discrete_action_to_prb,
    DEFAULT_WEIGHTS,
)
from .greenran_kpis import parse_kpm_file, build_observation
from .greenran_reward import compute_greenran_reward


class GreenRanEnv(NsOranEnv):
    """
    GreenRAN DRL Environment for slice-aware-sim.cc (UFPA GreenRAN scenarios).

    Supports two action modes:
        - "continuous" (SAC): action is a 3-dim vector in [-1, 1]
        - "discrete" (DDQN): action is an integer index into the action table

    Supports two observation modes:
        - "paper": 4x4 matrix [btx, bfs, rsh, tdp] x [VIDEO_EMBB, SENSOR_MMTC, GENERIC_EMBB, cell]
        - "debug": legacy 3x5 matrix for backward compatibility

    IPC semaphore names follow the GreenRAN convention:
        /rslaq_metrics_<simId>  and  /rslaq_control_<simId>

    Scenario names (matching C++ InitGreenRanScenarios):
        greenran_low, greenran_normal, greenran_video_heavy,
        greenran_congestion, greenran_night_energy, greenran_balanced
    """

    GREENRAN_SCENARIOS = {
        "greenran_low":        {"videoUes": 5, "sensorUes": 8,  "genericUes": 5},
        "greenran_normal":     {"videoUes": 5, "sensorUes": 8,  "genericUes": 20},
        "greenran_video_heavy":{"videoUes": 5, "sensorUes": 8,  "genericUes": 15},
        "greenran_congestion": {"videoUes": 5, "sensorUes": 8,  "genericUes": 50},
        "greenran_night_energy":{"videoUes": 5, "sensorUes": 8,  "genericUes": 3},
        "greenran_balanced":   {"videoUes": 5, "sensorUes": 8,  "genericUes": 25},
    }

    def __init__(
        self,
        ns3_path: str,
        scenario_configuration: dict,
        output_folder: str,
        optimized: bool = False,
        action_mode: str = "continuous",
        observation_mode: str = "paper",
        max_steps: int | None = None,
        include_scheduler: bool = False,
        sla_config: dict | None = None,
        apply_p_sta: bool = True,
    ):
        # Ensure required keys exist
        scenario_configuration.setdefault("simId", [""])
        scenario_configuration.setdefault("periodMs", [100])
        scenario_configuration.setdefault("scenario", ["greenran_normal"])
        scenario_configuration.setdefault("seed", [1])
        scenario_configuration.setdefault("simTime", [4.0])

        # Compute max_steps automatically if not provided
        sim_time = float(scenario_configuration.get("simTime", [4.0])[0])
        app_start = 0.5  # fixed in C++ slice-aware-sim.cc
        period_ms = int(scenario_configuration.get("periodMs", [100])[0])
        if max_steps is None:
            max_steps = int((sim_time - app_start) * 1000 / period_ms)
            if max_steps <= 0:
                max_steps = 50  # fallback safety
        elif isinstance(max_steps, str):
            max_steps = int(max_steps)
        self.max_steps = max_steps

        self.action_mode = action_mode
        self.observation_mode = observation_mode
        self.include_scheduler = include_scheduler
        self.sla_config = sla_config or {}
        self.apply_p_sta = apply_p_sta
        self.scenario_name = scenario_configuration.get("scenario", ["greenran_normal"])[0]

        # Infer total UEs from scenario defaults
        scenario_params = self.GREENRAN_SCENARIOS.get(self.scenario_name, self.GREENRAN_SCENARIOS["greenran_normal"])
        self.video_ues = int(scenario_configuration.get("videoUes", [scenario_params["videoUes"]])[0])
        self.sensor_ues = int(scenario_configuration.get("sensorUes", [scenario_params["sensorUes"]])[0])
        self.generic_ues = int(scenario_configuration.get("genericUes", [scenario_params["genericUes"]])[0])
        self.num_ues = self.video_ues + self.sensor_ues + self.generic_ues

        # Action table for discrete mode
        if self.action_mode == "discrete":
            self.action_table = build_discrete_action_table(
                step=0.1, include_scheduler=self.include_scheduler
            )
            action_space = spaces.Discrete(len(self.action_table))
        elif self.action_mode == "continuous":
            self.action_table = None
            action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(3,), dtype=np.float32
            )
        else:
            raise ValueError(f"Unknown action_mode: {action_mode}")

        # Observation space
        if self.observation_mode == "paper":
            obs_shape = (4, 4)
        elif self.observation_mode == "debug":
            obs_shape = (3, 5)
        else:
            raise ValueError(f"Unknown observation_mode: {observation_mode}")

        observation_space = spaces.Box(
            low=0.0, high=1.0, shape=obs_shape, dtype=np.float32
        )

        # Control header
        control_header = [
            "timestamp", "sliceId", "dedicatedPRB", "minPRB", "maxPRB"
        ]
        if self.include_scheduler:
            control_header.append("algorithm")

        super().__init__(
            ns3_path=ns3_path,
            scenario="GreenRan-slice",
            scenario_configuration=scenario_configuration,
            output_folder=output_folder,
            optimized=optimized,
            skip_configuration=True,
            control_header=control_header,
            log_file="GreenRanActions.txt",
            control_file="rslaq_actions_for_ns3.csv",
        )

        self.observation_space = observation_space
        self.action_space = action_space

        self.num_slices = get_num_slices()

        self._base_seed = int(scenario_configuration.get("seed", [1])[0])
        self._episode_count = 0
        self._seed_cycle = int(scenario_configuration.get("seed_cycle", [100])[0])
        self._current_seed_index = 0

        self.observations = np.zeros(obs_shape, dtype=np.float32)
        self.kpi_dict: dict = {}
        self.num_steps = 0
        self.latest_action_info: dict = {}
        self.kpi_history: deque[dict] = deque(maxlen=10)

    @override
    def reset(self, *, seed=None, options=None):
        self.num_steps = 0
        self._episode_count += 1
        self._current_seed_index = (self._episode_count - 1) // self._seed_cycle
        current_seed = self._base_seed + self._current_seed_index
        self.scenario_configuration["seed"] = [current_seed]
        self.kpi_history.clear()
        return super().reset(seed=seed, options=options)

    @override
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
            if k in ("seed_cycle", "_current_seed_index"):
                continue
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

        # GreenRAN uses /rslaq_metrics_<simId> and /rslaq_control_<simId>
        nameMetricsReadySemaphore = "/rslaq_metrics_" + sim_uuid
        nameControlSemaphore = "/rslaq_control_" + sim_uuid
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
        Convert agent action into ns-3 control tuples.

        For continuous mode: action is np.ndarray shape (3,).
        For discrete mode: action is int (index into action_table).
        """
        if self.action_mode == "continuous":
            raw = np.asarray(action, dtype=np.float32).flatten()
            if raw.shape[0] != 3:
                raise ValueError(
                    f"Continuous action must have shape (3,), got {raw.shape}"
                )
            prb_pct = continuous_action_to_prb(raw, apply_p_sta=self.apply_p_sta)
            scheduler_id = -1
        elif self.action_mode == "discrete":
            if not isinstance(action, (int, np.integer)):
                raise ValueError(
                    f"Discrete action must be an integer, got {type(action)}"
                )
            action_idx = int(action)
            if self.action_table is None:
                raise RuntimeError(
                    "action_table is None but action_mode is discrete."
                )
            prb_pct, scheduler_id = discrete_action_to_prb(
                action_idx, self.action_table, apply_p_sta=self.apply_p_sta
            )
        else:
            raise ValueError(f"Unknown action_mode: {self.action_mode}")

        actions = []
        for slice_idx in range(self.num_slices):
            dedicated = float(prb_pct[slice_idx])
            entry = (slice_idx, dedicated, dedicated, 100.0)
            if self.include_scheduler:
                sch = int(scheduler_id) if scheduler_id >= 0 else 0
                entry = entry + (sch,)
            actions.append(entry)

        self.latest_action_info = {
            "prb_pct": prb_pct.tolist(),
            "scheduler_id": int(scheduler_id),
            "action_mode": self.action_mode,
        }
        return actions

    @override
    def _get_obs(self):
        return self.observations

    @override
    def _compute_reward(self) -> float:
        """
        Compute SLA-aware reward using the dedicated GreenRAN reward module.
        """
        reward_result = compute_greenran_reward(
            metrics=self.kpi_dict,
            scenario=self.scenario_name,
            action_info=self.latest_action_info,
            config=self.sla_config,
            step_count=self.num_steps,
            kpi_history=list(self.kpi_history),
        )
        self._last_reward_result = reward_result
        if reward_result.terminated:
            self.terminated = True
        return float(reward_result.reward)

    @override
    def _init_datalake_usecase(self):
        pass

    @override
    def _fill_datalake_usecase(self):
        """
        Read rslaq-kpms.txt, parse per-slice metrics, and build observation.
        """
        kpm_files = glob.glob(os.path.join(self.sim_path, "rslaq-kpms.txt"))
        if not kpm_files:
            return

        self.kpi_dict = parse_kpm_file(
            kpm_files[0], last_timestamp=self.last_timestamp
        )
        if "_latest_timestamp" in self.kpi_dict:
            self.last_timestamp = self.kpi_dict.pop("_latest_timestamp")

        use_proxy_bfs = self.sla_config.get("use_proxy_bfs", False)
        max_buffer_bytes = self.sla_config.get("max_buffer_bytes", 100000.0)

        self.observations = build_observation(
            self.kpi_dict,
            mode=self.observation_mode,
            use_proxy_bfs=use_proxy_bfs,
            max_buffer_bytes=max_buffer_bytes,
        )

    @override
    def step(self, action) -> tuple:
        if not self.is_simulation_over():
            actions = self._compute_action(action)
            self.action_controller.create_control_action(self.last_timestamp, actions)
            self.controlSemaphore.release()
            self._wait_data_availability()
            self._fill_datalake()

        if self.kpi_dict:
            self.kpi_history.append(self.kpi_dict.copy())

        self.num_steps += 1
        if self.num_steps >= self.max_steps:
            self.truncated = True

        obs = self._get_obs()
        reward_val = self._compute_reward()

        info = self._build_info(action)
        return obs, reward_val, self.terminated, self.truncated, info

    def _build_info(self, raw_action) -> dict:
        """Build the info dict returned by step()."""
        info = {
            "is_open": self.is_open,
            "results": self.sim_result,
            "num_steps": self.num_steps,
            "max_steps": self.max_steps,
            "scenario": self.scenario_name,
            "action_info": self.latest_action_info.copy(),
            "raw_action": raw_action,
        }

        for sid in range(self.num_slices):
            metrics = self.kpi_dict.get(sid, {})
            info[f"slice_{sid}_{slice_name(sid)}"] = {
                "throughput_mbps": metrics.get("throughputMbps_sum", 0.0),
                "plr_mean": metrics.get("plr_mean", 0.0),
                "dLostPackets_sum": metrics.get("dLostPackets_sum", 0.0),
                "resourceSharePct_mean": metrics.get("resourceSharePct_mean", 0.0),
                "dTxBytes_sum": metrics.get("dTxBytes_sum", 0.0),
                "bufferBytes_max": metrics.get("bufferBytes_max", 0.0),
            }

        if hasattr(self, "_last_reward_result"):
            info["reward_debug"] = self._last_reward_result.debug_info
            info["outage_flags"] = self._last_reward_result.outage_flags
            info["soft_flags"] = self._last_reward_result.soft_flags

        return info
