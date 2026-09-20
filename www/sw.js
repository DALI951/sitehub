/* SiteHub service worker — network-first with cache fallback (duoscore lesson) */
var CACHE = "sitehub-v1";
var SHELL = ["./", "./index.html", "./css/style.css", "./js/app.js", "./seed.json", "./manifest.webmanifest", "./icon.svg", "./icons/icon-192.png"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(SHELL).catch(function (err) { console.warn("shell partial", err); });
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);

  /* never cache the live API — always hit the server */
  if (url.pathname.indexOf("api.php") !== -1) {
    e.respondWith(
      fetch(req).catch(function () {
        return new Response(JSON.stringify({ sites: [], offline: true }), {
          headers: { "Content-Type": "application/json" }
        });
      })
    );
    return;
  }

  /* network-first: freshness wins, cache as fallback */
  e.respondWith(
    fetch(req)
      .then(function (res) {
        if (res && res.ok) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      })
      .catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || (url.pathname.endsWith("/") ? caches.match("./index.html") : undefined);
        });
      })
  );
});