"""
Interactive Command-Line Interface (CLI) for Flight Option Finder Agent.

Usage:
    python cli.py                           # Starts interactive multi-turn chat
    python cli.py "Find flights from Delhi to Mumbai under 6000"
"""

import sys
import os
import argparse
from tabulate import tabulate

# Ensure UTF-8 output even in standard Windows CMD (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent.flight_agent import FlightAgent


def print_trace_table(state):
    """Render agent execution trace as a formatted ASCII table."""
    rows = []
    for t in state.trace:
        tool = t.tool or "—"
        inp = str(t.input)[:32] if t.input else "—"
        res = str(t.result)[:42] if t.result else "—"
        dec = str(t.decision)[:32] if t.decision else "—"
        rows.append([t.step, t.action, tool, inp, res, dec])
    
    print("\n" + "=" * 80)
    print("📊 AGENT EXECUTION TRACE (Plan-Act-Observe-Decide Loop)")
    print("=" * 80)
    print(tabulate(rows, headers=["Step", "Action", "Tool", "Input", "Result", "Decision"], tablefmt="grid"))


def run_single_query(agent, query, show_trace=True):
    """Execute one query through the agent and print formatted output."""
    print("\n" + "─" * 80)
    print(f"👤 USER: \"{query}\"")
    print("─" * 80)
    
    state = agent.run(query)
    
    if show_trace:
        print_trace_table(state)
        
    print("\n" + "─" * 80)
    print("🤖 AGENT RESPONSE:")
    print("─" * 80)
    print(agent.get_response_text(state))
    print(f"\n📝 CURRENT MEMORY: {agent.memory.summary_str()} (Turn {agent.memory.turn_count})")
    print("─" * 80)
    return state


def interactive_mode():
    """Run an interactive conversation loop in the terminal."""
    agent = FlightAgent()
    print("=" * 80)
    print("✈️  FLIGHT OPTION FINDER — INTERACTIVE AGENT CLI")
    print("=" * 80)
    print("Type your flight request naturally (e.g. 'Find a flight from Delhi to Mumbai under 6000').")
    print("The agent maintains session memory across turns.")
    print("Type 'memory' to inspect memory, 'clear' to reset, or 'exit'/'quit' to leave.\n")
    
    while True:
        try:
            user_input = input("\n👉 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye! Have a safe flight! ✈️")
                break
            if user_input.lower() == "clear":
                agent.reset_memory()
                print("🧹 Session memory cleared.")
                continue
            if user_input.lower() == "memory":
                print(f"📝 Current Memory: {agent.memory.summary_str()}")
                continue
                
            run_single_query(agent, user_input, show_trace=True)
            
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flight Option Finder Agent CLI")
    parser.add_argument("query", nargs="?", help="Optional natural-language flight query to run directly")
    parser.add_argument("--no-trace", action="store_true", help="Hide intermediate execution trace table")
    
    args = parser.parse_args()
    
    if args.query:
        agent = FlightAgent()
        run_single_query(agent, args.query, show_trace=not args.no_trace)
    else:
        interactive_mode()
