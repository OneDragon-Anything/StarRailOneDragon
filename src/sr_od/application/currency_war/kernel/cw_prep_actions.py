"""货币战争 备战决策环 共享动作词表(kernel 桶)。

本模块是决策核(decision)与应用执行层(app)之间的**共享词汇**:PrepAction 动作全集、
动作键函数与统一观察视图 PrepObservation。纯 dataclass 标记 + 纯函数,零副作用、
零识别/执行逻辑——「执行一个动作」在 app/prep_actions.py 的 PrepActionExecutor,
「产出动作」在策略层 CwStrategy.decide_prep_action 系钩子。

为何落在 kernel:决策核产出这些动作、执行层消费这些动作,任一侧定义都会造成
另一侧的反向依赖(分包依赖矩阵 §3.2:decision 只可依 kernel/data;app 依一切)。
共享词表归 kernel 是唯一同时满足两侧的方向。

slot 语义全局统一:**物理槽位** —— 备战栏 1-9 / 前排 1-4 / 后排 1-N;非 bench 列表下标!
与族 A(cw_state.Action 策略动作)同名类(SellBench/DeployMove/SellDeployed)的坐标系对照:
族 B 物理槽位 = 族 A 下标 + 1(bench 域);deployed 域两族结构不同(族 B=row+slot
物理排槽位,族 A=紧缩列表下标)——完整对照表见 cw_state.py Action 节约定块。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState

# ===== 动作全集 =====


class PrepAction:
    """备战决策环动作标记基类(策略 → 框架的单步意图载体)。"""


@dataclass
class DeferSpheres(PrepAction):
    """控制流:奖励球留置(本环不再尝试;不计 stall,计步数)。"""


@dataclass
class BailToOuter(PrepAction):
    """控制流:中止本环交外环(弹层/事件;框架信号不走验证链)。"""
    reason: str = ""


@dataclass
class ClickSpheres(PrepAction):
    """点奖励球(带上界批,大球优先,内验早停;掉箱即停回环交规则统筹)。"""
    max_k: int = 1


@dataclass
class OpenBox(PrepAction):
    """开补给箱(点「开启」→ 弹武装箱 overlay;开箱即腾席)。slot=None → 第一箱。"""
    slot: int | None = None


@dataclass
class OpenTome(PrepAction):
    """开秘密典籍(点槽两次:选中→开启 → 弹星徽四选一;开典籍即腾席+loop 0i 接管选卡)。

    建档:投资策略「秘密典籍」给的红金典籍道具占备战席 1 槽(类补给箱);
    选卡决策在 loop 0i handler(板上阵营匹配),本动作只负责把典籍点开。slot=None → 第一典籍。
    """
    slot: int | None = None


@dataclass
class PickBoxCard(PrepAction):
    """武装箱 4 选 1 点卡。card_idx=None → 执行器内嵌默认选卡(v7 M-3:P1 住执行器,P5 上移策略)。"""
    card_idx: int | None = None


@dataclass
class SellBench(PrepAction):
    """卖备战席角色(slot=物理槽位 1-9;身份感知「卖谁」由策略层保证)。"""
    slot: int


@dataclass
class SellDeployed(PrepAction):
    """卖已上阵角色(row=front/back + 物理槽位)。"""
    row: str
    slot: int


@dataclass
class DeployMove(PrepAction):
    """bench → 上阵单步拖拽(腾席链专用;组合部署走 RunDeploy 保四项板上行为)。"""
    from_slot: int
    to_row: str            # "front" / "back"
    to_slot: int


@dataclass
class LevelUp(PrepAction):
    """买经验升等级(点「购买经验」循环至 level+1;cap+1 = 腾席链 b 步)。"""


@dataclass
class EnsureShopOpen(PrepAction):
    """开商店(gold 只在开态可读)。⚠️ W970 批 C 退役(dd-017):生产路径改发
    :class:`OpenShop`(read_only 变体),本类仅存续于旧环/离线兼容面。"""


@dataclass
class EnsureShopClosed(PrepAction):
    """关商店(HP 只在关态可读)。⚠️ W970 批 C 退役(dd-017):关店由商店决策空序列
    触发 CloseShopOp;开态清洁面板场景改发 :class:`OpenShop`(read_only)。"""


@dataclass
class OpenShop(PrepAction):
    """开商店意图(W970 批 C/§4.3.6,dd-017;EnsureShop 意图退役后的承接形态)。

    read_only=False:显式开店 → 流程层编排商店动作循环(观察→decide_shop_screen
    →波执行→空序列 CloseShopOp→节点探针)。
    read_only=True:读数性开店(腾席链 b 取 gold 真值 / 开态清洁面板)→
    OpenShopOp(幂等:已开不点)→ 商店观察刷新 → **不调商店决策** →
    CloseShopOp → 回备战(M-6 门保持:free=0 不进买牌)。
    """
    read_only: bool = False


@dataclass
class StartBattle(PrepAction):
    """出战(环出口;含未达上限确认;验证=备战标识消失)。StartBattle 豁免屏蔽。"""


@dataclass
class RunBuyPhase(PrepAction):
    """组合(P1 过渡):整段买牌 = RunBuyPhase(执行器组合分支已随 BuyShopCards 壳退役删除;动作类型保留供期望态/对账兼容)。"""


@dataclass
class RunDeploy(PrepAction):
    """组合(P1 过渡):整体部署 = DeployBenchOp(v7 H-2:保 D-10 换血/同角色去重/前排保证/cap 门
    四项板上行为,P3 原子化时上移策略)。"""


@dataclass
class RunEquip(PrepAction):
    """组合(P1 过渡):全员装备 = EquipAllOp(P3 溶解为 WearEquip)。"""


# 动作全集白名单(F3 membership 校验;新动作加入全集时同步此处)
PREP_ACTION_TYPES: tuple = (
    DeferSpheres, BailToOuter, ClickSpheres, OpenBox, OpenTome, PickBoxCard,
    SellBench, SellDeployed, DeployMove, LevelUp,
    EnsureShopOpen, EnsureShopClosed, StartBattle,
    OpenShop,
    RunBuyPhase, RunDeploy, RunEquip,
)
# ⚠️ 教训:**新增 PrepAction 必须同步登记本白名单**——漏登记时 validate 拒
# 「未知动作类型」,动作从未真正执行(OpenTome 曾漏登记,数百次 F3 拒绝
# 被误读为执行失败;F3 校验是最后防线,登记是入口门)。


def action_key(action: PrepAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数;SellBench(3) 与 SellBench(5) 各自计数)。"""
    import dataclasses

    if dataclasses.is_dataclass(action):
        params = dict(vars(action))
        if not params:
            return type(action).__name__   # 无字段 dataclass(StartBattle 等)→ 裸名
        return f'{type(action).__name__}({params})'
    return type(action).__name__


@dataclass
class PrepObservation:
    """备战决策环统一观察(决策单一输入,组合现成 reader 不新写识别)。

    P1 恒空字段(策略不得依赖):overlay_state / overlay_options / shop_cards /
    owned_equips(P4 工具域接线)。

    分层语义:state/bench_chars/deployed_chars/deploy_vacancy 只在 heavy
    观察刷新(环入口 + 每个执行过的游戏动作后);light 步沿用上次 heavy 值(可能 stale,
    单线程内 stale 窗口 = 无动作步,安全)。轻字段(spheres/boxes/占用/shop_open/overlay)
    每步现读。
    """
    state: GameState | None = None        # heavy 重读;gold 仅 shop_open 时可信
    state_gold_trusted: bool = False      # state.gold 是否可信(= heavy 时 shop 开)
    # 子态可读性(observe_full 产出;heavy 刷新/
    # light 沿用)——node_seq/shop_cards 本帧是否可读(按子态
    # 尽力读,跨步拼装全面性)。
    substate: dict = field(default_factory=dict)
    bench_chars: list[BenchChar] = field(default_factory=list)   # heavy: SIFT 身份
    deployed_chars: list[BenchChar] = field(default_factory=list)
    spheres: list = field(default_factory=list)       # read_reward_spheres [(color, Point, r)]
    boxes: list = field(default_factory=list)         # read_supply_boxes [(slot, Point)]
    tomes: list = field(default_factory=list)         # read_tomes [(slot, Point)] 秘密典籍
    free_bench_slots: int = 0           # 9 − 占用(角色+箱都占席;CV 每步现读)
    deploy_vacancy: int = 0             # deploy_cap − deployed_count(heavy 刷新)
    shop_open: bool = False             # 锚点「按钮-收起」可见(每步现读)
    box_overlay_open: bool = False      # 武装箱 overlay(标识-请选择;每步现读)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号(每步现读)
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    back_size: int = 6
    overlay_state: str | None = None    # P5
    # 事件 overlay 检测(盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即 BailToOuter
    # 交外环分支 handler;实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)
