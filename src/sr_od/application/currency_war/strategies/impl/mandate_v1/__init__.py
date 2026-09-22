"""货币战争新核包(mandate_v1 换核,statefn 层先行批;换核迁移序原文已删档,
考古走 git 历史)。

域内术语(本包注释用词的单一参考;前三个为玩法文档在册词,后两个为本
包直白化后的标准称呼):
- 锁线:把最终阵容(目标线)确定下来、此后围绕它买牌的阶段与状态。玩法
  先例 = ``docs/game/currency_war/research/final_comps/README.md``
  「见核心即锁线、围绕它买」;系统语义正本 =
  ``docs/develop/sr_od/application/currency_war/strategy-docs/
  12_line_and_intention.md``(代码对应 ``locked_comp`` 等符号)。
- 腾席:腾出备战席位——bench 满先卖最弱杂件,或升人口扩容。用户玩法
  纪律在册 = ``docs/game/currency_war/research/user_playstyle.md``
  条目 [32]「腾席优先级」。
- 让位:优先级让步——两判据冲突帧,低优先一方放弃(「X 让位给 Y」)。
  玩法先例 = ``docs/game/currency_war/research/economy.md``(经济让位
  保血)、``user_playstyle.md``(购买让位于息线)。
- 放行判定:把一个备战动作(部署/装备穿戴等)真正发出之前的条件判定,
  缺一即本帧不发、留待下帧。设计文档旧称「发射门」(T-127/P79-3 等
  ADR 在册词),读旧文档时同义对照。
- 替补席线内成员:在 bench 上、属于目标线、因板满尚未上场等待换上的
  成员。设计文档旧称「压席成员」。

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
正本 §8.5/§8.6-6 改名归位后的目标名(迁移批次三;历史名兼容别名已随
迁移尾批清理)。
"""
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    install_strategy_state_factory,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)

install_strategy_state_factory(StrategyState)
