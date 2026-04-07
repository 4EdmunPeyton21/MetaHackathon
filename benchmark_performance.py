"""
benchmark_performance.py
-------------------------
Performance and Accuracy Audit Tool for PII Redactor.

This script measures:
1. Latency (ms): Time taken for Reset and Step operations.
2. Accuracy: Final reward score achieved by a baseline scripted agent.

Usage:
    python benchmark_performance.py
"""

import asyncio
import time
import json
import statistics
import os
from typing import List, Dict

try:
    import websockets
except ImportError:
    print("Error: websockets package required. Run: pip install websockets")
    exit(1)

# --- Configuration ---
TASKS = ["easy", "medium", "hard"]
TRIALS_PER_TASK = 3
WS_URL = os.getenv("ENV_WS_URL", "ws://localhost:7860/ws")

# Sample Redaction Scripts for testing accuracy
SCRIPTS = {
    "easy": r'''
import re
path="customers.csv"
with open(path, "r") as f: c=f.read()
c=re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED]", c)
with open(path, "w") as f: f.write(c)
''',
    
    "medium": r'''
import re
path="chat_logs.txt"
with open(path, "r") as f: c=f.read()
c=re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED]", c)
with open(path, "w") as f: f.write(c)
''',
    
    "hard": r'''
import json, re
path="records.json"
with open(path, "r") as f: data=json.load(f)
def r(obj):
  if isinstance(obj, dict): return {k: r(v) for k, v in obj.items()}
  if isinstance(obj, list): return [r(i) for i in obj]
  if isinstance(obj, str):
    obj = re.sub(r"\b\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\b", "[REDACTED]", obj)
    obj = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED]", obj)
    obj = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED]", obj)
    obj = re.sub(r"\(\d{3}\) \d{3}-\d{4}", "[REDACTED]", obj)
  return obj
data["customers"] = r(data["customers"])
with open(path, "w") as f: json.dump(data, f, indent=2)
'''
}

async def run_benchmark():
    print("\n" + "="*60)
    print("  PII REDACTOR PERFORMANCE AUDIT")
    print("="*60)
    print(f"Server: {WS_URL}")
    print(f"Trials: {TRIALS_PER_TASK} per task")
    print("-" * 60)

    results = []

    for task in TASKS:
        print(f"Benchmarking Task: {task.upper()}...")
        task_latencies_reset = []
        task_latencies_step = []
        task_scores = []

        for i in range(TRIALS_PER_TASK):
            try:
                async with websockets.connect(WS_URL) as ws:
                    # 1. Measure Reset Latency
                    reset_msg = json.dumps({"type": "reset", "data": {"task_id": task}})
                    start_reset = time.perf_counter()
                    await ws.send(reset_msg)
                    raw_reset = await ws.recv()
                    task_latencies_reset.append((time.perf_counter() - start_reset) * 1000)

                    # 2. Measure Step Latency & Accuracy
                    script = SCRIPTS[task]
                    step_msg = json.dumps({
                        "type": "step", 
                        "data": {"action_type": "python", "command": script}
                    })
                    
                    start_step = time.perf_counter()
                    await ws.send(step_msg)
                    raw_step = await ws.recv()
                    task_latencies_step.append((time.perf_counter() - start_step) * 1000)
                    
                    step_data = json.loads(raw_step)
                    reward = step_data.get("data", {}).get("reward", 0.0)
                    task_scores.append(reward if reward is not None else 0.0)
                    
                    if reward == 0.0 or reward is None:
                        print(f"  [DEBUG] {task} step failed. Response: {json.dumps(step_data, indent=2)}")

                    # Close session
                    await ws.send(json.dumps({"type": "close", "data": {}}))
            except Exception as e:
                print(f"  [ERROR] Trial {i+1} failed: {e}")

        if task_latencies_reset:
            results.append({
                "task": task,
                "reset_avg": statistics.mean(task_latencies_reset),
                "step_avg": statistics.mean(task_latencies_step),
                "accuracy": statistics.mean(task_scores)
            })

    # --- Print Results Table ---
    if not results:
        print("\n[ERROR] No successful trials recorded. Is the server running?")
        return

    print("\nFINAL PERFORMANCE REPORT")
    print("-" * 75)
    print(f"{'TASK':<10} | {'RESET (ms)':<15} | {'STEP (ms)':<15} | {'ACCURACY':<10}")
    print("-" * 75)
    for r in results:
        print(f"{r['task'].upper():<10} | {r['reset_avg']:>13.2f} | {r['step_avg']:>13.2f} | {r['accuracy']:>9.3f}")
    print("-" * 75)
    
    overall_latency = statistics.mean([r['step_avg'] for r in results])
    overall_acc = statistics.mean([r['accuracy'] for r in results])
    
    print(f"OVERALL AVG STEP LATENCY: {overall_latency:.2f} ms")
    print(f"OVERALL AVG ACCURACY:     {overall_acc*100:.1f}%")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_benchmark())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[ERROR] Main loop failed: {e}")
