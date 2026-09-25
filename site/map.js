const L = {
  en: {
    indicator: "Indicator", view: "View", level: "Level", change: "Change", census: "Census", population: "Population",
    s_all: "All", s_urban: "Urban", s_rural: "Rural", s_male: "Men", s_female: "Women",
    find: "Find a commune",
    nodata: "No data", decrease: "decrease", increase: "increase", rural: "Rural", urban: "Urban",
    caveat: "HCP's commune boundaries, from its census cartography: coded by 2014 commune and served by its RGPH 2024 results platform. The communes are the same in 2014 and 2024. 2004 values are shown on these boundaries; where communes were reorganised in 2008-2009, a 2004 value may cover a different territory.",
    noncomp: "Definitions differ between censuses; read the change with care.",
    point: "seed point", allind: "All indicators",
    city: "city (arrondissements combined)", communes: "communes",
  },
  fr: {
    indicator: "Indicateur", view: "Affichage", level: "Niveau", change: "Évolution", census: "Recensement", population: "Population",
    // HCP's own terms for the breakdowns (RGPH 2024 results platform)
    s_all: "Ensemble", s_urban: "Urbain", s_rural: "Rural", s_male: "Masculin", s_female: "Féminin",
    find: "Trouver une commune",
    nodata: "Pas de donnée", decrease: "baisse", increase: "hausse", rural: "Rurale", urban: "Urbaine",
    point: "point d'ancrage", allind: "Tous les indicateurs", communes: "communes",
  },
  ar: {
    indicator: "المؤشر", view: "العرض", level: "المستوى", change: "التطور", census: "الإحصاء", population: "السكان",
    s_all: "المجموع", s_urban: "الوسط الحضري", s_rural: "الوسط القروي", s_male: "الذكور", s_female: "الإناث",
    find: "البحث عن جماعة",
    nodata: "لا توجد معطيات", decrease: "انخفاض", increase: "ارتفاع", rural: "قروية", urban: "حضرية",
    point: "نقطة الارتكاز", allind: "جميع المؤشرات", communes: "جماعة",
  },
};
// Colour-blind-safe ramps: viridis (more = lighter) and ColorBrewer PuOr (decrease purple, increase orange).
const SEQ = ["#440154", "#443983", "#31688e", "#21918c", "#35b779", "#90d743", "#fde725"];
const DIV = ["#542788", "#998ec3", "#d8daeb", "#f7f7f7", "#fee0b6", "#f1a340", "#b35806"];
const FLAG = ["#90d743", "#31688e"];
// Orientation labels: [English name, map unit (French and Arabic names come from HCP), lon, lat, tier (1 always, 2 from zoom 6,
// 3 from zoom 7.5), label side]. Coastal labels sit over the sea.
const CITIES = [
  ["Rabat", "04.421.01.", -6.8417, 34.0209, 1, "w"], ["Casablanca", "06.141.01.", -7.5898, 33.5731, 1, "w"],
  ["Fez", "03.231.01.", -5.0003, 34.0331, 1], ["Marrakesh", "07.351.01.", -7.9811, 31.6295, 1],
  ["Tangier", "01.511.01.", -5.834, 35.7595, 1, "w"], ["Agadir", "09.001.01.01.", -9.5981, 30.4278, 1, "w"],
  ["Oujda", "02.411.01.23.", -1.9086, 34.6814, 1], ["Laâyoune", "11.321.01.03.", -13.1625, 27.1253, 1, "w"],
  ["Dakhla", "12.391.01.01.", -15.958, 23.6848, 1, "w"], ["Meknes", "03.061.01.01.", -5.5473, 33.8935, 2],
  ["Kenitra", "04.281.01.01.", -6.5802, 34.261, 2, "w"], ["Tetouan", "01.571.01.11.", -5.3626, 35.5889, 2],
  ["Nador", "02.381.01.05.", -2.9335, 35.1681, 2], ["Beni Mellal", "05.091.01.01.", -6.3498, 32.3373, 2],
  ["Errachidia", "08.201.01.05.", -4.4245, 31.9314, 2], ["Ouarzazate", "08.401.01.07.", -6.8934, 30.9189, 2],
  ["Guelmim", "10.261.01.03.", -10.0574, 28.987, 2], ["Safi", "07.431.01.03.", -9.2372, 32.2994, 2, "w"],
  ["El Jadida", "06.181.01.03.", -8.5007, 33.2316, 2, "w"], ["Al Hoceima", "01.051.01.01.", -3.9372, 35.2517, 2],
  ["Essaouira", "07.211.01.05.", -9.7595, 31.5085, 2, "w"],  ["Mohammedia", "06.371.01.01.", -7.3833, 33.6861, 3], ["Settat", "06.461.01.15.", -7.6164, 33.001, 3],
  ["Berrechid", "06.117.01.03.", -7.5872, 33.2655, 3],
  ["Khouribga", "05.311.01.07.", -6.9063, 32.8811, 3], ["Khenifra", "05.301.01.01.", -5.668, 32.9394, 3],
  ["Ifrane", "03.271.01.03.", -5.1107, 33.5228, 3], ["Sefrou", "03.451.01.09.", -4.8288, 33.8305, 3],
  ["Taza", "03.561.01.11.", -4.0103, 34.21, 3], ["Taounate", "03.531.01.05.", -4.64, 34.536, 3],
  ["Chefchaouen", "01.151.01.01.", -5.2636, 35.1688, 3],
  ["Larache", "01.331.01.03.", -6.156, 35.1932, 3, "w"],
  ["Ksar El Kebir", "01.331.01.01.", -5.9033, 35.0017, 3],
  ["Ouezzane", "01.405.01.09.", -5.5836, 34.7969, 3],
  ["Sidi Kacem", "04.481.01.11.", -5.7076, 34.226, 3],
  ["Sidi Slimane", "04.491.01.07.", -5.9256, 34.2648, 3, "w"],
  ["Khemisset", "04.291.01.01.", -6.0662, 33.824, 3], ["Guercif", "02.265.01.03.", -3.3536, 34.2257, 3],
  ["Taourirt", "02.533.01.33.", -2.897, 34.4073, 3], ["Berkane", "02.113.01.09.", -2.32, 34.92, 3],
  ["Driouch", "02.167.01.09.", -3.39, 34.976, 3], ["Jerada", "02.275.01.17.", -2.16, 34.31, 3],
  ["Figuig", "02.251.01.03.", -1.229, 32.109, 3], ["Bouarfa", "02.251.01.01.", -1.959, 32.531, 3],
  ["Midelt", "08.363.01.03.", -4.734, 32.68, 3], ["Boulemane", "03.131.01.01.", -4.73, 33.362, 3],
  ["El Hajeb", "03.171.01.05.", -5.371, 33.689, 3], ["Azilal", "05.081.01.01.", -6.5718, 31.9616, 3],
  ["Fquih Ben Salah", "05.255.01.05.", -6.6853, 32.5022, 3],
  ["El Kelaa des Sraghna", "07.191.01.03.", -7.4058, 32.058, 3],
  ["Youssoufia", "07.585.01.13.", -8.529, 32.2464, 3],
  ["Benguerir", "07.427.01.01.", -7.9543, 32.236, 3],
  ["Sidi Bennour", "06.467.01.07.", -8.427, 32.65, 3],
  ["Chichaoua", "07.161.01.01.", -8.766, 31.544, 3], ["Tahannaout", "07.041.01.09.", -7.951, 31.35, 3],
  ["Taroudant", "09.541.01.13.", -8.877, 30.47, 3], ["Tiznit", "09.581.01.07.", -9.7316, 29.6974, 3],
  ["Sidi Ifni", "10.473.01.03.", -10.1733, 29.3797, 3, "w"], ["Tata", "09.551.01.07.", -7.969, 29.743, 3],
  ["Zagora", "08.587.01.13.", -5.838, 30.332, 3], ["Tinghir", "08.577.01.11.", -5.532, 31.515, 3],
  ["Tan-Tan", "10.521.01.01.", -11.103, 28.438, 3], ["Assa", "10.071.01.01.", -9.427, 28.609, 3],
  ["Smara", "11.221.01.01.", -11.67, 26.739, 3], ["Boujdour", "11.121.01.01.", -14.485, 26.126, 3, "w"],
  ["Tarfaya", "11.537.01.05.", -12.926, 27.939, 3, "w"], ["Aousserd", "12.066.03.05.", -14.325, 22.553, 3],
];
const YEARS = [2004, 2014, 2024];
const CITY = /^\d+\.\d+\.\d+\.$/;

const openGroups = new Set();
let D, map, byId = {}, loaded = {}, state = { slice: "all", ind: "pct_electricity", y: 2024, mode: "level", pair: [2014, 2024],
  sel: null, base: true };
// English wherever a string has no French or Arabic (definitions, notes and caveats are English only)
const t = (k) => L[MC.lang][k] || L.en[k] || k;
const isEn = (k) => !L[MC.lang][k];
// French and Arabic labels are HCP's own; where HCP gives none in Arabic its French label is used, then English
const label = (ind) => { const x = D.indicators[ind]; return x[MC.lang] || (MC.lang === "ar" && x.fr) || x.en; };
const groupName = (g) => D.groups[g][MC.lang];
const uname = (u) => (MC.lang === "en" ? u.name : u[`name_${MC.lang}`]);
const pname = (u) => D.provinces[u.prov][MC.lang];
const F = (v, ind = state.ind) => MC.fmt(v, D.indicators[ind].unit, D.indicators[ind].agg);

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("i") && D.indicators[h.get("i")]) state.ind = h.get("i");
  if (h.get("y")) state.y = +h.get("y");
  if (h.get("m")) state.mode = h.get("m");
  if (h.get("p")) state.pair = h.get("p").split("-").map(Number);
  if (h.get("c")) state.sel = h.get("c");
  if (SLICES.includes(h.get("s"))) state.slice = h.get("s");
}
function writeHash() {
  const h = new URLSearchParams({ i: state.ind, m: state.mode });
  if (state.mode === "level") h.set("y", state.y); else h.set("p", state.pair.join("-"));
  if (state.sel) h.set("c", state.sel);
  if (state.slice !== "all") h.set("s", state.slice);
  history.replaceState(null, "", "#" + h.toString());
}

function vintages(ind) { return Object.keys(D.indicators[ind].vintages).map(Number).sort(); }
function pairs(ind) {
  const v = vintages(ind), out = [];
  for (let a = 0; a < v.length; a++) for (let b = a + 1; b < v.length; b++) out.push([v[a], v[b]]);
  return out;
}
// the whole population, or one of HCP's breakdowns; an indicator offers a breakdown only where all three censuses do
const SLICES = ["all", "urban", "rural", "male", "female"];
const has = (ind, sl = state.slice) => sl === "all" || D.indicators[ind].slices.includes(sl);
const key = (ind, y, sl = state.slice) => `${sl}:${ind}|${y}`;
// values are split by catalogue theme and breakdown; a map group can gather several themes
const loadGroup = (g) => Promise.all(Object.keys(D.indicators)
  .filter(k => D.indicators[k].group === g && has(k)).map(k => loadTheme(D.indicators[k].theme)));
function loadTheme(th, sl = state.slice) {
  const f = sl === "all" ? th : `${th}.${sl}`;
  return (loaded[f] ||= fetch(`data/map/${f}.json`).then(r => r.json())
    .then(v => Object.entries(v).forEach(([k, x]) => (D.values[`${sl}:${k}`] = x))));
}
function series(ind, y) {
  return D.values[key(ind, y)] || [];
}
function current() {
  if (state.mode === "level") return series(state.ind, state.y);
  const [a, b] = state.pair, va = series(state.ind, a), vb = series(state.ind, b);
  return va.map((x, i) => (x == null || vb[i] == null ? null : vb[i] - x));
}

const at = (sorted, p) => sorted[Math.floor(p * (sorted.length - 1))];
const uniq = (xs) => xs.filter((x, i) => i === 0 || x > xs[i - 1]);
// n colours spread over a ramp, for when tied breaks leave fewer classes
const spread = (ramp, n) => Array.from({ length: n }, (_, i) => ramp[n === 1 ? 0 : Math.round((i * (ramp.length - 1)) / (n - 1))]);

// Levels: breaks computed at export for each indicator and view, from all three censuses together (so a colour
// means the same value in every census), by whichever of quantiles, Fisher-Jenks or Fisher-Jenks on log(1 + x)
// fits best with no class under 0.5% of values; 0 is a class of its own where a tenth or more of values are 0
function levelBreaks() {
  const all = vintages(state.ind).flatMap(y => series(state.ind, y)).filter(v => v != null);
  const b = D.indicators[state.ind].breaks[state.slice];
  return { edges: b.edges, zeros: b.method.endsWith("+zero"), min: Math.min(...all), max: Math.max(...all) };
}
// two significant figures, or three where two would merge neighbouring breaks
function nice(edges) {
  for (const d of [2, 3, 4]) {
    const r = edges.map(e => +e.toPrecision(d));
    if (new Set(r).size === r.length) return r;
  }
  return edges;
}
// Change: symmetric classes around 0 at the 20th, 50th and 80th percentiles of the absolute change, so the palest
// class holds the smallest fifth of changes and equal colours mean equal magnitudes either way
function changeBreaks(vals) {
  const abs = vals.filter(v => v != null).map(Math.abs).sort((a, b) => a - b);
  if (!abs.length) return [];
  const e = nice(uniq([0.2, 0.5, 0.8].map(p => at(abs, p))));
  return [...e.map(x => -x).reverse(), ...e];
}
function classify(vals) {
  const unit = D.indicators[state.ind].unit;
  if (state.mode === "level" && unit === "flag") {
    return { cls: vals.map(v => (v == null ? -1 : v ? 1 : 0)), colors: FLAG, ticks: [t("rural"), t("urban")], kind: "flag" };
  }
  if (state.mode === "change") {
    const edges = changeBreaks(vals);
    const cls = vals.map(v => (v == null ? -1 : edges.filter(e => v > e).length));
    const s = vals.filter(v => v != null);
    return { cls, colors: spread(DIV, edges.length + 1), edges, kind: "div", min: Math.min(...s), max: Math.max(...s) };
  }
  const b = levelBreaks();
  const cls = vals.map(v => (v == null ? -1 : b.edges.filter(e => v > e).length));
  return { cls, colors: spread(SEQ, b.edges.length + 1), edges: b.edges, zeros: b.zeros, kind: "seq", min: b.min, max: b.max };
}

function paint() {
  const vals = current();
  const c = classify(vals);
  for (let i = 0; i < vals.length; i++) map.setFeatureState({ source: "cells", id: i }, { c: c.cls[i] });
  const expr = ["match", ["feature-state", "c"]];
  c.colors.forEach((col, j) => expr.push(j, col));
  expr.push(getComputedStyle(document.documentElement).getPropertyValue("--nodata").trim() || "#e4e3de");
  map.setPaintProperty("cells-fill", "fill-color", expr);
  legend(c);
  writeHash();
}

// one row per class: its colour and value range
function legend(c) {
  const unit = D.indicators[state.ind].unit, f = v => F(v);
  const sign = (v) => (c.kind === "div" && v > 0 ? "+" : "") + f(v);
  const el = document.getElementById("legend");
  let rows;
  if (c.kind === "flag") rows = c.colors.map((col, j) => [col, c.ticks[j]]);
  else rows = c.colors.map((col, j) => {
    const lo = j === 0 ? c.min : c.edges[j - 1], hi = j === c.edges.length ? c.max : c.edges[j];
    if (c.zeros && j === 0) return [col, f(0)];
    if (c.zeros && j === 1) return [col, `> ${f(0)} – ${sign(hi)}`];
    return [col, lo === hi ? sign(lo) : `${sign(lo)} – ${sign(hi)}`];
  });
  const unitLabel = c.kind === "flag" ? "" : c.kind === "div" && unit === "%" ? MC.unitName("pts") : MC.unitName(unit);
  el.innerHTML = `
    ${rows.map(([col, txt]) => `<div class="row"><i style="background:${col}"></i><bdi>${MC.esc(txt)}</bdi></div>`).join("")}
    <div class="row nd"><i></i>${t("nodata")}</div>
    ${unitLabel ? `<div class="u">${MC.esc(unitLabel)}</div>` : ""}`;
}

function controls() {
  const sel = document.getElementById("ind");
  const byGroup = {};
  Object.entries(D.indicators).filter(([k]) => has(k)).forEach(([k, v]) => (byGroup[v.group] ||= []).push(k));
  sel.innerHTML = Object.keys(D.groups).filter(g => byGroup[g]).map(g =>
    `<optgroup label="${MC.esc(groupName(g))}">${byGroup[g]
      .sort((a, b) => label(a).localeCompare(label(b)))
      .map(k => `<option value="${k}">${MC.esc(label(k))}</option>`).join("")}</optgroup>`
  ).join("");
  sel.value = state.ind;
  document.getElementById("slice").innerHTML = SLICES.map(sl =>
    `<button data-s="${sl}" aria-pressed="${sl === state.slice}">${t(`s_${sl}`)}</button>`).join("");
  document.querySelectorAll("#slice button").forEach(b => b.onclick = () => setSlice(b.dataset.s));

  const v = vintages(state.ind);
  if (state.mode === "change" && v.length < 2) state.mode = "level";
  if (!v.includes(state.y)) state.y = v[v.length - 1];
  const ps = pairs(state.ind);
  if (!ps.some(p => p.join() === state.pair.join())) state.pair = ps[ps.length - 1] || state.pair;

  document.querySelectorAll("#mode button").forEach(b => {
    b.setAttribute("aria-pressed", b.dataset.m === state.mode);
    b.disabled = b.dataset.m === "change" && v.length < 2;
  });
  const yrs = document.getElementById("years");
  yrs.innerHTML = state.mode === "level"
    ? YEARS.map(y => `<button data-y="${y}" aria-pressed="${y === state.y}" ${v.includes(y) ? "" : "disabled"}>${y}</button>`).join("")
    : ps.map(p => `<button dir="ltr" data-p="${p.join("-")}" aria-pressed="${p.join() === state.pair.join()}">${p[0]}→${p[1]}</button>`).join("");
  yrs.querySelectorAll("button").forEach(b => b.onclick = () => {
    if (b.dataset.y) state.y = +b.dataset.y; else state.pair = b.dataset.p.split("-").map(Number);
    controls(); paint(); detail();
  });

  const ind = D.indicators[state.ind];
  document.getElementById("ind-title").textContent = label(state.ind);
  const n = state.mode === "level" ? ind.vintages[state.y]?.n : null;
  document.getElementById("ind-def").innerHTML = `${MC.esc(ind.definition)}${n ? ` <span class="muted">${n.toLocaleString()} / ${D.units.length} ${t("communes")}</span>` : ""}`;
  const note = document.getElementById("ind-note");
  const warn = [];
  if (ind.note) warn.push(MC.esc(ind.note));
  if (state.mode === "change" && ind.comparable === false) warn.unshift(`<b>${t("noncomp")}</b>`);
  note.innerHTML = warn.join("<br>");
  note.hidden = !warn.length;
  document.querySelectorAll("[data-t]").forEach(el => {
    el.textContent = t(el.dataset.t);
    if (isEn(el.dataset.t)) { el.lang = "en"; el.dir = "ltr"; } else { el.removeAttribute("lang"); el.removeAttribute("dir"); }
  });
  document.getElementById("i18n").innerHTML = MC.translateNote();
}

// a breakdown the current indicator lacks falls back to the first indicator that has it
async function setSlice(sl) {
  if (sl === state.slice) return;
  state.slice = sl;
  if (!has(state.ind)) state.ind = Object.keys(D.indicators).find(k => has(k));
  await loadTheme(D.indicators[state.ind].theme);
  controls(); paint(); detail();
}

function detail() {
  const el = document.getElementById("detail");
  if (state.sel == null || !(state.sel in byId)) { el.hidden = true; return; }
  const i = byId[state.sel], u = D.units[i];
  const groups = [];
  const curGroup = D.indicators[state.ind].group;
  for (const g of Object.keys(D.groups)) {
    const inds = Object.keys(D.indicators).filter(k => D.indicators[k].group === g && has(k))
      .sort((a, b) => label(a).localeCompare(label(b)));
    const open = openGroups.has(g) || g === curGroup;
    if (open && inds.some(k => !D.values[key(k, 2024)])) loadGroup(g).then(detail);
    const body = inds.map(k => {
      const cells = YEARS.map(y => {
        const v = D.values[key(k, y)]?.[i];
        const cur = k === state.ind && (state.mode === "level" ? y === state.y : state.pair.includes(y));
        return `<td class="num${cur ? " cur" : ""}">${F(v, k)}</td>`;
      }).join("");
      return `<tr><td>${MC.esc(label(k))}</td>${cells}</tr>`;
    }).join("");
    if (inds.length) groups.push(`<details data-g="${g}"${open ? " open" : ""}>
      <summary>${MC.esc(groupName(g))} <span class="muted">${inds.length}</span></summary>
      <table><thead><tr><th></th>${YEARS.map(y => `<th class="num">${y}</th>`).join("")}</tr></thead>
      <tbody>${body}</tbody></table></details>`);
  }
  el.innerHTML = `
    <h3>${MC.esc(uname(u))}</h3>
    <div class="meta">${MC.esc(pname(u))} · <code dir="ltr">${MC.esc(u.id)}</code>${CITY.test(u.id) ? ` · <span lang="en" dir="ltr">${t("city")}</span>` : ""} · ${t("point")}: ${MC.esc(u.pt)}</div>
    <div class="h">${t("allind")}</div>
    <div class="groups">${groups.join("")}</div>`;
  el.querySelectorAll("details").forEach(d => d.addEventListener("toggle", () => {
    if (d.open) { openGroups.add(d.dataset.g); loadGroup(d.dataset.g).then(detail); }
    else openGroups.delete(d.dataset.g);
  }));
  el.hidden = false;
}

function select(id, fly) {
  if (state.sel != null && state.sel in byId) map.setFeatureState({ source: "cells", id: byId[state.sel] }, { sel: false });
  state.sel = id;
  if (id != null && id in byId) {
    map.setFeatureState({ source: "cells", id: byId[id] }, { sel: true });
    const u = D.units[byId[id]];
    if (fly) map.flyTo({ center: [u.lon, u.lat], zoom: Math.max(map.getZoom(), 8) });
  }
  detail(); writeHash();
}

function tooltip(e) {
  const tip = document.getElementById("tip");
  if (!e || !e.features?.length) { tip.hidden = true; return; }
  const i = e.features[0].id, u = D.units[i], unit = D.indicators[state.ind].unit;
  const v = current()[i];
  let sub = "";
  if (state.mode === "change") {
    const [a, b] = state.pair;
    const lvl = (y) => MC.withUnit(F(series(state.ind, y)[i]), unit, false);
    sub = `<bdi>${a}: ${lvl(a)}</bdi> → <bdi>${b}: ${lvl(b)}</bdi>`;
  }
  const y = state.mode === "level" ? state.y : null;
  tip.innerHTML = `<b>${MC.esc(uname(u))}</b><br><span class="muted">${MC.esc(pname(u))}</span><br>
    <span class="v"><bdi>${state.mode === "change" && v != null ? (v > 0 ? "+" : "") : ""}${MC.withUnit(F(v), unit, state.mode === "change")}</bdi></span>
    ${sub ? `<br><span class="muted">${sub}</span>` : ""}`;
  const r = document.getElementById("map").getBoundingClientRect();
  const x = Math.min(e.point.x + 14, r.width - 270), yy = Math.min(e.point.y + 14, r.height - 110);
  tip.style.left = x + "px"; tip.style.top = yy + "px"; tip.hidden = false;
}

const dark = () => document.documentElement.dataset.theme === "dark" ||
  (document.documentElement.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);

async function main() {
  MC.header("map");
  const [d, cells, outline, context] = await Promise.all(
    ["data/map/index.json", "data/communes_hcp2024.geojson", "data/outline.geojson", "data/context.geojson"]
    .map(u => fetch(u).then(r => r.json())));
  const cols = d.units;
  D = { ...d, values: {}, units: cols.id.map((_, i) => Object.fromEntries(Object.keys(cols).map(k => [k, cols[k][i]]))) };
  D.units.forEach((u, i) => (byId[u.id] = i));
  readHash();
  if (!has(state.ind)) state.slice = "all";
  await loadTheme(D.indicators[state.ind].theme);
  const datalist = () => (document.getElementById("communes").innerHTML = D.units
    .map(u => `<option value="${MC.esc(uname(u))} — ${MC.esc(pname(u))}"></option>`).join(""));
  datalist();

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {
        cells: { type: "geojson", data: cells, promoteId: "i", attribution: 'HCP RGPH · <a href="https://www.naturalearthdata.com">Natural Earth</a> · GeoNames · Wikidata' },
        outline: { type: "geojson", data: outline },
        context: { type: "geojson", data: context },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": css("--sea") } },
        { id: "context", type: "fill", source: "context", paint: { "fill-color": css("--land") } },
        { id: "context-line", type: "line", source: "context", paint: { "line-color": css("--line"), "line-width": 0.6 } },
        { id: "cells-fill", type: "fill", source: "cells", paint: { "fill-color": css("--nodata"), "fill-opacity": 0.88 } },
        { id: "cells-line", type: "line", source: "cells", paint: {
          "line-color": dark() ? "#1a1a19" : "#fcfcfb", "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.15, 8, 0.8] } },
        { id: "outline", type: "line", source: "outline", paint: { "line-color": css("--text-3"), "line-width": 0.8 } },
        { id: "cells-hover", type: "line", source: "cells", paint: {
          "line-color": css("--text"), "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.6, 0] } },
        // halo + ink rather than a hue, so the selection never collides with a ramp colour
        { id: "cells-sel-halo", type: "line", source: "cells", paint: {
          "line-color": css("--surface"), "line-width": ["case", ["boolean", ["feature-state", "sel"], false], 5, 0] } },
        { id: "cells-sel", type: "line", source: "cells", paint: {
          "line-color": css("--text"), "line-width": ["case", ["boolean", ["feature-state", "sel"], false], 2.2, 0] } },
      ],
    },
    bounds: [[-17.2, 20.7], [-0.9, 36.0]],
    fitBoundsOptions: { padding: 20 },
    attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  const tip = document.createElement("div");
  tip.id = "tip"; tip.className = "tip"; tip.hidden = true;
  document.getElementById("map").appendChild(tip);

  // HTML markers render Arabic natively; a symbol layer would need glyphs and the RTL text plugin
  const cityEls = CITIES.map(([en, id, lon, lat, tier, side]) => {
    const el = document.createElement("div");
    el.className = `city t${tier}${side === "w" ? " w" : ""}`;
    el.dataset.en = en; el.dataset.fr = D.units[byId[id]].name_fr; el.dataset.ar = D.units[byId[id]].name_ar;
    new maplibregl.Marker({ element: el, anchor: side === "w" ? "right" : "left" }).setLngLat([lon, lat]).addTo(map);
    return el;
  });
  const cityNames = () => cityEls.forEach(el => (el.innerHTML = `<i></i><span>${MC.esc(el.dataset[MC.lang])}</span>`));
  const cityZoom = () => {
    const el = document.getElementById("map"), z = map.getZoom();
    el.classList.toggle("zoomed", z >= 6); el.classList.toggle("zoomed2", z >= 7.5);
  };
  cityNames(); map.on("zoom", cityZoom);
  MC.onLang(cityNames);

  map.on("load", () => {
    cityZoom(); controls(); paint(); if (state.sel) select(state.sel, true);
    let hover = null;
    map.on("mousemove", "cells-fill", (e) => {
      map.getCanvas().style.cursor = "pointer";
      const id = e.features[0].id;
      if (hover !== id) {
        if (hover != null) map.setFeatureState({ source: "cells", id: hover }, { hover: false });
        hover = id; map.setFeatureState({ source: "cells", id }, { hover: true });
      }
      tooltip(e);
    });
    map.on("mouseleave", "cells-fill", () => {
      map.getCanvas().style.cursor = "";
      if (hover != null) map.setFeatureState({ source: "cells", id: hover }, { hover: false });
      hover = null; tooltip(null);
    });
    map.on("click", "cells-fill", (e) => select(D.units[e.features[0].id].id, false));
  });

  document.getElementById("ind").onchange = async (e) => {
    state.ind = e.target.value;
    await loadTheme(D.indicators[state.ind].theme);
    controls(); paint(); detail();
  };
  document.querySelectorAll("#mode button").forEach(b => b.onclick = () => {
    if (b.disabled) return; state.mode = b.dataset.m; controls(); paint(); detail();
  });
  document.getElementById("q").onchange = (e) => {
    const name = e.target.value.split(" — ")[0].trim().toLowerCase();
    const prov = (e.target.value.split(" — ")[1] || "").trim().toLowerCase();
    const names = u => [u.name, u.name_fr, u.name_ar].map(x => x.toLowerCase());
    const u = D.units.find(u => uname(u).toLowerCase() === name && (!prov || pname(u).toLowerCase() === prov))
      || D.units.find(u => names(u).some(x => x.startsWith(name)));
    if (u) select(u.id, true);
  };
  MC.onLang(() => { controls(); paint(); detail(); datalist(); });
}
main();
