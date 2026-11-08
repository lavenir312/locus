# ledger.json 模板

台账是笔记的底账，不是给人读的，是给门禁和下一轮复查用的。放在笔记同目录。

```json
{
  "book": "书名",
  "chapter": "ch012",
  "src": "work/012.md",
  "blocks": [
    {"id": "p000", "status": "no-content", "reason": "EPUB 转换占位「未知」"},
    {"id": "p001", "status": "duplicate", "reason": "与章标题重复"},
    {"id": "p004", "status": "covered", "reason": "进入 claim-001"}
  ],
  "claims": [
    {"id": "claim-001", "type": "原意", "text": "白话/启蒙/西学三项晚清已具备，不构成分界", "sources": ["p004", "p005"]},
    {"id": "claim-002", "type": "推断", "text": "换官不换制度则贪腐仍在", "sources": ["p010"],
     "note": "原文以连续设问呈现，非断言"}
  ],
  "closedLists": [
    {"id": "cl-01", "label": "《药》五个阶层", "expected": 5, "found": 5, "sources": ["p030"]},
    {"id": "cl-02", "label": "作者给出的三个层次", "expected": 3, "found": 3, "sources": ["p012", "p018", "p025"]},
    {"id": "cl-03", "label": "转变发生的三个条件", "expected": 3, "found": 3, "sources": ["p050"]},
    {"id": "cl-04", "label": "土谷祠之梦四预言", "expected": 4, "found": 4, "sources": ["p042"]},
    {"id": "cl-05", "label": "本章尾注", "expected": 27, "found": 27, "sources": ["p060", "p086"]}
  ],
  "terms": [
    {"term": "官本位", "en": "official-centrism",
     "def": "把官场职位视为社会资源与价值中心的观念结构",
     "context": "作者用来概括晚清谴责小说共同的问题意识（p008）",
     "related": ["国民性"], "sources": ["p008", "p009"], "first": "p008"}
  ],
  "gaps": [
    "作者称「官场官员形象消失」很少有人统计讨论，但章内未给出计数，属定性观察",
    "尾注所引原始文献（陈平原、钱理群、竹内好、毕飞宇、阿城）未核对"
  ],
  "review": {
    "errorPass": [
      {"id": "F-01", "finding": "尾注[7]用1981版、[10]引同篇用2005版", "action": "分别登记，不合并"}
    ],
    "omissionPass": [
      {"id": "M-01", "finding": "p033「狂人最后也赴某地候补」初稿漏收", "action": "补入正文"}
    ]
  }
}
```

## 填表规矩

- `blocks` 只要没进 claims，就必须有一条，状态四选一，理由一句话。
- `claims.type` 只用四个值：原意 / 事实 / 推断 / 存疑。
- `closedLists` 的 expected 来自原文的说法（「至少三层」「五个阶层」），found 是逐个数出来的结果。两数不等时改 found 不改 expected。
- `terms.first` 必须是 sources 里最早的段号。
- `gaps` 必须存在。没有缺口写空数组，不要省略这个字段。
- `review` 两遍分开记，每条有 id、发现、处置。
