"""全动作单一注册表(动作 op 重组):词表类 → 动作 op 类一张表,
``action_op_class_for`` = 类级查询(终结判定/executor/落地门消费面),
``action_op_class_for_type`` = 词表**类**级查询(注册完备测试消费口),
``action_op_for`` = 构造helper(ctx + param + env 组装新壳 op)。

**op 形态(sim 统一批换父)**:动作 op =
``CwActionXxxOp``,继承 CW 操作基类 ``CwOperation``
(operations/cw_operation_base;原 ``ActionOp`` ABC 删除),构造
签名 = ``(ctx, param, env)``,域依赖经 env 结构化传入(``PrepExecEnv``/
``ShopExecEnv``/``OverlayPickExecEnv``);op 内机械执行后直调自己的上报
函数(映射单一源 = ``kernel/cw_action_report`` 同名上报函数,
op-layer.md §1.2)。

**并入状态**:商店域五行首批已登记;备战域已并入登记;事件线 pick 族
已并入登记。注册完备测试(sr-od-test test_action_registry)
以本表为机械约束对象:遍历统一词表 ``cw_vocab.CW_ACTION_TYPES`` +
事件线 pick 族 ``cw_events.PICK_ACTION_TYPES``,逐类断言本表解析可命中。
(原 CompTransaction 行已随 unified-action-factory R3 删除——整档
替换宏动作全链停用。)

**同名动作双域行更替申报**:词表归一后 ``CwActionSellBenchParam``/
``CwActionLevelUpParam`` 两类为商店/备战共用词表,单一表一键一行——两行
指向备战域 op(``CwActionSellBenchOp``/``CwActionLevelUpOp``)。依据:发出
面策略收缩至备战期后(flow/screens-actions-capability §5 判例),两类的
生产发出只在备战域,备战 op 即唯一活执行路径;原商店域 op 类随文件
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
    CwActionCloseShopParam,
    CwActionCollectOreParam,
    CwActionDeployMoveParam,
    CwActionFurnaceUseParam,
    CwActionLevelUpParam,
    CwActionLevelUpShopParam,
    CwActionLuckyTokenUseParam,
    CwActionObsParam,
    CwActionOpenBookcardParam,
    CwActionOpenBoxParam,
    CwActionOpenShopParam,
    CwActionOpenTomeParam,
    CwActionPerfectProjectorUseParam,
    CwActionPickBoxCardParam,
    CwActionPickEncounterParam,
    CwActionPickExpertInviteParam,
    CwActionPickFortuneParam,
    CwActionPickInvestEnvParam,
    CwActionPickInvestStrategyParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickStarTomeParam,
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
from sr_od.application.currency_war.operations.cw_op.cw_close_shop_action import (
    CwActionCloseShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_collect_ore_action import (
    CwActionCollectOreOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_deploy_move_action import (
    CwActionDeployMoveOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_obs_action import (
    CwActionObsOp,
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
from sr_od.application.currency_war.operations.cw_op.cw_pick_box_card_action import (
    CwActionPickBoxCardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_encounter_action import (
    CwActionPickEncounterOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_expert_invite_action import (
    CwActionPickExpertInviteOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_fortune_action import (
    CwActionPickFortuneOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_invest_action import (
    CwActionPickInvestOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_megastar_action import (
    CwActionPickMegastarOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_partner_action import (
    CwActionPickPartnerOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_planner_action import (
    CwActionPickPlannerOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_star_tome_action import (
    CwActionPickStarTomeOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_supply_action import (
    CwActionPickSupplyOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_pick_wish_trial_action import (
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
    CwActionCollectOreParam: CwActionCollectOreOp,
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
    CwActionStartBattleParam: CwActionStartBattleOp,   # 终结(返回主循环战斗分支)
    CwActionOpenShopParam: CwActionOpenShopOp,         # terminal 承载行(执行抛,正常路径不可达)
    # 观察族(策略发出 CwActionObs = 环内重观察上报,不返回主循环;
    # 现役接线域 = 备战决策环,重观察执行半 = 宿主 CwScreenPrep
    # .reobserve_in_visit;其他域发出 = 宿主能力缺失 AssertionError 响亮暴露)
    CwActionObsParam: CwActionObsOp,
    # 事件线 pick 族(overlay act 段经工厂,机械体 = 各 overlay 画面
    # op act 确认链迁移体。终态契约:策略器产出 = 词表 Pick 子类型,kernel
    # Pick 族 = 纯函数内部返回值,不再进注册表)。
    CwActionPickEncounterParam: CwActionPickEncounterOp,
    CwActionPickSupplyParam: CwActionPickSupplyOp,
    CwActionPickMegastarParam: CwActionPickMegastarOp,
    CwActionPickPartnerParam: CwActionPickPartnerOp,
    CwActionPickPlannerParam: CwActionPickPlannerOp,
    CwActionPickInvestEnvParam: CwActionPickInvestOp,   # 投资两屏拆类后两行同指一 op(机械链同构;上报按 param 类型分派,投资两屏迁移批)
    CwActionPickInvestStrategyParam: CwActionPickInvestOp,
    CwActionPickFortuneParam: CwActionPickFortuneOp,   # pick-op-unify 并入
    CwActionPickWishTrialParam: CwActionPickWishTrialOp,   # pick-op-unify 并入
    CwActionPickStarTomeParam: CwActionPickStarTomeOp,   # pick-op-unify 并入(点卡即选)
    CwActionPickBoxCardParam: CwActionPickBoxCardOp,   # pick-op-unify 并入(点卡即选)
    CwActionPickExpertInviteParam: CwActionPickExpertInviteOp,   # pick-op-unify 并入(点卡即选)
}


def action_op_class_for_type(action_type: type) -> type[SrOperation]:
    """词表**类** → 动作 op 类(类级解析,不构造动作实例;注册完备测试
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
        '(:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_class_for(action: Action) -> type[SrOperation]:
    """词表实例 → 动作 op **类**(类级查询,不构造 op 实例)。

    消费面 = 终结判定与 ``terminal``/``terminal_wait`` 类属性读取
    (消费点经注册表读类属性,禁消费点私表)与执行器/商店落地门的
    (ctx, param, env) 组装构造(op 形态正本 = action_ops.md §1);
    行序语义同构造 helper。
    词表外类型 AssertionError 响亮暴露(语义:非法返回
    = 策略器 bug,禁静默跳过;文案中性,注册表现跨域共用)。"""
    for cls, op_cls in _REGISTRY.items():
        if isinstance(action, cls):
            return op_cls
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{type(action).__name__}'
        '(:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_for(action: Action, ctx: SrContext, env: object) -> SrOperation:
    """动作词表 → 动作 op 实例(构造 helper:注册表类级解析 +
    (ctx, param, env) 组装,新壳构造签名)。

    消费面 = overlay act 段(经工厂分派保持「意图类型 → 点击链」单一
    映射);执行器/商店落地门按 op 形态正本(action_ops.md §1)直接走
    ``action_op_class_for(action)(ctx, action, env=...)``。env 形参 =
    域执行环境结构化包(运行时不检查,项目既有风格)。词表外类型
    AssertionError 响亮暴露(语义同上)。"""
    return action_op_class_for(action)(ctx, action, env)
