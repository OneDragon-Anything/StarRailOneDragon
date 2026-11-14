# 每月余烬兑换 v1 迭代设计（总纲）

## 0. 元信息

- 迭代目标：新建 app「每月余烬兑换」（`monthly_embers_exchange`），每月自动把常驻商店·兑换商店·余烬兑换 tab 的月限三件套按配置兑换掉；进一条龙默认组每日跑、月内已换自动跳过（需求与八条用户裁定见 [requirement.md](requirement.md) §3）。
- 状态：草案（待设计对抗批收敛后定稿）
- 文档清单：
  - [details/framework-monthly-period.md](details/framework-monthly-period.md) —— 运行记录月度周期件（公共框架新增 MONTHLY）
  - [details/store-exchange-recognizer.md](details/store-exchange-recognizer.md) —— 商店画面识别器（读数走识别通道，不造读数 op）
  - [requirement.md](requirement.md) / [flow.md](flow.md) / [decomposition.md](decomposition.md) —— 探索产物沉淀（单一源自此迁移，探索目录停更）
  - [operation-flow-1.md](operation-flow-1.md) —— 新 op `OpenExchangeShop` 设计书
  - [application-flow.md](application-flow.md) —— app 编排稿（分支 / 失败语义 / run_record / config）
  - [landing.md](landing.md) —— 落地阶段拆分与验收

## 1. 问题与动机

- 现状症状：兑换商店余烬 tab 每期限量三件套（星轨专票 5 张、星轨通票动态额度、命运的足迹 1 张），额度随版本过期作废；目前靠人肉记忆手动兑换，易忘、易过期浪费。
- 根因归层：**流程层**——兑换动作本身已有已验证的购买 op（`ExchangeShopBuyGoods`，实机联调完成），缺的是「按月周期、按优先级、可配置」的自动编排。
- 解决到哪：余烬月限渠道三件套的全自动兑换 + 月度运行记录 + 优先级/开关配置 + 一条龙默认组接入。
- 明确不解决（防外溢）：
  - 星芒渠道三件套（各 1/1 版本限额度，本期余额 4 星芒什么都换不了）——待办；
  - 协议商店 / 聚灵铸星 / 任何真实货币充值；
  - 数量配置（全部拉满，用户裁定 2026-11-13）。

## 2. 方案

### 2.1 系统级变化

1. **新 app** `monthly_embers_exchange`：APP_NAME=每月余烬兑换，DEFAULT_GROUP=True，NEED_NOTIFY=True，运行记录周期 MONTHLY（新件）。编排 = 导航段（`OpenExchangeShop`）→ 兑换段（按配置优先级循环 `ExchangeShopBuyGoods(count=None)`）→ 返回段（`BackToNormalWorldPlus`），无独立领奖段（获得物品弹窗在购买 op 内处理，依据 flow.md §2 段表）。
2. **新 op** `OpenExchangeShop`：无参导航 op（手机菜单 → 商店 → 常驻商店页），终点=商店列表页、不指定子 tab（见 [operation-flow-1.md](operation-flow-1.md)）。
3. **复用 op 语义化扩展**：`ExchangeShopBuyGoods` 的失败出口补语义化状态（卡片不可购 / 列表未找到 / 余额不足 / 售罄横条），app 按状态分支（契约见 [application-flow.md](application-flow.md) §3.2）；只加状态值不改流程行为。
4. **公共框架新件**：`AppRunRecordPeriod.MONTHLY`（见 [details/framework-monthly-period.md](details/framework-monthly-period.md)）。
5. **建档修复**：商店 tab 选中态模板互串（两模板任何时候同时命中，选中判别特征=底部高亮下划线不在模板里）——重裁两张选中态模板，`ShopSwitchTabOp` 的切换验证从空转恢复为真验证（依据 flow.md §4.1-1；不修则真实兑换的 tab 切换无验证，属实现前置阻断项）。
6. **画面识别器** `StoreExchangeRecognizer`：商店屏结构化读数（余额 / 当前 tab / 三件套角标），解析逻辑与购买 op 单一源共用（见 [details/store-exchange-recognizer.md](details/store-exchange-recognizer.md)）；app 主链不依赖它（购买 op 自带月限与余额判定），它是 MCP 侧「本月还能换啥」的读数通道。

### 2.2 详设划分与跨详设接口契约

| 契约 | 内容 | 消费方 |
|---|---|---|
| C1 `OpenExchangeShop` | 无参构造；起点任意画面；终点=商店页（子 tab 未指定）；结果状态 SUCCESS / FAIL；无消耗 | app 导航段、MCP agent |
| C2 `ExchangeShopBuyGoods` 状态集 | `PURCHASED`（data 带 bought/unit_price/balance_left/monthly_left）/ `CARD_UNAVAILABLE` / `NOT_FOUND` / `INSUFFICIENT_MATERIALS` / `SOLD_OUT` / 其余 `FAIL` | app 兑换段分支（语义见 application-flow §3.3） |
| C3 MONTHLY 周期 | `AppRunRecordPeriod.MONTHLY = 3`；重置判据 = 运行记录 dt 的年月段与当前不同（dt 已含游戏刷新小时偏移） | app 运行记录、一条龙跳过判据 |
| C4 识别器 extras | `currency: int\|None`、`active_tab`、`goods[商品标识符].{remaining,total,sold_out,visible}`；字段语义随 `extras_doc` 带出 | MCP agent（analyze_screen）；app 不消费 |

### 2.3 端到端实测用例（真实消耗，用户裁定 2026-11-13 第 7 条授权）

本期通票剩 2/5（180 余烬）留给本 app 实测：串联验证第一跑真实购买 2 张（走「成功兑换」路径）；第二跑三件套全为已售罄/已换光形态，验证「预期内无事可做→标完成」路径。两条路径一真一空都过 = 端到端验收通过。
