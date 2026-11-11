# 遗器装备流程改造 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

### 3.1 S1 画面建档与 fixture

**范围**：按 design.md §2.4 清单建档（MCP `upsert_screen_area`/`create_screen` 落 yml+合并缓存）；「按钮-遗器建议排序」改纯坐标区「按钮-排序设置」并改造消费点——`equip_relic.py` 排序前置链的弹窗打开动作从 `round_by_find_and_click_area`（find 命中文本）改为坐标直点 + until 转移验证（纯坐标区 find 不命中，同模块遗器位点击既有模式）；两篇画面 doc 增补 + 两篇新建（筛选面板/筛选规则弹窗）。边界：不含新 op 实现（含上述 equip_relic.py 消费点改造）。
**设计依据**：design.md §2.1（F1-F21 事实与帧）、§2.4。
**文件面**：`assets/game_data/screen_info/`（经 MCP 工具）、`src/sr_od/application/cultivation/relic/operations/equip_relic.py`（仅排序弹窗打开动作消费点）、`docs/game/screens/遗器-替换.md`、`docs/game/screens/遗器-排序规则.md`、`docs/game/screens/遗器-替换-筛选.md`(新)、`docs/game/screens/遗器-替换-筛选规则.md`(新)；测试仓 `screens/遗器-替换/`（14 摸底帧 + 平坦值帧已归档）与 `test/sr_od/application/cultivation/relic/operations/test_equip_relic.py`（两处旧 area 名断言随改名更新）。
**依赖**：无
**优先级建议**：0
**完成判据**：
- MCP `analyze_screen` 对「遗器-替换-筛选」「遗器-替换-筛选规则」精准命中（拿对应帧离线验证 + 实机开面板复核一次）；
- `equip_relic.py` 排序前置链改为纯坐标打开后，既有流程测试（含更新后断言）全绿；
- 完成前常规检查（本文首节）。
**验收凭据形式**：画面对照（离线帧 analyze 命中）+ 既有测试全绿。

### 3.2 S2 词条解析层下沉与词缀读取器

**范围**：`src/sr_od/mys/sr_relic_stats.py`(新) 承接五表三函数全量下沉（design.md §2.2 逐符号清单）；`relic_eval_tools.py` 删下沉符号改 import（`MAIN_CHECK_SLOTS`/`ROSTER_STRUCTURE_ERROR_MESSAGE` 留守）；`relic_detail_reader.py`(新) 按 design.md §2.3 实现读区结构化解析（F17-F20：角标区域判读次数、平坦/% 消歧、未识别词标记、`times_confirmed` 降级标记）+ 解析单测。边界：不含任何 op 实现；不改 `mys_evaluate_relic_substats` 出参语义。
**设计依据**：design.md §2.2、§2.3（relic_detail_reader 段）、§2.6（下沉取舍）。
**文件面**：`src/sr_od/mys/sr_relic_stats.py`(新)、`src/sr_od/backend/mcp/relic_eval_tools.py`、`src/sr_od/application/cultivation/relic/relic_detail_reader.py`(新)；测试仓对应镜像文件 + fixture（词缀详情两帧：% 形态 + 平坦形态）。
**依赖**：无（与 S1 并行）
**优先级建议**：1
**完成判据**：
- `mys_evaluate_relic_substats` 既有测试全绿（行为不变的回归锁）；
- `relic_detail_reader` 对「候选详情词缀.webp」（% 形态：6.9%[1]/9.1%[1]/22.0%[3]/3.4%[0]）与「候选详情词缀平坦值.webp」（平坦形态：防御力55[2]/18.1%[2]）解析与帧实读一致（角标区域判读生效，行级 OCR 尾数误读被清洗）；整帧 OCR 一次断言共享，实测 ≥2s 登记 slow_marks.txt；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名（解析单测 + 评估工具回归）。

### 3.3 S3 筛选 op

**范围**：`FilterRelicReplaceOp`（design.md §2.3：参数/入口/set_name 链含弹窗内先「全部清除」/sort_stat 链为「打开弹窗→关建议排序→选等级→不确认→清残留→点属性行→确认」的显式构成，前置子链与 equip_relic 同源复制并注明）+ fixture_controller 流程测试（set_name 链 / sort_stat 链 / 幂等空跑 / 重复运行同参数不反选 四条剧本）。边界：不做筛选/排序的清除收尾；多属性排序不支持（单 `sort_stat`）。
**设计依据**：design.md §2.1 F1-F16、§2.3 FilterRelicReplaceOp 段（含共享态跨 op 约束）。
**文件面**：`src/sr_od/application/cultivation/relic/operations/filter_relic_replace.py`(新)；测试仓镜像测试文件。
**依赖**：S1
**优先级建议**：2
**完成判据**：
- 流程测试四剧本全绿，节点点击与转移断言对照 F1-F16；sort 链验证锚 = 摘要读区与「等级|<属性名>」全等；
- 实机单跑一次 `set_name` 链 + `sort_stat` 链成功（MCP run_operation，跑完游戏停在正确筛选列表、摘要文本 = 期望形态）；
- 实机验证「全部清除」在套装弹窗内清除勾选生效（幂等依据）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名 + 实机 run 运行记录。

### 3.4 S4 候选扫描 op

**范围**：`ScanRelicCandidatesOp`（design.md §2.3：单屏语义/静态排序前置检查/逐卡点选读词缀/详情 OCR 件名优先/bottom_reached）+ 流程测试。边界：不翻页不滚顶（调用方职责）；不做预标注。
**设计依据**：design.md §2.1 F17-F19、§2.3 ScanRelicCandidatesOp 段。
**文件面**：`src/sr_od/application/cultivation/relic/operations/scan_relic_candidates.py`(新)；测试仓镜像测试文件。
**依赖**：S1、S2（排序摘要读区 area 来自 S1；词缀解析来自 S2）
**优先级建议**：2
**完成判据**：
- 流程测试全绿：含「建议排序开着 → 显式失败」（替换屏默认态帧取 default.webp）「正常单屏扫描 → JSON 档案与 bottom_reached 断言」「masked 卡以详情 OCR 件名入档」；
- 实机单跑一次：对当前列表产出候选 JSON，抽 2 件与实机画面详情面板对读一致（验收时开游戏核对）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名 + 实机 JSON 抽查对照。

### 3.5 S5 EquipRelicOp 词缀约束扩展

**范围**：`EquipRelicOp` 新增 `substat_criteria` 参数、`verify_selected` 约束判定与 `_substat_reports` 概要累计、`find_and_select` 耗尽分流（design.md §2.3）；入口「筛选中」角标预检（共享态防线）；None 路径行为不变回归。边界：不改候选定位与抢件逻辑（耗尽 fail 文案与概要分流、入口预检除外）；数值型约束不做。
**设计依据**：design.md §2.2、§2.3 EquipRelicOp 扩展段（含共享持久筛选态的跨 op 约束）。
**文件面**：`src/sr_od/application/cultivation/relic/operations/equip_relic.py`；测试仓镜像测试文件。
**依赖**：S2
**优先级建议**：2
**完成判据**：
- 既有 EquipRelicOp 测试（criteria=None）全绿；
- 新增流程测试：首件不满足→跳过→次件满足→替换；全部不满足→fail 带逐件概要（与「未找到」文案分流）；「筛选中」角标在场→入口显式失败带提示；
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

- `docs/develop/sr_od/application/cultivation/README.md`：§5 域内 op 清单 ← S3/S4/S5（新增 FilterRelicReplaceOp / ScanRelicCandidatesOp，EquipRelicOp 标注约束参数；detail_reader 为 OCR 读区解析件非 ScreenRecognizer，不属 §3 记述对象，不改 §3）
- `.agents/skills/sr-od-game-coach/references/mechanics/relic-enhancement.md`：§3 装备与更换（流程重写，含共享筛选态的操作顺序约束）← S6（随 S3/S4/S5 语义定稿）
- `docs/game/screens/遗器-替换.md`：筛选漏斗/排序摘要/升降序增补 ← S1
- `docs/game/screens/遗器-排序规则.md`：属性排序分区增补 ← S1
- `docs/game/screens/遗器-替换-筛选.md`(新) / `遗器-替换-筛选规则.md`(新) ← S1
