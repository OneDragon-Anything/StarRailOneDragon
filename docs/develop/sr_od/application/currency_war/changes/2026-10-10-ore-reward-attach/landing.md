# 晶矿奖励附着通道 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号与任务 id;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 kernel 声明通道与生成内核
**范围**:生成函数、声明注册表、GameState 三域(ore_rewards / ore_declared_pending / ore_declared_done,含开局种子与快照恢复登记)、挂接入口(容差配对轨迹继承)、声明入队/过期电平函数(纯 kernel 面,无调用方接线)。边界——不含 collect_ore 改造、不含 sim/live 写端接线。
**设计依据**:design.md §2;details/ore-reward-channel.md 全文。
**文件面**:`src/sr_od/application/currency_war/kernel/cw_ore_reward.py`(生成函数)、`kernel/cw_investments.py`(ENV_ORE_GRANTS + 构建校验)、`kernel/cw_game_state.py`(两域定义 + 种子 + 恢复表登记)、`kernel/cw_ore_channel.py`(新模块:挂接入口 + 入队/过期)、`obs/cw_identity_obs.py`(**常量公开化重命名** `_SPHERE_PERSIST_POS_TOL` → `SPHERE_PERSIST_POS_TOL`,含模块内引用点同步;kernel 侧函数体内 lazy import)、`sr-od-test/test/sr_od/application/currency_war/test_cw_collect_ore_rand.py`(生成函数与入口单测)。
**依赖**:无。
**优先级建议**:10
**完成判据**:
- 行为对照 ore-reward-channel §1–§5(三域定义/种子与恢复登记/注册表校验三条/生成函数语义/挂接入口步序含容差配对/**生成集 = 无附着现役身份(含 level 缺读帧后自动补生成)**/**消费 = pending 移除 + done 追加同一写**/入队电平规则与过期电平清理);
- **轨迹继承**:容差配对命中不重掷(roll 调用计数为零)、键重挂写行、**声明金在坐标抖动场景下保全**(构造「坐标漂移 ≤12px 的连续两帧」测试,断言声明附着仍在且未重掷);
- ENV_ORE_GRANTS 与 ENV_ECONOMY 双源同值校验:改一处金额 import 即炸;
- 快照→恢复后 `ore_rewards` 值类型仍为 `dict[str, OreReward]`、`ore_declared_pending`/`ore_declared_done` 仍为 tuple-of-tuple;
- 完成前常规检查(本文首节)。
**验收凭据形式**:单测名(配对继承/抖动保全/生成分配/采样/错档炸;校验器三条;入口步序写行 evidence;种子与恢复)。

## 3.2 点击兑现改造
**范围**:collect_ore 上报按附着值兑现、缺项兜底、level 语义收窄、ore_rewards 键移除;投影审计晶矿条目更新。边界——不改求交/席满守卫/写序/出参语义。
**设计依据**:details/ore-click-consume.md 全文。
**文件面**:`kernel/cw_action_report/collect_ore.py`、`kernel/cw_projection_audit.py`、`sr-od-test/.../test_cw_collect_ore_rand.py`、`test_cw_ore_container.py`、`test_cw_unified_action_2a.py`。
**依赖**:3.1。
**优先级建议**:5
**完成判据**:
- 行为对照 ore-click-consume §1(命中零掷/缺项兜底 evidence 前缀/detach 写序/level 收窄/`ore_reward_attach_missing_level` reason);
- 投影审计条目对照 §3;
- 既有 evidence 名断言不回归(§4,7 处 monkeypatch 迁移面);
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名(命中零掷计数、兜底路径、缺项∧level None reason、键移除、既有写行断言全绿)。

## 3.3 sim 接线
**范围**:节点窗起点声明入队(直发金绕行)+ **位面过渡过期清理接线**、位面开局矿呈现(与奖励节点矿同批合并、坐标面板序续接)、spheres 写端统一过挂接入口、rng 键装配、占位退役、新增披露键。
**设计依据**:details/ore-sim-plane-start.md 全文;ore-reward-channel §4(入口契约)。
**文件面**:`sim/cw_sim_backend.py`、`sr-od-test/.../test_cw_sim_backend.py`、`test_cw_sim_seam.py`。
**依赖**:3.1。
**优先级建议**:5
**完成判据**:
- 行为对照 ore-sim-plane-start §1–§5(入队幂等/过期清理留痕/开局矿与锚点矿同批一次写且坐标无撞键/空读照写清理/掷序确定性/占位删除/披露键新增);
- 增发货币 sim 局:位面开局金不再直发,点击声明矿后金入账(数值 = 6/8,sim 辖域 P1+P2 内实测;**12 由 3.1 生成函数单测覆盖**——sim 第一期 `plane>2` raise,位面 3 不可达);
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名 + sim 局数值对照。

## 3.4 live 挂接
**范围**:备战观察写端 spheres 写改过挂接入口;声明入队/过期**电平规则**接线(observe_full 回执后、spheres 写前检查,无 op 成员/无边沿);策略禁读文档契约。
**设计依据**:ore-reward-channel §4–§5(入口与 live 接线规约:电平规则/次序硬约束/sig 形态);ore-click-consume §2(契约落点)。
**文件面**:`operations/cw_screen/cw_screen_prep.py`、`kernel/cw_prep_actions.py`(契约注)、`sr-od-test/test/sr_od/application/currency_war/test_cw_prep_node_row_housekeeping.py`(备战观察链家计,挂接/入队接线断言落此)。
**依赖**:3.1。
**优先级建议**:5
**完成判据**:
- spheres 观察写端唯一入口 = report_spheres_observed(无第二写径);
- **入队先于同帧 spheres 写**:构造位面过渡帧测试,断言该帧生成即含声明附着(次序接反则声明永不附着的承载性判据);**测试构造约束:`test_cw_prep_node_row_housekeeping` 现行形态 monkeypatch `observe_full`(fake 不写 node)——入队测试的 fake 必须「真实写 node」(或走真漏斗),否则按漏斗前值构造的断言假绿**(plane 写点在 observe_full 漏斗内,见 ore-reward-channel §5);
- **电平静幂等(done 标记)**:构造**同位面多备战环**跨环场景(每环 op 重建,环间声明已被消费),断言声明**仅入队一次、仅兑现一次**(6 金真值场景;守卫失效形态 = 每环重发,对照面 18 金);
- 电平过期清理(位面过渡后旧 plane 条目移除)留痕;恢复局(快照含 done)不重发;
- 契约注落位(select_ore_clicks docstring + 模块头);
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名(挂接写行、入队次序、跨环单发、过期留痕、恢复不重发)+ grep 无旁路写径。

## 末阶段:正本更新
**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1–3.4。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单
- docs/develop/sr_od/application/currency_war/game_state/fields.md:spheres 域节(附着值独立域说明)+ 新域 ore_rewards / ore_declared_pending / ore_declared_done ← 3.1
- docs/develop/sr_od/application/currency_war/game_state/gain-chain.md:环境发放族新增 ENV_ORE_GRANTS 声明矿通道 ← 3.1
- docs/develop/sr_od/application/currency_war/flow/projection_contract.md:状态面板行的域清单内联描述(表格为单行长述,非逐域一行)——补 ore_rewards / ore_declared_pending / ore_declared_done 三域与 spheres 写端统一挂接入口说明 ← 3.1/3.4
- docs/develop/sr_od/application/currency_war/sim/sim-wiring.md:节点窗起点序(声明入队 + 过期清理替代直发金)+ 位面开局矿呈现 ← 3.3
- docs/game/currency_war/research/invest_effects.md:§1 批 2「时点日程」新增增发货币条目(位面开局声明矿流程模型,呈现面首遇待验)← 3.3
