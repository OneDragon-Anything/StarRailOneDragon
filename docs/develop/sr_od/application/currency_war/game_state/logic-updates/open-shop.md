# 开店(OpenShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

备战画面点开商店面板——转场族动作,画面态周转(备战 → 商店面板块)。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionOpenShopParam`(单一形态,无受限变体;受限会话进出店同走本路径,访问内消费由策略决策入口自限)。op 载体 = `operations/cw_op/cw_open_shop_action.py::CwActionOpenShopOp`——**注册行 = terminal 承载行**(承载终结判定/等待的类属性:`terminal=True`,`terminal_wait=1.0`,消费点经注册表 `action_op_class_for` 读类属性,禁消费点私表);`execute` 抛 AssertionError——开店流程编排截流在 `operations/cw_screen/cw_screen_prep.py::_act_execute_default`(OpenShop 分支)→ `_open_shop_phase`,动作 op 不承载开店;可达(经注册表分派到本 op 执行)= 分派聚合入口被绕过,以显式报错防静默复活。

## 2. 逻辑态域集

容器(GameState,游戏状态对象,下同)**全域零写(显式申报「逻辑态 = 空」)**:开店 = 画面态周转,零局内资源变更;上报函数 = `zero_writes.py::report_action_open_shop_param`(零写族申报)。商店载荷/gold 真值由开店后的入口观察重建(`shop` 载荷域 = 由观察侧负责写入,路由清点独占)。

## 3. 确定面转移规则(逐条)

1. **显式开店**:`_open_shop_phase` → open_shop(规范动作形态:单段机械执行 + 发出即记账恒 True,2026-10-16 open-shop-action-spec;幂等归流程层——店已开由外循环 0n 三锚/`visit_open_shop` 入口观察判定)→ `visit_open_shop`(商店画面 op `cw_screen_shop.py::CwScreenShop` 节点直驱:入口观察 → `decide_shop_action` 单动作 round_wait 循环 + 逻辑态直写,终结动作=发出后即结束本次访问,收店并入画面 op);
2. **0n 转交**:店已开态由外循环三个 id_mark 识别标志确认,直接构造商店画面 op 访问(同口 `visit_open_shop`,零开店动作);
3. **发出即职责完成**:open_shop 的验关型失败回执消费已拆除——店实际开没开由下一帧观察侧对账自然闭环(备战帧读互斥;访问失败路径不开收,店留着交上层/外环重新识别)。

## 4. 随机面

无(开新店的首批牌面 = 随机面,归开店后入口观察重建)。

## 5. 拒绝语义

容器零写语义下无 `applied=False` 拒绝形态;开店失败 = 流程层编排轮次语义,归画面 op 层,不在本篇。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionOpenShopParam`;`operations/cw_op/cw_open_shop_action.py::CwActionOpenShopOp`(`terminal`/`terminal_wait` 类属性;execute 抛);`operations/cw_screen/cw_screen_prep.py::_act_execute_default`(OpenShop 截流)/ `_open_shop_phase` / `visit_open_shop`;`kernel/cw_action_report/zero_writes.py::report_action_open_shop_param`(零写申报)。

## 7. 语义验证

「逻辑态 = 空」的容器声明:本动作不改写局内资源,真值由开店后入口观察重建;无 M1 投影测试对象(零写族函数,不经商店/备战上报函数写域)。终结判定/等待时长消费 = 注册表类属性读取(`terminal_wait=1.0` 与原决策循环逐字等价,等价测试 = `test_cw_unified_action_3`)。

## 8. 判例注记(动作发出阶段)

备战期出口(与 CloseShop 对侧:备战/商店切换唯一通道);席满腾位链(关店 → 备战卖 → 重开,节点内重开牌面持久)以本动作收链。终态语义总表 = [screens/README](../../screens/README.md) §4。

## 9. 依据

`kernel/cw_vocab.py::CwActionOpenShopParam` docstring(形态语义);`operations/cw_screen/cw_screen_prep.py::_open_shop_phase` docstring(开店编排/失败不开收);`operations/cw_op/cw_open_shop_action.py` 模块头(terminal 承载行裁定);[../action-logic-state.md](../action-logic-state.md) §5(转场类动作逻辑态 = 空)。
