"""货币战争 备战决策环 共享动作词表(kernel 桶)。

本模块是决策核(decision)与应用执行层(app)之间的**共享词汇**:PrepAction 动作全集、
动作键函数与统一观察视图 PrepObservation。纯 dataclass 标记 + 纯函数,零副作用、
零识别/执行逻辑——「执行一个动作」在 app/prep_actions.py 的 PrepActionExecutor,
「产出动作」在策略层 CwStrategy.decide_prep_screen 决策接口(ADR-0583 措辞:
契约方法不称钩子)。

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

from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar

# ===== 动作全集 =====


@dataclass
class PrepAction:
    """备战决策环动作标记基类(策略 → 框架的单步意图载体)。

    ``route_tag`` = 发射臂路线标签(T-159 备战旗标状态机 §3.3;桥
    ``bridge.decide_from_turn`` 从 ``Emitted.reason`` 透传,动作自带、
    无时序错位面)。定位 = 策略内部路由键(发射分支的构造事实,不随
    时间漂移、不维护状态),只回答「该次落地该不该清 S1 开店闩」的
    环路控制路由问题,**非**卖出资格面(资格单一源 = sell_gate 装配 A)
    、非放行证据(T-153 治理立场对表:禁检查器采信)。值域:现役发射位
    = m4_fuel_sell / interest_prep(单帧锁
    ``test_route_tag_whitelist`` 锁映射表);deploy_launch 类由动作类型
    (RunDeploy)承载不占本字段。kw_only 缺省 '' ⇒ 构造调用全向后兼容。
    """
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


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
    """卖备战席角色(slot=物理槽位 1-9;身份感知「卖谁」由策略层保证)。

    reason = 线账闭合孤儿证明载体(**记录非指令**,执行层不读;'' = 未标,
    为缺省形态)。纯归因遥测面(通道枚举×发射位填充)已随 2026-09-08
    用户归因遥测删除指令整体拆除,唯一承重填充值 = ``line_switch_
    collapse``(T-141 检查器豁免判别食物:线账闭合孤儿清算标记,授予
    须伴随登记簿线账闭合证明,ADR-0591 §4;检查器豁免键集单一源 =
    cw_state.SELL_BENCH_CONVERT_REASONS,键集保留非发射面)。字段带
    默认 '' ⇒ 类型消费全向后兼容;reason 不入幂等键(action_key 经
    字段 metadata 排除——reason 值不改变动作实例身份,幂等粒度 =
    类型 + 行为参数);prep 域不入 sim 账本(engine 转录按白名单挑字段)。
    """
    slot: int
    reason: str = field(default='', metadata={'action_key_exclude': True})


#: 卖出发射位值域闭集(2026-09-08 用户归因遥测删除指令后 = 唯一承重
#: 值)。原 ADR-0585 §3 批 4 的 5 通道值中,仅 line_switch_collapse 有
#: 存活填充位(凑息回拉换线闭合卖出载体+商店孤儿证明打标链);其余
#: 通道值/转化特化值的发射位填充已全撤,无填充位的枚举值不保留。
#: 转化特化值单一源 = cw_state.SELL_BENCH_CONVERT_REASONS(同轮买卖
#: 检查豁免键集,保留)。新增发射位先在此登记再接线(登记门:值漂移
#: 由 test_cw_sell_reason_matrix 双向暴露)。
SELL_BENCH_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',     # 线账闭合孤儿清算(T-141/ADR-0591 证明打标制)
})


#: 检查器孤儿豁免键集(同轮买后卖检查的孤儿清算豁免边;**与上方发射位
#: 值域登记门 SELL_BENCH_REASONS 分离的独立闭集**,T-180):两集当前同值
#: 但语义不同源——发射登记门的新增值不得静默放大豁免面(豁免面若随
#: 登记门生长即成振荡防空洞;同轮买卖振荡零容忍 = ADR-0267/0593 治理
#: 立场)。当前值 = line_switch_collapse(线账闭合孤儿清算证明标记,
#: 授予须伴随登记簿线账闭合事件,ADR-0591 §4)。三消费位 = sim/checks
#: /ledger 的 check_no_same_round_buy_sell 与 check_oscillation_xp_cap、
#: sim/checks/suspects 的 d1_same_round_pair_review(检查器/复盘面同键
#: 集,禁借道发射登记门)。值漂移由 test_cw_sell_reason_matrix 暴露。
SELL_BENCH_ORPHAN_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',
})


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
    """开商店(gold 备战帧同可见可读:玩家确认 2026-09-09「干净备战帧金币可见」,
    恢复局备战期金币无机制性例外——备战帧观察为 gold 覆盖写端之一,非「仅开态可读」)。
    ⚠️ W970 批 C 退役:生产路径改发
    :class:`OpenShop`(read_only 变体),本类仅存续于旧环/离线兼容面。"""


@dataclass
class EnsureShopClosed(PrepAction):
    """关商店(HP 只在关态可读)。⚠️ W970 批 C 退役:关店由商店决策空序列
    触发 CwOpCloseShop;开态清洁面板场景改发 :class:`OpenShop`(read_only)。"""


@dataclass
class OpenShop(PrepAction):
    """开商店意图(W970 批 C/§4.3.6;EnsureShop 意图退役后的承接形态)。

    read_only=False:显式开店 → 流程层编排商店动作循环(观察→decide_shop_screen
    →波执行→空序列 CwOpCloseShop→节点探针)。
    read_only=True:读数性开店(腾席链 b 取 gold 真值 / 开态清洁面板)→
    CwOpOpenShop(幂等:已开不点)→ 商店观察刷新 → **不调商店决策** →
    CwOpCloseShop → 回备战(M-6 门保持:free=0 不进买牌)。
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
    """组合(P1 过渡):整体部署 = CwScreenDeploy(v7 H-2:保 D-10 换血/同角色去重/前排保证/cap 门
    四项板上行为,P3 原子化时上移策略)。"""


@dataclass
class RunEquip(PrepAction):
    """组合(P1 过渡):全员装备 = CwOpEquipAll(P3 溶解为 WearEquip)。"""


@dataclass
class RunTools(PrepAction):
    """组合(工具执行批 ADR-0532):工具消耗 = CwOpTools(G1 准入 admitted
    工具动作逐件 drag + 21 号稿 §3.2 消耗确认通道;判据单一源 =
    cw_equip_env.evaluate_tool_actions,执行层禁第二套时机判断)。"""


# 动作全集白名单(F3 membership 校验;新动作加入全集时同步此处)
PREP_ACTION_TYPES: tuple = (
    DeferSpheres, BailToOuter, ClickSpheres, OpenBox, OpenTome, PickBoxCard,
    SellBench, SellDeployed, DeployMove, LevelUp,
    EnsureShopOpen, EnsureShopClosed, StartBattle,
    OpenShop,
    RunBuyPhase, RunDeploy, RunEquip, RunTools,
)
# ⚠️ 教训:**新增 PrepAction 必须同步登记本白名单**——漏登记时 validate 拒
# 「未知动作类型」,动作从未真正执行(OpenTome 曾漏登记,数百次 F3 拒绝
# 被误读为执行失败;F3 校验是最后防线,登记是入口门)。


def action_key(action: PrepAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数;SellBench(3) 与 SellBench(5) 各自计数)。

    带 ``action_key_exclude`` metadata 的字段不入键(现役 =
    SellBench.reason 卖出归因 + PrepAction.route_tag 发射臂路线标签
    [T-159 §3.3]):幂等粒度 = 行为参数,归因/路由标签不改变动作实例
    身份——同槽位不同归因是同一动作,禁拆成两个幂等键。
    """
    import dataclasses

    if dataclasses.is_dataclass(action):
        params = dict(vars(action))
        for f in dataclasses.fields(action):
            if f.metadata.get('action_key_exclude'):
                params.pop(f.name, None)
        if not params:
            return type(action).__name__   # 无字段 dataclass(StartBattle 等)→ 裸名
        return f'{type(action).__name__}({params})'
    return type(action).__name__


@dataclass
class PrepObservation:
    """备战决策环统一观察(决策单一输入,组合现成 reader 不新写识别)。

    P1 恒空字段(策略不得依赖):overlay_state / overlay_options / shop_cards。
    (owned_equips 原列本清单,已随 P4 观察接线转正——见下方装备域字段块。)

    分层语义:bench_chars/deployed_chars/deploy_vacancy 只在 heavy
    观察刷新(环入口 + 每个执行过的游戏动作后);light 步沿用上次 heavy 值(可能 stale,
    单线程内 stale 窗口 = 无动作步,安全)。轻字段(spheres/boxes/占用/shop_open/overlay)
    每步现读。
    局内事实不在帧上(容器化段 2:state 槽退役,黑板帧 = 纯视觉/占用
    观察载体,帧保留域封闭清单见设计件 §2.1-2;决策读 = session 容器
    单例 board_state_of,同帧同视图纪律)。
    state_gold_trusted = gold 仅 shop 开态可信(F2 门,heavy 刷新)。
    """
    state_gold_trusted: bool = False      # gold 是否可信(= heavy 时 shop 开)
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
    deploy_divergent: bool = False      # vacancy 分母双源分歧位(15 号稿批 C:
                                        # True=deployed 计数取的是低值仲裁,
                                        # 部署放行判定按 §4.2 延迟;准备面载体)
    deploy_stale: bool = False          # vacancy 陈旧位(True=缓存沿用:
                                        # cap/paddle 双缺,B5 陈旧值过门申报)
    shop_open: bool = False             # 锚点「按钮-收起」可见(每步现读)
    box_overlay_open: bool = False      # 武装箱 overlay(标识-请选择;每步现读)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号(每步现读)
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    # (back_size 字段已删(波 5b 死字段退役,写读闭环终端消费者零;决策链
    #  后排容量单一源 = 容器 back_capacity_of)。)
    overlay_state: str | None = None    # P5
    # 事件 overlay 检测(盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即 BailToOuter
    # 交外环分支 handler;实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)
    # ===== 装备域三路事实 P4 观察接线(ADR-0601 §3-C1 演进方向,T-171)=====
    # 采集点 = observe_full heavy 装配层(obs 域统一采集单一源);deployed
    # 名单已由上方 deployed_chars 覆盖,此三字段补 owned/occupied 两路。
    # None = 识别域资源未就绪(模板库/区域/TM grays 缺,原因在采集层
    # log 留证),消费方按各自 fail/保守通道处理;[]/{} = 真读到空。
    owned_equips: list | None = None     # 装备区 owned 件名池(全量含工具,W209g 口径;heavy 刷新)
    # occupied_equips 键坐标系:row ∈ 'front'|'back',slot = 画面物理槽位
    # 1-based(前排 1-4 / 后排 1-选档 N,与 prep_actions §13.1 slot 语义同域);
    # 取值时机 = 生成期快照(heavy 帧现读)。
    occupied_equips: dict | None = None  # 已穿装备明细 {(row, 物理槽位): [件名]}
    # 消费 = 装备计划步后排槽位戳记上界(执行域)。决策链后排容量单一源
    # 仍 = 容器 back_capacity_of,勿回接本字段(波 5b 删除的 back_size 是
    # 决策链死字段;本字段是执行域戳记消费,两者不同源不互通)。
    back_layout_slots: int | None = None  # 后排布局选档槽数(select_back_layout 直传;None=布局未知态双弃权帧)
