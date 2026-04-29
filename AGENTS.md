# AGENTS.md

Guidelines for agentic coding assistants working in the RSLAQ repository.

## Project Layout

- `ns-3-dev/` — C++ network simulator (ns-3 + 5G-LENA)
  - `scratch/rslaq/` — RSLAQ scheduler and simulation script
  - `contrib/nr/` — 5G-LENA module
- `ns-o-ran-gym/` — Python Gymnasium environment and DRL training
  - `src/nsoran/` — Base environment, datalake, action controller
  - `src/environments/` — RSLAQ-specific environment (`rslaq_env.py`)
  - `examples/` — Training scripts (DDQN, SAC, OPT)
  - `tests/` — pytest test suite

## Build / Lint / Test Commands

### ns-3-dev (C++)

```bash
cd ns-3-dev

# Configure (first time or after CMake changes)
./ns3 configure --enable-examples --enable-tests

# Build everything
./ns3 build

# Build only the RSLAQ simulation target (fastest for iteration)
./ns3 build rslaq-sim

# Run the ns-3 test runner (all tests)
./test.py

# Run a single ns-3 test suite by name
./test.py -s <test-suite-name>
```

### ns-o-ran-gym (Python)

```bash
cd ns-o-ran-gym

# Install in editable mode (preferred for development)
pip install -e .

# Run the full pytest suite
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_rslaq_reward.py

# Run a single test function
python -m pytest tests/test_rslaq_reward.py::test_reward_normal_all_good

# Build distribution (not usually needed in dev)
hatch build
```

## Code Style

### Python

- **Formatter**: Follow `black` conventions (line length 100) and `isort` profile black.
- **Imports**: group stdlib, third-party, then local modules separated by blank lines.
- **Typing**: Use type hints everywhere (`int | None`, `dict[str, Any]`, `-> list[tuple]`).
- **Naming**:
  - `snake_case` for functions, variables, modules
  - `CamelCase` for classes
  - `UPPER_SNAKE_CASE` for module-level constants
- **Error handling**: Raise explicit exceptions (`ValueError`, `RuntimeError`) with descriptive messages; avoid bare `except`.
- **Comments**: Docstrings for public classes and methods; inline comments only when logic is non-obvious.
- **Tests**: Use plain `assert` in pytest-style tests. Keep tests deterministic (no unseeded randomness).

### C++ (ns-3)

- **Style**: GNU ns-3 style (`/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */`).
- **Naming**:
  - `PascalCase` for classes
  - `CamelCase` for methods and free functions
  - `m_camelCase` for member variables
  - `UPPER_SNAKE_CASE` for constants / enums
- **Headers**: Use `#pragma once`. Document public API with Doxygen `/** @brief ... */` blocks.
- **Logging**: Use `NS_LOG_COMPONENT_DEFINE("MyComponent")` and `NS_LOG_*` macros; avoid raw `std::cout` in scheduler hot paths.
- **Memory**: Prefer `Ptr<>` and `std::shared_ptr` / `std::vector` over raw pointers.

## Important Conventions

1. **IPC Protocol**: The C++ simulator and Python agent communicate via POSIX semaphores and CSV files every 10 ms. Do not change filenames (`rslaq_actions_for_ns3.csv`, `rslaq-kpms.txt`) or semaphore naming patterns without updating both sides.
2. **RNTI Mapping**: UE RNTIs are assigned dynamically by 5G-LENA. Always query the scheduler mapping rather than hard-coding RNTI ranges.
3. **Weight Renormalization**: Effective slice weights `p_j` are computed only for slices with active demand (buffer > 0). The last active slice receives the remainder.
4. **P_STA Decomposition**: Final resource allocation is `p_final = P_STA + p_opt * 0.5`. Ensure this decomposition is applied exactly once (either in Python or C++, not both).
5. **Uplink is NOT slice-aware**: Only downlink scheduling implements slice-aware RBG allocation.

## Testing Checklist

Before finishing a change:

- [ ] `python -m pytest tests/` passes for Python changes.
- [ ] `./ns3 build rslaq-sim` compiles cleanly for C++ changes.
- [ ] If adding a new test, run the specific test function first (`pytest tests/...::...`).

No Cursor rules or Copilot instructions are present in this repository.
