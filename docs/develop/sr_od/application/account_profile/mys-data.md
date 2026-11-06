# mys 数据层正本（账号数据映射 + 游戏静态定义）

> `SrBackendContext` mys 切片的两个数据域：**账号运行时数据**（米游社接口实时拉取）与**游戏静态定义**（官方 wiki 快照固化为 Python 常量）。本文是结构契约正本（as-built）；迭代过程见 `changes/`，数据管道工序归私有 skill `sr-od-dev-relic-data`（junction 挂载，不入本仓）。

## 1. 游戏静态定义（遗器套装数据层）

**单一真相源**：`src/sr_od/mys/sr_relic_sets.py` 常量模块（用户裁定：禁 JSON 数据文件、数据写代码）。固化内容：62 套遗器（隧洞 34 + 位面饰品 28）、192 单件（件名/部位/描述）、2/4 件效果文案、套装获取途径、内部 set_id。数据源 = 官方 wiki 遗器频道快照，人工审阅后固化；固化后本模块即唯一权威载体（快照 JSON 为易失本地件，不持久化）。

**接口契约**（纯常量 + 纯函数，零 IO 零状态）：

- `resolve_set_name(piece_name)` — 件名 → 套装名；miss 返回 None 并 warning（不抛异常），由映射层落「未知套装」兜底
- `resolve_set_by_tid(tid)` — 米游社遗器件 id → 套装定义；tid 公式 = `base + set_id*10 + pos`（隧洞 base=60000、位面 base=50000）
- `icon_webp_rel_path(set_id, pos)` — 单件图标归档的项目相对路径（纯公式寻址不查存在性）
- `build_set_effects(relics, ornaments)` — 佩戴件分组统计 → 已激活套装效果条目
- 索引：`PIECE_TO_SET`（件名反查）、`_SET_BY_NAME`、`_SET_BY_ID`（set_id 反查）——模块加载时各建一次

**set_id 双源锚定与顺序律**：set_id 按实装顺序连续分配（隧洞从 101 起、位面从 301 起），常量排列序 = 实装序，与 set_id 严格双射（测试 `test_set_id_biject_with_list_order` 锁定）。新套装按此律续排，实证手段两档：tid 反查（账号穿戴后）与图标对照仲裁（实装初期即可），工序见私有 skill。

**图标归档**：`assets/game_data/relic_icons/iconrelic_<set_id>_<pos>.webp`（全量单件，客户端解包产物转档）。识别模板边界：SIFT 特征匹配可用、matchTemplate 像素比对不可用（实测口径沿 avatar-extract）。

**数据分层原则**：定义层（ID/名称/图标/分类/效果文案）进常量；内容层（词条每级数值、养成数值）不固化，运行时经 mys 接口现查。wiki 词条偶有错字/缺段——effects 与件名以已固化常量为准，wiki 只作新增字段来源。

**版本刷新**：重抓 wiki 快照 → diff 常量 → 人工审阅更新（禁直灌）→ set_id 顺序律续排 → 图标增量解包归档 → 测试锚点同步。完整工序（含脚本）见私有 skill `sr-od-dev-relic-data`；版本更新总入口 = `sr-od-version-update-adaptation` skill 路由表。

## 2. 账号运行时数据（米游社）

- **装配链**：`SessionStore` → `DeviceIdentity` → `MysClient` → `SrMysClient`（`MysAccessController` 状态机持有，验证循环上限 3；凭据纪律见 `mys.md`）
- **两档端点**：`hkrpg/api/index`（轻口径角色列表）与 `hkrpg/api/avatar/info`（全量明细，`need_wiki=true`）
- **映射契约**：`SrCharacterDetail` = 轻口径十字段 + relics/ornaments/ranks/skills/properties/set_effects 六组明细；遗器单件 `SrRelic` 的套装名经 `resolve_set_name` 件名反查（miss 落「未知套装」），已激活套装效果经 `build_set_effects` 产出（`mys-relic-sets` design §2 契约）
- **会话纪律**：过期只打标记不清本机数据；登录会话落 `config/<实例>/mys/`，密码不落盘

## 3. 查询入口（MCP）

- `relic_lookup(query)` — 遗器静态定义查询（套装名/件名/tid/子串模糊），薄壳直读常量模块，零 IO 零游戏依赖；模糊多命中返回候选不猜（`relic_tools.py`，写法遵循 [mcp-implementation.md](../backend/mcp-implementation.md)）
- `mys_get_characters` / `mys_get_roster_detail` — 账号数据（`mys_tools.py`）
- HTTP 适配器未对齐遗器查询（两个消费方都有需求时按 design P11 收进 backend 共享）
