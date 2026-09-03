# DD-009:旧方案零引用机制整批清退——约 20 族默认关开关+影子比对残留删除

- Status: accepted(用户裁定 2026-09-02「我们是重构,旧方案彻底出局」;清退批执行,编排者验收)
- 依据: OLD_MIX_AUDIT.md §1.3/§3/§5(逐族 grep 新方案四件套+dd-NNN 零引用后删)

## 决策

删除全部「默认关+无新方案引用+无重开判据」的旧机制开关族(开关生命周期第 4 态:判负/无承接即删码留墓碑):

- 影子比对族(ADR-0465 承诺未执行的删除):registry 字段+decision_assembly/prep_director 接线+遥测事件与落盘;
- spend_gate 三开关+decision_v2/spend_gate.py 整模块(功能已由新支出判据接管,ADR-0499 关死裁定的落地);
- 兑现链 v2 全族(W802)、P1 档位推进全族(W803)、形态达标三方向(ADR-0432/0433/0434)、C1 定向(ADR-0443)、C4 双开关、crisis_fallback(W956)、w875/w878/junk_first/equip_env_fill3、longterm_refresh、megastar_enhance、boss_tax_p75 标量。

## Why

用户重构裁定「一切按新方案能数学证明的来,旧方案彻底不考虑」。清查(OLD_MIX_AUDIT)实证:上述各族在新方案四件套与 dd-NNN 决策中零语义引用,均为「默认关+判据挂账未跑」的悬置态——违反开关生命周期纪律(禁无期限悬置),且死开关面持续消耗审计注意力。

## Consequences

- 保留(边界):decision_v2 全栈本体(§4.1 冻结共存承接)、θ/D_min/δ(provisional None)、λ_death 分层表(活校准+兜底清单)、posture_release 活机制(ADR-0426 release 帧 spend_gate_active);
- 各删族 registry 位置留墓碑注释(指向本 ADR 与原 ADR);
- 遥测 schema 历史字段按只读保留(新数据恒 None);
- docs 旧层 as-built 提及处(02_comp/03_tactics/README/02_knowledge_registries/SWITCH_INVENTORY)随文档同步批更新。
