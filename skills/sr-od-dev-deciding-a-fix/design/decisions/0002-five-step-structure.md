# 0002. 五步流程结构(因果链前置 + 前提验证并入步 4 + 必填槽位 + actionable 层停点)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
「决定怎么修」需一个可被 review 的决策流程。设计时面临几个结构选择:因果链(根因挖掘)与影响面 / 权衡的先后;前提验证(候选方案的前提是事实还是假设)是否单列步骤;根因挖多深停。

baseline(无 skill 处理 pywin32 #2428)暴露两个过程纪律缺口,对应 SKILL.md 步骤里的两个必填槽位:
1. **前提验证槽**:baseline 否决「锁 pywin32 311」理由是「锁不住」—— 未验证的假设(实际显式声明 `pywin32<312` 即锁得住,下 wheel 验证 311 自带 `pythonwin/mfc140u.dll`)。→ SKILL.md 步骤 4 强制「前提验证」。
2. **上游修复状态槽**:baseline 没挖到「312 是 regression、上游已修待 build 313」,误判锁版本是「永久拖延」而非「有终点的临时止损」。→ SKILL.md 步骤 1 因果链含「修复状态」层、步骤 4 强制填「上游修复状态」。

## Decision Drivers
- **因果依赖**:根因的「修复状态」决定方案「临时/永久」,是权衡(步骤 4)的核心维度,不能在权衡之后才挖 → 因果链前置。
- **不过度工程**:前提验证针对具体候选方案,单列早期步骤会过早(候选还没生成就验证前提无的放矢)→ 并入步骤 4。
- **防过度挖掘**:根因可无限深挖,停在「有权且能修」的层 → actionable 层原则。
- **通用 gap(非模型补偿)**:两槽位是任何合理模型按 RCA 方法论都该做的标准动作(baseline 漏了是过程纪律问题,不是某模型怪癖)→ 经 RCA 过滤后进共享 SKILL.md 正文。

## Considered Options
1. **前提验证单列早期步骤**:更显眼,但前提是针对具体候选方案的,早于步骤 3(生成候选)无意义 → 过早。
2. **因果链后置(先影响面再挖根因)**:影响面筛选需要先知道介入点,介入点来自因果链 → 顺序倒置。
3. **因果链前置 + 前提验证并入权衡步 + actionable 层停点**(选中)。
4. **根因挖到底(到上游源码 setup.py)**:超出本项目权限(给上游提 PR 修 setup.py 不可行动);上游也已修 → 过度。

## Decision
选 3。五步顺序与槽位见 SKILL.md「决策流程」。actionable 层 = 你有权且有能力修的那层,再深是过度。

baseline(pywin32 #2428)案例论据(仅 design,不进正文):
- 因果链:症状(闪退)→ import win32ui ImportError → win32ui.pyd 找不到 mfc140u.dll → pywin32 312 wheel 不含 mfc140u.dll → 上游 setup.py 条件写反(PR #2755)→ 已修(commit 3cc74e0)待 build 313。
- 介入点:锁 `pywin32<312`(包级,311 自带 mfc140u.dll);备选「移除 win32ui import」(代码级,grep 验证全库仅 `pc_game_window.py` 用)。
- 前提验证:下 311/312 wheel 对比,确认 311 含 `pythonwin/mfc140u.dll`、312 不含。
- 上游修复状态:regression + 待 build 313 → 锁版本是「有终点的临时止损」。
- baseline 对照:无 skill 的 agent 否决「锁 311」(误以为锁不住)、未挖到上游已修(误判永久拖延)—— 正是两个必填槽位要防的。

## Consequences
- **正向**:因果链前置让修复状态信息在权衡前就位;前提验证并入避免过早;actionable 层防过度挖掘;两必填槽位把 baseline 通用 gap 固化。
- **负向**:五步顺序对简单 bug 可能偏重(每步可轻量过);actionable 层判据有主观性(「有权且能修」需人判)。
- **推翻它碎什么**:因果链后置 → 上游修复状态信息缺失 → 方案临时/永久误判;前提验证单列 → 早于候选生成无意义;去掉 actionable 层 → 挖到上游源码不可行动。

## Links
- 本 skill [ADR-0001](0001-methodology-type-green-required.md)(baseline 论证用法 / 方法论型归类)。
- SKILL.md「决策流程」。
