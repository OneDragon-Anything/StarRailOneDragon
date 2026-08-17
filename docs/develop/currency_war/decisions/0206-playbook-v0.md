# ADR-0206: 预案层 v0(22 号处置:条件响应分支表 + 触发即执行承诺)

## Status

Accepted(2026-08-17;core 落地,批量批准 UI/局中执行/表-实 telemetry 挂实机批)

## Context

13 号回溯 5016 行抓 56 处违约(金零进展 38/钉死不 pivot 8/hp 毒化 10)——摆振
(姿态在门间拉扯)与僵住(该定不定)的根因:每门每回合独立重评估,局部 eval
反复否决全局正确的响应。正确响应知识已存在(门/ADR/plaza 纪律),缺执行结构。
12 号的「人要在场」约束是落地最大障碍。

## Decision Drivers

- 治本:结构消除摆振/僵住,而非让决策更聪明
- 人的协议成本从「事中 N 次」压到「开局 1 次」
- 给 13 号前向合约供给结构化载体、给 14 号免费对照组

## Considered Options

1. **Playbook 分支表(选)**:trigger(受限谓词:开局可知+已有 reader)+
   response(响应包:模式切换/参数,非单点动作)+ provenance + 修订门(预注册
   判决,不静默漂移);触发即执行,不再逐回合重评估;
2. 继续手写门族(现状):每门局部 eval,摆振结构性存在;
3. 12 号事中问询每分支:人的注意力成本错位。

## Decision

选 1。cw_playbook.py v0:Branch/BranchCondition/Playbook(match+触发计数)/
INITIAL_PLAYBOOK 四条种子(血线应急[M案例]/连胜守护[plaza纪律]/P3遭遇恒低
[ADR-0130 语义入表]/boss前清算[17号派生])。前向检查器 v0 简化为载体位
(完整违约判定挂 13 号消费批)。J1 覆盖率审计(56 违约映射)挂 M 语料回放批。

## Consequences

- 手写门族获得降级路径(表初始条目+对拍锚),非立即删除;
- 局中执行接线(battle_loop 查 match→应用 response)挂实机批次——先影子
  (表-实对照落 telemetry)后切流,47 号纪律;
- 22 号提案文件删档(INDEX 行替换)。
