# plaza-carry-retirement 迭代设计（总纲）

## 0. 元信息

- 迭代目标：`Comp.plaza_carry` 整字段退役，carry 锚收编为 core 序顶端的派生读数（用户裁定，2026-11-06 字段排查会话：「终局阵容 carry 就应该是阵容中优先级最高的核心角色，无需额外定义」；本篇为该裁定的完整设计）。
- 状态：草案
- 文档清单：（无详设——单文档方案，本篇即完整设计）

## 1. 问题与动机

- 现状症状（四条，均为可复核的存量事实）：
  1. **派生关系事实已存在但未契约化**：全库 21 线中 18 线 `carry_anchor(comp) == comp.core_chars[0]`（无契约的巧合一致）；3 条空值线（银枝/飞霄/桑博）的 `CARRY_ANCHOR_FALLBACK` 补全值全部 `== core_chars[0]`——该表实为 core[0] 复述表。复核方式：逐线代入两式比对（复核脚本口径见 §2.4）。
  2. **双源病补丁两张**：`_LINE_ANCHOR_DIVERGENCE`（评分锚与聚类锚分歧登记，现 1 条）与 `CARRY_ANCHOR_FALLBACK`（3 条）——carry 若从成员结构派生，两表无存在理由（fallback 值恒等 core[0]，分歧线随火花裁定收口）。
  3. **火花星间旅人线结构例外**（cw_comps 火花线条目 + 建库断言③的羁绊半边豁免）：聚类锚「火花」∉ core ∉ members——fp 点名折条、部署 L1 named 层（10⁹ 域）、装备分配第一顺位全部指向一个采购集不买、卖牌不保护、无星级目标的非成员；三个 carry 读口三值（`carry_anchor`=火花 / `rating_anchor`=花火〔分歧登记表〕/ `intention_core`=花火〔∈core 约束〕）。行为面割裂是结构冲突的直接表现。
  4. **core 声明序无主次契约**：巡海击破 core[0]=不死途（羁绊结构序）而锚=波提欧（core[1]）；双王圣杯 core[0]=吉尔伽美什而锚=Saber（core[1]）——「谁是定义件」的主次信息只由 plaza_carry 一处承载，core 序本身不含该语义。
- 根因归层：**语义层**。「谁是阵容定义件」是成员结构的属性（优先级顶端），现状被独立登记为统计抄录字段（plaza 聚类 carry 直接进运行时行为链：fp/部署/装备/评分），跳过手判层消化——层次混淆：**对账锚是校准流程的元数据，不是行为机器的判据源**。违反 comp-definition「派生优先」判据（能从既有字段派生的不手编：carry 可由 core 序顶端派生，18/21 已同值、2/21 序换位后同值、1/21 裁定后同值）。次生根因：core 序的「首位=定义件」惯例（18/21）从未契约化，导致主次信息被迫外溢到独立字段。
- 解决到哪：`plaza_carry` 字段、`CARRY_ANCHOR_FALLBACK`、`_LINE_ANCHOR_DIVERGENCE` 三件全退役；`carry_anchor` 改派生 `core_chars[0]`（core 序契约化「首位=定义件」）；火花线裁定收口（方向与依据见 §2.2）；plaza 聚类降级为版本重跑对账证据（gen_plaza_comps.py 差异报告，人裁定是否重排）。
- 明确不解决（外溢面，禁并入本迭代）：
  - `member_rank_of` 三档化（core[0]=0/core 其余=1/shared=2，让位序获得「定义件最后让」保护精度）——让位序行为增益，独立小批；
  - run 分配器键空间重整（改按线名一臂）——统计归零重启，超范围；本迭代仅换键源为查表（值恒等，见 §2 系统级变化 6）；
  - 火花线 need_star 精值定档——数据核对项（§3.1），非设计决策；
  - comp-definition「登记↔消费一致性建库校验族」外溢立项（key-items-retirement design §1 已登记的族级防复发件）。

## 2. 方案

### 2.1 系统级变化

1. **core 序契约化**：`core_chars[0]` = 定义件（主C）——写进 `Comp.core_chars` 的字段注释与 `members` 读口 docstring（「序 = 注册表声明序（首位=定义件）」）；数据批完成 2 套换位 + 1 套裁定（§2.2）。
2. **`carry_anchor` 改派生**：`return comp.core_chars[0] if comp.core_chars else ''`——七处消费点（form_progress / deploy_search×2 / equip_allocation / cw_equip_env / cw_plugins / cw_run_allocator 改造后不再消费，见 6）签名与返回值域不变，零改动（cw_run_allocator 除外）。
3. **字段与两表退役**：`Comp.plaza_carry` 字段、`CARRY_ANCHOR_FALLBACK` 表、`_LINE_ANCHOR_DIVERGENCE` 表删除；`rating_anchor` 函数删除，评分锚消费点直读 `carry_anchor`（line_select 内部 2 处）。
4. **点名件统一表达式换源（`named_units` 收编）**：现表达式 `named = (anchor,) if anchor else tuple(core)` 的「终局单锚/过渡全员」区分信号依赖 anchor 可空——派生后 anchor 恒非空（core 非空线），区分信号消失。新增模块级派生函数：
   ```
   named_units(comp: Comp | None) -> tuple[str, ...]
     终局条目（comp.name ∉ TRANSITION_COMBO_PARTS）→ (comp.core_chars[0],)
     过渡组合条目（comp.name ∈ TRANSITION_COMBO_PARTS）→ tuple(comp.core_chars)
     comp=None（裸键组）→ ()
   ```
   过渡判据 = `TRANSITION_COMBO_PARTS` 键集（生成器单一源，键集与条目名集一致性已有建库校验①钉住）；`form_progress`（点名折条）与 `deploy_search` L1 named 层（:278-282）共用本函数——「同一表达式」契约保持，表达式本体换源。required-deployed-retirement 在 cw_comps:1410 与 deploy_search:275-282 的就地表达式随批替换。
5. **`intention_core` 简化**：`return comp.core_chars[0] if comp.core_chars else ''`（原「plaza_carry∈core → 用之；否则 core[0]」的分支删除——core[0] 必 ∈ core，∈core 约束由构造满足；miss 计数语义不变，火花线计数键变化随 §2.2 申报）。
6. **run 分配器键源换表**：新增 `LINE_STAT_CLUSTER: dict[str, str]`（线名 → 统计簇名，21 条，值 = 各线现行 `carry_anchor` 值快照；语义 = 跨局 adherence 统计的分组键，**非行为判据**——统计事实的合法运行时消费仅此一处）；`arm_key_of` 由 `carry_anchor(comp)` 改查表。键值恒等 → 分配器统计零重启。版本重跑时与 `PLAZA_CARRY_CLUSTERS` 核对（§2 系统级变化 8）。
7. **锚不变量断言改造**（`_validate_anchor_invariants`）：断言①（终局线锚非空）→ 等价改写「COMP_LIBRARY 全线 core_chars 非空」；断言②（过渡条目锚空）→ 改「过渡条目 `named_units` == core 全员」（判据换 TRANSITION_COMBO_PARTS，防线语义不变：过渡点名件=全员）；断言③（锚可达性：∈members ∨ 羁绊∩档0）→ **删除**（core[0] ∈ members 由构造恒真）；断言④（过渡 core ≤9）不动。
8. **对账迁移**：`tools/cw/gen_plaza_comps.py` 生成末尾追加差异报告——逐线比对「聚类 carry vs `COMP_LIBRARY` 各线 core_chars[0]」，输出不同值线清单（版本重跑流程消费；人裁定是否重排 core 序）。plaza 聚类自此只以「校准证据」身份存在。

### 2.2 行为变化申报（逐线）

统一验证口径（沿 key-items-retirement / or-reqs-retirement 先例）：不做 A/B 模拟对照；行为验证 = 落地批测试全绿 + 恒等断言（§2.4）+ 实机首局观察记为遗留待办（不设为完成判据）。

| 线 | 变化 | 说明 |
|---|---|---|
| 15 线（锚==core[0] 且序不变） | 无 | 逐位恒等（§2.4 判定式） |
| 银枝群攻 / 追击飞霄 / 专家桑博DOT | 无 | fallback 值恒等 core[0]，表删除零行为 |
| 巡海击破 | core 序换位（波提欧进首位，不死途次之） | 锚值不变；members 序 / 装备分配 core 档内序 / 圈人 core 档内次级排序微差（次级序变化，主判据零变化） |
| 双王圣杯 | core 序换位（Saber 进首位，吉尔伽美什次之） | 同上 |
| **火花星间旅人** | **裁定收口（方向 = 实战口径）**：core 增「火花」进首位（→ [火花, 花火, 爻光, 开拓者·欢愉, 银狼LV.999]），花火保留 core 次位 | 依据就地标注：plaza 火花簇 n=25（V4.4 实证，Final carry=火花）vs BV 转录攻略单篇（2026-02 录制，V4.0 时代口径花火主C）——版本差与样本量双差指向实战口径。行为变化：members +火花（采购面/卖牌保护/成员视图纳入）；need_star 补火花条目（精值按 plaza 火花簇 `carry_star3_rate` 于数据批定档）；评分锚 花火→火花（持花火由 +8000 降 +4000〔仍在 core〕、持火花由 carry_set 成员档升 +8000——carry_set 原含火花，证据门行为不变）；意向核心 花火→火花（miss 计数重置，键变统计重启）；fp 点名 / 部署 L1 named / 装备第一顺位 **值不变**（原锚就是火花）。裁定可翻案性：推翻时仅改数据批一处（core 序与 need_star），代码批与断言不受影响；分歧沿革归 final_comps 交叉核对记录（§2.3） |
| 过渡组合条目（C(5,2)=10） | 无 | named_units 换源值恒等（core 全员），测试锁 |
| run 分配器 | 无 | arm 键值恒等（查表快照） |

### 2.3 知识归宿登记

| 知识 | 归宿 |
|---|---|
| 聚类实证 carry（「统计层说主C是谁」） | gen_plaza_comps.py 差异报告（版本重跑对账证据，人裁定重排） |
| 火花/花火主C分歧沿革 | final_comps 交叉核对记录（火花线条目就地注释 + final_yinlang_joy 构造机理节核对） |
| 「18/21 首位即定义件」惯例 | core 序契约（docstring），由惯例升为结构语义 |

### 2.4 复核脚本口径（供落地批重跑验证）

```
恒等判定(除申报线外逐位同): carry_anchor_new(comp) == carry_anchor_old(comp)
  申报线 = 巡海击破/双王圣杯(锚值不变仅序变)/火花星间旅人(按 §2.2 裁定)
fallback 恒等: CARRY_ANCHOR_FALLBACK[线] == core_chars[0] (3 线, 退役前复核)
named_units 恒等(过渡条目): tuple(core_chars) 与旧表达式 else 半边同值
```

（本迭代不把一次性脚本入仓；判定式即持久口径，落地后重跑应得「字段不存在」。）

### 2.5 接口契约（对消费方的破坏面）

- `Comp.plaza_carry` 属性消失：生产直读 1 处（cw_intention.py `intention_core`）随批改写；注释引用 1 处（cw_loop.py :1778 附近）清理；测试构造 1 处（test_select_deployment.py :54 构造参数）删参。
- `CARRY_ANCHOR_FALLBACK` / `_LINE_ANCHOR_DIVERGENCE` / `rating_anchor` 符号消失：生产消费点（carry_anchor 内部 / line_select 2 处）随批改写；测试断言 2 文件（test_faction_derivation_locks :195-207 锚派生口径断言整段改写为派生读数断言；test_line_select rating_anchor 相关断言改读 carry_anchor）同步。
- `carry_anchor` / `carry_set` 签名与返回值域不变：其余消费点零改动。
- `TRANSITION_COMBO_PARTS` 从模块内部键集升为过渡判据公开消费源（import 期可用性不变，键集校验已有）。
- 测试桩兼容性：form_progress docstring 的「测试桩须按本表达式属性面(plaza_carry/core_chars)构造」句随换源改为「按 core_chars 构造」——缺 plaza_carry 属性的旧桩不再被容忍路径引用。
