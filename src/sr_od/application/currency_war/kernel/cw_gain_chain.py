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

失败安全:链原语**零吞错**(容器写分支/回调效果分支异常上抛);
best-effort 边界只在登记/遥测申报分支内(失败 log + 缺陷留存证据、不阻塞);
唯一调用点级显式例外 = 欢愉契约条件分支授予 rider(住
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
from sr_od.application.currency_war.data.cw_chars import (
    EXPERT_CHARS,
    assert_expert_names,
)
from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    EQUIP_ACQUIRE_CONSEQUENCES,
    EffectKind,
    TriggerKind,
    _portal_acquired_key,
    apply_board_rewrite,
    register_portal_from_env,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_place,
    bench_slot_unit,
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
    _bridge_sig,
    _emit_defect,
    anchor_aware_write,
    apply_effect_burst_grant,
    bench_view_of_working,
    deployed_indexed_of_view,
    deployed_view_of_indexed,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    BENCH_ITEM_KINDS,
    BENCH_ITEM_NAMES,
    ENV_BOSS_GRANTS,
    ENV_GIFTS,
    ENV_REROLL_NAMES,
    INVESTMENT_ENVS,
    STRATEGY_CONDITIONAL_GRANTS,
    STRATEGY_DELAYED_GRANTS,
    STRATEGY_DELAYED_OFFERS,
    STRATEGY_ECONOMY,
    STRATEGY_EFFECTS,
    STRATEGY_ENCOUNTER_BATTLE_GRANTS,
    STRATEGY_GRANTS,
    STRATEGY_WIN_GOLD_GRANTS,
    equips_by_category,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    resolve_plane_node_seqs,
)
from sr_od.application.currency_war.kernel.cw_pool import grant_char_pool

#: 链内写端缺省署名(gain-chain.md §2:写点迁移属申报过的行为变化,新写端新名,
#: 不沿用旧名伪装连续;动作落地接入显式传同值)。
GAIN_CHAIN_PRODUCER: str = 'CwGainChain'

#: 缺陷留存证据 kind 词表(_emit_defect 台账行分键;留存证据不停机,gain-chain.md §6)。
#: 未观察 kind 族(bench/equips 两原生 kind + DEFECT_COND_BENCH_UNOBSERVED
#: 条件形态在场判定)现役生产不可达:开局种子底座下生产链路
#: 阵容/装备域不再有 None,拒落/不判档零写无缺陷发出(词表停用申报正本 =
#: gain-chain.md §6)。
DEFECT_OVERFLOW_TAKEN: str = 'gain_chain_overflow_slot_taken'
DEFECT_PORTAL_REGISTER: str = 'gain_chain_portal_register_failed'
DEFECT_STRATEGY_REGISTER: str = 'gain_chain_strategy_register_failed'
DEFECT_COND_BENCH_UNOBSERVED: str = 'gain_chain_cond_bench_unobserved'

#: 无效载荷拒绝 kind(策略/环境名归一后为空/'?'——零写 + 留存证据;无效输入
#: 拒绝,非防重复保护;正本 = gain-chain.md §2.4-0/§2.1-0)。
PICK_INVEST_INVALID_PAYLOAD: str = 'pick_invest_invalid_payload'

#: 追加随机环境申报行 kind(独立小块,非 DEFECT_ 词表成员:语义 = 申报
#: 非缺陷,不入「缺陷留存证据 kind 词表」块以免破块内前缀分组,沿本模块
#: PICK_INVEST_INVALID_PAYLOAD 先例;通道沿 advisor 申报行同族——申报行
#: 是语义申报非缺陷告警)。追加环境真值 live 不可观察,申报留证;正本 =
#: gain-chain.md §3 追加随机环境段/§6。
ENV_REROLL_DECL: str = 'gain_chain_env_reroll_decl'

#: 敌后破坏(id 146)词缀失效删除分支的采样分支具名键(函数内经
#: :func:`action_sampling_rng` 解析,双端同槽先例 = env_merge_grant;
#: 正本 = 迭代 2026-09-23-invest-effects-calc T-45 设计稿 §2.1 裁决点 b)。
ENV_AFFIX_DISABLE_RNG_TOOL: str = 'env_affix_disable'

#: 敌后破坏删除分支的空容器申报行 kind(选卡时词缀容器空[简报失读等]→
#: 跳过删除:实机已失效而模型未删,偏差全程持续无自愈——该态容器非
#: 随机态,补观察谓词不命中;独立小块沿 ENV_REROLL_DECL 同形,语义申报
#: 非缺陷告警;正本 = T-45 设计稿 §6 披露键 3)。
ENV_AFFIX_DISABLE_EMPTY_DECL: str = 'env_affix_disable_empty_container'

#: 敌后破坏(id 146)环境规范名(枚举即收敛硬编码分支的判定键,单卡
#: 零复用面不入登记表;normalize_invest_name 归一恒等——纯中文名)。
ENV_AFFIX_DISABLE_ENV: str = '敌后破坏'


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
    """合成载体升星 + 装备继承的 frozen 新构造(merge_simulate 同式)。

    产物**显式置 uid=None**(合成产物 = 新实体,实例粒度上场锁的用户
    裁定口径:「买了之后导致合成升星的,那也可以上场」——漏置则被锁
    uid 随 replace 随行进产物,下场回 bench 后遭守卫误拦)。"""
    if isinstance(carrier, BenchSlot):
        if carrier.unit is None:
            raise TypeError('merge 载体 BenchSlot 无 Unit(占位件不可合成)')
        return replace(carrier, unit=replace(carrier.unit, star=new_star,
                                             equips=list(new_equips),
                                             uid=None))
    if isinstance(carrier, Unit):
        return replace(carrier, star=new_star, equips=list(new_equips),
                       uid=None)
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


# ============================================================ 链内工作池与写分支


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
        # 禁造 Unit 假身份进合成素材组(带名 + 查映射编译类别,单一源 =
        # cw_investments.BENCH_ITEM_KINDS;占位只被读 .unit/merge 忽略
        # 非 unit,行为面零差,改带名为单一源完备性)
        pool.ovf.append(BenchSlot(kind=BENCH_ITEM_KINDS[card], item=card))
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
    """链内递归帧共享累计器(效果名/合成级数/写步编号/升星事实;gain-chain.md
    §2 evidence 后缀 ``#mergeN`` 编号沿 merge on_step 先例)。

    ``facts`` = 每级合并的产物身份 ``(角色名, 新星级)``(合并升星触发
    发放采集用,进程内瞬态不入容器;顶层 :func:`gain_character` 收尾
    统一交触发检查——链递归中途 gs 写未收束,顶层发火保一致)。"""

    def __init__(self) -> None:
        self.effects: list[str] = []
        self.merges: int = 0
        self.step: int = 0
        self.facts: list[tuple[str, int]] = []


def _gain_character_core(gs: GameState, name: str, star: int, *, rand: bool,
                         sig: ChannelSig, evidence: str, producer: str,
                         enter: bool, ovf_star: int | None,
                         acc: _ChainAcc, uid: int | None = None
                         ) -> GainOutcome:
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
        # uid = 环境发放链注入的实例号(现役两处传:check_env_battle_grants
        # 发放刻 + on_env_gained 赠卡锁分支发放刻;其余调用缺省 None——
        # 商店购入/观察重建单位天然无实例号)。
        slot = BenchSlot(kind='unit',
                         unit=Unit(char_id=name, star=star, uid=uid))
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
            acc.facts.append(product)   # 升星事实(合并升星触发发放采集)
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
       = 登记分支跳过、容器写照常,与 report 函数 session 缺省语义同构);
    3. **触发环境效果**(on_env_gained)。

    ``rng`` = 环境随机支(chars_random_immediate)采样注入,透传
    on_env_gained(缺省回退在该函数体内,与 gain_invest_strategy 的 rng
    形参同构)。

    容器写分支零吞错:写/回调效果分支异常上抛。
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
    # 节点序列场字段写分支(设计 §2.1,**写点唯一**):修饰规则唯一
    # 计算点 = resolve_plane_node_seqs,注册即落全量(改写注册表内
    # 修饰表/表外默认表,无半态);通道 = write_logic(序列由 desc 规则化
    # 确定,可准确计算 → 逻辑写,非采样面),插在 active_env 落账后。
    # live 与 sim 同走本获得链(report_action_pick_invest_env_param 同源),
    # 单点覆盖双端。
    gs.write_logic(gs.node_seq_by_plane,
                   resolve_plane_node_seqs(canon),
                   produced_by=producer, evidence='node_seq:env', sig=sig)
    if session is not None:
        try:
            register_portal_from_env(session, env_name)
        except Exception as e:  # noqa: BLE001  登记分支 best-effort(gain-chain.md §6)
            log.warning(f'[cw-gain] portal 登记分支失败(不阻塞):{env_name} {e}')
            _emit_defect(field_name='active_env', expected='portal 登记成功',
                         actual=f'登记分支异常:{e}',
                         evidence=f'gain_invest_env:{env_name}', sig=sig,
                         kind=DEFECT_PORTAL_REGISTER)
    effects = on_env_gained(gs, session, env_name, rand=rand, sig=sig,
                            rng=rng)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


def gain_character(gs: GameState, name: str, star: int, *, rand: bool,
                   sig: ChannelSig, evidence: str,
                   producer: str, uid: int | None = None) -> GainOutcome:
    """获得角色(gain-chain.md §2 固定时序):落位(备战空槽 → bench_place;席满 →
    溢出落位写 overflow 两字段;溢出位被占 → 零写留存证据,bench 未观察 =
    直构域拒落零写)→
    on_character_gained 回调 → 单级 3 合 1 升星判断(池 = 备战 ∪ 上阵 ∪
    溢出)→ 升星产物递归重进本原语 → 合并升星触发发放收尾(链内采集的
    升星事实交 ``cw_env_grants.check_env_merge_grants``,顶层收尾统一发火
    ——递归中途 gs 写未收束,收尾时 gs 一致;触发分支 best-effort 异常
    log 不阻塞链主分支)。链内所有写共享入口 sig(gain-chain.md §2),
    evidence 加 ``#place``/``#mergeN`` 后缀区分。

    ``uid`` = 落位单位的实例号(可选尾形参,缺省 None;现役注入点两处 =
    环境发放链 check_env_battle_grants 发放刻与 on_env_gained 赠卡锁分支
    发放刻——实例粒度上场锁的赋号注入,实例语义 =
    cw_game_state.env_grant_deploy_locks 字段注释;其余全部
    现役调用点零传 = 单位天然无实例号)。

    溢出善后(腾位/卖牌)不归链——链只如实记账(gain-chain.md §2)。
    """
    acc = _ChainAcc()
    outcome = _gain_character_core(gs, name, star, rand=rand, sig=sig,
                                   evidence=evidence, producer=producer,
                                   enter=True, ovf_star=None, acc=acc,
                                   uid=uid)
    if acc.facts:
        # 合并升星触发发放(事件携带事实无 done;发放物不在触发集 =
        # 链天然终止无环)。kernel 反向模块级零 import 契约:函数内
        # 惰性取(cw_env_grants 模块级依赖本模块,反向即环)。
        try:
            from sr_od.application.currency_war.kernel.cw_env_grants import (
                check_env_merge_grants,
            )
            check_env_merge_grants(gs, tuple(acc.facts), sig=sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning(f'[cw-gain] 合并升星触发发放分支失败(不阻塞):'
                        f'{acc.facts} {e}')
        # 星星相印合成金腿同区发火(挂点选型 = T-26 顶层收尾段与
        # check_env_merge_grants 同区:链递归中途 gs 写未收束,顶层发火保
        # 一致,与买牌上报发火段同一时序纪律;随 _write_merge_step 尾逐级
        # 发火行为等价,单点收尾免逐级短路维护)。函数内自门 sim 装配
        # (live 零写),异常不阻塞链主分支。
        try:
            check_strategy_star_merge_gold(gs, tuple(acc.facts), sig=sig,
                                           producer=producer)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning(f'[cw-gain] 合成金腿发放分支失败(不阻塞):'
                        f'{acc.facts} {e}')
    return outcome


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
    落位(备战槽或溢出位)。``rand=False`` = 确定发放(策略箱分支/环境发放
    同约定,gain-chain.md §5);``producer`` 缺省 = 链缺省署名。

    公开动机(kernel 策略发放面补「占席道具」形态,迭代
    2026-09-24-advanced-armory-box design §2.2):本原语公开前效果体
    (cw_gain_effects)无占席道具发放口可消费——骇客卡 bench 分支走
    gain_character,道具分支无对应入口。
    """
    return _place_bench_item(gs, item, rand=rand, evidence=evidence,
                             sig=sig, producer=producer)


def queue_delayed_invest_offer(gs: GameState, name: str, *,
                               sig: ChannelSig,
                               producer: str = GAIN_CHAIN_PRODUCER) -> str:
    """策略延时 offer 入队原语(策略卡「N个节点后一次定品质三选一」
    通道唯一登记写端):查 ``STRATEGY_DELAYED_OFFERS`` 登记行,追加
    ``(卡名, delay_nodes)`` 到 ``gs.pending_strategy_offers`` 一次
    write 回写,返回效果串 ``strategy_offer_scheduled:<品质>@<节拍>``。

    - rand 语义:登记 = 确定事件(倒计时按登记值推算,零采样),写通道
      仍经 :func:`_select_write` 单一收束(未锚定期自动随机态,箱腿
      同约定,gain-chain.md §5);
    - 消费语义不在本原语(不对称申报):到点呈现归 sim 专用腿
      (cw_sim_backend,kernel 不 import sim);live 队列恒悬置 =
      模型推算知识(快照存续,实机 offer 由游戏自己呈现,屏幕驱动
      天然覆盖,零停机风险);
    - 递归形态:到点呈现选中的卡若自身带登记行,经获得链
      on_strategy_gained 重进本原语再入队(注册表驱动,机制测试锁;
      现役注册面仅黄金期货,链式行为 = 族批注册落地后的交付态);
    - 未登记卡调用 = KeyError 响亮(登记腿由注册表派生,生产不可达;
      直调误用禁静默)。

    公开动机:队列写入不在效果体 handler 内直写——handler 只做注册表
    查行 + 本原语调用(与 _make_box_grant_effect → gain_bench_item
    薄壳分工同款),写通道单一收束在链模块。"""
    offer = STRATEGY_DELAYED_OFFERS[name]
    queued = tuple(gs.pending_strategy_offers.value or ()) \
        + ((name, int(offer.delay_nodes)),)
    write = _select_write(gs, rand=False)
    write(gs.pending_strategy_offers, queued, produced_by=producer,
          evidence=f'queue_delayed_invest_offer:{name}', sig=sig)
    return (f'strategy_offer_scheduled:{offer.offer_quality}'
            f'@{offer.delay_nodes}')


def queue_delayed_strategy_grant(gs: GameState, name: str, *,
                                 sig: ChannelSig,
                                 producer: str = GAIN_CHAIN_PRODUCER) -> str:
    """策略延时发放入队原语(策略卡「N个节点后获得发放物」通道唯一
    登记写端;与 queue_delayed_invest_offer 并列独立域——offer 族到点
    产出 = 选卡屏事件,本族到点产出 = 世界发放写,消费原语不同不合并):
    查 ``STRATEGY_DELAYED_GRANTS`` 登记行,追加 ``(卡名, delay_nodes)``
    到 ``gs.pending_strategy_grants`` 一次 write 回写,返回效果串
    ``strategy_grant_scheduled:<发放物>@<节拍>``。

    - rand 语义:登记 = 确定事件(倒计时按登记值推算,零采样),写通道
      仍经 :func:`_select_write` 单一收束(箱腿同约定,gain-chain.md §5);
    - 消费语义不在本原语(不对称申报):到点发放归 sim 专用腿
      (:func:`discharge_due_strategy_grants`,调用仅存在于 sim 模块);
      live 队列随 tick 递减至 0 悬置 = 模型推算知识(实机发放由游戏自己
      执行,装备入栏 = equips 观察首见,观察覆盖,零停机风险);
    - 未登记卡调用 = KeyError 响亮(登记腿由注册表派生,生产不可达;
      直调误用禁静默)。

    公开动机:队列写入不在效果体 handler 内直写——handler 只做注册表
    查行 + 本原语调用(queue_delayed_invest_offer 同款薄壳分工,写通道
    单一收束在链模块)。"""
    grant = STRATEGY_DELAYED_GRANTS[name]
    queued = tuple(gs.pending_strategy_grants.value or ()) \
        + ((name, int(grant.delay_nodes)),)
    write = _select_write(gs, rand=False)
    write(gs.pending_strategy_grants, queued, produced_by=producer,
          evidence=f'strategy_grant_queue:{name}', sig=sig)
    return f'strategy_grant_scheduled:{grant.item}@{grant.delay_nodes}'


#: 策略卡条件发放写端署名(家族单一标识,cw_env_grants._PRODUCER 同款
#: 家族先例;写端 = 本模块 check_strategy_conditional_grants,tick 位
#: 发放刻,新写端新名不沿用链缺省伪装连续)。
_CONDITIONAL_PRODUCER: str = 'strategy_conditional_grant'


def check_strategy_conditional_grants(gs: GameState) -> None:
    """策略卡条件发放检查(节点边界 tick 内联腿,advanced 位闸;唯一调用
    点 = cw_game_state._tick_strategy_conditional_grants,经函数级惰性
    import 反向取本函数——本模块模块级依赖 cw_game_state,反向模块级
    即环)。

    遍历持卡(active_strategies 容器直读)∩ STRATEGY_CONDITIONAL_GRANTS,
    跳过已闩(strategy_conditional_done);条件 = 角色池(备战 ∪ 上阵 ∪
    溢出,gain_character 升星判断同池口径)内最大同名单位数 ≥ 阈值
    (「8个一样的角色」卡面直读,升星产物计 1)→ gain_equipment 具名
    发放(rand=False:达标即确定事件,无采样面)→ 发放成功(placed)
    才落闩。拒落域(equips 未观察)不闩——池现值维持达标时后续 tick
    重试自愈;bench 未观察(直构域)= 池不可评估整腿跳过,同拒落自愈
    面。卖出/合成使同名计数回落不回滚已发放(闩 = 「首次」语义);同
    tick 多张持卡条件卡各自独立判定发放。"""
    view = gs.bench.value
    if view is None:
        return
    counts: dict[str, int] = {}
    for slot in view.slots:
        if slot is not None and slot.kind == 'unit' \
                and slot.unit is not None:
            counts[slot.unit.char_id] = counts.get(slot.unit.char_id, 0) + 1
    for u in deployed_indexed_of_view(gs.deployed.value):
        if u is not None:
            counts[u.char_id] = counts.get(u.char_id, 0) + 1
    ovf = str(gs.overflow_card.value or '')
    if ovf and ovf not in BENCH_ITEM_NAMES:
        counts[ovf] = counts.get(ovf, 0) + 1
    done = tuple(gs.strategy_conditional_done.value or ())
    for name in gs.active_strategies.value or ():
        spec = STRATEGY_CONDITIONAL_GRANTS.get(name)
        if spec is None or name in done:
            continue
        if max(counts.values(), default=0) < spec.threshold_same_name:
            continue
        sig = _bridge_sig(gs)
        evidence = f'strategy_conditional_grant:{name}'
        out = gain_equipment(gs, spec.item, rand=False, sig=sig,
                             evidence=evidence,
                             producer=_CONDITIONAL_PRODUCER)
        if out.placed:
            # 登记事实直写(env_grants_done 同款:write_logic 直写非
            # 随机态面;发放与封账同 evidence 同 sig 同组)
            gs.write_logic(gs.strategy_conditional_done, done + (name,),
                           produced_by=_CONDITIONAL_PRODUCER,
                           evidence=evidence, sig=sig)
            done = done + (name,)


#: 策略卡战后触发发放写端署名(家族单一标识,先例 =
#: _CONDITIONAL_PRODUCER 同款;写端 = 本模块 check_strategy_battle_grants,
#: sim 结算位发放刻,新写端新名不沿用链缺省伪装连续)。
_BATTLE_GRANT_PRODUCER: str = 'strategy_battle_grant'


def check_strategy_battle_grants(gs: GameState, node_kind: str,
                                 sig: ChannelSig) -> tuple[tuple[str, str], ...]:
    """策略卡战后触发发放检查(「遭遇节点战斗结算后获得占席道具」触发器
    单一源,策略卡战后触发发放首例;唯一调用点 = sim 结算腿——live 零写
    观察覆盖:箱落备战席有画面真值,实机局不接本通道)。

    条件矩阵(顺序即短路序,沿 check_env_streak_grants 形态;逐序返回
    空 = 未发放):

    1. ``node_kind != 'encounter'`` →()(节点类型条件;kind = 调用方
       传结算点现值,修饰局场字段改写天然跟随零特判);
    2. 逐持卡(active_strategies 容器直读)查 STRATEGY_ENCOUNTER_
       BATTLE_GRANTS,表外卡零条目跳过(集合语义:多卡同持各自独立
       判定发放);
    3. 逐道具 ``gain_bench_item`` 确定发放(rand=False:登记/环境类
       确定发放,gain-chain.md §5;evidence
       ``strategy_post_battle#<卡名>``)。

    - **无 done 闩**:卡文无「首次」限定 = 每次遭遇节点战斗后都发
      (可重复);防重 = 调用方节点键幂等守卫,不设第二守卫;
    - **零 rng**:确定发放,落位位置由容器状态决定非采样;
    - bench 未观察(None)→ 原语内拒落零写(placed=False 不计发放)
      ——宁缺勿造,与 env 触发器同契约(开局种子底座下生产不可达,
      直构/测试形态防御);席满溢出落位/溢出位被占零写留证 =
      原语内建既定语义,本函数零二次判读;
    - 返回实际发放的 (卡名, 道具名) 序列(登记表值逐对一致性的
      断言面;生产调用零回调面,返回值忽略)。
    """
    if node_kind != 'encounter':
        return ()
    granted: list[tuple[str, str]] = []
    for name in gs.active_strategies.value or ():
        items = STRATEGY_ENCOUNTER_BATTLE_GRANTS.get(name)
        if not items:
            continue
        for item in items:
            if gain_bench_item(gs, item, rand=False, sig=sig,
                               evidence=f'strategy_post_battle#{name}',
                               producer=_BATTLE_GRANT_PRODUCER):
                granted.append((name, item))
    return tuple(granted)


#: 胜利结算条件金计数单位(卡面直读:「每有一个佩佩」——佩佩 = 本表
#: 语义的计数目标;与 STRATEGY_GRANTS 招财狗行 chars_immediate 及
#: cw_gain_effects 具名角色发放名单同名单一源对拍归测试锁。表扩计数
#: 目标异构卡时随批改表值形态,本常量随迁)。
_WIN_GOLD_COUNT_UNIT: str = '佩佩'


def check_strategy_win_gold_grants(gs: GameState, *, won: bool,
                                   hp_delta: int) -> int:
    """策略卡胜利结算条件金检查(「战斗胜利后，若未损失小队生命值，
    则每有一个佩佩就会为你提供1金币」触发器单一源,招财狗 id 103501
    首例;唯一调用点 = sim 结算腿——live 零写观察覆盖:金由游戏侧
    自发入账,下一结算屏金真值覆盖自动吸收,实机局不接本通道)。

    条件矩阵(顺序即短路序,check_strategy_battle_grants 形态):

    1. 持卡 ∩ STRATEGY_WIN_GOLD_GRANTS 为空(未持卡/表外卡同路,
       表外卡禁从效果原文自动猜装)→ 0;
    2. ``not won`` → 0(胜利判据);
    3. ``hp_delta != 0`` → 0(未损血判据;两条件并列必要:扑满败局
       形态 won=False ∧ hp_delta=0 存在(sim 扑满不掉血豁免只改
       hp_delta 保留掷点 won),单条件 hp_delta==0 会误发——双写保
       desc 原文两半句,未来输出面演进不缺语义);
    4. 数佩佩:合并池(备战槽 ∪ 上阵两排槽 ∪ 溢出位,与升星判断
       同池口径——佩佩恒后台,仍可因席满落溢出/未上阵在备战,都是
       玩家「有」的佩佩)内身份 == :data:`_WIN_GOLD_COUNT_UNIT` 的
       单位数 n(单位数不折星,2星佩佩 = 1个佩佩,「每有一个佩佩」
       量词「个」直修饰单位;bench/deployed 未观察 None → 该域计 0
       宁缺勿造,env 触发器同契约;溢出位按身份串计,溢出「有件未
       识别」形态〔overflow_warning ∧ 身份空串〕自然计 0,sim 生产
       不可达——溢出身份由获得链直写恒有串)→ 返回 n × 表值。

    - **零 rng**:条件全真值,无采样面;
    - **无 done 闩**(周期型):每战斗结算重查,防重归调用方节点键
      幂等守卫,本函数零二次守卫;
    - **纯读零写**(契约同 check_strategy_level_grants:决策与写面
      分离)——返回金数,写面(observe 金独立笔)归调用方,故无
      sig 入参,与 check_env_streak_grants 自带写面形态差异显式申报;
    - 触发域(desc 无载面:卡面「战斗胜利」未限定节点类型)= 全部
      结算节点,由调用方挂点承载(结算腿不设节点类型守卫);假设经
      STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION 披露键随局申报。
    """
    held = [n for n in (gs.active_strategies.value or ())
            if n in STRATEGY_WIN_GOLD_GRANTS]
    if not held or not won or hp_delta != 0:
        return 0
    n = 0
    bench = gs.bench.value
    if bench is not None:
        for slot in bench.slots:
            if slot is not None and slot.kind == 'unit' \
                    and slot.unit is not None \
                    and str(slot.unit.char_id) == _WIN_GOLD_COUNT_UNIT:
                n += 1
    for u in deployed_indexed_of_view(gs.deployed.value):
        if u is not None and str(u.char_id) == _WIN_GOLD_COUNT_UNIT:
            n += 1
    if str(gs.overflow_card.value or '') == _WIN_GOLD_COUNT_UNIT:
        n += 1
    return n * sum(STRATEGY_WIN_GOLD_GRANTS[name] for name in held)


def check_strategy_star_merge_gold(
        gs: GameState, star_merge_events: tuple[tuple[str, int], ...], *,
        sig: ChannelSig, producer: str) -> None:
    """合成 3 星事件条件金发放腿(「每次合成3星角色时，获得5金币」触发器
    单一源,星星相印 id 104001;调用点 = 角色 3 星合成两生产域单点双调——
    买牌上报合并发火段 + 获得链顶层收尾,事件形状 = ``(角色名, 合成后
    星级)`` 元组序列,与 :func:`check_env_merge_grants` 入参同形)。发放
    由 STRATEGY_EFFECTS ON_MERGE ∧ ECONOMY 条目驱动:同触发装备域经济卡
    (武力刷新)经穿戴上报名单集另路,本腿 payload 字段
    ``gold_per_3star_merge`` 判别双向鸭子缺省 0,两域零串扰(fields.md
    §5.3 生产点分离禁混账)。

    条件矩阵(顺序即短路序,逐序返回 = 零动作):

    1. ``star_merge_events`` 空 → 零动作;
    2. ``to_star == 3`` 事件计数 0(升星非 3 星档,如级联中间级 1→2)
       → 零动作——发放量 = 3 星事件数 × ``gold_per_3star_merge``,
       「每次合成3星」按合成结果事件计,级联一次调用只计一个 3 星事件;
    3. 账本双过滤(ON_MERGE ∧ ECONOMY)后无 ``gold_per_3star_merge>0``
       命中(未持卡 = 条目缺位,持表外卡同路;表外卡禁从效果原文自动
       猜装)→ 零动作——未来同触发异载体卡鸭子缺省 0 天然零发放;
    4. sim 后端未装配(live 形态)→ 零写(金面禁猜测直写:实机 +5 由
       游戏自发,合成无独立画面,下一商店/备战帧金观察覆盖兜底);
    5. gold 现值 None → 宁缺勿造跳过(事件携带事实无 done 闩,下个合成
       事件自动重查,重试零成本)。

    - 金写 = ``gs.observe`` 独立 evidence 笔,evidence 带 ``sim:engine:``
      命名空间(sim 侧策略金腿家族统一形态:T-108 到级/尾款金、T-130
      胜利金同款)——本腿挂点金位可为 logic 来源(买牌上报内金位刚经
      proj_buy_gold 同事务 logic 写),覆盖必须落失配抑制分支 = 记账路径,
      禁入真失配告警;与刷新出对金腿(挂点金位恒观察锚定,裸 tag)的
      形态差异由挂点金位来源状态决定,两腿各自自洽;
    - sig = 函数内自构 obs 族(observe 渠道校验只收 obs 族;入参 sig 为
      logic 族仅溯源申报不消费,T-121 同款纪律);``producer`` 入
      group_id 供判读分域(buy/gain 来源可过滤);
    - 零 rng:事件计数确定,无采样面;多卡同持各自独立判定
      (ledger 遍历语义,出对金腿同形)。
    """
    if not star_merge_events:
        return
    count = sum(1 for _name, new_star in star_merge_events
                if int(new_star) == 3)
    if count <= 0:
        return
    total = 0
    for e in gs.effects.entries:
        if e.spec.trigger is not TriggerKind.ON_MERGE \
                or e.spec.category is not EffectKind.ECONOMY:
            continue
        n = int(getattr(e.spec.payload, 'gold_per_3star_merge', 0) or 0)
        if n > 0:
            total += n * count
    if total <= 0:
        return
    # kernel → sim 判据消费沿 cw_sim_ports 惰性 import 先例(函数内取,
    # 模块级反向即环);live 未装配早退 = 零写纪律执行点。
    from sr_od.application.currency_war.sim.cw_sim_ports import (
        sim_backend_installed,
    )
    if not sim_backend_installed():
        return
    g = gs.gold.value
    if g is None:
        return
    from sr_od.application.currency_war.sim.cw_sim_base import sim_evidence
    gs.observe(gs.gold, int(g) + total,
               evidence=sim_evidence(f'strategy_star_merge_gold:{count}'),
               sig=ChannelSig(family='obs',
                              actor='StrategyStarMergeGoldGrant',
                              mode='synthesized',
                              group_id=f'strategy:star-merge-gold:{producer}'))


#: 策略卡到级发放写端署名(家族单一标识,_CONDITIONAL_PRODUCER/
#: _BATTLE_GRANT_PRODUCER 同款家族纪律;公开常量 = 写端在 sim 接线段
#: ——决策函数纯判定零写,金/闩两笔写归调用方,sim 需跨模块引用署名,
#: GAIN_CHAIN_PRODUCER 同公开例;新写端新名不沿用链缺省伪装连续)。
LEVEL_GRANT_PRODUCER: str = 'strategy_level_grant'


def check_strategy_level_grants(gs: GameState) -> tuple[str, int] | None:
    """策略卡到级条件发放决策(成长基金 id 101701 首例;状态检查型语义
    ——持卡 ∧ 等级达标 ∧ 未闩即发,「拿卡时已 ≥ 目标级」同发:等级是
    容器现值非事件流,拿卡时点无从回溯历史跨越,T-102 条件腿「容器现值
    求值」同款先例;语义假设经 sim 披露键申报,实机对拿卡已达标是否补发
    未采证)。

    契约:纯读零写零 rng,返回待发放 ``(规范卡名, 金额)`` 或 None;两笔
    写(金 + done 闩)归调用方按所在端通道纪律执行(sim = 金 observe 独立
    笔 + 闩 write_logic,advance 双点接线;live 零接线 = 金面禁直写,
    观察覆盖兜底)。registry 驱动 = ``STRATEGY_ECONOMY`` 现值遍历,新到级
    卡登记行即自动覆盖,零改本函数(局终同拍多卡双就绪边角:单笔返回
    契约会漏第二笔,现世界不可达,多卡批落地时改列表返回并申报)。

    短路矩阵(序即短路序,check_env_refresh_grants 七序形态):
    1. active_strategies ∩ STRATEGY_ECONOMY 中 ``gold_at_level_target>0``
       的条目,交集空 → None(未持卡/持表外到级卡同路;表外卡禁从效果
       原文自动猜装);
    2. 卡名 ∈ strategy_conditional_done → None(一次性封账,「首次」
       语义——等级单调不减下达标态持续为真,靠闩封账非靠跨越检测);
    3. gs.level.value None → None(等级从未观察,宁缺勿造);
    4. gs.gold.value None → None(金未观察,宁缺勿造**不封账**——本
       函数零写,值到位后下次检查自动重查发放);
    5. 现值等级 < gold_at_level_target → None(现役 sim 经验常量下
       全程封顶 7 级:节点 70 + 选卡即时腿 26 = 上界 96 < 3→9 级累计
       门槛 194,XP_TO_NEXT_LEVEL 求和——本腿恒短路于此序 = 休眠正确
       路径,sim 披露键申报;经验源扩网后零改激活,锁面固化边界);
    6. 达标 → (卡名, gold_at_level)。
    """
    done = tuple(gs.strategy_conditional_done.value or ())
    for name in gs.active_strategies.value or ():
        eff = STRATEGY_ECONOMY.get(name)
        if eff is None or eff.gold_at_level_target <= 0:
            continue
        if name in done:
            continue
        level = gs.level.value
        gold = gs.gold.value
        if level is None or gold is None:
            continue
        if int(level) < eff.gold_at_level_target:
            continue
        return (name, int(eff.gold_at_level))
    return None


def _node_frame(gs: GameState) -> str:
    """链内 frame 字符串(「位面-轮」统一标识,如 ``2-3``;节点未观察 =
    空——登记分支 evidence 用;编号时代的 p{plane}-r{round} 双形态随键
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
       策略时,按名字去重就行了」;跳写后登记/效果分支照常);
    2. **效果账本登记**(best-effort:`session=None` = 跳过[局外/测试
       形态],容器写照常):``STRATEGY_EFFECTS`` 归一名命中 →
       ``effects.register_strategy`` + burst 桥 ``apply_effect_burst_grant``
       + 板面重写桥 ``apply_board_rewrite``
       (acquired_key = 节点序位快照);失败 log + 缺陷留存证据(``DEFECT_STRATEGY_
       REGISTER``)、不阻塞;
    2.5 **环境取卡触发发放**(T-46 策略大师金币分支;②后③前,所有取卡
       来源的共同必经点,live 上报与 sim 选卡/直发双端覆盖):单一源 =
       ``cw_env_grants.check_env_pick_grants``,注册后现读长度即含本张
       已持有数,异常零吞上抛(容器写分支纪律);
    3. **触发策略效果**:`on_strategy_gained`(查 ``PICK_INVEST_EFFECTS``
       分派;未收录卡安静不写)。

    rand 纪律:投资策略确认 = 确定性入口(False);效果体含采样(骇客
    改件)→ 对其子链翻转 rand=True(§5)。``rng`` = 采样注入点(缺省
    ``random.Random()`` 生成点在 :func:`on_strategy_gained` 内;sim 可
    播种)。容器写分支零吞错;登记分支 best-effort。
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
    # ① 注册(按名字去重追加;跳写后登记/效果分支照常)
    cur = list(gs.active_strategies.value or [])
    write = _select_write(gs, rand)
    if canon not in cur:
        write(gs.active_strategies, cur + [canon], produced_by=producer,
              evidence=f'gain_invest_strategy:{canon}', sig=sig)
    # ② 效果账本登记(best-effort 分支)
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
        except Exception as e:  # noqa: BLE001  登记分支 best-effort(gain-chain.md §6)
            log.warning('[cw-gain] 策略登记分支失败(不阻塞):%s %s', canon, e)
            _emit_defect(field_name='active_strategies',
                         expected='效果账本登记成功',
                         actual=f'登记分支异常:{e}',
                         evidence=f'gain_invest_strategy:{canon}', sig=sig,
                         kind=DEFECT_STRATEGY_REGISTER)
    # 环境取卡触发发放(T-46 策略大师金币分支):位置 = ②后③前——②为
    # best-effort 分支不拦本分支;本分支在③(on_strategy_gained 直调零防护)
    # 之前,③异常发生在金入账之后不回吞。held_after = 注册后现读长度
    #(含本张口径,用户裁定 2026-10-26:同名跳写形态下「这张」本就在
    # 列表,现长度即含本张,零特判)。kernel 反向模块级零 import 契约:
    # 函数内惰性取(cw_env_grants 模块级依赖本模块,反向即环);容器写分支
    # 零吞错,异常上抛可见。
    from sr_od.application.currency_war.kernel.cw_env_grants import (
        check_env_pick_grants,
    )
    check_env_pick_grants(gs, len(gs.active_strategies.value or []), sig)
    # ③ 触发策略效果
    effects = on_strategy_gained(gs, canon, rand=rand, sig=sig, rng=rng)
    return GainOutcome(placed=True, landing='skipped', merge_levels=0,
                       effects=effects, detail='')


# ============================================================ 枚举回调(gain-chain.md §3;现役四枚举)
# (无注册表——用户裁定:回调函数体内枚举即收敛,不设注册机构。)


def _place_bench_item(gs: GameState, item: str, *, rand: bool,
                      evidence: str, sig: ChannelSig,
                      producer: str = GAIN_CHAIN_PRODUCER) -> bool:
    """占席道具(带名)落位(角色落位同构:_build_pool/bench_place/
    _select_write 序;槽件 = ``BenchSlot(kind=BENCH_ITEM_KINDS[item],
    item=item)``——带名 + 查映射编译类别,映射单一源 =
    cw_investments.BENCH_ITEM_KINDS,映射外道具名直查 KeyError 响亮
    (键缺 = 代码 bug,禁静默兜底),双端同一获得链——sim 世界写入即容器
    写)。席满 → 溢出落位(实机真值 2026-09-24
    用户确认:道具与角色同款——落溢出席并阻断进入战斗;两字段直写,身份 =
    道具名,消费方按 BENCH_ITEM_NAMES 判 kind);溢出位已被占 → 零写 +
    留存证据禁猜(与角色入账分支同款,gain-chain.md §6)。返回是否落位(备战槽或
    溢出位)。``producer`` = 写端署名(缺省 = 链缺省,环境通道现役调用点
    不传即行为不变;策略效果体经公开口 :func:`gain_bench_item` 透传)。"""
    if gs.bench.value is None:
        return False
    pool = _build_pool(gs, None)
    assert pool is not None   # bench 已判非 None,构建恒有池
    write = _select_write(gs, rand)
    slot = BenchSlot(kind=BENCH_ITEM_KINDS[item], item=item)
    if bench_place(pool.bench, slot) is not None:
        write(gs.bench, bench_view_of_working(pool.bench, pool.orig_view),
              produced_by=producer, evidence=f'{evidence}#place',
              sig=sig)
        return True
    if _overflow_occupied(gs):
        # 溢出位已被占(席满 + 溢出位再溢出):游戏行为未实证 → 零写 +
        # 留存证据,禁猜(角色入账分支同款,gain-chain.md §6)
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


def _unlock_experts(gs: GameState, chars: tuple[str, ...], *, rand: bool,
                    evidence: str, sig: ChannelSig) -> None:
    """专家顾问解锁入池写原语(权威状态 = ``gs.unlocked_experts``,只增去重)。

    - 官方机制(economy.md §1):专家顾问初始不参与普通商店招募,获得
      对应投资环境/投资策略(advisor 道登记表 ENV_GIFTS/STRATEGY_GRANTS
      advisor=True)或装备(分身墨镜族)后「使其在本局游戏中加入商店」
      ——本原语 = 该事实的唯一容器落点;池派生
      (:func:`cw_pool.unlocked_expert_copies`)按名并入
      ``EXPERT_COPIES_ASSUMED`` 副本,商店发牌即可刷出;
    - 成员闭集闸(:func:`assert_expert_names`)写入期即校验,越界名炸错
      优于静默混池;
    - 解锁 = 确定事实非采样 → rand 透传(gain-chain.md §5;写通道经
      :func:`_select_write` 单一收束);重复解锁幂等(只增去重)。
    """
    if not chars:
        return
    assert_expert_names(chars)
    current = tuple(gs.unlocked_experts.value or ())
    merged = current + tuple(c for c in chars if c not in current)
    if merged == current:
        return
    write = _select_write(gs, rand)
    write(gs.unlocked_experts, merged, produced_by=GAIN_CHAIN_PRODUCER,
          evidence=evidence, sig=sig)


def _cond_expert_presence_names(gs: GameState) -> set[str] | None:
    """条件形态在场判定读口(挂点④专用;唯一消费点 = :func:`on_env_gained`
    advisor 分道条件形态支):环境获得时刻在场单位名集合 = 备战席 ∪ 上阵
    ∪ 溢出位(三次容器读全廉价,与合成池 ``_build_pool`` 同三域口径;
    槽件解包走 ``bench_slot_unit`` 读口单一源,禁内联 kind 判断)。溢出位
    身份串可能是占席道具名(非角色),入集无害——判据按规范名直等,
    道具名不可能命中触发名。bench 未观察(None)→ None 供调用方
    fail-closed:开局种子恒种 bench,种子底座下生产双端不可达,本分支
    实为直构/测试形态防御(缺陷 kind = DEFECT_COND_BENCH_UNOBSERVED,
    同族先例 = cw_env_grants.check_env_boss_grants 席面未观察分支)。"""
    view = gs.bench.value
    if view is None:
        return None
    names: set[str] = set()
    for slot in view.slots:
        u = bench_slot_unit(slot)
        if u is not None:
            names.add(str(u.char_id))
    for dep in deployed_indexed_of_view(gs.deployed.value):
        if dep is not None:
            names.add(str(dep.char_id))
    card = str(gs.overflow_card.value or '')
    if card:
        names.add(card)
    return names


def on_env_gained(gs: GameState, session: object, env_name: str, *,
                  rand: bool, sig: ChannelSig,
                  rng: random.Random | None = None) -> tuple[str, ...]:
    """「获得投资环境」触发型效果枚举(gain-chain.md §3)。

    - ``ENV_GIFTS`` 命中 → **先按 advisor 分道,两道互斥**:advisor=False
      (契约,直接送卡)→ chars_immediate 逐个 ``gain_character(char, 1★)``
      (1★ 先验同句式先例:骇客效果体同族,现役 =
      ``cw_gain_effects.py::PICK_INVEST_EFFECTS``;先验错 = 响停修因非
      随机);advisor=True(特邀专家/顾问入商店族)→ **不入席**,经
      :func:`_unlock_experts` 写解锁状态(官方效果文「使其在本局游戏中
      加入商店」= 入池可刷,非直接送单位;容器权威字段 =
      ``gs.unlocked_experts``,池派生消费 = cw_pool);chars_immediate 在
      advisor 行仅作解锁名单输入,禁再入席;
    - **开局替换清席支**(``replaces_opening_supply``,advisor 分道之后、
      具名支之前;首例 = 人才储备 id 144「开局补给替换为3个随机3费角色」):
      移除 bench 上全部角色槽(kind='unit';占席道具类槽不在替换面——开局窗
      结构性不存在,防御性保留)后按后续支发放。写通道 = :func:`_select_write`
      单一收束(清席 = 确定发放语义,rand 原样透传);live 选卡窗未锚定落
      随机态,由首备战帧 bench 整表观察覆盖收口;sim 恒未锚定,落账即世界
      真值(纠回 M01 预写的开局 4 张,选卡前无消费者)。零角色槽(live 空
      底座)零写,只留效果串 ``env_opening_replace:<removed>``;
    - **环境即时金收入分支**(世界规则,注册表结构化通道):环境经济
      ``economy.gold_instant`` 非零 → gold 直加(两执行面同源;旧 sim
      引擎私有分支随驱动反转停用,规则落本链为单一源);
    - **追加随机环境申报行**(``ENV_REROLL_NAMES`` 命中,金收入分支之后):选卡
      后游戏随即再随机获得一个环境,该掷骰 live 端不可观察(active_env
      无观察覆盖通道)→ 申报留证一行(``kind = ENV_REROLL_DECL``,语义
      申报非缺陷告警),行为 fail-closed(容器写序列与普通环境逐位一致);
      世界掷骰 = sim 后端追加获得分支二次入链
      (``cw_sim_backend._on_invest_picked``,原语复用),双端各产一行
      如实记录「选择时点真值未知」;
    - **随机赠卡锁分支**(``ENV_DEPLOY_LOCK_GRANTS`` 命中,申报行之后、
      ENV_GIFTS 查表之前;世界发放域登记表白名单,首例 = 英雄登场):
      获得当刻随机赠卡——牌库时点池(cw_pool ``grant_char_pool`` = 规格
      域 ∩ 当时牌库,未解锁专家剔除)内均匀掷骰选名 →
      ``gain_character`` 落席(星级 = spec.star;效果体含采样 → 子链
      rand=True,``rng`` 缺省回退自掷,随机支同款三层已通)→ 实例发号
      (``env_grant_uid_seq`` 计数器,T-30 同款,uid 随落位单位 =
      锁匹配键)→ 锁记录 ``(名, uid, 解锁序位)`` 追加
      ``env_grant_deploy_locks``(解锁序位 = 获得刻生效序位沿节点日程表
      步进 deploy_lock_nodes 步,计数起点 = 获得节点计入锁定段;未锚定
      窗防御基准 (1,1);步进遇 None 停留最后合法值)→
      ``perfect_win_accel`` 开时追加完胜作用域键 ``deploy_lock_uid#<uid>``
      落 ``env_grants_done``(作用域隔离:完胜改写只碰本卡 uid 集,
      消费 = cw_env_grants.check_env_deploy_lock_perfect)。效果串两行
      ``env_gift_random:<名>@<星>star``(与随机支同前缀同形,审计归组)+
      ``env_deploy_lock:<名>#uid<n>@<位>-<轮>``(锁登记串)。落位成败与
      锁记录/done 解耦(placed=False 零写留证,锁记录照写)。锁随 uid
      不随名(掷骰名是猜测,bench 首观察覆盖纠偏,守卫拒/放对象不受扰);
      拦截复用 deploy_move/swap_deploy 既有守卫零新建(设计 = T-33
      设计稿 §2.3,迭代 2026-09-23-invest-effects-calc);
    - **随机支**(``chars_random_immediate``,具名支之后):牌库时点池
      (cw_pool ``grant_char_pool`` = 规格域 ∩ 当时牌库,未解锁专家剔除,
      用户裁定 2026-10-28)内均匀掷骰选名 → ``gain_character`` 落席,星级
      = spec.star;效果体含采样 → 子链 rand=True(gain-chain.md §5)——
      未锚定期(开局窗)本就走 write_logic_rand,rand=True 声明采样语义
      并保锚定后不进失配网(实机猜错 = 首观察静默覆盖,
      logic_rand_outcome 收尾,不触发告警停局)。效果串
      ``env_gift_random:<名>@<星>star``(与具名支 ``env_gift:`` 前缀分离,
      采样发放可独立过滤审计);``rng`` 缺省回退自掷(直构/测试形态;
      正式接线由上报函数条件解析传入,sim 装配 = 流键 rng 即世界真值)。
      首例 = 人才引进(id 109,开局 1 个随机 4 费,星级先验 1);
    - **即时装备支**(``equips_immediate``,随机支之后、即时道具支之前):
      具名装备逐名 ``gain_equipment`` 入栏(equips 库存,不占席)——确定
      具名发放,写通道走随机态(rand=True 硬编码,2026-10-17 用户裁定:
      「选卡时点游戏实际发下」对首例环境未经实机判读核实,卡面文本是唯一
      证据——猜测写 + 观察覆盖纠偏,首观察静默覆盖不进失配网;先例 =
      T-5 财富宝钻随机态获得/T-29 全奖励分支随机态);效果串
      ``equip_gift:<名>``,与 ``env_gift:``/``env_star_grant:``/
      ``item_gift:`` 前缀分域。首例 = 红钻贵族(卡文序「钻先箱后」,
      装备支位于道具支之前,遥测序与卡文对齐);
    - **道具通道**(``items_immediate`` + ``items_scheduled``):道具 =
      占席待开箱,非角色非装备。即时支:落位写入(角色落位同构:备战空槽
      放带名槽件 ``BenchSlot(kind=BENCH_ITEM_KINDS[名], item=名)``,类别
      查映射编译——bookcard 槽件发放首例 = 专家研讨会,开卡/选卡链现役
      承接;双端同一获得链,sim 世界写入即容器写);席满 = 溢出落位(实机
      真值:道具与角色同款——落溢出席并阻断进入战斗;溢出位被占 = 零写
      留存证据,helper 内);效果串
      ``item_gift:<名>`` 恒登记(数量 = 元素重复次数),开箱链由外循环
      画面分发承接(武装箱选择画面独立建档)。定时支:逐项入容器队列
      ``pending_item_grants``(一次 write 回写整表,登记不落席),效果串
      ``item_scheduled:<名>@<节点键>``(数量 = 元素重复次数,发放事实
      登记与即时通道同阶),到点发放 = :func:`discharge_due_item_grants`;
    - **随机装备支**(``equips_random_immediate``,落地序 = 即时道具支之后、
      定时支之前):类别池(equips_by_category 注册表派生)内均匀掷骰选名 →
      ``gain_equipment(rand=True)`` 入栏(equips 库存,不占席);效果串
      ``env_star_grant:<名>``,绑定分支 = 发放名落 done 条件键
      ``star_grant#<名>``(placed 守卫下写,分支2 触发依赖,
      check_env_boss_grants 消费);首例 = 劳务派遣合同(分支1);
    - **词缀失效删除分支**(``ENV_AFFIX_DISABLE_ENV`` 命中,延迟道具支线
      之后、ENV_GIFTS 查表之前;硬编码分支沿 DOT_CONTRACT_ENV 枚举即
      收敛先例):选敌后破坏 → 词缀名单(gs.enemy_affixes)非空时均匀
      随机删 1 个、剩余列表整条替换写回(经 :func:`_select_write` 择道,
      rand=True 双保险声明采样链——live 选卡在开局未锚定窗自动落随机态,
      位面详情补观察闭环转正);容器空 → 跳过删除,零写 + 申报行
      (``kind = ENV_AFFIX_DISABLE_EMPTY_DECL``,实机已失效而模型未删,
      偏差全程持续)。采样分支具名流键 ``action_sampling_rng(
      'env_affix_disable', None)`` 分支内自解析(env_merge_grant 双端同槽
      先例);删除写触发词缀域写尾 HP 先验回调(cw_opening_hp.
      on_enemy_affixes_logic_write,_write_logic_frame 挂点)。效果串
      ``env_affix_disable:<词缀名>``。首例 = 敌后破坏(id 146;
      设计 = T-45 设计稿 §2.1,迭代 2026-09-23-invest-effects-calc);
    - 查无效果(表外环境)= 安静不写(用户裁定),真值归观察覆盖。
      (欢愉契约条件分支不在本枚举:其正式模型 = 银狼策划选择上报动作落地时点的
      条件分支 rider,住 ``cw_action_report.pick_planner``,触发事件 =
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
        # sim 端随后由后端追加获得分支二次入链(cw_sim_backend.
        # _on_invest_picked),本行为历史申报行双端各产一行如实记录。
        _emit_defect(field_name='active_env',
                     expected='追加卷中环境名(游戏侧事实)',
                     actual=f'{_name}(选择事实;真值不可观察)',
                     evidence=f'on_env_gained:{_name}', sig=sig,
                     kind=ENV_REROLL_DECL)
    # effects 累积面自赠卡锁分支起(表外环境恒空 = () 逐位不变;前瞻边界:
    # 若未来 advisor 分支改为复用 effects 累积,本上移位需重审——现 advisor
    # 分道自构字面元组返回,与本累积面无交集)。
    effects: list[str] = []
    # 随机赠卡锁分支(世界发放域登记表白名单,ENV_GIFTS 查表之前——表外
    # 环境零写径不受扰):采样发卡 + 实例发号 + 上场锁写 + 完胜作用域
    # done 登记,同窗相邻写(设计 = T-33 设计稿 §2.3,迭代
    # 2026-09-23-invest-effects-calc)。锁随 uid 不随名:守卫匹配键 =
    # uid(cw_env_grants.deploy_lock_block_reason),掷骰名是猜测、bench
    # 首观察静默覆盖纠偏,不影响锁的拒/放对象。kernel 反向模块级零
    # import 契约:函数内惰性取(本函数既有 DOT_ANCHOR_KEY_PREFIX/
    # STAR_GRANT_KEY_PREFIX 同款函数级避环)。
    from sr_od.application.currency_war.kernel.cw_env_grants import (
        DELAYED_OPEN_ACCEL_KEY,
        DEPLOY_LOCK_UID_KEY_PREFIX,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        effective_node_pos,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_DELAYED_ITEM_GRANTS,
        ENV_DEPLOY_LOCK_GRANTS,
    )
    from sr_od.application.currency_war.kernel.cw_node_schedule import (
        sequence_next,
    )
    _lock = ENV_DEPLOY_LOCK_GRANTS.get(_name)
    if _lock is not None:
        roll_rng = rng if rng is not None else random.Random()
        pool = grant_char_pool(gs, _lock.spec)
        if not pool:
            # 构建期已闸(_validate_env_deploy_lock_grants 池非空),运行期
            # 空 = 注册表漂移或全专家域未解锁;零写留 log 防御分支
            # (chars_random 支同款,不改容器不炸链)
            log.warning(
                f'[cw-gain] 随机赠卡池空(注册表漂移?):'
                f'{_name} cost={_lock.spec.cost} '
                f'type_tag={_lock.spec.type_tag!r}')
        else:
            name = roll_rng.choice(pool)   # 档内均匀 v0(T-10 披露同族)
            # 发号复用 env_grant_uid_seq 计数器(T-30 同款,实例身份赋号刻
            # = 发放刻;uid 随 gain_character 落位单位,锁匹配键)
            uid = int(gs.env_grant_uid_seq.value or 0) + 1
            gs.write_logic(gs.env_grant_uid_seq, uid,
                           produced_by=GAIN_CHAIN_PRODUCER,
                           evidence=f'on_env_gained:{_name}#uid', sig=sig)
            gain_character(gs, name, _lock.spec.star, rand=True, sig=sig,
                           evidence=f'on_env_gained:{_name}',
                           producer=GAIN_CHAIN_PRODUCER, uid=uid)
            # 解锁序位 = 获得刻生效序位沿节点日程表步进锁期(计数起点 =
            # 获得节点计入锁定段,设计定读);生效序位未锚定 = 开局段
            # 结构性形态,防御基准 (1,1);步进遇 None(局终方向)停留
            # 最后合法值(check_env_battle_grants 同款)
            base = effective_node_pos(gs) or (1, 1)
            unlock = base
            for _ in range(_lock.deploy_lock_nodes):
                nxt = sequence_next(unlock, gs.node_seq_by_plane.value)
                if nxt is None:
                    break   # 局终方向无后继:停留最后合法值(T-30 同款)
                unlock = nxt
            # 锁记录 = 登记事实非观察投影,write_logic 直写(T-30 域规格);
            # 落位成败与锁记录解耦(placed=False 溢出位被占零写留证,
            # 锁记录照写 = check_env_battle_grants 同口径)
            gs.write_logic(gs.env_grant_deploy_locks,
                           tuple(gs.env_grant_deploy_locks.value or ())
                           + ((name, uid, unlock),),
                           produced_by=GAIN_CHAIN_PRODUCER,
                           evidence=f'env_deploy_lock:{_name}', sig=sig)
            if _lock.perfect_win_accel:
                # 完胜作用域登记走 env_grants_done 现成 (env, key) 通道,
                # 键 = deploy_lock_uid#<uid> 作用域隔离键——完胜改写只碰
                # 本卡 uid 集(check_env_deploy_lock_perfect 消费),T-30
                # 流萤等异环境锁记录不受本卡完胜加速(卡面「将其」= 本卡
                # 赠卡;两环境共存形态结构性可达,active_env 为链)
                done = tuple(gs.env_grants_done.value or ())
                gs.write_logic(gs.env_grants_done,
                               done + ((_name,
                                        f'{DEPLOY_LOCK_UID_KEY_PREFIX}'
                                        f'{uid}'),),
                               produced_by=GAIN_CHAIN_PRODUCER,
                               evidence=(f'env_deploy_lock:{_name}'
                                         f'#accel_scope'), sig=sig)
            effects.append(f'env_gift_random:{name}@{_lock.spec.star}star')
            effects.append(f'env_deploy_lock:{name}'
                           f'#uid{uid}@{unlock[0]}-{unlock[1]}')
    # 延迟道具支线(世界发放域登记表白名单,同在 ENV_GIFTS 查表之前——
    # 表外环境零写径不受扰):倒计时件 = 战利品区浮动件非占席(实机板件
    # 实证,T-34 设计稿 §1)→ 纯队列登记零席位写(不调 _place_bench_item,
    # 不碰 bench/overflow 任何字段);开盒内容不建模(卡面 desc 无载,硬
    # 裁定 = T-34 设计稿披露 1)。解锁位 = 获得刻生效序位沿日程表步进
    # open_delay_nodes 步(计数起点 = 获得节点计入,裁决点 3;生效序位
    # 未锚定 = 开局段结构性形态,防御基准 (1,1);步进遇 None(局终方向)
    # 停留最后合法值,T-33 锁分支同款)。设计 = T-34 设计稿 §2.3,迭代
    # 2026-09-23-invest-effects-calc。
    _delayed = ENV_DELAYED_ITEM_GRANTS.get(_name)
    if _delayed is not None:
        base = effective_node_pos(gs) or (1, 1)
        unlock = base
        for _ in range(_delayed.open_delay_nodes):
            nxt = sequence_next(unlock, gs.node_seq_by_plane.value)
            if nxt is None:
                break   # 局终方向无后继:停留最后合法值(T-33 同款)
            unlock = nxt
        write = _select_write(gs, rand)   # 与链内其余写同收口
        write(gs.pending_item_opens,
              tuple(gs.pending_item_opens.value or ())
              + ((_delayed.item, unlock),),
              produced_by=GAIN_CHAIN_PRODUCER,
              evidence=f'on_env_gained:{_name}#open_queue', sig=sig)
        if _delayed.perfect_win_accel:
            done = tuple(gs.env_grants_done.value or ())
            if (_name, DELAYED_OPEN_ACCEL_KEY) not in done:
                # 幂等:重复获得不重写(队列两条独立条目照登记,加速
                # 作用域 done 键只写一次)
                gs.write_logic(gs.env_grants_done,
                               done + ((_name, DELAYED_OPEN_ACCEL_KEY),),
                               produced_by=GAIN_CHAIN_PRODUCER,
                               evidence=f'on_env_gained:{_name}#accel_scope',
                               sig=sig)
        effects.append(f'item_open_scheduled:{_delayed.item}'
                       f'@{unlock[0]}-{unlock[1]}')
    # 词缀失效删除分支(敌后破坏 id 146「开局时，使一个已生成的敌人词缀
    # 失效。」,世界发放域硬编码分支沿 DOT_CONTRACT_ENV 枚举即收敛先例,
    # 不入登记表——单卡零复用面;设计 = T-45 设计稿 §2.1,迭代
    # 2026-09-23-invest-effects-calc):失效建模 = 删除式——从词缀名单
    # (gs.enemy_affixes)均匀随机删 1 个、剩余列表整条替换写回,经
    # _select_write 择道且 rand=True 双保险声明采样链(live 选卡发生在
    # 开局未锚定窗 → 自动落随机态 = 裁定的「词缀要变成随机态」;掷骰
    # = live 模型猜测/sim 世界真值,偏差由位面详情补观察闭环转正,
    # cw_screen_prep 委派谓词消费 logic_rand_fields)。删除写触发词缀域
    # 写尾 HP 先验回调(cw_opening_hp.on_enemy_affixes_logic_write,
    # _write_logic_frame 挂点);效果串与 ``env_gift_random:`` 家族同形
    # 分前缀,审计归组。
    if _name == ENV_AFFIX_DISABLE_ENV:
        _aff = list(gs.enemy_affixes.value or [])
        if not _aff:
            # 空容器边界(设计 §2.1/披露键 3):选卡时容器空(简报失读等)
            # → 跳过删除,零写 + 申报行留证(实机已失效而模型未删)。
            _emit_defect(field_name='enemy_affixes',
                         expected='词缀名单非空(可执行失效删除)',
                         actual='空容器(实机已失效而模型未删,偏差申报)',
                         evidence=f'on_env_gained:{_name}', sig=sig,
                         kind=ENV_AFFIX_DISABLE_EMPTY_DECL)
        else:
            # 采样分支具名流键:分支内自解析(注入槽优先,缺省回退自掷;
            # 无命中分支不取槽不扰他局流键,check_env_merge_grants 同款)。
            # kernel 反向模块级零 import 契约:action_sampling_rng 住上报
            # 函数族包,函数内惰性取(gain-chain.md §8 单向破环先例)。
            from sr_od.application.currency_war.kernel.cw_action_report import (
                action_sampling_rng,
            )
            roll_rng = action_sampling_rng(ENV_AFFIX_DISABLE_RNG_TOOL, None)
            removed = roll_rng.choice(_aff)   # 简报现值池均匀 v0(披露键 1/4)
            kept = list(_aff)
            kept.remove(removed)   # 名单无重复元素,恰删采样命中的 1 个
            write = _select_write(gs, True)
            write(gs.enemy_affixes, kept, produced_by=GAIN_CHAIN_PRODUCER,
                  evidence=f'on_env_gained:{_name}#affix_disable', sig=sig)
            effects.append(f'env_affix_disable:{removed}')
    grant = ENV_GIFTS.get(_name)
    if grant is None:
        return tuple(effects)
    if grant.advisor:
        unlock_tail = '+'.join(grant.chars_immediate)
        if grant.chars_conditional:
            # 条件形态支(首例 = 特邀专家:银狼,「获得角色触发型」族挂点④;
            # 设计 = 迭代 2026-09-23-invest-effects-calc T-42 §2.4):
            # 「首次获得」涵盖环境获得之前已发生的获得——环境获得时刻对
            # 在场单位(bench ∪ deployed ∪ 溢出位)判一次,开局种子起手与
            # 先购得后经蓝海改写等中途获得本环境局在此收口;环境获得后的
            # 首次获得由三渠道判据承接(expert_conditional_trigger,两挂点
            # 合起来覆盖「首次」全语义)。本挂点不走该判据函数——此处
            # 「获得」= 在场判定本身,非单名获得事件。
            presence = _cond_expert_presence_names(gs)
            if presence is None:
                # bench 未观察 → fail-closed 不判零写 + 缺陷留存证据
                # (种子底座下生产双端不可达——开局种子恒种 bench,直构/
                # 测试形态防御;同族先例 = cw_env_grants.check_env_boss_
                # grants 席面未观察分支)
                _emit_defect(field_name='bench',
                             expected='环境获得时刻席面可读(条件形态在场判定)',
                             actual='bench 未观察(None)',
                             evidence=f'on_env_gained:{_name}', sig=sig,
                             kind=DEFECT_COND_BENCH_UNOBSERVED)
            elif '银狼LV.999' in presence:
                # 触发映射硬编码单一源注:触发角色名 银狼LV.999 只在
                # ENV_GIFTS['特邀专家:银狼'].chars_conditional 条件描述
                # 散文(注释性二元组不进判据),此处与
                # expert_conditional_trigger 条件①同源同映射
                _unlock_experts(gs, ('银狼',), rand=rand,
                                evidence=f'on_env_gained:{_name}#expert_unlock',
                                sig=sig)
                unlock_tail = '银狼'
            # 未命中/未观察 → 维持现值空尾效果串(事实申报,遥测面零改动;
            # 空尾即「条件形态未触发」的自然读法)
        else:
            _unlock_experts(gs, grant.chars_immediate, rand=rand,
                            evidence=f'on_env_gained:{_name}#expert_unlock',
                            sig=sig)
        return (f'advisor_unlock:{_name}:{unlock_tail}',)
    if grant.replaces_opening_supply:
        # 开局替换清席支(先清后发,首例 = 人才储备 id 144;设计 = T-43 设计稿
        # §2.3,迭代 2026-09-23-invest-effects-calc):「开局补给替换」=
        # 开局发放的初始角色被本环境赠卡取代——移除 bench 上全部角色槽
        # (kind='unit';占席道具类槽不在替换面,开局窗该形态结构性不存在,
        # 防御性保留),部署行/溢出席开局窗恒空不触。写通道 = _select_write
        # 单一收束(清席 = 确定发放语义,rand 原样透传,具名支同款):live
        # 选卡窗未锚定 → 落随机态,由首备战帧 bench 整表观察覆盖收口;sim 恒
        # 未锚定 → 落账即世界真值(纠回 M01 预写的开局 4 张,选卡前无消费者)。
        # 零角色槽(live 空底座形态)零写,只留效果串申报替换事实。
        view = gs.bench.value
        slots = list(view.slots) if view is not None else []
        kept = [s for s in slots if s is None or s.kind != 'unit']
        removed = len(slots) - len(kept)
        if removed:
            write = _select_write(gs, rand)
            write(gs.bench, bench_view_of_working(kept, view),
                  produced_by=GAIN_CHAIN_PRODUCER,
                  evidence=f'on_env_gained:{_name}#opening_replace', sig=sig)
        effects.append(f'env_opening_replace:{removed}')
    for char in grant.chars_immediate:
        # 送卡为确定发放(非采样)→ rand 原样透传(gain-chain.md §5)
        gain_character(gs, char, 1, rand=rand, sig=sig,
                       evidence=f'on_env_gained:{_name}',
                       producer=GAIN_CHAIN_PRODUCER)
        effects.append(f'env_gift:{char}')
    # 持续伤害契约锚键分支(纯登记件非门控,消费 = 对账面):获得刻
    # best-effort 登记 'dot_anchor#<位面>-<轮>'(与即时分支同窗相邻,
    # write_logic 直写,同 evidence 同 sig;设计 = T-28 设计稿 §2.1,
    # 迭代 2026-09-23-invest-effects-calc)。须显式判 node——_node_frame
    # 节点未观察返回空串,照抄会产出 'dot_anchor#-' 畸形键;开局三选一
    # 获取时 sim 节点尚未进窗(node None)→ 不写 = 预期形态,缺锚不影响
    # 猜测写/计数/证实(check_env_dot_grants 门控 = active_env)。
    # kernel 反向模块级零 import 契约:函数内惰性取常量(先例 = 下方
    # 随机装备绑定分支 STAR_GRANT_KEY_PREFIX 同款函数级避环)。
    from sr_od.application.currency_war.kernel.cw_env_grants import (
        DOT_ANCHOR_KEY_PREFIX,
        DOT_CONTRACT_ENV,
    )
    if _name == DOT_CONTRACT_ENV and gs.node.value is not None:
        done = tuple(gs.env_grants_done.value or ())
        gs.write_logic(gs.env_grants_done,
                       done + ((_name,
                                f'{DOT_ANCHOR_KEY_PREFIX}'
                                f'{_node_frame(gs)}'),),
                       produced_by=GAIN_CHAIN_PRODUCER,
                       evidence=f'on_env_gained:{_name}', sig=sig)
    if grant.chars_random_immediate:
        # 随机支:效果体含采样 → 子链 rand=True(gain-chain.md §5 递归
        # 调用点按效果自身性质传参)。星级 = spec.star(人才引进 1 = 先验
        # 非结构值,先验错走随机态观察覆盖不响停);rng 缺省回退自掷
        # (直构/测试形态;正式接线 = 上报函数条件解析传入,sim 装配 =
        # 流键 rng 即世界真值,on_strategy_gained 的 roll_rng 同款回退)。
        roll_rng = rng if rng is not None else random.Random()
        for spec in grant.chars_random_immediate:
            pool = grant_char_pool(gs, spec)
            if not pool:
                # 构建期已闸(_validate_env_gifts 池非空),运行期空 =
                # 注册表漂移或全专家域未解锁;零写留 log 防御分支
                # (不改容器,不炸链)
                log.warning(
                    f'[cw-gain] 随机赠卡池空(注册表漂移?):'
                    f'{_name} cost={spec.cost} type_tag={spec.type_tag!r}')
                continue
            name = roll_rng.choice(pool)
            gain_character(gs, name, spec.star, rand=True, sig=sig,
                           evidence=f'on_env_gained:{_name}',
                           producer=GAIN_CHAIN_PRODUCER)
            effects.append(f'env_gift_random:{name}@{spec.star}star')
    for eq in grant.equips_immediate:
        # 装备 = 确定具名发放,写通道走随机态(rand=True 硬编码,2026-10-17
        # 用户裁定):「选卡时点游戏实际发下红钻」对该环境未经实机判读核实,
        # 卡面文本是唯一证据——猜测写 + equips 观察覆盖纠偏,首观察静默
        # 覆盖落 logic_rand_outcome 台账,锚定与否都不进失配网
        #(anchor_aware_write rand=True 恒随机态;先例 = T-5 财富宝钻随机态
        # 获得/T-29 全奖励分支随机态)。rand=True 只声明猜测语义,本分支零采样
        # 不需 rng。gain_equipment 原语内聚:equips 尾追(#equip 后缀
        # evidence 自动带上)+ on_equipment_gained 回调(红钻表外零子链)。
        # 落位成败与效果串解耦(开箱分支同口径:栏未观察拒落零写时效果串仍登记)。
        gain_equipment(gs, eq, rand=True, sig=sig,
                       evidence=f'on_env_gained:{_name}',
                       producer=GAIN_CHAIN_PRODUCER)
        effects.append(f'equip_gift:{eq}')
    for item in grant.items_immediate:
        # 落位 = 角色落位同构(_build_pool/bench_place/write 序;席满 →
        # 溢出落位,溢出位被占 = 零写留存证据,helper 内);效果串恒登记
        #(发放事实,与落位成败解耦)
        _place_bench_item(gs, item, rand=rand,
                          evidence=f'on_env_gained:{_name}', sig=sig)
        effects.append(f'item_gift:{item}')
    if grant.equips_random_immediate:
        # 随机装备支(世界发放域,首例劳务派遣合同分支1「获得随机星徽」):
        # 类别池(equips_by_category,注册表派生单源)内均匀掷骰选名 →
        # gain_equipment 入栏;效果体含采样 → 子链 rand=True(gain-chain.md
        # §5);rng 缺省回退自掷(采样是猜测口径,观察校准;正式接线 =
        # 上报函数条件解析传入,sim 装配 = 流键 rng 即世界真值,
        # chars_random_immediate 支同款)。落地序 = items_immediate 支之后、
        # 定时支之前。绑定门(ENV_BOSS_GRANTS 成员资格,模块级 import,
        # 同源无环):绑定语义 = 劳务派遣合同分支2(首领节点按绑定星徽发
        # 角色)专属——成员发放名落 done 条件键 'star_grant#<名>' 供分支2
        # 绑定解析、效果串沿 'env_star_grant:' 前缀;非成员(概念股族及
        # 后继)零 done 键、前缀 'env_equip_random:'(与具名支 'equip_gift:'
        # /随机角色支分域,审计归组键)——加门治「无条件绑定等第二个
        # 消费者」的潜伏缺陷,绑定态行为逐位不变。
        eq_rng = rng if rng is not None else random.Random()
        bound = _name in ENV_BOSS_GRANTS
        for cat in grant.equips_random_immediate:
            pool = equips_by_category(cat)
            if not pool:
                # 构建期已闸(_validate_env_gifts 类别闭集/池非空),运行期
                # 空 = 注册表漂移;零写留 log 防御分支(不改容器,不炸链;
                # 与 chars_random 支空池防御及分支2 池空防御对称)
                log.warning(f'[cw-gain] 随机装备类别池空(注册表漂移?):'
                            f'{_name} category={cat!r}')
                continue
            name = eq_rng.choice(pool)
            outcome = gain_equipment(gs, name, rand=True, sig=sig,
                                     evidence=f'on_env_gained:{_name}',
                                     producer=GAIN_CHAIN_PRODUCER)
            # 绑定分支(仅 ENV_BOSS_GRANTS 成员):发放名落 done 条件键
            # 'star_grant#<名>'(同窗相邻写,分支2 触发依赖);equips 未观察
            # 时 gain_equipment 零写跳档(placed=False)→ 绑定同样不落,
            # 宁缺勿造与分支2 缓发口径对齐(禁「绑定在而装备未发」残缺态)。
            # STAR_GRANT_KEY_PREFIX 函数级取常量:cw_env_grants 触发函数
            # 消费本模块 gain_character,模块级互导成环(先例 =
            # pick_invest_env.action_sampling_rng 同款函数级避环)
            if bound and outcome.placed:
                from sr_od.application.currency_war.kernel.cw_env_grants import (
                    STAR_GRANT_KEY_PREFIX,
                )
                done = tuple(gs.env_grants_done.value or ())
                gs.write_logic(gs.env_grants_done,
                               done + ((_name,
                                        f'{STAR_GRANT_KEY_PREFIX}{name}'),),
                               produced_by=GAIN_CHAIN_PRODUCER,
                               evidence=f'on_env_gained:{_name}#bind',
                               sig=sig)
            prefix = 'env_star_grant:' if bound else 'env_equip_random:'
            effects.append(f'{prefix}{name}')
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


def discharge_due_item_opens(gs: GameState, *, rand: bool,
                             sig: ChannelSig) -> tuple[str, ...]:
    """倒计时件到点开盒原语(环境延迟开盒通道;与 discharge_due_item_grants
    同区并列):读 pending_item_opens 现值,生效序位 ≥ 解锁位的条目为命中
    并弹除,其余保留;一次 write 回写保留队列,返回效果串(每命中项
    ``item_opened:<名>``)。唯一调用点 = sim 进节点收口
    (discharge_due_item_grants 调用邻位,cw_sim_backend 进节点收尾,
    T-34 设计稿 §2.4 挂点);实机局不接(不对称申报,
    cw_game_state.pending_item_opens 域注,T-34 设计稿裁决点 4)。

    - 零消耗分支:件 = 战利品区浮动件非占席(实机板件实证,T-34 设计稿
      §1),无席位槽可消耗——开盒 = 队列弹除 + 板件从战利品区消失
      (游戏侧事实,模型零席位写;开出的奖励若落席由现役 bench/装备
      观察自然捕捉)。
    - 开盒零产出写入(硬裁定:开盒内容卡面 desc 无载,放弃建模 =
      T-34 设计稿披露 1 delayed_item_open_content_unmodeled;sim 世界
      比实机少一份随机奖励;真值建立后 = 本原语加发放分支,零迁移)。
    - rand 语义:开盒 = 确定事件(非采样),调用方传 rand=False
      (discharge_due_item_grants 同款);写通道经 :func:`_select_write`
      单一收口;effective_node_pos 未锚定(None)→ 零写;命中集空 →
      零写。

    kernel 反向模块级零 import 契约外:effective_node_pos 住 cw_game_
    state(本模块既有模块级依赖),函数内惰性取沿 on_env_gained 同名
    先例,零新模块边。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        effective_node_pos,
    )
    eff = effective_node_pos(gs)
    if eff is None:
        return ()
    queue = tuple(gs.pending_item_opens.value or ())
    hit = [entry for entry in queue if entry[1] <= eff]
    if not hit:
        return ()
    keep = tuple(entry for entry in queue if entry[1] > eff)
    write = _select_write(gs, rand)
    write(gs.pending_item_opens, keep, produced_by=GAIN_CHAIN_PRODUCER,
          evidence=f'discharge_due_item_opens:p{eff[0]}-r{eff[1]}',
          sig=sig)
    return tuple(f'item_opened:{item}' for item, _unlock in hit)


def discharge_due_strategy_grants(gs: GameState, *, rand: bool,
                                  sig: ChannelSig) -> tuple[str, ...]:
    """策略延时发放到点原语(策略延时世界发放通道;与
    discharge_due_item_grants 弹除语义同构的并列独立域):读
    ``pending_strategy_grants`` 现值,remaining <= 0 条目 = 到期
    (「到了及以后都算」,错过不悬空),逐条查 ``STRATEGY_DELAYED_GRANTS``
    登记行取发放物分道发放——∈ EQUIPMENTS → gain_equipment(装备腿,
    尾追入栏)/ ∈ BENCH_ITEM_NAMES → gain_bench_item(占席道具腿),
    均确定发放随 rand 透传;队列条目只存卡名不存发放物 = 改名安全
    单一源。到期即弹除不回队(发放即消费;发放拒落零写 = 该件世界性
    丢失,留存证据于队列回写行,环境定时通道弹除语义同构)。保留队列
    与现值判等非空才一次 write 回写。返回效果串(每条
    ``delayed_grant:<item>(placed=<bool>)``,与落位成败解耦)。

    - rand 语义:策略延时发放 = 确定发放,调用方传 ``rand=False``
      (gain-chain.md §5;写通道仍经 :func:`_select_write` 单一收束);
    - 注册表查行失败防御(实现批后注册表漂移,正常不可达;import 校验
      在先):零写 + log warning + 条目保留不弹除,披露面 = 消费端
      sim 留证披露键,见值即注册表与队列失配,升级排查;
    - live 不接本原语(不对称申报,模块边界承担:调用仅存在于 sim
      模块,kernel 不 import sim);实机发放由游戏自己执行,装备入栏
      = equips 观察首见,audit 'equips' 行吸收。"""
    queue = tuple(gs.pending_strategy_grants.value or ())
    keep: list[tuple[str, int]] = [tuple(e) for e in queue if int(e[1]) > 0]
    if len(keep) == len(queue):
        return ()
    effects: list[str] = []
    for name, remaining in queue:
        if int(remaining) > 0:
            continue
        grant = STRATEGY_DELAYED_GRANTS.get(name)
        if grant is None:
            log.warning(f'[cw-gain] 策略延时发放注册表查行失败(注册表漂移?),'
                        f'条目保留:{name!r}')
            keep.append((name, int(remaining)))
            continue
        evidence = f'strategy_grant_due:{name}'
        if grant.item in EQUIPMENTS:
            outcome = gain_equipment(gs, grant.item, rand=rand, sig=sig,
                                     evidence=evidence,
                                     producer=GAIN_CHAIN_PRODUCER)
            placed = outcome.placed
        elif grant.item in BENCH_ITEM_NAMES:
            placed = gain_bench_item(gs, grant.item, rand=rand, sig=sig,
                                     evidence=evidence,
                                     producer=GAIN_CHAIN_PRODUCER)
        else:
            log.warning(f'[cw-gain] 策略延时发放物双域皆非(import 校验在先,'
                        f'漂移防御),条目保留:{name!r} {grant.item!r}')
            keep.append((name, int(remaining)))
            continue
        effects.append(f'delayed_grant:{grant.item}(placed={placed})')
    if tuple(keep) != queue:
        write = _select_write(gs, rand)
        write(gs.pending_strategy_grants, tuple(keep),
              produced_by=GAIN_CHAIN_PRODUCER,
              evidence='strategy_grant_due', sig=sig)
    return tuple(effects)


def expert_conditional_trigger(gs: GameState, char_name: str, *, rand: bool,
                               sig: ChannelSig, evidence: str) -> bool:
    """特邀专家族条件形态触发判据(「首次获得 X 时,顾问入商店」;首例 =
    特邀专家:银狼,设计 = 迭代 2026-09-23-invest-effects-calc T-42
    §2.1/§2.3)。三条件全与:

    ①``char_name`` == 触发角色名——现役唯一 = ``银狼LV.999``,触发映射
      硬编码分支、不建注册表:触发角色名只存在于
      ``ENV_GIFTS['特邀专家:银狼'].chars_conditional`` 的条件描述散文
      「首次获得【银狼LV.999】时,顾问入商店」,该字段 = (顾问名, 条件
      散文)注释性二元组不进判据(cw_investments.py 字段定义),本行即
      映射单一源(枚举即收敛、不设注册机构先例 = 本模块枚举回调区
      头注);按规范名直等,费用档无关——银狼LV.999 升费 3/4/5 档全
      通吃(lv999_cost_tier 是费用字段非名字,不进判据);
    ②``gs.active_env`` 归一后 == 本卡名(normalize_invest_name 同款,
      gain_invest_env 归一行先例;登记表单环境互斥天然挡他环境的同形
      发放渠道——如欢愉契约开局送银狼LV.999 不触发本卡);
    ③``'银狼' ∉ gs.unlocked_experts``——「已触发」与「已解锁」同一
      事实,防重发记账与消费同源、不立第二账本;``_unlock_experts``
      幂等短路免费兜住升星产物递归重进与假想双发;顾问已被他通道解锁
      (邀请函等)时本条件短路零写(效果文无新事实,语义正确)。

    命中 → :func:`_unlock_experts`(唯一容器落点 + 闭集闸 + 只增去重 +
    rand 透传全由原语承载,判据层不开第二写点、不自写去重)→ 返回
    True 供调用方发效果串(现役 = ``expert_unlock:银狼``)。判据 =
    纯读 + 条件写,零吞错(状态写沿主链纪律,gain-chain.md §6;与
    on_buy 记录面 best-effort 分层——记录可弃,状态写不可静默失败)。

    **触发面完备性口径**(防按「on_character_gained 单点收敛」旧口径
    理解覆盖面;「获得银狼LV.999」获得事实三派,现役触发可达性如实):
    - 商店购买(现役主流,购买回调分支 report_action_buy_card_param 追加
      判据,3 费档基础池恒可刷);
    - 平行桥 grant_bench_unit_cascade(装备获得后果确定性通道 数据拷贝
      仪Max 送 1★银狼LV.999;随机通道经获得链 on_equipment_gained,
      现役 HACKER_MOD_POOL_V0 无该件,张力反例成真时即真渠道);
    - 获得链 gain_character(on_character_gained 收敛点转发;链上生产
      调用点全量普查现役可达获得 = boss 节点羁绊分支,被条件②×
      ENV_BOSS_GRANTS 单环境互斥挡在触发外——本接线 = 收敛点承诺兑现
      + 登记表未来扩入带目标名池发放分支的防御)。
    豁免(非渠道)= 升费/上阵变费分支(已有单位改费用档,无获得事件)/
    复制系(复制前提 = 目标已在手,「首次」必然更早发生)/ grant_bucket
    (现役纯查询候选口无落席写点)/ 专家邀请函(解锁的是顾问非
    银狼LV.999)。开局种子起手与先获后选环境局(首次获得先于环境获得)
    由挂点④收口(on_env_gained advisor 分道条件形态支,环境获得时刻
    在场判定)。
    """
    if char_name != '银狼LV.999':
        return False
    if normalize_invest_name(str(gs.active_env.value or '')) \
            != '特邀专家:银狼':
        return False
    if '银狼' in (gs.unlocked_experts.value or ()):
        return False
    _unlock_experts(gs, ('银狼',), rand=rand,
                    evidence=f'{evidence}#expert_unlock', sig=sig)
    return True


def on_character_gained(gs: GameState, name: str, star: int, *,
                        rand: bool, sig: ChannelSig) -> tuple[str, ...]:
    """「获得角色」触发型效果枚举(gain-chain.md §3)。

    在用枚举 = 转发特邀专家族条件形态判据
    (:func:`expert_conditional_trigger`;首个消费者 = 特邀专家:银狼,
    命中发效果串 ``expert_unlock:银狼``)。**本函数 = 该类效果未来的唯一
    收敛点**——新效果核实后在此加分支;递归子链的 rand 按效果自身性质传
    (gain-chain.md §5)。
    """
    _ = star   # 接口位保留(判据按规范名直等,星级/费用档无关;升星产物
    # 递归重进由判据条件③幂等短路,无需星级)
    if expert_conditional_trigger(gs, name, rand=rand, sig=sig,
                                  evidence='on_character_gained'):
        return ('expert_unlock:银狼',)
    return ()


def on_equipment_gained(gs: GameState, item: str, *, rand: bool,
                        sig: ChannelSig) -> tuple[str, ...]:
    """「获得装备」触发型效果枚举(gain-chain.md §3):消费
    ``EQUIP_ACQUIRE_CONSEQUENCES`` 数据表(装备获得→送出单位;该表是
    游戏数据映射不是效果注册表,保留)→ 命中且送出单位为专家顾问
    (分身墨镜族卡文「解锁并获得」= 入池 + 送单位两条分支,口述权威
    2026-09-18 送单位入账分支)→ :func:`_unlock_experts` 先写解锁再送单位
    入席;非专家送出单位(银狼LV.999)只走送单位入账分支。表外件 = 查无效果
    安静不写。"""
    granted = EQUIP_ACQUIRE_CONSEQUENCES.get(item)
    if granted is None:
        return ()
    name, star = granted
    effects: list[str] = []
    if name in EXPERT_CHARS:
        _unlock_experts(gs, (name,), rand=rand,
                        evidence=f'on_equipment_gained:{item}#expert_unlock',
                        sig=sig)
        effects.append(f'equip_expert_unlock:{name}')
    gain_character(gs, name, star, rand=rand, sig=sig,
                   evidence=f'on_equipment_gained:{item}',
                   producer=GAIN_CHAIN_PRODUCER)
    return (*effects, f'equip_consequence:{name}',)


def on_strategy_gained(gs: GameState, strategy_name: str, *, rand: bool,
                       sig: ChannelSig,
                       rng: random.Random | None = None) -> tuple[str, ...]:
    """「获得投资策略」触发型效果枚举(gain-chain.md §3;枚举即收敛
    无注册表):两条分支依次消费——

    1. **advisor 解锁分支**:查 ``STRATEGY_GRANTS``(顾问入商店族登记,
       advisor=True 11 条)→ :func:`_unlock_experts` 写解锁状态(官方
       效果文「使其在本局游戏中加入商店」= 入池可刷;与
       :func:`on_env_gained` advisor 道同一原语);
    2. **效果体分支**:查 ``PICK_INVEST_EFFECTS``(效果内容住
       ``cw_gain_effects.py``,本模块模块级查表)分派效果函数;未收录卡 =
       查无效果安静不写,真值归观察覆盖。``rng`` = 采样注入(缺省
       ``random.Random()`` 在本函数体内生成;效果体含采样 → 对其子链传
       rand=True,§5)。"""
    canon = normalize_invest_name(strategy_name)
    effects: list[str] = []
    _grant = STRATEGY_GRANTS.get(canon)
    if _grant is not None and _grant.advisor:
        _unlock_experts(gs, _grant.chars_immediate, rand=rand,
                        evidence=f'on_strategy_gained:{canon}#expert_unlock',
                        sig=sig)
        effects.append(f'advisor_unlock:{canon}:'
                       f'{"+".join(_grant.chars_immediate)}')
    fn = PICK_INVEST_EFFECTS.get(canon)
    if fn is None:
        return tuple(effects)
    roll_rng = rng if rng is not None else random.Random()
    return (*effects, *fn(gs, sig=sig, rng=roll_rng))
