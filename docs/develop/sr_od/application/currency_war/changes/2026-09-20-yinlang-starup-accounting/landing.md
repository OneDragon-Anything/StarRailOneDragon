# 银狼升星记账 落地

> 阶段小节 = 账本立任务的唯一源（照小节 `dag.py add`，criteria 预注册指向本节）。设计依据 = [design.md](design.md)（定稿）。

## 3.1 费用档字段 + 访问器 + 观察除数修复

**范围**：①`GameState` 顶层字段 `lv999_cost_tier: Field[int]`（默认 None；值域 {3,4,5}；归 `match_facts` 域，域版本 bump 并在 `DEFAULT_GS_SCHEMA` 行注明；`cw_projection_audit.py` 登记投影审计行）；②kernel 单一访问器 `cw_economy.py::effective_cost(gs, char_id)`（银狼LV.999 → 档字段 None 归约 3；其余 → 注册表 `CHARACTERS[char_id].cost`；未注册 → 0；docstring 含双语义边界 + 档分支扩展位声明 + 与 `bench_char_cost` 的口径分野）；③`resolve_cost_star` 参数语义升级改名 `roster_cost`→`base_cost` + 调用点（`cw_observation.py:1988`）改传 `effective_cost`，穿线 = `game_state_from_ctx(ctx)`、None → `ch.cost` 现役兜底。
**边界**：不含 pick_planner 迁移（3.2）；不含 deploy 档行（3.3）；静态画像族/估值族/sim 池零触碰（design §2.6）。
**设计依据**：design.md §2.1 / §2.3 / §2.0（判据与定谳）。
**文件面**：`kernel/cw_game_state.py`、`kernel/cw_economy.py`、`obs/cw_observation.py`、`kernel/cw_projection_audit.py`；`sr-od-test/` 对应测试。
**依赖**：无。
**优先级建议**：9
**完成判据**：
- 访问器三形态锁（LV.999 None→3 / 档值透传 / 其余角色注册表值 / 未注册→0）；
- `resolve_cost_star` 纯函数用例：badge=4/档=4→1★/4费、badge=12/档=4→2★/12费、badge 缺失→roster_fallback 语义不变；
- 调用点穿线后商店观察在档≠起始费时 cost/star 正确（误记消除锁）；None 兜底路径语义不变；
- L1 通过。
**验收凭据形式**：测试名 + L1。

## 3.2 pick_planner 两相迁移 + 升费腿档行

**范围**：①新建 `kernel/cw_action_report/pick_planner.py`：`report_action_pick_planner_param` 两相（发射相意图遥测零写 / 落地相 `EVIDENCE_OVERLAY_CLOSED` 分派：equip 腿入栏+后果链原样迁入、upgrade 腿变换窗三态 + 恰一枚且现档<5 → 变换落行后级联前写档行 `planner_upgrade_tier`、现档=5 → 不写留证 `planner_upgrade_tier_ceiling`、多枚/零枚档不动、unknown/weaken 原样）；②`cw_screen_yinlang.py` 落地记账块删除 + 重入裁决出口改调 report（落地相）+ 发射 param 挂实例 `self._pick_param`；③`cw_overlay_pick_action.py` PickPlannerOp 发射上报改调新 report；④`zero_writes.py` planner 委托退役；⑤测试迁移面全项（design §2.2 申报：8+ 直调迁移、zero_writes 导入面、两相对照、档行断言、resolve_cost_star 用例已在 3.1）。
**边界**：sim planner 效果腿维持占位披露；decision 半/classify_planner_leg/证据闩机制本体零改动（只迁宿主）；`merge_simulate` 引擎零改动。
**设计依据**：design.md §2.2（全分支与时序定点）。
**文件面**：`kernel/cw_action_report/pick_planner.py`（新建）、`operations/cw_screen/cw_screen_yinlang.py`、`operations/cw_op/cw_overlay_pick_action.py`、`kernel/cw_action_report/zero_writes.py`；`sr-od-test/` 对应测试。
**依赖**：3.1（访问器 + 字段）。
**优先级建议**：9
**完成判据**：
- 升费选卡落地：恰一枚 → 变换 + 级联 + 档行三落（时序锁）；多枚/零枚 → 档不动 + 留证；现档=5 → ceiling 留证零写；
- 装备选卡落地：入栏 + 后果链（回归）；未解析 → 翻来源留证（回归）；
- 证据闩幂等锁：确认未落地重走 → 落地相不重复应用；
- zero_writes planner 委托归零；发射相零容器写锁；
- L1 通过。
**验收凭据形式**：测试名 + L1。

## 3.3 上阵变费腿档行 + 观察面 OCR 建档 area

**范围**：①`deploy_move.py` 变换窗补档行：落位 = (银狼LV.999, 3★) 且现档<5（`effective_cost` 读口）→ 落场写后补 `write_logic(lv999_cost_tier, 现档+1)`（evidence=`deploy_upgrade_tier`）；现档=5 → 恒等搬运；②`cw_screen_yinlang.py` observe node 文本归属过滤改两卡 area rect 中心点判定（先例 `_anchor_hit_full_ocr` 同式），rect 经 `screen_loader.get_area('货币战争-银狼升星', '骇入选项-左卡/右卡')`，area 缺失回退硬编码带；`CARD_TEXT_Y_LO/HI` 退役。
**边界**：识别面捕获集变化的实机对拍归实机窗（§2.4 申报已覆盖）；deploy 其余路径零行为差。
**设计依据**：design.md §2.5 / §2.4。
**文件面**：`kernel/cw_action_report/deploy_move.py`、`operations/cw_screen/cw_screen_yinlang.py`（仅 observe node）；`sr-od-test/` 对应测试。
**依赖**：3.1（访问器）；3.2（同测试文件 `test_cw_yinlang_phase32.py` 防并行冲突）。
**优先级建议**：8
**完成判据**：
- (银狼LV.999, 3★) 档<5 上阵 → 落场 1★ + 档行两落（变换窗锁扩展）；档=5 → 恒等搬运零差；
- 观察过滤走建档 rect（area 命中锁）+ 兜底路径行为不变（两 node family 族锁适配）；
- L1 通过。
**验收凭据形式**：测试名 + L1。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：全部落地阶段。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/flow/action_ops.md`：§4.5 PickPlanner 行（两相形态收编：发射相/落地相语义 + 档行）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/pick-planner.md`：容器写语义从「零写」改两相落地相分步（§1/§2/§7）← 3.2
- `docs/develop/sr_od/application/currency_war/screens/planner.md`：代码/建档/观察面（area 过滤）/落地相（pick_planner.py）← 3.2/3.3
- `docs/develop/sr_od/application/currency_war/screens/README.md`：§5.5 planner 零写注（两相例外）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：`lv999_cost_tier` 字段节（当前费用档语义/写端清单）← 3.1
- `docs/game/currency_war/research/equipment_mechanics.md`：§7:162-163 待实测边角清偿（档行+观察对账定谳「新费档」归属）← 3.1/3.2
- `docs/develop/sr_od/application/currency_war/strategy-docs/25_event_overlays.md`：银狼升星行处理形态注（如引用两相语义）← 3.2
