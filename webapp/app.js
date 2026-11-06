/* Chang Monitor: Telegram Mini App */
(() => {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp;
  const inTelegram = !!(tg && tg.initData);
  const $ = (s, el = document) => el.querySelector(s);
  const LANGS = ["uz", "ru", "en"];
  const PROFILES = ["none", "sensitive", "pregnant", "elderly", "child", "athlete"];
  const SENSITIVE = ["sensitive", "pregnant", "elderly", "child"];
  const RISK_COLORS = ["#4caf50", "#fbc02d", "#fb8c00", "#e53935"];
  const STATUS_COLORS = ["#2e9d4f", "#e08a00", "#d93025"];
  // O'zbekiston tabiati ranglari: firuza (koshinlar), lojuvard, qum, anor, saksovul, o'rik, tog'
  const NATURE = { firuza: "#12968b", lojuvard: "#2c5aa8", qum: "#d9a050", anor: "#c63b4a", saksovul: "#5f8f3e", orik: "#f08a4b", tog: "#6d7fb0" };
  const REGION_OF = { nukus: "aral", moynoq: "aral", urganch: "khorezm", buxoro: "kyzylkum", navoiy: "kyzylkum", qarshi: "kashka",
    termiz: "surkhan", samarqand: "zarafshan", toshkent: "capital", jizzax: "mirzachul", guliston: "mirzachul",
    namangan: "fergana", andijon: "fergana", fargona: "fergana" };
  const REGION_STYLE = { aral: ["🌊", "desert"], khorezm: ["🕌", "desert"], kyzylkum: ["🏜", "desert"], kashka: ["🌾", "desert"],
    surkhan: ["☀️", "desert"], zarafshan: ["🕌", "heritage"], capital: ["🏙", "capital"], mirzachul: ["🌾", "steppe"],
    fergana: ["⛰", "mountain"], other: ["📍", "capital"] };
  const THEMES = ["auto", "light", "dark"];

  const state = {
    lang: "uz",
    place: { key: "toshkent" },   // {key} yoki {lat, lon}
    profile: "none",
    meta: null,
    data: null,
    overview: null,
    settings: null,                // serverdagi sozlamalar (faqat Telegram ichida)
    view: "home",
    charts: {},
    map: null,
    mapLayers: { cities: null, reports: null, cloud: null, arrows: null, dots: null },
    mapMode: "cities",
    grid: null,
    frame: 0,
    playing: null,
    history: null,
    historyFor: null,
    historyDays: 30,
    histMetric: "pm10",
    histYear: null,
    dlFrom: null,
    dlTo: null,
    historySource: "live",
    archiveSummary: null,
    reports: null,
    aralYear: 1960,
    photoBlob: null,
    theme: "auto",
    sensor: null,
    sensorsMap: null,
  };

  // ---------------- Yordamchilar ----------------
  const store = {
    get(k, d) { try { const v = localStorage.getItem("chang_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("chang_" + k, JSON.stringify(v)); } catch { /* maxfiy rejim */ } },
  };

  const tv = (key) => {
    const own = I18N[state.lang] && I18N[state.lang][key];
    return own !== undefined ? own : I18N.uz[key];
  };
  function tr(key, vars) {
    let s = tv(key);
    if (typeof s !== "string") s = key;
    if (vars) for (const k in vars) s = s.replace("{" + k + "}", vars[k]);
    return s;
  }
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const haptic = (type = "selection") => {
    try {
      if (!tg || !tg.HapticFeedback) return;
      if (type === "selection") tg.HapticFeedback.selectionChanged();
      else if (type === "success" || type === "error") tg.HapticFeedback.notificationOccurred(type);
      else tg.HapticFeedback.impactOccurred(type);
    } catch { /* eski Telegram */ }
  };

  function levelIdx(pm10) {
    const lim = state.meta.levels.limits;
    for (let i = 0; i < lim.length; i++) if ((pm10 || 0) < lim[i]) return i;
    return lim.length;
  }
  const levelColor = (pm10) => state.meta.levels.colors[levelIdx(pm10)];
  const levelName = (pm10) => state.meta.levels.names[state.lang][levelIdx(pm10)];
  const levelAdvice = (pm10) => state.meta.levels.advice[state.lang][levelIdx(pm10)];

  function cityName(key) {
    if (!state.meta) return "…";
    const c = state.meta.cities.find((x) => x.key === key);
    return c ? c.name[state.lang] : tr("myLocation");
  }
  const placeName = () => state.place.key ? cityName(state.place.key) : tr("myLocation");
  const weatherName = (code) => (state.meta.weather_names[state.lang] || {})[code] || "—";
  const weatherEmoji = (code) => state.meta.weather_emoji[code] || "🌡";

  function windDir(deg) {
    if (deg === null || deg === undefined) return "—";
    return state.meta.wind_dirs[state.lang][Math.round(deg / 45) % 8];
  }

  const todayStr = () => new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Tashkent" });
  const whenText = (iso) => iso.slice(0, 10) === todayStr() ? tr("today") : tr("tomorrow");
  function shortDate(iso) {
    const d = new Date(iso.slice(0, 10) + "T12:00");
    return d.getDate() + " " + MONTHS_SHORT[state.lang][d.getMonth()];
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2200);
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    if (inTelegram) headers["X-Init-Data"] = tg.initData;
    if (typeof opts.body === "string") headers["Content-Type"] = "application/json";
    const r = await fetch(path, Object.assign({}, opts, { headers }));
    if (!r.ok) {
      const err = new Error(path + " → " + r.status);
      err.status = r.status;
      throw err;
    }
    return r.json();
  }

  function placeQuery() {
    const p = state.place;
    return p.key ? "key=" + encodeURIComponent(p.key) : "lat=" + p.lat.toFixed(3) + "&lon=" + p.lon.toFixed(3);
  }
  const placeLatLon = () => {
    if (state.data) return [state.data.lat, state.data.lon];
    const c = state.meta.cities.find((x) => x.key === state.place.key);
    return c ? [c.lat, c.lon] : [state.place.lat, state.place.lon];
  };

  // ---------------- Hudud (geografiya) ----------------
  function regionKey() {
    const k = state.place.key || (state.data && state.data.scene_key);
    return REGION_OF[k] || "other";
  }
  function applyRegion() {
    document.documentElement.dataset.region = REGION_STYLE[regionKey()][1];
  }

  // ---------------- Mavzu (Avto / Yorug' / Qorong'i) ----------------
  function applyTheme() {
    const root = document.documentElement;
    const sysDark = tg && tg.colorScheme ? tg.colorScheme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = state.theme === "dark" || (state.theme === "auto" && sysDark);
    root.dataset.scheme = dark ? "dark" : "light";
    root.dataset.theme = state.theme;
    if (tg) {
      try {
        if (state.theme === "auto") {
          tg.setHeaderColor("secondary_bg_color");
          tg.setBackgroundColor("secondary_bg_color");
        } else {
          const bg = getComputedStyle(root).getPropertyValue("--bg").trim();
          if (/^#[0-9a-f]{6}$/i.test(bg)) { tg.setHeaderColor(bg); tg.setBackgroundColor(bg); }
        }
      } catch { /* eski versiya */ }
    }
    if (window.Chart) {
      Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue("--hint").trim() || "#888";
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    }
  }

  function applyI18n() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = tr(el.dataset.i18n); });
    $("#captionInput").placeholder = tr("captionPh");
    $("#cityName").textContent = placeName();
  }

  // ---------------- Ma'lumot yuklash ----------------
  async function loadData(force) {
    const btn = $("#refreshBtn");
    btn.classList.add("spin");
    if (!state.data || force === "skeleton") renderSkeleton();
    try {
      state.data = await api("/api/city?" + placeQuery());
      renderAll();
      loadSensor();
    } catch (e) {
      console.error(e);
      renderError();
    } finally {
      btn.classList.remove("spin");
    }
    api("/api/overview").then((o) => {
      state.overview = o.cities;
      renderCityList();
      if (state.view === "stats") renderStats();
      if (state.map) renderCityMarkers();
    }).catch(() => {});
    loadReports();
    if (state.view === "stats") loadHistory();
  }

  async function loadReports() {
    try {
      const [lat, lon] = placeLatLon();
      const r = await api(`/api/reports?lat=${lat}&lon=${lon}`);
      state.reports = r.reports;
    } catch { state.reports = []; }
    renderReportsCard();
    if (state.map) renderReportPins();
  }

  function renderSkeleton() {
    $("#view-home").innerHTML =
      '<div class="skeleton" style="aspect-ratio:1000/560"></div>' +
      '<div class="skeleton" style="height:190px"></div><div class="skeleton" style="height:220px"></div>';
  }

  function renderError() {
    const html = '<div class="card error-box"><div style="font-size:40px">😔</div><p>' + esc(tr("error")) +
      '</p><button type="button" class="retry">' + esc(tr("retry")) + "</button></div>";
    $("#view-home").innerHTML = html;
    $("#view-forecast").innerHTML = html;
    decorateHeads($("#view-forecast"));
    document.querySelectorAll(".retry").forEach((b) => b.addEventListener("click", () => loadData("skeleton")));
  }

  function renderAll() {
    applyI18n();
    renderHome();
    renderForecast();
    renderSettings();
    if (state.view === "stats") renderStats();
    if (state.map) { renderCityMarkers(); renderLegend(); }
  }

  // ---------------- Hisob-kitoblar ----------------
  function hourlyIndex(times) {
    const m = {};
    (times || []).forEach((t, i) => { m[t] = i; });
    return m;
  }

  function profileFactor(act) {
    if (SENSITIVE.includes(state.profile)) return 0.6;
    if (state.profile === "athlete" && act === "run") return 0.8;
    return 1;
  }

  const ACTS = [
    { id: "run", icon: "🏃", name: "actRun", good: 50, caution: 100, rain: true, heat: true },
    { id: "walk", icon: "🚶", name: "actWalk", good: 100, caution: 250, rain: true, heat: true },
    { id: "child", icon: "👶", name: "actChild", good: 50, caution: 100, rain: true, heat: true, wind: true },
    { id: "window", icon: "🪟", name: "actWindow", good: 50, caution: 150, wind: true },
  ];

  // Bitta soat uchun faollik holati: 0 = mumkin, 1 = ehtiyot, 2 = tavsiya etilmaydi
  function actStatus(act, i) {
    const d = state.data, ah = d.air.hourly, wh = d.weather && d.weather.hourly;
    const pm = ah.pm10[i];
    if (pm === null || pm === undefined) return null;
    const f = profileFactor(act.id);
    let s = pm < act.good * f ? 0 : pm < act.caution * f ? 1 : 2;
    const reasons = [];
    if (wh) {
      const wi = state._wIndex[ah.time[i]];
      if (wi !== undefined) {
        if (act.rain && (wh.precipitation || [])[wi] >= 0.5) { s = Math.max(s, 1); reasons.push(tr("reasonRain")); }
        if (act.heat && (wh.temperature_2m || [])[wi] >= 35) { s = Math.max(s, 1); reasons.push(tr("reasonHeat")); }
        if (act.wind && (wh.wind_gusts_10m || [])[wi] >= state.meta.alert.gust) { s = Math.max(s, 1); reasons.push(tr("reasonWind")); }
      }
    }
    return { s, reasons };
  }

  function next24() {
    const ah = state.data.air.hourly, now = state.data.air.current.time;
    const start = Math.max(0, ah.time.findIndex((t) => t >= now));
    return { start, idx: Array.from({ length: 24 }, (_, k) => start + k).filter((i) => i < ah.time.length) };
  }

  const isDaytime = (t) => { const h = +t.slice(11, 13); return h >= 6 && h <= 21; };
  const fmtRange = (t1, t2) => {
    const h2 = (+t2.slice(11, 13) + 1) % 24;
    return t1.slice(11, 16) + "–" + String(h2).padStart(2, "0") + ":00";
  };

  function bestRun(act) {
    const ah = state.data.air.hourly;
    const { idx } = next24();
    let best = null, cur = null;
    for (const i of idx) {
      const st = actStatus(act, i);
      const ok = st && st.s === 0 && isDaytime(ah.time[i]);
      if (ok) {
        if (!cur) cur = { a: i, b: i }; else cur.b = i;
      } else if (cur) {
        if (!best) best = cur;
        cur = null;
      }
    }
    if (cur && !best) best = cur;
    return best ? fmtRange(ah.time[best.a], ah.time[best.b]) : null;
  }

  function bestWindow() {
    const ah = state.data.air.hourly;
    const { idx } = next24();
    let best = null;
    for (let k = 0; k + 2 < idx.length; k++) {
      const ids = [idx[k], idx[k + 1], idx[k + 2]];
      if (!ids.every((i) => isDaytime(ah.time[i]))) continue;
      const vals = ids.map((i) => ah.pm10[i]).filter((v) => v !== null);
      if (vals.length < 3) continue;
      const mean = vals.reduce((a, b) => a + b, 0) / 3;
      if (!best || mean < best.mean) best = { mean, a: ids[0], b: ids[2] };
    }
    return best && { range: fmtRange(ah.time[best.a], ah.time[best.b]), mean: best.mean };
  }

  function cigarettes() {
    const ah = state.data.air.hourly, day = state.data.air.current.time.slice(0, 10);
    const vals = ah.time.map((t, i) => (t.startsWith(day) ? ah.pm2_5[i] : null)).filter((v) => v !== null && v !== undefined);
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length / 22;
  }

  function usAqiIdx(v) { return v <= 50 ? 0 : v <= 100 ? 1 : v <= 150 ? 2 : v <= 200 ? 3 : v <= 300 ? 4 : 5; }
  const AQI_COLORS = ["#4caf50", "#fbc02d", "#fb8c00", "#e53935", "#8e24aa", "#7b1e1e"];
  function uvIdx(v) { return v < 3 ? 0 : v < 6 ? 1 : v < 8 ? 2 : v < 11 ? 3 : 4; }

  // ---------------- Asosiy sahifa ----------------
  function gaugeSVG(pm10) {
    const max = 500, cx = 75, cy = 78, r = 60;
    const lim = [0, ...state.meta.levels.limits, max];
    const colors = state.meta.levels.colors;
    const pt = (v, rr) => {
      const a = Math.PI * (1 - Math.min(v, max) / max);
      return [cx + rr * Math.cos(a), cy - rr * Math.sin(a)];
    };
    let arcs = "";
    for (let i = 0; i < lim.length - 1; i++) {
      const [x1, y1] = pt(lim[i], r), [x2, y2] = pt(Math.min(lim[i + 1], max), r);
      arcs += `<path d="M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}"
                stroke="${colors[i]}" stroke-width="12" fill="none" opacity=".9"/>`;
    }
    const [mx, my] = pt(pm10 || 0, r);
    return `<svg class="gauge" viewBox="0 0 150 92" aria-hidden="true">${arcs}
      <circle cx="${mx.toFixed(1)}" cy="${my.toFixed(1)}" r="8" fill="${levelColor(pm10)}" stroke="var(--card)" stroke-width="3"/>
      <text x="${cx}" y="${cy - 10}" text-anchor="middle" class="gauge-val" data-count="${pm10}">${fmt(pm10)}</text>
      <text x="${cx}" y="${cy + 8}" text-anchor="middle" class="gauge-unit">PM10 µg/m³</text></svg>`;
  }

  function compassSVG(deg) {
    const letters = state.lang === "ru" ? ["С", "В", "Ю", "З"] : state.lang === "uz" ? ["Sh", "Shq", "J", "G'"] : ["N", "E", "S", "W"];
    const rot = deg === null || deg === undefined ? 0 : deg + 180;
    let ticks = "";
    for (let i = 0; i < 24; i++) {
      const a = (i * 15) * Math.PI / 180, r1 = i % 6 === 0 ? 38 : 41;
      ticks += `<line x1="${50 + r1 * Math.sin(a)}" y1="${50 - r1 * Math.cos(a)}" x2="${50 + 44 * Math.sin(a)}" y2="${50 - 44 * Math.cos(a)}" stroke="var(--hint)" stroke-width="${i % 6 === 0 ? 2 : 1}" opacity=".6"/>`;
    }
    return `<svg class="compass" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="46" fill="var(--soft)"/>${ticks}
      <text x="50" y="22" text-anchor="middle" font-size="10" font-weight="700" fill="var(--text)">${letters[0]}</text>
      <text x="80" y="54" text-anchor="middle" font-size="9" fill="var(--hint)">${letters[1]}</text>
      <text x="50" y="86" text-anchor="middle" font-size="10" fill="var(--hint)">${letters[2]}</text>
      <text x="20" y="54" text-anchor="middle" font-size="10" fill="var(--hint)">${letters[3]}</text>
      <g class="needle" style="transform: rotate(${rot}deg)">
        <path d="M50 24 L57 52 L50 47 L43 52 Z" fill="var(--accent)"/>
        <path d="M50 76 L54 52 L50 55 L46 52 Z" fill="var(--hint)" opacity=".6"/>
      </g></svg>`;
  }

  function riskRing(score, lvl) {
    const r = 46, c = 2 * Math.PI * r, off = c * (1 - clamp(score, 0, 100) / 100);
    return `<svg class="risk-ring" viewBox="0 0 112 112" aria-hidden="true">
      <circle cx="56" cy="56" r="${r}" fill="none" stroke="var(--soft)" stroke-width="11"/>
      <circle class="arc" cx="56" cy="56" r="${r}" fill="none" stroke="${RISK_COLORS[lvl]}" stroke-width="11" stroke-linecap="round"
        stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" transform="rotate(-90 56 56)"
        style="--c:${c.toFixed(1)};--off:${off.toFixed(1)}"/>
      <text x="56" y="62" text-anchor="middle" class="rv" data-count="${score}">${score}</text>
      <text x="56" y="78" text-anchor="middle" class="rl">/ 100</text></svg>`;
  }

  function riskCard() {
    const rk = state.data.risk;
    if (!rk) return "";
    const f = rk.factors, lv = tv("riskLevels");
    const bar = (label, score, val, color) => `<div class="factor"><span class="muted">${esc(label)}</span>
      <span class="bar"><i style="width:${clamp(score, 0, 100)}%;--fc:${color}"></i></span><b>${val}</b></div>`;
    const rainTxt = f.rain.value > 0.2 ? `${fmt(f.rain.value, 1)} ${tr("mm")}` : tr("riskRainNone");
    const wd = WEEKDAYS_SHORT[state.lang];
    const days = rk.days.slice(0, 3).map((d) => `<div class="risk-day" style="--rc:${RISK_COLORS[d.level]}">
      ${esc(wd[new Date(d.date + "T12:00").getDay()])}<b>${d.score}</b></div>`).join("");
    return `<div class="card"><h4>${esc(tr("risk"))}</h4>
      <div class="risk">${riskRing(rk.score, rk.level)}
        <div><p class="risk-level" style="--rc:${RISK_COLORS[rk.level]}">${esc(lv[rk.level])}</p>
          ${bar(tr("riskWind"), f.wind.score, fmt(f.wind.value) + " " + tr("ms"), "#1e88e5")}
          ${bar(tr("riskDry"), f.dry.score, f.dry.score + "%", "#c58b3a")}
          ${bar(tr("riskDust"), f.dust.score, fmt(f.dust.value), "#8d6e63")}
          ${bar(tr("riskRain"), f.rain.factor < 1 ? 100 * (1 - f.rain.factor) : 0, rainTxt, "#42a5f5")}
        </div></div>
      <div class="risk-days">${days}</div>
      <p class="muted small" style="margin:10px 0 0">${esc(tr("riskNote"))}</p></div>`;
  }

  function activityCard() {
    const bw = bestWindow();
    const lab = [tr("stOk"), tr("stCaution"), tr("stNo")];
    const nowI = next24().start;
    const rows = ACTS.map((a) => {
      const st = actStatus(a, nowI);
      if (!st) return "";
      const best = bestRun(a);
      const reason = st.reasons.length ? ` · ${esc(st.reasons.join(", "))}` : "";
      return `<div class="act"><div class="a-ico">${a.icon}</div>
        <div><div class="a-name">${esc(tr(a.name))}</div>
          <div class="a-best">${best ? esc(tr("bestAt", { range: best })) : esc(tr("noGood"))}${reason}</div></div>
        <span class="status" style="--sc:${STATUS_COLORS[st.s]}">${esc(lab[st.s])}</span></div>`;
    }).join("");
    const head = bw ? `<div class="best-window"><div class="bw-ico">🌿</div><div>
        <div class="muted small">${esc(tr("bestWindow"))}</div>
        <div class="bw-time">${esc(bw.range)}</div>
        <div class="muted small">PM10 ≈ ${fmt(bw.mean)} µg/m³</div></div></div>` : "";
    return `<div class="card"><h4>${esc(tr("activities"))}</h4>${head}${rows}</div>`;
  }

  function cigaretteCard() {
    const n = cigarettes();
    if (n === null) return "";
    const whole = Math.floor(n), frac = n - whole;
    const icons = "🚬".repeat(Math.min(whole, 12)) + (frac >= 0.25 && whole < 12 ? '<span class="half">🚬</span>' : "");
    return `<div class="card"><h4>${esc(tr("cigTitle"))}</h4>
      <div class="cig"><div class="cig-num" data-count="${n.toFixed(1)}" data-dec="1">${fmt(n, 1)}</div>
        <div><div>${esc(tr("cigText", { n: fmt(n, 1) }))}</div><div class="cig-icons">${icons || "✨"}</div></div></div>
      <p class="muted small" style="margin:10px 0 0">${esc(tr("cigNote"))}</p></div>`;
  }

  function fullAqCard() {
    const a = state.data.air.current;
    if (a.us_aqi === undefined && a.ozone === undefined) return "";
    const ai = usAqiIdx(a.us_aqi || 0);
    const m = (label, v, unit) => `<div class="metric"><div class="m-label">${label}</div><div class="m-val">${fmt(v)}<small>${unit}</small></div></div>`;
    const uv = a.uv_index;
    return `<div class="card"><h4>${esc(tr("fullAq"))}</h4>
      ${a.us_aqi !== undefined && a.us_aqi !== null ? `<div class="aqi-badge"><div class="ab-num" style="--ac:${AQI_COLORS[ai]}">${fmt(a.us_aqi)}</div>
        <div><div class="muted small">${esc(tr("usAqi"))}</div><div class="ab-name">${esc(tv("aqiLevels")[ai])}</div></div></div>` : ""}
      <div class="pollutants">
        ${m(esc(tr("ozone")), a.ozone, "µg/m³")}${m(tr("no2"), a.nitrogen_dioxide, "µg/m³")}${m(tr("so2"), a.sulphur_dioxide, "µg/m³")}
        ${m(tr("co"), a.carbon_monoxide, "µg/m³")}
        <div class="metric"><div class="m-label">${esc(tr("uv"))}</div><div class="m-val">${fmt(uv, 1)}<small>${uv !== undefined && uv !== null ? esc(tv("uvLevels")[uvIdx(uv)]) : ""}</small></div></div>
        ${m(tr("pm25"), a.pm2_5, "µg/m³")}
      </div></div>`;
  }

  function reportsCardHTML() {
    const list = (state.reports || []).filter((r) => r.km === undefined || r.km <= 300).slice(0, 10);
    const items = list.length ? `<div class="reports-row">${list.map((r) => `
      <div class="report-card"><img loading="lazy" src="/api/report_photo/${r.id}" alt="">
        <div class="rc-meta"><div class="rc-cap">${esc(r.caption || cityName(r.city))}</div>
        <div class="muted">${r.km !== undefined ? esc(tr("kmAway", { km: r.km })) + " · " : ""}${esc(r.created.slice(11, 16))}</div></div></div>`).join("")}</div>`
      : `<p class="muted small" style="margin:0">${esc(tr("noReports"))}</p>`;
    return `<h4>${esc(tr("reports"))}</h4><p class="muted small" style="margin:-6px 0 10px">${esc(tr("reportsNear"))}</p>
      ${items}<button type="button" class="ghost-btn" id="openReport">${esc(tr("sendReport"))}</button>`;
  }

  function renderReportsCard() {
    const el = $("#reportsCard");
    if (el) { el.innerHTML = reportsCardHTML(); decorateHeads(el.parentNode); }
  }

  // ---------------- Haqiqiy datchik ----------------
  async function loadSensor() {
    if (!state.meta.sensors) return;
    state.sensor = null;
    renderSensorCard();
    try { state.sensor = await api("/api/sensor?" + placeQuery()); } catch { state.sensor = { available: false, reason: "error" }; }
    renderSensorCard();
  }

  function renderSensorCard() {
    const el = $("#sensorCard");
    if (!el) return;
    el.innerHTML = sensorCardHTML();
    decorateHeads(el.parentNode);
  }

  function sensorCardHTML() {
    const s = state.sensor, head = `<h4>${esc(tr("sensor"))}</h4>`;
    if (!s) return head + '<div class="skeleton" style="height:110px;margin:0"></div>';
    if (!s.available) {
      const msg = s.reason === "far" && s.station ? tr("sensorFar", { name: s.station.name, km: s.station.km }) : tr("sensorErr");
      return head + `<p class="muted small" style="margin:0">${esc(msg)}</p>`;
    }
    const ai = usAqiIdx(s.aqi || 0), a = state.data.air.current;
    const row = (label, model, real, realAqi) => {
      const max = Math.max(model || 0, real || 0, 1);
      const col = realAqi !== null && realAqi !== undefined ? AQI_COLORS[usAqiIdx(realAqi)] : "var(--accent)";
      return `<div class="cmp"><div class="cmp-l">${label}</div><div class="cmp-bars">
        <div class="cmp-bar"><i style="width:${(100 * (model || 0) / max).toFixed(0)}%;background:var(--hint)"></i><span>${fmt(model)}</span></div>
        <div class="cmp-bar"><i style="width:${(100 * (real || 0) / max).toFixed(0)}%;background:${col}"></i><span>≈${fmt(real)}</span></div>
      </div></div>`;
    };
    const time = (s.station.time || "").slice(11, 16) || "—";
    return head + `<div class="aqi-badge"><div class="ab-num" style="--ac:${AQI_COLORS[ai]}">${fmt(s.aqi)}</div>
        <div><div class="ab-name">${esc(s.station.name)}</div>
        <div class="muted small">${esc(tr("sensorKm", { km: s.station.km }))} · ${esc(tr("sensorUpdated", { time }))}</div>
        <div class="small"><b>${esc(tr("sensorLegend"))}:</b> ${esc(tv("aqiLevels")[ai])}</div></div></div>
      <div class="cmp-legend"><span><i style="background:var(--hint)"></i>${esc(tr("sensorModel"))}</span>
        <span><i style="background:var(--accent)"></i>${esc(tr("sensorReal"))}</span><span class="muted">µg/m³</span></div>
      ${row("PM2.5", a.pm2_5, s.pm25, s.pm25_aqi)}${row("PM10", a.pm10, s.pm10, s.pm10_aqi)}
      <p class="muted small" style="margin:10px 0 0">${esc(tr("sensorNote"))}
        ${s.station.url ? `<a class="ext-link" href="${esc(s.station.url)}">${esc(tr("sensorOpen"))} ↗</a>` : ""}</p>`;
  }

  function heroHTML() {
    const d = state.data, a = d.air.current, w = (d.weather && d.weather.current) || null;
    const dt = new Date(a.time + ":00");
    const date = `${WEEKDAYS_LONG[state.lang][dt.getDay()]}, ${shortDate(a.time)} · ${a.time.slice(11, 16)}`;
    const color = levelColor(a.pm10);
    return `<div class="hero" style="--hc:${color}">
      <img id="heroImg" alt="${esc(placeName())}" src="/api/scene?${placeQuery()}&bare=1&t=${encodeURIComponent(a.time)}">
      <div class="hero-shade"></div>
      <div class="hero-top"><span><span class="hero-region">${REGION_STYLE[regionKey()][0]} ${esc(tv("regions")[regionKey()])}</span>
        <span class="hero-date">${esc(date)}</span></span><span class="hero-live"><i></i>${esc(tr("now"))}</span></div>
      <div class="hero-bottom">
        <div>${w ? `<div class="hero-temp"><span data-count="${w.temperature_2m}">${fmt(w.temperature_2m)}</span>°</div>
          <div class="hero-desc">${weatherEmoji(w.weather_code)} ${esc(weatherName(w.weather_code))}</div>
          <div class="hero-feels">${esc(tr("feels"))} ${fmt(w.apparent_temperature)}°</div>`
          : `<div class="hero-desc">${esc(placeName())}</div>`}</div>
        <div class="hero-aqi"><div class="ha-num" data-count="${a.pm10}">${fmt(a.pm10)}</div><div class="ha-unit">PM10 µg/m³</div>
          <div class="ha-lv" style="--lc:${color}">${esc(levelName(a.pm10))}</div></div>
      </div></div>`;
  }

  function quickHTML() {
    const d = state.data, a = d.air.current, w = (d.weather && d.weather.current) || {};
    const q = (icon, color, label, val) => `<div class="q" style="--qc:${color}"><div class="q-ico">${icon}</div>
      <div><div class="q-l">${esc(label)}</div><div class="q-v">${val}</div></div></div>`;
    let html = '<div class="quick">';
    if (d.risk) html += q("🎯", RISK_COLORS[d.risk.level], tr("riskShort"), `${d.risk.score}<span class="muted small">/100</span>`);
    if (w.wind_speed_10m !== undefined) html += q("💨", "#1e88e5", tr("wind"), `${fmt(w.wind_speed_10m)} ${tr("ms")} ${esc(windDir(w.wind_direction_10m))}`);
    if (w.relative_humidity_2m !== undefined) html += q("💧", "#26a6d1", tr("humidity"), `${fmt(w.relative_humidity_2m)}%`);
    if (a.uv_index !== undefined && a.uv_index !== null) html += q("☀️", "#f5a623", tr("uv"), fmt(a.uv_index, 1));
    html += q("🫁", levelColor(a.pm10), tr("pm25"), `${fmt(a.pm2_5)} <span class="muted small">µg/m³</span>`);
    return html + "</div>";
  }

  // Kartochka sarlavhasidagi emojini rangli belgi (ikonka) qilib chiqaradi
  const HEAD_COLORS = Object.values(NATURE);
  function decorateHeads(root) {
    const defaults = {
      [tr("airQuality")]: "🌫", [tr("weather")]: "⛅", [tr("next24")]: "📉", [tr("dustChart")]: "🏜",
      [tr("windChart")]: "💨", [tr("language")]: "🌐", [tr("notifications")]: "🔔",
    };
    root.querySelectorAll(".card > h4:not(.ch)").forEach((h) => {
      const text = h.textContent.trim();
      let icon = null, title = text;
      const m = text.match(/^(\S+)\s+(.*)$/);
      if (m && /\p{Extended_Pictographic}/u.test(m[1])) { icon = m[1]; title = m[2]; }
      if (!icon) icon = defaults[text.split(" · ")[0]] || "•";
      const color = HEAD_COLORS[[...icon].reduce((acc, ch) => acc + ch.codePointAt(0), 0) % HEAD_COLORS.length];
      h.classList.add("ch");
      h.innerHTML = `<span class="h-ico" style="--ic:${color}">${icon}</span><span>${esc(title)}</span>`;
    });
  }

  // Raqamlarni 0 dan sanab chiqaradi
  function animateCounts(root) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    root.querySelectorAll("[data-count]").forEach((el) => {
      const target = parseFloat(el.dataset.count);
      if (Number.isNaN(target)) return;
      const dec = +(el.dataset.dec || 0), t0 = performance.now(), dur = 900;
      const step = (now) => {
        const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        el.textContent = (target * e).toFixed(dec);
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  function renderHome() {
    const d = state.data, a = d.air.current, w = (d.weather && d.weather.current) || null;
    state._wIndex = hourlyIndex(d.weather && d.weather.hourly && d.weather.hourly.time);
    applyRegion();
    const color = levelColor(a.pm10);
    let html = heroHTML() + quickHTML();

    if (d.warn.dust) {
      const t = d.warn.dust.time;
      html += `<div class="banner" style="--c:#e53935"><span class="b-ico">⚠️</span><span>${esc(tr("warnDust",
        { when: whenText(t), hour: t.slice(11, 16), pm10: fmt(d.warn.dust.pm10) }))}</span></div>`;
    }
    if (d.warn.wind) {
      const t = d.warn.wind.time;
      html += `<div class="banner" style="--c:#fb8c00"><span class="b-ico">💨</span><span>${esc(tr("warnWind",
        { when: whenText(t), hour: t.slice(11, 16), gust: fmt(d.warn.wind.gust) }))}</span></div>`;
    }


    const adv = state.profile !== "none" ? tv("profileAdvice")[state.profile] : null;
    html += `<div class="card"><h4>${esc(tr("airQuality"))}</h4>
      <div class="aqi">${gaugeSVG(a.pm10)}
        <div><p class="level-name" style="--lc:${color}">${esc(levelName(a.pm10))}</p>
        <p class="level-advice">${esc(levelAdvice(a.pm10))}</p></div></div>
      <div class="metrics">
        <div class="metric"><div class="m-label">${tr("pm25")}</div><div class="m-val">${fmt(a.pm2_5)}<small>µg/m³</small></div></div>
        <div class="metric"><div class="m-label">${esc(tr("dust"))}</div><div class="m-val">${fmt(a.dust)}<small>µg/m³</small></div></div>
        <div class="metric"><div class="m-label">${esc(tr("aod"))}</div><div class="m-val">${fmt(a.aerosol_optical_depth, 2)}</div></div>
        <div class="metric"><div class="m-label">${esc(tr("humidity"))}</div><div class="m-val">${w ? fmt(w.relative_humidity_2m) : "—"}<small>%</small></div></div>
      </div>
      ${adv ? `<div class="for-you"><b>${tv("profileIcons")[state.profile]} ${esc(tr("forYou"))}:</b> ${esc(adv)}</div>` : ""}</div>`;

    if (state.meta.sensors) html += `<div class="card" id="sensorCard">${sensorCardHTML()}</div>`;
    html += riskCard();
    html += activityCard();

    if (w) {
      html += `<div class="card"><h4>${esc(tr("weather"))}</h4>
        <div class="wx-top"><div class="wx-emoji">${weatherEmoji(w.weather_code)}</div>
          <div><div class="wx-temp">${fmt(w.temperature_2m)}°</div></div>
          <div><div class="wx-desc">${esc(weatherName(w.weather_code))}</div>
          <div class="muted small">${esc(tr("feels"))} ${fmt(w.apparent_temperature)}°</div></div></div>
        <div class="wx-grid">${compassSVG(w.wind_direction_10m)}
          <div class="wx-rows">
            <div class="wx-row"><span class="muted">${esc(tr("wind"))}</span><b>${fmt(w.wind_speed_10m, 1)} ${tr("ms")}</b></div>
            <div class="wx-row"><span class="muted">${esc(tr("gusts"))}</span><b>${fmt(w.wind_gusts_10m)} ${tr("ms")}</b></div>
            <div class="wx-row"><span class="muted">${esc(tr("direction"))}</span><b>${esc(windDir(w.wind_direction_10m))}</b></div>
            <div class="wx-row"><span class="muted">${esc(tr("precip"))}</span><b>${fmt(w.precipitation, 1)} ${tr("mm")}</b></div>
          </div></div></div>`;
    }

    html += `<div class="card"><h4>${esc(tr("next24"))}</h4><div class="chart-box"><canvas id="chart24"></canvas></div></div>`;
    html += cigaretteCard();
    html += fullAqCard();
    html += `<div class="card" id="reportsCard">${reportsCardHTML()}</div>`;
    html += `<p class="footer-note">${esc(tr("updated"))}: ${esc(a.time.replace("T", " "))}</p>`;

    $("#view-home").innerHTML = html;
    decorateHeads($("#view-home"));
    animateCounts($("#view-home"));
    const img = $("#heroImg");
    img.addEventListener("load", () => img.classList.add("loaded"));
    if (img.complete) img.classList.add("loaded");
    draw24h();
  }

  // ---------------- Grafiklar ----------------
  function hourlyLabels(times) {
    const wd = WEEKDAYS_SHORT[state.lang];
    return times.map((t) => {
      const h = t.slice(11, 13);
      return h === "00" ? wd[new Date(t.slice(0, 10) + "T12:00").getDay()] : h + ":00";
    });
  }

  function startIndex(times, now) {
    const i = times.findIndex((t) => t >= now);
    return i < 0 ? 0 : i;
  }

  const bandsPlugin = {
    id: "bands",
    beforeDatasetsDraw(chart, _args, opts) {
      if (!opts || !opts.bands) return;
      const { ctx, chartArea: ca, scales: { y } } = chart;
      ctx.save();
      for (const b of opts.bands) {
        const top = y.getPixelForValue(Math.min(b.to, y.max)), bot = y.getPixelForValue(Math.max(b.from, y.min));
        if (bot <= ca.top || top >= ca.bottom) continue;
        ctx.fillStyle = b.color;
        ctx.fillRect(ca.left, Math.max(top, ca.top), ca.right - ca.left, Math.min(bot, ca.bottom) - Math.max(top, ca.top));
      }
      ctx.restore();
    },
  };

  function levelBands(alpha) {
    const lim = [0, ...state.meta.levels.limits, 10000];
    return state.meta.levels.colors.map((c, i) => ({ from: lim[i], to: lim[i + 1], color: c + alpha }));
  }

  function nowLinePlugin(index) {
    return {
      id: "nowline",
      afterDatasetsDraw(chart) {
        if (index === null || index < 0) return;
        const { ctx, chartArea: ca, scales: { x } } = chart;
        const px = x.getPixelForValue(index);
        ctx.save();
        ctx.strokeStyle = Chart.defaults.color;
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(px, ca.top); ctx.lineTo(px, ca.bottom); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = Chart.defaults.color;
        ctx.font = "11px " + Chart.defaults.font.family;
        ctx.fillText(tr("now"), px + 4, ca.top + 11);
        ctx.restore();
      },
    };
  }

  function makeChart(id, config) {
    if (state.charts[id]) state.charts[id].destroy();
    const el = document.getElementById(id);
    if (!el || !window.Chart) return;
    state.charts[id] = new Chart(el, config);
  }

  const baseOpts = (extra = {}) => Object.assign({
    responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { display: false }, tooltip: { padding: 10, cornerRadius: 10 } },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
      y: { beginAtZero: true, grid: { color: "rgba(127,127,127,.12)" }, ticks: { maxTicksLimit: 5 } },
    },
    elements: { point: { radius: 0, hoverRadius: 4 } },
  }, extra);

  function draw24h() {
    const h = state.data.air.hourly, now = state.data.air.current.time;
    const s = startIndex(h.time, now);
    const times = h.time.slice(s, s + 25), pm = h.pm10.slice(s, s + 25);
    const maxV = Math.max(120, ...pm.filter((v) => v !== null)) * 1.15;
    makeChart("chart24", {
      type: "line",
      data: { labels: hourlyLabels(times), datasets: [{
        data: pm, borderColor: "#d84315", borderWidth: 2.5, tension: .35, fill: false,
        segment: { borderColor: (c) => levelColor(c.p1.parsed.y) },
      }] },
      options: baseOpts({ plugins: { legend: { display: false }, bands: { bands: levelBands("22") } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                  y: { beginAtZero: true, max: Math.round(maxV), grid: { color: "rgba(127,127,127,.12)" }, ticks: { maxTicksLimit: 4 } } } }),
      plugins: [bandsPlugin],
    });
  }

  // ---------------- Prognoz ----------------
  function renderForecast() {
    const d = state.data;
    const daily = d.weather && d.weather.daily;
    const wd = WEEKDAYS_LONG[state.lang];
    const riskDays = (d.risk && d.risk.days) || [];
    let html = `<div class="days">`;
    d.days.forEach((day) => {
      const dt = new Date(day.date + "T12:00");
      const wi = daily ? daily.time.indexOf(day.date) : -1;
      const w = (k) => (wi >= 0 ? daily[k][wi] : null);
      const rd = riskDays.find((x) => x.date === day.date);
      html += `<div class="day" style="--lc:${levelColor(day.pm10)}">
        <div class="d-name">${esc(wd[dt.getDay()])}</div>
        <div class="d-date">${day.date.slice(8, 10)}.${day.date.slice(5, 7)}</div>
        <div class="d-emoji">${wi >= 0 ? weatherEmoji(w("weather_code")) : "🌫"}</div>
        ${wi >= 0 ? `<div class="d-temp">${fmt(w("temperature_2m_max"))}° <span>${fmt(w("temperature_2m_min"))}°</span></div>` : ""}
        <div class="d-pm">PM10 ${fmt(day.pm10)}</div>
        <div class="d-row">${esc(levelName(day.pm10))}</div>
        ${rd ? `<div class="d-risk" style="--rc:${RISK_COLORS[rd.level]}">🎯 ${esc(tr("riskShort"))} ${rd.score}</div>` : ""}
        ${wi >= 0 ? `<div class="d-row">☔ ${fmt(w("precipitation_sum"), 1)} ${tr("mm")} · ${fmt(w("precipitation_probability_max"))}%</div>
        <div class="d-row">💨 ${fmt(w("wind_speed_10m_max"))}–${fmt(w("wind_gusts_10m_max"))} ${tr("ms")}</div>` : ""}
      </div>`;
    });
    html += `</div>`;
    html += `<div class="card"><h4>${esc(tr("dustChart"))}</h4><div class="chart-box tall"><canvas id="chartDust"></canvas></div></div>`;
    if (d.weather && d.weather.hourly) {
      html += `<div class="card"><h4>${esc(tr("windChart"))}</h4><div class="chart-box tall"><canvas id="chartWind"></canvas></div></div>`;
    }
    html += `<p class="footer-note">${esc(tr("source"))}</p>`;
    $("#view-forecast").innerHTML = html;
    decorateHeads($("#view-forecast"));
    if (state.view === "forecast") drawForecastCharts();
  }

  function drawForecastCharts() {
    const d = state.data, h = d.air.hourly;
    const nowIdx = startIndex(h.time, d.air.current.time);
    const vals = h.pm10.concat(h.dust).filter((v) => v !== null);
    makeChart("chartDust", {
      type: "line",
      data: { labels: hourlyLabels(h.time), datasets: [
        { label: "PM10", data: h.pm10, borderColor: "#d84315", borderWidth: 2.5, tension: .35 },
        { label: tr("dust"), data: h.dust, borderColor: "#8d6e63", borderWidth: 2, borderDash: [6, 4], tension: .35 },
      ] },
      options: baseOpts({
        plugins: { legend: { display: true, labels: { boxWidth: 14, boxHeight: 2 } }, bands: { bands: levelBands("1f") } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
                  y: { beginAtZero: true, max: Math.round(Math.max(150, ...vals) * 1.15), grid: { color: "rgba(127,127,127,.12)" } } },
      }),
      plugins: [bandsPlugin, nowLinePlugin(nowIdx)],
    });

    const wh = d.weather && d.weather.hourly;
    if (!wh) return;
    const gustLimit = state.meta.alert.gust;
    const wvals = wh.wind_speed_10m.concat(wh.wind_gusts_10m).filter((v) => v !== null);
    const wNow = startIndex(wh.time, d.weather.current ? d.weather.current.time : d.air.current.time);
    makeChart("chartWind", {
      type: "line",
      data: { labels: hourlyLabels(wh.time), datasets: [
        { label: tr("windSpeed"), data: wh.wind_speed_10m, borderColor: "#1e88e5", backgroundColor: "rgba(30,136,229,.15)",
          borderWidth: 2.5, tension: .35, fill: true },
        { label: tr("gusts"), data: wh.wind_gusts_10m, borderColor: "#64b5f6", borderWidth: 1.8, borderDash: [6, 4], tension: .35 },
      ] },
      options: baseOpts({
        plugins: {
          legend: { display: true, labels: { boxWidth: 14, boxHeight: 2 } },
          bands: { bands: [{ from: gustLimit, to: 1000, color: "#e5393518" }] },
          tooltip: { callbacks: { afterBody: (items) => {
            const deg = (wh.wind_direction_10m || [])[items[0].dataIndex];
            return deg === undefined || deg === null ? "" : tr("direction") + ": " + windDir(deg);
          } } },
        },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
                  y: { beginAtZero: true, max: Math.round(Math.max(gustLimit + 3, ...wvals) * 1.2),
                       grid: { color: "rgba(127,127,127,.12)" }, title: { display: true, text: tr("ms") } } },
      }),
      plugins: [bandsPlugin, nowLinePlugin(wNow)],
    });
  }

  // ---------------- Xarita ----------------
  function initMap() {
    if (state.map || !window.L) return;
    state.map = L.map("map", { zoomControl: false, attributionControl: true, zoomSnap: 0.25 });
    // OpenStreetMap xaritasi: API kalit talab qilmaydi. Qorong'i mavzuda CSS filtr bilan qoraytiriladi.
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, className: "osm-tiles",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(state.map);
    state.mapLayers.cities = L.layerGroup().addTo(state.map);
    state.mapLayers.reports = L.layerGroup().addTo(state.map);
    state.mapLayers.arrows = L.layerGroup();
    state.mapLayers.dots = L.layerGroup();
    state.mapLayers.sensors = L.layerGroup();
    fitCities();
    renderCityMarkers();
    renderReportPins();
    renderLegend();
  }

  function fitCities() {
    const pts = state.meta.cities.map((c) => [c.lat, c.lon]);
    state.map.fitBounds(L.latLngBounds(pts), { padding: [28, 28], paddingTopLeft: [20, state.mapMode === "cloud" ? 70 : 20], paddingBottomRight: [20, 60] });
  }

  function renderLegend() {
    if (state.mapMode === "sensors") {
      const lim = [0, 50, 100, 150, 200, 300];
      $("#mapLegend").innerHTML = `<b>📡 ${esc(tr("sensorLegend"))}</b>` + AQI_COLORS.map((c, i) =>
        `<span><i style="background:${c}"></i>${lim[i]}${i < lim.length - 1 ? "–" + lim[i + 1] : "+"}</span>`).join("");
      return;
    }
    if (state.mapMode === "cloud") {
      $("#mapLegend").innerHTML = `<b>${esc(tr("cloudLegend"))}</b> 0 <span class="gradient-bar"></span> 300+`;
      return;
    }
    const lim = [0, ...state.meta.levels.limits];
    $("#mapLegend").innerHTML = `<b>${esc(tr("legend"))}</b>` + state.meta.levels.colors.map((c, i) =>
      `<span><i style="background:${c}"></i>${lim[i]}${i < lim.length - 1 ? "–" + lim[i + 1] : "+"}</span>`).join("") +
      `<span>📸 ${esc(tr("reportsLayer"))}</span>`;
  }

  function renderCityMarkers() {
    if (!state.map) return;
    const g = state.mapLayers.cities;
    g.clearLayers();
    const ov = state.overview || [];
    state.meta.cities.forEach((c) => {
      const o = ov.find((x) => x.key === c.key) || {};
      const has = o.pm10 !== undefined && o.pm10 !== null;
      const color = has ? levelColor(o.pm10) : "#90a4ae";
      const sel = state.place.key === c.key ? " sel" : "";
      const icon = L.divIcon({ className: "", html: `<div class="pin${sel}" style="background:${color}">${fmt(o.pm10)}</div>`, iconSize: [0, 0] });
      const wx = o.temp !== undefined && o.temp !== null ? `<br>${weatherEmoji(o.code)} ${fmt(o.temp)}° · 💨 ${fmt(o.wind)} ${tr("ms")}` : "";
      L.marker([c.lat, c.lon], { icon }).addTo(g).bindPopup(
        `<b>${esc(c.name[state.lang])}</b><br>PM10 ${fmt(o.pm10)} µg/m³ · ${esc(has ? levelName(o.pm10) : "—")}${wx}
        <button class="popup-btn" type="button" data-key="${c.key}">${esc(tr("select"))}</button>`);
    });
  }

  function renderReportPins() {
    if (!state.map) return;
    const g = state.mapLayers.reports;
    g.clearLayers();
    (state.reports || []).forEach((r) => {
      const icon = L.divIcon({ className: "", html: '<div class="report-pin">📸</div>', iconSize: [0, 0] });
      L.marker([r.lat, r.lon], { icon, zIndexOffset: 500 }).addTo(g).bindPopup(
        `<img src="/api/report_photo/${r.id}" alt=""><b>${esc(cityName(r.city))}</b> · ${esc(r.created.slice(5, 16).replace("T", " "))}
         ${r.caption ? "<br>" + esc(r.caption) : ""}`);
    });
  }

  // ----- Chang buluti (animatsiya) -----
  function dustRGBA(v) {
    if (v === null || v === undefined || v < 20) return [0, 0, 0, 0];
    const stops = [[20, [245, 210, 90, 0.05]], [50, [240, 185, 60, 0.45]], [100, [228, 145, 45, 0.65]],
      [180, [190, 105, 30, 0.8]], [300, [115, 55, 18, 0.88]]];
    for (let i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        const [v0, c0] = stops[i - 1], [v1, c1] = stops[i], f = (v - v0) / (v1 - v0);
        return c0.map((x, k) => x + (c1[k] - x) * f);
      }
    }
    return stops[stops.length - 1][1];
  }

  function cloudImage(frame) {
    const g = state.grid, rows = g.lats.length, cols = g.lons.length, vals = g.dust[frame];
    const small = document.createElement("canvas");
    small.width = cols; small.height = rows;
    const sctx = small.getContext("2d"), img = sctx.createImageData(cols, rows);
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        const [r, gg, b, a] = dustRGBA(vals[i * cols + j]);
        const p = ((rows - 1 - i) * cols + j) * 4;  // shimol tepada
        img.data[p] = r; img.data[p + 1] = gg; img.data[p + 2] = b; img.data[p + 3] = Math.round(a * 255);
      }
    }
    sctx.putImageData(img, 0, 0);
    const big = document.createElement("canvas");
    big.width = cols * 24; big.height = rows * 24;
    const bctx = big.getContext("2d");
    bctx.imageSmoothingEnabled = true;
    bctx.imageSmoothingQuality = "high";
    bctx.filter = "blur(5px)";
    bctx.drawImage(small, 0, 0, big.width, big.height);
    return big.toDataURL("image/png");
  }

  function arrowSVG() {
    return '<svg viewBox="0 0 24 24"><path d="M12 2 L18 14 L13 12 L13 22 L11 22 L11 12 L6 14 Z"/></svg>';
  }

  async function showCloud() {
    if (!state.grid) {
      $("#timeLabel").textContent = tr("cloudLoading");
      try { state.grid = await api("/api/grid"); } catch (e) { console.error(e); toast(tr("error")); return; }
    }
    const g = state.grid, half = g.step / 2;
    const bounds = [[g.lats[0] - half, g.lons[0] - half], [g.lats[g.lats.length - 1] + half, g.lons[g.lons.length - 1] + half]];
    if (!state.mapLayers.cloud) {
      state.mapLayers.cloud = L.imageOverlay(cloudImage(0), bounds, { opacity: 0.9, interactive: false });
    }
    state.mapLayers.cloud.addTo(state.map);
    // Shamol strelkalari (har ikkinchi nuqtada)
    const ag = state.mapLayers.arrows;
    ag.clearLayers();
    state._arrows = [];
    if (g.wind_dir) {
      g.lats.forEach((la, i) => g.lons.forEach((lo, j) => {
        if (i % 2 || j % 2) return;
        const m = L.marker([la, lo], { icon: L.divIcon({ className: "wind-arrow", html: arrowSVG(), iconSize: [18, 18] }), interactive: false });
        m.addTo(ag);
        state._arrows.push({ m, k: i * g.lons.length + j });
      }));
      ag.addTo(state.map);
    }
    const dots = state.mapLayers.dots;
    dots.clearLayers();
    state.meta.cities.forEach((c) => L.circleMarker([c.lat, c.lon], { radius: 3, color: "#fff", weight: 1, fillColor: "#263238", fillOpacity: 1 })
      .bindTooltip(c.name[state.lang], { direction: "top", offset: [0, -4] }).addTo(dots));
    dots.addTo(state.map);
    const slider = $("#timeSlider");
    slider.max = g.times.length - 1;
    slider.value = state.frame;
    setFrame(state.frame);
  }

  function setFrame(f) {
    const g = state.grid;
    if (!g) return;
    state.frame = f;
    state.mapLayers.cloud.setUrl(cloudImage(f));
    const t = g.times[f];
    $("#timeLabel").textContent = WEEKDAYS_SHORT[state.lang][new Date(t.slice(0, 10) + "T12:00").getDay()] + " " + t.slice(11, 16);
    $("#timeSlider").value = f;
    if (g.wind_dir) {
      state._arrows.forEach(({ m, k }) => {
        const el = m.getElement();
        const deg = g.wind_dir[f][k], sp = g.wind_speed ? g.wind_speed[f][k] : 5;
        if (el && deg !== null) {
          const svg = el.querySelector("svg");
          svg.style.transform = `rotate(${deg + 180}deg) scale(${clamp(0.7 + (sp || 0) / 12, 0.7, 1.6)})`;
        }
      });
    }
  }

  function togglePlay(force) {
    const play = force !== undefined ? force : !state.playing;
    clearInterval(state.playing);
    state.playing = null;
    $("#playBtn").textContent = play ? "❚❚" : "▶";
    if (!play || !state.grid) return;
    state.playing = setInterval(() => setFrame((state.frame + 1) % state.grid.times.length), 700);
  }

  function setMapMode(mode) {
    state.mapMode = mode;
    document.querySelectorAll("#mapSeg button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
    $("#timeline").hidden = mode !== "cloud";
    if (!state.map) return;
    if (mode !== "cloud") togglePlay(false);
    ["cities", "reports", "cloud", "arrows", "dots", "sensors"].forEach((k) => state.mapLayers[k] && state.map.removeLayer(state.mapLayers[k]));
    if (mode === "cloud") showCloud();
    else if (mode === "sensors") showSensors();
    else { state.mapLayers.cities.addTo(state.map); state.mapLayers.reports.addTo(state.map); }
    renderLegend();
  }

  async function showSensors() {
    if (!state.sensorsMap) {
      try { state.sensorsMap = (await api("/api/sensors")).stations; } catch { state.sensorsMap = []; }
    }
    const g = state.mapLayers.sensors;
    g.clearLayers();
    state.sensorsMap.forEach((st) => {
      const color = AQI_COLORS[usAqiIdx(st.aqi)];
      const icon = L.divIcon({ className: "", html: `<div class="pin sensor-pin" style="background:${color}">📡 ${fmt(st.aqi)}</div>`, iconSize: [0, 0] });
      L.marker([st.lat, st.lon], { icon }).addTo(g).bindPopup(
        `<b>${esc(st.name)}</b><br>${esc(tr("sensorLegend"))}: <b>${fmt(st.aqi)}</b> · ${esc(tv("aqiLevels")[usAqiIdx(st.aqi)])}
         ${st.time ? "<br><span style='opacity:.7'>" + esc(st.time) + "</span>" : ""}`);
    });
    if (state.mapMode === "sensors") g.addTo(state.map);
  }

  // ---------------- Statistika va ochiq arxiv ----------------
  const METRICS = {
    pm10: { label: () => "PM10", key: "pm10_mean", key2: "pm10_max", who: 45, unit: "µg/m³" },
    pm25: { label: () => "PM2.5", key: "pm25_mean", key2: "pm25_max", color: "#e07a3a", who: 15, unit: "µg/m³" },
    dust: { label: () => tr("dust"), key: "dust_mean", key2: "dust_max", color: "#a8794a", unit: "µg/m³" },
    aqi: { label: () => "AQI", key: "aqi_max", color: "#8e4ec6", unit: "" },
    temp: { label: () => tr("mTemp"), key: "temp_max", key2: "temp_min", color: "#f08a4b", color2: "#2c5aa8", unit: "°C" },
    wind: { label: () => tr("wind"), key: "wind_max", key2: "gust_max", color: "#2c5aa8", unit: "m/s" },
    risk: { label: () => tr("riskShort"), key: "risk", color: "#c63b4a", unit: "/100" },
  };

  async function loadHistory() {
    const q = placeQuery();
    if (state.history && state.historyFor === q) return renderStats();
    state.history = null;
    renderStats();
    let rows = null, source = "live";
    if (state.place.key) {
      try {
        const r = await api(`/api/archive?key=${encodeURIComponent(state.place.key)}&days=0`);
        if (r.days.length >= 7) { rows = r.days; source = "archive"; state.archiveSummary = r.summary; }
      } catch (e) { console.warn("archive", e); }
    }
    if (!rows) {  // arxiv yo'q (joylashuv yoki arxiv hali to'lmagan): so'nggi 92 kun
      try {
        const r = await api("/api/history?" + q);
        rows = r.days.map((d) => ({ date: d.date, pm10_mean: d.mean, pm10_max: d.max, pm25_mean: d.pm25, dust_max: d.dust }));
      } catch (e) { console.error(e); rows = []; }
    }
    state.history = rows;
    state.historyFor = q;
    state.historySource = source;
    renderStats();
  }

  function periodRows() {
    if (state.historyDays) return state.history.slice(-state.historyDays);
    if (state.histYear) return state.history.filter((d) => d.date.startsWith(String(state.histYear)));
    return state.history;
  }
  const historyYears = () => [...new Set((state.history || []).map((d) => +d.date.slice(0, 4)))].sort((a, b) => b - a);

  // Yillar bo'yicha qisqacha statistika (PM10)
  function yearlyStats() {
    const by = {};
    (state.history || []).forEach((d) => {
      if (d.pm10_mean === null || d.pm10_mean === undefined) return;
      const y = d.date.slice(0, 4), o = (by[y] = by[y] || { sum: 0, n: 0, dusty: 0, who: 0, max: 0, src: d.src });
      o.sum += d.pm10_mean; o.n++;
      if (d.pm10_mean > 100) o.dusty++;
      if (d.pm10_mean > 45) o.who++;
      o.max = Math.max(o.max, d.pm10_max || 0);
    });
    return Object.keys(by).sort((a, b) => b - a).map((y) => ({ year: +y, avg: by[y].sum / by[y].n, ...by[y] }));
  }

  function yearsOverviewHTML() {
    const ys = yearlyStats();
    if (!ys.length) return `<p class="muted small">${esc(tr("error"))}</p>`;
    const maxAvg = Math.max(...ys.map((y) => y.avg), 1);
    const rows = ys.map((y) => `<button type="button" class="yrow" data-year="${y.year}">
        <b>${y.year}</b>
        <span class="ybar"><i style="width:${(100 * y.avg / maxAvg).toFixed(0)}%;background:${levelColor(y.avg)}"></i></span>
        <span style="color:${levelColor(y.avg)}"><b>${fmt(y.avg)}</b></span>
        <span>${y.dusty}</span><span>${y.who}</span><span class="muted">${fmt(y.max)}</span></button>`).join("");
    return `<div class="muted small" style="margin:12px 0 6px">${esc(tr("yearlyTable"))} · ${esc(tr("tapYear"))}</div>
      <div class="yhead"><span>${esc(tr("colYear"))}</span><span></span><span>${esc(tr("colAvg"))}</span>
        <span>${esc(tr("colDusty"))}</span><span>${esc(tr("colWho"))}</span><span>${esc(tr("colMax"))}</span></div>
      <div class="ytable">${rows}</div>
      <p class="muted small" style="margin:8px 0 0">${esc(tr("srcNote"))}</p>`;
  }


  function rankingHTML() {
    const ov = (state.overview || []).filter((o) => o.pm10 !== null && o.pm10 !== undefined).slice().sort((a, b) => a.pm10 - b.pm10);
    if (!ov.length) return `<div class="skeleton" style="height:200px"></div>`;
    const max = Math.max(...ov.map((o) => o.pm10), 100);
    const medal = (i) => (i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i === ov.length - 1 ? "🔥" : i + 1);
    return ov.map((o, i) => `<div class="rank${o.key === state.place.key ? " me" : ""}">
      <span class="r-pos">${medal(i)}</span><span class="r-name">${esc(cityName(o.key))}</span>
      <span class="r-bar"><i style="width:${(100 * o.pm10 / max).toFixed(0)}%;background:${levelColor(o.pm10)}"></i></span>
      <b>${fmt(o.pm10)}</b></div>`).join("");
  }

  function historyHTML() {
    if (state.history === null) return `<div class="skeleton" style="height:260px"></div>`;
    if (state.historyDays === 0 && !state.histYear) return yearsModeHTML();
    const days = periodRows();
    if (!days.length) return `<p class="muted">${esc(tr("error"))}</p>`;
    const pm = days.filter((d) => d.pm10_mean !== null && d.pm10_mean !== undefined);
    const avg = pm.reduce((a, d) => a + d.pm10_mean, 0) / Math.max(1, pm.length);
    const dusty = pm.filter((d) => d.pm10_mean > 100).length;
    const who = pm.filter((d) => d.pm10_mean > 45).length;
    const worst = pm.reduce((a, d) => ((d.pm10_max || 0) > (a.pm10_max || 0) ? d : a), pm[0] || {});
    const firstDow = (new Date(days[0].date + "T12:00").getDay() + 6) % 7;
    let cells = '<i class="empty"></i>'.repeat(firstDow);
    cells += days.map((d) => `<i data-day="${d.date}" style="background:${d.pm10_mean !== null && d.pm10_mean !== undefined ? levelColor(d.pm10_mean) : "var(--soft)"}"></i>`).join("");
    const legend = state.meta.levels.colors.map((c) => `<i style="background:${c}"></i>`).join("");
    const periods = [[30, "days30"], [90, "days90"], [365, "days365"], [0, "yearsTab"]];
    const metricChips = Object.keys(METRICS).filter((k) => state.historySource === "archive" || ["pm10", "pm25", "dust"].includes(k))
      .map((k) => `<button type="button" data-metric="${k}" class="${k === state.histMetric ? "on" : ""}">${esc(METRICS[k].label())}</button>`).join("");
    return `${periodSegHTML()}${state.historyDays === 0 ? yearChipsHTML() : ""}
      <p class="small" style="margin:12px 0 0">${esc(state.historyDays === 0 && state.histYear
        ? tr("yearSummary", { y: state.histYear, n: days.length, d: dusty }) : tr("historySummary", { n: days.length, d: dusty }))}</p>
      <div class="tiles">
        <div class="tile"><div class="t-val" style="color:${levelColor(avg)}">${fmt(avg)}</div><div class="t-label">${esc(tr("avgPm"))}</div></div>
        <div class="tile"><div class="t-val">${dusty}</div><div class="t-label">${esc(tr("dustyDays"))}<br>${esc(tr("dustyDaysDesc"))}</div></div>
        <div class="tile"><div class="t-val">${who}</div><div class="t-label">${esc(tr("whoDays"))}<br>${esc(tr("whoDaysDesc"))}</div></div>
        <div class="tile day-link" data-day="${worst.date || ""}"><div class="t-val" style="color:${levelColor(worst.pm10_max)}">${fmt(worst.pm10_max)}</div>
          <div class="t-label">${esc(tr("worstDay"))}<br>${worst.date ? esc(shortDate(worst.date)) : "—"} ›</div></div>
      </div>
      <div class="muted small">${esc(tr("calendar"))} · ${esc(tr("tapDay"))}</div>
      <div class="calendar-wrap" id="calWrap"><div class="calendar" id="calendar">${cells}</div></div>
      <div class="cal-legend">${esc(tr("less"))} ${legend} ${esc(tr("more"))}</div>
      <div class="chips" id="metricChips">${metricChips}</div>
      <div class="chart-box tall"><canvas id="chartHist"></canvas></div>`;
  }

  function periodSegHTML() {
    const periods = [[30, "days30"], [90, "days90"], [365, "days365"], [0, "yearsTab"]];
    return `<div class="seg four" id="histSeg">${periods.map(([d, k]) =>
      `<button type="button" data-days="${d}" class="${state.historyDays === d ? "on" : ""}">${esc(tr(k))}</button>`).join("")}</div>`;
  }

  function yearChipsHTML() {
    const ys = historyYears();
    return `<div class="chips" id="yearChips"><button type="button" data-hyear="" class="${!state.histYear ? "on" : ""}">${esc(tr("allYears"))}</button>` +
      ys.map((y) => `<button type="button" data-hyear="${y}" class="${state.histYear === y ? "on" : ""}">${y}</button>`).join("") + "</div>";
  }

  function yearsModeHTML() {
    const metricChips = Object.keys(METRICS).filter((k) => state.historySource === "archive" || ["pm10", "pm25", "dust"].includes(k))
      .map((k) => `<button type="button" data-metric="${k}" class="${k === state.histMetric ? "on" : ""}">${esc(METRICS[k].label())}</button>`).join("");
    return `${periodSegHTML()}${yearChipsHTML()}${yearsOverviewHTML()}
      <div class="muted small" style="margin:14px 0 0">${esc(tr("monthlyChart"))}</div>
      <div class="chips" id="metricChips">${metricChips}</div>
      <div class="chart-box tall"><canvas id="chartHist"></canvas></div>`;
  }

  function coverageHTML() {
    const h = state.meta.history || {}, s = state.archiveSummary || {};
    const lines = [];
    if (s.first) lines.push(tr("covWeather", { from: s.first.slice(0, 4) }));
    if (s.pm_first) lines.push(tr("covPm", { from: s.pm_first.slice(0, 4) }));
    const e = h.eac4 || {};
    if (!e.key) lines.push(tr("covEac4Need"));
    else if (e.running) lines.push(tr("covEac4Run", { year: e.running }));
    else if (e.errors && e.errors.length) lines.push(tr("covEac4Err", { detail: (e.error_detail || "").slice(0, 120) }));
    if (h.history === "running" && !e.running) lines.push(tr("covImporting"));
    return lines.length ? `<div class="coverage"><b>${esc(tr("coverage"))}</b>${lines.map((l) => `<div>${esc(l)}</div>`).join("")}</div>` : "";
  }

  function archiveHTML() {
    const open = `<p class="muted small" style="margin:0 0 10px">${esc(tr("archiveOpen"))}</p>`;
    let info;
    if (state.historySource === "archive" && state.archiveSummary) {
      const a = state.archiveSummary;
      info = `<div class="archive-info"><div class="ai-num">${a.days}</div><div>${esc(tr("archiveInfo", { first: shortDate(a.first), last: shortDate(a.last) }))}</div></div>`;
    } else {
      info = `<p class="small" style="margin:0 0 10px">${esc(tr("archiveLive"))}</p>`;
    }
    const cityBtn = state.place.key
      ? `<button type="button" class="primary-btn" id="dlCity">${esc(tr("dlCity", { place: placeName() }))}</button>` : "";
    const first = +((state.archiveSummary && state.archiveSummary.first) || todayStr()).slice(0, 4);
    const last = +todayStr().slice(0, 4);
    if (!state.dlFrom || state.dlFrom < first) state.dlFrom = first;
    if (!state.dlTo || state.dlTo > last) state.dlTo = last;
    const opts = (sel) => Array.from({ length: last - first + 1 }, (_, i) => first + i)
      .map((y) => `<option value="${y}" ${y === sel ? "selected" : ""}>${y}</option>`).join("");
    return `<h4>${esc(tr("archiveTitle"))}</h4>${info}${coverageHTML()}${open}
      <div class="range"><label>${esc(tr("fromYear"))}<select id="dlFrom">${opts(state.dlFrom)}</select></label>
        <span>—</span><label>${esc(tr("toYear"))}<select id="dlTo">${opts(state.dlTo)}</select></label></div>
      ${cityBtn}<button type="button" class="ghost-btn" id="dlAll">${esc(tr("dlAll"))}</button>`;
  }

  function drawMonthlyChart() {
    const m = METRICS[state.histMetric] || METRICS.pm10, by = {};
    state.history.forEach((d) => {
      const v = d[m.key];
      if (v === null || v === undefined) return;
      const k = d.date.slice(0, 7), o = (by[k] = by[k] || { s: 0, n: 0 });
      o.s += v; o.n++;
    });
    const months = Object.keys(by).sort();
    const vals = months.map((k) => +(by[k].s / by[k].n).toFixed(1));
    const MS = MONTHS_SHORT[state.lang];
    makeChart("chartHist", {
      type: "line",
      data: { labels: months.map((k) => MS[+k.slice(5, 7) - 1] + " " + k.slice(2, 4)), datasets: [{
        label: m.label(), data: vals, borderColor: m.color || "#d84315", backgroundColor: (m.color || "#d84315") + "26",
        fill: true, borderWidth: 2, pointRadius: 0, tension: .3,
        segment: m.color ? undefined : { borderColor: (c) => levelColor(c.p1.parsed.y) },
      }] },
      options: baseOpts({
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${m.label()}: ${fmt(c.parsed.y, 1)} ${m.unit}` } } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
                  y: { beginAtZero: state.histMetric !== "temp", grid: { color: "rgba(127,127,127,.12)" } } },
        onClick: (_e, els) => { if (els.length) { state.histYear = +months[els[0].index].slice(0, 4); renderStats(); } },
      }),
    });
  }

  function drawHistoryChart() {
    if (!state.history || !state.history.length) return;
    if (state.historyDays === 0 && !state.histYear) return drawMonthlyChart();
    const days = periodRows(), m = METRICS[state.histMetric] || METRICS.pm10;
    const vals = days.map((d) => d[m.key] ?? null);
    const many = days.length > 120;
    const main = {
      label: m.label() + (m.key2 ? (m.key.endsWith("_max") ? " (" + tr("max") + ")" : "") : ""),
      data: vals, borderRadius: 3, borderWidth: many ? 1.5 : 0, pointRadius: 0, tension: .3,
      backgroundColor: m.color ? m.color + (many ? "33" : "cc") : vals.map((v) => levelColor(v) + "dd"),
      borderColor: m.color || "#d84315", fill: many,
    };
    const datasets = [main];
    if (m.key2 && (state.histMetric === "temp" || state.histMetric === "wind")) {
      datasets.push({ type: "line", label: state.histMetric === "temp" ? "min" : tr("gusts"), data: days.map((d) => d[m.key2] ?? null),
        borderColor: m.color2 || "#64b5f6", borderWidth: 1.6, borderDash: [5, 4], pointRadius: 0, tension: .3 });
    }
    makeChart("chartHist", {
      type: many ? "line" : "bar",
      data: { labels: days.map((d) => shortDate(d.date)), datasets },
      options: baseOpts({
        plugins: { legend: { display: datasets.length > 1, labels: { boxWidth: 14, boxHeight: 2 } },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y, 1)} ${m.unit}` } } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                  y: { beginAtZero: state.histMetric !== "temp", grid: { color: "rgba(127,127,127,.12)" } } },
        onClick: (_e, els) => { if (els.length) openDay(days[els[0].index].date); },
      }),
      plugins: m.who ? [{
        id: "who",
        afterDatasetsDraw(chart) {
          const { ctx, chartArea: ca, scales: { y } } = chart;
          const py = y.getPixelForValue(m.who);
          if (py < ca.top || py > ca.bottom) return;
          ctx.save(); ctx.strokeStyle = "#e53935"; ctx.setLineDash([5, 4]);
          ctx.beginPath(); ctx.moveTo(ca.left, py); ctx.lineTo(ca.right, py); ctx.stroke();
          ctx.fillStyle = "#e53935"; ctx.font = "11px " + Chart.defaults.font.family;
          ctx.fillText(tr("whoShort", { v: m.who }), ca.left + 4, py - 4); ctx.restore();
        },
      }] : [],
    });
  }

  // ----- Kun tafsilotlari -----
  function dayDetailHTML(d) {
    const dt = new Date(d.date + "T12:00");
    const row = (label, val) => `<div class="dl-row"><span class="muted">${esc(label)}</span><b>${val}</b></div>`;
    const v = (x, dec = 0, unit = "") => (x === null || x === undefined ? "—" : `${fmt(x, dec)}${unit ? " " + unit : ""}`);
    const pair = (a, b, unit, dec = 0) => `${v(a, dec)} / ${v(b, dec)}${unit ? " " + unit : ""}`;
    const sensor = d.sensor_n
      ? row(tr("dSensor") + " (" + tr("dSensorN", { n: d.sensor_n }) + ")", `AQI ${v(d.sensor_aqi)} · PM2.5 ${v(d.sensor_pm25)} · PM10 ${v(d.sensor_pm10)}`)
      : row(tr("dSensor"), `<span class="muted">${esc(tr("dSensorNone"))}</span>`);
    return `<h3>${esc(WEEKDAYS_LONG[state.lang][dt.getDay()])}, ${esc(shortDate(d.date))} ${d.date.slice(0, 4)}</h3>
      <p class="muted small" style="margin:-6px 0 12px">📍 ${esc(placeName())}</p>
      ${d.pm10_mean !== undefined && d.pm10_mean !== null ? `<div class="day-badge" style="--lc:${levelColor(d.pm10_mean)}">
        <b>${fmt(d.pm10_mean)}</b><span>PM10 µg/m³ · ${esc(levelName(d.pm10_mean))}</span></div>` : ""}
      <div class="dl-title">${esc(tr("airQuality"))} <span class="muted">(${esc(tr("dMean"))} / ${esc(tr("max"))})</span></div>
      ${row("PM10", pair(d.pm10_mean, d.pm10_max, "µg/m³"))}
      ${row("PM2.5", pair(d.pm25_mean, d.pm25_max, "µg/m³"))}
      ${row(tr("dust"), pair(d.dust_mean, d.dust_max, "µg/m³"))}
      ${row(tr("aod"), v(d.aod_mean, 2))}
      ${row(tr("usAqi") + " (" + tr("max") + ")", v(d.aqi_max))}
      ${row(tr("ozone"), v(d.o3_mean, 0, "µg/m³"))}${row("NO₂", v(d.no2_mean, 0, "µg/m³"))}
      ${row("SO₂", v(d.so2_mean, 0, "µg/m³"))}${row("CO", v(d.co_mean, 0, "µg/m³"))}
      ${row(tr("uv") + " (" + tr("max") + ")", v(d.uv_max, 1))}
      <div class="dl-title">${esc(tr("weather"))}</div>
      ${row(tr("mTemp") + " (min / " + tr("max") + ")", pair(d.temp_min, d.temp_max, "°C"))}
      ${row(tr("humidity"), v(d.rh_mean, 0, "%"))}
      ${row(tr("wind") + " / " + tr("gusts") + " (" + tr("max") + ")", pair(d.wind_max, d.gust_max, tr("ms")))}
      ${row(tr("precip"), v(d.precip_sum, 1, tr("mm")))}
      ${row(tr("riskShort"), d.risk === null || d.risk === undefined ? "—" : `<span style="color:${RISK_COLORS[d.risk < 25 ? 0 : d.risk < 50 ? 1 : d.risk < 75 ? 2 : 3]}">${fmt(d.risk)}/100</span>`)}
      ${sensor}`;
  }

  function openDay(date) {
    const d = (state.history || []).find((x) => x.date === date);
    if (!d) return;
    haptic();
    $("#dayContent").innerHTML = dayDetailHTML(d);
    openSheet("daySheet", true);
  }

  async function downloadArchive(all) {
    const key = all ? "all" : state.place.key;
    if (!key) return;
    const from = Math.min(state.dlFrom, state.dlTo), to = Math.max(state.dlFrom, state.dlTo);
    const url = `${location.origin}/api/archive.csv?key=${encodeURIComponent(key)}&from=${from}&to=${to}&lang=${state.lang}`;
    haptic("light");
    if (inTelegram) {
      try {  // eng ishonchli: bot faylni chatga yuboradi
        await api("/api/archive/send", { method: "POST", body: JSON.stringify({ key, from: String(from), to: String(to), lang: state.lang }) });
        haptic("success");
        return toast(tr("archiveSent"));
      } catch (e) { console.warn("send", e); }
      try { if (tg.downloadFile) return tg.downloadFile({ url, file_name: `chang_arxiv_${key}_${from}-${to}.csv` }); } catch { /* eski versiya */ }
      return tg.openLink(url);
    }
    const a = document.createElement("a");
    a.href = url; a.download = "";
    document.body.appendChild(a); a.click(); a.remove();
  }

  // Orol dengizi: sxematik suv havzalari (har yil uchun)
  const ARAL = {
    1960: [{ cx: 150, cy: 120, rx: 105, ry: 92 }],
    1980: [{ cx: 150, cy: 125, rx: 88, ry: 80 }],
    1989: [{ cx: 130, cy: 52, rx: 42, ry: 24 }, { cx: 160, cy: 145, rx: 68, ry: 62 }],
    2005: [{ cx: 128, cy: 50, rx: 40, ry: 23 }, { cx: 118, cy: 150, rx: 18, ry: 55 }, { cx: 178, cy: 150, rx: 38, ry: 46 }],
    2014: [{ cx: 128, cy: 50, rx: 41, ry: 23 }, { cx: 116, cy: 152, rx: 13, ry: 50 }],
    2024: [{ cx: 128, cy: 50, rx: 41, ry: 23 }, { cx: 114, cy: 150, rx: 10, ry: 44 }],
  };

  function aralHTML() {
    const y = state.aralYear, shapes = ARAL[y];
    const water = shapes.map((s) => `<ellipse class="water" cx="${s.cx}" cy="${s.cy}" rx="${s.rx}" ry="${s.ry}" fill="#3a8fd6" opacity=".85"/>`).join("");
    let saxaul = "";
    if (y >= 2014) {
      for (let i = 0; i < 26; i++) {
        const a = i * 2.4, r = 40 + (i * 37) % 55;
        saxaul += `<circle cx="${(175 + Math.cos(a) * r * 0.55).toFixed(0)}" cy="${(150 + Math.sin(a) * r * 0.6).toFixed(0)}" r="3" fill="#5d8a3a" opacity=".8"/>`;
      }
    }
    const years = Object.keys(ARAL).map((k) => `<button type="button" data-year="${k}" class="${+k === y ? "on" : ""}">${k === "2024" ? "2020+" : k}</button>`).join("");
    return `<h4>${esc(tr("aralTitle"))}</h4><p class="small muted" style="margin:0">${esc(tr("aralIntro"))}</p>
      <svg class="aral-svg" viewBox="0 0 300 240" role="img" aria-label="Aral">
        <ellipse cx="150" cy="120" rx="105" ry="92" fill="none" stroke="#7a5b2e" stroke-width="1.5" stroke-dasharray="5 4" opacity=".6"/>
        ${water}${saxaul}
        <text x="150" y="232" text-anchor="middle" font-size="10" fill="#7a5b2e">${esc(tr("aralSchema"))} · ${y === 2024 ? "2020+" : y}</text>
        <text x="245" y="215" font-size="10" fill="#7a5b2e">Mo'ynoq ●</text>
      </svg>
      <div class="years" id="aralYears">${years}</div>
      <p class="aral-text">${esc(tv("aral")[y])}</p>`;
  }

  function renderStats() {
    $("#view-stats").innerHTML =
      `<div class="card"><h4>${esc(tr("ranking"))}</h4>${rankingHTML()}</div>
       <div class="card"><h4>${esc(tr("history"))} · ${esc(placeName())}</h4>${historyHTML()}</div>
       ${state.history !== null ? `<div class="card" id="archiveCard">${archiveHTML()}</div>` : ""}
       <div class="card" id="aralCard">${aralHTML()}</div>
       <p class="footer-note">${esc(tr("source"))}</p>`;
    decorateHeads($("#view-stats"));
    drawHistoryChart();
    const cw = $("#calWrap");
    if (cw) cw.scrollLeft = cw.scrollWidth;
  }

  // ---------------- Sozlamalar ----------------
  function renderSettings() {
    const s = state.settings;
    const disabled = inTelegram ? "" : "disabled";
    const tgHtml = (txt) => esc(txt).replace(/&lt;(\/?)(b|i)&gt;/g, "<$1$2>").replace(/\n/g, "<br>");
    const names = tv("profiles"), icons = tv("profileIcons");
    const themeNames = { auto: tr("themeAuto"), light: tr("themeLight"), dark: tr("themeDark") };
    let html = `<div class="card"><h4>${esc(tr("theme"))}</h4><div class="seg">` +
      THEMES.map((m) => `<button type="button" data-theme-set="${m}" class="${m === state.theme ? "on" : ""}">${esc(themeNames[m])}</button>`).join("") +
      `</div><p class="muted small" style="margin:8px 0 0">${esc(tr("themeDesc"))}</p></div>`;
    html += `<div class="card"><h4>${esc(tr("language"))}</h4><div class="seg">` +
      LANGS.map((l) => `<button type="button" data-lang="${l}" class="${l === state.lang ? "on" : ""}">${{ uz: "O'zbekcha", ru: "Русский", en: "English" }[l]}</button>`).join("") +
      `</div></div>`;
    html += `<div class="card"><h4>${esc(tr("profile"))}</h4><p class="muted small" style="margin:-4px 0 10px">${esc(tr("profileDesc"))}</p>
      <div class="profiles">${PROFILES.map((p) => `<button type="button" class="profile-opt${p === state.profile ? " on" : ""}" data-profile="${p}">
        <span>${icons[p]}</span><span>${esc(names[p])}</span></button>`).join("")}</div>
      ${SENSITIVE.includes(state.profile) ? `<p class="muted small" style="margin:10px 0 0">${esc(tr("profileAlertNote", { n: state.meta.alert.sensitive_pm10 }))}</p>` : ""}</div>`;
    html += `<div class="card"><h4>${esc(tr("notifications"))}</h4>
      <div class="toggle-row"><div><div class="t-title">${esc(tr("alerts"))}</div><div class="muted small">${esc(tr("alertsDesc"))}</div></div>
        <label class="switch"><input type="checkbox" id="tAlerts" ${s && s.alerts ? "checked" : ""} ${disabled}><span></span></label></div>
      <div class="toggle-row"><div><div class="t-title">${esc(tr("daily"))}</div><div class="muted small">${esc(tr("dailyDesc"))}</div></div>
        <label class="switch"><input type="checkbox" id="tDaily" ${s && s.daily ? "checked" : ""} ${disabled}><span></span></label></div>
      <p class="muted small" style="margin:8px 0 0">${esc(inTelegram ? tr("notifCity", { place: placeName() }) : tr("onlyTg"))}</p></div>`;
    html += `<div class="card">
      <details><summary>${esc(tr("tips"))}</summary><div class="content">${tgHtml(state.meta.tips[state.lang])}</div></details>
      <details><summary>${esc(tr("about"))}</summary><div class="content">${tgHtml(state.meta.info[state.lang])}</div></details>
    </div>`;
    html += `<p class="footer-note">${esc(tr("source"))}</p>`;
    $("#view-settings").innerHTML = html;
    decorateHeads($("#view-settings"));
  }

  async function saveSettings(patch, silent) {
    if (!inTelegram) return;
    try {
      state.settings = await api("/api/me", { method: "POST", body: JSON.stringify(patch) });
      if (!silent) toast(tr("saved"));
    } catch (e) {
      console.error(e);
      if (!silent) toast(tr("error"));
    }
  }

  function setTheme(m) {
    if (!THEMES.includes(m) || m === state.theme) return;
    state.theme = m;
    store.set("theme", m);
    haptic();
    applyTheme();
    if (state.data) renderAll(); else renderSettings();
  }

  function setProfile(p) {
    if (!PROFILES.includes(p)) return;
    state.profile = p;
    store.set("profile", p);
    haptic();
    renderSettings();
    if (state.data) renderHome();
    saveSettings({ profile: p });
    if (!inTelegram) toast(tr("saved"));
  }

  // ---------------- Bo'ron rasmini yuborish ----------------
  function openReportSheet() {
    if (!inTelegram) return toast(tr("reportOnlyTg"));
    state.photoBlob = null;
    $("#photoPreview").hidden = true;
    $("#photoPickText").hidden = false;
    $("#captionInput").value = "";
    $("#sendReportBtn").disabled = true;
    $("#reportPlace").textContent = tr("reportPlace", { place: placeName() });
    openSheet("reportSheet", true);
  }

  // Rasmni kichraytirib JPEG qiladi (tezroq yuklanishi uchun)
  function compressImage(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const max = 1600, k = Math.min(1, max / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        c.toBlob((b) => (b ? resolve(b) : reject(new Error("blob"))), "image/jpeg", 0.85);
        URL.revokeObjectURL(img.src);
      };
      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  }

  async function onPhotoPicked(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      state.photoBlob = await compressImage(file);
      const prev = $("#photoPreview");
      prev.src = URL.createObjectURL(state.photoBlob);
      prev.hidden = false;
      $("#photoPickText").hidden = true;
      $("#sendReportBtn").disabled = false;
    } catch (err) {
      console.error(err);
      toast(tr("error"));
    }
  }

  async function sendReport() {
    if (!state.photoBlob) return;
    const btn = $("#sendReportBtn");
    btn.disabled = true;
    btn.textContent = tr("sending");
    const fd = new FormData();
    fd.append("photo", state.photoBlob, "storm.jpg");
    fd.append("caption", $("#captionInput").value.trim());
    const p = state.place;
    if (p.key) fd.append("key", p.key); else { fd.append("lat", p.lat); fd.append("lon", p.lon); }
    try {
      const r = await api("/api/report", { method: "POST", body: fd });
      haptic("success");
      toast(r.status === "pending" ? tr("reportPending") : tr("reportSaved"));
      openSheet("reportSheet", false);
      loadReports();
    } catch (e) {
      console.error(e);
      haptic("error");
      toast(e.status === 429 ? tr("reportLimit") : tr("error"));
    } finally {
      btn.textContent = tr("send");
      btn.disabled = false;
    }
  }

  // ---------------- Shahar tanlash ----------------
  function renderCityList() {
    const ov = state.overview || [];
    $("#cityList").innerHTML = state.meta.cities.map((c) => {
      const o = ov.find((x) => x.key === c.key);
      const pm = o && o.pm10 !== null && o.pm10 !== undefined
        ? `<span class="ci-pm" style="background:${levelColor(o.pm10)}">${fmt(o.pm10)}</span>` : "";
      return `<button type="button" class="city-item${state.place.key === c.key ? " on" : ""}" data-key="${c.key}">
        <span>${esc(c.name[state.lang])}</span>${pm}</button>`;
    }).join("");
  }

  function openSheet(id, show) {
    document.querySelectorAll(".sheet").forEach((s) => { if (s.id !== id || !show) s.classList.remove("show"); });
    if (show) $("#" + id).classList.add("show");
    $("#sheetBackdrop").classList.toggle("show", show);
    if (show && id === "citySheet") renderCityList();
  }

  function selectPlace(place) {
    state.place = place;
    store.set("place", place);
    haptic("light");
    openSheet("citySheet", false);
    if (state.map) state.map.closePopup();
    state.history = null;
    showView("home");
    loadData("skeleton");
    if (place.key) saveSettings({ city: place.key });
    else saveSettings({ city: "loc", lat: place.lat, lon: place.lon });
  }

  function useLocation() {
    const done = (lat, lon) => selectPlace({ lat, lon });
    const fail = () => toast(tr("locDenied"));
    try {
      const lm = tg && tg.LocationManager;
      if (lm && tg.isVersionAtLeast && tg.isVersionAtLeast("8.0")) {
        lm.init(() => {
          if (!lm.isLocationAvailable) return browserLoc();
          lm.getLocation((loc) => (loc ? done(loc.latitude, loc.longitude) : fail()));
        });
        return;
      }
    } catch { /* brauzer usuliga o'tamiz */ }
    browserLoc();
    function browserLoc() {
      if (!navigator.geolocation) return fail();
      navigator.geolocation.getCurrentPosition((p) => done(p.coords.latitude, p.coords.longitude), fail,
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
    }
  }

  // ---------------- Bo'limlar ----------------
  function showView(view) {
    state.view = view;
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
    window.scrollTo({ top: 0 });
    if (view !== "map") togglePlay(false);
    if (view === "forecast" && state.data) drawForecastCharts();
    if (view === "stats") loadHistory();
    if (view === "map") {
      initMap();
      setTimeout(() => { if (state.map) { state.map.invalidateSize(); fitCities(); } }, 60);
    }
  }

  function setLang(lang) {
    if (!LANGS.includes(lang) || lang === state.lang) return;
    state.lang = lang;
    store.set("lang", lang);
    haptic();
    if (state.data) renderAll(); else applyI18n();
    renderCityList();
    if (state.map) { renderCityMarkers(); renderReportPins(); renderLegend(); if (state.mapMode === "cloud") setFrame(state.frame); }
    saveSettings({ lang });
  }

  // ---------------- Hodisalar ----------------
  function bindEvents() {
    document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => { haptic(); showView(t.dataset.view); }));
    $("#cityBtn").addEventListener("click", () => { haptic(); openSheet("citySheet", true); });
    $("#sheetBackdrop").addEventListener("click", () => openSheet("", false));
    $("#refreshBtn").addEventListener("click", () => { haptic("light"); state.history = null; loadData(); });
    $("#locBtn").addEventListener("click", useLocation);
    $("#cityList").addEventListener("click", (e) => {
      const b = e.target.closest(".city-item");
      if (b) selectPlace({ key: b.dataset.key });
    });
    $("#mapSeg").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-mode]");
      if (b) { haptic(); setMapMode(b.dataset.mode); }
    });
    $("#playBtn").addEventListener("click", () => { haptic(); togglePlay(); });
    $("#timeSlider").addEventListener("input", (e) => { togglePlay(false); setFrame(+e.target.value); });
    $("#photoInput").addEventListener("change", onPhotoPicked);
    $("#sendReportBtn").addEventListener("click", sendReport);
    document.addEventListener("click", (e) => {
      const p = e.target.closest(".popup-btn");
      if (p) selectPlace({ key: p.dataset.key });
      const l = e.target.closest("[data-lang]");
      if (l) setLang(l.dataset.lang);
      const th = e.target.closest("[data-theme-set]");
      if (th) setTheme(th.dataset.themeSet);
      const ext = e.target.closest(".ext-link");
      if (ext) { e.preventDefault(); if (tg && tg.openLink) tg.openLink(ext.href); else window.open(ext.href, "_blank", "noopener"); }
      const pr = e.target.closest("[data-profile]");
      if (pr) setProfile(pr.dataset.profile);
      if (e.target.closest("#openReport")) { haptic(); openReportSheet(); }
      const hd = e.target.closest("#histSeg button[data-days]");
      if (hd) { haptic(); state.historyDays = +hd.dataset.days; state.histYear = null; renderStats(); }
      const hy = e.target.closest("#yearChips button[data-hyear], .yrow[data-year]");
      if (hy) { haptic(); state.histYear = +(hy.dataset.hyear ?? hy.dataset.year) || null; renderStats(); }
      const mc = e.target.closest("#metricChips button[data-metric]");
      if (mc) { haptic(); state.histMetric = mc.dataset.metric; document.querySelectorAll("#metricChips button").forEach((b) => b.classList.toggle("on", b === mc)); drawHistoryChart(); }
      const dl = e.target.closest(".day-link[data-day]");
      if (dl && dl.dataset.day) openDay(dl.dataset.day);
      if (e.target.closest("#dlCity")) downloadArchive(false);
      if (e.target.closest("#dlAll")) downloadArchive(true);
      const y = e.target.closest("#aralYears button[data-year]");
      if (y) { haptic(); state.aralYear = +y.dataset.year; $("#aralCard").innerHTML = aralHTML(); decorateHeads($("#view-stats")); }
      const cell = e.target.closest("#calendar i[data-day]");
      if (cell) openDay(cell.dataset.day);
    });
    document.addEventListener("change", (e) => {
      if (e.target.id === "dlFrom") state.dlFrom = +e.target.value;
      if (e.target.id === "dlTo") state.dlTo = +e.target.value;
      if (e.target.id === "tAlerts") { haptic(); saveSettings({ alerts: e.target.checked }); }
      if (e.target.id === "tDaily") { haptic(); saveSettings({ daily: e.target.checked }); }
    });
    if (tg) tg.onEvent("themeChanged", () => { if (state.theme !== "auto") return; applyTheme(); if (state.data) renderAll(); });
  }

  // ---------------- Boshlash ----------------
  async function init() {
    if (tg) { tg.ready(); tg.expand(); try { tg.disableVerticalSwipes && tg.disableVerticalSwipes(); } catch { /* */ } }
    state.theme = store.get("theme", "auto");
    if (!THEMES.includes(state.theme)) state.theme = "auto";
    applyTheme();
    const tgLang = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && (tg.initDataUnsafe.user.language_code || "").slice(0, 2);
    state.lang = store.get("lang", LANGS.includes(tgLang) ? tgLang : "uz");
    state.place = store.get("place", { key: "toshkent" });
    state.profile = store.get("profile", "none");
    applyI18n();
    bindEvents();
    renderSkeleton();
    try {
      state.meta = await api("/api/meta");
    } catch (e) {
      console.error(e);
      return renderError();
    }
    applyI18n();
    const sensBtn = $('#mapSeg [data-mode="sensors"]');
    if (sensBtn) sensBtn.hidden = !state.meta.sensors;
    if (inTelegram) {
      try {
        state.settings = await api("/api/me");
        if (state.settings.lang && !store.get("lang", null)) state.lang = state.settings.lang;
        if (state.settings.profile && PROFILES.includes(state.settings.profile)) state.profile = state.settings.profile;
        const keys = state.meta.cities.map((c) => c.key);
        if (state.settings.city && keys.includes(state.settings.city)) {
          state.place = { key: state.settings.city };
        } else if (state.settings.city === "loc" && state.settings.lat !== null) {
          state.place = { lat: state.settings.lat, lon: state.settings.lon };
        } else {  // birinchi kirish: bildirishnomalar ishlashi uchun joyni serverga saqlaymiz
          const p = state.place;
          saveSettings(p.key ? { city: p.key, lang: state.lang, profile: state.profile }
            : { city: "loc", lat: p.lat, lon: p.lon, lang: state.lang, profile: state.profile }, true);
        }
      } catch (e) { console.warn("settings", e); }
    }
    await loadData("skeleton");
  }

  init();
})();
