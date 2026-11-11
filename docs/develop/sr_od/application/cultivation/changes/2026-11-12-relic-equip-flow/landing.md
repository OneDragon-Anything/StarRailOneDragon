# 遗器装备流程改造 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

### 3.1 S1 画面建档与 fixture

**范围**：按 design.md §2.4 清单建档（MCP `upsert_screen_area`/`create_screen` 落 yml+合并缓存）；「按钮-遗器建议排序」改纯坐标区「按钮-排序设置」并修复消费点 `equip_relic.py`；两篇画面 doc 增补 + 两篇新建（筛选面板/筛选规则弹窗）。边界：不含任何 op 实现。
**设计依据**：design.md §2.1（F1-F19 事实与帧）、§2.4。
**文件面**：`assets/game_data/screen_info/`（经 MCP 工具）、`src/sr_od/application/cultivation/relic/operations/equip_relic.py`（仅 area 名消费点）、`docs/game/screens/遗器-替换.md`、`docs/game/screens/遗器-排序规则.md`、`docs/game/screens/遗器-替换-筛选.md`(新)、`docs/game/screens/遗器-替换-筛选规则.md`(新)；测试仓 `screens/遗器-替换/`（14 帧已归档）。
**依赖**：无
**优先级建议**：0
**完成判据**：
- MCP `analyze_screen` 对「遗器-替换-筛选」「遗器-替换-筛选规则」精准命中（拿对应帧离线验证 + 实机开面板复核一次）；
- `equip_relic.py` 排序前置链的排序弹窗打开动作改为纯坐标 area 后，既有流程测试全绿；
- 完成前常规检查（本文首节）。
**验收凭据形式**：画面对照（离线帧 analyze 命中）+ 既有测试全绿。

### 3.2 S2 词条解析层下沉与词缀读取器

**范围**：`src/sr_od/mys/sr_relic_stats.py`(新) 承接三表+解析函数（design.md §2.2）；`relic_eval_tools.py` 删本地副本改 import，测试 import 随迁；`relic_detail_reader.py`(新) 按 design.md §2.3 实现读区结构化解析（F17/F18 形态：次数缺失按 0 计带 `times_confirmed`、平坦/% 消歧、未识别词标记）+ 解析单测。边界：不含任何 op 实现；不改 `mys_evaluate_relic_substats` 出参语义。
**设计依据**：design.md §2.2、§2.3（relic_detail_reader 段）、§2.6（下沉取舍）。
**文件面**：`src/sr_od/mys/sr_relic_stats.py`(新)、`src/sr_od/backend/mcp/relic_eval_tools.py`、`src/sr_od/application/cultivation/relic/relic_detail_reader.py`(新)；测试仓对应镜像文件 + fixture（词缀详情帧）。
**依赖**：无（与 S1 并行）
**优先级建议**：1
**完成判据**：
- `mys_evaluate_relic_substats` 既有测试全绿（行为不变的回归锁）；
- `relic_detail_reader` 对「候选详情词缀.webp」帧解析出与实机 OCR 一致的 1 主 + 4 副结构（次数缺失容错生效）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名（解析单测 + 评估工具回归）。

### 3.3 S3 筛选 op

**范围**：`FilterRelicReplaceOp`（design.md §2.3 参数/入口/两条链/验证锚）+ fixture_controller 流程测试（set_name 链与 sort_stat 链两条剧本；幂等空跑剧本）。边界：不做清除筛选/清除排序；多属性排序不支持（单 `sort_stat`）。
**设计依据**：design.md §2.1 F1-F16、§2.3 FilterRelicReplaceOp 段。
**文件面**：`src/sr_od/application/cultivation/relic/operations/filter_relic_replace.py`(新)；测试仓镜像测试文件。
**依赖**：S1
**优先级建议**：2
**完成判据**：
- 流程测试三剧本（套装筛选/属性排序/幂等）全绿，节点点击与转移断言对照 F1-F16；
- 实机单跑一次 `set_name` 链 + `sort_stat` 链成功（MCP run_operation，跑完游戏停在正确筛选列表）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名 + 实机 run 运行记录。

### 3.4 S4 候选扫描 op

**范围**：`ScanRelicCandidatesOp`（design.md §2.3：单屏语义/静态排序前置检查/逐卡点选读词缀/详情 OCR 件名优先/bottom_reached）+ 流程测试。边界：不翻页不滚顶（调用方职责）；不做预标注。
**设计依据**：design.md §2.1 F17-F19、§2.3 ScanRelicCandidatesOp 段。
**文件面**：`src/sr_od/application/cultivation/relic/operations/scan_relic_candidates.py`(新)；测试仓镜像测试文件。
**依赖**：S2（relic_detail_reader）
**优先级建议**：2
**完成判据**：
- 流程测试全绿：含「建议排序开着 → 显式失败」「正常单屏扫描 → JSON 档案与 bottom_reached 断言」「masked 卡以详情 OCR 件名入档」；
- 实机单跑一次：对当前列表产出候选 JSON，抽 2 件与画面 doc 词缀人工对照一致；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名 + 实机 JSON 抽查对照。

### 3.5 S5 EquipRelicOp 词缀约束扩展

**范围**：`EquipRelicOp` 新增 `substat_criteria` 参数与 `verify_selected` 约束判定（design.md §2.3）；None 路径行为不变回归。边界：不改候选定位/抢件/排序前置逻辑；数值型约束不做。
**设计依据**：design.md §2.2、§2.3 EquipRelicOp 扩展段。
**文件面**：`src/sr_od/application/cultivation/relic/operations/equip_relic.py`；测试仓镜像测试文件。
**依赖**：S2
**优先级建议**：2
**完成判据**：
- 既有 EquipRelicOp 测试（criteria=None）全绿；
- 新增流程测试：首件不满足→跳过→次件满足→替换；全部不满足→fail 带逐件概要；约束词含别名与口径包解析正确；
- 实机单跑一次带约束替换成功（选一件明显满足约束的副本）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名 + 实机 run 运行记录。

### 3.6 S6 文档同步与正本更新

**范围**：game coach `relic-enhancement.md` §3 按新流程重写（design.md §1 流程形态）；正本更新清单逐条落地。
**设计依据**：design.md §1、§2.3；本文件「正本更新清单」。
**文件面**：`.agents/skills/sr-od-game-coach/references/mechanics/relic-enhancement.md`、`docs/develop/sr_od/application/cultivation/README.md`、`docs/game/screens/`（若 S1 后有增量）。
**依赖**：S1-S5 全部
**优先级建议**：0
**完成判据**：正本更新清单清零；正本与实现一致；game coach 流程档与新 op 语义一致（含「人定」决策点表述）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/cultivation/README.md`：§5 域内 op 清单 ← S3/S4/S5（新增 FilterRelicReplaceOp / ScanRelicCandidatesOp，EquipRelicOp 标注约束参数）
- `docs/develop/sr_od/application/cultivation/README.md`：§3 识别器自含口径（若 detail_reader 归域口径需提一笔） ← S2
- `.agents/skills/sr-od-game-coach/references/mechanics/relic-enhancement.md`：§3 装备与更换（流程重写）← S6（随 S3/S4/S5 语义定稿）
- `docs/game/screens/遗器-替换.md`：筛选漏斗/排序摘要/升降序增补 ← S1
- `docs/game/screens/遗器-排序规则.md`：属性排序分区增补 ← S1
- `docs/game/screens/遗器-替换-筛选.md`(新) / `遗器-替换-筛选规则.md`(新) ← S1
