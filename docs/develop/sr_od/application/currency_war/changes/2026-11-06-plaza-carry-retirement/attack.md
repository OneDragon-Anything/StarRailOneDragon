# plaza-carry-retirement 设计对抗报告（第 1 轮·无前提攻击）

> 攻击面：核一（无前提——主张逐条对代码核验 + 实现者试读）为主，核二/核三并重。
> 结论：**9 个有效攻击点（1 高 / 4 中 / 4 轻），全部处置**；3 个攻击落空（附驳回理由）。

## 有效攻击点与处置

### A6【高】断言②改写为恒真式，防线空洞化 + 新漂移面无防线
- 攻击：design §2.1 第 7 条将断言②改为「过渡条目 named_units == core 全员」——named_units 的过渡半边**定义就是** `tuple(comp.core_chars)`，该断言恒真，防线归零。旧断言②防的漂移（手改表让过渡条目意外获得单锚 → 点名件语义翻转）在新判据下的对应形态是**终局线名撞 combo 命名**（含 `+`）→ 被判过渡 → named 从单锚翻转为全员——此面无任何防线。
- 处置：§2.1 第 7 条断言②重写为两条实防线：「TRANSITION_COMBO_PARTS 键集 == TRANSITION_LIBRARY 条目名集（与 _validate_transition_combos ① 双钉）」∧「COMP_LIBRARY 线名集 ∩ TRANSITION_COMBO_PARTS 键集 = ∅（防撞名翻转）」。

### A2【中】named_units 过渡判据身份驱动，测试桩语义未申报
- 攻击：旧表达式数据驱动（桩 plaza_carry 空 → 自然走全员半边，桩可测两态）；新判据 `comp.name in TRANSITION_COMBO_PARTS` 身份驱动——库外构造（测试桩/手写条目）恒按终局半边解释（named=core[0]），**过渡语义对桩不再可测**，只能用真 TRANSITION_LIBRARY 条目。设计 §2.5 未申报此测试性变化。
- 处置：§2.5 测试桩兼容性段补申报（过渡语义测试须取真条目；桩恒终局半边为**设计语义**非缺陷）。

### A5【中】关键取舍段缺失（详设深度不满足「实现者无需再设计」）
- 攻击：四个已裁取舍未入档，实现者/未来考古无从得知落选理由：①member_priority 全序字段落选；②LINE_STAT_CLUSTER 为何整表（21 条）而非分歧表；③火花裁定两方向取舍；④过渡判据为何用键集而非 `Comp.is_transition` 字段。
- 处置：design 增 §2.6 关键取舍，四项就地入档。

### A8【中】火花线 need_star 定档规则不完整
- 攻击：§2.2 只说「按 plaza 火花簇 carry_star3_rate 定档」，未给定档规则（饥饿两档表口径），且花火既有 3★ 条目（攻略明文）去留未裁。
- 处置：§2.2 火花行补全：火花按 carry 位无攻略明文 → 饥饿两档表（star3 率实测值定档，数据批就地注释）；花火 3★ 条目**保留**（攻略明文星级不随主C 裁定失效，花火仍 core 次位）。

### A10【中】grep 零残留判据口径不精确
- 攻击：`plaza_carry` 字符串在 `data/cw_plaza_comps.py`（`PlazaCarryCluster.carry` 为聚类层自有字段）与 gen 工具中**合法存在**；「src 生产代码零残留」会把合法共存面炸成误报。
- 处置：landing 3.2 判据限定域：「kernel/strategies/operations/sim 的 Comp 属性面（`\.plaza_carry` / `plaza_carry=` 构造参数）」；data 层聚类字段与 gen 工具不在此列。

### A1【轻】docstring 语义段清理面不完整
- 攻击：符号 grep 抓不到不含符号名的注释语义段（form_progress「锚源是统计字段(plaza_carry 聚类 + fallback)，版本重跑换锚 → fp/锁定/部署语义随之变」整段、carry_anchor/carry_set/_validate_anchor_invariants docstring）。
- 处置：landing 3.2 范围补「锚源语义注释段清理」项。

### A7【轻】对账报告对无簇线行为未定义
- 攻击：3 条空值线聚类侧查无 carry 簇，「聚类 carry vs core[0]」比对对其 undefined——实现者需自行拍板（违反无需再设计）。
- 处置：§2.1 第 8 条补：无簇线单列「无簇」标注行，不进差异清单。

### A9【轻】意向核心 miss 计数状态迁移未申报
- 攻击：intention_core 键变化（花火→火花）后旧计数残留行为未申报。
- 处置：§2.2 补申报：miss 计数为局内状态、换键随局重置无跨局迁移面；落地批核对 intention 状态生命周期属实（若实测为跨局状态则补迁移申报）。

### A11【轻】正本更新清单完整性未经 grep 核验
- 攻击：清单 7 项之外，flow/ 各篇、15 号篇、telemetry 文档可能仍有 carry 口径引用面。
- 处置：landing 末阶段判据补：先 grep `plaza_carry|CARRY_ANCHOR|carry_anchor` 全 docs/skills 面，命中篇不在清单则补列。

## 落空攻击（附驳回理由）

1. 「intention_core 在 3.1→3.2 中间态行为漂移」——落空：3.1 后 plaza_carry∈core（巡海/双王/火花换位或入册后均 ∈core）→ 旧逻辑取 plaza_carry == core[0]，与简化版恒等。
2. 「LINE_STAT_CLUSTER 快照时点在 3.2 后语义模糊」——落空：3.1 后 carry_anchor 值 == core[0]（3.1 判据钉死），3.2 派生化后同值，任意时点快照同值。
3. 「carry_anchor 七处消费点清单遗漏」——落空：全库 grep 复核，line_select 间接消费已由变化 3（rating_anchor 删除）覆盖，余七处清单完整。

## 修订与状态

处置 A1–A11 已全部修订进 design.md（§2.1/§2.2/§2.5/新增 §2.6）与 landing.md（3.2 判据与范围、末阶段判据）；修订后全量同步复查通过（引用锚存在性 / 判据同步 / 文件面真实路径）。攻击收敛，状态：**定稿**。
