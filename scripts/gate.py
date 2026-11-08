"""交付门禁：原 · 全 · 术 · 易 四类硬检查。

读笔记 + 台账 + 原文，四项全过才准交付。任一项不过，退出码 1。

用法:
    python gate.py --note note.md --ledger ledger.json --src work/012.md
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit  # 同目录，复用引文/术语/定位核验

CONF = {'原意', '事实', '推断', '存疑', '作者原意', '原文事实与数据', '合理推断', '无法确认'}


def load(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def cjk(t):
    return len(re.findall(r'[\u4e00-\u9fff]', t))


def redundant(text, minlen=30):
    """找重复出现的长片段：同一 30 字串出现两次以上，通常是把同一意思说了两遍。"""
    t = re.sub(r'\s+', '', text)
    seen, dup = {}, []
    for i in range(0, max(0, len(t) - minlen), 8):
        seg = t[i:i + minlen]
        if seg in seen:
            dup.append(seg)
        else:
            seen[seg] = i
    return list(dict.fromkeys(dup))[:6]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--note', required=True)
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--json', default=None)
    ap.add_argument('--min-cover', type=float, default=0.3,
                    help='AR4 要求的锚点覆盖比例，默认 0.3；提要级 0.15 也算过')
    a = ap.parse_args()

    note = open(a.note, encoding='utf-8').read()
    led = load(a.ledger)
    body, paras, nsrc = audit.load_src(a.src)
    total = len(paras) or 1

    items = [audit.verify(f, nsrc) for f, _ in audit.extract_quotes(note)]
    off = [i for i in items if i[0] == 'off']
    ids = [int(x) for x in re.findall(r'\[?ch\d{3}:p(\d{3})\]?', note)]
    ids += [int(x) for x in re.findall(r'[（(]p(\d{3})[)）]', note)]
    uniq = len(set(ids) & set(paras))

    claims = led.get('claims', [])
    blocks = led.get('blocks', [])
    cls = led.get('closedLists', [])
    terms = led.get('terms', [])
    review = led.get('review', {})

    # ---- 原 ----
    ar1 = all(c.get('type') in CONF for c in claims) and bool(claims)
    ar2 = all(all(int(s.strip('p')) in paras for s in c.get('sources', [])) for c in claims) if claims else False
    ar3 = len(off) == 0
    cover = len(set(ids) & set(paras)) / total
    ar4 = len(set(ids) & set(paras)) >= max(3, total * a.min_cover)
    # ---- 全 ----
    covered = {int(b['id'].strip('p')) for b in blocks if str(b.get('id', '')).startswith('p')}
    for c in claims:
        covered |= {int(s.strip('p')) for s in c.get('sources', []) if s.strip('p').isdigit()}
    co1 = len(covered & set(paras)) >= total * 0.9
    co2 = all(int(x.get('expected', -1)) == int(x.get('found', -2)) for x in cls) and bool(cls)
    co3 = 'gaps' in led
    # ---- 术 ----
    sh1 = len(terms) >= max(2, min(5, total // 15))
    sh2 = all(t.get('term') and t.get('def') and t.get('sources') for t in terms)
    # 豁免：若已在笔记里标明「学界通名」「材料外」「作者未用」，不算自造
    WAIVE = ('学界通名', '材料外', '作者未用', '通用译名', '学界通用')
    sus = []
    for t in terms:
        n = audit.norm(t['term'])
        if n in nsrc or t['term'] in audit.DEFAULT_LEXICON:
            continue
        blob = str(t.get('def', '')) + str(t.get('context', '')) + str(t.get('note', ''))
        if any(w in blob for w in WAIVE):
            continue
        sus.append(t['term'])
    sh3 = not sus
    # ---- 易 ----
    yi1 = bool(re.search(r'\bL-?1\b|一句话|^>.*(?:这篇|本章|全书)', note, re.M))
    n = cjk(note)
    yi2 = 800 <= n <= 9000
    yi3 = len(redundant(note)) == 0
    yi4 = True
    for mm in re.findall(r'```mermaid(.*?)```', note, re.S):
        if re.search(r'(-->|---|\|)[^|\n]*\|\s*\d+\s*\|', mm):
            yi4 = False

    rows = [
        ('原', 'AR1 每条结论标注来源等级', ar1, ''),
        ('原', 'AR2 引文逐字回原文', ar3, f'{len(off)} 条对不上' if off else ''),
        ('原', 'AR3 结论挂真实存在的段号', ar2, ''),
        ('原', 'AR4 定位覆盖足够段落', ar4,
         f'{uniq}/{total} = {cover:.1%}，要求 {a.min_cover:.0%}'
         + ('' if ar4 else '｜要么补锚点，要么这是提要级、用 --min-cover 0.15 明说')),
        ('全', 'CO1 逐块覆盖', co1, f'{len(covered & set(paras))}/{total} 段有落点'),
        ('全', 'CO2 封闭清单数目相符', co2, f'{len(cls)} 项清单'),
        ('全', 'CO3 缺口已登记', co3, ''),
        ('术', 'SH1 术语表成规模', sh1, f'{len(terms)} 条'),
        ('术', 'SH2 每条术语有界定与出处', sh2, ''),
        ('术', 'SH3 无自造术语', sh3, ('待改：' + '、'.join(sus[:6])) if sus else ''),
        ('易', 'YI1 有分层概述', yi1, ''),
        ('易', 'YI2 篇幅适度', yi2, f'{n} 字'),
        ('易', 'YI3 无明显重复', yi3, ''),
        ('易', 'YI4 图不靠编号/颜色代替文字', yi4, ''),
    ]
    npass = sum(r[2] for r in rows)
    print(f'{os.path.basename(a.note)}｜{npass}/{len(rows)} 通过 → '
          f'{"准入交付" if npass == len(rows) else "阻止交付"}\n')
    cur = None
    for cat, name, ok, info in rows:
        if cat != cur:
            print(f'【{cat}】')
            cur = cat
        print(f'  {"PASS" if ok else "FAIL"}  {name}' + (f'   —— {info}' if info else ''))
    if a.json:
        json.dump({'rows': [{'cat': c, 'rule': r, 'pass': p, 'info': i} for c, r, p, i in rows],
                   'pass': npass, 'total': len(rows)},
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
