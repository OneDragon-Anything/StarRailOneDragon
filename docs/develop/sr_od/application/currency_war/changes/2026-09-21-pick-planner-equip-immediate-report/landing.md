# PickPlanner/PickEquip 两相上报清偿 落地

> 阶段小节 = 账本唯一源（立任务照各节 `dag.py add`，criteria 预注册指向本节）。
> **通用工程门**（定义 = 本节；源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）：ruff 改动文件 + 直接受影响测试全绿。

## 3.1 选择装备屏单相化（equip 先行）

**范围**：`kernel/cw_action_report/pick_equip.py` 单相化（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED`，一口写 owned 入栏+后果链，未解析翻来源留证语义保持）；`cw_screen_equip_pick.py` 组装点换 `normalize_registry_equip_name`（T-1 已建入口）、删 `_pick_pending`/`_pending_pick`/重入裁决出口门、act 派发即 `round_success` 终结；`CwActionPickEquipOp.run` 确认后（点卡后固定等 1.2s）立即上报完整结果。**不含**：planner 屏（3.2 辖内）。
**设计依据**：design.md §2.0、§2.1（equip）、§2.2 表、§2.3（取舍 1/2/4）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_equip.py`、`operations/cw_screen/cw_screen_equip_pick.py`、`operations/cw_op/cw_overlay_pick_action.py`（仅 CwActionPickEquipOp 体）、`sr-od-test/` 受影响测试（含 `test_cw_pick_channels_t60.py` EQUIP_EVIDENCE 面）
**依赖**：无
**优先级建议**：7
**完成判据**：
- 行为对照 design.md §3 验收锚 1（行为锁：点卡后容器即持 owned 规范名+后果链，含泛用注册表件归一命中用例；派发即终结断言；pick_equip 来源 `EVIDENCE_OVERLAY_CLOSED` 零残留）
- 通用工程门
**验收凭据形式**：equip 单相行为锁测试（命中/未解析/泛用件三型）+ `test_cw_pick_channels_t60.py`/`test_cw_yinlang_phase32.py` 受影响面全绿

## 3.2 骇入策划屏单相化（planner）

**范围**：`kernel/cw_action_report/pick_planner.py` 单相化（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED`；一口写 = ⓪unknown/weaken 留证/零写分支逐位保持 → equip 腿 → upgrade 变换窗三态+档行，前置硬校验语义逐位保持）；`CwActionPickPlannerOp.run` 确认点击后立即上报完整结果（leg_type/norm_item 经 env kwargs）、体内 `op._confirm_pending = True` 置位删除；`cw_screen_yinlang.py` 删 `_confirm_pending`/`_pending_leg`/`_pick_param`/重入裁决出口门、act 派发即 `round_success` 终结。**不含**：equip 屏（3.1 已清）；`classify_planner_leg` 语义。
**设计依据**：design.md §2.0（时序等价论证）、§2.1（planner）、§2.2 表、§2.3（取舍 1/3/4）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_planner.py`、`operations/cw_screen/cw_screen_yinlang.py`、`operations/cw_op/cw_overlay_pick_action.py`（仅 CwActionPickPlannerOp 体）、`sr-od-test/` 受影响测试（含 `test_cw_yinlang_phase32.py`）
**依赖**：3.1（共享 `cw_overlay_pick_action.py` 防冲突串行）
**优先级建议**：6
**完成判据**：
- 行为对照 design.md §3 验收锚 2（行为锁：equip 腿命中入栏+后果链 / upgrade 变换+档行+级联 / unknown 留证 / weaken 零写——确认点击后容器即持；派发即终结断言；planner 来源 `EVIDENCE_OVERLAY_CLOSED` 零残留）
- 通用工程门
**验收凭据形式**：planner 单相行为锁测试（equip 腿/upgrade 三态/unknown/weaken 四型）+ `test_cw_yinlang_phase32.py` 重写后全绿

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2 全部完成。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（含 `changes/` 禁引纪律自查）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `flow/action_ops.md`：§4.5（**欠账标注段整段摘除**——全域清零；PickPlanner/PickEquip 两行描述更新为单相即时上报）← 3.1/3.2
- `screens/op-layer.md`：§1.1（重入裁决「仅限未迁移屏」清单收敛——yinlang/equip_pick 行迁出）、§1.2（欠账引用面复核清零）、§3（分型表 yinlang/equip_pick 行注：重入裁决退役改派发即终结）← 3.1/3.2
- `screens/README.md`：§5.5 单选族表（两行上报形态更新）← 3.1/3.2
- `screens/yinlang.md`（如存在该篇）：对应节更新 ← 3.2（正本更新批先核该篇在册性）
- `screens/equip_pick.md`：重入裁决/证据闩表述清除 ← 3.1
- 兜底：正本更新批内全仓 grep `EVIDENCE_OVERLAY_CLOSED`（验收锚 3 口径，零豁免）+「两相/落地相/发射相」在 action_ops §4.5 的残留表述 ← 收尾
