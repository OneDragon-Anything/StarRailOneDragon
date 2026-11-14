# 每月余烬兑换 v1 迭代设计（总纲）

## 0. 元信息

- 迭代目标：新建 app「每月余烬兑换」（`monthly_embers_exchange`），自动把常驻商店·兑换商店·余烬兑换 tab 的月限三件套按配置兑换掉；进一条龙默认组每日跑、已换自动跳过（需求与八条用户裁定见 [requirement.md](requirement.md) §3）。
- 状态：草案（待设计对抗批收敛后定稿）
- 文档清单：
  - [details/store-exchange-recognizer.md](details/store-exchange-recognizer.md) —— 商店画面识别器（读数走识别通道，不造读数 op）
  - [requirement.md](requirement.md) / [flow.md](flow.md) / [decomposition.md](decomposition.md) —— 探索产物沉淀（单一源自此迁移，探索目录停更）
  - [operation-flow-1.md](operation-flow-1.md) —— 新 op `OpenExchangeShop` 设计书
  - [application-flow.md](application-flow.md) —— app 编排稿（分支 / 失败语义 / run_record / config）
  - [landing.md](landing.md) —— 落地阶段拆分与验收

## 1. 问题与动机

- 现状症状：兑换商店余烬 tab 每期限量三件套（星轨专票 5 张、星轨通票动态额度、命运的足迹 1 张），额度随版本过期作废；目前靠人肉记忆手动兑换，易忘、易过期浪费。
- 根因归层：**流程层**——兑换动作本身已有已验证的购买 op（`ExchangeShopBuyGoods`，实机联调完成），缺的是「按周期、按优先级、可配置」的自动编排。
- 解决到哪：余烬月限渠道三件套的全自动兑换 + 每日运行记录 + 优先级/开关配置 + 一条龙默认组接入。
- 明确不解决（防外溢）：
  - 星芒渠道三件套（各 1/1 版本限额度，本期余额 4 星芒什么都换不了）——待办；
  - 协议商店 / 聚灵铸星 / 任何真实货币充值；
  - 数量配置（全部拉满，用户裁定 2026-11-13）。

## 2. 方案

### 2.1 系统级变化

1. **新 app** `monthly_embers_exchange`：APP_NAME=每月余烬兑换，DEFAULT_GROUP=True，NEED_NOTIFY=True，运行记录周期 **DAILY**（理由与取舍见 §2.4）；编排 = 导航段（`OpenExchangeShop`）→ 兑换段（按配置优先级循环 `ExchangeShopBuyGoods(count=None)`）→ 返回段（`BackToNormalWorldPlus`），无独立领奖段（获得物品弹窗在购买 op 内处理，依据 flow.md §2 段表）。
2. **新 op** `OpenExchangeShop`：无参导航 op（手机菜单 → 商店 → 常驻商店页），终点=商店列表页、不指定子 tab（见 [operation-flow-1.md](operation-flow-1.md)）。
3. **复用 op 语义化扩展**：`ExchangeShopBuyGoods` 失败出口在 data 补机器可读字段 `fail_status`（语义集与逐口落位见 [application-flow.md](application-flow.md) §3.1）；`status` 字段保持人读诊断句不变（框架日志纪律：每轮打 status 给人看），流程行为与消息文本零变化。
4. **建档修复**：商店 tab 选中态模板互串（两模板任何时候同时命中，选中判别特征=底部高亮下划线不在模板里）——重裁两张选中态模板，`ShopSwitchTabOp` 的切换验证从空转恢复为真验证（依据 flow.md §4.1-1；不修则真实兑换的 tab 切换无验证，属实现前置阻断项）。
5. **画面识别器** `StoreExchangeRecognizer`：商店屏结构化读数（余额 / 当前 tab / 三件套角标），解析逻辑与购买 op 单一源共用（见 [details/store-exchange-recognizer.md](details/store-exchange-recognizer.md)）；app 主链不依赖它（购买 op 自带月限与余额判定），它是 MCP 侧「本月还能换啥」的读数通道。
6. **MCP 配置通道登记**：SR 侧 MCP 配置工具经 `src/sr_od/backend/config_router.py` 的静态路由表按 app_id 路由（现仅 4 条，未注册不可达）——app 的 6 个配置字段要在 MCP 可读写，须在该表登记 RouterEntry（field_schema + 写穿缓存的 get_config）；无框架新件、无公共包改动。

### 2.2 详设划分与跨详设接口契约

| 契约 | 内容 | 消费方 |
|---|---|---|
| C1 `OpenExchangeShop` | 无参构造；起点任意画面；终点=商店页（子 tab 未指定）；结果状态 SUCCESS / FAIL；无消耗 | app 导航段、MCP agent |
| C2 `ExchangeShopBuyGoods` fail_status | 失败时 `data['fail_status']` ∈ {`SOLD_OUT`, `CARD_UNAVAILABLE`, `NOT_FOUND`, `INSUFFICIENT_MATERIALS`}，data 同时带 `goods`；无 fail_status 的失败 = 非预期失败。状态→代码出口的逐口落位表在 application-flow §3.1（契约的唯一权威表） | app 兑换段分支（语义见 application-flow §3.1/3.2） |
| C3 运行记录语义 | 周期 DAILY（框架现成件，无新件）；「预期内完成」的标记裁定（含零购买场景）见 application-flow §3.2 终态表——该表是标记语义的唯一权威 | 一条龙跳过判据（is_done）、GUI 运行记录展示 |
| C4 识别器 extras | `currency: int\|None`、`active_tab`、`goods[商品标识符].{remaining,total,sold_out,visible}`；字段语义随 `extras_doc` 带出 | MCP agent（analyze_screen）；app 不消费 |

### 2.3 app 与 config 的接线通道

- app 运行时：factory `create_application` 内经 `self.get_config(instance_idx, group_id)` 取配置实例、`self.get_run_record(instance_idx)` 取运行记录，构造参数注入 app（样板 = large_map_recorder 的 create_application）；不经 SrContext 属性接线（GUI 侧用 `ctx.run_context.get_config` 取同一缓存实例，样板 = large_map_recorder 的 GUI interface）。
- MCP 配置工具：RouterEntry 的 get_config 经 `ctx.run_context.get_config(...)` 取同一缓存实例（写穿纪律，config_router 模块 docstring 约定），写立即生效无需重启。

### 2.4 关键取舍

- **运行记录周期取 DAILY、放弃 MONTHLY**：期限口径实为「版本周」未分辨（本期倒计时≈12-01 恰与月初重合，flow.md §4.2-2）；若月限额度随版本在月中刷新，「月内跳过」的 MONTHLY 机制会让新额度延迟到下月 1 日才兑换（最长盲窗≈整月），且一条龙的跳过判据（is_done）发生在 app 运行前，op 动态读数防不住被跳过。DAILY + 预期内完成照常标完成：额度月中解锁次日即被补上（两口径下都零延迟），代价是买完后每日本多一次约 70 秒的导航+扫描空跑；跳过语义由 op 层售罄拦截承担（不重买），运行记录层不再做月内跳过。若下期实勘分辨出纯月历口径，v2 可再引入 MONTHLY（框架件设计已随本迭代取舍记录入 git 历史）。
- **「拉满」遇余额不足的形态未实测**：本期余烬余额 41562，无法在不真实挥霍的前提下构造余额不足形态；滑条是否按余额截断未知。v1 语义 = 弹窗「兑换材料不足」横条出现即点取消、该项 0 张、终止循环（INSUFFICIENT_MATERIALS）；若实为「滑条按余额截断少买」则结果更优（记录实际购买数）。该形态记为已知限制，运行期遇异形（确认按钮禁用无横条等）走非预期失败中止，下期额度低水位时实勘补分支。
- **app 不设 const PRIORITY**：一条龙组内顺序交用户组配置自调；本 app 起止锚定大世界，组内任意顺序都安全。
- **tab 选中态模板重裁**（表示层修复）：备选「文本区加 color_range 锁白色」放弃——下划线特征更强且同时压制两模板互串，一次修复两处；备选「app 不依赖切换验证」放弃——真实消耗场景无验证不可接受。
- **月度周期件曾经的框架设计**（`AppRunRecordPeriod.MONTHLY`）已随周期取舍整体撤销，不进本迭代；设计原文存 git 历史（本文件上一版）。

### 2.5 端到端实测用例（真实消耗，用户裁定 2026-11-13 第 7 条授权）

本期通票剩 2/5（180 余烬）留给本 app 实测：串联验证第一跑真实购买 2 张（走「成功兑换」路径）；第二跑三件套全为已售罄/已换光形态，验证「预期内无事可做→标完成」路径。两条路径一真一空都过 = 端到端验收通过。
