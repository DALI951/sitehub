<?php
/**
 * SiteHub detector — https://modali.powerpme.com/sitehub/api.php
 *
 * Auto-detects every deployed site:
 *   1. Scans /public_html for folders with a landing index.html/index.php
 *      (a new upload = automatically detected on next poll)
 *   2. Overlays each folder's site.json when present (name/description/order/...)
 *   3. Adds GitHub Pages sites fetched from the DALI951 repos API (cached 15 min)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store');

$webroot  = dirname(__DIR__);            // /public_html
$selfDir  = basename(__DIR__);           // sitehub
$baseUrl  = 'https://modali.powerpme.com';
$now      = date('c');

/* ---------------------------------------------------------------- helpers */

function read_text($path, $max = 90000) {
    $h = @fopen($path, 'rb');
    if (!$h) return '';
    $s = fread($h, $max);
    fclose($h);
    return $s === false ? '' : $s;
}

function head_html($text) {
    $text = preg_replace('/<!--.*?-->/s', '', $text);
    if (preg_match('/<head[^>]*>(.*?)<\/head>/is', $text, $m)) return $m[1];
    $pos = stripos($text, '<body');
    return $pos === false ? $text : substr($text, 0, $pos);
}

function meta_content($html_head, $len) {
    if (preg_match('/<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']{0,'.$len.'})["\']/i', $html_head, $m)) return $m[1];
    if (preg_match('/<meta[^>]+content=["\']([^"\']{0,'.$len.'})["\'][^>]*name=["\']description["\']/i', $html_head, $m)) return $m[1];
    if (preg_match('/<meta[^>]+property=["\']og:description["\'][^>]*content=["\']([^"\']{0,'.$len.'})["\']/i', $html_head, $m)) return $m[1];
    if (preg_match('/<meta[^>]+content=["\']([^"\']{0,'.$len.'})["\'][^>]*property=["\']og:description["\']/i', $html_head, $m)) return $m[1];
    return '';
}

function title_of($html_head) {
    if (preg_match('/<title[^>]*>(.*?)<\/title>/is', $html_head, $m)) {
        return trim(preg_replace('/\s+/', ' ', $m[1]));
    }
    if (preg_match('/<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']/i', $html_head, $m)) return trim($m[1]);
    if (preg_match('/<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']/i', $html_head, $m)) return trim($m[1]);
    if (preg_match('/<h1[^>]*>(.*?)<\/h1>/is', $html_head, $m)) return trim(preg_replace('/\s+/', ' ', strip_tags($m[1])));
    return '';
}

function favicon_of($dirAbs, $dirName, $selfDir, $html_head) {
    if (preg_match('/<link[^>]+rel=["\'](?:shortcut\s+)?icon["\'][^>]*href=["\']([^"\']+)["\']/i', $html_head, $m)
        || preg_match('/<link[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut\s+)?icon["\']/i', $html_head, $m)
        || preg_match('/<link[^>]+rel=["\']apple-touch-icon["\'][^>]*href=["\']([^"\']+)["\']/i', $html_head, $m)) {
        $href = $m[1];
        $abs  = 'https://modali.powerpme.com/' . $dirName . '/';
        if (preg_match('#^https?://#i', $href)) return $href;
        if ($href === '') return '';
        return $abs . ltrim($href, '/');
    }
    if ($dirName !== $selfDir && @is_file($dirAbs . '/favicon.ico')) {
        return 'https://modali.powerpme.com/' . $dirName . '/favicon.ico';
    }
    if (@is_file($dirAbs . '/icon.svg')) {
        return 'https://modali.powerpme.com/' . $dirName . '/icon.svg';
    }
    return '';
}

function read_site_json($dirAbs) {
    $path = $dirAbs . '/site.json';
    if (!@is_file($path)) return null;
    $j = @json_decode(read_text($path, 50000), true);
    return is_array($j) ? $j : null;
}

/* ------------------------------------------------------- scan subfolders */

$sites   = [];
$scanned = [];

// root site (the server / itself)
$rootMeta = read_site_json($webroot);
if (is_array($rootMeta) && !empty($rootMeta['hide'])) {
    /* hidden root */
} else {
    $rootHtml = head_html(read_text($webroot . '/index.html'));
    if ($rootHtml !== '' || true) {
        $sites[] = [
            'name'        => $rootMeta['name']        ?? (title_of($rootHtml) ?: 'Dali Portfolio'),
            'description' => $rootMeta['description'] ?? (meta_content($rootHtml, 300) ?: 'Ranked first — the server root itself.'),
            'url'         => $rootMeta['url']         ?? ($baseUrl . '/'),
            'host'        => 'server',
            'order'       => $rootMeta['order']       ?? 1,
            'favicon'     => $rootMeta['favicon']     ?? '',
        ];
        $scanned[] = '/ (root)';
    }
}

$entries = @scandir($webroot);
if ($entries === false) {
    http_response_code(500);
    die(json_encode(['error' => 'cannot read ' . $webroot]));
}
sort($entries);

foreach ($entries as $d) {
    if ($d === '.' || $d === '..') continue;
    if ($d[0] === '.' || $d[0] === '_') continue;          // dotfiles & framework dirs
    $abs = $webroot . '/' . $d;
    if (!is_dir($abs)) continue;

    $meta = read_site_json($abs);
    if (is_array($meta) && !empty($meta['hide'])) continue;

    $hasIndex = @is_file($abs . '/index.html') || @is_file($abs . '/index.php');
    if (!$hasIndex && !is_array($meta)) {
        // no landing page and no override -> likely a resources/API folder, skip
        continue;
    }

    $html  = head_html(read_text($abs . '/index.html'));
    $name  = $meta['name']  ?? (title_of($html) ?: ucfirst($d));
    $desc  = $meta['description'] ?? (meta_content($html, 300) ?: 'Deployed on the server — no description yet.');
    $order = $meta['order'] ?? ($d === $selfDir ? 0 : 100);
    $url   = $meta['url']   ?? ($baseUrl . '/' . $d . '/');

    $sites[] = [
        'name'        => $name,
        'description' => $desc,
        'url'         => $url,
        'host'        => 'server',
        'order'       => $order,
        'favicon'     => $meta['favicon'] ?? favicon_of($abs, $d, $selfDir, $html),
    ];
    $scanned[] = '/' . $d;
}

/* ---------------------------------------------------- GitHub Pages sites */

$ghCache = sys_get_temp_dir() . '/sitehub-gh-pages.json';
$gh      = null;
if (@is_file($ghCache) && filemtime($ghCache) > time() - 900) {
    $gh = @json_decode(read_text($ghCache, 2000000), true);
}
if ($gh === null) {
    $ctx = stream_context_create(['http' => [
        'timeout'    => 8,
        'user_agent' => 'SiteHub-detector (DALI951)',
        'ignore_errors' => true,
    ]]);
    $raw = @file_get_contents('https://api.github.com/users/DALI951/repos?per_page=100&sort=updated', false, $ctx);
    if ($raw !== false) {
        $repos = @json_decode($raw, true);
        if (is_array($repos)) {
            $gh = [];
            foreach ($repos as $r) {
                if (empty($r['has_pages']) || !empty($r['private']) || !empty($r['fork'])) continue;
                $gh[] = [
                    'name'        => $r['name'],
                    'description' => trim((string)($r['description'] ?? '')) ?: 'Live on GitHub Pages.',
                    'url'         => 'https://dali951.github.io/' . strtolower($r['name']) . '/',
                ];
            }
            @file_put_contents($ghCache, json_encode($gh));
        }
    }
}
if (is_array($gh)) {
    foreach ($gh as $r) {
        $sites[] = [
            'name'        => $r['name'],
            'description' => $r['description'],
            'url'         => $r['url'],
            'host'        => 'github',
            'order'       => 300,
            'favicon'     => '',
        ];
        $scanned[] = 'gh:' . $r['name'];
    }
}

/* -------------------------------------------------------------- response */

usort($sites, function ($a, $b) {
    if ($a['order'] != $b['order']) return $a['order'] <=> $b['order'];
    return strcasecmp($a['name'] ?? '', $b['name'] ?? '');
});

echo json_encode([
    'updatedAt' => $now,
    'serverScanned' => $scanned,
    'sites'         => array_values($sites),
], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);