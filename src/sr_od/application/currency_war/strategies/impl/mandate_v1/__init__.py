"""货币战争新核包(mandate_v1 换核,statefn 层先行批;换核迁移序原文已删档,
取回口径=ADR-0644)。

落位(策略统一迁移批):``decision/cw4/`` 整体迁入 ``strategies/impl/mandate_v1/``(编号承 cw3 谱系);
strategy_id=``mandate_v1``。本批只落 statefn 状态函数层(NMF §2 的 22 项
状态量单一源)+ audit 零调参审计载体 + 「挂后台效果」资格谓词载体(前置半步 0);
判据(criteria)/骨架(mandate)/证明(proof)/入口(entry)/桥(bridge)随
换核批 1 落地,不在本包内预留空壳。

依赖方向单向(01_math_framework §1 定位与权限总图):入口 → 判据/义务 → 状态函数 → 数据注册表;
本包内部:statefn 只 import 数据/内核注册表(cw_chars/cw_shop_odds/cw_economy/
cw_plane_table/cw_state/cw_comps)与同层 statefn 模块,禁回调 op 层与判据层。
禁相对导入(项目 AGENTS 硬约束)。

装配副作用(本包被导入即生效):向 kernel 的策略状态工厂注入槽注册
``StrategyState`` 工厂(kernel 依赖矩阵禁 kernel→impl 边,写路径的惰性
冷建经槽反转;先例 = obs 缓存清理/合成特效帧门注入槽)。类名 = 设计
正本 §8.5/§8.6-6 改名归位后的目标名(迁移批次三;历史名 MandateState
为同对象别名保留)。
"""
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    install_strategy_state_factory,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)

install_strategy_state_factory(StrategyState)
