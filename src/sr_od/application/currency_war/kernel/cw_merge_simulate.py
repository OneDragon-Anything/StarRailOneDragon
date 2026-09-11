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
   BenchChar.equips 原样继承,不做类别分流(分流是佩戴决策域)。

与 ``cw_state._merge_bench`` 的关系:_merge_bench 是 tracked 侧既有不动点
合并(语义同源),本引擎在其规则上增加**合成链记录**(每级 (星级, 落点,
继承装备))+ 满栏自动多买张数,供期望态对账逐级核对(对账五分类之
「合成落点/星级不符」的期望值来源)。两实现的规则若漂移,以 merge_
mechanics 为准修齐(单一语义源,双载体是 tracked 原地推进 vs 期望态
纯函数的不同形态需要)。

恒成立不变量(EXPECTED_STATE §P2 批注 5):合成后「场上同名同星 ≤1」
——本引擎出参断言,违例即抛(模型错当场暴露,不进对账静默)。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from sr_od.application.currency_war.kernel.cw_board_state import (
    ShopCard as _ContainerShopCard,
)
from sr_od.application.currency_war.kernel.cw_board_state import (
    shop_cards_to_legacy,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    BenchChar,
    bench_place,
    merge_buy_completes,
    merge_buy_k,
    same_star_count,
)


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
    """merge_simulate 出参:终态 + 合成链 + 实际购入张数。"""
    bench_after: list[BenchChar | None]
    deployed_after: list[BenchChar | None]
    chain: list[MergeStep]
    buy_k: int               # 实际购入张数(含满栏自动多买;0 = 满栏且不可触发 → 拒买)
    multi_buy: bool = False  # 满栏自动多买是否发生(buy_k > 请求张数)
    #: 满栏多买 + 合成腾槽后仍无处安放的散牌(merge_mechanics §2.5 已知
    #: 建模缺口;对账只评 1-9 槽,本列表供证据落证,不抛)
    overflow: list[BenchChar] = field(default_factory=list)


def _identity_of(bc: BenchChar | None) -> tuple[str, int]:
    return ((getattr(bc, 'char_id', '') or ''), int(getattr(bc, 'star', 1) or 1))


def merge_simulate(bench: list[BenchChar | None],
                   deployed: list[BenchChar | None],
                   name: str, star: int, k: int = 1,
                   in_shop_count: int | None = None) -> MergeSimResult:
    """买牌 (name, star, 请求张数 k) 的合成终态推演(纯函数;不改入参)。

    - 常态:逐张落入备战空槽(§1 最左空位)→ 不动点合并;
    - 满栏:仅当本次购买能触发合成(``merge_buy_completes``)才放行,
      自动多买 k = ``min(店内张数, 3 − 已有 mod 3)``(§2.5;in_shop_count
      缺省按 3-mod 保守取,调用方有店内真值时显式传);
    - 合成链逐级记录(落点/继承);出参断言「场上同名同星 ≤1」。

    名称/星级未知(name 空)→ 原样返回零推进(宁缺勿造,与买牌期望态
    通道同口径)。
    """
    bench_t: list[BenchChar | None] = [deepcopy(b) for b in (bench or [])]
    while len(bench_t) < BENCH_CAPACITY:
        bench_t.append(None)
    dep_t: list[BenchChar | None] = [deepcopy(d) for d in (deployed or [])]
    chain: list[MergeStep] = []
    overflow: list[BenchChar] = []
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
        if len([b for b in bench_t if b is not None]) >= BENCH_CAPACITY:
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
            bc = BenchChar(slot=0, char_id=name, star=star_n,
                           position_pref='back')
            if bench_place(bench_t, bc) is None:
                overflow.append(bc)   # 满栏暂溢出(合成腾槽后再归位)
    # 不动点合并(逐级记录链;分组键 = 同名同星,全域 bench∪deployed∪溢出
    # ——满栏多买的第 3 张在溢出表里,必须进合成池,否则合成永不触发)
    while True:
        merged = False
        scan = [b for b in bench_t if b is not None] \
            + [d for d in dep_t if d is not None] + list(overflow)
        for bc in scan:
            if not bc.char_id:
                continue
            group = [x for x in scan
                     if x.char_id == bc.char_id and x.star == bc.star]
            if len(group) < 3:
                continue
            take = group[:3]
            # 载体:含场上 → 场上那个同星位置;全备战(含溢出件时溢出件
            # 记入溢出表,落点语义以 bench 槽位归位后为准)→ take[0]
            #(扫描序 = bench 槽位升序,即最左)
            dep_idx = next((i for i, d in enumerate(dep_t)
                            if any(x is d for x in take)), None)
            if dep_idx is not None:
                carrier = dep_t[dep_idx]
                landing_kind, landing_slot = 'deployed', dep_idx
            else:
                carrier = take[0]
                if carrier in overflow:
                    landing_kind, landing_slot = 'bench', 0   # 溢出件归位后定槽(对账校准项)
                else:
                    landing_kind = 'bench'
                    landing_slot = (bench_t.index(carrier) + 1)   # 物理槽位 1-9
            inherited: list[str] = []
            for x in take:
                if x is carrier:
                    continue
                inherited += list(getattr(x, 'equips', None) or [])
                # 对象身份删除(dataclass 值相等会让 `is not` 判断失效,
                # 对象身份唯一可行——同 compute/merge 既有口径)
                if x in overflow:
                    overflow.remove(x)
                elif any(x is b for b in bench_t):
                    bench_t[bench_t.index(x)] = None
                else:
                    _i = next(i for i, d in enumerate(dep_t) if d is x)
                    dep_t[_i] = None
            chain.append(MergeStep(name=carrier.char_id, from_star=carrier.star,
                                   to_star=carrier.star + 1,
                                   landing_kind=landing_kind,
                                   landing_slot=landing_slot,
                                   inherited_equips=inherited))
            carrier.star += 1
            carrier.equips = list(getattr(carrier, 'equips', None) or []) + inherited
            merged = True
            break   # 重扫(结构已变)
        if not merged:
            break
    # 溢出归位:合成腾出的空槽优先(§2.5 满栏购买先腾后落)
    still_overflow: list[BenchChar] = []
    for bc in overflow:
        if bench_place(bench_t, bc) is None:
            still_overflow.append(bc)
    # 恒成立不变量(§P2 批注 5):场上同名同星 ≤1
    dep_keys = [_identity_of(d) for d in dep_t if d is not None and d.char_id]
    if len(dep_keys) != len(set(dep_keys)):
        raise AssertionError(
            f'merge_simulate 不变量违例:场上同名同星 >1({dep_keys})')
    return MergeSimResult(bench_after=bench_t, deployed_after=dep_t,
                          chain=chain, buy_k=eff_k, multi_buy=multi_buy,
                          overflow=still_overflow)


def field_family_of(path: str) -> str:
    """路径 → 字段族(覆盖点可信门过滤用;EXPECTED_STATE §2 字段族口径)。"""
    head = (path or '').split('.', 1)[0]
    if head in ('tracked_bench_chars', 'tracked_deployed', 'bench', 'deployed'):
        return 'tracked'
    return head or 'unknown'


def same_star_count_public(name: str, star: int,
                           bench: list[BenchChar | None],
                           deployed: list[BenchChar | None]) -> int:
    """同星计数透出(测试/对账便利;单一源仍是 cw_state.same_star_count)。"""
    return same_star_count(name, star, bench, deployed)
