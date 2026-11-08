"""把书或长文拆成带稳定段序锚点的纯文本，供精读流程逐块处理。

锚点格式 [chNNN:pMMM]：章号 + 章内段序。笔记里任何一句引文都能反查到这里。
只用标准库。支持 epub / txt / md / html。

用法:
    python extract.py <入力> --out work/ [--min-chars 120]
"""
import argparse, html, json, os, re, sys, zipfile

BLOCK = r'<br\s*/?>|</p>|</div>|</h[1-6]>|</li>|</tr>|</blockquote>'
NOISE = re.compile(r'^[\s\d\-—·…\.、,，]*$')


def strip_tags(raw):
    raw = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw, flags=re.S | re.I)
    raw = re.sub(BLOCK, '\n', raw, flags=re.I)
    raw = re.sub(r'<[^>]+>', '', raw)
    raw = html.unescape(raw)
    out = []
    for ln in raw.split('\n'):
        ln = re.sub(r'[ \t\u3000\xa0]+', ' ', ln).strip()
        if ln and not NOISE.match(ln):
            out.append(ln)
    return out


def emit(chs, out_dir, src_name):
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for i, (title, paras, src) in enumerate(chs):
        body = '\n\n'.join(f'[ch{i:03d}:p{j:03d}] {p}' for j, p in enumerate(paras))
        path = os.path.join(out_dir, f'{i:03d}.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'# {title}\n\n> 源文件: {src} | 段落数: {len(paras)} | 字数: {sum(len(p) for p in paras)}\n\n{body}\n')
        manifest.append({'ch': i, 'title': title, 'src': src, 'paras': len(paras),
                         'chars': sum(len(p) for p in paras), 'file': f'{i:03d}.md'})
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'book': src_name, 'chapters': manifest}, f, ensure_ascii=False, indent=1)
    tot = sum(m['chars'] for m in manifest)
    print(f'{src_name}: {len(manifest)} 章 / {tot} 字')
    for m in manifest[:3]:
        print(f'  ch{m["ch"]:03d} {m["paras"]:4d}段 {m["chars"]:6d}字  {m["title"][:44]}')
    if len(manifest) > 3:
        print(f'  ... 末章 ch{manifest[-1]["ch"]:03d} {manifest[-1]["chars"]}字 {manifest[-1]["title"][:30]}')
    return manifest


# ---------- epub ----------
def read_epub(path, min_chars):
    z = zipfile.ZipFile(path)
    names = z.namelist()

    def rd(n):
        return z.read(n).decode('utf-8', 'ignore')

    # 目录：toc.ncx 优先，其次 nav.xhtml，最后按 spine 文件顺序
    navs = []
    ncx = next((n for n in names if n.lower().endswith('.ncx')), None)
    if ncx:
        t = rd(ncx)
        for m in re.finditer(r'<navPoint[^>]*>.*?<text>(.*?)</text>.*?<content\s+src="([^"]+)"', t, re.S):
            navs.append((html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip(), m.group(2).split('#')[0]))
    if not navs:
        opf = next((n for n in names if n.lower().endswith('.opf')), None)
        if opf:
            base = os.path.dirname(opf)
            ids = dict(re.findall(r'<item\s+[^>]*id="([^"]+)"[^>]*href="([^"]+)"', rd(opf)))
            items = dict(re.findall(r'<item\s+[^>]*href="([^"]+)"[^>]*id="([^"]+)"', rd(opf)))
            ids.update({v: k for k, v in items.items()})
            spine = re.findall(r'<itemref\s+[^>]*idref="([^"]+)"', rd(opf))
            for s in spine:
                if s in ids:
                    navs.append(('', os.path.normpath(os.path.join(base, ids[s])).replace('\\', '/')))
    if not navs:
        navs = [('', n) for n in names if n.lower().endswith(('.html', '.xhtml', '.htm'))]

    chs, seen = [], set()
    for title, src in navs:
        if src in seen or src not in names:
            continue
        seen.add(src)
        paras = strip_tags(rd(src))
        if not title and paras:
            title = paras[0][:40]
        if paras:
            chs.append((title or f'第 {len(chs)+1} 节', paras, src))
    # 相邻碎章合并，避免一个节标题单独成章
    if min_chars <= 0:
        return chs
    if min_chars <= 0:
        return chs
    merged = []
    for t, p, s in chs:
        if len(''.join(p)) < min_chars and merged:
            mt, mp, ms = merged[-1]
            merged[-1] = (mt, mp + p, ms)
        else:
            merged.append((t, p, s))
    return merged


# ---------- txt ----------
CH_PAT = re.compile(r'^\s*(第[0-9零一二三四五六七八九十百千]+[章回卷部篇节]|序言|自序|前言|引言|导论|绪论|后记|结语|尾声|附录|跋)\b')


def read_txt(path, min_chars):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    lines = [l.strip() for l in raw.split('\n')]
    paras, buf = [], []
    for l in lines:
        if l:
            buf.append(l)
        elif buf:
            paras.append(' '.join(buf) if len(buf) == 1 else '\n'.join(buf))
            buf = []
    if buf:
        paras.append('\n'.join(buf))
    chs, cur_title, cur = [], None, []
    for p in paras:
        first = p.split('\n')[0]
        if len(first) < 40 and CH_PAT.match(first):
            if cur:
                chs.append((cur_title or f'第 {len(chs)+1} 节', cur, path))
            cur_title, cur = first, []
        else:
            cur.append(p)
    if cur:
        chs.append((cur_title or f'第 {len(chs)+1} 节', cur, path))
    return chs or [('全文', paras, path)]


# ---------- md / html ----------
def read_md(path, min_chars):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    blocks, cur_title, cur = [], None, []
    for line in raw.split('\n'):
        if re.match(r'^#\s+', line):
            if cur:
                blocks.append((cur_title or path, cur, path))
            cur_title, cur = line.lstrip('#').strip(), []
        elif line.strip():
            cur.append(line.strip())
        elif cur:
            cur.append('')
    if cur:
        blocks.append((cur_title or path, cur, path))
    out = []
    for t, ls, s in blocks:
        paras = [p for p in '\n'.join(ls).split('\n\n') if p.strip()]
        if paras:
            out.append((t, paras, s))
    return out or [('全文', [raw[:2000]], path)]


def read_html(path, min_chars):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    parts = re.split(r'(?=<h1[^>]*>)', raw, flags=re.I)
    out = []
    for i, part in enumerate(parts):
        m = re.match(r'<h1[^>]*>(.*?)</h1>', part, re.S | re.I)
        title = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else f'第 {i+1} 节'
        paras = strip_tags(part)
        if paras:
            out.append((title, paras, path))
    return out or [('全文', strip_tags(raw), path)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--out', default='work')
    ap.add_argument('--min-chars', type=int, default=0, help='小于此字数的章并入上一章；默认 0 不合并，保持章号与原始目录一一对应')
    a = ap.parse_args()
    p, ext = a.input, os.path.splitext(a.input)[1].lower()
    reader = {'.epub': read_epub, '.txt': read_txt, '.md': read_md,
              '.markdown': read_md, '.html': read_html, '.htm': read_html}.get(ext)
    if not reader:
        sys.exit(f'不支持的格式: {ext}（支持 epub/txt/md/html）')
    chs = reader(p, a.min_chars)
    emit(chs, a.out, os.path.basename(p))


if __name__ == '__main__':
    main()
