# Flight Option Finder — Agentic AI Travel Assistant

## What It Does

The Flight Option Finder is an AI **agent** (not a chatbot) that finds and picks flights within a user's budget. It implements a genuine **PLAN → ACT → OBSERVE → DECIDE** loop: given a natural-language goal like *"Find a non-stop flight from Delhi to Mumbai under ₹6,000"*, the agent retrieves stored memory, parses the request, creates an execution plan, calls `search_flights(from, to)` to discover available flights, observes the results and applies budget filtering, calls `compare_price(options, budget)` to rank and compare candidates, then runs a decision engine that scores each flight by price, non-stop status, and time preference. It always provides a **primary recommendation** and a **second-best fallback**. The entire multi-step trace is recorded so every decision is transparent and explainable.

## Tools and Memory

The agent uses two working tools: **`search_flights(from_city, to_city)`** searches a local flight dataset and returns structured flight dictionaries with airline, price, stops, and schedule. **`compare_price(options, budget)`** sorts flights by price, identifies the cheapest and second-best options, separates under-budget from over-budget flights, and isolates non-stop flights within budget. Both tools are real Python functions that execute and return data used by the agent — there are no fake tool calls.

**Memory** (`ConversationMemory`) persists across multiple turns within the same session. It stores the user's budget, origin, destination, non-stop preference, and time-of-day preference. In Turn 1, the user might say *"My budget is ₹6,000 and I prefer non-stop from Delhi to Mumbai"*. In Turn 2, when the user says *"Find another flight"*, the agent reads memory, retrieves the stored constraints, and uses them without requiring the user to repeat anything. Memory is written after every turn and read at the start of every turn.

## Honest Failure

During development, `compare_price` crashed with a `TypeError` when `search_flights` returned an empty list for an unknown route and the agent passed the empty list to comparison without checking. The fix was two-fold: (1) `compare_price` now validates its input and returns a structured "no options available" response instead of crashing, and (2) the agent's `observe_search` step detects an empty result set and skips comparison entirely, transitioning directly to the decision step which reports honestly that no flights exist for the route. This is demonstrated in Scenario 3 of the notebook, where a ₹2,000 budget produces no valid options and the agent reports the gap to the closest available flight.

---

## Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (57 tests)
python -m pytest tests/ -v

# Run notebook
jupyter notebook notebooks/flight_option_finder_demo.ipynb
```

## Project Structure

```
CSE476/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── flights.json            # 23 flights across 7 routes
├── src/
│   ├── agent/
│   │   ├── flight_agent.py     # Core agent with plan-act loop
│   │   ├── state.py            # AgentState + structured trace
│   │   ├── memory.py           # ConversationMemory (persists across turns)
│   │   └── planner.py          # NLP intent parser
│   ├── tools/
│   │   ├── search_flights.py   # Tool 1: search_flights(from, to)
│   │   └── compare_price.py    # Tool 2: compare_price(options, budget)
│   ├── models/
│   │   └── flight.py           # Flight dataclass
│   └── config.py
├── tests/
│   ├── test_search_flights.py
│   ├── test_compare_price.py
│   ├── test_memory.py
│   └── test_agent.py
└── notebooks/
    └── flight_option_finder_demo.ipynb  # 3 scenarios
```

## Viva Reference

| Question | Where to find it |
|---|---|
| Where is the plan-act loop? | `src/agent/flight_agent.py` → `run()` method (while loop with state transitions) |
| Where does the agent decide the next step? | Each `_step_*` method sets `state.current_step` based on observations |
| Where are tool calls? | `_step_execute_search` → `search_flights()`, `_step_execute_compare` → `compare_price()` |
| Where is memory written? | `_step_memory_update` writes to `self.memory` |
| Where is memory read? | `_step_retrieve_memory` reads from `self.memory` and applies to state |
| How do tool results influence decisions? | `_step_observe_search` filters by budget; `_step_decision` scores by price + preferences |
| How are failures handled? | Empty results → skip compare → report honestly with closest fallback |
