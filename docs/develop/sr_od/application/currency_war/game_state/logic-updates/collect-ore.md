# 采晶矿(ClickSpheres)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

点击备战画面奖励面板的晶矿,点开后晶矿金由游戏侧异步入账。op 载体 = `operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`(批3 体迁,`prep_actions.py::PrepActionExecutor._collect_ore` 薄委托);词表 = `kernel/cw_vocab.py::CwActionCollectOreParam`(`points` = 按点击序的晶矿心坐标列)。发射条件 = 备战策略产 ClickSpheres(点击列由决策侧现算,见 §3)。

## 2. 逻辑态域集

容器 GameState **金域零写**(域级申报):晶矿金金额在执行点不可推算(实机样本 +4/+7/+6 无界,数据注册表无晶矿金数值表 = 声明盲区)——按效果写入归属判据,含随机面不建逻辑写端,金真值归观察收口(上报函数 `report_action_collect_ore_param`:金账零推进申报)。

**本动作的逻辑态计算 = 窗登记**:op 自上报 `report_action_collect_ore_param` 按 payload 晶矿数开**备战环随机收入待吸收窗**(session 形参在场时)——`game_state_of(session).exec_books.prep_sphere_income_pending += len(action.points)`(唯一写端)。窗 = `kernel/cw_game_state.py::ExecBooks.prep_sphere_income_pending`(非 Field 过程簿记,计数坐标系 = 本局采晶矿个数,局级清零)。

**视觉域容器翻转**(迭代 2026-09-18-prep-obs-retirement 阶段 3.4/3.5):晶矿载荷进容器 `spheres` 域(`SphereSight.points`),**容器摘晶矿腿与窗登记内聚同一上报函数** = `report_action_collect_ore_param`——按载荷坐标精确摘除(坐标匹配,原黑板腿逐位迁移;域未观察/载荷无交集 = 陈旧提案零写;count/colors 同步重算)。

## 3. 确定面转移规则(逐条)

1. **机械执行**:载荷即点击列,纯机械逐个点(mouse_move + click + park),零读屏、零排序、零截断——大晶矿优先/上界挑选归决策侧 kernel `kernel/cw_prep_actions.py::select_ore_clicks`(发射位现算,上界 = `SPHERE_CLICK_HARD_CAP`);
2. **窗登记**:发出后 op 自上报 `report_action_collect_ore_param` 按载荷晶矿数累加 `prep_sphere_income_pending`(推进失败不阻塞执行链);
3. **正向差吸收**(观察边界,game state 侧执行):窗在时逻辑金被实读证伪的唯一合法形状 = 正向差 → `kernel/cw_game_state.py::GameState._absorb_prep_sphere_income` 命中,落 `prep_sphere_income_absorbed` 台账行(无告警无停机,豁免 ≠ 消失同纪律)后清窗、覆盖照常采新;
4. **收口**:店开帧金观察(`sig.screen` = 货币战争-备战-开商店)是备战随机收入窗末站——`GameState.observe` 在该帧无条件清窗(晶矿金到账、晶矿金为 0 或点击落空在此都有了结;窗不跨轮存续,防虚额残留吞后续正向失配);
5. 固定等待 2s 等飞行动画(`operations/cw_op` 固定等待族;等待不是判效)。

## 4. 随机面 / 观察面

晶矿金金额与到账时机 = 随机面归观察(§2 申报盲区);被点的晶矿从视觉帧摘除是确定面,未被点开的晶矿(席满搁浅等)由下一帧观察 `spheres` 现读回补。

**红线与已知盲区**(显式申报,正本 = `ExecBooks.prep_sphere_income_pending` 字段注):窗关时正向失配照真失配停 / 负差照停(收入不可负,负差 = 推算 bug)/ 店开帧后照停;窗内「卖退款投影少算」类纯 gold 正向 bug 无行域痕迹会被本窗吞(低概率,申报残留面);与节点边界金闩(`boundary_gold_mode`)双窗并存时,边界闩先行消费正差则本窗顺延到店开帧收口——金额归因混账为已申报的放宽方向,兜底 = bench/board 行域失配面独立把守。

## 5. 拒绝语义

无拒绝形态(纯机械恒发出):`points` 为空由发射位不产动作;词表 `validate` 静态参数拒 = 发出前输入契约拒绝(`emitted=False`,非判效);点击未生效 = 观察侧对账显影(§3 第 3 条反向:负差/无窗失配照停)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionCollectOreParam`;`kernel/cw_prep_actions.py::select_ore_clicks` / `ore_click_targets_of` / `SPHERE_CLICK_HARD_CAP`;`kernel/cw_action_report/click_spheres.py::report_action_collect_ore_param`(容器精确摘晶矿 + 窗登记内聚单点)/`ExecBooks.prep_sphere_income_pending` / `GameState._absorb_prep_sphere_income` / `GameState.observe`(店开帧收口);`operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`。

## 7. 语义验证

金域零写语义 = 「消费真值归观察」契约 + 上报函数申报(零金推进);容器摘晶矿腿 = `report_action_collect_ore_param` 单点(测试锚 `test_collect_ore_container_precise_drop`/`test_sphere_empty_read_yields_no_targets`);窗语义 = 失配精确吸收第三例(20260918-reconcile 第 9 例收口),吸收行为由观察边界测试与台账行(`prep_sphere_income_absorbed`)承载。

## 8. 判例注记(发射期)

备战期(奖励面板只在备战画面;发射位 = 备战策略 `strategies/impl/mandate_v1/entry.py` prep_spheres,席满搁浅走策略侧 defer 计数)。商店期无本动作。

## 9. 依据

`kernel/cw_game_state.py::ExecBooks.prep_sphere_income_pending` 字段注(机理/红线/盲区正本);`kernel/cw_action_report/click_spheres.py::report_action_collect_ore_param` docstring(容器精确摘晶矿 + 窗登记);[flow/action_ops.md](../../flow/action_ops.md) §4.2 ClickSpheres 行/§2.2 固定等待族;[fields.md](../fields.md) §3.2.8(晶矿)。
