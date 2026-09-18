"""全动作单一注册表(统一动作工厂批1;design.md §2.3):词表类 → 动作
op 类一张表,``action_op_for`` = 全动作唯一注册点(单一工厂),
``action_op_class_for`` = 类级查询(终结判定消费面,不构造实例),
``action_op_class_for_type`` = 词表**类**级查询(注册完备锁消费口,
不构造动作实例)。

**收编状态**:商店域五行批1 首批在册;备战域批3 收编在册(design.md
§2.4);事件线 pick 族批4 收编在册(§2.5,overlay act 段自此经工厂)。
注册完备锁(批4)自此以本表为机械约束对象:遍历统一词表
``cw_vocab.CW_ACTION_TYPES`` + 事件线 pick 族 ``cw_events.PICK_ACTION_
TYPES``,逐类断言本表解析可命中(测试 = sr-od-test test_cw_unified_
action_4)。(原 CompTransaction 行已随 unified-action-factory 批2b R3
删除——整档替换宏动作全链退役。)

**同名动作双域行更替申报(批3)**:词表归一(批2b)后 ``CwActionSellBenchParam``/
``CwActionLevelUpParam`` 两类为商店/备战共用词表,单一表一键一行——两行自批1 商店
op 更替为备战 op(``PrepSellBenchOp``/``PrepLevelUpOp``)。依据:发射面
策略收缩至备战期后(flow/screens-actions-capability §5 判例),两类的
生产发射只在备战域,备战 op 即唯一活执行路径;商店域 op 类
(``cw_sell_bench_action.SellBenchOp``/``cw_level_up_action.LevelUpOp``)
随行更替退出注册(文件保留为商店域能力面,生产不可达:商店决策面
decide_shop_action 仅产 CwActionBuyCardParam/CwActionRefreshShopParam/CwActionCloseShopParam),本注记 = 其
注销登记。

**注册行顺序敏感**:``action_op_class_for`` 按行序 isinstance 首中即返
——is-a 链的父类行必须在子类可独立匹配处之前兜底(子类共享父 op 时
父行即足;子类需独立 op 时其行必须插在父行之前)。现役先例 =
``CwActionLevelUpShopParam`` is-a ``CwActionLevelUpParam`` 同备战 op(单击,无子类独立行)。分区
注释按「族 → 基类兜底行 → 具体类行」摆放。
"""
from __future__ import annotations

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
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickSupplyParam,
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
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_buy_card_action import (
    BuyCardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_click_spheres_action import (
    ClickSpheresOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_close_shop_action import (
    CloseShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_deploy_move_action import (
    DeployMoveOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_bookcard_action import (
    OpenBookcardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_box_action import (
    OpenBoxOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_shop_action import (
    OpenShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_tome_action import (
    OpenTomeOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
    EncounterPickOp,
    MegastarPickOp,
    PartnerPickOp,
    PlannerPickOp,
    SupplyPickOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_prep_level_up_action import (
    PrepLevelUpOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_prep_sell_bench_action import (
    PrepSellBenchOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_refresh_shop_action import (
    RefreshShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_sell_deployed_action import (
    SellDeployedOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_start_battle_action import (
    StartBattleOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_tool_use_action import (
    ToolUseOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_wear_equip_action import (
    WearEquipOp,
)

# 商店族(批1 首批在册;行序敏感,见模块头「注册行顺序敏感」节)
_REGISTRY: dict[type, type[ActionOp]] = {
    CwActionBuyCardParam: BuyCardOp,
    CwActionRefreshShopParam: RefreshShopOp,
    CwActionCloseShopParam: CloseShopOp,
    # 备战族(批3 收编;CwActionSellBenchParam/CwActionLevelUpParam 两行自批1 商店行更替,见模块头
    # 「同名动作双域行更替申报」节。CwActionLevelUpShopParam = 同字段双类型
    # (词表摊平后 is-a 链消亡),显式独立行,与 CwActionLevelUpParam 同备战 op)
    CwActionSellBenchParam: PrepSellBenchOp,
    CwActionLevelUpParam: PrepLevelUpOp,
    CwActionLevelUpShopParam: PrepLevelUpOp,
    CwActionDeployMoveParam: DeployMoveOp,
    CwActionSellDeployedParam: SellDeployedOp,
    CwActionWearEquipParam: WearEquipOp,
    CwActionClickSpheresParam: ClickSpheresOp,
    CwActionOpenBoxParam: OpenBoxOp,
    CwActionOpenTomeParam: OpenTomeOp,
    CwActionOpenBookcardParam: OpenBookcardOp,
    CwActionFurnaceUseParam: ToolUseOp,
    CwActionPrivilegeCardUseParam: ToolUseOp,
    CwActionWrenchUseParam: ToolUseOp,
    CwActionPrecisionWrenchUseParam: ToolUseOp,
    CwActionStaffProjectorUseParam: ToolUseOp,
    CwActionPerfectProjectorUseParam: ToolUseOp,
    CwActionLuckyTokenUseParam: ToolUseOp,
    # 转场族(批3)
    CwActionStartBattleParam: StartBattleOp,   # 基类契约在册例外(返回值 = 点击序列已执行)
    CwActionOpenShopParam: OpenShopOp,         # terminal 承载行(execute 抛,正常路径不可达)
    # 事件线 pick 族(批4;design.md §2.5——overlay act 段经工厂,机械体
    # = 各 overlay 画面 op act 确认链逐字迁移,域 env = OverlayPickExecEnv。
    # 终态契约 §2.2 注册行换键名:策略器产出 = 词表 Pick 子类型,kernel
    # Pick 族 = 纯函数内部返回值,不再进注册表)。
    CwActionPickEncounterParam: EncounterPickOp,
    CwActionPickSupplyParam: SupplyPickOp,
    CwActionPickMegastarParam: MegastarPickOp,
    CwActionPickPartnerParam: PartnerPickOp,
    CwActionPickPlannerParam: PlannerPickOp,
}


def action_op_class_for_type(action_type: type) -> type[ActionOp]:
    """词表**类** → 动作 op 类(类级解析,不构造动作实例;批4 注册完备锁
    消费口——design.md §2.5「经注册表类级查询,不构造业务动作实例」)。

    行序语义与 :func:`action_op_class_for` 的 isinstance 首中同构:实例
    解析 ``isinstance(a, K)`` ⟺ 类级 ``issubclass(type(a), K)``,故按行
    序 issubclass 首中即同语义(is-a 兜底一致,CwActionLevelUpShopParam 先例)。词表
    外类型 AssertionError 响亮暴露(语义同上)。"""
    for cls, op_cls in _REGISTRY.items():
        if issubclass(action_type, cls):
            return op_cls
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{action_type.__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_class_for(action: Action) -> type[ActionOp]:
    """词表实例 → 动作 op **类**(类级查询,不构造 op 实例)。

    消费面 = 终结判定与 ``terminal``/``terminal_wait`` 类属性读取
    (design.md §2.4「终结等待时长 = op 类属性,消费点经注册表读类属性,
    禁消费点私表」);行序语义同 ``action_op_for``。词表外类型
    AssertionError 响亮暴露(沿用 ADR-0517 决策 9 语义:非法返回 =
    策略器 bug,禁静默跳过;文案中性,注册表现跨域共用)。"""
    for cls, op_cls in _REGISTRY.items():
        if isinstance(action, cls):
            return op_cls
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')


def action_op_for(action: Action) -> ActionOp:
    """动作词表 → 动作 op(全动作唯一注册点;行序 isinstance 首中即返,
    类级解析单一源 = ``action_op_class_for``)。词表外类型 AssertionError
    响亮暴露(语义同上)。"""
    return action_op_class_for(action)(action)
