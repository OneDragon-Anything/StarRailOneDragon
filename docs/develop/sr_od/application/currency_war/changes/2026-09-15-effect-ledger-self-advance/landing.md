# 效果账本自推进迁移 落地

> 阶段 3.1/3.2 的拆分原则：kernel 段先以**未接线**形态落地（直调单测），接线与 loop 块删除**同一提交原子切换**——两驱动共存窗口不落盘（攻击 F7）。

## 3.1 kernel 效果推进段 + 经济提供方（未接线）
**范围**：`cw_game_state.py` 新增 `register_boundary_economy_provider` 注册口、`boundary_settled_ord` 工程字段、效果推进段函数（独立可调、未接入 `observe_screen_context`）。边界：不动四腿本体、不动 `cw_effect_inventory` 现有函数签名、不动 `observe_screen_context`、不删 cw_loop 块。
**设计依据**：design.md §2 方案 1（a-f 全项，含 None 守卫随迁、双水位、参数源派生层反解、best-effort 边界）。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_game_state.py`；`sr-od-test/test/sr_od/application/currency_war/test_cw_game_state.py`（或新增同域测试文件）。
**依赖**：无。
**优先级建议**：5
**完成判据**：
- 直调段函数单测：①`effective=None` → 整段跳过（账本零推进、零发放——「未观察不当真进节点」守卫）；②备战帧派生序推进 → 账本 advanced + 刷新余额到账；③金结算：提供方在场 + killed + streak 可知 → `NodeBoundarySettlement.written=True` 且 `branch`/`income_total` 与 `_node_key_for_ord(effective)` 反解键一致（错窗防护判据）；④同序重复调用幂等（无二次发放/结算）；⑤`killed=False` → 金结算跳过、其余段照常；⑥未注册提供方 → 金结算跳过、其余段照常；⑦`node.value.kind` 为空串 → 照传（else→combat 现值语义，非跳过）。
- 现有 kernel 直调测试（advance/grant/settle）全绿不改动语义。
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：上述测试名 + ruff。

## 3.2 原子切换：管线接线 + cw_loop tick 块删除（同一提交）
**范围**：`observe_screen_context` 尾段接入效果推进段；cw_loop 备战分支效果账本 tick 块删除（含金结算成功 log.info 与段失败 warning 旧行）；生产注册点落地（ctx 级一次性注册，provider 动态读 `ctx.cw_match`）；随块失用 import 清理；sim/测试中依赖 loop tick 时序的经济断言改为直注提供方或直调 kernel。
**设计依据**：design.md §2 方案 2/3、行为变化申报（四条全项）、接口契约。
**文件面**：`src/sr_od/application/currency_war/operations/cw_loop.py`；`src/sr_od/application/currency_war/kernel/cw_game_state.py`（接线 diff）；生产注册点所在文件（应用装配）；受影响测试文件。
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 全量 CW 测试绿。
- F1 错窗防护回归：0q 位面过渡场景单测——推进至 (p+1,1) 后金结算参数为反解键（非镜像旧键 (p,9,'boss')），且 boss 收入不重结、新节点收入恰结一次。
- F7 双驱动回归：弹窗腿先推进形态单测——后续备战帧结算恰一次、账本余期/刷新无双扣。
- grep `advance_node|grant_effect_node_refresh_balance|settle_node_boundary_gold|project_effect_capacity` 在 `operations/` 下零残留（kernel/strategies/sim 消费除外）。
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：测试名 + grep 输出。

## 3.3 哨兵交接申报（非代码阶段）
**范围**：向哨兵待办（「备战环空转」面独立小批）申报**日志形状变化**并核对哨兵影响面：①金结算成功行标签 `[cw-loop] 节点边界金结算…` → `[cw][effect] 节点边界金结算…`；②段失败行 `[cw-loop] 效果账本 tick 失败…` → `[cw][effect] 效果推进段失败…`；③到期留证 warning 行不变。核对结论：`[cw][effect]` 不在哨兵 LOOP 白名单前缀（`cw_sentinel.py` LOOP_PREFIXES）与 HIT 词表中，无哨兵语义影响；登记核对结论一行。
**设计依据**：design.md §2 行为变化申报（日志形状条）。
**文件面**：`.debug/progress/` 当前活跃迭代进度账本（本地）。
**依赖**：3.2
**优先级建议**：2
**完成判据**：进度账本登记核对结论（一行，含上述三点）。
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
- `flow/outer_loop.md`：§3 进入序「GameState 心跳观察者采样 + 效果账本节点 tick」合并步**整步删除**——心跳采样半句已随先行提交（删除观察断流心跳采样）从代码移除，效果账本 tick 半句随本迭代 3.2 移除 ← 3.2
- `game_state/effect-domain.md`：§节点推进族 现态挂点行（「备战分支 advance_node」→「observe_screen_context 派生管线效果推进段」）← 3.2
- `game_state/strategy-env-impacts.md`：效果桥条目「现态挂点=cw_loop 备战分支 tick…目标态=派生管线效果域段」合一为现状描述；迁移三面③（计数器退役）标注挂效果域批 M3 ← 3.2
- `game_state/README.md`：若索引行描述效果推进挂点则同步（条件项）← 3.2
