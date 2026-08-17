# ADR-0198: 重入层 v0 落地(redesign 31 号处置:journal 词表+纯投影+三级重入语义)

## Status

Accepted(2026-08-17,策略优化会话;journal 常开落盘/StrategySession 投影化/温重入差异
推断的执行侧挂实机批次)

## Context

31 号诊断:世界态接手已解决,策略态失忆零投入——session 每局新建局终销毁,重启丢
target_comp/20 预注册/22 批准/15 影子模块态;telemetry 是胚胎(enabled=False 生产关、
词表只有决策迹、零消费)——14/28/13/29 的输入结构上不存在。

## Decision Drivers

- 架构纪律(宪法主张):任何模块不得持有不可重导的隐藏可变状态——要么投影要么事件
- 诚实原则:重入后信念变宽,不是变准

## Considered Options

1. **词表+投影+三级判定纯函数先行(选)**:执行侧(常开落盘/session 改造/冷重入指纹
   分类)挂批次;
2. 直接常开 journal 改 telemetry 管线——先立语义再动生产路径;
3. 不做——失忆继续,恢复局连事后分析都降级(M18 活案例)。

## Decision

选 1:`cw_reentry.py` v0——

- ``JournalEvent`` 四族词表(动作/观测/外生/随机数消费)+ projection_version pinning
  (防改投影函数=悄悄改写历史解释);
- ``project``:journal 前缀 → world_state 纯投影(obs 最后值 + action 重放;
  对账=投影内部推导规则);
- ``reentry_level`` 三级(热/温/冷)+ ``widen_beliefs_on_gap``(温重入加宽语义:
  缺席证据不可记,方差乘子 1+0.15×缺口轮)+ ``replay_rng``(种子+消费序号 → 断点恢复);
- **J1 过(测试)**:合成 journal 热重入逐字段精确恢复(bench/deployed/board 动作重放);
  三级判定;加宽语义;rng 断点一致且消费数敏感;版本 pinning。

## Consequences

- 消费红利位就绪:14(ex-ante 重放)/28(状态带规范导出)/13(生产局语料)/
  24(journal 前缀作 sim 种子+同前缀配对);
- 22 批准/20 预注册成为持久事件的自然落点(外生族);
- 31 号处置完成(v0),提案文件删档;测试 +5。
