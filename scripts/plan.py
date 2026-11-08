#!/usr/bin/env python3
"""开工前算账：扫原文、定档位、排批次、剔掉已经写过的章。

做一件事 —— 在你花钱之前，先把这本书要花多少钱、分几批、
哪些章不该塞进批量里，摆成一张表。

用法：
  python plan.py --src work/ --notes notes/           # 看计划
  python plan.py --src work/ --notes notes/ --batch 6 # 指定每批章数
  python plan.py --src work/ --tier lite              # 全book强制提要级
  python plan.py --src work/ --json plan.json         # 机器可读，供批处理接力
"""
import argparse
import glob
import json
import os
import re
import sys

CJK = re.compile(r'[\u4e00-\u9fff]')
PARA = re.compile(r'^\[ch(\d{3}):p(\d{3})\]', re.M)

# 四档精度：(档名, 目标字数下限, 目标字数上限, 适用原文篇幅下限, 适用上限)
TIERS = [
    ('index', 200, 400, 0, 3000),
    ('lite', 800, 1200, 3000, 6000),
    ('std', 1500, 2500, 6000, 12000),
    ('deep', 2500, 4000, 12000, 10 ** 9),
]

# 每批原文总量上限（字）。超过这个数，子单元读一遍的上下文就太长，
# 单次调用变贵、且更容易漏段。实测 4 万字一批是稳的。
BATCH_CHARS = 40000
# 单章超过这个字数，独占一批：它是全书最长的几章，塞进批量会拖累同批其它章
SOLO_CHARS = 14000


def load_src(path):
    """读一章原文，返回 (题名, 汉字数, 段数)。"""
    text = open(path, encoding='utf-8').read()
    title = ''
    for ln in text.split('\n')[:6]:
        s = ln.strip()
        if s.startswith('# '):
            title = s[2:].strip()
            break
    if not title:
        title = os.path.basename(path).replace('.md', '')
    title = re.sub(r'^第?\s*\d{1,3}\s*[章节]\s*', '', title)
    return title, len(CJK.findall(text)), len(PARA.findall(text))


def pick_tier(chars, force=None):
    if force:
        return force
    for name, _lo, _hi, c0, c1 in TIERS:
        if c0 <= chars < c1:
            return name
    return 'std'


def tier_words(name):
    for n, lo, hi, _c0, _c1 in TIERS:
        if n == name:
            return lo, hi
    return 1500, 2500


def existing_notes(notes_dir):
    """已写好的笔记，取文件名前三位章号。"""
    hit = {}
    for f in glob.glob(os.path.join(notes_dir, '**', '*.md'), recursive=True):
        if os.sep + 'work' + os.sep in f:
            continue
        m = re.match(r'(\d{1,3})', os.path.basename(f))
        if m:
            hit.setdefault(int(m.group(1)), f)
    return hit


def pack(chapters, batch_size, batch_chars):
    """把章按累计字数装箱，超大章单独一批。"""
    batches, cur, acc = [], [], 0
    for c in chapters:
        solo = c['chars'] >= SOLO_CHARS
        over = acc + c['chars'] > batch_chars
        full = batch_size and len(cur) >= batch_size
        if cur and (solo or over or full):
            batches.append(cur)
            cur, acc = [], 0
        cur.append(c)
        acc += c['chars']
        if solo:
            batches.append(cur)
            cur, acc = [], 0
    if cur:
        batches.append(cur)
    return batches


def main():
    ap = argparse.ArgumentParser(description='精读开工前的成本与批次清单')
    ap.add_argument('--src', required=True, help='原文目录（extract.py 的产出）')
    ap.add_argument('--notes', default=None, help='笔记目录；给了就跳过已写好的章')
    ap.add_argument('--tier', default=None,
                    choices=[t[0] for t in TIERS], help='强制档位，默认按篇幅自动')
    ap.add_argument('--batch', type=int, default=8, help='每批章数上限，默认 8')
    ap.add_argument('--json', default=None, help='把计划写成 json')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.src, '*.md')))
    if not files:
        print(f'{a.src} 里没有 .md，先用 extract.py 拆书', file=sys.stderr)
        return 2

    done = existing_notes(a.notes) if a.notes else {}
    rows, skipped = [], []
    for f in files:
        m = re.match(r'(\d{1,3})', os.path.basename(f))
        if not m:
            continue
        ch = int(m.group(1))
        title, chars, paras = load_src(f)
        if chars < 200:                      # 空章、纯标题页
            continue
        row = dict(ch=ch, title=title, chars=chars, paras=paras, file=f)
        if ch in done:
            row['note'] = done[ch]
            skipped.append(row)
        else:
            row['tier'] = pick_tier(chars, a.tier)
            rows.append(row)

    if not rows:
        print(f'全部 {len(skipped)} 章都已有笔记，没有要写的。')
        return 0

    batches = pack(rows, a.batch, BATCH_CHARS)

    # 预算：原文读一遍 + 笔记写一遍，按中文字符估 token（1 字≈1.6 token），
    # 再乘 2.6 的返工余量（读原文、比对、少量修正各一轮）。
    src_chars = sum(r['chars'] for r in rows)
    note_chars = sum(sum(tier_words(r['tier'])) / 2 for r in rows)
    token_in = src_chars * 1.6 * 2.2
    token_out = note_chars * 1.6 * 1.3

    if not a.quiet:
        print(f'\n待写 {len(rows)} 章，原文 {src_chars:,} 字。'
              f'另有 {len(skipped)} 章已存在，跳过。')
        by = {}
        for r in rows:
            by[r['tier']] = by.get(r['tier'], 0) + 1
        seg = '｜'.join(f'{k} {v} 章' for k, v in sorted(by.items()))
        print(f'档位分布：{seg}')
        print(f'预计笔记 {int(note_chars):,} 字，输入约 {token_in / 10000:.0f} 万 token，'
              f'输出约 {token_out / 10000:.0f} 万 token')
        print(f'排成 {len(batches)} 批：')
        for i, b in enumerate(batches, 1):
            cs = sum(x['chars'] for x in b)
            ids = f"{b[0]['ch']:03d}" if len(b) == 1 else f"{b[0]['ch']:03d}–{b[-1]['ch']:03d}"
            tag = '（大章独占）' if len(b) == 1 and b[0]['chars'] >= SOLO_CHARS else ''
            print(f'  批{i}: {ids}  {len(b)} 章  {cs:,} 字{tag}')
        solo = [r for r in rows if r['chars'] >= SOLO_CHARS]
        if solo:
            print('\n单独派的大章（塞进批量会拖累同批）：')
            for r in solo:
                print(f"  {r['ch']:03d} {r['title']}  {r['chars']:,} 字 {r['paras']} 段")
        thin = [r for r in rows if r['paras'] < 12]
        if thin:
            print(f'\n段数过少（<12 段）{len(thin)} 章，可能是拆章出错，先看一眼：'
                  + '、'.join(f"{r['ch']:03d}" for r in thin[:8]))

    if a.json:
        json.dump(dict(rows=rows, batches=[[r['ch'] for r in b] for b in batches],
                       skipped=[r['ch'] for r in skipped],
                       src_chars=src_chars, note_chars=int(note_chars)),
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if not a.quiet:
            print(f'\n计划已写入 {a.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
