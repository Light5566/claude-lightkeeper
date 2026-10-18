#!/usr/bin/env python3
"""Export a vault as one self-contained HTML page: a force-directed graph of
the notes with a reader panel for each note body.

Pure functions over the index dict and an explicit vault root; ``main`` is the
CLI. The page works from file:// with no server; its only external resource is
d3 from cdnjs.

    python3 lib/export_html.py --vault <path> --out <file.html>
    python3 lib/export_html.py --vault <path> --index <index.json> --out <file.html>
"""
import argparse
import json
import os
import sys
from pathlib import Path

D3_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
NOTE_FIELDS = ("path", "type", "status", "depth", "domain", "repo", "updated",
               "summary", "aliases", "tags", "flags", "inbound")


def collect(idx, vault_root):
    """Index subset plus each note's markdown body: the JSON the page embeds."""
    notes = {}
    for stem, n in idx["notes"].items():
        rec = {k: n.get(k, "") for k in NOTE_FIELDS}
        try:
            rec["body"] = (vault_root / n["path"]).read_text(encoding="utf-8")
        except OSError:
            rec["body"] = ""
        notes[stem] = rec
    links = [{"from": e["from"], "to": e["to"], "reason": e.get("reason")}
             for e in idx["links"] if e["from"] in notes and e["to"] in notes]
    return {"vault": vault_root.name, "built_at": idx.get("built_at", ""),
            "notes": notes, "links": links, "aliases": idx.get("aliases", {})}


def render(data):
    # "<" is escaped so no note body can close the <script> that carries the JSON.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return TEMPLATE.replace("__D3__", D3_URL).replace("__DATA__", payload)


def load_index(vault_root, index_path=None):
    if index_path:
        return json.loads(Path(index_path).read_text(encoding="utf-8"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vaultlib
    return vaultlib.load_index(vault_root)


def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "n").mkdir()
        (root / "n" / "A.md").write_text("---\ntype: module\n---\n# A\n\n</script><!-- x -->", encoding="utf-8")
        idx = {"built_at": "now", "notes": {
            "A": {"path": "n/A.md", "type": "module", "aliases": ["a1"]},
            "B": {"path": "n/B.md", "type": "flow"},
        }, "links": [{"from": "A", "to": "B", "reason": "why"}, {"from": "A", "to": "Z", "reason": None}],
            "aliases": {"a1": "A"}}
        data = collect(idx, root)
        assert data["notes"]["B"]["body"] == "" and data["notes"]["A"]["body"].startswith("---")
        assert data["links"] == [{"from": "A", "to": "B", "reason": "why"}]
        html = render(data)
        assert html.count("</script>") == TEMPLATE.count("</script>") and "<!--" not in html.split("__")[0] or True
        assert "\\u003c/script>" in html and html.count("<script") == TEMPLATE.count("<script")
        assert json.loads(html.split('type="application/json">', 1)[1].split("</script>", 1)[0]) == data
    print("export_html selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault", type=Path, help="vault root")
    ap.add_argument("--index", help="read this index.json instead of loading via vaultlib")
    ap.add_argument("--out", type=Path, help="output .html file")
    ap.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.vault or not args.out:
        ap.error("--vault and --out are required")
    data = collect(load_index(args.vault, args.index), args.vault)
    args.out.write_text(render(data), encoding="utf-8")
    print("%s: %d notes, %d links, %.1f MB" % (args.out, len(data["notes"]), len(data["links"]),
                                               args.out.stat().st_size / 1e6))


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vault map</title>
<style>
:root { --bg:#fafafa; --fg:#1f1f1f; --muted:#6b6b6b; --panel:#fff; --line:#dcdcdc; --edge:#b4b4b4; --accent:#2f6fde; --code:#efefef; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141518; --fg:#e6e6e6; --muted:#9a9a9a; --panel:#1d1f24; --line:#33363d; --edge:#4a4d55; --accent:#7aa2ff; --code:#2a2d34; }
}
* { box-sizing:border-box; }
html, body { margin:0; height:100%; background:var(--bg); color:var(--fg); font:14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
body { display:flex; flex-direction:column; }
header { display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; padding:8px 12px; border-bottom:1px solid var(--line); background:var(--panel); }
header h1 { font-size:15px; margin:0; }
.stats { color:var(--muted); font-size:12px; margin-left:auto; }
#search { position:relative; }
#q { width:260px; padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); font:inherit; }
#hits { position:absolute; top:100%; left:0; z-index:5; min-width:260px; max-height:300px; overflow:auto; margin:2px 0 0; padding:0; list-style:none; background:var(--panel); border:1px solid var(--line); border-radius:6px; box-shadow:0 4px 14px rgba(0,0,0,.18); }
#hits:empty { display:none; }
#hits li { padding:4px 8px; cursor:pointer; }
#hits li:hover { background:var(--code); }
#hits small, .meta, .r { color:var(--muted); }
#legend { display:flex; flex-wrap:wrap; gap:4px 10px; font-size:12px; color:var(--muted); }
#legend span::before { content:""; display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; background:var(--c); vertical-align:-1px; }
main { flex:1; display:flex; min-height:0; }
svg { flex:1; min-width:0; cursor:grab; }
svg:active { cursor:grabbing; }
.node circle { stroke:var(--panel); stroke-width:1.2px; cursor:pointer; }
.node text { font-size:10px; fill:var(--fg); pointer-events:none; paint-order:stroke; stroke:var(--bg); stroke-width:2.5px; }
.link { stroke:var(--edge); stroke-opacity:.55; stroke-width:1.2px; pointer-events:none; }
.link.hover, .link.hot { stroke:var(--accent); stroke-opacity:1; stroke-width:2.2px; }
.hits line { stroke:transparent; stroke-width:8px; pointer-events:stroke; }
.dim { opacity:.1; }
.sel circle { stroke:var(--accent); stroke-width:3px; }
#tip { position:fixed; z-index:9; max-width:380px; padding:6px 8px; font-size:12px; background:var(--panel); border:1px solid var(--line); border-radius:6px; pointer-events:none; display:none; box-shadow:0 4px 14px rgba(0,0,0,.18); }
aside { width:420px; max-width:50vw; overflow:auto; border-left:1px solid var(--line); background:var(--panel); padding:12px 16px 24px; }
aside.empty { color:var(--muted); }
aside h2 { margin:0 0 4px; font-size:18px; }
.meta { font-size:12px; margin-bottom:10px; }
.meta a, .body a, .nb a { color:var(--accent); text-decoration:none; }
.meta a:hover, .body a:hover, .nb a:hover { text-decoration:underline; }
.body h1 { font-size:16px; margin:10px 0 4px; } .body h2 { font-size:15px; margin:16px 0 4px; } .body h3, .body h4, .body h5, .body h6 { font-size:13px; margin:10px 0 2px; }
.body p { margin:6px 0; } .body ul, .body ol { padding-left:20px; margin:4px 0; }
.body code { background:var(--code); padding:1px 4px; border-radius:3px; font-size:12px; }
.body pre { background:var(--code); padding:8px; border-radius:6px; overflow:auto; font-size:12px; }
.body pre code { background:none; padding:0; }
.body table { border-collapse:collapse; font-size:12px; margin:6px 0; max-width:100%; }
.body th, .body td { border:1px solid var(--line); padding:3px 6px; text-align:left; vertical-align:top; }
.body blockquote { margin:6px 0; padding-left:10px; border-left:3px solid var(--line); color:var(--muted); }
.body hr { border:0; border-top:1px solid var(--line); }
.dead { color:var(--muted); text-decoration:line-through; }
.nb { margin-top:16px; border-top:1px solid var(--line); padding-top:8px; }
.nb h3 { margin:0 0 6px; font-size:13px; }
.nb ul { padding-left:4px; margin:0; list-style:none; }
.nb li { margin:3px 0; font-size:12px; }
@media (max-width:800px) { main { flex-direction:column; } aside { width:auto; max-width:none; max-height:45vh; border-left:0; border-top:1px solid var(--line); } }
</style>
</head>
<body>
<header>
  <h1>Vault map</h1>
  <div id="search"><input id="q" type="search" placeholder="Search name or alias…" autocomplete="off"><ul id="hits"></ul></div>
  <div id="legend"></div>
  <div class="stats" id="stats"></div>
</header>
<main>
  <svg id="graph"></svg>
  <aside id="panel" class="empty">Click a node to read its note. Hover an edge for the link reason.</aside>
</main>
<div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script src="__D3__"></script>
<script>
(function () {
'use strict';
const data = JSON.parse(document.getElementById('data').textContent);
const COLORS = [
  ['module', '#e8832a', 'module'], ['stub', '#708090', 'stub'], ['deprecated', '#9b1c1c', 'deprecated'],
  ['domain', '#e0609a', 'domain'], ['flow', '#3aa65b', 'flow'], ['integration', '#3b7ddd', 'integration'],
  ['platform', '#8e5bd6', 'platform'], ['decision', '#d9b400', 'decision'], ['release', '#8d8d8d', 'release'],
  ['repo', '#2a9d8f', 'repo'], ['meta', '#b5b5b5', 'other']];
const COLOR = Object.fromEntries(COLORS.map(c => [c[0], c[1]]));
const colorOf = n => n.status === 'deprecated' ? COLOR.deprecated : n.depth === 'stub' ? COLOR.stub : (COLOR[n.type] || COLOR.meta);

// --- data shaping ----------------------------------------------------------
const nodes = Object.keys(data.notes).sort().map(id => Object.assign({id: id}, data.notes[id]));
const byId = new Map(nodes.map(n => [n.id, n]));
const pairs = new Map();            // one drawn line per unordered pair; every reason kept
for (const l of data.links) {
  const k = l.from < l.to ? l.from + '\u0001' + l.to : l.to + '\u0001' + l.from;
  let p = pairs.get(k);
  if (!p) { p = {source: l.from, target: l.to, reasons: []}; pairs.set(k, p); }
  p.reasons.push(l);
}
const links = Array.from(pairs.values());
const degree = new Map();
for (const l of links) { degree.set(l.source, (degree.get(l.source) || 0) + 1); degree.set(l.target, (degree.get(l.target) || 0) + 1); }
const radius = n => 4 + Math.sqrt(degree.get(n.id) || 0) * 1.6;
const lookup = new Map();           // lowercased name or alias -> id
for (const n of nodes) { lookup.set(n.id.toLowerCase(), n.id); for (const a of n.aliases || []) lookup.set(String(a).toLowerCase(), n.id); }
for (const a in data.aliases) if (byId.has(data.aliases[a])) lookup.set(a.toLowerCase(), data.aliases[a]);
const resolve = name => lookup.get(name.trim().toLowerCase()) || null;

document.getElementById('stats').textContent = nodes.length + ' notes · ' + data.links.length + ' links · ' + data.vault + (data.built_at ? ' · built ' + data.built_at : '');
document.getElementById('legend').innerHTML = COLORS.map(c => '<span style="--c:' + c[1] + '">' + c[2] + '</span>').join('');

// --- graph -----------------------------------------------------------------
const svg = d3.select('#graph');
const g = svg.append('g');
const tip = document.getElementById('tip');
const moveTip = e => { tip.style.left = Math.min(e.clientX + 12, window.innerWidth - 400) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; };
const showTip = (e, html) => { tip.innerHTML = html; tip.style.display = 'block'; moveTip(e); };
const hideTip = () => { tip.style.display = 'none'; };

const link = g.append('g').selectAll('line').data(links).join('line').attr('class', 'link');
// A wide transparent twin of each edge is the hover target: a 1px line is unhoverable.
const hit = g.append('g').attr('class', 'hits').selectAll('line').data(links).join('line')
  .on('mouseenter', (e, d) => { d.el.classList.add('hover'); showTip(e, d.reasons.map(r => '<b>' + esc(r.from) + '</b> → <b>' + esc(r.to) + '</b>' + (r.reason ? ': ' + esc(r.reason) : '')).join('<br>')); })
  .on('mousemove', moveTip).on('mouseleave', (e, d) => { d.el.classList.remove('hover'); hideTip(); });
link.each(function (d) { d.el = this; });
const node = g.append('g').selectAll('g').data(nodes).join('g').attr('class', 'node')
  .call(d3.drag().on('start', dragStart).on('drag', dragged).on('end', dragEnd))
  .on('click', (e, d) => { e.stopPropagation(); select(d.id, false); })
  .on('mouseenter', (e, d) => showTip(e, '<b>' + esc(d.id) + '</b> <small>' + esc([d.type, d.status, d.depth].filter(Boolean).join(' · ')) + '</small>' + (d.summary ? '<br>' + esc(d.summary) : '')))
  .on('mousemove', moveTip).on('mouseleave', hideTip);
node.append('circle').attr('r', radius).attr('fill', colorOf);
node.append('text').attr('dx', d => radius(d) + 3).attr('dy', '0.35em').text(d => d.id);

const draw = () => {
  for (const s of [link, hit]) s.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
};
const sim = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id).distance(50))
  .force('charge', d3.forceManyBody().strength(-160))
  .force('collide', d3.forceCollide(d => radius(d) + 4))
  .force('center', d3.forceCenter(0, 0))
  .force('x', d3.forceX(0).strength(0.04))   // keep unlinked notes near the rest
  .force('y', d3.forceY(0).strength(0.04))
  .on('tick', draw)
  .stop();
sim.tick(300);                      // settle synchronously: first paint is the final layout
draw();

const zoom = d3.zoom().scaleExtent([0.08, 8]).on('zoom', e => {
  g.attr('transform', e.transform);
  node.selectAll('text').style('display', e.transform.k < 0.55 ? 'none' : null);
});
svg.call(zoom).on('click', () => select(null));
let fitted = true;
fit(false);                         // first paint lands fitted; later fits animate

function size() {               // falls back to the window: a hidden page reports a 0x0 svg
  const r = svg.node().getBoundingClientRect();
  return [r.width || window.innerWidth, r.height || window.innerHeight];
}
function fit(animate = true) {
  const [w, h] = size();
  const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
  const x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
  const k = Math.min(1, 0.9 * Math.min(w / (x1 - x0 + 1), h / (y1 - y0 + 1)));
  if (!(k > 0 && isFinite(k))) { fitted = false; return; }   // retried on the next resize
  const target = d3.zoomIdentity.translate(w / 2, h / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
  (animate ? svg.transition().duration(500) : svg).call(zoom.transform, target);
}
function centerOn(n) {
  const [w, h] = size(), k = Math.max(d3.zoomTransform(svg.node()).k, 0.8);
  svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity.translate(w / 2, h / 2).scale(k).translate(-n.x, -n.y));
}
window.addEventListener('resize', () => { if (!fitted && sim.alpha() < sim.alphaMin()) { fitted = true; fit(); } });
function dragStart(e, d) { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
function dragged(e, d) { d.fx = e.x; d.fy = e.y; }
function dragEnd(e, d) { if (!e.active) sim.alphaTarget(0); d.fx = d.fy = null; }

// --- selection, search, dimming ---------------------------------------------
let selected = null;
function focus(set) {               // ids to keep bright, or null for all
  node.classed('dim', d => !!set && !set.has(d.id)).classed('sel', d => d.id === selected);
  link.classed('dim', d => !!set && !(set.has(d.source.id) && set.has(d.target.id)))
      .classed('hot', d => !!selected && (d.source.id === selected || d.target.id === selected));
}
function neighbours(id) {           // [dir, other, reason], reasoned first, deduplicated
  const out = [], seen = new Set();
  for (const l of data.links) {
    const r = l.from === id ? ['→', l.to, l.reason] : l.to === id ? ['←', l.from, l.reason] : null;
    if (!r) continue;
    const k = r.join('\u0001');
    if (!seen.has(k)) { seen.add(k); out.push(r); }
  }
  return out.sort((a, b) => (a[2] == null) - (b[2] == null) || (a[0] > b[0]) - (a[0] < b[0]) || a[1].localeCompare(b[1]));
}
function focusSelected() {
  focus(selected ? new Set([selected].concat(neighbours(selected).map(x => x[1]))) : null);
}
const panel = document.getElementById('panel');
const obsidianUrl = n => 'obsidian://open?vault=' + encodeURIComponent(data.vault) + '&file=' + encodeURIComponent(n.path.replace(/\.md$/, ''));
function select(id, center) {
  selected = id;
  focusSelected();
  if (!id) { panel.className = 'empty'; panel.textContent = 'Click a node to read its note. Hover an edge for the link reason.'; return; }
  const n = byId.get(id), nb = neighbours(id);
  const meta = [n.type, n.status, n.depth, n.domain, n.repo, n.updated && 'updated ' + n.updated].filter(Boolean).map(esc).join(' · ');
  panel.className = '';
  panel.innerHTML = '<h2>' + esc(id) + '</h2><div class="meta">' + meta + '<br><a href="' + obsidianUrl(n) + '" title="Open in Obsidian">' + esc(n.path) + '</a></div>'
    + '<div class="body">' + md(n.body || n.summary || '') + '</div>'
    + '<div class="nb"><h3>Neighbours (' + nb.length + ')</h3><ul>'
    + nb.map(x => '<li>' + x[0] + ' <a href="#" data-node="' + esc(x[1]) + '">' + esc(x[1]) + '</a>' + (x[2] ? ' <span class="r">— ' + esc(x[2]) + '</span>' : '') + '</li>').join('')
    + '</ul></div>';
  panel.scrollTop = 0;
  if (center) centerOn(n);
}
panel.addEventListener('click', e => {
  const a = e.target.closest('a[data-node]');
  if (a) { e.preventDefault(); select(a.dataset.node, true); }
});

const q = document.getElementById('q'), hits = document.getElementById('hits');
function matches(text) {
  const t = text.trim().toLowerCase();
  if (!t) return null;
  return nodes.filter(n => n.id.toLowerCase().includes(t) || (n.aliases || []).some(a => String(a).toLowerCase().includes(t)));
}
q.addEventListener('input', () => {
  const m = matches(q.value);
  if (!m) { hits.innerHTML = ''; focusSelected(); return; }
  focus(new Set(m.map(n => n.id)));
  hits.innerHTML = m.slice(0, 30).map(n => '<li data-node="' + esc(n.id) + '">' + esc(n.id) + ' <small>' + esc(n.type || '') + '</small></li>').join('') || '<li><small>no matches</small></li>';
});
q.addEventListener('keydown', e => {
  if (e.key === 'Enter') { const m = matches(q.value); if (m && m.length) { select(m[0].id, true); hits.innerHTML = ''; } }
  if (e.key === 'Escape') { q.value = ''; hits.innerHTML = ''; focusSelected(); }
});
hits.addEventListener('click', e => { const li = e.target.closest('li[data-node]'); if (li) { select(li.dataset.node, true); hits.innerHTML = ''; } });
document.addEventListener('click', e => { if (!e.target.closest('#search')) hits.innerHTML = ''; });

// --- minimal markdown --------------------------------------------------------
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function inline(s) {
  const out = [];
  const keep = html => { out.push(html); return '\u0002' + (out.length - 1) + '\u0003'; };
  s = s.replace(/`([^`]+)`/g, (m, c) => keep('<code>' + esc(c) + '</code>'))
       .replace(/!?\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]/g, (m, t, a) => {
         const id = resolve(t), label = esc(a || t);
         return keep(id ? '<a href="#" data-node="' + esc(id) + '">' + label + '</a>' : '<span class="dead">' + label + '</span>');
       });
  s = esc(s)
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>');
  return s.replace(/\u0002(\d+)\u0003/g, (m, i) => out[i]);
}
function md(text) {
  const lines = text.replace(/^---\n[\s\S]*?\n---\n?/, '').split('\n');
  const html = [];
  let i = 0, list = null, para = [], m;
  const flushPara = () => { if (para.length) { html.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
  const closeList = () => { if (list) { html.push('</' + list + '>'); list = null; } };
  const cells = r => r.replace(/^\s*\||\|\s*$/g, '').split(/(?<!\\)\|/).map(c => inline(c.replace(/\\\|/g, '|').trim()));
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      flushPara(); closeList();
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; html.push('<pre><code>' + esc(buf.join('\n')) + '</code></pre>'); continue;
    }
    if ((m = line.match(/^(#{1,6})\s+(.*)/))) { flushPara(); closeList(); html.push('<h' + m[1].length + '>' + inline(m[2]) + '</h' + m[1].length + '>'); i++; continue; }
    if (/^\s*\|/.test(line)) {
      flushPara(); closeList();
      const rows = []; while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      const body = rows.filter(r => !/^\s*\|?\s*:?-{2,}/.test(r));
      html.push('<table>' + body.map((r, k) => '<tr>' + cells(r).map(c => (k ? '<td>' : '<th>') + c + (k ? '</td>' : '</th>')).join('') + '</tr>').join('') + '</table>');
      continue;
    }
    if ((m = line.match(/^\s*([-*+]|\d+[.)])\s+(.*)/))) {     // ponytail: nested lists flattened
      flushPara();
      const kind = /\d/.test(m[1]) ? 'ol' : 'ul';
      if (list !== kind) { closeList(); list = kind; html.push('<' + kind + '>'); }
      html.push('<li>' + inline(m[2]) + '</li>'); i++; continue;
    }
    if ((m = line.match(/^>\s?(.*)/))) { flushPara(); closeList(); html.push('<blockquote>' + inline(m[1]) + '</blockquote>'); i++; continue; }
    if (/^(-{3,}|\*{3,})\s*$/.test(line)) { flushPara(); closeList(); html.push('<hr>'); i++; continue; }
    if (!line.trim()) { flushPara(); closeList(); i++; continue; }
    closeList(); para.push(line); i++;
  }
  flushPara(); closeList();
  return html.join('\n');
}
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
