# 渲染管线（详设）

## 问题与约束

- 输入 = journal JSONL，两行型：`row='write'`（字段写入行）/ `row='obs_event'`（观察事件行）。行模型权威 = `docs/develop/sr_od/application/currency_war/game_state/journal.md` §1 与 `src/sr_od/application/currency_war/telemetry/journal_query.py:12-17`。
- 宽容读取契约：坏行/半行/非对象行逐行跳过 + 计数留痕，禁炸（`journal_query.py:19-35`）；读入口单一源 = `read_journal_stats`。
- 行自带快照 `state.values` = **写入至今的累计子集**（实测不同键上界 46 个，单行 1-38 键宽窄不一，非全量快照；Field 声明全集 85 个见 `cw_game_state.py:2209-2636`，仅作语义注释来源）。节点归属功能只依赖 `node`/`current_screen` 两键在写时刻在场，实测成立。
- 术语（首现定义）：**观察道/效果钩子/动作道** = journal 写入三渠道封闭集（权威 = journal.md §2「三渠道封闭集与渠道签名」）：`sig.family='obs'` = 观察道（画面读数写入）；`'logic_action'` = 动作道（动作执行及其回执）；`'logic_hook'` = 效果钩子（效果桥回写，`cw_game_state.py:1373-1378`）。**仲裁行** = `row='obs_event'` 行（识别回读与账面不一致的裁决记录，实测 verdict 为自由文本，如「采新-对账纠漂(SIFT 实读)」）。
- `--run` 过滤：按行 `run_id` 精确匹配；`--run` 值不在数据出现过的 run 集合内 → 报错退出码 2（与旧渲染器「未知 run 全渲染+警告」不同，语义变更已申报 design §2）；空 run_id 行仅在 ts 落于切片首末行时间窗内时放行——**窗取切片行首末行 ts，不取档案 start_ts/end_ts 元数据**（实测 9/23 档案 end_ts==start_ts，多数行越窗，元数据不可信）。

## 方案

### §1 行加载与排序

1. `read_journal_stats` → (rows, stats)；`--match` 读档案切片 `slices['state/journal.jsonl']`，切片缺 → 报错退出码 2（不做 live 回退，理由见 design §2 CLI 契约）；`--journal` 直读文件。
2. `--run` 过滤（语义见问题与约束）；过滤后按 `ts` 升序稳定排序（同 ts 保持行序）。
3. `stats`（坏行计数）进局头「数据完整性」行（render-spec §2）。

### §2 节点分组

- 每行节点键 = `state.values.node`（`{plane, round_num, kind}`，NodeKey 结构 `cw_game_state.py:690-697`）。
- 节点显示名：`节点 <plane>-<round_num> <类型中文>`；类型取**组内首行**的 `node.kind`（组内 kind 会翻转——实测备战→战斗窗过渡处 reward→battle，钉死取首行）；中文映射（词表来源 = NodeKey.kind 注释 `cw_game_state.py:697`，实测值 live+sim 合并覆盖）：`reward→奖励`、`battle→战斗`、`encounter→遭遇`、`supply→补给`、`boss→BOSS`、`prep→备战`；未知值原样显示。
- 节点章按 (plane, round_num) 升序。

### §3 无 node 行归属链（优先级从上到下）

1. 行在**首个节点组首行之前** → 参与开局段（按 §4 画面切分归入开局画面章）；
2. 其后、且带画面证据（注册 actor 或 current_screen 在场）→ 落「未归节」虚拟组：标题 `未归节`，组内照常按 §4 画面切分 + §5 动作切分渲染；
3. 无 node 且无画面证据（未注册 actor 且无 current_screen）→ `annex_unattached`（文末「未归行」清单，防静默丢行，判据同旧渲染器 `_mk_unattached` `replay_to_md.py:792-803`）。

### §4 画面章切分（节点组内）

- **快照画面章**：组内首行恒开启一个画面章（基线 = 组边界，解决跨组同值是否开章的歧义）；此后 `state.values.current_screen` 值相对**当前章 screen id** 变化 = 画面切换锚，开启新章（弹层章结束后回到底层画面的行：值与底层快照章 id 相同 → 续开该快照章；新值 → 开新快照章）。
- **弹层行归属只认 actor 映射**：实测弹层动作的回执 `screen` 字段恒为底层画面（备战/商店，524 条全量零弹层值）、弹层 actor 的 `sig.screen` 恒空——回执 screen 与 sig.screen **不参与切分**，仅作章内动作锚定注记。行 `sig.actor` 命中画面注册表（render-spec §3，actor 全名 → 画面 id）→ 该行归入对应弹层画面章（在该行处开新章，章持续到下一画面证据出现）。
- **未注册 screen id**（实测 sim 侧 `货币战争-BOSS简报/补给/遭遇节点`）：按原样 id 开章、0 观察键集空、非决策面，并记缺口。
- **未注册 actor**：不切分，挂当前画面章尾注 + 记缺口（缺口可见性 = 对「断供静默」病根的正面设计目标：新画面未注册时报告内可见，而非整章静默消失）。

### §5 动作节切分与状态差分

- **动作锚** = `field='receipts'` 且 `same_value≠true` 的 write 行（实测 524 条 receipts 行中 183 条为 no-op 整窗重写，必须排除）。回执域是滚动窗整窗替换写（写端 `(list(old)+[receipt])[-8:]`，`note_action_receipt` `cw_game_state.py:1341-1366`）→ 每条锚行的最新动作 = `after[-1]`。
- 一条回执 = 一个动作节；**重试链合并**：连续回执同 `op` 且前条 `applied=false` → 合并一节，节内逐条列出（实测样例：StartBattle 重发链）。
- **状态变化行归属 = 写入行自身所在画面章**（跨章不串挂）；章内差分区间 = 动作锚 i 之后至下一动作锚 i+1（或章末）：
  - 区间内 write 行（`field≠'receipts'`、`same_value≠true`）逐行记 `(field, 前值, 后值=after, sig.family, sig.actor)`，挂动作节 i 的状态变化表；
  - 章内首个动作锚之前的 write 行 → 章「章内变化」块（渲染为章尾无锚变化表，典型 = 战斗章的 settlement 写入）；
  - 前值 = 该 field 在本变化行之前最近一条写入行的 `after`；无 → 本变化行快照 `state.values[field]`；再无 → `(起点)`；
  - `sig.family='logic_hook'` 行说明列标「(效果钩子)」；`sig.family='obs'` 行不入状态变化（观察道写入是读数不是动作效果），进 0 观察或画面章尾注。
- receipts 窗口行自身不进状态变化表。
- 回执动词开放演化申报：发射点以 `op=type(action).__name__` 透传（`cw_screen_shop.py:288`），词表是开放集——映射表（render-spec §4.1）未命中时原样显示动词，禁猜。

### §6 渲染中间表示（跨详设接口契约，字段闭集）

```
Report
├─ meta: [(键, 值)]            # 键名闭集：game_id / runs(段 run_id 列表) / code_commit /
│                              #   registry_fingerprint / start_ts / end_ts / final_type /
│                              #   final_plane / final_round / final_hp / final_gold /
│                              #   final_duration_s / continuity_note
│                              #   （值来源：game_id=CLI；code_commit 等终局键=match_final 写入行；
│                              #    runs=行内 run_id 去重或档案 segments；时间=切片首末行 ts；
│                              #    continuity_note=档案元数据（--journal 无档案时省略该行））
├─ stats: {bad_json, non_dict, byte_repair}
├─ sections: [Section]         # 按序：开局组 → 节点组×N → 未归节组(有则)
Section =
  ├─ kind: 'open' | 'node' | 'unattached'
  ├─ node: {plane, round, kind_cn} | None      # kind='node' 时必有
  └─ screens: [Screen]
Screen =
  ├─ screen_id: str                            # 画面注册表键或原样 id
  ├─ title: str
  ├─ entry: [(键, 值)]                         # 0 观察 = 章首行快照（进入时态）
  ├─ entry_tables: [(表标题, 表头, 行)]         # 商品牌面/补给选项等表格
  ├─ actions: [Action]
  ├─ trailing_changes: [(field, 前值, 后值, 说明, is_hook)]   # 章内变化块（无锚前缀写入行）
  ├─ annots: [str]                             # 尾注（仲裁/观察更新/未注册 actor 缺口）
  └─ has_decision: bool                        # False = 不渲染策略评价节
Action =
  ├─ no: int                                   # 章内序号，1 基
  ├─ op: str
  ├─ title: str                                # render-spec §4 组装规则
  ├─ receipt: {applied, reason, detail, extra}
  └─ deltas: [(field, 前值, 后值, 说明, is_hook)]
Report.annex_unattached: [str]
```

- 该结构为 pipeline↔render-spec 唯一共享面；render-spec 除 meta 键集（键名闭集在上）外不得引用 journal 行内字段。

### §7 CLI 与输出

- 参数语义见 design §2 CLI 契约；零渲染内容（journal 空/全过滤）→ 输出仅局头 + 「无渲染行」说明，退出码 0；档案/journal 不存在、`--run` 未知 → 退出码 2。
- 验收选局注意：9/23 两个 live run 无战斗窗行（战斗章验收选 9/18 及更早 run，如 run_20260918_012509）；node.kind 六值词表的实测面 = live（reward/battle）+ sim（supply/encounter/boss 等仅 sim 有）。

## 关键取舍

- **复用 src `journal_query` vs 零 src 导入**（旧设计理由 = 免 PYTHONPATH 直跑，`replay_to_md.py:61-63`）：选复用。宽容读取契约与行模型单一源在 journal_query（模块头自述「唯一判读读面」），第二实现必漂移；代价 = 运行需 `PYTHONPATH=src`（项目标准运行方式，AGENTS.md §1.2）。import src 先例 = `tools/cw/repair_invest_attribution.py:67-72`（import telemetry.match_archive，同为遥测消费方）。
- **节点归属用行内快照 vs 旧两遍式重建**：行行自足快照使重建不需要（journal.md §1 行模型）；旧重建算法全部服务于旧流无快照形态，不迁移。
- **就地重写同名文件 vs 新文件**：CLI 习惯面保持，调用方零迁移；旧实现无一分支可复用（全部建立在旧流行上）。
- **fixture 单测为硬判据的动机**：旧渲染器零测试是断供静默五周的伴生根（attack.md D1）——数据源再次换代时，测试红是唯一自动报警面。
- **缺口可见性为设计目标**：未注册 actor/screen id 显影为章尾缺口注记而非静默吞行——流程层病根（换代断供不可见）在消费侧的对抗手段。
