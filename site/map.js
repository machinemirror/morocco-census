const L = {
  en: {
    indicator: "Indicator", view: "View", level: "Level", change: "Change", census: "Census",
    find: "Find a commune", hideImputed: "Hide imputed values",
    nodata: "No data", decrease: "decrease", increase: "increase", rural: "Rural", urban: "Urban",
    caveat: "Commune shapes are Thiessen approximations built from one point per commune; HCP publishes no commune boundaries. Shapes show roughly where a commune is, not its true extent.",
    noncomp: "Definitions differ between censuses; read the change with care.",
    imputed: "imputed from neighbouring communes (post-2004 reorganisation)",
    fuzzy: "2004 values matched by name similarity", point: "seed point", allind: "All indicators",
    city: "city (arrondissements combined)", communes: "communes",
  },
  fr: {
    indicator: "Indicateur", view: "Affichage", level: "Niveau", change: "Évolution", census: "Recensement",
    find: "Trouver une commune", hideImputed: "Masquer les valeurs imputées",
    nodata: "Pas de donnée", decrease: "baisse", increase: "hausse", rural: "Rurale", urban: "Urbaine",
    caveat: "Les contours sont des polygones de Thiessen construits à partir d'un point par commune ; le HCP ne publie pas de limites communales. Ils indiquent l'emplacement approximatif, pas l'étendue réelle.",
    noncomp: "Les définitions diffèrent entre recensements ; interpréter l'évolution avec prudence.",
    imputed: "imputé à partir des communes voisines (réorganisation post-2004)",
    fuzzy: "valeurs 2004 appariées par similarité de nom", point: "point d'ancrage", allind: "Tous les indicateurs",
    city: "ville (arrondissements agrégés)", communes: "communes",
  },
  ar: {
    indicator: "المؤشر", view: "العرض", level: "المستوى", change: "التطور", census: "الإحصاء",
    find: "البحث عن جماعة", hideImputed: "إخفاء القيم المقدّرة",
    nodata: "لا توجد معطيات", decrease: "انخفاض", increase: "ارتفاع", rural: "قروية", urban: "حضرية",
    caveat: "أشكال الجماعات تقريبية (مضلعات ثيسن) مبنية انطلاقاً من نقطة واحدة لكل جماعة، إذ لا تنشر المندوبية السامية للتخطيط حدود الجماعات. تبيّن الأشكال الموقع التقريبي للجماعة لا امتدادها الحقيقي.",
    noncomp: "تختلف التعاريف بين الإحصاءات؛ يُرجى قراءة التطور بحذر.",
    imputed: "مقدّرة انطلاقاً من الجماعات المجاورة (بسبب إعادة التقسيم بعد 2004)",
    fuzzy: "قيم 2004 مُطابَقة على أساس تشابه الأسماء", point: "نقطة الارتكاز", allind: "جميع المؤشرات",
    city: "مدينة (مقاطعات مجمّعة)", communes: "جماعة",
  },
};
// Colour-blind-safe ramps: viridis (reversed, so more = darker) and ColorBrewer PuOr.
const SEQ = ["#fde725", "#90d743", "#35b779", "#21918c", "#31688e", "#443983", "#440154"];
const DIV = ["#b35806", "#f1a340", "#fee0b6", "#f7f7f7", "#d8daeb", "#998ec3", "#542788"];
const FLAG = ["#90d743", "#31688e"];
// Orientation labels: [en, fr, ar, lon, lat, tier (1 always, 2 from zoom 6, 3 from zoom 7.5), label side]. Coastal labels sit over the sea.
const CITIES = [
  ["Rabat", "Rabat", "الرباط", -6.8417, 34.0209, 1, "w"], ["Casablanca", "Casablanca", "الدار البيضاء", -7.5898, 33.5731, 1, "w"],
  ["Fez", "Fès", "فاس", -5.0003, 34.0331, 1], ["Marrakesh", "Marrakech", "مراكش", -7.9811, 31.6295, 1],
  ["Tangier", "Tanger", "طنجة", -5.834, 35.7595, 1, "w"], ["Agadir", "Agadir", "أكادير", -9.5981, 30.4278, 1, "w"],
  ["Oujda", "Oujda", "وجدة", -1.9086, 34.6814, 1], ["Laâyoune", "Laâyoune", "العيون", -13.1625, 27.1253, 1, "w"],
  ["Dakhla", "Dakhla", "الداخلة", -15.958, 23.6848, 1, "w"], ["Meknes", "Meknès", "مكناس", -5.5473, 33.8935, 2],
  ["Kenitra", "Kénitra", "القنيطرة", -6.5802, 34.261, 2, "w"], ["Tetouan", "Tétouan", "تطوان", -5.3626, 35.5889, 2],
  ["Nador", "Nador", "الناظور", -2.9335, 35.1681, 2], ["Beni Mellal", "Béni Mellal", "بني ملال", -6.3498, 32.3373, 2],
  ["Errachidia", "Errachidia", "الرشيدية", -4.4245, 31.9314, 2], ["Ouarzazate", "Ouarzazate", "ورزازات", -6.8934, 30.9189, 2],
  ["Guelmim", "Guelmim", "كلميم", -10.0574, 28.987, 2], ["Safi", "Safi", "آسفي", -9.2372, 32.2994, 2, "w"],
  ["El Jadida", "El Jadida", "الجديدة", -8.5007, 33.2316, 2, "w"], ["Al Hoceima", "Al Hoceïma", "الحسيمة", -3.9372, 35.2517, 2],
  ["Essaouira", "Essaouira", "الصويرة", -9.7595, 31.5085, 2, "w"],  ["Mohammedia", "Mohammédia", "المحمدية", -7.3833, 33.6861, 3], ["Settat", "Settat", "سطات", -7.6164, 33.001, 3],
  ["Berrechid", "Berrechid", "برشيد", -7.5872, 33.2655, 3],
  ["Khouribga", "Khouribga", "خريبكة", -6.9063, 32.8811, 3], ["Khenifra", "Khénifra", "خنيفرة", -5.668, 32.9394, 3],
  ["Ifrane", "Ifrane", "إفران", -5.1107, 33.5228, 3], ["Sefrou", "Séfrou", "صفرو", -4.8288, 33.8305, 3],
  ["Taza", "Taza", "تازة", -4.0103, 34.21, 3], ["Taounate", "Taounate", "تاونات", -4.64, 34.536, 3],
  ["Chefchaouen", "Chefchaouen", "شفشاون", -5.2636, 35.1688, 3],
  ["Larache", "Larache", "العرائش", -6.156, 35.1932, 3, "w"],
  ["Ksar El Kebir", "Ksar El Kébir", "القصر الكبير", -5.9033, 35.0017, 3],
  ["Ouezzane", "Ouezzane", "وزان", -5.5836, 34.7969, 3],
  ["Sidi Kacem", "Sidi Kacem", "سيدي قاسم", -5.7076, 34.226, 3],
  ["Sidi Slimane", "Sidi Slimane", "سيدي سليمان", -5.9256, 34.2648, 3, "w"],
  ["Khemisset", "Khémisset", "الخميسات", -6.0662, 33.824, 3], ["Guercif", "Guercif", "جرسيف", -3.3536, 34.2257, 3],
  ["Taourirt", "Taourirt", "تاوريرت", -2.897, 34.4073, 3], ["Berkane", "Berkane", "بركان", -2.32, 34.92, 3],
  ["Driouch", "Driouch", "الدريوش", -3.39, 34.976, 3], ["Jerada", "Jerada", "جرادة", -2.16, 34.31, 3],
  ["Figuig", "Figuig", "فجيج", -1.229, 32.109, 3], ["Bouarfa", "Bouarfa", "بوعرفة", -1.959, 32.531, 3],
  ["Midelt", "Midelt", "ميدلت", -4.734, 32.68, 3], ["Boulemane", "Boulemane", "بولمان", -4.73, 33.362, 3],
  ["El Hajeb", "El Hajeb", "الحاجب", -5.371, 33.689, 3], ["Azilal", "Azilal", "أزيلال", -6.5718, 31.9616, 3],
  ["Fquih Ben Salah", "Fquih Ben Salah", "الفقيه بن صالح", -6.6853, 32.5022, 3],
  ["El Kelaa des Sraghna", "El Kelaâ des Sraghna", "قلعة السراغنة", -7.4058, 32.058, 3],
  ["Youssoufia", "Youssoufia", "اليوسفية", -8.529, 32.2464, 3],
  ["Benguerir", "Benguerir", "ابن جرير", -7.9543, 32.236, 3],
  ["Sidi Bennour", "Sidi Bennour", "سيدي بنور", -8.427, 32.65, 3],
  ["Chichaoua", "Chichaoua", "شيشاوة", -8.766, 31.544, 3], ["Tahannaout", "Tahannaout", "تحناوت", -7.951, 31.35, 3],
  ["Taroudant", "Taroudant", "تارودانت", -8.877, 30.47, 3], ["Tiznit", "Tiznit", "تيزنيت", -9.7316, 29.6974, 3],
  ["Sidi Ifni", "Sidi Ifni", "سيدي إفني", -10.1733, 29.3797, 3, "w"], ["Tata", "Tata", "طاطا", -7.969, 29.743, 3],
  ["Zagora", "Zagora", "زاكورة", -5.838, 30.332, 3], ["Tinghir", "Tinghir", "تنغير", -5.532, 31.515, 3],
  ["Tan-Tan", "Tan-Tan", "طانطان", -11.103, 28.438, 3], ["Assa", "Assa", "أسا", -9.427, 28.609, 3],
  ["Smara", "Smara", "السمارة", -11.67, 26.739, 3], ["Boujdour", "Boujdour", "بوجدور", -14.485, 26.126, 3, "w"],
  ["Tarfaya", "Tarfaya", "طرفاية", -12.926, 27.939, 3, "w"], ["Aousserd", "Aousserd", "أوسرد", -14.325, 22.553, 3],
];
const YEARS = [2004, 2014, 2024];
const CITY = /^\d+\.\d+\.\d+\.$/;

const openThemes = new Set();
let D, map, byId = {}, state = { ind: "pct_electricity", y: 2024, mode: "level", pair: [2014, 2024], hideImp: false,
  sel: null, base: true };
const t = (k) => L[MC.lang][k] || k;
const label = (ind) => D.indicators[ind][MC.lang];
const tx = (o, k) => o[`${k}_${MC.lang}`] || o[k];
const F = (v, ind = state.ind) => MC.fmt(v, D.indicators[ind].unit, D.indicators[ind].agg);

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("i") && D.indicators[h.get("i")]) state.ind = h.get("i");
  if (h.get("y")) state.y = +h.get("y");
  if (h.get("m")) state.mode = h.get("m");
  if (h.get("p")) state.pair = h.get("p").split("-").map(Number);
  if (h.get("c")) state.sel = h.get("c");
}
function writeHash() {
  const h = new URLSearchParams({ i: state.ind, m: state.mode });
  if (state.mode === "level") h.set("y", state.y); else h.set("p", state.pair.join("-"));
  if (state.sel) h.set("c", state.sel);
  history.replaceState(null, "", "#" + h.toString());
}

function vintages(ind) { return Object.keys(D.indicators[ind].vintages).map(Number).sort(); }
function pairs(ind) {
  const v = vintages(ind), out = [];
  for (let a = 0; a < v.length; a++) for (let b = a + 1; b < v.length; b++) out.push([v[a], v[b]]);
  return out;
}
function isImputed(i, y) {
  const u = D.units[i], f = y === 2004 ? u.src04 : y === 2014 ? u.src14 : u.src24;
  const ds = D.indicators[state.ind].vintages[y]?.dataset;
  return ds === "panel_commune" && typeof f === "string" && f.startsWith("imputed");
}
function series(ind, y) {
  const v = D.values[`${ind}|${y}`] || [];
  return state.hideImp && ind === state.ind ? v.map((x, i) => (isImputed(i, y) ? null : x)) : v;
}
function current() {
  if (state.mode === "level") return series(state.ind, state.y);
  const [a, b] = state.pair, va = series(state.ind, a), vb = series(state.ind, b);
  return va.map((x, i) => (x == null || vb[i] == null ? null : vb[i] - x));
}

function quantileBreaks(vals, k) {
  const s = vals.filter(v => v != null).sort((a, b) => a - b);
  if (!s.length) return [];
  const br = [];
  for (let j = 1; j < k; j++) br.push(s[Math.floor((j / k) * (s.length - 1))]);
  return br;
}
function classify(vals) {
  const unit = D.indicators[state.ind].unit;
  if (state.mode === "level" && unit === "flag") {
    return { cls: vals.map(v => (v == null ? -1 : v ? 1 : 0)), colors: FLAG, ticks: [t("rural"), t("urban")], kind: "flag" };
  }
  if (state.mode === "change") {
    const abs = vals.filter(v => v != null).map(Math.abs).sort((a, b) => a - b);
    const m = abs[Math.floor(0.95 * (abs.length - 1))] || 1;
    const edges = [-5, -3, -1, 1, 3, 5].map(x => (x / 7) * m);
    const cls = vals.map(v => (v == null ? -1 : edges.filter(e => v > e).length));
    return { cls, colors: DIV, edges, kind: "div" };
  }
  const br = quantileBreaks(vals, 7);
  const cls = vals.map(v => (v == null ? -1 : br.filter(e => v > e).length));
  const s = vals.filter(v => v != null);
  return { cls, colors: SEQ, edges: br, kind: "seq", min: Math.min(...s), max: Math.max(...s) };
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

function legend(c) {
  const unit = D.indicators[state.ind].unit, f = v => F(v);
  const el = document.getElementById("legend");
  let ticks;
  if (c.kind === "flag") ticks = `<span>${c.ticks[0]}</span><span>${c.ticks[1]}</span>`;
  else if (c.kind === "div") ticks = `<span>≤ −${f(-c.edges[0])} ${t("decrease")}</span><span>0</span><span>${t("increase")} ≥ +${f(c.edges[5])}</span>`;
  else ticks = `<span>${f(c.min)}</span><span>${f(c.edges[3])}</span><span>${f(c.max)}</span>`;
  const unitLabel = c.kind === "flag" ? "" : c.kind === "div" && unit === "%" ? MC.unitName("pts") : MC.unitName(unit);
  el.innerHTML = `
    <div class="bar">${c.colors.map((col, j) => {
      const lo = j === 0 ? (c.min ?? null) : c.edges?.[j - 1], hi = c.edges?.[j] ?? c.max;
      const title = c.kind === "seq" ? `${f(lo)} – ${f(hi)}` : c.kind === "div" ? "" : c.ticks[j];
      return `<span style="background:${col}" title="${MC.esc(title)}"></span>`;
    }).join("")}</div>
    <div class="ticks">${ticks}</div>
    <div class="nd"><i></i>${t("nodata")}${unitLabel ? " · " + MC.esc(unitLabel) : ""}</div>`;
}

function controls() {
  const sel = document.getElementById("ind");
  const byTheme = {};
  Object.entries(D.indicators).forEach(([k, v]) => (byTheme[v.theme] ||= []).push(k));
  sel.innerHTML = Object.keys(D.themes).filter(th => byTheme[th]).map(th =>
    `<optgroup label="${MC.esc(D.themes[th][MC.lang])}">${byTheme[th]
      .sort((a, b) => label(a).localeCompare(label(b)))
      .map(k => `<option value="${k}">${MC.esc(label(k))} (${vintages(k).join(", ")})</option>`).join("")}</optgroup>`
  ).join("");
  sel.value = state.ind;

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
  document.getElementById("ind-def").innerHTML = `${MC.esc(tx(ind, "definition"))}${n ? ` <span class="muted">${n.toLocaleString()} / ${D.units.length} ${t("communes")}</span>` : ""}`;
  const note = document.getElementById("ind-note");
  const warn = [];
  if (ind.note) warn.push(MC.esc(tx(ind, "note")));
  if (state.mode === "change" && ind.comparable === false) warn.unshift(`<b>${t("noncomp")}</b>`);
  note.innerHTML = warn.join("<br>");
  note.hidden = !warn.length;
  const usesPanel = Object.values(ind.vintages).some(x => x.dataset === "panel_commune");
  document.getElementById("imp-row").hidden = !usesPanel;
  document.querySelectorAll("[data-t]").forEach(el => (el.textContent = t(el.dataset.t)));
}

function detail() {
  const el = document.getElementById("detail");
  if (state.sel == null || !(state.sel in byId)) { el.hidden = true; return; }
  const i = byId[state.sel], u = D.units[i];
  const groups = [];
  const curTheme = D.indicators[state.ind].theme;
  for (const th of Object.keys(D.themes)) {
    const inds = Object.keys(D.indicators).filter(k => D.indicators[k].theme === th)
      .sort((a, b) => label(a).localeCompare(label(b)));
    const body = inds.map(k => {
      const cells = YEARS.map(y => {
        const v = D.values[`${k}|${y}`]?.[i];
        const cur = k === state.ind && (state.mode === "level" ? y === state.y : state.pair.includes(y));
        return `<td class="num${cur ? " cur" : ""}">${D.indicators[k].vintages[y] ? F(v, k) : ""}</td>`;
      }).join("");
      return `<tr><td>${MC.esc(label(k))}</td>${cells}</tr>`;
    }).join("");
    if (inds.length) groups.push(`<details data-th="${th}"${openThemes.has(th) || th === curTheme ? " open" : ""}>
      <summary>${MC.esc(D.themes[th][MC.lang])} <span class="muted">${inds.length}</span></summary>
      <table><thead><tr><th></th>${YEARS.map(y => `<th class="num">${y}</th>`).join("")}</tr></thead>
      <tbody>${body}</tbody></table></details>`);
  }
  const flags = [];
  if (u.src04 && u.src04.startsWith("imputed")) flags.push(`2004: ${t("imputed")}`);
  if (u.src04 === "fuzzy") flags.push(t("fuzzy"));
  if (u.src14 && u.src14.startsWith("imputed")) flags.push(`2014 MPI: ${t("imputed")}`);
  if (u.src24 && u.src24.startsWith("imputed")) flags.push(`2024 MPI: ${t("imputed")}`);
  el.innerHTML = `
    <h3>${MC.esc(u.name)}</h3>
    <div class="meta">${MC.esc(u.prov)} · <code>${MC.esc(u.id)}</code>${CITY.test(u.id) ? " · " + t("city") : ""} · ${t("point")}: ${MC.esc(u.pt)}</div>
    ${flags.length ? `<div class="note" style="margin-bottom:.5rem">${flags.map(MC.esc).join("<br>")}</div>` : ""}
    <div class="h">${t("allind")}</div>
    <div class="groups">${groups.join("")}</div>`;
  el.querySelectorAll("details").forEach(d => d.addEventListener("toggle", () =>
    d.open ? openThemes.add(d.dataset.th) : openThemes.delete(d.dataset.th)));
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
  tip.innerHTML = `<b>${MC.esc(u.name)}</b><br><span class="muted">${MC.esc(u.prov)}</span><br>
    <span class="v"><bdi>${state.mode === "change" && v != null ? (v > 0 ? "+" : "") : ""}${MC.withUnit(F(v), unit, state.mode === "change")}</bdi></span>
    ${sub ? `<br><span class="muted">${sub}</span>` : ""}${y && isImputed(i, y) ? `<br><span class="muted">${t("imputed")}</span>` : ""}`;
  const r = document.getElementById("map").getBoundingClientRect();
  const x = Math.min(e.point.x + 14, r.width - 270), yy = Math.min(e.point.y + 14, r.height - 110);
  tip.style.left = x + "px"; tip.style.top = yy + "px"; tip.hidden = false;
}

const dark = () => document.documentElement.dataset.theme === "dark" ||
  (document.documentElement.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);

async function main() {
  MC.header("map");
  const [d, cells, outline, context] = await Promise.all(
    ["data/map.json", "data/communes.geojson", "data/outline.geojson", "data/context.geojson"]
    .map(u => fetch(u).then(r => r.json())));
  D = d;
  D.units.forEach((u, i) => (byId[u.id] = i));
  readHash();
  document.getElementById("communes").innerHTML = D.units
    .map(u => `<option value="${MC.esc(u.name)} — ${MC.esc(u.prov)}"></option>`).join("");

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {
        cells: { type: "geojson", data: cells, promoteId: "i", attribution: 'HCP RGPH · <a href="https://www.naturalearthdata.com">Natural Earth</a> · GADM · GeoNames' },
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
  const cityEls = CITIES.map(([en, fr, ar, lon, lat, tier, side]) => {
    const el = document.createElement("div");
    el.className = `city t${tier}${side === "w" ? " w" : ""}`;
    el.dataset.en = en; el.dataset.fr = fr; el.dataset.ar = ar;
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

  document.getElementById("ind").onchange = (e) => { state.ind = e.target.value; controls(); paint(); detail(); };
  document.querySelectorAll("#mode button").forEach(b => b.onclick = () => {
    if (b.disabled) return; state.mode = b.dataset.m; controls(); paint(); detail();
  });
  document.getElementById("imp").onchange = (e) => { state.hideImp = e.target.checked; paint(); };
  document.getElementById("q").onchange = (e) => {
    const name = e.target.value.split(" — ")[0].trim().toLowerCase();
    const prov = (e.target.value.split(" — ")[1] || "").trim().toLowerCase();
    const u = D.units.find(u => u.name.toLowerCase() === name && (!prov || u.prov.toLowerCase() === prov))
      || D.units.find(u => u.name.toLowerCase().startsWith(name));
    if (u) select(u.id, true);
  };
  MC.onLang(() => { controls(); paint(); detail(); });
}
main();
