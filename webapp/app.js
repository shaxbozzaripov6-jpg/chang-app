/* Chang Monitor: Telegram Mini App */
(() => {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp;
  const inTelegram = !!(tg && tg.initData);
  const $ = (s, el = document) => el.querySelector(s);
  const LANGS = ["uz", "ru", "en"];

  const state = {
    lang: "uz",
    place: { key: "toshkent" },   // {key} yoki {lat, lon}
    meta: null,
    data: null,
    overview: null,
    settings: null,                // serverdagi sozlamalar (faqat Telegram ichida)
    view: "home",
    charts: {},
    map: null,
    mapMarkers: [],
  };

  // ---------------- Yordamchilar ----------------
  const store = {
    get(k, d) { try { const v = localStorage.getItem("chang_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("chang_" + k, JSON.stringify(v)); } catch { /* maxfiy rejim */ } },
  };

  function tr(key, vars) {
    let s = (I18N[state.lang] && I18N[state.lang][key]) || I18N.uz[key] || key;
    if (vars) for (const k in vars) s = s.replace("{" + k + "}", vars[k]);
    return s;
  }
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const haptic = (type = "selection") => {
    try {
      if (!tg || !tg.HapticFeedback) return;
      if (type === "selection") tg.HapticFeedback.selectionChanged();
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

  function whenText(iso) {
    const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Tashkent" });
    return iso.slice(0, 10) === today ? tr("today") : tr("tomorrow");
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 1800);
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    if (inTelegram) headers["X-Init-Data"] = tg.initData;
    if (opts.body) headers["Content-Type"] = "application/json";
    const r = await fetch(path, Object.assign({}, opts, { headers }));
    if (!r.ok) throw new Error(path + " → " + r.status);
    return r.json();
  }

  function placeQuery() {
    const p = state.place;
    return p.key ? "key=" + encodeURIComponent(p.key) : "lat=" + p.lat.toFixed(3) + "&lon=" + p.lon.toFixed(3);
  }

  // ---------------- Mavzu (yorug'/qorong'i) ----------------
  function applyTheme() {
    const dark = tg ? tg.colorScheme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.scheme = dark ? "dark" : "light";
    if (tg) {
      try {
        const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
        tg.setHeaderColor("secondary_bg_color");
        tg.setBackgroundColor(bg || "secondary_bg_color");
      } catch { /* eski versiya */ }
    }
    if (window.Chart) {
      Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue("--hint").trim() || "#888";
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    }
  }

  // ---------------- Matnlarni joylash ----------------
  function applyI18n() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = tr(el.dataset.i18n); });
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
    } catch (e) {
      console.error(e);
      renderError();
    } finally {
      btn.classList.remove("spin");
    }
    api("/api/overview").then((o) => {
      state.overview = o.cities;
      renderCityList();
      if (state.map) renderMapMarkers();
    }).catch(() => {});
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
    document.querySelectorAll(".retry").forEach((b) => b.addEventListener("click", () => loadData("skeleton")));
  }

  function renderAll() {
    applyI18n();
    renderHome();
    renderForecast();
    renderSettings();
    if (state.map) renderMapMarkers();
  }

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
                stroke="${colors[i]}" stroke-width="12" fill="none" stroke-linecap="butt" opacity=".9"/>`;
    }
    const [mx, my] = pt(pm10 || 0, r);  // yoy ustidagi belgi
    return `<svg class="gauge" viewBox="0 0 150 92" aria-hidden="true">${arcs}
      <circle cx="${mx.toFixed(1)}" cy="${my.toFixed(1)}" r="8" fill="${levelColor(pm10)}" stroke="var(--card)" stroke-width="3"/>
      <text x="${cx}" y="${cy - 10}" text-anchor="middle" class="gauge-val">${fmt(pm10)}</text>
      <text x="${cx}" y="${cy + 8}" text-anchor="middle" class="gauge-unit">PM10 µg/m³</text></svg>`;
  }

  function compassSVG(deg) {
    const letters = state.lang === "ru" ? ["С", "В", "Ю", "З"] : state.lang === "uz" ? ["Sh", "Shq", "J", "G'"] : ["N", "E", "S", "W"];
    const rot = deg === null || deg === undefined ? 0 : deg + 180;  // strelka shamol qayoqqa esayotganini ko'rsatadi
    let ticks = "";
    for (let i = 0; i < 24; i++) {
      const a = (i * 15) * Math.PI / 180, r1 = i % 6 === 0 ? 38 : 41;
      ticks += `<line x1="${50 + r1 * Math.sin(a)}" y1="${50 - r1 * Math.cos(a)}" x2="${50 + 44 * Math.sin(a)}" y2="${50 - 44 * Math.cos(a)}" stroke="var(--hint)" stroke-width="${i % 6 === 0 ? 2 : 1}" opacity=".6"/>`;
    }
    return `<svg class="compass" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="46" fill="var(--soft)"/>${ticks}
      <text x="50" y="22" text-anchor="middle" font-size="10" font-weight="700" fill="var(--text)">${letters[0]}</text>
      <text x="80" y="54" text-anchor="middle" font-size="10" fill="var(--hint)">${letters[1]}</text>
      <text x="50" y="86" text-anchor="middle" font-size="10" fill="var(--hint)">${letters[2]}</text>
      <text x="20" y="54" text-anchor="middle" font-size="10" fill="var(--hint)">${letters[3]}</text>
      <g class="needle" style="transform: rotate(${rot}deg)">
        <path d="M50 24 L57 52 L50 47 L43 52 Z" fill="var(--accent)"/>
        <path d="M50 76 L54 52 L50 55 L46 52 Z" fill="var(--hint)" opacity=".6"/>
      </g></svg>`;
  }

  function renderHome() {
    const d = state.data, a = d.air.current, w = (d.weather && d.weather.current) || null;
    const color = levelColor(a.pm10);
    let html = "";

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

    html += `<div class="hero"><img id="heroImg" alt="${esc(placeName())}"
      src="/api/scene?${placeQuery()}&lang=${state.lang}&t=${encodeURIComponent(a.time)}"></div>`;

    html += `<div class="card"><h4>${esc(tr("airQuality"))}</h4>
      <div class="aqi">${gaugeSVG(a.pm10)}
        <div><p class="level-name" style="--lc:${color}">${esc(levelName(a.pm10))}</p>
        <p class="level-advice">${esc(levelAdvice(a.pm10))}</p></div></div>
      <div class="metrics">
        <div class="metric"><div class="m-label">${tr("pm25")}</div><div class="m-val">${fmt(a.pm2_5)}<small>µg/m³</small></div></div>
        <div class="metric"><div class="m-label">${esc(tr("dust"))}</div><div class="m-val">${fmt(a.dust)}<small>µg/m³</small></div></div>
        <div class="metric"><div class="m-label">${esc(tr("aod"))}</div><div class="m-val">${fmt(a.aerosol_optical_depth, 2)}</div></div>
        <div class="metric"><div class="m-label">${esc(tr("humidity"))}</div><div class="m-val">${w ? fmt(w.relative_humidity_2m) : "—"}<small>%</small></div></div>
      </div></div>`;

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
    html += `<p class="footer-note">${esc(tr("updated"))}: ${esc(a.time.replace("T", " "))}</p>`;

    $("#view-home").innerHTML = html;
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

  // Grafik foniga rangli xavf zonalarini chizuvchi plagin
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

  // ---------------- Prognoz sahifasi ----------------
  function renderForecast() {
    const d = state.data;
    const daily = d.weather && d.weather.daily;
    const wd = WEEKDAYS_LONG[state.lang];
    let html = `<div class="days">`;
    d.days.forEach((day) => {
      const dt = new Date(day.date + "T12:00");
      const wi = daily ? daily.time.indexOf(day.date) : -1;
      const w = (k) => (wi >= 0 ? daily[k][wi] : null);
      html += `<div class="day" style="--lc:${levelColor(day.pm10)}">
        <div class="d-name">${esc(wd[dt.getDay()])}</div>
        <div class="d-date">${day.date.slice(8, 10)}.${day.date.slice(5, 7)}</div>
        <div class="d-emoji">${wi >= 0 ? weatherEmoji(w("weather_code")) : "🌫"}</div>
        ${wi >= 0 ? `<div class="d-temp">${fmt(w("temperature_2m_max"))}° <span>${fmt(w("temperature_2m_min"))}°</span></div>` : ""}
        <div class="d-pm">PM10 ${fmt(day.pm10)}</div>
        <div class="d-row">${esc(levelName(day.pm10))}</div>
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
    fitCities();
    renderMapMarkers();
    renderLegend();
  }

  function fitCities() {
    const pts = state.meta.cities.map((c) => [c.lat, c.lon]);
    state.map.fitBounds(L.latLngBounds(pts), { padding: [28, 28], paddingBottomRight: [28, 70] });
  }

  function renderLegend() {
    const lim = [0, ...state.meta.levels.limits];
    $("#mapLegend").innerHTML = `<b>${esc(tr("legend"))}</b>` + state.meta.levels.colors.map((c, i) =>
      `<span><i style="background:${c}"></i>${lim[i]}${i < lim.length - 1 ? "–" + lim[i + 1] : "+"}</span>`).join("");
  }

  function renderMapMarkers() {
    if (!state.map) return;
    state.mapMarkers.forEach((m) => m.remove());
    state.mapMarkers = [];
    const ov = state.overview || [];
    state.meta.cities.forEach((c) => {
      const o = ov.find((x) => x.key === c.key) || {};
      const color = o.pm10 !== undefined && o.pm10 !== null ? levelColor(o.pm10) : "#90a4ae";
      const sel = state.place.key === c.key ? " sel" : "";
      const icon = L.divIcon({ className: "", html: `<div class="pin${sel}" style="background:${color}">${fmt(o.pm10)}</div>`,
        iconSize: [0, 0] });
      const m = L.marker([c.lat, c.lon], { icon }).addTo(state.map);
      const wx = o.temp !== undefined && o.temp !== null
        ? `<br>${weatherEmoji(o.code)} ${fmt(o.temp)}° · 💨 ${fmt(o.wind)} ${tr("ms")}` : "";
      m.bindPopup(`<b>${esc(c.name[state.lang])}</b><br>PM10 ${fmt(o.pm10)} µg/m³ · ${esc(o.pm10 !== undefined && o.pm10 !== null ? levelName(o.pm10) : "—")}${wx}
        <button class="popup-btn" type="button" data-key="${c.key}">${esc(tr("select"))}</button>`);
      state.mapMarkers.push(m);
    });
  }

  // ---------------- Sozlamalar ----------------
  function renderSettings() {
    const s = state.settings;
    const disabled = inTelegram ? "" : "disabled";
    const tgHtml = (txt) => esc(txt).replace(/&lt;(\/?)(b|i)&gt;/g, "<$1$2>").replace(/\n/g, "<br>");
    let html = `<div class="card"><h4>${esc(tr("language"))}</h4><div class="seg">` +
      LANGS.map((l) => `<button type="button" data-lang="${l}" class="${l === state.lang ? "on" : ""}">${{ uz: "O'zbekcha", ru: "Русский", en: "English" }[l]}</button>`).join("") +
      `</div></div>`;
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
  }

  async function saveSettings(patch, silent) {
    if (!inTelegram) return;
    try {
      state.settings = await api("/api/me", { method: "POST", body: JSON.stringify(patch) });
      if (!silent) toast(tr("saved"));
    } catch (e) {
      console.error(e);
      toast(tr("error"));
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

  function openSheet(show) {
    $("#citySheet").classList.toggle("show", show);
    $("#sheetBackdrop").classList.toggle("show", show);
    if (show) renderCityList();
  }

  function selectPlace(place) {
    state.place = place;
    store.set("place", place);
    haptic("light");
    openSheet(false);
    if (state.map) state.map.closePopup();
    showView("home");
    loadData("skeleton");
    if (place.key) saveSettings({ city: place.key });
    else saveSettings({ city: "loc", lat: place.lat, lon: place.lon });
  }

  function useLocation() {
    const done = (lat, lon) => selectPlace({ lat, lon });
    const fail = () => toast(tr("locDenied"));
    try {  // Telegram'ning o'z joylashuv xizmati (yangi versiyalarda)
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

  // ---------------- Bo'limlar orasida o'tish ----------------
  function showView(view) {
    state.view = view;
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
    window.scrollTo({ top: 0 });
    if (view === "forecast" && state.data) drawForecastCharts();
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
    if (state.map) { renderMapMarkers(); renderLegend(); }
    saveSettings({ lang });
  }

  // ---------------- Hodisalar ----------------
  function bindEvents() {
    document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => { haptic(); showView(t.dataset.view); }));
    $("#cityBtn").addEventListener("click", () => { haptic(); openSheet(true); });
    $("#sheetBackdrop").addEventListener("click", () => openSheet(false));
    $("#refreshBtn").addEventListener("click", () => { haptic("light"); loadData(); });
    $("#locBtn").addEventListener("click", useLocation);
    $("#cityList").addEventListener("click", (e) => {
      const b = e.target.closest(".city-item");
      if (b) selectPlace({ key: b.dataset.key });
    });
    document.addEventListener("click", (e) => {
      const p = e.target.closest(".popup-btn");
      if (p) selectPlace({ key: p.dataset.key });
      const l = e.target.closest("[data-lang]");
      if (l) setLang(l.dataset.lang);
    });
    document.addEventListener("change", (e) => {
      if (e.target.id === "tAlerts") { haptic(); saveSettings({ alerts: e.target.checked }); }
      if (e.target.id === "tDaily") { haptic(); saveSettings({ daily: e.target.checked }); }
    });
    if (tg) tg.onEvent("themeChanged", () => { applyTheme(); if (state.data) renderAll(); });
  }

  // ---------------- Boshlash ----------------
  async function init() {
    if (tg) { tg.ready(); tg.expand(); try { tg.disableVerticalSwipes && tg.disableVerticalSwipes(); } catch { /* */ } }
    applyTheme();
    const tgLang = tg && tg.initDataUnsafe && tg.initDataUnsafe.user && (tg.initDataUnsafe.user.language_code || "").slice(0, 2);
    state.lang = store.get("lang", LANGS.includes(tgLang) ? tgLang : "uz");
    state.place = store.get("place", { key: "toshkent" });
    applyI18n();
    bindEvents();
    renderSkeleton();
    try {
      state.meta = await api("/api/meta");
    } catch (e) {
      console.error(e);
      return renderError();
    }
    if (inTelegram) {
      try {
        state.settings = await api("/api/me");
        if (state.settings.lang && !store.get("lang", null)) state.lang = state.settings.lang;
        if (state.settings.city && state.settings.city in Object.fromEntries(state.meta.cities.map((c) => [c.key, 1]))) {
          state.place = { key: state.settings.city };
        } else if (state.settings.city === "loc" && state.settings.lat !== null) {
          state.place = { lat: state.settings.lat, lon: state.settings.lon };
        } else {  // birinchi kirish: bildirishnomalar ishlashi uchun joyni serverga saqlaymiz
          const p = state.place;
          saveSettings(p.key ? { city: p.key, lang: state.lang } : { city: "loc", lat: p.lat, lon: p.lon, lang: state.lang }, true);
        }
      } catch (e) { console.warn("settings", e); }
    }
    await loadData("skeleton");
  }

  init();
})();
