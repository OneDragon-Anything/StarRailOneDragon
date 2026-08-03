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
| 米游社百科 API `act-api-takumi-static.mihoyo.com/.../sr_wiki/v1/content/info?content_id=<id>` | ✅ 可用 | 通过 Edge 内 `fetch()` 顺序抓取(同一 origin,CORS 放行)。content/info 取详情,content/list 取列表。 |
| `web_reader` / `WebFetch` / `Bash curl` | ❌ 不可用 | web_reader 拒中文 URL;WebFetch 拦 CN 域名;Bash 沙箱无网。 |

**复现方法**:用 chrome-devtools 连 Edge → navigate 到 `miyoushe.com/sr/wiki/channel/map/209` → evaluate_script 内 `fetch(content/info?content_id=X)` 顺序取各条目 → 解析 `contents[0].text` 里的 URL 编码 `data-data` JSON(含 rate/type/desc/material/分级效果)。

---

## 文件说明

| 文件 | 内容 | 条目数 | 完整度 |
|---|---|---|---|
| [gameplay.md](gameplay.md) | 米游社官方玩法说明(content/6564 全文)+ 机制框架速查 | — | 🟢 完整 |
| [factions.md](factions.md) | 羁绊全表:阵营13/流派12/独立6,逐层效果原文 | 31 | 🟢 完整 |
| [characters.md](characters.md) | 角色花名册:费用/站位/类型/阵营/流派(反查) | 74 | 🟢 完整 |
| [investment_strategies.md](investment_strategies.md) | 投资策略:棱彩/金/银三档 + 效果原文 | 216 | 🟢 完整 |
| [investment_envs.md](investment_envs.md) | 投资环境:概念股/邀请/契约/时代/经济/规则/专家 | 74 | 🟢 完整 |
| [equipment.md](equipment.md) | 装备:简易7/进阶33/特权27/星徽22/白昼6/Fate~24/工具11 | ~130 | 🟢 核心 |
| [competitors.md](competitors.md) | 敌人词缀/节点机制 | — | 🟡 部分 |
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
- 赛季扩充说明: V3.8(article/71454150)、V4.0(73128301)、V4.2(74751746)、V4.4(76641553)

---

## 剩余缺口

| 缺口 | 影响 | 补法 |
|---|---|---|
| 概念股"角色:/装备:"具体清单 | 概念股送的精确角色名 | 图鉴原文是图标,抓取被剥离;效果文本已含规律(送某羁绊角色+装备) |
| Fate 系列装备(7890-7921)逐条效果 | 命运圣杯羁绊配装 | 已列名,效果待逐条 content/info 补(本次未展开) |
| 敌人词缀完整名单+精确效果 | A8 对策配置 | 米游社图鉴未收录,需实机 OCR 落库 |
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
