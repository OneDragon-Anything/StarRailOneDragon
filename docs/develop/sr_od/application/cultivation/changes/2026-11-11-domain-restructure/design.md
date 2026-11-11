# 账户养成域包（cultivation）结构重构 迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户裁定（2026-11-11 会话）：①operations 平铺中的养成域代码归位 `application/cultivation/`，按角色/光锥/遗器分子包；②遗器与光锥**彻底不共用**（连几何定位底层也各域独立）；③只迁移刷材料相关（technique/选人导航件留 operations），刷材料按用途分线（角色突破/技能升级/光锥，不挤一个 op）；④迁移优先使用 PyCharm 方法（语义级重构）。
- 状态：草案
- 文档清单：无详设（单文档方案，§2 即完整设计）

## 1. 问题与动机

- 现状症状：
  1. `src/sr_od/operations/` 37 个 py 文件（含 `__init__.py`），养成域约 16 件与导航/战斗/兜底工具混居，域边界不可见；
  2. 遗器/光锥识别器共用基类（`equip_list_recognizer.py` 的 `_EquipListRecognizerBase`）：兜底策略「认错优于 null」是遗器场景的裁定（代码 L608-609 注释「用户裁定」），光锥被连带；算法缺陷同源传播——2026-11-11 遗器批 T-19 实证兜底 argmax 无门槛漏检错认（快枪手野穗毡帽在列表第 2 行 12 屏未找到），光锥侧同段逻辑同病；
  3. `FarmLightConeMaterialOp` 名字通用实为光锥线专属（起点=`光锥-等级提升` 晋阶画面，模块 docstring L1-28），角色突破/行迹线的缺料刷取无实现。
- 根因归层：**约定层**——域代码未按域归位的组织约定缺失，非流程/语义问题。修法 = 域归位 + 两域物理分家，是根修不是症状补丁。
- 解决到哪：①养成域归位；②遗器/光锥识别器彻底分家（含定位/角标底层各域自含）；③刷材料按线分 op 骨架（光锥线现状归位 + 角色/行迹线立项候实机窗）。
- 明确不解决：`tl_*` 逐光捡金 12 文件归位 `treasures_lightward` 包（独立迭代，另行立项）；technique/选人导航件归属调整（用户裁定留 operations）；T-19 兜底算法根治本体（本迭代交付结构前提，根治 = 本迭代 T-6 在分家后的遗器识别器上做，见 landing §3.5）。

## 2. 方案

### 2.1 目标结构（最终形态）

```
src/sr_od/application/cultivation/            # 账户养成域(命名依据:游戏 UI 按钮实名「培养」,
│                                             #  社区与 sr-od-game-coach 全库统一用「养成」,两词同义)
├── character/
│   └── operations/
│       ├── upgrade_character.py              # ← sr_od/operations/upgrade_character.py
│       ├── upgrade_trace.py                  # ← sr_od/operations/upgrade_trace.py
│       ├── character_light_cone_recognizer.py # ← 同名(src 内零消费方,靠 recognizer 扫描自动注册)
│       └── farm_ascension_material.py        # 【新 op,候实机窗】角色突破缺料刷取
├── light_cone/
│   ├── operations/
│   │   ├── equip_light_cone.py               # ← sr_od/operations/equip_light_cone.py
│   │   ├── upgrade_light_cone.py             # ← 同名
│   │   ├── superimpose_light_cone.py         # ← 同名
│   │   ├── open_light_cone_replace.py        # ← 同名
│   │   └── farm_material.py                  # ← 同名,类改名 FarmLightConeMaterialOp(见 §2.4)
│   └── light_cone_list_recognizer.py         # 【新,批次B】自含识别器(定位+识别+角标+兜底全内联)
└── relic/
    ├── operations/
    │   ├── equip_relic.py                    # ← sr_od/operations/equip_relic.py
    │   ├── equip_relic_enhance.py            # ← 同名
    │   ├── select_bag_relic.py               # ← 同名
    │   └── open_relic_replace.py             # ← 同名
    └── relic_list_recognizer.py              # 【新,批次B】自含识别器(T-6 兜底根治在此演进)
```

批次B 后退役（消费方归零）：`sr_od/operations/equip_list_recognizer.py`、`grid_template_locate.py`、`equip_owner_match.py`（依据：三者 src 内消费面 grep 实证——equip_list_recognizer 仅被 equip_light_cone L46/equip_relic L37/open_relic_replace L26 引用；grid_template_locate 与 equip_owner_match 的 src 唯一消费方 = equip_list_recognizer）。

**留守清单**（不迁移，用户裁定③）：`technique.py`、`select_character.py`、`goto_character_detail.py`、`switch_character_tab.py`（通用导航/战斗准备）；`grid_template_locate.py` 批次B 前留守、批次B 退役；`back_to_normal_world_plus.py`（大世界兜底）、`sr_operation.py`（op 基类）、`tl_*` 系列、其余工具件（不在养成域）。

### 2.2 识别器分家口径

- 每域一个**自含**识别器文件：网格定位（OCR 等级锚 + 轮廓补充 + 网格吸附过滤）、模板库加载、整屏主匹配、格内兜底、角标 owner 匹配全部内联——两域之间**零 import**（用户裁定②：不共用；代价 = 定位/角标逻辑约 600 行 ×2 复制，域自治优先于 DRY，接受）。
- 复制的边界：仅「遗器 vs 光锥」两域之间。域内保持单份；若未来出现第三份同构复制，按根源两问升架构级设计件再议。
- 两域识别器保留各自既有差异化标定：光锥 9 列（列距 139px）vs 遗器 4 列（123px）；角标几何光锥卡左上 44px vs 遗器卡右上 ~40px；等级解析「等级N」1-80 vs「+N」0-15；光锥叠影 rank vs 遗器 masked/部位 tab 先验——这些差异在现共用基类里本就是子类覆写（依据：equip_list_recognizer.py L182-341），分家即摊平。
- 兜底策略各自独立演进：遗器侧 T-6 按三路线选型（低置信门槛/重试标记/图像哈希对照）重做兜底；光锥侧不跟随，按自己的实机证据另行决策。
- 测试镜像同步拆分：`test_equip_list_recognizer.py` → `test_relic_list_recognizer.py` + `test_light_cone_list_recognizer.py`；`test_equip_owner_match.py` → 光锥组（48 用例 = 21 真角标 + 27 负样本）/遗器组（33 用例 = 11 + 22）拆两文件（依据：`.debug/progress/2026-11-11-relic-equip/reports/T-17-r1.md` 测试构成记录；数值经对抗审逐项计数复核）。拆分时点 = 批次B，锁行为不变（现全量用例迁移后全绿）。
- 通用函数的复制口径（写死，防「归入 vs 内联」歧义）：原 `grid_template_locate.py` / `equip_owner_match.py` 中的全部可复用函数（`load_template_gray`、`locate_cells_by_votes`、`detect_card_anchors`、`detect_card_rects_contours`、`identify_cells`、`_cached_template_features`、`match_owner` 等）**两域各复制一份完整实现**，不建任何跨域共享模块——两域测试文件（`test_equip_relic.py`/`test_equip_light_cone.py`）对这些工具的直接 import 同步改为引各自域识别器模块内的同名函数。

### 2.3 刷材料分线

- **光锥线（本迭代归位）**：`farm_material.py` 迁 `light_cone/operations/`，类 `FarmLightConeMaterialOp` 改名 `FarmLightConeMaterialOp`。改名依据：与角色/行迹线两兄弟命名对称；op_id 随迁改变（见 §2.5），运行时无断裂（MCP `run_operation` 经 `list_operations` 现场反射取 id，非持久注册表）。
- **角色突破线/行迹线（本迭代立项）**：`FarmCharacterAscensionMaterialOp` / `FarmTraceMaterialOp`，`cond=实机窗摸底`——角色晋阶/行迹画面的缺料栏形态未实机摸底，光锥线的红色计数条判缺料等标定（farm_material.py L10-20 实测注释）不可直接外推；实现以实机摸底建档为前置。
- 三线 op 各自完整实现，不抽共用底层（用户裁定②同一哲学；跳转弹窗/途径行定位/委托刷取的流程形态在三条线的起点画面上可能同构也可能漂移，待三条线都落地后再评估是否值得域内归并，本次预判不做）。

### 2.5 影响面与机械事实

- **注册不断**：op 与 recognizer 扫描根已是 `['sr_od.operations', 'sr_od.application']` 双根 rglob 全深度（依据：`screen_recognizer_scan.py` L29 + 注释、`operation_registry.py` L39 同构）——迁入 application 任意深度后 MCP 自动发现，零适配。
- **op_id 变更面**：`sr_od.operations.<模块>.<类名>` → `sr_od.application.cultivation.<域>.operations.<模块>.<类名>`。运行时无断点（registry 纯反射现算）； **文档同步清单** = `skills/sr-od-game-coach/references/` 下 3 个文件的旧 op_id 前缀引用（`basics/新手与日常决策.md` L57/89/102/107-119/123、`mechanics/light-cone-enhancement.md` L38-159、`mechanics/relic-enhancement.md` L75-160） **加类名级引用**——`FarmLightConeMaterialOp` 在 basics 有 3 处不带路径的裸类名引用（L57/89/123），改名后必须一并同步；批次A 归零判据按「旧路径前缀 + 裸类名」双 grep 设计（见 landing §3.1）。
- **迁移方法**（用户指示④）：文件搬移 `git mv` 保历史；import 更新优先 PyCharm MCP——模块符号级 `rename_refactoring` 语义更新（适用处）/`search_text` 穷尽定位（不可用处兜底），每步 `get_file_problems` 验证 unresolved reference 归零收口（AGENTS.local §5）。
- **测试镜像**：随源文件同步移动（AGENTS.md §10.2 文件镜像规范），`sr-od-test/test/sr_od/operations/test_<名>.py` → `sr-od-test/test/sr_od/application/cultivation/<域>/operations/…`。

### 2.6 关键取舍

- **复制 vs 共用底层**：备选「底层几何下沉 common/、策略层分家」被用户裁定否决（②「不共用」）——采纳彻底复制；本设计的复制面有既有测试锁行为（分家批次判据），漂移风险有界。
- **FarmLightConeMaterialOp 改名**：备选「保留旧名减少文档改动」放弃——三线对称命名是分线的可见性前提，文档 30 处同步是一次性成本。
- **识别器拆分与 T-19 根治分离**：本迭代批次B 只做结构分家（行为锁定），算法根治独立成阶段（§3.5）——结构变更与行为变更不混批，验收面各自干净。

## 3. 落地

阶段拆分、依赖、完成判据见 [landing.md](landing.md)；文档索引与进度见 [README.md](README.md)。
