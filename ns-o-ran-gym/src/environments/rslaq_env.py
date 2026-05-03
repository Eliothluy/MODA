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

from .rslaq_slice_ids import (
    get_num_slices,
    normalize_slice_id,
    slice_name,
)
from .rslaq_action_spaces import (
    build_discrete_action_table,
    continuous_action_to_prb,
    discrete_action_to_prb,
    DEFAULT_WEIGHTS,
)
from .rslaq_kpis import parse_kpm_file, build_observation
from .rslaq_reward import compute_rslaq_reward


class RslaqEnv(NsOranEnv):
    """
    RSLAQ DRL Environment for O-RAN QoS xApp.

    Supports two action modes:
        - "continuous" (SAC): action is a 3-dim vector in [-1, 1]
        - "discrete" (DDQN): action is an integer index into the action table

    Supports two observation modes:
        - "paper": 4x4 matrix [btx, bfs, rsh, tdp] x [eMBB, URLLC, MTC, cell]
        - "debug": legacy 3x5 matrix for backward compatibility

    Important: bfs and tdp are currently proxies using plr and lostPackets.
    See rslaq_kpis.py for TODOs on replacing them with real metrics.

    P_STA decomposition: By default (apply_p_sta=True), the environment applies
    P_STA decomposition in Python before sending actions to ns-3. Set apply_p_sta=False
    when ns-3 handles P_STA decomposition (to avoid double application).
    """

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
        scenario_configuration.setdefault("periodMs", [10])
        scenario_configuration.setdefault("scenario", ["normal"])
        scenario_configuration.setdefault("seed", [1])
        scenario_configuration.setdefault("appStart", [0.5])
        scenario_configuration.setdefault("simTime", [4.0])

        # Compute max_steps automatically if not provided
        sim_time = float(scenario_configuration.get("simTime", [4.0])[0])
        app_start = float(scenario_configuration.get("appStart", [0.5])[0])
        period_ms = int(scenario_configuration.get("periodMs", [10])[0])
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
        self.scenario_name = scenario_configuration.get("scenario", ["normal"])[0]

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

        # Control header depends on scheduler inclusion
        control_header = [
            "timestamp", "sliceId", "dedicatedPRB", "minPRB", "maxPRB"
        ]
        if self.include_scheduler:
            control_header.append("algorithm")

        super().__init__(
            ns3_path=ns3_path,
            scenario="rslaq-sim",
            scenario_configuration=scenario_configuration,
            output_folder=output_folder,
            optimized=optimized,
            skip_configuration=True,
            control_header=control_header,
            log_file="RslaqActions.txt",
            control_file="rslaq_actions_for_ns3.csv",
        )

        # Override spaces set by base class (if any) with our own
        self.observation_space = observation_space
        self.action_space = action_space

        self.num_slices = get_num_slices()
        self.num_ues = scenario_configuration.get("ues", [20])[0]

        self._base_seed = int(scenario_configuration.get("seed", [1])[0])
        self._episode_count = 0
        self._seed_cycle = int(scenario_configuration.get("seed_cycle", [100])[0])
        self._current_seed_index = 0

        self.observations = np.zeros(obs_shape, dtype=np.float32)
        self.kpi_dict: dict = {}
        self.num_steps = 0
        self.latest_action_info: dict = {}

        # History of per-step KPI dicts for consecutive-period outage detection
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
                    "action_table is None but action_mode is discrete. "
                    "This should not happen."
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
                # scheduler_id may be -1 if action table doesn't include it
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
        Compute SLA-aware reward using the dedicated reward module.
        """
        reward_result = compute_rslaq_reward(
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
        # Update last_timestamp from parser
        if "_latest_timestamp" in self.kpi_dict:
            self.last_timestamp = self.kpi_dict.pop("_latest_timestamp")

        # Get observation config from sla_config
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
        # Base class handles simulation lifecycle (wait, fill datalake, etc.)
        # We call the base logic manually to inject max_steps and info
        if not self.is_simulation_over():
            actions = self._compute_action(action)
            self.action_controller.create_control_action(self.last_timestamp, actions)
            self.controlSemaphore.release()
            self._wait_data_availability()
            self._fill_datalake()

        # Store current KPI dict in history for consecutive-period detection
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

        # Add per-slice KPIs if available
        for sid in range(self.num_slices):
            metrics = self.kpi_dict.get(sid, {})
            info[f"slice_{sid}_{slice_name(sid)}"] = {
                "throughput_mbps": metrics.get("throughputMbps_sum", 0.0),
                "plr_mean": metrics.get("plr_mean", 0.0),
                "dLostPackets_sum": metrics.get("dLostPackets_sum", 0.0),
                "resourceSharePct_mean": metrics.get("resourceSharePct_mean", 0.0),
                "dTxBytes_sum": metrics.get("dTxBytes_sum", 0.0),
            }

        # Reward debug info if available
        if hasattr(self, "_last_reward_result"):
            info["reward_debug"] = self._last_reward_result.debug_info
            info["outage_flags"] = self._last_reward_result.outage_flags
            info["soft_flags"] = self._last_reward_result.soft_flags

        return info


