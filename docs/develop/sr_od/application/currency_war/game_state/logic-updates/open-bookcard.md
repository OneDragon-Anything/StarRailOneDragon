# 书册(OpenBookcard)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点开占备战席 1 槽的书册卡道具:书册卡离席腾槽 + 专家邀请函五选一弹窗弹出;选卡不在本执行链,点完开启本动作即结束本次访问。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionOpenBookcardParam`(`slot: int | None`,None = 首张;与 OpenBox/OpenTome 同签名);op 载体 = `operations/cw_op/cw_open_bookcard_action.py::CwActionOpenBookcardOp`(体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_bookcard`)。

## 2. 逻辑态域集

**状态容器(GameState)腾位写入**(上报函数 = `kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`,op 自上报):bench 槽位 kind `bookcard` → `empty`(开卡即腾位,占席事实进状态容器(GameState,游戏状态对象,下同))。守卫 = bench 未观察 / 槽不存在 / 槽类型不符 → 陈旧提案零写;`slot=None` = 首个 `kind='bookcard'` 槽。**类型边界申报**:书册卡槽状态容器 kind = `'bookcard'` 独立分型(观察链 `find_bookcards` 槽号集构造),不并入 `'supply_box'` 降级口径——降级口径下开箱分支会对卡槽误发 OpenBox(腾位 kind 门单一源 = `kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`)。

**其它域零写**:选卡后果(专家邀请函五选一)随机面归观察。

## 3. 确定面转移规则(逐条)

1. 书册卡道具占备战席 1 槽(与补给箱/秘密典籍并列第三件占席道具);点槽「开启」→ 道具离席腾槽(状态容器 bench 槽 kind → `empty`,`bench_free_slots` 派生 +1);
2. 专家邀请函五选一弹窗弹出;选卡决策 = 弹窗画面 op `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite`(默认策略单一源 = `choose_expert_index` 原位),由外循环按画面分发(分发判定单一源 = flow/outer_loop.md §2 阶段一身份分发);本动作不选卡;
3. **动作发出形态**(开卡时机归策略实现管):动作发出点 = 策略器 entry ① prep 实体面卡片分支(状态容器 bench kind `'bookcard'` 触发)→ 本动作**终结**(= 发出后结束本次访问;op 类 `terminal=True`,与 OpenBox 终结化同构,规范锚 = op-layer.md §1.4)→ 备战环返回主循环,弹窗帧不进完整观察;每次访问恰发一张,其余张由下一访问观察后自然续清;
4. 动画等待 = `_OVERLAY_ANIM_WAIT_S` 固定等待(等待归产生动画的操作;弹窗就位与否交下一帧观察)。

## 4. 随机面 / 观察面

五选一卡面内容 = 随机面归观察;选卡**后果**默认不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6;chosen_expert 落地记录走观察侧写入的 chosen_* 域组)。有显式到账登记的照登记(已登记先例 = 专家邀请函「现金为王」兜底选项 gold+4,写入口 = `kernel/cw_exec_state.py::apply_confirm_effect` ConfirmExpertCash 分支,见 [op-effects.md](op-effects.md))。

## 5. 拒绝语义

- 画面无书册卡(`find_bookcards` 空)= 未发出(round 结果失败态,观察-执行竞态),返回主循环重新观察重派;
- `action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);
- validate 参数非法(slot 越界)= Director 拒绝执行 + 结束本次访问并保留证据。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionOpenBookcardParam`;`prep_actions.py::PrepActionExecutor._open_bookcard` / `validate`;`kernel/cw_action_report/open_bookcard.py::report_action_open_bookcard_param`(腾位函数);`strategies/impl/mandate_v1/entry.py` ① 卡片分支(动作发出点);`kernel/cw_events.py::choose_expert_index`(选卡决策单一源;`cw_screen_expert_invite.py` 仅函数体内 import)。

## 7. 语义验证

腾位写入语义单一源 = `report_action_open_bookcard_param`(bench kind 'bookcard' → 'empty',陈旧提案零写;行为测试 = `test_cw_unified_action_2c::test_open_bookcard_logic_state_frees_slot`,状态容器版腾位测试)。选卡后果归观察(选择落地不记预期值)。原聚合写入入口分支与 sim 整帧副本载体(simulate)已随动作 op 重组与 sim 重做停用,考古归 git。

## 8. 先例注记(动作发出阶段)

**备战期**(动作发出点 = 策略器卡片分支):卡片先于箱/典籍分支(旧入口清场先于观察的全局序),弹窗选卡交外循环按画面分发;商店期无本动作(占席道具只在备战画面可见可点)。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §3.7(OpenBookcard 节);[screens/README](../../screens/README.md) §5.5(开书册卡行);`strategies/impl/mandate_v1/entry.py` emit ① 卡片分支注释(用户裁定与分支顺序);`prep_actions.py::PrepActionExecutor._open_bookcard` docstring(识别语义与 `_OVERLAY_ANIM_WAIT_S` 统一);[fields.md](../fields.md) §4.2 事件选择行(选择落地不记预期值)。
