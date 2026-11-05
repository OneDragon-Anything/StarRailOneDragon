# or_reqs 退役与过渡组合制（or-reqs-retirement）迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户裁定（2026-11-05 会话，五项）——
  1. `or_reqs` 整字段退役；
  2. 终局「希儿量子」条目改纯 AND：档 0 = 量子同频 4 + 贝洛伯格 4；
  3. 过渡层重构为「5 个过渡羁绊构造块 × 两两组合 10 条静态枚举」，**凑出两个羁绊才算锁定**（单羁绊凑出不锁）；
  4. 不设终局直通特殊条目，终局锁定走现行统一机制（位面 2 + 投资策略选完 → 终局候选首名）；
  5. 过渡买面增加货架虚拟评估（与终局侧货架资格买入同构）。
- 状态：草案
- 文档清单：
  - [details/seele-final-comp.md](details/seele-final-comp.md) —— 终局希儿量子条目改档与 fp 行为核算
  - [details/transition-combos.md](details/transition-combos.md) —— 过渡羁绊构造块与组合条目生成机器
  - [details/or-reqs-cleanup.md](details/or-reqs-cleanup.md) —— or_reqs 退役符号级清理清单
  - [details/virtual-eval-arm.md](details/virtual-eval-arm.md) —— 过渡侧货架资格虚拟评估

## 1. 问题与动机

### 现状症状

1. **判据口径错位**：`or_reqs` 的 OR 语义出处全部是过渡体系文档（transition_combos.md:166「引擎：量子3 或 贝2 都行……不设完全体门槛」= 位面 1 体系启动判据），却被装进终局线「希儿量子」的成型判据——档 0 的 `{量4, 贝2}` 被 OR 承接规则整体免账成死数据，终局线 `form_progress` 与过渡条目「希儿引擎」逐字恒同（均为「希儿在场 ∧ 量2∨贝2」），终局完成度失去度量意义（fp=1.0 时板面可能只是过渡形态；希儿+1 量子件 fp=0.75 即过 commit 线 0.4）。
2. **特殊逻辑面**：为该字段存在的机器 = form_progress 的 OR 折法 + 承接规则 + 建库校验③ + deploy_search 的 OR 组折叠三函数 + `SEELE_OR_REQS`/`SEELE_CARRY_CHAR` 常量；另有一整套「希儿系」平行机器横跨 9 个文件（cw_deploy_logic/cw_system_cards/cw_engine_facts/predicates/cw_win_model/cw_affinity_table/cw_line_facts/cw_bridge_pool/deploy_search），同一判据「希儿在场 ∧ 量2∨贝2」在 Comp 侧（OR 折法）与 kernel 侧（`seele_system_formed`）两套表示，靠注释声明对齐、无结构单一源。
3. **游戏知识与字段定义矛盾**：终局形态实证（final_seele_quantum 构造机理，n=67）=「量子4+贝4 双修（36/35 篇几乎不分离）」「贝洛伯格至少 2 尽量追 4」「量子4 57/67 过半」——终局判据应为量4∧贝4 的 AND，不是任一即成的 OR。
4. **过渡层单条目制的方向缺口**：现行 `TRANSITION_LIBRARY` 4 条单体系条目、凑出单体系即锁单条目，锁定后另一体系（如仙舟DOT 局的 DOT 半边）失去买面/保护方向。comp-structure-unification 3.3 放弃「体系对组合形态」的裁定按用户 2026-11-05 新裁定部分翻案：组合形态条目化，但走静态枚举 + 现有候选计分机器，不复活旧运行时状态机。

### 根因归层

- **语义层**（主）：过渡体系启动判据被用作终局成型判据——两层判据该各自归位（启动归过渡、完全体归终局）。
- **表示层**（次）：同一判据两套表示（Comp OR 折法 vs kernel 谓词），表示重复靠注释对齐。

### 解决到哪；明确不解决（外溢申报）

解决：§0 五项裁定。

不解决、另行立项（本迭代明确不做）：
- carry 单名基准五源统一（`LINE_ANCHOR` 21 行手编大表 / cw_intention:185 / equip_allocation / cw_equip_env 的本地实现不查 fallback）——本迭代只同步核对 LINE_ANCHOR 希儿行数值仍正确；
- `key_equips` ↔ `equip_assign` 迁移收尾（8 套未迁移）；
- `equip_taboos` 类级条目「护盾件(类)」零消费调用点；
- `transition_chars` 消费面萎缩（全库仅送卡估值一处）的处置；
- `need_star`/`key_items` 键与成员名单关系的白名单校验（本迭代只加「键 ∈ 角色注册表」基本校验，名单关系校验涉数据修正——如双王圣杯·远坂凛该进 core 还是白名单——需游戏知识裁定，外溢）。

## 2. 方案

### 系统级变化

1. **终局侧**（详设一）：`COMP_LIBRARY`「希儿量子」条目档 0 改 `{量子同频: 4, 贝洛伯格: 4}`、新增档 1 `{战技点: 2, 治疗: 2}`（从 flex_factions 升档），`flex_factions` 收敛为 `["盛会之星", "列车同行"]`，删 `or_reqs`；`required_deployed=("希儿",)` 保留。fp 分度恢复：希儿+量1 从 0.75 → 0.42（仍过 commit 线 0.4，「希儿到手即开线」语义由 required 折条承载不丢），完全体 = 1.0。
2. **过渡侧**（详设二）：`TRANSITION_LIBRARY` 重构——模块级 5 个 `TransitionBond` 构造块（仙舟3 / DOT2 / 列车2 / 希儿量2 / 希儿贝2，三型计分口径收进构造块），建库期 `itertools.combinations` 程序化生成 10 条组合条目（Comp 结构，档 0 = 两键 AND + 点名件 required）；**锁定域 = 组合条目**（单羁绊构造块不进库、永不锁定）；现行候选计分/锁定机器（update_transition_candidates）零改动复用。
3. **退役清理**（详设三）：`or_reqs` 字段与全部字段层机器删除（OR 折法/承接规则/校验③/SEELE 常量/deploy_search 希儿伪键三处）；kernel 结算侧谓词族保留不动。
4. **虚拟评估**（详设四）：过渡计分核心提纯为纯函数，买牌场景对「在手 ∪ 货架」虚拟计分，货架牌 ∈ 虚拟过渡候选组合的计分成员域 → 过渡资格买入（与终局货架资格买入同构）。

### 详设划分与跨详设接口契约

- **契约 A（详设一 ↔ 详设三）**：详设一落地后 `COMP_LIBRARY` 内 `or_reqs` 清零；**全库**清零在详设二替换过渡条目后达成——中间态 = 过渡库旧「希儿引擎」条目仍持 `or_reqs`（OR 机器保持可运行，希儿量子终局线已按纯 AND 折算）。详设三机器删除的前置 = 全库清零。两阶段互不阻塞、中间态可运行。
- **契约 B（详设二 ↔ 详设四）**：过渡计分与排序核心 = 纯函数 `transition_scores(held, sources) -> list[tuple[str, float]]`——函数内完成「计分（持有分+减分面）+ 过滤 >0 + 排序（分数降序, 注册序）」，返回**有序全序列表**；实机帧（update_transition_candidates）与虚拟帧（资格臂）各自对返回列表切片取前 N（纯切片，无实现漂移空间）。排序键禁两处实现——tie-break 分叉会使虚拟候选序与实机锁定序不一致。
- **契约 C（顺序锁）**：先换过渡条目库（详设二，旧「希儿引擎」条目随之退役）→ 后删 or_reqs 机器（详设三）——顺序固定，禁倒置（倒置 = 旧希儿引擎条目失去 OR 表达）。
- **契约 D（数据层边界）**：kernel `seele_system_formed` / `SEELE_AMP_FACTIONS` / `engines_count` / `is_seele_system_member` 保留不动（结算键 rung、胜率模型、A/B 工具、守恒门的数据层，comp-structure-unification 迭代 transition-library.md「保留边界」涵盖——该清单逐符号列的是 SYSTEM_CARDS 数据本体/engines_count 等，seele 谓词族为其延伸归类，保留面成立）；`knowledge/cw_line_facts.SEELE_SYSTEM` 亦保留（telemetry/schema.py 的 RHO_SYSTEM_KEYS 实测观测面独立消费，见详设三 #7）。本迭代只动 Comp 表示侧与部署评分侧。
