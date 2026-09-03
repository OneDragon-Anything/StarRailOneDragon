# 货币战争重构周期文档审计(DOC_AUDIT_CYCLE1)

> 审计日期:2026-09-01。审计者:独立文档审计子 agent(未参与本周期写作)。
> 范围:① proofs p38/p39/p40/p42/p43/p46/p47/p48/p49/p50(本周期有勘误/修复性编辑的十件);② user_playstyle.md([41]/[42])/economy.md(§1/§10.1)/combat.md §4;③ docs/develop/currency_war/redesign/ 全套(README/01/02/03/NAVIGATION/PHASE2_PACKAGE_REPORT);④ 同步性抽查(02 R 条目 vs 注册表源码直调 6 条;01 §4 消费点 vs cw3/ 落位 4 处)。
> 本报告只记录,未改任何被审文档。

---

## 1. 高危项:对抗报告临时引用悬空(重点检查项)

### 1.1 事实盘点

按项目注释/文档规范「**引用必须是持久索引**」,正文引用要么是持久索引(ADR-NNNN/文件路径/符号名),要么是纯语义描述。本周期十件证明正文中的对抗轮次标记(`P4x_ADV_RN`、`FINAL_SWEEP_A/B`、`DESIGN_FINAL_ATTACK 阻断-N` 等)指向的原始报告**全部**落在 `.debug/temp/currency_war/redesign/`(如 `P48_ADV_R1.md`/`P48_ADV_R1_DISPOSITION.md`/`FINAL_SWEEP_A.md`/`DESIGN_FINAL_ATTACK.md`)——该目录**不入 git**,temp 清理后所有引用悬空,勘误的证据链(谁提出、亲跑证伪数据、处置裁决)将无处可考。

**标记数量与分布(十件审计范围内,正则精确计数):**

| 文件 | 标记总数 | 明细 |
|---|---|---|
| p40-refresh-ev.md | **26** | P40_ADV_R1×11、R2×8、R3×5、FINAL_SWEEP_A×1、(跨引 P46_ADV_R3×1) |
| p46-spend-gate-rejection-ev.md | **16** | P46_ADV_R1×6、R2×4、R4×3、FINAL_SWEEP_B×1、(跨引 P40/P46_ADV_R3 各×1) |
| p38-completion-probability.md | **14** | P38_ADV_R2×8、R1×5、FINAL_SWEEP_A×1 |
| p47-interest-account.md | **11** | P47_ADV_R1×5、R3×3、R2×3 |
| p39-levelup-ev.md | **9** | P39_ADV_R1×6、R2×3 |
| p48-batch-xp-banking-ev.md | **5** | P48_ADV_R1×3、FINAL_SWEEP_B×2 |
| p43-streak-interest-tradeoff-ev.md | **2** | P43_ADV_R2×2 |
| p42 / p49 / p50 | **0** | 正文已收敛(残留为「R1 勘误:…」等语义化措辞或以内容本身陈述) |
| **合计** | **83** | |

范围外同型:p41-hoard-sell-ev.md 密度更高(P41_ADV_R1/R2/R3 数十处,含 `R3-N4`/`R2-B1` 式条目标记),同病,处置时应一并纳入。此外 redesign 设计文档也引用同一批临时报告:01 §4.10(DESIGN_FINAL_ATTACK 阻断-2)、01 §7/03 §3 批1(阻断-1)、02 R03(阻断-2)、02 R05(R2-F1-需改⑧)、01/02/03 全文的 `R3-N5`/`R4-M3`/`R5 勘误`/`R6-N7`/`R9 核验` 等轮次标记 → 指向 `.debug/temp/currency_war/redesign/ADVERSARIAL_R1-R9*.md`。

### 1.2 评估:收敛 vs 晋升

两手段都需要,**按标记内容三分类处置**:

- **A 类(约 7 成):「P4x_ADV_RN 修/勘误:初稿说 X,现为 Y」**——修订内容已完整吸收进正文当前表述,标记只剩过程史。→ **收敛**:删标记,保留正文当前结论(其成立理由正文已自带)。这类是规范「变更史不进正文」的直接违例,删标记即是合规化,不损失信息。
- **B 类:标记背后有独立证据数据,正文只给了结论**(例:p41 B1 翻序实证 12/32 与 45/243 网格数据、p47 R2 亲算 549 格对拍、p38 ADV_R1 R5 变等级混合探针 ≤0.4pp、DESIGN_FINAL_ATTACK 阻断-2 的轮岗 361/1806 频率证据)。→ **晋升**:把该证据段(数据+脚本指针)落进对应证明件的「自检与证据」节,或把含脚本(`p47_adv_r2_check.py` 等)一并晋升到 `tools/cw/proofs/`(已有先例:interest_account.py 头注即指向 `tools/cw/proofs/p47_check.py`)。
- **C 类:处置裁决本身**(DISPOSITION 文件里的「接受/驳回/部分采纳」理由,尤其 DESIGN_FINAL_ATTACK 阻断-1(A/B 过线才删旧包的时序裁决)与阻断-2(轮岗语义勘误的用户方法论裁定)——这两条是**活的约束**,01/02/03 都在引用)。→ **晋升**:将 DISPOSITION 报告晋升为持久文档,建议 `docs/develop/currency_war/redesign/decisions/`(与 ADR 体系衔接:阻断-1/-2 各一条决策记录,或并入现有 ADR 序列)。晋升后正文标记改为指向该持久路径。

**建议执行序**:先做 C 类(两条阻断裁决是 Phase 3 执行门,悬空风险最高)→ 再 B 类(挑有独立数据的 5-8 处)→ 最后 A 类批量删标记(机械操作,可脚本辅助+人工抽验)。全部完成后,`.debug/temp/currency_war/redesign/` 的对抗报告才可安全清理。

---

## 2. 规范性问题清单(路径 / 节 / 类型 / 建议)

| # | 位置 | 类型 | 问题 | 建议 |
|---|---|---|---|---|
| N1 | proofs 十件(§1 全表) | 变更史入正文 | 83 处「ADV_RN 修/勘误/需改N」标记 = 变更史,规范要求归处置记录/ADR,正文只留当前值成立的理由 | 按 §1.2 三分类处置 |
| N2 | PHASE2_PACKAGE_REPORT.md | 进度/变更叙述入 docs | 整文件是「本次实际改动清单+自检结果」= 实现进度+变更史,规范「实现进度不进任何文档,归进度追踪;变更史归 ADR」 | 迁至 `.debug/progress/` 当前迭代目录或 redesign/decisions/ 存档;其 §4 G2(毕业判据挂账)需先确认已落 01 §8(已落,G2 条款在 01 §8 ① 可查)再迁 |
| N3 | user_playstyle.md 头部 L4「条目编号 1-41 为稳定 ID」;L3「[1]-[42]」误写为权威序表述 | 同步性(见 §3.3-1) | [42] 已存在,「1-41」上界过期 | 改为「1-42」或去上界(「已分配编号为稳定 ID」) |
| N4 | 01 §0/§1、README §0 多处「user_playstyle [1]-[41]」 | 同步性 | 同 N3,design 侧引用面同步过期 | 随 N3 一批改为 [1]-[42] |
| N5 | 01 头部「数值纪律:阈值/权重值一律不写死…只写常量名」 vs 01 §2「刷:刷新(2 金/次)」、§4.4「单步 EV(…− 2 金)」、§4.1「[17] 息律(**>50**…)」 | 自相矛盾(轻) | 设计文档自设纪律后正文硬编码常量值 2 金/50 金(§0 速查表的数值有出处声明,可豁免;§2/§4 是决策规则面) | §2/§4 改写常量名(SHOP_REFRESH_COST/INTEREST_THRESHOLD),或数值纪律声明豁免「机制事实速查值」 |
| N6 | 01 §6 表末行「p47 联动登记(…**执行中**)」 vs 同行状态列「**已执行并 R9 核验闭环**」 | 状态位自相矛盾 | 行标题残留执行中口径 | 行标题去「执行中」 |
| N7 | 01/README/NAVIGATION 大量「R3-N5/R4-M3/R5-N8/R6-N7/R9/R2-F1-需改⑧」轮次标记 | 引用悬空(同 §1) | 指向 temp 的 ADVERSARIAL_R1-R9 报告 | 并入 §1.2 C 类晋升批 |
| N8 | 02 §3.1 合成律清单(add/max/min/互斥)缺 **multiply** 定义;但 01 §4.10 四元组声明 `[min/max/add/互斥]`、同节示例用「轮岗 multiply 概率表」「伟大征服 ×3」,cw3/knowledge/mutations.py 已实现 `COMBINE_MULTIPLY` | 契约缺口 | 语义单一源(02 §3)未覆盖已落码的合成律 | 02 §3.1 补 multiply 定义(代数乘/概率表域乘),01 §4.10 四元组括注同步 |
| N9 | 「收口」「挂账」「满养」「换轨」「联动批」「五方」等术语在 01/README 首现无定义 | 术语黑话(轻) | 多数为项目已约定俗成(用户裁定语境反复出现),但 01 是「Phase 3 实现者」的第一入口,新实现者无密码本 | 01 头部或 NAVIGATION 加 6-8 行术语小词典(一行一词:收口=对抗审查通过后关闭修改;满养=终局线锁定后的全额培养投入;换轨=判据式从过渡口径切换到规范口径) |
| N10 | README §3「Phase 3 未开始」/ PHASE2 报告 G4「OBS 盘点迁 docs 前不得开工 Phase 3」 vs cw3/ 包已存在(strategy/resolver/math 八模块+注册桥) | 同步性(见 §3.4-4) | 文档面与实现面状态错位 | README §3 Phase 3 行改「已开工(骨架先行:resolved 契约/数学薄封装/双被测体壳已落,逐机器逻辑未接)」,并核对开工门 G4(OBS_INVENTORY 是否已迁 docs——未迁则开工门被跳过,需在账本登记豁免理由或补迁) |

**保留声明(审后认为合规、不建议改的)**:
- NAVIGATION.md 自我定位「组织/导航层,不含语义;冲突以 01 为准」——干净,保持。
- economy.md §1 卖回还池条、§10.1 收入公式行、combat.md §4:均为「结论+证据+裁定日期」形态,日期是裁定锚点不是变更史,合规。
- user_playstyle [41]/[42] 条目本体:口述原话+精确化分层+证明件指针(p48/p42/p50),形态正确;速查表两处均已更新。
- proofs p42/p49/p50:标记已收敛为语义表述的正面样本,A 类收敛的目标形态可参照。

---

## 3. 同步性抽查结果

### 3.1 02_knowledge_registries.md R 条目 vs 注册表源码(直调 6+ 条,全部命中)

| 抽查条 | 文档声明 | 源码直调 | 结果 |
|---|---|---|---|
| R01 池副本 | `POOL_COPIES_PER_CARD` 1/2费=27、3/4/5费=9 | cw_shop_odds.py:33 `{1:27,2:27,3:9,4:9,5:9}` | ✅ |
| R02/R04 槽位 | `SHOP_SLOTS`=5「不考虑昔涟诗篇」 | cw_shop_odds.py:28 同注 | ✅ |
| R07 XP 族 | `XP_PER_BUY`=4;`XP_TO_NEXT_LEVEL` 9→84 | cw_state.py:42-43 `{3:4,…,9:84}`;economy §9「用户确认正确」行与文档一致 | ✅ |
| R09 收入 | `BASE_INCOME`=5;`REWARD_BASE_GOLD_BY_ROUND` {1:3,2:4};`STREAK_GOLD_TABLE` 0-1→1/2-4→2/5→3/6+→4;`LOSS_GOLD_BY_NODE` battle2/encounter4/boss4 | cw_economy.py:43/63/70/76 全部一致(表 `(1,1,2,2,2,3,4)` 按 idx=streak 查即文档四档) | ✅ |
| R10/R11 息律 | `INTEREST_THRESHOLD`=50,cap=5;开源节流300101→9/利息上调300801→10/买断制300901息关/狸财经狸304001+2 | cw_factions.py:134;cw_invest_data.py:243/249/250/283 原文逐条吻合(含「+2」「<20 取 10」「P3 首领取全部」) | ✅ |
| R05 刷价 | `SHOP_REFRESH_COST`=2/`REFRESH_COST_BASE`=2;长线利好 30 刷→1 金+20 金 | cw_economy.py:269;cw_state.py:53;registry:1666-1668(threshold=30/price=1) | ✅ |
| R13 卖退金 | 1★全额/2★×3/3★×9,仅 star≥2∧cost≥2 减 1 | cw_state.py:870-883 `sell_refund` 条件一致(含 1 费豁免) | ✅ |
| R02 持有副本 | 板面+备战 3^(s-1) 折算 | cw_economy.py:665 `_owned_core_copies` bench∪deployed 同口径 | ✅ |
| R03 突变 id | 轮岗114「每备战阶段重新随机」/市场干预102201/采购专员201201每7次、303101每5次/概率事件300401 45% | cw_invest_data.py:383/61/124/273/245 逐条吻合 | ✅ |

### 3.2 01 §4 消费点 vs cw3/ 新包落位(抽 4 处,全部落位)

| 抽查点 | 文档声明 | cw3 落位 | 结果 |
|---|---|---|---|
| 02 §1/§4 resolve_* 契约(10 个签名) | 决策层只准经 resolve_* 取数 | cw3/knowledge/resolver.py 实现 §4.1 全部 10 个签名 + 超集 5 个(resolve_free_refresh/xp_flows/shop_behavior/difficulty/channel) | ✅(超集见 §3.4-5) |
| 01 §4.10 四元组/合成律/保守降级 | (操作数,合成律,状态依赖,时效)+未登记告警降级 | cw3/knowledge/mutations.py 四元组常量 + resolver 头注「未登记→保守降级+告警,不静默」逐条对应 | ✅(multiply 缺口见 N8) |
| 01 §4.4 金日程/R09 责任边界 | 收入组分单一源=cw_economy 常量,禁复制数值 | cw3/economy/income.py 仅 import 常量,零复制 | ✅ |
| 01 §7/03 批 1a 双被测体并存 | 新层薄壳 selectable,旧包不删 | cw3/strategy.py(CwStrategy 薄壳,批 1b 挂账声明)+ strategies/cw3_strategy.py 注册桥 | ✅ |
| (附)p47 L 消费 resolved cap / Z1 位面长度 | 「消费 resolved I_cap 不自带 5」;R_全局 按实际位面长度 | cw3/math/interest_account.py(cap 参数化)+ node_schedule.py(P1=9/P2=7/P3=9、TOTAL=25) | ✅ |

### 3.3 发现的漂移(需修)

1. **[42] 编号上界过期**(N3/N4):user_playstyle 头部「条目编号 1-41 为稳定 ID」与 01/README 的「[1]-[41]」引用面,[42] 已入库未跟上。
2. **「Z1」标签二义**:README §3 冻结条件③写「Z1 代码缺陷 L 落码前必修」(语境=p46 Z1:`total_remaining_nodes` 写死 9);NAVIGATION §2 条件③写「Z1 代码缺陷(**P19② 序依赖缺口**)」;cw3/math/node_schedule.py 自称「Z1 修复」实现的是 p46 Z1。**两个不同缺陷共用一个标签**,冻结条件③到底指哪个,三处文档不一致(p46 Z1 原文=L 换轨前必修 `cross_plane_remaining_nodes`;P19② 是羁绊计数两遍法)。建议:条件③拆成两条各指其名(「p46 Z1 R_全局 缺陷」/「P19② 两遍法修正」),cw3 已修前者、后者仍未修(全 cw3 无 P19 相关代码,与「Phase 3 前置任务」挂账一致)。
3. **02 §4.1 契约签名 vs resolver 实现超集**(轻):代码多出 5 个 resolve_* 入口,02 的「形态为准」条款可覆盖,但建议 02 §4.1 补一行「实现可含派生超集入口,以 resolver 实况为准」防未来对拍误报。
4. **README Phase 3 状态失真**(N10):cw3 骨架已落,文档仍「未开始」;同时开工门 G4(OBS 盘点迁 docs)与 cw3 已开工的时序矛盾需显式豁免或补迁。
5. **01 §6 行标题「执行中」残留**(N6)。

---

## 4. 处置方案汇总

**修(按优先级)**:
1. §1.2 C 类:DESIGN_FINAL_ATTACK 阻断-1/-2 处置报告晋升为持久决策记录(redesign/decisions/),01/02/03 引用改指持久路径——Phase 3 执行门不能挂在 temp 上。
2. §3.3-2:「Z1」标签二义拆名(README/NAVIGATION/01 三处,10 分钟修,防 Phase 3 前置任务漏项)。
3. §3.3-1/4:[42] 编号上界 + README Phase 3 状态行。
4. N8:02 §3.1 补 multiply 合成律定义。
5. §1.2 B 类→A 类:证据段晋升后,批量清理 proofs 83 处(+p41)变更史标记。

**保留声明(不改)**:economy/combat/user_playstyle 本周期三个新条目面;NAVIGATION;p42/p49/p50 的已收敛形态;PHASE2_PACKAGE_REPORT 在 G2 挂账确认转移后迁出 docs/develop(进度面归进度追踪)。
