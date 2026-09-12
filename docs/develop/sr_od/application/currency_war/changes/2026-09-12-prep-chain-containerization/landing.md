# prep 链容器化 落地

> 阶段唯一源纪律:本文件 = 账本阶段唯一源;设计改 → 本文件改 → 账本跟着改,禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12(含 `ruff check` 仅改动文件、测试纪律;各阶段完成判据统一引用,不逐条复述)。
> 行号锚纪律:行号随代码漂移,一律以符号为准;各段批首按符号 grep 复核一次(设计件卷首同款纪律)。

## 3.1 段 1·决策判据签名切容器(规模 M)

**范围**:设计件 §2.2 全部——emit 置顶 `bs = board_state_of(session)`、五处签名切 `bs: BoardState`(①`_sphere_progress_sig`/②`_lambda_quantile_armed`/③`_upgrader_evaluate`(死参 gold 删除)/④`_reconcile_posture_authorization`(hp 经 `decision_hp`)/⑤`_criteria_pass`)、下游漏斗判据四件切 bs(`level_spend_blocked`/`levelup_budget_gate`/`line_switch_sell`/`funding_support_sell`)、`locked_buy_cap_hold` 零改兼容(kernel 已双形态)、:551 消桥。边界:不含 §2.3 消点、不含 prep 域全簇(`state = obs.state` 视图维持供数,寿命 = 段 2)。
**设计依据**:design/prep链容器化方案.md §2.2;锁面 §4-P1/P2/P7。
**文件面**:entry.py、criteria/sell.py、criteria/levelup.py(+测试仓对应锁)。
**依赖**:波 4(T-97)落库(criteria 两件为波 4 在飞文件)。
**优先级建议**:6
**完成判据**:
- 五处签名切 bs,域读按 §2.2 逐处映射;行为差申报逐条落实(①缺省镜像等价/②None 分支退役+引导窗缺省镜像逐位一致/③死参 gold 删除/④hp 经 decision_hp 禁直读旁路/⑤金轮位读口)
- §4-P1(五处签名行为等价锁)/§4-P2(漏斗判据等价锁+locked_buy_cap_hold 双形态值等价)/§4-P7(last_state 决策依赖清零,段 1 起持续绿)
- §12 通用工程门(引用,不复述)
**验收凭据形式**:测试锁族(基线 test_cw_mandate_decide / test_cw_p2_blood_band,批首按消费函数名 grep 补全)+ruff check

## 3.2 段 2·备战黑板槽退役(规模 L)

**范围**:设计件 §2.3+§2.4 全部——观察口消点(:711-714 视图合成/:716 无 session 兜底/:833 light 缓存+`_cached_state` 收缩及其三处留证读点改道/:494-495 端口路径装配,归宿见 §2.6 边界行)、`PrepObservation.state` 槽删除、emit 体非传参 state 直读三点清零(:415-416/:525/:621)、prep 域全簇切换(run_mandate/wanted_closure_emit/fuel_sell_candidates/record_round_sold/should_switch/evaluate_evidence_gate/p1_blood_floor/p2_blood_floor + predicates 帧兼容支删除)、对账族/观察终饰(dual 拷回/gated_hp)/缺陷行改道、新 kernel 写口 `apply_prep_action_logic`(域集封闭 gold/bench,sig 纪律 family='logic_action')、finalize 买后暂存容器喂入、adapter 缝收敛(snapshot_to_obs state 装配删/decision_state 骨架退役)、snapshot_from_obs 改纯容器锚。边界:last_state 三写点零触碰(波 5);cw_bs_view.py 文件本体不删(波 5);sim 三件零触碰(§1.3-6)。
**段内执行序(先接后删,禁乱序)**:①全簇切换+对账/装配缝改道(§2.4-1/2)→ ②投影写口+finalize 喂入(§2.4-3/4)→ ③消点+state 槽删除+adapter 缝收敛(§2.3/§2.4-5)。消点前置 = ①②完成(视图供数在切换完成前不拆,§2.3 前置条件)。
**设计依据**:design/prep链容器化方案.md §2.3/§2.4/§2.6;锁面 §4-P3/P4/P5/P6/P7/P8。
**文件面**:cw_screen_prep.py、cw_prep_actions.py、mandate.py、proof.py、statefn/predicates.py、adapter.py、assembly.py、decision_assembly.py、kernel/cw_board_state.py(+测试仓对应锁;含假环境 prep 测试容器喂入改造——§2.6 端口路径边界行,测试仓文件面批首 grep 补全)。
**依赖**:段 1 + 波 4 落库(文件互斥 §1.3-1)。
**优先级建议**:7
**完成判据**:
- 槽与视图退役:§4-P3(game_state_view 零活调用)/§4-P4(obs.state 槽零引用+state_gold_trusted 消费零波及)/§4-P6(prep 域容器单源)绿
- 投影写口:§4-P5(apply_prep_action_logic 等价锁+域集封闭断言+None 跳写登记面)绿
- §4-P7 持续绿;§4-P8(帧代次标注契约形状锁按新写点清单重推:apply_prep_action_logic 投影 none 写/finalize view 写保留)绿
- §12 通用工程门(引用,不复述)
**验收凭据形式**:测试锁族(test_cw_board_state_consume / test_cw_mandate_lifecycle / test_cw_migration_budget_authority,批首 grep 补全)+实机窗口 ≥1 完整局备战链判读(备战决策/投影推进/买后重估/last_state 链;局数候编排者,设计件 §4 建议段 2 交付后安排)+ruff check

## 3.3 段 3·商店黑板槽退役收尾(规模 S)

**范围**:设计件 §2.5 后半 shop_state_frame 全部(M2 移缴面承接)——写点 2 处删(投影写/融合写)、遥测读 1 处改容器读、槽字段与注释面删(cw_strategy_session.py)、标注槽 `shop_frame_class` 保留+坐标系重锚申报(「最近一次商店域容器观察写点」,落地批同步注释面)。边界:`prep_obs_frame` 不辖(§4-P4 辖);波 4 步 4 已辖面(dual/focus 拷入取消等)不重复执行。
**设计依据**:design/prep链容器化方案.md §2.5 后半;锁面 §4-M2。
**文件面**:cw_op_buy_cards.py、cw_strategy_session.py(+测试仓 M2 锁)。
**依赖**:波 4 落库;与段 1/段 2 无相互依赖,可并行派(文件域互斥满足;r5-migration-plan「同一时刻最多两波在飞」约束下段 1 与段 3 不同文件域可并行)。
**优先级建议**:5
**完成判据**:
- §4-M2(全仓 src+测试仓 `shop_state_frame` grep=0)绿;`shop_frame_class` 保留断言(§4-P8 关联面)
- §12 通用工程门(引用,不复述)
**验收凭据形式**:M2 grep=0 凭据+测试锁+ruff check

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:全部落地阶段
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `game_state/fields.md`:§8 代码层面结构(符号指针)——`apply_prep_action_logic` 登记行 ← 段 2
- `flow/session.md`:槽注——`prep_obs_frame` 视觉域收敛(帧保留域封闭清单)/`shop_state_frame` 行删除/`shop_frame_class` 坐标系重锚 ← 段 2/段 3
- `changes/2026-09-11-unified-state/design/商店黑板容器化方案.md`:§4-M2 行收敛(移缴承接闭环注记) ← 段 3
- `game_state/r5-migration-plan.md`:波次表 prep 面行(prep 链容器化落地态回写) ← 全部段
