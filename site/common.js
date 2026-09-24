// Shared chrome: nav, EN/FR switch (remembered per browser), small helpers.
const MC = (() => {
  const T = {
    en: { map: "Map", catalogue: "Catalogue", downloads: "Downloads", about: "About", tag: "Moroccan census by commune" },
    fr: { map: "Carte", catalogue: "Catalogue", downloads: "Téléchargements", about: "À propos", tag: "Recensement marocain par commune" },
  };
  let lang = "en";
  try { lang = localStorage.getItem("mc-lang") || (navigator.language || "").startsWith("fr") && "fr" || "en"; } catch (e) {}
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
      <div class="lang" role="group" aria-label="Language">
        <button data-l="en" aria-pressed="${lang === "en"}">EN</button>
        <button data-l="fr" aria-pressed="${lang === "fr"}">FR</button>
      </div>`;
    el.querySelectorAll(".lang button").forEach(b => b.onclick = () => setLang(b.dataset.l, active));
    document.documentElement.lang = lang;
  }

  function setLang(l, active) {
    lang = l;
    try { localStorage.setItem("mc-lang", l); } catch (e) {}
    header(active);
    listeners.forEach(f => f(l));
  }

  const nf = (d) => new Intl.NumberFormat(lang === "fr" ? "fr-FR" : "en-US", { maximumFractionDigits: d });
  function fmt(v, unit, agg) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    if (agg === "sum" && unit !== "%") return nf(0).format(v);
    if (unit === "flag") return v ? (lang === "fr" ? "oui" : "yes") : (lang === "fr" ? "non" : "no");
    const a = Math.abs(v);
    return nf(a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 3).format(v);
  }
  function bytes(n) {
    return n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1e3)) + " kB";
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  return { header, get lang() { return lang; }, onLang: f => listeners.push(f), fmt, bytes, esc };
})();
