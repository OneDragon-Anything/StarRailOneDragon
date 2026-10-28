# 补给决策链接线 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（只对改动文件跑，禁全仓）；
- 本阶段直接受影响测试全量一次通过（`uv run pytest` 相关子集，路径见各阶段验收凭据）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 补给画面 op 决策链接线（根修）

**范围**：`cw_screen_supply_node.py` 的 act/`_do_action` 按设计重写——决策输入与门槛统一到 `self._obs.options`（§2.1）、执行半两态化（§2.2）、`CARD_BODY` 盲点兜底删除 + 守卫①②补齐（§2.3）、`_sup_opts`/`_refresh_point` 降格执行载体（更名 + 注释收敛）。同步适配测试仓 op 流程面测试。**边界：不含动作 op 文件（`cw_pick_supply_action.py` 动 3.2）、不含正本文档（末阶段）、不含 sim 后端与世界分支（零改动）。**
**设计依据**：design.md §2.1 / §2.2 / §2.3 / §2.6
**文件面**：`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_supply_node.py`；`sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_cw_screen_supply_node.py`；`sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_obs_arch_event_screens.py`；`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_supply.py`（断言形式适配——design §2.6 预测失准的修正，实现期裁定入面）
**依赖**：无
**优先级建议**：0
**完成判据**：
- 行为对照 design.md：空候选零点击终结零派发（§2.1）；pick 内容源 = obs 载体、实机/sim 机械执行分流（§2.2）；`CARD_BODY` 常量与兜底路径不存在、idx 越界 `AssertionError`、词表外返回 `round_fail`（§2.3）；刷新两态——实机锚点+dx 机械点击、sim 经 `文本-剩余次数` area 端口点击触发后端 `_supply_refresh`（§2.2）；
- 对照闸拒绝防线分支有测试覆盖（design §2.6 新增 6）：桩驱动「重调仍返刷新建议」→ 实机 `round_fail` / sim 零点击终结零派发；
- sim 两态新测试通过：装 `SimBackend` 跑补给节点 → `decide_supply` 被调、owned 内容载荷分支入账写行、`chosen_supply` 写行、节点推进（§2.6 新增 1-4）；
- 存量适配测试通过：`test_obs_arch_event_screens.py::test_supply_*` 三条 + `test_cw_screen_supply_node.py` 全量；
- 完成前常规检查（本文件首节）
**验收凭据形式**：测试名——新增 sim 两态测试 + `sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/` 受影响全量

## 3.2 PickSupply 回执接线

**范围**：`cw_pick_supply_action.py` 接 `note_action_receipt`（op/actor = `CwActionPickSupplyOp` 硬编码、screen = `货币战争-补给`、reason 事实码两态语义、detail = idx+内容摘要），照 `cw_op_open_shop.py::_note_receipt` 形态；**新 reason 码词表登记**——`定位缺失(按钮-确认)` 按 kernel 纪律「先登记词表再使用」登记进 `cw_game_state.py::note_action_receipt` docstring 词表（暂住节）。同步扩展动作 op 测试回执断言。**边界：不含画面 op（3.1 已闭）、不含刷新链（不接回执，design §2.4）、不含渲染器；fields.md 正本登记归末阶段正本更新。**
**设计依据**：design.md §2.4 / §2.6（新增 5）
**文件面**：`src/sr_od/application/currency_war/operations/cw_op/cw_pick_supply_action.py`；`src/sr_od/application/currency_war/kernel/cw_game_state.py`（仅 reason 码词表 docstring 段）；`sr-od-test/test/sr_od/application/currency_war/operations/cw_op/test_overlay_ops.py`
**依赖**：无（与 3.1 无代码耦合；端到端联验在 3.3）
**优先级建议**：1
**完成判据**：
- 动作 op 执行后 journal `receipts` 域恰一条回执行，op/screen/actor 字段断言通过；实机定位缺失形态报 `定位缺失(按钮-确认)`，sim 受理恒 reason=''；
- `test_overlay_ops.py::test_supply_pick_op_clicks_target_and_confirms` 扩测通过；
- 完成前常规检查（本文件首节）
**验收凭据形式**：测试名（`test_overlay_ops.py` 扩测）

## 3.3 sim 冒烟局端到端验证

**范围**：skill 驱动脚本跑固定 seed sim 局（`uv run python skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py --seed <固定值>`），验收 journal 断言清单（下）；零生产文件改动，验收记录落本迭代 README 进度行。**边界：不修代码（发现问题回 3.1/3.2 打回路由）；不做跨批统计对照（行为分界批，§2.5 只申报不对照）。**
**设计依据**：design.md §2.5 / §2.6
**文件面**：无（临时验收产物落 `.debug/`）
**依赖**：3.1、3.2
**优先级建议**：2
**完成判据**：
- journal 断言全过：①补给节点出现 `decide_supply` 策略决策记录（strategy 遥测流）；②选卡帧出现 owned 内容载荷分支入账写行（非翻来源行；bench 分支对占位池不可达，不在断言面）；③`chosen_supply` 写行存在；④`receipts` 域出现 `CwActionPickSupplyOp` 回执行；⑤宝钻发放分支**不在本批验收**——sim 占位池下结构性不可达（占位钻标挂基础件名 × `DIAMOND_EQUIP_NAMES` 名单派生失配，design §2.2），激活归前置②批，本批对该分支零断言；⑥全局无「内容全未知翻来源」形态的补给上报行（`pick_supply_content_flip`）；
- 常规检查不适用（零代码零测试改动），仅汇报断言结果。
**验收凭据形式**：journal 行锚清单（对照判据逐项给行号；⑤ = 零断言申报，落验收记录）

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本文档。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/screens/supply.md`：能力面 as-built（两 node 行为、执行两态、守卫、兜底删除）← 3.1
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §1.1：新增实例载体纪律条款（决策输入一律取 obs 载体或容器槽；实例载体只准存机械执行细节，禁承载决策输入、禁作决策门槛）← 3.1
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §1.3：守卫登记补录——补给节点守卫①②条目（「新增屏随其批补录」纪律）← 3.1
- `docs/develop/sr_od/application/currency_war/strategy-docs/30_supply_screen.md` §3/§4/§6：§3 对照闸拒绝处置随防线变更更新（旧文「零点击结束本次访问」）；§4 接线描述两态化；§6 sim 盲区申报改写（前置①完成消除结构性盲区；残项 = 前置②分布真实化 + 占位钻名口径（含宝钻分支激活路径裁定）+ 分布失真声明义务）← 3.1
- `docs/develop/sr_od/application/currency_war/game_state/fields.md` 回执契约节：reason 码词表补录 `定位缺失(按钮-确认)` ← 3.2
- `docs/develop/sr_od/application/currency_war/flow/README.md` §2.3 sim 消费面注记：「全决策面 sim 可达」补限定——补给判据 sim 可调用，占位分布失真声明至前置②完成 ← 3.1
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md`：核对三处表述与新行为一致性，漂移处更新——§3.2 点击源「补给刷新」行、转移声明 `pick_supply` 行、`diamond_count` 写端行 ← 3.3
- `src/sr_od/application/currency_war/kernel/cw_game_state.py`（note_action_receipt docstring 暂住节）：3.2 挂账收敛——既有重复条目（`定位缺失(按钮-商店)`/`定位缺失(按钮-收起)` 各两次）去重 + 「全仓仅 4 处产回执执行链」计数随第 5 处（pick_supply）更新 ← 3.2
