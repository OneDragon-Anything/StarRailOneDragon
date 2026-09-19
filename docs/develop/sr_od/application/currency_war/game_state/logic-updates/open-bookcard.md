# 书册(OpenBookcard)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点开占备战席 1 槽的书册卡道具:书册卡离席腾槽 + 专家邀请函五选一弹窗弹出;选卡不在本执行链,点完开启本动作即交回。词表 = `kernel/cw_vocab.py::CwActionOpenBookcardParam`(`slot: int | None`,None = 首张;与 OpenBox/OpenTome 同签名);op 载体 = `operations/cw_op/cw_open_bookcard_action.py::CwActionOpenBookcardOp`(体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_bookcard`;书册卡原独立导航链已 R10 链拆归位备战词表)。

## 2. 逻辑态域集

**容器腾席腿**(上报函数 = `kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`,op 自上报):bench 槽位 kind `bookcard` → `empty`(开卡即腾席,占席事实进容器)。守卫 = bench 未观察 / 槽不存在 / 槽类型不符 → 陈旧提案零写;`slot=None` = 首个 `kind='bookcard'` 槽。**类型边界申报**:kind 细分批(2026-09-19)起书册卡槽有独立容器 kind `'bookcard'`(观察链 `find_bookcards` 槽号集构造,不再统一降级 `'supply_box'`——降级时代开箱臂会对卡槽误发 OpenBox,由入口清场先于观察 masking)。

**其它域零写**:选卡后果(专家邀请函五选一)随机面归观察。

## 3. 确定面转移规则(逐条)

1. 书册卡道具占备战席 1 槽(与补给箱/秘密典籍并列第三件占席道具);点槽「开启」→ 道具离席腾槽(容器 bench 槽 kind → `empty`,`bench_free_slots` 派生 +1);
2. 专家邀请函五选一弹窗弹出;选卡决策 = 弹窗画面 op `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite`(默认策略单一源 = `choose_expert_index` 原位),由外循环 0k 按画面分发;本动作不选卡;
3. **发射形态**(用户裁定 2026-09-19 开卡时机归策略实现管):发射位 = 策略器 entry ① prep 实体面卡片臂(容器 bench kind `'bookcard'` 触发;原备战环入口清场段 `_clear_prep_cards` 代发通道撤销)→ 本动作**终结**(op 类 `terminal=True`,与 OpenBox R7 终结化同构)→ 备战环交回外循环,弹窗帧不进 heavy 观察;每次访问恰发一张,其余张由下一访问观察后自然续清;
4. 动画等待 = `_OVERLAY_ANIM_WAIT_S` 固定等待(等待归产生动画的操作;弹窗就位与否交下一帧观察)。

## 4. 随机面 / 观察面

五选一卡面内容 = 随机面归观察;选卡**后果**默认不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6;chosen_expert 落地记录走观察写端 chosen_* 域组)。有显式到账登记的照登记(在册先例 = 专家邀请函「现金为王」兜底选项 gold+4,写口 = `kernel/cw_exec_state.py::apply_confirm_effect` ConfirmExpertCash 分支,见 [op-effects.md](op-effects.md))。

## 5. 拒绝语义

- 画面无书册卡(`find_bookcards` 空)= 未发出(`emitted=False`,观察-执行竞态),交回重观察重派;
- `action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);
- validate 参数非法(slot 越界)= Director 拒绝执行 + 交回留证。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionOpenBookcardParam`;`prep_actions.py::PrepActionExecutor._open_bookcard` / `validate`;`kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`(腾席函数);`strategies/impl/mandate_v1/entry.py` ① 卡片臂(发射位);`operations/cw_screen/cw_screen_expert_invite.py::choose_expert_index`(选卡决策单一源)。

## 7. 语义验证

腾席腿语义单一源 = `report_action_open_bookcard_param`(bench kind 'bookcard' → 'empty',陈旧提案零写;行为锁 = `test_cw_unified_action_2c::test_open_bookcard_logic_state_frees_slot`,容器版腾席锁)。选卡后果归观察(选择落地不记预期值)。原聚合写口分支与 sim 整帧副本载体(simulate)已随动作 op 重组与 sim 重做退役,考古归 git。

## 8. 判例注记(发射期)

**备战期**(发射位 = 策略器卡片臂):卡片先于箱/典籍臂(旧入口清场先于观察的全局序),弹窗选卡交外循环 0k 分发;商店期无本动作(占席道具只在备战画面可见可点)。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §3.7(OpenBookcard 节);[screens/README](../../screens/README.md) §3.6(开书册卡行);`strategies/impl/mandate_v1/entry.py` emit ① 卡片臂注释(用户裁定与臂序);`prep_actions.py::PrepActionExecutor._open_bookcard` docstring(识别语义与 `_OVERLAY_ANIM_WAIT_S` 统一);[fields.md](../fields.md) §4.2 事件选择行(选择落地不记预期值)。
