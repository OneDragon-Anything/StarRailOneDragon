"""cw_game_ports —— 货币战争假环境注入口协议(T-120 sim 重设计 批 0)。

**交付性质(「生产零行为改动」的判据)**:本文件 = 观察源端口/执行器端口
两个 Protocol 契约 + 模块级安装槽,是**惰性纯协议新文件**——当前零消费点、
不被任何生产模块 import,确定性测试直接对其编程;批 1 起才由观察改道
调用点消费。因此它的落地对生产缺省路径零影响(T-120 方案 §6.2 批 0 行
「唯一生产树新增 = 惰性纯协议文件」;消费面自证 = 测试仓
test_cw_game_ports.py 零生产消费守卫锁)。

**方案出处**:T-120 方案 v2(`.debug/temp/currency_war/t120_sim_redesign/
方案.md`,**易失产物**)§2.3 观察注入接口 / §2.4 动作落点接口 / §3.2
端口协议形状 / §3.3 装配纪律。ADR 落点 = T-120 退役批(docs/develop/
currency_war/decisions/,编号待分配:INDEX 尾现役 ADR-0582,T-119 契约批
已预留 0583)——本文注释引用方案路径属暂记指针,后续批须回填 ADR 编号
(测试纪律「批报告类出处」同判)。

**缺省 None = 生产路径**:模块槽缺省 ``(None, None)``,生产全程不安装;
``observation_source()``/``action_sink()`` 返回 None 时调用点走现行真实
读屏/真实执行链,行为逐位不变。安装只发生在测试 harness 显式接通(批 1),
装配纪律:进程内单装配、卸载复位 None(方案 §3.3)。

**依赖边界**:运行时只引用 kernel 纯类型(GameState/ShopCard/Action/
PrepObservation),ctx 仅 TYPE_CHECKING——零 obs/operations/sim 依赖。
生产实现(批 1,LiveCwObserver 住 obs 桶)与假实现(测试仓)实现本协议,
依赖方向单向无环(方案 §3.1 层级裁决:协议住 CW 根,零依赖纯抽象)。

(迁移批 3.2:端口契约改容器形态——``ObservationBundle.state``/
``ExecResult.observed`` 切 GameState,假环境直产容器真值;实现方契约 =
容器直写(与读屏路径 read_game_state 观察漏斗直写同语义),消费方逐帧
读数面自行经容器读口装配。)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_vocab import Action, ShopCard

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


@dataclass
class ObservationBundle:
    """入口观察产物对(GameState 主载荷 + 备战 heavy 观察;方案 §2.3 表)。

    为何是薄对而非新观察容器:方案 §2.3 明文「不发明新容器」——被测 op
    消费的观察产物就是这两件真类型。``state`` 恒在(商店段/最小读/补给
    快照路径只消费容器单例;迁移批 3.2 起为容器形态,实现方已直写真值);
    ``prep`` 仅备战 heavy 观察路径填充(None = 该观察阶段无 heavy 观察,
    消费方按阶段分流)。
    """

    state: GameState
    prep: PrepObservation | None = None


@dataclass
class ExecResult:
    """动作执行回执(方案 §2.4 执行器端口的回执形状)。

    - ``applied``:动作是否生效(假游戏按规则判定,如满栏非合成拒买);
    - ``income``:卖出实收回金(执行点真值;现行生产由 read_gold 对拍
      承载同一语义位,cw_op_buy_cards 金账对拍);
    - ``verification``:执行层验证载荷(刷新有效性=新牌面摘要/买后卡面/
      退金对拍位;键面由各画面执行器自申报);
    - ``observed``:执行后观察快照(假游戏真值,喂 tracked 账与期望态
      对账;None = 该动作不产出快照)。
    """

    applied: bool
    income: int | None = None
    verification: dict = field(default_factory=dict)
    observed: GameState | None = None


@runtime_checkable
class CwObservationSource(Protocol):
    """观察源端口:被测代码取「环境观察」的唯一入口(方案 §2.3/§3.2)。

    实现方 = LiveCwObserver(生产,批 1,obs 桶封装现行读链)或
    FakeCwObserver(测试仓,假游戏状态机真值直出)。实现契约两则
    (方案 §2.3 契约三则中辖端口的两条):

    - **保真位语义不取消**:容器 ``Field.source``/``sig.quality`` 保真位
      (hp 真读/沿用、gold 真读)在假环境恒「真读」形态——这是「完美观测」
      环境参数,不是造假(迁移批 3.2:位载体随帧表示退役由帧布尔位改
      容器来源位,语义不变);
    - **读屏次数语义保留**:每次观察调用必须留痕(次数/时点)——观察
      注入换掉的是**读图**,不是「观察」这个语义事件,读屏节奏类判读
      在假环境仍须可审计(留痕载体由实现自定)。
    """

    def screen_identity(self, ctx: SrContext) -> str:
        """画面档名(= screen_info screen_name;外循环分支分发的判定输入,
        outer_loop §2.2 分支序锚匹配族消费同名)。"""
        ...

    def observe_prep(self, ctx: SrContext, phase: str) -> ObservationBundle:
        """入口观察。

        ``phase`` = ADR-0462 规范入口序列阶段键(obs.cw_observation 的
        ``PHASE_PREP_CLEAN``/``PHASE_PREP_SHOP_OPEN``/
        ``PHASE_BATTLE_OR_TRANSIT``),决定消费方按哪些字段消费——**不是**
        screen_info 画面名(那是 :meth:`screen_identity` 的辖域),两者
        词表不同源,混用会把「读哪些字段」与「在哪个画面」两个语义搅在一起。
        """
        ...

    def observe_shop_cards(self, ctx: SrContext) -> list[ShopCard]:
        """店面卡牌(含费用/星级;生产语义 = read_shop_cards 读链产物)。"""
        ...

    def overlay_options(self, ctx: SrContext, kind: str) -> list[Any]:
        """浮层选项载荷。元素形状随 ``kind`` = 生产对应 reader 的选项词表
        (invest 族 = 选项名 str;supply = SupplyOption 结构化载荷;
        装备三选一/简报词缀同理)——协议不折叠这些形状,折叠即丢失
        消费方已依赖的结构;kind 词表随批 1 改道清单定形。"""
        ...


@runtime_checkable
class CwActionSink(Protocol):
    """执行器端口:被测代码落「动作」的唯一入口(方案 §2.4/§3.2)。

    生产实现(LiveActionSink,批 1)= 现行动作 op execute(坐标点击/
    拖拽)+ 执行侧验证读(read_gold 对拍/read_shop_cards 重读)的原样
    封装,生产行为逐位不变;测试实现(FakeActionSink)= 假游戏
    ``apply(action)``,动作语义投影走 ``cw_state.simulate`` 单一源 +
    规则外效应一次落定(方案 §2.2:假游戏不内联任何动作转移)。
    """

    def execute_action(self, ctx: SrContext, action: Action,
                       env: Any | None = None) -> ExecResult:
        """执行一个动作并回执。

        ``env`` = 动作执行步的宿主语境(T-120 方案 §3.3「商店动作执行步」
        改道点承载;批 1 起传入):生产形状 = operations 桶
        ``cw_shop_action_ops.ShopExecEnv``(协议住 CW 根、不 import
        operations 类型,故只以 Any 申报形状——依赖方向 = operations→CW 根单向)。
        live 实现(批 2 LiveActionSink)消费它驱动点击/验证读;fake 实现
        (测试仓 FakeActionSink)消费它落「账本位随动」——动作账(ledger)
        与 tracked 账是 visit 级宿主状态,不随动作传递就无处落(方案 §2.4
        「规则外效应(池 ret/take、账本位)一次落定」的执行器半边)。

        假环境不建模命中/浮层竞态/点击落空——**执行失败面结构性为零**,
        这是环境替身的边界申报而非缺陷(方案 §2.4;sim-design §2.3-1
        同款申报)。动作是否生效仍由 ``applied`` 申报(规则性拒绝,
        如满栏非合成拒买,与「执行层落空」是两回事)。
        """
        ...


# ---- 模块级安装槽(方案 §3.2/§3.3;decision_assembly.install_obs_ports
# ---- 「模块级槽 + 缺省关 + 装配点显式接通」同构模式的扩展,非新模式)----

_INSTALLED: tuple[CwObservationSource | None, CwActionSink | None] = (None, None)


def install_game_ports(observer: CwObservationSource,
                       sink: CwActionSink) -> None:
    """显式接通两端口(测试 harness 在构建 ctx 后、跑 op 前调用)。

    进程内单装配:重复安装 raise——两套假游戏并存时静默覆盖会让前者的
    断言读到后者的状态,错误形态必须是响的(测试隔离纪律)。清槽语义
    只归 :func:`uninstall_game_ports`,本函数不接受 None。
    """
    global _INSTALLED
    if observer is None or sink is None:
        raise ValueError('install_game_ports 不接受 None 参数'
                         '(卸载请用 uninstall_game_ports)')
    if _INSTALLED != (None, None):
        raise RuntimeError('游戏端口已安装(进程内单装配);'
                           '先 uninstall_game_ports 再重装')
    _INSTALLED = (observer, sink)


def uninstall_game_ports() -> None:
    """卸载复位 None(幂等;测试 teardown 必调——模块槽是进程全局,
    残留会跨测试文件泄漏,方案 §3.3「装配后可卸载复位 None」)。"""
    global _INSTALLED
    _INSTALLED = (None, None)


def observation_source() -> CwObservationSource | None:
    """当前观察源;None = 生产真实读屏(调用点按 None 分流走原读链)。"""
    return _INSTALLED[0]


def action_sink() -> CwActionSink | None:
    """当前执行器;None = 生产真实执行(调用点按 None 分流走原执行链)。"""
    return _INSTALLED[1]
