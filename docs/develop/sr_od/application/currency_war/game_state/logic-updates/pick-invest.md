# 投资选择两行(PickInvestStrategy / PickInvestEnv)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。**一篇辖两注册行**:两行同指一个 op 类 `CwActionPickInvestOp`(族文件先例 = [tools.md](tools.md)),机械半同构,屏别差异在词表类与上报函数分派。语义单一源声明:策略支 = [../gain-chain.md](../gain-chain.md) §2.4、环境支 = 同篇 §2.1;字段级正本 = [../fields.md](../fields.md) §3.4.4(active_strategies)/ §3.4.3(active_env);本篇为接线面摘要,冲突以正本为准。

## 1. 动作是什么

投资两屏(投资策略 3 选 1 / 投资环境 3 选 1)的选择动作。词表两 param 类(`kernel/cw_vocab.py`),字段同构:

| 词表类 | 屏别 | 字段形 |
|---|---|---|
| `CwActionPickInvestStrategyParam` | 投资策略 | `idx`(候选槽位下标,0 基,坐标系 = 对应 payload 槽 options 列表下标,生成期快照)+ `reason`(归因记录,`''`=未标)+ `norm_name`(选中卡归一规范名,`normalize_invest_name`;OCR 原始名不静默改写由 handler 持有)+ `route_tag`(后两者不入动作实例键)|
| `CwActionPickInvestEnvParam` | 投资环境 | 同上 |

- op 载体 = `operations/cw_op/cw_pick_invest_action.py::CwActionPickInvestOp`(非终结;机械链同构:点选中(safe_click 防吞点击)→ 0.7s 选中动画等待 → 确认(`emit_overlay_confirm` 机械交回)。屏间差异全部经 `OverlayPickExecEnv` 显式传入——定位点/确认钮中心/裁决词(`'投资策略'`/`'投资环境'`),op 类体内零决策零读屏。
- 注册两行(`operations/cw_op/cw_action_registry.py`):两 param 类型同指 `CwActionPickInvestOp`,上报按 param 类型机械分派。
- 发射位 = 投资策略/投资环境两画面 op 决策半经注册表工厂 `action_op_for` 派发(画面篇 = [../../screens/invest_strategy.md](../../screens/invest_strategy.md) §4,环境屏同构)。

## 2. 逻辑态域集

- `active_strategies`(名单+品质,fields.md §3.4.4)/ `active_env`(§3.4.3);
- effect_inventory 登记腿(fields.md §5.1)/ chars、equips 赠卡腿(gain-chain.md §2.2/§2.3,经效果分派)。
- 写入口 = 两上报函数(`kernel/cw_action_report/pick_invest_strategy.py::report_action_pick_invest_strategy_param` / `pick_invest_env.py::report_action_pick_invest_env_param`),即时单相:确认点击后一次调用写全部效果(action_ops.md §1 增补 2)。

## 3. 确定面转移规则

**策略支**(`gain_invest_strategy`,逐腿一句,正本 = gain-chain.md §2.4):

1. 无效载荷拒绝:归一后空/`'?'` = 零写 + 缺陷留证(`pick_invest_invalid_payload`);
2. `active_strategies` 按名字去重追加(跳写后登记/效果腿照常,零幂等闸);
3. 效果账本登记腿 best-effort(`register_strategy` + burst 桥 + 板面重写桥;`session=None` 跳过;失败 `gain_chain_strategy_register_failed` 不阻塞);
4. `on_strategy_gained` 效果分派(赠卡入席腿:银狼 `gain_character` 链式时序 + 改件 `gain_equipment(rand=True)` 采样子链 + `on_equipment_gained` 回调)。

**环境支**(`gain_invest_env`,正本 = gain-chain.md §2.1):`active_env` 注册 → portal 登记腿 best-effort(`register_portal_from_env`;`session=None` 跳过,失败留证不阻塞)→ `on_env_gained` 效果枚举。

## 4. 随机面

链入口 `rand=False` 确定性(两上报函数固定传 rand=False);效果体含采样(骇客改件)对其子链翻转 `rand=True`(gain-chain.md §5)。

## 5. 拒绝语义

- 无效载荷 = 零写:策略支链内拒绝 + 留证(输入拒绝,非防重复保护,gain-chain.md §2.4 腿 0);环境支缺名 = 零写 noop(`landing_noop`,选择事实缺名禁写);
- 重复上报 = 零幂等闸,跳写去重仅为数据卫生,bug 面按 bug 治理(gain-chain.md §2.4 腿 1)。

## 6. kernel 符号锚

- 词表:`kernel/cw_vocab.py::CwActionPickInvestStrategyParam` / `CwActionPickInvestEnvParam`;
- 注册行:`operations/cw_op/cw_action_registry.py`(两行同指 `CwActionPickInvestOp`);
- op:`operations/cw_op/cw_pick_invest_action.py::CwActionPickInvestOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;
- 上报:`kernel/cw_action_report/pick_invest_strategy.py` / `kernel/cw_action_report/pick_invest_env.py`;
- 链:`kernel/cw_gain_chain.py::gain_invest_strategy` / `gain_invest_env`。

## 7. 语义验证

- `test_cw_yinlang_phase32.py`(即时上报/无效载荷/去重/骇客链)、`test_cw_unified_action_4.py`(注册表分派)= 申报源 [../../screens/invest_strategy.md](../../screens/invest_strategy.md) §9;
- `test_cw_gain_chain.py`(链腿)。
