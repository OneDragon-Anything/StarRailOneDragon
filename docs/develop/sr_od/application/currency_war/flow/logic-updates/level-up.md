# 买经验(LevelUp / LevelUpShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

点击「购买经验」按钮一次 = +`XP_PER_BUY` 经验、扣单击价金;经验攒满当前级门槛即升级、溢出结转(单击经验模型,ADR-0129)。两形态一词表:商店单击形态 `LevelUpShop`(is-a `LevelUp`,op = `operations/cw_op/cw_level_up_action.py::LevelUpOp`,单动作形态每帧恰发一击);备战逐帧单击形态(粒度定案④/R6:升 N 击 = N 帧各发一次,执行器授权面全删)。词表 = `kernel/cw_vocab.py::LevelUp`。

## 2. 逻辑态域集

**商店域写口** = `kernel/cw_game_state.py::apply_shop_action_logic` LevelUpShop 腿(`isinstance` LevelUp 消费):

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| gold | 写 | `gold −= 动作 cost × 实击数`;None 跳写 |
| xp | 写 | 二元组 `(当前级已攒, 升下一级门槛)`,推进算子单一源 = `xp_apply_clicks`(跨级结转 + 满级封顶零推进) |
| level | **跳写(域集封闭申报)** | 升档等观察覆盖;`level` 不在 `SHOP_PROJECTION_DOMAINS` |
| shop / bench / equips | 跳写 | 修饰效果副作用(商业间谍偷牌/晋升名额变费)未建模,后果归观察(缺口 G7/G8) |

**备战域写口** = `kernel/cw_game_state.py::apply_prep_action_logic` LevelUp 分支:域集 = xp/**level**/gold 子集(`PREP_PROJECTION_DOMAINS`;备战域 level **写**,与商店域 level 跳写的域集差异 = 各域集封闭申报面)。**deploy_cap 不写**——容量真值由观察写端防抖读承接(`max_units` 的 cap<level 兜底规则保守承接升级增量)。level/xp 缺读 = 域级跳写。

## 3. 确定面转移规则(逐条)

1. 每击:+`XP_PER_BUY` 经验、−单击价;攒满当前级门槛(`XP_TO_NEXT_LEVEL`)即升级、溢出结转(推进算子单一源 = `kernel/cw_economy.py::xp_apply_clicks`;封顶 `MAX_PLAYER_LEVEL`);
2. **单击价单一源** = `kernel/cw_economy.py::xp_click_cost` 两支语义:**显示价支**(容器 `level_up_cost` 观察价直通——游戏侧已算好全部折扣,下限 0)/ **兜底支**(基价 `XP_CLICK_COST_FALLBACK` 减在册折扣:`xp_buy_cost_discount` + 等级门折扣 `xp_click_discount_from_level`,`level_of(bs) ≥ xp_click_discount_from_level_at` 生效;折扣只降价不减经验)。发射面把现算值装进 `action.cost`,转移函数按 `action.cost` 扣减(商店域 × 击数,备战域单击);
3. 金:gold `−=` 单击价 × 实击数。商店域击数 = 执行回执 `ShopActionExecuted.levelup_clicks`(生产落地门喂 1;缺回执 = `applied=False, reason='levelup_clicks_not_fed'` 本轮不写,等观察覆盖)。**备战域金腿 = `action.cost` 直写**(本口唯一写点,批 2b 翻转已落码;原 2a 中间态执行缝金差 `_executed_gold_delta` 对 LevelUp 恒 0/退役,防双记);
4. 授权/发射门全在决策核发射位(备战域):每帧发射前置 = `clicks_to_next_level` 现算击数 > 0;金地板(`spend_unified`)/预算闸(`levelup_budget_gate`)/血闸(`blood_xp_gate`)/血本位模式(`blood_xp_gate_for`)= 发射位门链;满级 = 击数 0,无授权不发射。执行器 `PrepActionExecutor._level_up` 零授权零计数(找钮 → 单击 → 光标 parking 防等级显示区毒化 → 升级事件挂点 `effects.on_level_up()`);
5. 经验/等级真值 = 下一帧观察经验对账族承接(XpLedger 通道单击推进 + OCR 真值 reconcile)。

**文档-实现偏差(action-logic-state.md §3.3)**:原文「金腿(批 2a 中间态)= 执行缝金差……`action.cost` 直写随批 2b 翻转生效」;实况 = 批 2b 翻转已落码,金腿 = `apply_prep_action_logic` LevelUp 分支按 `action.cost` 直写(`kernel/cw_exec_state.py::apply_op_effect` else 分支注与 `prep_actions.py::PrepActionExecutor._level_up` docstring 同证),执行缝金差对 LevelUp 退役。本篇按实现写入。

## 4. 随机面

无。修饰效果副作用(商业间谍「升级时刷新商店并偷最贵 3 张」、晋升名额「买经验时随机一槽变高 1 费」)未建模,后果归观察(缺口 G7/G8)。

## 5. 拒绝语义

- **满级点击无效**:商店域 `level_of(bs) ≥ MAX_PLAYER_LEVEL` → `applied=False, reason='level_cap'`,零写(零金零经验);备战域 = 发射面击数 0 不发(无授权不发射),`xp_apply_clicks` 内部同门封顶;
- 击数回执缺失:`applied=False, reason='levelup_clicks_not_fed'` 跳写;
- 血本位模式(奋斗协议):成本币种切血,金费函数出域,血闸独立车道(`blood_xp_gate`,fail-closed)。

## 6. kernel 符号锚

`kernel/cw_game_state.py::apply_shop_action_logic`(LevelUpShop 腿)/ `apply_prep_action_logic`(LevelUp 分支);`kernel/cw_economy.py::xp_apply_clicks` / `xp_click_cost` / `clicks_to_next_level` / `XP_PER_BUY` / `XP_TO_NEXT_LEVEL` / `XP_CLICK_COST_FALLBACK` / `MAX_PLAYER_LEVEL` / `blood_xp_gate` / `blood_xp_gate_for`;`prep_actions.py::PrepActionExecutor._level_up`;发射面 cost 装载 = `strategies/impl/mandate_v1/shop.py`(xp_click_cost 现算 → LevelUpShop)与 `strategies/impl/mandate_v1/entry.py`。

## 7. 与 sim simulate 的等价关系(M1 锁)

`kernel/cw_vocab.py::simulate` LevelUp 分支 = 第二载体:满级门同源(`MAX_PLAYER_LEVEL`)、`s.gold -= action.cost`、xp 单击步长 + while 门槛结转——与容器转移函数逐位等价(锁 M1;满级拒绝语义两载体同形)。`LevelUpShop ≡ LevelUp`(同字段类型归一后全等,对拍口径)。备战域为语义源平移关系(单击步长同算子 `xp_apply_clicks`)。

## 8. 判例注记(发射期)

**能力面在役、策略面收缩至备战期**(判例 = [../screens-actions-capability.md](../screens-actions-capability.md) §5,2026-09-14):商店开画面的 LevelUpOp 机制上可用,但默认策略**不在商店期买经验**——升等级收缩至备战期决策(strategy-docs/22 号篇)。备战域逐帧单击形态 = 升级唯一生产发射面。

## 9. 依据

`research/xp-rules.md` §2(购买经验单价/门槛表/折扣只降价不减经验);`kernel/cw_economy.py::xp_click_cost` docstring(两支语义与出域声明);[../game_state/fields.md](../../game_state/fields.md) §3.2.10/§3.2.11(level/xp/level_up_cost)/§4.2 LevelUp 行;design.md unified-action-factory §2.6 LevelUp 粒度定案④。
