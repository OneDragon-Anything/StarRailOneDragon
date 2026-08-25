# ADR-0020: autonomous-loop 三节删除(通用机制归位公共 skill)

- 日期:2026-08-26
- Status:accepted

## 背景

`references/autonomous-loop.md` 经多轮演化堆积了三节与 `od-dev-agent-autonomous-mode`(公共 skill,当日刚重构)重复或已过期的内容:

1. **goal/schedule 消费机制段**(导语第二段):写死「goal 轮第一动作=过 SKILL.md 的 8 步 checklist」等消费描述——公共 skill 当日改为 7 步开启 checklist + 事件驱动模式后**过期**,且消费机制本身是通用内容;
2. **编排者-worker 执行架构节**:与公共 skill §2 编排者-worker 模式大面积双源(分工/主会话不写实现);CW 增量(worker prompt 必含/薄切流水线)已由「派单模板硬规范①-④」覆盖或属可泛化方法论;
3. **授权边界节**:当日刚从 AGENTS.local 迁入,内容为通用自主推进授权面,非 CW 专属。

## Considered Options

1. 保留并标注「通用单一源在公共 skill」——否决:双源必然漂移(本次过期就是实证),标注挡不住;
2. 逐条裁剪只留 CW 增量——否决:增量已各有承载(派单硬规范/提醒网表),剩余不足以成节;
3. **整节删除+导语一行单一源声明(选)**:导语改为「通用机制(goal/schedule 消费/事件驱动/…/编排者-worker 分工/授权边界)单一源=od-dev-agent-autonomous-mode,本文不复述」。

## 后果

- 授权边界删除后在所有层(AGENTS.local/skill)均无副本——授权面完全由公共 skill + 自主推进模式节六字段承载;若公共 skill 未覆盖某授权场景,按公共 skill 的「疑点记档」处理,不再回迁项目层。
- SKILL.md「goal/schedule 自我校准」节路由行的编排清单同步去掉「编排者-worker 分工」。
- autonomous-loop.md 定位收窄为纯 CW 专属编排资产:七角色提醒网/派单硬规范/派发扫描源 C+E/素材泵/对抗审查/数学标尺/哨兵消费协议。

## 关联

- 前型:ADR-0018(同日同型——细则撤除+一行机制路由,无知识丢失,全部有更强承载处)
