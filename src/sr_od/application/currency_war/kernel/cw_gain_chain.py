"""货币战争 获得链(gain-chain):获得原语 + 事件回调枚举 + 单级合成。

链式规范正本 = docs/develop/sr_od/application/currency_war/game_state/
gain-chain.md(原语契约/时序/溢出落位/随机态纪律/失败安全/接入面现状)。
接入面(双支):投资环境动作落地接入(``cw_action_report.pick_invest_env``)+
投资策略动作落地接入(``cw_action_report.pick_invest_strategy``),均经
``cw_action_report`` 上报函数消费本模块。

链式过程语义:「获得」= 注册/落位 → 事件回调 → 3 合 1 升星判断 →
升星产物重进获得角色(回调 → 升星判断 → …,无三连同名同星即终止)。回调
先于升星的理由 = 回调可能补齐第三只(用户裁定);升星产物也触发获得角色
回调。

随机态纪律:每个函数一个 ``rand: bool`` 必带入参、递归
透传、效果体含采样时可翻转子链——本次写是否处于随机语义,不承诺全链
一致;写通道经 :func:`_select_write` 单一收束(通道规则「未锚定 →
随机态」,开局种子底座与锚定标志):rand=True 或容器未锚定 →
``write_logic_rand``(未锚定期链落账 = 未验证推算,首观察静默覆盖);
锚定后按形参(rand=False → ``write_logic`` 确定面,失配网原样生效)。

失败安全:链原语**零吞错**(容器写腿/回调效果腿异常上抛);
best-effort 边界只在登记/遥测申报腿内(失败 log + 缺陷留存证据、不阻塞);
唯一调用点级显式例外 = 欢愉契约条件腿授予 rider(住
``cw_action_report.pick_planner``,授予与选项应用两条独立因果不互拖);
bench/equips 未观察(None)= 开局种子底座下生产不可达(局容器缓存
单例冷建即种):直构/sim 域保留拒落档零写,无缺陷发出;席满且溢出位
被占 = 游戏行为未实证:零写 + 留存证据,禁猜。

模块拆分:效果内容(策略卡效果注册表 ``PICK_INVEST_EFFECTS`` + 骇客采样池
+ 效果体)住 ``cw_gain_effects.py``——本模块模块级查表,效果体函数内
惰性 import 本模块原语(单向破环);拆分契约正本 = gain-chain.md §8
(模块拆分段)。
"""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    EQUIP_ACQUIRE_CONSEQUENCES,
    _portal_acquired_key,
    apply_board_rewrite,
    register_portal_from_env,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_place,
)
from sr_od.application.currency_war.kernel.cw_gain_effects import (
    PICK_INVEST_EFFECTS,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    GameState,
    Unit,
    _emit_defect,
    anchor_aware_write,
    apply_effect_burst_grant,
    bench_view_of_working,
    deployed_indexed_of_view,
    deployed_view_of_indexed,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    BENCH_ITEM_NAMES,
    ENV_GIFTS,
    ENV_REROLL_NAMES,
    INVESTMENT_ENVS,
    STRATEGY_EFFECTS,
    normalize_invest_name,
    random_char_pool,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    resolve_plane_node_seqs,
)

#: 链内写端缺省署名(gain-chain.md §2:写点迁移属申报过的行为变化,新写端新名,
#: 不沿用旧名伪装连续;动作落地接入显式传同值)。
GAIN_CHAIN_PRODUCER: str = 'CwGainChain'

#: 缺陷留存证据 kind 词表(_emit_defect 台账行分键;留存证据不停机,gain-chain.md §6)。
#: 未观察两 kind(bench/equips)现役生产不可达:开局种子底座下生产链路
#: 阵容/装备域不再有 None,拒落档零写无缺陷发出(词表停用申报正本 =
#: gain-chain.md §6)。
DEFECT_OVERFLOW_TAKEN: str = 'gain_chain_overflow_slot_taken'
DEFECT_ADVISOR_DECL: str = 'gain_chain_advisor_decl'
DEFECT_PORTAL_REGISTER: str = 'gain_chain_portal_register_failed'
DEFECT_STRATEGY_REGISTER: str = 'gain_chain_strategy_register_failed'

#: 无效载荷拒绝 kind(策略/环境名归一后为空/'?'——零写 + 留存证据;无效输入
#: 拒绝,非防重复保护;正本 = gain-chain.md §2.4-0/§2.1-0)。
PICK_INVEST_INVALID_PAYLOAD: str = 'pick_invest_invalid_payload'

#: 追加随机环境申报行 kind(独立小块,非 DEFECT_ 词表成员:语义 = 申报
#: 非缺陷,不入「缺陷留存证据 kind 词表」块以免破块内前缀分组,沿本模块
#: PICK_INVEST_INVALID_PAYLOAD 先例;通道沿 advisor 申报行同族——申报行
#: 是语义申报非缺陷告警)。追加环境真值 live 不可观察,申报留证;正本 =
#: gain-chain.md §3 追加随机环境段/§6。
ENV_REROLL_DECL: str = 'gain_chain_env_reroll_decl'


@dataclass(frozen=True)
class GainOutcome:
    """获得链原语出参(三原语共用;留存证据/测试用、零决策消费,沿
    ``cw_effect_inventory.py::BenchGrantResult`` 先例)。

    [字段定义] landing 取值:'bench' = 落备战槽 / 'overflow' = 溢出位 /
    'skipped' = 未落席(环境/装备原语无席位语义,与拒落路径共用此档)。
    placed = 本次原语的容器写主步是否发生(环境 = active_env 写、装备 =
    入栏写、角色 = 落位);detail = 拒落因键('' = 正常)。
    """

    placed: bool
    landing: str
    merge_levels: int
    effects: tuple[str, ...]
    detail: str = ''


# ============================================================ 单级合成
# (gain-chain.md §2.2 升星判断:链式版需要「单级合成 + 产物回调」的时机,merge_simulate 是一次
# 到底的不动点推演无回调时机——故此处独立实现单级函数,规则逐条对齐
# merge_simulate 不动点合并段(:206-279:分组键 (char_id, star)、场上载体
# 优先、全备战取最左、溢出件合成腾槽归位优先、装备继承并入、场上同名
# 同星 ≤1 不变量),对齐由交叉核对测试「同池同输入下,单级×N 次 ==
# merge_simulate 终态」——禁第二套语义漂移。)


def _entry_ident(x: object) -> tuple[str, int] | None:
    """计数族条目身份读协议(bench 侧 BenchSlot / deployed 侧 Unit /
    溢出侧 BenchSlot;占位件与空槽无身份,fail-closed 跳过禁猜)。"""
    if x is None:
        return None
    if isinstance(x, BenchSlot):
        if x.kind == 'unit' and x.unit is not None:
            return (str(x.unit.char_id), int(x.unit.star or 1))
        return None
    if isinstance(x, Unit):
        return (str(x.char_id), int(x.star or 1))
    return None


def _entry_equips(x: object) -> list[str]:
    """条目装备读(装备继承并入口;BenchSlot → 内嵌 Unit,Unit 直读)。"""
    u = x.unit if isinstance(x, BenchSlot) else x
    return list(getattr(u, 'equips', None) or [])


def _bump_carrier(carrier: object, new_star: int,
                  new_equips: list[str]) -> object:
    """合成载体升星 + 装备继承的 frozen 新构造(merge_simulate 同式)。"""
    if isinstance(carrier, BenchSlot):
        if carrier.unit is None:
            raise TypeError('merge 载体 BenchSlot 无 Unit(占位件不可合成)')
        return replace(carrier, unit=replace(carrier.unit, star=new_star,
                                             equips=list(new_equips)))
    if isinstance(carrier, Unit):
        return replace(carrier, star=new_star, equips=list(new_equips))
    raise TypeError(f'merge 载体形状不支持: {type(carrier).__name__}')


def merge_step_once(bench: list[BenchSlot | None],
                    deployed: list[Unit | None],
                    overflow: list[BenchSlot]) -> tuple[str, int] | None:
    """单级 3 合 1(gain-chain.md §2.2 升星判断):判一次合成、就地推进三域工作表,返回升星
    产物身份 ``(char_id, star+1)``;无同名同星 3 只 → None(链终止)。

    规则逐条对齐 ``cw_merge_simulate.merge_simulate`` 不动点合并段
    (:206-279;交叉核对测试校验同池同输入终态一致,禁第二套语义):
    - 合成池 = bench ∪ deployed ∪ overflow(满栏溢出件必须进池,否则
      合成永不触发);分组键 = (char_id, star);扫描序 = bench 槽位升序
      → deployed 下标升序 → overflow 表序(与 merge_simulate 内部扫描
      同序,交叉核对前提);
    - 载体:take 中含场上 → 场上那个的位置;全备战 → 最左(take[0]);
    - 素材摘除 = 置 None / 删溢出项(降序摘除防位移);装备继承 = 被消耗
      两只的装备全量并入载体;
    - 溢出件合成腾槽归位优先(:275-279 同款):合成摘除腾出的空槽优先
      承接仍滞留的溢出件,归位不下的留在溢出表;
    - 场上同名同星 ≤1 恒成立不变量:违例即抛(模型错当场暴露)。

    递归深度有界靠星级/件数自然收敛(op-layer「循环无上限」纪律同源,
    不设计数防御)。
    """
    scan: list[tuple[str, int, object, tuple[str, int] | None]] = (
        [('bench', i, b, _entry_ident(b))
         for i, b in enumerate(bench) if b is not None]
        + [('dep', i, d, _entry_ident(d))
           for i, d in enumerate(deployed or []) if d is not None]
        + [('ovf', j, s, _entry_ident(s))
           for j, s in enumerate(overflow)])
    for _dom, _idx, _item, ident in scan:
        if ident is None or not ident[0]:
            continue
        cid, cstar = ident
        group = [e for e in scan if e[3] == (cid, cstar)]
        if len(group) < 3:
            continue
        take = group[:3]
        # 载体:场上优先;全备战(含溢出件)→ take[0](扫描序即最左)
        dep_take = next((e for e in take if e[0] == 'dep'), None)
        carrier_entry = dep_take if dep_take is not None else take[0]
        inherited: list[str] = []
        ovf_remove: list[int] = []
        for e in take:
            if e is carrier_entry:
                continue
            inherited += _entry_equips(e[2])
            if e[0] == 'ovf':
                ovf_remove.append(e[1])
            elif e[0] == 'bench':
                bench[e[1]] = None
            else:
                deployed[e[1]] = None
        for j in sorted(ovf_remove, reverse=True):
            overflow.pop(j)   # 降序摘除:低索引摘除不位移未摘高索引项
        carrier = carrier_entry[2]
        new_star = cstar + 1
        new_carrier = _bump_carrier(carrier, new_star,
                                    _entry_equips(carrier) + inherited)
        if carrier_entry[0] == 'dep':
            deployed[carrier_entry[1]] = new_carrier
        elif carrier_entry[0] == 'bench':
            bench[carrier_entry[1]] = new_carrier
        else:
            # 溢出表索引可能已被本级素材摘除位移,按对象身份重定位
            j = next(k for k, s in enumerate(overflow) if s is carrier)
            overflow[j] = new_carrier
        # 溢出归位:合成腾出的空槽优先承接(merge_simulate 溢出件腾槽归位同款)
        still: list[BenchSlot] = []
        for s in list(overflow):
            if bench_place(bench, s) is None:
                still.append(s)
        overflow[:] = still
        # 恒成立不变量:场上同名同星 ≤1(merge_simulate 出参断言同源)
        dep_keys = [e[3] for e in
                    [('dep', i, d, _entry_ident(d))
                     for i, d in enumerate(deployed) if d is not None]
                    if e[3] is not None and e[3][0]]
        if len(dep_keys) != len(set(dep_keys)):
            raise AssertionError(
                f'merge_step_once 不变量违例:场上同名同星 >1({dep_keys})')
        return (cid, new_star)
    return None


# ============================================================ 链内工作池与写腿


def _select_write(gs: GameState, rand: bool) -> Callable[..., None]:
    """链写通道选择单一收束(同源委托 :func:`anchor_aware_write`——择道
    语义单一源住 cw_game_state,与效果账本桥共享,防 kernel 内循环
    import;全部写选择点必经本口,禁散写 ``write_logic_rand if rand`` 形态)。

    语义(与委托口一致):形参 ``rand=True``(采样链)或容器未锚定
    (开局种子底座窗口)→ ``write_logic_rand``——未锚定期链的落账是
    「未验证推算」,走随机态让首观察静默覆盖;锚定后恢复形参语义
    (rand=False → ``write_logic`` 确定面,失配网原样生效,P2/P3 位面
    环境送卡的落位验证信号保留)。直构容器视同未锚定。
    """
    return anchor_aware_write(gs, rand)


def _slot_sig(slots: list) -> list:
    """槽表值签名(变更检测用;判「该域是否需要落一行」,与
    cw_effect_inventory._slot_sig 同构——签名只驱动落行,不承载语义)。"""
    out = []
    for x in (slots or []):
        if x is None:
            out.append(None)
            continue
        ident = _entry_ident(x)
        out.append(None if ident is None else (str(getattr(x, 'kind', 'unit')
                                                   or 'unit'),) + ident
                        + (tuple(_entry_equips(x)),))
    return out


def _dep_sig(deployed: list) -> list:
    """deployed 下标表值签名(变更检测用;None 洞原样)。"""
    out = []
    for d in (deployed or []):
        out.append(None if d is None
                   else (str(d.char_id), int(d.star or 1),
                         tuple(d.equips or ())))
    return out


@dataclass
class _WorkPool:
    """链内工作池:gs 现帧派生的三域工作副本 + 构建时签名(gain-chain.md §2 落位
    基座同 grant_bench_unit_cascade:bench 槽表 + 上阵定长 10 下标工作表
    ——窗口期桥,视图同源派生)。"""

    bench: list[BenchSlot | None]
    dep: list[Unit | None]
    ovf: list[BenchSlot]
    orig_view: BenchView
    orig_dep_view: object = None
    bench_sig: list = field(default_factory=list)
    dep_sig: list = field(default_factory=list)
    #: 构建时溢出位身份('' = 溢出位空;容器字段只存身份串,星级不入
    #: 容器——链记星级经 ovf_star 线程递归帧传递,观察来源按 1 兜底)
    ovf_name: str = ''


def _build_pool(gs: GameState,
                ovf_star: int | None) -> _WorkPool | None:
    """gs 现帧 → 工作池(回调子链会写 gs,升星判断前必须重建——回调
    补齐的第三只就在新帧里;bench 未观察 = 无池,调用方跳过合成)。

    溢出位来源两分(gain-chain.md §2.2 升星判断 合成池口径):链内溢出单位含链记星级;
    观察来源的溢出卡星级缺读按 1 兜底(现行口径,cw_game_state.py
    overflow_card 字段注释)。
    """
    orig_view = gs.bench.value
    if orig_view is None:
        return None
    pool = _WorkPool(bench=list(orig_view.slots),
                     dep=deployed_indexed_of_view(gs.deployed.value),
                     ovf=[], orig_view=orig_view,
                     orig_dep_view=gs.deployed.value)
    card = str(gs.overflow_card.value or '')
    if card in BENCH_ITEM_NAMES:
        # 占席道具身份(实机真值:道具与角色同款溢出语义)→ 惰性槽件,
        # 禁造 Unit 假身份进合成素材组(词表单一源 = cw_investments.py::
        # BENCH_ITEM_NAMES)
        pool.ovf.append(BenchSlot(kind='supply_box'))
    elif card:
        pool.ovf.append(BenchSlot(kind='unit', unit=Unit(
            char_id=card, star=int(ovf_star) if ovf_star is not None else 1)))
    pool.ovf_name = card
    pool.bench_sig = _slot_sig(pool.bench)
    pool.dep_sig = _dep_sig(pool.dep)
    return pool


def _overflow_occupied(gs: GameState) -> bool:
    """溢出位占用判定:身份非空,或告警在场而身份未识别(True ∧ '' =
    有卡未识别,字段注释口径)——两种形态都视为占位,第二次溢出禁猜空位。"""
    return bool(gs.overflow_card.value) or gs.overflow_warning.value is True


def _write_merge_step(gs: GameState, pool: _WorkPool, *, rand: bool,
                      sig: ChannelSig, producer: str, evidence: str) -> None:
    """单级合成后的容器写(受影响域各落一行,merge_cascade_write 范式:
    签名比对判「是否需要落行」;行域载体在场上 = bench + deployed 两行
    ——deployed 单字段视图整值替换,合一写;溢出位
    腾空 → overflow 两字段成对清写)。"""
    write = _select_write(gs, rand)
    if _slot_sig(pool.bench) != pool.bench_sig:
        write(gs.bench, bench_view_of_working(pool.bench, pool.orig_view),
              produced_by=producer, evidence=evidence, sig=sig)
    if _dep_sig(pool.dep) != pool.dep_sig:
        write(gs.deployed,
              deployed_view_of_indexed(pool.dep, pool.orig_dep_view),
              produced_by=producer, evidence=evidence, sig=sig)
    if pool.ovf_name and not pool.ovf:
        # 溢出件被合成消费/腾槽归位 → 溢出位腾空,两字段成对清写
        #(与落位写对称;下帧 heavy 实读覆盖修正)
        write(gs.overflow_warning, False, produced_by=producer,
              evidence=evidence, sig=sig)
        write(gs.overflow_card, '', produced_by=producer, evidence=evidence,
              sig=sig)
    elif pool.ovf and not pool.ovf_name:
        # 理论不可达(溢出位只能经落位写产生);保守写身份防账面漂移
        u = pool.ovf[0].unit
        if u is not None:
            write(gs.overflow_card, str(u.char_id), produced_by=producer,
                  evidence=evidence, sig=sig)


class _ChainAcc:
    """链内递归帧共享累计器(效果名/合成级数/写步编号;gain-chain.md §2 evidence
    后缀 ``#mergeN`` 编号沿 merge on_step 先例)。"""

    def __init__(self) -> None:
        self.effects: list[str] = []
        self.merges: int = 0
        self.step: int = 0


def _gain_character_core(gs: GameState, name: str, star: int, *, rand: bool,
                         sig: ChannelSig, evidence: str, producer: str,
                         enter: bool, ovf_star: int | None,
                         acc: _ChainAcc) -> GainOutcome:
    """:func:`gain_character` 递归核(帧内固定时序 gain-chain.md §2:落位(仅
    enter 帧)→ 回调 → 单级升星判断 → 产物递归(enter=False,产物已在
    载体位,不再落位——升星产物重进获得角色的语义 = 回调 + 后续升星
    判断,merge_simulate 载体留原位的落点规则不允许二次落位)。"""
    placed_flag = False
    landing = 'skipped'
    if enter:
        if gs.bench.value is None:
            # bench 未观察(None)= 开局种子底座下生产不可达(局容器缓存
            # 单例冷建即种);直构/sim 域仍可 None → 拒落档零写,无缺陷
            # 发出(缺陷 kind 已停用,真值归首观察覆盖)。
            return GainOutcome(placed=False, landing='skipped',
                               merge_levels=acc.merges,
                               effects=tuple(acc.effects),
                               detail='bench_unobserved')
        pool = _build_pool(gs, ovf_star)
        assert pool is not None   # bench 已判非 None,构建恒有池
        write = _select_write(gs, rand)
        slot = BenchSlot(kind='unit', unit=Unit(char_id=name, star=star))
        if bench_place(pool.bench, slot) is not None:
            write(gs.bench, bench_view_of_working(pool.bench,
                                                  pool.orig_view),
                  produced_by=producer, evidence=f'{evidence}#place',
                  sig=sig)
            placed_flag = True
            landing = 'bench'
        elif _overflow_occupied(gs):
            # 溢出位已被占(链内连环授予第二次溢出):游戏行为未实证 →
            # 零写 + 留存证据,禁猜(gain-chain.md §6)
            _emit_defect(field_name='overflow_card',
                         expected='溢出位空(可落第二次溢出)',
                         actual=f'溢出位已被占(card={gs.overflow_card.value!r},'
                                f'warning={gs.overflow_warning.value})',
                         evidence=evidence, sig=sig,
                         kind=DEFECT_OVERFLOW_TAKEN)
            return GainOutcome(placed=False, landing='skipped',
                               merge_levels=acc.merges,
                               effects=tuple(acc.effects),
                               detail='overflow_slot_taken')
        else:
            # 席满 → 溢出落位(配套裁定:溢出建模):两字段各一行、同 evidence 同
            # sig 同组;星级不入容器字段(只有身份串),链内工作池自记
            #(ovf_star 线程传给升星判断;写入即知真值,不依赖观察兜底)
            pool.ovf.append(slot)
            write(gs.overflow_warning, True, produced_by=producer,
                  evidence=f'{evidence}#place', sig=sig)
            write(gs.overflow_card, name, produced_by=producer,
                  evidence=f'{evidence}#place', sig=sig)
            placed_flag = True
            landing = 'overflow'
            ovf_star = star
    # 回调(升星产物也触发;回调可递归调任意链原语,递归子链的 rand 按
    # 效果自身性质传 gain-chain.md §5)——回调先于升星:回调可能补齐第三只
    acc.effects.extend(on_character_gained(gs, name, star, rand=rand,
                                           sig=sig))
    # 升星判断(单级;回调子链已写 gs,必须重建工作池再判)
    pool = _build_pool(gs, ovf_star)
    if pool is not None:
        product = merge_step_once(pool.bench, pool.dep, pool.ovf)
        if product is not None:
            acc.merges += 1
            acc.step += 1
            _write_merge_step(gs, pool, rand=rand, sig=sig,
                              producer=producer,
                              evidence=f'{evidence}#merge{acc.step}')
            new_ovf_star = (int(pool.ovf[0].unit.star)
                            if pool.ovf and pool.ovf[0].unit is not None
                            else None)
            # 升星产物重进获得角色(回调 → 升星判断 → …;无三连即终止)
            _gain_character_core(gs, product[0], product[1], rand=rand,
                                 sig=sig, evidence=evidence,
                                 producer=producer, enter=False,
                                 ovf_star=new_ovf_star, acc=acc)
    return GainOutcome(placed=placed_flag, landing=landing,
                       merge_levels=acc.merges,
                       effects=tuple(acc.effects), detail='')


# ============================================================ 三原语(gain-chain.md §2)


def gain_invest_env(gs: GameState, session: object, env_name: str, *,
                    rand: bool, sig: ChannelSig,
                    rng: random.Random | None = None,
                    producer: str = GAIN_CHAIN_PRODUCER) -> GainOutcome:
    """获得投资环境(gain-chain.md §2.1):

    0. **无效载荷拒绝(前置)**:归一后名为空/``'?'`` = 零写 + 缺陷留存证据
       (``PICK_INVEST_INVALID_PAYLOAD``)——无效输入拒绝(零写 + 留存证据
       纪律),非防重复保护;
    1. **注册** = ``active_env`` 逻辑写(写端署名 = producer;选择事实
       产生在动作执行时,契约 = gain-chain.md §2.1;写值 = 归一后名);
    2. **效果账本登记**(best-effort:失败 log + 留存证据不阻塞;session=None
       = 登记腿跳过、容器写照常,与 report 函数 session 缺省语义同构);
    3. **触发环境效果**(on_env_gained)。

    ``rng`` = 环境随机支(chars_random_immediate)采样注入,透传
    on_env_gained(缺省回退在该函数体内,与 gain_invest_strategy 的 rng
    形参同构)。

    容器写腿零吞错:写/回调效果腿异常上抛。
    """
    canon = normalize_invest_name(str(env_name or ''))
    if not canon or canon == '?':
        _emit_defect(field_name='active_env',
                     expected='有效投资环境名',
                     actual=f'无效载荷:{env_name!r}',
                     evidence='gain_invest_env', sig=sig,
                     kind=PICK_INVEST_INVALID_PAYLOAD)
        return GainOutcome(placed=False, landing='skipped', merge_levels=0,
                           effects=(), detail='invalid_payload')
    write = _select_write(gs, rand)
    write(gs.active_env, canon, produced_by=producer,
          evidence=f'gain_invest_env:{canon}', sig=sig)
    # 节点序列场字段写腿(设计 §2.1,**写点唯一**):修饰规则唯一
    # 计算点 = resolve_plane_node_seqs,注册即落全量(白名单内修饰表/
    # 白名单外默认表,无半态);通道 = write_logic(序列由 desc 规则化
    # 确定,可准确计算 → 逻辑写,非采样面),插在 active_env 落账后。
    # live 与 sim 同走本获得链(report_action_pick_invest_env_param 同源),
    # 单点覆盖双端。
    gs.write_logic(gs.node_seq_by_plane,
                   resolve_plane_node_seqs(canon),
                   produced_by=producer, evidence='node_seq:env', sig=sig)
    if session is not None:
        try:
            register_portal_from_env(session, env_name)
        except Exception as e:  # noqa: BLE001  登记腿 best-effort(gain-chain.md §6)
            log.warning(f'[cw-gain] portal 登记腿失败(不阻塞):{env_name} {e}')
            _emit_defect(field_name='active_env', expected='portal 登记成功',
                         actual=f'登记腿异常:{e}',
                         evidence=f'gain_invest_env:{env_name}', sig=sig,
                         kind=DEFECT_PORTAL_REGISTER)
    effects = on_env_gained(gs, session, env_name, rand=rand, sig=sig,
                            rng=rng)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


def gain_character(gs: GameState, name: str, star: int, *, rand: bool,
                   sig: ChannelSig, evidence: str,
                   producer: str) -> GainOutcome:
    """获得角色(gain-chain.md §2 固定时序):落位(备战空槽 → bench_place;席满 →
    溢出落位写 overflow 两字段;溢出位被占 → 零写留存证据,bench 未观察 =
    直构域拒落零写)→
    on_character_gained 回调 → 单级 3 合 1 升星判断(池 = 备战 ∪ 上阵 ∪
    溢出)→ 升星产物递归重进本原语。链内所有写共享入口 sig(gain-chain.md §2),
    evidence 加 ``#place``/``#mergeN`` 后缀区分。

    溢出善后(腾位/卖牌)不归链——链只如实记账(gain-chain.md §2)。
    """
    acc = _ChainAcc()
    return _gain_character_core(gs, name, star, rand=rand, sig=sig,
                                evidence=evidence, producer=producer,
                                enter=True, ovf_star=None, acc=acc)


def gain_equipment(gs: GameState, item: str, *, rand: bool,
                   sig: ChannelSig, evidence: str,
                   producer: str) -> GainOutcome:
    """获得装备(gain-chain.md §2):equips 追加入栏(栏未观察 = 直构域
    拒落零写)→
    on_equipment_gained 回调(装备获得→送单位数据表分派)。装备无升星
    判断;子链合成级数留存证据在子链遥测行,本出参 merge_levels 恒 0。"""
    inv = gs.equips.value
    if inv is None:
        # equips 未观察(None)= 开局种子底座下生产不可达(局容器缓存
        # 单例冷建即种);直构/sim 域仍可 None → 拒落档零写,无缺陷
        # 发出(缺陷 kind 已停用,真值归首观察覆盖)。
        return GainOutcome(placed=False, landing='skipped', merge_levels=0,
                           effects=(), detail='equips_unobserved')
    write = _select_write(gs, rand)
    write(gs.equips, list(inv) + [item], produced_by=producer,
          evidence=f'{evidence}#equip', sig=sig)
    effects = on_equipment_gained(gs, item, rand=rand, sig=sig)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


def gain_bench_item(gs: GameState, item: str, *, rand: bool,
                    sig: ChannelSig, evidence: str,
                    producer: str = GAIN_CHAIN_PRODUCER) -> bool:
    """获得占席道具(占席道具公开发放口;命名沿 gain_character/gain_equipment
    系):落位语义全部复用 :func:`_place_bench_item`(备战空槽 → 席满
    溢出落位 → 溢出位被占零写留存证据,2026-09-24 道具落位语义)。返回是否
    落位(备战槽或溢出位)。``rand=False`` = 确定发放(策略箱腿/环境发放
    同约定,gain-chain.md §5);``producer`` 缺省 = 链缺省署名。

    公开动机(kernel 策略发放面补「占席道具」形态,迭代
    2026-09-24-advanced-armory-box design §2.2):本原语公开前效果体
    (cw_gain_effects)无占席道具发放口可消费——骇客卡 bench 腿走
    gain_character,道具腿无对应入口。
    """
    return _place_bench_item(gs, item, rand=rand, evidence=evidence,
                             sig=sig, producer=producer)


def _node_frame(gs: GameState) -> str:
    """链内 frame 字符串(「位面-轮」统一标识,如 ``2-3``;节点未观察 =
    空——登记腿 evidence 用;编号时代的 p{plane}-r{round} 双形态随键
    表示统一,消除同 run 双形态并立,迭代
    2026-10-12-abolish-node-ordinal 披露 2)。"""
    _nd = gs.node.value
    return (f'{_nd.plane}-{_nd.round_num}' if _nd is not None else '')


def gain_invest_strategy(gs: GameState, session: object,
                         strategy_name: str, *, rand: bool,
                         sig: ChannelSig, rng: random.Random | None = None,
                         producer: str = GAIN_CHAIN_PRODUCER) -> GainOutcome:
    """获得投资策略(gain-chain.md §2 四原语之一;三段式
    对齐 :func:`gain_invest_env`):

    0. **无效载荷拒绝(前置)**:归一后名为空/``'?'`` = 零写 + 缺陷留存证据
       (``PICK_INVEST_INVALID_PAYLOAD``)——无效输入拒绝(零写 + 留存证据
       纪律),非防重复保护;
    1. **注册**:`gs.active_strategies` **按名字去重追加**(归一名已在
       列表 → 跳写;持卡列表写入语义 = 数据卫生,裁定「增加持有的投资
       策略时,按名字去重就行了」;跳写后登记/效果腿照常);
    2. **效果账本登记**(best-effort:`session=None` = 跳过[局外/测试
       形态],容器写照常):``STRATEGY_EFFECTS`` 归一名命中 →
       ``effects.register_strategy`` + burst 桥 ``apply_effect_burst_grant``
       + 板面重写桥 ``apply_board_rewrite``
       (acquired_key = 节点序位快照);失败 log + 缺陷留存证据(``DEFECT_STRATEGY_
       REGISTER``)、不阻塞;
    3. **触发策略效果**:`on_strategy_gained`(查 ``PICK_INVEST_EFFECTS``
       分派;未收录卡安静不写)。

    rand 纪律:投资策略确认 = 确定性入口(False);效果体含采样(骇客
    改件)→ 对其子链翻转 rand=True(§5)。``rng`` = 采样注入点(缺省
    ``random.Random()`` 生成点在 :func:`on_strategy_gained` 内;sim 可
    播种)。容器写腿零吞错;登记腿 best-effort。
    """
    canon = normalize_invest_name(str(strategy_name or ''))
    if not canon or canon == '?':
        _emit_defect(field_name='active_strategies',
                     expected='有效投资策略名',
                     actual=f'无效载荷:{strategy_name!r}',
                     evidence='gain_invest_strategy', sig=sig,
                     kind=PICK_INVEST_INVALID_PAYLOAD)
        return GainOutcome(placed=False, landing='skipped', merge_levels=0,
                           effects=(), detail='invalid_payload')
    # ① 注册(按名字去重追加;跳写后登记/效果腿照常)
    cur = list(gs.active_strategies.value or [])
    write = _select_write(gs, rand)
    if canon not in cur:
        write(gs.active_strategies, cur + [canon], produced_by=producer,
              evidence=f'gain_invest_strategy:{canon}', sig=sig)
    # ② 效果账本登记(best-effort 腿)
    if session is not None:
        try:
            _spec = STRATEGY_EFFECTS.get(canon)
            if _spec is not None:
                _key = _portal_acquired_key(gs, session)
                _frame = _node_frame(gs)
                gs.effects.register_strategy(_spec, _key)
                apply_effect_burst_grant(gs, _spec, frame=_frame)
                _rw = apply_board_rewrite(gs, _spec, frame=_frame)
                if _rw is not None:
                    log.info('[cw-gain] 板面重写桥:%s(退款 %s/清空域 %s)',
                             _rw.rewrite, _rw.refund_gold,
                             ','.join(_rw.cleared_fields) or '无')
                log.info('[cw-gain] 效果账本登记:%s(acquired=%s)', canon,
                         _key)
        except Exception as e:  # noqa: BLE001  登记腿 best-effort(gain-chain.md §6)
            log.warning('[cw-gain] 策略登记腿失败(不阻塞):%s %s', canon, e)
            _emit_defect(field_name='active_strategies',
                         expected='效果账本登记成功',
                         actual=f'登记腿异常:{e}',
                         evidence=f'gain_invest_strategy:{canon}', sig=sig,
                         kind=DEFECT_STRATEGY_REGISTER)
    # ③ 触发策略效果
    effects = on_strategy_gained(gs, canon, rand=rand, sig=sig, rng=rng)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


# ============================================================ 枚举回调(gain-chain.md §3;现役四枚举)
# (无注册表——用户裁定:回调函数体内枚举即收敛,不设注册机构。)


def _place_bench_item(gs: GameState, item: str, *, rand: bool,
                      evidence: str, sig: ChannelSig,
                      producer: str = GAIN_CHAIN_PRODUCER) -> bool:
    """占席道具(武装箱系)落位(角色落位同构:_build_pool/bench_place/
    _select_write 序;槽件 = ``BenchSlot(kind='supply_box')``,双端同一
    获得链——sim 世界写入即容器写)。席满 → 溢出落位(实机真值 2026-09-24
    用户确认:道具与角色同款——落溢出席并阻断进入战斗;两字段直写,身份 =
    道具名,消费方按 BENCH_ITEM_NAMES 判 kind);溢出位已被占 → 零写 +
    留存证据禁猜(与角色腿同款,gain-chain.md §6)。返回是否落位(备战槽或
    溢出位)。``producer`` = 写端署名(缺省 = 链缺省,环境通道现役调用点
    不传即行为不变;策略效果体经公开口 :func:`gain_bench_item` 透传)。"""
    if gs.bench.value is None:
        return False
    pool = _build_pool(gs, None)
    assert pool is not None   # bench 已判非 None,构建恒有池
    write = _select_write(gs, rand)
    slot = BenchSlot(kind='supply_box')
    if bench_place(pool.bench, slot) is not None:
        write(gs.bench, bench_view_of_working(pool.bench, pool.orig_view),
              produced_by=producer, evidence=f'{evidence}#place',
              sig=sig)
        return True
    if _overflow_occupied(gs):
        # 溢出位已被占(席满 + 溢出位再溢出):游戏行为未实证 → 零写 +
        # 留存证据,禁猜(角色腿同款,gain-chain.md §6)
        _emit_defect(field_name='overflow_card',
                     expected='溢出位空(可落第二次溢出)',
                     actual=f'溢出位已被占(card={gs.overflow_card.value!r},'
                            f'warning={gs.overflow_warning.value}),'
                            f'{item} 未落位',
                     evidence=evidence, sig=sig,
                     kind=DEFECT_OVERFLOW_TAKEN)
        return False
    # 席满 → 溢出落位(两字段各一行,同 evidence 同 sig;道具无升星语义,
    # 不进合成判断)
    write(gs.overflow_warning, True, produced_by=producer,
          evidence=f'{evidence}#place', sig=sig)
    write(gs.overflow_card, item, produced_by=producer,
          evidence=f'{evidence}#place', sig=sig)
    return True


def on_env_gained(gs: GameState, session: object, env_name: str, *,
                  rand: bool, sig: ChannelSig,
                  rng: random.Random | None = None) -> tuple[str, ...]:
    """「获得投资环境」触发型效果枚举(gain-chain.md §3)。

    - ``ENV_GIFTS`` 命中 → **先按 advisor 分道,两道互斥**:advisor=False
      (契约,直接送卡)→ chars_immediate 逐个 ``gain_character(char, 1★)``
      (1★ 先验同句式先例:骇客效果体同族,现役 =
      ``cw_gain_effects.py::PICK_INVEST_EFFECTS``;先验错 = 响停修因非
      随机);advisor=True(特邀专家,顾问入商店)→ **不入席**——容器无
      商店池字段,身份只进遥测申报一行(先例 = advisor 申报行同族,正本
      = gain-chain.md §3 advisor 条);chars_immediate 在 advisor 行仅作
      顾问身份输入,禁再入席;
    - **环境即时金腿**(世界规则,注册表结构化通道):环境经济
      ``economy.gold_instant`` 非零 → gold 直加(两执行面同源;旧 sim
      引擎私有腿随驱动反转停用,规则落本链为单一源);
    - **追加随机环境申报行**(``ENV_REROLL_NAMES`` 命中,金腿之后):选卡
      后游戏随即再随机获得一个环境,该掷骰 live 端不可观察(active_env
      无观察覆盖通道)→ 申报留证一行(``kind = ENV_REROLL_DECL``,语义
      申报非缺陷告警),行为 fail-closed(容器写序列与普通环境逐位一致);
      世界掷骰 = sim 后端追加获得腿二次入链
      (``cw_sim_backend._on_invest_picked``,原语复用),双端各产一行
      如实记录「选择时点真值未知」;
    - **随机支**(``chars_random_immediate``,具名支之后):规格过滤池
      (random_char_pool)内均匀掷骰选名 → ``gain_character`` 落席,星级
      = spec.star;效果体含采样 → 子链 rand=True(gain-chain.md §5)——
      未锚定期(开局窗)本就走 write_logic_rand,rand=True 声明采样语义
      并保锚定后不进失配网(实机猜错 = 首观察静默覆盖,
      logic_rand_outcome 收尾,不触发告警停局)。效果串
      ``env_gift_random:<名>@<星>star``(与具名支 ``env_gift:`` 前缀分离,
      采样发放可独立过滤审计);``rng`` 缺省回退自掷(直构/测试形态;
      正式接线由上报函数条件解析传入,sim 装配 = 流键 rng 即世界真值)。
      首例 = 人才引进(id 109,开局 1 个随机 4 费,星级先验 1);
    - **道具通道**(``items_immediate`` + ``items_scheduled``):道具 =
      占席待开箱,非角色非装备。即时支:落位写入(角色落位同构:备战空槽放
      ``BenchSlot(kind='supply_box')``,双端同一获得链,sim 世界写入即
      容器写);席满 = 溢出落位(实机真值:道具与角色同款——落溢出席并
      阻断进入战斗;溢出位被占 = 零写留存证据,helper 内);效果串
      ``item_gift:<名>`` 恒登记(数量 = 元素重复次数),开箱链由外循环
      画面分发承接(武装箱选择画面独立建档)。定时支:逐项入容器队列
      ``pending_item_grants``(一次 write 回写整表,登记不落席),效果串
      ``item_scheduled:<名>@<节点键>``(数量 = 元素重复次数,发放事实
      登记与即时通道同阶),到点发放 = :func:`discharge_due_item_grants`;
    - 查无效果(表外环境)= 安静不写(用户裁定),真值归观察覆盖。
      (欢愉契约条件腿不在本枚举:其正式模型 = 银狼策划选择上报动作落地时点的
      条件腿 rider,住 ``cw_action_report.pick_planner``,触发事件 =
      头号玩家选项弹窗被处理。)
    """
    _name = normalize_invest_name(env_name)
    _env = INVESTMENT_ENVS.get(_name)
    _eff = _env.economy if _env is not None else None
    if _eff is not None and _eff.gold_instant:
        write = _select_write(gs, rand)
        write(gs.gold, int(gs.gold.value or 0) + int(_eff.gold_instant),
              produced_by=GAIN_CHAIN_PRODUCER,
              evidence=f'on_env_gained:instant_gold:{_name}', sig=sig)
    if _name in ENV_REROLL_NAMES:
        # 追加随机环境型:选卡后游戏随即再随机获得一个环境,该掷骰 live 端
        # 不可观察(active_env 无观察覆盖通道,选择事实与真值不可分辨)——
        # 申报留证,行为 fail-closed(选卡容器写序列与普通环境逐位一致);
        # sim 端随后由后端追加获得腿二次入链(cw_sim_backend.
        # _on_invest_picked),本行为历史申报行双端各产一行如实记录。
        _emit_defect(field_name='active_env',
                     expected='追加卷中环境名(游戏侧事实)',
                     actual=f'{_name}(选择事实;真值不可观察)',
                     evidence=f'on_env_gained:{_name}', sig=sig,
                     kind=ENV_REROLL_DECL)
    grant = ENV_GIFTS.get(_name)
    if grant is None:
        return ()
    if grant.advisor:
        for char in grant.chars_immediate:
            _emit_defect(field_name='shop_pool', expected=None,
                         actual=f'{char} 顾问入商店(advisor 申报,不入席)',
                         evidence=f'on_env_gained:{_name}', sig=sig,
                         kind=DEFECT_ADVISOR_DECL)
        return (f'advisor_decl:{_name}',)
    effects: list[str] = []
    for char in grant.chars_immediate:
        # 送卡为确定发放(非采样)→ rand 原样透传(gain-chain.md §5)
        gain_character(gs, char, 1, rand=rand, sig=sig,
                       evidence=f'on_env_gained:{_name}',
                       producer=GAIN_CHAIN_PRODUCER)
        effects.append(f'env_gift:{char}')
    if grant.chars_random_immediate:
        # 随机支:效果体含采样 → 子链 rand=True(gain-chain.md §5 递归
        # 调用点按效果自身性质传参)。星级 = spec.star(人才引进 1 = 先验
        # 非结构值,先验错走随机态观察覆盖不响停);rng 缺省回退自掷
        # (直构/测试形态;正式接线 = 上报函数条件解析传入,sim 装配 =
        # 流键 rng 即世界真值,on_strategy_gained 的 roll_rng 同款回退)。
        roll_rng = rng if rng is not None else random.Random()
        for spec in grant.chars_random_immediate:
            pool = random_char_pool(spec)
            if not pool:
                # 构建期已闸(_validate_env_gifts 池非空),运行期空 =
                # 注册表漂移;零写留 log 防御分支(不改容器,不炸链)
                log.warning(
                    f'[cw-gain] 随机赠卡池空(注册表漂移?):'
                    f'{_name} cost={spec.cost} type_tag={spec.type_tag!r}')
                continue
            name = roll_rng.choice(pool)
            gain_character(gs, name, spec.star, rand=True, sig=sig,
                           evidence=f'on_env_gained:{_name}',
                           producer=GAIN_CHAIN_PRODUCER)
            effects.append(f'env_gift_random:{name}@{spec.star}star')
    for item in grant.items_immediate:
        # 落位 = 角色落位同构(_build_pool/bench_place/write 序;席满 →
        # 溢出落位,溢出位被占 = 零写留存证据,helper 内);效果串恒登记
        #(发放事实,与落位成败解耦)
        _place_bench_item(gs, item, rand=rand,
                          evidence=f'on_env_gained:{_name}', sig=sig)
        effects.append(f'item_gift:{item}')
    if grant.items_scheduled:
        # 定时支:登记不落席,入队待到点(一次 write 回写整表;entry 形见
        # cw_game_state.pending_item_grants 注)。节点键格式 import 期已闸
        #(cw_investments._validate_env_gifts),此处直解析。
        queued = list(gs.pending_item_grants.value or [])
        for _node_key, _item in grant.items_scheduled:
            _plane_s, _round_s = _node_key.split('-')
            queued.append({'env': _name, 'plane': int(_plane_s),
                           'round_num': int(_round_s), 'item': _item})
            effects.append(f'item_scheduled:{_item}@{_node_key}')
        write = _select_write(gs, rand)
        write(gs.pending_item_grants, queued, produced_by=GAIN_CHAIN_PRODUCER,
              evidence=f'on_env_gained:{_name}', sig=sig)
    return tuple(effects)


def discharge_due_item_grants(gs: GameState, *, plane: int, round_num: int,
                              rand: bool, sig: ChannelSig) -> tuple[str, ...]:
    """定时道具到点发放原语(环境定时发放通道;与 on_env_gained 同区):
    读 ``pending_item_grants`` 现值,按 (plane, round_num) 分割命中/保留,
    命中项逐个 ``_place_bench_item`` 落位(备战空槽 → 席满溢出落位 → 溢出位
    被占零写留存证据,复用即时通道同款道具落位语义),命中非空才一次 write 回写
    保留队列。返回效果串(每命中项 ``item_gift:<名>``,与落位成败解耦,
    即时通道同阶)。

    - rand 语义:环境发放 = 确定发放,调用方传 ``rand=False``(gain-chain.md
      §5;写通道仍经 :func:`_select_write` 单一收束);
    - 零吞错:落位异常上抛(gain-chain.md §6),队列回写收尾;生产挂点
      (sim 进节点收束)无重入面 = 无幂等需求,未来实机挂点接线时按其
      重入面另评(迭代 2026-09-24-scheduled-env-gifts design §2.3);
    - 实机局不接本原语(同迭代 design §2.5 不对称申报):队列登记后保持
      原样,备战真值由观察覆盖。
    """
    due: list[dict] = []
    keep: list[dict] = []
    for entry in list(gs.pending_item_grants.value or []):
        if int(entry['plane']) == plane and int(entry['round_num']) == round_num:
            due.append(entry)
        else:
            keep.append(entry)
    effects: list[str] = []
    for entry in due:
        _place_bench_item(gs, str(entry['item']), rand=rand,
                          evidence=f'discharge_due_item_grants:'
                                   f'p{plane}-r{round_num}', sig=sig)
        effects.append(f"item_gift:{entry['item']}")
    if due:
        write = _select_write(gs, rand)
        write(gs.pending_item_grants, keep, produced_by=GAIN_CHAIN_PRODUCER,
              evidence=f'discharge_due_item_grants:p{plane}-r{round_num}',
              sig=sig)
    return tuple(effects)


def on_character_gained(gs: GameState, name: str, star: int, *,
                        rand: bool, sig: ChannelSig) -> tuple[str, ...]:
    """「获得角色」触发型效果枚举(gain-chain.md §3)。

    初始枚举 = **空集**(暂无已核实的「获得角色时」触发型效果;查无
    效果安静不写,用户裁定)。**本函数 = 该类效果未来的唯一收敛点**——新
    效果核实后在此加分支;递归子链的 rand 按效果自身性质传(gain-chain.md §5)。
    """
    _ = gs, name, star, rand, sig   # 接口位保留(收敛点入参齐全)
    return ()


def on_equipment_gained(gs: GameState, item: str, *, rand: bool,
                        sig: ChannelSig) -> tuple[str, ...]:
    """「获得装备」触发型效果枚举(gain-chain.md §3):消费
    ``EQUIP_ACQUIRE_CONSEQUENCES`` 数据表(装备获得→送出单位;该表是
    游戏数据映射不是效果注册表,保留)→ 命中 → ``gain_character`` 送出
    单位入席递归(表值星级随表;确定发放 → rand 原样透传 gain-chain.md §5)。
    表外件 = 查无效果安静不写。"""
    granted = EQUIP_ACQUIRE_CONSEQUENCES.get(item)
    if granted is None:
        return ()
    name, star = granted
    gain_character(gs, name, star, rand=rand, sig=sig,
                   evidence=f'on_equipment_gained:{item}',
                   producer=GAIN_CHAIN_PRODUCER)
    return (f'equip_consequence:{name}',)


def on_strategy_gained(gs: GameState, strategy_name: str, *, rand: bool,
                       sig: ChannelSig,
                       rng: random.Random | None = None) -> tuple[str, ...]:
    """「获得投资策略」触发型效果枚举(gain-chain.md §3;枚举即收敛
    无注册表):查 ``PICK_INVEST_EFFECTS``(效果内容住
    ``cw_gain_effects.py``,本模块模块级查表)分派效果函数;未收录卡 =
    查无效果安静不写,真值归观察覆盖。``rng`` = 采样注入(缺省
    ``random.Random()`` 在本函数体内生成;效果体含采样 → 对其子链传
    rand=True,§5)。"""
    fn = PICK_INVEST_EFFECTS.get(normalize_invest_name(strategy_name))
    if fn is None:
        return ()
    roll_rng = rng if rng is not None else random.Random()
    return tuple(fn(gs, sig=sig, rng=roll_rng))
