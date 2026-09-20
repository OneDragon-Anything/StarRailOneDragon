# 节点推进动作上报化 迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-20，会话五点）：①节点边界定义重立（推进 = 终结动作落地）；②效果计数职责分家（推进只盘点在场效果，登记语义归拿卡上报）；③推进前置门 = node_ord 现值为观察态（结构防重复推进）；④抽独立结算确认动作 op；⑤一步到位原子切换（不设新旧并存验证期）。
- 状态：草案
- 文档清单：无详设（单文档方案，本篇即完整设计）

## 1. 问题与动机

- 现状症状：
  1. **触发点隐藏**：节点推进（四腿派生）住 kernel `cw_game_state.py::observe_screen_context`，生产触发写点只有两处远端——观察汇聚漏斗尾段（`cw_observation.py::read_game_state` → `_phase_screen_context` 相位映射）与 `cw_loop.py::_note_branch_screen`（5 个调用点）。画面 op 层面零可见性：读任何一个画面 op 看不出「观察我会推进节点、发效果余额」。
  2. **设计与实况漂移**：弹窗腿四成员（遭遇/投资策略/补给/商店面板）中前三类的上下文名在生产无写点（分派分支不调 `_note_branch_screen`）——休眠腿。快弹窗形态下「先推进后选卡」（node-derivation.md §3.3 裁定 2）对这三类实际不成立，推进推迟到选完卡后的备战帧；三屏类型直定从不落账。
  3. **遥测副作用**：`telemetry/cw_match_recorder.py::extract_frame` 经漏斗（phase=None → 备战帧映射）可推进活容器节点状态——录帧改变逻辑态。
  4. **推断制固有复杂度**：守卫族/缓存守卫/恢复局禁用/BOSS 简报幂等锚/级联双推进双保险，全部为「从画面散射推断节点」而设；守卫族漂移与级联双推进是两次实证事故类（node-derivation.md 修订链 R3.1/R4）。
- 根因归层：**流程层·触发模型**。节点边界在游戏里的因果是「终结动作落地」（结算确认/补给确认），实现却建模成「画面观察的推断量」——因果错位是全套推断防御机制的根。
- 解决到哪：触发模型换代（§2）——推进 = 终结动作上报；观察 = 锚定 + 兜底；三条推断腿整体退役。
- 明确不解决：①节点序坐标系粗糙面（投资环境增节点使 (plane-1)*9+round 公式漂移，既有信息项，node-derivation.md §5-③.4）；②效果域批 M3 挂账项（`_last_tick_node` 计数器退役）——本迭代只新增观察态门，不动账本内部去重；③类型派生机制本体（简报直定/商店查链/链读链不动，只随序号挂点变化调整触发）；④入口链（`cw_entry/`）不接上报——开局首节点由观察锚定覆盖（§2.4）。

## 2. 方案

### 2.1 节点边界定义重立（定义本体）

- **新定义**：节点推进 = 上一节点终结动作落地。战斗节点终结 = 结算胜利确认（「继续挑战」）；补给节点终结 = 补给选择确认。位面末节点推进后由序号公式 (plane-1)*9+round 自然跨位面（9+1=10=(2-1)*9+1，node-derivation.md §3.2 坐标系）。
- 备战画面从「推进触发面」改判为「对账锚定面」（§2.4）。弹药核对：全部节点边界流转 E4（开局，无前置确认→观察锚定建 1）/E7（结算确认）/E10-E11（补给确认）/E12（奖励关结算确认→boss 节点，0p 降为纯过渡屏）/E13（boss 结算确认→跨位面）均可由两动作点 + 观察锚定覆盖（node-derivation.md §3.1 全景图逐边核对）；S1-S10 走查同源。
- 依据：用户裁定 2026-09-20①；本节取代 node-derivation.md §3.3「定义基准」（R5 裁定「节点推进 = 进入该节点的备战画面」）——正本更新阶段落改判记录。

### 2.2 容器语义：node_ord 两态生命周期与观察态门

**字段语义改判**：`node_ord` 从「纯逻辑层派生字段」（现行：四腿全部 write_logic，禁 observe 直写序键——node-derivation.md §3.2-7 字段层次终极版）改为**两态字段**：

- **observation（锚定态）**：写端 = `observe(node_ord, R)`，R = 顶栏/节点条读数序号（解析读数，与 gold 的 OCR 解析同类，非游戏规则推算——这是「observe 直写」的合法性依据；`top_bar_raw` 原文观察层保留不动，两字段分工不变）。锚定写端两处（§2.4）。
- **logic（推进态，未确认）**：写端 = 终结动作上报推进（§2.3）。

**推进门（用户裁定③）**：`report_node_advance` 前置门 = **双条件** `node_ord.value is not None ∧ node_ord.source == 'observation'`。门挡 → obs_event arbitrate 留证，零推进。语义：只有已被观察确认的节点值才允许被动作推进——重复上报、重试、任何第二条推进路径在结构上不可能；去重键 `node_hist_ord` 保留作水位与第二道防线。
**value 守卫不可省（攻击 R1 定谳）**：Field 缺省 `source='observation'`（cw_game_state.py::Field 定义），新容器 node_ord = (None, 'observation')——若门只查 source，开局/恢复局（锁定臂直出战、relaunch 残留结算屏）的首次终结确认会误放行且 candidate = effective+1 在 effective=None 时无定义。双条件下：value=None（开局链/恢复局首锚定前）→ 挡；value 在场且 source=observation → candidate = max(value, hist)+1 可计算。锁定臂语义修正复述：其首次结算确认被 **value 守卫**挡（非 source 门），由战后备战帧观察锚定补齐——行为结论不变，机制表述以本段为准。

**观察锚定处置规则**（单一源 = kernel 锚定 helper，两写端共用；R = 本帧读数，v = 现值）：

| 分支 | 处置 | 依据 |
|---|---|---|
| R > v | 观察采新，且**经推进生效原语落账**（写 node_ord/hist + 效果推进尾段同临界区；补推：漏上报自愈） | 绝对值坐标，采新即对齐；账本 `advance_node` 去重为序相等判（cw_effect_inventory.py::advance_node），序号前进不经 tick 即永久漏该节点每节点发放（攻击 F2①） |
| R == v | 直写同值（source=observation，同值行；logic 态此分支 = 动作推进被观察确认翻锚定态——下一节点终结动作由此解锁） | 重复上报解锁即锚定语义 |
| R < v | 不写 + obs_event arbitrate 留证（倒退免疫，node-derivation.md §3.3 规则三现值保留） | 节点序局内单调（游戏无回退流转，§3.1 E15 终局除外）；R<v 只能是读数误读或幻影推进残余 |
| v = None（首锚定） | 任何 R → 写 R（source=observation）+ hist 占位 + 效果推进尾段 | E4 开局建 1 / 恢复局重建语义；开局链期间拾取的效果由此首拍发放（与现行首备战帧 tick 时机一致） |

**幻影推进残余的自愈路径**（申报）：上报已带转移证据门（§2.3），幻影（上报了但游戏没走）被结构性预防；若证据被误命中（模板误报级），残余形态 = logic 值领先一档，后续锚定被 R<v 分支挡住、下一次终结动作被门挡、再下一节点观察 R>v 补齐——**绝对值坐标保证无累积误差，偏差有界一个观察周期**。效果账本不回滚（`grant_free_refreshes` 计数器与 `advance_node` 递减无逆操作；幻影预防在前，接受该残余边界并留证）。

**推进生效原语（kernel 单一入口）**：序号前进的任何合法写点（动作上报 / 观察补推）都必须经同一原语 `advance_node_effective`（命名实施批可调）：candidate 去重守卫 → 写 `node_ord`（**写入来源由调用方定**：动作上报路径 = logic（推进未确认态，观察态门语义的前提）；锚定补推路径 = observation（观察采新即确认态——否则补推后源态落 logic，下一次终结动作被门误挡一拍））+ `node_hist_ord` 占位 → 现有 `tick_effect_boundary` 尾段（账本 advance_node + `grant_effect_node_refresh_balance` 在场盘点发放 + `project_effect_capacity`）同临界区执行。锚定补推（R>v）同样是真实节点进入（恢复局/锁定臂/证据 miss 的自愈路径），漏 tick 即该节点每节点发放永久丢失（攻击 F2① 定谳）。`tick_effect_boundary` 现签名中 `prep_frame` 参数为遗迹（历史语义「金结算仅备战帧触发」随 `settle_node_boundary_gold` 全仓零生产调用点已死，`_tick_effect_boundary_impl` 现值不读该参数），迁移批删除该参数并清理 `observe_screen_context` 尾段过期闸注释（攻击 F2②）；`tick_effect_boundary` 本体保留独立可调口（sim/直测，2026-09-15-effect-ledger-self-advance design §2.1 申报不变）。锚定直写行的 sig = obs 族（mode='read'，actor = 宿主 op 登记名），journal 行型不变。

**锚定 helper 的写法边界（实现级约束）**：`observe_node_anchor` 的写端**不经通用 `observe()`**——R>v 与 logic 现值失配会误入「观察覆盖 logic 失配」安灯三分流（`observe()` 的 logic mismatch 通用机制）；helper 对 node_ord 直写 `Field(source='observation')`（节点域专用写口，先例 = `settle_truth` 的结算金币专用口：绕三分流、留证行承载豁免语义），三分支（R>v 采新+原语 / R==v 锚定 / R<v 丢弃留证）全部在 helper 内显式处置，通用失配机制不辖节点域。

### 2.3 推进触发面（动作上报）

**共用推进函数**（kernel，唯一动作推进口）：`report_node_advance(gs, *, trigger: str, sig: ChannelSig | None = None) -> None` = 观察态门（§2.2 双条件）→ candidate = `effective_node_ord + 1` → 推进生效原语（§2.2）。trigger 封闭集 = `{'settle_confirm', 'supply_confirm'}`（留证 actor 归因）；sig family = logic_action，actor = 触发 op 自由命名标识（攻击 R2 定谳：现役 `_validate_sig` 只校 family、不设 actor 注册闸，`REGISTERED_ACTORS` 机制已退役——journal 行归因用 actor 字符串，无注册面）。

**触发点 1——结算确认动作 op（用户裁定④）**：新 op `CwOpSettleConfirm`（`operations/cw_op/cw_op_settle_confirm.py`；非策略动作面——不经动作注册表、无 CwAction param，命名与构造从画面框 op 惯例 `CwOpOpenShop/CwOpCloseShop`）。职责 = 点击「继续挑战」（含现役 M39 长按兜底重试策略，cw_screen_battle_wait.py 长按兜底专用点迁入）→ 等完成判据白名单命中（转移证据）→ `report_node_advance(trigger='settle_confirm')`。证据 miss = 不上报，长按兜底继续重试（现行为）。`CwScreenBattleWait` ②段（结算点击）改调本 op；③段白名单出口判定保留（幂等：已命中帧不重复点击）。战败分支不建 op、不推进（终局流转 E15，节点序止于终局）。
**证据集同源条款（攻击 R3 定谳，封 E12 拆批缝）**：op 的转移证据集 = 完成判据白名单**全集**（备战系/补给/遭遇/投资策略/**强敌来袭**锚，与 `CwScreenBattleWait` ③段同一判定 helper），等待语义同 ③段（白名单命中即返，无独立短超时）。由此：boss 流中「证据 miss 而流转真实发生」不可达——流转发生 ⇒ 简报锚现身 ⇒ 白名单命中 ⇒ 上报先于 `CwScreenBossBriefing` 分派，hist 已推进至 boss 节点，简报类型直定目标恒正确（序号与类型经同锚同源归凑，等价旧模型 `_derive_node_boss_brief` 同批原子性）；证据 miss ⇒ 流转未发生（或锚识别失败——此时简报 op 同样不会被分派，类型直定无从触发，缝不存在）。
锚定可用性边界（申报，机制表述随 R1 修正）：恢复局锁定臂（`cw_loop.py::locked_resume_sync_and_battle` 直出战）首次结算确认被 value 守卫挡（§2.2），由战后备战帧观察锚定补齐——绝对值坐标，无 skew。

**触发点 2——补给确认**：`CwActionPickSupplyOp`（`cw_overlay_pick_action.py::CwActionPickSupplyOp`）确认链点击补转移证据（until = 下一节点备战锚，E11：补给确认 → 下一节点干净备战帧，无自动弹链）→ 现有 `report_action_pick_supply_param` 调用点旁增调 `report_node_advance(trigger='supply_confirm')`。证据 miss = 不上报（无重试编排，兜底 = 观察锚定补推 §2.2）。
辖域契约修正案（攻击 F5）：转移证据在本 op 中的角色 = **上报时点门**（决定报不报），非执行验证（不重试、不恢复、不判效）——与 screens/op-layer.md §1.2「动作 op 禁做任何验证」的禁令（verify+retry 编排）不冲突但字面相抵，正本更新阶段在 §1.2 增补具名例外条款：「节点终结上报类动作 op 允许以转移证据作上报时点门；证据 miss 不上报不重试，兜底归观察锚定」。

**报告时点语义**：两触发点均为「转移证据确认后」上报——逻辑态不领先游戏现实（幻影预防）；「先推进后选卡」结构性成立（确认点击先于下一节点一切弹窗与选卡，裁定 2 由因果序保证，不再依赖弹窗推断）。

### 2.4 观察锚定面（两写端）

1. **干净备战帧：`CwScreenPrep` 观察 node**（攻击 F1 定谳，原「漏斗尾段」方案作废）：备战 heavy 观察（`obs/cw_observe_full.py::observe_full`，内部漏斗 `read_game_state`）的回执 `GameStateReadReceipt` 携带本帧 plane/round_num → 备战 op 观察段调 `observe_node_anchor(node_ordinal_of(plane, round_num))`（§2.2 处置规则）。**漏斗彻底退出节点域写入**（上下文对/`top_bar_raw` 观察层保留）——recorder（`cw_match_recorder.py::extract_frame` 经漏斗）与一切旁路读数从此零节点域副作用，§2.7-5 申报成立。锚定输入与现行备战腿同源（`read_phase_round` 直读/缓存/守卫语义不变，风险面不变）。覆盖面核对：生产备战帧的画面 op 消费 = `CwScreenPrep`（外循环备战分支分派，锚定唯一挂点）；`cw_loop.py` 仲裁路径另有 prep_clean 漏斗读（`cw_loop.py:598`）——纯域读数不挂锚定，无缺口（攻击 R4 表述修正）；锁定臂不经备战 op = 无锚定，门挡自愈路径照走（§2.3 触发点 1 申报）。

**「退出节点域」的精确辖域（攻击 B1 修正）**：漏斗退出的 = **推进域**（`node_ord`/`node_hist_ord` 写入）；`gs.node` 观察镜像写端（漏斗内 plane/round 读口基底，cw_observation.py 漏斗段）**保留在漏斗**——它是决策层坐标消费（`_defeat_latch`/`_shop_panel_type_target`/读口基底，cw_game_state.py 读口段）的供给端，字面拆掉即决策坐标全断。recorder 申报同步精确化：录帧的**推进副作用**（四腿+效果 tick）消失；`gs.node` 镜像/域观察写入保留（与 gold/hp 同类的观察域写入，零派生零推进）。
2. **补给屏节点条**：`CwScreenSupplyNode` 观察链新增节点条读数（视觉实证 V3：补给屏顶部居中节点条「备战阶段 X-Y」屏显，node-derivation.md §④-C V3；现役 `read_phase_round` 的 A_PHASE 识别区不含该位置——需 screen_info 扩识别 area，按 od-dev-screen-onboarding 建档流程落坐标与模板）→ 同一锚定 helper。这是补给「自动弹」形态（结算确认直接弹补给屏，无本节点备战帧）的唯一锚定点，缺它则补给确认被门挡、走观察补齐（可运行但退化，故列为必做）。

`prev_screen`/`current_screen` 上下文对与 `top_bar_raw` 观察层：保持现状（观察域，供 journal 审计与商店查链）。

### 2.5 退役清单（一步到位，用户裁定⑤）

| 退役物 | 位置 |
|---|---|
| 弹窗腿本体 + 守卫族/弹窗族常量 + 缓存守卫 + 恢复局禁用分支 | `cw_game_state.py::_derive_node_inferred`、`SCREEN_CONTEXT_POPUP_FAMILY`、`SCREEN_CONTEXT_GUARD_PREV` |
| 位面过渡腿 | `cw_game_state.py::_derive_node_plane_transition`（跨位面由序号公式自然承载，§2.1） |
| BOSS 简报腿 + 幂等锚（序号半部） | `cw_game_state.py::_derive_node_boss_brief` 序号推进半退役；**类型直定半迁移触发点**（攻击 F4）：现触发 = 本腿内部 + `_note_branch_screen('货币战争-BOSS简报')`，两载体均退役——类型直定改挂 `CwScreenBossBriefing` 观察 node（简报屏上报经 kernel `_write_derived_node_type` 直定 boss 类型，目标 = 现 hist = 已被奖励关结算确认推进的 boss 节点；actor/sig 语义保留），简报屏仍是 boss 类型权威。**直定前置同源守卫（攻击 R3 定谳）**：直定仅在简报 op 被分派（锚命中）时发生，而锚命中 ⇒ 结算确认证据命中（证据集同源条款 §2.3）⇒ hist 已是 boss 节点——「hist 落后、类型写错节点」的形态结构性不可达 |
| 循环分支写点 ×5 | `cw_loop.py::_note_branch_screen` 及五处分支调用点（BOSS简报/位面过渡/简报/投资环境/等待1-1） |
| 遭遇/补给/策略休眠类型直定路径 | `SCREEN_NODE_TYPE_DIRECT` 三成员（生产从未有写点，退役 = 零行为变化；类型来源 = 简报直定 + 链读链 + 商店查链，均现役） |
| 备战腿派生写法 | `_derive_node_observed` 的 write_logic 写法 → observe 锚定 helper（§2.2 改判） |

切换纪律：共存窗口按阶段如实画像（攻击 F3）——3.2 后：`settle_confirm` 被门挡（旧备战腿 write_logic 使 source=logic），留证噪声行 ≈ 每节点一行的预期现象，节点跟踪仍由旧腿全权驱动；3.3 后：补给屏锚定使 `supply_confirm` 在补给节点可过门（部分放行，与旧腿靠去重键共存无害）；3.5 切换批一次完成「备战锚定切换 + BOSS 类型直定迁移 + 旧腿退役 + 漏斗/loop 收口」，同批原子（无旧路径残留窗口）。共存期遥测画像是过渡态，不做判读依据。

### 2.6 效果计数职责分家（用户裁定②）

- **节点推进侧**：只盘点当时在场效果发放每节点余额（`grant_effect_node_refresh_balance` 现语义，零改动）。搜打撤在不在场由拿卡时序自然决定，推进函数无感知。
- **拿卡登记侧**：拿卡动作触发的效果生效（burst 一次性额度）现状已挂选卡登记点（`apply_effect_burst_grant`，采样点 = CwScreenInvestStrategy 确认落地后，cw_game_state.py::apply_effect_burst_grant 注）。per_node 族（搜打撤/加油站/双手狸/本金充裕）拿卡当节点是否补发 = 效果登记建模问题：新模型下默认不补发（与推进时序自然一致）；若 game 侧证据表明游戏在拿卡当节点即给每节点额度，则在登记点按 payload 建模补发。逐效果核查挂 landing 阶段 3.4，结论落 game 侧 research（证据分级）。
- 与今天快弹窗形态相比的行为差异（入场拿的效果当节点从「发」变「不发（除非建模补发）」）在 §2.7 申报。

### 2.7 行为变化申报

1. 推进时点：观察散射推断（弹窗/备战帧被采到）→ 终结动作转移证据确认处（提前到下一节点任何画面渲染之前）。
2. 「先推进后选卡」：由弹窗推断（三类休眠不成立）→ 结构成立。
3. 效果发放时点：提前到确认时刻；条件族（本金充裕）金采样 = 结算真值（`apply_settlement_cover` 结算链先于「继续挑战」点击，cw_screen_battle_wait.py 结算观察段），比今天快弹窗路径的陈旧金更准。
4. 入场拿的 per_node 效果当节点发放：默认消失（§2.6 可建模补发）——与快弹窗形态相反、与慢形态一致；策略数学核查挂 3.4。
5. recorder 录帧的**推进副作用**消失（漏斗退出推进域写入，锚定写端 = `CwScreenPrep` 观察 node，§2.4；攻击 F1 定谳）；`gs.node` 观察镜像写端保留漏斗（观察域写入，非推进，辖域界定见 §2.4 攻击 B1 修正）。
6. journal 行 actor：派生腿 actor（derive_node_*）退役，新 actor = 两触发 op + 锚定 helper + BOSS 类型直定（`CwScreenBossBriefing` 观察 node）；行型语义（write/obs_event）不变。
7. 「字段层次终极版·禁 observe 直写序键」裁决推翻（§2.2），正本落改判记录。
8. 效果发放触发面扩为两条推进路径（动作上报 + 观察锚定补推，均经推进生效原语 §2.2）——恢复局/锁定臂/证据 miss 自愈路径从「序号前进但不发放」变「当帧补齐发放」（攻击 F2① 申报）。
9. 开局链五屏（简报/投资环境/等待1-1/BOSS简报/位面过渡）的上下文对写入随 `_note_branch_screen` 退役消失——journal 画像面变化，零逻辑消费（守卫族已亡、类型直定改挂画面 op 不依赖上下文域名）；入口链接上下文上报属可选后续，不在本迭代（攻击 F7 申报）。

### 2.8 关键取舍

- **观察态门 + 转移证据门双门并用** vs 单门：证据门防幻影（逻辑领先现实），源门防重复（结构不可能二推）——互补不冗余，均为用户裁定面（③ = 源门；证据门 = 项目 Operation 规范 §3「画面切换点击带 until 证据」的既有纪律延伸）。
- **observe 直写 node_ord** vs 保持 write_logic + 独立锚定水位位：直写免加状态位、source 语义即门输入；代价 = 推翻旧裁决（已申报 §2.7-7）。解析顶栏序号与解析 OCR 金价同类，归读数不归推算。
- **倒退免疫保留** vs 观察赢回退：保留（R<v 一律丢弃留证）。观察赢回退会把单帧读数误读落成真值回退且无账本逆操作；免疫的最坏残余（幻影领先一档）有界且自愈（§2.2）。
- **抽独立结算 op**（用户裁定④）vs battle_wait 内直调：形态与补给侧对称、M39 重试策略随 op 内聚；代价 = battle_wait ②段重构（状态机段边界小改，③段白名单判定提 helper 共用）。
- **一步到位**（用户裁定⑤）vs 并行验证期：共存窗口仅存在于本迭代落地批之间（3.1-3.4），不作为交付形态；终态无旧机制残留，符合「机制整体退役，重新出现即架构回潮」纪律（screens/op-layer.md §4）。
