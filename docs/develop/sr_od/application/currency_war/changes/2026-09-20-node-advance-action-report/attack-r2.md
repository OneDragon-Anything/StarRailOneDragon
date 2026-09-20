# 设计对抗报告·第二轮（核一·无前提专攻）

> 攻击对象：本目录 design.md（第一轮修订版）/ landing.md / README.md；规范 = docs/develop/harness/iteration-design.md §7 核一。
> 权威源 = game_state/node-derivation.md、screens/op-layer.md、game_state/journal.md 载体面、代码实况（符号锚均在 `src/sr_od/application/currency_war/` 下，2026-09-20 工作树，逐处直调复核）。
> 第一轮已处置发现（F1-F7）不重报；本轮主攻修订新增内容、代码事实核、E 边复走。

## ① 结论

**阻断 1 / 应修 2 / 低 2**。修订新增内容的主体（推进生效原语来源参数化、锚定 helper 写法边界、F1/F4/F5 修正案、共存期画像）经代码核验**自洽且可落**；但**观察态门的开局/恢复局初值主张与 `Field` 缺省事实正面相抵**（阻断 R1）——设计自证的自愈路径（锁定臂被门挡）在所述门定义下不成立。另有一处引用已退役机制（REGISTERED_ACTORS）与一处 E12 拆批后新开的类型错写缝。

## ② 逐条发现

### R1（阻断）观察态门在开局/恢复局**不挡**：`Field` 缺省 source='observation'，设计的「门自然挡住」与「锁定臂结算确认被门挡」两句均与代码事实相抵

- **位置**：design §2.2 推进门段（「开局态（value=None，入口链/恢复局首帧前）门自然挡住」）/ §2.3 锚定可用性边界段（「恢复局锁定臂……其结算确认被门挡一次，由战后备战帧观察锚定补齐」）/ §2.2 处置规则表（无 v=None 行）。
- **攻击**：门定义 = `node_ord.source == 'observation'`。代码事实：`Field` 缺省即 `source='observation'`（`cw_game_state.py:450` `source: FieldSource = 'observation'`），`node_ord: Field[int] = field(default_factory=Field)`（`cw_game_state.py:2383`）——**每局冷建/异常弃置后的新容器，node_ord 现态 = (value=None, source='observation')，门放行**。「门自然挡住」不成立；设计给出的辩护（「开局没有终结动作」）也只覆盖正常新局，覆盖不了设计自己点名申报的两条路径：
  1. **恢复局锁定臂**（`cw_loop.py:1929-1941` 锁定分支直接出战，不经 CwScreenPrep = 无锚定；`locked_resume_sync_and_battle` 后进 battle_wait）：首战结算确认触发 `report_node_advance`，门（按文）放行 → candidate = `effective_node_ord + 1`，此时 effective = None（`effective_node_ord` 双源皆 None 返 None，`cw_game_state.py:3138-3140`）→ None+1 未定义（TypeError 或实现者自创 None→1）。若自创 None→1：真实节点可能在 P3-r5，凭空写 node_ord=1+tick 一次再靠 R>v 补推拉回——恰是设计声称「被门挡一次」要防的形态。§2.3 该段是第一轮后新增的修订内容，其安全性论证整体建立在错误前提上。
  2. **relaunch 残留结算屏**（`cw_screen_battle_wait.py:671-677` `_mark_relaunch_residual` 所在链）：恢复局首事件即结算屏「按钮-继续挑战」，同上路径，且此形态连「锁定臂」辩护都套不上。
- 另：§2.2 处置规则表只有 R>v/R==v/R<v 三分支，**v=None（开局首锚定建 1，E4）无定义行**——E4 是设计自己声明的覆盖面（§2.1「E4……无前置确认→观察锚定建 1」），实现者按表无法开工。
- **依据**：`kernel/cw_game_state.py:450`（Field 缺省 source）、`:2383`（node_ord 声明）、`:3138-3140`（effective None 语义）、`operations/cw_loop.py:1929-1941`（锁定臂无备战锚）、`operations/cw_screen/cw_screen_battle_wait.py:731-766`（②段结算确认触发位）；design §2.2/§2.3 原文。
- **要求**：门定义补 `value is not None`（或等效：effective 非 None 才可计算 candidate，None → 门挡留证，与「未观察不当真进节点」的 tick 闸同句式）；处置规则表补 v=None 行（E4 首锚定建 1 的显式分支）；§2.3 锁定臂段按修正后的门复述自愈时序。三处同批改，定稿前完成。

### R2（应修）「REGISTERED_ACTORS 扩两名额」引用已退役机制——全仓零命中，`_validate_sig` 现值只校渠道族、明文「不设白名单闸」

- **位置**：design §2.3 共用推进函数段（「REGISTERED_ACTORS 扩两名额，sig 纪律同 R5 W1/ADR-0634」）；landing 3.1 范围⑤（「REGISTERED_ACTORS 扩新 actor 名」）。
- **攻击**：全仓（src/ 全树）grep `REGISTERED` 零命中；现役校验 = `cw_game_state.py:353-361::_validate_sig`，只查 `sig.family ∈ allowed_families`，docstring 明文「actor 仅作遥测/台账行的动作身份标注，**不设白名单闸**」。该机制在 2026-09-16 迭代中仍在（attack 报告引 `cw_game_state.py:285-336`），此后已随某批退役——设计（修订新增段）与 landing 判据⑤指向一个不存在的登记步骤：实现者在 kernel 里找不到要扩的表，要么停手申报、要么自创白名单闸（与现役「不设白名单」纪律相反）。sig 声明的可落性本身无碍（`logic_action` 在 `CHANNEL_FAMILIES` 封闭集内，`cw_game_state.py:326`；trigger op 类名作 actor 自由标注即可）。
- **依据**：grep 全仓 `REGISTERED` = 0；`kernel/cw_game_state.py:353-361`；design §2.3 / landing 3.1 原文。
- **要求**：design §2.3 与 landing 3.1⑤ 改写为现役事实（family 校验 + actor 自由标注，无登记步），或如实申报「本迭代引入 actor 白名单闸」为机制变更（须另立论证，不建议）。

### R3（应修）E12 拆批新缝：奖励关结算确认**证据 miss** 时，BOSS 类型直定把 boss 类型写到上一（奖励）节点——旧模型序号+类型同批原子无此形态

- **位置**：design §2.5 退役清单第 3 行（「类型直定改挂 CwScreenBossBriefing 观察 node……目标 = 现 hist = 已被奖励关结算确认推进的 boss 节点」）；E12/S6。
- **攻击**：新模型把「推进到 (p,9)」（结算确认上报，whitelist 等待有时限）与「boss 类型写入」（CwScreenBossBriefing 观察 node）拆成两个载体、两个时点。目标序取「现 hist」隐含「上报必先于简报 op」——该序在证据命中路径成立（report 在 whitelist 命中点、外循环下轮才分派简报 op），但在**证据 miss 路径**断裂：结算确认 op 的 whitelist 等待超时（miss = 不上报）而流转真实发生 → 外循环照常按 0p 分派 CwScreenBossBriefing → hist 仍停 (p,8) → 类型直定把 boss 写到 (p,8) 奖励节点。类型写无逆操作（无回滚面），后续锚定补推只修序不修类型——奖励节点类型永久污染，比旧模型（`_derive_node_boss_brief` 序号+类型同批双写，`cw_game_state.py:3364` 起）净劣化。设计对「settle_confirm 证据 miss」已申报自愈（锚定补推），但未对「类型直定依赖 hist 已被推进」这一新耦合做 miss-path 分析。
- **依据**：`kernel/cw_game_state.py:3364-3397`（旧腿序号+kind 同批双写）；`observe_screen_context` `:3058-3061`（0p 触发现役通道）；design §2.3（证据 miss = 不上报）/ §2.5 第 3 行原文。
- **要求**：简报类型写端加守卫（目标序 ≠ 预期 boss 序——如 effective+1 未被 hist 占位——时留证零写，交链读链/留证缺位），或把类型目标改为与推进同源校验；E12/S6 论证补 miss-path 一句。

### R4（低）§2.4-1「生产备战帧唯一消费 op = CwScreenPrep」与代码事实不符（无锚定缺口，表述失准）

- **位置**：design §2.4 写端 1 覆盖面核对句。
- **内容**：`cw_loop.py:598` `_launch_frame_arbitration` 在 CwScreenPrep 之外还有一次生产 `read_game_state(phase=PHASE_PREP_CLEAN)` 调用（出战前仲裁开店路径）。该路径发生在 prep 访问内、锚定已先行，**无锚定覆盖缺口**；但「唯一消费 op」是覆盖面论证的判定据句，失准表述会在后续判读中被反例击穿。改「干净备战帧的外循环分派消费 op 唯一 = CwScreenPrep（其余 prep_clean 漏斗读均发生在 prep 访问内，锚定已先行）」即可。
- **依据**：`operations/cw_loop.py:586-599`；design §2.4-1。

### R5（低）3.6 场景清单与 §2.7 行为申报对账缺两行：金采样时点（§2.7-3）与自愈路径当帧发放（§2.7-8）无场景级锁

- **位置**：landing 3.6 场景清单 / design §2.7-3、§2.7-8。
- **内容**：3.6 九条场景覆盖推进面全集，但 §2.7-3（条件族金采样 = 结算真值，`apply_settlement_cover` 先于「继续挑战」点击）与 §2.7-8（补推路径当帧补齐发放）两条**行为变化申报**没有对应场景/断言面——3.1 单测锁「发放恰一次」的量，不锁「金采样源=结算真值、早于上报」的时序。行为变化申报无验证锚 = 不可独立验收。建议 3.6 补两条剧本（结算真值金先行断言 / 恢复局补推当帧发放断言）。
- **依据**：landing 3.6 原文清单 vs design §2.7 逐条。

## ③ 核一覆盖清单（design 各节 → 核过 → 结论）

| 节 | 核查内容 | 结论 |
|---|---|---|
| §2.1 边界定义 | E1-E18 逐边对两动作点+锚定覆盖（见 ④ E 边复走） | ✓（R3 一处拆批缝） |
| §2.2 处置表/推进原语/锚定 helper | ① 表三分支与 `read_phase_round` 输入面：回执 plane/round 恒 int（`cw_observation.py:992-1057` last-known-good 单调守卫+值域守卫+跨局 reset，miss 回退旧值/兜底 (1,1)），「与现行备战腿同源、风险面不变」属实 ✓；② 原语来源参数化内部自洽（action=logic / 补推=observation 的「误挡一拍」论证成立；`advance_node` 序相等去重 → 跳档漏发论证沿第一轮 F2 属实）；③ `prep_frame` 遗迹主张实码证实：`_tick_effect_boundary_impl`（`cw_game_state.py:3269-3280`）函数体不读该参数；`settle_node_boundary_gold` 全仓零调用点（仅 def+注释）✓；④ helper 直写口先例 = `settle_truth`（`:2772-2798`）绕三分流 + obs sig，成立；R<v 留证走 `note_obs_event('arbitrate')` 在词表（`OBS_EVENT_EVENTS:334`）✓；journal 载体规范（渠道族/行型）相容 ✓；⑤ **v=None 无分支 = R1** | ✗ R1，余 ✓ |
| §2.3 触发点 1/2 | ① op 结构描述与实码吻合：②段结算点击 = `_dispatch_frame` `:731-766`（含 M39 长按 `:758-764`、settle_stay 状态机字段）、③段白名单 = `wait()` 出口 A `_hit_completion_anchor:269-289`（五锚+boss OCR 兜底+位面过渡 OCR），「提出 helper 共用」可行 ✓；抽 `CwOpSettleConfirm` 与驻留状态机形态（op-layer §3 `CwScreenBattleWait` 行）相容——子 op 从 ②段 调起、不拆两 node，不触豁免裁定 ✓；白名单出口判定保留的幂等性成立（whitelist 命中即 exit，不重复进 ②段）✓；② 补给侧：`CwActionPickSupplyOp.run`（`cw_overlay_pick_action.py:200-233`）确认链 = `round_by_find_and_click_area(..., success_wait=1.5)`，until 插入点存在（项目 AGENTS §3 在册能力）、现有 `report_action_pick_supply_param` 调用点 `:228` 旁增调可行；「证据 miss 不上报不重试」与其单发+宿主重入结构相容（重入再走 = 确认置灰零副作用，miss 常态由锚定补推收口）✓；③ F5 修正案（时点门非执行验证）与 op-layer §1.2 原文核过，例外条款已列正本清单 ✓；④ **门/锁定臂前提 = R1；REGISTERED_ACTORS = R2** | ✗ R1/R2，余 ✓ |
| §2.4 写端 1/2 | ① `observe_full` 回执真携带 plane/round_num（`cw_observe_full.py:108-133` → `GameStateReadReceipt` `cw_observation.py:2187-2188`）；CwScreenPrep 观察 node 可拿回执：`_observe` heavy 段 `_st = _of.get('read_receipt')`（`cw_screen_prep.py:262`，session 非 None 块内、reobserve_in_visit 同链）——锚定接线可行 ✓；漏斗退出节点域后 recorder 零副作用主张成立（recorder 直调 `read_game_state`，`cw_match_recorder.py:80`，节点域写入随漏斗收口消失）✓；② 补给屏节点条：观察 node 在（`cw_screen_supply_node.py:142-155`），V3 实证节点条屏显且不在 A_PHASE 区（node-derivation §④-C V3），sr-od-test fixture `货币战争-补给/default.webp` 在库可作离线对拍 ✓；③ **「唯一消费 op」= R4** | R4，余 ✓ |
| §2.5 退役清单/切换纪律 | 五调用点 `cw_loop.py:1547/1559/1594/1605/1623` 实测吻合；上下文对开局链消费面 = 仅 `_derive_node_inferred`（退役）+ projection 审计行（非逻辑），§2.7-9「零逻辑消费」成立 ✓；共存画像（3.2 后 settle 门挡：旧备战腿 write_logic 使 source=logic ✓；3.3 后 supply 部分放行 ✓）与 landing 阶段序一致 ✓；**BOSS 迁移行 = R3** | R3，余 ✓ |
| §2.6/§2.7 | §2.6 分家与 `apply_effect_burst_grant`（`:1204`）/`grant_effect_node_refresh_balance`（`:1223`）挂点描述相符 ✓；§2.7 九条逐条对码：1/2/6/7/9 成立（9 见上）、5 成立、8 沿原语成立、3/4 语义可核但缺验证锚（R5） | R5，余 ✓ |
| landing 3.1-3.7 | 3.1 判据含 F2① 回归锁 ✓（但范围⑤ = R2）；3.2 剧本可判 ✓；3.3 两形态剧本+fixture 判据可独立验收 ✓；3.4 边界清晰 ✓；3.5 grep 归零判据可判定（符号集封闭：`_note_branch_screen`/`SCREEN_CONTEXT_POPUP_FAMILY`/`SCREEN_CONTEXT_GUARD_PREV`/`SCREEN_NODE_TYPE_DIRECT`/三 `_derive_node_*` 均为实名符号）✓；3.6 = R5；3.7 清单齐 ✓ | R2/R5，余 ✓ |

### E 边复走（新模型；重点 = 补推时序组合 / 恢复局 / 快弹窗+补给自动弹+位面过渡复合）

E1/E2/E3 零推进 ✓（入口链零上报零锚定，E2 开局 0q 无腿亦无上报 ✓）；E4 首锚定建 1 ✓（但处置表缺 v=None 行 = R1 的组成部分）；E5/E6/E16/E17/E18 零 ✓；E7 两形态（whitelist 备战锚含商店面板下透出形态，currency_war_prep.md:32「锚在 overlay 下仍可透出」）✓；E8 快弹窗四类证据=弹窗锚或透出备战锚 ✓；E9 R==v 翻锚定 ✓；E10 divert/自动弹两形态（自动弹：结算确认证据=补给锚→report→补给屏节点条 R==v 翻→确认→report，链闭合）✓；E11 until 备战锚+补推自愈 ✓（连续补给节点形态：until 备战锚 miss→不报→补给屏节点条 R>v 补推+tick，自愈成立）；E12 公式承载 ✓、**类型侧 = R3**；E13 boss 确认→(p+1,1)=effective+1，位面过渡 OCR 证据在白名单 ✓；级联 B（0q→商店）：report 在 0q 证据点，后继商店/prep 帧无第二推进源 ✓；级联 A（0p→商店）：report 在 0p 证据点 ✓（类型 = R3）；E14 恢复局：备战帧先行→锚定建值 ✓；弹窗先行→无锚定无上报→消化后备战帧补推 ✓；**锁定臂 = R1**；E15 战败无 op ✓。复合序列（奖励关结算→0p→商店自动开→boss 备战→出战→boss 结算→0q→下位面）：每步恰一推进源，无双推边；唯一断裂 = R3 的 miss-path。幻影残余路径（logic 领先一档→R<v 挡→门挡→R==v/R>v 收口）自洽，账本无逆操作申报在案 ✓。**未发现第一轮遗漏的双推/漏推边**。

## ④ 与第一轮发现的关系（已修项复验结果）

| 一轮发现 | 修订处置 | 复验 |
|---|---|---|
| F1 锚定写端家 | §2.4-1 迁 CwScreenPrep 观察 node | ✓ 修复成立（回执可达性实测，§2.4 行）；遗留 R4 表述失准 |
| F2 补推 tick / prep_frame | §2.2 推进生效原语（两路径同临界区+来源参数化）+ prep_frame 删除 | ✓ 修复成立（实码双证：impl 不读参数、settle_node_boundary_gold 零调用） |
| F3 共存期画像 | §2.5 切换纪律分阶段 | ✓ 成立（与代码 source 语义逐段对上） |
| F4 BOSS 类型触发通道 | §2.5 迁 CwScreenBossBriefing | ✓ 通道修复，但修订本身引入 R3 新缝 |
| F5 补给验证契约 | §2.3 辖域修正案 + 正本清单 §1.2 例外条款 | ✓ 成立 |
| F6 行号锚 | 全文符号锚 | ✓ 抽查吻合 |
| F7 上下文对消失 | §2.7-9 申报 | ✓ 成立（消费面 grep 复核：仅派生腿+审计行） |

第一轮 attack.md 的核三结论（根因归层成立、E 边拓扑无破）在本轮复走下维持；本轮全部新发现集中在**门初值语义（R1）、已退役机制引用（R2）、拆批类型耦合（R3）**三处，均为修订新增内容自身的问题面。
