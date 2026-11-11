---
name: sr-od-dev-relic-data
description: 维护崩坏:星穹铁道「遗器套装数据」全流程的单一入口——拉取全量套装列表(国内 wiki + 国际服双源)、维护权威表与项目内套装英文 id、部位英文术语、生成/审阅常量、识别模板规范库。游戏版本更新要新套装信息、回填/核对套装 id、查遗器数据来源时都用,即使没明说。解包与图标导出手法归本机解包类 skill(若已挂载);wiki 接口细节归 sr-od-dev-official-api;光锥同构体系归 sr-od-dev-cone-data。英文:relic set data pipeline, version update relic sets, relic set id。
---

# sr-od-dev-relic-data:遗器套装数据

## 1. 总流程 checklist(版本更新/新套装实装时)

1. ☐ 刷新双源输入:① `scripts/fetch_sr_wiki_relic_list.py`(国内 wiki 遗器频道,content_id);② `scripts/fetch_hoyowiki_relic_en_names.py`(国际服 zh/en 互连 → 英文名/id)。产物在 `.debug/temp/relic_wiki/`。
2. ☐ 国内 wiki 详情重抓(新套装词条详情:效果/件名/desc)——详情抓取脚本含官方 wiki 特殊模板解析,归本机解包类 skill(若已挂载);只拿名称/编号不需要它。
3. ☐ diff 常量 `src/sr_od/mys/sr_relic_sets.py`:新套装清单对照 → **人工审阅**新条目(set_name/kind/pieces/effects/obtain/desc)。**禁直灌 wiki 数据**——wiki 词条有错字/缺段实测;效果数值要双源交叉(官方公告原文 × wiki),冲突以官方公告为准(实证:4.7 亚空异容所 18% vs 测试服库 15%,公告胜;BWIKI 件名「深黢」vs 公告「深黯」,公告胜)。
4. ☐ 常量更新:`RelicSetDef` 新条目(排列序 = 实装序);`id` 字段按国际服英文名归一化回填,国际服未收录留空串(宁缺勿错)。文本源优先级:官方公告原文 > wiki。
5. ☐ 权威表重跑:`scripts/build_relic_authority_table.py` → `references/relics-full.json`;脚本会报告未消费词条/空 id 清单,不为零时人工审阅。
6. ☐ 图标:归档(名称键)与识别模板库(见 §3)增量补录——解包导出与转档手法归本机解包类 skill(若已挂载)。
7. ☐ 测试锚点:`sr-od-test/test/sr_od/mys/test_sr_relic_sets.py` 锁死套装总数/件数/效果齐备形态/新套装锚点(件名+效果+desc),版本更新后同步;空 id 套装名单在白名单常量里维护。
8. ☐ 提交(主仓与测试仓分开,逐文件点名)+ 重启项目 MCP server(`relic_lookup` 直读常量)。

## 2. id 体系(架构约定)

**套装英文 id = 官方英文名归一化**(小写仅字母数字,符号全剥),与 `sr_light_cones.LightConeDef.id` 同规。数据源 = 国际服 wiki(en-us)词条英文名。

**id 是中枢键**:wiki 数据(国内 content_id / 国际服 page_id / 英文名)与解包数据(解包侧图标编号)各自映射到 id 上,**不建 wiki↔解包直连**——两个数据源只在 id 上会合。解包侧编号与名称的映射归本机解包类 skill(若已挂载),公开仓不存数字编号。

**部位英文**(官方术语,国际服词条 Set 块 pos 字段实证):隧洞 `Head/Hands/Body/Feet`(pos 1-4)、位面 `Planar Sphere/Link Rope`(pos 5-6);归一化后见常量 `RELIC_POS_EN`。

**宁缺勿错**:国际服未收录的套装(2026-11-11 时点 7 套:星如我见的领航员/戏梦点星的伶人/贪噬禁果的异端/坠星启航地/寰宇生研院/神的瞬息欢愉/亚空异容所)id 留空串,模板库不入库,国际服同步后回填补录。空 id 名单由测试白名单锁定,回填时收紧白名单。

**译名差异**:国际服 zh 词条名与国服官方名可能不同(实证:国服「停转的萨尔索图」= intl「停止转动的萨尔索图」)——权威表按 entry_page_id 对齐,差异登记 `intl_cn` 别名字段(构建脚本 `INTL_ALIAS`),权威表键恒为国服官方名。

## 3. 识别模板规范库

`assets/template/relic_icon/<template_id>/raw.webp`,template_id = `<套装id>_<部位英文归一化>`(如 `spacesealingstation_planarsphere`)。命名约定即注册表,无 config.yml;遍历入口 `src/sr_od/config/relic_templates.py::iter_relic_templates(ctx)`(未知目录/缺原图直接 raise)。空 id 套装暂缓入库,回填后补录。

双库关系:名称键旧库 `assets/game_data/relic_icons/` 已随消费方迁移到 `iter_relic_templates` 删除——识别消费以规范库为唯一正库,勿再按名称键归档或寻址。

## 4. 权威表(references/relics-full.json)

键 = 归一化中文名(国服官方名);字段:cn/en/id/kind/wiki_content_id/hoyowiki_page_id/intl_cn(仅译名差异时)/order(实装序,与常量排列序一致)/source(`wiki`=国内 wiki 有词条,`manual`=官方公告占位,wiki 同步后转正)。

## 5. 冻结与脏数据纪律

- 常量是唯一权威载体:已固化条目以模块值为准,wiki 只喂新增字段;重抓 diff 出现已有条目文本漂移只报告不直改(实测 wiki 有编辑损坏)。
- 效果数值必须双源:官方公告原文 × 社区 wiki;测试服数据库(gacha 类)数值可能滞后于正式服。
- 件名错字以官方公告/已固化常量为准。

## 附录 A:id 定义链示例

```
国服官方名「太空封印站」
  → 国际服 en 名 "Space Sealing Station"(entry_page_id 147)
  → 归一化 id "spacesealingstation"(小写仅字母数字)
  → 部位 Planar Sphere → 归一化 "planarsphere"
  → 模板 template_id "spacesealingstation_planarsphere"
```

解包侧(编号↔名称)与国内 wiki 侧(content_id↔名称)的连接都经由名称域落到 id,见 §2。
