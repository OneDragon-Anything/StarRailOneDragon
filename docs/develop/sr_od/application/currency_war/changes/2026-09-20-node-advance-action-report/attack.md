# 设计对抗报告：2026-09-20-node-advance-action-report

> 攻击对象：本目录 design.md（草案）/ landing.md / README.md。
> 规范 = docs/develop/harness/iteration-design.md §7；权威源 = game_state/node-derivation.md、screens/op-layer.md、代码实况（符号锚均在 src/sr_od/application/currency_war/ 下，2026-09-20 工作树）。

## ① 结论

**阻断性发现 2 个 / 非阻断 5 个（应修 3、低 2）**。核三治本结论成立：根因归层（流程层·触发模型因果错位）与权威源一致，E1-E18 逐边在新模型（双门 + 两锚定写端）下均可推进且无双推边——问题不在流转拓扑，而在**效果推进段的数据流接线**（阻断 2）与**两处写点归属的自相矛盾**（阻断 1）。定稿前须先解决两个阻断项。

## ② 逐条发现

### F1（阻断）锚定写端 1 的「家」自相矛盾：§2.4-1 说在漏斗尾段，§2.7-5 说漏斗退出节点域写入

- **位置**：design §2.4 写端 1 / §2.7 行为变化申报 5。
- **攻击**：§2.4-1 明文「干净备战帧：漏斗 `read_game_state` 尾段（现 `observe_screen_context` 备战腿位置改造）→ `observe_node_anchor`」——锚定写端 1 生产挂点在漏斗内。§2.7-5 却申报「recorder 录帧副作用消失（**漏斗退出节点域写入**）」。两句只能有一句成立：
  - 若锚定留在漏斗（§2.4 侧）：`telemetry/cw_match_recorder.py::extract_frame` 仍调 `read_game_state(ctx, img)`（cw_match_recorder.py:80，phase 缺省 None）→ `_phase_screen_context(None,…) → SCREEN_PREP_FRAME`（cw_observation.py:2781-2782）→ 锚定照跑。recorder 录帧仍会写节点域：R==v 同值行、**R>v 时补推并推 hist 水位**——§1 症状 3（录帧改变逻辑态）只是减弱（写入变为观察源），并未「消失」，申报不实。
  - 若漏斗退出节点域写入（§2.7 侧）：生产链路上备战帧锚定**没有任何挂点**（漏斗是备战帧观察的唯一生产通道），观察态门在生产中永远无法回臂，第二次以后的终结动作全部被门挡——方案不可运行。
- **依据**：cw_observation.py:2728-2739（漏斗尾段调 `observe_screen_context`）+ :2781-2782（phase None → 备战帧映射）；cw_match_recorder.py:80；design §2.4/§2.7-5 原文。
- **要求**：定稿前裁决锚定写端 1 的确切位置；若留在漏斗，须改写 §2.7-5（recorder 副作用 = 「推断式推进消失、观察源写入与补推仍在」，并评估 recorder 帧乱序时补推误触发的边界）；若移出漏斗，须给出新挂点（谁在生产备战帧调锚定）。

### F2（阻断）锚定补推（R>v）路径没有效果推进段；report 路径 tick 的 `prep_frame` 实参未定——效果发放丢档/金结算闸语义悬空

- **位置**：design §2.2 处置规则表（R>v 行）/ §2.2 效果计数（尾段迁移）段 / §2.3 锚定可用性边界。
- **攻击**（两叉，同一根）：
  1. §2.2 只把 `tick_effect_boundary` 挂在 `report_node_advance` 通过门后的尾段；锚定 helper 的 R>v 分支（补推：漏上报自愈）推进 `node_ord` + `node_hist_ord`，**不 tick**。而补推恰是设计自己申报的高频自愈路径（§2.3 恢复局锁定臂「由战后备战帧观察锚定补齐」、§2.4-2 补给屏 area miss「走观察补齐」、恢复局 mid-battle 首结算被门挡后的首锚定）。后果：账本 `advance_node` 的去重是**序相等**判（cw_effect_inventory.py:355 `node_ordinal == self._last_tick_node`），补推使序从 N 跳到 N+1 但无 tick，下一次 report 的 tick 直接调 `advance_node(N+2)` —— N+1 这一档 `grant_effect_node_refresh_balance` 永不发放（grant 仅 `advanced=True` 时调用，cw_game_state.py:1343-1345 docstring 自证「每节点恰一次，重复调用即双计」→ 反面 = 跳档即漏发）。搜打撤/加油站/双手狸/本金充裕的每节点免费刷新在该节点凭空少一档——这是策略面可感知的资源损失，§2.7 未申报。
  2. `tick_effect_boundary(gs, *, prep_frame: bool)` 的 `prep_frame` 闸承载金结算时点（「金结算仅备战帧触发，0q/0p/弹窗推进帧递延」，cw_game_state.py:3195-3198 现值语义）。两个触发点（结算确认/补给确认）都不是备战帧；report 尾段调用时 `prep_frame` 传 True 还是 False，design 全文未写。传错即改变金结算时点（§2.7-3 只申报了「金采样=结算真值更准」，没申报闸值）。
- **依据**：cw_game_state.py:3356-3385（tick 本体与 prep_frame 闸）、:1328-1365（grant 语义）、cw_effect_inventory.py:332-357（advance_node 去重）；design §2.2/§2.3/§2.4-2。
- **要求**：定稿前补两件事——①补推路径的效果推进语义（补推后是否补 tick；若不 tick，须申报「自愈节点丢一档 per_node 发放」为接受边界并写进 §2.7）；②report 尾段 tick 的 `prep_frame` 实参值及其金结算后果申报。两条都是实现者无法自行拍板的核心数据流（违反规范「实现者无需再设计」）。

### F3（应修）共存期画像失真：3.3 上线补给屏锚定后，「动作上报被门挡 = 留证噪声」对该窗口不成立

- **位置**：design §2.5 切换纪律段 / landing 3.3、3.5。
- **攻击**：§2.5 称「3.1-3.4 共存期新旧两套并存（旧腿继续驱动，动作上报被门挡 = 留证噪声）」。但 landing 3.3 在切换批（3.5）**之前**就把 `observe_node_anchor` 接进 `CwScreenSupplyNode` 生产观察链。补给锚定一旦把 `node_ord` 写成 observation 态，`supply_confirm` 上报即**通过观察态门**——新模型在 3.3→3.5 窗口内对补给侧部分提前生效（旧腿同时还在跑）。安全性靠 hist 去重（candidate==hist 同序照写）与 `advance_node` 序去重兜底，大概率无双重推进，但：①设计对该混合态零分析零申报；②「门挡留证噪声」作为共存期判读口径在该窗口是错的（留证噪声会被误读为异常）；③3.3 的完成判据（两形态各推进恰一次）在旧腿在场的 harness 里如何隔离验证未说明。切换批 3.5 本身（一次提交原子退役 + 锚定切换）结构上没问题。
- **依据**：landing 3.3 范围②（「CwScreenSupplyNode 观察链接节点条读数 → observe_node_anchor」）、3.5 依赖仅 3.2/3.3；design §2.5 切换纪律段；代码层面门输入 = `node_ord.source`（design §2.2），观察锚定是其唯一生产翻转源。
- **要求**：要么把补给锚定接线挪进 3.5（真·一步切换），要么在 §2.5 申报 3.3-3.5 混合窗的行为画像与判读口径，并在 3.3 判据里加「旧腿在场下恰一次推进」的对照测试。

### F4（应修）BOSS 类型直定「保留半」失去触发通道：`_note_branch_screen('货币战争-BOSS简报')` 退役后 0p 不再进 `observe_screen_context`

- **位置**：design §2.5 退役清单第 3/4 行。
- **攻击**：§2.5 说「BOSS 简报腿 + 幂等锚（序号半部）退役；类型直定半保留（`_write_derived_node_type` boss 分支，简报屏仍是 boss 类型权威）」。实况：boss 类型写点不是独立分支，它住在 `_derive_node_boss_brief` 内部（cw_game_state.py:3503-3505，序号半自己调用 `_write_derived_node_type('boss', target=candidate)`）；而 `observe_screen_context` 收到 `SCREEN_BOSS_BRIEFING` 的唯一生产来源是 `cw_loop.py:1547` 的 `_note_branch_screen('货币战争-BOSS简报')`——同表第 4 行要删的 5 调用点之一。两行一起执行后：0p 画面不再进 `observe_screen_context`，类型直定半**既没有调用点也没有触发通道**，「保留」落空；boss 节点类型将只能依赖链读链（新局首段链缺位 = None 诚实缺位）。E12/S6 的 boss 类型权威主张随之下坠。设计未指明保留半的新挂点与目标序取值（effective？hist？）。
- **依据**：cw_game_state.py:3163-3166（0p 分支触发序号腿）+ :3499-3505（类型写在序号腿内）；cw_loop.py:1547；design §2.5 表。
- **要求**：给出保留半的新触发接线（谁在 0p 采到时、以什么目标序调用类型直定），或显式裁定 boss 类型改由链读链/上报时随 trigger 携带，并同步 E12/S6 论证。

### F5（应修）补给触发点把「转移证据 until」塞进动作 op，与 op-layer §1.2「动作 op 禁做任何验证」相抵触且未申报裁决

- **位置**：design §2.3 触发点 2 / §2.8 取舍一；landing 3.3 范围①；正本更新清单 op-layer 行。
- **攻击**：`CwActionPickSupplyOp` 是注册表动作 op（cw_overlay_pick_action.py:203-255，现役确认链 `round_by_find_and_click_area(..., success_wait=1.5)` 零判效，代码注释自证「零判效」契约）。op-layer §1.2 硬规则：「动作 op 只管机械执行，**禁做任何验证**、禁设验证→重试编排；发出即职责完成，落地判定归观察侧」。设计要求在该 op 确认链上补 until = 下一节点备战锚，且「证据 miss = 不上报」——这是在动作 op 内做转移验证并以验证结果分支上报，直接踩 §1.2。§2.8 引的依据是项目 AGENTS.md §3（画面切换点击带 until）与「既有纪律延伸」，但 AGENTS 是全项目通用层，CW 的 op-layer 是更具体的在册合同，二者冲突时设计必须显式裁决并列入正本更新——清单里 op-layer 行只写「§2 report 族与触发矩阵」，未含 §1.2 契约修订。（结算侧 `CwOpSettleConfirm` 不受此条约束：它是画面框 op 惯例（CwOpOpenShop 族），非注册表动作 op，设计已作区分 ✓。）
- **依据**：op-layer.md §1.2 原文；cw_overlay_pick_action.py:203-255；design §2.3/§2.8；landing 正本更新清单 op-layer 行。
- **要求**：三选一并写明：①until 证据判定移出动作 op（宿主画面 op 重入裁决承载，动作 op 只发确认）；②正本清单扩项申报 op-layer §1.2 对「终结动作上报型 op」的例外条款；③补给上报退回无证据形态、幻影预防只靠源门（须重论证 §2.8 互补论证）。

### F6（低）两处行号锚过期

- **位置**：design §2.3 触发点 2、§2.6。
- **内容**：§2.3 引 `operations/cw_op/cw_overlay_pick_action.py:176` 指称 `CwActionPickSupplyOp`——:176 实际是 `CwActionPickEncounterOp.run` 节点装饰行，`CwActionPickSupplyOp` 类在 :203。§2.6 引「`apply_effect_burst_grant`，采样点 = CwScreenInvestStrategy 确认落地后，`cw_game_state.py:1330` 注」——函数定义在 :1309，:1330 已是 `grant_effect_node_refresh_balance` 的 docstring；调用点实况 = cw_screen_invest_strategy.py:484。依据标注纪律要求锚可用，判读按符号名可恢复，定稿时顺手刷新。（对照：`cw_screen_battle_wait.py:256-290` 白名单、`:219/:230` M39、`cw_loop.py` 1547/1559/1594/1605/1623 五调用点均实测吻合 ✓。）

### F7（低）退役 `_note_branch_screen` 后开局链期间上下文对无写点，与 §2.4「上下文对保持现状」不一致且未申报

- **位置**：design §2.4 末段 / §2.5 退役清单第 4 行 / §2.7。
- **内容**：漏斗只覆盖 prep/shop/battle 三相位（cw_observation.py:2760-2790）；开局链五屏（简报/投资环境/等待1-1/0p/0q）的上下文名唯一写点就是 `_note_branch_screen` 五调用点。3.5 删完后，开局链期间 `prev_screen/current_screen` 零写入——§2.4「保持现状（观察域，供 journal 审计与商店查链）」对开局链段不成立，journal 审计丢开局链上下文行属未申报行为变化（商店查链用 node_path 链，不受影响）。建议：改 §2.4 措辞或保留分支标识写入的去派生化瘦身版，并进 §2.7 申报。

## ③ 规范遵循核对表（iteration-design.md §7 核二）

| 项 | 结果 |
|---|---|
| 总纲四节齐（§0 元信息/§1 问题动机/§2 方案）+ 单文档方案深度 | ✓（§0 含目标指针与状态；单文档申明；§2 达详设深度） |
| 依据就地标注 | 大体 ✓ 且锚绝大多数实测吻合；两处过期（F6）；F1/F2 属「主张与自身方案矛盾/数据流断链」，非单纯缺标注 |
| 实现者无需再设计 | ✗ —— F1（锚定挂点二选一）、F2（补推 tick 与 prep_frame 实参）、F4（boss 类型触发）、F5（动作 op 验证契约）均为实现者必遇且无答案的语义选择 |
| 无过程叙事 | ✓（全文无「本轮/已改」类措辞） |
| landing 阶段小节七件齐 | ✓（3.1-3.7 每节 范围/设计依据/文件面/依赖/优先级/完成判据/验收凭据形式 七件俱全；边界「明确不含」各节均有） |
| 阶段可独立验收 / 判据可验证 | 基本 ✓；3.3 受 F3 影响（混合窗判读口径缺失）；模板项「§12 通用工程门（引用）」未出现在任何阶段判据（各阶段以 ruff/pytest 内联替代；iteration-design.md 自身无 §12 节，该模板行指向的外部正本不明，记录备查，不单独立案） |
| 固定末阶段 = 正本更新 + 清单 | ✓（3.7 + 清单八条） |
| README 只串文档记进度 | ✓（文档清单/进度四行，与 landing 阶段数 7 一致） |

## ④ 全量同步复查结果（design ↔ landing ↔ README ↔ 权威源/文件面）

- **design → node-derivation.md 引用锚**：§3.1 全景图 / §3.2 坐标系与 §3.2-7 字段层次 / §3.3 定义基准与规则三 / §3.6 S1-S10 / §5-③.4 漂移信息项 / §④-C V3 补给屏节点条——全部存在且 design 的转述属实（含「四腿全 write_logic 禁 observe 直写」「守卫族漂移与级联双推进两次事故」「R3 勘误：快弹窗形态备战帧可零采样」）✓。
- **design → 代码符号描述**：生产写点两处远端（cw_observation.py:2736 + cw_loop 五调用点）、弹窗腿四成员中前三类生产无写点（漏斗仅映射 商店面板/备战/战斗三态，cw_observation.py:2781-2789；五分支写点全为守卫族/开局链成员）、三屏类型直定生产不落账（`SCREEN_NODE_TYPE_DIRECT` 触发前提 = observe_screen_context 收到该屏名，生产无此输入）、白名单内容（:260-267 含备战/补给/遭遇/投资策略/BOSS简报锚 + 位面过渡 OCR）、M39 长按（:219/:230-233）——全部与代码吻合 ✓。
- **landing → design 引用锚**：3.1→§2.2/§2.3、3.2→§2.3 触发点1、3.3→§2.3 触发点2/§2.4 写端2、3.4→§2.6、3.5→§2.5、3.6→§2.1-§2.4、3.7→清单——全部存在 ✓。
- **文件面真实路径**：`kernel/cw_game_state.py`、`operations/cw_op/cw_op_settle_confirm.py`（新建）、`operations/cw_screen/cw_screen_battle_wait.py`、`operations/cw_op/cw_overlay_pick_action.py`、`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_screen_report/supply_node.py`、`obs/cw_observation.py`、`operations/cw_loop.py`——全部在库/可新建 ✓。
- **正本更新清单目标**：node-derivation.md / fields.md / effect-domain.md / flow/README.md / flow/outer_loop.md / flow/action_exec.md / screens/op-layer.md 均在库 ✓；`docs/game/currency_war/research/` 由 3.4 新建（现仅 README.md，属创建非失锚）✓。清单遗漏项：op-layer §1.2 契约修订（F5）、op-layer §6「节点推进权威 = 统一 state 派生规则」句随触发模型换代的改写（清单只列 §2）——随 F5/正本批补。
- **README**：进度与 landing 阶段数一致（0/7）✓；状态「草案 + 设计对抗进行中」符合生命周期 ✓。

## ⑤ 核三附记（治本与逐边）

- §1 归层成立：症状 1-4 共同根 = 「因果（终结动作）被建模成观察推断量」，与 node-derivation R3/R3.1/R4 修订链（守卫族漂移、级联双推、渲染序≠采样序三次实证事故）互证；§2 以换触发模型 + 整体退役四腿/守卫族/幂等锚回应，是根修不是症状贴膏，且按 §1.1 外溢纪律把坐标系漂移/效果域 M3/类型派生本体排除并逐条指认归属 ✓。
- E1-E18 逐边新模型走查：E1/E2/E3 零推进 ✓；E4 观察建 1 ✓；E5/E6/E16/E17/E18 段内零 ✓；E7/E8 结算确认上报（白名单含遭遇/投资策略/补给/BOSS简报锚，快弹窗形态证据即弹窗本身，「先推进后选卡」结构性成立）✓；E9 R==v 翻锚定 ✓；E10 两形态（divert 备战锚定 / 自动弹补给屏锚定）✓；E11 until 备战锚 + 补推自愈 ✓（效果侧见 F2）；E12 奖励关确认→(p,9)，公式承载 ✓（类型侧见 F4）；E13 boss 确认→(plane+1,1)=effective+1，位面过渡 OCR 在白名单内作证据 ✓；E14 恢复局首锚定/补推 ✓；E15 战败不建 op ✓。未发现新模型下推不动或双推的边。S1-S10 同源结论一致。
