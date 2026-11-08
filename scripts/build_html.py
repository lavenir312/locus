#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把分章 Markdown 笔记构建成单册自包含 HTML。

特性：侧栏目录（按子目录分组）｜全文搜索｜点 (pMMM) 右侧滑出原文段落｜mermaid 懒渲染
无脚本也能读：全书连续排版，目录用原生锚点跳转，JS 只做增强。

用法
    python build_html.py --notes out/ --src work/ --title "书名" --out 书名_精读.html

约定
    笔记：<notes>/<组>/*.md，或 <notes>/*.md（顶层归"总论"）；文件名以三位章号开头
    原文：<src>/NNN.md，段落以 [chNNN:pMMM] 开头；用于锚点回看与字数统计
依赖：pip install markdown
"""
import os, re, json, glob, argparse, html as ihtml

try:
    import markdown as _md
except ImportError:
    raise SystemExit('需要 markdown 库：pip install markdown')

MD_EXT = ['tables', 'fenced_code', 'sane_lists']
PUNCT = re.compile(r'[\s\u3000]|[\u3000-\u303f]|[\uff00-\uffef]')


def load_src(src_dir):
    data = {}
    if not src_dir or not os.path.isdir(src_dir):
        return data
    for f in glob.glob(os.path.join(src_dir, '*.md')):
        m = re.match(r'(\d{3})', os.path.basename(f))
        if not m:
            continue
        ch = int(m.group(1))
        t = open(f, encoding='utf-8').read()
        paras = {}
        for mm in re.finditer(r'\[ch\d{3}:p(\d{3})\]\s*([\s\S]*?)(?=\n\[ch\d{3}:p\d{3}\]|\Z)', t):
            body = re.sub(r'\[\d{1,3}\]', '', mm.group(2)).strip()
            if body:
                paras[mm.group(1)] = body
        data[ch] = paras
    return data


def md_to_html(text, ch):
    blocks = []

    def stash(m):
        blocks.append(m.group(1).strip())
        return f'\n\n@@MERMAID{len(blocks)-1}@@\n\n'
    text = re.sub(r'```mermaid\n([\s\S]*?)```', stash, text)

    def anch_full(m):
        c2, p = m.group(1), m.group(2)
        return (f'<span class="anc" data-ch="{c2}" data-p="{p}" '
                f'title="查看第 {int(p)} 段原文">p{p}</span>')

    def anch(m):
        p = m.group(1)
        return (f'<span class="anc" data-ch="{ch}" data-p="{p}" '
                f'title="查看第 {int(p)} 段原文">p{p}</span>')
    text = re.sub(r'\[ch(\d{3}):p(\d{3})\]', anch_full, text)
    text = re.sub(r'[（(]p(\d{3})[）)]', lambda m: '（' + anch(m) + '）', text)

    text = re.sub(r'^> 底本：.*\n(?:> .*\n)*', '', text, flags=re.M)
    text = re.sub(r'^#\s+.*\n', '', text, count=1, flags=re.M)

    body = _md.markdown(text, extensions=MD_EXT)
    for i, code in enumerate(blocks):
        div = f'<div class="mermaid">{ihtml.escape(code)}</div>'
        body = body.replace(f'<p>@@MERMAID{i}@@</p>', div).replace(f'@@MERMAID{i}@@', div)
    return body


def collect(notes_dir, only=None):
    """返回 [(组名, 子项列表)]。only 给定时只取该组，用于按部拆册。"""
    groups = []
    top = sorted(glob.glob(os.path.join(notes_dir, '*.md')))
    subs = sorted([d for d in glob.glob(os.path.join(notes_dir, '*'))
                   if os.path.isdir(d) and os.path.basename(d) != 'work'])   # work/ 是原文不是笔记
    if top:
        groups.append(('总论', top))
    for d in subs:
        fs = sorted(glob.glob(os.path.join(d, '*.md')))
        if fs:
            groups.append((os.path.basename(d), fs))
    if only:
        groups = [g for g in groups if g[0] == only]
    return groups


def build(a, only=None):
    src = load_src(a.src)
    meta = {}
    mp = os.path.join(a.src or '', 'manifest.json')
    if os.path.exists(mp):
        for c in json.load(open(mp, encoding='utf-8')).get('chapters', []):
            meta[c['ch']] = c

    toc, sections = [], []
    for gname, files in collect(a.notes, only):
        items = []
        for f in files:
            m2 = re.match(r'(\d+)', os.path.basename(f))
            if not m2:
                continue
            ch = int(m2.group(1))
            text = open(f, encoding='utf-8').read()
            cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
            level = '提要级' if cjk < 1500 else '标准级'
            mt = re.match(r'#\s+(.+)', text)
            title = re.sub(r'^\d+\s*', '', mt.group(1).strip()) if mt else os.path.basename(f)
            mm = meta.get(ch)
            sub = (f'{mm.get("chars", 0)} 字原文 · {mm.get("paras", 0)} 段 · 笔记 {cjk} 字'
                   if mm else f'笔记 {cjk} 字')
            sid = f'c{ch:03d}'
            items.append({'id': sid, 'title': title, 'level': level, 'sub': sub,
                          'html': md_to_html(text, f'{ch:03d}'), 'ch': ch})
        if items:
            toc.append({'group': gname, 'items': [{'id': i['id'], 'title': i['title'],
                                                   'level': i['level']} for i in items]})
            sections += [(i['id'], gname, i['title'], i['sub'], i['level'], i['html']) for i in items]

    nav = []
    for g in toc:
        nav.append(f'<div class="grp"><div class="grp-h">{ihtml.escape(g["group"])}</div>')
        for it in g['items']:
            lv = ' lite' if it['level'] == '提要级' else ''
            nav.append(f'<a class="navi{lv}" href="#{it["id"]}" data-id="{it["id"]}">'
                       f'{ihtml.escape(it["title"])}</a>')
        nav.append('</div>')
    nav = '\n'.join(nav)

    arts = []
    for sid, glabel, title, sub, level, body in sections:
        badge = (f'<span class="lv lite">{level}</span>' if level == '提要级'
                 else f'<span class="lv">{level}</span>')
        arts.append(f'''<section class="chapter" id="{sid}" data-title="{ihtml.escape(title)}">
<header class="ch-head"><div class="ch-grp">{ihtml.escape(glabel)}</div>
<h1>{ihtml.escape(title)}</h1>
<div class="ch-sub">{badge}<span>{ihtml.escape(sub)}</span></div></header>
<div class="ch-body">{body}</div></section>''')
    arts = '\n'.join(arts)
    used = {int(re.match(r'c(\d+)', s[0]).group(1)) for s in sections if re.match(r'c(\d+)', s[0])}
    srcz = json.dumps({str(k): v for k, v in src.items() if k in used},
                      ensure_ascii=False, separators=(',', ':'))

    page = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ihtml.escape(a.title)} · 精读</title>
<style>
:root{{--bg:#faf8f4;--paper:#fffdfa;--ink:#23262d;--muted:#7a7468;--faint:#a9a294;
--line:#e7e1d5;--accent:#3f4f9e;--red:#9b3b46;--side:#1d2130;--side-ink:#cfd3e0;
--side-faint:#7b8299;--mark:#fff3c4}}
*{{box-sizing:border-box}}html,body{{margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-size:16px;line-height:1.9;
font-family:-apple-system,"PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif;
-webkit-font-smoothing:antialiased}}
#side{{position:fixed;left:0;top:0;bottom:0;width:278px;background:var(--side);color:var(--side-ink);
overflow-y:auto;padding:22px 0 40px;z-index:30}}
#side::-webkit-scrollbar{{width:6px}}#side::-webkit-scrollbar-thumb{{background:#39405a;border-radius:3px}}
.brand{{padding:0 22px 18px;border-bottom:1px solid #2b3145}}
.brand h1{{font-size:14.5px;margin:0 0 4px;color:#fff;font-weight:600;line-height:1.5}}
.brand p{{margin:0;font-size:11px;color:var(--side-faint);line-height:1.6}}
#q{{margin:16px 18px 8px;width:calc(100% - 36px);padding:8px 11px;border-radius:6px;
border:1px solid #333a52;background:#161a26;color:#dfe3ee;font-size:13px;outline:none}}
#q:focus{{border-color:#5a6bb8}}
.grp{{margin:14px 0 4px}}
.grp-h{{padding:6px 22px;font-size:11px;color:#6f7893;letter-spacing:1.2px}}
.navi{{display:block;padding:5px 22px 5px 26px;font-size:13px;color:var(--side-ink);
text-decoration:none;border-left:2px solid transparent;line-height:1.5}}
.navi:hover{{background:#242a3d;color:#fff}}
.navi.on{{background:#252c42;color:#fff;border-left-color:#7d8ce0}}
.navi.lite{{color:#98a0b8}}
.navi.lite::after{{content:"速";font-size:9px;color:#5d6580;margin-left:6px;
border:1px solid #39405a;border-radius:3px;padding:0 3px}}
#main{{margin-left:278px}} .wrap{{max-width:750px;margin:0 auto;padding:52px 40px 120px}}
.chapter{{display:block;padding-top:10px;scroll-margin-top:20px}}
.chapter+.chapter{{border-top:1px solid var(--line);margin-top:60px;padding-top:50px}}
.ch-head{{border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:28px}}
.ch-grp{{font-size:11.5px;color:var(--accent);letter-spacing:1.4px;margin-bottom:8px}}
.ch-head h1{{font-family:"Songti SC","SimSun",serif;font-size:26px;line-height:1.45;
margin:0 0 10px;font-weight:700}}
.ch-sub{{font-size:12px;color:var(--muted);display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.lv{{font-size:10.5px;padding:1px 6px;border-radius:3px;background:#eef0fa;color:var(--accent);
border:1px solid #d8dcf2}}
.lv.lite{{background:#fdf5e8;color:#9a6a25;border-color:#f0e0c4}}
.ch-body h2{{font-family:"Songti SC","SimSun",serif;font-size:18.5px;margin:32px 0 12px;
padding-left:11px;border-left:3px solid var(--accent);line-height:1.5}}
.ch-body h3{{font-size:15.5px;margin:24px 0 8px;color:#3a3f4d;font-weight:600}}
.ch-body p{{margin:0 0 15px}} .ch-body strong{{color:#1a1d24}}
.ch-body em{{color:var(--red);font-style:normal;font-size:.94em}}
.ch-body ul,.ch-body ol{{margin:0 0 16px;padding-left:22px}} .ch-body li{{margin:5px 0}}
.ch-body blockquote{{margin:18px 0;padding:12px 18px;background:#f4f1ea;
border-left:3px solid #cfc7b6;color:#4a4a48;border-radius:0 4px 4px 0}}
.ch-body blockquote p:last-child{{margin:0}}
.ch-body table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:13.5px}}
.ch-body th,.ch-body td{{border:1px solid var(--line);padding:7px 11px;text-align:left;vertical-align:top}}
.ch-body th{{background:#f3f0e9;font-weight:600}}
.ch-body tr:nth-child(even) td{{background:#fbfaf6}}
.ch-body hr{{border:0;border-top:1px solid var(--line);margin:32px 0}}
.ch-body code{{background:#f2efe8;padding:1px 5px;border-radius:3px;font-size:.9em}}
.anc{{font-family:ui-monospace,Consolas,monospace;font-size:11px;color:var(--accent);
background:#eef0fa;border:1px solid #dfe3f5;border-radius:3px;padding:0 4px;cursor:pointer;
white-space:nowrap;transition:.15s}}
.anc:hover{{background:var(--accent);color:#fff;border-color:var(--accent)}}
#drawer{{position:fixed;right:0;top:0;bottom:0;width:min(520px,42vw);background:var(--paper);
border-left:1px solid var(--line);box-shadow:-8px 0 30px rgba(40,35,25,.10);
transform:translateX(102%);transition:transform .26s cubic-bezier(.3,.8,.3,1);z-index:40;
display:flex;flex-direction:column}}
#drawer.on{{transform:none}}
.dh{{padding:16px 22px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;
align-items:center;font-size:12.5px;color:var(--muted)}}
.dh b{{color:var(--accent)}}
.dh button{{background:none;border:0;font-size:19px;color:var(--faint);cursor:pointer;line-height:1}}
.dc{{padding:20px 22px;overflow-y:auto;font-size:14.5px;line-height:1.95;color:#3a3a38;
font-family:"Songti SC","SimSun",serif;white-space:pre-wrap}}
.mermaid{{margin:22px 0;text-align:center;background:#fdfcf9;border:1px solid var(--line);
border-radius:6px;padding:16px 8px;overflow-x:auto;font-size:12px;color:#8b93b8}}
#menu{{display:none;position:fixed;left:14px;top:14px;z-index:50;background:var(--side);color:#fff;
border:0;border-radius:6px;padding:8px 11px;font-size:16px;cursor:pointer}}
@media(max-width:900px){{#side{{transform:translateX(-100%);transition:transform .25s}}
#side.on{{transform:none}}#main{{margin-left:0}}.wrap{{padding:62px 20px 100px}}
#menu{{display:block}}#drawer{{width:100vw}}}}
</style></head><body>
<button id="menu">☰</button>
<aside id="side">
 <div class="brand"><h1>{ihtml.escape(a.title)}</h1><p>原·全·术·易 精读 · {len(sections)} 篇</p></div>
 <input id="q" placeholder="搜索全文…（Ctrl/⌘+K）" autocomplete="off">
 <nav id="toc">{nav}</nav>
</aside>
<main id="main"><div class="wrap">{arts}</div></main>
<div id="drawer"><div class="dh"><span id="dtitle">原文</span><button id="dclose">✕</button></div>
<div class="dc" id="dbody"></div></div>
<script>window.SRC={srcz};</script>
<script>
var chapters=[].slice.call(document.querySelectorAll('.chapter'));
var navis=[].slice.call(document.querySelectorAll('.navi'));
var side=document.getElementById('side');
var navmap={{}};navis.forEach(function(a){{navmap[a.dataset.id]=a}});
if('IntersectionObserver' in window){{
  var io=new IntersectionObserver(function(es){{
    es.forEach(function(e){{
      if(e.isIntersecting){{
        navis.forEach(function(a){{a.classList.remove('on')}});
        var a=navmap[e.target.id];
        if(a){{a.classList.add('on');
          if(a.offsetTop<side.scrollTop||a.offsetTop>side.scrollTop+side.clientHeight-90)
            side.scrollTop=a.offsetTop-side.clientHeight/2;}}
      }}
    }});
  }},{{rootMargin:'-8% 0px -82% 0px'}});
  chapters.forEach(function(c){{io.observe(c)}});
}}
navis.forEach(function(a){{a.addEventListener('click',function(){{side.classList.remove('on')}})}});

var drawer=document.getElementById('drawer'),dt=document.getElementById('dtitle'),
    db=document.getElementById('dbody');
document.getElementById('dclose').onclick=function(){{drawer.classList.remove('on')}};
document.addEventListener('click',function(e){{
  var a=e.target.closest('.anc');if(!a)return;
  var rec=window.SRC[a.dataset.ch]||{{}};
  var txt=rec[a.dataset.p]||rec[String(parseInt(a.dataset.p,10))]||'（未找到该段）';
  var sec=a.closest('.chapter');
  dt.innerHTML='第 <b>'+(sec?sec.dataset.title.slice(0,16):a.dataset.ch)+'</b> · p'+a.dataset.p;
  db.textContent=txt;drawer.classList.add('on');
}});

var q=document.getElementById('q');
q.addEventListener('input',function(){{
  var k=q.value.trim();
  navis.forEach(function(a){{
    if(!k){{a.style.display='';return}}
    var ch=document.getElementById(a.dataset.id);
    a.style.display=(a.textContent+(ch?ch.innerText:'')).indexOf(k)>=0?'':'none';
  }});
  if(k.length>=2){{
    for(var i=0;i<chapters.length;i++){{
      if(chapters[i].innerText.indexOf(k)>=0){{chapters[i].scrollIntoView();break}}
    }}
  }}
}});
document.addEventListener('keydown',function(e){{
  if((e.metaKey||e.ctrlKey)&&e.key==='k'){{e.preventDefault();q.focus()}}
  if(e.key==='Escape')drawer.classList.remove('on');
}});
document.getElementById('menu').onclick=function(){{side.classList.toggle('on')}};
if(location.hash){{var el=document.getElementById(location.hash.slice(1));
  if(el)setTimeout(function(){{el.scrollIntoView()}},60);}}

var mm=null;
function renderMermaid(nodes){{
  if(!Array.isArray(nodes))nodes=[nodes];
  nodes=nodes.filter(function(n){{return n&&n.classList.contains('mermaid')&&!n.dataset.done}});
  if(!nodes.length)return Promise.resolve();
  if(!mm){{
    return import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')
      .then(function(m){{mm=m.default;
        mm.initialize({{startOnLoad:false,theme:'base',themeVariables:{{
          fontFamily:'-apple-system,PingFang SC,Microsoft YaHei,sans-serif',fontSize:'13px',
          primaryColor:'#eef0fa',primaryTextColor:'#23262d',primaryBorderColor:'#c3cae8',
          lineColor:'#8b93b8',secondaryColor:'#fdf5e8',tertiaryColor:'#faf8f4'}}}});
        return Promise.all(nodes.map(function(n,i){{
          n.dataset.done='1';
          return mm.render('m'+Date.now()+i,n.textContent)
            .then(function(r){{n.innerHTML=r.svg}}).catch(function(){{}});
        }}));
      }}).catch(function(){{}});
  }}
  return Promise.all(nodes.map(function(n,i){{
    n.dataset.done='1';
    return mm.render('m'+Date.now()+i,n.textContent)
      .then(function(r){{n.innerHTML=r.svg}}).catch(function(){{}});
  }}));
}}
if('IntersectionObserver' in window){{
  var mo=new IntersectionObserver(function(es){{
    es.forEach(function(e){{if(e.isIntersecting){{mo.unobserve(e.target);renderMermaid([e.target])}}}});
  }},{{rootMargin:'400px'}});
  [].slice.call(document.querySelectorAll('.mermaid')).forEach(function(n){{mo.observe(n)}});
}}else{{
  renderMermaid([].slice.call(document.querySelectorAll('.mermaid')));
}}
</script></body></html>'''
    open(a.out, 'w', encoding='utf-8').write(page)
    print(f'已生成 {a.out}｜{os.path.getsize(a.out)/1024/1024:.2f} MB｜{len(sections)} 篇｜{len(toc)} 组')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--notes', required=True, help='笔记目录')
    ap.add_argument('--src', default=None, help='原文目录（用于锚点回看；可略）')
    ap.add_argument('--out', required=True, help='输出 html 路径')
    ap.add_argument('--title', default='精读笔记')
    ap.add_argument('--split', choices=['none', 'part'], default='none',
                    help='none 出单册；part 按笔记子目录（部）各出一册，--out 视为输出目录')
    a = ap.parse_args()

    if a.split == 'none':
        build(a)
        return

    groups = collect(a.notes)
    if len(groups) < 2:
        print(f'只有 {len(groups)} 组，拆册没意义，改出单册')
        build(a)
        return
    if a.out.lower().endswith(('.html', '.htm')):
        a.out = os.path.dirname(a.out) or '.'
        print(f'--split 下 --out 视为目录，改写为 {a.out}')
    os.makedirs(a.out, exist_ok=True)
    made, empty = [], []
    for gname, files in groups:
        if not any(re.match(r'\d+', os.path.basename(f)) for f in files):
            empty.append(gname)
            continue
        safe = re.sub(r'[\\/:*?"<>|]', '_', gname)
        sub = argparse.Namespace(**vars(a))
        sub.out = os.path.join(a.out, f'{safe}.html')
        sub.title = f'{a.title}·{gname}' if gname != '总论' else f'{a.title}·总论'
        build(sub, only=gname)
        made.append(sub.out)
    if empty:
        print(f'跳过无正文章节的目录：{"、".join(empty)}')
    print(f'共 {len(made)} 册：' + '、'.join(os.path.basename(m) for m in made))


if __name__ == '__main__':
    main()
