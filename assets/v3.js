"use strict";

const SUMMARY_URL = "data/processed/site-summary.json?v=3.1.0";
const state = {
  summary: null,
  charts: new Map(),
  explorerCache: new Map(),
  explorer: null,
};

const COLORS = {
  navy: "#102d45",
  navyDeep: "#081d2e",
  teal: "#176b70",
  tealLight: "#5ca4a5",
  gold: "#c39138",
  goldLight: "#e1c27e",
  china: "#9b4937",
  chinaLight: "#c47a64",
  other: "#2f7882",
  ink: "#17242c",
  inkSoft: "#59666d",
  line: "#cfc8b8",
  paper: "#fcfaf4",
  white: "#ffffff",
};

const el = (id) => document.getElementById(id);
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const compactMoney = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });
const compactNumber = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const pct = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });

const MINERAL_LABELS = {
  aluminum: "Aluminum",
  antimony: "Antimony",
  bismuth: "Bismuth",
  chromium: "Chromium",
  cobalt: "Cobalt",
  copper: "Copper",
  ferroalloys: "Ferroalloys",
  iron: "Iron",
  manganese: "Manganese",
  minor_metals: "Minor metals",
  mixed_carbonates: "Mixed carbonates",
  mixed_metal_oxides: "Mixed metal oxides",
  natural_graphite: "Natural graphite",
  nickel: "Nickel",
  rare_earths: "Rare-earth proxy basket",
  tantalum: "Tantalum",
  tin: "Tin",
  tungsten: "Tungsten",
  uranium_thorium: "Uranium and thorium",
  zinc: "Zinc",
};

function finite(value) {
  return Number.isFinite(Number(value)) ? Number(value) : null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function displayMoney(value, compact = false) {
  const parsed = finite(value);
  return parsed === null ? "Not available" : (compact ? compactMoney : money).format(parsed);
}

function displayNumber(value, compact = false) {
  const parsed = finite(value);
  return parsed === null ? "Not available" : (compact ? compactNumber : integer).format(parsed);
}

function displayPercent(value) {
  const parsed = finite(value);
  return parsed === null ? "Not available" : pct.format(parsed);
}

function destroyChart(key) {
  const chart = state.charts.get(key);
  if (chart) chart.destroy();
  state.charts.delete(key);
}

function createChart(key, canvas, config) {
  destroyChart(key);
  const chart = new Chart(canvas, config);
  state.charts.set(key, chart);
  return chart;
}

function baseOptions({ percentAxis = false, stacked = false, dark = false } = {}) {
  const text = dark ? "#dce6e9" : COLORS.inkSoft;
  const grid = dark ? "rgba(255,255,255,.12)" : "rgba(23,36,44,.12)";
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    normalized: true,
    parsing: true,
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: COLORS.navyDeep,
        titleColor: COLORS.white,
        bodyColor: COLORS.white,
        padding: 10,
        callbacks: {},
      },
    },
    scales: {
      x: {
        stacked,
        ticks: { color: text, maxRotation: 0, autoSkip: true, maxTicksLimit: 9, font: { size: 11 } },
        grid: { display: false },
        border: { color: grid },
      },
      y: {
        stacked,
        beginAtZero: true,
        suggestedMax: percentAxis ? 1 : undefined,
        max: percentAxis ? 1 : undefined,
        ticks: {
          color: text,
          font: { size: 11 },
          callback: percentAxis ? (value) => `${Math.round(value * 100)}%` : undefined,
        },
        grid: { color: grid },
        border: { display: false },
      },
    },
  };
}

const revisionLines = {
  id: "revisionLines",
  afterDatasetsDraw(chart, _args, options) {
    if (!options || !Array.isArray(options.years)) return;
    const { ctx, chartArea, scales } = chart;
    const labels = chart.data.labels || [];
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = options.color || "rgba(195,145,56,.45)";
    ctx.setLineDash([3, 4]);
    options.years.forEach((year) => {
      const index = labels.indexOf(year);
      if (index < 0) return;
      const x = scales.x.getPixelForValue(index);
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
    });
    ctx.restore();
  },
};

function configureChartDefaults() {
  if (!window.Chart) throw new Error("Chart.js did not load.");
  Chart.defaults.font.family = 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  Chart.defaults.color = COLORS.inkSoft;
  Chart.defaults.devicePixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  Chart.register(revisionLines);
}

async function getJson(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

function renderHero() {
  const { headline, rare_earth_share_annual: series, disparity } = state.summary;
  el("headlineValue").textContent = displayPercent(headline.value);
  el("headlineYear").textContent = headline.year;
  el("headlineNumerator").textContent = displayMoney(headline.numerator_usd, true);
  el("headlineDenominator").textContent = displayMoney(headline.denominator_usd, true);

  const canvas = el("heroSparkline");
  createChart("hero", canvas, {
    type: "line",
    data: {
      labels: series.map((row) => row.year),
      datasets: [{
        data: series.map((row) => row.share),
        borderColor: COLORS.china,
        backgroundColor: "rgba(155,73,55,.12)",
        borderWidth: 2.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
        spanGaps: false,
        tension: 0.12,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      normalized: true,
      parsing: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => displayPercent(context.raw) } } },
      scales: { x: { display: false }, y: { display: false, min: 0, max: 1 } },
    },
  });

  const annualShares = series.filter((row) => finite(row.share) !== null);
  const start = annualShares.find((row) => row.year === 1993);
  const peak = annualShares.reduce((best, row) => row.share > best.share ? row : best, annualShares[0]);
  const currentYtd = disparity.find((row) => row.year === 2026 && row.ytd_flag === "true");
  const ytdShare = currentYtd.china_value_usd / (currentYtd.china_value_usd + currentYtd.other_selected_value_usd);
  el("startShare").textContent = displayPercent(start?.share);
  el("peakShare").textContent = displayPercent(peak?.share);
  el("peakYear").textContent = `${peak?.year ?? "—"} peak`;
  el("currentYtdShare").textContent = displayPercent(ytdShare);
}

function disparitySelection() {
  return {
    period: el("disparityPeriod").value,
    measure: document.querySelector('input[name="disparityMeasure"]:checked').value,
  };
}

function renderDisparity() {
  const { period, measure } = disparitySelection();
  const ytd = period === "ytd";
  const rows = state.summary.disparity.filter((row) => row.ytd_flag === String(ytd));
  const usable = rows.filter((row) => ytd ? row.year <= 2026 : row.year <= 2025);
  const isValue = measure === "value";
  const chinaKey = isValue ? "china_value_usd" : "china_reported_mass_kg";
  const otherKey = isValue ? "other_selected_value_usd" : "other_selected_reported_mass_kg";
  const unit = isValue ? "USD" : "kg";
  const valueFormatter = isValue ? compactMoney : compactNumber;
  const options = baseOptions({ stacked: true });
  options.plugins.tooltip.callbacks.label = (context) => `${context.dataset.label}: ${valueFormatter.format(context.raw)}`;
  options.plugins.revisionLines = { years: [1996, 2002, 2007, 2012, 2017, 2019, 2022] };
  options.scales.y.ticks.callback = (value) => valueFormatter.format(value);

  createChart("disparity", el("disparityChart"), {
    type: "line",
    data: {
      labels: usable.map((row) => row.year),
      datasets: [
        {
          label: "China",
          data: usable.map((row) => finite(row[chinaKey])),
          borderColor: COLORS.china,
          backgroundColor: "rgba(155,73,55,.72)",
          borderWidth: 1.8,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          stack: "total",
          spanGaps: false,
        },
        {
          label: "Other selected origins",
          data: usable.map((row) => finite(row[otherKey])),
          borderColor: COLORS.other,
          backgroundColor: "rgba(47,120,130,.63)",
          borderWidth: 1.8,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          stack: "total",
          spanGaps: false,
        },
      ],
    },
    options,
  });

  el("disparityKicker").textContent = isValue ? "Customs value · current dollars" : "Compatible reported mass measures · kilograms";
  el("disparityNote").textContent = isValue
    ? "The series sums only the 18 origins selected in the source query. It is not total U.S. imports."
    : "Reported mass combines compatible kilogram measures from separate quantity slots. Suppressed or unmeasured quantities mean this is coverage—not total physical tonnage; HTS 8505 changes measurement regime in 2019.";
  el("disparityChart").setAttribute("aria-label", `${period === "annual" ? "Annual" : "January through April YTD"} ${isValue ? "import value" : "reported mass"} for China and other selected U.S. rare-earth proxy origins, ${usable[0].year} through ${usable.at(-1).year}.`);

  el("disparityTable").querySelector("tbody").innerHTML = usable.map((row) => {
    const china = finite(row[chinaKey]);
    const other = finite(row[otherKey]);
    const share = china !== null && other !== null && china + other > 0 ? china / (china + other) : null;
    const render = isValue ? displayMoney : displayNumber;
    return `<tr><td>${row.year}</td><td>${render(china)}</td><td>${render(other)}</td><td>${displayPercent(share)}</td></tr>`;
  }).join("");
}

function populateShareControls() {
  const select = el("shareMineral");
  const minerals = Object.keys(state.summary.china_share_by_mineral);
  select.innerHTML = minerals.map((mineral) => `<option value="${escapeHtml(mineral)}"${mineral === "rare_earths" ? " selected" : ""}>${escapeHtml(MINERAL_LABELS[mineral] || mineral.replaceAll("_", " "))}</option>`).join("");
}

function renderShare() {
  const mineral = el("shareMineral").value;
  const period = el("sharePeriod").value;
  const rows = state.summary.china_share_by_mineral[mineral]?.[period] || [];
  const label = MINERAL_LABELS[mineral] || mineral.replaceAll("_", " ");
  const options = baseOptions({ percentAxis: true });
  options.plugins.tooltip.callbacks.label = (context) => `${label}: ${displayPercent(context.raw)}`;
  options.plugins.revisionLines = { years: [1996, 2002, 2007, 2012, 2017, 2022] };
  createChart("share", el("shareChart"), {
    type: "line",
    data: {
      labels: rows.map((row) => row.year),
      datasets: [{
        label,
        data: rows.map((row) => finite(row.share)),
        borderColor: COLORS.china,
        backgroundColor: "rgba(155,73,55,.1)",
        borderWidth: 3,
        pointRadius: 1.5,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.08,
        spanGaps: false,
      }],
    },
    options,
  });
  el("shareTitle").textContent = label;
  el("shareChart").setAttribute("aria-label", `China share of selected-origin U.S. ${label} import value, ${period === "annual" ? "annual through 2025" : "January through April YTD through 2026"}.`);
  el("shareTable").querySelector("tbody").innerHTML = rows.map((row) => `<tr><td>${row.year}</td><td>${displayPercent(row.share)}</td><td>${row.share === null ? "Missing denominator" : "Reported"}</td></tr>`).join("");
}

function renderDiversity() {
  const usRows = state.summary.us_non_china_diversification;
  const usOptions = baseOptions({ dark: true });
  usOptions.plugins.tooltip.callbacks.label = (context) => `${context.raw} positive selected suppliers`;
  usOptions.plugins.revisionLines = { years: [1996, 2002, 2007, 2012, 2017, 2022], color: "rgba(225,194,126,.35)" };
  usOptions.scales.y.suggestedMax = 17;
  usOptions.scales.y.ticks.precision = 0;
  createChart("us-diversity", el("usDiversityChart"), {
    type: "line",
    data: {
      labels: usRows.map((row) => row.year),
      datasets: [{
        data: usRows.map((row) => finite(row.non_china_supplier_count)),
        borderColor: COLORS.goldLight,
        backgroundColor: "rgba(225,194,126,.12)",
        borderWidth: 2.3,
        pointRadius: 0,
        fill: true,
        spanGaps: false,
      }],
    },
    options: usOptions,
  });
  el("usDiversityChart").setAttribute("aria-label", "Count of positive non-China suppliers within the 18 selected U.S. import origins, annual 1993 through 2025.");

  const prc = state.summary.prc_supply_origins;
  if (prc.status !== "loaded") {
    el("prcCoverageStatus").textContent = "PRC reporter series: not loaded";
    el("prcBanner").innerHTML = `<p><strong>PRC reporter data unavailable.</strong> ${escapeHtml(prc.message)} The site does not substitute U.S. exports.</p>`;
    return;
  }

  const start = prc.yearly[0];
  const latest = prc.yearly.at(-1);
  el("prcCoverageStatus").textContent = `PRC reporter series: ${prc.coverage[0]}–${prc.coverage[1]}`;
  el("prcBanner").innerHTML = `<p><strong>${start.positive_origin_count} to ${latest.positive_origin_count} positive origins.</strong> China-reporter HS 2846 import records expand from ${start.year} to ${latest.year}. The source mix changes sharply, but HHI moves from ${decimal.format(start.hhi_value_0_1)} to ${decimal.format(latest.hhi_value_0_1)}—a wider origin set did not automatically mean lower concentration.</p>`;

  const prcOptions = baseOptions({ dark: true });
  prcOptions.plugins.tooltip.callbacks.label = (context) => `${context.raw} positive origins`;
  prcOptions.plugins.revisionLines = { years: [1996, 2000, 2002, 2007, 2012, 2017, 2022], color: "rgba(225,194,126,.35)" };
  prcOptions.scales.y.ticks.precision = 0;
  createChart("prc-origins", el("prcOriginsChart"), {
    type: "line",
    data: {
      labels: prc.yearly.map((row) => row.year),
      datasets: [{
        data: prc.yearly.map((row) => row.positive_origin_count),
        borderColor: COLORS.chinaLight,
        backgroundColor: "rgba(196,122,100,.13)",
        borderWidth: 2.3,
        pointRadius: 0,
        fill: true,
        spanGaps: false,
      }],
    },
    options: prcOptions,
  });
  el("prcOriginsChart").setAttribute("aria-label", `Count of positive reported origins for China imports of HS 2846, ${prc.coverage[0]} through ${prc.coverage[1]}.`);
  renderSupplierCards();
  renderTopOrigins();
}

function renderSupplierCards() {
  const prc = state.summary.prc_supply_origins;
  if (prc.status !== "loaded") return;
  const usByIso = new Map(state.summary.us_selected_supplier_series.partners.map((row) => [row.iso3, row]));
  const prcByIso = new Map(prc.selected_partners.map((row) => [row.iso3, row]));
  const grid = el("supplierCards");
  grid.innerHTML = prc.selected_partners.map((partner) => {
    const latest = partner.annual.at(-1);
    const usLatest = usByIso.get(partner.iso3)?.annual.find((row) => row.year === 2024);
    return `<article class="supplier-card"><h4>${escapeHtml(partner.name)}</h4><div class="canvas-shell"><canvas id="supplier-${partner.iso3}" role="img"></canvas></div><dl><div><dt>U.S. view · 2024</dt><dd>${displayPercent(usLatest?.share)}</dd></div><div><dt>China view · 2024</dt><dd>${displayPercent(latest?.share)}</dd></div></dl></article>`;
  }).join("");

  prc.selected_partners.forEach((partner) => {
    const us = usByIso.get(partner.iso3)?.annual.filter((row) => row.year <= 2024) || [];
    const prcRows = prcByIso.get(partner.iso3)?.annual || [];
    const years = prcRows.map((row) => row.year);
    const usMap = new Map(us.map((row) => [row.year, row.share]));
    const options = baseOptions({ percentAxis: true, dark: true });
    options.plugins.tooltip.callbacks.label = (context) => `${context.dataset.label}: ${displayPercent(context.raw)}`;
    options.scales.x.ticks.maxTicksLimit = 5;
    const key = `supplier-${partner.iso3}`;
    createChart(key, el(key), {
      type: "line",
      data: {
        labels: years,
        datasets: [
          { label: "U.S. reporter", data: years.map((year) => finite(usMap.get(year))), borderColor: COLORS.goldLight, borderWidth: 1.8, pointRadius: 0, spanGaps: false },
          { label: "China reporter", data: prcRows.map((row) => finite(row.share)), borderColor: COLORS.chinaLight, borderDash: [5, 3], borderWidth: 2.2, pointRadius: 0, spanGaps: false },
        ],
      },
      options,
    });
    el(key).setAttribute("aria-label", `${partner.name} share in the U.S. selected-origin rare-earth proxy view and the China all-origin HS 2846 view, 1993 through 2024.`);
  });
}

function renderTopOrigins() {
  const prc = state.summary.prc_supply_origins;
  const latest = prc.yearly.at(-1);
  const first = prc.yearly[0];
  const ledger = el("topOriginsLedger");
  ledger.innerHTML = `<h3>${latest.year}: the record identifies the sources</h3><p>HS 2846 import value rose from ${displayMoney(first.world_value_usd, true)} in ${first.year} to ${displayMoney(latest.world_value_usd, true)} in ${latest.year}. The latest leading origins are determined from the all-partner data, not a hand-picked list.</p><div class="top-origin-grid">${latest.top_origins.slice(0, 4).map((origin) => `<div><strong>${displayPercent(origin.share)}</strong><span>${escapeHtml(origin.name)} · ${displayMoney(origin.value_usd, true)}</span></div>`).join("")}</div><p class="chart-note">China changes from Special to General trade-system reporting in 2000. HS revision bands occur in 1996, 2002, 2007, 2012, 2017, and 2022. China has no comparable annual Comtrade record for 2025–2026 in this frozen build.</p>`;
}

function populateExplorer() {
  const select = el("explorerHts");
  select.innerHTML = state.summary.explorer_index.map((row) => `<option value="${row.hts}"${row.hts === "2846" ? " selected" : ""}>${row.hts} · ${escapeHtml(row.label)}</option>`).join("");
  const params = new URLSearchParams(window.location.search);
  const hts = params.get("hts");
  if (hts && state.summary.explorer_index.some((row) => row.hts === hts)) select.value = hts;
  for (const [id, key] of [["explorerFlow", "flow"], ["explorerPeriod", "period"], ["explorerMeasure", "measure"]]) {
    const value = params.get(key);
    if (value && [...el(id).options].some((option) => option.value === value)) el(id).value = value;
  }
  const year = Number(params.get("year"));
  if (Number.isInteger(year) && year >= 1993 && year <= 2026) el("explorerYear").value = year;
  updateExplorerYearRange();
  loadExplorer();
}

async function explorerData(hts) {
  if (!state.explorerCache.has(hts)) {
    state.explorerCache.set(hts, getJson(`data/processed/explorer/${hts}.json?v=3.1.0`));
  }
  return state.explorerCache.get(hts);
}

function updateExplorerYearRange() {
  const max = el("explorerPeriod").value === "ytd" ? 2026 : 2025;
  const input = el("explorerYear");
  input.max = max;
  if (Number(input.value) > max) input.value = max;
  el("explorerYearOutput").textContent = input.value;
}

async function loadExplorer() {
  const hts = el("explorerHts").value;
  el("explorerTitle").textContent = `HTS ${hts}`;
  el("explorerMeta").textContent = "Loading compact record shard…";
  try {
    state.explorer = await explorerData(hts);
    renderExplorer();
  } catch (error) {
    el("explorerMeta").textContent = "Record shard unavailable";
    el("explorerScope").textContent = error.message;
  }
}

function explorerRows() {
  if (!state.explorer) return [];
  const flow = el("explorerFlow").value;
  const ytd = el("explorerPeriod").value === "ytd";
  return state.explorer.rows.filter((row) => row[0] === flow && row[4] === ytd);
}

function aggregateExplorer(rows, measure, targetYear = null) {
  const measureIndex = { value_usd: 5, reported_mass_kg: 6, unit_value_usd_per_reported_kg: 7 }[measure];
  const groups = new Map();
  rows.filter((row) => targetYear === null || row[3] === targetYear).forEach((row) => {
    const key = targetYear === null ? row[3] : row[2];
    if (!groups.has(key)) groups.set(key, { value: 0, numerator: 0, denominator: 0, seen: false });
    const group = groups.get(key);
    if (measure === "unit_value_usd_per_reported_kg") {
      const unitValue = finite(row[7]);
      const mass = finite(row[9]);
      if (unitValue !== null && mass !== null && mass > 0) {
        group.numerator += unitValue * mass;
        group.denominator += mass;
        group.seen = true;
      }
    } else {
      const value = finite(row[measureIndex]);
      if (value !== null) {
        group.value += value;
        group.seen = true;
      }
    }
  });
  return new Map([...groups].map(([key, group]) => [key, group.seen ? (measure === "unit_value_usd_per_reported_kg" ? (group.denominator ? group.numerator / group.denominator : null) : group.value) : null]));
}

function renderExplorer() {
  const data = state.explorer;
  const rows = explorerRows();
  const measure = el("explorerMeasure").value;
  const year = Number(el("explorerYear").value);
  const flowLabel = el("explorerFlow").selectedOptions[0].textContent;
  const periodLabel = el("explorerPeriod").value === "ytd" ? "Jan–Apr YTD" : "full year";
  el("explorerTitle").textContent = `HTS ${data.hts} · ${data.label}`;
  el("explorerMeta").textContent = `${flowLabel} · ${periodLabel}`;
  el("explorerStage").textContent = data.processing_stage;
  el("explorerScope").textContent = `${data.scope_note} ${data.quantity_note}`;
  el("rankingTitle").textContent = `Leading partners, ${year}`;

  const years = [...new Set(rows.map((row) => row[3]))].filter((value) => el("explorerPeriod").value === "ytd" || value <= 2025).sort((a, b) => a - b);
  const total = aggregateExplorer(rows, measure);
  const china = aggregateExplorer(rows.filter((row) => row[2] === "CHN"), measure);
  const measureLabels = {
    value_usd: "Value",
    reported_mass_kg: "Reported mass",
    unit_value_usd_per_reported_kg: "Unit value",
  };
  const formatter = measure === "value_usd" ? compactMoney : compactNumber;
  const options = baseOptions();
  options.plugins.tooltip.callbacks.label = (context) => `${context.dataset.label}: ${formatter.format(context.raw)}`;
  options.plugins.revisionLines = { years: data.hts === "8505" ? [1996, 2002, 2007, 2012, 2017, 2019, 2022] : [1996, 2002, 2007, 2012, 2017, 2022] };
  options.scales.y.ticks.callback = (value) => formatter.format(value);
  createChart("explorer-timeline", el("explorerTimeline"), {
    type: "line",
    data: {
      labels: years,
      datasets: [
        { label: "Selected-origin total", data: years.map((value) => total.get(value)), borderColor: COLORS.teal, borderWidth: 2.6, pointRadius: 0, spanGaps: false },
        { label: "China", data: years.map((value) => china.get(value)), borderColor: COLORS.china, borderWidth: 2.2, borderDash: [6, 3], pointRadius: 0, spanGaps: false },
      ],
    },
    options,
  });
  el("explorerTimeline").setAttribute("aria-label", `${measureLabels[measure]} for HTS ${data.hts}, China and the selected-origin total, ${years[0]} through ${years.at(-1)}.`);

  const partnerValues = aggregateExplorer(rows, measure, year);
  const partnerName = new Map(rows.map((row) => [row[2], row[1]]));
  const ranking = [...partnerValues]
    .filter(([, value]) => finite(value) !== null)
    .map(([iso, value]) => ({ iso, name: partnerName.get(iso), value }))
    .sort((a, b) => b.value - a.value);
  const top = ranking.slice(0, 10);
  const barOptions = baseOptions();
  barOptions.indexAxis = "y";
  barOptions.interaction.mode = "nearest";
  barOptions.scales.x.ticks.callback = (value) => formatter.format(value);
  barOptions.scales.y.ticks.autoSkip = false;
  barOptions.plugins.tooltip.callbacks.label = (context) => `${measureLabels[measure]}: ${formatter.format(context.raw)}`;
  createChart("explorer-partners", el("explorerPartners"), {
    type: "bar",
    data: {
      labels: top.map((row) => row.name),
      datasets: [{ data: top.map((row) => row.value), backgroundColor: top.map((row) => row.iso === "CHN" ? COLORS.china : COLORS.teal), borderWidth: 0 }],
    },
    options: barOptions,
  });
  el("explorerPartners").setAttribute("aria-label", `Leading reported partners for HTS ${data.hts} by ${measureLabels[measure].toLowerCase()} in ${year}.`);

  const yearRows = rows.filter((row) => row[3] === year).sort((a, b) => (finite(b[5]) || 0) - (finite(a[5]) || 0));
  el("explorerTable").querySelector("tbody").innerHTML = yearRows.map((row) => `<tr><td>${escapeHtml(row[1])}</td><td>${displayMoney(row[5])}</td><td>${displayNumber(row[6])}</td><td>${finite(row[7]) === null ? "Not available" : money.format(row[7])}</td><td>${row[8] === "quantity_incomplete" ? "Quantity incomplete" : "Reported"}</td></tr>`).join("");
  updateExplorerUrl();
}

function updateExplorerUrl() {
  const params = new URLSearchParams(window.location.search);
  params.set("hts", el("explorerHts").value);
  params.set("flow", el("explorerFlow").value);
  params.set("period", el("explorerPeriod").value);
  params.set("measure", el("explorerMeasure").value);
  params.set("year", el("explorerYear").value);
  history.replaceState(null, "", `${window.location.pathname}?${params.toString()}${window.location.hash}`);
}

function downloadExplorerCsv() {
  if (!state.explorer) return;
  const columns = state.explorer.columns;
  const rows = explorerRows();
  const quote = (value) => {
    if (value === null || value === undefined) return "";
    const text = String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const content = [columns, ...rows].map((row) => row.map(quote).join(",")).join("\n") + "\n";
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `hts-${state.explorer.hts}-${el("explorerFlow").value}-${el("explorerPeriod").value}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderProvenance() {
  const labels = {
    imports_for_consumption: "U.S. imports",
    domestic_exports: "U.S. domestic exports",
    china_reported_imports: "China-reported imports",
  };
  el("provenanceTable").querySelector("tbody").innerHTML = state.summary.sources.map((source) => `<tr><td>${labels[source.flow] || escapeHtml(source.flow)}</td><td><a href="${escapeHtml(source.file)}">${escapeHtml(source.file.split("/").at(-1))}</a></td><td title="${source.sha256}">${source.sha256}</td></tr>`).join("");
}

function bindEvents() {
  el("disparityPeriod").addEventListener("change", renderDisparity);
  document.querySelectorAll('input[name="disparityMeasure"]').forEach((input) => input.addEventListener("change", renderDisparity));
  el("shareMineral").addEventListener("change", renderShare);
  el("sharePeriod").addEventListener("change", renderShare);
  el("explorerHts").addEventListener("change", loadExplorer);
  ["explorerFlow", "explorerMeasure"].forEach((id) => el(id).addEventListener("change", renderExplorer));
  el("explorerPeriod").addEventListener("change", () => { updateExplorerYearRange(); renderExplorer(); });
  el("explorerYear").addEventListener("input", () => { el("explorerYearOutput").textContent = el("explorerYear").value; renderExplorer(); });
  el("downloadExplorer").addEventListener("click", downloadExplorerCsv);
}

async function init() {
  configureChartDefaults();
  try {
    state.summary = await getJson(SUMMARY_URL);
    renderHero();
    renderDisparity();
    populateShareControls();
    renderShare();
    renderDiversity();
    populateExplorer();
    renderProvenance();
    bindEvents();
  } catch (error) {
    console.error(error);
    el("headlineValue").textContent = "Data unavailable";
    el("prcCoverageStatus").textContent = "Statistical record failed to load";
    el("prcBanner").innerHTML = `<p><strong>Local data could not be loaded.</strong> ${escapeHtml(error.message)}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", init);
