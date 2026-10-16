# sim-screen-announce 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/tools sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 sim 广播 + 渲染器切章收窄与注册表扩容

**范围**：①`sim/cw_sim_backend.py` 新增 `_announce_screen`（值级豁免 SETTLE/LOBBY，design §2.1）并接 10 处广播点；②`tools/cw/replay_to_md.py` 切章证据收窄（§2.2.1）+ SCREEN_REGISTRY 扩 11 键（§2.2.2）+ 相邻合并键 title 与注册纪律（§2.2.3）+ _opening_note 空值跳过（§2.2.4）；③两侧 fixture 单测。边界：不动实机链路（obs/漏斗零改动）、不动 sim 状态机本体、不改 references。
**设计依据**：design.md §2.1-§2.3 全篇。
**文件面**：`src/sr_od/application/currency_war/sim/cw_sim_backend.py`；`tools/cw/replay_to_md.py`；`src/sr_od/application/currency_war/kernel/cw_projection_audit.py`（:413 current_screen 行 basis 改「实机 = observe_screen_context；sim = _announce_screen(evidence screen: 前缀)」——广播落地即成第二写点，静态申报须同步）；`sr-od-test/test/tools/test_replay_render.py`；`sr-od-test/test/sr_od/application/currency_war/sim/test_sim_backend.py`（sim 测试落位现成宿主）。
**依赖**：无。
**优先级建议**：0
**完成判据**：
- **存量回归（先建基线再改的显式步骤）**：改动前先渲染并存基线——sim 存量 `--journal .debug/currency_war/telemetry/sim/sim_match_20261016_082523/state/journal.jsonl` 与 live 存量 `--journal .debug/currency_war/telemetry/live/state/journal.jsonl --run run_20260918_012509` 各留基线文件；改动后同参重渲，**验收口径（T-1 验收裁决）= sim 存量逐档案 diff = 0；live 存量 diff 仅限四类正向/已知效果**（①空值噪声注记删除 ②战斗节点尾陈值备战幽灵章摘除 ③瞬态帧幽灵战斗章摘除 ④策略窗末动作归属位移——cw_game_state.py:3294 已登记回写病理的如实显影，非本迭代引入）；实测 = sim 0 diff、live 27 档案 9 零 diff/18 全为上述四类；
- sim fixture（raw sink 路标：现成 capture_state_journal 是投影捕获无 sig/快照，断言广播行 family=obs 须 `set_state_journal_sink(rows.append)` 直挂，**并配 `set_run_id_provider`（照 harness capture_state_journal:263-264 双装，缺一则局外拒写门静默吞全部行）**）：广播行 prev_screen/current_screen 对 family=obs 入账；**12 处赋值点中 10 处广播、SETTLE/LOBBY 值不广播（值级豁免逐值断言）**；
- 渲染器 fixture：cs 广播行开正式画面章（备战/商店/11 overlay 全注册形态，无缺口注记）；**切章证据收窄——携带陈值 cs 的非广播行不切章（幽灵章回归用例）**；overlay actor 行 + cs 广播行相邻合并单章；同值广播行不重开章；**存量四测适配（收窄后快照 `screen=` 不再开章）**：test_screen_split / test_placeholder / test_empty_action_screen / test_shop_entry_table 的开章行改为 `field='current_screen'` 广播行形态（mkrow(field='current_screen', after=画面名)），断言保持；test_screen_split 未注册样本由 货币战争-BOSS简报（注册表扩容后变注册键，原断言必红）换为 货币战争-大厅 或 货币战争-结算（保住未注册兜底覆盖，勿顺势改断言）；
- **并行批警示**：cw_sim_backend.py 工作区或有他批在飞改动（终审时点 T-23 约 473-529 区间 +4 行未提交）——提交该文件须逐 hunk 核对 diff，他批 hunk 混入即剥离或延后提交并在报告申报；
- 完成前常规检查（本文首节）。
**验收凭据形式**：单测名清单 + 双存量零 diff 记录（基线文件路径 + diff 输出）+ 新 fixture 断言。

## 3.2 正本更新

**范围**：①源迭代 render-spec §3 快照章注册表补 11 行（新键 → 章名/决策面/键集，标注「sim 广播值」）+ 注册纪律行「同 title 必须同规格」+「sim 侧未注册 id」兜底行样本改通称（原三值样本已随扩容变注册键）；②源迭代 pipeline §4 补「sim 广播形态：current_screen 值来自引擎声明（evidence 前缀 screen:、mode=synthesized），切章规则同形；切章证据 = field='current_screen' 写入行本体」句 + **T-1 提请①**「组首行（cur=None）非广播 cs 行按行内快照值开基线章」语义句（实现口径 = pipeline §4 组首行恒开章 + §2.3 占位清零收口）；③`sim/sim-wiring.md:57` 流程面域行修正（原申报机制 update_screen_after_operation = 框架路由簿记非容器写入；现行为 = _announce_screen 容器广播）+ **T-1 提请②** `cw_projection_audit.py:413` basis 同步（实机 = observe_screen_context；sim = _announce_screen）；④本迭代 README 进度收尾。**跨迭代申报**：①②落在 journal-review-renderer 迭代的 details/ 工件，其寿命受该迭代清理约束——修订段落写「以代码为准」口径（渲染器 SCREEN_REGISTRY/切章实现为最终事实），防清理后失锚。
**设计依据**：design.md §2.2/§2.3；attack.md R2/R3/Q1。
**文件面**：`changes/2026-10-16-journal-review-renderer/details/render-spec.md`；`changes/2026-10-16-journal-review-renderer/details/pipeline.md`；`docs/develop/sr_od/application/currency_war/sim/sim-wiring.md`；本迭代 README。
**依赖**：3.1。
**优先级建议**：0
**完成判据**：注册表 11 行与渲染器实现一致（逐行对照）；render-spec/pipeline 修订段与实现行为一致；sim-wiring.md:57 与实况一致；README 进度终态。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `changes/2026-10-16-journal-review-renderer/details/render-spec.md` §3 快照章注册表 11 行 + 注册纪律行 ← 3.2
- `changes/2026-10-16-journal-review-renderer/details/pipeline.md` §4 sim 广播形态 + 切章证据收窄句 ← 3.2
- `docs/develop/sr_od/application/currency_war/sim/sim-wiring.md` :57 流程面域行（兑现既有申报的机制更正）← 3.2
- （渲染器 SCREEN_REGISTRY 本体 = 代码即正本，docstring as-built 随 3.1）
