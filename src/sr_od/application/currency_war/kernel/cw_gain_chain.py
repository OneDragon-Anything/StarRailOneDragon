"""货币战争 获得链(gain-chain):获得三原语 + 事件回调枚举 + 单级合成。

链式规范正本 = docs/develop/sr_od/application/currency_war/game_state/
gain-chain.md(原语契约/时序/溢出落位/随机态纪律/失败安全/接入面现状)。
首个接入面(投资环境落地相,``cw_action_report.pick_invest`` portal 支)
消费本模块。

链式过程语义:「获得」= 注册/落位 → 事件回调 → 3 合 1 升星判断 →
升星产物重进获得角色(回调 → 升星判断 → …,无三连同名同星即终止)。回调
先于升星的理由 = 回调可能补齐第三只(用户裁定);升星产物也触发获得角色
回调。

随机态纪律:每个函数一个 ``rand: bool`` 必带入参、递归
透传、效果体含采样时可翻转子链——本次写是否处于随机语义,不承诺全链
一致;写通道 = rand=True 走 ``write_logic_rand``(采样链)、False 走
``write_logic``(确定面)。

失败安全:链原语**零吞错**(容器写腿/回调效果腿异常上抛);
best-effort 边界只在登记/遥测申报腿内(失败 log + 缺陷留证、不阻塞);
未观察(bench/equips)= bug 面:零写 + 留证不停机,根治归观察
补全批;席满且溢出位被占 = 游戏行为未实证:零写 + 留证,禁猜。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    EQUIP_ACQUIRE_CONSEQUENCES,
    register_portal_from_env,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_place,
    deployed_indexed_to_rows,
    deployed_rows_to_indexed,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    GameState,
    Unit,
    _emit_defect,
    bench_view_of_working,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_GIFTS,
    normalize_invest_name,
)

#: 链内写端缺省署名(gain-chain.md §2:写点迁移属申报过的行为变化,新写端新名,
#: 不沿用旧名伪装连续;落地相接入显式传同值)。
GAIN_CHAIN_PRODUCER: str = 'CwGainChain'

#: 缺陷留证 kind 词表(_emit_defect 台账行分键;留证不停机,gain-chain.md §6)。
DEFECT_BENCH_UNOBSERVED: str = 'gain_chain_bench_unobserved'
DEFECT_OVERFLOW_TAKEN: str = 'gain_chain_overflow_slot_taken'
DEFECT_EQUIPS_UNOBSERVED: str = 'gain_chain_equips_unobserved'
DEFECT_ADVISOR_DECL: str = 'gain_chain_advisor_decl'
DEFECT_PORTAL_REGISTER: str = 'gain_chain_portal_register_failed'

#: 欢愉契约条件腿采证期临时翻来源闩的披露键 kind(自 pick_invest 迁入;
#: 「条件腿标记面」:头号玩家触发无观察锚无采样
#: 模型,定谳前触发帧收口自愈留证不停局;**有界显式测量仪表,定谳后
#: 必须撤**——残留 = 临时闩未撤的显式信号)。
JOY_PROVISIONAL_KIND: str = 'joy_contract_provisional'


@dataclass(frozen=True)
class GainOutcome:
    """获得链原语出参(三原语共用;留证/测试用、零决策消费,沿
    ``BenchGrantResult`` 先例 cw_effect_inventory.py:1442)。

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
# 同星 ≤1 不变量),对齐由对拍测试锁「同池同输入下,单级×N 次 ==
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
    (:206-279;对拍测试锁同池同输入终态一致,禁第二套语义):
    - 合成池 = bench ∪ deployed ∪ overflow(满栏溢出件必须进池,否则
      合成永不触发);分组键 = (char_id, star);扫描序 = bench 槽位升序
      → deployed 下标升序 → overflow 表序(与 merge_simulate 内部扫描
      同序,对拍前提);
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
    基座同 grant_bench_unit_cascade:bench 槽表 + 上阵行域下标派生表)。"""

    bench: list[BenchSlot | None]
    dep: list[Unit | None]
    ovf: list[BenchSlot]
    orig_view: BenchView
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
                     dep=deployed_rows_to_indexed(gs.front_row.value,
                                                  gs.back_row.value),
                     ovf=[], orig_view=orig_view)
    card = str(gs.overflow_card.value or '')
    if card:
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
    签名比对判「是否需要落行」;行域载体在场上 = bench+front+back 同号
    三行;溢出位腾空 → overflow 两字段成对清写)。"""
    write = gs.write_logic_rand if rand else gs.write_logic
    if _slot_sig(pool.bench) != pool.bench_sig:
        write(gs.bench, bench_view_of_working(pool.bench, pool.orig_view),
              produced_by=producer, evidence=evidence, sig=sig)
    if _dep_sig(pool.dep) != pool.dep_sig:
        front, back = deployed_indexed_to_rows(pool.dep)
        write(gs.front_row, front, produced_by=producer, evidence=evidence,
              sig=sig)
        write(gs.back_row, back, produced_by=producer, evidence=evidence,
              sig=sig)
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
            # 【待梳理标记】bench 未观察 = bug 面(用户裁定:接管局进来在
            # 备战,观察可补全)——零写 + 留证不停机;根治归观察补全批。
            _emit_defect(field_name='bench',
                         expected='bench 已观察(获得链落位前提)',
                         actual='bench 未观察(None)',
                         evidence=evidence, sig=sig,
                         kind=DEFECT_BENCH_UNOBSERVED)
            return GainOutcome(placed=False, landing='skipped',
                               merge_levels=acc.merges,
                               effects=tuple(acc.effects),
                               detail='bench_unobserved')
        pool = _build_pool(gs, ovf_star)
        assert pool is not None   # bench 已判非 None,构建恒有池
        write = gs.write_logic_rand if rand else gs.write_logic
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
            # 零写 + 留证,禁猜(gain-chain.md §6)
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
                    producer: str = GAIN_CHAIN_PRODUCER) -> GainOutcome:
    """获得投资环境:①注册 = active_env 逻辑写(active_env 注册在动作落地相
    获得链——原点卡前写退役,用户裁定 2026-09-21,正本 = game_state/
    gain-chain.md;新写端新名不沿用旧名伪装连续);
    ②效果账本登记(best-effort:失败 log + 留证不阻塞;session=None
    = 登记腿跳过、容器写照常,与 report 函数 session 缺省语义同构);
    ③触发环境效果(on_env_gained)。

    容器写腿零吞错:写/回调效果腿异常上抛。
    """
    write = gs.write_logic_rand if rand else gs.write_logic
    write(gs.active_env, env_name, produced_by=producer,
          evidence=f'gain_invest_env:{env_name}', sig=sig)
    if session is not None:
        try:
            register_portal_from_env(session, env_name)
        except Exception as e:  # noqa: BLE001  登记腿 best-effort(gain-chain.md §6)
            log.warning(f'[cw-gain] portal 登记腿失败(不阻塞):{env_name} {e}')
            _emit_defect(field_name='active_env', expected='portal 登记成功',
                         actual=f'登记腿异常:{e}',
                         evidence=f'gain_invest_env:{env_name}', sig=sig,
                         kind=DEFECT_PORTAL_REGISTER)
    effects = on_env_gained(gs, session, env_name, rand=rand, sig=sig)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


def gain_character(gs: GameState, name: str, star: int, *, rand: bool,
                   sig: ChannelSig, evidence: str,
                   producer: str) -> GainOutcome:
    """获得角色(gain-chain.md §2 固定时序):落位(备战空槽 → bench_place;席满 →
    溢出落位写 overflow 两字段;溢出位被占/bench 未观察 → 零写留证)→
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
    """获得装备(gain-chain.md §2):equips 追加入栏(栏未观察 = 同 bug 留证规则)→
    on_equipment_gained 回调(装备获得→送单位数据表分派)。装备无升星
    判断;子链合成级数留证在子链遥测行,本出参 merge_levels 恒 0。"""
    inv = gs.equips.value
    if inv is None:
        # 【待梳理标记】未观察 = bug 面(用户裁定):零写 + 留证不停机
        _emit_defect(field_name='equips',
                     expected='equips 已观察(获得链入栏前提)',
                     actual='equips 未观察(None)',
                     evidence=evidence, sig=sig,
                     kind=DEFECT_EQUIPS_UNOBSERVED)
        return GainOutcome(placed=False, landing='skipped', merge_levels=0,
                           effects=(), detail='equips_unobserved')
    write = gs.write_logic_rand if rand else gs.write_logic
    write(gs.equips, list(inv) + [item], produced_by=producer,
          evidence=f'{evidence}#equip', sig=sig)
    effects = on_equipment_gained(gs, item, rand=rand, sig=sig)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


# ============================================================ 三枚举回调(gain-chain.md §3)
# (无注册表——用户裁定:回调函数体内枚举即收敛,不设注册机构。)


def on_env_gained(gs: GameState, session: object, env_name: str, *,
                  rand: bool, sig: ChannelSig) -> tuple[str, ...]:
    """「获得投资环境」触发型效果枚举(gain-chain.md §3)。

    - ``ENV_GIFTS`` 命中 → **先按 advisor 分道,两道互斥**:advisor=False
      (契约,直接送卡)→ chars_immediate 逐个 ``gain_character(char, 1★)``
      (星级未标 = 1★ 同句式先例,先验错 = 响停修因非随机,锚
      pick_invest.py 骇客 bench 腿同款口径);advisor=True(特邀专家,
      顾问入商店)→ **不入席**——容器无商店池字段,身份只进遥测申报
      一行(先例 = pick_invest hacker shop_pool decl);chars_immediate
      在 advisor 行仅作顾问身份输入,禁再入席;
    - 查无效果(表外环境)= 安静不写(用户裁定),真值归观察覆盖。
    - 欢愉契约条件腿(头号玩家触发)标记面:bench/equips 值不变
      ``write_logic_rand`` 翻来源 + 留证行 kind =
      :data:`JOY_PROVISIONAL_KIND`(自 pick_invest 效果函数迁入,行为
      逐位等价;临时测量仪表,定谳后撤闩换正式模型)。
    """
    _name = normalize_invest_name(env_name)
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
    if _name == '欢愉契约':
        # 条件腿(头号玩家触发)临时翻来源闩:值不变 write_logic_rand 翻
        # bench/equips 两域 → 触发帧观察差异收口自愈留证不停局,多局拼
        # 数据;定谳后必须撤(见 JOY_PROVISIONAL_KIND 声明)。
        for dom in ('bench', 'equips'):
            fld = gs.bench if dom == 'bench' else gs.equips
            if fld.value is None:
                continue
            gs.write_logic_rand(fld, fld.value,
                                produced_by=GAIN_CHAIN_PRODUCER,
                                evidence='on_env_gained:欢愉契约#provisional',
                                sig=sig)
            effects.append(f'provisional_mark:{dom}')
        _emit_defect(field_name='bench', expected='joy_conditional_pending',
                     actual='joy_contract_provisional_flip',
                     evidence='on_env_gained:欢愉契约#provisional', sig=sig,
                     kind=JOY_PROVISIONAL_KIND)
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
