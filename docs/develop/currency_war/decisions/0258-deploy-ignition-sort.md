# ADR-0258: deploy 点火增量排序(四体系判据进场位;r404-A1)

- **Status**: accepted
- **Date**: 2026-08-23

## Context

过渡阵容 = 四体系两两组合(用户口述[20][21][22],transition_combos.md 重写
定稿)。60 局 r6 归因:未成型局 44% =「差 1 人·bench 有货未上」——根因是
r251 时代 select_deployments 排序只看阵营身份,不看「是否恰好点火」:
vacancy=1 时冗余第 4 仙舟会挤掉点火的三月七(探针实证)。

## Considered Options

1. **排序加 ignition_gain 首键**(「恰好让某体系凑满 tier 的那张」最优先)
   ——不改围栏/不改购买,只动进场位排序;deploy 侧纯函数可锁可变异自检。
2. 购买侧优先买点火件——购买已有 r368-r387 谓词族,再叠维度=复杂化;
   且「买了但上不去」的病灶在 deploy 侧。
3. 围栏禁冗余件上场——过度:冗余件在无点火件可上时填空仍有价值
  (r387 富余放行语义)。

## Decision

选 1:`cw_deploy_logic.ignition_gain`(该角色上阵后「过渡体系达成数」
增量;体系=仙舟3/列车2/DOT2,希儿系不参与 deploy 排序——希儿本人是
target 件)+ TRANSITION_TRAITS 同源常量(与 cw_sim._TRANSITION_TRAITS
同语义;不 import cw_sim 防成环,两边注释互指)作 select_deployments
排序首键。锁测试 3 条。

## Consequences

- 探针实证修复前病(vacancy=1 冗余压点火),ignition_held=0;
- sim engines2_by_r6 不动(0.433)——后续诊断破案:排序已不是瓶颈,
  40/43 局未成型真根因=重复件占位(r404-A2,ADR-0259);A1 正确但
  非当时主病灶;
- 设计意图与 sim 数字源:交接文档( cw_dev/交接_2026-08-23_过渡体系
  重构与A1A2.md,作者会话末交接)——本 ADR 由主会话按交接记载补写
  (作者会话已结束)。
