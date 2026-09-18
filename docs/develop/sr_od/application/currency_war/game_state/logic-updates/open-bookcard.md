# 书册(OpenBookcard)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点开占备战席 1 槽的书册卡道具:书册卡离席腾槽 + 专家邀请函五选一弹窗弹出;选卡不在本执行链,点完开启本动作即交回。词表 = `kernel/cw_vocab.py::OpenBookcard`(`slot: int | None`,None = 首张;与 OpenBox/OpenTome 同签名);op 载体 = `operations/cw_op/cw_open_bookcard_action.py::OpenBookcardOp`(体迁薄委托 = `prep_actions.py::PrepActionExecutor._open_bookcard`;书册卡原独立导航链已 R10 链拆归位备战词表)。

## 2. 逻辑态域集

**容器 GameState 零写**:`apply_prep_action_logic` 对集外动作型直接返回(本动作不属 `PREP_PROJECTION_DOMAINS` 写域辖下的四个容器动作类型;箱/典籍/书册卡是视觉域推进,域级跳写申报同 OpenBox/OpenTome)。

**备战观察帧推进**(`kernel/cw_prep_actions.py::PrepObservation`,宿主 `session.prep_obs_frame`;写口 = `operations/cw_screen/cw_screen_prep.py::_project_prep_obs` OpenBookcard 分支):`free_bench_slots` **+1**(开卡即腾席)。书册卡无独立载荷列表字段(箱/典籍有 `boxes`/`tomes`,书册卡占席事实只在 `free_bench_slots` 现读口径)→ 摘件 = 腾席 +1,与 heavy 现读 `slot_occupied` 扫描同式。

## 3. 确定面转移规则(逐条)

1. 书册卡道具占备战席 1 槽(与补给箱/秘密典籍并列第三件占席道具);点槽「开启」→ 道具离席腾槽(观察帧 `free_bench_slots` +1);
2. 专家邀请函五选一弹窗弹出;选卡决策 = 弹窗画面 op `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite`(默认策略单一源 = `choose_expert_index` 原位),由外循环 0k 按画面分发;本动作不选卡;
3. **发射形态**(在役发射位):备战环入口清场段 `operations/cw_screen/cw_screen_prep.py::_clear_prep_cards` 识别到书册卡 → 改产本动作经执行器发射(`validate` 参数校验 → `_act_execute`)→ **本访问交回外循环**(弹窗已弹,heavy 观察禁读弹窗帧);每次访问至多发一张,其余张由外循环下一轮自然续清。是否升 director 门控留策略侧定(升门控时需随 OpenBox 终结化同构补备战 visit 终结分支;现词表发射形态已备完整逻辑态分支);
4. 动画等待 = `_OVERLAY_ANIM_WAIT_S` 固定等待(等待归产生动画的操作;弹窗就位与否交下一帧观察)。

## 4. 随机面 / 观察面

五选一卡面内容 = 随机面归观察;选卡**后果**默认不记预期值(事件线选择非逻辑态通道,[../action-logic-state.md](../action-logic-state.md) §6;chosen_expert 落地记录走观察写端 chosen_* 域组)。有显式到账登记的照登记(在册先例 = 专家邀请函「现金为王」兜底选项 gold+4,写口 = `kernel/cw_exec_state.py::apply_op_effect` ConfirmExpertCash 分支,见 [op-effects.md](op-effects.md))。

## 5. 拒绝语义

- 画面无书册卡(`find_bookcards` 空)= 未发出(`emitted=False`,观察-执行竞态),交回重观察重派;
- `action.slot` 对位无匹配 = 未发出(detail 载实读槽位表);
- 过渡帧不开(`is_prep_like_frame` 不命中)= 不发,交 heavy 观察(识别抖动由外循环轮间自愈);
- validate 参数非法(slot 越界)= Director 拒绝执行 + 交回留证。

## 6. kernel 符号锚

`kernel/cw_vocab.py::OpenBookcard`;`prep_actions.py::PrepActionExecutor._open_bookcard` / `validate`;`kernel/cw_prep_actions.py::PrepObservation`;`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`(OpenBookcard 分支)/ `_clear_prep_cards`(发射位);`operations/cw_screen/cw_screen_expert_invite.py::choose_expert_index`(选卡决策单一源);`kernel/cw_game_state.py::apply_prep_action_logic`(集外零写申报)。

## 7. 语义验证

OpenBookcard 不在 `cw_vocab.py::Action` 联合内(零局内资源推进,与容器零写同义——本动作只动画面态与备战观察帧,局内账本真值不变)。等价性由「视觉域动作容器零写」契约承载;原 sim 整帧副本载体(simulate)已退役,考古归 git。

## 8. 判例注记(发射期)

**备战期**(发射位 = 备战环入口清场段,流程义务非策略判据门):书册卡清场先于当帧决策,弹窗选卡交外循环 0k 分发;商店期无本动作(占席道具只在备战画面可见可点)。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §3.7(OpenBookcard 节);[screens/README](../../screens/README.md) §3.6(开书册卡行);`operations/cw_screen/cw_screen_prep.py::_clear_prep_cards` docstring(两段清场与交回契约);`prep_actions.py::PrepActionExecutor._open_bookcard` docstring(识别语义与 `_OVERLAY_ANIM_WAIT_S` 统一);[fields.md](../fields.md) §4.2 事件选择行(选择落地不记预期值)。
