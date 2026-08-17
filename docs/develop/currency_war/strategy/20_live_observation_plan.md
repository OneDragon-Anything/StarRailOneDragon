# 20. Live 观测规划:待实机提案的遥测/钩子需求(2026-08-17,用户指令)

> 目的:开 live 测试前,把剩余需实机观察的提案(12/14/22/27/39/41/44)所需数据
> **全部前置为 hook/遥测**,一次实机窗口收齐。原则:
> 1. **观测优先于干预**——本轮只加采集,不改决策行为(切流另有批次);
> 2. **31 号 journal 词表对齐**——新增事件族按 cw_reentry 四族语义落 telemetry,
>    为 journal 常开(31 号执行侧)预铺;
> 3. **最新策略实现的对齐**——巨星 comp 偏好/遭遇三态+奖励/钻双通道/效果台账
>   (v2 字段)/DP 定制解这些新决策,其输入输出必须可回放。

## 需求矩阵(提案 × 需要的观测)

| 提案 | 需要什么 | 观测形态 | 落点 |
|---|---|---|---|
| **27 能力画像** | prep_director 的 `_fail_counts`/`_blocked`/bail 原因**落盘**(动作族×画面×原因码);跨局聚合 | 新事件路 `exec_events.jsonl` | prep_director 钩子 |
| **14 反事实复盘** | ex-ante 信念条件分支:决策点的候选分(含落选)、当回合观测、动作实际执行结果 | decisions.jsonl **已记 candidate_scores**;补 actions_executed vs planned 差异 | battle_loop |
| **22 预案层** | 高利害条件的实际触发频率(bench 满/hp 阈值/difficulty spike) | 外生事件族 `exogenous.jsonl` | battle_loop 节点分发处 |
| **39 主动实验** | 免费窗口清单(必死局/免费局判定)+ 当前每窗口已采信号 | 窗口登记(run summary 扩字段) | run 终 |
| **41 示范对齐** | 用户接管时段的画面+动作反演 | **人在场协议,本轮不自动采**(隐私/在场判定未建)——留接口 | — |
| **44 战斗观测** | 战斗内截帧(周期性,非交互死时间) | `battle_frames/` 截图序列(采样率低,5s/帧) | battle_loop 战斗等待处 |
| **12 人机问询** | 决策分歧点(影子 DP vs 生产姿态差)频率 | 复用 shadow diff 日志(cw_shadow_ab 已有,加落盘开关) | 每回合 |
| **效果台账/DP 定制解(本轮新)** | 持卡组合×实际姿态查询(验证台账→DP 链) | decisions.jsonl 扩字段:active_strategies + dp_posture_tag + ledger_fingerprint | battle_loop 决策点 |
| **巨星 P2/遭遇 P9/钻 P8(本轮新)** | 新决策的实际选择与理由 | 决策点各记 pick+reason(已有 reason 字符串,补结构化) | 各 handler |

## 落地(live 批次)

### A. 遥测扩容(纯增量,enabled 门控不变)
1. `exec_events.jsonl`(27 号):动作族执行失败/阻塞事件,含 fail_reason 分类;
2. `exogenous.jsonl`(22/31 号):节点类型转换/弹窗/干预/boss 简报事件;
3. `decisions.jsonl` 扩字段(14/新策略):active_strategies、dp_posture(影子查询)、
   ledger_fingerprint、megastar_pick、encounter_pick(含 rewards 与三态打分)、
   supply_pick(含 has_diamond 通道来源);
4. `battle_frames/`(44 号):战斗内周期截帧(低采样);
5. run summary 扩(39 号):death_window(必死局判定字段,供免费窗口登记)。

### B. 默认开启策略
生产默认 `enabled=False` 不变(框架纪律);**live 测试期**由 config 开
`debug_telemetry`(已有配置位)——开一次开关,五路全收。

### C. 钩子(采集型,用完即删类不适用——这批是常驻观测,非临时)
- prep_director bail/fail 落 exec_events(27 号数据源,正在蒸发的数据);
- battle_loop 节点分发落 exogenous(22 号触发频率);
- 战斗等待循环低频截帧(44 号);
- 影子 DP diff 落盘开关(12 号分歧频率)。
