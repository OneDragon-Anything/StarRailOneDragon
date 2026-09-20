# 卖备战(SellBench)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

把备战席某槽位的角色拖到出售区卖出,回收退款。op(词表摊平后商店/备战共用词表单一注册行)= `operations/cw_op/cw_prep_sell_bench_action.py::CwActionSellBenchOp`(唯一活执行路径;原商店域文件 `cw_sell_bench_action.py` 已退役删除,能力面语义由上报函数保留,判例见 §8);执行器 = `prep_actions.py::PrepActionExecutor._sell_bench`(拖拽原语共享 = `prep_actions.py::drag_bench_to_sell`)。词表 = `kernel/cw_vocab.py::CwActionSellBenchParam`(`bench_idx` = bench 槽位表下标 0-8)。

## 2. 逻辑态域集

**容器写口(双域统一单点)** = 上报函数 `kernel/cw_action_report/sell_bench.py::report_action_sell_bench_param`(原商店腿/备战腿的历史两份随动作 op 重组合一,申报面 = 函数 docstring):

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| bench | 写 | 该槽 kind → `empty`(**不移位**,ADR-0316 槽位语义;跨动作组下标恒稳),**原生 `BenchView.slots` 直操**(容器原生形态,不经任何换形往返,BenchSlot kind 五分类在写口保形) |
| gold | 写 | `gold += 退款`;gold 未读(None)= 域级跳写 |
| equips | 写 | 被卖单位身上全部装备追加进 owned 库存(`sold.equips` 非空才写;原备战域缺口随双域腿统一补齐——历史「商店腿有/备战域留观察覆盖」的不对称消亡) |
| overflow_card / overflow_warning | 条件写 | 溢出腿另写两旗标域(§3 第 5 条,容器状态条件域无关携带) |
| 其余域 | 跳写 | 不触商店载荷/经验/上阵域 |

守卫 = 空槽/**占位件**(kind ≠ 'unit')/越界零写——占位件无卖出语义(sell_gate 占位恒拒防线同口径);expect 代际校验统一携带(非空 expect 失配 = 陈旧提案拒,live 提案恒 '' 零行为)。

**效果账面(申报:执行缝无金腿)**:卖出回金的容器唯一写点 = 上报函数(按 `sell_refund` 直写金账)——原聚合口 `apply_op_effect` 的 SellBench 分支已随「统一观察对账迭代 2026-09-16 归因批」退役(执行缝 + 投影双腿各记一次 +refund,实读倒挂 −2 实证);执行缝现只算执行点金差 `_executed_gold_delta` 进回执 extra 留证,**不经它直推容器金账**。

## 3. 确定面转移规则(逐条)

1. 备战席该槽位清空(kind → `empty` 不移位;槽位空/越界 = 陈旧提案拒,§5);
2. `gold += 退款`,公式单一源 = `kernel/cw_economy.py::sell_refund`:退款 = 招募费(`bench_char_cost`,注册表单一源,未知按中位保守估)× 星级倍数表 `_SELL_MULT`(1★ 全额;2★/3★/4★ = 合成副本数同构倍数);**手续费口径**:star≥2 且 cost≥2 再 −1;cost=1 豁免(2★1费 卖出 = 全额倍数,live 实测定谳;3★2费 = +17 已 live 定谳,4★ 档仍未核 = 缺口 G3 剩余);
3. **装备全量回装备区**(上报函数 C6 守恒腿):被卖单位身上全部装备(简易/进阶/核心不分)进 owned 装备库存——穿戴是可逆暂借(【口述·权威】`research/equipment_mechanics.md` §1;kernel 按 C6 装备守恒回收建模);
4. 陈旧提案拒:expect 身份与槽内不符 = 零写(ADR-0317);
5. **溢出条件腿**(2026-09-15 实机建档,`docs/game/screens/currency_war_prep.md` 告警节):`overflow_warning` 在场(备战席满告警横幅 = 存在未安置溢出角色,此刻出战点击被游戏忽略)时,卖出语义补一条——**腾出槽当帧记溢出卡入位**(`bench[idx]` 槽 kind 回占为 `unit`(入位卡身份,星级缺读按 1 兜底);「卖 → 溢出卡自动入自由槽」是游戏侧行为,有溢出时席必满、自由槽恒唯一,落位无歧义)+ `overflow_card` 消费清空 + 旗标 logic 消亡(下帧实读覆盖)。入位对象身份缺读(`overflow_card` 空)= 跳过入位(槽留空等观察),卖出语义本体不受阻。**两账同帧**:容器腿(上报函数,入位卡回占槽位——席空数派生自然不 +1,腾出槽即刻回占)/ 执行侧 tracked 主账吸收(session 形参在场时,摘该槽 + 追加入位卡后经 `bench_from_compact` 重建槽位表——缺吸收 = 商店播种守卫双账分叉,实机 2-4 停机实证)。(原第三面「黑板帧镜像」随 `gs.prep_obs` 黑板退役删除——迭代 2026-09-18-prep-obs-retirement 阶段 3.5,镜像语义由容器回占面全量承载。)

## 4. 随机面

无。卖价修饰效果(大裁员/降本增效 `sell_price_mult`)的作用口径待实证(净额 vs 基础价 = 缺口 G4),缺口闭合前不写修饰腿、退款按基础公式。

## 5. 拒绝语义

- 槽位越界 / 槽空:`LogicOutcome(applied=False, reason='bench_idx_out_of_range:<idx>')`,零容器写;
- **期望失配 stale_proposal**:expect 非空且与槽内 `char_id` 不符 = `applied=False, reason='stale_proposal:<expect>!=<实际>'`,零写(ADR-0317;live 提案 expect 恒空不校验,校验面辖非空 expect 提案);
- 执行器零判效:拖拽发出即职责完成,落地事实归观察侧 reconcile;「拒买语义」在本动作不存在(卖出恒可用)。

## 6. kernel 符号锚

`kernel/cw_action_report/sell_bench.py::report_action_sell_bench_param`(双域统一单点,原生 `BenchView.slots` 直操);`kernel/cw_economy.py::sell_refund` / `bench_char_cost` / `_SELL_MULT`;`kernel/cw_vocab.py::mutate_bench_deployed`(SellBench 分支,tracked 同步);`prep_actions.py::PrepActionExecutor._sell_bench` / `_track_remove_bench` / `_executed_gold_delta`(金差仅回执留证) / `drag_bench_to_sell`。

## 7. 语义验证(M1 直锁)

卖出动作转移语义单一源 = 上报函数(`report_action_sell_bench_param`:expect 陈旧提案拒零写 + 置 empty 不移位 + `sell_refund` 回金 + 装备回收 + 溢出腿,双域统一单点)。原 `kernel/cw_vocab.py::simulate` SellBench 分支(整帧副本第二载体)已随零生产消费退役,考古归 git。商店域投影语义由直锁 M1(`test_cw_shop_projection_logic`)钉住。C6 装备守恒核对的活机制 = 观察边界 reconcile(下一入口装备区读数覆盖;原 sim 侧 `EquipsLedger` 快照比对对账入口挂在已删函数内,随 simulate 退役)。

## 8. 判例注记(发射期)

**能力面在役、策略面收缩至备战期**(判例 = [screens/README](../../screens/README.md) §5,2026-09-14):商店开画面机制上可用(注册行随词表摊平指备战 op),但默认策略**不在商店期卖**——席满腾位/凑息/筹资/换线塌缩卖收缩至备战期决策;席满腾位链 = 关店 → 备战期卖 → 重开(节点内关店/重开不刷新牌面,牌面持久)。商店域 `mandate_v1/shop.py::_note_sell` 策略侧卖出自记 = 在册违例(README 违例表),待判例修正波移除。

## 9. 依据

`research/economy.md` §3(卖出退金与手续费;3★ 定谳);`research/equipment_mechanics.md` §1(卖出 = 装备全量回区,缺口 G5 = 帧级证据未采按守恒建模);`kernel/cw_action_report/sell_bench.py::report_action_sell_bench_param` docstring(溢出腿/session 吸收申报);[fields.md](../fields.md) §3.2.21(备战席溢出)/§4.2 SellBench 行。
