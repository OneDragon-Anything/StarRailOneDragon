# 门谓词定稿与 335 卡审计规格（详设）

> 承接总纲 §2.1/§2.2 深化；全集机器单一源 = `2026-09-12-invest-env` §2.1。
> 本文对总纲遗留的全部语义选择给出定稿（角色全集口径 / 失格跳过域 / S1 前提守卫 / 审计规格 / 锁表 / 机器共享契约），
> 实现者遇到未覆盖的选择 → 停手回任务书指认本文件提请修订，禁自行拍板（iteration-design 写作硬规则 2）。
> 依据标注约定：`cw_investments.py:n` / `cw_events.py:n` / `cw_comps.py:n` = 直调行号（2026-09-12 注册表态）；
> 「直调」= 本详设写作时以脚本实跑注册表取得的值，非转述。

## 问题与约束

### 边界

本篇辖：decide_event 策略分支全集门的全部语义、S1 前提守卫、335 卡审计方法论、锁设计、与环境迭代的共享契约。
不辖：环境分支一切（invest-env）、T-162 判据本体（零改动，仅消费旗标语义细化，见 §3.4）、意向层持卡价值重估（总纲 §1.3-1 明确不解决）。

### 从总纲承接的接口契约

- 全集阵营维 = `candidate_faction_universe(evicted)`（invest-env §2.1.1 定义的签名与语义，落 `kernel/cw_comps.py`），本迭代只消费不复刻；
- `evicted` 语义单一源 = 意向层「等同信号未发生」契约（invest-env §2.1.1），decide_event 既有参数，零接口新增（`cw_events.py:195`）；
- 归因串仅观测、不进检查器白名单（C1→D4 口径，`cw_events.py:243-245` 同款声明）；
- 失格语义 = 形态 B（分数落 0 垫底），非集合级排除——三选一强制选一帧仍可选（用户裁定 2026-09-12，invest-env §0）。

### 宪法对账（硬约束）

- 禁拍值：本门是集合存在性谓词，零数值进决策门；品质回落 rank×2+econ 等既有编码常数不动（`cw_events.py:253-257`）；
- 位面零字面量：门谓词无位面维（宪法第 2 条，`strategy-docs/00_framework.md` §1）；
- 定序与基数分账：门是结构判据不是分值族，不进 max() 覆盖定序的任何一档（定序纪律）；它作用在分值族**之前**（删支，不打分）；
- 数字三形态：本文全部数字 = 【注】注册表直调值（`strategy-docs/01_math_framework.md` §6），无【拟】项。

## 方案

### 1. 数据基础：注册表直调盘点（§2 各定稿的共享证据，全部 evicted=∅）

| 项 | 值 | 出处 |
|---|---|---|
| 策略卡总数 | 335（银 77 / 金 135 / 棱彩 123） | 直调 `INVESTMENT_STRATEGIES` |
| 绑定表 | 87 条 = 手建模 66 + 星徽套组派生 21；结构 = (factions, core_chars) 双维 frozenset | `cw_investments.py:754-856`；派生 `:829-850` |
| 绑定形态分布 | 双维非空 59 / 纯阵营 7 / 纯角色 21 / 双空 0 | 直调 `STRATEGY_BINDINGS` |
| 非锚定卡 | 248（= 335 − 87，不触门） | 直调 |
| COMP_LIBRARY | 20 套；阵营全集 20 / core_chars 并集 49 / shared_chars 并集 36（core 外 6：刃、布洛妮娅、椒丘、流萤、遐蝶、银狼）/ transition_chars 并集 20（core∧shared 外 4：丹恒·腾荒、星期日、艾丝妲、赛飞儿） | 直调 `cw_comps.py` COMP_LIBRARY |
| 被绑阵营 | 去重 24；全集外 4 = 护盾、治疗、狼狩、盛会之星（四者均仅作为 flex_factions 出现，无任何 comp 核心） | 直调 |
| 被绑角色 | 去重 42；∈core 27 / 仅 shared 3（刃、椒丘、银狼）/ 仅 transition 4 / 三清单全外 8（佩拉、停云、加拉赫、姬子、砂金、罗刹、貊泽、青雀） | 直调 |
| 经济引擎 | 38 张（`is_economy_engine`）；引擎∧锚定 = {按劳分配, 砂里淘金} | 直调 `cw_events.py:105-123` |
| 血本位 | 2 张（奋斗协议、不等价交换），绑定双空，pv 45/20 | `cw_investments.py:154-166` 直调 |
| 定义型 | 7 张，全部单 comp 亲和，值域 {1.0, 0.8, 0.6}，全部 ∈ 绑定表 ∧ 指向 comp ∈ COMP_LIBRARY | `cw_comps.py:408-417` 直调 |
| PICK_VALUE | 315 条，值域 12-75；未评估 20 张 | `cw_investments.py:908-1224` 直调 |
| **门咬合面（净失格集）** | **18 张**（预失格 19 − 引擎豁免 1「砂里淘金」，逐卡名单见 §7 锁表 D-c） | 直调 |
| evicted 动态翻面预演 | evict 希儿量子 → 新增失格 3 = 量子力学 / 量子同频星徽 / 量子同频星徽套组（量子同频阵营仅希儿量子核心，直调） | 直调 |
| S3 结构不可达实证 | 净失格 18 卡 × 20 comp 全组合对齐 N = 0 | 直调（N 定义 = `cw_events.py:316-317`） |

### 2. 角色全集口径定稿（总纲 §2.1 待定点）

**定稿：角色全集 = ⋃ `comp.core_chars`，遍历域 = {comp ∈ COMP_LIBRARY | comp.name ∉ evicted}——不含 shared_chars，不含 transition_chars。**

论证三条：

1. **S3 计维对齐（结构主证）**：S3 对齐的 N = len((绑定factions ∩ D\*factions) ∪ (绑定chars ∩ D\*chars))（`cw_events.py:316-317`），而 D\* 的角色维恒 = comp 的 `core_chars`（`cw_events.py:152` 锁线支、`:164` 信号支）。绑定角色 ∉ 任何候选 comp 的 core_chars ⟹ 对一切可达 D\* 该维贡献恒 0 ⟹ 该卡结构上永不 align。门的存在意义 = 把「结构上无用」的卡移出 S4 竞争；把永不 align 的卡留在 S4 = 病灶本体（总纲 §1.1）。角色全集若含 shared/transition，等于给永不 align 的卡发通行证，与门语义自相矛盾。
2. **与阵营口径同构**：阵营全集 = `comp.factions`（核心羁绊，form_tiers 键 ⊆ 它，`cw_comps.py:93-94`）且用户已裁定 flex_factions 不入集（invest-env §2.1.1：「弹性羁绊是阵容能临时吃的，不是可能玩的方向」）。shared_chars（「与其他 comp 共享…转型可复用」，`cw_comps.py:109`）与 transition_chars（「早期打工牌」，`cw_comps.py:110`）正是角色侧的「临时可吃、非玩的方向」，同判排除。
3. **错杀差集有界且逐卡可议**：core vs core∪shared 的失格差集恰 4 张（狼狩星徽、狼狩星徽套组、锻冶专家:刃、骇客专家:银狼，直调 §1）；transition 再加入零增量（仅 transition 被绑角色丹恒·腾荒/星期日/艾丝妲/赛飞儿所在卡均另绑集内阵营或核心角色，直调）。差集 4 张中，狼狩星徽系的效果主体是狼狩阵营羁绊装备（阵营维已判全集外），椒丘绑定是该阵营 key 角色的从属证据——让 shared 椒丘复活狼狩星徽 = 复活「给不玩的阵营送羁绊装备」（总纲 §1.1 症状原文）。刃/银狼的专家卡若确有库内消费方向，错杀修正路径 = 修 COMP_LIBRARY（invest-env §1.3-7 先例：「研究遗漏导致错杀的修正路径 = 修 COMP_LIBRARY，不是放松门」），user-priority 覆写保留为人工兜底（§3.1 steering 行）。

**落码形态：`candidate_core_char_universe` 独立函数，不与阵营全集合并。**

```python
# kernel/cw_comps.py,candidate_faction_universe 同区(COMP_LIBRARY 派生 helper 区)
def candidate_core_char_universe(evicted: frozenset[str] | set[str] = frozenset()) -> frozenset[str]:
    """候选角色全集 = 非 evicted 阵容的 core_chars 并集(策略全集门角色维,详设 §2)。
    不含 shared_chars/transition_chars:两清单是「临时可吃」成员,非「可能玩的方向」
    (与阵营全集排除 flex_factions 同判);且 S3 对齐角色维只数 core_chars,
    绑定角色出集 = 结构上永不 align。evicted 语义 = 意向层「等同信号未发生」
    (与 candidate_faction_universe 同源同义)。"""
```

不合并成单函数的理由：env 分支只消费阵营维、策略分支消费双维，合并函数会迫使 env 调用点解包无用半边；两函数镜像同构、遍历域共用一个私有 helper（见 §8），双函数即零二次建模。

### 3. 失格跳过域语义定稿（总纲 §2.1「S4 裸分支跳过」的精确化）

**定稿：门失格跳过整个 S4 常规评估域——评估分支（eval）、LCS 形变裸分（eval-lcs）、品质回落（prior-{rarity}）三支全跳；分数落 0；候选归因串 `strategy-off-universe`。**

#### 3.1 逐分支可达性推演（现行代码 `cw_events.py:281-346`，失格卡 = 锚定 ∧ 非豁免 ∧ 双维交集空）

| 分支（行号） | 现行可达性 | 门后可达性 | 判定 |
|---|---|---|---|
| S1 定义 120（:311-313） | 仅 affinity 表内卡 | **不可达**：前提守卫拦截（§4）；affinity 空 = 天然不触发 | 守卫 |
| S3 对齐 45N+20（:314-324） | N≥1 才可达 | **结构不可达**：D\* ⊆ 全集（D\*① locked_comp 经 `get_comp` 只返 COMP_LIBRARY 在册线 `:150-152`；D\*② 只对 COMP_LIBRARY 在册线发射且继承 evicted 过滤 `:153-157,162-163`）⟹ 失格卡绑定 ∩ D\* = ∅ ⟹ N=0；18 卡 × 20 comp 全组合 N=0 实测（§1） | 无需门（结构保证 + 锁 §7 D-d 钉住） |
| S2 经济域带（:328-334） | engine 卡 | **不可达**：engine ⇒ 豁免 ⟹ 失格集内 engine 恒假；「引擎∧锚定∧锚外」唯一点位 = 砂里淘金，由豁免保住（§1） | 豁免优先于门 |
| S4 eval（:337-338，pv 非 None） | pv∈12-75 | **门跳过**——病灶主面（净失格 18 卡中 14 张有 pv，直调） | 门辖 |
| S4 prior-{rarity}（:339-341） | 未评估卡，rank×2+econ ∈ {0..5} | **门跳过**——4 张未评估失格卡（战术专家:佩拉 / 步狸村之谜 / 锻冶专家:刃 / 领航专家:姬子）现行落 2-4 分 | 门辖 |
| eval-lcs（:344-346） | 形变名 ∧ `pick_value_of` LCS 命中 | **门跳过**：`pick_value_of` 与门共用 `resolve_strategy_canonical` 解析源（`cw_investments.py:1237-1265`），门以 canonical 身份同判（§5） | 门辖 |
| env 支（:352-366） | — | 结构不可达（策略∩环境注册表双空，`cw_events.py:429-430` 直调在案声明） | — |
| steering（:367-378） | priority +30 / forbid −10000 | **保留**：用户语义最高，失格卡被点名仍可胜出（与环境门 U5 锁同形，invest-env §2.7） | 门不辖 |
| DoT 惩罚（:379-380） | −100 | 保留（对已落 0 的失格卡只更负，无语义） | 门不辖 |
| 血本位三态 L1-L3（:391-416） | 非血卡恒落 L1 | 失格卡非血（血卡绑定双空直调 §1）⟹ 照常落 L1，0 分参与 argmax；全失格帧 L1 argmax 取首序 = 强制选一仍可选 | 门不辖 |

#### 3.2 为何跳全域而非只跳 eval 支

- 若只跳 eval：形变名经 LCS 仍拿 12-75 裸分（eval-lcs 支）、未评估卡仍拿 0-5 回落分——失格卡在失格集内部与对合格卡边缘继续无信息竞争，垫底语义破缺；
- 三支同族：`cw_events.py:223-228` docstring 把 eval / eval-lcs / 品质回落并列为「S4 常规评估层」，属同一分值族；品质回落的设计语义是「未评估时别全盲」（`:226-228`），而全集门是比「知识缺省」更强的结构事实，结构规则压过缺省先验；
- 与环境侧「落 0 垫底」对账：env 无品质回落域（invest-env §2.1.2 注：「env 本就无回落——落 0 即天然垫底」），env 失格天然单支落 0。策略侧 S4 三支全域跳过后，失格策略卡的残余可达面（steering / DoT / 血分区 / 强制选一）与失格 env 卡**逐位同形**——这就是两门「同构」的可检验含义（锁 §7 G11 钉住）。

#### 3.3 分数与归因的落点形态

失格且无 steering 命中的候选：score = 0.0（初值原样）、reason = `strategy-off-universe`（在跳过点覆写默认 'eval'，:283；全无用帧该卡胜出时对外可见——`env-off-universe` 同款语义，invest-env §2.1.2）。steering 命中则按现行覆写序变 `user-priority`/`user-forbid`。

#### 3.4 T-162 刷新分类的旗标细化（判据本体零改动）

门不改 T-162 逻辑（`cw_events.py:417-468`），但 **S1 旗标语义随前提守卫细化**：`_cand_s1` 从「名字在 affinity 表」（:386 现行 `bool(_aug)`）细化为「S1 前提成立」（= 前提 ∧ 在表）。理由：前提破缺的定义卡已失格，顶级槽保护（防刷掉顶级卡）对它失去对象；若旗标仍 True，失格定义卡反被保护不刷——与 T-162「非顶级可刷」的弱占优论证直接冲突。现行注册表 7 张定义卡前提全真（§1）⟹ 该细化**现行零漂移**，仅约束未来演化。同帧消费序安全（G8「先判帧级闸后取分类」）不受影响：旗标仍在同一循环内存档。

### 4. S1 定义型豁免的前提守卫定稿（总纲 §2.1 豁免面 1 的细化）

- **触发面（不变）**：`augment_affinity(opt)` 非空（`cw_events.py:307,311-313`；归一单一源 `cw_comps.py:420-431`）。
- **前提谓词**：`premise_ok(opt) ⇔ ∃ c ∈ keys(augment_affinity(opt)): c ∈ COMP_LIBRARY ∧ c ∉ evicted`。
  - **∃ 形态（任一支在全集即豁免）**：与门谓词的并集形同构、错杀最小化；直调现状 7/7 单 comp 亲和，∃/∀ 无行为差，∃ 形态只约束未来多 comp 条目；
  - **亲和值（1.0/0.8/0.6）不进门判定**：现行 S1 触发 = 表非空，值不参与（:311-313 只查 `if _aug`）；加值阈值 = 无推导拍值（宪法第 1 条/公理 1），且会分叉 S1 触发语义。值继续服务既有消费者（held_strategy_fit 等，`cw_comps.py:1450,1733,2388`），本迭代不碰；
  - 前提同时是绑定表的覆盖守卫（总纲 §2.1 豁免面 1 原义）：affinity 指向库外 comp ⟹ 拿到即改玩法无处兑现 ⟹ 该卡回归常规候选资格判定（失格 ⟺ 绑定双维也全集外；绑定若仍在集内则落 S4 裸分竞争，两守卫各辖各维，合取不重复）。
- **守卫的辖域（恰好两处消费）**：①S1 分支 `if _aug and premise_ok` ；②T-162 `_cand_s1` 旗标（§3.4）。detect_signals 的 ① 层亲和排除、held_strategy_fit 等意向层消费**不接**本前提（总纲 §1.3-1 意向层不动）。
- **时序 = 选卡时点快照**：前提在每次 decide_event 帧上按该帧 `evicted` 现算（与 D\*、全集同一帧快照，`cw_events.py:258-261` 单帧单读同款纪律）。已持有卡不回溯——decide_event 只评桌面 3 候选，结构性不存在「重评持卡」；拿到定义卡之后该 comp 再被 evicted，卡已入手，其价值重估归意向层（held_strategy_fit / pivot），非本门辖域。

### 5. 门谓词总装（落码形态，实现者无需再设计）

**判据（单帧单读快照后逐候选求值）**：

```
失格(s) ⇔ anchored(s) ∧ ¬premise_ok(s) ∧ ¬engine(s) ∧ (fs(s) ∩ U_f = ∅) ∧ (cs(s) ∩ U_c = ∅)
  anchored(s) ⇔ strategy_bindings(s) ≠ (∅, ∅)                # cw_investments.py:862-870,绑定单一源
  premise_ok(s) ⇔ §4 谓词                                     # 仅 affinity 表内卡非平凡
  engine(s) ⇔ is_economy_engine(s.economy)                    # cw_events.py:105-123
  U_f = candidate_faction_universe(evicted)                   # invest-env §2.1.1 落码,帧外一次
  U_c = candidate_core_char_universe(evicted)                 # 本迭代 §2,帧外一次
  fs(s), cs(s) = strategy_bindings(以 canonical 身份解析的 s)
```

- **身份解析**：精确命中（`_st is not None`）直接用 `_st`；精确 miss 的形变名经 `resolve_strategy_canonical(opt)`（`cw_investments.py:1237-1254`，归一 + LCS 阈值 0.6 + |Δlen|≤3）解析后以 canonical 卡进门——与 `pick_value_of` 的 eval-lcs 消费同源（:1257-1265），形变名不失守。解析失败（完全未知名）⟹ 无身份 ⟹ 不锚定 ⟹ 不触门（保守向：漏放而非错杀，`strategy_bindings` 缺键语义同款，:868-870）。
- **落码位**：`cw_events.py` 评分循环内、血本位分类（:298-306）邻位增加失格分类（复用同一 `_canon_st` 形态）；跳过点两处——S4 尾块（:335-343）与 eval-lcs 支（:344-346）以 `if not _失格:` 包裹；S1 位（:311-313）改 `if _aug and premise_ok`。
- **豁免优先序**：血本位分区（结构性，is_blood_economy 字段族与门零交集）＞ S1 前提豁免（120）＞ S2 引擎豁免（域带）＞ 门。失格集定义已内含「非豁免」，故引擎/定义卡恒不进门。
- **不动的面**：`ENV_PICK_VALUE`/`PICK_VALUE`/`STRATEGY_BINDINGS`/`AUGMENT_COMP_AFFINITY` 四表零改动（门是消费侧谓词）；steering 常数、品质回落编码、D\* 解析、env 分支、T-162 判据本体、`refresh_slots` 语义全部不动。
- **归因串**：`strategy-off-universe`；与 `env-off-universe` 同为仅观测归因，不进任何检查器白名单（C1→D4）。
- **无开关**：结构判据直接落码，回滚 git revert（总纲 §2.4；strategy-work §3）。

### 6. 335 卡盘点审计规格（landing 3.1 的方法论）

#### 6.1 逐卡分类决策树（判定顺序 = 豁免优先序镜像，每步出处 = 注册表符号）

对 `INVESTMENT_STRATEGIES` 每张卡依序判定，产出**唯一主分类 + 交叉旗标**：

1. **定义型？** `augment_affinity(卡名)` 非空（`cw_comps.py:408-417`）→ 主分类 = 定义型；门行为 = 豁免（前提 = §4 谓词，逐卡记录指向 comp 及其在库/evicted 态）。
2. **血本位？** `is_blood_economy(卡.economy)`（`cw_investments.py:154-166`）→ 分区自辖（不触门）。
3. **经济引擎？** `is_economy_engine(卡.economy)`（`cw_events.py:105-123`）→ 豁免。
4. **绑定锚定？** `strategy_bindings(卡)` 非空（`cw_investments.py:853-870`）→ 触门：失格 ⟺ fs∩U_f=∅ ∧ cs∩U_c=∅（§5，evicted=∅ 与若干 evicted 预演帧都算）；集内 → 保留。
5. **非锚定** → 不触门。

顺序依据：S1 支配一切常规评估（:210-213）、血分区在全部分值族之外（:235-241）、S2 带压过 S4（:66-72）、门在 S4 门口（§5）——分类树顺序即代码优先序镜像，交叉旗标（如「引擎∧锚定」）照实并列记录，不复判。

#### 6.2 覆盖缺口挖掘协议（找「应锚定未锚定」）

- **Pass 1·名字形态扫描**：卡名含「星徽」「星徽套组」「专家:」「顾问」→ 必须在绑定表有行，或给出显式「不锚定」结论。套组已有派生守卫（缺单件建模 import 即炸，`cw_investments.py:846-848`）；单件无守卫，靠本扫描。已预跑实抓 1 例：**星徽大使叽米**（棱彩，pv=50，效果「超稀有的叽米登场！爆出超多星徽！！」直调）——效果 = 随机星徽池（多目标），非特定 comp 专属 ⟹ 判「非锚定」，记挂账说明（多目标随机授予 ≠ 单 comp 预示，判据见下）。
- **Pass 2·效果原文专名扫描**：模式字典 = ①绑定表 factions∪chars 全集（24+42 名）∪ ②COMP_LIBRARY factions/core/shared/transition 全清单 ∪ ③游戏阵营全集 = 官方 config API（`tools/cw/gen_plaza_invest.py` 同源端点）`data.trait_info_list` 键的 `trait_name` 全集——2026-09-12 实测 33 名（含绑定表 24 名与全集外 4 名：护盾/治疗/狼狩/盛会之星），字典③的完备性以该键全集为准，审计批开工前重拉一次对账。命中卡逐条人工复核。
- **人工复核判定规则（锚定的充要判据，原文 `cw_investments.py:749-751`）**：效果引用 comp 专属机制/召唤物/星徽/赠 key 角色，且该引用是效果价值的**承载主体**（无它则效果空转或错向）→ 锚定；泛用数值（全队强度/给金/装备/全队护盾/治疗强度）中恰好出现同名同形词 → 不锚定。
- **假阳性对照件（已直调，复核时对样）**：现金为王（「提供护盾」= 泛用护盾数值 ≠ 护盾阵营）、量产型装甲祝福（「护盾强度」同）、生命之花祝福（「治疗强度」同）——与绑定表前言记载的两类噪声（战术义眼/生命之花祝福，:750-751）同族。凡与对照件同形的命中一律不锚定。
- **缺口的处置**：确认「应锚定未锚定」→ 逐条列出（卡名/效果引文/应绑实体/证据等级），由 landing 3.2 决定补 `STRATEGY_BINDINGS` 条目（landing 3.2 文件面已预留 `cw_investments.py`）；补条目 = 门咬合面扩大，须同步补该卡锁 fixture。

#### 6.3 审计表 schema（`details/strategy-335-audit.md`，335 行 + 二义挂账段）

| 列 | 语义与格式 |
|---|---|
| 卡名 | 注册表规范名（canon） |
| rarity | 银/金/棱彩 |
| economy | 有/无（`st.economy is not None`） |
| pv | PICK_VALUE 整值或 `—`（未评估 20 张） |
| 绑定f | 顿号连接的阵营名，空 = `∅`（与绑定c 分列：机检与 fixture 逐维核对按维取值） |
| 绑定c | 顿号连接的角色名，空 = `∅` |
| 旗标 | 定义 / 血 / 引擎（可并列，逐符号出处） |
| 门行为 | 豁免(前提✓) / 豁免(引擎) / 分区自辖 / **失格** / 集内保留 / 不触门（六值闭集） |
| 现行S4可达支 | eval(pv 值) / prior-{rarity}(值) / —（失格卡必填，对照 §3.1 推演表） |
| 出处 | 注册表符号（行级证据；绑定行必填，非锚定行填「缺键」） |
| 备注 | 二义挂账 / 挖矿命中 / 预演翻面说明 |

**二义卡挂账格式**（表尾独立段）：`「<卡名>」二义：<一句话疑问> → 缺省 = 不锚定（保守向：门漏放非错杀，§5 身份解析同款缺省）｜挂账：<去处>`。缺省方向与门的缺键语义一致（strategy_bindings 空 = 不触门）。

#### 6.4 验收口径

1. 335 行全分类，**零「待定」残留**（二义必须落到挂账格式，含缺省与去处）；
2. 每行带注册表出处；「门行为=失格」行集合与 §7 锁表 D-c 的 18 卡名单**逐卡相等**（不等 = 表错或注册表漂移，先红后改）；
3. 缺口清单逐条带效果原文引文与复核结论（对照件规则引用）；
4. 「绑定全集外实卡」清单 = D-c 名单 + evicted 预演翻面卡（量子系 3 张），供锁 fixture 引用。

### 7. 锁表（`test_cw_strategy_universe.py` 新建；fixture 直调核验仿 `test_cw_invest_refresh.py` 先例——模块头断言 fixture 卡 pv 与全集成员，注册表漂移先红）

**漂移断言（模块头，先行锁）**：

| 编号 | 断言 | 设计依据 |
|---|---|---|
| D-a | `len(INVESTMENT_STRATEGIES)=335`；`len(STRATEGY_BINDINGS)=87`；`len(PICK_VALUE)=315` 值域 12-75 | §1 直调 |
| D-b | `candidate_faction_universe()` = 20 阵容名集；`candidate_core_char_universe()` = 49 角色名集 | §1/§2 直调 |
| D-c | 净失格集（§5 判据，evicted=∅）= 18 张枚举名单：停云顾问、加拉赫顾问、战术专家:佩拉、护盾星徽、护盾星徽套组、摸个鱼吧I、摸个鱼吧II、摸个鱼吧III、步狸村之谜、潜行专家:貊泽、狼狩星徽、狼狩星徽套组、琼玉专家:青雀、调饮专家:加拉赫、贸易专家:停云、锻冶专家:刃、领航专家:姬子、骇客专家:银狼 | §1 直调 |
| D-d | ∀comp ∈ COMP_LIBRARY ∧ ∀D-c 卡：对齐 N=0（S3 结构不可达漂移哨兵） | §3.1 |
| D-e | `AUGMENT_COMP_AFFINITY` 7 键 ⊆ `STRATEGY_BINDINGS` ∧ 指向 comp ∈ COMP_LIBRARY（S1 前提现行全真） | §1 直调 |

**行为锁**（帧 = 3 策略卡；pv 值为直调【注】值，测试模块头再断言一次防漂移）：

| 编号 | 帧（pv 直调值） | 断言 | 标注 | 设计依据 |
|---|---|---|---|---|
| G1 | {摸个鱼吧III 48, 价值投资·金 45, 复印件 45} | 选价值投资·金（现行选摸个鱼吧III——行为变化锚点；失格卡 reason=strategy-off-universe） | 先行 | §3.1 eval 支 |
| G2 | {战术专家:佩拉 —, 不虚此行 —, 离火燎原 —}（三卡全未评估、全金、prior 各 2；失格卡在 idx0） | 选不虚此行 idx1（现行 idx0 佩拉同分先胜——prior 支不可达锚点；对照卡必须同为未评估，带 eval 分的卡会压过 prior 支使锚点失效） | 先行 | §3.1 prior 支 |
| G3 | {贸易专家:停雲（LCS→停云）, 招财狗 30, 现金为王 30} | 选招财狗（现行 eval-lcs 40 选停雲——形变名以 canonical 身份进门锚点） | 先行 | §5 身份解析 |
| G4 | {黑塔纪元 —, OOTD·金 50, 价值投资·金 45} | 黑塔纪元，reason=augment-defining（前提成立侧回归，S1 120 不变） | 先行 | §4 |
| G5 | {量子同频星徽 28, 气氛组 20, 赌神·银 20}，无 evicted | 选量子同频星徽（对照帧） | 先行 | §4 前提✓侧 |
| G6 | G5 帧 + `evicted={'希儿量子'}` | 选气氛组；量子同频星徽失格（量子同频阵营出全集 + 前提破缺） | 先行 | §2/§4 evicted 动态 |
| G7 | G6 帧 → T-162 | 量子同频星徽槽 ∈ refresh_slots（前提破缺 ⟹ `_cand_s1`=False ⟹ 非顶级可刷） | 先行 | §3.4 |
| G8 | {砂里淘金 25, OOTD·金 50, 中产阶级 50} | 砂里淘金，reason=econ-engine（引擎豁免优先于门；「引擎∧绑定∧锚外」唯一点位回归） | 先行 | §5 豁免序 |
| G9 | {奋斗协议 45, 复印件 45, 赌神·银 20} | 选复印件 reason=eval+blood-avoided（现行不变——血本位三态与门正交的血卡侧回归；「不受辖」的结构证明 = 模块头断言两血卡绑定双空 ⟹ 门谓词 anchored 恒假；血卡永不入 L1 分区，胜出面不可区分故以结构断言承重） | 先行 | §3.1 血分区 |
| G10 | {仙舟星徽 28, 快请专家·彩 40, 躺平 22} + `locked_comp='景元仙舟'` | 仙舟星徽，reason=align×N（N 直调 = 1，45+20=65 压裸分；集内锚定卡的 S3 通路零误伤） | 先行 | §3.1 S3 正交 |
| G11 | {摸个鱼吧III, 贸易专家:停云, 潜行专家:貊泽} | 全失格帧：选 idx0，reason=strategy-off-universe，score=0（强制选一仍可选，与环境门垫底语义逐位同形） | 先行 | §3.2/§3.3 |
| G12 | {护盾星徽 28, 气氛组 20, 招财狗 30}，对照帧无 priority →选招财狗；`strategy_priority=['护盾星徽']` → 护盾星徽 reason=user-priority（0+30=30 与招财狗同分，idx0 先胜——steering 复活失格卡锚点；注：复活面 = 0+30 ≥ 帧内其余候选最高有效分，其余候选 >30 时救不回（=30 依赖 idx 先胜）；与环境门 U5 同形） | 同左 | 先行 | §3.1 steering |
| G13 | {摸个鱼吧III, 价值投资·金 45, 复印件 45} → T-162 | refresh_slots 含失格槽（门不改刷新分类的回归对账） | 先行 | 总纲 §2.3 |
| G14 | monkeypatch **双表注入**：`AUGMENT_COMP_AFFINITY` 注卡 X = {'库外comp': 1.0, '库内comp': 0.8}、注卡 Y = {'仅库外comp': 1.0}，**并**同步 `STRATEGY_BINDINGS` 给 Y 注双维全集外绑定（X 不注绑定）——注入卡不在绑定表则 anchored 恒假、门不辖，「Y 失格」断言结构性不可达，故 Y 须双表注入 | X 豁免保留（S1 120，∃ 形态）；Y 失格（reason=strategy-off-universe；多 comp 前提与库外指向的注入型守卫；现行表无多 comp 条目，直调 7/7 单 comp） | **占位** | §4 |

占位锁标注原则：G14 为注入型（注册表现状不可达）；其余全部先行锁（现行表直调可定）。landing 3.1 审计若翻面任何二义卡（如星徽大使叽米改判锚定），受影响锁 fixture 按审计结论重定——审计表与锁表的对账点是 D-c 名单（§6.4-2）。

**回归面**：`test_cw_invest_refresh.py` 全量（T-162 判据本体未动）＋ invest-env 迭代全部锁（`test_cw_env_universe.py` U1-U6、`test_cw_env_economy.py`、`test_cw_env_gift.py` G 组、`test_cw_env_pool_rewrite.py` Q 组、R 组 kernel 侧）——同文件（cw_events.py）改动 + 共享 helper 重构（env 3.4 之后同区含 `candidate_char_universe`/`gift_hit_tier`），环境迭代全部锁组都是本批回归的硬组成（§8）。

### 8. 与环境迭代的机器共享契约

- **落码序（硬约束）**：invest-env 3.1（`candidate_faction_universe` + env 分支门 + U 组锁）先行合入并验收（产物依赖：阵营全集函数本体 §5 消费 + U 组锁 = 行为保持重构的保绿凭据）；本迭代 landing 3.2 开窗**另受同文件互斥约束**——见下方「同文件互斥集成窗口」（invest-env 3.5 收口）。本迭代 landing 3.1（335 审计）不依赖环境落码，可先行（其 `candidate_*` 断言以本详设 §1 直调值为准）。
- **共享函数签名**：
  - 环境侧已定：`candidate_faction_universe(evicted: frozenset[str] | set[str] = frozenset()) -> frozenset[str]` @ `kernel/cw_comps.py`（invest-env §2.1.1）；
  - 本侧新增：`candidate_core_char_universe(evicted: frozenset[str] | set[str] = frozenset()) -> frozenset[str]` @ 同区（§2）。**命名与 env 送卡型候选角色池显式分立**：env 详设（`2026-09-12-invest-env` details/env-value-models.md §2.1.3）的 `candidate_char_universe` = core∪shared（辖「赠卡有没有人用」），本侧 core-only（辖「结构上永不 align 的绑定」，S3 角色维只数 core）。两问不同答案，同文件落码**禁共用一名**——env 侧由其跟进方落地时须核对该命名约定；**本节 = 两迭代共享边界的单一源**（阵营维共用一函数 + 角色维分立双函数 + 失格/evicted 语义镜像不另立），env design.md §1.3-2 跨迭代契约行与本节同义；
  - 遍历域单一源：模块内私有 helper（如 `_candidate_comps(evicted)`）承载 {comp ∈ COMP_LIBRARY | name ∉ evicted}，两公开函数共用。抽 helper 属行为保持重构，落在本批（环境批之后），以环境迭代全部锁（§7 回归面，含 G 组直调分档锁）+ D-a/D-b 漂移断言保绿；环境批自身的函数签名与语义零改动。
- **decide_event 帧级单读**：环境批落 `_universe = candidate_faction_universe(evicted)`（循环外一次）；本批在其邻位加 `_universe_chars = candidate_core_char_universe(evicted)`，策略门**复用环境批的 `_universe` 变量作阵营维**（同一变量零二次调用——「同一台机器的第二个消费位」的字面落实），禁在策略分支内联重写「faction ∈ ⋃comp.factions」。
- **同文件互斥集成窗口**：`kernel/cw_events.py` 同时至多一个在飞落地批。序 = invest-env **3.5**（env 分支汇合集成 = env 侧 `cw_events.py` 最后触面；3.1/3.4 由其依赖闭包传递覆盖）合入验收 → 本批 3.2 开窗；`kernel/cw_investments.py` 触面（本批补绑定条目 vs env 3.2/3.6 schema/表）互斥由两迭代 landing 头注声明、编排者排序。本批回归必须带环境迭代全部锁（§7 回归面）。
- **禁二次建模红线**：全集语义（候选 = 非 evicted COMP_LIBRARY）、evicted 语义（意向层「等同信号未发生」）、失格语义（落 0 垫底 + 归因串口径）三者的单一源分别在 invest-env §2.1.1 / §2.1.1 / §2.1.2，本迭代只消费与镜像，不另立定义。

## 关键取舍

| 备选 | 为何放弃 |
|---|---|
| 角色全集含 shared_chars | 4 卡差集（狼狩星徽系/锻冶专家:刃/骇客专家:银狼）中狼狩星徽系效果主体是全集外阵营，放行 = 复活病灶；且这些卡对一切可达 D\* 结构上永不 align（§2 论证 1/3）；错杀修正路径 = 修 COMP_LIBRARY，不是放松门 |
| 角色全集含 transition_chars | 实测零增量（仅 transition 被绑角色所在卡均另绑集内实体，§1/§2）；原则同 shared（临时可吃 ≠ 玩的方向） |
| 角色全集并入 `candidate_faction_universe` 返回二元组 | env 调用点被迫解包无用半边；双镜像函数 + 共享 helper 同样零二次建模且各自单责（§2 落码形态） |
| 门只跳 eval 支、放过 eval-lcs/prior | 形变名复活（LCS 12-75）与未评估卡回落分（0-5）保留失格卡的无信息竞争，垫底语义破缺；三支同属 S4 常规评估族（§3.2） |
| 门谓词按「绑定名 ∈ 派生候选 comp 的 factions∪chars」内联实现 | 二次建模全集机器（禁）；且漏掉 evicted 动态收窄的一致性保障（§8 红线） |
| S1 前提用亲和值阈值（如 ≥0.8 才豁免） | 无推导拍值（0.6 的量子力学现行 S1 触发，改阈值 = 分叉 S1 语义）；∃/∀ 与值域都不进门前提，维持表非空触发（§4） |
| S1 前提取 ∀（全部亲和 comp 在集才豁免） | 错杀面更大；与门谓词并集形不同构；现状 7/7 单 comp 无行为差，∃ 形态仅约束未来（§4，锁 G14） |
| 失格卡同时剔出 T-162 可刷集 | 总纲已否（§2.5）：失格槽本就可刷（刷掉它 = 改善支）；本设计只细化 `_cand_s1` 旗标语义使前提破缺的定义卡不被顶级保护（§3.4） |
| 失格卡从 L1 分区剔除（集合级排除） | 用户裁定形态 B（落 0 垫底）；全失格帧强制选一需要 L1 保留失格卡（§3.1，锁 G11） |
| 门同时给 env 分支加角色维 | env 分支的角色维由送卡型详设独立承载（core∪shared 门槛镜像，env-value-models.md §2.1）；策略门的 core-only 角色维是另一问（S3 计维对齐），两维不共用一个函数（§8 命名分立注） |
