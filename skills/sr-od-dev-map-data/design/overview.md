# design/overview — sr-od-dev-map-data

## 定位

星铁「大世界地图信息」的单一入口 skill:区域信息(星球/区域/特殊点)、副本信息(指南注册表)、大地图资产(绘制/录制)三主题。版本更新适配、新区域/新副本录入、地图重录都从这里路由进对应方法文档。

## 边界

- 锄大地路线编写、巡访自动化 op、小地图(minimap)识别调参、screen_info 画面建档不在本 skill:玩法自动化开发归 od-dev-gameplay-automation / od-dev-write-operation / od-dev-screen-onboarding。
- 「版本更新后跟什么」的总编排归 sr-od-version-update-adaptation;本 skill 只承载地图信息各注册表本身的更新方法(含副本注册表)。
- 地图录制只产底图资产(raw/mask/定标坐标),不写路线。

## 构成

- `SKILL.md`:三主题路由 + 排序约束(副本先于角色数据录入)。
- `references/region-data-entry.md`:区域信息数据模型、录入方法、命名规则、验证。
- `references/dungeon-data-entry.md`:副本注册表(指南 yml)更新方法(自 sr-od-version-update-adaptation 迁入)。
- `references/large-map-record.md`:大地图绘制产线选择与 srmap 定标录制流程。
- `scripts/`:srmap 定标产线脚本(gen_map / calib_affine_gen / calib_by_anchors / search_512 / verify_gen)。

## 决策与动机

- **三主题合一个 skill**:区域、副本、地图资产共享同一批存储(`world_patrol_map` yml、`large_map`/`mm_icon` 模板、指南副本注册表)与同一批数据源(srmap / 官方 wiki / 实机),版本更新时三件事一起发生;分散多处会造成入口漂移与重复维护。整合前:副本方法在 sr-od-version-update-adaptation 的 references、地图绘制在 sr-od-dev-large-map-record(已整体并入本 skill 并删除)。
- **副本更新排在角色数据录入之前**(承接 version-update 侧约束的根因):角色数据管道生成「材料→刷取副本」映射时以副本注册表的分类/关卡/区域字段做 join 与锚点校验,注册表落后 = join 报警或新角色材料查不到刷取点。
- **大地图绘制以 srmap 定标法为一级产线**:官方全地形底图 + SIFT 定标,端到端实测接入生产(残差 ~0.87px);`large_map_recorder` 应用(实机逐格截图拼合)为兜底产线——全实机渲染无需定标,但慢且要求区域已探索。产线选择判据写进 large-map-record.md。
- **机制结论**(自 sr-od-dev-large-map-record design 迁移;2026-09 实机实验,约 15 层):
  - 分层渲染:实机大地图 = 当前层深色实体 + 其他层淡显;官方切片是全层深色的页面合成图。二者渲染语义差异是「纯官方纹理匹配门」的上限来源(单层 ~0.89,多层 0.6~0.8),线性调色无法修复;实机贴回把覆盖区修正为运行时渲染,门 ≥0.99。
  - 跨层对齐:同区域各层共享官方页面坐标系(双层同机位互投影 1~7px);但各层实机缩放档有 0.1%~0.5% 微差,跨层共享定标变换不成立 → 逐层独立定标。
  - 缩放档连续分布 0.17~3.4(小区域底图分辨率低 → s>1;大区域 → s<1),scale 不作护栏主判据;质量判据 = rot、残差、内点数。
  - 底图艺术倾斜:个别区域官方切片相对实机渲染有 ~2° 旋转 + 轻微剪切(哀丽秘榭实测,相似变换残差 11px、仿射 1.4px)→ 需要仿射级模型兜底。
  - srmap 点位为编辑者手标(逐点 ±7~25px,部分准到 ±5px),运行时点击靠 ±100px 图标模板窗兜底可用;巡访精修 lm_pos 是精度根治手段。
  - 未探索区域不可录:实机只渲染已走路径,无地形可与全地形底图对应,先在游戏内探索再录。
