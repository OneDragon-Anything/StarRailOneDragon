# 效果账本自推进迁移 落地

## 3.1 kernel 效果推进段 + 经济提供方
**范围**：`cw_game_state.py` 新增 `register_boundary_economy_provider` 注册口与管线尾段（推进/留证/发放/金结算/容量重锚，best-effort 边界）；接入 `observe_screen_context`。边界：不动四腿本体、不动 `cw_effect_inventory` 现有函数签名、不删 cw_loop 块（下一阶段）。
**设计依据**：design.md §2 方案 1/2 与接口契约。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_game_state.py`；`sr-od-test/test/sr_od/application/currency_war/test_cw_game_state.py`（或新增同名域测试文件）。
**依赖**：无。
**优先级建议**：5
**完成判据**：
- 新增单测：①备战帧管线调用推进 `node_ord` 后账本 advanced 且刷新余额到账；②提供方在场 + settlement killed + streak 可知 → 金面 write_logic 增量 = 收入三支+财富；③未注册提供方 → 跳过金结算、其余段照常；④同帧重复观察幂等（账本去重，无二次发放）；⑤`killed=False` 跳过金结算。
- 现有 kernel 直调测试（advance/grant/settle）全绿不改动语义。
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：上述测试名 + ruff。

## 3.2 cw_loop tick 块删除
**范围**：删备战分支效果账本 tick 块（含到期留证/发放/金结算/容量重锚与 best-effort 边界）；随块失用的 import 清理；sim/测试中依赖 loop tick 时序的经济断言改为直注提供方或直调 kernel。
**设计依据**：design.md §2 方案 3 与行为变化申报。
**文件面**：`src/sr_od/application/currency_war/operations/cw_loop.py`；生产注册点（ctx 级一次性注册，开局链初始化处）；受影响测试文件。
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 全量 CW 测试绿；grep `advance_node|grant_effect_node_refresh_balance|settle_node_boundary_gold|project_effect_capacity` 在 `operations/` 下零残留（kernel/strategies/sim 消费除外）。
- 行为变化两点的回归证据：观察派生即推进（单测已在 3.1）；弹窗腿进入触发推进（新增一例弹窗腿单测）。
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：测试名 + grep 输出。

## 3.3 哨兵交接申报（非代码阶段）
**范围**：在哨兵待办（「备战环空转」面独立小批）的输入清单里补一条：本迁移后账本推进不产生新日志节奏变化（到期留证 warning 行保留），无新增哨兵需求；确认无遗漏后关闭该项核对。
**设计依据**：design.md §1 明确不解决节。
**文件面**：`.debug/progress/` 当前活跃迭代进度账本（本地）。
**依赖**：3.2
**优先级建议**：2
**完成判据**：进度账本登记核对结论（一行）。
**验收凭据形式**：账本条目。

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：全部落地阶段。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单
- `game_state/effect-domain.md`：§节点推进族 现态挂点行（「备战分支 advance_node」→「observe_screen_context 派生管线效果推进段」）← 3.2
- `game_state/strategy-env-impacts.md`：效果桥条目「现态挂点=cw_loop 备战分支 tick…目标态=派生管线效果域段」合一为现状描述 ← 3.2
- `flow/outer_loop.md`：§3 备战表面默认分支进入序中「效果账本节点 tick」步删除（步骤随删重排）← 3.2
- `game_state/README.md`：若索引行描述效果推进挂点则同步 ← 3.2
