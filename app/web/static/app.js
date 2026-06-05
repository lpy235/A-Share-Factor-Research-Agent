const form = document.querySelector("#run-form");
const runButton = document.querySelector("#run-button");
const statusTitle = document.querySelector("#status-title");
const runIdEl = document.querySelector("#run-id");
const errorBox = document.querySelector("#error-box");
const selectedCount = document.querySelector("#selected-count");
const factorCount = document.querySelector("#factor-count");
const eventCount = document.querySelector("#event-count");
const selectedFactors = document.querySelector("#selected-factors");
const factorList = document.querySelector("#factor-list");
const reportOutput = document.querySelector("#report-output");
const traceList = document.querySelector("#trace-list");
const rawOutput = document.querySelector("#raw-output");

let currentRun = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setLoading(true);
  setStatus("Running research");

  try {
    const documentIds = await uploadDocumentIfNeeded();
    const payload = buildRunPayload(documentIds);
    const run = await postJson("/research/runs", payload);
    currentRun = run;
    renderRun(run);
    await loadTrace(run.run_id);
    setStatus("Completed");
  } catch (error) {
    showError(error.message || "Run failed");
    setStatus("Failed");
  } finally {
    setLoading(false);
  }
});

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.tab;
    document.querySelectorAll(".tab-button").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `${target}-tab`);
    });
  });
});

function buildRunPayload(documentIds) {
  return {
    research_topic: valueOf("#research-topic"),
    source_mode: valueOf("#source-mode"),
    document_ids: documentIds,
    universe: "CSI300",
    start_date: valueOf("#start-date"),
    end_date: valueOf("#end-date"),
    max_chunks: numberOf("#max-chunks"),
    max_sources: numberOf("#max-sources"),
    allow_live_fetch: checked("#allow-live-fetch"),
    retrieval_mode: valueOf("#retrieval-mode"),
    embedding_dim: 256,
    extraction_mode: valueOf("#extraction-mode"),
    enable_llm_extraction: checked("#enable-llm"),
    llm_retry_count: 1,
    data_provider: valueOf("#data-provider"),
    cache_enabled: checked("#cache-enabled"),
    fallback_to_fixture: checked("#fallback-to-fixture"),
    market_data_cache_dir: "data_cache",
  };
}

async function uploadDocumentIfNeeded() {
  const fileInput = document.querySelector("#document-file");
  if (!fileInput.files.length) {
    return [];
  }

  const data = new FormData();
  data.append("file", fileInput.files[0]);
  const response = await fetch("/documents", {
    method: "POST",
    body: data,
  });
  if (!response.ok) {
    throw new Error(await responseText(response, "Document upload failed"));
  }
  const body = await response.json();
  return [body.document_id];
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await responseText(response, "Request failed"));
  }
  return response.json();
}

async function loadTrace(runId) {
  const response = await fetch(`/runs/${runId}/events`);
  if (!response.ok) {
    throw new Error(await responseText(response, "Could not load trace events"));
  }
  const body = await response.json();
  renderTrace(body.events || []);
}

function renderRun(run) {
  runIdEl.textContent = run.run_id;
  selectedCount.textContent = run.selected_factors.length;
  factorCount.textContent = run.factor_specs.length;
  selectedFactors.classList.toggle("empty-state", run.selected_factors.length === 0);
  selectedFactors.innerHTML = run.selected_factors.length
    ? run.selected_factors.map((name) => `<span class="chip">${escapeHtml(name)}</span>`).join("")
    : "No factor selected.";

  factorList.classList.toggle("empty-state", run.factor_specs.length === 0);
  factorList.innerHTML = run.factor_specs.length
    ? run.factor_specs.map(renderFactor).join("")
    : "No generated formulas.";

  reportOutput.textContent = run.report_markdown || "No report returned.";
  rawOutput.textContent = JSON.stringify(run, null, 2);
}

function renderFactor(factor) {
  const selected = currentRun?.selected_factors?.includes(factor.factor_name) ? "Selected" : "Candidate";
  return `
    <article class="factor-item">
      <div class="factor-name">
        <span>${escapeHtml(factor.factor_name)}</span>
        <span>${selected}</span>
      </div>
      <code class="formula">${escapeHtml(factor.formula || "")}</code>
      <p class="factor-meta">${escapeHtml(factor.hypothesis || "")}</p>
      <p class="factor-meta">Source: ${escapeHtml(factor.source_title || "unknown")}</p>
    </article>
  `;
}

function renderTrace(events) {
  eventCount.textContent = events.length;
  traceList.innerHTML = events.length
    ? events.map(renderEvent).join("")
    : '<li class="empty-state">No trace events returned.</li>';
}

function renderEvent(event) {
  const payload = JSON.stringify(event.payload || {}, null, 2);
  return `
    <li class="trace-item">
      <strong>${escapeHtml(event.node)} · ${escapeHtml(event.event_type)}</strong>
      <div class="trace-payload">${escapeHtml(payload)}</div>
    </li>
  `;
}

function setLoading(isLoading) {
  runButton.disabled = isLoading;
  runButton.textContent = isLoading ? "Running..." : "Run research";
}

function setStatus(text) {
  statusTitle.textContent = text;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function valueOf(selector) {
  return document.querySelector(selector).value;
}

function numberOf(selector) {
  return Number.parseInt(valueOf(selector), 10);
}

function checked(selector) {
  return document.querySelector(selector).checked;
}

async function responseText(response, fallback) {
  const text = await response.text();
  return text || fallback;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

