"""货币战争 剩余牌库派生(固定牌库 − 持有;商店发牌与效果随机授予共用的采样空间单一源)。

- 每卡副本数:1/2 费 27、3/4/5 费 9(常量单一源 =
  ``data/cw_shop_odds.py`` 的 ``POOL_COPIES_PER_CARD``;口径出处 =
  ``docs/game/currency_war/research/economy.md`` §1)——3/4/5 费同 9,
  升费换档只换桶归属、副本数不变;
- **专家顾问不入基础牌库**(economy.md §1:专家初始不参与普通商店招募,
  名单权威 = 注册表 ``Character.is_expert``):基础牌库 = 非专家角色 ×
  副本数;解锁入池 = 容器 ``gs.unlocked_experts`` 按名并入
  ``EXPERT_COPIES_ASSUMED`` 副本(待实机核)——解锁写端 = 获得链 advisor
  道(环境/策略)+ 装备通道(cw_gain_chain),本模块只消费;
- **池量按不变量派生**:剩余牌库 = 固定牌库 − 持有副本总数(held 由容器
  bench/deployed 星级派生,Σ 3^(star−1);合成不销毁,2★ 计 3 张/3★ 计
  9 张)。买/卖/合成只改容器持有态,无「卖出回池」可变计数事件;
- **双出口 + 规格授予池**(档过滤与商店过滤解耦,出口共用一次派生无第二实现):
  商店发牌出口 :func:`drawable_names` = 档匹配 ∧ 剩余 >0 ∧ 持有 <9
  (持有某牌 ≥9 张 → 该牌不再进店 = 商店通道定案口径;试用与自有同池
  同计数);效果随机授予出口 :func:`grant_bucket_names` = 档匹配 ∧
  剩余 >0(**不含 ≥9 过滤**——授予通道是否受清空约束无定案,商店口径
  不无据继承,v0 披露随函数申报);规格授予池 :func:`grant_char_pool` =
  RandomCharSpec 域 ∩ 当时牌库(获得链随机赠卡族采样空间,专家随解锁
  态进出——用户裁定 2026-10-28「授予候选 = 当时牌库里存在的角色」)。
- 池构成族突变其余形态(黑塔纪元特殊池/援军类)未建模。人才下沉 2★ 直出
  已建发牌侧翻星腿(kernel/cw_shop_deal,概率注册表
  ENV_SHOP_TWO_STAR_DEAL_PROB = 用户占位)——本模块零改动:2★ 直出改的
  是单次购买副本转移粒度(1→3),池集合与不变量账自动自洽;游戏侧发牌
  扣减/购买扣减的池粒度(1 槽还是 3 副本)未观测,极端失配走守恒破
  raise 响停修因(本模块头既有申报)。

随机量:无(池是派生状态非动作;抽名随机与随机效果收束由消费方覆盖——
效果批采样后经 ``logic_rand_outcome`` 行候校准,本模块只供采样空间查询)。

守恒破显式炸错语义申报:剩余出现负值即 raise(文案 = 「池派生与持有
约束不一致」),跨层后果 = 沿消费链直达运行层、run 停(效果链登记腿
best-effort 不兜容器写)。实机侧 held 为观察容器派生,观测噪声(单位
身份/星级误读)同样可触发;响停修因优于静默夹零(夹零掩盖病灶),语义
按显式暴露接受。豁免:held 中的名不在(基础池 ∪ 解锁专家)时不参与
守恒检查(摸个鱼吧 II/III 等直接赠卡通道给到的单位,其名未解锁入池——
持有真值成立但商店本就不可刷,非守恒破)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    EXPERT_CHARS,
    assert_expert_names,
)
from sr_od.application.currency_war.data.cw_shop_odds import POOL_COPIES_PER_CARD
from sr_od.application.currency_war.kernel.cw_economy import effective_cost
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    RandomCharSpec,
    random_char_pool,
)

#: 专家入池副本数(首版建模假设,标注待核;普通卡 3/4/5 费同为 9)。
EXPERT_COPIES_ASSUMED: int = 9

#: 授予出口 v0 披露键·维度一(未实测):授予采样是否受商店「持有 ≥9
#: 清空」约束——本出口现态 = 不受;效果批消费后由 ``logic_rand_outcome``
#: 行候校准(冶金炉采样池同款先例)。
GRANT_BUCKET_NO_NINE_FILTER_V0: str = 'grant_bucket_no_nine_filter_v0'

#: 授予出口 v0 披露键·维度二(未实测):消费方抽名分布 = **按名均匀**,
#: 非按剩余副本数加权(本出口返回去重名集,不含权重信息)。
GRANT_BUCKET_UNIFORM_BY_NAME_V0: str = 'grant_bucket_uniform_by_name_v0'


def fixed_pool() -> dict[str, int]:
    """基础固定牌库(名 → 副本数;**不含专家顾问**)。

    = 注册表非专家角色 × ``POOL_COPIES_PER_CARD`` 按费取副本。专家顾问
    (``Character.is_expert``)初始不参与普通商店招募(economy.md §1),
    解锁后经 :func:`remaining_pool` 系列从 ``gs.unlocked_experts`` 并入
    ——入池是本局解锁状态的结果,不在纯注册表派生里。纯注册表派生:
    剩余池按名计、费用桶只在查询时现分,档不进本函数签名、gs 不入纯
    派生。
    """
    pool: dict[str, int] = {}
    for name, ch in CHARACTERS.items():
        if ch.is_expert:
            continue
        copies = POOL_COPIES_PER_CARD.get(ch.cost, 0)
        if copies > 0:
            pool[name] = copies
    return pool


def unlocked_expert_copies(gs: GameState) -> dict[str, int]:
    """已解锁专家的入池副本账(名 → ``EXPERT_COPIES_ASSUMED``)。

    数据源 = 容器 ``gs.unlocked_experts``(获得链 advisor 道/装备通道
    写入);成员闭集闸(:func:`assert_expert_names`)在读取口再落一道,
    防越界名静默混池。
    """
    names = tuple(gs.unlocked_experts.value or ())
    assert_expert_names(names)
    return dict.fromkeys(names, EXPERT_COPIES_ASSUMED)


def held_copies(gs: GameState) -> dict[str, int]:
    """持有副本账(名 → Σ 3^(star−1);容器 bench/deployed 星级派生)。

    单一派生口:开局手牌写入 bench 后本函数即有定义,无需可变账本;
    试用与自有角色同池同计数。同名即同档(全场同名角色费用档唯一,
    升费后含商店在架卡一律为新费用档),按名归并即完整账,与档无关。
    """
    held: dict[str, int] = {}
    front, back = deployed_rows_of(gs)
    units = list(bench_units_of(gs)) + [d for d in (*front, *back)
                                        if d is not None]
    for u in units:
        name = str(getattr(u, 'char_id', '') or '')
        if not name:
            continue
        star = max(1, int(getattr(u, 'star', 1) or 1))
        held[name] = held.get(name, 0) + 3 ** (star - 1)
    return held


def _remaining_and_held(gs: GameState, *,
                        include_experts: bool,
                        ) -> tuple[dict[str, int], dict[str, int]]:
    """(剩余池, held) 一次派生(剩余 = 固定 − held;守恒破显式炸错)。

    ``include_experts`` = 是否并入解锁专家(商店发牌出口与效果随机授予
    出口均 True——专家入池时机随容器解锁态,用户裁定 2026-10-28「授予
    候选 = 当时牌库里存在的角色」,见 :func:`grant_char_pool`)。held 中
    不在派生池的名(未解锁直接赠卡单位、cost=0 系统单位)跳过守恒检查。
    """
    fixed = fixed_pool()
    if include_experts:
        fixed.update(unlocked_expert_copies(gs))
    held = held_copies(gs)
    remaining: dict[str, int] = {}
    for name, copies in fixed.items():
        value = copies - held.get(name, 0)
        if value < 0:
            raise ValueError(
                f'牌池守恒破:{name} 剩余 {value} < 0(固定 {copies};'
                '池派生与持有约束不一致)')
        remaining[name] = value
    return remaining, held


def remaining_pool(gs: GameState) -> dict[str, int]:
    """剩余池 = 固定牌库(含解锁专家)− held(不变量派生;负值 = 池守恒
    破,显式炸错)。

    负值出现即池派生与持有约束不一致(实机侧观测噪声亦可触发,跨层
    语义申报见模块头注);静默夹零会掩盖病灶,按显式暴露处置。
    """
    return _remaining_and_held(gs, include_experts=True)[0]


def drawable_names(gs: GameState, cost: int) -> list[str]:
    """某费用档当前可进店名集(商店发牌出口,sim 发牌消费)。

    三条件:费用档匹配(经 :func:`effective_cost` 档感知——银狼LV.999
    升费后当前档 = 容器 ``gs.lv999_cost_tier``,归入新费用档桶;其余角色
    恒等注册表值)∧ 剩余 > 0 ∧ held < 9(持有 ≥9 清空 = 商店发牌过滤
    定案口径;1/2 费 27 副本下 held ≥9 时仍有剩余,两条件不可互替)。

    专家顾问 = 已解锁名按费档自然进本出口(未解锁不在池不可刷,
    economy.md §1 商店招募口径)。
    """
    remaining, held = _remaining_and_held(gs, include_experts=True)
    return sorted(
        name for name, left in remaining.items()
        if left > 0 and held.get(name, 0) < 9
        and effective_cost(gs, name) == cost)


def grant_bucket_names(gs: GameState, cost: int) -> list[str]:
    """某费用档当前可被随机授予名集(效果随机授予出口,效果批消费)。

    两条件:费用档匹配(:func:`effective_cost` 档感知,与商店出口同一
    过滤)∧ 剩余 > 0——**不含**商店「持有 ≥9 清空」过滤(授予通道是否
    受清空约束无定案,商店口径不无据继承)。

    v0 口径双维披露(均未实测,效果批消费后由 ``logic_rand_outcome``
    行候校准,冶金炉采样池同款先例):
    - :data:`GRANT_BUCKET_NO_NINE_FILTER_V0`:是否受 ≥9 清空约束
      (本出口现态 = 不受);
    - :data:`GRANT_BUCKET_UNIFORM_BY_NAME_V0`:抽名分布 = 按名均匀,
      非按剩余副本数加权。

    专家顾问 = 已解锁名随 ``include_experts=True`` 入本出口(用户裁定
    2026-10-28:授予候选 = 当时牌库里存在的角色,与商店出口同一牌库
    时点口径;规格型授予采样见 :func:`grant_char_pool`)。

    调用时序契约(消费者侧):本函数为纯查询、held 仅容器派生——
    「先回归后重抽」定案(2026-09-21)⇒ 消费方必须先把回归/摘除写落
    容器再采样;无工作副本派生入口,工作副本合并范式不适用于本出口。
    """
    remaining, _held = _remaining_and_held(gs, include_experts=True)
    return sorted(
        name for name, left in remaining.items()
        if left > 0 and effective_cost(gs, name) == cost)


def grant_char_pool(gs: GameState, spec: RandomCharSpec) -> list[str]:
    """随机角色授予采样空间 = 规格域 ∩ 当时牌库(获得链 4 采样点消费)。

    基底 = :func:`random_char_pool` 静态派生(注册表 + 开拓者双形态合并,
    不变);叠加牌库时点一致性 = 剔除未解锁专家(用户裁定 2026-10-28
    「按当时牌库里存在的角色决定」):专家入池时机与商店同源
    (economy.md §1 解锁入池),解锁后即入授予候选。环境注册时点解锁
    恒空(解锁通道 = 特邀专家卡/装备分身墨镜族/条件触发,全部晚于环境
    选择)→ 概念股族/人才系候选不含专家;中局通道(boss 腿2/晶矿随机
    羁绊支)随容器现值——已解锁专家可被授予 = 一般原则推论,非实机直接
    证词(logic_rand_outcome ``env_gift_random:`` 行候校准兜底)。

    按名均匀掷骰由消费方承担(消费点 = cw_gain_chain 随机支/deploy-lock
    腿、cw_env_grants boss 腿2/晶矿随机羁绊支);副本数/≥9 过滤语义不在
    本池(与 :func:`grant_bucket_names` 的剩余桶口径分域,两 v0 披露键
    随该出口不随本池)。构建期静态校验(random_char_pool 池非空)为必要
    条件;过滤后空 = 全专家域且未解锁(现库不存在),运行期守卫兜底。
    """
    unlocked = frozenset(gs.unlocked_experts.value or ())
    return [n for n in random_char_pool(spec)
            if n not in EXPERT_CHARS or n in unlocked]
