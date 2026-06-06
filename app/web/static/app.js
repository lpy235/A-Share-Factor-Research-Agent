const form = document.querySelector("#run-form");
const runButton = document.querySelector("#run-button");
const statusTitle = document.querySelector("#status-title");
const statusCopy = document.querySelector("#status-copy");
const statusPill = document.querySelector("#status-pill");
const runIdEl = document.querySelector("#run-id");
const errorBox = document.querySelector("#error-box");
const selectedCount = document.querySelector("#selected-count");
const factorCount = document.querySelector("#factor-count");
const eventCount = document.querySelector("#event-count");
const metricSummary = document.querySelector("#metric-summary");
const sourceList = document.querySelector("#source-list");
const selectedFactors = document.querySelector("#selected-factors");
const factorList = document.querySelector("#factor-list");
const metricsTable = document.querySelector("#metrics-table");
const reportOutput = document.querySelector("#report-output");
const traceList = document.querySelector("#trace-list");
const rawOutput = document.querySelector("#raw-output");
const runConfig = document.querySelector("#run-config");
const uploadInput = document.querySelector("#document-file");
const uploadLabel = document.querySelector("#upload-label");
const workflowSteps = document.querySelectorAll("#workflow-steps li");
const launchActions = document.querySelectorAll(".launch-action");

const sourceModeLabels = {
  auto: "自动找资料",
  upload: "仅上传",
  hybrid: "混合",
};
const retrievalLabels = {
  hybrid: "混合 RAG",
  vector: "向量检索",
  keyword: "关键词检索",
};
const extractionLabels = {
  rule: "规则抽取",
  hybrid: "混合抽取",
  llm: "LLM Schema",
};
const dataProviderLabels = {
  fixture: "内置示例数据",
  akshare: "AKShare",
};

let currentRun = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  resetWorkflow();
  setLoading(true);
  setStatus("研究运行中", "系统正在检索资料、生成因子公式并运行回测校验。", "running");

  try {
    const documentIds = await uploadDocumentIfNeeded();
    const payload = buildRunPayload(documentIds);
    renderRunConfig(payload);
    const run = await postJson("/research/runs", payload);
    currentRun = run;
    renderRun(run);
    await loadTrace(run.run_id);
    setStatus("研究运行完成", "下方可以查看入选因子、回测指标、研究报告和执行追踪。", "done");
  } catch (error) {
    showError(error.message || "运行失败");
    setStatus("运行失败", "工作流在生成完整结果前停止，请检查配置或接口返回。", "failed");
  } finally {
    setLoading(false);
  }
});

uploadInput.addEventListener("change", () => {
  uploadLabel.textContent = uploadInput.files.length
    ? uploadInput.files[0].name
    : "选择 Markdown、txt 或 PDF 文件";
  setActiveLaunch(uploadInput.files.length ? "upload" : "topic");
  if (uploadInput.files.length) {
    setSourceMode("upload");
  }
});

document.querySelectorAll("input, select, textarea").forEach((control) => {
  control.addEventListener("change", () => renderRunConfig(buildRunPayload([])));
});

launchActions.forEach((button) => {
  button.addEventListener("click", () => {
    const mode = button.dataset.launch;
    if (prepareLaunch(mode)) {
      form.requestSubmit();
    }
  });
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

renderRunConfig(buildRunPayload([]));
setActiveLaunch("sample");

function prepareLaunch(mode) {
  setActiveLaunch(mode);
  if (mode === "sample") {
    document.querySelector("#research-topic").value = "A股量价类动量因子";
    setSourceMode("auto");
    document.querySelector("#retrieval-mode").value = "hybrid";
    document.querySelector("#extraction-mode").value = "rule";
    document.querySelector("#data-provider").value = "fixture";
    document.querySelector("#start-date").value = "2020-01-01";
    document.querySelector("#end-date").value = "2020-12-31";
  }
  if (mode === "topic") {
    setSourceMode("auto");
  }
  if (mode === "upload") {
    setSourceMode(uploadInput.files.length ? "upload" : "hybrid");
    if (!uploadInput.files.length) {
      uploadInput.click();
      setStatus("请选择材料", "选择论文、研报、Markdown 或文本文件后，再点击“上传论文/研报”运行。", "idle");
      renderRunConfig(buildRunPayload([]));
      return false;
    }
  }
  renderRunConfig(buildRunPayload([]));
  return true;
}

function setActiveLaunch(mode) {
  launchActions.forEach((button) => {
    button.classList.toggle("active", button.dataset.launch === mode);
  });
}

function setSourceMode(mode) {
  const radio = document.querySelector(`input[name="source_mode_radio"][value="${mode}"]`);
  if (radio) {
    radio.checked = true;
  }
}

function buildRunPayload(documentIds) {
  return {
    research_topic: valueOf("#research-topic"),
    source_mode: selectedRadioValue("source_mode_radio"),
    document_ids: documentIds,
    universe: valueOf("#universe"),
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
  if (!uploadInput.files.length) {
    return [];
  }

  const data = new FormData();
  data.append("file", uploadInput.files[0]);
  const response = await fetch("/documents", {
    method: "POST",
    body: data,
  });
  if (!response.ok) {
    throw new Error(await responseText(response, "材料上传失败"));
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
    throw new Error(await responseText(response, "请求失败"));
  }
  return response.json();
}

async function loadTrace(runId) {
  const response = await fetch(`/runs/${runId}/events`);
  if (!response.ok) {
    throw new Error(await responseText(response, "无法加载执行追踪"));
  }
  const body = await response.json();
  renderTrace(body.events || []);
  updateWorkflow(body.events || []);
}

function renderRun(run) {
  runIdEl.textContent = run.run_id;
  selectedCount.textContent = run.selected_factors.length;
  factorCount.textContent = run.factor_specs.length;
  selectedFactors.classList.toggle("empty-state", run.selected_factors.length === 0);
  selectedFactors.innerHTML = run.selected_factors.length
    ? run.selected_factors.map((name) => `<span class="chip">${escapeHtml(name)}</span>`).join("")
    : "暂无入选因子。";

  factorList.classList.toggle("empty-state", run.factor_specs.length === 0);
  factorList.innerHTML = run.factor_specs.length
    ? run.factor_specs.map(renderFactor).join("")
    : "暂无生成公式。";

  const metrics = Array.isArray(run.metrics) ? run.metrics : extractMetrics(run.report_markdown);
  renderMetricSummary(metrics);
  renderMetrics(metrics);
  renderSources(run.factor_specs);
  reportOutput.textContent = run.report_markdown || "接口未返回研究报告。";
  rawOutput.textContent = JSON.stringify(run, null, 2);
}

function renderFactor(factor) {
  const selected = currentRun?.selected_factors?.includes(factor.factor_name);
  const badgeClass = selected ? "factor-badge selected" : "factor-badge";
  const badgeText = selected ? "入选" : "候选";
  return `
    <article class="factor-item">
      <div class="factor-name">
        <span>${escapeHtml(factor.factor_name)}</span>
        <span class="${badgeClass}">${badgeText}</span>
      </div>
      <code class="formula">${escapeHtml(factor.formula || "")}</code>
      <p class="factor-meta">${escapeHtml(factor.hypothesis || "")}</p>
      <p class="factor-meta">来源：${escapeHtml(factor.source_title || "未知资料")}</p>
    </article>
  `;
}

function renderMetrics(metrics) {
  metricsTable.classList.toggle("empty-state", metrics.length === 0);
  if (!metrics.length) {
    metricsTable.innerHTML = "暂无指标。";
    return;
  }

  metricsTable.innerHTML = `
    <table class="metrics-table">
      <thead>
        <tr>
          <th>因子</th>
          <th>Rank IC</th>
          <th>ICIR</th>
          <th>覆盖率</th>
          <th>缺失率</th>
          <th>最大回撤</th>
          <th>Sharpe</th>
        </tr>
      </thead>
      <tbody>
        ${metrics
          .map(
            (metric) => `
              <tr>
                <td>${escapeHtml(metric.factor_name || "")}</td>
                <td>${escapeHtml(metric.mean_rank_ic || "")}</td>
                <td>${escapeHtml(metric.icir || "")}</td>
                <td>${escapeHtml(metric.coverage_ratio || "")}</td>
                <td>${escapeHtml(metric.missing_ratio || "")}</td>
                <td>${escapeHtml(metric.max_drawdown || "")}</td>
                <td>${escapeHtml(metric.sharpe || "")}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderMetricSummary(metrics) {
  metricSummary.classList.toggle("empty-state", metrics.length === 0);
  if (!metrics.length) {
    metricSummary.innerHTML = "运行后展示 Rank IC、ICIR、覆盖率和 Sharpe。";
    return;
  }

  const bestRankIc = bestMetric(metrics, "mean_rank_ic");
  const bestIcir = bestMetric(metrics, "icir");
  const bestCoverage = bestMetric(metrics, "coverage_ratio");
  const bestSharpe = bestMetric(metrics, "sharpe");
  metricSummary.innerHTML = [
    renderSummaryItem("最佳 Rank IC", bestRankIc, "mean_rank_ic"),
    renderSummaryItem("最佳 ICIR", bestIcir, "icir"),
    renderSummaryItem("覆盖率", bestCoverage, "coverage_ratio"),
    renderSummaryItem("Sharpe", bestSharpe, "sharpe"),
  ].join("");
}

function renderSummaryItem(label, metric, key) {
  const value = metric ? formatMetric(metric[key]) : "-";
  const factor = metric?.factor_name || "暂无因子";
  return `
    <div class="summary-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(factor)}</small>
    </div>
  `;
}

function renderSources(factors) {
  const sourceMap = new Map();
  factors.forEach((factor) => {
    const title = factor.source_title || "未知资料";
    const url = factor.source_url || "";
    const key = `${title}|${url}`;
    const source = sourceMap.get(key) || {
      title,
      url,
      factors: [],
    };
    source.factors.push(factor.factor_name);
    sourceMap.set(key, source);
  });
  const sources = [...sourceMap.values()];
  sourceList.classList.toggle("empty-state", sources.length === 0);
  sourceList.innerHTML = sources.length
    ? sources.map(renderSource).join("")
    : "运行后展示因子和资料来源的对应关系。";
}

function renderSource(source) {
  const title = escapeHtml(source.title);
  const url = escapeHtml(source.url || "本地资料");
  const factorText = `${source.factors.length} 个因子`;
  return `
    <div class="source-row">
      <div>
        <strong>${title}</strong>
        <span>${url}</span>
      </div>
      <em>${escapeHtml(factorText)}</em>
    </div>
  `;
}

function bestMetric(metrics, key) {
  return metrics.reduce((best, metric) => {
    const value = Math.abs(Number.parseFloat(metric[key]));
    if (Number.isNaN(value)) {
      return best;
    }
    if (!best || value > Math.abs(Number.parseFloat(best[key]))) {
      return metric;
    }
    return best;
  }, null);
}

function formatMetric(value) {
  const number = Number.parseFloat(value);
  if (Number.isNaN(number)) {
    return value == null ? "-" : String(value);
  }
  return number.toFixed(3);
}

function extractMetrics(report) {
  if (!report) {
    return [];
  }
  return report
    .split("\n")
    .filter((line) => line.startsWith("- factor_name="))
    .map((line) => {
      const pairs = line
        .replace(/^- /, "")
        .split(", ")
        .map((item) => item.split("="));
      return Object.fromEntries(pairs);
    });
}

function renderTrace(events) {
  eventCount.textContent = events.length;
  traceList.innerHTML = events.length
    ? events.map(renderEvent).join("")
    : '<li class="empty-state">暂无追踪事件。</li>';
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

function updateWorkflow(events) {
  const completedNodes = new Set(
    events.filter((event) => event.event_type === "node_completed").map((event) => event.node),
  );
  const failedNodes = new Set(
    events.filter((event) => event.event_type === "node_failed").map((event) => event.node),
  );
  workflowSteps.forEach((step) => {
    const node = step.dataset.node;
    step.classList.toggle("done", completedNodes.has(node));
    step.classList.toggle("failed", failedNodes.has(node));
  });
}

function resetWorkflow() {
  workflowSteps.forEach((step) => {
    step.classList.remove("done", "failed");
  });
  eventCount.textContent = "0";
}

function renderRunConfig(payload) {
  runConfig.innerHTML = `
    <span>资料来源：${escapeHtml(labelFor(sourceModeLabels, payload.source_mode))}</span>
    <span>检索方式：${escapeHtml(labelFor(retrievalLabels, payload.retrieval_mode))}</span>
    <span>抽取方式：${escapeHtml(labelFor(extractionLabels, payload.extraction_mode))}</span>
    <span>行情数据：${escapeHtml(labelFor(dataProviderLabels, payload.data_provider))}</span>
    <span>回测窗口：${escapeHtml(payload.start_date)} 至 ${escapeHtml(payload.end_date)}</span>
  `;
}

function setLoading(isLoading) {
  runButton.disabled = isLoading;
  runButton.textContent = isLoading ? "运行中..." : "运行当前研究";
}

function setStatus(title, copy, mode) {
  statusTitle.textContent = title;
  statusCopy.textContent = copy;
  statusPill.textContent = statusText(mode, title);
  statusPill.className = `status-pill ${mode || "idle"}`;
}

function statusText(mode, fallback) {
  if (mode === "running") {
    return "运行中";
  }
  if (mode === "done") {
    return "已完成";
  }
  if (mode === "failed") {
    return "失败";
  }
  return fallback || "就绪";
}

function labelFor(labels, value) {
  return labels[value] || value;
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

function selectedRadioValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`).value;
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
