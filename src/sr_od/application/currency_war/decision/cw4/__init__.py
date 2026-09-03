"""货币战争新核包(mandate_v1 换核,IMPL_DESIGN §6.4-R 步 2 批)。

包名裁定(2026-09-03):保留 ``decision/cw4/``(编号承 cw3 谱系);
strategy_id=``mandate_v1``。本批只落 statefn 状态函数层(NMF §2 的 22 项
状态量单一源)+ audit 零调参审计载体 + 「挂后台效果」资格谓词载体(前置半步 0);
判据(criteria)/骨架(mandate)/证明(proof)/入口(entry)/桥(bridge)随
换核批 1 落地,不在本包内预留空壳。

依赖方向单向(IMPL_DESIGN §1):入口 → 判据/义务 → 状态函数 → 数据注册表;
本包内部:statefn 只 import 数据/内核注册表(cw_chars/cw_shop_odds/cw_economy/
cw_plane_table/cw_state/cw_comps)与同层 statefn 模块,禁回调 op 层与判据层。
禁相对导入(项目 AGENTS 硬约束)。
"""
