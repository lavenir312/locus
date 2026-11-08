"""原·术·全 三项机器核验。

  quotes  引文逐字回核：引号里的话必须能在原文找到，或明确是省略节选
  terms   术语核验：笔记里的术语必须出自原文，或属通行学术术语，不许自造
  anchors 定位核验：每个段序锚点必须指向真实存在的段落

用法:
    python audit.py quotes  --note note.md --src work/012.md
    python audit.py terms   --note note.md --src work/012.md [--lexicon lex.txt]
    python audit.py anchors --note note.md --src work/012.md
    python audit.py all     --note note.md --src work/012.md --json out.json
退出码：全过 0，有 off 引文或疑似自造术语 1。
"""
import argparse, json, os, re, sys

PUNCT = '，。、；：？！「」『』（）()《》〈〉“”‘’"\'—…·,.;:?!/\\-*#>|`~[]{} \t\n\r　　'
_TBL = {ord(c): None for c in PUNCT}


def norm(s):
    return s.translate(_TBL).lower()


# 通行学术术语，命中即视为合规（可被 --lexicon 追加）
DEFAULT_LEXICON = """
叙事视角 全知视角 限知视角 叙事者 隐含作者 可靠叙事 不可靠叙事 复调 狂欢化 陌生化 典型化
现实主义 批判现实主义 浪漫主义 现代主义 后现代主义 自然主义 象征主义 唯美主义
启蒙 启蒙运动 人道主义 人文主义 国民性 民族性 白话文 文言 话本 章回体 谴责小说
鸳鸯蝴蝶派 新文化运动 五四运动 文学革命 人的文学 人民文学 普罗文学 左翼文学
阶级分析 阶级论 人性论 精神胜利法 奴隶 奴才 主奴关系 官本位 立人
能指 所指 隐喻 换喻 反讽 悖论 互文性 母题 原型 意象 叙事学 结构主义 解构主义
话语 意识形态 现代性 主体性 他者 规训 文化霸权 公共领域 有机知识分子 文化领导权
社会主义 资本主义 封建主义 官僚制 科层制 韦伯式 内卷化 差序格局 乡土中国
EPUB PDF DOCX TXT HTML MD Mermaid mermaid JSON OCR AI LLM
""".split()


def load_src(path):
    t = open(path, encoding='utf-8').read()
    # 去掉行首锚点，正文单独保存；同时保留「段号 -> 原文」映射
    paras = {}
    for m in re.finditer(r'\[ch(\d{3}):p(\d{3})\]\s*([^\n]*(?:\n(?!\[ch|\n)[^\n]*)*)', t):
        paras[int(m.group(2))] = m.group(3).strip()
    body = '\n'.join(paras[k] for k in sorted(paras)) if paras else t
    body_nc = re.sub(r'\[\d{1,3}\]', '', body)  # 去掉尾注编号再比对
    return body, paras, norm(body_nc)


def lcs_ratio(a, b):
    """a 的最长公共子串长度 / len(a)。只用于短片段对窗口。"""
    if not a or not b:
        return 0.0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                v = prev[j - 1] + 1
                cur[j] = v
                if v > best:
                    best = v
        prev = cur
    return best / len(a)


def verify(frag, nsrc):
    # 剥离引文末端的定位括注，如 (p011，引自《忽然想到·三》)
    frag = re.sub(r'[（(]\s*p\d{3}[^）)]*[)）]\s*$', '', frag)
    frag = re.sub(r'[（(]\s*第\s*\d+[^）)]*[)）]\s*$', '', frag)
    # 省略号分段核对：每段都在原文里，说明是合法节选而非改写
    segs = [s for s in re.split(r'…+|\.{3,}', frag) if len(norm(s)) >= 6]
    if len(segs) >= 2:
        subs = [verify(s, nsrc) for s in segs]
        if all(v in ('exact', 'near', 'spliced') for v, _ in subs):
            return 'spliced', 1.0
    n = norm(frag)
    if len(n) < 6:
        return 'too_short', 1.0
    if n in nsrc:
        return 'exact', 1.0
    key = n[:10]
    idx = nsrc.find(key)
    if idx >= 0:
        win = nsrc[max(0, idx - 30): idx + len(n) + 30]
        r = lcs_ratio(n, win)
        if r >= 0.85:
            return 'near', round(r, 3)
        return 'off', round(r, 3)
    if len(n) <= 100:
        r = lcs_ratio(n, nsrc)
        return ('near' if r >= 0.85 else 'off'), round(r, 3)
    return 'off', 0.0


# ---------- quotes ----------
LABEL_Q = re.compile(r'〔引〕\s*[“"]([^“”"\n]{4,}?)[”"]')
ANCHORED_Q = re.compile(r'[“"]([^“”"\n]{10,}?)[”"]\s*[（(]?p\d{3}')

META = ('AI 辅助', '底本', '标注约定', '执行方式', '材料：', '定位', '输出：', '原书：', '版权', '来源：', '四档', '以下为', '第一部分')


def extract_quotes(text):
    """统一的引文抽取。四种写法都算，同一套规则给 audit 与 batch_audit 共用：
       〔引〕"……"（显式标注）｜"……"（紧跟 (pMMM) 锚点）｜> 引用块｜「……」
    """
    cut = text.find('\n## ')
    if cut > 0:
        text = text[cut:]

    # 术语表 / 缺口 / 核验台账等节不是引文
    keep, skip = [], False
    for ln in text.split('\n'):
        if re.match(r'^##\s*(术语|缺口|接回|核验|方法来源|附)', ln):
            skip = True
            continue
        if re.match(r'^##\s', ln):
            skip = False
        if not skip:
            keep.append(ln)
    body = '\n'.join(keep)

    out = []
    for m in LABEL_Q.finditer(body):
        out.append((m.group(1).strip(), '标注引文'))
    for m in ANCHORED_Q.finditer(body):
        out.append((m.group(1).strip(), '紧跟锚点'))
    for line in body.split('\n'):
        s = line.strip()
        if s.startswith('|'):
            continue
        if s.startswith('>'):
            frag = s.lstrip('> ').strip()
            frag = re.sub(r'^〔引〕\s*', '', frag)          # 去掉引文标记
            frag = re.sub(r'\s*(\[ch\d{3}:p\d{3}\]|[（(]?p\d{3}[）)]?)\s*$', '', frag)  # 去尾部锚点（两种写法）
            inner = re.search(r'[“"]([^“”"\n]{6,})[”"]', frag)
            if inner:                                       # 有内层引号就取内层
                frag = inner.group(1)
            if len(norm(frag)) >= 12 and not any(frag.startswith(m) for m in META):
                out.append((frag, '引用块'))
    for q in re.findall(r'「([^「」]{6,300})」', body):
        if len(norm(q)) >= 6:
            out.append((q, '直角引号'))

    seen, res = set(), []
    for frag, kind in out:
        frag = frag.strip('。，、；：')
        key = norm(frag)
        if key and key not in seen and len(key) >= 6:
            seen.add(key)
            res.append((frag, kind))
    return res


def cmd_quotes(note, src):
    body, paras, nsrc = load_src(src)
    items = []
    for frag, kind in extract_quotes(open(note, encoding='utf-8').read()):
        verdict, r = verify(frag, nsrc)
        items.append({'kind': kind, 'verdict': verdict, 'ratio': r, 'text': frag[:70]})
    ex = [i for i in items if i['verdict'] == 'exact']
    sp = [i for i in items if i['verdict'] == 'spliced']
    nr = [i for i in items if i['verdict'] == 'near']
    off = [i for i in items if i['verdict'] == 'off']
    print(f'引文 {len(items)} 条｜逐字 {len(ex)}｜省略节选(逐段核对通过) {len(sp)}｜近似 {len(nr)}｜对不上 {len(off)}')
    for i in off:
        print(f'  [对不上 {i["ratio"]}] {i["text"]}')
    for i in nr:
        print(f'  [近似 {i["ratio"]}] {i["text"][:50]}')
    return {'total': len(items), 'exact': len(ex), 'spliced': len(sp), 'near': len(nr),
            'off': len(off), 'items': items}


# ---------- terms ----------
TERM_PATTERNS = [
    (re.compile(r'「([^「」，。？！；：\s]{2,12})」'), '引号术语'),
    (re.compile(r'\*\*([^*\n，。？！；：、]{2,10})\*\*'), '加粗术语'),
    (re.compile(r'\b([A-Z]{2,8})\b'), '英文缩写'),
]
TITLES = re.compile(r'《([^》]{2,30})》')  # 书名单列，不参与"自造术语"判罚


def cmd_terms(note, src, lexicon):
    body, paras, nsrc = load_src(src)
    text = open(note, encoding='utf-8').read()
    lex = set(DEFAULT_LEXICON) | set(lexicon)
    nlex = {norm(x) for x in lex}
    # mermaid 代码块里的 flowchart/sequenceDiagram 等语法词不是术语
    text = re.sub(r'```mermaid[\s\S]*?```', '', text)
    LABELS = {'作者说', '我的判断', '引', '推断', '原意', '事实', '存疑', '一句话', '注', '出处'}
    cand, seen = [], set()
    for pat, kind in TERM_PATTERNS:
        for m in pat.finditer(text):
            t = m.group(1).strip()
            if t in seen or len(norm(t)) < 2 or t in LABELS:
                continue
            seen.add(t)
            cand.append((t, kind))
    titles = [x.strip() for x in TITLES.findall(text)]
    ok, lexhit, suspect = [], [], []
    for t, kind in cand:
        n = norm(t)
        if n and n in nsrc:
            ok.append((t, kind, '原文有'))
        elif t in lex or n in nlex:
            lexhit.append((t, kind, '通行术语'))
        else:
            suspect.append((t, kind, '原文无、词表无'))
    print(f'术语候选 {len(cand)}｜原文可查 {len(ok)}｜通行术语表命中 {len(lexhit)}｜需核查 {len(suspect)}')
    if titles:
        miss_t = [x for x in titles if norm(x) not in nsrc]
        if miss_t:
            print(f'  （书名 {len(titles)} 个，其中 {len(miss_t)} 个不在本章原文内，属正常：' + '、'.join(miss_t[:4]) + '）')
    for t, kind, why in suspect:
        print(f'  [需核查] {t}  ({kind}) —— {why}；若为自造请改学界通用名，若来自材料外请标「材料外」')
    if lexhit:
        print('  通行术语用法示例：' + '、'.join(t for t, _, _ in lexhit[:10]))
    return {'total': len(cand), 'in_source': len(ok), 'lexicon': len(lexhit), 'suspect': len(suspect),
            'suspect_list': [t for t, _, _ in suspect]}


# ---------- anchors ----------
def cmd_anchors(note, src):
    body, paras, nsrc = load_src(src)
    text = open(note, encoding='utf-8').read()
    ids = [int(x) for x in re.findall(r'\[?ch\d{3}:p(\d{3})\]?', text)]
    ids += [int(x) for x in re.findall(r'[（(]p(\d{3})[)）]', text)]
    for a, b in re.findall(r'第\s*(\d+)\s*[–\-—]\s*(\d+)\s*段', text):
        ids += list(range(int(a), int(b) + 1))
    ids += [int(x) for x in re.findall(r'第\s*(\d+)\s*段', text)]
    total = len(paras) or 1
    present = set(paras)
    bad = sorted(set(i for i in ids if i not in present))
    uniq = len(set(ids) & present)
    print(f'定位 {len(ids)} 处｜指向不同段落 {uniq}/{total}（{uniq/total:.0%}）｜越界或不存在的段号 {len(bad)}')
    if bad:
        print('  不存在的段号：' + '、'.join(f'p{b:03d}' for b in bad[:20]))
    return {'total': len(ids), 'unique': uniq, 'paras_total': total,
            'coverage': round(uniq / total, 3), 'bad': bad}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['quotes', 'terms', 'anchors', 'all'])
    ap.add_argument('--note', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--lexicon', default=None, help='额外术语表文件，一行一词')
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    lexicon = []
    if a.lexicon and os.path.exists(a.lexicon):
        lexicon = [l.strip() for l in open(a.lexicon, encoding='utf-8') if l.strip()]
    res = {}
    if a.cmd in ('quotes', 'all'):
        print('=== 引文 ===')
        res['quotes'] = cmd_quotes(a.note, a.src)
    if a.cmd in ('terms', 'all'):
        print('\n=== 术语 ===')
        res['terms'] = cmd_terms(a.note, a.src, lexicon)
    if a.cmd in ('anchors', 'all'):
        print('\n=== 定位 ===')
        res['anchors'] = cmd_anchors(a.note, a.src)
    if a.json:
        json.dump(res, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'\n结果写入 {a.json}')
    fail = res.get('quotes', {}).get('off', 0) > 0 or res.get('terms', {}).get('suspect', 0) > 0 \
        or len(res.get('anchors', {}).get('bad', []) or []) > 0
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
