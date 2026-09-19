# 试用揭示卡(RevealTrial)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点开占备战席 1 槽的试用角色揭示卡(发光金卡,`find_trial_reveal_cards` 识别):点开即**免费**得 2★ 试用角色,原地变普通角色卡由 SIFT 自然识别。**终结动作**(揭示即引入新事实——板上多一个身份不可预知的角色,与 OpenBox R7 终结化同构):点完本动作即交回外循环,下一入口 heavy 观察读到揭示后真实板面再续决策。词表 = `kernel/cw_vocab.py::CwActionRevealTrialParam`(`slot: int | None`,None = 首张;与 OpenBox/OpenTome/OpenBookcard 同签名);op 载体 = `operations/cw_op/cw_reveal_trial_action.py::CwActionRevealTrialOp`。

## 2. 逻辑态域集

**容器零写**(零写族申报 = `kernel/cw_action_report/zero_writes.py::report_action_reveal_trial_param`):揭示出的 2★ 试用角色身份不可预知,腾席/入席事实归下一入口 heavy 观察覆盖,零窗口暴露。

## 3. 确定面转移规则(逐条)

1. 试用角色揭示卡占备战席 1 槽;点槽 → 揭示卡消失、2★ 试用角色入席(观察收口,容器下一帧实读覆盖);
2. **发射形态**(用户裁定 2026-09-19 开卡时机归策略实现管):发射位 = 策略器 entry ① prep 实体面卡片臂(容器 bench kind `'trial_card'` 触发)→ 备战环交回外循环重观察;每次访问恰发一张,其余张由下一访问观察后自然续清。

## 4. 随机面 / 观察面

揭示出的角色身份与星级(2★)= 随机/观察面,容器零写等覆盖。

## 5. 拒绝语义

- 画面无揭示卡(`find_trial_reveal_cards` 空)= 未发出(`emitted=False`,观察-执行竞态),交回重观察重派;
- `action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);
- validate 参数非法(slot 越界)= Director 拒绝执行 + 交回留证。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionRevealTrialParam`;`prep_actions.py::PrepActionExecutor.validate`;`kernel/cw_action_report/zero_writes.py::report_action_reveal_trial_param`(零写申报);`strategies/impl/mandate_v1/entry.py` ① 卡片臂(发射位);`obs/cw_identity_obs.py::find_trial_reveal_cards`(识别单一源)。

## 7. 语义验证

零写申报 = `report_action_reveal_trial_param`(容器零写,揭示身份归观察;行为锁 = `test_cw_unified_action_2c::test_reveal_trial_dispatch_mechanical` 机械半 + `test_prep_terminal_set_matches_registry_terminal_attrs` 终结集锁)。发射臂锁 = `test_cw_unified_action_2c::test_entry_card_arms_emit_from_bench_kind`。

## 8. 判例注记(发射期)

**备战期**(发射位 = 策略器卡片臂):免费揭示先于书册卡、先于箱/典籍臂(旧入口清场先于观察的全局序);商店期无本动作(占席道具只在备战画面可见可点)。历史形态:原为备战环入口清场段直接点击(非动作、不进词表),随卡片臂策略器化收编为词表动作。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §3.8(RevealTrial 节);[fields.md](../fields.md) 备战动作逻辑态写口覆盖面申报(零写族);`strategies/impl/mandate_v1/entry.py` emit ① 卡片臂注释(用户裁定与臂序)。
