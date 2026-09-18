# 开店(OpenShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

备战画面点开商店面板——转场族动作,画面态周转(备战 → 商店面板块)。词表 = `kernel/cw_vocab.py::CwActionOpenShopParam`(两形态字段:`read_only` 读数性开店 / `restricted_spend` 受限访问)。op 载体 = `operations/cw_op/cw_open_shop_action.py::CwActionOpenShopOp`——**注册行 = terminal 承载行**:类属性承载终结判定/等待(`terminal=True`,`terminal_wait=1.0`,消费点经注册表 `action_op_class_for` 读类属性,禁消费点私表);`execute` 抛 AssertionError——开店流程编排截流在 `operations/cw_screen/cw_screen_prep.py::_act_execute_default`(OpenShop 分支)→ `_open_shop_phase`,动作 op 不承载开店;可达(经注册表分派到本 op 执行)= 分派漏斗被绕过,响亮暴露防静默复活。

## 2. 逻辑态域集

容器 GameState **全域零写(显式申报「逻辑态 = 空」)**:开店 = 画面态周转,零局内资源变更;上报函数 = `zero_writes.py::report_action_open_shop_param`(零写族申报,含 read_only)。商店载荷/gold 真值由开店后的入口观察重建(`shop` 载荷域 = 观察写端,路由清点独占)。

## 3. 确定面转移规则(逐条)

1. **restricted_spend=True**(受限访问 = 发射帧仲裁意图,金出口族出口 B;判定单一源 = 策略前置发射位经 kernel `in_launch_spend_zone`):`_act_execute_default` 截流 → `operations/cw_loop.py::_launch_frame_arbitration`——仲裁单元自含预检/域判/预算闸(花后金位跌破息线即拒)/第三载体行,本帧不发射次帧复判;
2. **read_only=True**(读数性开店:腾席链 b 取 gold 真值 / 开态清洁面板):`_open_shop_phase` → `cw_op_open_shop.open_shop`(幂等,已开不点)→ heavy 观察(gold 开态真值进 session;帧代次 = none,不接商店决策——M-6 门 free=0 不进买牌)→ `cw_op_close_shop.close_shop` → 节点探针 → 回备战;回执 `(progressed, detail)` = 读数性开店事实(非动作成败回执);
3. **read_only=False**(显式开店):`_open_shop_phase` → open_shop → `visit_open_shop`(商店单动作循环 run_buy_waves:入口观察 → `decide_shop_action` 逐动作循环 + 逻辑态直写,终结 op 交回;`MAX_REFRESH` 硬墙)→ CwOpCloseShop → finalize_buy_phase → 节点探针;
4. **发出即职责完成**:open_shop/close_shop 的验关型失败回执消费已拆除——店实际开没开由下一帧观察侧对账自然闭环(heavy 观察 gold 真值/备战帧读互斥;波循环失败路径不开收语义不变)。

## 4. 随机面

无(开新店的首批牌面 = 随机面,归开店后入口观察重建)。

## 5. 拒绝语义

容器零写语义下无 `applied=False` 拒绝形态;开店失败 = 流程层编排轮次语义,归画面 op 层,不在本篇。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionOpenShopParam`;`operations/cw_op/cw_open_shop_action.py::CwActionOpenShopOp`(`terminal`/`terminal_wait` 类属性;execute 抛);`operations/cw_screen/cw_screen_prep.py::_act_execute_default`(OpenShop 截流)/ `_open_shop_phase` / `visit_open_shop`;`operations/cw_loop.py::_launch_frame_arbitration`(restricted_spend 仲裁);`kernel/cw_action_report/zero_writes.py::report_action_open_shop_param`(零写申报)。

## 7. 语义验证

「逻辑态 = 空」的容器声明:本动作不改写局内资源,真值由开店后入口观察重建;无 M1 投影直锁对象(零写族函数,不经商店/备战上报函数写域)。终结判定/等待时长消费 = 注册表类属性读取(`terminal_wait=1.0` 与原决策循环逐字等价,等价测试锁 = `test_cw_unified_action_3`)。

## 8. 判例注记(发射期)

备战期出口(与 CloseShop 对侧:备战/商店切换唯一通道);席满腾位链(关店 → 备战卖 → 重开,节点内重开牌面持久)以本动作收链。终态语义总表 = [screens/README](../../screens/README.md) §4。

## 9. 依据

`kernel/cw_vocab.py::CwActionOpenShopParam` docstring(两形态语义);`operations/cw_screen/cw_screen_prep.py::_open_shop_phase` docstring(read_only 分支/节点探针挂点/失败不开收);`operations/cw_op/cw_open_shop_action.py` 模块头(terminal 承载行裁定);[../action-logic-state.md](../action-logic-state.md) §5(转场类动作逻辑态 = 空)。
