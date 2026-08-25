# ADR-0018: goal/schedule 自检纪律机制化替代(撤销 ADR-0011 的细则层)

- **Status**: accepted
- **日期**: 2026-08-25

## Context

ADR-0011(2026-08-22)设立「goal/schedule 自我校准」节,含 goal 轮纪律 5 条+schedule 提醒纪律 2 条。其诞生背景自述:「schedule 校准注入有效但依赖用户手工设置」——当时七角色提醒网(2026-08-24 定调)尚未建成,goal/schedule 消息内容不自解释,需在 skill 内写「收到消息先对照纪律自检」的 meta 层。

现状:①goal/schedule 机制已清楚(消息到达方式/prompt 自解释性);②七角色提醒网常驻,多条自检纪律**已成为提醒 prompt 本身**(行为校准角色=三问,进度对表角色=入口对实况);③通用机制(事件驱动/空转轮/目标切换与迭代封存/早停收口)在 od-dev-agent-autonomous-mode 已有覆盖。用户据此裁决:这两节纪律已无用。

## Considered Options

1. 保留(防机制失效日)——否决:双轨(纪律文本+机制化提醒)同内容并存=双源,且 agent 每次多读一层已内嵌于提醒 prompt 的指令。
2. 全删不留路由——否决:goal 轮「第一动作过 checklist」的路由信息仍需一行(SKILL.md 导读承载);schedule 消费的 CW 专属内容(七角色表)仍是活资产。
3. **细则撤除+一行机制路由(选)**:删两节,导语改为「goal 醒来第一动作=过 SKILL.md checklist;schedule 提醒=按 prompt+当期并行度执行;通用机制单一源=od-dev-agent-autonomous-mode」,七角色表等 CW 专属编排资产保留。

## Decision

选 3。逐条去向(全部有更强承载处,无知识丢失):过 checklist→SKILL.md 导读句;按 skill 干→AGENTS.local+autonomous-mode 通用;战役化→autonomous-mode「目标切换与迭代封存」;空转轮→autonomous-mode「事件驱动模式」(更彻底:定时轮没新事件=空转);收尾自检→autonomous-mode「早停与收口」+进度对表提醒(45min);schedule 三问→七角色表「行为校准」行 prompt 本身;提醒≠指令→七角色表节判据行。

## Consequences

- ADR-0011 部分撤销(细则层);其「校准点放 skill 内、离工作现场近」的落点原则仍有效——现在的承载形态是提醒网 prompt+一行路由,比纪律节更近。
- autonomous-loop.md 定位收窄为「CW 编排资产」(提醒网/派单硬规范/worker 架构/对抗/素材泵/裁决标尺/哨兵消费),不再含 goal/schedule 消费 meta 纪律。
- 机制依赖声明:本决策依赖七角色提醒网常驻——若提醒网停用(schedule 不可用),需按 autonomous-mode「若环境只有定时轮,降级为心跳用」的降级路径走,不回抄已删细则。
