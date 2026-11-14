# application-flow · 每月余烬兑换编排设计稿

> 对标 op 开发的 nodes.md：四段式骨架落成具体 op 序列；失败处理语义、run_record、config 在本文件一次定死（写代码时不再随手定）。事实记录（走查）在 flow.md，本文件是设计稿。

## 1. 节点图

```
[框架自动: 检测窗口+进游戏 (need_check_game_win)]
① 导航段
  n1 到达兑换商店        OpenExchangeShop()                          (起点)
② 兑换段
  n2 按优先级逐项兑换     for goods in 开启项(按 priority 升序, 同值按固定序):
                          ExchangeShopBuyGoods(goods, count=None).execute()
                          └─ 按 §3 状态分支
③ 领奖段: 无（获得物品弹窗在购买 op 内处理, flow.md §2 裁定）
④ 返回段
  n3 返回大世界          BackToNormalWorldPlus()
```

- n1 失败 → 直接 round_fail 结束（后续无从谈起，中止档）。
- n2 结束（无论换没换到东西）→ n3；n3 保证一条龙在大世界干净交接。
- app 类继承 `SrApplication`，`run_record` 传 `ctx.monthly_embers_exchange_run_record`。

## 2. 兑换项与排序

| 商品标识符 | 月限 | 默认开关 | 默认优先级 |
|---|---|---|---|
| `special_pass` | 5 | 开 | 10 |
| `pass` | 动态（本期 2/5） | 开 | 20 |
| `tracks_of_destiny` | 1 | 开 | 30 |

- 排序 = priority 升序；同值按固定序兜底 专票 > 通票 > 足迹（用户裁定 8）。
- 数量一律 `count=None` 拉满（用户裁定 2：数量不可配）。
- 循环中途遇「余额不足」即终止循环，其后项全部放弃（用户裁定 1：换到换不动为止、后面的放弃）。优先级高的项单价未必更高（专票 90×剩余 / 足迹 60），先高优先级可能少换总张数——这是裁定 1 的既定语义（优先级=用户意愿排序），不做 cheapest-first 优化。

## 3. 失败处理语义（必须设计档，逐状态显式处理）

### 3.1 分支总表（C2 契约的消费方）

| ExchangeShopBuyGoods 结果 | 语义 | 动作 |
|---|---|---|
| `PURCHASED` | 换到 | 记购买数量/单价/余额进运行记录；继续下一项 |
| `SOLD_OUT` / `CARD_UNAVAILABLE` | 本期额度已尽（弹窗横条售罄 / 卡角标已售罄·已达上限·未解锁） | 该项记入跳过清单；继续下一项（预期内——本月已换过的重复运行就是全员此形态） |
| `NOT_FOUND` | 列表扫到底没找到商品（可能下架/版本变动） | 该项记入跳过清单并带告警标注；继续下一项（商品不在售 ≠ 失败，阻塞重跑无意义） |
| `INSUFFICIENT_MATERIALS` | 余额不足（弹窗预判或横条） | **终止循环**，其后项记「因余额放弃」；按正常完成收尾 |
| 其他 `FAIL` | 非预期失败（画面异常 / 确认未生效 / 余额终验不符 / 画面未回商店页等） | **中止 app**：n2 直接 round_fail（跳过 n3 的正常路径由框架失败收尾处理），运行记录标失败 |

- 单项真实失败 = 中止（用户裁定 5）；「售罄/未找到/余额不足」是兑换生意的预期内结果而非失败——区分依据 = 该状态是否意味「这次运行没达成应有状态」：预期内结果下 app 状态仍是「本周期已处理完」。

### 3.2 终态与运行记录标记（周期标记裁定）

| 场景 | run_status | 标「本周期已完成」？ | 依据 |
|---|---|---|---|
| 全部开启项处理完毕（含全部售罄跳过、零购买） | SUCCESS | **标** | 预期内的无事可做照常标完成，防一条龙反复空跑（判例：跳过分两种之「预期内」） |
| 部分换到 + 部分售罄/放弃 | SUCCESS | **标** | 本周期该做的都做了（额度尽是天数问题，下月重置后才可再换） |
| 循环因余额不足提前终止 | SUCCESS | **标** | 裁定 1「换到换不动为止」= 达成用户意图的终态，非失败 |
| 非预期失败中止 | FAIL | **不标** | 「该做没做成」，一条龙下周期自动重跑补做（判例之「该做没做成」） |

### 3.3 运行记录业务字段（一次落地，不留空壳）

`MonthlyEmbersExchangeRunRecord(AppRunRecord)`，period=MONTHLY（C3 契约）：

| 字段 | 类型 | 语义 |
|---|---|---|
| `bought_pass` / `bought_special_pass` / `bought_tracks_of_destiny` | int | 本次各商品实际购买数量（成功路径由 PURCHASED data.bought 写入） |
| `skip_note` | str | 跳过与放弃明细（如 `pass:SOLD_OUT,tracks_of_destiny:NOT_FOUND`），空 = 无跳过 |
| `balance_left` | int \| None | 最后一项兑换后余额（尽力留痕，读不出 = None） |

`reset_record` 覆写：状态复位 + 上述字段清零（父类只复位状态，业务字段各 app 自清——父类注释约定）。

## 4. config 处理方式

`MonthlyEmbersExchangeConfig(ApplicationConfig)`（app_id=monthly_embers_exchange，走 factory `create_config` 通道——MCP 配置工具经 factory 读到）：

| 字段 | 类型/默认 | 用途 |
|---|---|---|
| `special_pass_enabled` / `pass_enabled` / `tracks_of_destiny_enabled` | bool / True | 单项开关；关闭项不进循环 |
| `special_pass_priority` / `pass_priority` / `tracks_of_destiny_priority` | int / 10, 20, 30 | 优先级，升序兑换；同值按 §2 固定序兜底 |

- 配置读取点：n2 循环开始时一次性读入并排序。
- 全部关闭场景 = 预期内无事可做 → 照常标完成（防一条龙反复空跑）。

## 5. 时序预算

导航 ~15s + 每项兑换 20-40s（滚动找卡为主）+ 返回 ~10s ≈ 全流程 1-2 分钟（flow.md §4.3 走查口径）。
