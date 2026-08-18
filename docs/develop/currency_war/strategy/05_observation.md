# 05 观测、对账与遥测

> 「读画面→GameState→对账→反馈→落盘」的观测闭环。本篇:obs 模块家族 / cw_reconcile / cw_performance / cw_telemetry / 日志格式。核心哲学:观测驱动非预测驱动(README §哲学)。

## 1. 观测模块家族(按屏分工)

| 模块 | 屏/对象 | 产出 |
|---|---|---|
| `cw_observation` | 备战屏 | `read_game_state` → GameState(gold/hp/level/board/shop/bench/deployed…) |
| `cw_obs_core` | 共享基础设施 | screen_info 区域读取 + OCR helper |
| `cw_identity_obs` | 备战屏视觉身份(SIFT,非 OCR) | bench/deployed 角色身份 |
| `cw_node_obs` | 节点选项 overlay | EncounterOption/SupplyOption/MegastarOption/PartnerOption |
| `cw_settlement_obs` | 结算屏 | 战后小队 HP(观测回路输入;失败屏 hp=0 conf=1.0) |
| `cw_briefing_obs` | 开局简报屏 | 敌人词缀 + 位面首领 + 基础敌难 |
| `cw_node_reader` | 备战顶部节点行(纯 CV) | 节点序列类型(奖励/战斗/遭遇/补给/巨星/boss…) |
| `cw_observe` | 可观测框架 | 统一日志 + 截图 |

**读取互斥**:gold 只在 shop 开态、HP 只在关态可读——由 EnsureShopOpen/Closed 动作显式管理,框架校验读取前置态。设计原则:签名 + 失败语义(字段 OCR 失败 → None/上回合值 + confidence=0,不抛错)+ sanity bounds(越界字段本回合作废防级联)。

## 2. cw_reconcile:对账公共层

tracking(内存 dead-reckoning)vs 读到的真值,多层校准(L0 内存跟踪 → L1 全图 OCR 对比 → L2 不一致兜底递进[裁剪再识/点击探查/定向重读] → L3 递进到底仍不一致 = 上游出错信号,保守恢复不硬猜)。环入口对账一步;单笔动作后验证互补回合总账。

## 3. cw_performance:观测反馈层

- **RoundOutcome(双侧观测)**:自身侧(hp_after 差分 + 置信度)+ 敌方侧(击杀/伤害,可观测时)+ comp_tag + intentional_fold 标记。
- **PerformanceTracker**:`recent_hp_loss_trend` = **归一化**掉血趋势(hp_delta / expected_drop(node_type),全部样本进同一条 trend——归一化而非按节点类型完全划分:消除「打 boss 掉得多=我弱」偏差又不丢样本/不震荡);intentional_fold 排除(防故意输污染);comp_tag 过滤(pivot 后旧 comp 降权);低置信不进 trend;冷启动(差分样本不足)→ None,调用方退静态先验。
- **comp_viability**(评已 commit 阵容):先验(成型度/装备/机制)× 先验权重 + 观测 × obs_weight(随观测轮次上升);评 candidate 用纯先验 comp_prior(双签名,02 §2)。
- **死局检测**:HP 低 + trend 高 + 下节点锁不住血三门。

## 4. cw_telemetry:决策迹采集

三路 jsonl(`.debug/temp/currency_war/replay/`):**outcomes**(每节点结算)、**decisions**(每决策点 state 快照 + 候选分 + 选择 + 理由;live 扩容字段:active_strategies / dp_posture 影子 / ledger_fingerprint / megastar·encounter·supply pick)、**runs**(局摘要,含免费窗口登记字段)。默认 `enabled=False` 门控,config `debug_telemetry` 一开全收。外生事件(节点转换/弹窗)与执行失败事件各自落盘(能力画像/预案触发频率语料)。

**回放语义**:replay = 把录制的 state 喂给策略比对决策——**回归测试与调试工具,不是胜率裁判**(obs 序列是当时策略产生的,换策略后游戏演化路径本就不同;真实 A/B 必须实机,07 §replay)。

## 5. 离线分析工具(消费 telemetry)

- `cw_weight_search`:CEM 权重搜索(防退化三件套,ADR-0194);
- `cw_divergence_stats`:影子 DP 姿态 vs 生产姿态分歧频率(人机问询触发门数据源);
- `cw_plan_replay_audit`:离线重放 plan() 比对 live 决策(对拍器)。

## 6. 日志格式标准(可检索;单一源)

CW 实机运行/识别加结构化日志。两种前缀区分普通 vs 需关注:

- `[cw][op][step][target] fields` —— **普通**(常规识别结果 / 流程)
- `[cw!][op][step][target] fields` —— **需关注**(漏检 / 顺序异常 / UNKNOWN 未建档画面 / 异常状态)

字段:`[op]` 模块(read_equipped/read_equips/deploy/equip_all/recognize 等)/ `[step]` 节点 / `[target]` 对象(slot=前排-1 / screen=备战 / char=飞霄);状态标记 `MISS=[名(val)]`(漏检)/ `UNKNOWN screen=`(未建档)/ `FOUND=`(找到);`| shot=<名>` 配对截图(定位画面)。

检索:漏检 `grep "\[cw!\].*MISS"` / 未建档画面 `grep "\[cw!\].*UNKNOWN"` / 全 CW `grep "\[cw\]"`。

落点:`read_equipped` MISS(装备 below 漏检)/ `read_equips` 顺序异常(owned 栏识别到后面但前面漏;布局:第一行独立[冶金炉多了左堆],下面从上到下、从右到左,跳格=前面漏检)/ `recognize` UNKNOWN(未建档画面)。logger 用 `log_utils.log`(框架默认);纯函数加可选 `logger=None` 参数(测试/离线不记)。
