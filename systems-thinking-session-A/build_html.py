"""Build two standalone HTML decks (slides only / slides + script) for Session A."""
import html
import json
import re
from pathlib import Path

SCR = Path("/private/tmp/claude-501/-Users-ductiennguyen-Library-Application-Support-Claude-scratch-workspaces-414f7e47-cbdf-40ea-9c5b-aa3f5463bd68-4b7742c0-37b8-4ae6-a968-57d0280a3b24-scratch-2026-10-11-39fe21/f1cb492d-1fcd-4880-a134-f2fe843efbcb/scratchpad")
SLIDES = Path.home() / "Documents/Presentation/systems-thinking-session-A/slides-source/slides"
SCRIPT = Path.home() / "Documents/Presentation/systems-thinking-session-A/script_session_A.md"
OUT = Path.home() / "Documents/Presentation/systems-thinking-session-A"

# slides included (demo removed) and their script section numbers
ORDER = [
    ("cover", "1"), ("hook", "2"), ("hook-code", "2b"), ("roadmap", "3"),
    ("queue-little", "4"), ("queue-curve", "5"), ("queue-lesson", "6"),
    ("delay-open", "7"), ("delay-dealer", "8"), ("delay-hpa", "9"),
    ("catalog-intro", "10"), ("catalog-cache", "11"), ("case-facebook", "11b"), ("catalog-pool", "12"), ("catalog-gc", "12b"),
    ("meta-states", "13"), ("case-aws", "13b"), ("meta-numbers", "14"), ("meta-example", "15"),
    ("meta-cld", "16"), ("break-loop", "17"), ("takeaways", "18"), ("bridge", "19"), ("sources", None),
]

# who speaks each slide: "1" / "2" / None. Rename people here.
NAMES = {"1": "Người 1", "2": "Người 2"}
SPEAKER = {s: "1" for s in ("cover hook hook-code roadmap queue-little queue-curve queue-lesson delay-open delay-dealer "
                            "delay-hpa takeaways bridge").split()}
SPEAKER.update({s: "2" for s in ("catalog-intro catalog-cache case-facebook catalog-pool catalog-gc meta-states case-aws "
                                 "meta-numbers meta-example meta-cld break-loop").split()})

ARROW = "clip-path:polygon(0 35%,60% 35%,60% 0,100% 50%,60% 100%,60% 65%,0 65%);flex:none"


def load_slide(sid):
    s = (SLIDES / f"{sid}.html").read_text()
    s = re.sub(r"<aside>.*?</aside>", "", s, flags=re.S)
    s = re.sub(r'<x-shape kind="arrow-right" style="([^"]*)">\s*</x-shape>',
               lambda m: f'<div style="{m.group(1)};{ARROW}"></div>', s)
    return s


def title_of(sec):
    m = re.search(r"<h[12][^>]*>(.*?)</h[12]>", sec, flags=re.S)
    return re.sub(r"<[^>]+>", " ", m.group(1)).replace("<br>", " ").strip() if m else ""


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]", r'<span class="dir">[\1]</span>', t)
    t = re.sub(r"\((kiểm tra[^)]*)\)", r'<span class="check">(\1)</span>', t)
    return t


def parse_script():
    text = SCRIPT.read_text()
    parts = re.split(r"^## ", text, flags=re.M)[1:]
    secs, qa, check = {}, [], []
    for p in parts:
        head, _, body = p.partition("\n")
        body = body.strip().rstrip("-").strip()
        m = re.match(r"(\d+b?)\. (.+?) \((\d+):(\d+)\)$", head.strip())
        if m:
            num, name, mm, ss = m.groups()
            secs[num] = {"name": name, "minutes": int(mm) + int(ss) / 60,
                         "label": f"{mm}:{ss}", "paras": [x.strip() for x in body.split("\n\n") if x.strip()]}
        elif head.startswith("Câu hỏi dự kiến"):
            for blk in [b for b in body.split("\n\n") if b.strip()]:
                q, _, a = blk.partition("\n")
                qa.append((q.strip("* ").strip(), a.strip()))
        elif head.startswith("Kiểm tra trước"):
            check = [re.sub(r"^\d+\.\s*", "", l).strip() for l in body.splitlines() if l.strip()]
    return secs, qa, check


CSS = """
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#0E1116;color:#F1EEE6;font-family:'IBM Plex Sans',Arial,sans-serif;overflow:hidden}
.app{display:flex;flex-direction:column;height:100%}
.main{flex:1;display:flex;min-height:0}
.stagewrap{flex:1;display:flex;align-items:center;justify-content:center;min-width:0;position:relative;padding:16px}
.stage{position:relative;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.5);border-radius:6px;background:#000}
.slide{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;display:none}
.slide.on{display:block}
.slide section{box-sizing:border-box;position:relative;width:1920px;height:1080px;overflow:hidden}
.slide p,.slide h1,.slide h2,.slide h3,.slide ul,.slide ol{margin:0}
.slide ul,.slide ol{padding-left:44px}
.slide li+li{margin-top:12px}
.slide table{border-collapse:collapse;width:100%}
.slide a{color:#1F6F68;text-decoration:underline}
.slide b{font-weight:600}
.bar{height:44px;display:flex;align-items:center;gap:16px;padding:0 20px;background:#14181F;border-top:1px solid #232A35;font-size:14px;color:#9AA4B2;flex:none}
.bar .grow{flex:1}
.bar button{background:#1F2630;color:#F1EEE6;border:1px solid #2E3744;border-radius:8px;padding:6px 14px;font:inherit;cursor:pointer}
.bar button:hover{background:#2A3340}
.who{padding:4px 12px;border-radius:999px;font-weight:600;font-size:13px;letter-spacing:.3px}
.who:empty{display:none}
.who.p1{background:#E8743B;color:#14181F}
.who.p2{background:#2F9E94;color:#0E1116}
.script .pill{display:inline-block;margin-left:8px;padding:2px 10px;border-radius:999px;font-family:'IBM Plex Sans',sans-serif;font-size:12px;font-weight:600;letter-spacing:.3px;vertical-align:1px;text-transform:none}
.script .pill.p1{background:#E8743B;color:#14181F}
.script .pill.p2{background:#2F9E94;color:#0E1116}
.prog{position:absolute;left:0;right:0;bottom:0;height:3px;background:#232A35}
.prog i{display:block;height:100%;background:#E8743B;width:0}
.script{width:min(36vw,560px);flex:none;background:#F4F1EA;color:#1B2029;overflow:auto;padding:28px 32px 48px;border-left:1px solid #DDD8CB;font-size:19px;line-height:1.6}
.script .tag{font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;color:#B4501D;margin:0 0 6px}
.script h2{font-size:24px;line-height:1.25;margin:0 0 4px;font-weight:600}
.script .time{font-family:'JetBrains Mono',monospace;font-size:14px;color:#1F6F68;margin:0 0 18px}
.script p{margin:0 0 14px}
.script .dir{color:#B4501D;font-style:italic}
.script .check{background:#FFE9A8;border-radius:4px;padding:0 4px}
.script code{font-family:'JetBrains Mono',monospace;font-size:.85em;background:#E8E2D2;border-radius:4px;padding:1px 5px}
.script .none{color:#5A6270;font-style:italic}
.doc{flex:1;overflow:auto;background:#F4F1EA;color:#1B2029;padding:48px 24px}
.doc .in{max-width:860px;margin:0 auto;font-size:20px;line-height:1.6}
.doc h2{font-size:36px;margin:0 0 8px;font-weight:600}
.doc .q{font-weight:600;margin:22px 0 4px}
.doc p{margin:0 0 10px}
.doc ol{padding-left:28px}
.doc li{margin:8px 0}
.doc .tag{font-family:'JetBrains Mono',monospace;font-size:14px;letter-spacing:2px;text-transform:uppercase;color:#B4501D;margin:0 0 6px}
.doc .box{background:#FBFAF6;border:1px solid #DDD8CB;border-radius:12px;padding:18px 22px;margin:14px 0}
.doc .check{background:#FFE9A8;border-radius:4px;padding:0 4px}
.doc code{font-family:'JetBrains Mono',monospace;background:#E8E2D2;border-radius:4px;padding:1px 5px}
@media (max-width:900px){.main{flex-direction:column}.script{width:auto;height:42%;border-left:0;border-top:1px solid #DDD8CB}}
"""

JS = """
(function(){
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var scripts=[].slice.call(document.querySelectorAll('.script-item'));
  var docs=[].slice.call(document.querySelectorAll('.doc'));
  var stagewrap=document.querySelector('.stagewrap');
  var stage=document.querySelector('.stage');
  var scriptBox=document.querySelector('.script');
  var counter=document.getElementById('counter');
  var who=document.getElementById('who');
  var NAMES=__NAMES__;
  var prog=document.querySelector('.prog i');
  var total=slides.length+docs.length;
  var i=0;
  try{var h=parseInt((location.hash||'').slice(1),10);if(h>=1&&h<=total)i=h-1;}catch(e){}
  function fit(){
    var w=stagewrap.clientWidth-32,h=stagewrap.clientHeight-32;
    var s=Math.min(w/1920,h/1080);if(s<=0)return;
    stage.style.width=1920*s+'px';stage.style.height=1080*s+'px';
    slides.forEach(function(el){el.style.transform='scale('+s+')';});
  }
  function show(n){
    i=Math.max(0,Math.min(total-1,n));
    var isDoc=i>=slides.length;
    slides.forEach(function(el,k){el.classList.toggle('on',k===i);});
    scripts.forEach(function(el,k){el.style.display=(k===i)?'block':'none';});
    docs.forEach(function(el,k){el.style.display=(slides.length+k===i)?'block':'none';});
    stagewrap.style.display=isDoc?'none':'flex';
    if(scriptBox){scriptBox.style.display=isDoc?'none':'block';scriptBox.scrollTop=0;}
    var w=(!isDoc&&slides[i].getAttribute('data-who'))||'';
    who.textContent=w?NAMES[w]:'';who.className='who'+(w?' p'+w:'');
    counter.textContent=(i+1)+' / '+total;
    prog.style.width=((i+1)/total*100)+'%';
    try{history.replaceState(null,'','#'+(i+1));}catch(e){}
    fit();
  }
  function next(){show(i+1)}function prev(){show(i-1)}
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' '){e.preventDefault();next();}
    else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prev();}
    else if(e.key==='Home')show(0);else if(e.key==='End')show(total-1);
    else if(e.key==='f'||e.key==='F')toggleFs();
    else if((e.key==='s'||e.key==='S')&&scriptBox){scriptBox.style.display=(scriptBox.style.display==='none')?'block':'none';fit();}
  });
  stagewrap.addEventListener('click',function(e){var r=stagewrap.getBoundingClientRect();(e.clientX-r.left>r.width/2)?next():prev();});
  var tx=null;stagewrap.addEventListener('touchstart',function(e){tx=e.touches[0].clientX;},{passive:true});
  stagewrap.addEventListener('touchend',function(e){if(tx===null)return;var d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>50)(d<0?next():prev());tx=null;});
  function toggleFs(){if(!document.fullscreenElement)document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen();else document.exitFullscreen();}
  document.getElementById('prev').onclick=prev;document.getElementById('next').onclick=next;document.getElementById('fs').onclick=toggleFs;
  var ts=document.getElementById('ts');if(ts)ts.onclick=function(){scriptBox.style.display=(scriptBox.style.display==='none')?'block':'none';fit();};
  window.addEventListener('resize',fit);
  show(i);
})();
"""

HEAD = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style></head><body>"""


def build(with_script):
    secs, qa, check = parse_script()
    slides_html, script_html = [], []
    total_min = sum(secs[n]["minutes"] for _, n in ORDER if n and n in secs)
    for idx, (sid, num) in enumerate(ORDER):
        sec = load_slide(sid)
        who = SPEAKER.get(sid)
        slides_html.append(f'<div class="slide" id="s-{sid}"' + (f' data-who="{who}"' if who else '') + f'>{sec}</div>')
        pill = f'<span class="pill p{who}">{NAMES[who]}</span>' if who else ''
        if with_script:
            if num and num in secs:
                s = secs[num]
                paras = "".join(f"<p>{inline(p)}</p>" for p in s["paras"] if not p.startswith("**Người nói"))
                body = (f'<p class="tag">Slide {idx + 1} · {html.escape(sid)}{pill}</p>'
                        f'<h2>{html.escape(title_of(sec) or s["name"])}</h2>'
                        f'<p class="time">Khoảng {s["label"]} phút</p>{paras}')
            else:
                body = (f'<p class="tag">Slide {idx + 1} · {html.escape(sid)}{pill}</p>'
                        f'<h2>{html.escape(title_of(sec))}</h2>'
                        '<p class="none">Không có lời nói. Slide này để dành cho phần hỏi đáp hoặc gửi tài liệu sau buổi nói.</p>')
            script_html.append(f'<div class="script-item" style="display:none">{body}</div>')

    docs = ""
    if with_script:
        qa_html = "".join(f'<p class="q">{inline(q)}</p><p>{inline(a)}</p>' for q, a in qa)
        chk = [c.replace("(mục 14)", "(slide Số liệu thực tế)") for c in check]
        chk_html = "".join(f"<li>{inline(c)}</li>" for c in chk)
        cut = ("Nếu thiếu giờ, cắt theo thứ tự: bỏ slide GC death spiral, nói lướt slide Số liệu thực tế, "
               "chỉ nhắc WorkOS ở slide Connection pool, rút hai ví dụ Delay còn một.")
        docs = (
            f'<div class="doc"><div class="in"><p class="tag">Phụ lục</p><h2>Thời gian và câu hỏi dự kiến</h2>'
            f'<div class="box"><p><b>Tổng thời gian ước tính:</b> khoảng {round(total_min)} phút, chưa tính hỏi đáp. '
            f'Mốc phút là ước tính, chưa đo thật. {html.escape(cut)}</p></div>'
            f'<div class="box"><p><b>Phân công:</b> {NAMES["1"]} nói slide 1 đến 10 và 22 đến 23 (khoảng 20 phút). '
            f'{NAMES["2"]} nói slide 11 đến 21 (khoảng 20 phút). Slide Nguồn tham khảo không ai nói. '
            f'Hỏi đáp: {NAMES["1"]} trả lời câu về Queue và Delay, {NAMES["2"]} trả lời câu về Catalog và Metastable.</p></div>{qa_html}</div></div>'
            f'<div class="doc"><div class="in"><p class="tag">Phụ lục</p><h2>Kiểm tra trước buổi nói</h2>'
            f'<div class="box"><ol>{chk_html}</ol></div></div></div>'
        )

    title = "Lỗi hết rồi, sao hệ thống vẫn chết? Session A" + (" (slide + script)" if with_script else " (slide)")
    keys = "← → hoặc Space: chuyển slide · F: toàn màn hình" + (" · S: ẩn/hiện script" if with_script else "")
    ts_btn = '<button id="ts" title="Ẩn/hiện script">Script</button>' if with_script else ""
    script_panel = f'<div class="script">{"".join(script_html)}</div>' if with_script else ""
    return (HEAD.format(title=html.escape(title), css=CSS)
            + '<div class="app"><div class="main"><div class="stagewrap"><div class="stage">'
            + "".join(slides_html) + "</div></div>" + script_panel + docs + "</div>"
            + f'<div class="bar"><span>{keys}</span><span class="grow"></span>{ts_btn}'
              '<span id="who" class="who"></span><button id="prev">‹</button><span id="counter"></span><button id="next">›</button>'
              '<button id="fs">Toàn màn hình</button><div class="prog"><i></i></div></div></div>'
            + "<script>" + JS.replace("__NAMES__", json.dumps(NAMES, ensure_ascii=False)) + "</script></body></html>")


if __name__ == "__main__":
    for name, ws in (("Session-A_slides.html", False), ("Session-A_slides-va-script.html", True)):
        out = build(ws)
        (OUT / name).write_text(out)
        print(name, len(out))
