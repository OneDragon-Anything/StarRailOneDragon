# ADR-0011 goal/schedule 自主推进校准节(元纪律入 skill)

## Status

accepted(2026-08-22;用户指令「goal 和 schedule 都能收到,想想在哪里提醒自己:按 skill 来/不陷入局部乱改/保持代码架构/文档同步/子 agent 对抗」)

> 2026-08-25:细则层(goal 轮纪律 5 条+schedule 提醒纪律 2 条)被 [ADR-0018](0018-goal-schedule-discipline-mechanized.md) 机制化替代撤销——七角色提醒网建成后,自检内容已是提醒 prompt 本身;「校准点放 skill 内、离工作现场近」的落点原则仍有效。

## Context

goal 长对话(100+ 轮实证)注意力会被「当前最显眼的刺激」稀释,最初指令失效——表现为干等/逐局打补丁/跳过文档直改代码。schedule 校准注入有效但依赖用户手工设置;且 AGENTS.local 的通用版自校准节不在 CW skill 内,goal 轮的智能体可能没读。

## Considered Options

1. 只靠 AGENTS.local 通用节:always-on 但非 CW 特化;goal 轮上下文膨胀后,距工作现场太远。
2. 只靠 schedule 注入:依赖手工设置,忘设就裸奔。
3. **skill 内加「goal/schedule 自我校准」节**(选):CW skill 是每轮必调的操作手册,校准点放 checklist 旁=离工作现场最近;与 AGENTS.local 通用版不冲突(通用管一切长任务,本节管 CW 轮次的具体自检点,含 8 步 checklist 回指)。

## Decision

选 3。七条:①goal 轮先过 8 步 checklist(点名步骤 4/5——文档与设计先行是常犯缺口);②schedule 三问;③按 skill 干(防记忆稀释);④保持架构(改动落既有层,新层=停下问);⑤文档同步不欠账;⑥子代理对抗(回指 ADR-0010);⑦每轮收尾自检(产出/进度树/临时清理/下轮焦点)。

## Consequences

- goal objective 更新时(如验收线变化),本节不需改——它管「怎么推进」不管「推进到哪」。
- 与 AGENTS.local「Agent 长任务自校准」节是通用-特化双层(同 ADR-0007 模式);语义冲突时两处同步修。
