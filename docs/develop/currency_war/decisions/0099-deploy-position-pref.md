# 0099. deploy 按角色前后台属性选排(替 0007「前排优先」)

- **Status**: accepted
- **Date**: 2026-08-12
- **原编号**: D-99(5.1.6)

## Context
`_deploy_deterministic`(0007)拖人时用 `targets = 前排空 + 后排空` 一锅 `pop(0)`,即**前排优先**:所有 bench 角色按 target 羁绊排序后,从第一个空目标槽开始填(前排先满才后排),**完全不看角色的前后台属性**。

2026-08-11 用户 live 观察一轮 bot 运行,暴露 4 个 deploy 行为 bug(live 观察 2):**角色放错排 = 完全没效果**。前台角色(position=front)被拖到后排、后台角色(back)被拖到前排,都不发挥站位效果。根因:0007 的「前排优先」对「无角色属性感知」的占位填充合理,但角色属性(`Character.position`:front/back/flex)是游戏机制 —— 必须按属性站位才生效。

## Decision Drivers
- **角色前后台属性是游戏机制**:`cw_chars.Character.position`(front/back/flex,V4.4 图鉴 74 名全标)+ `position_pref()`(flex 默认 back)。前台角色站前排、后台角色站后排才有效。
- **live 观察**:放错排角色完全没效果(用户 2026-08-11 观察 4 bug 之一,最重 —— 站错 = 角色白上)。
- **0007 前排优先**:对无属性感知的占位填充合理,但有属性时应按属性;0007 边界也明说「不知角色身份」,身份/站位由后续补(D-8 补身份排序,本 ADR 补站位)。
- 数据源已就绪:`Character.position_pref()` 注册表可查,无需补数据。

## Considered Options
1. **保留前排优先(0007 现状)** —— 放错排角色无效(live 观察),核心 bug 不修。
2. **按 position_pref 选排**(前台→前排空槽、后台/flex→后排空槽;对应排满才 fallback 另一排,避免不上场)(选中)。
3. **后排优先** —— 对后排角色多场景,但前台角色又被放后排,同样错(只是错向相反)。

## Decision
`_deploy_deterministic` 加 `_bench_pos`(SIFT 读 bench 身份 → `get_char` 查 `position_pref()`)→ 每个 bench 角色按 pref 选对应排的空槽;**对应排满才 fallback 另一排**(防角色上不了场)。flex 默认 back(`position_pref` 语义;后排槽 6 > 前排 4,容错)。SIFT 漏读身份的 bench 角色 → 默认 back(保守)。

替 0007 的 `targets` 一锅 `pop(0)` 前排优先,改成 `front_empty` / `back_empty` 两池按 pref 取。target 羁绊排序(D-8)保留(target 先 + rest),排序决定**谁先拖**,pref 决定**拖到哪排**。

## Consequences
- **正向**:角色按属性站对排 → 发挥效果(核心,修 live 观察 2 最重 bug)。
- **负向/代价**:
  - 依赖 SIFT 身份读 bench `char_id`(漏读 → 默认 back,可能把前台角色误放后排;SIFT 71 立绘库可靠,漏读少)。
  - 总是读 bench 身份(不再 `_tgt` gate),多一次 SIFT 开销(行为正确性 > 微小性能,接受)。
- **边界**:
  - flex 默认 back(`position_pref` 语义);后续 comp 阵型 formation 可覆盖(暂不实现)。
  - **只管站位**:同角色去重(5.1.7)/ deploy_cap 上限(5.1.8)未做 —— 这两个是 live 观察暴露的另外 2 个 deploy 行为 bug,本 ADR 不覆盖。
  - fallback 是次优(pref 错位),仅对应排满时触发(避免不上场优先于站对排)。

## Links
- 修正 [0007](0007-deploy-deterministic-cv-verify.md) 的「前排优先」Decision(0007 边界「不知角色身份」由 D-8 + 本 ADR 补全)。
- `src/sr_od/application/currency_war/operations/prep/deploy_bench.py` `_deploy_deterministic`。
- 角色属性源:`cw_chars.Character.position` / `position_pref()`。
- 关联 live bug:5.1.6(本 ADR)/ 5.1.7 同角色去重 / 5.1.8 deploy_cap(均记 `cw_dev/5_实现/5.1_deploy_op/进度.md`)。
