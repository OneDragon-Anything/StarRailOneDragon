# 采集与存储（详设）

## 问题与约束
- 总纲划给本篇的接口契约：DecisionRecord 行格式（envelope 键闭集 + payload 自治）与存储路径（`<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`，run_id 由 sink 落盘前补齐），见 design.md §2，本篇不复制。
- 契约面约束：CwStrategy 的决策入口是终态契约（`strategies/impl/cw_strategy.py:82-93`，2026-09-16 用户裁定「干净断不留壳」）——捕获不得要求实现改名或改签名；画面 op 只做观察 + 调一个决策入口、不加生产接线步（R191，`strategies/impl/mandate_v1/bridge.py:9-11` 注）。
- 纯逻辑纪律：策略本体不碰屏幕/控制器、可离线 unit 测（`cw_strategy.py:8-10`「本模块纯逻辑」）；decision 桶依赖矩阵只可依 data/kernel（`bridge.py:7-8`）——基类捕获缝不得引入策略包对 telemetry/app 层的 import（**含 run_id 供给**，见 §2 run_id 归 sink）。
- best-effort 纪律：记录层故障不毒化动作链（`kernel/cw_game_state.py:1438` 回执写入先例：`except → log.debug`）。
- 遥测装配槽先例：模块级槽 + 缺省关 + 装配点显式接通（`set_obs_reset_hook`，`cw_strategy.py:261`；`set_recorder_replay_dir`，`telemetry/state.py:60`）。

## 方案

### 1. 捕获缝 = 显式闭集包裹 + in-flight 守卫（纯新增，零改契约面）
- **包裹面 = 显式 14 入口名闭集常量**（不是 `decide_*` 名称前缀规则——前缀规则会把非决策入口卷入，如 `decide_shop_screen` 序列驱动器 `bridge.py:271` 返回 list、违背「恰一动作」信封语义）。闭集 = `cw_strategy.py` 抽象入口全集 14 个：`decide_prep_screen` / `decide_shop_action` / `decide_invest_strategy` / `decide_invest_env` / `decide_supply` / `decide_encounter` / `decide_megastar` / `decide_partner` / `decide_planner` / `decide_star_tome` / `decide_wish_trial` / `decide_box_card` / `decide_fortune` / `decide_expert_invite`（`cw_strategy.py:146-221` 实数 14 个；文件 docstring :14「15」与 :82「14」自相矛盾，3.1 顺带勘误该 docstring 计数）。
- 机制：`CwStrategy.__init_subclass__` 在子类类创建时，对闭集内且定义于本类的函数包记录 wrapper（wrapper 带标记 `_decision_recorded`，已标记不包）。基类 `@abstractmethod` 声明不包——包裹只发生在具体实现类。
- **嵌套归属规则（in-flight 守卫）**：子类经 `super()` 复用基类实现时（实证：`MandateV1Strategy.decide_shop_action` 末行 `super().decide_shop_action()`，`bridge.py:269`，基类实现在 flow 层同名且同被包），内层调用**直通不记录**——wrapper 入口检查实例旗 `_decision_in_flight`：已在飞 = 直接执行原方法；否则置旗 → 执行 → 记录 → 清旗（try/finally；决策循环单线程，无并发面）。
- wrapper 语义：`self._dseq_counter` 自增（构造清零）→ 调原方法 → 填信封 → 调 `self.decision_payload()` 收载荷 → sink 落盘（best-effort，异常 `log.debug` 吞掉，不影响返回值）→ 空动作（`CwActionObsParam`）返回前**清决策上下文槽**（发不出的动作后随无回执，防陈旧 dtag，见 §2）→ 原样返回。**决策入口抛异常的帧不落记录**（异常面已有各自留证通道，如 `cw_screen_prep.py:805-807`）。
- 调用点与实现零改动：画面 op 侧 `match.strategy.decide_X()`（`operations/cw_screen/cw_screen_prep.py:805`、`cw_screen_shop.py:602`、`cw_screen_supply_node.py:311` 等）照旧。

### 2. 信封字段供给与 dtag 关联锚
- `strategy_id` = `self.STRATEGY_ID`（`cw_strategy.py:96`）；`entry` = 被包裹方法名（14 闭集）；`node` = gs.node 现读（plane/round_num/kind 三键，键名与 journal `round_num` 对齐；缺 = null）；`ts` = 写入时刻 ISO8601。
- `emitted` = 返回动作摘要，固定三键 `{op, reason, route_tag}`：op = 类型名；reason/route_tag = 动作自带归因字段（`kernel/cw_vocab.py:158-159` 等，逐类声明），**取值一律 `getattr(x, key, '')` 容缺**——非 CwAction 返回值（如备战拦截帧，`mandate.py:223` 四硬约束检查点）与 `__new__` 桩无属性形态（`prep_actions.py:272` 同款惯例）都不抛、不丢记录。空动作 `CwActionObsParam` 同样成记录（其 scope 语义由 journal 既有行承载，不入信封）。
- **run_id 归 sink**：wrapper 信封不含 run_id（策略包禁 import telemetry，见问题与约束）；sink 落盘前读 `telemetry.state.current_run_id()` 补齐，并做局外零写判断（§4）。
- **dtag 进回执 = kernel 决策上下文槽**（新 `kernel/cw_decision_ctx.py`，~30 行）：
  - `set_decision_tag(dtag: str | None)` / `take_decision_tag() -> str | None`（读后清）/ `reset_decision_tag()`（测试与装配复位口——槽是模块级单例态，跨测试残留会污染回执断言，sr-od-test conftest 复位面随 3.2 登记）；
  - wrapper 在返回非空动作前 `set_decision_tag(dtag)`；空动作返回前清槽（§1——空动作不产回执，陈旧 dtag 无主）；
  - `note_action_receipt`（`kernel/cw_game_state.py:1364`，receipts 域唯一写点）写行时 `take_decision_tag()`，非 None 并入 `receipt['dtag']`——四调用点（prep 统一口 `prep_actions.py:367` / close_shop `cw_close_shop_action.py:51` / open_shop `cw_op_open_shop.py:43` / shop 落地门 `cw_screen_shop.py:287`）零改动；
  - **适用域申报（本设计最重要的一条边界）**：全仓仅上述 4 处产回执。12 个选择族入口（supply/encounter/invest×2/megastar/partner/planner/star_tome/wish_trial/box_card/fortune/expert_invite）的动作执行走上报函数族自报（`kernel/cw_vocab.py:667`「op 内自上报」），**从不产回执**——它们的 join 走 render-assembly §2 章级挂载（entry→章键表），不走 dtag。
  - 陈旧槽残余面推演（设计声明，攻击复核项）：槽只被「下一次非空动作 decide」覆盖或「回执读取」清空；空动作路径主动清；pick 族 decide 置槽后无回执读取，但 pick 族也不产回执——**不存在「陈旧 dtag 搭上无关节」的生产路径**；渲染侧另有指纹一致性校验兜底（render-assembly §3）。
  - 依赖方向合规：slot 模块在 kernel，strategies → kernel 单向 import。
- `bridge.py:366` `decide_prep_frame` 的非生产驱动器 `decide_shop_screen`（回放/序列测试路径）不在包裹闭集——但其内层 `self.decide_shop_action()`（`bridge.py:328`）**在闭集内被包裹**：装 sink 即逐动作产记录；这些 dtag 无回执消费（驱动器不经 `note_action_receipt`，走上报函数族直推，`bridge.py:344-355`），渲染侧按未落地注记处理（render-assembly §3 适用集钉死：行 2 记录只走动作级 join）。缺省 sink 未装配 = 零写，序列测试零副作用不变。

### 3. payload 钩子
- 基类 `decision_payload(self) -> dict`（缺省 `{}`），子类覆写；wrapper 在原方法返回后调用，异常 → `{}` 降级。
- **mandate_v1 v1 覆写**（全部 gs + state 现读，不依赖 entry 内部局部量）：
  - `direction: {locked, comp, candidates}` —— `session_scope.direction_comp_of(gs)`（12 号稿 §2 方向读口）与 `state.line_candidates`（`mandate_state.py:341`；锁定后恒空集，`session_scope.py:330`）；
  - `k_members: [str]`、`k_fallback: {hit: bool, band: str}` —— **按 `entry.py:459-472` 同源算法**：`predicates.line_members(direction_comp_of(gs))`，为空且 `v3_intention` 在场时走 `cw_intention.k_empty_window_fallback` 回退腿；payload 记回退腿是否命中与带名（band），防回退帧的依据块被误读为锁定线成员（候选 A 复核判读面）；
  - `window: {char: {open, sig}}` —— 对 k_members 与板面上出现的终局库成员逐个：`entry._entry_window_open(gs, char)`（`entry.py:281`）给结论 + `Comp.entry_signals.get(char)` 给信号描述 `[kind, threshold]`；终局库成员集 = `_ENDGAME_LIBRARY_MEMBERS`（`entry.py:275`）。
  - 依据：候选 A（上阵窗口自锁）的复核需要「决策帧上窗口判据的输入与结论现值」，`_entry_window_open` 是唯一判定核（22 号篇 第 6 步判据载体），现状无任何落点。
- 更细域内量（商店会话内部等）：策略后续经私有 state 槽自存、钩子里读（`cw4_frame_action_record` 先例，`bridge.py:338`），本迭代不预建。

### 4. sink 装配槽与落盘
- **槽位与写盘分离，保持策略包零 I/O**：
  - 槽：`cw_strategy.py` 模块级 `_DECISION_SINK: Callable[[dict], None] | None = None` + `set_decision_sink(fn)`（`set_obs_reset_hook` 同款）；
  - 写盘实现：telemetry 包新模块 `telemetry/strategy_telemetry.py` 提供 `strategy_telemetry_sink(record: dict) -> None`——补 `run_id`（`telemetry/state.py` current_run_id）→ run_id 空 = 丢弃（局外零写，回执域同语义 `cw_game_state.py:1420-1422`）→ append 单行 JSON 到 `<get_recorder().replay_dir>/strategy/<strategy_id>_<run_id>.jsonl`；目录自建；**逐行写后即 flush**（决策频度低、行小，无性能面；防进程异常丢尾部记录——journal `flush_pending` 漏行先例，`telemetry/state.py:210-214`）；**句柄缓存键 = (recorder 根, strategy_id, run_id)**（根变更 = 重定向，缓存自然失效，`telemetry/state.py:60` 换根重建单例语义对齐）；
  - 装配点：生产 = `decision_assembly.py`（与 `install_obs_ports` 同位，app 层）；sim = `cw_sim_match_drive.py` 装配段（recorder 重定向同段，根已重定向故落点自动随根）。缺省 None = 零写——纯单测零副作用，conftest 无需清理。
- 多局/多策略：实例不跨局（`cw_strategy.py:80`）→ dseq 天然按局清零；strategy_id/run_id 分文件。

### 5. 失败隔离与测试锁面
- wrapper/sink 全 best-effort（遥测异常不毒化决策与执行）。
- 测试锁面（sr-od-test）：信封键闭集与 dtag 格式 / 显式闭集包裹面（`decide_shop_screen` 不被包）/ in-flight 守卫（super() 链恰一条记录）/ 局外零写 / payload 钩子异常降级 / `note_action_receipt` dtag 并入与 take 清槽 / 空动作清槽 / sink 异常不影响 decide 返回值。

## 关键取舍
- **模板方法改名**（基类 `decide_*` → 内部钩子 + 基类公有壳）：动 14 入口契约面，撞终态契约用户裁定，弃。
- **op 调用点包裹**：每屏一处生产接线步，违 R191，弃。
- **名称前缀包裹**（`decide_*` 通配）：会把 `decide_shop_screen` 驱动器（list 返回）卷入信封「恰一动作」语义，且无法从名字区分生产/非生产面，弃——显式闭集。
- **dseq 走 CwAction 字段**：`route_tag` 已从基类摊平为逐动作类重声明（`cw_vocab.py:146`「原 CwAction 基类唯一字段，摊平后逐动作类重声明」，45+ 类），逐类加字段 = 大面积契约噪声，弃——kernel 决策上下文槽（run_id provider 注入同款极简面）。
- **记录进 journal 加 row 类型**：journal 是 gs 契约面（gs_schema 登记/投影审计/水位线机制），异构策略载荷污染单一源，且策略侧异常波及 kernel 写径，弃——独立文件使「按需加载」天然成立。
- **时间戳 join**：同秒多动作漂移（`decision_frame_hooks.py:10-11` ts 秒级对齐教训自证），弃——dtag 精确 join。
- **payload 在 entry 内部采集**：每域入口插桩 = 漏报面回归自觉制，弃——出口后 gs/state 现读面零侵入；更细量后续走 state 槽自存。
- **wrapper 填 run_id**：需要策略包 import telemetry，违纯逻辑依赖矩阵（N3 攻击成立），弃——run_id 归 sink（telemetry 层天然持有）。
