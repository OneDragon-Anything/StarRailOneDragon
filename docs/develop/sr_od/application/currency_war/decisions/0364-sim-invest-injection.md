# ADR-0364: sim 投资策略/环境语料注入

- 状态:已采纳(2026-08-29)
- 关联:ADR-0338(直通线资格)/ ADR-0357(P1 配方锁)/ ADR-0362(sim P2 段)/ W161 判读报告

## 背景与问题

W161 实证:sim(cw_sim)全文不建模 `active_strategies`/`active_env`——实机这两者由
`handle_invest_strategy`/`handle_invest_env` 局中采集进 session,消费面 =
意向层①资格通道(`_direct_line_qualified`,ADR-0338)、经济聚合
(`economy_effect_of` 链)、cw_events 打分。W145(ADR-0357)后 P1 锁 comp 仅剩
①资格通道 → sim 缺输入 = 通道永不点火 → P1 永不锁 comp → V_D 目标恒空
(sim 757/757 帧死在「①目标空」)→ **sim 一切含 D 的 P1 结论零外推力**。

## 决策

1. **注入形态 = 案 a(按 plaza 实选频次分布的确定性随机采样)× 案 c
   (参数化,默认关)**,弃案 b(固定剧本集):见「Considered Options」。
2. 新模块 `cw_sim_invest.py`(注入数据面单一源):
   - `SimInvestProfile(active_env, picks)`:注入剧本;`sample_invest_profile(seed)`
     确定性采样(独立 rng 流 `random.Random('w162-invest-<seed>')`,不触碰
     sim 主 rng → 默认关 = 主路径逐位零漂移);
   - 名字分布 = `cw_plaza_comps.PLAZA_CARRY_CLUSTERS` 的 `augs`(策略实选
     89 名)/`portals`(环境偏好 44 名)频次跨聚类求和;全角冒号归一
     (plaza「骇客专家：银狼」→注册表「骇客专家:银狼」),注册表外名丢弃
     并经 `freq_dropped_names()` 披露(当前 0 丢弃);
   - 选卡日程 `SIM_STRATEGY_PICK_SCHEDULE` = 实机 replay 真值
     (decisions.jsonl 63 局):(1,1,1.0) 开局 / (1,3,0.79) P1 r3 主选卡 /
     (1,9,0.08) / (2,2,0.40) / (2,6,0.02)。**不新采**。
3. `simulate_p1(..., invest=False|True|SimInvestProfile)`,`simulate_p1_batch`
   透传 + invest headline 三联(`invest_env_rate`/`avg_invest_strategies`/
   `invest_p1_lock_rate`/`avg_p1_locked_rounds`)。
4. **注入语义与实机 handler 对齐**(单一源参照 = handler 写点):
   - 环境:开局写 `session.active_env`(handle_invest_env L197);
   - 策略:按日程轮 append `session.active_strategies`(去重防重选,
     handle_invest_strategy L200-202);state 镜像(生产由 cw_observation
     每帧同步,sim 在注入点直写,等价语义);
   - 选卡时点 = 轮收入结算后、决策前(实机 overlay 出现在备战期)。
5. **经济聚合生效子集**(economy_effect_of 链在 sim 内的接线):
   - `interest_cap_override`(收入行利息帽)、`gold_per_node`(收入行
     `invest` 键)、`instant_gold`(选卡时点入账)、`free_refresh_per_node`
     (RefreshShop 刷价 = 额度内 0,cw_economy._refresh_cost 同语义)。
   - 其余字段不建模(战力类走策略层评分本就生效;事件类/触发类效果
     sim 无对应机制面)。
6. 观测:`SimResult.invest_env`/`invest_strategies`/`p1_locked_rounds`
   (P1 段意向 locked 轮数——①通道激活直证,off 口径恒 0)。
7. **锚**:默认关 → 既有 ANCHOR_REGISTRY_N300(off 口径)不变;
   新增并行锚 ANCHOR_REGISTRY_N300_INVEST(invest-on 口径,注释链
   「策略环境注入换锚」)。invest 批与 off 批的 drift 表进 W162 报告。

## Considered Options

| 选项 | 结论 | 理由 |
|---|---|---|
| a) sim 全局随机采样(按 plaza 频次分布) | **采纳** | 实机分布代表性最佳(784 篇高难帖频次);同 seed 确定性 → A/B 同 seed 同注入 = 配对可比 |
| b) 固定剧本集(每 seed 确定性抽 3-5 套典型组合) | 弃选 | 剧本集是手选锚,代表性靠人工维护;覆盖策略/环境组合空间 ~89×44 需要的套数远超 3-5,少量剧本会把结论锚在抽样点上;且与 a 同为确定性,a 的频次加权天然给全空间 |
| c) 参数化注入(config 开关+列表,默认关) | **采纳(与 a 复合)** | 默认关保零漂移回归门;`SimInvestProfile` 显式传 = c 的列表形态(测试/A-B 固定臂),True = a 的采样形态 |
| (弃)sim 内真跑 decide_invest 选卡 | 不采 | sim 无 overlay 画面/3 选 1 候选生成机制;造候选分布 = 又一层无校准语料,频次表已是更好的实证分布 |

## 影响

- 策略层零改动(本批 = sim 输入面批);W157 的 P2 段基建/plane 键化不动
  (注入是 P1/P2 共用输入,`_seg_plane` 键对两段同辖)。
- 含 D 的 P1 侧 sim 结论自此批起应以 invest=True 口径为基准;
  off 口径(默认)仍用于零漂移回归与历史对照。
- 已知边界:①注入策略 = plaza 频次分布(玩家实选分布),非游戏内
  3 选 1 候选的均匀先验——分布口径偏「高手拿什么」,与实机 bot 面临的
  候选分布差异记为语料边界;②环境对 41 号账本等消费面的数值效果不在
  本批(环境 EconomyEffect 接线是独立批,ADR-0144 notes 已记结构性断层)。

## 验证

ruff 0 → 新锁 13 passed(`test_cw_w162_invest_inject.py`)→ 全量 pytest →
零漂移门(改前 HEAD vs 注入代码 invest=False,seeds 0-19 diff={})→
n=20 冒测(①通道激活 14/20 局;off 口径 20/20 恒 0)→ n=300 双口径
锚与 drift 表(W162 报告)。
