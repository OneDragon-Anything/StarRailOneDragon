# 采晶矿(ClickSpheres)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

点击备战画面奖励面板的晶矿,点开后晶矿金由游戏侧异步入账。op 载体 = `operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`(批3 体迁,`prep_actions.py::PrepActionExecutor._collect_ore` 薄委托);词表 = `kernel/cw_vocab.py::CwActionCollectOreParam`(`points` = 按点击序的晶矿心坐标列)。发射条件 = 备战策略产 ClickSpheres(点击列由决策侧现算,见 §3)。

## 2. 逻辑态域集

容器 GameState **金域零写**(域级申报):晶矿金金额在执行点不可推算(实机样本 +4/+7/+6 无界,数据注册表无晶矿金数值表 = 声明盲区)——按效果写入归属判据,含随机面不建逻辑写端。

**本动作的逻辑态计算 = 容器摘晶矿**:op 自上报 `report_action_collect_ore_param` 按载荷坐标从容器 `spheres` 域(`OreSight.points`)精确摘除被点的晶矿(坐标匹配;域未观察/载荷无交集 = 陈旧提案零写;count/colors 同步重算)。金真值归观察收口:**当前无金吸收规则**(随机对账申报面 2026-09-19 拆除待重设计),晶矿金入账造成的金对账失配照真失配停。

## 3. 确定面转移规则(逐条)

1. **机械执行**:载荷即点击列,纯机械逐个点(mouse_move + click + park),零读屏、零排序、零截断——大晶矿优先/上界挑选归决策侧 kernel `kernel/cw_prep_actions.py::select_ore_clicks`(发射位现算,上界 = `SPHERE_CLICK_HARD_CAP`);
2. **容器摘晶矿**:发出后 op 自上报 `report_action_collect_ore_param` 精确摘除被点晶矿(推进失败不阻塞执行链);
3. 固定等待 2s 等飞行动画(`operations/cw_op` 固定等待族;等待不是判效)。

## 4. 随机面 / 观察面

晶矿金金额与到账时机 = 随机面归观察(§2 申报盲区);被点的晶矿从视觉帧摘除是确定面,未被点开的晶矿(席满搁浅等)由下一帧观察 `spheres` 现读回补。

**已知缺口**(显式申报):晶矿金入账后下一备战帧金观察对逻辑态失配现无吸收规则(随机对账申报面拆除待重设计),照真失配停;重设计方向 = 晶矿金到账建模或对账规则,落地前本动作在含购买投影的轮次会响停。

## 5. 拒绝语义

无拒绝形态(纯机械恒发出):`points` 为空由发射位不产动作;词表 `validate` 静态参数拒 = 发出前输入契约拒绝(`emitted=False`,非判效);点击未生效 = 观察侧对账显影(`spheres` 现读回补未摘晶矿)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionCollectOreParam`;`kernel/cw_prep_actions.py::select_ore_clicks` / `ore_click_targets_of` / `SPHERE_CLICK_HARD_CAP`;`kernel/cw_action_report/click_spheres.py::report_action_collect_ore_param`(容器精确摘晶矿)/`GameState.observe`(金真值观察收口);`operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`。

## 7. 语义验证

金域零写语义 = 「消费真值归观察」契约 + 上报函数申报(零金推进);容器摘晶矿腿 = `report_action_collect_ore_param` 单点(测试锚 `test_collect_ore_container_precise_drop`)。

## 8. 判例注记(发射期)

备战期(奖励面板只在备战画面;发射位 = 备战策略 `strategies/impl/mandate_v1/entry.py` prep_spheres,席满搁浅走策略侧 defer 计数)。商店期无本动作。

## 9. 依据

`kernel/cw_action_report/click_spheres.py::report_action_collect_ore_param` docstring(容器精确摘晶矿);[flow/action_ops.md](../../flow/action_ops.md) §4.2 ClickSpheres 行/§2.2 固定等待族;[fields.md](../fields.md) §3.2.8(晶矿)。
