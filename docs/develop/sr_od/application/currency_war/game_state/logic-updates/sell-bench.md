# 卖备战(SellBench)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

把备战席某槽位的角色拖到出售区卖出,回收退款。双域双载体:商店域 op = `operations/cw_op/cw_sell_bench_action.py::SellBenchOp`(能力面在役、策略面收缩至备战期,判例见 §8);备战域执行器 = `prep_actions.py::PrepActionExecutor._sell_bench`(拖拽原语共享 = `prep_actions.py::drag_bench_to_sell`)。词表单一 = `kernel/cw_vocab.py::SellBench`(统一词表后无族分,`bench_idx` = bench 槽位表下标 0-8)。

## 2. 逻辑态域集

**商店域写口** = `kernel/cw_game_state.py::apply_shop_action_logic` SellBench 腿(域集封闭 `SHOP_PROJECTION_DOMAINS`):

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| bench | 写 | 该槽位置 None(**不移位**,ADR-0316 槽位语义;跨动作组下标恒稳),`bench_view_of_slots` 重建直写 |
| gold | 写 | `gold += 退款`;gold 未读(None)= 域级跳写 |
| equips | 写 | 被卖单位身上全部装备追加进 owned 库存(`sold.equips` 非空才写) |
| 其余域 | 跳写 | 不触商店载荷/经验/上阵域 |

**备战域写口** = `kernel/cw_game_state.py::apply_prep_action_logic` SellBench 腿,域集封闭 = `PREP_PROJECTION_DOMAINS` 的 gold/bench 子集;**equips 域不在备战写口域集**(域集封闭申报,装备回区留观察覆盖)。溢出腿另写 `overflow_card`/`overflow_warning` 两旗标域(§3 第 5 条)。

**效果账腿** = `kernel/cw_exec_state.py::apply_op_effect` SellBench 分支:tracked 快照退款 → `_advance_gold` 直推容器金账(logic_action 渠道,观察赢);身份不可辨 = None 诚实缺失,禁保守估值假账。注意与 SellDeployed 分支的不对称:本分支**无** owned 装备恢复腿(备战域装备回收归观察覆盖),卖上阵分支有(op-effects.md §2)。

## 3. 确定面转移规则(逐条)

1. 备战席该槽位清空(置 None 不移位;槽位空/越界 = 陈旧提案拒,§5);
2. `gold += 退款`,公式单一源 = `kernel/cw_economy.py::sell_refund`:退款 = 招募费(`bench_char_cost`,注册表单一源,未知按中位保守估)× 星级倍数表 `_SELL_MULT`(1★ 全额;2★/3★/4★ = 合成副本数同构倍数);**手续费口径**:star≥2 且 cost≥2 再 −1;cost=1 豁免(2★1费 卖出 = 全额倍数,live 实测定谳;3★2费 = +17 已 live 定谳,4★ 档仍未核 = 缺口 G3 剩余);
3. **装备全量回装备区**(商店域腿):被卖单位身上全部装备(简易/进阶/核心不分)进 owned 装备库存——穿戴是可逆暂借(【口述·权威】`research/equipment_mechanics.md` §1;kernel 按 C6 装备守恒回收建模);
4. 陈旧提案拒:expect 身份与槽内不符 = 零写(ADR-0317);
5. **溢出条件腿**(2026-09-15 实机建档,`docs/game/screens/currency_war_prep.md` 告警节):`overflow_warning` 在场(备战席满告警横幅 = 存在未安置溢出角色,此刻出战点击被游戏忽略)时,卖出语义补一条——**腾出槽当帧记溢出卡入位**(`bench[idx] := 溢出卡`;「卖 → 溢出卡自动入自由槽」是游戏侧行为,有溢出时席必满、自由槽恒唯一,落位无歧义)+ `overflow_card` 消费清空 + 旗标 logic 消亡(下帧实读覆盖)。入位对象身份缺读(`overflow_card` 空)= 跳过入位(槽留空等观察),卖出语义本体不受阻;星级缺读按 1 兜底。**三账同帧**:容器腿(本写口)/ 执行侧 tracked 主账吸收(session 形参在场时,摘该槽 + 追加入位卡后经 `bench_from_compact` 重建槽位表——缺吸收 = 商店播种守卫双账分叉,实机 2-4 停机实证)/ 黑板帧镜像(`_project_prep_obs` 入位卡补进 bench_chars、free_bench_slots 不 +1——腾出槽即刻回占)三面同帧同源。

## 4. 随机面

无。卖价修饰效果(大裁员/降本增效 `sell_price_mult`)的作用口径待实证(净额 vs 基础价 = 缺口 G4),缺口闭合前不写修饰腿、退款按基础公式。

## 5. 拒绝语义

- 槽位越界 / 槽空:`LogicOutcome(applied=False, reason='bench_idx_out_of_range:<idx>')`,零容器写(备战域写口 = 静默零写守卫,等观察覆盖);
- **期望失配 stale_proposal**:expect 非空且与槽内 `char_id` 不符 = `applied=False, reason='stale_proposal:<expect>!=<实际>'`,零写(语义源 = simulate SellBench 分支 ADR-0317;live 提案 expect 恒空不校验,校验面辖非空 expect 提案);
- 执行器零判效:拖拽发出即职责完成,落地事实归观察侧 reconcile;「拒买语义」在本动作不存在(卖出恒可用)。

## 6. kernel 符号锚

`kernel/cw_game_state.py::apply_shop_action_logic`(SellBench 腿)/ `apply_prep_action_logic`(SellBench 腿 + 溢出腿);`kernel/cw_economy.py::sell_refund` / `bench_char_cost` / `_SELL_MULT`;`kernel/cw_exec_state.py::apply_op_effect`(SellBench 分支)/ `_advance_gold`;`kernel/cw_vocab.py::mutate_bench_deployed`(SellBench 分支,tracked 同步);`prep_actions.py::PrepActionExecutor._sell_bench` / `_track_remove_bench` / `drag_bench_to_sell`;`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`(溢出镜像)。

## 7. 与 sim simulate 的等价关系(M1 锁)

`kernel/cw_vocab.py::simulate` SellBench 分支 = 同一规则第二载体:expect 陈旧提案 → 账本记 rejected 零推进;`bench_clear` 置 None + `sell_refund` 回金 + `s.equips.extend` 装备回收。容器写口逐腿平移同分支(拒因形态同键);sim 侧 C6 装备守恒对账(`EquipsLedger`)对卖出动作前后跑快照比对。商店域两载体等价归锁 M1(`test_cw_shop_projection_logic`);备战域为语义源平移关系(`PREP_PROJECTION_DOMAINS` 登记面申报)。

## 8. 判例注记(发射期)

**能力面在役、策略面收缩至备战期**(判例 = [screens/README](../../screens/README.md) §5,2026-09-14):商店开画面的 SellBenchOp 机制上可用,但默认策略**不在商店期卖**——席满腾位/凑息/筹资/换线塌缩卖收缩至备战期决策;席满腾位链 = 关店 → 备战期卖 → 重开(节点内关店/重开不刷新牌面,牌面持久)。商店域 `mandate_v1/shop.py::_note_sell` 策略侧卖出自记 = 在册违例(README 违例表),待判例修正波移除。

## 9. 依据

`research/economy.md` §3(卖出退金与手续费;3★ 定谳);`research/equipment_mechanics.md` §1(卖出 = 装备全量回区,缺口 G5 = 帧级证据未采按守恒建模);`kernel/cw_game_state.py::apply_prep_action_logic` docstring(溢出腿/session 吸收申报);[fields.md](../fields.md) §3.2.21(备战席溢出)/§4.2 SellBench 行。
