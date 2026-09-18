# 买经验(LevelUp / LevelUpShop)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

点击「购买经验」按钮一次 = +`XP_PER_BUY` 经验、扣单击价金;经验攒满当前级门槛即升级、溢出结转(单击经验模型,ADR-0129)。两形态一词表、一注册行:注册行 = `operations/cw_op/cw_prep_level_up_action.py::CwActionLevelUpOp`(词表摊平后 LevelUp/LevelUpShop 同字段双类型共用本 op,唯一活执行路径;`LevelUpShop` 经注册表独立行同解析本 op——商店屏升级意图与备战单击同构,升 N 击 = N 帧各发一次);原商店域 op 文件 `operations/cw_op/cw_level_up_action.py::LevelUpOp` = **已退役删除**(动作 op 重组批③注销登记,能力面语义由上报函数保留,判例见 screens/README §5)。词表 = `kernel/cw_vocab.py::CwActionLevelUpParam`(LevelUpShop = 同字段双类型 `CwActionLevelUpShopParam`)。

## 2. 逻辑态域集

**商店域写口** = 上报函数 `kernel/cw_action_report/level_up.py::report_action_level_up_param`(LevelUpShop 同字段双类型,经 `level_up_shop.py::report_action_level_up_shop_param` 一行委托同函数):

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| gold | 写 | `gold −= 动作 cost × 实击数`;None 跳写 |
| xp | 写 | 二元组 `(当前级已攒, 升下一级门槛)`,推进算子单一源 = `xp_apply_clicks`(跨级结转 + 满级封顶零推进) |
| level | **条件写**(2026-09-18 扩面) | 升档直写:跨档才写(`proj_levelup_level`);跳写对 = (level, xp) 同进退,任一未读整体跳写——等级滞留会让下一击按旧级重算(花金零等级推进),而等级 = 席位 cap 解锁地板(`max_units_of` 经读口自动跟随)。`level` 在 `SHOP_PROJECTION_DOMAINS`(域集封闭申报) |
| shop / bench / equips | 跳写 | 修饰效果副作用(商业间谍偷牌/晋升名额变费)未建模,后果归观察(缺口 G7/G8) |

**备战域写口** = 同一上报函数 `report_action_level_up_param`(双域腿统一单点):写域 = xp/**level**/gold(跳写对 (level, xp) 同进退,申报面 = 函数 docstring)。**deploy_cap 不写**——容量真值由观察写端防抖读承接(`max_units` 的 cap<level 兜底规则保守承接升级增量)。level/xp 缺读 = 域级跳写。

## 3. 确定面转移规则(逐条)

1. 每击:+`XP_PER_BUY` 经验、−单击价;攒满当前级门槛(`XP_TO_NEXT_LEVEL`)即升级、溢出结转(推进算子单一源 = `kernel/cw_economy.py::xp_apply_clicks`;封顶 `MAX_PLAYER_LEVEL`);
2. **单击价单一源** = `kernel/cw_economy.py::xp_click_cost` 两支语义:**显示价支**(容器 `level_up_cost` 观察价直通——游戏侧已算好全部折扣,下限 0)/ **兜底支**(基价 `XP_CLICK_COST_FALLBACK` 减在册折扣:`xp_buy_cost_discount` + 等级门折扣 `xp_click_discount_from_level`,`level_of(bs) ≥ xp_click_discount_from_level_at` 生效;折扣只降价不减经验)。发射面把现算值装进 `action.cost`,转移函数按 `action.cost` 扣减(商店域 × 击数,备战域单击);
3. 金:gold `−=` 单击价 × 实击数。击数 = 执行回执 `ShopActionExecuted.levelup_clicks`(生产落地门喂 1;缺回执 = `applied=False, reason='levelup_clicks_not_fed'` 本轮不写,等观察覆盖)。**金腿 = 上报函数按 `action.cost`×击数直写**(本口唯一写点,批 2b 翻转已落码;原 2a 中间态执行缝金差 `_executed_gold_delta` 对 LevelUp 恒 0/退役,防双记);
4. 授权/发射门全在决策核发射位(备战域):每帧发射前置 = `clicks_to_next_level` 现算击数 > 0;金地板(`spend_unified`)/预算闸(`levelup_budget_gate`)/血闸(`blood_xp_gate`)/血本位模式(`blood_xp_gate_for`)= 发射位门链;满级 = 击数 0,无授权不发射。执行器 `PrepActionExecutor._level_up` 零授权零计数(找钮 → 单击 → 光标 parking 防等级显示区毒化 → 升级事件挂点 `effects.on_level_up()`);
5. 经验/等级真值 = 下一帧观察经验对账族承接(XpLedger 通道单击推进 + OCR 真值 reconcile)。

**文档-实现偏差(action-logic-state.md §3.3)**:原文「金腿(批 2a 中间态)= 执行缝金差……`action.cost` 直写随批 2b 翻转生效」;实况 = 批 2b 翻转已落码,金腿 = 上报函数 `report_action_level_up_param` 按 `action.cost` 直写(`prep_actions.py::PrepActionExecutor._level_up` docstring 同证),执行缝金差对 LevelUp 退役。本篇按实现写入。

## 4. 随机面

无。修饰效果副作用(商业间谍「升级时刷新商店并偷最贵 3 张」、晋升名额「买经验时随机一槽变高 1 费」)未建模,后果归观察(缺口 G7/G8)。

## 5. 拒绝语义

- **满级点击无效**:商店域 `level_of(bs) ≥ MAX_PLAYER_LEVEL` → `applied=False, reason='level_cap'`,零写(零金零经验);备战域 = 发射面击数 0 不发(无授权不发射),`xp_apply_clicks` 内部同门封顶;
- 击数回执缺失:`applied=False, reason='levelup_clicks_not_fed'` 跳写;
- 血本位模式(奋斗协议):成本币种切血,金费函数出域,血闸独立车道(`blood_xp_gate`,fail-closed)。

## 6. kernel 符号锚

`kernel/cw_action_report/level_up.py::report_action_level_up_param`(同字段双类型 LevelUpShop 经 `level_up_shop.py::report_action_level_up_shop_param` 一行委托);`kernel/cw_economy.py::xp_apply_clicks` / `xp_click_cost` / `clicks_to_next_level` / `XP_PER_BUY` / `XP_TO_NEXT_LEVEL` / `XP_CLICK_COST_FALLBACK` / `MAX_PLAYER_LEVEL` / `blood_xp_gate` / `blood_xp_gate_for`;`prep_actions.py::PrepActionExecutor._level_up`;发射面 cost 装载 = `strategies/impl/mandate_v1/shop.py`(xp_click_cost 现算 → LevelUpShop)与 `strategies/impl/mandate_v1/entry.py`。

## 7. 语义验证(M1 直锁)

买经验动作转移语义单一源 = 上报函数 `report_action_level_up_param` 单点(推进算子共用 `xp_apply_clicks`;xp/level 跨档直写,域集扩面申报见 `SHOP_PROJECTION_DOMAINS` 登记面注)。原 `kernel/cw_vocab.py::simulate` LevelUp 分支(整帧副本第二载体)已随零生产消费退役,考古归 git。语义验证 = 投影直锁 M1(`test_cw_shop_projection_logic`:击数×单击价扣金/xp 跨档结转/level 升档直写/满级零金零经验零写,均在锁内)。`LevelUpShop ≡ LevelUp`(同字段双类型,词表同一语义)。

## 8. 判例注记(发射期)

**能力面在役、策略面收缩至备战期**(判例 = [screens/README](../../screens/README.md) §5,2026-09-14):注册行已更替为备战 op(§1),商店域 op 文件机制上保留但生产不可达,默认策略**不在商店期买经验**——升等级收缩至备战期决策(strategy-docs/22 号篇)。备战域逐帧单击形态 = 升级唯一生产发射面。

## 9. 依据

`research/xp-rules.md` §2(购买经验单价/门槛表/折扣只降价不减经验);`kernel/cw_economy.py::xp_click_cost` docstring(两支语义与出域声明);[fields.md](../fields.md) §3.2.10/§3.2.11(level/xp/level_up_cost)/§4.2 LevelUp 行;design.md unified-action-factory §2.6 LevelUp 粒度定案④。
