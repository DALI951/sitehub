/* SiteHub — app.js */
"use strict";

var API = "https://modali.powerpme.com/sitehub/api.php";
var CACHE_KEY = "sitehub.v1";
var SEEN_KEY = "sitehub.seen.v1";

var state = {
  sites: [],
  filter: "all",
  checkedAt: null,
  offline: false
};

var els = {
  grid: document.getElementById("grid"),
  status: document.getElementById("statusline"),
  refresh: document.getElementById("btnRefresh"),
  filters: document.getElementById("filters")
};

/* ---------- helpers ---------- */

function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function esc(s) {
  var d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function timeAgo(ts) {
  if (!ts) return "never";
  var s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return s + "s ago";
  var m = Math.floor(s / 60);
  if (m < 60) return m + "m ago";
  var h = Math.floor(m / 60);
  if (h < 24) return h + "h ago";
  return Math.floor(h / 24) + "d ago";
}

function hostOf(url) {
  try { return new URL(url).host.replace(/^www\./, ""); }
  catch (e) { return ""; }
}

/* ---------- storage ---------- */

function loadCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || "null"); }
  catch (e) { return null; }
}
function saveCache(payload) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(payload)); } catch (e) {}
}

function savedSeen() {
  try { return JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"); }
  catch (e) { return []; }
}
function markSeen(urls) {
  var seen = savedSeen();
  urls.forEach(function (u) { if (seen.indexOf(u) === -1) seen.push(u); });
  try { localStorage.setItem(SEEN_KEY, JSON.stringify(seen)); } catch (e) {}
}

/* ---------- render ---------- */

function render() {
  var grid = els.grid;
  grid.innerHTML = "";
  var seen = savedSeen();

  if (!state.sites.length) {
    var msg = el("div", "msg");
    if (state.loading) msg.textContent = "Scanning your deployed sites…";
    else if (state.offline) {
      msg.textContent = "Offline and no saved list on this device yet. Connect once so SiteHub can memorize your sites.";
      var retry = el("button", null, "Try again");
      retry.addEventListener("click", load);
      msg.appendChild(retry);
    } else {
      msg.textContent = "Could not reach the server. Tap refresh to retry.";
      var r2 = el("button", null, "Refresh");
      r2.addEventListener("click", load);
      msg.appendChild(r2);
    }
    grid.appendChild(msg);
    return;
  }

  var list = state.sites;
  if (state.filter !== "all") {
    list = list.filter(function (s) { return s.host === state.filter; });
  }
  if (!list.length) {
    var empty = el("div", "msg", "No sites on this host yet.");
    grid.appendChild(empty);
    return;
  }

  list.forEach(function (s) {
    var isNew = !state.offline && seen.indexOf(s.url) === -1;

    var card = el("a", "card");
    card.href = s.url;
    card.target = "_blank";
    card.rel = "noopener";

    var top = el("div", "card-top");
    var av = el("div", "avatar");
    if (s.favicon) {
      var img = el("img");
      img.src = s.favicon;
      img.alt = "";
      img.loading = "lazy";
      img.onerror = function () { img.style.display = "none"; };
      av.appendChild(img);
    } else {
      av.textContent = (s.name || "?").charAt(0).toUpperCase();
    }
    top.appendChild(av);

    var nameRow = el("div", "card-name");
    nameRow.appendChild(el("h2", null, s.name));
    if (isNew) nameRow.appendChild(el("span", "badge-new", "NEW"));
    top.appendChild(nameRow);
    card.appendChild(top);

    card.appendChild(el("p", "c-desc", s.description || "No description yet."));

    var foot = el("div", "c-foot");
    foot.appendChild(el("span", "host " + (s.host === "github" ? "github" : "server"),
      s.host === "github" ? "GitHub Pages" : "Server"));
    foot.appendChild(el("span", "c-url", hostOf(s.url)));
    var arr = el("span", "arrow");
    arr.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>';
    foot.appendChild(arr);
    card.appendChild(foot);

    grid.appendChild(card);
  });
}

/* ---------- data ---------- */

function setStatus(text) {
  els.status.textContent = text;
}

function apply(payload, opts) {
  opts = opts || {};
  if (!payload || !payload.sites || !payload.sites.length) {
    state.sites = [];
    state.offline = opts.offline || false;
    state.loading = false;
    render();
    return;
  }
  var fresh = payload.sites.slice().sort(function (a, b) {
    var oa = a.order == null ? 100 : a.order;
    var ob = b.order == null ? 100 : b.order;
    if (oa !== ob) return oa - ob;
    return (a.name || "").localeCompare(b.name || "");
  });
  state.sites = fresh;
  state.offline = !!opts.offline;
  state.loading = false;
  state.checkedAt = opts.checkedAt || Date.now();

  if (!opts.offline && !opts.seeded) {
    saveCache({ sites: fresh, checkedAt: state.checkedAt });
    markSeen(fresh.map(function (s) { return s.url; }));
  }

  var n = fresh.length;
  var hostCount = {};
  fresh.forEach(function (s) { hostCount[s.host] = (hostCount[s.host] || 0) + 1; });
  setStatus(n + (n === 1 ? " site" : " sites") + " · checked " + timeAgo(state.checkedAt) +
    (opts.offline ? " · offline snapshot" : ""));

  render();
}

function fetchTimeout(url, ms) {
  var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
  var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, ms) : null;
  return fetch(url, { cache: "no-store", signal: ctrl ? ctrl.signal : undefined })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .finally(function () { if (timer) clearTimeout(timer); });
}

function load() {
  state.loading = true;
  els.refresh.classList.add("spinning");
  setStatus("Scanning…");
  render();

  var cached = loadCache();

  fetchTimeout(API + "?t=" + Date.now(), 9000)
    .then(function (payload) {
      apply(payload, { checkedAt: Date.now() });
      els.refresh.classList.remove("spinning");
    })
    .catch(function () {
      if (cached && cached.sites && cached.sites.length) {
        apply(cached, { offline: true });
      } else {
        /* last resort: bundled seed so a first-run APK with no net still shows something */
        return fetchTimeout("seed.json?t=" + Date.now(), 5000)
          .then(function (payload) {
            apply(payload, { seeded: true, checkedAt: Date.now() });
          })
          .catch(function () {
            state.offline = true;
            state.loading = false;
            apply({ sites: [] }, { offline: true });
          })
          .finally(function () { els.refresh.classList.remove("spinning"); });
      }
      els.refresh.classList.remove("spinning");
    });
}

/* ---------- events ---------- */

els.refresh.addEventListener("click", load);
els.filters.addEventListener("click", function (e) {
  var chip = e.target.closest(".fchip");
  if (!chip) return;
  state.filter = chip.getAttribute("data-filter");
  Array.prototype.forEach.call(els.filters.children, function (c) {
    c.classList.toggle("active", c === chip);
  });
  render();
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  });
}

document.addEventListener("DOMContentLoaded", load);