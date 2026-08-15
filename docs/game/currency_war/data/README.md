# 货币战争 · 基础资料索引(cw_data/)

> **用途**:策略配置地基 + 理解攻略术语。**只存原始数据**,不含策略代码。
> **数据基准**:V4.4 赛季(数据抓取日 2026-08-03)。
> **主来源**:米游社百科「货币战争图鉴」`channel/map/209`(权威)。全部标 🟢 米游社原文 / 🟡 攻略一致 / 🔴 未找到。

---

## 访问限制(必读)

本环境抓取通道的可达性(决定数据来源):

| 通道 | 结果 | 说明 |
|---|---|---|
| **chrome-devtools MCP → headless Edge(远程调试 19999)** | ✅ 可用 | 本次主通道。驱动已登录的 Edge 抓米游社百科全文。 |
| 米游社百科 API `act-api-takumi-static.mihoyo.com/.../sr_wiki/v1/content/info?content_id=<id>` | ✅ 可用 | 通过 Edge 内 `fetch()` 顺序抓取(同一 origin,CORS 放行)。`content/info` 取详情,`home/content/list?channel_id=209` 取全树(含子频道+条目列表)。 |
| `web_reader` / `WebFetch` / `Bash curl` | ❌ 不可用 | web_reader 拒中文 URL;WebFetch 拦 CN 域名;Bash 沙箱无网。 |

**复现方法**:用 chrome-devtools 连 Edge → navigate 到 `miyoushe.com/sr/wiki/channel/map/209` → evaluate_script 内 `fetch('home/content/list?channel_id=209')` 取全树(5 子频道:员工210/装备211/投资策略212/投资环境213/羁绊214,各含 content_id 列表) → 对每个 content_id 调 `fetch('content/info?content_id=X')` → 解析 `contents[0].text` 里 URL 编码的 `data-data` JSON(含 rate/type/desc/material/分级效果)。

---

## 文件说明

| 文件 | 内容 | 条目数 | 完整度 |
|---|---|---|---|
| [gameplay.md](gameplay.md) | 米游社官方玩法说明(content/6564 全文)+ 机制框架速查 | — | 🟢 完整 |
| [factions.md](factions.md) | 羁绊全表:阵营13/流派12/独立6,逐层效果原文 | 31 | 🟢 完整 |
| [traits.json](traits.json) + [traits/](traits/) | **羁绊官方数据**(V4.4,攻旅广场 lineup/index 采集;tiers/效果全文/成员,`tools/cw/gen_factions.py` 生成) | 33 | 🟢 官方 |
| [characters.md](characters.md) | 角色花名册:费用/站位/类型/阵营/流派(反查) | 74 | 🟢 完整 |
| ~~investment_strategies.md~~(已删,ADR-0150) | 投资策略 → **代码单一源** `src/sr_od/application/currency_war/cw_invest_data.py`(plaza API 官方 334 条,`tools/cw/gen_plaza_invest.py` 生成,版本更新重跑) | 334 | 🟢 官方 API 全量(与游戏内数据银行同口径) |
| [invest_cards.md](invest_cards.md) | 投资策略/环境**人读版**(同生成器第二产物,与代码双向链接,id 为锚) | 334+83 | 🟢 同源生成勿手编 |
| ~~investment_envs.md~~(已删,D-68) | 投资环境 → **代码单一源** `src/sr_od/application/currency_war/cw_investments.py::INVESTMENT_ENVS` | ~82 | 🟢 全量(数据银行核对 83/解锁 68);代码已建模,doc 冗余已删(用户原则:代码已建模的游戏数据不存 doc) |
| [equipment.md](equipment.md) | 装备:简易7/进阶33/特权35/星徽22/白昼6/命运改件16/骇客改件16/特殊2/工具11 | 153 | 🟢 米游社图鉴153条全覆盖(游戏内155) |
| [competitors.md](competitors.md) | 敌人词缀(~50)/竞争对手阵营/节点机制 | ~50词缀 | 🟡 米游社图鉴无「竞争对手」分类(🔴 20个竞争对手阵营待实机) |
| [advantage_layouts.md](advantage_layouts.md) | 优势布局/职级效果(等价钻钞 meta 增益) | ~20 | ⚠️ bwiki,米游社-pending |

---

## 关键来源 URL

- 玩法说明(权威): https://www.miyoushe.com/sr/wiki/content/6564/detail
- 货币战争图鉴根: https://www.miyoushe.com/sr/wiki/channel/map/209
  - 员工(角色): channel/map/209/210
  - 装备: channel/map/209/211
  - 投资策略: channel/map/209/212
  - 投资环境: channel/map/209/213
  - 羁绊: channel/map/209/214
- 内容详情 API: `https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info?app_sn=sr_wiki&content_id=<id>`
- 内容列表 API(取全树): `https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list?app_sn=sr_wiki&channel_id=209` → 返回 5 子频道 + 各条目 content_id 列表(⚠️ 图鉴**无「竞争对手」子频道**,该 20 项需实机补)
- 赛季扩充说明: V3.8(article/71454150)、V4.0(73128301)、V4.2(74751746)、V4.4(76641553)

---

## 剩余缺口

| 缺口 | 影响 | 补法 |
|---|---|---|
| **米游社图鉴 vs 游戏内数据银行差额** | ~~策略差19(315/334)~~ **已闭**(plaza API 334 全量,ADR-0150)、环境差5 已闭(API 83)、装备差2(153/155) | 投资策略/环境已切 plaza API 直出(`gen_plaza_invest.py`,内建 diff);装备差 2 🔴 待实机补 |
| **竞争对手阵营(20个)** | A8 boss 阵营/克制关系 | 米游社图鉴 channel/map/209 **无「竞争对手」子频道**(只有员工/装备/投资策略/投资环境/羁绊5类)。游戏内数据银行有20个竞争对手阵营 → 🔴 需实机 OCR 或米游社专页(待日后收录) |
| 概念股"角色:/装备:"具体清单 | 概念股送的精确角色名 | 图鉴原文是图标,抓取被剥离;效果文本已含规律(送某羁绊角色+装备) |
| 敌人词缀完整名单+精确效果 | A8 对策配置 | 米游社图鉴未收录词缀(competitors.md 现为攻略统计🟡),需实机 OCR 落库 |
| 罗刹站位/类型 | 角色表小缺口 | content/6252 单独取(本次批量漏取) |
| **优势布局全量(钻钞 cost + 效果原文)** | 跨局 meta(R2-1 / 09) | advantage_layouts.md 暂用 bwiki;米游社图鉴 channel/map/209 **无此项**,玩法说明 6564 只有机制 → 待米游社专页(若日后收录)或实机校准 |
| **费用刷新概率表(等级 × 1-5 费)** | A4 牌池模型精度(蒙特卡洛 D 牌) | bwiki/gachabase 均无精确表;可能游戏内才公开 → 实机 OCR 逐等级记录 OR 米游社专页(若日后收录) |
| 装备合成配方(哪 2 简易→哪进阶) | 07 装备合成树(EQUIP_RECIPES) | equipment.md 有效果无逐条配方;待 content/info 逐条补或实机 |

> **注**:旧文件 `../cw_game_data.md` 已废弃,数据已拆分到本目录各文件。

---

## 版本更新流程(赛季扩充时重抓,方便迭代)

货币战争是赛季制(gameplay:"赛季重新划分角色定位/羁绊/费用/投资策略"),版本更新数据会变。**更新步骤**:

1. **查版本变更**:读官方赛季扩充说明 article —— V3.8=`71454150`、V4.0=`73128301`、V4.2=`74751746`、V4.4=`76641553`(新版本找对应 article)→ 知道改了哪些(新角色/羁绊调整/费用变/新投资策略环境/新装备)。
2. **重抓米游社图鉴**:chrome-devtools + Edge → `channel/map/209` 各子频道(员工=210/装备=211/投资策略=212/投资环境=213/羁绊=214)→ API `content/info?content_id=<id>` 顺序取(见"复现方法")→ 覆盖对应 cw_data/ 文件。
3. **核对 diffs**:新抓 vs 旧,标变更(factions tiers 变?character 费用/阵营变?新事件?新装备?)→ 更新 `cw_factions.py` / `currency_war_config.py` / `COMP_LIBRARY`。
4. **源标注**:每条数据标米游社 content_id/URL + 版本(V4.x),便于追溯 + 下次更新定位。**一切游戏数据都要有来源**(用户要求:攻略可看其他源,具体游戏数据以米游社/游戏内为准)。
5. **回归测试**:`cw_factions`/config 改后跑 `sr-od-test/test/sr_od/app/currency_war/`,确保策略代码不崩。

> **数据源优先级**:米游社百科/游戏内(权威)>>> bwiki/NGA/攻略(参考,需米游社校准)。标注 🟢 米游社原文 / 🟡 攻略一致 / 🔴 未找到。
