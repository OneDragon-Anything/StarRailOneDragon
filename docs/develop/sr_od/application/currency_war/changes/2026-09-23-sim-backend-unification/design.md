# sim 统一（SimBackend）迭代设计（总纲）

## 0. 元信息

- 迭代目标：把 sim 从「策略注入式自驱动引擎」重构为「游戏后端」，让真流程（外层循环 + 画面 op + 动作 op + 策略器 mandate_v1）在 sim 世界之上跑通一局。本迭代是投资效果逻辑计算迭代（`changes/` 外，进度树 `2026-09-23-invest-effects-calc`）登记的前置「sim 统一」。MVP = 确定性跑通一局 P1→P2（用户裁定 2026-09-23：暂不考虑批跑/A/B/统计）。
- 状态：定稿
- 文档清单：
  - `details/sim-backend.md` —— SimBackend：世界模拟、画面状态机、overlay 事实触发层、`_Eng` 字段收敛、旧引擎退役
  - `details/flow-seam.md` —— 流程接缝：端口模块、CwOperation 覆写面、观察生成器、运行器与桩、测试迁移

## 1. 问题与动机

**现状症状**：

- sim 引擎（`sim/cw_sim_engine.py::CwSimEngine`/`simulate_run`）自驱动：自持相位机与世界账本，策略注入式喂帧。唯一策略消费面 = 商店决策驱动器（`decide_shop_screen`；依据 = `docs/develop/sr_od/application/currency_war/flow/README.md` §2.3「sim 消费面注记」：prep 屏编排域在 sim 无实体真值源、不可达）。
- 投资效果消费面狭窄且与流程侧分叉：
  - 选卡分支只写名字不走获得链（`sim/cw_sim_offer.py::apply_strategy_pick`/`apply_env_pick` vs 流程侧 `kernel/cw_action_report/pick_invest_strategy.py` → `kernel/cw_gain_chain.py::gain_invest_strategy`）——契约送卡/骇客改件/burst 即时金/板面重写 sim 全丢；
  - 环境经济消费手读注册表（`cw_sim_engine.py::_apply_env_plane_gold`）；
  - 名单常量住 sim 私有（`cw_sim_offer.py::QUALITY_REWRITE_ENV_NAMES`）= 第二真相源。
- 引擎私有 `_Eng`（`cw_sim_engine.py`）与容器存在三处真双账：`plane`/`round_num` vs `gs.node`；相位载荷（`options`/`supply_opts`/`encounter_opts`/`box_cands`/`ores`）vs 容器各 `*_opts` 槽（写端 = 画面 op 观察上报）；`streak_unsigned` vs 容器带符号连胜（无符号可派生 = `max(带符号, 0)`）。

**动机**：投资效果逻辑计算迭代要求 plaza V4.4 全部 417 条投资卡的效果在「决策层选卡打分、经济模拟、sim 推演」一份实现、双端消费。现状 sim 消费面使每条新建模的卡要么 sim 缺席、要么 sim 另写一份。

**根因归层**：架构——sim 自驱（自当驱动者、自持世界账本、自实现效果消费）与流程侧既有裁决（容器 = 局内事实独占承载；kernel = 规则单一源；两执行面同走上报函数族）平行演化。

**解决方向**（用户裁定 2026-09-23）：驱动反转——真流程当驱动者，sim 退居「游戏后端」。

**解决到哪**：见 §2。**明确不解决**：批跑/A/B/统计工具；战斗与收入校准补齐（coarse 结算照用，hp/掉血类读数缺口申报照旧）；P3 段（现役口径 = 进场即局终 `p3_unobserved`）；入口链/退出链（sim 从对局内起点开始）；overlay 触发目录补全（数据缺口族待实机补档，见详设 §3）；噪声注入（对账失能补偿）；性能。

## 2. 方案

**系统级变化**（读一遍知全貌）：

1. **SimBackend**（世界后端，新）：组合持有 `GameState` + 后端私有运行时（用户裁定 2026-09-23：定名 SimBackend、组合不继承）。内含画面状态机（当前画面 + 载荷）、节点日程与进节点序列、overlay 事实触发层、随机流键体系。世界规则件自旧引擎平移（收入/经验/发牌/offer 采样/coarse 战斗/结算），选卡分支改接 kernel 获得链，敌人词缀入 seed。
2. **流程接缝**（新）：端口模块（缺省 `None` = 纯实机，零行为变化）+ `CwOperation` 基类覆写面（哨兵帧 + `round_by_*` sim 应答 + until 可见性问询）+ 按 screen_info 档名注册的每屏观察生成器（产物走 `cw_screen_report` 同名上报函数落容器）+ 运行器与 controller 桩（fail-loud）。
3. **旧引擎退役**（删，用户裁定 2026-09-23）：`CwSimEngine`/`simulate_run`/`StepResult`/`CwSimPhase` 驱动壳删除；规则件平移后逐模块归宿见详设；`sim/cw_replay.py`（journal 重放）不依赖引擎、不受影响；测试仓 `test_cw_sim_engine.py` 等规则断言平移。
4. **不变式**（全案锁死）：容器一份（`GameState`）；写通道三条各一（观察 = `report_screen_*`、动作 = `report_action_*`、节点 = `report_node_advance`）；决策输入 = 容器直读（不变）；双路径仅「获取观察」与「机械点击」两条分支——观察分支改道 = 每屏显式读屏点一行机械改（helper 接线），决策/动作/节点推进的 op 体零改动。
5. **容器字段判据**（全案锁死）：实机对局中存在且可观察/影响玩法的世界事实 → `GameState` Field（双端受益）；实机不可观察的生成器采样簿记 → SimBackend 私有。禁第三形态（GameState 子类）。

**详设划分与跨详设接口契约**（唯一必须在总纲定死的深度内容）：

- 接口契约唯一载体 = `sim/cw_sim_ports.py`（flow-seam 详设定形，sim-backend 详设消费）：
  - `install_sim_backend(backend)` / `uninstall_sim_backend()`：模块槽缺省 `None`；进程内单装配重复安装 raise；teardown 必卸（模式先例 = `decision_assembly.install_obs_ports` 家族「模块级槽 + 缺省关 + 装配点显式接通」）。
  - `screen_identity() -> str`：画面状态机答 screen_info 档名。
  - `observe(screen_name)`：生成器直出该屏 `CwScreenXxxObs` 形状产物；消费方 = 画面 op 读屏点，产物必须经 `cw_screen_report` 同名上报函数落容器。
  - `sim_or_live_observation(screen_name, live_read)`：读屏点改道 helper（装了后端 → `observe`，否则原读链）；定义在端口模块，逐屏显式读屏点一行接线（flow-seam 详设 §2）。
  - `click_answer(op, screen_name, area_name, until_find_all, until_not_find_all) -> OperationRoundResult`：点击 = 档案点位直成功；until = 问状态机可见性。
  - `visible(screen_name, area_name) -> bool`：until / 门可见性问询。
- **事件钩子契约**（SimBackend 消费；经 kernel 事件钩子槽广播——模块级槽 + 缺省关 + 装配点接通，先例 = `kernel/cw_game_state.py::set_defect_sink`；op 代码零改动）。槽载两类事件：
  - **转移事件**（引发画面转移的具名封闭集；权威源 = `docs/develop/sr_od/application/currency_war/screens/` 各篇终结/交回表 + `cw_action_registry` 注册表）：已知成员 `report_node_advance`（trigger 封闭集 {settle_confirm, supply_confirm}，flow/README §1）、start_battle、pick 族确认、开箱动作落地；盘点方法 = flow-seam 详设 §1。
  - **事实事件**（不引发画面转移的世界变化；overlay 触发层消费）：板面组成变化（deploy / 买牌合成 / sell / wear 落地后）、升星事件；广播点 = 对应上报函数写后。
- **里程碑**：M0 基建（端口/基类/换父/桩/运行器）→ M1 SimBackend 核心（状态机 + 规则件平移 + 选卡接获得链 + 词缀入 seed + overlay 触发机制与一期目录）→ M2 金路径生成器（13 档名，含子态分派）→ M3 首局验收（确定性双跑一致 / 跑完零 fail / 容器不变式 / 旧规则断言平移）。阶段拆分与验收判据见 `landing.md`。
