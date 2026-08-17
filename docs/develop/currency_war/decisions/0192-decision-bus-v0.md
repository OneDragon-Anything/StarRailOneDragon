# ADR-0192: 决策总线 v0 落地(redesign 30 号处置:类型化声明黑板+预注册仲裁+裁决记录)

## Status

Accepted(2026-08-17,策略优化会话;PrepDirector 接线[声明发射端改造]为消费批次)

## Context

30 号诊断:15 影子模块同时输出时的语义未定义——冲突被无人记录的调用顺序静默裁决
(13 号「钉死 8 例」审不出谁压的);预列 7 条未定义组合缝(22×03/06×03/18×03/27×21/
16×22/04 分布/19×15)。缺的不是更好的模块,是「它们同时说话时的语义」。

## Decision Drivers

- J1 判据:缝普查 ≥6 + 合成冲突正确裁决并记录
- 12 号问询的分歧信号至今无输入源——本层冲突检测器是其上游(机器先裁,裁不动才问)

## Considered Options

1. **声明类型格+查表仲裁先行(选)**:Claim 四类(Goal/Propose/Veto/Evidence)+
   预注册优先级表(GOAL_PRIORITY/VETO_SAFETY_ORDER 数据驱动,规则不进代码)+
   ArbitrationRecord 全量记录;kill-switch 零漂移;
2. 直接改造 PrepDirector 调用图为声明发射——先立语义层再接全家,回归面小;
3. 维持隐式调用序——压制继续不可审计。

## Decision

选 1:`cw_decision_bus.py` v0——

- 仲裁协议:evidence 并入/goal 查优先级表/propose 先过 veto 域(硬否决剔、软降权乘)
  再比/veto 冲突按安全序、不可裁决余数升级(12 号路由);
- veto 命中语义:显式 scope 对齐 + payload 关键词粗对(propose 未声明 scope 时保守命中;
  精确匹配挂接线批次);
- **测试全过(6)**:evidence 直通;**缝 #2(06×03)goal 优先级裁决+双方记录**;
  **缝 #4(27×18)veto 安全序裁决**;硬否决剔除/软降权乘入;不可裁决升级;零漂移。

## Consequences

- URID 裁决记录成为 13(审压制)/14(provenance)/12(分歧信号)的首个输入源;
- 22 号「playbook>eval」降格为注册表首条目(顺带修缝 #1 的否决对象指向不明);
- PrepDirector 声明化接线与 7 缝全量 J1 普查挂消费批次;
- 30 号处置完成(v0),提案文件删档;测试 +6。
