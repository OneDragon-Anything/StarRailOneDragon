# 设计对抗报告：2026-11-11-domain-restructure（账户养成域包结构重构）

> 攻击者：独立对抗审 agent（2026-11-11）。攻击规范 = `docs/develop/harness/iteration-design.md` §7 三核（无前提 / 规范遵循 / 治本）。
> 机械断言全部独立复核（grep/read 实测，不采信设计文档自述）；行级证据就地标注。

## 1. 结论：打回（无阻断级，7 条应修 + 2 条存疑；修订后可复检定稿）

设计骨架成立：迁移面收敛（src 目录外零消费方，实测确认）、双扫描根断言为真、T-19 承接链账本实证一致、七件套齐。打回理由 = 应修项集中在「验收判据的可执行性与覆盖面」「正本更新清单不全」「依据指针错位」「design↔landing↔账本三处失同步」——全部是局部修订，不动设计结构：

| # | 严重度 | 一句话 |
|---|---|---|
| A1 | 应修 | 批次A 判据命令 `uv run python src/sr_od/backend/operation_registry.py` 不可执行（无 `__main__` 块，零输出） |
| A2 | 应修 | game-coach 归零判据 grep 模式覆盖不了类名引用（`FarmLightConeMaterialOp` ×3）与格式说明行；行清单漏 L102 |
| A3 | 应修 | 正本更新清单漏 3 个 docs/game/screens 文档的失效路径引用 |
| A4 | 应修 | design §2.2 依据指针错位：48/33 测试构成出处标成 T-22，实为 T-17-r1 |
| A5 | 应修 | landing §3.1 括号分类 11 件 ≠ 同句「12 个现有文件」（漏 farm_material） |
| A6 | 应修 | 批次B 隐性连带面未点名：两个 op 测试文件 import grid_template_locate + src 两处注释悬挂 |
| A7 | 应修 | landing 末阶段「依赖：全部落地阶段」与账本 T-7 deps=[T-2,T-3] 失同步，且字面口径会卡死收尾 |
| A8 | 存疑 | 治本核验：归位修法未沉淀通用组织约定，下一域归位无约定可循 |
| A9 | 存疑 | 机械数字偏差：平铺文件 36→实测 37；tl_* 13→实测 12（前缀口径） |

## 2. 机械断言复核表

| # | 断言（出处） | 核验手法 | 结果 |
|---|---|---|---|
| M1 | 扫描根双根 `['sr_od.operations','sr_od.application']`，screen_recognizer_scan L29 / operation_registry L39（design §2.5） | 读两文件全文 | **一致**。`screen_recognizer_scan.py` L29、`operation_registry.py` L39-42 均为该双根，rglob 全深度；行号标注精确 |
| M2 | equip_list_recognizer 消费面 = 3 op：equip_light_cone L46 / equip_relic L37 / open_relic_replace L26（design §2.1） | grep `RelicReplaceRecognizer\|LightConeReplaceRecognizer` 全 src | **一致**。3 个 import 行号全对；其余命中为定义处与 docstring 提及，非消费 |
| M3 | grid_template_locate / equip_owner_match 的 src 唯一消费方 = equip_list_recognizer（design §2.1） | grep 全 src | **一致（限 src 代码 import）**。唯一 import = equip_list_recognizer L43/L47。注意两处边界（见 A6）：①equip_relic.py L4、equip_light_cone.py L57/L211 为注释提及，非 import；②测试仓 test_equip_relic.py L30-33、test_equip_light_cone.py L37-40 直接 import grid_template_locate——断言只声称 src，成立，但批次B 连带面因此存在 |
| M4 | character_light_cone_recognizer src 零消费、靠扫描自动注册（design §2.1） | grep 全 src + 读文件 | **一致**。全 src 仅定义文件 L30 一处命中；类无 `__init__`、screen_name 为类属性，无参实例化可行，迁移后仍在扫描根内 |
| M5 | game-coach 3 文件 30 处引用，行清单 basics L57/89/107-119/123、light-cone L38-159、relic L75-160（design §2.5） | grep + 逐文件读 | **部分一致**。3 文件 ✅；行清单与实际引用行吻合（范围式标注）。但「30 处」按宽口径（op_id + 类名 + 格式行提及）实测约 30 上下成立，**按 landing 判据的 6 个 op_id 前缀 grep 只有 16 行命中**——两口径差 = 判据覆盖缺口（A2）；行清单漏 L102 格式说明行（A2） |
| M6 | test_equip_owner_match 光锥组 48 用例（21 正 + 27 负）/ 遗器组 33 用例（11 正 + 22 负）（design §2.2） | 读测试文件逐项计数 | **一致**。光锥正 = 10×2 帧 + 1 = 21、负 = 26 + 1 = 27；遗器正 = 4 + 7 = 11、负 = 17 + 5 = 22。与文件 docstring 自述及 design 断言全符。**但依据指针错位**（A4）。「测试仓镜像 11 文件」之说 design/landing 均无此字样；实测：迁移 12 文件的现有测试镜像 = **10**（character_light_cone_recognizer、superimpose_light_cone 无测试镜像），批次B 拆分对象另 2（test_equip_list_recognizer / test_equip_owner_match） |
| M7 | FarmMaterialOp 现状 = 光锥线专属，起点=光锥-等级提升，docstring L1-28、红条标定 L10-20（design §1/§2.3） | 读 farm_material.py 头部 | **一致**。L1-28 docstring（L3 起点实名「光锥-等级提升」）；L10-20 实测段含计数条红字判定与 OCR 漏读注释；类定义 L76 |
| M8 | 光锥 op 相互/对底层的 import 关系（批次A/B 文件面完整性） | 逐文件读 import + grep | **一致，无漏消费方**。upgrade_light_cone L34 / superimpose_light_cone L37 / open_light_cone_replace L26 均只 import sr_operation（不碰识别器）；equip_light_cone L46 import 识别器；farm_material 只 import 常量表与 UseTrailblazePower。**全 src 对迁移 12 模块的目录外引用 = 零**（含 gui/application/backend）；`from sr_od.operations import X` 形式仅测试仓 4 处（均为迁移文件自身镜像测试）；custom_combine_op 的 OpEnum 不含任何养成 op；mcp/app.py 仅 enter_game 引用（迁移面外）；tools/mcp、screen_info、config/ 均零硬编码 |
| M9 | op_id 变更运行时无断裂：registry 纯反射现算、非持久注册表（design §2.3/§2.5） | 读 operation_registry.py | **一致**。op_id = `f'{module}.{cls.__name__}'`（L312）现算；resolve_op_class 现场解析（L329-369）；无持久化。**附带发现**：landing §3.1 判据给的直跑命令无效，见 A1 |
| M10 | 差异化标定本就是子类覆写，equip_list_recognizer L182-341（design §2.2） | 读该区间 | **一致**。L182 = LightConeReplaceRecognizer 类头；区间内含光锥 9 列 139px（L209）、角标左上 44px（L197-202）、等级「等级N」1-80（L293-309）、叠影模板匹配（L211-240）、遗器 4 列 123px（L341）、角标右上 ~40px（L326-333） |
| M11 | 兜底「认错优于 null」用户裁定注释在 L608-609（design §1） | 读该区间 | **一致**。L608-609：「…直接取聚簇最高的名字,不设分数门槛(用户裁定:认错也只会认成库内最近似,优于 null)」 |
| M12 | 定位/角标逻辑约 600 行 ×2 复制（design §2.2） | 数行数 | **合理（估算口径）**。grid_template_locate 253 行 + equip_owner_match 199 行 = 452，加识别器内定位/角标段 ≈600；两域全内联后总量 ≈1100-1200，与「×2」吻合 |
| M13 | landing §3.5 承接原遗器批 T-19 | 读 `2026-11-11-relic-equip/dag.jsonl` | **一致**。T-19 终态 `dead`（2026-11-11T08:58:55），why 指认承接 = 新账本 T-6（criteria 继承）；新账本 `2026-11-11-cultivation-refactor/` 已建，T-2~T-7 与 landing 阶段一一对应。**但 T-7 deps 见 A7** |
| M14 | §3.5 离线样本证据存在（截图 + 怪盗假面错认样本） | 文件检索 | **一致**。`screenshot_20261111_020229_129273.png` 存在于 `.debug/sr_od_mcp/screenshot/`；「怪盗」记录在 `2026-11-11-relic-equip/REPORT.md` 与 `evidence/T-1-head-restored.md` |
| M15 | operations 平铺 36 个文件；tl_* 13 文件（design §1） | 列目录计数 | **偏差**。顶层非 `__init__` 文件实测 **37**（差 1，无口径说明）；tl_ 前缀文件实测 **12**（as 5 + fh 2 + pf 4 + reward_claim 1；加 goto_treasures_lightward 才 13——「tl_* 13 文件」措辞与前缀口径不符）。见 A9 |
| M16 | 测试镜像路径 `test/sr_od/application/cultivation/<域>/operations/`（design §2.5） | 对照 AGENTS.md §10.2 镜像规范 | **一致**（op 文件在 `<域>/operations/` 下，镜像含 operations 层；批次B 识别器不在 operations 子包，其测试落点 design 未写死，可按镜像规范推出，见走查 §4 批次B） |

## 3. 攻击点清单

### A1【严重度：应修】批次A 复验判据的首选命令不可执行

- **出处**：landing.md §3.1 完成判据第 2 条「`uv run python src/sr_od/backend/operation_registry.py` 或 MCP `list_operations` 复验」。
- **问题**：`src/sr_od/backend/operation_registry.py` 全文 457 行**无 `if __name__ == '__main__'` 块**——直跑该文件 = import 模块后零输出、零退出码，实现者拿不到「迁移动作出现在扫描结果」的任何证据，要么误判通过要么停手提修订。同样，recognizer 注册复验（scan_recognizers 需 ctx 占位 + 无参实例化）也没有可执行命令形态。
- **已核可行性**：`scan_operations(ctx)` 的 ctx 仅占位（纯反射，L279-326），`scan_recognizers(ctx)` 同构——两者**不连游戏可跑**，需一次性脚本形态或 MCP server 活着。
- **修法**：判据改写为可执行形态，二选一：①「MCP `list_operations` 复验（需 MCP server 运行，不依赖游戏窗口）」；②给出一次性脚本命令（如 `uv run python -c "from sr_od.backend.operation_registry import scan_operations; ..."` 打印新 op_id 清单）。账本 T-2 criteria「run_operations 扫描含全部迁移动作」随判据同步（iteration-design §3.1：阶段小节变更 → 账本同步）。

### A2【严重度：应修】game-coach 归零判据 grep 模式与同步意图不匹配，会假绿

- **出处**：landing.md §3.1 完成判据第 4 条（6 个 `sr_od.operations.` 前缀归零）；design.md §2.5 行清单「basics L57/89/107-119/123」。
- **问题**：game-coach 文档存在三类不被该 grep 模式覆盖的同步对象：
  1. **类名形态引用**：`basics/新手与日常决策.md` L57「`FarmLightConeMaterialOp` 跳转路径通用」、L89「③ 走 `FarmLightConeMaterialOp` 跳转路径」、L123「`FarmLightConeMaterialOp` 刷满」——`FarmLightConeMaterialOp` 改名 `FarmLightConeMaterialOp` 后这 3 处必须同步，但 grep 前缀模式抓不到类名，改完跑判据 = 假绿；
  2. **op_id 格式说明行**：basics L102「op_id 格式 `sr_od.operations.<模块>.<类名>`」与 L116「op_id = `sr_od.operations.<模块>.<类名>`」——迁移后对养成 op 不再成立，L116 在行清单内、**L102 不在**（清单从 L107 起），漏行；
  3. design 的「30 处」为宽口径（含类名与格式行提及），landing 判据只验 16 行 op_id 形态——验收覆盖面 < 同步意图面。
- **修法**：判据补两条 grep：`FarmLightConeMaterialOp`（basics 全文归零）+ 格式行人工核对项；design §2.5 行清单补 L102。或声明「grep 归零仅覆盖 op_id 形态，类名与格式行另附人工核对清单」。

### A3【严重度：应修】正本更新清单漏 3 个 docs/game/screens 文档的失效路径引用

- **出处**：landing.md「正本更新清单」节（仅 4 条：cultivation 正本区 / AGENTS.md §1.1 / relic-enhancement.md §5 / TODO.md）。
- **问题**：正本区（docs/game/）存在引用被迁移/退役模块路径的文档，迁移后成死链，清单未收录（grep `docs/` 实测）：
  - `docs/game/screens/光锥-替换.md` L4：引 `src/sr_od/operations/equip_list_recognizer.py`——批次B 退役后死链；
  - `docs/game/screens/遗器-排序规则.md` L54：引 `src/sr_od/operations/equip_relic.py`——批次A 迁移后死链；
  - `docs/game/screens/遗器-替换.md` L56：引 `equip_owner_match.match_owner`、L61：引 `test/sr_od/operations/test_equip_owner_match.py`——批次B 退役/拆分后死链。
- **规范出处**：iteration-design.md §5 硬规则 4（修订后全量同步复查——「逐一核设计引用的每个符号/路径存在性」；正本引用面未扫全）。
- **修法**：正本更新清单补 3 行（各标注触发阶段：遗器-排序规则 ← 批次A；光锥-替换、遗器-替换 ← 批次B）。

### A4【严重度：应修】48/33 测试构成的依据指针错位

- **出处**：design.md §2.2「test_equip_owner_match.py → 光锥组（48 用例）/遗器组（33 用例）拆两文件（依据:遗器批账本 T-22 交付记录的测试构成）」。
- **问题**：T-22 与测试构成无关——`2026-11-11-relic-equip/dag.jsonl` T-22 title = 「SelectBagRelicOp 应修合并批:set_name=None 分支不点卡违背首件契约…」，其交付记录不含 48/33 测试构成。构成记录实际在 `2026-11-11-relic-equip/reports/T-17-r1.md`（progress 目录内唯一含 test_equip_owner_match 构成描述的交付记录）。48/33 数值本身经本审直接读测试文件逐项计数**核实为真**（见 M6），故属指针错位非依据虚假。
- **规范出处**：iteration-design.md §5 硬规则 1（依据就地标注——依据须真实可回查）。
- **修法**：指针改为 `sr-od-test/test/sr_od/operations/test_equip_owner_match.py` 模块 docstring（自含、抗 changes/ 清理）或 T-17-r1.md。

### A5【严重度：应修】landing §3.1 括号分类 11 件 ≠ 同句 12 件（漏 farm_material）

- **出处**：landing.md §3.1 范围：「git mv 迁移 design.md §2.1 结构树所列 12 个现有文件（遗器 4 op、光锥 4 op、角色 2 op + 1 识别器）」。
- **问题**：括号分类 4+4+2+1 = **11**，漏 `farm_material.py`（光锥应为 5 op）。design §2.1 结构树齐全（权威源无缺），账本 T-2 title 数对（「遗器4op/光锥4op+farm_material/角色2op+1识别器」= 12）——唯 landing 括号错。这是 iteration-design §5 硬规则 4 卡点描述的「design↔landing 失同步」形态实证（同迭代第 3 处失同步，见 A3/A7）。
- **修法**：括号改「（遗器 4 op、光锥 5 op（含 farm_material）、角色 2 op + 1 识别器）」。

### A6【严重度：应修】批次B 隐性连带面未点名（测试借用 + 注释悬挂）

- **出处**：landing.md §3.2 范围/文件面/判据。
- **问题**：
  1. **op 测试文件 import 借用**：`sr-od-test/test/sr_od/operations/test_equip_relic.py` L30-33 与 `test_equip_light_cone.py` L37-40 直接 `from sr_od.operations.grid_template_locate import (load_template_gray, locate_cells_by_votes)`——这两个文件是 op 流程测试，**不属于**「识别器镜像拆分」，但 grid_template_locate 删除后它们 import 崩、全量测试红。范围小节「测试镜像拆分」字面不含此连带；判据「退役三文件删除后全仓 grep 消费方归零」若「全仓」含 sr-od-test 可兜住 import 面，但依赖实现者自行发现。
  2. **src 注释悬挂**：equip_relic.py L4、equip_light_cone.py L57/L211 注释提及 grid_template_locate（「见 grid_template_locate」类指引）——删除后注释指向不存在模块，grep import 归零验不出注释。按 AGENTS.md §8「出处写成持久索引或纯语义描述」，批次B 应顺手改写。
  3. **措辞歧义**：范围「grid_template_locate.py、equip_owner_match.py 内容**按域归入**两识别器」与 design §2.2「全内联、两域零 import」存在张力——通用函数（load_template_gray/locate_cells_by_votes/match_owner）的唯一一致解是**两域各复制一份**，「按域归入」字面可误读为「按消费方切分、各归各家」（切分出共享层即违裁定②）。两个测试借用函数因此也应两域各得一份，测试各自改引本域。
- **修法**：§3.2 范围补一句：「含 test_equip_relic / test_equip_light_cone 的 grid_template_locate 借用 import 改引（通用定位/角标函数两域各一份）；equip_relic / equip_light_cone 注释中的 grid_template_locate 指引同步改写为语义描述」；「按域归入」改「全量内联复制进两域识别器（通用函数两域各一份，行为锁定）」。

### A7【严重度：应修】末阶段依赖与账本 T-7 失同步，且字面口径卡死收尾

- **出处**：landing.md 末阶段「**依赖**：全部落地阶段」；账本 `2026-11-11-cultivation-refactor/dag.jsonl` T-7 `deps: ["T-2","T-3"]`。
- **问题**：两处不一致。且「全部落地阶段」的字面口径意味着 T-7（正本更新）要等 T-4/T-5/T-6——三者均 `cond=实机窗` 的长周期任务，收尾会被实机窗无限期卡住。账本按 [T-2,T-3] 立任务反映的才是内容真值（正本更新清单 4 条全部由批次A/批次B 触发，无一条依赖新 op/兜底根治）。
- **规范出处**：iteration-design.md §3.1「阶段小节 = 账本唯一源：立任务 = 照阶段小节内容 dag.py add…禁止两处各自演化」；硬规则 4。
- **修法**：landing 末阶段依赖改为明确语义，如「§3.1、§3.2（正本化内容仅涉结构归位与路径引用；§3.3/§3.4/§3.5 为候实机窗的独立批，不阻塞正本更新）」——与账本对齐；或维持「全部落地」并把 T-7 deps 补全（不推荐：制造人为卡点）。

### A8【严重度：存疑】治本核验：域归位修法未沉淀通用组织约定

- **出处**：design.md §1 根因归层「约定层」、§2.1 留守清单。
- **核验**：归层结论成立——operations 平铺混居确是组织约定缺失（表示/流程/语义层均无恙）；修法（归位 + 两域分家）对本域是根修；T-19 兜底根治显式排期（§1「明确不解决」+ landing §3.5）符合「症状修法须显式声明战术权衡 + 排期根治」；「第三份同构复制升架构级设计件」预置了跨件半问出口（§2.2）。
- **存疑点**：本迭代只搬走养成域，**「operations 顶层放什么」的通用约定没有沉淀**——tl_* 12 件（已声明外溢 ✅）之外的通用工具件混居现状延续，operation_registry.py L36-38 注释里的约定口径（「工具型 operation 约定放 `<app>/tools/` 子包」）与本次落点（`<域>/operations/`）并存两套措辞。下一域（tl_*）归位时无单一约定可循，同族第 2 件到来时仍是逐件修。
- **建议**（不阻塞定稿）：正本更新清单加一条——cultivation 域正本顺手写明本域落点所依据的组织约定（一句即可），tl_* 迭代立项时直接引用。

### A9【严重度：存疑】两处机械数字无依据标注且与实测偏差

- **出处**：design.md §1「`src/sr_od/operations/` 36 个平铺文件」「`tl_*` 逐光捡金 13 文件」。
- **实测**：顶层非 `__init__` .py = **37**；tl_ 前缀文件 = **12**（加 goto_treasures_lightward 才 13）。偏差不改变任何结论（迁移面以 §2.1 结构树为准，结构树逐文件核对无缺），但两处均无依据标注且数错，正中 iteration-design §5 硬规则 1 的「未标注 = 弱点自带坐标」。
- **修法**：修订时校正数字并标口径（36→37 并注明是否排除 sr_operation.py 基类的口径；13→改「tl_* 12 文件 + goto_treasures_lightward」或「逐光捡金域 13 文件」）。

## 4. 实现者走查记录（逐阶段「凭这份能开工吗」）

| 阶段 | 走查结论 | 明细 |
|---|---|---|
| §3.1 批次A | **能开工；验收判据需修缮后自洽** | 结构树（§2.1）是完整权威源，逐文件可执行；git mv + import 更新 + PyCharm 收口方法有出处（AGENTS.local §5）；消费面已实证收敛（目录外零引用），实现者不会踩隐性断裂。卡点：①首选复验命令零输出（A1）——实现者跑到这条会停；②括号 11 vs 12（A5）——按括号理解会漏 farm_material，按结构树执行则无碍；③game-coach 同步按行清单可执行，但类名 3 处改完无人验（A2）。附带提醒：测试 fixture 目录（equip_owner_match/、equip_light_cone/、equip_relic/ 等实机截图目录）随测试文件一起 `git mv`——测试内 `Path(__file__).parent` 相对引用，目录不搬则测试红 |
| §3.2 批次B | **能开工；连带面靠「跑测试兜设计」不理想** | 拆分口径、行为锁定、判据（互不 import grep / 用例计数对账）齐；「按域归入」与「全内联」的歧义可实现者需自行拍板通用函数归属（A6.3，唯一一致解可推断但不应留推断空间）；两个 op 测试文件的 import 崩要等全量测试红才暴露（A6.1）。识别器测试落点路径 design 未写死——可按镜像规范推（识别器不在 operations 子包 → 测试落 `<域>/` 根而非 `<域>/operations/`），建议批次B 范围一句话写死 |
| §3.3 角色突破新 op | **能开工（候实机窗）** | 摸底→建档→实现→实机验收闭环完整；「流程形态参照光锥线」给出参照物与不可外推项（红条标定 L10-20 不可直接外推，§2.3 已声明）；真实消耗须用户同意的判据合规；文件面含 screen_info 摸底建档 |
| §3.4 行迹新 op | **能开工（候实机窗，与 §3.3 同窗）** | 七件以引用式复用 §3.3（信息可得，弱自包含，记录备查不单列攻击点）；入口边界（按当前打开技能）明确 |
| §3.5 遗器兜底根治 | **能开工（候实机窗）** | 承接链账本实证一致（T-19 dead → 新账本 T-6 criteria 继承）；三路线选型有出处（原 T-19 title）；离线样本双证据在盘（截图文件 + 怪盗假面记录）；判据①②逐字继承原 criteria，④离线回归可验证 |
| 末阶段 正本更新 | **清单补全后可执行** | 现清单 4 条均真实存在可执行（TODO.md SelectBagRelicOp 条实证在 L310；cultivation 正本区现状仅 changes/ 子目录，「从 design.md 正本化」成立）；漏 3 个 game/screens 文档（A3）；依赖口径失同步（A7） |

## 5. 核二·规范遵循逐条核

| 规范（iteration-design §5/§3.1） | 核验结果 |
|---|---|
| 硬规则 1 依据就地标注 | 大体良好——扫描根行号、消费面 grep、docstring 行号等标注经独立复核**精确为真**（M1-M12）。违例：A4（指针错位）、A9（两处数字无标注且偏差）、A5（「12 个」无拆解依据且括号自矛盾） |
| 硬规则 2 实现者无需再设计 | 无「待定/酌情/看情况」残留；「候实机窗」是 cond 声明（合法挂起机制）非语义未定。缺口：A1（判据不可执行——停手令会被触发）、A6.3（通用函数归属留推断空间） |
| 硬规则 3 无过程叙事 | **合规**。无「本轮/修订后/已改」措辞；§0 用户裁定指针是裁定内容引用非过程叙事 |
| 硬规则 4 修订后全量同步 | **违规实证 3 处**：A3（正本引用面没扫全）、A5（括号 vs 计数）、A7（末阶段依赖 vs 账本） |
| 阶段小节七件 | §3.1-§3.5 + 末阶段 **7/7 齐全**（§3.4 文件面为引用式复用 §3.3，信息完整，备注不攻） |
| README 模板符合度 | 文档节/进度节结构与模板一致；「设计对抗:未开始」待本报告后更新并附 attack.md 链接 |

## 6. 核三·治本核验小结

- §1 归层结论（约定层）**成立**：平铺混居是组织约定缺失，非流程/语义缺陷；判定与「修法 = 归位 + 分家」自洽。
- §2 修的是根：本域归位是根修；兜底算法缺陷（症状同源传播）显式排期根治（§3.5），符合「症状修法须显式声明战术权衡 + 排期根治」。
- 同族逐件修风险：tl_* 已声明外溢独立迭代（§1，符合 iteration-design §1.1 边界判定）；遗留缺口 = 通用组织约定未沉淀（A8，存疑级建议）。

—— 报告完。攻击面覆盖：三份文档全文走读、16 项机械断言独立复核、9 个攻击点（7 应修 + 2 存疑）、6 阶段实现者走查。未改动设计文档、代码与账本。
