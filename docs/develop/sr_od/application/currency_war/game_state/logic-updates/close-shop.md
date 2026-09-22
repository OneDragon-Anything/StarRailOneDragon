# 关商店(CloseShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

收起商店面板回备战画面。**访问终结**动作、恒可用终结(全函数契约「无动作可做」的表达 = 策略器主动选关店)。op 载体 = `operations/cw_op/cw_close_shop_action.py::CwActionCloseShopOp`(`terminal=True`,执行位 = 真机械点击「按钮-收起」+ 幂等已关出口 + 自上报清场;终态契约「终结不入 decisions 行」,执行事实回执由动作 op 自身承担)。词表 = `kernel/cw_vocab.py::CwActionCloseShopParam`。

## 2. 逻辑态域集

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| shop | 上报函数写(结构离屏),生产跳写 | 上报函数腿 = `leave_screen(bs.shop)`(载荷语义失效;离屏写渠道 = obs 族,actor 沿逻辑态直写签名转造);**生产落地门对终结动作整体跳写**——牌面/gold 真值由下一段入口观察重建 |
| 其余全部域 | 跳写 | 关店本身不改任何局内资源事实 |

回执域(`receipts`):动作 op 执行体两出口各落一条(`kernel/cw_game_state.py::note_action_receipt` 唯一写点)——点击已发 = applied=true;幂等已关(「按钮-收起」不在)= applied=false + reason(无动作可发)。

## 3. 确定面转移规则(逐条)

1. shop 域结构离屏(上报函数 `report_action_close_shop_param` = `leave_screen`;`bs.shop.value` 非 None 才写);
2. **关店本身不改牌面事实**:节点内关店→重开**不刷新**(牌面持久),跨节点才自动刷新全店(`research/economy.md` §2.1)——牌面去留由节点推进事件锚定,不由本动作推算;
3. 执行体机械序:幂等入口观察(「收起」不在 = 店已关,直接成功)→ 点「按钮-收起」→ 固定等待 `SHOP_CLOSE_ANIM_S`(收起过场 ~1s,`research/screen_flow_timing.md` #15)→ 机械交回(零验证,收起消失与否归下一帧观察;点击未生效 = 外循环 0n 重分发自然重派,重派即重试)。

## 4. 随机面

无。

## 5. 拒绝语义

无拒绝形态(恒可用终结)。幂等已关出口的 applied=false 是「无动作可发」的簿记事实,不是失败。执行侧零判效(点没点上由重入观察裁决)。

## 6. kernel 符号锚

`kernel/cw_action_report/close_shop.py::report_action_close_shop_param`(`leave_screen`)/ `note_action_receipt`;`operations/cw_op/cw_close_shop_action.py::CwActionCloseShopOp`(执行体;原编排壳 `cw_op_close_shop.py::CwOpCloseShop` 已随执行位收编退役删除);终结语义总表 = [screens/README](../../screens/README.md) §4。

## 7. 语义验证(终结作废契约)

动作转移语义单一源 = 上报函数(`report_action_close_shop_param` = `leave_screen` 结构离屏)。原聚合写口调用面与原单步动作应用器 `simulate` 已随动作 op 重组与 sim 重做退役,考古归 git。投影直锁 M1(`test_cw_shop_projection_logic`)含 CloseShop 离屏腿;本动作期望态语义由「终结作废」契约承载——期望态随终结作废,由下一次入口观察重建,离屏域值失效等价于下帧观察全量覆盖。

## 8. 判例注记(发射期)

商店期收工动作(判例 = [screens/README](../../screens/README.md) §5:商店期默认面 = 买/刷/**关**);席满腾位链(关店 → 备战卖 → 重开,牌面持久)以本动作为链首。备战/商店切换的唯一终结通道(备战域 OpenShop 的对侧)。

## 9. 依据

`research/economy.md` §2.1(节点内关店重开不刷新);`research/screen_flow_timing.md` #15;`kernel/cw_action_report/close_shop.py::report_action_close_shop_param` docstring 与 `ShopActionExecuted.refresh_paid` 注(终结跳写申报);[screens/README](../../screens/README.md) §3.5/§4(访问终结语义)。
