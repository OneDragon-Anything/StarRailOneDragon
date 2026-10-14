# 刷新商店(RefreshShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

点击商店「按钮-刷新」,整店 5 槽全部重掷。**访问终结**动作(= 发出后结束本次访问,返回主循环重新识别画面):刷新是唯一引入新事实的动作,执行即本访问结束、返回主循环,重进 = 全新入口观察重建期望态(次数无硬墙;无限刷新环 = 策略实现 bug 框架不兜底)。op 载体 = `operations/cw_op/cw_refresh_shop_action.py::CwActionRefreshShopOp`(`terminal=True`,体内零读屏零验证);动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionRefreshShopParam`。

## 2. 逻辑态域集

| 域 | 写 / 跳写(跳写 = 留空不写、等观察覆盖) | 说明 |
|---|---|---|
| gold | 上报函数分支写,生产跳写 | 上报函数:`gold −= 实付刷新费`(仅 `executed.refresh_paid` 在场时写;生产 op 不喂——实付金含免费刷注入等差异不可自算,sim 与生产同一段 op 代码同不喂;显式喂入为上报函数保留的申报差异参数通道,在用零生产喂入方) |
| shop | **随机态写入(`write_logic_rand`)** | 刷新上报在计数后经 kernel 发牌采样器 `kernel/cw_shop_deal.py::sample_shop_deal`(与 sim `deal_shop` 同一发牌代码)采 5 槽 payload,经 `write_logic_rand` 随机态专用通道写——实机上采样是猜测,观察覆盖差异 = 预期内(落 `logic_rand_outcome` 记录行,不触发失配告警),真值 = 下一入口观察(以实际观察为准);level 缺读该分支跳写(概率表按级索引,宁缺勿造) |
| free_refresh_left | 免费帧写(逻辑态) | 免费判定 = Field 值 > 0(入口观察确认的剩余次数;None = 未观察 → 保守按付费,不扣 Field——次数是记账面非决策闸);免费帧 `write_logic` 扣减(max(0, left−1),下限 0) |
| refresh_total / refresh_paid(效果账本) | 写(计数分支) | 写入方 = 刷新上报函数经 `gs.effects.record_refresh` 单一入口(`kernel/cw_effect_inventory.py`);refresh_total 恒 +1,免费帧不动 refresh_paid(付费累计,长线利好阈值型,免费帧混入即污染) |
| shop_refresh_cost | **跳写** | 写入方 = 现场 OCR 唯一(观察通道);免费帧「免费」读数 None → 不落 0(付费域纯净性) |

## 3. 确定面转移规则(逐条)

1. **免费次数扣减**(Field 扣减):free 判定输入 = 显式 `free` 优先(喂入口保留,在用调用方恒 None),None 回退 Field 值判定;免费帧经 `write_logic(gs.free_refresh_left, max(0, left−1))` 扣减(produced_by/evidence 保留证据)。免费刷新的事实可见性 = Field 既有的失配告警(观察确认与动作扣减不符即停机)——零手写对账记录表;
2. **计数**(`record_refresh` 单一入口,未落地不计数):refresh_total 恒 +1;免费帧 refresh_paid 不写;同帧推进按策略触发计数(`bump_key(CounterKey.REFRESH)`,采购专员族门槛面)——「一次刷新,账本一处入账」;
3. **随机态写入**:采样器按 `REFRESH_PROB[level]` 费用档加权掷点 + 档内可进店名集均匀抽(`data/cw_shop_odds.py` 注册表;剩余牌库派生 = `kernel/cw_pool.py::drawable_names`),逐槽独立、允许重复同名;sim 与实机走同一发牌代码(两执行面同源,详见 [../../flow/projection_contract.md](../../flow/projection_contract.md) §3.6);
4. **金币扣减**(条件分支):`gold −= executed.refresh_paid`(免费帧 0 不写;在用生产与 sim 同跳写,喂入通道保留)。

## 4. 随机面

**刷后的新牌面 = 整店 5 槽全换**(非逐槽补空,实机实证 `research/economy.md` §2.1)→ 上报函数以随机态采样预写期望态(`write_logic_rand` 通道;观察覆盖 = 预期内),真值归下一入口观察。免费刷新的概率事件(免费次数获得)= 两效果桥发放(`apply_effect_burst_grant`/`grant_effect_node_refresh_balance`,容器 Field 同格登记,见 [../fields.md](../fields.md) 商店免费刷新节)。

**UI 陷阱已登记**:面板右下「刷新金币数」区域实际印的是利息徽标(min(gold//10,5)),不是刷价(三路来源交叉核对后已定案,`REFRESH_COST_BASE` 注)。

## 5. 拒绝语义

无拒绝形态(刷新恒可发):上报函数 `applied` 恒 True——计数即职责完成,调用方仅在动作实际发出后进本口(未落地不计数)。决策侧刷新允许性(利息线门槛等策略判据,详见 strategy-docs/23_shop_screen.md)归策略面,不在本篇。

## 6. kernel 符号锚

`kernel/cw_action_report/refresh_shop.py::report_action_refresh_shop_param`(计数 + Field 免费次数扣减 + 随机态写入单一入口);`kernel/cw_shop_deal.py::sample_shop_deal`(发牌采样器);`kernel/cw_effect_inventory.py::record_refresh`(计数入账);`kernel/cw_economy.py::REFRESH_COST_BASE`(刷价缺读回退常量);`operations/cw_op/cw_refresh_shop_action.py::CwActionRefreshShopOp`。

## 7. 语义验证(M1 直锁)

刷新动作转移语义单一源 = 上报函数。原 `simulate` RefreshShop 分支(仅扣金、不模拟牌面)与动作侧真值读取/证据票据已随迭代停用,考古归 git。投影直锁 M1(`test_shop_projection_logic`:付费刷新扣金/免费帧金域不写/免费次数 Field 扣减,均在锁内)。差异申报保留:金币分支仅 sim 喂 `executed.refresh_paid`——引擎差异参数通道,非规则分叉。

## 8. 判例注记(动作发出阶段)

商店期默认动作面 = 买牌/刷新/关店(判例 = [screens/README](../../screens/README.md) §5);刷新在列,发出判据 = strategy-docs/23_shop_screen.md(利息线门槛等)。备战域无刷新动作(刷新属商店画面)。

## 9. 依据

`research/economy.md` §2(刷价 2 金恒定与 UI 陷阱)/§2.1(整店全换/节点切换自动刷新);[fields.md](../fields.md)(商店免费刷新 `free_refresh_left` Field 三个写入来源);[shop.md](../../screens/shop.md)(访问终结语义)。
