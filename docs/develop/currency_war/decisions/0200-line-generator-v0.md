# ADR-0200: 机制推导线生成器 v0 落地(redesign 25 号处置:结构枚举+半解析先验+配额)

## Status

Accepted(2026-08-17,策略优化会话;真实注册表接线[cw_chars/合成图 K7]与生命周期接线
[21 种子池/20 审判]为消费批次)

## Context

25 号诊断:427 羁绊组合 vs ~20 聚类条目——pair_synergy 对人类没玩过的对收缩到 0(防
optimizer's curse 的正确纪律),副作用是人类未探索区零信号;版本 bump 后只能等人类攻略
(真空期打旧 meta)。

## Decision Drivers

- 知识来源切换:plaza 拟合(向后看)→ 机制数据正向合成(向前生成,零对局样本出候选)
- 「生成器只提出,评审机器处置」——零新治理

## Considered Options

1. **注入式枚举+定性先验先行(选)**:RoleFacts/LineSkeleton 注入(生产接 cw_chars,
   测试 mock);半解析核(trait 断点+职能覆盖+费用档)——不是战斗模拟器,只作离线
   排序过滤,不进回合内决策;
2. 全解析核+量纲锚(19 号 D≥E 钉量纲)——锚定挂批次;
3. 不做——版本真空桥接与内生发现回路继续缺位。

## Decision

选 1:`cw_line_generator.py` v0——

- ``enumerate_skeletons``:carry × 阈值可达另一 trait(剪枝:≤4 费可铺/站位合法),
  与已知线去重只发增量;
- ``strength_prior``:断点项(阈值低=易激活)+ 职能覆盖(缺输出 ×0.5)+ 费用档窗口;
- ``cost_gate_and_quota``:成本门(17 号 formation_cost 注入)+ top-K;
- **J1 过(测试)**:枚举覆盖可达带且增量去重生效(已知对不重发、未知对有生成);
  先验语义(缺输出降权);配额降序+成本门杀超预算。

## Consequences

- 三源 provenance(mechanism/plaza/handwritten)可溯;生成候选走 21→20→05→13 既有
  机器(provenance 低先验入场);
- 版本真空桥接能力就位(注册表随游戏更新即重发);
- 25 号处置完成(v0),提案文件删档;测试 +3。
