# 刷新商店(RefreshShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

点击商店「按钮-刷新」,整店 5 槽全部重掷。**段终结**动作:刷新是唯一引入新事实的动作,执行即本段结束,下一段入口观察重建期望态。op 载体 = `operations/cw_op/cw_refresh_shop_action.py::RefreshShopOp`(`terminal=True`);词表 = `kernel/cw_vocab.py::RefreshShop`。

## 2. 逻辑态域集

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| gold | 转移函数腿写,生产跳写 | 转移函数:`gold −= 实付刷新费`(paid>0 才写,None 跳写);**生产落地门对终结动作整体跳写**(期望态按下段入口重观察作废,`ShopActionExecuted.refresh_paid` 申报注)——现役喂入方 = sim/回放驱动器 |
| shop | **跳写(域级)** | 刷后牌面 = 整店 5 槽全换(随机面)→ payload 本动作不写,新牌面归下一段入口观察;模拟器同口径(「shop 内容变化未知,不模拟具体牌;仅扣金」) |
| total_refresh_count / paid_refresh_count / free_refresh_balance | 写(计数组腿) | 容器写端 = 刷新执行落地门 `kernel/cw_game_state.py::record_refresh_execution`,生产在役(终结跳写不影响计数组——它挂在落地门的 RefreshShop 分支,先于终结门) |
| shop_refresh_cost | **跳写** | 写端 = 现场 OCR 唯一(ADR-0622 观察通道);免费帧「免费」读数 None → 不落 0(付费域纯净性) |
| xp(按刷产经验修饰) | 修饰腿写 | 淘金客 `xp_per_refresh` = 经验域 logic 写(fields.md §4.2 修饰段) |

## 3. 确定面转移规则(逐条)

1. **金腿**(转移函数腿):`gold −= 实付刷新费`。刷价真值 = 容器 `shop_refresh_cost`(备战帧现场 OCR,ADR-0622;缺读 = 建模基价 `REFRESH_COST_BASE` 显式缺省,`kernel/cw_economy.py::refresh_cost_effective`)。免费帧(paid=0)金域不写。免费刷新来源(概率事件 / 按节点免费额度)只影响实付金,不改「整店全换」;
2. **计数组腿**(`record_refresh_execution`,写入 = 仅逻辑,未落地不计数):`total_refresh_count` 恒 +1;免费帧 `paid_refresh_count` **不写**(付费域纯净性,长线利好触发载体防毒化)且 `free_refresh_balance` −1(下限 0);付费帧 `paid_refresh_count` +1。计数从未写过(None)按 0 基线起算(局内单调累计的构造事实);免费判定输入 = 刷前按钮态 UI 真值优先(`ShopVisitLedger.refresh_free_truth`),失读回退逻辑账余额(余额未建模局恒 paid = 保守形态);真值↔逻辑账分歧落缺陷票(零决策留证);
3. **效果账计数腿**:`apply_action_outcome` 内 `effects.bump_key(CounterKey.REFRESH)`(采购专员族门槛计数面,挂执行落地门);
4. 执行侧留证:刷前金/刷前牌名/待对账标记三件进 ledger(对账收口在观察侧,op 内零比对,`REFRESH_CLICK_SETTLE_WAIT_S` 固定等待);牌名集前后三值对比仅作安灯豁免判定输入 + 遥测字段(非判效)。

## 4. 随机面

**刷后的新牌面 = 整店 5 槽全换**(非逐槽补空,实机实锤 `research/economy.md` §2.1)→ 店载荷失效,新牌面归下一段入口观察。免费刷新的 proc(概率事件 45%)也是随机面(留证通道 = 牌面已变 ∧ 金未扣 → 截图 + flag,不停机)。

**UI 陷阱在册**:面板右下「刷新金币数」区域实际印的是利息徽标(min(gold//10,5)),不是刷价(三流对拍定谳,`REFRESH_COST_BASE` 注)。

## 5. 拒绝语义

- 转移函数无 executed 回执(`refresh_paid=None`)= `applied=False, reason='refresh_paid_not_fed'` 跳写(实付金含免费刷注入等引擎差异不可自算;sim 引擎显式传 `refresh_paid` = 申报差异参数通道);
- 生产侧无 applied=False 拒绝形态(刷新恒可发);visit 级刷新硬墙 = `MAX_REFRESH`(`cw_screen_buy_cards.py`,超墙终结集降级仅关店,`../../screens/shop.md` §5)是发射面预算闸,非转移函数拒绝。

## 6. kernel 符号锚

`kernel/cw_game_state.py::apply_shop_action_logic`(RefreshShop 腿)/ `record_refresh_execution`;`kernel/cw_economy.py::REFRESH_COST_BASE` / `refresh_cost_effective` / `SHOP_REFRESH_COST`(赋值别名,非第二源);`kernel/cw_vocab.py::simulate`(RefreshShop 分支);执行落地门 = `operations/cw_screen/cw_screen_buy_cards.py::apply_action_outcome`(计数组 + 效果账计数挂点);`operations/cw_op/cw_refresh_shop_action.py::RefreshShopOp`。

## 7. 与 sim simulate 的等价关系(M1 锁)

`simulate` RefreshShop 分支 = `s.gold -= action.cost`,shop 不模拟(随机面同口径);容器转移函数逐腿同式(金腿 + payload 跳写)。差异申报:sim 显式喂 `refresh_paid`,生产终结跳写——差异归属 = 「终结动作整体跳写」的申报过渡语义,非规则分叉(锁 M1 辖非终结动作的逐位等价)。

## 8. 判例注记(发射期)

商店期默认动作面 = 买牌/刷新/关店(判例 = [screens/README](../../screens/README.md) §5);刷新在列,发射判据 = strategy-docs/23_shop_screen.md(息线门 R1 等)。备战域无刷新动作(刷新属商店画面)。

## 9. 依据

`research/economy.md` §2(刷价 2 金恒定与 UI 陷阱)/§2.1(整店全换/节点切换自动刷新);[fields.md](../fields.md) §3.3.4–§3.3.9(刷价与免费刷新族)/§4.2 RefreshShop 行(计数组行为口径与免费帧闸);[shop.md](../../screens/shop.md)(visit 级刷新硬墙)。
