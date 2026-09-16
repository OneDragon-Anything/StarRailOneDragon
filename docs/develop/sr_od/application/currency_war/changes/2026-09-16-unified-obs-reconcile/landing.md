# 统一观察对账与安灯 落地

## 3.1 机制批（对账三分流 + 豁免注册表 + 安灯槽 + 画面名补齐）
**范围**：新建 `kernel/cw_mismatch_policy.py`（`EXEMPT_REGISTRY: dict[tuple[str, str], tuple[ExemptEntry, ...]]` 空 + `ExemptEntry{screen, field, logic_evidence, reason}` + `lookup_mismatch_exempt`（精确桶→通配桶独立评估）+ `_ANDON_HOOK` 槽 + `set_reconcile_andon_hook`；零依赖 `cw_game_state`）；`cw_game_state.observe()` 失配处置改三分流接线（`observe()` 内现 `_emit_defect` 调用处）；`_emit_defect` 增加 sig 形参（行携带观察侧 screen/actor/group_id + 逻辑侧 `Field.evidence`）并补 `ts`（`datetime.now().isoformat(timespec='seconds')`）；`_MISMATCH_SUPPRESS_PREFIXES` 加入 `'sim:synthesized'`；观察侧主喂入口补画面名——`cw_observation.py` 的 `read_game_state` 增加 `screen_name: str | None = None` 可选参（`_sig_read` / `_sig_carry` 链路落 sig.screen），**调用点传其已知画面建档名**（调用面以 grep `read_game_state(` 清点为准：cw_loop / cw_screen_prep / cw_screen_buy_cards 等已知者传名，不知者传 None——现状 `read_game_state(ctx, None, …)` 测试形态不变）。**不含** app 装配（槽缺省关）、**不含**旧安灯删除。
**设计依据**：design.md §2.1-§2.4、§2.2 键坐标系与画面名来源
**文件面**：`kernel/cw_mismatch_policy.py`（新）、`kernel/cw_game_state.py`、`obs/cw_observation.py`、`operations/cw_loop.py`（调用点传名）、`operations/cw_screen/cw_screen_prep.py`（调用点传名）、`operations/cw_screen/cw_screen_buy_cards.py`（调用点传名）、`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 单测覆盖三分流：真失配 → 落 `observe_vs_logic_mismatch` 行（含 ts + screen/actor/group_id/logic_evidence）+ hook 被调；豁免命中（精确 screen 键、`'*'` 通配键、logic_evidence 前缀命中/不命中、同 (screen, field) 多条目并存、screen=None 仅通配可命中各一例）→ `exempt_mismatch` 行（同形状换 kind）+ hook 不被调；sim 前缀 → 不落行不调 hook；hook 缺省 None 零副作用
- 存量测试同步：`test_cw_game_state.py::test_observe_over_logic_mismatch_defect_row_and_sink_drain`、`test_cw_game_state_consume.py` 锁新行形状与抑制语义；`read_game_state(ctx, None, …)` 既有调用形态测试不变（None → sig.screen=None）
- 主喂入口补画面名后：调用点已知画面名处金字段失配行 screen 在场（非 None），精确豁免键可命中
- L1 全绿（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + `ruff check` 干净

## 3.2 金失配全模式归因批
**范围**：design §2.6 辖域全量归因——①86+ 行恒 +2（首位线索：finalize「不可观项混入」注释与免刷 proc，`free_refresh_balance` / `refresh_free_truth` 建模要件已在；**基数为移动值**——慢性模式实时复现中，以归因时点重数为准，可抓现行：journal 尾段即有新鲜样本）；②金散失配单发行；③write_logic 直写端族时序面清点（关店金直写 / node_ledger_backfill / 恢复局 write_logic），逐个定性。**台账内 JSON 跨行截断的坏行残片非失配行，不计入模式统计。**出口三分类：建模补全 / 结构性申报豁免（逐画面申报，禁字段级通配用于执行敏感字段）/ 识别侧误读。**不装配**安灯钩子。
**设计依据**：design.md §2.6
**文件面**：遥测/台账只读；视出口动推算代码、`kernel/cw_mismatch_policy.py`（豁免条目 + 补测试）或识别代码
**依赖**：3.1（豁免条目落点与 sig.screen 存在）
**优先级建议**：8
**完成判据**：
- 归因结论成文（journal 行引用 + 机制解释 + 统计时点与口径注记 + 每条模式的复现载体选型），存本迭代目录 `attribution.md`
- 每条模式落定出口且验收通过：①建模补全/③修识别 = 复现载体复跑零复现（sim 重放该单元序列，或实机局后生产缺陷台账零新增该模式行，选型钉入报告）；②申报豁免 = 条目落地，该模式落 `exempt_mismatch` 行；直写端族逐个定性有结论
- §12 通用工程门

**验收凭据形式**：归因报告 + 修模/识别 diff + 复现载体复跑判读结果（或注册表条目 diff + exempt 行落证）

## 3.3 装配批（武装安灯 + 实机验证期）
**范围**：`currency_war_app.py` `CurrencyWarApp.__init__` 装配段（与 `set_defect_sink` 同点）注入 andon 闭包：每局闩（闭包内 dict，键 run_id）+ run_id 空只落证不停机 + `ctx.controller.screenshot()` 帧经 `debug_utils.save_debug_image` 落盘（前缀 `reconcile_andon_<run_id>_<field>_`，失败不拦）+ 写 `.debug/temp/cw_reconcile_andon.flag`（三要素文案按 design §2.4）+ `ctx.run_context.stop_running(reason='hook:reconcile_mismatch')`。
**设计依据**：design.md §2.4、§2.6 装配后验证期
**文件面**：`currency_war_app.py`、`sr-od-test` 装配/闭包单测
**依赖**：3.1、3.2
**优先级建议**：7
**完成判据**：
- 单测：注入闭包后真失配 → flag 内容含三要素 + stop 调用恰一次；同局第二失配被闩跳过；run_id 空 → 只落证不 stop；截图失败不拦 flag/stop
- 缺省环境（未注入）行为不变
- **实机验证期**：武装后实机连跑 ≥3 局（需用户游戏窗口），停机触发 0、或每触发已归因并按三分类出口处置
- §12 通用工程门

**验收凭据形式**：测试名清单 + 实机局 run_record 与停机触发台账

## 3.4 旧安灯退役批
**范围**：design §2.5 删除面全量（仅代码与测试）——`run_state.py` 整文件；`cw_screen_prep` 安灯段 + 购买单元记账段（含 `visit_open_shop` 暂存块）+ finalize 回填两行（金对拍本体保留）；fact_rows 死通道退役（`ShopLedger.fact_rows` 字段、`note_shop_action_receipt` 形参与调用点、`cw_shop_action_ops` 注释；journal receipts 行与 include_payload 保留、注释动机改归「动作留证」）；`telemetry/query.py` 分类器双函数（grep 复核零消费后删）；`sr-od-test/test_cw_identity_funnel.py` 头注释引用清理。正本文档更新不在本批（归末阶段清单）。
**设计依据**：design.md §2.5
**文件面**：`run_state.py`（删）、`operations/cw_screen/cw_screen_prep.py`、`operations/cw_screen/cw_screen_buy_cards.py`、`operations/cw_op/cw_shop_action_ops.py`、`telemetry/query.py`、`telemetry/match_archive.py`（注释指针）、`sr-od-test/test/sr_od/application/currency_war/test_cw_identity_funnel.py`（注释）
**依赖**：3.3（先武装后拆旧——覆盖连续性）
**优先级建议**：6
**完成判据**：
- `grep` 零残留，扫描范围 = `src/sr_od/application/currency_war` + `sr-od-test` 两仓（docs 归末阶段不进 grep 面）；词表：`exec_fail` / `classify_spend_unit` / `plan_gold_flow` / `_spend_unit_` / `_exec_fail_hook` / `_unit_facts` / `_unit_meta` / `unit_exec_facts_from_receipts` / `fact_rows` / `run_state import`
- L1 全绿；§12 通用工程门

**验收凭据形式**：grep 输出 + pytest

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `flow/guards.md`：§3「执行失败安灯」节 → 改写为「观察对账与安灯」（判定总闸/豁免注册表三分流/安灯契约/验证期）；§5 降级链表对账行同步 ← 3.4
- `flow/README.md`：守卫表「执行失败安灯」行改指新机制 ← 3.4
- `game_state/README.md`：观察赢失配处置语义改三分流（豁免/抑制/安灯）+ 安灯钩子槽 ← 3.1/3.3
- `game_state/fields.md`：失配处置相关段（缺陷行 ts/sig 字段、`exempt_mismatch` 行型；L787「牌名集对比仅作留证遥测与安灯豁免」行按分类器退役改写）← 3.1/3.4
- `game_state/node-domain.md`：缺陷行型描述同步（ts/sig 字段、exempt_mismatch 行）← 3.1
- `screens/prep.md`：购买单元安灯行改指统一对账（L69 引「guards.md §4」顺手纠正为实节）← 3.4
- `screens/shop.md`：L55 / L81③④ / L98 安灯分类器消费与执行失败安灯行改指统一对账 ← 3.4
- `flow/action_exec.md`：L37 RefreshShopOp「牌名集对比仅作安灯 free_refresh_proc 豁免判定输入 + 遥测」改写（verdict 随分类器退役，只剩遥测半边）← 3.4
- `game_state/logic-updates/refresh-shop.md`：L24 同族「仅作安灯豁免判定输入」行改写 ← 3.4
- `kernel/cw_mismatch_policy.py` 模块头正本指针（game_state 对账正本节）← 3.1
