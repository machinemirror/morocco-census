// Shared chrome: nav, the map's EN/FR/AR switch (remembered per browser), small helpers. Only the map is
// multilingual, and only for HCP's own place names and indicator labels; every other page is English.
const MC = (() => {
  const T = {
    en: { map: "Map", catalogue: "Catalogue", downloads: "Downloads", about: "About", tag: "Moroccan census by commune" },
    fr: { map: "Carte", catalogue: "Catalogue", downloads: "Téléchargements", about: "À propos", tag: "Recensement marocain par commune" },
    ar: { map: "الخريطة", catalogue: "الفهرس", downloads: "التحميلات", about: "حول المشروع", tag: "الإحصاء العام للسكان والسكنى حسب الجماعة" },
  };
  let lang = "en";
  const multilingual = document.body.dataset.page === "map";
  if (multilingual) {
    try { lang = localStorage.getItem("mc-lang") || ["fr", "ar"].find(l => (navigator.language || "").startsWith(l)) || "en"; } catch (e) {}
    if (!T[lang]) lang = "en";
  }
  const ISSUE = "https://github.com/machinemirror/morocco-census/issues/new?labels=translation&title=";
  const ASK = {
    fr: { page: "Cette page n'existe qu'en anglais. Vous maîtrisez le français ? Aidez-nous à la traduire",
          map: "Les définitions et les notes n'existent qu'en anglais. Vous maîtrisez le français ? Aidez-nous à les traduire",
          link: "écrivez-nous sur GitHub" },
    ar: { page: "هذه الصفحة متوفرة بالإنجليزية فقط. هل تتقن العربية؟ ساعدنا في ترجمتها",
          map: "التعاريف والملاحظات متوفرة بالإنجليزية فقط. هل تتقن العربية؟ ساعدنا في ترجمتها",
          link: "راسلنا على GitHub" },
  };
  // on the map, a note in the chosen language; on English-only pages, one line in each
  function translateNote() {
    const line = (l, kind) => `<p lang="${l}" dir="${l === "ar" ? "rtl" : "ltr"}">${ASK[l][kind]} : ` +
      `<a href="${ISSUE}${encodeURIComponent(`Translation (${l})`)}">${ASK[l].link}</a>.</p>`;
    if (multilingual) return lang === "en" ? "" : line(lang, "map");
    return line("fr", "page") + line("ar", "page");
  }
  const listeners = [];

  function header(active) {
    const el = document.querySelector("header.topbar");
    const t = T[lang];
    el.innerHTML = `
      <a class="brand" href="./">morocco-census <span>· RGPH 2004 · 2014 · 2024</span></a>
      <nav class="nav">
        ${["map", "catalogue", "downloads", "about"].map(k =>
          `<a href="${k === "map" ? "./" : k + ".html"}" ${k === active ? 'aria-current="page"' : ""}>${t[k]}</a>`).join("")}
      </nav>
      <div class="spacer"></div>
      ${multilingual ? `<div class="lang" role="group" aria-label="Language">
        <button data-l="en" aria-pressed="${lang === "en"}">EN</button>
        <button data-l="fr" aria-pressed="${lang === "fr"}">FR</button>
        <button data-l="ar" aria-pressed="${lang === "ar"}" lang="ar" title="العربية">ع</button>
      </div>` : ""}`;
    el.querySelectorAll(".lang button").forEach(b => b.onclick = () => setLang(b.dataset.l, active));
    const note = document.getElementById("i18n-page");
    if (note) note.innerHTML = translateNote();
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }

  function setLang(l, active) {
    lang = l;
    try { localStorage.setItem("mc-lang", l); } catch (e) {}
    header(active);
    listeners.forEach(f => f(l));
  }

  // ar-MA: Morocco writes Arabic text with Western digits
  const nf = (d) => new Intl.NumberFormat({ fr: "fr-FR", ar: "ar-MA" }[lang] || "en-US", { maximumFractionDigits: d });
  function fmt(v, unit, agg) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    if (agg === "sum" && unit !== "%") return nf(0).format(v);
    if (unit === "flag") return { en: ["no", "yes"], fr: ["non", "oui"], ar: ["لا", "نعم"] }[lang][v ? 1 : 0];
    const a = Math.abs(v);
    if (unit === "%") return nf(a >= 1 || a === 0 ? 1 : 2).format(v);
    if (unit === "index 0-1") return nf(3).format(v);
    if (["children per woman", "persons per room", "persons"].includes(unit)) return nf(2).format(v);
    if (["km", "years", "per 1,000", "per 1,000 births", "per 1,000 residents"].includes(unit)) return nf(1).format(v);
    return nf(a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 3).format(v);
  }
  const UNITS = {
    pts: { en: "pts", fr: "pts", ar: "نقطة" },
    km: { en: "km", fr: "km", ar: "كلم" },
    years: { en: "years", fr: "ans", ar: "سنة" },
    "children per woman": { en: "children per woman", fr: "enfants par femme", ar: "طفل لكل امرأة" },
    "persons per room": { en: "persons per room", fr: "personnes par pièce", ar: "شخص في الغرفة" },
    "per 1,000": { en: "per 1,000", fr: "pour 1 000", ar: "في الألف" },
    "per 1,000 births": { en: "per 1,000 births", fr: "pour 1 000 naissances", ar: "لكل 1000 ولادة حية" },
    persons: { en: "persons", fr: "personnes", ar: "نسمة" },
    households: { en: "households", fr: "ménages", ar: "أسرة" },
    dwellings: { en: "dwellings", fr: "logements", ar: "مسكن" },
    establishments: { en: "establishments", fr: "établissements", ar: "مؤسسة" },
    jobs: { en: "jobs", fr: "emplois", ar: "منصب شغل" },
    souks: { en: "souks", fr: "souks", ar: "سوق" },
    douars: { en: "douars", fr: "douars", ar: "دوار" },
    "per 1,000 residents": { en: "per 1,000 residents", fr: "pour 1 000 habitants", ar: "لكل 1000 نسمة" },
    index: { en: "index", fr: "indice", ar: "مؤشر" },
    "index 0-1": { en: "index 0-1", fr: "indice 0-1", ar: "مؤشر 0-1" },
    flag: { en: "0/1 flag", fr: "indicateur 0/1", ar: "مؤشر 0/1" },
    code: { en: "code", fr: "code", ar: "رمز" },
    text: { en: "text", fr: "texte", ar: "نص" },
    page: { en: "page", fr: "page", ar: "صفحة" },
  };
  const unitName = (u) => UNITS[u]?.[lang] ?? u;
  // a change in a percentage is in percentage points, not percent
  function withUnit(s, unit, change) {
    if (s === "—" || ["flag", "index", "index 0-1"].includes(unit)) return s;
    if (unit === "%") return change ? `${s} ${unitName("pts")}` : lang === "en" ? `${s}%` : `${s}\u202f%`;
    return `${s} ${unitName(unit)}`;
  }
  function bytes(n) {
    return n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1e3)) + " kB";
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  return { header, get lang() { return lang; }, onLang: f => listeners.push(f), fmt, withUnit, unitName, bytes, esc, translateNote };
})();
