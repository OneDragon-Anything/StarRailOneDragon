"""货币战争交互 overlay 生命周期注册表(单一枚举点)。

每个 overlay 一条 :class:`OverlaySpec` 声明(识别锚/语义类/退场动作/派发序),
五个消费面(P0 清场 / director bail / cw_loop 派发 / 退出恢复链 /
UPPER_SCREENS 帧态门派生段)按字段派生消费,消灭「新增画面要手工同步多处」的
结构性缺口(ADR-0269 病灶;设计单一源 = 设计收口终版五条定案)。

**切换状态**:注册表 + 一致性断言就绪;
B 面(director bail 扫描,cw_screen_prep 事件 overlay 检测)已切换为消费
``derive_decision()``;A 面(P0 清场)已切换为消费 ``derive_clearable()``
(桥接点 = ``cw_screen_prep.ENTRY_OVERLAY_CLOSE``,派生映射,消费循环
未变;2026-09-03 gate 清尾批随消费方迁址——gate 模块已退役);其余消费面
(cw_loop 分支 / 退出链)尚未切换。全部切换完成前,
本表对未切换面是「声明 + 锁」,不是运行时唯一判定源。

C1 红线(机器化于测试仓 ``test_cw_overlay_registry.py``):
``semantic='decision'`` ⇒ ``closable is False``——关闭即丢决策内容的交互
overlay(选卡/选择类,曾实证遭遇节点被清场误关,C1 事故)禁止进清场派生集。

**桶归属 = kernel(共享声明表,零包内依赖)**:UPPER_SCREENS 帧态门拼装在
kernel(``cw_obs_core``),包布局矩阵禁 kernel→obs 边(kernel 只许依 data);
本表是纯声明(dataclass + 字符串常量,无任何包内 import),落 kernel 使
kernel 消费面合法,obs/app 消费面(obs→kernel / app→kernel)同样合法。
"""
from __future__ import annotations

from dataclasses import dataclass

#: 语义类:decision = 有专属 handler 的交互 overlay(选卡/选择即推进,关闭即丢决策内容)
SEMANTIC_DECISION: str = 'decision'
#: 语义类:display = 展示型弹窗(无决策内容,关闭即走)
SEMANTIC_DISPLAY: str = 'display'
#: 语义类:system = 流程性弹窗(确认/提示/节点容器)
SEMANTIC_SYSTEM: str = 'system'

#: 退场动作:点 close_area 按钮(清场/退局链共用载荷)
CLOSE_ACTION_AREA: str = 'close_area'
#: 退场动作:点裸坐标(close_point 载荷,1080p)
CLOSE_ACTION_POINT: str = 'point'
#: 退场动作:按 ESC
CLOSE_ACTION_ESC: str = 'esc'
#: 退场动作:交专属 handler 消化(decision 类常态)
CLOSE_ACTION_HANDLE: str = 'handle'

#: 恢复/退局面动作:派 handler 消化
RECOVERY_HANDLE: str = 'handle'
#: 恢复/退局面动作:按 ESC
RECOVERY_ESC: str = 'esc'
#: 恢复/退局面动作:点返回按钮(close_area 载荷)
RECOVERY_BACK_BUTTON: str = 'back_button'
#: 恢复/退局面动作:复用 close_action 载荷(close_area 或 point)离屏
RECOVERY_CLOSE: str = 'close'


@dataclass(frozen=True)
class OverlaySpec:
    """单个交互 overlay 的生命周期声明(识别/语义/退场/派发)。"""

    # ── 识别 ──
    # 键;必须已建档于 assets/game_data/screen_info(与 screen_info 同键空间)
    screen_name: str
    # 识别锚 area 名(五消费面统一走此锚,禁各自再写锚)
    anchor_area: str
    # ── 语义 ──
    # 'decision' | 'display' | 'system'(SEMANTIC_* 常量)
    semantic: str
    # 第二锚(可选;双锚防误派;非空 = 同帧双命中才派发)
    anchor_area_alt: str = ''
    # 专属 handler 类名;decision 恒非空;'' = 无(清场/兜底消化)
    handler_id: str = ''
    # 可清场否;decision 恒 False(C1 红线,一致性测试断言)
    closable: bool = False
    # ── 退场动作 ──
    # 'close_area' | 'point' | 'esc' | 'handle'(CLOSE_ACTION_* 常量)
    close_action: str = CLOSE_ACTION_AREA
    # close_action='close_area' 时必填(清场/退局链共用)
    close_area: str = ''
    # close_action='point' 时必填(1080p 界内,一致性测试校验)
    close_point: tuple[int, int] | None = None
    # ── 派发与计数 ──
    # C 面派发优先序(全表唯一,一致性测试断言;非 C 面消费的 gate/退局-only
    # 条目排在所有分支条目之后)
    dispatch_priority: int = 0
    # 恢复/退局面动作:'esc'|'back_button'|'handle'|'close'(RECOVERY_* 常量)
    recovery_exit: str = RECOVERY_CLOSE
    # director bail 同因键后缀('事件overlay:' 前缀由消费方拼;decision 类
    # 必填且全表唯一,一致性测试断言)
    bail_tag: str = ''
    # 未建档条目 = False(实机建档后置 True
    # 并补 screen_name/anchor_area 终值);False 条目不参与任何派生
    # (UPPER_SCREENS/清场集/bail 扫描集),一致性测试豁免其建档断言
    active: bool = True


#: 注册表(唯一枚举点)。声明序 = UPPER_SCREENS 派生段顺序(与迁移前常量
#: 逐位一致);C 面派发序用 dispatch_priority 字段表达,与声明序无关。
OVERLAY_REGISTRY: tuple[OverlaySpec, ...] = (
    # ── decision(9 条;= 现 director bail 清单成员,C1 红线 closable=False)──
    OverlaySpec(
        screen_name='货币战争-列车同行',
        anchor_area='标识-选择伙伴',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenPartner',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=2,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='partner',
    ),
    OverlaySpec(
        screen_name='货币战争-祈愿试炼',
        anchor_area='标识-祈愿试炼',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenWishTrial',
        close_action=CLOSE_ACTION_HANDLE,
        # 派发序:必须在道具详情(19,未激活)之前——祈愿选项名含「聘用书」,
        # 曾被道具详情分支截胡(实机死循环实锤);序提前后负条件即不需要
        dispatch_priority=11,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='wish_trial',
    ),
    OverlaySpec(
        screen_name='货币战争-遭遇节点',
        anchor_area='标识-遭遇节点',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenEncounter',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=4,
        # 退局面(2026-09-13 退局调度器架构):退出 op 不再内联处理本画面,
        # 处理单一源 = CwScreenEncounter(loop 分发);本表 recovery_exit 是
        # 本表恢复链自身的出口声明,与退出 op 解耦
        recovery_exit=RECOVERY_BACK_BUTTON,
        bail_tag='encounter',
    ),
    OverlaySpec(
        screen_name='货币战争-投资策略',
        anchor_area='标识-请选择投资策略',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenInvestStrategy',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=6,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='invest_strategy',
    ),
    OverlaySpec(
        screen_name='货币战争-投资环境',
        anchor_area='标识-投资环境',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenInvestEnv',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=7,
        # 退局面(2026-09-13):本画面由 loop 分发 CwScreenInvestEnv 处理,
        # 退出 op 不再内联(处理单一源在画面 op)
        recovery_exit=RECOVERY_BACK_BUTTON,
        bail_tag='invest_env',
    ),
    OverlaySpec(
        screen_name='货币战争-盛会之星',
        anchor_area='标识-盛会之星',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenMegastar',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=3,
        # ⚠️ 挂账更新(2026-09-13 退局调度器架构):旧「退出 op 盛会之星分支
        # 直点门图标」已删——本画面由 loop 分发 CwScreenMegastar 处理(选候选
        # +确认)。recovery_exit=esc 与实际恢复出口(点候选+确认离开)不符的
        # 元数据修正仍按原挂账待 D 面统一切换时一并重推
        recovery_exit=RECOVERY_ESC,
        bail_tag='megastar',
    ),
    # display/system 交替段(声明序对齐 UPPER_SCREENS 派生段)
    # 展示型奖励总览:环入口可一键关(清场派生集成员,A 面消费)
    OverlaySpec(
        screen_name='货币战争-积分奖励',
        anchor_area='标识-积分奖励',
        semantic=SEMANTIC_DISPLAY,
        closable=True,
        close_area='按钮-关闭',
        dispatch_priority=15,
        recovery_exit=RECOVERY_CLOSE,
    ),
    OverlaySpec(
        screen_name='货币战争-简报',
        anchor_area='标识-本场对局首领',
        semantic=SEMANTIC_SYSTEM,
        handler_id='CwScreenBriefing',
        close_action=CLOSE_ACTION_HANDLE,
        # P2/P3 开局位面简报(三 boss+词缀+下一步),0 系最前消化(全屏 OCR
        # 密集屏,头部 find_area 优先命中绕开全屏 OCR 依赖)
        dispatch_priority=1,
        recovery_exit=RECOVERY_CLOSE,
    ),
    # 中断挑战弹窗:流程性(退局/挂起语义),环入口可一键关
    OverlaySpec(
        screen_name='货币战争-中断挑战弹窗',
        anchor_area='标识-中断挑战',
        semantic=SEMANTIC_SYSTEM,
        closable=True,
        close_area='按钮-关闭',
        dispatch_priority=16,
        # 退局链现状 = 点「放弃并结算」(按钮域动作);D 面切换时按按钮域
        # 载荷精确化,先以点关闭钮作恢复口径
        recovery_exit=RECOVERY_CLOSE,
    ),
    OverlaySpec(
        screen_name='货币战争-未达上限警告',
        anchor_area='标识-未达上限警告',
        semantic=SEMANTIC_SYSTEM,
        handler_id='CwScreenDeployNotFull',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=5,
        recovery_exit=RECOVERY_HANDLE,
    ),
    OverlaySpec(
        screen_name='货币战争-提示-前台无角色',
        anchor_area='标识-无角色提示',
        semantic=SEMANTIC_SYSTEM,
        close_area='按钮-确认',
        dispatch_priority=14,
        recovery_exit=RECOVERY_CLOSE,
    ),
    # 武装箱弹窗:四选一选卡有专属 handler(0f),但**也是现清场表成员**——
    # 环入口清它 = 现行生产行为;语义归 system(非 decision)保两维现状:
    # bail 扫描集(= decision 条目)不加成员、清场派生集不减成员。
    # 「关闭即丢一次开箱选择」的取舍与补给同型,见补给条注释。
    OverlaySpec(
        screen_name='货币战争-武装箱弹窗',
        anchor_area='标识-简易武装箱',
        semantic=SEMANTIC_SYSTEM,
        handler_id='CwScreenArmoryBox',
        closable=True,
        close_area='按钮-关闭',
        dispatch_priority=9,
        recovery_exit=RECOVERY_HANDLE,
    ),
    OverlaySpec(
        screen_name='货币战争-商店刷新概率表',
        anchor_area='标识-刷新概率表',
        semantic=SEMANTIC_DISPLAY,
        # 不进清场派生集(非 closable,零行为前提);
        # close_point 载荷供 cw_loop 0e2 / 恢复链复用
        close_action=CLOSE_ACTION_POINT,
        # × 位置 VLM 定位(实测坐标);无关闭按钮 area
        close_point=(1501, 263),
        dispatch_priority=10,
        recovery_exit=RECOVERY_CLOSE,
    ),
    # 星徽详情浮窗:纯展示(点星徽弹详情)。对局内消费 = 阶段一身份分发
    # (判据 = 建档双 id_mark 组合 AND 全命中;cw_loop 星徽详情分支)——
    # 本条 OverlaySpec 是分类/清场表成员(单锚=变体帧同样漏,如实申报);
    # 入口链守卫 = AND(防御面);op 内 entry_ok = 双锚其一(OR,接管面
    # 比分发宽,变体帧经兜底重判后的自愈面)。原「分发 OR/守卫 AND 有意
    # 分叉」的调和前提已随分发收编建档组合 AND 失效(ADR-0607 历史读法
    # 以本注为准)。
    OverlaySpec(
        screen_name='货币战争-星徽详情',
        anchor_area='标识-流派星徽',
        semantic=SEMANTIC_DISPLAY,
        close_area='按钮-关闭',
        dispatch_priority=17,
        recovery_exit=RECOVERY_CLOSE,
    ),
    # 星徽秘典弹窗:decision 化(设计定案 5)——有选卡价值(0i 阵营匹配选卡),
    # 「关闭即丢决策内容」;closable=False ⇒ 不在清场派生集(环入口不再
    # 一键关,改由 0i 选卡消化)。
    # handler_id:CwScreenBookcard(原挂账 HandleStarTome 已清——秘典实现
    # 经命名迁移落 CwScreenBookcard,0i 分发同源)。
    OverlaySpec(
        screen_name='货币战争-星徽秘典弹窗',
        anchor_area='标识-星徽秘典',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenBookcard',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=12,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='star_tome',
    ),
    OverlaySpec(
        screen_name='货币战争-备战-专家邀请函',
        anchor_area='标识-专家邀请函',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenExpertInvite',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=13,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='bookcard',
    ),
    # 补给:节点级选卡(CwScreenSupplyNode 生命周期 owner)。语义 decision ⇒
    # C1 红线 closable=False ⇒ 不在清场派生集——补给 modal 不被环入口
    # 「返回备战界面」一键离场,改走 bail → CwScreenSupplyNode 消化(与星徽
    # 秘典同型「严格不劣」论证:少丢一次补给选择;CwScreenSupplyNode._in_node
    # = 标识-补给阶段 area 命中,覆盖非节点期弹出场景)。
    OverlaySpec(
        screen_name='货币战争-补给',
        anchor_area='标识-补给阶段',
        semantic=SEMANTIC_DECISION,
        handler_id='CwScreenSupplyNode',
        close_action=CLOSE_ACTION_HANDLE,
        dispatch_priority=8,
        recovery_exit=RECOVERY_HANDLE,
        bail_tag='supply',
    ),
    # 难度确认:开局难度确认弹窗,长尾——无 cw_loop 消费分支、无专属
    # handler(设计定案未单独裁决);声明为 system + 推进按钮载荷挂账,
    # 待出现消费需求时再定语义/接 handler
    OverlaySpec(
        screen_name='货币战争-难度确认',
        anchor_area='标识-当前难度职级',
        semantic=SEMANTIC_SYSTEM,
        close_area='按钮-开始对局',
        dispatch_priority=18,
        recovery_exit=RECOVERY_HANDLE,
    ),
    # 商店卡牌详情弹窗(实机事故建档,2026-09-08):奖励节点采晶矿误触
    # 开的角色 offer 购买页(0e2 概率表/1d 星徽详情之后同族第三例)。语义
    # display(买不买归商店域——0t 分支只点 X 关闭交回重判,店开时商店
    # 访问路径接管购买,关闭不丢决策内容);closable=False ⇒ 不进清场
    # 派生集(弹窗有主 = cw_loop 0t 分支,点 X 带验效,禁清场旁路双owner)。
    # 双锚表达 0t 判据(购买 ∧ 角色详情,双 id_mark 同帧全中才派发);
    # close_area 按钮-关闭 = cw_lobby_close 同族模板。
    OverlaySpec(
        screen_name='货币战争-商店卡牌详情',
        anchor_area='按钮-购买',
        anchor_area_alt='按钮-角色详情',
        semantic=SEMANTIC_DISPLAY,
        close_area='按钮-关闭',
        dispatch_priority=21,
        recovery_exit=RECOVERY_CLOSE,
    ),
    # ── 未激活条目(active=False,待实机建档)──
    # 道具详情弹窗(聘用书类 modal):现 cw_loop 0e3 裸 OCR 分支;建档后
    # screen_name/anchor_area 取建档终值(id_mark 用独有标题行),判定坍缩
    # 为单 area 锚。派发序必须在祈愿试炼(11)之后(祈愿选项名含「聘用书」)。
    OverlaySpec(
        screen_name='货币战争-道具详情弹窗',
        anchor_area='',
        semantic=SEMANTIC_DISPLAY,
        close_action=CLOSE_ACTION_POINT,
        # × 位置 VLM 定位(cw_loop 0e3 现值)
        close_point=(1862, 65),
        dispatch_priority=19,
        recovery_exit=RECOVERY_CLOSE,
        active=False,
    ),
    # 消耗品详情浮层:「拖动到」只出现在消耗品详情 modal(天然独有
    # id_mark 候选),建档后单锚收编。
    # ⚠️ 挂账(ESC 清零批元数据):下方 esc 双声明描述的 cw_loop 0f ESC 分支
    # 已删除——现关层行为 = 分发 CwScreenConsumableOverlay 点同族「道具详情
    # 弹窗/按钮-关闭」×(× 同位 (1862,65))。条目未建档保持 inactive;
    # 建档批按该实作改声明并清 esc 值。
    OverlaySpec(
        screen_name='货币战争-消耗品详情浮层',
        anchor_area='',
        semantic=SEMANTIC_DISPLAY,
        close_action=CLOSE_ACTION_ESC,
        dispatch_priority=20,
        recovery_exit=RECOVERY_ESC,
        active=False,
    ),
)

#: handler 收拢挂账集(历史:HandleStarTome 挂账已随命名迁移清账——
#: 秘典实现落 CwScreenBookcard)。当前为空集;机制保留:新 handler_id
#: 先挂此集豁免 import 断言,收拢落地后移除(集合必须 ⊆ registry 引用集)。
PENDING_HANDLER_IDS: frozenset[str] = frozenset()


def derive_upper_screens() -> tuple[str, ...]:
    """UPPER_SCREENS 派生段:registry 全量激活条目(声明序)。

    帧态门消费方(cw_obs_core.is_prep_like_frame 逐屏判定)再拼
    ``UPPER_SCREENS_NON_OVERLAY`` 残余段成完整常量;新 overlay 建档 +
    一条激活 spec 即自动获得帧态门排除。
    """
    return tuple(spec.screen_name for spec in OVERLAY_REGISTRY if spec.active)


def derive_clearable() -> tuple[OverlaySpec, ...]:
    """P0 清场派生集:激活且 closable 的条目(声明序;A 面消费)。"""
    return tuple(spec for spec in OVERLAY_REGISTRY
                 if spec.active and spec.closable)


def derive_decision() -> tuple[OverlaySpec, ...]:
    """director bail 扫描派生集:激活的 decision 条目(声明序;B 面消费)。"""
    return tuple(spec for spec in OVERLAY_REGISTRY
                 if spec.active and spec.semantic == SEMANTIC_DECISION)


def dispatch_order() -> tuple[OverlaySpec, ...]:
    """C 面表驱动派发序:激活条目按 dispatch_priority 升序。"""
    return tuple(sorted((s for s in OVERLAY_REGISTRY if s.active),
                        key=lambda s: s.dispatch_priority))
