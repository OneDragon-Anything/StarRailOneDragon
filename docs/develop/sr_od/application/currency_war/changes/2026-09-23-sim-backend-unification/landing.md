# sim 统一（SimBackend）落地

> 阶段小节 = 账本立任务的唯一源。设计依据 = [design.md](design.md) + 两详设。

## 3.1 接缝基建批（端口 + 钩子槽 + CwOperation + 换父 + 运行器桩）

**范围**：①新建 `sim/cw_sim_ports.py`（端口五口含 `sim_or_live_observation` 改道 helper + 模块槽缺省关 + 单装配纪律）；②kernel 事件钩子槽（缺省 `None`，转移/事实两类事件广播）；③新建 `operations/cw_operation_base.py::CwOperation`（`screenshot` 哨兵帧 / `round_by_find_and_click_area` / `round_by_find_area` sim 应答 + until 可见性问询）；④operations 树全部直继承 `SrOperation` 类换父（2026-09-23 grep 实测 67；完成判据 = 换父后同 grep 零命中）；⑤`round_by_*` / `screen_utils` 调用点全量清点表 + 直连 controller 旁路逐点 port 检查（含 `prep_actions.py::PrepActionExecutor` 拖拽腿）；⑥转移事件封闭集盘点附录（`details/flow-seam.md` §1 盘点方法；消费 = 本批②广播点接线 + 3.2 backend 订阅）；⑦`sr-od-test/test/harness/` sim 运行器（真 screen_loader + controller 桩触碰即炸 + install/uninstall + fast_sleep）。
**边界**：不含 SimBackend 本体与生成器（3.2/3.3）；逐屏读屏点改道接线归 3.3；不含旧引擎退役；正本文档归末阶段。
**设计依据**：`details/flow-seam.md` §1–§2、§4；`design.md` §2 接口契约与事件钩子契约。
**文件面**：`sim/cw_sim_ports.py`（新）、`operations/`（新基类 + 换父）、kernel 钩子槽所涉上报函数文件、`prep_actions.py`（app 根，直连旁路检查）、`sr-od-test/test/harness/`。
**依赖**：无。
**优先级建议**：10
**完成判据**：
- 端口缺省 `None` 下全量 CW 测试绿（实机路径零行为变化）；
- 桩测试：装最小假后端后 `CwOperation.screenshot` 返回哨兵帧不触 controller、直连 `ctx.controller` 即 `AssertionError`；
- 单装配重复安装 raise、teardown 卸载复位（端口协议测试）；
- 换父后 grep `^class Cw\w+\(SrOperation\)` 零命中；
- L1 全量通过（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q`）。
**验收凭据形式**：测试名 + L1。

## 3.2 SimBackend 核心批（状态机 + 规则件平移 + 选卡获得链 + 词缀 seed + overlay 触发 + 旧引擎退役）

**范围**：①`SimBackend` dataclass（字段收敛表执行：双账消灭三处；新增容器 Field `pending_loss`/`shop_locked`/`diamond_count`；私有簿记落位）；②画面状态机（初始序列 / 转移源两类 / 节点推进序列平移）；③规则件平移（`details/sim-backend.md` §4 归宿表逐模块执行：收入/经验/发牌/offer 采样/coarse 战斗/结算/装备腿走 tool_use 上报）；④选卡腿接获得链（pick 动作走 `report_action_pick_invest_*` → `gain_invest_*`；`apply_env_pick`/`apply_strategy_pick`/`inject_choices` 退役）；⑤词缀入 seed（流键 `reset/affixes`；`RunConfig.enemy_affixes` 降级 override）；⑥overlay 触发层（机制 + 一期目录：开箱/巨星/planner 评估器，巨星消费事实事件）；⑦旧引擎退役执行（`cw_sim_engine.py`/`cw_sim_phase.py` 删除及归宿表全部退役项，全树零引用）；⑧`QUALITY_REWRITE_ENV_NAMES` 迁 kernel 常量位（`PIGGY_ENV_NAMES` 本在 kernel `cw_reward_node.py`，无作业）。
**边界**：生成器与流程联调归 3.3/3.4（本批 backend 以直接驱动测试）；触发目录补全（partner/expert/fate/aha/hack）出局。
**设计依据**：`details/sim-backend.md` 全篇。
**文件面**：`sim/`（backend 新件 + 旧件退役）、kernel（新 Field / 钩子槽消费 / 名单常量 / 上报缺口补语义）、`kernel/cw_game_state.py`（新 Field）、`sr-od-test/` 对应测试。
**依赖**：3.1。
**优先级建议**：9
**完成判据**：
- 旧规则断言平移绿（收入/经验/发牌/结算/装备，自 `test_cw_sim_engine.py` 迁移）；
- 同 seed 同 RunConfig reset 双跑容器逐位一致（确定性测试）；
- 获得链断言：选契约环境送卡入席、选策略卡 burst/板面重写/改件链生效（对齐 `cw_gain_chain` 现役语义）；
- 退役模块全树零引用（grep 零命中）；
- L1 全量通过。
**验收凭据形式**：测试名 + 确定性双跑 diff 为空 + grep 零命中记录。

## 3.3 金路径生成器批

**范围**：①金路径档名生成器 13 个 + 档名注册表（键 = screen_info 档名，子态由生成器内部分派；清单 = `details/flow-seam.md` §3：备战（含晶矿子态、wait_one_one 变体）/商店/battle_wait/补给/投资环境/投资策略/简报/boss 简报/位面过渡/遭遇/开箱/巨星/planner）；②未注册屏呈现 = 响错；③`PrepObservation` 控制信号产出；④逐屏读屏点改道接线（`sim_or_live_observation`，3.1① helper；文件面 = `operations/cw_screen/` 观察 node）。
**边界**：非金路径屏不出注册表；overlay 数据缺口族不落评估器。
**设计依据**：`details/flow-seam.md` §3。
**文件面**：`sim/`（生成器 + 注册表）、`operations/cw_screen/`（读屏点改道接线）、`sr-od-test/` 生成器测试。
**依赖**：3.1、3.2。
**优先级建议**：8
**完成判据**：
- 每生成器单测：构造世界态 → 生成 obs → 经同名 `report_screen_*` 落容器 → 容器字段断言；
- 状态机呈现未注册屏 = 具名响错（测试）；
- 金路径清单覆盖核对（清单逐行有生成器）；
- L1 全量通过。
**验收凭据形式**：测试名 + 清单对照。

## 3.4 首局验收批（全流程联调 + MVP 尺）

**范围**：①首局全流程测试：reset → P1 → P2 boss → 局终，真策略 mandate_v1 决策、真 CwLoop 驱动；②确定性双跑逐位一致；③容器不变式断言（金币不出现无规则依据的负值 / hp 轨迹与结算记录一致 / 经验等级符合规则表 / 局终无未消费败态挂账）；④联调暴露的流程/策略侧真 bug 修复（设计依据不变，修法按各域规范）。
**边界**：性能不在验收面；校准缺口只申报不补齐；overlay 数据缺口族维持披露。
**设计依据**：`design.md` §2 里程碑 M3 尺（四条）。
**文件面**：`sr-od-test/`（验收测试）、联调暴露面所属文件（逐点申报）。
**依赖**：3.3。
**优先级建议**：9
**完成判据**：
- 总纲 M3 四条尺全绿：确定性双跑一致 / 跑完零 op fail 零 retry 耗尽 / 容器不变式断言绿 / 旧规则断言平移全绿；
- L1 全量通过。
**验收凭据形式**：验收测试名 + 双跑 diff 为空记录。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本；辖外申报——`simulate_run` 退役使 A/B 现状从「挂起」变「通道拆除」，写 `.debug/temp/skill_feedback.md`（`sim-testing`/`strategy-work` 两篇现状注记同步，交 skill 迭代方）。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1–3.4 全部。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/sim/`：正本按 SimBackend 新架构重写相关篇（引擎篇退役 / 后端架构篇新增） ← 3.2、3.3
- `docs/develop/sr_od/application/currency_war/flow/README.md`：§2.3「sim 消费面注记」与 §2.4「归因域限定」现值化（全决策面 sim 可达） ← 3.4
- `docs/develop/sr_od/application/currency_war/flow/projection_contract.md`：§3.6「两副面孔」与动作腿表述现值化（sim 动作腿 = op → 上报函数族同构，`cw_sim_actions.apply_player_action` 委托串退役） ← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：新增容器 Field（pending_loss / shop_locked / diamond_count）登记 ← 3.2
