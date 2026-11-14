# application-flow · 每月余烬兑换编排设计稿

> 对标 op 开发的 nodes.md：四段式骨架落成具体 op 序列；失败处理语义、run_record、config 在本文件一次定死（写代码时不再随手定）。事实记录（走查）在 flow.md，本文件是设计稿。

## 1. 节点图

```
[框架自动: 检测窗口+进游戏 (need_check_game_win)]
① 导航段
  n1 到达兑换商店      OpenExchangeShop()                       (起点)
② 兑换段
  n2 按优先级逐项兑换   for goods in 开启项(按 priority 升序, 同值按固定序):
                         r = ExchangeShopBuyGoods(goods, count=None).execute()
                         └─ 按 §3 分支; 非预期失败 → 记下失败语境, 转向 n4
③ 返回段(正常路径)
  n3 返回大世界        BackToNormalWorldPlus()
④ 失败收尾
  n4 尽力返回大世界     BackToNormalWorldPlus()(自身失败不覆盖原始失败语境) → round_fail(原始语境)
```

- n1 失败 → 直接转向 n4（后续无从谈起，中止档）。
- n2 全部项处理完毕（无论换没换到东西）→ n3。
- **非预期失败也走 n4 返回大世界**——app 失败结束时框架不做任何画面收尾（Application.after_operation_done 只更新记录与通知），一条龙会直接跑下一个 app；留在商店页会把异常起点传染给链上其他 app（AGENTS.md §4：app 之间在大世界干净交接）。BackToNormalWorldPlus 失败不掩盖原始失败信息。
- **边界声明**：节点内未捕获异常（如配置值构造 op 抛 ValueError）由框架捕异常转 FAIL 直接收尾，不经 n4——该路径无画面收尾，依赖下一 app 入口兜底，接受该边界。
- app 类继承 `SrApplication`；factory `create_application` 注入 config 与 run_record（构造参数），app 不经 SrContext 属性读配置（§4）。

## 2. 兑换项与排序

| 商品标识符 | 月限 | 默认开关 | 默认优先级 |
|---|---|---|---|
| `special_pass` | 5 | 开 | 10 |
| `pass` | 动态（本期 2/5） | 开 | 20 |
| `tracks_of_destiny` | 1 | 开 | 30 |

- 排序 = priority 升序；同值按固定序兜底 专票 > 通票 > 足迹（用户裁定 8）。
- 数量一律 `count=None` 拉满（用户裁定 2：数量不可配）。
- 循环遇 `INSUFFICIENT_MATERIALS` 即终止循环，其后未尝试项记 `SKIP_BALANCE` 放弃（用户裁定 1：换到换不动为止、后面的放弃）。优先级高的项单价未必更低，先高优先级可能少换总张数——这是裁定 1 的既定语义（优先级=用户意愿排序），不做 cheapest-first 优化。
- 已知限制与主形态：滑条按余额截断是在档主形态（拉满买到余额允许的张数，PURCHASED bought=实际数，继续下一项——见 design.md §2.4 与 docs/game/screens/store.md §8）；「兑换材料不足」横条 → 该项 0 张并终止循环（INSUFFICIENT_MATERIALS），该横条形态本期无法实测（余烬余额 41562 构造不出），作备选分支保留。

## 3. 失败处理语义（必须设计档，逐状态显式处理）

### 3.1 分支总表（C2 契约的权威表：状态 → 代码出口 → app 动作）

| `data.fail_status` | 购买 op 内的触发出口 | 语义 | app 动作 |
|---|---|---|---|
| `SOLD_OUT` | 列表角标「已售罄」拦截；弹窗状态横条「已售罄」（两出口合并） | 本期限额度已尽 | 该项记 skip_note；继续下一项（预期内——本月已换过的重复运行就是全员此形态） |
| `CARD_UNAVAILABLE` | 列表角标「已达上限」「未解锁」拦截 | 卡面不可购（v1 三件套不会出现，通用性预留） | 同 SOLD_OUT 分支处理 |
| `NOT_FOUND` | 列表扫到底未命中；首屏未命中（scroll_search=False）；滚动次数保险上限 | 商品不在列表（下架/版本变动） | 该项记 skip_note（`goods:NOT_FOUND` 即告警语义，可见性见 §3.4）；继续下一项（商品不在售 ≠ 失败，阻塞重跑无意义） |
| `INSUFFICIENT_MATERIALS` | 弹窗状态横条「兑换材料不足」（点取消）；余额预判失败（仅 count 模式，本 app 不会触达）；月限超限预判（仅 count 模式，本 app 不会触达） | 余额/额度不够换满 | **终止循环**，其后未尝试项记 `SKIP_BALANCE`；按正常完成收尾 |
| （无 fail_status 的失败） | 其余全部失败出口（画面异常 / 确认未生效——confirm 连等封顶后转 FAIL / 余额终验不符 / 画面未回商店页等） | 非预期失败 | **中止**：转向 n4 尽力返回大世界后 round_fail，运行记录标失败 |

- 单项真实失败 = 中止（用户裁定 5）；「售罄/未找到/余额不足」是兑换生意的预期内结果而非失败——区分依据 = 该状态是否意味「这次运行没达成应有状态」。
- 载体约定：购买 op 的 `status` 保持人读诊断句（框架日志纪律）；机器可读语义只进 `data['fail_status']`，app 分支只认 data 字段，不对 status 文本做子串匹配；fail 出口的 `data.goods` = **英文标识符**（与 PURCHASED 出口同口径，skip_note 随此口径）。

### 3.2 终态与运行记录标记（周期标记裁定，C3 权威表）

运行记录周期 = **DAILY**（取舍依据 design.md §2.4）：当日完成即标 done，当日不再跑；次日 dt 翻转自动重跑。额度刷新无论发生在月内（版本口径）还是月初（月历口径），最迟次日被补上。

| 场景 | run_status | 标「当日已完成」？ | 依据 |
|---|---|---|---|
| 全部开启项处理完毕（含全部售罄跳过、NOT_FOUND 跳过、零购买、全部关闭） | SUCCESS | **标** | 预期内的无事可做照常标完成，当日防重复空跑；次日刷新自然重跑（判例：预期内无事可做照常标） |
| 部分换到 + 部分售罄/放弃 | SUCCESS | **标** | 当日该做的都做了（额度尽靠后续每日重跑自然补，售罄拦截不重买） |
| 循环因余额不足提前终止 | SUCCESS | **标** | 裁定 1「换到换不动为止」= 达成用户意图的终态，非失败；次日重跑时余额若恢复（如领了余烬）会继续换 |
| 非预期失败中止 | FAIL | **不标** | 「该做没做成」，一条龙次日重跑补做（判例之「该做没做成」） |

### 3.3 运行记录业务字段（一次落地，不留空壳）

`MonthlyEmbersExchangeRunRecord(AppRunRecord)`，period=DAILY：

| 字段 | 类型 | 语义 |
|---|---|---|
| `bought_pass` / `bought_special_pass` / `bought_tracks_of_destiny` | int | 本次各商品实际购买数量（PURCHASED data.bought 写入） |
| `skip_note` | str | 跳过与放弃明细，格式 `goods:STATUS` 分号连接（tried 项用 §3.1 状态值；未尝试的放弃项用 `goods:SKIP_BALANCE`），空 = 无跳过 |
| `balance_left` | int \| None | 最后一项兑换后余额（尽力留痕，读不出 = None） |

- **写入时机**：业务字段随循环逐项即时写入（PURCHASED / 跳过即写，非收尾统一写）——非预期失败中止时保留已写部分，失败日的已购数量与余额不丢失，便于人工对账。
- **构造注入**：run_record 的 `game_refresh_hour_offset` 由 factory 从 `GameAccountConfig(instance_idx)` 注入（同 trick_snack 样板）——当日翻转边界与游戏刷新时刻对齐，不用缺省 0（日历午夜）。
- `reset_record` 覆写：状态复位 + 上述字段清零（父类只复位状态，业务字段各 app 自清——父类注释约定）；周期重置由框架按 dt 判定触发。

### 3.4 NOT_FOUND 告警的可见通道

NOT_FOUND（商品消失/关键词失配）是唯一「每天 SUCCESS 却在漏东西」的形态，告警走两道：
1. n2 节点挂 `@node_notify(when=NotifyTiming.CURRENT_DONE, detail=True)`，终轮 status 写人读摘要（含 skip_note 全文）——用户通知配置开启细节模式时，结束通知带该状态行；
2. 运行记录 `skip_note` 持久留痕（GUI 运行卡片不展示业务字段，查 yml：`config/<idx>/app_run_record/monthly_embers_exchange.yml`）。

接受「细节通知关闭且未查记录时告警不可见」的边界；不做专用推送机制（v2 若实发生活失配再升级）。

## 4. config 处理方式

`MonthlyEmbersExchangeConfig(ApplicationConfig)`（app_id=monthly_embers_exchange，per-instance+group 落盘 `config/<idx>/<group>/monthly_embers_exchange.yml`）：

| 字段 | 类型/默认 | 用途 |
|---|---|---|
| `special_pass_enabled` / `pass_enabled` / `tracks_of_destiny_enabled` | bool / True | 单项开关；关闭项不进循环 |
| `special_pass_priority` / `pass_priority` / `tracks_of_destiny_priority` | int / 10, 20, 30 | 优先级，升序兑换；同值按 §2 固定序兜底 |

- **读取通道**：factory `create_config` 实现（返回上述类实例）；app 构造注入（§1）；GUI 与 MCP 经 `ctx.run_context.get_config(...)` 取**同一缓存实例**（写立即生效）。GUI 绑定另需 config 类提供 `*_adapter` 属性（config-and-gui 生态，GUI 阶段落地）。
- **MCP 配置工具通道**：`src/sr_od/backend/config_router.py` 登记 RouterEntry——`get_config` 走 `ctx.run_context.get_config`（写穿缓存）；`field_schema` 声明 6 个字段（bool×3 + int×3，带语义 desc）；`supported_ops=('get','set','describe')`，无列表项（add/delete/update 不支持）。未登记则 MCP 工具对该 app_id 一律不可达（现网行为，实测机制）。
- 配置读取点：n2 循环开始时一次性读入并排序；全部关闭场景 = 预期内无事可做 → 照常标完成（§3.2 行 1）。

## 5. 时序预算

常规跑（有商品可换）：导航 ~15s + 每项兑换 20-40s + 返回 ~10s ≈ 1-2 分钟（flow.md §4.3 走查口径）。全售罄形态每日空跑：导航 ~15s + 逐项回顶扫描找卡（售罄灰卡滞留列表底，逐项为成本最高形态）×3 + 返回 ~10s ≈ 1.5-2.5 分钟（§3.2 取舍的已知代价）。
