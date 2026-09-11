# ADR-0562: 外循环 0n 开商店分支处理改交商店访问路径——收店决策权归策略器(CloseShop 终结)

## 1. 背景与问题

外循环 0n 分支(备战-开商店子态,commit 68dee747 批落地)的处理是**路由层硬编码**:识别商店态后直接点「按钮-收起」收店 → 交回外循环重判(分键 `branch_shop_open_collapse`)。

该处理违反 ADR-0517 已落码的终结语义(ADR-0518 实施批):「关店」本来就是商店画面 op 的一等终结动作(CloseShop,决策 4/5),「收不收、买不买」应由策略器基于期望态决定,不是外循环写死。且硬收起造成无谓往返:收起 → 备战环 → 想买 → 重新开店,每轮多两次画面切换。

## 2. 决策

0n 分支命中后**转交商店访问路径**:委托 `CwScreenPrep.visit_open_shop`(新增公开方法,= 原 `_open_shop_phase` 尾段编排的提取)——入口观察现读牌面重建期望态 → 策略器逐动作决策(买/卖/升/刷)→ CloseShop 终结收店 → finalize_buy_phase → 节点探针。路由层零收店点击。

### 接线方式裁定(任务书选项 b:转交编排入口)

- 选项 a(0n 分支直接构造 run_buy_waves + close_shop + finalize)会把「尾段编排」复制进 cw_loop,形成第二个编排源,漂移风险;且节点探针等宿主方法在 loop 上不存在。
- 选项 b(转交 CwScreenPrep)保持 shop_visit.md 声明的编排归属(cw_screen_prep 持有商店访问编排),0n 分支只做委托,实现面最小。

## 3. 关键语义声明

- **店已开入口幂等**:不调 open_shop——店已开由 0n 三 id_mark 锚确认,连点都不发(比依赖 open_shop 幂等性更进一步)。入口观察读的是已开的店,与「RefreshShop 后 break 交回段循环(店不关)、段循环收工无条件 close_shop」的终结语义完全兼容。
- **hp 三件组来源**:缺省 `(None, False, False)`——0n 入口无备战观察(商店开态 HP 区不可读,读互斥),`session.last_state` 可能是外循环上一轮的陈旧值,不可作决策依据 → `_apply_hp` 不覆盖,保留 read_game_state 产物,血线消费门 fail-closed 拒收。显式开店路径经参数传入开店前备战观察的 hp。
- **入口观察重建 last_state**:进入时陈旧的 `session.last_state` 由入口观察(唯一决策读屏点,ADR-0517 决策 8)归零。
- **深度防御不变**:达标臂浮层扫描(readiness_overlay_hold)与 CwScreenPrep 环入口 `_try_collapse_open_shop` 守卫保留——0n 处理不再收店后,环入口守卫仍兜「漏帧进备战环」。

## 4. 遥测分键

`branch_shop_open_collapse` 拆分:
- `branch_shop_open_hit` = 0n 分支命中(原命中语义保留,改名去掉「collapse」误导);
- `branch_shop_open_visit_ok` / `branch_shop_open_visit_fail` = 商店访问结果。

## 5. Considered Options

| 方案 | 裁决 |
|---|---|
| a. 0n 分支内联 run_buy_waves→close→finalize | 否:编排双源 + 宿主方法缺失 |
| b. 转交 CwScreenPrep.visit_open_shop(提取共用尾段) | **采纳**:编排单一源,显式开店与 0n 共用 |
| 维持硬编码收起 | 否:违反 ADR-0517 终结语义 + 无谓往返 |

## 6. 影响

- `operations/cw_loop.py`:0n 分支体改委托(决策帧挂点行保留)。
- `operations/cw_screen/cw_screen_prep.py`:新增 `visit_open_shop`;`_open_shop_phase` 尾段改委托(编排单一源)。
- 测试:行为锁重推(收起点击+分键 → 商店访问被调用+关店终结);新增策略路径锁(`test_cw_shop_open_visit.py`)。
