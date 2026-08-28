# Flight Option Finder — Agentic AI Travel Assistant

## Problem
Searching for flights often involves juggling multiple tabs, manually applying constraints, and attempting to find the perfect balance between price, schedule, and layovers. A standard search engine requires the user to constantly tweak filters. This project solves that by introducing an **AI Agent** that understands constraints (e.g., budget limits) and soft preferences (e.g., time of day, non-stop), autonomously executes search and comparison tools, and presents a reasoned recommendation.

## Why this is an agent
This is not a traditional chatbot. It implements a true agentic loop:
1. **Tool usage**: It has discrete tools (`search_flights`, `compare_price`) that it invokes based on a plan.
2. **Multi-step decision making**: It doesn't just call one tool. It searches for flights, *observes* the results, applies budget constraints to filter them, and *then* decides to call the price comparison tool on the remaining valid options before applying soft preferences.
3. **Memory**: It maintains state across conversational turns. If you tell it your budget in Turn 1, it will automatically apply that constraint when you ask for a route in Turn 2.

## Tools
1. `search_flights(origin, destination, date)`: Connects to our flight data provider (mocked locally) to retrieve raw flight schedules for a specific route.
2. `compare_price(options)`: A computational tool that takes the list of valid options, sorts them, isolates the cheapest and second-best alternatives, and calculates the exact price difference for the agent to consider.

## Memory
The agent uses a session-based memory module (`AgentMemory`). It remembers:
- Budget constraints
- Preferred time of day
- Non-stop preferences
- Last searched route

This affects future decisions by automatically injecting these constraints into the `evaluate_results` and `apply_preferences` steps of the agent loop, without requiring the user to restate them.

## Architecture

```text
Frontend (React/Vite)
   │
   ▼ HTTP
Backend (FastAPI)
   │
   ▼
Agent State Machine
   ├── Memory (Session state)
   ├── Planning (Intent parsing)
   └── Tool execution
          ├── search_flights
          └── compare_price
   │
   ▼
Recommendation Engine
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup

1. **Clone/Navigate to the directory**:
   ```bash
   cd flight-option-finder
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

## Environment variables
There is an `.env.example` file. Since this project is configured to run deterministically using local mocked data, no API keys are required to run the core agent demo.

```env
# .env.example
PORT=8000
ENVIRONMENT=development
# LLM_API_KEY= # Not required for deterministic local run
```

## Running backend
From the `backend` directory:
```bash
uvicorn app.main:app --reload --port 8000
```

## Running frontend
From the `frontend` directory:
```bash
npm run dev
```

## Running notebook
From the root directory:
```bash
jupyter notebook notebooks/agent_demo.ipynb
```
*(Requires Jupyter to be installed in your environment)*

## Testing
From the `backend` directory:
```bash
pytest
```

## Demo scenarios

1. **Normal Search**: "Find a flight from Delhi to Mumbai under 8000."
   - Agent extracts route and budget, calls search, evaluates, calls compare, and recommends the best option.
2. **Memory Context**: 
   - Turn 1: "My budget is 7000 and I want a morning flight." (Agent saves this).
   - Turn 2: "Find me a flight from DEL to BOM." (Agent automatically applies the 7000 budget and morning preference).
3. **Failure/No Valid Option**: "Find a flight from Delhi to Mumbai under 5000."
   - Agent searches, applies the 5000 budget constraint, observes 0 remaining flights, and gracefully fails without calling `compare_price`.

## Honest failure
**Failure:** During the initial development of the `compare_price` tool and the evaluation loop, the agent failed to properly filter flights by budget because the JSON data stored prices as strings (e.g., `"7450"`), causing string-based sorting which produced incorrect "cheapest" flights (e.g., `"10000"` was considered cheaper than `"8000"`).

**Fix:** I introduced explicit Pydantic schemas (`Flight` schema) to strictly type the data. The backend now parses the JSON and casts `price` to a `float`. The evaluation logic (`f["price"] <= self.memory.budget`) was also updated to ensure strict numerical comparison before sorting.

## Viva preparation
- **Where is the agent loop?**: `backend/app/agent/graph.py` inside the `run()` function. It explicitly transitions through states.
- **Where are tools implemented?**: `backend/app/tools/`
- **Where is memory implemented?**: `AgentMemory` in `backend/app/agent/state.py`.
- **How do tool results influence decisions?**: In `_evaluate_results`, if `valid_flights` becomes empty after applying constraints to the results of `search_flights`, the agent skips `_execute_compare` entirely and transitions directly to `_select_option` to report failure.
