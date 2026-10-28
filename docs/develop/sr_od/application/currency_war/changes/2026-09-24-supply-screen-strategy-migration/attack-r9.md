# 设计对抗报告 · 第 9 轮（attack-r9）

> 审查日期 2026-09-24。无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态，r8 修订后文本）。判据源自取并全部直调复核，未采信任何前轮报告结论。规范源：docs/develop/harness/iteration-design.md（§3 七件套/§5 四硬规则/§7 三核）、.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md（§1 零调参/未证即退役、§4 验证阶梯与可观测性声明、§5 单帧测试、§6 对抗纪律）、strategy-docs/00_framework.md（宪法五/六）、strategy-docs/01_math_framework.md、项目 AGENTS.md。行号锚按任务纪律以符号锚优先，±3 漂移且语义锚成立者不登记。sr-od-test 为 gitignore 独立仓，grep 在该目录显式补扫。

## 发现清单

### R9-1 [中] 30 号稿「裁定登记」内容清单缺刷新结构裁定及其原文收载，§2.4「收原文」承诺未落进 §2.7 内容规格与 landing 3.3 完成判据（核一·篇内一致性 + 核二·硬规则 4 全量同步 + R8-2 吸收不彻底）
- **位置**：design.md:97（§2.7「裁定登记（三级优先 / 终局名单 / 溢出席，用户 2026-09-24）」）与 landing.md:35（3.3 完成判据「裁定登记（三级优先/终局名单/溢出席，用户 2026-09-24）」同枚举）；对照 design.md:7（§0 裁定指针「选卡三级优先**与刷新「三空才刷」结构**：用户裁定 2026-09-24」）、design.md:68（§2.4「此解读**随 30 号稿裁定登记收原文**、属待用户确认面」）。
- **发现**：①§0 把「三级优先」与「刷新三空才刷结构」并列为同一用户裁定指针的两半，§2.7/landing 3.3 给 30 号稿的裁定登记枚举只剩三项，刷新结构裁定从内容规格中消失——两处对同一裁定的覆盖面不一致。②R8-2 的修正方向②明确要求「30 号稿裁定登记收录裁定原文（或向用户确认『末级』定义）」，本稿 §2.4 也已按此承诺「随 30 号稿裁定登记收原文」；但承载该承诺的落点（§2.7 内容清单、landing 3.3 验收判据）都没有把裁定原文列入——实现者照 landing 3.3 的字面清单交付 30 号稿时，「存在任一非末级项 = 值得拿」的裁定原文与刷新结构裁定将无处落位，§2.4 申报的「待用户确认面」失去可对账的裁定锚，R8-2 要求的可审计性在验收链上断开。
- **修正方向**：design.md:97 与 landing.md:35 的裁定登记枚举补入「刷新『三空才刷』结构（含『存在任一非末级项 = 值得拿』裁定原文，末级定义待用户确认面）」，或显式改述「裁定登记收录 §0 所列 2026-09-24 裁定全集及原文」。

### R9-2 [低] `cw_screen_supply_node.py:18-19` 的「重调一次决策按原评分选」陈旧句在 `:8-14` 锚外，未入注释收口「已知点全列」（核一·边界完整性 + 核二·硬规则 4；R8-5 同类第二处）
- **位置**：design.md:80（收口清单对 `cw_screen_supply_node.py` 只锚 `:8-14`/`:242-245`/`:39-40`/`:272-280`）；对照 cw_screen_supply_node.py:18-19（模块 docstring 续段「剩余 ≤0 或 None = 拒绝 → **重调一次决策按原评分选**(单轮内有界)」）。
- **发现**：该句与 ：272-280 内联注同源同病——闸内嵌后「按原评分选」分支不可达（重调同输入同输出仍返 Suggestion → 零点击，本稿 §2.4 自己的推演），且 kernel 判据随批消失后句子双重过期。其字面行号（18-19）落在 `:8-14` 锚界之外，「已知点全列」的申报被同一模块内的另一处陈旧句证伪（R8-5 对 SupplyOption docstring 的同类判定先例在册）。末阶段全仓复扫可兜底，但申报面完整性同 R8-5 判例应补。
- **修正方向**：design.md:80 的该文件锚由 `:8-14` 扩为 `:8-20`（或补 `:18-19`），改写口径同 ：272-280（新闸语义）。

### R9-3 [低] §2.1 `SupplyPick` 引用面枚举漏 `cw_pick_supply_action.py:37` docstring 提及，「消费 = …」全称枚举不完备（核一·依据标注精确性）
- **位置**：design.md:34（「src 仓内无外部类型 import（消费 = `cw_events` 内部 `EVENT_PICK_TYPES` 元组与 `EventPick` 联合别名 + flow 鸭子式字段消费 + `cw_vocab.py:728/915` docstring 提及）」）；对照 cw_pick_supply_action.py:37（「刷新链 = ``SupplyPick.refresh`` 决策的执行半」——src 内第三处 docstring 提及）。
- **发现**：src 仓内 `SupplyPick` 的 docstring 提及共两处（cw_vocab:728/915、cw_pick_supply_action:37，全仓 grep 复核），枚举只收 cw_vocab 一处、漏 cw_pick_supply_action 一处——而后者恰在 §2.6 收口清单内，说明该引用是已知面，§2.1 的「消费 = …」全称枚举却未含。「无外部类型 import」的承重结论不受影响（该处确非类型 import），失真在枚举自称完备。
- **修正方向**：design.md:34 枚举补「+ `cw_pick_supply_action.py:37` docstring 提及」（或改述为「docstring 提及见 §2.6 收口清单」）。

### R9-4 [低] 3.2 文件面未并入 3.1 交付文件，而「入库面 = 申报面」复核恰在 3.2 执行，复核对照物存在解析歧义（核一·landing 阶段可验收性 + 核二·硬规则 4）
- **位置**：landing.md:19（3.2 文件面只列 kernel/operations/obs 删除收口面 + sr-od-test 旧测试，不含 3.1 交付件）；对照 landing.md:6（3.1「通用工程门的提交/复核两项由 3.2 承接」）与 landing.md:3/26（通用工程门「提交后 `git show --stat` 复核入库面 = 申报面」在 3.2 执行）。
- **发现**：3.1 不单独 commit，其交付件（`strategies/impl/mandate_v1/supply.py`、`strategies/impl/flow.py`、`test_cw_supply_decision.py`）随 3.2 一并入库——3.2 的提交入库面 = 3.1 ∪ 3.2 文件集，而 3.2 文件面按「本阶段允许动的文件」口径只列了自己的编辑面。执行者照 3.2 完成判据做 `git show --stat` 对照时，申报面取「3.2 文件面」则必现集合外文件、取「3.1 ∪ 3.2」又无一处明文给出并集——歧义可经阅读 3.1 豁免注化解，但判据本身未自足。
- **修正方向**：landing.md:19 补一句「本阶段 commit 面 = 3.1 交付件（见 3.1 文件面）∪ 本表；`git show --stat` 复核对照两者并集」。

### R9-5 [低] 两账构造（spare + 行域/备战席穿戴账）将在 `flow.decide_box_card` 与 `supply.decide` 出现第二份逐字平移副本，抽离取舍未申报（核三·跨件半问 + 宪法六共用判据精神）
- **位置**：design.md:56（「`supply.decide` 内自 gs 构造（gs 为纯函数输入，同口径同源）」）；对照 flow.py:718-739（decide_box_card 现役 inline 构造，无共享读口）；design.md:107-111（§2.8 关键取舍无此条目）。
- **发现**：「spare = gs.equips；worn = 行域展平 ∪ 备战席成员 equips 透传」的账构造约定，本批后在策略层存在两个代码落点（box 卡、补给），两份 inline 实现无单一源约束，未来任一侧加过滤/口径修订（如占位件排除、穿戴门）即静默漂移。§2.8 只申报了「复用 equip_tier」取舍，未申报「账构造 inline 重复 vs 抽共享读口」的取舍与理由；§2.2「同口径同源」的「同源」指同一 gs 输入，不构成防漂移机制。这是同族构造第二次出现（第一次 = decide_box_card），按跨件半问应至少显式登记取舍或给出抽离路径（如 kernel 侧 `worn_equips_of(gs)` 读口两处共消费）。
- **修正方向**：二选一并落稿——①§2.8 增补一条：「两账构造在 box/supply 两处 inline 重复，抽离挂账（触发条件 = 第三消费方出现或任一侧口径修订）」；②本批直接抽 kernel 读口（如 `cw_game_state.worn_equips_of`），box/supply 共消费，box 侧行为零变化纯重构。

## 实际攻击过的面清单（全部直调复核，值/锚逐一对源）

1. **三份对象全文精读 + 三向同步复查**：design §0-§2.8 / landing 3.1-3.4+末阶段+正本清单 / README 文档-进度，引用锚存在性、判据同步、文件面真实路径、正本清单完备（正本清单 8 项与 §2.7 逐一互核、30 号稿双列合法）。
2. **规范对照**：iteration-design（阶段七件套逐阶段清点、无详设合法性、README 模板、§1.1 迭代边界、硬规则 1-4）；strategy-work §1（新判据零自由参数、+10 死、通用值表保留 = 16 号稿在册处置 + §2.2 所有权申报、带钻支配未证边界申报）、§4（sim 可观测性声明含占位分布盲区申报、实机锚事前写定、锚点没中处置、验收线保全三入口）、§5（单帧测试 9 项与 §2.2-§2.5 逐条映射、测试语义不校验牌面）、§6（对抗纪律、prereg 保全）；AGENTS.md 文档/测试/提交规范。
3. **kernel 码点直调**：cw_events.py :1/:552/:583/:585-596/:599-605/:609-612/:616-647（只消费 equip/has_diamond；:627-628 空帧；:633-635 无钻必刷；:637/:641-642 key_fit +10）/:786（`_equip_value` planner 保留消费）/:1002-1007（登记面）；cw_equip_value.py :1（「禁第二套打分」裁定）/:36/:42-80/:163-189（tier 3/2/1/0、key 可含重复按 count 计需、近兑现备用账）/:192-210（(tier, base) 字典序 argmax、并列取输入序先——与 §2.2 排序语义逐位同构）；cw_survey19_hooks.py :1-8/:46-56；cw_comps.py :102-112（core/shared/transition/key_equips）；get_comp :1178-1183（缺名 None）。
4. **kernel 其余**：cw_game_state.py（:109-115 TYPE_CHECKING、:209 supply 域版本 2、:614-616 payload、:2146 supply_refresh_left、:2283 supply 字段、:2210-2229 溢出位单槽、:3645-3663 `deployed_rows_of` 行域二元组/`bench_units_of` Unit 读口）；cw_intention.py :1123-1194（pair_target_comp 伪 comp 构造未传 key_equips → 恒空，申报②⑤前提成立）、:2073-2079（降格清 locked_comp）；cw_merge_simulate.py :93-119（`_entry_identity` 非 Unit/BenchSlot → None 静默跳过，直传二元组漏计机制成立）/:337（同名同星 ≥3 合一）/:424-433（same_star_count 全场域）；cw_effect_inventory.py :1463-1513（席满拒落零写）；cw_action_report/pick_supply.py :48-50/:79-84（恒 1★、单位入账分支经 grant_bench_unit_cascade）；cw_vocab.py :728/:915；cw_screen_report/supply_node.py :16/:41/:29-37（列序 = 画面物理列序）；cw_node_obs.py :21/:206/:215（三钻集）。
5. **策略层/sim/测试**：flow.py :326-353（锁线物化链、P1 伪 comp 臂）、:515-518（ist 同源先例）、:537-552（现役闸前移 + 内务 ：546）、:692-739（decide_box_card 三先例：get_comp 失败告警/两账构造/`*_wf, *_wb` 展平）；cw_strategy.py :173（ABC 方法名保留）；invest_env.py :375-401（闸内嵌 None fail-closed 先例）；cw_sim_backend.py :75-79/:573-585（每帧恰一带钻槽 → 新旧恒选钻、刷新两侧永不触发、sim 读数恰同申报成立）；sim/cw_replay.py :10-12（--diff 退役、回放只辖商店）；sim_backend_runner.py :314-381（真 CwLoop + 真 mandate_v1 装配）；test_cw_unified_action_4.py :27-33/:303；test_cw_obs_arch_event_screens_step3.py :47/:61（stub 以方法名挂接，flow 方法名保留后继续有效）；test_cw_supply_pick_immediate_report.py :125；kernel 侧 supply 决策专项测试零在册（双仓 grep 复核，sr-od-test 显式补扫）；supply_reroll_decision 双仓零消费、唯一 import 点 cw_events:552 只取 encounter_tier_score（死代码判定复核成立）；sim/checks/ledger.py 全仓零命中（sim/ 目录 glob 无 checks 子树）。
6. **文档锚直调**：25 号稿 :3-4/:11/:18（族清单 11 屏逐屏清点 ✓）；13 号稿 :11（§0 fallback 纪律字面辖域「接口级 idx=0 兜底」——§2.2 精神引用 + 偏离显式申报合格）/:18（decide_invest_env 改指先例）/:20/:40；08 号稿 :19（P42 component_demand/hoard_gaps + P40 变体②、非 P81 辖域口径逐字）；16 号稿 :74（挂账在册、死引用 `cw_events.py:293` 与 `sim/checks/ledger.py:970/1035`、替锚口径）；strategy-docs README §2（末篇 28、30 空闲）/§3（kernel 存量 = 待迁）；screens/supply.md :12/:33/:40/:63/:80/:88；docs/game/screens 两份 :19/:32/:37/:39/:57；decide_supply 全仓指针面清点（src 6 文件 + 正本 5 文件 + flow/README.md:81 契约方法名指称，对照收口清单与 3.3 词表）。
7. **命题索引**：math_proofs P40（变体①-⑩在册）/P42（🔴 待标定 = λ 流/partner 到位率，与「E4 derive 待标定」一致）/P81（限投资策略屏逐卡刷新，本批不消费）/P97 行。
8. **同构先例与在飞批**：env 批 design §1「明确不解决」登记补给迁移（:18）；29 批 design :5（29 号稿占用）/:23（同登记）、29 批 landing :32-33（decide_event 约 270 行删除、13 号稿增补共用判据节、sim-redesign 改指先例、本批行号锚重核义务——§2.7 跨批协调表述逐条对上）；8 处共享编辑面逐处核实（25/13/README §2/16/08[E2、E15 vs 本批 E4]/cw_events 模块 docstring/flow.py/cw_vocab.py）；sim-redesign design :70/:104/:267 三处复用面声明（R8-1 修正后日期与锚复核成立）；chain-observation landing 通用工程门自包含形态（本 landing 逐字同构）；SKILL.md 测试分层 L1 口径（landing 命令与单一源一致，非第二源）。
9. **验收线保全抽扫**：.debug/progress 全树（25 迭代目录）`补给|supply` 命中逐类清点——无任何以补给选择为判据面的在册验收线（命中均为失活线史档/上报链/模板/字段面）；math_proofs 无补给判据节。
10. **逐轮吸收复核**：R8 六项（R8-1 日期+锚、R8-2 显式解读降格+锚③改写、R8-3 §2.1 符号名、R8-4 两处引用改述、R8-5 收口清单补 ：588-592、R8-6 :74 重写映射）逐条验证已吸收；README 计数复核（第 1-7 轮 16+7+8+7+6+6+8 = 58 ✓、第 8 轮 高 0/中 2/低 4 ✓、第 6 轮 3 项经第 7 轮补课 = R6-3 两项 + R6-5 ✓）；硬规则 3（design/landing 无「第 N 轮/已改」过程叙事）。
11. **篇内一致性专项**：decide 签名与 §2.5 flow 接线/landing 3.1 范围三方一致；两账口径 §2.2-§2.5 多点对齐；闸语义 §2.4/§2.6/landing ⑧ 与 op 逐分支推演（闸内嵌后对照闸唯一触发面 = 锚点缺、重调零点击、op 层零行为改动）；空帧/P1 帧/降格帧/席满帧口径 §2.2/§2.4/§2.5/§2.6 与申报①-⑤、锚①-⑤、单帧测试①-⑨ 四方互核。
12. **核三治本**：归层（分层语义 + 语义）成立；迁移 + 模型重建修的是根；逐画面推进 = 宪法六明定节奏非逐件症状修；E4 derive/数据批/augment 改写面/sim 真实池四类挂账分流清楚，无范围外溢混入。

## 结论

5 项发现（中 1 / 低 4）。中级 1 项为 R8-2 吸收链在 30 号稿内容规格与 landing 验收判据上的断点（裁定原文收载承诺未落清单）；低级 4 项为收口清单/枚举完备性与阶段交接判据精度。设计主体（迁移结构、三级字典序、闸内嵌、删除面、测试面、验证申报、跨批协调）经全量直调复核无新增实质缺陷；r8 六项吸收全部到位。
