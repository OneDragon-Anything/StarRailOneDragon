# 商店开画面(shop · 货币战争-备战-开商店)

> 代码 = `operations/cw_screen/cw_screen_prep.py::_open_shop_phase`(流程层商店编排)+ `operations/cw_screen/cw_screen_buy_cards.py::run_buy_waves`(商店单动作循环)+ `probe_node_type`(关店后节点行探针,商店域)。职责:商店打开态的一次访问编排——单动作决策循环驱动 `decide_shop_action`、终结动作离店、收尾。路径根 = `src/sr_od/application/currency_war/`。
> **决策判据(买什么/卖什么/刷不刷/升不升)一律不在本篇**——本篇只管「循环怎么转、期望态怎么推进、何时离店」;判据见 [../../strategy-docs/11_shop_decisions.md](../strategy-docs/11_shop_decisions.md)。

## 1. 分发判定

- 外循环分支 0n(店已开态):开商店画面档**三 id_mark** 同帧——「备战标识-购买经验」∧「按钮-收起」∧「标识-备战阶段」(`_shop_open_anchors_hit`;与干净备战的「按钮-出战」天然互斥)。分发 = 阶段一身份行(三 id_mark;历史穿透命中曾把部署/出战点击打在浮层上,§2.2)。
- 显式开店:备战访问内 `OpenShop` 动作 → `visit_open_shop`(本篇 §2 编排单一源)。受限访问(`restricted_spend=True`)在 `_act_execute_default` 截流走仲裁单元,不经本篇编排。
- 发射帧仲裁受限访问:策略前置发射位产受限访问意图(armed ∧ 金超息线)→ 备战访问 op 执行仲裁单元(spend_gate 仲裁;带内段 fail-closed 不开店)。
- 建档 = `assets/game_data/screen_info/currency_war_battle_prep_shop_open.yml`(商店牌-1..5 / 按钮-刷新 / 备战标识-购买经验 / 按钮-收起 等 area)。

## 2. 画面形态声明

**决策循环形态**。决策入口 = 契约 `decide_shop_action`(`strategies/impl/mandate_v1/shop.py`;**全函数**:f(期望态) → 恰一个动作,「无动作可做」= CloseShop 恒可用终结;观察帧缺失即抛错)。段循环外层 `for _ in range(MAX_REFRESH + 1)`(刷新终结 = 下一段开始),内层决策循环 `while True`(防御帧帽 `SHOP_SEGMENT_ACTION_CAP=16`,超帽 RuntimeError 响亮暴露)。生产执行侧逐帧调用;sim 引擎/回放经 `decide_shop_screen` 驱动器消费(非契约成员)。

## 3. 观察面

**段顶入口观察** = 唯一决策读屏点 = 对账边界(`operations/cw_screen/cw_screen_buy_cards.py` 段顶):

```
read_game_state(phase=PHASE_PREP_SHOP_OPEN) 全量现读,漏斗容器直写(obs 族渠道签名;
  产出 GameStateReadReceipt 回执)
→ 店开入口防抖(shop 域未入容器时有界重读 3×0.8s;仍缺 = 交决策前置门)
→ 首段帧代次标注 full(shop_frame_class;续段 none 保持首段值)
→ node_type 台账回填(键 = 本帧 plane/round;查不到保持 None fail-open;
  回填 = write_logic 台账权威值覆盖,下一备战帧真读观察赢)
→ gold==0 救援(读 0 时重读 4 帧取首个 >0;结果留证,救回值经观察渠道覆盖写)
→ 店开帧预算披露覆写(gold 真值入链,overflow/budget 三预算字段)
→ 播种期对账 guard_expected_vs_tracked(stage='seed';先对账分叉归因「播种/入口账」,
  逻辑态直写后分叉才归「逻辑态模型」)
```

观察写入 = ①观察态上报进 GameState 的观察边界;段内不比对、不重建(统一规范 = [op-layer.md](op-layer.md) §1.3;关键信息未观察由字段态值前置拦截,见 §5 全 unknown 窗)。

## 4. 动作面

```
while True(零读屏):
  action = strategy.decide_shop_action(session, config)   # 恰一个动作,全函数
  │    异常 → 留证后上抛
  ├─ CloseShop 终结 → break(关店点击由编排壳 CwOpCloseShop 承担)
  ├─ RefreshShop ∧ ledger.total_refresh ≥ MAX_REFRESH → 硬墙跳过:
  │    plan_truncated=True + refresh_skipped='max_cap'(可见化不停)→ break
  ├─ spend_gate(发射帧仲裁,缺省 None):拒 = 本动作不执行 + 本访问收工
  ├─ 守卫断言 guard_proposal_vs_expected(提案对象在期望态存在且未被消费,
  │    炸出 = 策略器算术 bug;防 bug 路栏,非控制流分支)
  ├─ 动作 op execute(注册表分发;机械发出,零成败判定):
  │    BuyCard:槽号定位(payload 定长槽阵列,数组下标+1 = 物理槽;身份同一性优先,
  │            退化 (name,star))→ 买前裁片纯留证 → 点牌位 → 动画窗 → 发出即记账
  │            (total_buy/spend_executed/bought_names)→ 满栏自动多买补差(k 单一源)
  │    LevelUp:点购买经验单击 → 动画等待(clicks 序列 = 动作内部步骤,决策循环逐帧重组)
  │    RefreshShop(段终结):刷前现读两口径 → 刷前刷新钮真值读(三态+免费剩余次数)→
  │            点刷新 → 牌行两帧指纹一致门(≤2s,超时回退静置)→ 发出即记账(刷价 = 基价常量);
  │            牌名集对比仅作安灯豁免判定输入 + 遥测(refresh_board_changed);
  │            免费刷新 proc 留证(牌面已变∧金未扣 → flag 不停机)
  │    SellBench(能力面;注册行已更替备战域):拖拽机械单发 → 发出即记账
  ├─ 落地门 apply_action_outcome(调用环单一源):execute 无返回(发出即职责完成,零判效);
  │    门保留为结构防线——未落地 ⇒ 两侧都不动;期望态推进 = op 自上报单点(终结跳写判断随 op 自辖)
  ├─ op 自上报(容器规则通道,纯计算零读屏):report_action_buy_card_param 单点
  │    (简单落位与合成升星腿内聚,买前快照三件组基点函数内第一时间取)直写容器
  │    → guard_expected_vs_tracked 双账断言(满栏合成买双账同构豁免)
  段尾:CloseShop 终结不入行;刷新 = 段终结后本段即 break ⇒ 每刷独立成行
段间判定:did_refresh=False → break(本段无刷新/硬墙 → 收工)
```

逐动作规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)(buy-card / refresh-shop / close-shop / level-up 各篇)。

## 5. 终结与交回

| 条件 | 语义 |
|---|---|
| **CloseShop 终结** | 策略器主动选关店(全函数「无动作可做」的表达)→ 本段收工。唯一常规离店条件 |
| 全 unknown 窗 | 牌面含 unknown 槽(整帧 OCR/SIFT 失读窗)→ **入口观察即停**(见下行;决策入口前置门仅返回 CloseShop 为纵深第二线) |
| 刷新硬墙 | visit 级 `total_refresh` ≥ MAX_REFRESH → 终结集降级仅关店(本轮当未刷新收工) |
| 未识别卡停机 | 每波入口观察回执落地即判:读链终判(内部易误判重观察后)仍含 unknown 槽(empty=确证空位不计)→ `stop_running(save_screenshot=True)` 框架截图留证 + round_fail——决策/购买不见残缺牌面(未识别不能降级带病跑;2026-09-16 迁移+框架化,防抖探针/flag 退役;细则 = [../flow/guards.md](../flow/guards.md) §3) |
| 循环异常 | 上抛 → 编排层单元 aborted 关账,店不收(交上层重新识别) |

`visit_open_shop` = 商店访问尾段(run_buy_waves → CwOpCloseShop → 节点探针)的**编排单一源**,显式开店与 0n 转交两路径共用;失败路径不收店(店留着交上层重新识别)。访问回执 detail = 固定完成事实串(无动作计数;该行不计入哨兵实质推进——零动作空转与真买牌在行形上不可分,推进可见化归 state/round 变化、复合动作成功、采晶矿成功等信号)。

收尾观测 `probe_node_type`(住 `cw_screen_buy_cards.py`,商店域):关店后 clean 备战帧读节点行序列(read_node_sequence)→ log + 未识别图标采集(版本前哨)+ 槽序表(`plane_node_table`)与台账按位合并写(写点③;挂点 = 商店访问尾,非商店轮不触发,覆盖以此为界)。纯观测,失败不阻塞收尾,无决策消费。

## 6. 状态上报面

- 动作 → 上报函数:op 自上报 `kernel/cw_action_report/<snake>.py::report_action_<snake>_param` 单点(买牌 = `report_action_buy_card_param`,快照与合成升星腿内聚,升星判据单一源 = `kernel/cw_game_state.py::detect_merge_upgrade`);逐动作规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)。
- 刷新计数域(refresh_counters)与 prev_node_spent 由上报函数腿直写(仅逻辑渠道)。

## 7. 子态与 overlay

- 商店卡牌详情弹窗:0t 分支(`CwScreenShopCardDetailPopup`,点 X 验消失,**绝不点购买**——买不买归商店域)。
- 商店刷新概率表弹窗:0e2 分支(点 × 关);概率条直读进 `refresh_probs` = 观察非动作。
- 暗色衬底弹窗遮蔽底层全部锚时,外循环 0 系弹窗族分支先行分流后才可能落到本画面分支。

## 8. 守卫与防线

- 未识别卡停机(§5,入口观察即停;用户裁定:未识别不能降级带病跑,识别不到就是 bug)。
- visit 级刷新硬墙 MAX_REFRESH(防「终结→重进→再刷新」外循环无进展);shop_visit_idle_gold 计数键(visit 语义)。
- EV 买面席位门(满栏帧不提案,拒因分键 shop_ev_bench_wait;满栏合成买面 m2_merge_completion 提案不在门辖)。
- 免费刷新 proc 留证:flag 不停机(免费不是失败)。

## 9. 遥测与锁面

- journal op 名 = 「商店访问」(0n 转交与显式开店同口);计数键 shop_visit_idle_gold / branch_shop_open_*;刷新遥测字段 refresh_board_changed + free_refresh_proc flag;投放分键 plan_visit_action_cap / shop_ev_bench_wait。
- 测试锁:商店投影逻辑锁(test_cw_shop_projection_logic)、R2 预算门对拍、P56 买面锁等,锁面 = `sr-od-test/test/sr_od/application/currency_war/`。
- game 侧知识:经济机制(刷新/息/锁商店) = [../../../../game/currency_war/research/economy.md](../../../../../game/currency_war/research/economy.md);合成机制 = [../../../../game/currency_war/research/merge_mechanics.md](../../../../../game/currency_war/research/merge_mechanics.md)。
