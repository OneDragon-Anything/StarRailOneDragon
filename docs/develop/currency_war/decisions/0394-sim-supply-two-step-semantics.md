# 0394 sim 补给选卡「恒 idx0」伪影修复(生产两步语义接产)

- 状态: accepted
- 日期: 2026-08-27
- 关联: ADR-0393(同族:sim 调用形态保真)、ADR-0294(件2,supply 披露计数)

## 背景(W212 批 A 定位,任务书 W213)

W212 批 A 发现 sim 的补给 3 选 1 存在系统性伪影:`cw_sim` r393 段调
`decide_supply(_opts, st, sess.target_comp, None)` 时**恒传默认
`refresh_used=False` 且丢弃返回的 refresh 标志**。而生产
`decide_supply`(cw_events)的两步语义是:

1. 带钻 → 直接选;
2. 全无钻 + 本局未刷 → 返回 `refresh=True`(idx=options[0]);
3. `refresh_used=True` → key_equips 契合(+10)+ 通用价值评分选。

sim 只取 `_pick.idx` 入池 → 步 2 的 idx 恒为 `options[0]`,而带钻命中
(~15%×3 列)之外的首调几乎必然走步 2 → **价值评分分支在 sim 从未执行,
恒取 idx0**。生产 `RunSupplyNode` 是真两步:首调 `refresh_used=session
._supply_refresh_used`(StrategySession 正式字段),refresh=True → 点刷新
按钮重掷 3 列(run_supply_node:68-71)→ 下一轮 loop 重读选项再选(此时
session 标志已置位 → 评分分支执行)。sim 的装备获取因此系统性偏离生产
(W212 量化:key_equips 命中率 sim 0.078 vs 生产语义 0.101,+29%)。

## 决策

cw_sim supply 段原生实现两步语义(W212 批建议 1;禁 monkeypatch 层修):

- 首调 `decide_supply(..., refresh_used=sess._supply_refresh_used)`;
- 返回 refresh 且未刷过 → session 标志置位(run_supply_node:71 同语义,
  字段是 StrategySession 正式字段,sim 直接复用零新状态)+ **重掷 3 列再
  调一次**(refresh_used=True → 评分分支);
- 重掷采样消耗**局内 rng 流**(与实机发放分布一致;W212 monkeypatch 臂
  用独立 rng 是补丁层限制,原生实现不走);
- 补给刷新不耗金:刷新按钮「剩余次数:1」计数制(run_supply_node:50
  实锤),非商店 RefreshShop 花金通道——sim 金账不动。

配套观测(W212 建议 2 部分):`SimResult.p1_key_hit_hits/total`(P1 出口
key_equips 命中度量,口径 = Σmin(需求份数, 持有份数)/Σ需求份数,与 W212
批 A 相同;持有 = deployed 已穿 + owned 池)+ 批报告 `p1_key_hit_rate`/
`p1_key_hit_runs`(有 key 需求局的均值)。

## Considered Options

| 方案 | 评 |
|---|---|
| **原生两步语义(采纳)** | 与生产 RunSupplyNode 逐行为对齐;session 正式字段零新状态;rng 流一致性(重掷消耗局内 rng)是 sim 可信度的根基 |
| monkeypatch 臂转正(W212 批 A 形态) | 补丁层必带独立 rng(拿不到局内 rng),发放分布与实机错位;且 monkeypatch 不入产线 |
| 只补 refresh_used 不重掷 | 半修:评分分支可达但选项集仍是首掷——与生产「重掷后再读再选」不符 |
| 不修(接受 sim 不建模) | sim 装备面验证承诺落空(同 ADR-0393 不修项的评法);key 命中率系统性低估 ~20-29% |

## 后果

- **装备面**:key_equips 命中率 0.080→0.098(n=300,seed 0-299,池
  861fc9f6,planes=2,invest on;W212 monkeypatch 臂同差 0.078→0.101,
  差额来自 rng 流与 min 口径的微小实现差)。
- **终态分布漂移 = rng 流移位,非因果通道**:重掷额外消耗局内 rng
  (每次 +3 choice +3 random),首个 supply 节点后所有下游采样(节点
  结算/Δ池/商店波)整体移位——n=300 的终态差异(never2 7→5、mal
  19→20、engines2_by_r6 0.507→0.497、出口 hp 31.13→30.08、P2 胜率
  0.1784→0.1911)全部在该样本量的二项噪声量级内(mal 的 1σ≈0.8%),
  且方向互有正负,与「装备效果未建模 → 装备语义改动无战力出口」的
  sim 已知边界一致。逐项数字与解释见 W213 批报告
  (`.debug/temp/currency_war/w213_sim_supply/w213_n300.json`)。
- **P1 段不再逐位零漂移**(与 ADR-0393 不同):supply 节点在 P1 也有,
  rng 流移位从首个 supply 节点起生效——这是语义修复的本意,不是回归;
  旧行为的「逐位一致」恰是伪影本身。
- 验证:A/B before/after 臂(before 臂 = monkeypatch 仿真旧「丢弃
  refresh 标志」形态,兼作测试锁的变异探针证据)+ 测试仓行为锁
  (test_cw_w213_sim_supply_two_step)+ cw_replay --diff + 全量 pytest。

## 实况与任务书冲突记录

无。任务书预估与 W212 批建议 1 一致,原生实现落地。
