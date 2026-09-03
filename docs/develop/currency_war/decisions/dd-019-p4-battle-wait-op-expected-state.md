# DD-019 · W971 P4 战斗等待 op 与期望态 infra 落地

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期决策记录,类名保持当时事实,未改)。

- 状态:accepted
- 日期:2026-09-02
- 关联:W971 `prereg/w971_flow_layer/05-battle.md`、`EXPECTED_STATE.md`(FINAL v3.1)、`02-state.md` §4.3;DD-011(判稳标志纪律)、DD-014(黑板决策接口)

## 背景与问题

W971 流程层重构 P4 有两件事:①战斗/结算窗口仍以 6 个内联分支散在 battle_loop
flat loop 里(1f 败局页/2 点空白加速/3 结算读点/3b 前往结算链/5 下一步/6 过场屏),
状态机(hp 真值链/败局闩/页间暂存)散挂实例属性,画面 op 生命周期无归属;
②操作 op 触发的识别面之外的游戏自变(典型:3合1 合成)没有统一的「期望态推进
→ 实读覆盖 → diff 留证」infra,雏形(BuyExpect/XpLedger/装备期望)各带各的簿记。

## 决策

1. **战斗等待 op 收编**(05-battle §1):新建 `operations/cw_flow/battle_wait_op.py`
   (BattleWaitOp + SettlementState)。三段式(等结算 → 结算处理 → 白名单完成判据)
   + 团灭终局第三出口(terminal_lobby)。主循环经「出战驻留闩 + 帧锚」双入口委托;
   op 返回后必经 round_wait 下轮全分支重判(环让位重入契约)。**3c 收口不随迁**
   ——runs summary/分配器/按局存档/match 清理写端留在主循环,遥测连续性红线
   (decisions.jsonl/outcomes 字段面零变更,遥测写端调用原样平移)。
2. **结算读点时序锚定**:#25 用户裁定(读点前 1.5s)与 M39 长按兜底(停留 ≥3 轮
   长按 960,898)随 op 迁移为 op 常量单一源。
3. **期望态容器 + apply_op_effect 同源接线**(EXPECTED_STATE §1/§6):
   `session.expected_state: dict[str, ExpectedEntry]`(path→条目;身份寻址 +
   组确认 group_id + 覆盖点绑定 confirm_point)。登记钩子挂
   `PrepActionExecutor.execute`(decision_assembly.execute 委托该执行器 =
   两执行面一次覆盖、零双写);登记失败不阻塞执行。
4. **覆盖点 reconcile**:prep_obs(备战观察,gold 关态不可信 = F5 可信门)/
   shop_wave_top(gold 可信源)/ settlement(hp/gold/level 全可信,新增
   `parse_settlement_assets` 读口)三点;diff 五分类留证经注入槽
   `set_evidence_sink`(生产 = `expected_reconcile.jsonl`,缺省关 = 只 log,
   测试零真实 IO)。
5. **雏形分道收编(禁一刀切)**:buy 通道保留 BuyExpect 载体 + DD-005 降级 +
   消费即清(expected_state 只做挂载点统一,kind='buy_expect');xp 通道保留
   XpLedger 锚点+轮界重锚(expected_state 只做簿记镜像);tracked 族保留
   reconcile_tracking 裁决器语义(双空读守卫/回退防抖/帧态门/银狼豁免),
   expected_state 只接管登记+清账簿记。
6. **merge_simulate 纯引擎**(EXPECTED_STATE §4):落点(全备战→最左/含场上→
   场上位置)/连锁/满栏自动多买(复用 merge_buy_k/completes 单一源)/装备
   全继承(玩家 2026-09-02 定谳);「场上同名同星 ≤1」恒成立断言内建。

## Considered Options(最值钱栏)

- 战斗窗口归属:**A. flat loop 保留内联分支**(现状,状态散挂、op 生命周期
  缺位)/**B. BattleWaitOp 承载单元生命周期(选定)**——战斗+结算满足
  node-per-op 判据(逻辑单元生命周期+单元内多阶段+单元作用域卡死判据);
  委托入口用「闩+帧锚」而非纯帧分类,避免为激活条件再建一套优先级阶梯。
- 3c 收口位置:**随 op 迁移** 会把局终遥测写端拖进子 op、终局分叉多一条跨 op
  状态回传链;**留主循环(选定)** = BattleWaitOp 只回 terminal 状态,收口
  零迁移,回退面最小。
- apply_op_effect 挂点:**decision_assembly 与 executor 双挂** 会双写;**executor
  单点(选定)** 因 assembly 天然委托 executor(装配层注释 + 回归锁双保险)。
- 卖出回金期望推进:精确 cost 需 roster 查表(`_char_fee`),查不到退
  「+售价(待实读)」到账登记条目——宁缺勿造,不拍值。

## 后果

- 战斗/结算链的修改面集中到 battle_wait_op(可 `run_operation` 单跑);
  battle_loop 净删 ~600 行内联分支。
- 期望态登记面对 `_handle_bench_full` 席满急救**显式不建模**(不经执行器,
  留证声明而非遗漏,EXPECTED_STATE §6)。
- 已知接线缺口(已勾销,接线批 2026-09):~~overlay 到账登记区的 handler 侧调用~~
  (已接:`_overlay_confirm.register_confirm_arrival` 按 §3.3 分道接入七个确认
  落地点,prep_obs reader 到账清账语义 = `cw_screen_prep.prep_obs_actual_for`);
  ~~装备分布期望态(RunEquip 子动作效果)~~(已接:`cw_op_equip_all.register_equip_worn`,
  M7 落点已验后 owned−1/角色 equips+1);~~外循环 stall 判定消费 expected_state
  轮次戳~~(已接:`cw_loop.prep_stall_pending_expected`,仅 prep_obs 可确认条目
  计入 stall 签名与留证线索)。
- 已知建模校准项:满栏语境合成落点(EXPECTED_STATE §P2 批注 2/6)与溢出件
  落点归位槽号——列对账优先观察项,由 expected_reconcile 实证修正。

## 实施决策(设计未覆盖处的贴近现状选择)

- BattleWaitOp 白名单完成判定用「备战标识-购买经验」单锚(宽到达判定);
  备战双锚精判留给主循环备战分支,避免同一判据双源。
- 主循环在 PrepDirector 成功后即置驻留闩(环出口未必是出战):非出战返回帧
  会被 op 白名单立即交回,多一次委托往返(~1s)换取入口确定性。
- 金账(gold 族)条目按「到账登记」处理(可信读清账不 diff),精确金对账
  保留在 spend 账本既有通道——expected_state 不建第二套绝对值金账。
