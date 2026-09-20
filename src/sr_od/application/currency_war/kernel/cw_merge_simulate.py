"""货币战争 合成引擎 merge_simulate(期望态 infra §4;纯函数离线可测)。

语义权威 = merge_mechanics §2/§2.5/§2.7 + EXPECTED_STATE.md §4(FINAL v3.1):
1. 同名同星计数 = bench+deployed 全场合计;满 3 → 升星,**连锁可多级**
   (2★ 产物再与 2★ 凑 3 → 3★);
2. 落点:三张全在备战栏 → 取最左;含场上 → 落场上那个同星的位置;
3. 满栏例外:能触发合成的牌满栏也买得进;自动多买一次买满缺数
   ``min(店内张数, 3 − 已有 mod 3)``,金账全款(无折扣);
4. 装备继承:三只身上的装备**全部**继承到升星产物(玩家口述 2026-09-02
   定谳,补备战案空白;与「场上吸收装备/站位随之继承」一致);
5. 星徽(阵营装备)不参与星数合成——本引擎只辖角色星数,装备名单随
   Unit.equips 原样继承,不做类别分流(分流是佩戴决策域)。

与 ``cw_state._merge_bench`` 的关系:_merge_bench 是 tracked 侧既有不动点
合并(语义同源),本引擎在其规则上增加**合成链记录**(每级 (星级, 落点,
继承装备))+ 满栏自动多买张数,供期望态对账逐级核对(对账五分类之
「合成落点/星级不符」的期望值来源)。两实现的规则若漂移,以 merge_
mechanics 为准修齐(单一语义源,双载体是 tracked 原地推进 vs 期望态
纯函数的不同形态需要)。

恒成立不变量(EXPECTED_STATE §P2 批注 5):合成后「场上同名同星 ≤1」
——本引擎出参断言,违例即抛(模型错当场暴露,不进对账静默)。

载体形状(benchchar-retirement P1 定形、P5 单形收窄):bench =
``list[BenchSlot | None]`` / deployed = ``list[Unit | None]``(§2.3);
元素 frozen → 推进 = replace 新构造 + 定位符索引,素材摘除 = 置 None
(保洞)。条目身份读协议(:func:`_entry_identity`)容器单形状,引擎
全链零 BenchChar 载体。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    bench_place,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    Unit,
    shop_cards_to_legacy,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ShopCard as _ContainerShopCard,
)

if TYPE_CHECKING:
    # 仅类型注解引用(旧 ShopCard = cw_state 动作域词汇,运行时鸭子读
    # name/star,零运行时依赖)。
    from sr_od.application.currency_war.kernel.cw_vocab import ShopCard


@dataclass
class MergeStep:
    """一级合成的链记录(对账逐级核对的最小单元)。

    [定义注释] landing_kind/landing_slot = 升星产物的落点坐标系:
    'bench' 时 landing_slot = 物理槽位 1-9(最左合成);'deployed' 时
    = deployed 槽位表下标 0-9(场上吸收,ADR-0392)。inherited_equips =
    被消耗两只的装备全量(§4 规则 4,玩家定谳)。
    """
    name: str
    from_star: int
    to_star: int
    landing_kind: str            # 'bench' | 'deployed'
    landing_slot: int
    inherited_equips: list[str] = field(default_factory=list)


@dataclass
class MergeSimResult:
    """merge_simulate 出参:终态 + 合成链 + 实际购入张数(benchchar-
    retirement P1 起容器原生形状:bench = BenchSlot | None 槽表 /
    deployed = Unit | None 下标槽表,§2.3)。"""
    bench_after: list[BenchSlot | None]
    deployed_after: list[Unit | None]
    chain: list[MergeStep]
    buy_k: int               # 实际购入张数(含满栏自动多买;0 = 满栏且不可触发 → 拒买)
    multi_buy: bool = False  # 满栏自动多买是否发生(buy_k > 请求张数)
    #: 满栏多买 + 合成腾槽后仍无处安放的散牌(merge_mechanics §2.5 已知
    #: 建模缺口;对账只评 1-9 槽,本列表供证据落证,不抛)
    overflow: list[BenchSlot] = field(default_factory=list)


def _identity_of(x: Unit) -> tuple[str, int]:
    """条目身份(容器 ``Unit``;分组键只读 char_id/star 两语义位)。"""
    return ((str(getattr(x, 'char_id', '') or '')),
            int(getattr(x, 'star', 1) or 1))


def _entry_identity(x: object) -> tuple[str, int] | None:
    """计数族条目身份读协议(容器单形状;benchchar-retirement P5 收窄):
    bench 侧 ``BenchSlot``(kind='unit' → 内嵌 Unit 身份;占位/empty →
    None)/deployed 侧 ``Unit``。原「观察边界 BenchChar 形」兼容支已随
    帧通道退役删除——P5 全仓零调用核实后收窄单形,非容器形状 = None
    (fail-closed 跳过,禁猜身份)。"""
    if x is None:
        return None
    if isinstance(x, BenchSlot):
        # BenchSlot:unit kind 才有身份(占位件五分类非角色)
        if x.kind == 'unit' and x.unit is not None:
            return _identity_of(x.unit)
        return None
    if isinstance(x, Unit):
        return _identity_of(x)
    return None


def _slots_iter(bench, deployed):
    """全场域占用条目迭代(bench∪deployed;分组键扫描单一遍历)。"""
    for x in (bench or []):
        if x is None:
            continue
        yield x, _entry_identity(x)
    for x in (deployed or []):
        if x is None:
            continue
        yield x, _entry_identity(x)


def _entry_equips(x) -> list[str]:
    """条目装备读(C6 继承腿;bench 侧 BenchSlot → 内嵌 Unit,deployed
    侧 Unit 直读)。"""
    u = x.unit if isinstance(x, BenchSlot) else x
    return list(getattr(u, 'equips', None) or [])


def _dep_sig(deployed) -> list:
    """deployed 下标表值签名(变更检测用;条目 = (char_id, star, equips),
    None 洞原样)。消费方 = 买牌上报的行写判据/采样链逐步写判据。"""
    return [None if d is None else
            (d.char_id, d.star, tuple(d.equips or ()))
            for d in (deployed or [])]


def _bench_sig(slots) -> list:
    """bench 槽表值签名(变更检测用;BenchSlot 条目 = (kind, unit 身份),
    占位件 kind 细分参与签名——kind 翻转即需落行)。"""
    out = []
    for s in (slots or []):
        if s is None:
            out.append(None)
            continue
        u = s.unit if s.kind == 'unit' else None
        out.append((s.kind, None if u is None else
                    (u.char_id, u.star, tuple(u.equips or ()))))
    return out


def merge_simulate(bench: list[BenchSlot | None],
                   deployed: list[Unit | None] | None,
                   name: str, star: int, k: int = 1,
                   in_shop_count: int | None = None) -> MergeSimResult:
    """买牌 (name, star, 请求张数 k) 的合成终态推演(纯函数;不改入参;
    P1 起容器原生形状 §2.3)。

    - 常态:逐张落入备战空槽(§1 最左空位)→ 不动点合并;
    - 满栏:仅当本次购买能触发合成(``merge_buy_completes``)才放行,
      自动多买 k = ``min(店内张数, 3 − 已有 mod 3)``(§2.5;in_shop_count
      缺省按 3-mod 保守取,调用方有店内真值时显式传);
    - 合成链逐级记录(落点/继承);出参断言「场上同名同星 ≤1」。

    名称/星级未知(name 空)→ 原样返回零推进(宁缺勿造,与买牌期望态
    通道同口径)。元素 frozen(BenchSlot/Unit)→ 推演以 replace 新构造
    推进,合成体 = 逐级 replace 链(零就地变异,工作副本与调用方断开
    别名由 frozen 保证)。
    """
    bench_t: list[BenchSlot | None] = list(bench or [])
    while len(bench_t) < BENCH_CAPACITY:
        bench_t.append(None)
    dep_t: list[Unit | None] = list(deployed or [])
    chain: list[MergeStep] = []
    overflow: list[BenchSlot] = []
    if not name:
        return MergeSimResult(bench_after=bench_t, deployed_after=dep_t,
                              chain=chain, buy_k=0)
    star_n = star or 1
    eff_k = 0
    multi_buy = False
    if k > 0:
        # 满栏例外(§2.5):自动多买张数取 min(店内张数, 3−已有 mod 3),复用
        # merge_buy_k/merge_buy_completes 单一源(禁消费方手搓同式)。
        # 假牌构造 = 容器类型 + 映射函数边界转换(双 ShopCard 归一,§2.5:
        # 转换只许在映射函数发生;helper 只消费 name/star,转换体 x 置 0
        # 不消费)。
        eff_k = k
        if sum(1 for b in bench_t if _entry_identity(b) is not None) \
                >= BENCH_CAPACITY:
            shop_cap = in_shop_count if in_shop_count is not None else 3
            _shop = shop_cards_to_legacy(
                [_ContainerShopCard(name=name, star=star_n)
                 for _ in range(max(0, min(shop_cap, 3)))])
            eff_k = merge_buy_k(name, star_n, bench_t, dep_t, shop=_shop)
            if not merge_buy_completes(name, star_n, bench_t, dep_t,
                                       shop=_shop) or eff_k <= 0:
                return MergeSimResult(bench_after=bench_t,
                                      deployed_after=dep_t,
                                      chain=[], buy_k=0)
            multi_buy = eff_k > k
        for _ in range(eff_k):
            slot = BenchSlot(kind='unit', unit=Unit(char_id=name,
                                                    star=star_n))
            if bench_place(bench_t, slot) is None:
                overflow.append(slot)   # 满栏暂溢出(合成腾槽后再归位)
    # 不动点合并(逐级记录链;分组键 = 同名同星,全域 bench∪deployed∪溢出
    # ——满栏多买的第 3 张在溢出表里,必须进合成池,否则合成永不触发)。
    # frozen 载体(BenchSlot/Unit)→ 以定位符 (域, 下标) 推进:素材摘除 =
    # 置 None/删溢出项,载体升星 = replace 新构造写回原定位。
    while True:
        merged = False
        scan: list[tuple[str, int, object, tuple[str, int] | None]] = (
            [('bench', i, b, _entry_identity(b))
             for i, b in enumerate(bench_t) if b is not None]
            + [('dep', i, d, _entry_identity(d))
               for i, d in enumerate(dep_t) if d is not None]
            + [('ovf', j, s, _entry_identity(s))
               for j, s in enumerate(overflow)])
        for _dom, _idx, _item, ident in scan:
            if ident is None or not ident[0]:
                continue
            cid, cstar = ident
            group = [e for e in scan if e[3] == (cid, cstar)]
            if len(group) < 3:
                continue
            take = group[:3]
            # 载体:含场上 → 场上那个同星位置;全备战(含溢出件时溢出件
            # 记入溢出表,落点语义以 bench 槽位归位后为准)→ take[0]
            #(扫描序 = bench 槽位升序,即最左)
            dep_take = next((e for e in take if e[0] == 'dep'), None)
            carrier_entry = dep_take if dep_take is not None else take[0]
            landing_kind = ('deployed' if dep_take is not None else 'bench')
            if dep_take is not None:
                landing_slot = dep_take[1]
            elif carrier_entry[0] == 'ovf':
                landing_kind, landing_slot = 'bench', 0   # 溢出件归位后定槽(对账校准项)
            else:
                landing_slot = carrier_entry[1] + 1   # 物理槽位 1-9
            inherited: list[str] = []
            ovf_remove: list[int] = []
            for e in take:
                if e is carrier_entry:
                    continue
                inherited += _entry_equips(e[2])
                if e[0] == 'ovf':
                    ovf_remove.append(e[1])
                elif e[0] == 'bench':
                    bench_t[e[1]] = None
                else:
                    dep_t[e[1]] = None
            for j in sorted(ovf_remove, reverse=True):
                overflow.pop(j)   # 降序摘除:低索引摘除不位移未摘高索引项
            carrier = carrier_entry[2]
            new_star = ident[1] + 1
            new_equips = _entry_equips(carrier) + inherited
            chain.append(MergeStep(name=cid, from_star=cstar,
                                   to_star=new_star,
                                   landing_kind=landing_kind,
                                   landing_slot=landing_slot,
                                   inherited_equips=inherited))
            new_carrier = _bump_carrier(carrier, new_star, new_equips)
            if carrier_entry[0] == 'dep':
                dep_t[carrier_entry[1]] = new_carrier
            elif carrier_entry[0] == 'bench':
                bench_t[carrier_entry[1]] = new_carrier
            else:
                # 溢出表索引可能已被本级摘除位移,按对象身份重定位
                j = next(k for k, s in enumerate(overflow)
                         if s is carrier)
                overflow[j] = new_carrier
            merged = True
            break   # 重扫(结构已变)
        if not merged:
            break
    # 溢出归位:合成腾出的空槽优先(§2.5 满栏购买先腾后落)
    still_overflow: list[BenchSlot] = []
    for slot in overflow:
        if bench_place(bench_t, slot) is None:
            still_overflow.append(slot)
    # 恒成立不变量(§P2 批注 5):场上同名同星 ≤1
    dep_keys = [ident for _dom, _i, _d, ident in
                [('dep', i, d, _entry_identity(d))
                 for i, d in enumerate(dep_t) if d is not None]
                if ident is not None and ident[0]]
    if len(dep_keys) != len(set(dep_keys)):
        raise AssertionError(
            f'merge_simulate 不变量违例:场上同名同星 >1({dep_keys})')
    return MergeSimResult(bench_after=bench_t, deployed_after=dep_t,
                          chain=chain, buy_k=eff_k, multi_buy=multi_buy,
                          overflow=still_overflow)


def _bump_carrier(carrier: object, new_star: int,
                  new_equips: list[str]) -> object:
    """合成载体升星 + 装备继承的 frozen 新构造(bench 侧 BenchSlot 包
    Unit / 场上裸 Unit 双载体;容器原生形状之外禁入——BenchChar 不再
    是本引擎载体,观察边界转换归 bench_from_compact/deployed_from_compact)。"""
    from dataclasses import replace
    if isinstance(carrier, BenchSlot):
        u = carrier.unit
        if u is None:
            raise TypeError('merge 载体 BenchSlot 无 Unit(占位件不可合成)')
        return replace(carrier, unit=replace(u, star=new_star,
                                             equips=list(new_equips)))
    if isinstance(carrier, Unit):
        return replace(carrier, star=new_star, equips=list(new_equips))
    raise TypeError(
        f'merge 载体形状不支持: {type(carrier).__name__}(容器原生 '
        f'BenchSlot/Unit 之外形状,禁复活 BenchChar 推演)')


def field_family_of(path: str) -> str:
    """路径 → 字段族(覆盖点可信门过滤用;EXPECTED_STATE §2 字段族口径)。"""
    head = (path or '').split('.', 1)[0]
    if head in ('tracked_bench_chars', 'tracked_deployed', 'bench', 'deployed'):
        return 'tracked'
    return head or 'unknown'


def same_star_count_public(name: str, star: int,
                           bench: list[BenchSlot | None],
                           deployed: list[Unit | None] | None) -> int:
    """同星计数透出(测试/对账便利;单一源仍是 cw_state.same_star_count)。"""
    return same_star_count(name, star, bench, deployed)


# ============================================================
# 候裁9 词汇迁入(原 kernel/cw_state.py 合成域):
# 升星合成规则族与本引擎双源收敛(单一语义源同文件定居;原 :35 的
# 本模块->cw_state 反向 import 同批消除)。
# ============================================================



def _merge_bench(bench: list[BenchSlot | None],
                 deployed: list[Unit | None] | None = None,
                 on_step: Callable[[], None] | None = None) -> None:
    """3 合 1 升星:同名同星 ≥3(全场域 bench+deployed)→ 合并为 1 个 star+1。

    游戏机制:招募 3 个相同星级同名角色自动升星。⚠️ **合并域 = 全场**——
    「3合1 是全场」;live 实证(2026-08-18 r17)与 merge_mechanics 单一
    语义源。合成载体:场上同名卡升星优先(触发处常见态),无场上卡则
    bench 首张升星。

    P1 起容器原生形状(§2.3):bench = ``list[BenchSlot | None]`` /
    deployed = ``list[Unit | None]`` 下标槽表;素材摘除 = 置 None 腾槽
    (ADR-0316/0392 保洞语义,合成载体留在原槽位);载体升星 = frozen
    replace 新构造(装备继承随之写回载体)。

    deployed=None(旧调用兼容)= 只看 bench(等价旧行为)。

    on_step(可选步回调,逻辑随机态采样链用):**每完成一级合并**(升星/
    置 None/装备继承全部落定后)调用一次,调用侧经回调把工作列表当前
    状态落容器(逐步写遥测);回调内看到的列表 = 该级合并完成后的状态。
    None = 现行为(逐级回调缺省,既有消费者零改动)。注意:一级合并可
    同时变更 bench 与行域(deployed 侧载体),调用侧按受影响域各落一行。
    """
    # 不动点循环:两轮上限在级联合并(3×1★→2★→…)不够;while 直到
    # 一轮无合并——游戏语义即如此,且级联有限(星≤5)自然终止
    while True:
        merged_any = False
        scan: list[tuple[str, int, object, tuple[str, int] | None]] = (
            [('bench', i, b, _entry_identity(b))
             for i, b in enumerate(bench) if b is not None]
            + ([('dep', i, d, _entry_identity(d))
                for i, d in enumerate(deployed) if d is not None]
               if deployed is not None else []))
        for _dom, _idx, _item, ident in scan:
            if ident is None or not ident[0]:
                continue
            cid, cstar = ident
            # 全场同名同星组(跨池;对象身份定位符)
            group = [e for e in scan if e[3] == (cid, cstar)]
            if len(group) < 3:
                continue
            take = group[:3]
            # 载体:场上优先
            carrier_entry = (next((e for e in take if e[0] == 'dep'), None)
                             or take[0])
            inherited: list[str] = []
            for e in take:
                if e is carrier_entry:
                    continue
                inherited += _entry_equips(e[2])
                if e[0] == 'bench':
                    bench[e[1]] = None
                else:
                    deployed[e[1]] = None
            carrier = carrier_entry[2]
            new_carrier = _bump_carrier(carrier, cstar + 1,
                                        _entry_equips(carrier) + inherited)
            if carrier_entry[0] == 'bench':
                bench[carrier_entry[1]] = new_carrier
            else:
                deployed[carrier_entry[1]] = new_carrier
            merged_any = True
            if on_step is not None:
                on_step()   # 该级合并已全部落定(升星/继承/置 None),回调看终态
            break   # 重扫(列表已变)
        if not merged_any:
            break


def will_merge_on_buy(card: ShopCard, bench: list[BenchSlot | None],
                      deployed: list[Unit | None] | None = None) -> bool:
    """买第 3 份同名同 1★ 即合成(S3/H3 口径,ADR-0325)。

    判据 = ``_merge_bench`` 分组键同口径:**同名同 1★ 计数(全场
    bench∪deployed)==2 且待买为 1★**——买后恰达 3 份触发合并。
    显式**不用星级加权**(1 个 2★ 加权 2 但同星计数=1,不合成交
    bench 净 +1;旧 candidates.will_merge 加权判据的误标例)。
    消费点:candidates.will_merge(生成侧)。ADR-0453 起满栏
    购买门/执行侧(simulate)改走一般式 merge_buy_completes/merge_buy_k
    (k 可 >1);本函数保留 = k=1 特例的生成侧标记语义。
    """
    if (card.star or 1) != 1:
        return False
    n = 0
    for _x, ident in _slots_iter(bench, deployed):
        if ident == (card.name, 1):
            n += 1
    return n == 2


def same_star_count(name: str, star: int,
                    bench: list[BenchSlot | None],
                    deployed: list[Unit | None] | None = None) -> int:
    """全场域同名同星计数(bench∪deployed;``_merge_bench`` 分组键同口径;
    条目身份读协议 = :func:`_entry_identity`,容器单形状)。"""
    n = 0
    for _x, ident in _slots_iter(bench, deployed):
        if ident == (name, star):
            n += 1
    return n


def star_base_copies(star: int) -> int:
    """星级 → 同名 **1★ 基础副本数** 折算(3**(star-1);【注】合成机制
    真值:每升一星由 3 份低星合成,1★=1/2★=3/3★=9)。

    单一源:折算的消费位(持有量入经济/牌池账等)一律经本函数,禁内联
    dict 或裸幂式第二表达(旧内联形态 = shop.py 星级折算 dict 与
    cw_comps/cw_economy/cw_intention 的散写 ``3 ** (star - 1)``,后者
    随批收敛挂账)。star 缺效(非 1-3)→ 保守折 1 份(与旧 dict 缺省
    ``.get(star, 1)`` 同值)。"""
    s = int(star or 1)
    if s < 1 or s > 3:
        return 1
    return 3 ** (s - 1)


def merge_material_reject_reason(name: str, star: int,
                                 bench: list[BenchSlot | None],
                                 deployed: list[Unit | None] | None = None,
                                 ) -> str:
    """bench 侧卖出通道的合成素材拒入守卫(返回拒因键,'' = 可卖)。

    判据:``c_excl = same_star_count(name, star, bench∪deployed) − 1``
    (含自身全场域计数再扣 victim 自己)``≥ 1`` ⇒ 拒入资格集,拒因键
    ``merge_material_guard``——与部署侧 ``cw_deploy_logic.
    swap_sell_exclusion_reason`` 的拒因闭集**同名同键**(同一守卫语义
    的两个卖出路径实现点;计数单一源 = ``same_star_count``,禁消费方
    手搓同式)。辖域 = bench 四卖出通道(M4 燃料/凑息卖/支付变现/
    换线塌缩),各通道原有资格谓词不动,只追加本子谓词。
    数学依据:同名同星满 3 即自动升星且不变量「场上同名同星 ≤1」
    (merge_mechanics.md §1/§2)⇒ c_excl≥2 稳态不可达,守卫生效域
    恒为 c_excl=1(2/3 合成进度,差最后一张)——卖出即销毁距 2★
    差一张的确定性进度期权,fail-closed 不卖。辖星 = 1(升星链语义
    不在本守卫辖域;2★ 成件全场唯一,子谓词恒放行)。
    设计出处:ADR-0558(合成素材拒入守卫,与部署侧 merge_material_guard
    同键);案发对账 = g_20260906_081836 / g_20260906_095111 两局 P2r1
    (2/3 进度素材被燃料类资格卖断)。
    """
    if (star or 1) != 1:
        return ''
    return ('merge_material_guard'
            if same_star_count(name, 1, bench, deployed) - 1 >= 1 else '')


def merge_material_stale_names(bench: list[BenchSlot | None],
                               deployed: list[Unit | None] | None = None,
                               ) -> tuple[str, ...]:
    """滞留素材名集(分键 ``merge_material_stale`` 的判定单一源)。

    判定:全场域(bench∪deployed)同名同 1★ 计数 ≥2 的名 = 存在 2/3
    合成进度素材对;计数单一源 = ``same_star_count``(与
    ``merge_material_reject_reason`` 同源,禁消费方手搓同式)。
    辖星 = 1(2★ 成件全场唯一,不构成素材对,同守卫口径)。
    排序 = 字母序去重(确定性计数,禁集合迭代序入账本)。
    「滞留」语义:对在场即 2/3 进度悬置;持续 N 轮计数仍增长 = N 轮
    未合成(合成后计数停止增长,轮差分归零)——轮级时长由消费端按
    键差分判读,本函数只答「当前帧哪些名滞留」。设计出处:ADR-0558
    §4 滞留显影欠账(G-B1 第四级)。
    """
    names = {ident[0] for _x, ident in _slots_iter(bench, deployed)
             if ident is not None and ident[1] == 1}
    return tuple(sorted(n for n in names if n
                        and same_star_count(n, 1, bench, deployed) >= 2))


def count_merge_material_blocked(counters: dict, name: str,
                                 dedup_names: set[str] | None = None,
                                 ) -> None:
    """拒因分键 ``merge_material_guard_blocked`` 的**事件口径**计数单一源。

    口径(C1,三审整改定谳):拦截**事件**计数,非评估次数——同一决策
    帧内同一素材名只计 1(帧内多通道资格评估、投影读(P56 liquid_
    refund)/腾席环重试对同名重复触达均去重),跨帧滞留素材每次新触达
    仍计。去重载体 = ``dedup_names``(调用方按帧创建并传入;None =
    无去重的单评语境,测试/离线直调)。评估次数口径为已废弃的实装
    偏差(ADR-0558 §4「拦截事件判读」被投影读/重试环污染的整改)。
    """
    if dedup_names is not None:
        if name in dedup_names:
            return
        dedup_names.add(name)
    counters['merge_material_guard_blocked'] = \
        counters.get('merge_material_guard_blocked', 0) + 1


def merge_buy_k(name: str, star: int,
                bench: list[BenchSlot | None],
                deployed: list[Unit | None] | None,
                shop: list[ShopCard] | None = None) -> int:
    """满栏合成买的一次点击购买张数 k(merge_mechanics.md §2.5 单一源)。

    k = min(店内同名同星张数, 3 − 已有数 mod 3)——上限口径「绝不多买」:
    只买到触发一次合成所需的量。返回值不含「是否真触发合成」判断
    (那由 ``merge_buy_completes`` 判);店内外身份计数共用
    ``same_star_count``/同键过滤,禁消费方各自手搓(双源漂移温床)。

    消费点:candidates/arbiter 满栏购买门(ADR-0453)/simulate 满栏多买
    (执行侧)/shop.py 买入意图记录(执行账 k×单价)。
    """
    star_n = star or 1
    own = same_star_count(name, star_n, bench, deployed) % 3
    in_shop = sum(1 for c in shop or []
                  if getattr(c, 'name', '') == name
                  and (getattr(c, 'star', 1) or 1) == star_n)
    return min(in_shop, 3 - own)


def merge_buy_completes(name: str, star: int,
                        bench: list[BenchSlot | None],
                        deployed: list[Unit | None] | None,
                        shop: list[ShopCard] | None = None) -> bool:
    """本次点击(买 k = ``merge_buy_k`` 张)是否恰好完成一次合成。

    判据 = 同名同星计数(备战栏+场上)+ 本次购买 ≥ 3(ADR-0453 允许条件,
    merge_mechanics §2.5);等价于 k == 3 − 已有数 mod 3。不满足 → 满栏
    照旧拒买(ADR-0283 守卫语义保留为兜底)。

    own≥1 门(ADR-0619):own=0(全场 bench∪deployed
    无同名同星)时合成买不成立,按满栏非合成买拒收——merge_mechanics
    §2.5 的满栏例外以「已有素材/载体在场、买入可完成合成」为前提,
    own=0 时首张买入既无空槽落位、也无进行中的合成可完成,游戏侧该
    点击被拒(金不扣、牌不下架)。缺此门的旧形态:own=0+店内 3 张
    误判可合成 → k=3 全为尾挂张、合成载体落 idx9 被 ``del bench[9:]``
    截删,双账同错且共同偏离游戏拒买真值。边界:§2.5「连升同理」
    (own=0 于基础星、栏满连买 3 张)为自标低置信口述未亲见,本门
    按拒买语义实现;若拖动对账网实证连升可行,须回本单一源改门。
    """
    own = same_star_count(name, star or 1, bench, deployed) % 3
    if own == 0:
        return False
    k = merge_buy_k(name, star, bench, deployed, shop)
    return own + k >= 3


def _apply_full_bench_merge_buy(bench: list[BenchSlot | None],
                                deployed: list[Unit | None] | None,
                                card: ShopCard,
                                shop: list[ShopCard] | None) -> int | None:
    """满栏合成买分支应用(``mutate_bench_deployed`` 与买牌上报共用
    单一源)。

    调用语境 = ``bench_place`` 失败(bench 无空槽)后的满栏买入;前置 =
    该买完成一次合成(``merge_buy_completes``,不满足 = 满栏拒买,
    ADR-0283 兜底)。应用 = k = ``merge_buy_k`` 张临时挂槽位表尾参与
    ``_merge_bench``(3 合 1 是全场;own+k ≡ 0 mod 3,合成本身恒耗尽
    尾挂张),截回定长 9。载体落点语义依赖 own≥1:own=1/2 时合成组
    含场内张,载体落在 idx<9 或场上,截断不伤;own=0 域(全尾挂、
    载体落 idx9 必被截删)由 ``merge_buy_completes`` 的 own≥1 门排除
    (ADR-0619)。返回应用张数 k;前置不满足返回 None(调用方
    据此 no-op)。

    双账同构依据(2026-09-09 05:52 运行局双响事故):满栏时游戏
    对完成合成的买入**接受并合成**(金照扣、bench 素材被消费腾槽、场上
    载体升星)——逻辑态与 tracked 两本账必须同走本分支;旧 tracked 侧
    丢件不合成使两账结构性分叉,守卫在同 visit 下一动作(逻辑态侧已腾槽、
    豁免条件失效)对拍误炸。
    """
    _name = card.name
    _star = card.star or 1
    if not merge_buy_completes(_name, _star, bench, deployed, shop):
        return None
    _k = max(1, merge_buy_k(_name, _star, bench, deployed, shop))
    for _ in range(_k):
        bench.append(BenchSlot(kind='unit', unit=Unit(
            char_id=_name, star=_star)))
    _merge_bench(bench, deployed)   # 全场域(3合1 是全场)
    del bench[BENCH_CAPACITY:]
    return _k
