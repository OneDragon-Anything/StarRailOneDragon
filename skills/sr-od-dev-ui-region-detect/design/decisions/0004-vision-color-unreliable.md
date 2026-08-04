# 0004. vision 颜色不可信精确值,定性可用 + CV 采样定准值

- **Status**: accepted
- **Date**: 2026-08-04

## Context

用 vision(VLM)描述画面元素时,会顺带报颜色 / RGB(如「亮青蓝 V~85%」)。实测本项目 vision
称图鉴卡边框「亮青蓝 V~85%」,CV 采样实测边框是 muted 紫蓝(BGR≈[129,108,140])—— vision
定性方向(偏亮、偏蓝调)对一半,数值不准。

根因(2025 学术共识):VLMs inherit human color perception、color illusions fool VLMs —— VLM
颜色感知是「人类式分类命名」(说「亮蓝」「暗紫」),**非像素级精确**,且会被色彩错觉骗。

## Decision Drivers

- **精确**:选 CV 信号(阈值 / inRange 范围)需要像素级精确值,VLM 给不了。
- **分工**:VLM 擅长定位 + 定性描述,CV 擅长精确数值 —— 各取所长。
- **可校验**:CV 采样(`np.mean(bbox)` 均值 / k-means 主色)能落盘复核;VLM 报的数值不能。

## Considered Options

1. **信 vision 报的颜色值**:数值不准(见 Context),用作阈值会导致 CV 法失效。
2. **vision 定性 + CV 采样定准值(选中)**:让 vision **定性**描述(够用来选 CV 信号:亮 vs 暗 /
   蓝调 vs 紫调)→ **精确阈值 / RGB 由 CV 采样定**(`np.mean(bbox)` / k-means 主色)。
3. **完全不用 vision 的颜色信息**:丢掉「定性方向」这个有用线索。

## Decision

选 2:**VLM 定位(在哪)+ CV 采样(准值)分工**。vision 颜色只取定性;别拿 vision 报的
「V~85%」当阈值。判据写进 `../../SKILL.md` vision 段。

## Consequences

- **正向**:CV 阈值有精确依据;vision 仍贡献定性线索(选信号维度:V / S / H 哪个是判别量)。
- **负向**:多一步 CV 采样(读 bbox 均值 / 主色);需先有一个 bbox(vision grounding 或手圈)。
- **follow-up**:跨模型换 vision 时(VLM 颜色感知随代际变),此分工不变 —— 精确值始终由 CV 定。

## Links

- `../../SKILL.md` vision 段(「颜色 / RGB 不可信精确值」)。
- 同源 vision 不可信问题:[ADR-0002](0002-numeric-verification-not-vision-judge.md)(计数 /
  对齐维度)。
- 外部:2025 学术共识(VLMs inherit human color perception; color illusions fool VLMs)。
