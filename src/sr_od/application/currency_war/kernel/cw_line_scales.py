"""货币战争 统一阵容评分·数量级标尺(单一常数源)。

出处 = 统一阵容评分迭代的数量级标尺设计(四轮对抗审查定稿:正项上界
全库自算校准,层间支配靠数量级实现,示意值 = 本表锁定值);权威版本
= 本文件常量(正本 = docs/develop/sr_od/application/currency_war/
strategy-docs/12_line_and_intention.md §1.1「数量级表」:常数单一源 =
本模块)。

单一源纪律:本迭代线分数值只写常量名、值在本文件一处定义。消费面 =
线分引擎(strategies/impl/mandate_v1/line_select)/词缀吃怕表
(kernel/cw_affinity_table)/投资通道派生(kernel/cw_invest_channels)/
选卡方向分与克制减分(mandate_v1/invest_strategy 与 pick_common)。

层级归属申报:标尺是被审查定稿的策略标尺常数(非玩法真值),驻 kernel 的
理由 = 吃怕表(kernel 数据文件)与线分(策略层)双侧消费,独立常量模块
免策略层↔kernel 反向 import 成环(与 cw_investments 里 kernel 注册表/
策略层分值映射的两层分工同一形态)。

不变量(标尺设计「sim 不变量」裁定):任意构局任一候选线,其全部正项之和
上界 < |重开级| = 100000——重开级单条即数值排他(含重开级命中的线分恒
低于无命中线);上界自算测试 = 测试仓 test_line_select「正项上界自算」。
"""
from __future__ import annotations

#: 重开级(词缀/boss)与万敌无燃料底线:排除 = 极大减分,任何构局正项和
#: 追不上(统一阵容评分裁定「排除=极大减分」)。
RESTART_PENALTY: int = -100_000

#: carry·anchor(线基准核心,每名):基准核心单卡即战力(攻略「希儿到手即开线」);
#: 单 anchor 压过一切环境正和。基准判定读口 = cw_comps.carry_anchor(core[0] 派生)。
CARRY_ANCHOR: int = 8_000

#: carry·其余 core(每名):非基准 core 减半(攻略主次语义——基准与辅助分档)。
CARRY_CORE: int = 4_000

#: 插件(每名)。
PLUGIN_BONUS: int = 500

#: 攻略热度每点:满热度 274 < 500 = 不足 1 插件(持有实证 > 社区先验)。
HEAT_PER_POINT: int = 1

#: 词缀强吃·顶级(万敌×正当防卫)。
AFFIX_STRONG_TOP: int = 900

#: 词缀强吃·燃料(万敌×忍无可忍族;姬子A×受击触发类归批 3 拆分)。
AFFIX_STRONG_FUEL: int = 750

#: 投资强档·定义卡(黑塔纪元/专家邀请/飞光:「拿到即定义线」手编表)。
INVEST_DEFINING: int = 500

#: 投资强档(期货任务链/定向刷新:契约/概念股)。
INVEST_STRONG: int = 300

#: 实证覆盖升档条目值(量子星徽×3→希儿/罗刹→列车:通道③默认 +150 按
#: 实证升强档——直接记载 > 类间概括 > 机制推定三级证据序的实证半边)。
EVIDENCE_UPGRADE_BONUS: int = 750

#: 投资中档(星徽默认/引擎匹配)。
INVEST_MID: int = 150

#: 软档(弱关联;flex 降档落点:强→+30/中→0)。
INVEST_SOFT: int = 30

#: 怕(词缀/boss)。
FEAR_PENALTY: int = -150

#: 选卡克制减分(counters_dot 硬排除迁移:克制 top1 线主派的卡给选卡分
#: −750,克制档,与实证升档同量级)。
COUNTER_PICK_PENALTY: int = -750
