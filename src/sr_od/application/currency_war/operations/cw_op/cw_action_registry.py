"""全动作单一注册表(动作 op 重组批③):词表类 → 动作 op 类一张表,
``action_op_class_for`` = 类级查询(终结判定/executor/落地门消费面),
``action_op_class_for_type`` = 词表**类**级查询(注册完备锁消费口),
``action_op_for`` = 构造helper(ctx + param + env 组装新壳 op)。

**op 形态(批③,design.md §1.1)**:动作 op = ``CwActionXxxOp``,继承
框架 ``SrOperation``(禁自建 op 基类——原 ``ActionOp`` ABC 删除),构造
签名 = ``(ctx, param, env)``,域依赖经 env 结构化传入(``PrepExecEnv``/
``ShopExecEnv``/``OverlayPickExecEnv``);op 内机械执行后直调自己的上报
函数(design.md §1.2 映射表)。

**收编状态**:商店域五行首批在册;备战域批3 收编在册;事件线 pick 族
批4 收编在册。注册完备锁(测试 = sr-od-test test_cw_unified_action_4)
以本表为机械约束对象:遍历统一词表 ``cw_vocab.CW_ACTION_TYPES`` +
事件线 pick 族 ``cw_events.PICK_ACTION_TYPES``,逐类断言本表解析可命中。
(原 CompTransaction 行已随 unified-action-factory 批2b R3 删除——整档
替换宏动作全链退役。)

**同名动作双域行更替申报(批3)**:词表归一后 ``CwActionSellBenchParam``/
``CwActionLevelUpParam`` 两类为商店/备战共用词表,单一表一键一行——两行
指向备战域 op(``CwActionSellBenchOp``/``CwActionLevelUpOp``)。依据:发射
面策略收缩至备战期后(flow/screens-actions-capability §5 判例),两类的
生产发射只在备战域,备战 op 即唯一活执行路径;原商店域 op 类随批③文件
删除(cw_sell_bench_action.py / cw_level_up_action.py,生产不可达),本
注记 = 其注销登记。

**注册行顺序敏感**:``action_op_class_for`` 按行序 isinstance 首中即返
——is-a 链的父类行必须在子类可独立匹配处之前兜底(子类共享父 op 时
父行即足;子类需独立 op 时其行必须插在父行之前)。现役先例 =
``CwActionLevelUpShopParam`` 同 ``CwActionLevelUpParam`` 同备战 op(单击,
无子类独立行)。分区注释按「族 → 基类兜底行 → 具体类行」摆放。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    CwActionBuyCardParam,
    CwActionClickSpheresParam,
    CwActionCloseShopParam,
    CwActionDeployMoveParam,
    CwActionFurnaceUseParam,
    CwActionLevelUpParam,
    CwActionLevelUpShopParam,
    CwActionLuckyTokenUseParam,
    CwActionOpenBookcardParam,
    CwActionOpenBoxParam,
    CwActionOpenShopParam,
    CwActionOpenTomeParam,
    CwActionPerfectProjectorUseParam,
    CwActionPickEncounterParam,
    CwActionPickFortuneParam,
    CwActionPickInvestParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickSupplyParam,
    CwActionPickWishTrialParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionRefreshShopParam,
    CwActionSellBenchParam,
    CwActionSellDeployedParam,
    CwActionStaffProjectorUseParam,
    CwActionStartBattleParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_buy_card_action import (
    CwActionBuyCardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_click_spheres_action import (
    CwActionClickSpheresOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_close_shop_action import (
    CwActionCloseShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_deploy_move_action import (
    CwActionDeployMoveOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_bookcard_action import (
    CwActionOpenBookcardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_box_action import (
    CwActionOpenBoxOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_shop_action import (
    CwActionOpenShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_tome_action import (
    CwActionOpenTomeOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
    CwActionPickEncounterOp,
    CwActionPickFortuneOp,
    CwActionPickInvestOp,
    CwActionPickMegastarOp,
    CwActionPickPartnerOp,
    CwActionPickPlannerOp,
    CwActionPickSupplyOp,
    CwActionPickWishTrialOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_prep_level_up_action import (
    CwActionLevelUpOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_prep_sell_bench_action import (
    CwActionSellBenchOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_refresh_shop_action import (
    CwActionRefreshShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_sell_deployed_action import (
    CwActionSellDeployedOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_start_battle_action import (
    CwActionStartBattleOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_tool_use_action import (
    CwActionToolUseOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_wear_equip_action import (
    CwActionWearEquipOp,
)
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 商店族(行序敏感,见模块头「注册行顺序敏感」节)
_REGISTRY: dict[type, type[SrOperation]] = {
    CwActionBuyCardParam: CwActionBuyCardOp,
    CwActionRefreshShopParam: CwActionRefreshShopOp,
    CwActionCloseShopParam: CwActionCloseShopOp,
    # 备战族(CwActionSellBenchParam/CwActionLevelUpParam 两行 = 双域共用词表
    # 指向备战 op,见模块头「同名动作双域行更替申报」节。CwActionLevelUpShopParam
    # = 同字段双类型(词表摊平后 is-a 链消亡),显式独立行,与
    # CwActionLevelUpParam 同备战 op)
    CwActionSellBenchParam: CwActionSellBenchOp,
    CwActionLevelUpParam: CwActionLevelUpOp,
    CwActionLevelUpShopParam: CwActionLevelUpOp,
    CwActionDeployMoveParam: CwActionDeployMoveOp,
    CwActionSellDeployedParam: CwActionSellDeployedOp,
    CwActionWearEquipParam: CwActionWearEquipOp,
    CwActionClickSpheresParam: CwActionClickSpheresOp,
    CwActionOpenBoxParam: CwActionOpenBoxOp,
    CwActionOpenTomeParam: CwActionOpenTomeOp,
    CwActionOpenBookcardParam: CwActionOpenBookcardOp,
    CwActionFurnaceUseParam: CwActionToolUseOp,
    CwActionPrivilegeCardUseParam: CwActionToolUseOp,
    CwActionWrenchUseParam: CwActionToolUseOp,
    CwActionPrecisionWrenchUseParam: CwActionToolUseOp,
    CwActionStaffProjectorUseParam: CwActionToolUseOp,
    CwActionPerfectProjectorUseParam: CwActionToolUseOp,
    CwActionLuckyTokenUseParam: CwActionToolUseOp,
    # 转场族
    CwActionStartBattleParam: CwActionStartBattleOp,   # 终结(交回外循环战斗分支)
    CwActionOpenShopParam: CwActionOpenShopOp,         # terminal 承载行(执行抛,正常路径不可达)
    # 事件线 pick 族(批4;overlay act 段经工厂,机械体 = 各 overlay 画面
    # op act 确认链迁移体。终态契约:策略器产出 = 词表 Pick 子类型,kernel
    # Pick 族 = 纯函数内部返回值,不再进注册表)。
    CwActionPickEncounterParam: CwActionPickEncounterOp,
    CwActionPickSupplyParam: CwActionPickSupplyOp,
    CwActionPickMegastarParam: CwActionPickMegastarOp,
    CwActionPickPartnerParam: CwActionPickPartnerOp,
    CwActionPickPlannerParam: CwActionPickPlannerOp,
    CwActionPickInvestParam: CwActionPickInvestOp,   # pick-op-unify 批收编(投资环境/策略两屏共用)
    CwActionPickFortuneParam: CwActionPickFortuneOp,   # pick-op-unify 批收编(T-3)
    CwActionPickWishTrialParam: CwActionPickWishTrialOp,   # pick-op-unify 批收编(T-3)
}


def action_op_class_for_type(action_type: type) -> type[SrOperation]:
    """词表**类** → 动作 op 类(类级解析,不构造动作实例;注册完备锁
    消费口)。

    行序语义与 :func:`action_op_class_for` 的 isinstance 首中同构:实例
    解析 ``isinstance(a, K)`` ⟺ 类级 ``issubclass(type(a), K)``,故按行
    序 issubclass 首中即同语义(is-a 兜底一致,CwActionLevelUpShopParam
    先例)。词表外类型 AssertionError 响亮暴露(非法返回 = 策略器 bug,
    禁静默跳过)。"""
    for cls, op_cls in _REGISTRY.items():
        if issubclass(action_type, cls):
            return op_cls
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{action_type.__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_class_for(action: Action) -> type[SrOperation]:
    """词表实例 → 动作 op **类**(类级查询,不构造 op 实例)。

    消费面 = 终结判定与 ``terminal``/``terminal_wait`` 类属性读取
    (消费点经注册表读类属性,禁消费点私表)与执行器/商店落地门的
    (ctx, param, env) 组装构造(design.md §1.3);行序语义同构造 helper。
    词表外类型 AssertionError 响亮暴露(ADR-0517 决策 9 语义:非法返回
    = 策略器 bug,禁静默跳过;文案中性,注册表现跨域共用)。"""
    for cls, op_cls in _REGISTRY.items():
        if isinstance(action, cls):
            return op_cls
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_for(action: Action, ctx: SrContext, env: object) -> SrOperation:
    """动作词表 → 动作 op 实例(构造 helper:注册表类级解析 +
    (ctx, param, env) 组装,批③ 新壳构造签名)。

    消费面 = overlay act 段(经工厂分派保持「意图类型 → 点击链」单一
    映射);执行器/商店落地门按 design.md §1.3 直接走
    ``action_op_class_for(action)(ctx, action, env=...)``。env 形参 =
    域执行环境结构化包(运行时不检查,项目既有风格)。词表外类型
    AssertionError 响亮暴露(语义同上)。"""
    return action_op_class_for(action)(ctx, action, env)
