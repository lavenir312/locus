# 机制出处：每条规则从哪来

本工具不是凭空设计的，四原则每条都可追溯到具体仓库的具体文件。有争议时以原仓库为准，这里只做取舍。

## 原｜忠诚原文

| 机制 | 出处 | 原话或要点 |
|---|---|---|
| 四档置信度 | dsh-deepread `skills/dsh-deepread/references/knowledge-map.md` | 作者原意（绿）＝原文明确表达的主张；原文事实与数据；合理推断（琥珀）＝基于原文的推演，原文未明说；无法确认（红）＝原文没有依据或来自原文之外 |
| 出处强制格式 | learn-from-materials `references/content-contract.md` · 出处规则 | 书籍 PDF 必须写「第N章《标题》·原书第N–M页·PDF第X–Y页」，不得只写页数或只写章号；「不把段落号推测成页码」 |
| 不虚报定位 | learn-from-materials `references/coverage-audit-schema.md` · 强制校验第 5、6 条 | 页码超出真实映射即报错；没有物理页边界的 PDF 不得标成精确页码 |
| 引文与改写分开 | learn-from-materials `content-contract.md` | 「材料原话只少量引用并明确标识；页面改写、模型推导、模型补充和外部检索必须彼此区分」 |

## 全｜完整详尽

| 机制 | 出处 | 原话或要点 |
|---|---|---|
| 逐块覆盖台账 | learn-from-materials `coverage-audit-schema.md` | 每个 sourceBlock 登记 status（covered / no-content / unreadable / duplicate）与理由 |
| 双向映射 | 同上 · 强制校验第 8 条 | 必须完成「材料关键主张→页面总结」与「页面总结→材料关键主张」两个方向；任何遗漏主张、孤立总结、跨单元错配都会阻止渲染 |
| 单元粒度 | `content-contract.md` · 内容单元规则 | 「结论组与分点不设置数量上限；按材料论证块完整展开，只有材料确实没有更多独立内容时才自然结束」 |
| 缺口不补 | `content-contract.md` · 小巴讲解与知识边界 | 材料未覆盖时明确说明；「禁止伪造材料出处，也禁止把模型补充写回静态材料知识库」 |
| 反面教训 | diomir0/idlearn `app/pipeline.py` | 中间层提示词只有一句 "Summarize concisely while preserving all key information"，没有封闭清单保护，27 条尾注在最终摘要里全部消失。**逐层压缩会吃掉细节，所以台账要在压缩之前建** |

## 术｜用专业概念

| 机制 | 出处 | 原话或要点 |
|---|---|---|
| 术语清单字段 | learn-from-materials `content-contract.md` · 术语大全规则 | term / fullName / zhMeaning / definition / context / related / units / 各自出处 / firstUnitId / sourceOrder |
| 概念边界 | 同上 | 「definition 准确解释『是什么』，不要为了通俗牺牲概念边界」 |
| 语境分离 | 同上 | 「context 只写材料怎样使用该词；材料外知识不能冒充材料语境」 |
| 术语去重 | 同上 | 先读 glossary、各单元 Key Concepts、材料命名框架、英文缩写，再去重 |
| 不做的事 | — | 五个仓库都没有术语一致性校验脚本。本工具的 `audit.py terms` 是为补这个缺口写的：把术语回原文找，原文没有又不是通行学术术语的，判为疑似自造 |

## 易｜可读不冗余

| 机制 | 出处 | 原话或要点 |
|---|---|---|
| 三级递进（解释→类比→图） | learn-from-materials `content-contract.md` · 小巴讲解与知识边界 | 一、首次先给学术严谨、概念准确、结构清楚的解释，不主动举例、不主动生成图片；二、用户明确说没懂才用画像类比，同时保留严谨定义；三、再次表示不理解才调用可视化 |
| 分层摘要 | 书籍蒸馏（本机 skill）`references/layered-summary.md` | L1 一句话 / L2 一段话 / L3 一页纸骨架 |
| 叙述优于罗列 | pf-sjtu/fastReader `src/services/prompts/config/v3-prompts.yaml` | chapterSummary 把「原文明确说了的」与「评析」切成两部分，第一部分只复述，不掺判断 |
| 图的四条硬约束 | learn-from-materials `references/diagram-design-and-delivery.md` · Visual standard | 「A number never stands alone: every numbered node always shows its title and type」；关系文字要写出两端（「覆铜板是 PCB 的核心组件 → 特种电子树脂的产品升级」），不许写「06 → 07」；Color alone must not encode relationships；Missing evidence is never permission to manufacture connections |
| 一份措辞 | 同上 · Two views, one wording source | 卡片与图共用同一份措辞（`model.nodes` + 共享的 describe()），不写第二份 |
| 删冗余 | 同上 · visual-system.md | 「Remove redundant graph introductions and large empty areas above a map」 |

## 不采用的部分

- learn-from-materials 的图形引擎（曲线布局、碰撞检测、动效调度）实现成本高，本工具用 mermaid 代替，只继承它的四条语义约束。
- dsh-deepread 的费曼式复习流程（合上书讲一遍、间隔复习计划）适合学习场景，精读笔记不强制。
- fastReader 的 WebDAV 同步、章节级缓存属于应用层，与笔记质量无关。
- idlearn 的递归摘要策略整条不采用——它正是「细节被中间层吃掉」的反例。
