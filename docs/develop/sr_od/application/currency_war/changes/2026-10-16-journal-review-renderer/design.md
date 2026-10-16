# journal-review-renderer 迭代设计（总纲）

## 0. 元信息
- 迭代目标：复盘报告模板重构 + 渲染器重写到 journal 行模型（用户裁定 2026-10-16 会话，四点：①报告结构 = 局头/开局/节点×画面×动作，其余章节全删；②凡定义的画面 op 一律单独成章，章内「0 观察 → 动作节×N → 策略评价」；③不处理策略侧保存的内容；④不兼容旧档案，旧渲染器不保留，后续重跑新遥测）。
- 状态：定稿（首轮三核对抗收敛 31 项 + 终审通过，一行级残留已同笔修订；2026-10-16）
- 文档清单：
  - [details/pipeline.md](details/pipeline.md) —— journal 解析与画面/动作重建管线（渲染中间表示定义）
  - [details/render-spec.md](details/render-spec.md) —— 逐画面/逐动作显示规范（消费中间表示）
- 对抗报告：[attack.md](attack.md)（首轮三核，31 项发现全部处置，处置状态逐条在案）

## 1. 问题与动机
- 现状症状：
  - `tools/cw/replay_to_md.py` 对 2026-09-13 之后的对局整条断供：旧遥测流（decisions/outcomes/exogenous/invest_cards/shop_snapshots/spend_ledger/cw4_counters）最后写入 2026-09-11（实测 `.debug/currency_war/telemetry/live/*.jsonl` mtime）；此后生产的档案切片仅剩 `state/journal.jsonl` 一个键（实测 `match_g_20260923_172823.json`，slices 单键 629 行，rounds 为空数组）；渲染器动作词表仍是旧长格式（实测 live decisions.jsonl 零条 `CwActionBuyCardParam`，回执为短动词 `BuyCard`）。
  - 报告结构与用户裁定不符：现渲染器模板的章节层级需重排为节点×画面×动作，且用户裁定删除局况速览等分析章节。
- 根因归层（两层）：
  - **断供机制 = 表示层**：遥测数据模型换代（多流模型 → journal 单流统一账），渲染器作为消费方未跟随迁移。权威自述：journal_query.py「journal 为唯一被读账本；旧 12 流视图族已随写入端停用，拆除」（`src/sr_od/application/currency_war/telemetry/journal_query.py:8-10`）。
  - **复发根因 = 流程层**：消费方迁移清单早登记了本消费面（`game_state/retirement.md` §7 #3，状态「待」），但停用前置条件的保护面（决策源/sim/判读三面，retirement.md §6 批次顺序门）未覆盖它，写面删除批在登记「待」时即执行；叠加渲染器零契约测试（sr-od-test 无 tools 测试），断供静默约五周才被发现。同型断供已 ≥3 次（2026-09-12 W4 流删除断链、2026-09-15 op_journal 停写迫使协议改道日志行、本次）。
- **血统**：本迭代 = retirement.md §7 #3「回放/修复工具改读新档案面」消费面切换的落地批，收尾时对该行清账（见 landing 正本更新清单）。
- 解决到哪：`tools/cw/replay_to_md.py` 就地重写为 journal 版（新结构输出，fixture 单测护住断供静默）；`tools/cw/review_skeleton.py` 删除（数据源 decisions.jsonl 与模板均属旧形态）；skill references 产出结构描述协同更新；retirement.md §7 #3 清账。
- **明确不解决**：策略侧会话态（v2/v3 意向、锁线 pair、dp_posture、cw4_counters 行为计数）不渲染（裁定③）；旧档案兼容（裁定④）；retirement §7 其余消费面行不属本迭代；复盘方法论本体（判定尺/裁决口径）不改——只改产出结构描述。协议四产出（候选清单/回灌读数/位面三问/完整性审计）落点 = **报告文末「复盘者附加」空节**（用户裁定 2026-10-16：渲染器只给标题不预填，复盘者义务产物填入该节）。

## 1.5 裁定解释与偏差申报（对四点裁定的字面执行口径）

1. 裁定②「凡定义的画面 op 一律单独成章」按字面执行：全部注册画面 op（含弹层与交互辅助 op）凡有 journal 行即成章；零写入行的 op 自然不出现（数据不存在，非设计排除）。原设计「弹窗族不成章并尾注」的收窄条款废除。
2. 裁定①的章节枚举无「收尾」：不设收尾章；终局事实由局头承载（match_final）；对局收口画面若有 journal 行，作为非决策面画面章自然出现（同裁定②口径）。
3. 裁定③字面覆盖 cw4_counters（策略行为键，retirement.md §3 定谳其承载策略行为）：不渲染。

## 2. 方案
- 系统级变化：
  1. **渲染器重写**（details/pipeline.md）：输入 = journal 行列表（宽容读取复用 `journal_query.read_journal_stats` 单一源）；按「每行自带 state.values 快照（写入至今累计子集）」做节点归属（零重建），按画面证据切画面章（快照变化 + actor 映射双轨），按回执行切动作节（same_value 过滤），动作锚间差分出状态变化；产出渲染中间表示（字段闭集）。
  2. **显示规范**（details/render-spec.md）：局头逐行键值；开局章（简报/投资环境等）；节点章（`节点 P-R 类型`，类型取组内首行 node.kind 中文映射）→ 画面章（`节点 P-R 类型 画面-备战` 式标题）→ `0 观察` 节 + 动作节×N + `策略评价` 节；不设收尾章；文末「复盘者附加」固定空节（协议四产出落点，见 §1）。速览/候选/回灌/审计/自检/计数器全部不输出。
  3. **review_skeleton.py 删除**：sim 局复盘改用新渲染器 `--journal <sim批>/state/journal.jsonl`（实测 sim 批目录有该文件）。
  4. **skill references 协同**：match-review.md 产出形态节、sim-testing.md 骨架生成器行、telemetry-reading.md 旧流引用清查（补报理由：该文件是复盘工具面操作手册，引用旧流/旧工具的行不更新会把复盘点误导到死流，属本迭代行为的直接文档后果）。
- 详设划分与跨详设接口契约：
  - pipeline.md 定义**渲染中间表示**（§6，含 Report.meta 键名闭集）；render-spec.md 按该结构定义显示形态（不得引用中间表示之外的 journal 行内字段，meta 键集除外——键名闭集在 pipeline §6）；两详设唯一共享面 = 中间表示字段清单，禁各自演化。
  - 实施顺序：pipeline 先行（含单测），render-spec 的画面注册表/字段中文映射随之落地于同一渲染器内。
- CLI 契约：`--match <game_id>` 只读档案（档案缺失报错退出码 2，**不回退 live journal**——live 为多局混合流，无档案元数据无法界定行域）；`--journal <path>` 裸 journal 文件（sim 批、live 未装配局、自定义路径，配 `--game-id` 命名）；`--run <run_id>`（未知值报错退出码 2——与旧渲染器「未知 run 全渲染+警告」的语义差异显式申报）；`--out` / `--stdout`；旧 `--replay-dir` 不再保留（自定义根改用 `--journal`）。缺省输出落点保持 `.debug/currency_war/deep_review/<game_id>.md`（2026-09-07 布局裁定，match-review.md 引用中）。
