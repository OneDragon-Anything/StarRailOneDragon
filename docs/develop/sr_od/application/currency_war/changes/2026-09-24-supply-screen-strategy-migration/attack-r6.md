# 设计对抗报告 · 第 6 轮（attack-r6）

> 审查日期 2026-09-24。无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态）。判据源自取并全部直调复核，未采信任何前轮报告结论。规范源：docs/develop/harness/iteration-design.md（四硬规则/§7 三核/阶段七件/正本清单）、.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md（§1 零调参/§4 验证阶梯/§5 单帧测试/§6 对抗纪律）、strategy-docs/00_framework.md 与 01_math_framework.md（宪法六条/数字三形态/未证即退役）、项目 AGENTS.md。

## 发现清单

### R6-1 [中] `cw_replay --diff` 豁免申报引用了不存在的文件路径：`tools/cw/cw_replay.py` 全仓不存在（核一·引用锚存在性 + 核二·硬规则 4）
- **位置**：design.md:90（§2.6 豁免申报行）。
- **发现**：申报写「该旗标已随切源退役（`tools/cw/cw_replay.py:10-12`）」。直调 `tools/cw/` 全目录清单与全仓 grep：`tools/cw/cw_replay.py` 不存在（tools/cw/ 下只有 replay_to_md.py 等 24 个脚本）；`--diff` 退役面声明的实址 = `src/sr_od/application/currency_war/sim/cw_replay.py:10-12`（模块头「退役面 = _rebuild_state/_restore_session/--diff 分歧对比/…」逐字在册），且现役用法只有 `--run/--rounds`（:14-17）。**语义主张本身核实成立**（旗标确已退役、现役回放面只辖商店决策、不辖补给），错的只是路径。这正是 iteration-design 硬规则 4 卡点「定稿前逐一核设计引用的每个符号/路径存在性」的目标错误类。
- **修正方向**：路径改 `sim/cw_replay.py:10-12`（或全限定 `src/sr_od/application/currency_war/sim/cw_replay.py:10-12`）。

### R6-2 [中] 「与接线同一 commit 原子切换」与 landing 两阶段结构 + 通用工程门（含逐阶段提交）互相矛盾（核一·landing 与设计一致性 + 核二·硬规则 4/阶段粒度）
- **位置**：design.md:76（§2.6 标题「删除面（与接线同一 commit 原子切换，新旧不并存）」）；landing.md:3（通用工程门定义含「提交后 git show --stat 复核」）、:6/:13（3.1 完成判据引用通用工程门）、:17（3.2 范围重申「与 3.1 同一 commit 原子切换」）、:20（3.2 依赖 3.1）。
- **发现**：通用工程门被 3.1 与 3.2 各自引用为完成判据，而门内含提交动作。若 worker 按判据执行，3.1 完成时必然产生一次提交——此刻 kernel 旧 `decide_supply` 仍在（删除归 3.2）= design 明文禁止的「新旧并存」提交态；若 worker 为守原子切换而推迟 3.1 的提交，则 3.1 无法按其完成判据（含通用工程门）独立验收，与 iteration-design §3.1「阶段 = 一个可独立派工、独立验收的实施批；判据依赖另一阶段未完成部分 = 划分不当」冲突。两条门必破其一，实现者撞上后只能停手提请修订。
- **修正方向**：二选一——①合并 3.1+3.2 为单阶段（「同一 commit」语义自洽，文件面并集、依赖不变）；②保留两阶段，但 3.1 完成判据显式豁免通用工程门的「提交」步（改为「工作区就绪 + ruff/测试全绿」，提交动作移至 3.2 与删除面一并执行，3.2 的 `git show --stat` 复核显式覆盖两阶段申报面），并在 3.1 范围句注明「本阶段交付态 = 未提交工作区，入库随 3.2 原子切换」。

### R6-3 [低] 三处行号锚漂移 + 一处标签失准（直调核实；值对标签错轻症）
- **位置与发现**：
  1. design.md:66（§2.4）「flow.py:545-546 的 refresh_used 预计算随迁删除」——实址 :544-545（:544 = `_left = self.gs.supply_refresh_left.value`，:545 = `refresh_used = ...`；:546 = `_consume_prep_direction_frame()` 入口内务行，不属删除面）。
  2. design.md:33（§2.1）「容器 gs.supply payload（cw_game_state.py:211 域版本 2）」——`'supply': 2` 条目实址 :209-210（:211 = `'event_choices': 1` 行）；同句 TYPE_CHECKING `:114` 锚正确。
  3. design.md:34/:80「cw_vocab.py:728/916（「替代 SupplyPick」表述）」——第二处「替代 SupplyPick.refresh 旗标」实址 :915（:916 为该 docstring 续行「发射后交回重入型…」）。
  4. design.md:77「EventPick 联合中该位（:1003/:1007）」——:1007 是 `EventPick` 类型联合正确；:1003 实为 `EVENT_PICK_TYPES` 运行时登记元组（非联合；两行删除意图均正确，标签以「登记面 + 联合」表述更准）。
- **修正方向**：落批前按实址校正三处行号；:1003 措辞改「`EVENT_PICK_TYPES` 登记元组 + `EventPick` 联合中该位」。

### R6-4 [低] 第 3 级排序未指明直调 `pick_equipment`，存在落「第二套打分」的实现分叉（核一·实现者无需再设计 + 核二·所引模块自身禁令）
- **位置**：design.md:53-57（§2.2 第 3 级）；关联依据 cw_equip_value.py:12-13（模块头「`equip_tier`/`pick_equipment`：通用选装入口……『候选全部为装备的多选一』场景禁第二套打分」）、:192-210（`pick_equipment` = (tier, base) 字典序 argmax、并列取输入序先者——与设计 :57 的排序语义逐位同构）。
- **发现**：设计只写「复用共享序数机器 `equip_tier`」+ 排序语义（tier 高者先 → 通用值高者先 → 输入序先），未指明执行载体。supply 第 3 级恰是该模块头点名的「候选全部为装备的多选一」场景（候选项 equip 名序列的多选一），供给侧 `pick_equipment([o.equip for o in 候选], key_equips=…, owned_spare=…, owned_total=…)` 可整体直调；照字面（只复用 `equip_tier`）实现会自写一套同语义 argmax 循环——§2.8 引「禁第二套」裁定作取舍依据的同一批，落在实现指令上却留了第二套的口子。
- **修正方向**：§2.2 第 3 级补一句「排序执行 = `cw_equip_value.pick_equipment` 直调（names = 候选项 equip 字段序列，idx 同序回映候选）」，或显式申报不直调的理由。

### R6-5 [低] 「空串 → None + 告警」与所引 decide_box_card 先例行为不符（核一·依据标注与先例一致性）
- **位置**：design.md:47（§2.2 签名注「空串/解析失败按未锁口径 None + 告警哨兵」）、:73（§2.5 同口径「空串/失败 → None + 告警」）；先例实码 flow.py:708-717。
- **发现**：先例中空串（falsy）走 `if locked:` 之外**不产生任何告警**，仅「非空但 `get_comp` 解析失败」才 `log.warning`。设计两处把「空串/解析失败」合并挂「+ 告警」，照字面实现会对空串也发告警（与先例行为分叉），照先例实现则设计表述失真——语义分叉无唯一答案。
- **修正方向**：改述为「空串按未锁口径（无告警）；非空但解析失败按未锁口径 + 告警哨兵（照先例）」。

### R6-6 [低] 跨批协调缺 cw_events.py 代码锚漂移申报（核一·边界完整性）
- **位置**：design.md:104（§2.7 跨批协调）；关联 design.md:77-80（§2.6 全部 cw_events 代码锚）；在飞 29 批 landing.md:33（跨批状态行）。
- **发现**：29 批 3.2 将删除 `decide_event` 全段（约 270 行，位于本批删除面之前）+ `is_economy_engine` 迁位，29 批 landing 已明写「本批（29）落地后 supply 批 design 行号锚 [:585-596/:616-647 等] 全数漂移——该批行号锚候本批落地后重核」；但本批 §2.7 的批序纪律只把「行号锚以落批时实址为准」写在**文档锚**清单（13 `:20`/`:40`、08 `:19`、16 `:74`、25 `:3-4`/`:11`/`:18`）上，cw_events.py 只以「模块 docstring」身份入共享编辑面清单——§2.6 的 8 处代码锚（`:583`/`:585-596`/`:599-605`/`:609-612`/`:616-647`/`:786`/`:1003`/`:1007`）不在重核申报内。删除执行按符号名定位故误删风险低，但「全量同步复查」申报面不完整。
- **修正方向**：§2.7 批序纪律补一句「29 批先落则本批 §2.6 全部 cw_events 行号锚按符号名（decide_supply/SupplyPick/段头注/`_equip_value`/EVENT_PICK_TYPES/EventPick/planner 消费点）重定位后执行」。

## 零发现面（实际攻击过且对得上的面）

- **代码锚直调（~40 处全对上）**：cw_events.py `:1`/`:583`/`:585-596`/`:599-605`/`:609-612`/`:616-647`（只消费 equip/has_diamond，char 全程未触；`:627-628` 空帧 idx=0；`:633-635` 无钻必刷；`:637`/`:641-642` key_fit set 隶属 +10）/`:786`（`_equip_value` 唯一保留消费点 = planner 装备档回落）/`:1002-1007`（登记面摘位安全——全仓 grep 零外部消费）；cw_equip_value.py `:36`（表自注）/`:42-80`（表本体）/`:163-189`（tier 3/2/1/0 语义、key 可含重复按 count 计需、近兑现按备用账）；cw_node_obs.py `:21`/`:206`/`:215`（三钻集合）；cw_game_state.py `:114`（TYPE_CHECKING）/`:2124`（board = 上阵羁绊计数派生量、键 = 羁绊名、禁双写——§2.3「禁双写」声明属实）/`:2209-2229`（溢出位单槽双写端）/`:3645-3663`（deployed_rows_of 行域二元组、bench_units_of 槽序 Unit 读口）；cw_merge_simulate.py `:88-119`（条目身份协议 fail-closed——「直传二元组静默跳过」声明属实）/`:337`（同名同星 ≥3 合一）/`:424-433`（same_star_count 全场域单一源）；cw_intention.py `:2073-2079`（降格路径清 locked_comp）；flow.py `:326-353`（锁线 comp 物化链/P1 伪 comp 臂/target_comp 写入）/`:505-552`（invest_env 意向解析先例 + 现役 decide_supply 闸前移）/`:692-739`（decide_box_card：get_comp 失败告警、两账构造、deployed 展平先例）；invest_env.py `:388-401`（闸内嵌 + None fail-closed 先例）；cw_survey19_hooks.py `:1-8`/`:46-56`（唯一 import 点 = cw_events.py:552 只取 encounter_tier_score，src+测试仓 grep 零消费——死代码判定成立）；cw_vocab.py `:728`/`:915`；cw_pick_supply_action.py `:37`；cw_screen_report/supply_node.py `:16`/`:41`；cw_screen_supply_node.py `:8-14`/`:39-40`（「sim 接线未接」陈旧注判定成立——`:189` sim_or_live_observation 与 `:275` 真调在产）/`:242-245`/`:272-280`；cw_sim_backend.py `:78`/`:573-585`（恒置恰一带钻槽——sim 盲区申报的机制核实成立：两侧都恒选钻、刷新两侧都永不触发）；cw_equipment_data.py `:53`（财富宝钻 effect 原文逐字）/:64-65；cw_effect_inventory.py `:1502-1505`（席满拒落零写）；kernel/cw_action_report/pick_supply.py `:48`（入席恒 1★ 先验）；cw_comps.py `:102-112`（core_chars/shared_chars/transition_chars 边界）；sim/checks/ledger.py 全仓零命中（16 号稿死引用「清理」判定成立）；cw_strategy.py `:172-175`（ABC 方法名保留 → 测试 stub 存活声明成立）。
- **测试面**：test_cw_unified_action_4.py `:27-33`/`:303` 恰此两处随删面；strategy 级 stub 两处（`:47`/`:61`、`:125`）桩在 flow 方法名——「不随删」声明成立；「在册无 kernel 侧 supply 决策专项测试」经双仓 grep 核实属实。
- **sim/验证面**：sim_backend_runner.py `:314-381` 真 CwLoop + 真 mandate_v1 装配属实；sim 可观测性申报（机械可达但被占位分布吞掉、非结构性盲区）机制链核实成立；验收线保全申报（proofs/batch_stats 无以补给选择为判据面的在册线）抽样复核成立；实机锚点①-⑤事前写定与行为申报①-⑤一一对应。
- **文档面**：25 号稿 `:3`/`:11`/`:18`（三锚 + 拆分头注先例 `:3-4`；尾部无其他补给残留，landing 3.3「仅剩拆分头注 1 行」判据可满足）；13 号稿 `:20`/`:40`（「组件/成品需求」描述与实码不符判定属实）/:11（OCR 未就绪纪律）/`:18`（改指先例）；08 号稿 `:19`（E4 行 P42 component_demand/hoard_gaps + P40 变体②口径逐字）；16 号稿 `:74`（挂账在册、死引用替锚口径正确）；strategy-docs README §2（分篇表末篇 28）/§3（kernel 存量 = 待迁）；29 号稿占用声明（invest-strategy design `:5`「本批新建 29 号稿」）与承接声明（env 批 design `:18`、投资策略批 design `:23`「明确不解决」均登记补给为后续批）；跨批共享编辑面 6 处（25/13/README §2/16/08 E2+E15/cw_events 模块头）与 29 批 landing 逐一互证；math_proofs 索引 P40（变体②在册）/P42（🔴 待标定 = λ 流/partner 到位率）/P81/P97 行与本批涉猎面一致，本批不声称期望最优。
- **宪法/规范面**：宪法五（SupplyOption 留 kernel = 观察载荷契约；EQUIP_GENERIC_VALUE/equip_tier 所有权申报「待迁策略内容、本批仅消费」与 00_framework §1.5 判据线一致）；宪法六（新画面文件 + 30 号稿一一对应；迁移逐画面、批内不夹带）；零调参（新判据零新自由参数；EQUIP_GENERIC_VALUE 按 16 号稿在册处置降格 tier 内定序常数、表值零变化——「档位实现常数」形态与 decide_planner 在册先例同构）；未证即退役（无第三态挂账；+10 隶属判据物理删除）；AGENTS.md 双层文档流/引用寿命（无代码或正本引 changes/ 的长期引用）；iteration-design 结构（§0-§2 齐备、landing 阶段七件齐、README 构成合规、无过程叙事——除 R6-2/R6-6 外全量同步成立）；核三治本（§1 归层成立：分层语义 + 语义双层；§2 修的是根——迁移治所有权、改形治价值模型缺轴、刷新收窄治无质量条件闸；逐画面节奏 = 宪法六明文，非逐件症状修补）。
