"use strict";

const DATA_URL = "data/v3/dataweb-series.json?v=3.0.0";
const REGISTRY_URL = "data/v3/dataset-registry.json?v=3.0.0";

const state = {
  data: null,
  registry: null,
  material: "2846",
  period: "comparable_jan_apr_ytd",
  year: 2026,
  lineGeometry: null,
  resizeTimer: null,
};

const el = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const compactUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

const exactUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function material() {
  return state.data.materials.find((row) => row.hts4 === state.material);
}

function series(flow, partnerId) {
  return state.data.series.find(
    (row) => row.flow === flow && row.partner_country_id === partnerId && row.hts4 === state.material,
  );
}

function point(flow, partnerId, year = state.year) {
  const row = series(flow, partnerId);
  if (!row) return { status: "not-reported", value: null, row: null };
  const index = state.data.years.indexOf(year);
  if (index < 0) return { status: "outside-series", value: null, row };
  if (row.suppressed[state.period][index]) return { status: "suppressed", value: null, row };
  const value = row[state.period][index];
  if (value === null || value === undefined) return { status: "source-blank", value: null, row };
  return { status: value === 0 ? "reported-zero" : "reported", value, row };
}

function pointLabel(result, { compact = false } = {}) {
  if (result.status === "suppressed") return "Suppressed";
  if (result.status === "source-blank") return "Source blank";
  if (result.status === "not-reported") return "Not reported in export";
  if (result.status === "outside-series") return "Outside series";
  return compact ? compactUsd.format(result.value) : exactUsd.format(result.value);
}

function periodLabel(year = state.year) {
  if (state.period === "comparable_jan_apr_ytd") return "January–April YTD";
  return year === 2026 ? "January–April YTD" : "full year";
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(280, rect.width);
  const height = Math.max(280, rect.height);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const context = canvas.getContext("2d");
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function tickValue(max, tickIndex, tickCount) {
  return (max * tickIndex) / tickCount;
}

function drawLineChart() {
  const canvas = el("lineChart");
  const { context: ctx, width, height } = setupCanvas(canvas);
  const years = state.data.years;
  const importsRow = series("imports_for_consumption", "chn");
  const exportsRow = series("domestic_exports", "chn");
  const valuesFor = (row) => years.map((year, index) => {
    if (!row || row.suppressed[state.period][index]) return null;
    return row[state.period][index];
  });
  const importValues = valuesFor(importsRow);
  const exportValues = valuesFor(exportsRow);
  const numeric = [...importValues, ...exportValues].filter((value) => Number.isFinite(value));
  const max = Math.max(...numeric, 1);
  const margin = { top: 24, right: 18, bottom: 42, left: width < 520 ? 58 : 72 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const x = (index) => margin.left + (index / (years.length - 1)) * plotWidth;
  const y = (value) => margin.top + plotHeight - (value / max) * plotHeight;
  const grid = css("--line");
  const muted = css("--ink-soft");
  const paper = css("--paper-strong");

  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, width, height);
  ctx.lineWidth = 1;
  ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
  ctx.textBaseline = "middle";
  ctx.textAlign = "right";

  const tickCount = 4;
  for (let tick = 0; tick <= tickCount; tick += 1) {
    const value = tickValue(max, tick, tickCount);
    const py = y(value);
    ctx.strokeStyle = grid;
    ctx.beginPath();
    ctx.moveTo(margin.left, py);
    ctx.lineTo(width - margin.right, py);
    ctx.stroke();
    ctx.fillStyle = muted;
    ctx.fillText(compactUsd.format(value), margin.left - 9, py);
  }

  const yearTicks = [1993, 2000, 2010, 2020, 2026];
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  yearTicks.forEach((year) => {
    const index = years.indexOf(year);
    ctx.fillStyle = muted;
    ctx.fillText(String(year), x(index), height - margin.bottom + 13);
  });

  function plot(values, color) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.6;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    let drawing = false;
    ctx.beginPath();
    values.forEach((value, index) => {
      const methodologyBreak = state.period === "annual_or_current_ytd" && index === years.length - 1;
      if (!Number.isFinite(value) || methodologyBreak) {
        if (drawing) ctx.stroke();
        ctx.beginPath();
        drawing = false;
      }
      if (!Number.isFinite(value)) return;
      const px = x(index);
      const py = y(value);
      if (!drawing) {
        ctx.moveTo(px, py);
        drawing = true;
      } else {
        ctx.lineTo(px, py);
      }
    });
    if (drawing) ctx.stroke();

    values.forEach((value, index) => {
      if (!Number.isFinite(value)) return;
      if (index === state.data.years.indexOf(state.year) || index === years.length - 1) {
        ctx.beginPath();
        ctx.arc(x(index), y(value), index === state.data.years.indexOf(state.year) ? 4.5 : 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = paper;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });
  }

  plot(importValues, css("--us"));
  plot(exportValues, css("--outbound"));

  if (state.period === "annual_or_current_ytd") {
    const breakX = x(years.length - 1) - plotWidth / (years.length - 1) / 2;
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = css("--gold");
    ctx.beginPath();
    ctx.moveTo(breakX, margin.top);
    ctx.lineTo(breakX, margin.top + plotHeight);
    ctx.stroke();
    ctx.restore();
  }

  const label = `${material().label}. U.S. imports from China and U.S. domestic exports to China, ${periodLabel()} values from 1993 through 2026.`;
  canvas.setAttribute("aria-label", label);
  state.lineGeometry = { years, importValues, exportValues, x, margin, plotWidth, width };
}

function drawBarChart() {
  const canvas = el("barChart");
  const { context: ctx, width, height } = setupCanvas(canvas);
  const rows = state.data.partners
    .map((partner) => ({ partner, result: point("imports_for_consumption", partner.id) }))
    .filter((entry) => entry.result.status === "reported" || entry.result.status === "reported-zero")
    .sort((a, b) => b.result.value - a.result.value)
    .slice(0, 8);
  const max = Math.max(...rows.map((row) => row.result.value), 1);
  const margin = { top: 14, right: width < 430 ? 70 : 96, bottom: 14, left: width < 430 ? 88 : 112 };
  const plotWidth = width - margin.left - margin.right;
  const rowHeight = (height - margin.top - margin.bottom) / Math.max(rows.length, 1);
  const paper = css("--paper-strong");
  const muted = css("--ink-soft");
  const line = css("--line");

  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, width, height);
  ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
  ctx.textBaseline = "middle";

  if (!rows.length) {
    ctx.fillStyle = muted;
    ctx.textAlign = "center";
    ctx.fillText("No reported values for this selection", width / 2, height / 2);
    canvas.setAttribute("aria-label", `No reported U.S. import values for ${material().label} in ${state.year}.`);
    return;
  }

  rows.forEach((row, index) => {
    const centerY = margin.top + rowHeight * index + rowHeight / 2;
    const barHeight = Math.min(24, rowHeight * 0.54);
    const barWidth = (row.result.value / max) * plotWidth;
    ctx.fillStyle = line;
    ctx.fillRect(margin.left, centerY - barHeight / 2, plotWidth, barHeight);
    ctx.fillStyle = row.partner.id === "chn" ? css("--prc") : css("--us");
    ctx.fillRect(margin.left, centerY - barHeight / 2, barWidth, barHeight);
    ctx.fillStyle = row.partner.id === "chn" ? css("--prc") : css("--ink-deep");
    ctx.textAlign = "right";
    ctx.fillText(row.partner.name, margin.left - 9, centerY);
    ctx.fillStyle = muted;
    ctx.textAlign = "left";
    ctx.fillText(compactUsd.format(row.result.value), margin.left + barWidth + 7, centerY);
  });

  canvas.setAttribute(
    "aria-label",
    `Top reported origins among the 18 partners in the U.S. import query for ${material().label}, ${state.year} ${periodLabel()}.`,
  );
}

function populateMetrics() {
  const coverage = state.data.coverage;
  const cards = [
    [state.data.years.length, "years", "1993 through 2026"],
    [coverage.selected_partner_count, "selected partners", "China and Hong Kong separate"],
    [coverage.commodity_count, "HTS4 categories", "Rare earths and other strategic products"],
    [integer.format(coverage.series_count), "normalized series", "Two frozen official workbooks"],
  ];
  el("metricsStrip").innerHTML = cards.map(([value, label, note]) => `
    <div class="scope-metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span><small>${escapeHtml(note)}</small></div>
  `).join("");
}

function populateMaterials() {
  const select = el("materialSelect");
  const grouped = new Map();
  state.data.materials.forEach((row) => {
    if (!grouped.has(row.group)) grouped.set(row.group, []);
    grouped.get(row.group).push(row);
  });
  select.innerHTML = [...grouped.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([group, rows]) => `
      <optgroup label="${escapeHtml(group)}">
        ${rows.sort((a, b) => a.label.localeCompare(b.label)).map((row) => `
          <option value="${row.hts4}">${row.hts4} · ${escapeHtml(row.label)} — ${escapeHtml(row.proxy_type)}</option>
        `).join("")}
      </optgroup>
    `).join("");
  if (!state.data.materials.some((row) => row.hts4 === state.material)) state.material = state.data.materials[0].hts4;
  select.value = state.material;
  select.disabled = false;
  el("periodSelect").disabled = false;
  el("yearSelect").disabled = false;
}

function renderKpis() {
  const imports = point("imports_for_consumption", "chn");
  const exports = point("domestic_exports", "chn");
  el("importKpi").textContent = pointLabel(imports, { compact: true });
  el("exportKpi").textContent = pointLabel(exports, { compact: true });
  el("importKpi").title = pointLabel(imports);
  el("exportKpi").title = pointLabel(exports);
  el("importKpiNote").textContent = `${state.year} ${periodLabel()} · reported origin · customs value`;
  el("exportKpiNote").textContent = `${state.year} ${periodLabel()} · reported destination · F.A.S. value`;
}

function renderLineTable() {
  const tbody = el("lineDataTable").querySelector("tbody");
  tbody.innerHTML = state.data.years.map((year) => {
    const imports = point("imports_for_consumption", "chn", year);
    const exports = point("domestic_exports", "chn", year);
    return `<tr>
      <th scope="row">${year}</th>
      <td class="numeric">${escapeHtml(pointLabel(imports))}</td>
      <td class="numeric">${escapeHtml(pointLabel(exports))}</td>
      <td>${escapeHtml(periodLabel(year))}</td>
    </tr>`;
  }).join("");
}

function valueCell(result) {
  if (["reported", "reported-zero"].includes(result.status)) {
    return `<td class="numeric">${escapeHtml(exactUsd.format(result.value))}</td>`;
  }
  return `<td><span class="cell-status">${escapeHtml(pointLabel(result))}</span></td>`;
}

function renderPartnerTable() {
  const rows = state.data.partners.map((partner) => ({
    partner,
    imports: point("imports_for_consumption", partner.id),
    exports: point("domestic_exports", partner.id),
  }));
  rows.sort((a, b) => {
    const av = Number.isFinite(a.imports.value) ? a.imports.value : -1;
    const bv = Number.isFinite(b.imports.value) ? b.imports.value : -1;
    return bv - av || a.partner.name.localeCompare(b.partner.name);
  });
  el("partnerTable").querySelector("tbody").innerHTML = rows.map(({ partner, imports, exports }) => `
    <tr class="${partner.id === "chn" ? "china-row" : ""}">
      <th scope="row">${escapeHtml(partner.name)}${partner.id === "chn" ? " · PRC" : ""}</th>
      ${valueCell(imports)}
      ${valueCell(exports)}
      <td>${partner.id === "chn" ? "Origin / destination; PRC reporter not loaded" : "Origin / destination"}</td>
    </tr>
  `).join("");
}

function renderSources() {
  el("sourceGrid").innerHTML = state.registry.sources.map((source) => {
    const flow = source.flow === "imports_for_consumption" ? "Imports for consumption" : "Domestic exports";
    const valueBasis = source.value_basis === "customs_value_usd" ? "Customs value" : "F.A.S. value";
    return `<article class="source-card">
      <p class="source-agency">${escapeHtml(source.agency)} · official USG statistical republication</p>
      <h3>${escapeHtml(flow)}, 1993–2026</h3>
      <div class="source-meta">
        <div><span>Downloaded</span><strong>${escapeHtml(source.download_date)}</strong></div>
        <div><span>Value basis</span><strong>${escapeHtml(valueBasis)}</strong></div>
        <div><span>Built series</span><strong>${integer.format(source.normalized_series_count)}</strong></div>
      </div>
      <p class="source-hash"><strong>SHA-256</strong><br>${escapeHtml(source.sha256)}</p>
      <div class="source-actions">
        <a href="${escapeHtml(source.local_file)}" download>Download unchanged XLSX</a>
        <a href="${escapeHtml(source.source_url)}" target="_blank" rel="noopener">Open DataWeb ↗</a>
      </div>
    </article>`;
  }).join("");
}

function renderSelection() {
  const selected = material();
  const period = state.data.periods[state.period];
  el("yearOutput").textContent = state.year;
  el("barYearPill").textContent = `${state.year} ${periodLabel()}`;
  el("lineChartTitle").textContent = `${selected.label}: U.S.-reported flows with China`;
  el("barChartTitle").textContent = `${selected.label}: selected U.S. import origins`;
  el("selectionBanner").innerHTML = `<strong>HTS ${escapeHtml(selected.hts4)}</strong> · ${escapeHtml(selected.label)} · ${escapeHtml(selected.proxy_type)} · ${escapeHtml(period.label)} · Focus: ${state.year}`;
  el("lineChartNote").textContent = state.period === "comparable_jan_apr_ytd"
    ? "Nominal U.S. dollars. Every point covers January–April, preserving period comparability."
    : "Nominal U.S. dollars. 1993–2025 are full years; 2026 covers January–April and is separated by a methodology break. It is not directly comparable with the prior full-year points.";
  el("tableScope").textContent = `${state.year} ${periodLabel()} · HTS ${selected.hts4} · ${selected.proxy_type}.`;
  renderKpis();
  drawLineChart();
  drawBarChart();
  renderLineTable();
  renderPartnerTable();
  updateUrl();
}

function updateUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("commodity", state.material);
  url.searchParams.set("period", state.period === "comparable_jan_apr_ytd" ? "ytd" : "mixed");
  url.searchParams.set("year", String(state.year));
  history.replaceState(null, "", `${url.pathname}?${url.searchParams.toString()}${url.hash}`);
}

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const commodity = params.get("commodity");
  const year = Number(params.get("year"));
  const period = params.get("period");
  if (commodity && /^\d{4}$/.test(commodity)) state.material = commodity;
  if (Number.isInteger(year) && year >= 1993 && year <= 2026) state.year = year;
  if (period === "mixed") state.period = "annual_or_current_ytd";
  if (period === "ytd") state.period = "comparable_jan_apr_ytd";
}

function bindExplorer() {
  el("materialSelect").addEventListener("change", (event) => {
    state.material = event.target.value;
    renderSelection();
  });
  el("periodSelect").addEventListener("change", (event) => {
    state.period = event.target.value;
    renderSelection();
  });
  let frame;
  el("yearSelect").addEventListener("input", (event) => {
    state.year = Number(event.target.value);
    el("yearOutput").textContent = state.year;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(renderSelection);
  });
}

function bindLineTooltip() {
  const canvas = el("lineChart");
  const tooltip = el("lineTooltip");
  canvas.addEventListener("pointermove", (event) => {
    if (!state.lineGeometry) return;
    const rect = canvas.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const { years, importValues, exportValues, margin, plotWidth } = state.lineGeometry;
    const ratio = Math.max(0, Math.min(1, (localX - margin.left) / plotWidth));
    const index = Math.round(ratio * (years.length - 1));
    const imports = importValues[index];
    const exports = exportValues[index];
    tooltip.innerHTML = `<strong>${years[index]} · ${escapeHtml(periodLabel(years[index]))}</strong><br>Imports: ${Number.isFinite(imports) ? escapeHtml(exactUsd.format(imports)) : "not reported"}<br>Domestic exports: ${Number.isFinite(exports) ? escapeHtml(exactUsd.format(exports)) : "not reported"}`;
    tooltip.hidden = false;
    const left = Math.min(rect.width - 225, Math.max(8, localX + 12));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${Math.max(8, event.clientY - rect.top - 72)}px`;
  });
  canvas.addEventListener("pointerleave", () => {
    tooltip.hidden = true;
  });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  el("themeToggle").setAttribute("aria-pressed", String(theme === "dark"));
  localStorage.setItem("critical-minerals-v3-theme", theme);
  if (state.data) {
    drawLineChart();
    drawBarChart();
  }
}

function bindShell() {
  const savedTheme = localStorage.getItem("critical-minerals-v3-theme");
  const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  applyTheme(savedTheme || preferred);
  el("themeToggle").addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
  el("navToggle").addEventListener("click", () => {
    const open = el("primaryNav").classList.toggle("is-open");
    el("navToggle").setAttribute("aria-expanded", String(open));
  });
  el("primaryNav").addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      el("primaryNav").classList.remove("is-open");
      el("navToggle").setAttribute("aria-expanded", "false");
    }
  });
  window.addEventListener("resize", () => {
    clearTimeout(state.resizeTimer);
    state.resizeTimer = setTimeout(() => {
      if (state.data) {
        drawLineChart();
        drawBarChart();
      }
    }, 120);
  });
}

function showError(error) {
  console.error(error);
  const banner = el("selectionBanner");
  banner.classList.add("error-banner");
  banner.textContent = "The statistical files could not be loaded. The unchanged XLSX workbooks remain available in the repository source register.";
  el("metricsStrip").innerHTML = `<div class="scope-metric" style="grid-column:1/-1"><strong>Data unavailable</strong><span>Static interface loaded; statistical JSON did not</span><small>${escapeHtml(error.message)}</small></div>`;
}

async function init() {
  bindShell();
  readUrl();
  const [dataResponse, registryResponse] = await Promise.all([fetch(DATA_URL), fetch(REGISTRY_URL)]);
  if (!dataResponse.ok) throw new Error(`Data request failed with ${dataResponse.status}`);
  if (!registryResponse.ok) throw new Error(`Registry request failed with ${registryResponse.status}`);
  state.data = await dataResponse.json();
  state.registry = await registryResponse.json();
  populateMetrics();
  populateMaterials();
  el("periodSelect").value = state.period;
  el("yearSelect").value = String(state.year);
  renderSources();
  bindExplorer();
  bindLineTooltip();
  renderSelection();
}

init().catch(showError);
