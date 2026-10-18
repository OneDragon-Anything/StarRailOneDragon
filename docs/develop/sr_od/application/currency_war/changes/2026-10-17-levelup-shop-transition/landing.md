# 2026-10-17-levelup-shop-transition 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）；L3 全量（`sr-od-test/ -m "not slow"`）仅 3.5 收尾阶段要求；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交（逐文件点名）；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit 后 `git show --stat` 复核入库面 = 申报面；
- 改 `src/` 代码后实机局前需重启项目 MCP server（本迭代为 sim 离线批，重启义务挂账到下次实机局前）。

### 3.1 商店会话升级意图出口
**范围**：`shop.py::_session_upgrade_check` 收窄为三分支判定（资格门七道成员集全链 / 命中∧不可发射 → None / 未命中 → None；命中∧可发射 → 返回关店动作）；删店内执行分支（`_emit_batch`/键驱动帧/授权帧执行）；`shop_upgrade_close_pending` 键退役（`mandate_state.py` 字段 + `session_scope.py` 重置表行）；会话循环注释同步。**不含**备战侧、词表退役（3.4）。
**设计依据**：design.md §2.1、§2.5（键退役部分）
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`、`mandate_state.py`、`session_scope.py`
**依赖**：无
**优先级建议**：9
**完成判据**：
- 升级命中∧资格门全链通过 → 返回 CloseShop 且 `shop_handled` 不置位；命中∧不可发射 → None（会话照常进买牌/刷新）；未命中 → None（对照 design §2.1 三分支）；
- 完成前常规检查（本文件首节）。
**验收凭据形式**：`test_shop_session_loop.py` 适配 + 新增「转场关店不置标记」「待付窗返回 None」单帧用例。

### 3.2 备战工序：随机态重开位 + 升级执行
**范围**：备战九段序按 design §2.2 重排（新增第 1 步随机态重开：清 `shop_handled` + 开店 + 清信号）；升级检查移第 4 步、资格门全链两屏同参（criteria/levelup 单一源判定函数）；凑金 = `levelup_liquidate_prep` 场景（`one_star_refund_only` → False）+ 排序键①②③；发射 = 单帧原子整批 + 执行帧清 handled 标记；P78-5 兜底腿随场景同步。**不含**信号写入端（3.3）、场景行退役（3.4）。
**设计依据**：design.md §2.2
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/entry.py`、`bridge.py`（工序表）、`criteria/sell_candidates.py`、`criteria/levelup.py`（资格门判定函数出口，如需收口）
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- 排序键三键按序（费用带外→低星→金当量）单帧断言；无停留目标帧①键不分组；发射后 `shop_handled` 清位；资格门七道逐道有拒因计数（对照 design §2.1 成员集）；
- 完成前常规检查（本文件首节）。
**验收凭据形式**：`test_shop_session_loop.py`/备战域单帧用例 + 排序键专项断言。

### 3.3 商业间谍升级回调
**范围**：买经验上报函数升级生效回调（EffectSpec 300201 在册判定 → 抽 5 张 → 偷最贵 3 张 → 剩 2 张为商店新牌面 → 置 `shop_randomized_pending`）；GameState 工程结构组非 Field 簿记槽（写端唯一 = 本回调，先例 = plane_node_sequences）；sim backend 牌面保存与开店呈现（`_shop_record` 接缝）；席满溢出「不入席 + 计数披露」。**不含**实机观察闭环验证（实机观察点，非本迭代码面）。
**设计依据**：design.md §2.3、§2.4
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/level_up.py`（上报链）、`kernel/cw_game_state.py`（簿记槽）、`kernel/cw_gain_effects.py` 或新增回调挂点、`sim/cw_sim_backend.py`
**依赖**：3.2
**优先级建议**：7
**完成判据**：
- sim 断言：持商业间谍升级 → 3 张真实入席 → 信号置位 → 备战重开触发 → 开店呈现剩余 2 张（非重新发牌）；无商业间谍 → 零商店副作用（对照 design §2.3/§2.4）；
- 完成前常规检查（本文件首节）。
**验收凭据形式**：sim 域单帧/短局用例（随机态闭环断言）。

### 3.4 预授权键退役与消费面迁移
**范围**：`levelup_preauth` 键退役 + 三消费面迁移（①节末凑息抑制条件改判据同帧重评〔拓宽申报〕；②发射原子性申报面；③刷新判据整级预留保护载体改判据现值〔拓宽申报〕）；`CwActionLevelUpShopParam` 词表 + 动作注册 + operations 发射面退役；`levelup_liquidate_shop` 场景行退役；`sim/cw_replay.py` 改动作名字符串分发；测试面 7 文件适配（`test_shop_session_loop`/`test_intention`/`test_levelup_prob_axis`〔语义重写〕/`test_sim_smoke_batch` 等，以 sweep 实测为准）。
**设计依据**：design.md §2.5
**文件面**：`mandate_v1/`、`kernel/cw_vocab.py`、kernel 动作注册、`operations/` 发射面、`sim/cw_replay.py`、`sr-od-test/test/...`（7 文件）
**依赖**：3.1、3.2、3.3
**优先级建议**：6
**完成判据**：
- 全仓 grep `levelup_preauth`/`shop_upgrade_close_pending`/`CwActionLevelUpShopParam`（src + sr-od-test）仅剩白名单面；L1 全绿；
- 完成前常规检查（本文件首节）。
**验收凭据形式**：grep 清零输出 + L1 测试报告。

### 3.5 全量验证与 sweep
**范围**：预注册判据 sim 验证（§2.6 全部五条：同 seed 双跑对照 + 溢金帧升级照发/刷新可达 + 人口位不饿死 + 随机态闭环计数 + 判据面禁 hp/胜率自查）；全仓 sweep 八词清零（design §2.7 词表，白名单外）。
**设计依据**：design.md §2.6、§2.7
**文件面**：`.debug` 批目录（报告）、测试仓、依 sweep 结果的小修
**依赖**：3.1–3.4
**优先级建议**：5
**完成判据**：
- §2.6 五条判据逐条有数字/断言对照（批跑报告落 `.debug`，报告路径回填本文件）；
- sweep 清零（白名单外）；
- 完成前常规检查（本文件首节）+ L3 全量。
**验收凭据形式**：批跑报告数字对照 + sweep 输出。

### 末阶段：正本更新
**范围**：按 design §2.7「矛盾文档处置清单」逐条更新（11号稿 §2/02号稿 M3/22号稿/23号稿/flow 两篇/game_state 三篇/screens 两篇/sim-wiring/重做详设三篇 + 工序重编号 ripple sweep）；历史记档与渲染器词表白名单不动。
**设计依据**：design.md §2.7
**文件面**：§2.7 清单所列正本文档
**依赖**：3.5
**优先级建议**：0
**完成判据**：§2.7 清单清零；正本与实现一致；sweep 复跑通过。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `strategy-docs/11_shop_decisions.md` §2（执行位置行/消费点/停留门行/预授权表述）← 3.5
- `strategy-docs/02_mandate_layer.md` M3 行 ← 3.5
- `strategy-docs/22_prep_screen.md`（旗标行/L57 重置行/工序编号）← 3.5
- `strategy-docs/23_shop_screen.md`（收缩判据行对账）← 3.5
- `flow/action_ops.md`、`flow/action_exec.md`（LevelUpShop 行/双类型句）← 3.5
- `game_state/action-logic-state.md` §2.5、`game_state/logic-updates/level-up.md`、`game_state/logic-updates/README.md` ← 3.5
- `screens/README.md`、`screens/shop.md`（LevelUpShop 行）← 3.5
- `sim/sim-wiring.md`（LevelUpShop 行 → 随机态呈现语义）← 3.5
- `changes/2026-10-12-prep-shop-workflow-redesign/details/`（shop_session/line_and_upgrade/prep_pipeline 三篇）← 3.5
