#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量核验一组章节笔记：引文逐字、锚点真实、段落覆盖。

适用场景：一本书分章写成 N 个 md，需要一次核完，而不是逐章跑 audit.py。

用法
    python batch_audit.py --notes out/ --src work/
    python batch_audit.py --notes out/ --src work/ --json report.json

约定
    原文文件：<src>/NNN.md（三位数字开头），段落以 [chNNN:pMMM] 开头
    笔记文件：<notes>/**/NNN_*.md，或与原文同名的 NNN.md
    笔记里的定位写法：紧邻锚点用 (pMMM)，跨章引用用 [chNNN:pMMM]

判定
    exact   逐字命中
    spliced 含「……」的节选，逐段都能命中（合法）
    near    部分命中
    off     命中不到，需要人工看
"""
import os, re, json, glob, argparse, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from audit import extract_quotes as _extract, verify as _verify, norm as _norm
except Exception:                      # 单独分发时退回本地实现
    _extract = None
    _verify = None
    _norm = None

PUNCT = re.compile(r'[\s\u3000]|[\u3000-\u303f]|[\uff00-\uffef]'
                   r'|[.,;:!?\'"()\[\]{}—–\-…·、。，；：？！“”‘’《》（）〔〕【】]')


def norm(s):
    s = re.sub(r'\[\d{1,3}\]', '', s)      # 去尾注编号
    return PUNCT.sub('', s)


def load_src(src_dir):
    """{ch: {p: text}}"""
    data = {}
    for f in glob.glob(os.path.join(src_dir, '*.md')):
        b = os.path.basename(f)
        m = re.match(r'(\d{3})', b)
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


INLINE_Q = re.compile(r'[“"]([^“”"\n]{10,}?)[”"]')
LABEL_Q = re.compile(r'〔引〕\s*[“"]([^“”"\n]{4,}?)[”"]')
ANCHORED_Q = re.compile(r'[“"]([^“”"\n]{10,}?)[”"]\s*[（(]?p\d{3}')


def extract_quotes(text):
    """只取真正的引用：显式标注、紧跟锚点，或引用块。跳过术语表/缺口等节。"""
    keep, skip = [], False
    for ln in text.split('\n'):
        if re.match(r'^##\s*(术语|缺口|接回|核验|方法来源|附)', ln):
            skip = True
            continue
        if re.match(r'^##\s', ln):
            skip = False
        if skip or ln.strip().startswith(('>', '|')):
            continue
        keep.append(ln)
    t = '\n'.join(keep)
    out = [m.group(1).strip() for m in LABEL_Q.finditer(t)]
    out += [m.group(1).strip() for m in ANCHORED_Q.finditer(t)]
    seen, res = set(), []
    for q in out:
        q = q.strip('。，、；：')
        if q and q not in seen and len(norm(q)) >= 6:
            seen.add(q)
            res.append(q)
    return res


def verify(q, nsrc):
    segs = [s for s in re.split(r'…+|\.{3,}', q) if len(norm(s)) >= 6]
    if len(segs) >= 2:
        ok = sum(1 for s in segs if norm(s) in nsrc)
        if ok == len(segs):
            return 'spliced'
        return 'off' if ok == 0 else 'near'
    n = norm(q)
    if not n:
        return 'empty'
    if n in nsrc:
        return 'exact'
    for size in (20, 14, 10, 7):
        for i in range(0, max(1, len(n) - size + 1), max(1, size // 2)):
            if n[i:i + size] in nsrc:
                return 'near' if size >= 10 else 'off'
    return 'off'


if _extract is not None:
    def extract_quotes(text):
        return [q for q, _k in _extract(text)]

    def verify(q, nsrc):
        # audit.verify 返回 (verdict, ratio)，这里只取判定
        r = _verify(q, nsrc)
        return r[0] if isinstance(r, tuple) else r

    norm = _norm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--notes', required=True, help='笔记目录（递归）')
    ap.add_argument('--src', required=True, help='原文目录，含 NNN.md')
    ap.add_argument('--json', default=None, help='输出明细 JSON')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    src = load_src(a.src)
    files = sorted(f for f in glob.glob(os.path.join(a.notes, '**', '*.md'), recursive=True)
                   if os.sep + 'work' + os.sep not in f)   # 原文目录不是笔记
    rows, tq, tok = [], 0, 0
    for f in files:
        b = os.path.basename(f)
        m = re.match(r'(\d+)', b)
        if not m:
            continue
        ch = int(m.group(1))
        paras = src.get(ch)
        if not paras:
            rows.append({'file': b, 'error': '原文缺失'})
            continue
        text = open(f, encoding='utf-8').read()
        # 跨章文件（总论/纲要）：引文在全书范围内核，锚点按各自章号校验
        cross = bool(re.search(r'\[ch\d{3}:p\d{3}\]', text))
        if cross:
            nsrc = norm('\n'.join(k for c in src.values() for k in c.values()))
            ids, bad = [], []
            for c2, p2 in re.findall(r'\[ch(\d{3}):p(\d{3})\]', text):
                ids.append(int(p2))
                if p2 not in src.get(int(c2), {}):
                    bad.append(f'ch{c2}:p{p2}')
            for p2 in re.findall(r'\(p(\d{3})\)', text):
                ids.append(int(p2))
        else:
            nsrc = norm('\n'.join(paras[k] for k in sorted(paras)))
            ids = [int(x) for x in re.findall(r'\(p(\d{3})\)', text)]
            ids += [int(x) for x in re.findall(r'\[ch\d{3}:p(\d{3})\]', text)]
            bad = sorted(set(i for i in ids if f'{i:03d}' not in paras))
        items = [(q, verify(q, nsrc)) for q in extract_quotes(text)]
        valid = ids if cross else [i for i in ids if f'{i:03d}' in paras]
        cnt = {k: sum(1 for _, v in items if v == k) for k in ('exact', 'spliced', 'near', 'off')}
        tq += len(items)
        tok += cnt['exact'] + cnt['spliced']
        rows.append({'ch': ch, 'file': b, 'paras': len(paras), 'quotes': len(items), **cnt,
                     'anchors': len(ids), 'anchor_valid': len(valid), 'anchor_bad': bad[:8],
                     'cross': cross,
                     'para_cover': round(len(set(valid)) / max(1, len(paras)), 2) if not cross else 0,
                     'off_list': [q[:60] for q, v in items if v == 'off'][:5]})

    ok = [r for r in rows if 'error' not in r]
    print(f'核验 {len(ok)} 篇｜引文 {tq} 条：逐字 {sum(r["exact"] for r in ok)}，'
          f'省略节选 {sum(r["spliced"] for r in ok)}，近似 {sum(r["near"] for r in ok)}，'
          f'对不上 {sum(r["off"] for r in ok)}')
    ta, tv = sum(r['anchors'] for r in ok), sum(r['anchor_valid'] for r in ok)
    print(f'锚点 {ta} 处：有效 {tv}，越界 {ta - tv}')
    if not a.quiet:
        print(f'\n{"章":>4} {"段":>4} {"引文":>4} {"逐字":>4} {"节选":>4} {"不符":>4} {"锚点":>4} {"覆盖":>6}')
        for r in ok:
            flag = ' <<' if r['off'] or r['anchor_bad'] else ''
            print(f'{r["ch"]:>4} {r["paras"]:>4} {r["quotes"]:>4} {r["exact"]:>4} '
                  f'{r["spliced"]:>4} {r["off"]:>4} {r["anchors"]:>4} {r["para_cover"]:>6.0%}{flag}')
    bad = [r for r in ok if r['off'] or r['anchor_bad']]
    if bad:
        print('\n需人工看：')
        for r in bad:
            print(f'  {r["file"]}：不符 {r["off"]}，坏锚点 {r["anchor_bad"]}')
            for q in r['off_list']:
                print(f'     「{q}」')
    if a.json:
        json.dump(rows, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'\n明细已写入 {a.json}')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
