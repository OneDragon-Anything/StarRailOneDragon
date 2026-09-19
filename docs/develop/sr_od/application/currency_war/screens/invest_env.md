# 投资环境三选一(invest_env · 货币战争-投资环境)

> 代码 = `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv`(两 node 直继承 `SrOperation`)。职责:投资环境 overlay 一次访问——稳定帧观察 → `decide_invest` 决策 →(按需)整组刷新终结动作 → 选卡确认链经 `CwActionPickInvestOp` 派发(台账变异窗派发前开)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_invest_env.yml`。

## 1. 分发判定

- 外循环分支 0s:id_mark 锚「货币战争-投资环境.标识-投资环境」。开场 1-1 前弹一次(后局中只弹投资策略,两画面不同 handler);接管局重入此屏同分支兜底分流。
- 链序:分发成功后外循环先跑本 op,再链 `CwScreenWaitOneOne`(等 1-1 备战锚就绪,两 op 两对 journal 行)——链序 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2 投资环境行。分发 = 阶段一身份行,单一源同 §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚门(miss = round_fail 交回外循环重判)→ 1s 稳定帧 → 候选一次读 → `report_screen_invest_env_obs` 落容器 `invest_env_opts` 槽 → obs 挂实例属性。决策动作 node = 顶部重入裁决(确认裁决:锚不在 = 环境选择落地 → success;锚在 = 未落地重走)→ 零参决策 `match.strategy.decide_invest_env()`(候选自容器槽;委托 `kernel/cw_events.py::decide_event`;环境帧刷新判据在 kernel,handler 禁直调 kernel 判据算刷新建议,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)→ 整组刷新终结交回 ∨ 选卡确认链经 `CwActionPickInvestOp` 派发(投资两屏共用 op,机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=10` 现役值仅框架异常路径消费)。刷新 = 终结动作,无 pending 裁决:点钮后本访问即 round_success 交回,外循环重进 = 入口重建重观察重分类。

## 3. 观察面

入口单次观察(观察 node)——`_observe_frame` 序:入口锚探测(miss = `hit=False`,观察 node round_fail 早退,无复探窗)→ 命中后 1s 稳定等待 → 重截稳定帧(标题出现后三卡才渲染稳定,时序口径 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #3)→ 候选读取 `_read_options`(全图 OCR,卡名行 y 带 360-410 + 2-8 字 + 排除表过滤,左→右排序)。刷新计数另有 log 观察通道(`read_invest_refresh_counts(ctx, screen, 'env')`,遥测面供 GameState 写入端;执行闸不消费本读数,`_decide_and_act` 独立现读同源 reader)。观察 payload = `CwScreenInvestEnvObs`(`hit`/`options`/`screen`,住 `kernel/cw_screen_report/invest_env.py`);report = `report_screen_invest_env_obs` 候选写容器 `invest_env_opts` 槽(空候选不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过)。决策零参读容器槽。

## 4. 动作面

决策动作 node 单决策体 `_decide_and_act`(零参:候选/稳定帧自观察轮 obs 载体):

```
names = opts 卡名;未注册环境名逐个告警(该项 env_fit 走中性 fallback)
act = match.strategy.decide_invest_env()(零参,候选读容器 invest_env_opts 槽)
  (无 match 局外防御 = 裸空容器 decide_event)
├─ 整组重掷刷新 = 终结动作(与策略屏不同构:单全局钮 + 单全局计数):
│    计数现读 read_invest_refresh_counts(..., 'env') → 全局计数 >0 才有授权
│    (读缺 = 无授权失败安全;重进后计数自然闸住再次刷新)
│    → 点「剩余次数」文本锚 + 固定偏移 _REFRESH_BTN_DX(-101,safe_click)
│    → 动画窗固定等待 1.5s → 刷后帧机械重读只作零效果留证输入
│      (计数未扣 ∧ 名集未变 = 强信号 → 缺陷台账 record_defect L2 留证,
│       零决策零改道;任一侧读缺 = 过渡帧不可判不猜)
│    → 零效果留证对账(消费即清)→ round_success = 本访问终结交回
│      (选卡/确认均不在本访问;外循环重进 = 入口重建)
├─ active_env 选卡时点写(点卡**前**,ADR-0598 语义;本屏与策略屏的写时点
│    差异为各自实证语义,禁互相统一):GameState active_env write_logic
│    (选完即关整局保留;session 份退役)+ portal 效果登记
│    (register_portal_from_env,best-effort;经济环境入结构化条目)
├─ 台账变异窗:选卡链派发**前**开窗(env_grace_until = now + 45s 常量
│    ENV_GRACE_S;pick-op-unify 批起自「确认前」平移至「派发前」,
│    宽限面只增不减)——环境选择是位面节点序列唯一变异源,确认到节点行
│    重读之间的查表不一致是合法变异,三票校验不得落缺陷台账
│    (关窗迁备战帧链写端)
└─ 选卡确认链:置确认 pending → 派发 CwActionPickInvestOp(投资两屏共用;
     机械链在动作 op 内,op 内自上报 report_action_pick_invest_param 零写;
     派发 param 携真实选中 idx,定位点 = 「区域-卡牌描述行」center.y
     [兜底常量 450] + 该卡 center-x[点立绘/卡名不选中,点描述区才选中],
     确认钮 = 「按钮-确认」center[兜底常量],裁决词「投资环境」;
     落地判定归 §2 确认裁决;台账写点②「确认后自截屏重读节点行」已
     退役——环境改型由返回备战后的入口观察链读承接)
```

选卡+确认链经动作工厂(`CwActionPickInvestOp`)派发;刷新圆钮点击留守画面 op(safe_click),刷新臂刷后机械重读只作零效果留证输入(`_reconcile_refresh_no_effect`),不进决策。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 整组刷新点击 | **访问终结** | round_success 交回外循环重进 = 入口重建,重进后重观察重分类 |
| 确认点击 | 机械交回 | 重入确认裁决:锚不在 = success 交回外循环(0s 链尾接 `CwScreenWaitOneOne`) |
| 入口锚 miss | op FAIL | 交回外循环按当前画面重分发 |

刷新 = 唯一引入新事实的动作,终结交回语义 = [op-layer.md](op-layer.md) §1.4;「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- `active_env` write_logic(本屏写入、选完即关整局保留;session 份退役;单次逻辑写入豁免——选择落地无定型帧可核对,后果走观察覆盖)。
- portal 效果登记(`kernel/cw_effect_inventory.py::register_portal_from_env`,active_env 写入同址;零决策消费,经济判据接登记数据归后续批)。
- 候选观察:`report_screen_invest_env_obs` 候选写容器 `invest_env_opts` 槽(空候选不写)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.3 / §4「投资选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8;效果激活账本 = fields.md §5.1。

## 7. 子态与 overlay

本屏无子态、无 overlay 覆盖面。0s 分支链尾的「等待 1-1」不是本屏子态,是独立推进 op(`CwScreenWaitOneOne`)。

## 8. 守卫与防线

- 未注册环境名告警(数据缺口可见化;env_fit 走中性 fallback 不阻塞)。
- 刷新零效果留证(缺陷台账 L2 记录,不停机不改道);偏移错 → 刷新未命中时重进后计数未扣、预算仍在 → 再次刷新,每圈耗 1 次外环重进(能力退化非事故,复测即修)。
- 读缺守卫:计数读缺 = 无授权(失败安全);无帧 = 刷新链跳过(旧调用形兼容)。
- 台账变异窗(45s)防确认后节点行刷新窗口内的三票校验误报。
- 验效废除与预算语义同 [op-layer.md](op-layer.md) §1.2;无本屏专属停机钩子([../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 =「投资环境」(0s 链另有「等待 1-1」独立行);分支屏记号 `_note_branch_screen` 两写点;op 内日志 tag = `[cw-env]`(计数读数/options/chose/reason、刷新终结交回)。
- 缺陷分键 = `invest_env.refresh_no_effect`(record_defect L2 留证)。
- 测试锁:两 node 行为锁 + 写入流对拍 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(重入裁决×门组合/观察门 miss 早退与 report/active_env 选卡时点写)。
- game 侧知识:画面与机制(环境 = 整局增益) = [../../../../game/screens/currency_war_invest_env.md](../../../../../game/screens/currency_war_invest_env.md);环境刷新判据 = `kernel/cw_events.py` 环境帧分支 + [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1。
