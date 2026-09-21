# PickPlanner/PickEquip 两相上报清偿 落地

> 阶段小节 = 账本唯一源（立任务照各节 `dag.py add`，criteria 预注册指向本节）。
> **通用工程门**（定义 = 本节；源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）：ruff 改动文件 + 直接受影响测试全绿。

## 3.1 选择装备屏单相化（equip 先行）

**范围**：`kernel/cw_action_report/pick_equip.py` 单相化（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED`，一口写 owned 入栏+后果链，未解析翻来源留证语义保持）；`cw_screen_equip_pick.py` 组装点换 `normalize_registry_equip_name`（T-1 已建入口）、删 `_pick_pending`/`_pending_pick`/重入裁决出口门、act 派发即 `round_success` 终结；`kernel/cw_vocab.py` 注释连带三处——`CwActionPickEquipParam.norm_item` 字段注释改写（归一换源）+ `CwActionPickSupplyParam.norm_item` T-1 遗留过期注释顺手清（attack2 F7）+ 两 param docstring「两相/落地相」措辞机械改写（attack3 F5）；`CwActionPickEquipOp.run` 点卡后固定等 1.2s 立即上报完整结果（本屏点卡即选、无确认步——「确认点击后」措辞不适用于本屏）。**不含**：planner 屏（3.2 辖内）。
**设计依据**：design.md §2.0、§2.1（equip）、§2.2 表、§2.3（取舍 1/2/4）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_equip.py`、`kernel/cw_vocab.py`（仅注释）、`operations/cw_screen/cw_screen_equip_pick.py`、`operations/cw_op/cw_overlay_pick_action.py`（仅 CwActionPickEquipOp 体）、`sr-od-test/` 受影响测试（含 `test_cw_pick_channels_t60.py` EQUIP_EVIDENCE 面、two_node_family 行为锁 equip act 断言 ：346/:348，attack3 F3）
**依赖**：无
**优先级建议**：7
**完成判据**：
- 行为对照 design.md §3 验收锚 1（行为锁：点卡后容器即持 owned 规范名+后果链，含泛用注册表件归一命中用例；派发即终结断言；pick_equip 来源 `EVIDENCE_OVERLAY_CLOSED` 零残留——范围 = src + sr-od-test；docs 正本面归末阶段正本更新批，attack6 N1 措辞勘误）
- 通用工程门
**验收凭据形式**：equip 单相行为锁测试（命中/未解析/泛用件三型）+ `test_cw_pick_channels_t60.py`/`test_cw_yinlang_phase32.py` 受影响面全绿

## 3.2 骇入策划屏单相化（planner）

**范围**：`kernel/cw_action_report/pick_planner.py` 单相化（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED`；一口写 = ⓪unknown 留证分支逐位保持（弱化词卡文落此——弱化兜底档已退役，`classify_planner_leg` 现役不产出 weaken，attack2 F5 实码口径）→ equip 腿 → upgrade 变换窗三态+档行，前置硬校验语义逐位保持 → unrouted 兜底零写逐位保持；**joy rider 挂点随单相调用点逐位保持迁移**，rider 腿行为锁归 joy 批验收面）；`CwActionPickPlannerOp.run` 确认点击后立即上报完整结果（leg_type/norm_item 经 env kwargs）、体内 `op._confirm_pending = True` 置位删除；`cw_overlay_pick_action.py` **模块头「三线例外」自述段**改写为单相清零表述（attack2 F6；3.1 未动此段，本批一并清）；`cw_screen_yinlang.py` 删 `_confirm_pending`/`_pending_leg`/`_pick_param`/重入裁决出口门、act 派发即 `round_success` 终结；`test_cw_gain_chain.py` 删 evidence kwarg 机械改写 10 处（attack3 F1，rider 行为锁断言保留）；`test_cw_unified_action_4.py` 删 `op._confirm_pending is True` 置位断言（点击链断言保留，attack5 A1）。**不含**：equip 屏（3.1 已清）；`classify_planner_leg` 语义。
**设计依据**：design.md §2.0（时序等价论证）、§2.1（planner）、§2.2 表、§2.3（取舍 1/3/4 + joy 协调申报）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_planner.py`、`operations/cw_screen/cw_screen_yinlang.py`、`operations/cw_op/cw_overlay_pick_action.py`（CwActionPickPlannerOp 体 + 模块头例外自述段 + `OverlayPickExecEnv` 类 docstring 腿型载荷段）、`sr-od-test/` 受影响测试（含 `test_cw_yinlang_phase32.py`、`test_cw_gain_chain.py`、`test_cw_unified_action_4.py`）
**依赖**：3.1（共享 `cw_overlay_pick_action.py` 防冲突串行）。joy rider 已提交（14dd40977）——原「joy 批先提交」前置已满足（attack3 F4）
**优先级建议**：6
**完成判据**：
- 行为对照 design.md §3 验收锚 2（行为锁：equip 腿命中入栏+后果链 / upgrade 变换+档行+级联 / unknown 留证[弱化词卡文落此] / unrouted 兜底零写——确认点击后容器即持；joy rider 挂点随调用点保持断言；派发即终结断言；planner 来源 `EVIDENCE_OVERLAY_CLOSED` 零残留——范围 = src + sr-od-test；docs 正本面归末阶段正本更新批，attack6 N1 措辞勘误）
- 通用工程门
**验收凭据形式**：planner 单相行为锁测试（equip 腿/upgrade 三态/unknown 留证/unrouted 兜底四型 + joy rider 挂点保持断言）+ `test_cw_yinlang_phase32.py` 重写后全绿

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2 全部完成。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（含 `changes/` 禁引纪律自查）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

✅ - `flow/action_ops.md`：§4.5（**欠账标注段整段摘除**——全域清零；PickPlanner/PickEquip 两行描述更新为单相即时上报）、§1 :22 禁止清单例句换现役反例或不举例（pick_invest 已删，「现役」表述过期）← 3.1/3.2
✅ - `flow/action_exec.md`：§2 事件线 pick 族段（:24 附近「其余屏(策划/补给/装备)=分步形态欠账…欠账标注见 action_ops §4.5」句更新为单相清零表述，消悬空引用；supply 确认行复核）← 3.1/3.2（attack2 F1）
✅ - `screens/op-layer.md`：§1.2 欠账引用句更新（:43 两相欠账清零）、:33 枚举句更新（分步例外清零）、:36 出口①枚举句更新（策划/装备并入派发即终结枚举）、:96 悬空引用清除、§3 节点循环行分型判据更新（yinlang/equip_pick 重入裁决退役改派发即终结）← 3.1/3.2（attack2 F3 + attack6 S3）
✅ - `screens/README.md`：§5.5 单选族表（两行上报形态更新）← 3.1/3.2
✅ - `screens/planner.md`：全篇两相+重入裁决表述清除（**§2(:12)/§4/§5/§6(:55)/开放设计注(:76)** 五处；§1 无涉）← 3.2（attack2 F2）
✅ - `screens/equip_pick.md`：重入裁决/证据闩表述清除 ← 3.1
✅ - `game_state/logic-updates/pick-planner.md`：文件头(:3)/**§2 四行(:11 两相节头/:13 发射相 bullet/:14 落地相 bullet——evidence=EVIDENCE_OVERLAY_CLOSED + 重入裁决出口表述/:17「weaken 零记账」行——weaken 已随 14dd40977 退役,该行现役即与代码不一致)**/§3(:23 _confirm_pending 步)/§5(:33 重入裁决)/§7(:41) 两相与证据闩表述清除 + :37「单一定义在 pick_invest」过期句修正（attack3 F2 锚位勘误；attack4 F1 补 §2 三行；attack5 A2 收回「:14 无涉」误排并把 :14 入清除面）← 3.2
✅ - `screens/README.md` 补：§6(:138) 即时上报枚举更新（attack3 F6）← 3.1/3.2
- 兜底：正本更新批内 `EVIDENCE_OVERLAY_CLOSED` 全域 grep（范围 = src + sr-od-test + docs 正本；豁免 = changes/ 历史工件）+「两相/落地相/发射相」措辞 grep（范围 = src + sr-od-test + docs 正本，覆盖叙述面；豁免 = changes/ 历史工件）← 收尾
