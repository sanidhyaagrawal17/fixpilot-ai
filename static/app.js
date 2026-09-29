document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("debug-form");
  const tracebackInput = document.getElementById("error-traceback");
  const sourceCodeInput = document.getElementById("source-code");
  const testCodeInput = document.getElementById("test-code");
  const githubUrlInput = document.getElementById("github-url");
  const clearBtn = document.getElementById("clear-traceback");
  const submitBtn = document.getElementById("btn-submit");
  const scenarioGroup = document.getElementById("scenario-btn-group");

  const backendStatus = document.getElementById("backend-status");
  const agentStatePill = document.getElementById("agent-state-pill");
  const timelineList = document.getElementById("timeline-list");
  const totalTimeLabel = document.getElementById("total-time");

  const docsSection = document.getElementById("docs-section");
  const docsList = document.getElementById("docs-list");

  const fixSection = document.getElementById("fix-section");
  const fixExplanation = document.getElementById("fix-explanation");
  const diffOutput = document.getElementById("diff-output");
  const fullCodeOutput = document.getElementById("full-code-output");
  const sandboxOutput = document.getElementById("sandbox-output");
  const copyBtn = document.getElementById("btn-copy-code");

  let currentFixedCode = "";

  // 1. Health Probe
  async function checkHealth() {
    try {
      const resp = await fetch("/api/health");
      if (resp.ok) {
        const data = await resp.json();
        const nebiusActive = data.providers?.nebius_token_factory;
        const tavilyActive = data.providers?.tavily_search;
        backendStatus.innerHTML = `● Active: ${nebiusActive ? 'Nebius API' : 'Diagnostic Simulation'}${tavilyActive ? ' + Tavily' : ''}`;
        backendStatus.style.color = "#22c55e";
      }
    } catch (e) {
      backendStatus.innerHTML = "● Offline";
      backendStatus.style.color = "#ef4444";
    }
  }
  checkHealth();

  // 2. Fetch and render pre-built scenarios
  async function loadScenarios() {
    try {
      const resp = await fetch("/api/scenarios");
      if (resp.ok) {
        const scenarios = await resp.json();
        scenarioGroup.innerHTML = "";
        scenarios.forEach((sc) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "scenario-btn";
          // Label formatting
          const label = sc.id.replace("scenario_", "").replace("_", " ");
          btn.textContent = label.toUpperCase();
          btn.title = sc.description;
          btn.addEventListener("click", () => {
            tracebackInput.value = sc.error_traceback;
            sourceCodeInput.value = sc.source_code;
            testCodeInput.value = sc.test_code;
            githubUrlInput.value = "";
          });
          scenarioGroup.appendChild(btn);
        });
      }
    } catch (e) {
      console.warn("Failed to load scenarios", e);
    }
  }
  loadScenarios();

  // Clear button
  clearBtn.addEventListener("click", () => {
    tracebackInput.value = "";
    sourceCodeInput.value = "";
    testCodeInput.value = "";
    githubUrlInput.value = "";
    tracebackInput.focus();
  });

  // Tab switching
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.getAttribute("data-tab");

      document.getElementById("tab-diff").style.display = target === "diff" ? "block" : "none";
      document.getElementById("tab-code").style.display = target === "code" ? "block" : "none";
      document.getElementById("tab-test").style.display = target === "test" ? "block" : "none";
    });
  });

  // Copy code button
  copyBtn.addEventListener("click", () => {
    if (currentFixedCode) {
      navigator.clipboard.writeText(currentFixedCode);
      const originalText = copyBtn.textContent;
      copyBtn.textContent = "Copied! ✓";
      setTimeout(() => {
        copyBtn.textContent = originalText;
      }, 2000);
    }
  });

  // Format unified diff with line-by-line colored spans
  function renderColoredDiff(diffText) {
    if (!diffText || !diffText.trim()) {
      return "No unified diff generated (replacement identical or direct).";
    }
    const lines = diffText.split("\n");
    return lines
      .map((line) => {
        const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
          return `<span class="diff-line-header">${escaped}</span>`;
        } else if (line.startsWith("+")) {
          return `<span class="diff-line-add">${escaped}</span>`;
        } else if (line.startsWith("-")) {
          return `<span class="diff-line-del">${escaped}</span>`;
        }
        return escaped;
      })
      .join("\n");
  }

  // 3. Form Submit Handler (with Streaming SSE parsing)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      error_traceback: tracebackInput.value.trim(),
      source_code: sourceCodeInput.value.trim() || null,
      test_code: testCodeInput.value.trim() || null,
      github_url: githubUrlInput.value.trim() || null,
      language: "python"
    };

    if (!payload.error_traceback) return;

    // Reset UI state
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-label").textContent = "Autonomous Debugger Active...";
    agentStatePill.querySelector(".status-indicator").className = "status-indicator active";
    agentStatePill.querySelector(".status-text").textContent = "Diagnosing";

    timelineList.innerHTML = "";
    docsSection.style.display = "none";
    docsList.innerHTML = "";
    fixSection.style.display = "none";
    totalTimeLabel.textContent = "";

    try {
      // Initiate streaming request
      const response = await fetch("/api/debug/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop(); // Keep partial fragment

        for (const ev of events) {
          if (!ev.startsWith("data: ")) continue;
          const jsonStr = ev.replace("data: ", "").trim();
          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);
            if (parsed.event === "step") {
              appendTimelineStep(parsed.data);
            } else if (parsed.event === "complete") {
              renderFinalResult(parsed.data);
            }
          } catch (err) {
            console.error("Failed to parse SSE event", err);
          }
        }
      }
    } catch (err) {
      console.error("Error during debug session", err);
      agentStatePill.querySelector(".status-indicator").className = "status-indicator error";
      agentStatePill.querySelector(".status-text").textContent = "Error";
      const errCard = document.createElement("div");
      errCard.className = "step-card retrying";
      errCard.innerHTML = `<div class="step-body"><strong style="color:#ef4444">Session Error:</strong> ${err.message}</div>`;
      timelineList.appendChild(errCard);
    } finally {
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-label").textContent = "Run Autonomous Debugger";
    }
  });

  function appendTimelineStep(step) {
    const card = document.createElement("div");
    card.className = `step-card ${step.status}`;

    const modelDisplay = step.model_used.includes("nemotron")
      ? step.model_used.split("/").pop()
      : step.model_used;

    card.innerHTML = `
      <div class="step-meta">
        <div>#${step.step}</div>
        <div style="font-size:0.7rem; color:var(--text-muted)">${step.duration_ms}ms</div>
      </div>
      <div class="step-body">
        <div style="font-size:0.75rem; color:var(--accent-blue); font-family:var(--font-mono); margin-bottom:2px">
          [${step.status.toUpperCase()}] &bull; ${modelDisplay}
        </div>
        <div class="step-detail">${step.detail}</div>
      </div>
    `;
    timelineList.appendChild(card);
    timelineList.scrollTop = timelineList.scrollHeight;
  }

  function renderFinalResult(result) {
    agentStatePill.querySelector(".status-indicator").className = result.success
      ? "status-indicator"
      : "status-indicator error";
    agentStatePill.querySelector(".status-indicator").style.background = result.success ? "#22c55e" : "#ef4444";
    agentStatePill.querySelector(".status-text").textContent = result.success ? "Resolved ✓" : "Needs Review";

    totalTimeLabel.textContent = `Completed in ${result.total_duration_ms}ms (${result.attempts} attempt${result.attempts > 1 ? "s" : ""})`;

    // Grounded docs
    if (result.doc_references && result.doc_references.length > 0) {
      docsSection.style.display = "block";
      docsList.innerHTML = result.doc_references
        .map(
          (d) => `
        <div class="doc-item">
          <a class="doc-link" href="${d.url}" target="_blank" rel="noopener">${d.title}</a>
          <div class="doc-snippet">${d.snippet}</div>
        </div>
      `
        )
        .join("");
    }

    // Fix and diff
    if (result.fix) {
      fixSection.style.display = "flex";
      currentFixedCode = result.fix.fixed_code;

      fixExplanation.innerHTML = `
        <strong>Root Cause Diagnosis:</strong> ${result.analysis ? result.analysis.root_cause : ''}<br>
        <strong>Fix Explanation:</strong> ${result.fix.explanation}
      `;

      diffOutput.innerHTML = renderColoredDiff(result.fix.diff);
      fullCodeOutput.textContent = result.fix.fixed_code;

      if (result.test_result) {
        sandboxOutput.textContent = `Exit Code: ${result.test_result.exit_code}\nExecution Time: ${result.test_result.duration_ms}ms\nPassed: ${result.test_result.passed}\n\nConsole Output:\n${result.test_result.output}`;
      } else {
        sandboxOutput.textContent = "No sandbox output captured.";
      }
    }
  }
});
