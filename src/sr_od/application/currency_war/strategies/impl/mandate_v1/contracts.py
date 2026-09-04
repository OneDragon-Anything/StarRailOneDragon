"""货币战争 新循环契约(Snapshot 快照 + Decision 决策,W583 阶段2批①)。

架构决策单一源 = ``docs/develop/currency_war/decisions/``(接口形态)与
设计审计报告 ``.debug/temp/currency_war/w561_arch_review/REPORT.md`` §三
(签名/快照契约/分类通道/控制流通道)。本模块**纯数据契约**:零 IO、零
识别调用、零决策逻辑;import 单向(只依赖 cw_state 既有结构,不反向依赖
包内其他模块)。

三个组件:
- ``Snapshot`` —— 备战决策环步的统一观察视图,新循环 ``decide(snapshot,
  session) -> Decision`` 的第一参数。快照纯(frozen、感知可复算、无决策侧
  状态);字段级 ``None = 不确定,永不猜测``(「读不到≠真值」纪律,反例
  实证 = read_shop_refresh_cost 兜底静默改值,见 W558 核查报告)。
- ``SubstateClassification`` —— 分类可信度通道:非 confident 快照框架不调
  decide,有界重试 → 停机留证(结构性缺口实证 = 「备战-角色详情」锚对
  真值帧全失配,ADR-0269 两段式门的前因与边界)。
- ``Decision`` —— decide 返回值:原子操作批 + 显式控制流通道(Defer/Bail
  是框架信号,不混进 ops)。

字段级语义/None 语义/来源/消费钩子的权威表 =
``.debug/temp/currency_war/w583_stage2_contracts/SCHEMA_DRAFT.md`` §四
(编排者审定版);sim 合成器(GameState→Snapshot)是无损门的第一个消费者。
"""
from __future__ import annotations

import copy
import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from sr_od.application.currency_war.kernel.cw_state import BenchChar, ShopCard

#: 快照 Schema 版本(字段只增不改删,废弃字段走两版过渡;不匹配显式报错,
#: 替代静默回退——接口版本化决策,设计审计报告 §三.8)。
SNAPSHOT_SCHEMA_VERSION = 1


class SnapshotSchemaVersionError(ValueError):
    """快照 ``schema_version`` 与契约当前版本不匹配(显式报错,禁静默回退)。

    语义改判(字段含义变化而非字段集变化)形状上不可见,唯一防线 = 改判
    必须动版本号;消费侧版本守卫拒绝旧语义快照,把静默错变成启动即炸。
    """


def require_schema_version(snapshot: Snapshot) -> None:
    """schema_version 执行者:消费侧进入 decide 循环前必须调用。

    「版本不匹配显式报错」不能停留在注释纪律——唯一指定执行点 =
    DirectorV2 环顶(快照 → decide 的唯一框架入口);本函数即该纪律的
    代码化,供执行点与测试直调。
    """
    if snapshot.schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotSchemaVersionError(
            f'快照 schema_version={snapshot.schema_version} != 契约版本 '
            f'{SNAPSHOT_SCHEMA_VERSION}:拒绝消费(字段只增不改删;语义改判'
            f'必须动版本——旧策略按旧语义读新快照是静默错)')


def derive_snapshot(snap: Snapshot, **changes: Any) -> Snapshot:
    """显式快照变换通道(唯一合法派生/覆写入口)。

    快照是 frozen + 只读容器的纯数据值:框架派生/覆写(如「bench 满警告」
    派生帧)必须经本函数得到新实例。``dataclasses.replace`` 对 frozen 本身
    合法,禁的是绕过本通道内联调用——那会让容器拷贝纪律失守(派生帧与原帧
    共享可变元素)。未显式覆写的容器字段做深拷贝,派生帧与原帧元素互不共享。
    """
    base: dict[str, Any] = {
        'bench': tuple(copy.deepcopy(b) for b in snap.bench),
        'deployed': tuple(copy.deepcopy(d) for d in snap.deployed),
        'shop_cards': (tuple(copy.deepcopy(c) for c in snap.shop_cards)
                       if snap.shop_cards is not None else None),
        'board': (MappingProxyType(dict(snap.board))
                  if snap.board is not None else None),
    }
    base.update(changes)
    return dataclasses.replace(snap, **base)


@dataclass(frozen=True)
class SubstateClassification:
    """子态分类结果(快照的分类可信度通道)。

    - ``name``:统一子态注册表键(如 ``'prep_shop'``);上层屏/事件 overlay
      收拢进同一注册表(消除 UPPER_SCREENS 与 event_overlay 双白名单双源,
      两者已在漂移)。
    - ``evidence``:命中锚与分数,审计/留证用。
    - ``confident`` 判据:两段式帧门通过且未命中任何上层屏(ADR-0269
      UPPER_SCREENS 逐屏排除)且无事件 overlay。结构性依据:分类锚对真值帧
      可整批失配(「备战-角色详情」3 真值帧全失配实证)——分类错误在新循环
      下 = decide 的世界模型错 = 全链错,必须显式暴露而非静默。
    - sim 合成侧恒 ``confident=True``(sim 无识别过程,分类恒真是合成器契约
      的一部分,进无损门断言)。
    """
    name: str
    evidence: tuple[str, ...] = ()
    confident: bool = True


@dataclass(frozen=True)
class RewardSphere:
    """奖励球(交互面观测)。

    坐标系 = 1080p 游戏空间绝对像素;取值时机 = 本帧观察快照(生成期)。
    """
    color: str
    x: int
    y: int
    radius: int = 0


@dataclass(frozen=True)
class SupplyBox:
    """武装箱(交互面观测;坐标系与时机同 RewardSphere)。"""
    x: int
    y: int


@dataclass(frozen=True)
class Tome:
    """秘密典籍(交互面观测;坐标系与时机同 RewardSphere)。"""
    x: int
    y: int


@dataclass(frozen=True)
class Snapshot:
    """备战决策环步统一观察视图(纯数据;每字段准入判据 = 有策略消费面)。

    逐字段语义/None 语义/来源/消费钩子权威表 = SCHEMA_DRAFT.md §四;此处
    注释只写「权威表之外的当前值成立理由」。通用不变式:

    - 空值表示总约定(消费侧按字段域取义,本条是唯一总注):``None`` =
      本帧不确定(观测失败/未读到),**禁兜底改值**——消费侧要用保守值须
      显式声明(错值比 None 更毒:错值以「确定的假」进决策);可选容器
      字段(board/shop_cards)``None``=未读、空容器=观测真值(board 空
      mapping=真清空);序列观测字段(spheres/boxes/tomes)空元组=「无,
      观测事实非失读」。
    - 槽位坐标系(**同一容器域内双基并存,消费 DeployMove 类动作参数时
      防 off-by-one**):bench/deployed 的容器下标 = 各容器物理槽位
      0-based(权威槽位,front_occupied/back_occupied 元素同系;
      deployed 下标 0-3=前排/4-9=后排,与 cw_state.deployed_place 同
      坐标系);元素 ``BenchChar.slot`` = **1-based 屏幕槽号**(信息位,
      与容器下标相差 1)——动作参数取 slot、位置判据取下标。
    - 不可变性防线:frozen + 容器字段为只读结构(bench/deployed/
      shop_cards = tuple、board = 只读映射),合成侧对元素**深拷贝**——
      快照与上游 GameState 无共享可变态(「snap.bench[0] is st.bench[0]」
      恒 False,等价性用 == 断言)。快照派生/覆写唯一合法通道 =
      ``derive_snapshot``(禁内联 dataclasses.replace 破墙)。
    - 新鲜度维度:快照**不承载**字段级 stale 语义。理由 = 新鲜度是观察端
      职责(现役 PrepObservation 的 heavy/light 分层归适配器),decide
      循环每步重观察已把「heavy 可能陈旧」收敛在观察端;把帧龄数字漏进
      纯数据契约会把观测职责转嫁给每个策略。
    - 批③适配器映射义务清单(本快照刻意不含、适配器必须从 session/常量
      **显式**映射,禁静默缺省——伪态拷贝漏拷持有策略集会使持有判据静默
      失效为空,双源裂缝实证):``dual_track_phase``(双轨阶段)、
      ``active_strategies``(持有策略集)、``equips``(持有装备池)、
      ``refresh_probs``(刷新概率条)。
    """
    schema_version: int = SNAPSHOT_SCHEMA_VERSION
    classification: SubstateClassification = field(
        default_factory=lambda: SubstateClassification(name='unknown',
                                                       confident=False))
    # —— 节点域 ——
    plane: int = 1
    round_num: int = 1          # 位面内轮次 1-based(非全局节点号)
    node_type: str | None = None            # None=本帧未读到(节点行被遮等)
    selected_difficulty: str = ''           # ''=未检测(阈值回退默认)
    # —— 经济域 ——
    gold: int | None = None                 # None=金区失读(禁 0 兜底)
    gold_trusted: bool = False              # =可作决策依据(shop 开态 fresh,F2 门)
    streak: int | None = None               # 带符号:+连胜/−连败;None=未读到
    level: int | None = None                # None=本帧未读到;单调守卫在 session
    xp_progress: tuple[int, int] | None = None   # (当前, 升级所需);None=未读到
    level_up_cost: int | None = None        # None=未读到(禁兜底改值)
    # —— 单位域 ——
    bench: tuple[BenchChar | None, ...] = ()
    deployed: tuple[BenchChar | None, ...] = ()
    board: Mapping[str, int] | None = None  # None=不可读;空 mapping=真清空(严格分义)
    deploy_cap: int | None = None
    deploy_vacancy: int | None = None       # None=cap 未读(禁 0 兜底:0=无空位吞部署)
    free_bench_slots: int | None = None     # None=占用面读不到(禁 0 兜底:0=满 → 猜测)
    front_occupied: frozenset[int] = frozenset()
    back_occupied: frozenset[int] = frozenset()
    front_size: int = 4
    back_size: int = 6
    # —— 商店域 ——
    shop_open: bool = False
    shop_cards: tuple[ShopCard, ...] | None = None  # None=本帧未读;卡内 name=''/cost=0=该维未识别
    # —— 交互面域(空元组=无,观测事实非失读)——
    spheres: tuple[RewardSphere, ...] = ()
    boxes: tuple[SupplyBox, ...] = ()
    tomes: tuple[Tome, ...] = ()
    box_overlay_open: bool = False
    event_overlay: str | None = None        # None=无 overlay;非 None=挡操作 → control=Bail
    # —— 生命域 ——
    hp: int | None = None                   # None=现读失败;陈值对账锚(last_hp_real
    #                                          /帧龄门/拒信通道)全在 session,快照纯
    hp_readable: bool = False
    # 不变式(无损门断言):hp is None ⇒ hp_readable is False(单向蕴含;
    # 反向不成立——现读成功值也可能被判不可信,由消费侧新鲜度判据处理)。


@dataclass(frozen=True)
class AtomOp:
    """原子操作骨架(批①只定载体;op 枚举分类学归 DirectorV2 批与
    prep_actions 动作族对账时定,禁此处先猜)。

    - ``op_key``:幂等/屏蔽集键——框架 per-key 连败计数 → 恢复原语 → 屏蔽集
      (防线链单一源 = 生命周期机制,框架所有,禁策略自实现)。
    - ``domain``:同域批校验用(批内 op 只允许同域;fail-stop:任一 op 未
      progressed → 批中止余下丢弃)。
    - 期望增量函数接口位:签名待 Expect 契约(期望态统一化阶段)定稿后接入,
      本批不预置字段。
    """
    op_key: str
    domain: str


@dataclass(frozen=True)
class Defer:
    """控制流:奖励球留置(框架信号;defer 计数与门=2 归框架,禁策略自实现)。"""
    reason: str = ''


@dataclass(frozen=True)
class Bail:
    """控制流:让位外环(overlay 挡操作/子态偏离;同因计数与 ping-pong 停机
    归框架)。"""
    reason: str = ''


@dataclass(frozen=True)
class Decision:
    """``decide(snapshot, session) -> Decision`` 的返回契约。

    - ``ops``:原子操作批(执行序即列表序;批语义 = 同域 + fail-stop)。
    - ``control``:显式控制流通道——Defer/Bail 是框架信号,不经 execute 验证
      链,与 ops 互斥使用(同发时框架以 control 优先并记缺陷台账)。
    """
    ops: tuple[AtomOp, ...] = ()
    control: Defer | Bail | None = None
