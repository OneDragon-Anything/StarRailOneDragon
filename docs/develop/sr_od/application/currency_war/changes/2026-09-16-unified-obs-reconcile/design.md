# 统一观察对账与安灯 迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-16 会话，守卫治理链·执行失败安灯裁决后续）：观察对账归 game state 统一承载；失配 = 逻辑态被实读证伪 = bug（两原因：此前观察态错 / 逻辑推算代码错），默认停机现场修复；豁免按「画面×字段×逻辑写端」声明式治理；执行失败安灯退役并入统一对账。
- 状态：定稿
- 文档清单：单文档方案（无详设），本文件即完整设计。

## 1. 问题与动机

### 1.1 现状症状
1. **对账机制分散且处置错位**：「逻辑态 vs 实读」同一性质的分歧存在两套机制——①执行失败安灯（`cw_screen_prep._exec_fail_hook_check` + `run_state.exec_fail_should_stop` + 8 verdict 分类器 `telemetry.query.classify_spend_unit`，verdict 域 = effective/not_effective/partial_mismatch/unplanned_spend/no_spend_quiet/plan_truncated/free_refresh_proc/unknown）长在执行链上，判定后停机；②通用观察失配对账（`GameState.observe()` 覆盖 logic 值失配 → 缺陷台账 `_emit_defect`）只留证不停。前者是对账却长在执行链（职责错位，用户裁定对账归 game state）；后者在正确的层却不停机（被证伪的逻辑态继续喂决策）。
2. **失配处置无治理位**：失配无豁免申报面、无停机位，ADR-0651 的「修推算代码」缺运行时强制力，缺陷行靠人翻台账。
3. **台账噪音不分流**：sim 链对账差异（`sim:synthesized` 证据，约 18.6 万行）与生产实读失配（约百行）混在同一生产缺陷台账（`.debug/temp/currency_war/bs_defect.jsonl`），且缺陷行无时间戳，无法定位时点。
4. **生产失配存量**（统计时点 2026-09-16，归因批报告须复注时点与口径；基数为移动值，慢性模式实时复现中）：非 sim 证据完整失配行 102 = 86 行同一慢性模式（逻辑 17 / 实读 19，恒 +2，待归因）+ 7 行金散失配（+7/−2/±2 单发）+ 9 行其他字段（备战席错槽 3、节点序差一 4、板羁绊缺认 1、商店牌面 1）；另有 2 行为 JSON 跨行截断的坏行残片（非失配行，归因批不计入模式统计）。

### 1.2 根因归层
**流程/语义层**：对账职责缺统一归属点（执行链一处、容器一处各管一段）；失配处置无治理结构（豁免/停机/留证无分流）。不是表示层问题——容器、渠道签名、自足快照账本机制本身健康，全部直接复用（依据：`game_state/journal.md` §1-§4、`kernel/cw_game_state.py` 写入口族）。

### 1.3 解决到哪 / 明确不解决
**解决**：统一对账判定收口到 `GameState.observe()` 唯一观察写入口；失配处置升级为「豁免声明 / sim 分流 / 默认安灯停机」三分流；观察侧签名补画面名；执行失败安灯退役并入；安灯武装前完成金失配全模式归因。
**明确不解决**：①非金散缺陷（席槽/节点序/板/商店）的逐行归因修复（按普通 bug 走日常修，不属本迭代；其复现触发的停机 = 安灯正常工作）；②sim 链自身的对账质量治理（sim 侧只做分流，不再管）；③字段级容差/模糊比较（比较恒精确等值）；④非容器字段的画面瞬态对账（不进决策的数据不对账）。

## 2. 方案

### 2.1 判定总闸：对账住在唯一写入口
- **位置**：`GameState.observe()`——渠道①唯一观察写入口，「禁旁路直写」有 grep 守卫锁硬约束（依据：`game_state/journal.md` §6 硬约束①、`kernel/cw_game_state.py::observe`）。全部画面 op 的观察数据必然过这扇门，判定在门上做一次，全域自动生效，各 op 零对账代码。
- **判定条件**（现状语义保留）：`target.source == 'logic'` 且现值非 None 且实读 ≠ 现值 → 失配。carry / leave_screen / write_prior / relay / write_logic 自身不比对（依据：`observe` docstring §2.1/§2.2 边界）。
- **三分流接线点** = `observe()` 内现 `_emit_defect` 调用处（失配比对之后、`_swap` 覆盖之前）——覆盖先落、安灯后触发，证据在场不依赖钩子成败。
- **比较语义**：精确等值，无容差。容差会把小分歧洗成背景噪音（真 bug 失去信号）。注意区分两个容差面：finalize 金差值双源对拍的 ±2 容差是**现役独立留证面**（2026-08-17 审计 #6 P2 引入，容忍收入/连胜金不可观项混入，依据 `cw_screen_prep.py` finalize 段注释），不在本迭代拆除；但「不可观项混入」在容器精确等值下就是失配源——其归因与建模出口见 §2.6。
- **对账辖域** = 容器字段（金/hp/牌面/备战席/板/商店/节点序等），恰为逻辑态消费面；未入容器的画面瞬态散读不对账（不进决策，错了无毒）。

### 2.2 豁免注册表（画面×字段×逻辑写端，声明式）
- **载体**：新模块 `kernel/cw_mismatch_policy.py`（命名避让既有 `kernel/cw_reconcile.py`——那是 CwReconcile 观察态锚定写点，与本模块失配处置注册表无涉），失配处置策略单一源：
  - `EXEMPT_REGISTRY: dict[tuple[str, str], tuple[ExemptEntry, ...]]`（键 = (screen, field)，值为条目元组——同画面同字段可并存多条不同写端前缀的豁免）；`ExemptEntry` = frozen dataclass `{screen, field, logic_evidence, reason}`。
  - `lookup_mismatch_exempt(screen, field, logic_evidence) -> ExemptEntry | None`：先 `(screen, field)` 精确桶、后 `('*', field)` 通配桶，**两桶独立评估互不阻断**（精确桶 evidence 不中不跳过通配桶）；桶内逐条比对 `logic_evidence` 前缀（条目 `'*'` = 不限写端），首条全维命中即返回。
- **键的坐标系（本迭代改造项）**：
  - `screen` 键取**本次 observe 写入的 sig.screen**（观察侧；logic 族写入 screen 恒 None，不参与）。`ChannelSig.screen` 现为可空且主喂入口（`cw_observation.py` `_sig_read` / `_sig_carry`）不填——金/牌面/商店/备战席等对账主要辖域的失配行 screen 恒 None，精确键会结构性失效。**本迭代给主喂入口补画面名**（改造手段见下），使精确键可用；screen 在场是 obs 族写入约定非机制强制，**lookup 时 sig.screen 为 None 则精确键不可能命中，仅 `'*'` 通配条目可豁免**（不可指名画面的写端由此退通配条目治理）。
  - **画面名来源（落地手段钉死）**：`read_game_state(ctx, screen, phase)` 现签名中 `screen` 是图像帧非建档名——本迭代给其增加可选参 `screen_name: str | None = None`，**由调用方传其已知画面建档名**（画面 op 分派时自知当前画面）。不知道画面名的调用点传 None：现状测试的 `read_game_state(ctx, None, …)` 形态不变，落「None 仅通配可豁免」语义。拒绝的备选：funnel 内自跑画面匹配（每次读附赠一次全画面匹配成本，读路径热，否）；读容器 `current_screen` 现值（该字段写源即观察，过渡期是滞后值，语义错，否）。
  - `logic_evidence` 维度用于**同字段内分流失配成因**：例「刷新执行写下的金值与实读不合」可按写端前缀精确豁免，而不波及同字段的购买写端（真点击落空照停）。
- **治理规则**：每条必带 `reason`（持久索引 = 文件路径/符号名/ADR-NNNN，或纯语义描述——项目注释规范同判）；条目为代码常量，变更走 review 可见；**豁免 ≠ 消失**——豁免命中仍落 `kind='exempt_mismatch'` 台账行（可审计），只是无告警无停机。
- **初始为空**。现状生产失配没有一条值得豁免：散缺陷是 bug（归日常修），金失配全模式待归因（归因后修模/申报，见 §2.6）。注册表的价值是给「未来确证的游戏机制性差异」留治理位，不是给已知 bug 开后门。
- **粒度纪律**：三个维度各自拒绝退化——无 screen 维度则无法按画面治理（本迭代补齐）；无 logic_evidence 维度则金字段免刷失配与真点击落空不可分（只能全豁免 = 吞真失败）；自由文本/闭包条件的豁免（在注册表里写代码）仍然拒绝——evidence 前缀是声明式签名，与 sim 前缀分流（§2.3）同构。

### 2.3 失配三分流（observe() 判定后的处置序）
失配命中后按序判定，命中即停：

1. **豁免命中**（§2.2 注册表，入参 = 观察侧 sig.screen / 字段名 / 逻辑侧 `Field.evidence`）→ 落 `kind='exempt_mismatch'` 台账行（**行形状与真失配行同构**：含 `ts` 与观察侧 screen/actor/group_id + 逻辑侧 evidence，仅 kind 不同），无告警、无停机。
2. **sim 证据命中**（`observed_evidence` 前缀 ∈ `_MISMATCH_SUPPRESS_PREFIXES`）→ 不落生产台账（现役抑制语义 = 直接 return，依据 `cw_game_state.py::_MISMATCH_SUPPRESS_PREFIXES` 注释）。本迭代把 `'sim:synthesized'` 与 `'sim:engine'` 并列入表。理由：sim 链对账归 sim 质量面（skill `sr-od-currency-war-dev` sim-testing 域），约 18.6 万行混入生产台账已实证分流必要。
3. **真失配** → 缺陷行（`kind='observe_vs_logic_mismatch'`，**行补 `ts` 字段**，格式 = journal 行同款 `datetime.now().isoformat(timespec='seconds')`；`_emit_defect` 增加 sig 形参，行携带观察侧 screen/actor/group_id 与逻辑侧 `Field.evidence`——现状缺陷行无 sig 信息，为本迭代改造点）+ 现有 `[cw!]` 告警日志 + **安灯钩子**（§2.4）。

行落盘先于钩子触发——证据在场不依赖钩子成败。

### 2.4 安灯钩子：kernel 纯记录，停机走注入槽
- **kernel 侧**：`cw_mismatch_policy.py` 持 `_ANDON_HOOK: Callable[[dict], None] | None = None` + `set_reconcile_andon_hook(fn)`。注入槽模式先例 = `set_defect_sink` / `set_star_evidence_saver`（`cw_game_state.py` / `decision_assembly.py`）。缺省 None = 测试/sim 环境零副作用（只留证不停机），满足项目「可注入回调、缺省无真实现」硬约束。**导入方向**：`cw_mismatch_policy` 零依赖 `cw_game_state`（被单向 import；kernel→kernel 单向依赖先例 = `cw_state_journal`）。
- **触发契约**：真失配缺陷行落行后同步调用 `hook(row)`；`row` = 缺陷行 dict（`ts / field / expected / actual / observed_evidence / screen / actor / group_id / logic_evidence`）。hook 异常不阻塞写路径（best-effort，同 defect sink 契约）。
- **装配侧**：装配点 = `currency_war_app.py` `CurrencyWarApp.__init__` 装配段（与 `set_defect_sink` 等注入槽同点注入，ctx=self 在场，先例已核）。闭包职责按序：
  1. **每局闩**：载体 = 闭包内 dict（键 = run_id）；run_id 取 `current_run_id_safe()`（`cw_game_state` 公开读口），本局已触发过 → 跳过；**run_id 为空（局外）→ 只落证不停机**（与 journal 局外拒写假行同向，依据 `cw_game_state._current_run_id_safe` 缺席语义）；
  2. **截图**：帧源 = `ctx.controller.screenshot()`，闭包非 op 不走 `Op.save_screenshot`，直用 `one_dragon` 调试落盘工具（`debug_utils.save_debug_image`，同 `Op.save_screenshot` 底座），前缀 `reconcile_andon_<run_id>_<field>_`；失败不拦停机（flag 是主哨兵，先例 = exec_fail 安灯截图策略）；
  3. **写 flag**：`.debug/temp/cw_reconcile_andon.flag`（仓根锚定绝对路径——daemon spawn 的非 CWD 进程相对路径落错，教训见 `run_state.py` flag 路径注释）。内容锁停机钩子三要素（od-dev-stop-hooks）：
     - 触发定位：`[HOOK-STOP]` 标记 + ts + run_id + 字段 + 画面/actor + 动作组 id + 逻辑写端 evidence + 逻辑值/实读值；
     - 处理步骤：两原因排查——①此前的观察态错了：查 `state/journal.jsonl` 该字段前序写入行（行行自足，含渠道签名与质量元数据）；②逻辑态推算代码错了：按 actor / group_id / logic_evidence 定位写入点修推算。归因一手数据 = journal 行（expected/actual/evidence + 写入后完整 state 快照）；
     - 移除条件：常驻兜底钩子——单次触发只删 flag；差异长期确证属游戏机制性结构 → 走豁免申报进注册表（带 reason），不留开关。
  4. **停机**：`ctx.run_context.stop_running(reason='hook:reconcile_mismatch')`（接收者先例 = 现役 exec_fail 安灯同口；该先例代码随 3.4 删除，接口形态以此处为准）。
- **触发时点语义**：失配写入点即刻触发（stop_running 为协作式，当前节点收尾后外循环退出）——被证伪的逻辑态不再喂下一个决策。

### 2.5 执行失败安灯退役
- **依据**：not_effective（计划花费 > 0 且金差 ≈ 0）= 金字段失配的特例（逻辑扣金、实读未扣 → observe 判失配 → 统一安灯接管；等价性的逻辑写端支撑 = `_advance_gold` 直推容器金账，依据 `cw_exec_state.py`），且用户裁定对账归 game state、执行链不做对账裁决。
- **删除面**：
  - `run_state.py` 整文件（`exec_fail_should_stop` / `write_exec_fail_flag` / flag 路径常量；唯一导入点 = `cw_screen_prep`）；
  - `cw_screen_prep`：`_exec_fail_hook_check`、`_spend_unit_close` 钩子判定块、`_exec_fail_hook_fired`，及购买单元记账段全量（`_spend_unit_open` / `_spend_unit_close` / `_unit_facts` / `_unit_meta` / `_spend_unit_key` / `_spend_unit_seq` / 模块级 `unit_exec_facts_from_receipts`——W3 起唯一现役职责是喂安灯事实，依据方法 docstring 与全消费面 grep）+ `_act_execute_default` OpenShop 分支的单元开合调用 + **`visit_open_shop` 的安灯 gold_open 捕获与执行事实暂存块**；
  - `finalize_buy_phase` 的 `_unit_facts['gold_close']` 回填两行（**金差值双源对拍本体保留**——独立留证面）；
  - **fact_rows 死通道退役**：`ledger.fact_rows` 唯一读端 = 安灯派生（`unit_exec_facts_from_receipts`），退役后成只写不读、无上界的死通道——`ShopLedger.fact_rows` 字段、`note_shop_action_receipt` 的 fact_rows 形参与其调用点、`cw_shop_action_ops` 相关注释一并删。**journal receipts 行与 include_payload 载荷保留**（行行自足的动作留证通道，安灯之外仍辖归因），注释动机从「安灯载体」改归「动作留证」；
  - `telemetry/query.py`：`classify_spend_unit` 与 `plan_gold_flow`（生产唯一消费面 = 退役安灯；`match_archive.py` 仅注释引用）——退役批 grep 复核零消费后删，注释指针改纯语义；
  - 测试面：exec_fail 族与分类器在 sr-od-test 无在册测试（grep 实证），无测试删除面——grep 判据覆盖注释残留（`test_cw_identity_funnel.py` 头注释对 run_state 的引用）。
- **不受影响**：journal receipts 通道（保留，见上）。

### 2.6 武装前置：金失配全模式归因 + 直写端清点
- **辖域**（不止 +2 慢性模式）：
  1. 86 行「逻辑 17 / 实读 19」恒 +2——首位线索 = finalize 对拍注释自认的「收入/连胜金不可观项混入」与免刷 proc（刷新已实证机制，持久锚 = `classify_spend_unit` docstring 的 free_refresh_proc 段；ADR-0456 编号仅存于代码注释引用，decisions/ 无落盘；`free_refresh_balance` 容器字段与 `refresh_free_truth` 真值通道已在）；
  2. 7 行金散失配（+7/−2/±2）；
  3. **write_logic 直写端族时序面清点**：关店金真读以 logic 通道直写、`node_ledger_backfill` 台账权威值直写（旧语义 = 下帧实读观察赢修正）、恢复局 write_logic——武装后这些写端与下帧实读的机制性分歧全部升格停机，逐个定性：确属推算错 = 修；确属「写时点早于游戏落定」的时序差 = 改写端时点或申报豁免。
- **归因手段**：`state/journal.jsonl` 行行自足快照回溯 + 生产缺陷台账行前后文；判读流程与查询工具 = skill `sr-od-currency-war-dev` `references/telemetry-reading.md`（判读流程节 + 遥测查询工具节）。
- **出口三分类**（每条模式必落其一，验收含复现载体复跑）：
  - ①建模补全（逻辑值把该机制算上）——验收 = 复现载体复跑该失配模式零复现（复现载体 = sim 重放该单元序列，或实机局后生产缺陷台账零新增该模式行，按模式可复现性二选一，归因报告钉明选型）；
  - ②结构性申报豁免（确证为游戏机制性差异且建模不可行）——验收 = 豁免条目落地，该模式落 `exempt_mismatch` 行；**豁免条目逐画面申报，禁 `('*', 'gold')` 类字段级通配用于执行敏感字段**（吞「买了没扣钱」类真失败 = §2.2 粒度纪律禁止的后门）；
  - ③识别侧误读（修识别）——验收 = 复现载体复跑零复现。
- **时序**：机制批先行（钩子槽缺省关 = 生产行为零变化），归因批不受时序阻塞；**归因批完成前安灯不装配**。
- **装配后验证期**：武装后实机连跑至少 3 局，停机触发为 0、或每触发均已归因并按出口处置，验证期才算过（实机窗口依赖用户，验收时点可与用户对齐）。

## 3. 关键取舍（备选 + 为何放弃）
1. **判定收口在写入口 vs 各 op 自查**：收口——统一性由唯一门 + 禁旁路守卫保证，新画面自动纳入；op 自查 = 每屏重复实现且必漏新屏。
2. **豁免三维度（画面×字段×逻辑写端）vs 更粗/更细**：字段级吞真执行失败；无写端维度则金字段免刷失配与真点击落空不可分；自由文本条件 = 注册表写代码必腐化——evidence 前缀是声明式签名非代码。
3. **安灯写入点即时触发 vs 外循环轮收口批量查**：即时——证伪态不喂下一个决策；轮收口省注入槽但脏态多活一轮。
4. **精确等值 vs ±容差**：等值——容差洗掉小 bug 信号（旧三流对拍时代的 `tolerance=2` 口径属已退役分类器，不进容器对账）；finalize ±2 对拍是独立留证面不拆除，但其「不可观项」在容器侧走归因建模出口，不走容器容差。
5. **旧安灯删除 vs 双轨保留**：删除——双轨两处停机语义必然漂移；覆盖连续性由「先武装（3.3）后拆旧（3.4）」时序保证。
6. **归因前置 vs 先武装后修**：前置——武装即每局停点（免刷/不可观项是高频机制性失配嫌疑）；机制先行零行为变化，归因不受阻。
7. **观察侧 sig.screen 补齐 vs 豁免退字段级**：补齐——画面名是对账数据的固有语义（journal 归因也要用），且保住按画面治理的粒度；退字段级 = 把「买了没扣钱」类真失败一并豁免。
