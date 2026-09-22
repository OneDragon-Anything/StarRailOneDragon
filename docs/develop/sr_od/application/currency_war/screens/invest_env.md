# 投资环境三选一(invest_env · 货币战争-投资环境)

> 代码 = `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv`(两 node 直继承 `SrOperation`)。职责:投资环境 overlay 一次访问——一次读全观察 → `decide_invest_env` 决策 →(按需)整组刷新终结动作 → 选卡确认链经 `CwActionPickInvestOp` 派发(台账变异窗派发前开)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_invest_env.yml`。

## 1. 分发判定

- 阶段一身份分发:id_mark 锚「货币战争-投资环境.标识-投资环境」;处理器臂 = `cw_loop.py::CwLoop._dispatch_identity_screen`(`if name == '货币战争-投资环境'` 链),登记清单 = `cw_loop.py::CwLoop.CW_DISPATCH_SCREENS`。分发单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2(新增画面三件套:建档 + 处理器臂 + 登记清单)。开场 1-1 前弹一次(后局中事件节点只弹投资策略,两画面不同 handler);接管局重入此屏走同分支兜底分流。
- 链序:分发成功后外循环先跑本 op,再链 `CwScreenWaitOneOne`(等 1-1 备战锚就绪,两 op 两对 journal 行);链序代码锚 = `cw_loop.py::CwLoop.loop` 投资环境分支段。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3;投资环境域的例外收窄见 §6)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚门(miss = round_fail 交回外循环重判)→ **一次读全**(候选 + 全局刷新剩余,零稳定帧等待)→ `report_screen_invest_env_obs` 落容器 `invest_env_opts` + `env_refresh_left` 槽 → obs 挂实例属性。决策动作 node = **零容器写**(选择事实不写本 node;active_env 注册/portal 登记/环境赠卡入席全在动作落地链,见 §6)——零参决策 `match.strategy.decide_invest_env()`(候选自容器槽;**空候选/无有效输出 = round_fail 显式失败,零盲发**;委托 `kernel/cw_events.py::decide_event`;环境帧刷新判据在 kernel,handler 禁直调 kernel 判据算刷新建议,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)→ 整组刷新终结交回 ∨ 选卡确认链经 `CwActionPickInvestOp` 派发(词表 = `CwActionPickInvestEnvParam`;**动作 op 点完确认立即上报完整结果**——经获得链 `gain_invest_env` 记)→ **round_success 终结交回外循环**(选完即交回 = [op-layer.md](op-layer.md) §1.1 + [README.md](README.md) §6;确认未生效 = 代码 bug,overlay 残留由外循环重识别重派,修法 = 点击链可靠性)。刷新 = 终结动作,无 pending 裁决:点钮后本访问即 round_success 交回,外循环重进 = 入口重建重观察重分类。

## 3. 观察面

入口单次观察(观察 node)——观察 node 内联序:入口锚探测(miss = `hit=False`,观察 node round_fail 早退,无复探窗)→ 命中后**一次读全**(零稳定帧等待):候选读取 `_read_options`(全图 OCR,卡名行 y 带 360-410 + 2-8 字 + 排除表过滤,左→右排序)+ 全局刷新剩余计数(`read_invest_refresh_counts(ctx, screen, 'env')`,首条 = (剩余次数, x, y),读缺 = None)→ **观察标准化门** `_standardize_options`(规范 = [op-layer.md](op-layer.md) §1.1):逐候选两段转换——形变归一 `normalize_invest_name` 精确命中注册表 → 不中再 LCS 相似匹配兜底(阈值常量 `ENV_LCS_THRESHOLD` ∧ 最高/次高分差 ≥ 歧义 margin 常量 `ENV_LCS_AMBIGUITY_MARGIN`——分差过近 = 注册表内歧义不可分辨,同分/近分一律拒判);两候选命中同一注册名 = 同名拒判,与转换失败同判(选项互斥屏,卡面与注册表一一对应,重复名 = 必有误读)。任一候选转换失败 ∨ 近分歧义 ∨ 同名命中 = 观察 node round_fail 整函数早退,零写容器零上报,交外循环重观察重读;容器 `invest_env_opts` 值域自此 = 标准注册名。残余风险登记:共享词素族单字误读(如「击口概念股」对击破/追击概念股近分跨名借分)由分差拒判拦截,表现为该访问 round_fail 多一轮重观察,非静默错名;残余风险 = 分差内真歧义被判失败,同为多一轮重观察。观察 payload = `CwScreenInvestEnvObs`(`hit`/`options`/`refresh`/`screen`,住 `kernel/cw_screen_report/invest_env.py`);report = `report_screen_invest_env_obs` 候选写容器 `invest_env_opts` 槽 + 刷新剩余写 `env_refresh_left`(观察写端,读缺跳写;空候选不写;match/gs 缺席的局外兜底路径跳过)。决策零参读容器槽,刷新闸直接消费 obs 携带读数。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickInvestOp`(`CwActionPickInvestEnvParam`,投资两屏拆类后两行同指一 op) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:定位点/确认钮/裁决词) | **即时上报**(动作 op 内,机械链发出后立即):`report_action_pick_invest_env_param` → `gain_invest_env` 整链(active_env 注册 + portal 登记 + 环境赠卡入席;reason=`gain_chain_applied`,见 §6)——零分步零证据等待 | **是(访问终结)**:派发后 `round_success` 终结交回;确认未生效 = 代码 bug(外循环重识别重派,修法 = 点击链可靠性) |
| 整组重掷刷新(无注册表动作 op;`CwActionRefreshInvestCardsParam` 仅策略建议载体) | 画面 op 留守臂(`_decide_and_act` 刷新终结分支:「剩余次数」文本锚定偏移 `safe_click`) | 无自上报(计数读数只作零效果留证,缺陷分键 `invest_env.refresh_no_effect`) | **是(访问终结)**:点击 + 动画窗 + 留证重读后 `round_success` 即交回;外循环重进 = 入口重建 |

单决策体 `_decide_and_act`(零参,输入 = 观察轮 obs 载体):

```
names = opts 卡名;空候选 → round_fail 显式失败(零盲发,先于局外出口——
  空候选 = OCR 读缺 bug 面,契约与局外无关)
未注册环境名逐个告警(该项 env_fit 走中性 fallback)
局外无 match(∨ gs 缺席)→ 零决策零点击 round_success 终结交回
  (画面 op 不产决策、不设兜底决策路径——正本 =
  op-layer.md §1.1「画面 op 不支持局外单独调用」;仅独立跑可达)
act = match.strategy.decide_invest_env()(零参,输入 = 容器标准名
  invest_env_opts 槽——观察标准化门产出,值域 = 标准注册名)
├─ 整组重掷刷新 = 终结动作(与策略屏不同构:单全局钮 + 单全局计数):
│    闸 = obs.refresh 携带读数 >0 才有授权(观察段一次读全,决策环零识别;
│      读缺 = 无授权失败安全)∧ 容器 env_refresh_left 剩余口径对照(≤0 = 尽)
│    闸败(建议帧但无授权/读缺)→ 同访问重调 decide_invest_env 落选卡:
│      flow 层 scratch 键 (kind, 候选元组) 同帧去重——建议帧首调发建议、
│      紧随重调落选卡并清键,零选卡漂移;防御 = 重调仍返刷新建议(策略
│      未实现去重)则弃动作 → round_fail 显式失败
│    授权 → 点「剩余次数」文本锚 + 固定偏移 _REFRESH_BTN_DX(-101,safe_click)
│    → 动画窗固定等待 1.5s → 刷后帧机械重读只作零效果留证输入
│      (计数未扣 ∧ 名集未变 = 强信号 → 缺陷台账 record_defect L2 留证,
│       零决策零改道;任一侧读缺 = 过渡帧不可判不猜)
│    → 零效果留证对账(消费即清)→ round_success = 本访问终结交回
│      (选卡/确认均不在本访问;外循环重进 = 入口重建)
├─ 决策无有效选卡输出 → round_fail 显式失败(零盲点)
├─ 选卡(选择事实零容器写,active_env/portal 登记不在画面 op——全走获得链
│    `kernel/cw_gain_chain.py::gain_invest_env`,动作 op 点完确认立即上报;
│    session 形参显式传入[局外/测试 = None 登记腿跳过]。环境即时效果腿 =
│    `on_env_gained` 枚举(`ENV_GIFTS` `chars_immediate` 送卡入席 / advisor
│    申报分道);欢愉契约条件腿不在该枚举——触发事件 = 头号玩家选项弹窗被
│    处理(银狼策划选择上报),授予 = 条件腿 rider
│    `kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`
│    (`active_env` 欢愉契约在册 → `gain_character` 1★ rand=True,写端 =
│    rider 链内落位/合成写),正本 = ../game_state/gain-chain.md §3)
├─ 台账变异窗:选卡链派发**前**开窗(env_grace_until = now + 45s 常量
│    ENV_GRACE_S)——环境选择是位面节点序列唯一变异源,确认到节点行
│    重读之间的查表不一致是合法变异,三票校验不得落缺陷台账
│    (关窗迁备战帧链写端)
└─ 选卡确认链:派发 CwActionPickInvestOp(机械链在动作 op 内,点完确认
     立即上报完整结果经获得链记;派发 param 携真实选中 idx(纯 idx 上报,
     名字自容器标准名单一源按序号提供——规范 = op-layer.md §1.1),
     定位点 = 「区域-卡牌描述行」center.y[兜底常量 450] + 该卡 center-x
     [点立绘/卡名不选中,点描述区才选中],确认钮 = 「按钮-确认」center
     [兜底常量],裁决词「投资环境」)
     → round_success = 本访问终结交回外循环
```

选卡+确认链经动作工厂(`CwActionPickInvestOp`)派发;刷新圆钮点击留守画面 op(safe_click),刷新臂刷后机械重读只作零效果留证输入(`_reconcile_refresh_no_effect`),不进决策。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 整组刷新点击 | **访问终结** | round_success 交回外循环重进 = 入口重建,重进后重观察重分类 |
| 选卡确认链派发 | **访问终结** | round_success 交回外循环重分发(本屏身份臂链尾接 `CwScreenWaitOneOne`;结果已即时上报写入;确认未生效 = 代码 bug,overlay 残留由外循环重识别重派) |
| 观察转换失败(标准化门) | 显式失败 | round_fail 零写零上报,交回外循环重观察重读 |
| 空候选/决策无有效输出 | 显式失败 | round_fail 交外循环(零盲发) |
| 局外无 match(仅独立跑可达) | **访问终结** | round_success 零决策零点击交回(op-layer.md §1.1 局外单跑条款) |
| 入口锚 miss | op FAIL | 交回外循环按当前画面重分发 |

刷新 = 唯一引入新事实的动作,终结交回语义 = [op-layer.md](op-layer.md) §1.4;「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- `active_env` 写入:动作落地获得链写(`kernel/cw_gain_chain.py::gain_invest_env`,
  写行署名 `GAIN_CHAIN_PRODUCER`;**写时点 = 动作执行时**——动作 op 点完确认
  立即上报,契约 = [../flow/action_ops.md](../flow/action_ops.md) §1 增补 2、
  链式规范正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md)
  §2.1/§8;链内无效载荷拒绝 = 零写留证,正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md) §2.1 步 0;本屏零容器写)。
- portal 效果登记:`gain_invest_env` 链内腿 → `kernel/cw_effect_inventory.py::
  register_portal_from_env`(best-effort,失败留证不阻塞;经济判据接登记数据归后续批)。
- 环境赠卡入席/席满溢出落位:`gain_invest_env` → `on_env_gained` 枚举 →
  `gain_character`(入席/溢出/升星链)。欢愉契约条件腿不在本枚举
  (触发条件/写端/正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md) §3;
  见 §4 选卡分支申报)。
- 候选观察:`report_screen_invest_env_obs` 候选写容器 `invest_env_opts` 槽 +
  刷新剩余写 `env_refresh_left`(观察写端,读缺跳写)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.3 / §4「投资选择」;效果账 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8;效果激活账本 = fields.md §5.1。

## 7. 子态与 overlay

本屏无子态、无 overlay 覆盖面。本屏分发链尾的「等待 1-1」不是本屏子态,是独立推进 op(`CwScreenWaitOneOne`)。

## 8. 守卫与防线

- 未注册环境名告警(数据缺口可见化;env_fit 走中性 fallback 不阻塞)。
- 刷新零效果留证(缺陷台账 L2 记录,不停机不改道);偏移错 → 刷新未命中时重进后计数未扣、预算仍在 → 再次刷新,每圈耗 1 次外环重进(能力退化非事故,复测即修)。
- 读缺守卫:计数读缺 = 无授权(失败安全);无帧 = 刷新链跳过。
- 台账变异窗(45s)防确认后节点行刷新窗口内的三票校验误报。
- 获得链守卫(落地相,正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md)):
  portal 登记腿 best-effort 失败留证不阻塞(已迁链内);特邀专家(advisor)卡面
  chars_immediate 不入席,身份只进遥测申报行(缺陷分键 `gain_chain_advisor_decl`);
  bench 未观察/溢出位被占 = 零写留证不停机。
- 验效废除与预算语义同 [op-layer.md](op-layer.md) §1.2;无本屏专属停机钩子([../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 =「投资环境」(本屏身份臂链另有「等待 1-1」独立行);op 内日志 tag = `[cw-env]`(计数读数/options/chose/reason、刷新终结交回)。
- 缺陷分键 = `invest_env.refresh_no_effect`(record_defect L2 留证)。
- 测试锁(逐项与测试实存对齐;测试仓根 = `sr-od-test/test/sr_od/application/currency_war/`):观察门 miss 早退 + 候选一次读落容器 `invest_env_opts` + obs 挂实例属性 = `test_cw_obs_arch_phase_screens.py::test_invest_env_observe_gate_and_report`;观察标准化门(可转换名 → 容器/obs 标准名,含归一精确与 LCS 兜底命中路径[「彩虹吋代」不过严回归锚];转换失败乱串 / 两候选命中同一注册名 / LCS 近分歧义[「击口概念股」双真名近分] → round_fail 零写零上报) = 同文件 `test_invest_env_observe_standardization_gate`;`env_refresh_left` 观察写端双腿(计数读得值写入 / 读缺跳写) = 同文件 `test_invest_env_refresh_left_observed_write` + `test_cw_screen_report_ports.py`(`_case_invest_env` 值与来源锁、空桩摄入序 `invest_env` 行:候选空整函数早退不写含 left);空候选零盲发 = `test_cw_obs_arch_phase_screens.py::test_invest_env_empty_opts_fail_not_blindfire`;派发即终结 + 派发时点写入对拍(active_env 已写) = `test_cw_obs_arch_phase_screens.py::test_invest_env_active_env_written_at_dispatch`;局外无 match = 零决策零点击 round_success 终结交回 = `test_cw_obs_arch_phase_screens.py::test_invest_env_no_match_zero_decision_handback`;机械链与 param 类型分派 + 即时上报接线 = `test_cw_unified_action_4.py::test_invest_pick_op_clicks_target_confirms_and_self_reports`;刷新零效果对账留证(缺陷分键 `invest_env.refresh_no_effect`) = `test_cw_unified_action_4.py::test_invest_env_refresh_no_effect_reconcile_records_defect`;portal 链与防污染(容器播种承载纯 idx 取名) = `test_cw_yinlang_phase32.py::test_invest_portal_landing_no_card_pollution`(ENV_GIFTS 全量发放 = 同文件 `test_invest_portal_env_gifts_full_access`);纯 idx 上报契约(名字自容器标准名单一源按序号提供,容器缺读/idx 越界 = 响亮失败)锁面 = `test_cw_action_report_contract.py` param 冒烟锁(invest_env 行随按 idx 取名契约播种容器承载)+ `test_cw_yinlang_phase32.py` portal 锁(idx → 链收容器同序标准名);链内无效载荷拒绝(detail=`invalid_payload` / active_env 零写 / 缺陷行 `pick_invest_invalid_payload`) = `test_cw_gain_chain.py::test_gain_invest_env_invalid_payload_zero_write`;命名/sig/写入域完备锁 = `test_cw_screen_report_ports.py`。
- game 侧知识:画面与机制(环境 = 整局增益) = [../../../../game/screens/currency_war_invest_env.md](../../../../../game/screens/currency_war_invest_env.md);环境刷新判据 = `kernel/cw_events.py` 环境帧分支 + [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1。
