# comp-readout-unification 迭代设计（总纲）

> 术语约定（首次出现定义）：**读口** = 从阵容注册表（`cw_comps.Comp`）取派生信息的正式
> 函数或属性，是消费该信息的唯一合法入口。**数据字段** = `Comp` 上人手编的知识登记
> 字段（core_chars/need_star 等）。**派生概念** = 策略代码实际消费的、由数据字段加工
> 出的信息（终局成员集、线 carry 单名锚、关键装备清单等）。
>
> **设计基线**：or-reqs-retirement 落地后快照（提交 9a1fc0cf8 之后；该并行迭代已
> 符号级删除 `or_reqs` 字段与希儿系伪键机器）。多 agent 并行期，各落地批开工前须
> 复核基线漂移（git log 对照本行提交号，漂移则先修订设计再动工）。

## 0. 元信息

- 迭代目标：用户裁定（2026-11-05 会话：「都做」——治本路线：读口层立法 + 四批收敛；
  A2 数据方向 = 教义为准重写、批 B 行为申报按攻略明文改写，同日确认）。
- 状态：对抗审两轮收敛（首轮三核+对照、复审无前提），必改项全部落文，可定稿
- 文档清单：
  - details/members-readout.md —— 批 A：终局成员集读口（members）落地与 14 处替换
  - details/carry-anchor.md —— 批 B：线 carry 单名锚统一（含分配器键换算第六处收编）
  - details/equip-projection.md —— 批 C：装备到人补全 8 套 + key_equips 字段退役为投影
  - details/roster-hygiene.md —— 批 D：双列回声数据清理 + shared_chars 语义诚实化

## 1. 问题与动机

### 现状症状（四族；存在性经双攻击者独立逐点核实，见 attack.md「相符清单」）

1. **终局成员集（core ∪ shared）无读口，14 处手写**：三种形态（保序去重 tuple × 3 /
   set 并集 × 7 / 两行式 fold set × 3 / 布尔判定 × 1）、防御程度混杂（全 getattr × 2 /
   半 getattr × 6 / or-默认 × 3 / 直读 × 3）。getattr 防御的历史理由（注册表外伪阵容
   条目）已随配方决策层退役（2026-11-04）消亡。清单见 details/members-readout.md §1
   （另核合法内联 2 处：derive_member_priority、送卡档位机器三名单扫描——单点概念
   性扫描，不属违例）。
2. **线 carry 单名锚六处承载**：`LINE_ANCHOR` 21 行手编表（与 `carry_anchor()`
   20/21 同值复制，唯一真分歧 = 火花星间旅人）+ equip_allocation（两处）/ cw_equip_env
   装备优先序不查 fallback + `cw_plugins.cross_line_skeleton` 读聚类集合 +
   `cw_loop._allocator_update` 分配器 arm 键换算（第六处；「阵容→arm 键」换算散在
   初始化侧与 update 侧两处，57-A1 修过的「键不配对恒 no-op」即其病灶）。详见
   details/carry-anchor.md §1。
3. **关键装备双源无防线**：`key_equips` 手编字段与 `equip_assign` 投影并存（C4/C5
   迁移期契约），21 套中 8 套未迁移到人数据；**恒等约束仅有 docstring 声明、无任何
   测试/建库校验钉住**（生产 docstring 三处指认不存在的「恒等测试」——既有文档债，
   见 attack.md B-1）。
4. **概念文档锚漂移**：predicates.py 模块级与函数 docstring 引「01_math_framework
   §2『目标线 K』/§5.3」——现行 01 号篇两处皆不存在（悬空引用）；「K」在 P41 证明
   （K=core_chars，shared=邻接）与 strategy-telemetry `k_members`（core ∪ shared）
   两处口径不一致。

### 根因归层：语义层（兼架构层）

Comp 的**数据字段层**（人编知识登记）与策略实际消费的**派生概念层**之间，从来没有
统一的读口设计。派生概念各自为政地散落在四种落点：Comp property（factions 族 × 4，
好形态）、模块函数（carry_anchor / derive_key_equips 族，好形态）、策略层手编表
（LINE_ANCHOR，病灶）、不落地由消费点各自拼装（成员集 14 处，病灶）。

**治本核验（跨件半问）**：这是同族问题的第二次出现——comp-structure-unification 3.1
（2026-11-04）已把**羁绊维度**的派生读口统一为 `core_faction_reqs` /
`bonus_faction_reqs`，但该次只统一了一个维度、未立「派生概念必须读口化」的通用法，
随后成员维度（14 处）、carry 维度（六源）、装备维度（双源）各自复发。按项目决策
原则（同族第二次 = 升架构级设计件），本迭代即为该架构级设计件：立法 + 读口清单 +
分批收敛，终结「发现一处烂一处补一处」。

### 解决到哪

1. **读口层两层模型立法**（§2）：数据字段层写知识登记语义、派生读口层写消费语义，
   两层 docstring 分责；
2. **读口清单**：概念 → 读口登记表（收窄列集，读口是可 grep 的代码符号；不设
   「消费面」列——它是代码结构的第二抄本，必漂移）；
3. **四批收敛**：批 A members / 批 B carry（含分配器键） / 批 C equip 投影 /
   批 D 数据卫生。

### 明确不解决（防范围外溢）

- **d1 schema 重构**（单一名单 + 档位标记）：推迟到 transition_chars 退役落定后——
  届时档位 3 收 2 才看得全终局形态，现在定形大概率二次搬迁；其增量收益已全部拆解
  （杜绝双列 → 批 D 零风险清理即可；档位显式 → 送卡档位机器已承载）。
- **kernel DI 管道退役**（cw_launch_admission / bridge 的 line_members 注入参）：
  独立后续迭代立项——members 落 Comp 后其存在理由消失，但该管道动三层文档引用的
  契约段，与本迭代四批零耦合，不并入。
- **equip_taboos 类级条目接线**（万敌「护盾件(类)」零消费）：知识正确性缺口另案。
- **transition_chars 退役**：另案；退役时须给 shop.py 买牌拒因标签 `transition_char`
  安排归宿。
- **P41 证明文本 K 口径债**：证明文档更新债另案；读口 docstring 只对齐现行实现口径
  （telemetry `k_members`），不引「目标线 K」名号。

## 2. 方案

### 2.1 系统级变化：读口层两层模型

```
数据字段层（人面向，Comp 字段）          派生读口层（机器面向，策略消费唯一入口）
────────────────────────────           ──────────────────────────────────────
core_chars / shared_chars      ──┐
faction_reqs / flex_factions     ├─→  members（终局成员集；批 A 新增）
need_star / key_items            │    carry_anchor + 分歧登记（批 B 统一）
equip_assign / equip_taboos      │    key_equips 投影（批 C 字段退役）
plaza_carry / required_deployed  │    factions / all_factions / core_faction_reqs
char_positions / name /          │    / bonus_faction_reqs（既有，不动）
transition_chars(退役另案)      ─┘    derive_member_priority / member_rank_of（既有）
```

**立法三条**（写入正本，见「正本更新清单」）：

1. **多消费点概念必须读口化**：一个派生概念出现第 2 个消费点时，必须在 kernel
   `cw_comps.py` 立读口；单点消费的一次性表达式不在此列（它不是概念——例：送卡
   档位机器的三名单扫描是合法内联）。
2. **管辖域 = Comp 派生概念**：凡派生自 `Comp` 数据字段、被策略层或 kernel 其他
   模块消费的概念，其读口落 `kernel/cw_comps.py`；**策略层立场数据**（LINE_HEAT /
   COMP_MEGASTAR_PREFERENCE / 词缀吃怕表——攻略热度统计与策略偏好，按 12 号篇
   分层归策略层）与**独立概念**（intention_core——意向核心，∈core 约束是 miss
   计数良定义的刻意语义，落 cw_intention）除外。禁消费点内联拼装字段组合
   （`set(c.core_chars) | set(c.shared_chars)` 这类写法即违例）。
3. **两层 docstring 分责**：字段 docstring 写知识登记语义（「凭什么信」：出处 /
   校准口径）；读口 docstring 写消费语义 + 正典文档锚。漂移在两层 docstring 对照下
   可见。

**守卫的诚实声明**：立法无自动守卫（项目测试纪律禁源码扫描测试）。守卫上限 =
读口清单（概念 → 读口，读口为可 grep 代码符号）+ review 关卡（comp-definition.md
方法论条目增补）。这强于现状——现状连「哪些概念该有读口」都无清单。

**读口清单（本迭代收口后的全景；状态列 ← 表示本迭代新增/收编）**

| 概念 | 读口 | 落点 | 状态 |
|---|---|---|---|
| 核心羁绊键集/档位 | `factions` / `core_faction_reqs` | Comp property | 既有（上迭代） |
| 加层羁绊 | `bonus_faction_reqs` | Comp property | 既有（上迭代） |
| 阵容轮廓 | `all_factions` | Comp property | 既有 |
| **终局成员集** | `members` | Comp property | **← 批 A 新增** |
| 线 carry 单名锚（聚类+补全口径） | `carry_anchor` | cw_comps 函数 | 既有 |
| 评分锚（攻略重述口径） | `rating_anchor`（分歧登记 ∘ carry_anchor） | line_select 函数 | **← 批 B 统一**；管辖域豁免：评分口径取攻略重述是评分决策（策略立场），同策略旁表依据 |
| 分配器 arm 键 | `arm_key_of`（= carry_anchor；键空间实测 = n_posts≥15 聚类 carry 名） | cw_run_allocator 函数（cw_loop 仅改调） | **← 批 B 收编** |
| CARRY 档全集 | `carry_set` | cw_comps 函数 | 既有 |
| 关键装备清单 | `key_equips` | Comp property（委托 derive_key_equips） | **← 批 C 退役字段改派生** |
| 成员优先级 | `member_rank_of` / `derive_member_priority` | cw_comps 函数 | 既有 |
| 意向核心（miss 计数） | `intention_core` | cw_intention 函数 | 独立概念，豁免管辖域（批 B 补分工声明） |
| 攻略热度 / 巨星偏好 / 词缀吃怕 | LINE_HEAT / COMP_MEGASTAR_PREFERENCE / affinity 表 | 策略层旁表 | 策略立场数据，豁免（12 号篇分层） |

### 2.2 四批概览与依赖

| 批 | 内容 | 行为 | 依赖 |
|---|---|---|---|
| A members | `Comp.members` + 14 处替换 + 薄委托 + 死防御清理 + 鸭型桩改造 + 悬空引用修正 | 零漂移 | 无 |
| B carry | LINE_ANCHOR 降分歧登记（21 行→1 行）+ 装备优先序三处统一 + 分配器键换算收编 + intention_core 分工声明 | 3 条空值线获得装备优先人（语义合理化）；分配器键行为按详设申报；评分锚零漂移 | 与批 A 同动 line_select.py——**串行执行**（无逻辑依赖） |
| C equip 投影 | 第 0 步补建恒等测试 → 8 套 equip_assign 补全（教义为准重写）→ key_equips 字段退役 property → 恒等测试转终态 | 装备证据面按教义校正（增/减/重写三方向，见详设申报） | 无（与批 B/D 在 cw_comps.py 交叠，串行更稳） |
| D 数据卫生 | ~18 套双列回声清理 + shared_chars docstring 诚实化 + core∩shared 建库校验 | 零漂移（members fromkeys 对双列清理鲁棒，批 A 先行 = 本批行为锚） | 批 A |

### 2.3 跨详设接口契约（唯一必须在总纲定死项）

1. 四批的新/改读口（`members` / `rating_anchor` + 分配器键换算 / `key_equips` 投影）
   互不依赖；Comp 数据类的改动（批 A property / 批 C 字段退役）各自独立成提交。
2. **评分锚读法**（批 B 定）：`line_select` 线分 anchor =
   `_LINE_ANCHOR_DIVERGENCE.get(comp.name) or carry_anchor(comp)`——分歧登记表仅列
   与 carry_anchor 不同值的线（现状唯一 = 火花星间旅人 → 花火），评分锚行为保真。
3. **key_equips 投影读法**（批 C 定）：字段删除后 `comp.key_equips` 读法零改动
   （property 委托 `derive_key_equips`，全量迁移后其 fallback 分支删除）；
   `derive_key_equips` 保留为唯一实现体；恒等测试第 0 步补建、随字段退役转终态
   （锁「全库 equip_assign 非空且键 ⊆ core∪shared」）。
4. `predicates.line_members` 签名与返回类型（`tuple[str, ...]`，comp=None → `()`）
   不变——9+ 下游、kernel DI 注入、遥测 `k_members` 读口全部无感（批 A 薄委托）。
