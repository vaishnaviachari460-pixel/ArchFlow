const communicationInput = document.getElementById("communication");
const analyzeButton = document.getElementById("analyzeButton");
const demoSelect = document.getElementById("demoSelect");
const statusElement = document.getElementById("status");
const emptyState = document.getElementById("empty");
const resultsSection = document.getElementById("results");
const summaryElement = document.getElementById("summary");
const risksElement = document.getElementById("risks");
const decisionsElement = document.getElementById("decisions");
const actionsElement = document.getElementById("actions");
const deadlinesElement = document.getElementById("deadlines");
const changesElement = document.getElementById("changes");
const signalsElement = document.getElementById("signals");
const metricsElement = document.getElementById("metrics");
const healthExplanationElement = document.getElementById("healthExplanation");
const historyElement = document.getElementById("history");
const exportButton = document.getElementById("exportButton");
const clearAnalysisButton = document.getElementById("clearAnalysisButton");
const refreshHistoryButton = document.getElementById("refreshHistory");
const charCount = document.getElementById("charCount");
const riskCount = document.getElementById("riskCount");
const decisionCount = document.getElementById("decisionCount");
const deadlineCount = document.getElementById("deadlineCount");
const changeCount = document.getElementById("changeCount");
const actionFilters = document.getElementById("actionFilters");
const actionLegend = document.getElementById("actionLegend");

const LATEST_ANALYSIS_KEY = "archflow_latest_analysis";
let currentAnalysis = null;
let currentActions = [];
let currentActionFilter = "ALL";

const demos = {
    material: `Supplier: Tiles M-305 are currently out of stock.\nContractor: We need approximately 450 tiles for the flooring work.\nSite Engineer: Flooring installation is scheduled to begin on 14 September.\nSupplier: New stock is expected only on 18 September.\nProject Manager: Please check whether an equivalent approved tile is available.\nClient: Do not purchase an alternative without approval.\nArchitect: I will review the proposed alternative today.`,
    revision: `Architect: The structural drawing has been updated to Rev 06.\nSite Engineer: Our team is currently working with Rev 05 on site.\nContractor: The staircase reinforcement has already been prepared according to Rev 05.\nProject Manager: Stop further reinforcement work until the latest drawing is verified.\nArchitect: Please ensure all teams switch to Rev 06 before continuing.\nClient: Approved. Proceed with Rev 06.`,
    delay: `Client: The project handover date remains 25 September.\nContractor: We have completed only 70% of the work.\nSite Engineer: The HVAC installation is still pending.\nSupplier: HVAC equipment delivery has been delayed by one week.\nProject Manager: The delay will affect testing and commissioning.\nClient: The handover date cannot be extended.\nContractor: We need additional workers to recover the schedule.\nProject Manager: Prepare a recovery plan by 11 September.\nClient: Approved. Proceed with additional manpower.`,
    change: `Architect: The specified flooring was originally approved as M-305.\nSupplier: M-305 is no longer available from our supplier.\nContractor: We recommend replacing it with M-310 to avoid delaying the flooring work.\nSite Engineer: Flooring installation is scheduled to start on 18 September.\nClient: Please submit the M-310 sample for review.\nArchitect: I have reviewed the sample and approve M-310 for the flooring.\nContractor: Proceed with ordering M-310.\nProject Manager: Confirm the delivery date before installation starts.`,
    healthy: `Architect: The lobby layout is approved for construction.\nContractor: We will complete the approved partition work this week.\nSite Engineer: Site progress is on schedule.\nClient: Approved. Proceed with the current layout.\nProject Manager: Confirm the inspection date with the site team.`
};

function setStatus(message, type = "") {
    statusElement.textContent = message;
    statusElement.className = `status ${type}`;
}

function updateCharCount() {
    const count = communicationInput.value.length;
    charCount.textContent = `${count.toLocaleString()} character${count === 1 ? "" : "s"}`;
}

if (communicationInput) communicationInput.addEventListener("input", updateCharCount);

if (communicationInput) communicationInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") analyzeCommunication();
});

if (demoSelect) demoSelect.addEventListener("change", () => {
    const value = demoSelect.value;
    if (!value || !demos[value]) return;
    communicationInput.value = demos[value];
    updateCharCount();
    setStatus(`${demoSelect.options[demoSelect.selectedIndex].text} demo loaded.`, "success");
    communicationInput.focus();
});

if (analyzeButton) analyzeButton.addEventListener("click", analyzeCommunication);
if (exportButton) exportButton.addEventListener("click", exportReport);
if (refreshHistoryButton) refreshHistoryButton.addEventListener("click", loadHistory);
if (clearAnalysisButton) clearAnalysisButton.addEventListener("click", () => { window.location.href = "/"; });

async function analyzeCommunication() {
    const communication = communicationInput.value.trim();
    if (!communication) {
        setStatus("Please enter some project communication.", "error");
        communicationInput.focus();
        return;
    }

    analyzeButton.disabled = true;
    analyzeButton.classList.add("loading");
    analyzeButton.textContent = "Analyzing…";
    setStatus("Analyzing project communication…", "loading");

    try {
        const formData = new FormData();
        formData.append("communication", communication);
        const response = await fetch("/analyze", { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Analysis failed.");

        currentAnalysis = data;
        currentActions = Array.isArray(data.actions) ? data.actions : [];
        localStorage.setItem(LATEST_ANALYSIS_KEY, JSON.stringify(data));
        window.location.href = `/results/${encodeURIComponent(data.analysis_id)}`;
        return;
    } catch (error) {
        console.error(error);
        setStatus(error.message || "Analysis failed.", "error");
    } finally {
        analyzeButton.disabled = false;
        analyzeButton.classList.remove("loading");
        analyzeButton.textContent = "Analyze Communication →";
    }
}

function displayResults(data) {
    currentAnalysis = data;
    currentActions = Array.isArray(data.actions) ? data.actions : [];
    emptyState.classList.add("hidden");
    resultsSection.classList.remove("hidden");
    resultsSection.classList.remove("results-reveal");
    void resultsSection.offsetWidth;
    resultsSection.classList.add("results-reveal");

    summaryElement.textContent = data.summary || "No summary available.";
    riskCount.textContent = data.risks?.length || 0;
    decisionCount.textContent = data.decisions?.length || 0;
    deadlineCount.textContent = data.deadlines?.length || 0;
    changeCount.textContent = data.changes?.length || 0;

    showMetrics(data);
    showHealthExplanation(data);
    showRisks(data.risks || []);
    showDecisions(data.decisions || []);
    showActions(currentActions);
    showDeadlines(data.deadlines || [], data.deadline_details || [], currentActions);
    showChanges(data.changes || []);
    showSignals(data);
}

function showMetrics(data) {
    const items = [
        ["PROJECT HEALTH", data.project_health || "HEALTHY", getHealthClass(data.project_health)],
        ["PRIORITY", data.priority || "LOW", getPriorityClass(data.priority)],
        ["RISKS", data.risks?.length || 0, ""],
        ["DECISIONS", data.decisions?.length || 0, ""],
        ["ACTIONS", currentActions.length, ""],
        ["DEADLINES", data.deadlines?.length || 0, ""]
    ];
    metricsElement.innerHTML = items.map(([label, value, cls]) => `
        <div class="metric ${cls}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>
    `).join("");
}

function showHealthExplanation(data) {
    const health = data.project_health || "HEALTHY";
    healthExplanationElement.className = `health-explanation ${getHealthClass(health)}`;
    healthExplanationElement.innerHTML = `<strong>Why this matters</strong><p>${escapeHtml(data.health_explanation || "No major project risks were detected.")}</p>`;
}

function showRisks(risks) {
    if (!risks.length) {
        risksElement.innerHTML = emptyMessage("No major risks detected.");
        return;
    }
    risksElement.innerHTML = risks.map(risk => `
        <article class="risk-item ${severityClass(risk.severity)}">
            <div class="risk-top"><span class="severity-dot"></span><strong>${escapeHtml(risk.risk || "Risk")}</strong><span class="severity-badge">${escapeHtml(risk.severity || "MEDIUM")}</span></div>
            <p>${escapeHtml(risk.description || "")}</p>
        </article>
    `).join("");
}

function showDecisions(decisions) {
    if (!decisions.length) {
        decisionsElement.innerHTML = emptyMessage("No confirmed decisions detected.");
        return;
    }
    decisionsElement.innerHTML = decisions.map(item => `
        <article class="decision-item"><span class="decision-icon">✓</span><div><strong>${escapeHtml(item.decision || "")}</strong><small>Owner: ${escapeHtml(item.owner || "Project Team")}</small></div></article>
    `).join("");
}

function showActions(actions) {
    const counts = {
        ALL: actions.length,
        PENDING: actions.filter(a => normalizeStatus(a.status) === "PENDING").length,
        "IN PROGRESS": actions.filter(a => normalizeStatus(a.status) === "IN PROGRESS").length,
        COMPLETED: actions.filter(a => normalizeStatus(a.status) === "COMPLETED").length
    };
    actionFilters.innerHTML = [
        ["ALL", "All"], ["PENDING", "🟠 Pending"], ["IN PROGRESS", "🔵 In Progress"], ["COMPLETED", "🟢 Completed"]
    ].map(([key, label]) => `<button class="filter ${currentActionFilter === key ? "active" : ""}" data-filter="${key}">${label} <b>${counts[key]}</b></button>`).join("");
    actionFilters.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => {
        currentActionFilter = button.dataset.filter;
        showActions(currentActions);
    }));

    actionLegend.innerHTML = `<span>🟠 Pending <small>Needs attention</small></span><span>🔵 In Progress <small>Currently being handled</small></span><span>🟢 Completed <small>Finished</small></span>`;

    const filtered = currentActionFilter === "ALL" ? actions : actions.filter(a => normalizeStatus(a.status) === currentActionFilter);
    if (!filtered.length) {
        actionsElement.innerHTML = emptyMessage("No actions in this status.");
        return;
    }

    actionsElement.innerHTML = filtered.map(action => {
        const status = normalizeStatus(action.status);
        return `<article class="action-item">
            <div class="action-main"><div class="action-title"><span class="action-status-icon ${getStatusClass(status)}">${getStatusIcon(status)}</span><strong>${escapeHtml(action.action || "")}</strong></div>
            <div class="action-meta"><span>👤 Owner: ${escapeHtml(action.owner || "Project Team")}</span><span>📅 Deadline: ${escapeHtml(action.deadline || "Not specified")}</span><span class="priority-mini">${escapeHtml(action.priority || "MEDIUM")}</span></div></div>
            <div class="status-buttons">
                ${["PENDING", "IN PROGRESS", "COMPLETED"].map(option => `<button class="status-button ${status === option ? "selected" : ""}" data-id="${action.id}" data-status="${option}">${getStatusIcon(option)} ${option === "IN PROGRESS" ? "In Progress" : option.charAt(0) + option.slice(1).toLowerCase()}</button>`).join("")}
            </div>
        </article>`;
    }).join("");

    actionsElement.querySelectorAll(".status-button").forEach(button => button.addEventListener("click", () => changeActionStatus(button.dataset.id, button.dataset.status)));
}

async function changeActionStatus(id, status) {
    try {
        const response = await fetch(`/actions/${encodeURIComponent(id)}`, {
            method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not update action.");
        const action = currentActions.find(item => String(item.id) === String(id));
        if (action) action.status = data.status;
        if (currentAnalysis) {
            currentAnalysis.actions = currentActions;
            localStorage.setItem(LATEST_ANALYSIS_KEY, JSON.stringify(currentAnalysis));
        }
        showMetrics(currentAnalysis);
        showActions(currentActions);
        setStatus("Action status updated.", "success");
    } catch (error) {
        setStatus(error.message, "error");
    }
}

function showDeadlines(deadlines, details, actions) {
    if (!deadlines.length) {
        deadlinesElement.innerHTML = emptyMessage("No deadlines detected.");
        return;
    }
    deadlinesElement.innerHTML = deadlines.map(deadline => {
        const related = actions.find(action => normalizeDeadline(action.deadline) === normalizeDeadline(deadline));
        const detail = details.find(item => normalizeDeadline(item.deadline) === normalizeDeadline(deadline));
        if (related) {
            return `<article class="deadline-item linked"><div class="deadline-date">⏰ <strong>${escapeHtml(deadline)}</strong></div><div class="linked-action">🔗 Linked action: <strong>${escapeHtml(related.action)}</strong><small>Owner: ${escapeHtml(related.owner || "Project Team")} · Status: ${escapeHtml(normalizeStatus(related.status))}</small></div></article>`;
        }
        if (detail?.action) {
            return `<article class="deadline-item"><div class="deadline-date">⏰ <strong>${escapeHtml(deadline)}</strong></div><div class="linked-action">Action detected: <strong>${escapeHtml(detail.action)}</strong><small>Owner: ${escapeHtml(detail.owner || "Project Team")}</small></div></article>`;
        }
        return `<article class="deadline-item"><div class="deadline-date">⏰ <strong>${escapeHtml(deadline)}</strong></div><div class="unlinked">⚠ No linked action detected</div></article>`;
    }).join("");
}

function showChanges(changes) {
    if (!changes.length) {
        changesElement.innerHTML = emptyMessage("No change compared with the previous project communication.");
        return;
    }
    changesElement.innerHTML = changes.map(change => `
        <article class="change-item"><div class="change-head"><span>↻</span><strong>${escapeHtml(change.title || change.type || "Change detected")}</strong></div>
        <div class="change-flow"><span>${escapeHtml(change.previous || "Previous")}</span><b>→</b><span>${escapeHtml(change.current || "Current")}</span></div>
        <p>${escapeHtml(change.impact || "")}</p><small>Suggested attention: ${escapeHtml(change.action || "Review the change with the project team.")}</small></article>
    `).join("");
}

function showSignals(data) {
    const revisions = data.revisions || [];
    const materials = data.materials || [];
    const items = [
        ["MESSAGES", data.message_count || 0],
        ["DRAWING REVISIONS", revisions.length ? revisions.map(x => `Rev ${x}`).join(" · ") : "None"],
        ["MATERIAL CODES", materials.length ? materials.join(" · ") : "None"]
    ];
    signalsElement.innerHTML = items.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`).join("");
}

async function loadBackendLatest() {
    try {
        const response = await fetch("/latest");
        const payload = await response.json();
        if (response.ok && payload.analysis) {
            currentAnalysis = payload.analysis;
            currentActions = payload.analysis.actions || [];
            localStorage.setItem(LATEST_ANALYSIS_KEY, JSON.stringify(payload.analysis));
            displayResults(payload.analysis);
            setStatus("Latest analysis restored.", "success");
            return true;
        }
    } catch (error) { console.warn("Latest analysis unavailable", error); }
    return false;
}

function restoreLocalAnalysis() {
    try {
        const raw = localStorage.getItem(LATEST_ANALYSIS_KEY);
        if (!raw) return false;
        const data = JSON.parse(raw);
        if (!data || !data.summary) return false;
        currentAnalysis = data;
        currentActions = data.actions || [];
        displayResults(data);
        return true;
    } catch (error) {
        console.warn("Could not restore local analysis", error);
        return false;
    }
}

async function loadHistory() {
    try {
        const response = await fetch("/history");
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Could not load history.");
        showHistory(payload.history || []);
    } catch (error) {
        historyElement.innerHTML = emptyMessage("History could not be loaded.");
        console.error(error);
    }
}

function showHistory(history) {
    if (!history.length) {
        historyElement.innerHTML = emptyMessage("No previous analyses saved yet.");
        return;
    }
    historyElement.innerHTML = history.map(item => `
        <button class="history-item" data-id="${item.id}">
            <div><strong>Analysis #${item.id}</strong><small>${escapeHtml(formatHistoryDate(item.created_at))}</small></div>
            <div class="history-summary"><span class="health-chip ${getHealthClass(item.project_health)}">${escapeHtml(item.project_health || "HEALTHY")}</span><span class="history-priority">${escapeHtml(item.priority || "LOW")}</span></div>
            <p>${escapeHtml(item.summary || "No summary")}</p>
        </button>
    `).join("");
    historyElement.querySelectorAll(".history-item").forEach(button => button.addEventListener("click", () => { window.location.href = `/results/${encodeURIComponent(button.dataset.id)}`; }));
}

async function loadHistoryItem(id) {
    try {
        const response = await fetch(`/history/${encodeURIComponent(id)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load analysis.");
        currentAnalysis = data;
        currentActions = data.actions || [];
        displayResults(data);
        window.scrollTo({ top: document.querySelector(".intelligence-card").offsetTop - 30, behavior: "smooth" });
        setStatus(`Analysis #${id} loaded.`, "success");
    } catch (error) { setStatus(error.message, "error"); }
}

async function exportReport() {
    if (!currentAnalysis) {
        setStatus("Analyze a project before exporting a report.", "error");
        return;
    }
    const data = currentAnalysis;
    const reportWindow = window.open("", "_blank", "width=900,height=900");
    if (!reportWindow) {
        setStatus("Please allow pop-ups to export the report.", "error");
        return;
    }
    const risks = (data.risks || []).map(r => `<li><strong>${escapeHtml(r.risk)}</strong> — ${escapeHtml(r.description)}</li>`).join("") || "<li>No major risks detected.</li>";
    const decisions = (data.decisions || []).map(d => `<li>${escapeHtml(d.decision)} <small>(${escapeHtml(d.owner || "Project Team")})</small></li>`).join("") || "<li>No confirmed decisions detected.</li>";
    const actions = (data.actions || []).map(a => `<li><strong>${escapeHtml(a.action)}</strong> — ${escapeHtml(a.owner || "Project Team")} — ${escapeHtml(a.deadline || "Not specified")} — ${escapeHtml(a.status || "PENDING")}</li>`).join("") || "<li>No actions detected.</li>";
    const changes = (data.changes || []).map(c => `<li><strong>${escapeHtml(c.title || c.type)}</strong>: ${escapeHtml(c.previous)} → ${escapeHtml(c.current)}</li>`).join("") || "<li>No changes detected.</li>";
    reportWindow.document.write(`<!doctype html><html><head><title>ArchFlow Project Report</title><style>body{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;color:#172033;line-height:1.55}h1{margin-bottom:4px}h2{margin-top:30px;border-bottom:1px solid #ddd;padding-bottom:8px}.meta{background:#f5f7fb;padding:18px;border-radius:12px}li{margin:8px 0}.badge{display:inline-block;padding:5px 10px;border-radius:20px;background:#eef3ff;margin-right:8px}small{color:#667085}</style></head><body><h1>ArchFlow</h1><p>Project Communication Intelligence</p><div class="meta"><b>Project Health:</b> ${escapeHtml(data.project_health)}<br><b>Priority:</b> ${escapeHtml(data.priority)}<br><b>Why:</b> ${escapeHtml(data.health_explanation || "")}</div><h2>Summary</h2><p>${escapeHtml(data.summary || "")}</p><h2>Risks</h2><ul>${risks}</ul><h2>Decisions</h2><ul>${decisions}</ul><h2>Action Items</h2><ul>${actions}</ul><h2>Deadlines</h2><ul>${(data.deadlines || []).map(d => `<li>${escapeHtml(d)}</li>`).join("") || "<li>None detected.</li>"}</ul><h2>Detected Changes</h2><ul>${changes}</ul><p><small>Generated by ArchFlow · AS-02 Communication</small></p></body></html>`);
    reportWindow.document.close();
    reportWindow.focus();
    setTimeout(() => reportWindow.print(), 300);
}

function normalizeStatus(status) {
    return String(status || "PENDING").trim().toUpperCase().replaceAll("_", " ");
}
function normalizeDeadline(value) { return String(value || "").trim().toLowerCase().replace(/\s+/g, " "); }
function getStatusClass(status) { return normalizeStatus(status).toLowerCase().replaceAll(" ", "-"); }
function getStatusIcon(status) { const value = normalizeStatus(status); return value === "COMPLETED" ? "🟢" : value === "IN PROGRESS" ? "🔵" : "🟠"; }
function severityClass(value) { return String(value || "MEDIUM").toLowerCase(); }
function getHealthClass(value) { return String(value || "HEALTHY").toLowerCase().replaceAll(" ", "-"); }
function getPriorityClass(value) { return `priority-${String(value || "LOW").toLowerCase()}`; }
function emptyMessage(text) { return `<div class="empty-message">${escapeHtml(text)}</div>`; }
function formatHistoryDate(value) { if (!value) return ""; const date = new Date(String(value).replace(" ", "T")); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
function escapeHtml(value) { return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }

if (communicationInput) updateCharCount();
(async function init() {
    const resultMatch = window.location.pathname.match(/^\/results\/(\d+)\/?$/);
    if (resultMatch) {
        try {
            const response = await fetch(`/history/${encodeURIComponent(resultMatch[1])}`, { cache: "no-store" });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not load analysis.");
            currentAnalysis = data;
            currentActions = data.actions || [];
            displayResults(data);
            const resultStatus = document.getElementById("resultStatus");
            if (resultStatus) resultStatus.textContent = `Analysis #${resultMatch[1]} · Saved project intelligence`;
        } catch (error) {
            console.error(error);
            const resultStatus = document.getElementById("resultStatus");
            if (resultStatus) resultStatus.textContent = error.message;
            if (emptyState) emptyState.innerHTML = `<div class="empty-message">${escapeHtml(error.message)}</div>`;
        }
    }
    await loadHistory();
})();
