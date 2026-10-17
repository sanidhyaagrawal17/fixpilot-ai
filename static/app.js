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
  const copyDiffBtn = document.getElementById("btn-copy-diff");
  const downloadReportBtn = document.getElementById("btn-download-report");

  // Sponsor & Model Telemetry Bar
  const telemetryBar = document.getElementById("telemetry-bar");
  const telemetryProvider = document.getElementById("telemetry-provider");
  const chipClassify = document.getElementById("chip-classify");
  const chipGround = document.getElementById("chip-ground");
  const chipDiagnose = document.getElementById("chip-diagnose");
  const chipSynthesize = document.getElementById("chip-synthesize");
  const chipVerify = document.getElementById("chip-verify");
  const verificationBadge = document.getElementById("verification-badge");

  // Guide Banner & Modal elements
  const guideBanner = document.getElementById("guide-banner");
  const btnToggleGuide = document.getElementById("btn-toggle-guide");
  const btnOpenGuide = document.getElementById("btn-open-guide");
  const instructionsModal = document.getElementById("instructions-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnModalGotit = document.getElementById("btn-modal-gotit");

  let currentFixedCode = "";
  let currentDiffText = "";
  let currentFullResponse = null;

  // 1. Health Probe
  async function checkHealth() {
    try {
      const resp = await fetch("/api/health");
      if (resp.ok) {
        const data = await resp.json();
        const nvidiaActive = data.providers?.nvidia_api;
        const nebiusActive = data.providers?.nebius_token_factory;
        const openrouterActive = data.providers?.openrouter_fallback;
        const tavilyActive = data.providers?.tavily_search;
        const primary = nvidiaActive ? 'NVIDIA API' : nebiusActive ? 'Nebius API' : openrouterActive ? 'OpenRouter' : 'Diagnostic Simulation';
        backendStatus.innerHTML = `● Active: ${primary}${tavilyActive ? ' + Tavily' : ''}`;
        backendStatus.style.color = "#22c55e";
        if (telemetryProvider) {
          telemetryProvider.textContent = `${primary} • Active`;
        }
      }
    } catch (e) {
      backendStatus.innerHTML = "● Offline";
      backendStatus.style.color = "#ef4444";
    }
  }
  checkHealth();

  // 2. Guide Banner Toggle & LocalStorage Persistence
  const GUIDE_KEY = "fixpilot_guide_collapsed";
  const isCollapsed = localStorage.getItem(GUIDE_KEY) === "true";
  if (isCollapsed && guideBanner) {
    guideBanner.classList.add("collapsed");
    btnToggleGuide.textContent = "Show Guide";
  }

  if (btnToggleGuide && guideBanner) {
    btnToggleGuide.addEventListener("click", () => {
      const willCollapse = !guideBanner.classList.contains("collapsed");
      guideBanner.classList.toggle("collapsed", willCollapse);
      btnToggleGuide.textContent = willCollapse ? "Show Guide" : "Hide Guide";
      localStorage.setItem(GUIDE_KEY, willCollapse ? "true" : "false");
    });
  }

  // 3. Instructions Modal Controls
  function openModal() {
    if (instructionsModal) {
      instructionsModal.style.display = "flex";
      document.body.style.overflow = "hidden";
    }
  }

  function closeModal() {
    if (instructionsModal) {
      instructionsModal.style.display = "none";
      document.body.style.overflow = "";
    }
  }

  if (btnOpenGuide) btnOpenGuide.addEventListener("click", openModal);
  if (btnCloseModal) btnCloseModal.addEventListener("click", closeModal);
  if (btnModalGotit) btnModalGotit.addEventListener("click", closeModal);

  if (instructionsModal) {
    instructionsModal.addEventListener("click", (e) => {
      if (e.target === instructionsModal) closeModal();
    });
  }

  // 4. Global Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && instructionsModal && instructionsModal.style.display === "flex") {
      closeModal();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      if (instructionsModal && instructionsModal.style.display === "flex") return;
      if (!submitBtn.disabled) {
        form.requestSubmit ? form.requestSubmit() : submitBtn.click();
      }
    }
  });

  // 5. Cache Idle Preview HTML for clean reset
  const idlePreview = document.getElementById("idle-preview");
  const idlePreviewHtml = idlePreview ? idlePreview.outerHTML : "";

  function restoreIdlePreview() {
    if (idlePreviewHtml) {
      timelineList.innerHTML = idlePreviewHtml;
    } else {
      timelineList.innerHTML = `<div class="timeline-empty">Submit an error or select a quick scenario to begin the agent loop.</div>`;
    }
  }

  // 6. Fetch and render pre-built scenarios
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
          const label = sc.id.replace("scenario_", "").replace(/_/g, " ");
          btn.textContent = label.toUpperCase();
          btn.title = sc.description;
          btn.addEventListener("click", () => {
            document.querySelectorAll(".scenario-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");

            tracebackInput.value = sc.error_traceback;
            sourceCodeInput.value = sc.source_code;
            testCodeInput.value = sc.test_code;
            githubUrlInput.value = "";
            tracebackInput.focus();
          });
          scenarioGroup.appendChild(btn);
        });
      }
    } catch (e) {
      console.warn("Failed to load scenarios", e);
    }
  }
  loadScenarios();

  // 7. Clear Form button
  clearBtn.addEventListener("click", () => {
    tracebackInput.value = "";
    sourceCodeInput.value = "";
    testCodeInput.value = "";
    githubUrlInput.value = "";
    document.querySelectorAll(".scenario-btn").forEach((b) => b.classList.remove("active"));
    docsSection.style.display = "none";
    docsList.innerHTML = "";
    fixSection.style.display = "none";
    if (telemetryBar) telemetryBar.style.display = "none";
    totalTimeLabel.textContent = "";
    agentStatePill.querySelector(".status-indicator").className = "status-indicator";
    agentStatePill.querySelector(".status-indicator").style.background = "";
    agentStatePill.querySelector(".status-text").textContent = "Ready";
    restoreIdlePreview();
    tracebackInput.focus();
  });

  // 8. Tab switching
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

  // 9. Action Bar: Copy & Download Handlers
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      if (currentFixedCode) {
        navigator.clipboard.writeText(currentFixedCode);
        const originalText = copyBtn.textContent;
        copyBtn.textContent = "Copied! ✓";
        setTimeout(() => { copyBtn.textContent = originalText; }, 2000);
      }
    });
  }

  if (copyDiffBtn) {
    copyDiffBtn.addEventListener("click", () => {
      if (currentDiffText) {
        navigator.clipboard.writeText(currentDiffText);
        const originalText = copyDiffBtn.textContent;
        copyDiffBtn.textContent = "Copied Diff! ✓";
        setTimeout(() => { copyDiffBtn.textContent = originalText; }, 2000);
      }
    });
  }

  if (downloadReportBtn) {
    downloadReportBtn.addEventListener("click", () => {
      if (!currentFullResponse) return;
      const jsonStr = JSON.stringify(currentFullResponse, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fixpilot_verification_report_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  // 10. Format unified diff with line-by-line colored spans
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

  function resetTelemetryChips() {
    if (chipClassify) chipClassify.querySelector(".chip-val").textContent = "-";
    if (chipGround) chipGround.querySelector(".chip-val").textContent = "-";
    if (chipDiagnose) chipDiagnose.querySelector(".chip-val").textContent = "-";
    if (chipSynthesize) chipSynthesize.querySelector(".chip-val").textContent = "-";
    if (chipVerify) chipVerify.querySelector(".chip-val").textContent = "-";
    if (verificationBadge) {
      verificationBadge.className = "verification-badge";
      verificationBadge.textContent = "SANDBOX IN PROGRESS";
    }
  }

  // 11. Form Submit Handler (with True Async SSE parsing)
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
    agentStatePill.querySelector(".status-indicator").style.background = "";
    agentStatePill.querySelector(".status-text").textContent = "Diagnosing";

    timelineList.innerHTML = "";
    docsSection.style.display = "none";
    docsList.innerHTML = "";
    fixSection.style.display = "none";
    totalTimeLabel.textContent = "";

    if (telemetryBar) {
      telemetryBar.style.display = "flex";
      resetTelemetryChips();
    }

    try {
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
        buffer = events.pop();

        for (const ev of events) {
          const trimmed = ev.trim();
          if (!trimmed || trimmed.startsWith(":")) continue; // Skip keep-alive heartbeats

          if (!trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.replace("data: ", "").trim();
          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);

            // Handle Phase 1 & 4 Tier Events
            if (parsed.event === "tier_start") {
              const tier = parsed.data.tier;
              if (tier === "classify" && chipClassify) chipClassify.querySelector(".chip-val").textContent = "running...";
              if (tier === "ground" && chipGround) chipGround.querySelector(".chip-val").textContent = "searching...";
              if (tier === "diagnose" && chipDiagnose) chipDiagnose.querySelector(".chip-val").textContent = "reasoning...";
              if (tier === "synthesize" && chipSynthesize) chipSynthesize.querySelector(".chip-val").textContent = "patching...";
              if (tier === "verify" && chipVerify) chipVerify.querySelector(".chip-val").textContent = "testing...";
            } else if (parsed.event === "tier_complete") {
              const tier = parsed.data.tier;
              const msStr = `${parsed.data.latency_ms}ms`;
              if (tier === "classify" && chipClassify) chipClassify.querySelector(".chip-val").textContent = msStr;
              if (tier === "ground" && chipGround) {
                chipGround.querySelector(".chip-val").textContent = msStr;
                if (parsed.data.payload?.references) {
                  renderDocsList(parsed.data.payload.references);
                }
              }
              if (tier === "diagnose" && chipDiagnose) chipDiagnose.querySelector(".chip-val").textContent = msStr;
              if (tier === "synthesize" && chipSynthesize) chipSynthesize.querySelector(".chip-val").textContent = msStr;
              if (tier === "verify" && chipVerify) chipVerify.querySelector(".chip-val").textContent = msStr;
            } else if (parsed.event === "retry_triggered") {
              // Adaptive retry re-grounding feedback card
              const retryCard = document.createElement("div");
              retryCard.className = "step-card retrying";
              retryCard.innerHTML = `
                <div class="step-meta"><div>RETRY</div></div>
                <div class="step-body">
                  <div style="font-size:0.75rem; color:var(--accent-orange); font-family:var(--font-mono); margin-bottom:2px">
                    [ADAPTIVE TAVILY RE-GROUNDING] &bull; Attempt ${parsed.data.attempt}
                  </div>
                  <div class="step-detail">New error detected: <code>${parsed.data.new_error}</code>. Executing delta search: <em>${parsed.data.delta_query}</em></div>
                </div>
              `;
              timelineList.appendChild(retryCard);
              timelineList.scrollTop = timelineList.scrollHeight;
            } else if (parsed.event === "pipeline_complete") {
              const pData = parsed.data;
              if (verificationBadge) {
                if (pData.verified) {
                  verificationBadge.className = "verification-badge pass";
                  verificationBadge.textContent = `SANDBOX PASS (Attempt ${pData.total_attempts}/3)`;
                } else {
                  verificationBadge.className = "verification-badge fail";
                  verificationBadge.textContent = "VALIDATION FAILED";
                }
              }
              if (pData.response) {
                currentFullResponse = pData.response;
                renderFinalResult(pData.response);
              }
            } else if (parsed.event === "step") {
              appendTimelineStep(parsed.data);
            } else if (parsed.event === "complete") {
              currentFullResponse = parsed.data;
              renderFinalResult(parsed.data);
            }
          } catch (err) {
            console.error("Failed to parse SSE event", err, jsonStr);
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

  function renderDocsList(references) {
    if (!references || references.length === 0) return;
    docsSection.style.display = "block";
    docsList.innerHTML = references
      .map((d) => {
        const scorePercent = d.score ? `${Math.round(d.score * 100)}% match` : "Verified doc";
        return `
          <div class="doc-item-enhanced">
            <div class="doc-header-row">
              <a class="doc-link" href="${d.url}" target="_blank" rel="noopener">${d.title}</a>
              <span class="doc-score-pill">${scorePercent}</span>
            </div>
            <div class="doc-snippet">${d.snippet}</div>
          </div>
        `;
      })
      .join("");
  }

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

    if (result.doc_references && result.doc_references.length > 0) {
      renderDocsList(result.doc_references);
    }

    if (result.fix) {
      fixSection.style.display = "flex";
      currentFixedCode = result.fix.fixed_code;
      currentDiffText = result.fix.diff;

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
