# 银狼专属装备全生命周期闭环 落地

> 阶段小节 = 账本立任务的唯一源（照小节 `dag.py add`，criteria 预注册指向本节）。阶段顺序 = 依赖优先：无采证门槛的落码批（3.2/3.4）先行或并行，候实机窗口的采证批（3.1）与其消费批（3.3）随后。

## 3.1 采证定谳批（实机采证 + 定谳档）

**范围**：实机局窗口内采集并定谳四项，产出定谳档（每项三槽：证据帧/journal 指针 / 结论 / 分支裁决）：
①R5① 欢愉契约条件腿到账形状（触发时点/频率/bench 增员?）；②R5② 特邀专家：银狼入席形态（双腿入席 vs 纯入商店）；③R3 席满未入席（`placed=False`）后续到账形态（延迟补发 vs 消失）；④T-56 千冶·刃来源卡定谳（不在银狼族 10 件内、不在 R2 定谳范围，来源另查）。
**边界**：零代码；R2 送角色腿与 R1 升费腿**已定谳不在采证范围**（design.md §2.2/§1.2）；事件随机未遇 = 该项挂 wait 候窗口（cond=「实机局遇对应事件」），禁按猜定谳。
**设计依据**：design.md §2.3 / §2.4 / §2.6。
**文件面**：`changes/2026-09-18-yinlang-exclusive-loop/details/evidence-verdicts.md`（新建）；截图/journal 归 `.debug/`（不入 git）。
**依赖**：无（候实机局窗口）。
**优先级建议**：8
**完成判据**：
- 四项逐项有证据指针 + 结论；①② 的分支裁决已按 design.md §2.3 预声明规则填毕；
- ④ 含来源卡定谳结论（在册卡名 or 量域/dead 裁决建议）。
**验收凭据形式**：定谳档对照（journal 行号/帧路径可复查）。

## 3.2 R1+R2 落码批（planner 双腿记账 + 送角色腿申报吸收）

**范围**：①R1 决策半载荷扩展（腿型判定 kernel 单一源 + 件名注册表相似归一（**最长名优先**，防「分身墨镜Max」被短名截胡）+ `OverlayPickExecEnv` 载荷字段）；②R1 发射点记账（装备腿双路：名键 `grant_equip_item` 主路 / 未解析双 pending+台账行兜底路；升费吸收窗 = `planner_upgrade_pending` 置位端（前置硬校验：恰一枚 2★银狼LV.999）+ merge_simulate 期望终态判定器；op 实例幂等闩）；③R2 落码（定谳口径，design.md §2.2：`EXTERNAL_BENCH_GRANTS` 三件条目 + 混合键域隔离注释 + 置位端单一源 helper + planner/随机两通道 + 三件 bench 吸收形状 = merge_simulate 期望终态全等（含合成级联）+ `EQUIP_REWRITE_DECLARATIONS` 读法统一 + `EQUIP_WRITE_SIDES` 分身墨镜系两行值 bridge→observation）；④prep heavy 帧读序调整：装备库存观察写端前置到 bench 观察写端之前（同帧双授予击穿修法，design.md §2.2；改动限两写端先后，不动识别）；⑤开工前机械核验升费表述修正批已落库（真身 commit `4e4a2769d`，grep 三处）；⑥测试仓锁（腿分类、归一双路、吸收窗置位/判定、三件置位/吸收含级联形状、幂等重入、读序同帧形状、恰等锁族）。
**边界**：sim planner 效果腿维持占位披露（不在本批）；R7 估值不在本批；R5 申报不在本批（候 3.1 定谳）；既有卡名键授予的纯超集吸收门零改动（merge 判定只辖三件 helper 路径与升费窗）。
**设计依据**：design.md §2.1 + §2.2（全部分支、假吸收防线与 fail-closed 边界在两节内）。
**文件面**：`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_planner.py`、`operations/cw_op/cw_overlay_pick_action.py`（仅 env 载荷字段）、`operations/cw_screen/cw_screen_prep.py`（仅读序）、`kernel/cw_events.py`（腿型判定单一源）、`kernel/cw_merge_simulate.py`（只消费不改引擎）、`kernel/cw_effect_inventory.py`（申报注释）、`kernel/cw_mismatch_policy.py`（三件条目 + 辖域/键域注释）、`kernel/cw_game_state.py`（置位端 helper + 吸收差额扫描 + 升费吸收窗判定器）；`sr-od-test/` 对应测试。
**依赖**：无前置阶段（3.1 不再是前置——R2 已定谳、R1 升费腿已定谳、装备腿双路自洽不需采证）。
**优先级建议**：9
**完成判据**：
- 选装备项：件名唯一命中 → 装备库存逻辑 +1 且三件命中时 bench pending 同帧置位（主路）；未解析 → 装备+bench 双 pending + 台账行（兜底路），吸收实测收口；
- 选升费项：置位前置校验（恰一枚 2★）→ 下一备战帧全域多重集 == merge_simulate 期望终态 → 吸收留行；形状不等照真失配响停；round_retry 重入不双记账；
- 随机通道：装备吸收命中三件 → bench pending 置位 → 同帧/次帧 bench 读按 merge 形状吸收授予单位（含凑满合成级联帧）；planner/随机两通道不双置；
- 同帧双授予形状锁：prep 帧内装备读先行 → bench 吸收一次通过（骇客卡 2+改件 1 形状）；
- 恰等锁族（`scan_rewrite_equipments` 等）不红；L1 通过。
**验收凭据形式**：测试名 + 实机单事件验证（planner 事件 / 三件到货事件对拍 journal）。

## 3.3 R5 申报裁决批

**范围**：按 3.1 定谳逐项落地：①欢愉契约条件腿按裁决（量域申报 or 排除项定谳注释）；②特邀专家：银狼按裁决（`EXTERNAL_BENCH_GRANTS` 补条摘排除 or 排除项定谳注释）；③配套测试仓锁与注释同步。
**边界**：不做政策级统一（T-20 域）；不动 R2 已落的三件条目。
**设计依据**：design.md §2.3（裁决规则已预声明，本批只按定谳填事实执行）。
**文件面**：`kernel/cw_mismatch_policy.py`、（量域形态若选）`kernel/cw_game_state.py`；`sr-od-test/` 对应锁。
**依赖**：3.1（①②定谳）。
**优先级建议**：6
**完成判据**：
- 两悬案逐项按定谳落地（申报条目 or 定谳注释），表/注释/锁三面一致；
- L1 通过。
**验收凭据形式**：表条目 diff 对照定谳档 + 测试名。

## 3.4 R4 门补齐 + R3/R8 残余收口批

**范围**：①R4 回退分支候选追加 `_wearable_gate_ok(worn=[], char='', item)` 过滤 + 测试锁；②R3 过期注释同步（`cw_effect_inventory.py` 载体段头注与 `EQUIP_REWRITE_DECLARATIONS` 同款措辞）+ 席满形态按 3.1③ 裁决处置（延迟补发 → 吸收预案；消失 → 注释申报收口）；③R8 两处术语注释（`cw_equipment_wear_rules_data.py` 旁证③、`cw_factions.py:105`）；④`spawn_equip_bench_unit` docstring 过期面同步（对抗审⑦：「银狼LV.999 星级未采证禁走本桥」等措辞按定谳更新；服务面行随分身墨镜系改辖申报表核订）；⑤R6 依赖申报（对抗审⑥，零码注释）：在 R2 helper/记账注释面登记「识别读完整性 = 记账正确性前置，漏检放大记账错误，安灯排查先核识别再断言记账」。
**边界**：不动识别面（R6 独立批，排除维持、放大因子登记见 design.md §2.8）；不动分配主路径；merge_simulate 引擎本体零改动。
**设计依据**：design.md §2.5 / §2.6 / §2.7 / §2.8（R6 依赖申报节）。
**文件面**：`kernel/cw_equip_wear_plan.py`、`kernel/cw_effect_inventory.py`（注释与预案 + docstring 同步）、`data/cw_equipment_wear_rules_data.py`（注释）、`data/cw_factions.py`（注释）；`sr-od-test/` 对应锁。
**依赖**：无前置依赖（①③④⑤可即派；②的席满处置段依赖 3.1③）。
**优先级建议**：7
**完成判据**：
- 身份读失败帧 + 专属件在 owned → 回退计划不含专属件（fail-closed 锁）；无门件计划行为不变；
- 注释面 grep「接线归辖批」零命中（载体域）；`spawn_equip_bench_unit` docstring 与定谳口径一致；
- R8 两处注释与 t54 例②实证口径一致；⑤依赖申报注释在位；
- L1 通过。
**验收凭据形式**：测试名 + grep 归零。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2、3.3、3.4 全部。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/game/currency_war/research/equipment_mechanics.md` §8（银狼专属装备）← 3.2（R2 定谳入正本：三件获得即送单位、bench 直授、与购买一致含合成/升星语义；升费腿实证增量归 §7）
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/pick-planner.md` ← 3.2（「容器 GameState 零写」声明 → 双腿记账逐动作逻辑态：装备腿逻辑写主路/双 pending 兜底 + 升费吸收窗申报）
- `docs/develop/sr_od/application/currency_war/flow/action_ops.md` §4.4（PickPlanner 行）← 3.2（发出即记账载荷语义）
- `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md`（申报表/写端登记对应节）← 3.2（R2 表辖域与写端值变化）+ 3.3（R5 申报变化）
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`（ExecBooks 置位端注释 + 新字段 `planner_upgrade_pending`）← 3.2
