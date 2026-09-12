# Autonomous Attack-Chain Hunter & Recovery Agent

An offline-first SOC investigation and response simulator for the Tech Zephyr 4.0 Agentic AI Hackathon, Track 5 / Problem 9.

## What makes it agentic

The application is not a chatbot or a one-shot classifier. The local controller maintains incident state and performs:

`Goal -> Missing evidence -> Tool choice -> Evidence -> Analysis -> Action -> Result -> Adapt -> Replan -> Verify`

The default incident intentionally makes `BLOCK_IP` fail partially because an active privileged session survives the IP block. The Recovery Agent requests session evidence, replans to `REVOKE_SESSION + BLOCK_IP`, executes it in the sandbox, and independently verifies the environment.

## Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app\main.py
```

Open `http://localhost:8501`. After installation, disconnect Wi-Fi: all scenario data, state, reports, and response actions are local synthetic data. No API key, cloud account, external database, or external URL is needed.

Run the tests with:

```powershell
python -m pytest
```

## Run on macOS/Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app/main.py
```

## Project map

- `app/`: Streamlit dashboard, styling, visual components, exports.
- `agents/`: investigation, analysis, response, recovery, and verification logic.
- `engine/`: persistent state, event bus, orchestrator, and planning utilities.
- `tools/`: local evidence tools and sandbox simulators.
- `data/scenarios/`: six synthetic incidents, including two different failure modes.
- `database/`: local SQLite snapshots, created at runtime.
- `reports/`: local JSON/HTML incident reports, created by the dashboard.
- `tests/`: deterministic workflow and safety tests.

## Safety boundary

Every alert, log, asset, vulnerability, network state, response, and failure is synthetic. Firewall, session, account, and host actions modify only an in-memory sandbox state and a local incident snapshot. No real exploitation, credential collection, persistence, malware, network access, or production changes are implemented.

## Optional local LLM

The deterministic engine is the default and remains the source of truth. If a user already runs Ollama locally, a future adapter may enrich summaries; nothing in the core workflow calls it and the default application never requires it.
