# mys 数据层权威版本（账号数据映射 + 游戏静态定义）

> `SrBackendContext` mys 切片的两个数据域：**账号运行时数据**（米游社接口实时拉取）与**游戏静态定义**（官方 wiki 快照固化为 Python 常量）。本文是结构契约权威版本（as-built）；数据管道工序与内部 ID 映射不在本仓维护。

## 1. 游戏静态定义（遗器套装数据层）

**单一真相源**：`src/sr_od/mys/sr_relic_sets.py` 常量模块（用户裁定：禁 JSON 数据文件、数据写代码）。固化内容：64 套遗器（隧洞 34 + 位面饰品 30）、196 单件（件名/部位/描述）、2/4 件效果文案、套装获取途径、套装英文 id。数据源 = 官方 wiki 遗器频道快照 + 官方版本公告（wiki 未收录的新套装），人工审阅后固化；固化后本模块即唯一权威载体（快照 JSON 为易失本地件，不持久化）。寻址一律名称键；编号映射不入公共仓（不在本仓维护）。套装英文 id = 官方英文名归一化，是 wiki 数据与本机私有侧编号映射两源数据的共同挂接键（体系详见 skill `sr-od-dev-relic-data`）。

**接口契约**（纯常量 + 纯函数，零 IO 零状态）：

- `resolve_set_name(piece_name)` — 件名 → 套装名；miss 返回 None 并 warning（不抛异常），由映射层落「未知套装」兜底
- `build_set_effects(relics, ornaments)` — 佩戴件分组统计 → 已激活套装效果条目
- 索引：`PIECE_TO_SET`（件名反查）、`_SET_BY_NAME`——模块加载时各建一次

**识别模板规范库**：`assets/template/relic_icon/<套装id>_<部位英文>/raw.webp`（遍历入口 `config/relic_templates.py`，空 id 套装暂缓入库）；识别用模板集一律经该入口取，不得自行扫目录或按名称键拼路径。遗器列表识别范式 = masked 模板匹配（`relic_list_recognizer`，双档级联）。

**数据分层原则**：定义层（名称/图标/分类/效果文案）进常量；内容层（词条每级数值、养成数值）不固化，运行时经 mys 接口现查。wiki 词条偶有错字/缺段——effects 与件名以已固化常量为准，wiki 只作新增字段来源。

**版本刷新**：重抓 wiki 快照 → diff 常量 → 人工审阅更新（禁直灌）→ 识别模板按规范库增量补录 → 测试锚点同步。完整工序（含内部 ID 续排与映射表同步）见 skill `sr-od-dev-relic-data`；版本更新总入口 = `sr-od-version-update-adaptation` skill 路由表。

## 2. 账号运行时数据（米游社）

- **装配链**：`SessionStore` → `DeviceIdentity` → `MysClient` → `SrMysClient`（`MysAccessController` 状态机持有，验证循环上限 3；凭据纪律见 `mys.md`）
- **两档端点**：`hkrpg/api/index`（轻口径角色列表）与 `hkrpg/api/avatar/info`（全量明细，`need_wiki=true`）
- **映射契约**：`SrCharacterDetail` = 轻口径十字段 + relics/ornaments/ranks/skills/properties/set_effects 六组明细；遗器单件 `SrRelic` 的套装名经 `resolve_set_name` 件名反查（miss 落「未知套装」），已激活套装效果经 `build_set_effects` 产出
- **会话纪律**：过期只打标记不清本机数据；登录会话落 `config/<实例>/mys/`，密码不落盘

## 3. 查询入口（MCP）

- `relic_lookup(query)` — 遗器静态定义查询（套装名/件名/子串模糊），薄壳直读常量模块，零 IO 零游戏依赖；模糊多命中返回候选不猜（`relic_tools.py`，写法遵循 [mcp-implementation.md](../backend/mcp-implementation.md)）
- `mys_get_characters` / `mys_get_roster_detail` — 账号数据（`mys_tools.py`）
- HTTP 适配器未对齐遗器查询（两个消费方都有需求时按 design P11 收进 backend 共享）
