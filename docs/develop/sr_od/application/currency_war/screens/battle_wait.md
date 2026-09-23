# 战斗等待(battle_wait · 战斗/结算窗族)

> 代码 = `operations/cw_screen/cw_screen_battle_wait.py::CwScreenBattleWait`(驻留状态机,单 node `wait`;用户裁定豁免两 node 形态)+ `::SettlementState`(战斗/结算链跨迭代状态机;`cw_loop.py::CwLoop.handle_init` 随 RunLoop 实例化注入,`__init__(ctx, st, config)`)。职责:出战交回后的战斗/结算窗驻留——等结算 → 结算处理(遥测读点 → 点「继续挑战」)→ 完成白名单/团灭终局分叉交回外循环。战斗自动进行(auto-battler),玩家无操作面。路径根 = `src/sr_od/application/currency_war/`。
> 驻留状态机豁免(用户裁定):本 op 单 node `wait()`(「战斗等待」,`node_max_retry_times=400`)——出口判定(大厅终局锚/完成白名单)与分支链在单 node 内逐轮重判,拆观察/决策动作两 node 会把出口判定与分支序的轮次耦合切开;内部结算链(`_write_settlement_observation`/`apply_settlement_cover`/SettlementState)逐位零改动。report = `kernel/cw_screen_report/battle_wait.py` 占位(结算覆盖写端在结算域,非画面观察记账,op 层零调用)。

## 1. 分发判定

- 外循环战斗窗分支,**双入口**(`cw_loop.py::CwLoop.loop` 战斗窗分支):①出战驻留闩 `_battle_wait_active`(备战分支出战成功置位);②帧锚 `_frame_in_battle_window`(接管局/残留结算屏;锚集 = 继续挑战按钮/败局页模板/数据统计/点击空白加速/总伤害/前往结算·返回货币战争——简报「下一步」刻意不列,与终局链共享词形宁缺勿造)。分发时注入宽限计时起点 `self._settle.battle_ts = self._battle_ts`。
- 位置:阶段二默认分支之后、3c 大厅收口之前(分发结构 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2「战斗窗」行)。外循环只回答「在不在战斗窗口」,单元内部分类(等待/结算页/败局链/过场屏)归本 op 分支链,不进外循环。
- 完成白名单与外循环分支共用画面锚,判定双源分工:`_hit_completion_anchor` 用备战**单锚**宽到达判定(「货币战争-备战.备战标识-购买经验」),「按钮-出战」双锚精判是循环备战分支职责——op 内重复双锚即双源。白名单含 boss 简报锚 + 片段判别与位面过渡 OCR(共享文案「点击空白处继续」不作跨画面判据,排他单一源 = [boss_briefing.md](boss_briefing.md) §1);位面简报不在切换链上,不列。

## 2. 画面形态声明

**空决策形态**(无选择面 ∧ 无逻辑态账;推进为流程义务)。本 op 为结算链收编的既有 op:轮询等待/长按兜底/宽限等重试语义为 as-built 保留,不在「新 op 单尝试」辖内([README.md](README.md) §3 形态判据的既有 op 豁免);无策略器问询。结构判据 = 逻辑单元生命周期 owner:战斗+结算是一个单元(开始 = 出战,结束 = 白名单锚/团灭终局),单元内多阶段由分支链分类。sim 腿 = 不适用(sim 事实来源为 coarse 结算产出非画面段)。节点 = `wait`(`@operation_node(name='战斗等待', node_max_retry_times=400)`)。

## 3. 观察面

驻留型轻观察(每轮 `round_wait` 后重截重判 = 等待型轮询观察;终局锚/完成白名单出口判定含早退轮次语义,归 `wait` node 内)。分支链消费 obs 解析工具箱(`obs/cw_settlement_obs.py`):`read_round_outcome`(结算读数 → `RoundOutcome`)/`parse_settlement_round`(头部「X-Y」)/`parse_settlement_progress`/`parse_progress_fill_ratio`/`read_settle_damage_breakdown`/`settle_page1_progress_sign`/`parse_settlement_assets`/`read_settle_gold_opt`;`obs/cw_observation.py::read_phase_round`(last-known 兜底源)。结算金读链:`parse_settlement_assets` token 解析失败(当前版本结算布局无『存量 <N>』token)→ `read_settle_gold_opt` 右上角货币计数定点读 + 稳定门(首读失败补采一帧;帧间不一致取末帧 + 冲突留证,补采上限 = `SETTLE_GOLD_MAX_POLLS`);token 与定点读双失败且胜局 = 落全帧 token 留证行供解析器加固对账;败局页无面板,读失败为预期形态。结算读数即对账边界:结算写点见 §6(时序红线 = 「结算即写」,禁惰性化)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;本屏无注册表动作 op、无策略器问询,动作 = 驻留状态机内的留守机械臂 + 一个画面框 op 委托臂(继续挑战推进 = `cw_op/cw_op_settle_confirm.py::CwOpSettleConfirm`,形态归属 = [op-layer.md](op-layer.md) §2.1 节点推进上报族例外——非动作注册表面、无 CwAction param);「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无注册表动作 op——继续挑战推进臂(挑战成功结算段) | 宿主采集与结算链(采集钩子 `settle_frame_collect` → 读点前等 1.5s + 重截 → `_record_round_outcome` → 新帧指纹计数)后**委托 `CwOpSettleConfirm`**:点击『货币战争-结算.按钮-继续挑战』→ 停留 ≥`CwOpSettleConfirm.SETTLE_STAY_LONG_PRESS` 轮长按 `SETTLEMENT_NEXT` 兜底 → 遭遇奖励兑现回调(`kernel/cw_encounter_selection.py::claim_encounter_reward`)→ `report_node_advance(trigger='settle_confirm')` 点击即上报;宿主对 op 失败 `round_fail` bail | 节点推进上报 settle_confirm([../flow/action_exec.md](../flow/action_exec.md) §2.1;宿主侧无动作上报) | 否(非终结):op `round_success` 交回宿主 `round_wait` 驻留,出口判定 = 宿主 ③段白名单 |
| 无注册表动作 op——败局链按钮族推进臂(1f/3b) | 画面 op 留守臂(OCR 按钮族「前往结算/下一页/下一步/返回货币战争」命中即点;全 miss 点空白 `BLANK`) | 无自上报(败局补录 `_record_loss_page` = telemetry-only 观察写端) | 否(非终结):发出后 `round_wait` 逐页推进 |
| 无注册表动作 op——点空白加速臂(结算页1 动画帧) | 画面 op 留守臂(OCR「点击空白加速」命中点空白) | 无自上报(progress/三项暂存 = 观察写端) | 否(非终结):发出后 `round_wait` |
| 无注册表动作 op——过场屏推进臂 | 画面 op 留守臂(OCR「总伤害」∨「货币战争-结算.标识-数据统计」命中点空白) | 无自上报 | 否(非终结):发出后 `round_wait` |
| 无注册表动作 op——自动战斗自愈臂 | 画面 op 留守臂(「货币战争-战斗.标识-我方行动待操作」∧「标识-回复技能」双锚连续命中 → 点「货币战争-战斗.按钮-自动战斗开关」) | 无自上报 | 否(非终结):开关动作后 `round_wait(wait=2)` 覆盖切换生效窗 |
| 无注册表动作 op——未知帧 bail 臂 | 画面 op 留守臂(宽限外连续 `UNKNOWN_BAIL_N` 轮全 miss → 截图留证) | 无自上报 | **是(bail 交回)**:round_fail 交外循环未知画面兜底链(不停机,裁决权留外循环) |

分支链 `_dispatch_frame` 自上而下(OCR 检测命中即点命中位置,检测/点击同源;`pre_delay=0` 保持检测即点):

| 分支 | 判定锚 | 动作与等待语义 |
|---|---|---|
| 挑战成功结算 | 「货币战争-结算.按钮-继续挑战」 | 采集钩子 → 读点前等 1.5s + 重截(结算数据后于按钮渲染,screen_flow_timing #6/#25)→ `_record_round_outcome` → 新帧指纹计数(`last_settle_fp` 同屏指纹,点击不生效不虚增 `rounds_done`)→ 委托 `CwOpSettleConfirm`(点击/长按兜底/兑现回调/settle_confirm 推进上报随 op);op 失败 → bail 交外循环兜底链 |
| 失败结算页(1f) | 「货币战争-结算-失败.标识-挑战进度」∧「标识-挑战结束」∧ 无继续挑战 | 进度符号(`settle_page1_progress_sign`):neg → 置败局闩;面板延迟门(`SETTLE_PANEL_WAIT_S`:伤害说明面板 visible 或超时才放行推进,超时兜底覆盖胜轮面板整块不现);页1 三项暂存(`settle_page1_progress`/`settle_page1_settle`,消费时同窗校验 `settle_p1_battle_ts == battle_ts`);`_record_loss_page`(telemetry-only 补录,同屏指纹防重)→ 按钮族 OCR(`前往结算/下一页/下一步/返回货币战争`)命中即点,全 miss 点空白 `BLANK` |
| 点空白加速 | OCR「点击空白加速」 | progress/三项暂存 + 面板延迟门 → 点空白加速(结算页1 动画帧) |
| 前往结算链(3b) | OCR 按钮族(同上四按钮) | 「前往结算」帧补 outcome 行(指纹防重);「下一步」∧ OCR「挑战失败」→ hp=0 补录 + 置败局闩;命中即点 |
| 战斗/过场屏 | OCR「总伤害」∨「货币战争-结算.标识-数据统计」 | 点空白推进 |
| 等待结算画面 | `_in_battle_grace` 宽限内(§8) | 自动战斗未开检测:「货币战争-战斗.标识-我方行动待操作」∧「标识-回复技能」双锚连续命中(时长 = 代码内联判定值,防技能演出相似视觉单帧误判)→ 点「按钮-自动战斗开关」自愈(点击非按键:开关为画面按钮,对窗口焦点敏感);否则静止 `round_wait` 轮询 |
| 未知帧 | 全 miss | 连续 `UNKNOWN_BAIL_N` 轮 → 截图留证(`battle_wait_bail` 前缀)→ `round_fail` 交外循环未知画面兜底链(不停机,裁决权留外循环) |

## 5. 终结与交回

出口在 `wait()` node 内、分支链之前:

| 出口 | 判定 | 语义 |
|---|---|---|
| `terminal_lobby` | 「货币战争-大厅.标识-创业指南」 | 团灭终局链终点(「返回货币战争」落点)→ round_success 交外循环 3c 收口(run 收口/分配器/存档装配写端在彼处,不随 op 化迁移;对局循环终止) |
| `back_to_loop` | 完成白名单 `cw_screen_battle_wait.py::SETTLE_COMPLETION_ANCHORS` 任一(判定本体 = 同文件 `hit_settle_completion_anchor`;备战单锚/补给/遭遇节点/投资策略/BOSS简报锚)+ boss 简报片段判别 + 位面过渡 OCR(带 boss 排他) | 「已回备战系画面」宽到达判定 → 交回外循环全分支重判;白名单后的面板就位判定由循环判定序承接,不在本 op 承诺内 |
| bail | 未知帧超 `UNKNOWN_BAIL_N` | round_fail 交兜底链(超时兜底语义) |

外循环 `on_result` 回调 = 战斗宽限守卫域(留外循环):`_settle.saw_settlement` → `_battle_ts=None`(窗口关,watch 恢复);`_battle_wait_active=False` 闩清出口归一(白名单/终局/bail 都清)。

## 6. 状态上报面

结算读数 → GameState/Session 覆盖链(`_record_round_outcome` = 结算观测回路,结算点即时直写;观察半写点单一源 = 模块级 `_write_settlement_observation`):

- **观察半直写**(「结算即写」时序红线,禁惰性化):`_write_settlement_observation` = `session.performance.record(obs)`(`RoundOutcome` 入 history 存档;last_streak/last_hp 等 session 防御缓存已随终态契约 §A/§B 退役——streak/hp/gold/level 真值链由结算覆盖写端直入容器 gs,失读 None 化跳过语义由覆盖写端承载);同点过 `hp_confidence ≥ 0.9` 门更新 `SettlementState.last_outcome_hp`(summary final_hp 真值源)。
- **容器半覆盖写**:`kernel/cw_game_state.py::apply_settlement_cover`(GameState settlement 域:hp_after/streak_after/killed/progress_delta/gold/level/xp——金/等级/经验仅胜局,缺席不写;note=`battle_done:<节点类型>`;best-effort 失败不阻塞)。金读链现役形态见 §3;读失败 = gold 缺席不写(本局无金真值覆盖)。结算域字段规格 = [../game_state/fields.md](../game_state/fields.md) §3.5。
- **plane/round 真值覆盖**:结算屏头部「X-Y」对 last-known 走单调门覆盖;双读不等 → `defects.record_defect('phase_round','perception_conflict')` 留证;残留屏(`_mark_relaunch_residual`)豁免并按屏面真值校正。
- **节点类型**:首领识别锚(『货币战争-结算.标识-首领』画面位)> gs 推导(`kernel/cw_game_state.py::node_kind_of`;session 识别源已退役,单一源 = 容器)> 探针表兜底(`_node_type_from_table`,宿主 = `gs.node_books.plane_node_table`)> 缺省『普通战斗』;词汇表统一 = `_normalize_node_type`。
- **killed 兜底链**:进度符号(`progress_delta > 0`)优先;hp 对比兜底(置信 ≥0.9 ∧ 轮次邻接门,时基 = `kernel/cw_plane_table.py::node_t_of`)。
- **遭遇选档观测面**(环写位):`_cw_selection_write` → `kernel/cw_encounter_selection.py::record_settlement_row`(残留行不入环;telemetry-only 面 `killed` 非显式败局行抑制不入环);对账落盘 hook `_cw_selection_capture`(缺省关,启用点 = 标定采集显式接通)。
- **效果账本结算挂点**:`game_state_of(session).effects.on_battle_end()`(现役注册表零 BATTLE_END 条目 = 行为面仅事件计数)+ 拷贝仪参与计数 `kernel/cw_effect_inventory.py::settle_copy_machine_participation`(成熟入席落日志)。各独立 best-effort 异常域,失败不阻塞结算链。
- **页1 暂存合并**:进度/三项遥测暂存在页2 记录时合并消费(暂存值优先于页2 同帧读数;跨窗滞留即弃,防上一场污染下一场)。

## 7. 子态与 overlay

子态 = 战斗进行中(宽限静止)/ 结算页1 动画帧(「点击空白加速」)/ 挑战成功结算页 / 败局链多页(前往结算 → 下一页 → 下一步 → 返回货币战争)/ 战斗/过场屏(总伤害/数据统计)/ 自动战斗未开双锚态。event overlay 不在本窗内(阶段一身份分发/特殊规则分支先行分流);白名单 miss = 继续驻留,不交回。

## 8. 守卫与防线

- **出战宽限(口径)**:`BATTLE_WATCH_GRACE_S` 内未见结算屏 = 战斗进行中合法静止,不进未知帧计数;关窗 = 见结算屏(`saw_settlement`)。`battle_ts` 由外循环注入。
- 未知帧 bail 上界 `UNKNOWN_BAIL_N`(节点作用域预算;战斗特效长帧期已由宽限挡在计数外,本值只辖「结算后卡死」形态)。
- 结算屏点击未生效的长按兜底(宿主 = `cw_op/cw_op_settle_confirm.py`:`SETTLE_STAY_LONG_PRESS` 轮阈值 + `SETTLEMENT_NEXT` 长按点;见 §4 分支表);同屏指纹防重(`last_settle_fp`/`last_loss_fp`);败局闩 `saw_defeat_settlement` 双证据(进度符号 neg,或面板负分量 ∧ t ≥ `SETTLE_DEFEAT_LATCH_MIN_T`——次级证据裁决 = `_defeat_latch_by_secondary`,节点真值键 = 容器 node 读口,fail-closed 不置闩);relaunch 残留结算屏判据宽限 `RELAUNCH_SETTLE_GRACE_S`。
- 自动战斗检测连续命中计时(防单帧误判);开关动作后 wait 覆盖切换生效窗。

## 9. 遥测与锁面

- journal op 名 = 「战斗等待」(dispatch 包装统一落 `[cw-op]` 行)+ 委托 op「货币战争-结算确认」(日志前缀 `[cw-settle-confirm]`);节点推进上报 = settle_confirm journal 行(actor 归因 = `kernel/cw_game_state.py::_NODE_ADVANCE_ACTORS` → CwOpSettleConfirm;判定语义 = [../flow/action_exec.md](../flow/action_exec.md) §2.1 / [../game_state/node-derivation.md](../game_state/node-derivation.md) §3.3);缺陷分键 = `phase_round`/`perception_conflict`(reader_source=`settlement_vs_prep_round`);结算观测日志前缀 `[cw-bwait]`,bail 留证 `[cw!]` 行;结算屏时序帧采集 = `operations/settle_collect_hooks.py::settle_frame_collect`(临时采集件,文件自声明清单完成后整段可删)。
- 测试锁:bail 预算锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(锁面目录 = 同目录;战斗等待专属行为锁的重建归属见模块头申报)。
- game 侧知识:结算时序 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #6/#25;画面档 = `assets/game_data/screen_info/currency_war_battle.yml`/`currency_war_settlement.yml`/`currency_war_settlement_fail.yml`/`currency_war_lobby.yml`。

## 开放设计注

① 结算写点 = 「结算即写」时序红线:驻留状态机豁免两 node 拆分,结算写点不迁不拆(拆入独立对账段必改执行时序,零变更红线优先;用户裁定)。② 结算锚 boundary 触发口([op-layer.md](op-layer.md) §6,转点锚 boundary 触发口候裁决)不接线——结算登记 = 观察写端非动作发射登记,动作锚注册表无登记件。
