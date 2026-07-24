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
const artifactList = document.querySelector("#artifact-list");
const runHistory = document.querySelector("#run-history");
const sourceDiagnostics = document.querySelector("#source-diagnostics");
const backtestAssumptions = document.querySelector("#backtest-assumptions");
const longOnlyMetrics = document.querySelector("#long-only-metrics");
const tradabilityDiagnostics = document.querySelector("#tradability-diagnostics");
const auditTrail = document.querySelector("#audit-trail");
const runConfig = document.querySelector("#run-config");
const uploadInput = document.querySelector("#document-file");
const uploadLabel = document.querySelector("#upload-label");
const workflowSteps = document.querySelectorAll("#workflow-steps li");
const launchActions = document.querySelectorAll(".launch-action");
const llmProvider = document.querySelector("#llm-provider");
const llmModel = document.querySelector("#llm-model");
const llmBaseUrl = document.querySelector("#llm-base-url");
const llmApiKey = document.querySelector("#llm-api-key");
const llmEnableFromSettings = document.querySelector("#llm-enable-from-settings");
const saveLlmConfig = document.querySelector("#save-llm-config");
const clearLlmConfig = document.querySelector("#clear-llm-config");
const llmConfigStatus = document.querySelector("#llm-config-status");

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
const LLM_CONFIG_STORAGE_KEY = "ashare-factor-agent-llm-config";

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
    const started = await postJson("/research/runs", payload);
    runIdEl.textContent = started.run_id;
    const result = await pollRunStatus(started.run_id);
    if (result.status === "failed") {
      throw new Error(result.error || "工作流执行失败");
    }
    currentRun = result;
    renderRun(result);
    await loadTrace(started.run_id);
    await loadRunHistory();
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

saveLlmConfig.addEventListener("click", () => {
  localStorage.setItem(LLM_CONFIG_STORAGE_KEY, JSON.stringify(readLlmConfig()));
  syncLlmExtractionSwitch();
  renderLlmConfigStatus("已保存模型配置到当前浏览器。");
  renderRunConfig(buildRunPayload([]));
});

clearLlmConfig.addEventListener("click", () => {
  localStorage.removeItem(LLM_CONFIG_STORAGE_KEY);
  llmProvider.value = "openai";
  llmModel.value = "gpt-5.2";
  llmBaseUrl.value = "";
  llmApiKey.value = "";
  llmEnableFromSettings.checked = false;
  syncLlmExtractionSwitch();
  renderLlmConfigStatus("已清空模型配置。");
  renderRunConfig(buildRunPayload([]));
});

llmEnableFromSettings.addEventListener("change", () => {
  syncLlmExtractionSwitch();
  renderRunConfig(buildRunPayload([]));
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

loadLlmConfig();
renderRunConfig(buildRunPayload([]));
setActiveLaunch("sample");
loadRunHistory();

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
    research_topic: valueOf("#research-topic") || null,
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
    llm_config: readLlmConfig(),
    data_provider: valueOf("#data-provider"),
    cache_enabled: checked("#cache-enabled"),
    fallback_to_fixture: checked("#fallback-to-fixture"),
    market_data_cache_dir: "data_cache",
    execution_mode: "next_open_to_next_open",
    commission_bps: numberOf("#commission-bps"),
    stamp_duty_bps: numberOf("#stamp-duty-bps"),
    slippage_bps: numberOf("#slippage-bps"),
    exclude_st: checked("#exclude-st"),
    min_listing_days: numberOf("#min-listing-days"),
    async_run: true,
  };
}

function loadLlmConfig() {
  const raw = localStorage.getItem(LLM_CONFIG_STORAGE_KEY);
  if (!raw) {
    renderLlmConfigStatus("未保存模型配置。未启用时系统使用规则抽取。");
    return;
  }
  try {
    const config = JSON.parse(raw);
    llmProvider.value = config.provider || "openai";
    llmModel.value = config.model || "gpt-5.2";
    llmBaseUrl.value = config.base_url || "";
    llmApiKey.value = config.api_key || "";
    llmEnableFromSettings.checked = Boolean(config.enable_llm_extraction);
    syncLlmExtractionSwitch();
    renderLlmConfigStatus("已从当前浏览器加载模型配置。");
  } catch {
    localStorage.removeItem(LLM_CONFIG_STORAGE_KEY);
    renderLlmConfigStatus("本地模型配置格式异常，已忽略。");
  }
}

function readLlmConfig() {
  return {
    provider: llmProvider.value,
    model: llmModel.value.trim(),
    base_url: llmBaseUrl.value.trim(),
    api_key: llmApiKey.value.trim(),
    enable_llm_extraction: llmEnableFromSettings.checked,
  };
}

function syncLlmExtractionSwitch() {
  document.querySelector("#enable-llm").checked = llmEnableFromSettings.checked;
  if (llmEnableFromSettings.checked) {
    document.querySelector("#extraction-mode").value = "hybrid";
  }
}

function renderLlmConfigStatus(prefix) {
  const config = readLlmConfig();
  const keyText = config.api_key ? `Key ${maskSecret(config.api_key)}` : "未填写 Key";
  const baseUrl = config.base_url || "默认 OpenAI 地址";
  llmConfigStatus.textContent = `${prefix} 当前：${labelLlmProvider(config.provider)} / ${config.model || "未填写模型"} / ${baseUrl} / ${keyText}`;
}

function labelLlmProvider(provider) {
  const labels = {
    openai: "OpenAI 兼容",
    deepseek: "DeepSeek",
    qwen: "通义千问",
    custom: "自定义",
  };
  return labels[provider] || provider;
}

function maskSecret(value) {
  if (!value) {
    return "";
  }
  if (value.length <= 8) {
    return "********";
  }
  return `${value.slice(0, 3)}...${value.slice(-4)}`;
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

async function pollRunStatus(runId, intervalMs = 1000, timeoutMs = 180000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await loadTrace(runId);
    } catch {
      // trace 加载失败不阻断轮询
    }
    const response = await fetch(`/runs/${runId}`);
    if (!response.ok) {
      throw new Error("无法获取运行状态");
    }
    const body = await response.json();
    if (body.status === "completed") {
      return body.response;
    }
    if (body.status === "failed") {
      return { status: "failed", error: (body.response || {}).error };
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("运行超时，请稍后在历史实验中查看结果。");
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

async function loadRunHistory() {
  const response = await fetch("/runs?limit=8");
  if (!response.ok) {
    return;
  }
  const body = await response.json();
  renderRunHistory(body.runs || []);
}

async function reopenRun(runId) {
  clearError();
  const response = await fetch(`/runs/${runId}`);
  if (!response.ok) {
    showError(await responseText(response, "无法打开历史实验"));
    return;
  }
  const body = await response.json();
  currentRun = body.response;
  renderRun(body.response);
  await loadTrace(runId);
  setStatus("已打开历史实验", "当前展示的是历史研究结果，可继续查看报告、图表和审计链。", "done");
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
  renderArtifacts(run.artifacts || []);
  renderSourceDiagnostics(run.source_diagnostics || {});
  renderBacktestAssumptions(run.backtest_assumptions || {});
  renderLongOnlyMetrics(run.long_only_metrics || []);
  renderTradabilityDiagnostics(
    run.tradability_diagnostics || {},
    run.universe_diagnostics || {},
  );
  renderAuditTrail(run.audit_trail || []);
  reportOutput.textContent = run.report_markdown || "接口未返回研究报告。";
  rawOutput.textContent = JSON.stringify(run, null, 2);
}

function renderRunHistory(runs) {
  runHistory.classList.toggle("empty-state", runs.length === 0);
  if (!runs.length) {
    runHistory.innerHTML = "暂无历史实验。";
    return;
  }
  runHistory.innerHTML = runs
    .map(
      (run) => `
        <button class="history-item" type="button" data-run-id="${escapeHtml(run.run_id)}">
          <span>${escapeHtml(run.research_topic)}</span>
          <small>${escapeHtml(run.selected_count)} 个入选 · ${escapeHtml(run.updated_at)}</small>
        </button>
      `,
    )
    .join("");
  runHistory.querySelectorAll(".history-item").forEach((button) => {
    button.addEventListener("click", () => reopenRun(button.dataset.runId));
  });
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
          <th>IS Rank IC</th>
          <th>OOS Rank IC</th>
          <th>ICIR</th>
          <th>IC 衰减</th>
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
                <td>${escapeHtml(formatMetric(metric.mean_rank_ic))}</td>
                <td>${escapeHtml(formatMetric(metric.mean_rank_ic_oos))}</td>
                <td>${escapeHtml(formatMetric(metric.icir))}</td>
                <td>${escapeHtml(formatMetric(metric.ic_decay_ratio))}</td>
                <td>${escapeHtml(formatMetric(metric.coverage_ratio))}</td>
                <td>${escapeHtml(formatMetric(metric.missing_ratio))}</td>
                <td>${escapeHtml(formatMetric(metric.max_drawdown))}</td>
                <td>${escapeHtml(formatMetric(metric.sharpe))}</td>
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
  const bestOosRankIc = bestMetric(metrics, "mean_rank_ic_oos");
  const bestIcir = bestMetric(metrics, "icir");
  const bestSharpe = bestMetric(metrics, "sharpe");
  metricSummary.innerHTML = [
    renderSummaryItem("最佳 IS Rank IC", bestRankIc, "mean_rank_ic"),
    renderSummaryItem("最佳 OOS Rank IC", bestOosRankIc, "mean_rank_ic_oos"),
    renderSummaryItem("最佳 ICIR", bestIcir, "icir"),
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

function renderArtifacts(artifacts) {
  artifactList.classList.toggle("empty-state", artifacts.length === 0);
  if (!artifacts.length) {
    artifactList.innerHTML = "运行后展示图表预览、Markdown 报告和 JSON 研究包下载入口。";
    return;
  }

  const charts = artifacts.filter((artifact) => artifact.kind === "chart");
  const files = artifacts.filter((artifact) => artifact.kind !== "chart");
  artifactList.innerHTML = `
    <div class="chart-grid">
      ${charts.map(renderChartArtifact).join("")}
    </div>
    <div class="download-grid">
      ${files.map(renderDownloadArtifact).join("")}
    </div>
  `;
}

function renderSourceDiagnostics(diagnostics) {
  const accepted = diagnostics.accepted || [];
  const rejected = diagnostics.rejected || [];
  sourceDiagnostics.classList.toggle("empty-state", !accepted.length && !rejected.length);
  if (!accepted.length && !rejected.length) {
    sourceDiagnostics.innerHTML = "运行后展示接受和过滤的资料来源。";
    return;
  }
  sourceDiagnostics.innerHTML = `
    <div class="diagnostic-kpis">
      <span>接受 ${escapeHtml(diagnostics.accepted_count || accepted.length)}</span>
      <span>过滤 ${escapeHtml(diagnostics.rejected_count || rejected.length)}</span>
    </div>
    ${accepted.slice(0, 4).map((item) => renderDiagnosticRow(item, "接受")).join("")}
    ${rejected.slice(0, 4).map((item) => renderDiagnosticRow(item, "过滤")).join("")}
  `;
}

function renderBacktestAssumptions(assumptions) {
  const entries = [
    ["股票池", assumptions.universe],
    ["区间", assumptions.start_date && `${assumptions.start_date} 至 ${assumptions.end_date}`],
    ["数据源", assumptions.data_provider],
    ["调仓", assumptions.rebalance_frequency],
    ["执行", assumptions.execution_mode],
    ["佣金", `${assumptions.commission_bps ?? 0} bps`],
    ["印花税", `${assumptions.stamp_duty_bps ?? 0} bps`],
    ["滑点", `${assumptions.slippage_bps ?? 0} bps`],
    ["样本切分", assumptions.oos_split_ratio],
    ["OOS 起点", assumptions.oos_split_date],
  ].filter((item) => item[1]);
  backtestAssumptions.classList.toggle("empty-state", entries.length === 0);
  if (!entries.length) {
    backtestAssumptions.innerHTML = "运行后展示股票池、数据源、交易成本和偏差提示。";
    return;
  }
  backtestAssumptions.innerHTML = `
    ${entries.map(([label, value]) => `<div class="diagnostic-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></div>`).join("")}
    ${(assumptions.bias_notes || []).map((item) => `<p class="diagnostic-note">${escapeHtml(item)}</p>`).join("")}
  `;
}

function renderLongOnlyMetrics(metrics) {
  longOnlyMetrics.classList.toggle("empty-state", metrics.length === 0);
  longOnlyMetrics.innerHTML = metrics.length
    ? metrics.map((metric) => `
        <div class="diagnostic-row">
          <strong>${escapeHtml(metric.factor_name)}</strong>
          <span>年化 ${formatMetric(metric.annualized_return)} · 超额 ${formatMetric(metric.excess_annualized_return)} · Sharpe ${formatMetric(metric.sharpe)}</span>
          <small>Beta ${formatMetric(metric.benchmark_beta)} · IR ${formatMetric(metric.information_ratio)} · 跟踪误差 ${formatMetric(metric.tracking_error)} · 回撤 ${formatMetric(metric.max_drawdown)} · 相对回撤 ${formatMetric(metric.relative_max_drawdown)}</small>
        </div>
      `).join("")
    : "暂无组合指标。";
}

function renderTradabilityDiagnostics(diagnostics, universe) {
  const entries = Object.entries(diagnostics);
  tradabilityDiagnostics.classList.toggle("empty-state", entries.length === 0);
  tradabilityDiagnostics.innerHTML = entries.length
    ? `
      ${entries.map(([factor, item]) => `
        <div class="diagnostic-row">
          <strong>${escapeHtml(factor)}</strong>
          <span>已应用：${escapeHtml((item.applied_rules || []).join(", ") || "无")}</span>
          <small>缺失：${escapeHtml((item.missing_fields || []).join(", ") || "无")}</small>
        </div>
      `).join("")}
      ${universe.warning ? `<p class="diagnostic-note">${escapeHtml(universe.warning)}</p>` : ""}
    `
    : "暂无交易诊断。";
}

function renderAuditTrail(entries) {
  auditTrail.classList.toggle("empty-state", entries.length === 0);
  if (!entries.length) {
    auditTrail.innerHTML = "运行后展示资料选择、因子抽取、DSL 校验和筛选解释。";
    return;
  }
  auditTrail.innerHTML = entries
    .map(
      (item) => `
        <article class="audit-item">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `,
    )
    .join("");
}

function renderDiagnosticRow(item, label) {
  return `
    <div class="diagnostic-row">
      <strong>${escapeHtml(label)}</strong>
      <span>${escapeHtml(item.title || item.url || "未知来源")}</span>
      <small>${escapeHtml(item.reason || item.policy || item.source_type || "")}</small>
    </div>
  `;
}

function renderChartArtifact(artifact) {
  return `
    <figure class="chart-artifact">
      <img src="${escapeHtml(artifact.url)}" alt="${escapeHtml(artifact.label)}" loading="lazy" />
      <figcaption>${escapeHtml(artifact.label)}</figcaption>
    </figure>
  `;
}

function renderDownloadArtifact(artifact) {
  return `
    <a class="download-artifact" href="${escapeHtml(artifact.url)}" target="_blank" rel="noreferrer">
      <span>${escapeHtml(artifact.label)}</span>
      <small>${escapeHtml(formatBytes(artifact.size_bytes))}</small>
    </a>
  `;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
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
    <span>LLM：${escapeHtml(payload.enable_llm_extraction ? `${labelLlmProvider(payload.llm_config.provider)} / ${payload.llm_config.model || "未填写模型"}` : "未启用")}</span>
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
