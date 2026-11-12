---
name: sr-od-dev-relic-data
description: 维护崩坏:星穹铁道「遗器套装数据」全流程的单一入口——拉取全量套装列表(国内 wiki + 国际服双源)、维护权威表与项目内套装英文 id、部位英文术语、生成/审阅常量、识别模板规范库。游戏版本更新要新套装信息、回填/核对套装 id、查遗器数据来源时都用,即使没明说。wiki 接口细节归 sr-od-dev-official-api;光锥同构体系归 sr-od-dev-cone-data。英文:relic set data pipeline, version update relic sets, relic set id。
---

# sr-od-dev-relic-data:遗器套装数据

## 1. 总流程 checklist(版本更新/新套装实装时)

1. ☐ 刷新双源输入:① `scripts/fetch_sr_wiki_relic_list.py`(国内 wiki 遗器频道,content_id);② `scripts/fetch_hoyowiki_relic_en_names.py`(国际服 zh/en 互连 → 英文名/id)。产物在 `.debug/game_data/relic/wiki/`(本 skill 拉取缓存统一落点;旁置 fetched_at.txt 记拉取时间,重跑前先看日期防用过期缓存)。
2. ☐ 国内 wiki 详情重抓(新套装词条详情:效果/件名/desc)——详情抓取脚本含官方 wiki 特殊模板解析,不在本仓维护;只拿名称/编号不需要它。
3. ☐ diff 常量 `src/sr_od/mys/sr_relic_sets.py`:新套装清单对照 → **人工审阅**新条目(set_name/kind/pieces/effects/obtain/desc)。**禁直灌 wiki 数据**——wiki 词条有错字/缺段实测;效果数值要双源交叉(官方公告原文 × wiki),冲突以官方公告为准(实证:4.7 亚空异容所 18% vs 测试服库 15%,公告胜;BWIKI 件名「深黢」vs 公告「深黯」,公告胜)。
4. ☐ 常量更新:`RelicSetDef` 新条目(排列序 = 实装序);`id` 字段按国际服英文名归一化回填,国际服未收录留空串(宁缺勿错)。文本源优先级:官方公告原文 > wiki。
5. ☐ 对账报告:`scripts/build_relic_authority_table.py`——常量 vs 双 wiki 缓存直接 diff,stdout 报告(未消费词条/空 id/别名;**零落盘**,权威表 JSON 已废除);不为零的项人工审阅后手改常量。
6. ☐ 图标:归档(名称键)与识别模板库(见 §3)增量补录——展示图取自米游社 wiki 词条,或游戏内截图后裁片。
7. ☐ 测试锚点:`sr-od-test/test/sr_od/mys/test_sr_relic_sets.py` 锁死套装总数/件数/效果齐备形态/新套装锚点(件名+效果+desc),版本更新后同步;空 id 套装名单在白名单常量里维护。
8. ☐ 提交(主仓与测试仓分开,逐文件点名)+ 重启项目 MCP server(`relic_lookup` 直读常量)。

wiki/米游社缺词条或缺图时,不空等外部收录——走 §6 兜底路由(wiki → 智库 → 副本)。

## 2. id 体系(架构约定)

**套装英文 id = 官方英文名归一化**(小写仅字母数字,符号全剥),与 `sr_light_cones.LightConeDef.id` 同规。数据源 = 国际服 wiki(en-us)词条英文名。

**id 是中枢键**:wiki 数据(国内 content_id / 国际服 page_id / 英文名)与本机私有侧的编号映射各自挂到 id 上,**不建 wiki↔编号直连**——两个数据源只在 id 上会合。编号与名称的映射不在本仓维护,公开仓不存数字编号。

**部位英文**(官方术语,国际服词条 Set 块 pos 字段实证):隧洞 `Head/Hands/Body/Feet`(pos 1-4)、位面 `Planar Sphere/Link Rope`(pos 5-6);归一化后见常量 `RELIC_POS_EN`。

**宁缺勿错**:国际服未收录的套装(2026-11-11 时点 7 套:星如我见的领航员/戏梦点星的伶人/贪噬禁果的异端/坠星启航地/寰宇生研院/神的瞬息欢愉/亚空异容所)id 留空串,模板库不入库,国际服同步后回填补录。空 id 名单由测试白名单锁定,回填时收紧白名单。

**译名差异**:国际服 zh 词条名与国服官方名可能不同(实证:国服「停转的萨尔索图」= intl「停止转动的萨尔索图」)——权威表按 entry_page_id 对齐,差异登记 `intl_cn` 别名字段(构建脚本 `INTL_ALIAS`),权威表键恒为国服官方名。

## 3. 识别模板规范库

`assets/template/relic_icon/<template_id>/raw.webp`,template_id = `<套装id>_<部位英文归一化>`(如 `spacesealingstation_planarsphere`)。命名约定即注册表,无 config.yml;遍历入口 `src/sr_od/config/relic_templates.py::iter_relic_templates(ctx)`(未知目录/缺原图直接 raise)。空 id 套装暂缓入库,回填后补录。

双库关系:名称键旧库 `assets/game_data/relic_icons/` 已随消费方迁移到 `iter_relic_templates` 删除——识别消费以规范库为唯一正库,勿再按名称键归档或寻址。

## 4. 对账报告(无中间权威表)

**零落盘**(2026-11-12 废除 references/relics-full.json 中转层——无人程序化消费,纯人工审阅用):`build_relic_authority_table.py` 直接对账常量 RELIC_SETS 与双 wiki 缓存,stdout 报告 manual 名单/空 id/译名别名/未消费词条;常量是唯一权威载体与数据本体,对账锚 = git 历史常量版本。

## 5. 冻结与脏数据纪律

- 常量是唯一权威载体:已固化条目以模块值为准,wiki 只喂新增字段;重抓 diff 出现已有条目文本漂移只报告不直改(实测 wiki 有编辑损坏)。
- 效果数值必须双源:官方公告原文 × 社区 wiki;测试服数据库(gacha 类)数值可能滞后于正式服。
- 件名错字以官方公告/已固化常量为准。

## 6. 数据缺口兜底路由(wiki 缺数据 → 智库 → 副本)

主源(双 wiki)缺词条/缺图时的降级层级,**逐层用,每层有前提与边界**:

```
层级1-2  wiki/米游社(主源)+ 展示图模板   —— §1 常规路径
   ↓ wiki 缺词条或缺图
层级3    智库图鉴(游戏内)              —— 前提:套装已在账号解锁
   ↓ 智库锁卡(未收录)
层级4    对应副本刷取解锁               —— 消耗开拓力,先获用户同意
```

### 6.1. 层级 3:智库图鉴兜底(免 wiki 的名称/分类权威源)

游戏内智库(数据银行)在 wiki 未收录时提供套装名、分类归属与收录状态。
导航 op 已建档(2026-11-12 实机验证,含英/中双语言词条):

| 步骤 | 用什么 |
|---|---|
| 进智库 | op `sr_od.operations.menu.open_data_bank.OpenDataBankOp()`——任意起点 → 智库主页 |
| 选分类进图鉴 | op `sr_od.operations.menu.select_data_bank_tab.SelectDataBankTabOp(tab='遗器')`——主页 7 分类图标路由;遗器图鉴分 隧洞遗器/位面饰品 两个子类,每卡显示 x/4(位面 x/2)部位收录数,右上角「已收录 总数」= 全局进度 |
| 读新套装 | 逐卡卡名(国服官方名)+ 收录数;**列表尾部 ??? 锁定卡 = 未收录套装**(名称不可见);新实装套装排在列表尾部 |
| 拿英文名 | op `sr_od.application.game_settings.game_settings_op.SwitchLanguageOp(target_lang='en')` 后重复进智库——图鉴列表页左上角第二行标题 = 国际服官方英文名;读完切回 `'cn'` |

用法对应 §1:新套装名进常量/权威表(国际服未收录时 id 留空,英文名可先从智库拿
作对照,权威 id 仍以国际服 wiki 词条为准——宁缺勿错不放开);「已收录」计数用于
验证新套装是否实装、以及层级 4 刷取后的解锁验收。

边界(实证):

- **未解锁套装在智库只显示 ???**——名称级兜底只对已解锁(至少获得过 1 件)
  套装成立;完全未收录的套装名字拿不到,进层级 4。
- 智库卡片**只有收录数,没有套装效果文本**——效果仍以官方公告原文 × wiki
  双源交叉(§5),智库不替代。
- 语言切换是真实操作且整包文本重载有延迟(切换后纯等待 10s+),读完即切回,
  不留账号在英文态。

### 6.2. 层级 4:副本刷取解锁(消耗开拓力,发起前必须获用户同意)

智库锁卡且用户要求解锁/拿数据时,刷对应副本直到新套装入图鉴:

| 步骤 | 用什么 |
|---|---|
| 找副本条目 | `assets/game_data/interastral_peace_guide_data.yml` 侵蚀隧洞(隧洞遗器)/饰品提取(位面饰品)分类,按套装名找 mission(display_name 字段即套装名);**条目缺失 = 先录副本数据**(归 sr-od-dev-map-data,新版本新副本未录时前置) |
| 配计划 | MCP `add_config_item(app_id='trailblaze_power', list_field='plan_list', item_dict={mission_id:'生存索引 侵蚀隧洞 <副本名> <区域名>', plan_times:N, run_times:0, team_num:0})`——team_num=0 用游戏内当前编队;对强度没把握时改用体力计划历史用得最多的配队编号(按 plan_list 各项 team_num 的使用次数统计) |
| 执行 | `run_standalone_app('trailblaze_power')`——指南传送/选次数/选队/战斗/结算全自动;每次 40 开拓力 |
| 验收 | 回智库遗器图鉴(6.1)看收录数变化;掉落随机(套×部位 8 选 1),集齐期望 ~20 次 |
| 收尾 | **恢复计划列表现场**——临时加的计划项删除;为避免旧计划被顺带执行而临时改动的项原样加回 |

⚠️ 真实消耗门:开拓力为稀缺资源,**发起前必须向用户说明次数与消耗并获明确同意**;
先跑小批(如 6 次)验证链路与掉落,再决定是否续刷。
⚠️ 行为注意:计划全部完成时框架会自动全量重置 run_times(`check_plan_run_times`,
loop=false 拦不住当轮内的重置)——别用「跑满体力」式大批量,收尾恢复现场。

### 6.3. 层级间的关系

- 层级 3/4 产出的是**名称、分类、收录状态与解锁动作**;常量字段的权威值
  (效果/desc/英文 id)仍走 §1 的 wiki 主源与 §5 双源纪律——智库兜底不降低
  数据纪律,只是不让「wiki 未收录」阻塞套装实装确认与收录推进。
- wiki 后续收录时按 §1 常规流程转正(source=manual → wiki),空 id 回填。

## 附录 A:id 定义链示例

```
国服官方名「太空封印站」
  → 国际服 en 名 "Space Sealing Station"(entry_page_id 147)
  → 归一化 id "spacesealingstation"(小写仅字母数字)
  → 部位 Planar Sphere → 归一化 "planarsphere"
  → 模板 template_id "spacesealingstation_planarsphere"
```

本机私有侧(编号↔名称)与国内 wiki 侧(content_id↔名称)的连接都经由名称域落到 id,见 §2。
