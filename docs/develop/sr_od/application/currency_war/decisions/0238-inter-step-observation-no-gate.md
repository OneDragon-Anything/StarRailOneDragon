# ADR-0238 步间观察不过稳定门(维持现状 + 升级判据)

## Status

accepted(2026-08-24;架构 review「循环序」主要新发现补定谳;review 文件处理后删除)

## Context

目标循环序「等画面稳定→观察→对账→hook→决策→操作→循环」在**环入口**完整闭环(gate → observe_full → reconcile → while decide/execute);但 director 环内步间(`_run_loop` while 尾 `obs = self._observe(heavy=True)`)直接重读不过 gate——步级闭环只做了一半。方案 v5 批次3 原列「步间稳定门」主干,实际收窄为「单写者 hp+substate+返回值消费」,步间门未做且**无决策记录**——「未做」与「决定不做」应有 ADR 定谳。

## Decision Drivers

- 成本:gate 一轮 poll 全图 OCR ~5s;环内每步都过 = 每步成本翻倍(备战有倒计时,预算敏感)——当时收窄的原因,真实有效。
- 风险:动作后特效/升星 overlay 帧污染步间 heavy 读(deployed 6→1 一类),暴露面从环入口缩到步间;现有缓解 = 每动作自带验证 + park_cursor + event_overlay 检测 + reconcile star 防抖,非根治。

## Considered Options

1. 立即实现步间全 gate:成本翻倍,污染证据频率未量化——过度工程。
2. 永久不做:步间污染实锤存在(r297 同病根),弃根治不合理。
3. **维持现状 + 升级判据**(选):步间不过 gate 依赖逐动作验证链;当判据出现时升级轻量步间窗(动作验证通过→heavy 观察前补短指纹窗,复用 gate 基元,非全 gate)。

## Decision

选 3。**升级判据**(任一满足即重开此项):
- 步间 heavy 读被特效帧污染的实测证据 ≥2 次/10 局(reconcile 防抖日志 `deployed_align` 截断/`star` 回退的步间时点命中);
- 新动作类型加入环内(其验证链未经历实机考验)且首局出现步间污染征兆。

在判据未触发期间:新增 reader/动作时,验证链设计必须覆盖「动作后 1-2 帧特效窗」(park_cursor + 源槽验证是模板,别裸读)。

## Consequences

- 方案 v5 批次3 的「步间门未做」从隐式现状升级为显式决策;review 四偏差中 #1 定谳完成,#2(组合 op 降级)/#3(P5 事件收编)归 ADR-0123 原计划推进,#4(hook 上收)同。
- 卫生项随本 ADR 顺手清:run_node.py 头 `# 未验证` 标记(子类 live 实证)。
