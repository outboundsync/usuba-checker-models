#!/usr/bin/env python3
"""Static labelling page generator: ONE self-contained HTML file (inline CSS + JS, no network, no repo access needed) that shows one finding at a time:
code snippet with the flagged line highlighted, a plain-English explanation, and the buttons Real / Not real / Unsure. Labels autosave in the browser (localStorage)
and export as JSON (download or copy). Works from file:// in any current browser.

  python3 scope/labelpage/make_label_page.py --batch scope/labelpage/sample_batch.json --out label_page.html [--title "S1 batch 1"]

Batch file: {"batch_id": str, "set": "S1" | "S2" | "S3" | "S4", "kind": "checker" | "added", "items": [item, ...]} with item =
  {"id": str, "plugin": str, "file": str, "line": int, "rule": str|null, "category": str|null, "severity": str|null,
   "explanation": str (plain English, what the finding claims and why it would matter),
   "claim": str (the finding text as the tool wrote it), "fix": str|null (the proposed patch, shown after the label is chosen),
   "snippet": {"start": int, "lines": [str, ...]}  (consecutive source lines starting at line number ``start``) }
Question asked per item: S1 / "checker": "Is this Checker scripts finding real?"  S3 / "added": "Is this added finding real?"  (Not real = false alarm / wrong.)
Export format: {"schema": "usuba-labels/1", "batch_id", "set", "labeler", "exported_at", "labels": [{"id", "label": "real"|"not_real"|"unsure", "note", "ts"}]}.
The exported labels are the ONLY thing that comes back; they carry item ids, never code.
"""
import argparse
import json
import sys

REQUIRED = ("id", "plugin", "file", "line", "explanation", "claim", "snippet")


def check_batch(b):
    errs = []
    if not isinstance(b, dict) or not isinstance(b.get("items"), list) or not b["items"]:
        return ["batch needs a non-empty items list"]
    for k in ("batch_id", "set", "kind"):
        if not isinstance(b.get(k), str):
            errs.append("missing " + k)
    ids = set()
    for i, it in enumerate(b["items"]):
        for k in REQUIRED:
            if k not in it:
                errs.append("item %d missing %s" % (i, k))
        if it.get("id") in ids:
            errs.append("duplicate id %r" % it.get("id"))
        ids.add(it.get("id"))
        sn = it.get("snippet") or {}
        if not isinstance(sn.get("lines"), list) or not isinstance(sn.get("start"), int):
            errs.append("item %d snippet needs start and lines" % i)
        elif not (sn["start"] <= it.get("line", -1) < sn["start"] + len(sn["lines"])):
            errs.append("item %d line %s is outside its snippet" % (i, it.get("line")))
    return errs


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#14161a;--fg:#e8e8ea;--mut:#9aa0a8;--card:#1d2026;--line:#2b2f37;--hl:#4a3b12;--real:#1f7a4d;--no:#a63a3a;--uns:#6b6f78;--acc:#5aa2ff}
@media (prefers-color-scheme:light){:root{--bg:#f6f7f9;--fg:#15171a;--mut:#5b616b;--card:#fff;--line:#d7dbe2;--hl:#fff1c2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;justify-content:space-between}
h1{font-size:18px;margin:0}.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;flex:1;min-width:120px}.bar i{display:block;height:100%;background:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-top:12px}
.meta{color:var(--mut);font-size:14px}.q{font-size:20px;font-weight:600;margin:0 0 6px}
pre{margin:8px 0 0;overflow:auto;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:0;font:13px/1.45 ui-monospace,Menlo,Consolas,monospace}
pre div{display:flex;white-space:pre}pre b{display:inline-block;min-width:4ch;text-align:right;padding:0 10px;color:var(--mut);font-weight:400;user-select:none}pre span{padding-right:12px}
pre .hl{background:var(--hl)}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}button{font:inherit;border:0;border-radius:8px;padding:12px 18px;color:#fff;cursor:pointer;min-width:120px}
#real{background:var(--real)}#no{background:var(--no)}#uns{background:var(--uns)}button.sel{outline:3px solid var(--acc)}button.nav{background:var(--line);color:var(--fg);min-width:90px}
textarea{width:100%;margin-top:10px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit}
.tag{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:0 6px;font-size:12px;color:var(--mut);margin-right:6px}
.fix{white-space:pre-wrap;font:13px ui-monospace,Menlo,Consolas,monospace}.hide{display:none}
footer{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}input[type=text]{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px}
</style></head><body><main>
<header><h1 id="title"></h1><span class="meta" id="pos"></span><div class="bar"><i id="prog"></i></div></header>
<div class="card" id="card">
 <div class="meta" id="meta"></div>
 <p class="q" id="q"></p>
 <p id="explain"></p>
 <p class="meta">Tool's wording: <span id="claim"></span></p>
 <pre id="code" aria-label="code"></pre>
 <div class="btns"><button id="real">1 &middot; Real</button><button id="no">2 &middot; Not real</button><button id="uns">3 &middot; Unsure</button>
  <button class="nav" id="prev">&larr; Back</button><button class="nav" id="next">Next &rarr;</button></div>
 <textarea id="note" rows="2" placeholder="Optional note (why?)"></textarea>
 <div id="fixbox" class="hide"><p class="meta">Proposed fix (shown after you choose):</p><div class="fix" id="fix"></div></div>
</div>
<footer><label>Your initials <input type="text" id="who" size="8"></label><button class="nav" id="export">Export labels (JSON)</button><button class="nav" id="copy">Copy JSON</button>
<button class="nav" id="load">Load saved labels</button><input type="file" id="file" accept=".json" class="hide"><span class="meta" id="status"></span></footer>
<p class="meta">Keys: 1 Real, 2 Not real, 3 Unsure, &larr; &rarr; move. Nothing leaves this page; labels live in this browser until you export them.</p>
</main>
<script id="batch" type="application/json">__BATCH__</script>
<script>
"use strict";
var B=JSON.parse(document.getElementById("batch").textContent), items=B.items, LS="usuba-labels:"+B.batch_id, st={labels:{},who:""}, i=0;
try{var s=JSON.parse(localStorage.getItem(LS)||"null"); if(s){st=s}}catch(e){}
var $=function(id){return document.getElementById(id)};
function save(){try{localStorage.setItem(LS,JSON.stringify(st))}catch(e){}}
function done(){return Object.keys(st.labels).length}
function firstOpen(){for(var k=0;k<items.length;k++){if(!st.labels[items[k].id])return k}return 0}
function render(){
 var it=items[i], l=st.labels[it.id]||{};
 $("title").textContent=(B.title||B.batch_id);
 $("pos").textContent=(i+1)+" / "+items.length+"  ("+done()+" labelled)";
 $("prog").style.width=(100*done()/items.length)+"%";
 var m=$("meta"); m.textContent=""; 
 [it.plugin, it.file+":"+it.line, it.rule||it.category, it.severity].forEach(function(t){if(t){var s=document.createElement("span");s.className="tag";s.textContent=t;m.appendChild(s)}});
 $("q").textContent = B.kind==="added" ? "Is this added finding real?" : "Is this Checker scripts finding real?";
 $("explain").textContent=it.explanation; $("claim").textContent=it.claim;
 var pre=$("code"); pre.textContent="";
 it.snippet.lines.forEach(function(t,k){var n=it.snippet.start+k, d=document.createElement("div"), b=document.createElement("b"), sp=document.createElement("span");
  b.textContent=n; sp.textContent=t||" "; if(n===it.line)d.className="hl"; d.appendChild(b); d.appendChild(sp); pre.appendChild(d)});
 ["real","no","uns"].forEach(function(id){$(id).classList.remove("sel")});
 var map={real:"real",not_real:"no",unsure:"uns"}; if(l.label)$(map[l.label]).classList.add("sel");
 $("note").value=l.note||""; $("who").value=st.who||"";
 var fb=$("fixbox"); if(l.label&&it.fix){fb.classList.remove("hide");$("fix").textContent=it.fix}else{fb.classList.add("hide")}
}
function put(v){var it=items[i]; st.labels[it.id]={label:v,note:$("note").value,ts:new Date().toISOString()}; save(); render(); if(i<items.length-1){i++; setTimeout(render,180)}}
function go(d){i=Math.max(0,Math.min(items.length-1,i+d));render()}
$("real").onclick=function(){put("real")};$("no").onclick=function(){put("not_real")};$("uns").onclick=function(){put("unsure")};
$("prev").onclick=function(){go(-1)};$("next").onclick=function(){go(1)};
$("note").onchange=function(){var l=st.labels[items[i].id]; if(l){l.note=$("note").value;save()}};
$("who").onchange=function(){st.who=$("who").value;save()};
document.addEventListener("keydown",function(e){if(e.target.tagName==="TEXTAREA"||e.target.tagName==="INPUT")return;
 if(e.key==="1")put("real");else if(e.key==="2")put("not_real");else if(e.key==="3")put("unsure");else if(e.key==="ArrowLeft")go(-1);else if(e.key==="ArrowRight")go(1)});
function payload(){return JSON.stringify({schema:"usuba-labels/1",batch_id:B.batch_id,set:B.set,labeler:st.who||"",exported_at:new Date().toISOString(),
 labels:items.filter(function(x){return st.labels[x.id]}).map(function(x){var l=st.labels[x.id];return {id:x.id,label:l.label,note:l.note||"",ts:l.ts}})},null,1)}
$("export").onclick=function(){var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([payload()],{type:"application/json"}));
 a.download="labels-"+B.batch_id+(st.who?"-"+st.who:"")+".json";document.body.appendChild(a);a.click();a.remove();$("status").textContent="exported "+done()+" labels"};
$("copy").onclick=function(){var t=payload();if(navigator.clipboard){navigator.clipboard.writeText(t).then(function(){$("status").textContent="copied"},function(){window.prompt("Copy:",t)})}else{window.prompt("Copy:",t)}};
$("load").onclick=function(){$("file").click()};
$("file").onchange=function(e){var f=e.target.files[0]; if(!f)return; var r=new FileReader(); r.onload=function(){try{var j=JSON.parse(r.result);
 if(j.batch_id!==B.batch_id){$("status").textContent="different batch";return}
 j.labels.forEach(function(x){st.labels[x.id]={label:x.label,note:x.note||"",ts:x.ts}}); if(j.labeler)st.who=j.labeler; save(); i=firstOpen(); render(); $("status").textContent="loaded"}catch(err){$("status").textContent="bad file"}}; r.readAsText(f)};
i=firstOpen(); render();
</script></body></html>
"""


def build(batch, title=None):
    errs = check_batch(batch)
    if errs:
        raise ValueError("; ".join(errs[:6]))
    b = dict(batch)
    if title:
        b["title"] = title
    data = json.dumps(b, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    return PAGE.replace("__TITLE__", (title or batch["batch_id"]).replace("<", "&lt;")).replace("__BATCH__", data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    a = ap.parse_args()
    with open(a.batch) as f:
        batch = json.load(f)
    try:
        html = build(batch, a.title)
    except ValueError as e:
        sys.exit("bad batch: %s" % e)
    with open(a.out, "w") as f:
        f.write(html)
    print("wrote %s (%d items, %d bytes)" % (a.out, len(batch["items"]), len(html)))


if __name__ == "__main__":
    main()
