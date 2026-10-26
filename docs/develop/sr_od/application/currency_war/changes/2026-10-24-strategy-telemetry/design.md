# 策略遥测 迭代设计（总纲）

## 0. 元信息
- 迭代目标：策略侧遥测——决策记录（信封+载荷）自动采集、独立存储、回执关联、复盘报告按需装配。需求原话锚（用户 2026-10-24）：「策略侧的遥测数据，是单独的，复盘脚本里按需加载对应的策略侧数据；以后实现多个策略器，每个策略器存的变量都不一样；复盘报告 = 画面op: 观察、策略发出动作op的依据(由策略遥测数据提供)、动作op」。
- 状态：草案
- 文档清单：
  - [details/capture-store.md](details/capture-store.md) —— 采集与存储：信封规范/捕获缝/dtag 关联锚/落盘与装配
  - [details/render-assembly.md](details/render-assembly.md) —— 消费端：渲染器发现/加载/join/报告块

## 1. 问题与动机
- 现状症状（sim 局 g_20261024_191633 复盘实证，报告 = `.debug/currency_war/telemetry/sim/sim_match_20261024_191618/review_g_20261024_191633.md`）：
  1. **方向状态零遥测**：锁定态（`target_comp`）不落 journal、不在对局档案（四键全文零命中，编排者复核实证）——「线何时锁定、哪条触发腿」不可判；复盘中「线锁定自 R1」推断因 `m2_locked_member` 标记在未锁定期同样发射而被打回（同报告「编排者复核勘误」节）；
  2. **策略行为计数只有终局聚合**：cw4_counters 仅在 match_final 收口行落盘（同局 journal v=618），`m1p_plan_empty=12` 无法定位是哪些评估帧、当时判据输入是什么；
  3. **主路径缺位自证**：`operations/decision_frame_hooks.py:3-7` 模块头明示「本钩子是识别仲裁留存证据，不是遥测替代——**决策依据的结构化重建才是主路径**」，主路径至今未建。
- 根因归层：**约定层**。策略↔流程契约（CwStrategy 终态契约，2026-09-16-strategy-terminal-contract 用户裁定）只约定动作输出（单一 `CwAction`），决策依据无输出位；遥测设施（kernel journal/对局档案）只覆盖 gs 状态面，策略私有状态面无采集规范。
- 解决到哪：
  1. DecisionRecord 数据规范（信封跨策略同构 + 载荷策略自治）；
  2. 基类自动捕获缝（结构上不可漏报，不靠实现自觉调用）；
  3. 独立存储（recorder 根 `strategy/` 目录 jsonl，与 kernel journal 分离）；
  4. dtag 回执关联锚（决策↔执行精确 join，不靠时间戳）；
  5. 渲染器按需装配（「策略依据」块；无数据 = 报告零变化）；
  6. mandate_v1 首个 payload（方向态/缺员/上阵窗口现值）。
- 明确不解决（防范围外溢）：cw4_counters 迁移收敛（另批）；per-strategy 专用渲染注册扩展（payload 通用渲染先行）；域内判据全量快照（商店会话内部量等，v1 只记出口后可现读面）；历史局回填（无历史数据，决策记录自本迭代起生效）。

## 2. 方案
- 系统级变化：策略器决策入口被基类自动包裹——包裹面 = **显式 14 入口名闭集**（非名称前缀规则），wrapper 填信封（含返回动作摘要）、调 `decision_payload()` 钩子收载荷、经装配槽 sink 追加落盘（run_id 与局外零写判断归 sink）；嵌套调用（子类经 `super()` 复用基类实现）由 in-flight 守卫归一为最外层一条记录；返回动作前在 kernel 决策上下文槽盖 dtag，动作回执行（`note_action_receipt` 唯一写点，`kernel/cw_game_state.py:1364`）带入 dtag；渲染器从批目录 `strategy/` 自动发现策略 jsonl，**两级挂载**——有回执形态按 dtag 精确 join 进动作节，pick 族等无回执形态（12 个选择族入口经上报函数族自报、不产回执，`kernel/cw_vocab.py:667`「op 内自上报」）按「入口→画面章键」映射表 + node 归章渲染「策略依据」小节。三处全降级：sink 未装配 = 零写；策略未覆写 payload 钩子 = `payload {}`；渲染无策略文件 = 报告与现状零差异（例外见 landing 3.4 书卡键集修复面）。
- **跨详设接口契约（总纲定死，详设不另设）**：
  1. **DecisionRecord 行格式**（capture-store ↔ render-assembly 唯一数据契约）：单行 JSON `{"envelope": …, "payload": …}`，jsonl 追加、行行自足。envelope 键闭集 = `{strategy_id, schema_version, dseq, dtag, entry, node, ts, emitted, run_id}`，其中 `dtag = "<strategy_id>:<dseq>"`（与回执 dtag 同值）；`entry` = 决策入口方法名（14 入口闭集，render-assembly §2 映射表的键）；`node = {plane, round_num, kind}`（gs.node 现读，键名与 journal `round_num` 对齐；缺 = null——null 帧不入章级挂载，计数并入局头策略遥测行「未归属 M 条」）；`emitted = [{op, reason, route_tag}]`（恰一动作；空动作 `CwActionObsParam` 同样成记录；非 CwAction 返回值照常成记录，归因键 getattr 缺省 `''`）；`run_id` 由 sink 落盘前补齐（wrapper 信封不含此键）；`payload` = 任意 JSON 对象（策略自治，缺 `{}`）。
  2. **存储与发现**：文件 = `<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`（追加；run_id 空 = 局外零写，判断在 sink）；渲染器缺省发现 = journal 同根 `strategy/` 目录全部 `*.jsonl`，`--strategy-telemetry` 可显式指定（文件或目录）。
  3. **join 语义（两级）**：①动作级——回执行 `dtag` → `envelope.dtag` 精确 join，依据块嵌入该动作节；②章级——无回执形态按 `entry` → 画面章键映射表（render-assembly §2）+ `node` 归章，依据块为章内「策略依据」小节。
- 详设划分：capture-store（落地阶段 3.1/3.2/3.3/3.5 的设计依据）+ render-assembly（阶段 3.4）。
