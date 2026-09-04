# 0129 购买经验单击模型 + XP 反推真等级

## Status

accepted(2026-08-15)

## Context

升级门与等级观测长期存在两个相互掩盖的错误,M15 复盘时由用户提供的门槛表一次性揭开:

1. **升级模型错**:代码把 LevelUp 当作「一次动作 = 升 1 级 + 扣整级大金(36-60)」。真实机制(用户实测口述,A5+):「购买经验」每点一次 **+4 XP、花 4-8 金**;经验攒够当前级门槛自动升级,溢出结转。门槛表:LV3→4=4、4→5=6、5→6=20、6→7=40、7→8=52、8→9=72、9→10=84(telemetry 多局 XP 分母 4/6/20/40 与之吻合,独立交叉验证)。
   - 后果:升级门过度保守(以为要 36-60 金才升得动)→ 实际每击 4-8 金 → **升级严重滞后**。M15 进位面 2 真实 lv5(3 费核心 D 牌带 7-8 级),却因 #2 看起来是 lv6,问题被掩盖。
2. **等级观测错**:read_level OCR 失败时静默用 _expected_level 启发式兜底,污染 telemetry 与策略输入(live 实锤:真 5→6 过渡期 level 列恒为启发值)。XP 条 "cur/need" 的分母 = 当前级→下一级门槛,反查即可得真等级。

## Decision Drivers

- 用户权威门槛表(2026-08-15 口述)+ telemetry 独立对拍一致。
- 「保住了息,但没买到阵容」(用户对位面 2 低血死的归因)—— 等级滞后直接压缩高费核心获取窗口。

## Considered Options

1. **保留整级大金模型,只调低价格表** —— 否:机制理解错,价格只是表象;单击+结转语义影响买经验节奏(可一轮多点)与 bench-full 破墙(点 N 击非付大金)。
2. **LevelUp 语义 = 点到升 1 级(批量单击打包成一个 Action)** —— 否:simulate 粒度失真(经验条中途状态丢),且执行侧已按次 click;保留 1 Action = 1 击,plan 按 clicks_to_next_level 发多个。
3. **采用**:单击模型 + XP 反推等级(本 ADR)。

## Decision

- `cw_state`:XP_PER_BUY=4、XP_TO_NEXT_LEVEL 表、XP_CLICK_COST_FALLBACK=4;simulate(LevelUp) 改为 +4XP、跨门槛自动升级+溢出结转、同步 xp_progress。
- `cw_decisions`:xp_click_cost(clicks_to_next_level / _want_level_up / _xp_gold_floor(追级 20、攒息 50、血危 10 —— 用户节奏「不影响吃息」)helpers;level_up_gate 改「该买 + 扣单击价不破地板」;plan 主 gate 发「点到下一级」序列(预算受地板约束);bench-full 破墙点够升 1 级的击数。
- `cw_observation`:`_level_from_xp` XP 分母反推真等级,与读值冲突信 XP + [cw!] 留证(1-2 级表外值不覆盖,安全)。
- `shop._handle_bench_full`:8 击 → 10 击(盖 6→7=40XP)。

验证:新增测试 10 项(state 3 / decisions 4 / observation 1 + 修正 2),CW 全套 378 passed。

