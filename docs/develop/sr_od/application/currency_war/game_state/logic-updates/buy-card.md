# 买牌(BuyCard)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则与两态制纪律见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

在商店开画面点击一张牌,把它买入备战席;若这次买入使同名同星凑满 3 个则自动升星(连锁可多级),备战席满时若该点击能完成一次合成则一击多张买满缺数。op 载体 = `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp`(非终结);词表 = `kernel/cw_vocab.py::CwActionBuyCardParam`。

## 2. 逻辑态域集

容器写语义单一源 = 上报函数 `kernel/cw_action_report/buy_card.py::report_action_buy_card_param`(简单落位与合成升星腿内聚单点:买前快照三件组函数内第一时间取,升星发生才整表覆盖,直锁 M1 = `test_cw_shop_projection_logic`)。登记面 = `SHOP_PROJECTION_DOMAINS`,本动作涉及的写域:

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| gold | 写 | `gold −= 牌单价 × k`(k = 实购张数);gold 未读(None)= 域级跳写,值留观察覆盖 |
| shop | 写 | 被买槽 kind 置 empty(留空不紧缩);同 (name, star) 的 k 张按槽序对前 k 个置换;离屏(None)= 跳写 |
| bench | 写 | 新单位落备战席首个空槽 + 合成连锁应用后的整表终态(`bench_view_of_slots` 重建直写) |
| front_row / back_row | 条件写 | 仅当合成连锁消费/升星了场上件(deployed 值签名变化)才整表随写;无合成触及场上 = 零写 |
| board | 派生随写 | **派生量**:front_row/back_row 行写端挂钩 `GameState._resync_board_delta` 自动增量重算,随上行条件写触发,本腿禁手写 |
| xp / level / equips / hp | 跳写 | 买牌不产经验(零购买子集反证,`research/xp-rules.md` §2);不触装备域 |

执行侧配套(非容器域):op 内 tracked 双账同步(`mutate_bench_deployed`,shop 视图透传)、买前裁片留证、效果账本 `CounterKey.BUY` 计数推进(挂执行落地门 `apply_action_outcome`)。

## 3. 确定面转移规则(逐腿)

**常态腿(备战席有空槽)**:

1. 新单位落备战席**首个空槽**(`cw_exec_state.py::bench_place`,槽号信息位归一 = 下标+1);
2. gold `−=` 牌单价 × k(常态 k=1;金账全款无打包价——满栏自动多买也无价格优惠,`research/merge_mechanics.md` §2.5);
3. 商店载荷:被买槽置 empty 留空不紧缩(买后右邻槽像素零变化实锤,`research/economy.md` §2.1);
4. **全场合成连锁**:买入后同名同星计数(备战∪场上,`cw_merge_simulate.py::same_star_count`)≥3 即升星。落点 = 场上那张的位置(装备/站位随之继承)或三张全在备战栏时最左一张的位置;连锁可多级(2★ 产物再凑 3 → 3★);三只身上的装备**全部**继承到产物(`kernel/cw_merge_simulate.py::_merge_bench` 不动点循环;装备继承 = 玩家定谳,merge_simulate 模块头规则 4)。升星触发时 front_row/back_row 整表 + board 重算随写(值签名变化才写)。升星触发判定单一源 = `kernel/cw_game_state.py::detect_merge_upgrade`(同名最高星抬升);
5. 生产调用序 = 动作 op(`CwActionBuyCardOp`)机械执行后直调 `report_action_buy_card_param` 单点——简单落位与升星腿内聚:买前快照三件组 = pre_bench/pre_deployed/pre_shop 作 scratch 基点,函数内第一时间取(原落地门/两驱动器三处抄写收编单点);升星发生才整表覆盖,后写赢。原落地门两写调用面(`apply_action_outcome` 直写块)已随动作 op 重组删除 = 双记防线;落地门现役保留面 = 卖出 route-tag 显影(`cw_screen_shop.py::apply_action_outcome`,同函数 S1 清键显影段);BUY 计数现役 = 上报函数 `on_buy` 回调单点,REFRESH 计数现役 = 效果账本 `record_refresh` 单口(触发 = `report_action_refresh_shop_param`),落地门刷新侧零代码。

**满栏例外腿(备战席满)**:

- 满栏仍买得进**当且仅当**本次点击能完成一次合成(判据单一源 = `cw_merge_simulate.py::merge_buy_completes`,前提门 = 已有同名同星素材 own≥1;own=0 满栏域游戏拒买,/);
- 一击多买张数 k = `cw_merge_simulate.py::merge_buy_k` = min(店内同名同星张数, 3 − 已有数 mod 3)(绝不多买,`research/merge_mechanics.md` §2.5);
- k 张逐张原价扣金(总价 = k×单价)、店载荷下架 k 张同身份牌、合成腾槽(应用机器 = `cw_merge_simulate.py::_apply_full_bench_merge_buy`,逻辑态直写与 tracked 双账同构单一源);
- 执行器张数回执 = `CwActionBuyCardOp` 现算 `merge_buy_k`,执行账补差 (k−1)×单价。

## 4. 随机面

商店直出 2★/3★ 的概率与出现(星级经费用徽章倍数反推,识别面)不进逻辑态;买入触发合成后的升星动画(~1s,`research/screen_flow_timing.md` #8b)= 画面时序。两者归下一帧观察。

## 5. 拒绝语义

- **满栏且合成不可达** = 游戏拒买:`LogicOutcome(applied=False, reason='bench_full')`,零容器写——金不扣、牌不下架;
- 买牌无 expect 陈旧提案域(SellBench 族语义,本动作无此域);执行侧另有提案守卫 `cw_shop_action_ops.py::guard_proposal_vs_expected`(所购牌名须在期望态店中,防策略器跨代际提案);
- 知识缺口 G1:非满栏一次点击恒买 1 张 = 框架推论未实测,闭合前按 k=1 记账,买后观察多张 → 对账纠偏 + 缺陷台账;G2:满栏连升(own=0)按拒买实现(申报边界)。

## 6. kernel 符号锚

`kernel/cw_action_report/buy_card.py::report_action_buy_card_param`(简单落位与升星腿内聚;获取计算完时点触发 `gs.effects.on_buy` 购买回调)/ `kernel/cw_game_state.py::detect_merge_upgrade`;`kernel/cw_merge_simulate.py::merge_buy_k` / `merge_buy_completes` / `_merge_bench` / `_apply_full_bench_merge_buy` / `same_star_count`;`kernel/cw_economy.py::card_cost`;`kernel/cw_exec_state.py::bench_place`;落地门 = `operations/cw_screen/cw_screen_shop.py::apply_action_outcome`(计数与显影保留面;BUY 计数已迁上报函数 on_buy 回调单点)。

## 7. 语义验证(M1 直锁)

买牌动作转移语义单一源 = 上报函数 `report_action_buy_card_param` 单点(快照与升星腿内聚):常态腿 gold 扣减 + 首空落位 + (name, star) 计数置换下架店牌(三态定长 5 槽模型);满栏腿 `_apply_full_bench_merge_buy` + 按 (name, star) 多集移除 k 张。原 `kernel/cw_vocab.py::simulate` BuyCard 分支(整帧副本第二载体)已随零生产消费退役,考古归 git。语义验证 = 投影直锁 M1(测试 `test_cw_shop_projection_logic`:常态落位/满栏多买 −k×单价/升档结转/满栏拒买逐域直断言)。

## 8. 判例注记(发射期)

商店期默认策略动作面 = 买牌/刷新/关店(判例 = [screens/README](../../screens/README.md) §5,2026-09-14);买牌是商店期主力动作(策略判据 = strategy-docs/23_shop_screen.md)。备战域无买牌(牌只在商店买)。

## 9. 依据

`research/merge_mechanics.md` §1/§2/§2.5/§2.6/§3;`research/economy.md` §2.1(槽位留空/整店全换);`research/xp-rules.md` §2(买牌不产经验);`kernel/cw_action_report/buy_card.py` docstring(快照/升星腿内聚与 k 来源申报);[fields.md](../fields.md) §3.3.1(商店牌行)/§4.2 BuyCard 行。
