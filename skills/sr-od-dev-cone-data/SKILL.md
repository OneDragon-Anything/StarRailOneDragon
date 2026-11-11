---
name: sr-od-dev-cone-data
description: 维护崩坏:星穹铁道「光锥数据」全流程的单一入口——拉取全量光锥列表(米游社+国际服双源)、维护权威表与项目内光锥 id、生成常量模块并审阅。游戏版本更新要新光锥信息、回填/核对光锥 id、查光锥词条数据来源时都用,即使没明说。遗器套装数据归本机装备数据类 skill(若挂载);wiki 接口细节归 sr-od-dev-official-api;光锥图标解包获取手法归本机解包类 skill(若挂载)。英文:maintain light cone data pipeline, version update light cone data, cone id definition。
---

# 光锥数据维护

> 分工：wiki 接口调用细节（域名/参数/字段位置）→ `sr-od-dev-official-api`；光锥图标的解包导出手法 → 本机解包类 skill（若挂载）；遗器套装数据 → 本机装备数据类 skill（若挂载）。本文只管流程编排与项目侧 id 定义。

## 总流程（必做 checklist）

**没做完这 6 步不算完成。**

1. ☐ 拉国内 wiki 光锥频道清单+详情（`scripts/fetch_sr_wiki_cone_list.py`）——判据：清单条数与权威表的差集可解释（新版本词条/未同步条目逐条对得上号）
2. ☐ 拉国际服英文名并中英互连（`scripts/fetch_hoyowiki_cone_en_names.py`，可能需代理环境变量）——判据：zh 有 en 无的条目逐条确认为未建页，而非接口失败
3. ☐ 组权威表并与现有常量模块对账（`scripts/build_cone_authority_table.py`）——判据：校验全过；新增条目清单与本版本公告一致
4. ☐ 生成常量模块并审阅 diff（`scripts/gen_light_cones.py`）——判据：校验全过；新增词条逐条过目；文本漂移报告逐条确认「冻结保留」符合预期
5. ☐ 新增光锥时补图标归档与实机验证——获取途径见 §3；账号没有新光锥则在提交信息注明「图标/实机待验证」
6. ☐ 测试锚点同步 + 分仓提交 + 重启 MCP server——判据：`sr-od-test` 的 `test_sr_light_cones.py`（锁总数/id 契约/基准值）通过；重启后 MCP `cone_lookup` 能查到新光锥

## 1. 拉取全量光锥列表（存临时目录）

| 拉取内容 | 脚本 | 临时产物 |
|---|---|---|
| 国内 wiki 清单 + 详情（中文名/命途/星级/特效/获取途径） | 本 skill `scripts/fetch_sr_wiki_cone_list.py` | `.debug/temp/cone_wiki/cone_details_cn.json` |
| 国际服官方英文名（zh/en 列表按词条 id 互连） | 本 skill `scripts/fetch_hoyowiki_cone_en_names.py` | `.debug/temp/wiki_cache/hoyowiki_cone_en_names.json` |

- 运行方式：项目根 `uv run python <脚本路径>`（均仅标准库 + requests；国际服域名可能需代理，urllib 自动读 `HTTP_PROXY`/`HTTPS_PROXY`）。
- **收录判据**：详情解析命中命途与星级才算有效词条；解析失败重试后仍无效的记入失败清单人工看，勿静默跳过。
- **脏数据纪律**：已固化词条的 obtain/skill 文本以常量模块冻结值为准——wiki 存在编辑损坏（梯度列表粘连、字符残缺实测），生成器自动冻结保留并报告漂移，人工只核对漂移是否该回改 wiki；wiki 只喂新增词条。
- 权威表随仓分发（`references/cones-full.json`，键 = 归一化中文名），是生成器与人工对账的锚；步骤 3 重跑即刷新。

## 2. 按光锥列表更新项目代码文件

| 代码文件 | 方式 | 操作 | 验证判据 |
|---|---|---|---|
| `src/sr_od/mys/sr_light_cones.py` | 脚本生成 | `uv run python skills/sr-od-dev-cone-data/scripts/gen_light_cones.py`（读权威表 + wiki 详情 + 现模块冻结文本） | `resolve_light_cone('<新光锥名>')` 命中且 id/星级/命途正确；ruff 不新增违规 |
| `sr-od-test/test/sr_od/mys/test_sr_light_cones.py` | 手动 | 总数、空 id 白名单、基准值（含 id 基准）随版本同步改 | 相关测试全量通过 |

- 生成器纪律：常量数据块**禁手改**（修正走重新生成）；生成后**人工审阅 diff**——新增词条逐条过目，文本漂移报告确认冻结语义符合预期。
- 实机验证：账号抽到新光锥后，在装备替换列表/详情页识别验证（识别手法归装备域）；未抽取则提交信息注明。

## 3. 图标获取与归档

- **识别模板库（规范库）**：`assets/template/light_cone_icon/<LightConeDef.id>/raw.webp`（id 键，命名约定即注册表）；遍历单一入口 = 项目 `src/sr_od/config/light_cone_templates.py`（`iter_light_cone_templates`）。新光锥同步入库；空 id（国际服未同步）暂缺，回填后补录。
- **数据图标归档（过渡库存）**：`assets/game_data/light_cone_icons/<光锥名>.webp`（名称键，`icon_webp_rel_path` 公式寻址）——存量消费方迁移到识别模板库后退役。
- 获取途径：本机解包类 skill 有光锥图标导出手法（按内部 id 段收窄增量导出）优先按它；没有则到米游社 wiki 词条取展示图降级使用，或游戏内截图。两库归档件卡框底色按稀有度与实机一致（5 星金框/4 星紫框/3 星蓝框）。

## 附录 A. 项目光锥 id 定义

- **id**：英文代号 = 官方英文名归一化——小写、仅保留字母数字、符号一律剥离（先例：In the Night → `inthenight`）。id 与角色域 `Character.id` 同风格、独立命名空间。
- **英文名来源**：国际版 HoYoWiki 光锥菜单（zh/en 列表按词条 id 互连，`fetch_hoyowiki_cone_en_names.py` 拉取，官方英文唯一源）。米游社国内站只有中文名，**推不出英文 id**。
- **未同步处理**：国际服未建页 → id 留空串，**宁缺勿错勿猜**；官方公告已给名的可先人工登记（权威表 `source=manual` 行，wiki 上线后自动转正，先例：当第一声「阿哈」响起）。国际服词条名含脏字符（前导空格/换行/BOM/半角标点实测），连表键归一化会清掉，勿手工对名。
- **对齐链**：`权威表（references/cones-full.json，键=归一化中文名）→ id/en/rarity/path_id + 两侧词条 id`。消费方：名称域 `LIGHT_CONE_BY_NAME`/`resolve_light_cone`/MCP `cone_lookup`/图标名称键寻址（过渡）；id 域 `src/sr_od/config/light_cone_templates.py`（卡面模板遍历）。
- **tid 边界**：游戏内部数字 tid 不入公开仓（常量/MCP 契约/测试均无）；tid ↔ 名称的映射与解包数据到本项目 id 的对接，归本机解包类 skill。
