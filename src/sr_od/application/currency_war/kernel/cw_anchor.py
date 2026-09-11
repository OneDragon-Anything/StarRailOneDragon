"""流程转点观测锚·登记机制(kernel;统一观察架构 §12,实现批 T-221)。

设计正本 = ``docs/develop/currency_war/design/统一观察架构-画面op基类设计.md``
§12:在流程确定性转点上触发的一次结构化观测(锚),三要素 = 确定性触发
时点 × 该时点权威事实集 × 落载体登记。本模块承载 §12.3 的登记表机制
(ANCHOR_REGISTRY 封闭集)、锚行七字段封装(AnchorEvent)与事件行载体
接线(emit_anchor → ExogenousEvent 流,结构化载荷住 choice)。
**载体墓碑(删除波 1 后现状)**:ExogenousEvent 流出口已退役为恒 no-op
桩(cw_telemetry_exit.record_exogenous),armed 与否都不落行;登记表各
行 host 所指原宿主写点已同步退役——载体与宿主归宿候裁挂起(retirement.md
§2 exogenous 行),接线批落地前本模块在役面 = 登记/校验/幂等,零落行。

**观测-only 边界(§12.0,用户裁定)**:本模块只做数据采集与计数登记,
状态改写/效果施加明确出栈(效果施加语义归 §8.2 效果结构化词表线)——
锚行 payload 的 ``effect_ref`` 槽位预留恒空(非空 = 红,结构锁见
emit_anchor),消费侧守卫(决策代码禁读锚行)= 测试仓 grep 锁,隔离
边界不是纸面声明。本模块 API 面不收 ctx/session/op 宿主对象(结构性
写向隔离:拿不到就写不了),零 run 状态触碰(§12.5-3 停机钩子分流)。

**封闭集纪律(§12.2,登记式先例 = cw_game_ports 消费面 / EMIT_TRIGGERED_
DECLARED / SELL_CHANNELS)**:新锚先入登记表再接线,集外锚 = 红;触发
时点型逐锚显式申报(landed/emitted/boundary,§6.4 轴三型),禁静默选型。
**H1 裁决(实现批钉死,2026-09-10)**:boundary 型锚的申报面 = 本登记表
行的触发时点型列(设计 §12.3 末段已定锚登记行必带该字段),不另立
BOUNDARY_TRIGGERED_DECLARED 独立表、不改既有 EMIT 表——第二申报面即双源。

**本批状态申报(惰性纯机制面,cw_game_ports 批 0 同款)**:当前零生产
调用点、不被任何生产模块 import,确定性测试直接对其编程——触发口接线
归后续批(buy/refresh 触发口随 §6.4 执行器收编批成立,R-J 挂账在案,
禁绕收编私接触发;boundary 触发口与注册表触达机制候 H6 终裁,禁静默
选型),接线批落调用点时同步扩测试仓零消费守卫白名单。sim 侧零动
(sim 桶零 import 有锁;「实机先行」= sim 域锚行落盘面候批,接线前
sim 域只验事实来源存在性,§12.4-A)。

闭集内 = §12.2 以「实机先行」标记的 8 锚;实机-only(box_opened/
event_choice/encounter 刷新发射)与缓立/出辖行不在本批,登记随其归属批。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sr_od.application.currency_war.kernel import cw_telemetry_exit

# ===== 触发时点轴(§6.4 三型;v10 扩展申报 boundary)=====

ANCHOR_TRIGGER_LANDED: str = 'landed'
#: 发射型(点击发射即置位不等验效)——在册成员为实机-only 锚,本批闭集无。
ANCHOR_TRIGGER_EMITTED: str = 'emitted'
ANCHOR_TRIGGER_BOUNDARY: str = 'boundary'

#: 触发时点轴封闭值域(申报校验用;轴外型 = 红)。
TRIGGER_AXIS: frozenset[str] = frozenset({
    ANCHOR_TRIGGER_LANDED, ANCHOR_TRIGGER_EMITTED, ANCHOR_TRIGGER_BOUNDARY,
})

#: 口径域封闭值域(§12.3 scope:消费侧跨批对读计数前必核,防口径混用,
#: T-211 归因批实证的锚侧预防)。
ANCHOR_SCOPES: frozenset[str] = frozenset({'global', 'plane', 'unit'})


# ===== 登记表行(§12.3 末段声明八字段)=====

@dataclass(frozen=True)
class AnchorSpec:
    """锚登记表行(§12.3:每锚一行,基类级持有的登记清单面)。

    字段逐条对应 §12.3 末段声明:anchor_id / 触发时点型 / 宿主 /
    载体 kind / sim 适用域 / evidence_required / 前置依赖 / 申报出处。
    ``carrier_kind=None`` 申报「载体 = 既有多写点面(非单一
    ExogenousEvent kind)」,锚行落盘路由候 H2 schema 修订批钉死。
    ``evidence_required`` 初判全部 False(§12.3;判定事实型锚 H3 定谳后
    改 True 并申报判定依据),True 时发射必须带 evidence_refs(指标 5
    留证在锚点定义内,非事后补采)。
    """

    anchor_id: str
    trigger_type: str
    host: str
    carrier_kind: str | None
    sim_domain: str
    evidence_required: bool
    prerequisite: str
    source: str


# ===== 锚行(§12.3 七字段封装,全部锚共用)=====

@dataclass
class AnchorEvent:
    """一次锚触发的记录行(§12.3 锚行封装)。

    七字段组到物理列的映射:①anchor_id;②trigger_type;③时点键 =
    ts/run_id/plane/round_num/node_seq/unit_seq(node_seq = 登记期快照;
    unit_seq 仅商店域动作锚,坐标 = (plane,round) 内购买单元序,1 起);
    ④payload(逐锚类型化槽位候 H2;effect_ref 槽位预留恒空,§12.0);
    ⑤scope;⑥evidence_refs;⑦produced_by(锚宿主 op 类名,沿登记件
    produced_by 口径)。

    [索引定义] node_seq/unit_seq:坐标系 = run 内 (plane, round) 键下的
    节点序位快照 / 购买单元序(与 spend_ledger.unit_seq 同坐标系);
    取值时机 = 登记期快照(生成期),不随执行期重排回写。
    """

    anchor_id: str
    trigger_type: str
    ts: str
    run_id: str
    plane: int
    round_num: int
    node_seq: int | None
    unit_seq: int | None
    payload: dict[str, Any]
    scope: str
    evidence_refs: list[dict[str, str]] = field(default_factory=list)
    produced_by: str = ''

    def to_row(self) -> dict[str, Any]:
        """落载体行的扁平序列(时点键组内的 round 以 §12.3 记名 ``round``
        落键,与数据类字段 round_num 同义)。"""
        return {
            'anchor_id': self.anchor_id,
            'trigger_type': self.trigger_type,
            'ts': self.ts,
            'run_id': self.run_id,
            'plane': self.plane,
            'round': self.round_num,
            'node_seq': self.node_seq,
            'unit_seq': self.unit_seq,
            'payload': dict(self.payload),
            'scope': self.scope,
            'evidence_refs': list(self.evidence_refs),
            'produced_by': self.produced_by,
        }


# ===== 登记表(封闭集;新锚 = 先改本表再接线,集外锚 = 红)=====

ANCHOR_REGISTRY: dict[str, AnchorSpec] = {
    'buy_landed': AnchorSpec(
        anchor_id='buy_landed',
        trigger_type=ANCHOR_TRIGGER_LANDED,
        host='on_outcome(BuyCard) 注册表件(现役登记件还在 cw_op_buy_cards'
             ' 执行落地门)',
        carrier_kind='buy_landed',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='触发口 on_outcome(BuyCard) 随 §6.4 执行器收编批成立'
                     '(R-J 挂账在案),禁绕收编私接触发;payload 类型化槽位'
                     '(含买因槽候裁)随 H2',
        source='统一观察架构 §12.2 buy_landed 行(T-221 落码)'),
    'sell_landed': AnchorSpec(
        anchor_id='sell_landed',
        trigger_type=ANCHOR_TRIGGER_LANDED,
        host='原宿主=卖牌执行点 sell_income 行写点(recorder.record_sell_income,'
             '已随删除波 1 退役;归宿候裁挂 retirement.md §2 exogenous 行)',
        carrier_kind='sell_income',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='channel 字段补登 + reason→channel 归一映射宿主与封闭'
                     '性守卫随 H2 钉死(发射侧 reason 自由串非闭集本身)',
        source='统一观察架构 §12.2 sell_landed 行(T-221 落码)'),
    'refresh_landed': AnchorSpec(
        anchor_id='refresh_landed',
        trigger_type=ANCHOR_TRIGGER_LANDED,
        host='原宿主=三写点面(spend_ledger 刷新字段 + shop_snapshots refresh'
             ' 行 + record_refresh_execution/REFRESH bump,均已随删除波 1 退役;'
             '归宿候裁挂 retirement.md §2 exogenous 行)',
        carrier_kind=None,
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='触发口随 §6.4 执行器收编批成立(R-J);试验边界键显影'
                     '挂 H2;非单一 kind 载体的锚行落盘面候 H2 申报',
        source='统一观察架构 §12.2 refresh_landed 行(T-221 落码)'),
    'levelup_landed': AnchorSpec(
        anchor_id='levelup_landed',
        trigger_type=ANCHOR_TRIGGER_LANDED,
        host='prep_actions._level_up 成功路径写点(现役 kind=level_up 行,'
             '同点调 on_level_up 升级标记挂点)',
        carrier_kind='level_up',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='击数/扣金扩字段随 H2;禁双行(另立 kind=levelup_landed'
                     ' 与现役行构成同事件两行 = 违指标 3,申报否决)',
        source='统一观察架构 §12.2 levelup_landed 行(T-221 落码)'),
    'battle_start': AnchorSpec(
        anchor_id='battle_start',
        trigger_type=ANCHOR_TRIGGER_LANDED,
        host='出战验真锚时点(备战标识消失,§6.2)',
        carrier_kind='battle_start',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='deployed 摘要复用既有观测漏斗(§12.5-5,零新读屏);'
                     '羁绊档位不入锚行(判读离线派生);kind 生产者 = 锚钩子'
                     '体候触发批',
        source='统一观察架构 §12.2 battle_start 行(T-221 落码)'),
    'node_enter': AnchorSpec(
        anchor_id='node_enter',
        trigger_type=ANCHOR_TRIGGER_BOUNDARY,
        host='画面分派点(cw_loop 外循环分派,进节点分派时点;现役 '
             'node_enter 写点 = 战斗结算后仅辖战斗节点,待收编)',
        carrier_kind='node_enter',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='boundary 触发口与注册表触达机制候 H6 终裁(禁静默选型;'
                     '申报面 = 本表触发时点型列,H1 已裁决);choice 载荷扩 '
                     'tick 回执随 H2',
        source='统一观察架构 §12.2 node_enter 行(T-221 落码)'),
    'plane_enter': AnchorSpec(
        anchor_id='plane_enter',
        trigger_type=ANCHOR_TRIGGER_BOUNDARY,
        host='过渡相位处理(位面专属过渡屏,§3.4)',
        carrier_kind='plane_enter',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='boundary 触发口候 H6;过渡相位表收编(§3.4)为宿主'
                     '接线前提',
        source='统一观察架构 §12.2 plane_enter 行(T-221 落码)'),
    'settlement': AnchorSpec(
        anchor_id='settlement',
        trigger_type=ANCHOR_TRIGGER_BOUNDARY,
        host='结算写端(CwScreenBattleWait 结算观察写端;宿主是 op = '
             'boundary 三锚例外)',
        carrier_kind='settlement',
        sim_domain='实机先行',
        evidence_required=False,
        prerequisite='boundary 触发口候 H6(H6 候选①的例外样本);候选值随 '
                     'H2;效果账本结算挂点(on_battle_end)接线 = 本锚组成'
                     '部分(记录模型设计 §5.1 挂账收敛)',
        source='统一观察架构 §12.2 settlement 行(T-221 落码)'),
}

# ===== payload 值域申报面(§12.5-4 闭集消费;kernel 零上层依赖)=====

#: 逐锚 payload 字段 → 值域闭集的「符号名锚」(定义点唯一,不抄值):
#: 键 = anchor_id,内层 = payload 字段名 → '模块.符号' 引用串。
#: kernel 禁上层依赖(sell_gate 住 strategies 桶),故登记面只存引用,
#: 值由装配点经 register_payload_domain_values 显式注入(缺省关 + 启动点
#: 显式接通,cw_telemetry_exit 同款纪律)。新增申报随 H2 schema 修订批
#: (买因槽候裁定形后同式申报 LAUNCH_CAUSES)。
PAYLOAD_DOMAIN_REFS: dict[str, dict[str, str]] = {
    'sell_landed': {'channel': 'sell_gate.SELL_CHANNELS'},
}

_ARMED_DOMAIN_VALUES: dict[str, frozenset[str]] = {}


def register_payload_domain_values(ref: str, values: frozenset[str]) -> None:
    """装配点显式注入值域闭集(生产武装点 = 触发口接线批的装配段;
    未申报的引用串拒收——防绕申报面私注值域)。"""
    declared = {r for fields in PAYLOAD_DOMAIN_REFS.values() for r in
                fields.values()}
    if ref not in declared:
        raise ValueError(
            f'值域引用 {ref!r} 未在 PAYLOAD_DOMAIN_REFS 申报(先申报再武装;'
            f'已申报 = {sorted(declared)})')
    _ARMED_DOMAIN_VALUES[ref] = frozenset(values)


# ===== 登记表完整性校验(封闭集纪律的机器面)=====

def validate_registry(
        registry: dict[str, AnchorSpec] | None = None) -> None:
    """登记表逐行校验(模块导入时自检 + 测试锁消费):触发时点型轴内、
    宿主/sim 适用域非空、载体 kind 形态合法。违规 = 红(炸错不静默收下)。"""
    reg = ANCHOR_REGISTRY if registry is None else registry
    for key, spec in reg.items():
        if spec.trigger_type not in TRIGGER_AXIS:
            raise ValueError(
                f'锚 {key!r} 触发时点型 {spec.trigger_type!r} 不在轴内'
                f'(合法值 = {sorted(TRIGGER_AXIS)},§6.4 轴三型;'
                f'逐锚显式申报禁静默选型)')
        if not spec.host or not spec.sim_domain:
            raise ValueError(f'锚 {key!r} 宿主/sim 适用域申报为空')
        if spec.carrier_kind is not None and not spec.carrier_kind:
            raise ValueError(f'锚 {key!r} carrier_kind 形态非法(空串;'
                             f'多写点面载体请申报 None)')
        if spec.anchor_id != key:
            raise ValueError(f'锚行 anchor_id 与登记键不一致:{key!r}')


validate_registry()


# ===== 幂等键(指标 3:每真值事件恰一行)=====

_DedupeKey = tuple[str, str, int, int, int | None, int | None, str]

_EMITTED_KEYS: set[_DedupeKey] = set()


def reset_anchor_dedupe() -> None:
    """幂等键集复位(测试隔离/局间复位用;键含 run_id,生产跨局不串)。"""
    _EMITTED_KEYS.clear()


# ===== 载体接线(事件行 = ExogenousEvent kind 词表,结构化载荷住 choice)=====

def emit_anchor(anchor_id: str, *, plane: int, round_num: int,
                payload: dict[str, Any], scope: str,
                produced_by: str = '',
                node_seq: int | None = None, unit_seq: int | None = None,
                evidence_refs: list[dict[str, str]] | None = None,
                event_key: str = '', summary: str = '') -> bool:
    """登记一次锚触发并走 §12.3 载体一上行口(载体墓碑见模块头:ExogenousEvent
    出口已退役恒 no-op 桩,受理后行不落盘,归宿候裁挂 retirement.md §2)。

    校验链(违规 = 红,炸错不静默):①封闭集(集外锚 = 红,锁①);
    ②scope 值域(§12.3);③effect_ref 恒空(结构锁,锁⑤——效果施加批
    消费该槽须先过用户裁决并同步改造守卫,禁静默启用);④留证门
    (evidence_required=true 的锚 evidence_refs 必填,指标 5);⑤已武装
    的 payload 值域闭集(如 sell channel ∈ SELL_CHANNELS,§12.5-4)。

    幂等(锁③):键 = (anchor_id, run_id, plane, round, node_seq,
    unit_seq, event_key);重试路径双触发零双行——第二发丢弃返 False。
    ``event_key`` = 发射侧事件区分词:同一时点键域内多次同名事件必带
    (如 buy_landed 的 槽位#序),天然单发的锚(node_enter 同
    (plane,round) 唯一)留空即可。

    局外(run_id 空)= no-op 返 False(不写假行,与既有外生行门控同);
    载体为多写点面(carrier_kind=None)的锚拒绝路由(落盘面候 H2,如实
    申报不假装)。返回 True = 已受理(受理≠落盘:载体出口退役现状下行
    不落,墓碑见模块头)。

    本函数是观测-only 面:不触 run 状态、不写 BoardState/决策域、不施加
    效果(§12.0);best-effort 语义由调用方自担(出口槽未武装时本函数
    经 cw_telemetry_exit 自动 no-op)。
    """
    spec = ANCHOR_REGISTRY.get(anchor_id)
    if spec is None:
        raise ValueError(
            f'锚 {anchor_id!r} 未入 ANCHOR_REGISTRY(集外锚 = 红,§12.2 '
            f'封闭集:新锚先登记再接线;在册 = {sorted(ANCHOR_REGISTRY)})')
    if scope not in ANCHOR_SCOPES:
        raise ValueError(
            f'scope {scope!r} 不在口径域封闭值域内(合法 = '
            f'{sorted(ANCHOR_SCOPES)},§12.3:消费侧防口径混用)')
    if payload.get('effect_ref') is not None:
        _bad_ref = payload.get('effect_ref')
        raise ValueError(
            f'effect_ref 槽位恒空(§12.0:效果施加出栈,取值 {_bad_ref!r} '
            f'非空 = 红;消费须先过用户裁决并改守卫)')
    if spec.evidence_required and not evidence_refs:
        raise ValueError(
            f'锚 {anchor_id!r} 申报 evidence_required(判定事实型,指标 5)'
            f':evidence_refs 必填(留证在锚点定义内,非事后补采)')
    for field_name, ref in PAYLOAD_DOMAIN_REFS.get(anchor_id, {}).items():
        value = payload.get(field_name)
        if value is None:
            continue
        values = _ARMED_DOMAIN_VALUES.get(ref)
        if values is not None and value not in values:
            raise ValueError(
                f'payload.{field_name}={value!r} 不在 {ref} 闭集值域内'
                f'(合法 = {sorted(values)};§12.5-4 禁第二套枚举)')
    if spec.carrier_kind is None:
        raise ValueError(
            f'锚 {anchor_id!r} 载体 = 非单一 kind 多写点面(carrier_kind='
            f'None),锚行落盘路由候 H2 申报(§12.2 如实申报,不假装有单'
            f'一载体)')
    run_id = cw_telemetry_exit.current_run_id()
    if not run_id:
        return False
    key: _DedupeKey = (anchor_id, run_id, int(plane), int(round_num),
                       None if node_seq is None else int(node_seq),
                       None if unit_seq is None else int(unit_seq),
                       event_key)
    if key in _EMITTED_KEYS:
        return False
    _EMITTED_KEYS.add(key)
    event = AnchorEvent(
        anchor_id=anchor_id, trigger_type=spec.trigger_type,
        ts=datetime.now().isoformat(timespec='seconds'), run_id=run_id,
        plane=int(plane), round_num=int(round_num), node_seq=node_seq,
        unit_seq=unit_seq, payload={**payload, 'effect_ref': None},
        scope=scope, evidence_refs=list(evidence_refs or []),
        produced_by=produced_by)
    cw_telemetry_exit.record_exogenous(
        round_num=event.round_num, kind=spec.carrier_kind,
        detail=f'anchor:{anchor_id} {summary}'.rstrip(),
        choice={'anchor': event.to_row()})
    return True
