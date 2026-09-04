# 0140 中期护航三套 + M18 复盘回归修正(散牌留 bench 人口门)

## Status

accepted(2026-08-15;攻略复查 #1 落地 + M18 复盘实证回归修复)

## Context

①难度攻略 22-34「中期护航三套」:6 级正式构筑、无需本体、极低造价、P2 稳定连胜 —— 龙丹护航(4战技点+3仙舟,服务直伤)/灵砂护航(4击破)/阿雅护航(3昼神+3能量,服务 DOT);护到 2-7/3-1 分水岭结单;成长型 comp(万敌/狼队/夜神/学者)不适用。transition_chars 数据此前零消费。
②M18 复盘(子代理)实证回归:ADR-0130 散牌留 bench 把「P1 开局囤牌」语义全局化 → P2 人口扩展期放置 3/18、满员率 76%、未达上限弹窗频发。

## Considered Options

- 护航消费点:新建 escort 计划器(重)vs **扩 transition_tempo_score**(现有 tempo 语义正交叠加,护航=有方向的过渡)→ 后者。
- 护航选择:全局一套 vs **按 target 机制属性匹配**(escort_for serves 匹配 + 成长型排除)。
- 散牌门:P1-only(按位面硬编码)vs **空位>2**(人口扩展期语义直接由 vacancy 表达,跨位面通用)。

## Decision

1. cw_comps:EscortComp 注册表(三套)+ escort_for(target)(serves 匹配;GROWTH_MECHANICS{燃血,欢愉叠层}排除)。
2. transition_tempo_score(state, target_comp):护航窗口((plane,round) ≤ (2,7))内护航羁绊凑出(≥2)→ 每羁绊 1.5× 加权;evaluate 传 target。
3. deploy_bench 散牌门回归修正:空位>2(人口扩展期)→ 散牌照旧上场(空位即战力,防未达上限弹窗);P1 开局(空位少)保持囤牌语义。

验证:escort_for 三例(希儿→龙丹/流萤→灵砂/万敌→None)+ tempo 窗口三态 + 全量 397 passed。

## M18 复盘要点归档(子代理报告,详 replay/m18_analysis_out*.txt)

- M18=恢复局(P2r2 接手):死于 P2-5(比 M15 多 3 轮),进 P2 HP 41 vs 1,boss 0 损 —— 修复栈方向正确。
- 金无滞留(峰 24/死 2);但 P2 段 0 次买经验(lv7 恒)—— 刷新(74金)与经验竞争,P2 推 8 未执行,下局观察(完整局 P1 段才能验 0129)。
- 弹窗修复实证生效(出场 1 次消化,出战成功);0131/0133-0135 未验到(该局无投资节点)。
