"""
pii_redactor_env/server/app.py
-------------------------------
FastAPI application entry-point.

Creates the HTTP/WebSocket server using ``openenv.core.env_server.create_fastapi_app``.
Also registers the ``POST /reset`` liveness endpoint required by Hugging Face
Spaces validation and serves a professional dashboard for evaluators.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from openenv.core.env_server import create_fastapi_app

from pii_redactor_env.models import PIIAction, PIIObservation
from pii_redactor_env.server.pii_environment import PIIRedactorEnvironment


# ---------------------------------------------------------------------------
# Create the OpenEnv FastAPI app (registers /step, /reset, /state, /health)
# ---------------------------------------------------------------------------
app: FastAPI = create_fastapi_app(PIIRedactorEnvironment, PIIAction, PIIObservation)


# ---------------------------------------------------------------------------
# Evaluator Dashboard (Root Route)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """
    Serves a professional landing page for evaluators to demo the environment.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PII Redactor Environment | OpenEnv Benchmark</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #f9f9f9; }
            .card { background: white; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px; }
            h1 { color: #1a365d; margin-top: 0; }
            h2 { color: #2c5282; border-bottom: 2px solid #edf2f7; padding-bottom: 10px; }
            .btn { background: #3182ce; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: 600; transition: background 0.2s; }
            .btn:hover { background: #2b6cb0; }
            .btn:disabled { background: #a0aec0; cursor: not-allowed; }
            pre { background: #1a202c; color: #e2e8f0; padding: 20px; border-radius: 6px; overflow-x: auto; font-size: 14px; min-height: 50px; }
            .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .status-item { background: #ebf8ff; padding: 15px; border-radius: 6px; border-left: 4px solid #4299e1; }
            .status-label { display: block; font-size: 12px; text-transform: uppercase; color: #4a5568; font-weight: bold; }
            .status-value { font-size: 18px; font-weight: bold; color: #2b6cb0; }
            .link { color: #3182ce; text-decoration: none; }
            .link:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>PII Redactor Environment</h1>
            <p><strong>Automated Data Privacy Compliance Benchmark for AI Agents</strong></p>
            <p>This environment challenges AI agents to act as Data Engineers tasked with cleaning sensitive customer datasets. It evaluates the ability to identify and redact PII (Credit Cards, SSNs, Emails) while maintaining 100% data integrity.</p>
            
            <div class="status-grid">
                <div class="status-item"><span class="status-label">Environment</span><span class="status-value">OpenEnv 0.2.0</span></div>
                <div class="status-item"><span class="status-label">SDK</span><span class="status-value">FastAPI / Docker</span></div>
                <div class="status-item"><span class="status-label">GitHub</span><span class="status-value"><a href="https://github.com/4EdmunPeyton21/MetaHackathon" class="link">Source Code</a></span></div>
            </div>
        </div>

        <div class="card">
            <h2>Interactive Demo</h2>
            <p>Click the button below to simulate an AI agent performing a redaction task on a CSV file.</p>
            <button id="demoBtn" class="btn" onclick="runDemo()">Run Automatic Demo</button>
            
            <div id="demoOutput" style="display: none; margin-top: 30px;">
                <div class="status-grid">
                    <div class="status-item"><span class="status-label">Current Task</span><span id="taskVal" class="status-value">Easy (CSV)</span></div>
                    <div class="status-item"><span class="status-label">Reward / Score</span><span id="rewardVal" class="status-value">0.00</span></div>
                    <div class="status-item"><span class="status-label">Done Status</span><span id="doneVal" class="status-value">False</span></div>
                </div>
                
                <h3>Last Action Taken</h3>
                <pre id="actionDisplay">Waiting for input...</pre>
                
                <h3>Environment Observation</h3>
                <pre id="obsDisplay">Waiting for input...</pre>
            </div>
        </div>

        <div class="card">
            <h2>Environment Architecture</h2>
            <p>The system is built on a modular architecture to ensure deterministic grading and sandboxed execution:</p>
            <ul>
                <li><strong>State Management</strong>: Ephemeral workspaces created for every episode.</li>
                <li><strong>Action Validation</strong>: Supports both Bash and Python script execution.</li>
                <li><strong>Grading Engine</strong>: Multi-weighted scoring (Redaction success + Data integrity).</li>
            </ul>
            <p>Evaluators should inspect the <code>pii_redactor_env/tasks/</code> directory for the full grading implementation logic.</p>
        </div>

        <script>
            async function runDemo() {
                const btn = document.getElementById('demoBtn');
                const output = document.getElementById('demoOutput');
                const actionDisp = document.getElementById('actionDisplay');
                const obsDisp = document.getElementById('obsDisplay');
                const rewardVal = document.getElementById('rewardVal');
                const doneVal = document.getElementById('doneVal');

                btn.disabled = true;
                btn.innerText = "Running Demo...";
                output.style.display = "block";

                try {
                    // 1. Reset
                    actionDisp.innerText = "ACTION: POST /reset { task_id: 'easy' }";
                    const resetRes = await fetch('/reset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ task_id: 'easy' })
                    });
                    const resetData = await resetRes.json();
                    obsDisp.innerText = JSON.stringify(resetData, null, 2);
                    
                    await new Promise(r => setTimeout(r, 1500));

                    // 2. Step
                    const demoAction = {
                        action_type: 'python',
                        command: 'import re\\npath="customers.csv"\\nwith open(path, "r") as f: c=f.read()\\nc=re.sub(r"\\\\b\\\\d{4}[- ]?\\\\d{4}[- ]?\\\\d{4}[- ]?\\\\d{4}\\\\b", "[REDACTED]", c)\\nwith open(path, "w") as f: f.write(c)\\nprint("Redacted successfully")'
                    };
                    actionDisp.innerText = "ACTION: POST /step " + JSON.stringify(demoAction, null, 2);
                    
                    const stepRes = await fetch('/step', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(demoAction)
                    });
                    const stepData = await stepRes.json();
                    obsDisp.innerText = JSON.stringify(stepData, null, 2);

                    // Robust parsing of reward and done status
                    // Reward can be top-level or nested inside observation
                    let reward = 0.0;
                    if (stepData.reward !== undefined && stepData.reward !== null) {
                        reward = stepData.reward;
                    } else if (stepData.observation && stepData.observation.reward !== undefined) {
                        reward = stepData.observation.reward;
                    }
                    
                    let done = false;
                    if (stepData.done !== undefined) {
                        done = stepData.done;
                    } else if (stepData.observation && stepData.observation.done !== undefined) {
                        done = stepData.observation.done;
                    }

                    rewardVal.innerText = (typeof reward === 'number') ? reward.toFixed(2) : reward;
                    doneVal.innerText = done.toString().toUpperCase();
                    
                    btn.innerText = "Demo Complete";
                } catch (e) {
                    obsDisp.innerText = "Error running demo: " + e.message + "\\nCheck browser console for details.";
                    console.error("Demo Error:", e);
                    btn.disabled = false;
                    btn.innerText = "Retry Demo";
                }
            }
        </script>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# Standard Endpoints
# ---------------------------------------------------------------------------
@app.get("/ping")
async def ping() -> dict:
    """Liveness check endpoint."""
    return {"status": "alive", "environment": "pii_redactor_env"}

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
