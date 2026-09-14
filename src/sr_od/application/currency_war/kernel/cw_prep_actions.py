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
class ClickSpheres(PrepAction):
    """点奖励球(R4 坐标参数化机械动作:载荷 = 有序球坐标点击列表)。

    ``points`` = 按点击顺序排列的球心坐标 (x, y)(1080p 游戏空间,与
    ``PrepObservation.spheres`` 的 Point 同系)。挑选逻辑(大球优先/
    上界截断)归决策侧 kernel 单一源 = :func:`select_sphere_clicks`,
    发射位调用之;执行器纯机械逐个点,零读屏零排序。逻辑态按载荷
    精确摘球(坐标匹配,``cw_screen_prep._project_prep_obs``)。
    """
    points: tuple[tuple[int, int], ...] = ()


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


# ===== 原子动作扩域(R2 组合壳溶解 / R8 工具按消耗品各立类;design.md
#      unified-action-factory §2.6)=====
#
# 词表边界(design §2.1):框架词表 = 原子动作 + 坐标参数化机械动作;
# 组合编排/授权循环/批内挑选逻辑 = 策略实现,不入词表。下列各类的
# 计划/授权面在发射位(kernel 计划构造 + 判据准入),类本体只载
# 「单步拖拽」参数。
#
# 通用坐标系声明(装备域两类目标,全族共用):
# - 装备源件 = owned 装备网格内 icon,按 ``item_name`` 机械现读定位
#   (执行坐标边合法现读;坐标不入动作——网格 reflow 会使坐标失真,
#   名字定位是唯一稳锚)。
# - 角色目标槽位 ``row``/``slot``:row ∈ 'front'|'back'(画面物理排);
#   slot = 画面物理槽位 1 基(前排 1-4 / 后排 1-选档 N;非列表下标,
#   与 prep_actions §13.1 slot 语义同域)。取值时机 = 生成期快照
#   (发射位从备战观察/容器槽位表现读;同一 visit 内 tracked 账随动,
#   槽位跨动作组恒稳——置 None 不移位坐标系,ADR-0392)。

@dataclass
class WearEquip(PrepAction):
    """穿装备(装备库 owned 件 → 目标角色物理槽位;R2 穿戴原子通路)。

    计划构造 = kernel ``build_equip_wear_plan``(自执行器模块迁居,
    决策侧逐帧现算);发射序即执行序(决策核逐帧取首项)。逻辑态 =
    ``obs.owned_equips`` 摘件(视觉域,与 OpenBox/OpenTome 同形);
    穿没穿归观察写入边对账(裁决 3 零比对出生:体内零 CV-diff 验穿)。
    ``char_name`` = 目标角色注册名('' = front-only 回退步,拖点 =
    前排空槽 avatar,与 EquipWearStep 契约同形)。
    """
    item_name: str
    char_name: str
    row: str            # 'front' | 'back'(见上方通用坐标系声明)
    slot: int           # 画面物理槽位 1 基(前排 1-4 / 后排 1-N)


@dataclass
class FurnaceUse(PrepAction):
    """冶金炉(R8 按消耗品各立类;双模式)。

    - target_kind='equip':拖装备 = 原地变异同类型随机(target =
      装备库 owned 件,``item_name``;产物不可预知 → 随机面观察收口,
      ``EQUIP_WRITE_SIDES['冶金炉']`` 负写端在册);
    - target_kind='char':拖角色 = 全拆 + 每件变异随机(target =
      角色槽位,``row``/``slot``;确定面 = 穿戴域 → 库存域全量迁移,
      变异产物 = 随机面观察收口)。
    """
    target_kind: str    # 'equip' | 'char'(作用对象模式;值域封闭)
    item_name: str = ''  # target_kind='equip':装备库 owned 件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基


@dataclass
class PrivilegeCardUse(PrepAction):
    """特权赋予卡(R8;双腿)。

    - target_kind='equip'(库存腿,现役执行臂):确定变换 = target 件
      名替换为对应·特权名(映射单一源 = ``cw_effect_inventory.
      privilege_counterpart``,写端 = ``transform_equip_to_privilege``);
    - target_kind='char'(拖角色腿):该角色已穿进阶装备随机一件变
      特权——「哪件被选」= 随机面 → 逻辑态只写工具 −1,选定后确定面
      归观察收口(``transform_worn_equip_to_privilege`` 桥在册)。
    """
    target_kind: str    # 'equip' | 'char'(值域封闭,同 FurnaceUse)
    item_name: str = ''  # target_kind='equip':被变换的进阶成品件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基


@dataclass
class WrenchUse(PrepAction):
    """拆装扳手(R8):target = 角色槽位(取下该角色全部穿戴,装备归属
    面回区);工具消耗品 −1(用后消失)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class PrecisionWrenchUse(PrepAction):
    """精密拆装扳手(R8):target = 角色槽位(同 WrenchUse);无限次用,
    工具库存面不递减(重复获得改 +1 金 = 贡献算术,获得回执窗在册)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class StaffProjectorUse(PrepAction):
    """员工投影仪(R8 投影仪按型号两类之一):target = 角色槽位
    (在备战席创造该角色 1 星复制);费用门 = 3 费及以下(门表单一源 =
    ``cw_affix_effects`` 投影仪费用门行),门由发射位判据面辖。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class PerfectProjectorUse(PrepAction):
    """完美投影仪(R8 投影仪按型号两类之二):target = 角色槽位
    (同 StaffProjectorUse 但无费用门)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class LuckyTokenUse(PrepAction):
    """好运令牌(R8):拖到角色 → 从其推荐进阶装备中获得一件。

    ⚠️ 发射位挂账(裁决 1/R9 纪律):作用对象判据面现役 fail-closed
    永不进准入(``cw_equip_env.evaluate_tool_actions`` rc_missing 拒因
    在册)——类随族立档 + 注册行,发射位禁无判据发射;判据面建模批
    补档(知识缺口登记 = ``flow/action-logic-state.md`` §7 好运令牌行)。
    """
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


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
    ClickSpheres, OpenBox, OpenTome,
    SellBench, SellDeployed, DeployMove, LevelUp,
    WearEquip,
    FurnaceUse, PrivilegeCardUse, WrenchUse, PrecisionWrenchUse,
    StaffProjectorUse, PerfectProjectorUse, LuckyTokenUse,
    StartBattle,
    OpenShop,
    RunDeploy, RunEquip, RunTools,   # 组合壳(R2):2a 原子通路就位后零构造,
)                                    # 类与登记行删除归批2b 归一删除面
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


#: 点球单批硬上限(原执行器 SPHERE_MAX_CLICKS 常量迁居 kernel:挑选上界
#: 归挑选函数,执行器只机械点载荷;防识别抖动死循环的防线语义不变)。
SPHERE_CLICK_HARD_CAP: int = 12


def select_sphere_clicks(spheres: list, cap: int,
                         ) -> tuple[tuple[int, int], ...]:
    """奖励球挑选 kernel 单一源(R4 ClickSpheres 改形;纯函数)。

    输入 = ``PrepObservation.spheres``([(color, Point, r)];颜色与半径
    仅排序消费,不进载荷);``cap`` = 本批点击预算(发射位常量,如
    mandate_v1 SPHERE_CLICK_BATCH_MAX_K)。输出 = 有序 (x, y) 点击列——
    大球优先(r 降序;稳定排序保持观察序),上界 = min(cap, 硬上限
    SPHERE_CLICK_HARD_CAP)。席满让路门/占席球语义归发射位(既有门),
    本函数不辖。

    消费面:发射位(mandate_v1 entry)构造 ClickSpheres 载荷;执行器
    零排序零截断纯机械点(第二实现禁)。
    """
    budget = max(0, min(int(cap), SPHERE_CLICK_HARD_CAP))
    ordered = sorted(spheres, key=lambda t: t[2], reverse=True)[:budget]
    return tuple((int(p.x), int(p.y)) for _c, p, _r in ordered)


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
    # 事件 overlay 检测(盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即
    # 交回外循环分支 handler;实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
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
