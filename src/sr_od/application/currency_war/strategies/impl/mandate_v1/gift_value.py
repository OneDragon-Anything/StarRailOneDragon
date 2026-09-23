"""赠卡价值(mandate_v1 共用模块;投资环境策略层迁移迭代 design.md §2.5)。

两个口径:
- **具名赠卡**(契约 ×7 + 特邀专家 ×4,登记 = ``cw_investments.ENV_GIFTS``
  留 kernel):档位判定复用 kernel ``cw_comps.gift_hit_tier``(角色在候选套
  中的身份档 = 机制事实判定,按宪法五判据线留 kernel;本模块只做「档→分」
  映射 = 策略立场,design §2.6 表 2)。advisor(付费顾问期权,特邀专家)
  按同档分 × :data:`ADVISOR_DISCOUNT`(「付费期权 < 白得」语义,承载旧
  ``GIFT_FLOOR_ADVISOR_CORE < GIFT_FLOOR_CORE`` 的序);赠卡失格删除:
  白得卡全员集外 → 赠卡分自然 0,**不再把整环境清零**(旧
  ``env-gift-off-universe`` 整体失格规则删除,环境其余成分照常计分,
  design §2.5)。
- **随机阵营赠卡**(概念股「获得【某阵营】角色」):该阵营注册成员
  (``cw_chars.chars_by_faction``)在未排除候选阵容名单
  (core∪shared∪transition)中出现者的档位分**算术平均**(随机发放取无偏
  期望;具名发放取最高档的口径差异 = 确定性赠卡承重面,沿旧机器
  details/env-value-models.md §2.1.2 规则①,非双重标准);无成员在册 → 0。

复用预留(design §2.9):投资策略屏迁移批直接复用具名/随机两口径,
接口本批一次定形。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import chars_by_faction
from sr_od.application.currency_war.kernel.cw_comps import gift_hit_tier
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_GIFTS,
    GiftGrant,
)

#: 赠卡档分(design §2.6 表 2;【拍】形态,初值经落地 3.1 裁决窗过目):
#: - core = 50:白得一条 A 线核心 ≈ 半条 A 线方向分量级;
#: - shared = 20:常用成员;
#: - transition = 5:打工件;
#: - off = 0:无消费方。
#: 键 = ``cw_comps.gift_hit_tier`` 返回档('core'|'shared'|'transition'|'off'),
#: 键完备由 invest_env 构建期校验兜底(四档任一缺键 → import 即炸)。
GIFT_TIER_SCORE: dict[str, float] = {
    'core': 50.0,
    'shared': 20.0,
    'transition': 5.0,
    'off': 0.0,
}

#: advisor 折减(同档分 × 0.5;「付费期权 < 白得」——顾问需再花店价且占
#: 购买预算,价值严格低于同档白得,design §2.5/§2.6 表 2 注)。
ADVISOR_DISCOUNT: float = 0.5


def named_gift_value(env_name: str,
                     evicted: frozenset[str] | set[str]) -> float:
    """具名赠卡分(ENV_GIFTS 在册环境;design §2.5 具名口径)。

    档位 = kernel ``gift_hit_tier``(即时集取最高档、条件集降一档的机器
    事实,evicted 传导免费获得);档→分映射见表 2;advisor 再乘
    ADVISOR_DISCOUNT。非 ENV_GIFTS 环境 → 0(无具名发放)。
    """
    grant = ENV_GIFTS.get(env_name)
    if grant is None:
        return 0.0
    score = GIFT_TIER_SCORE[gift_hit_tier(grant, evicted)]
    if grant.advisor:
        score *= ADVISOR_DISCOUNT
    return score


def random_faction_gift_value(faction: str,
                              evicted: frozenset[str] | set[str]) -> float:
    """随机阵营赠卡分(概念股「获得【某阵营】角色」;design §2.5 随机口径)。

    成员档位判定 = 对单角色合成 ``GiftGrant(chars_immediate=(名,))`` 调
    kernel ``gift_hit_tier``——单角色即时发放的命中档即该角色的最高身份档,
    与 ``cw_comps._char_gift_tier`` 同义,借此复用 kernel 档位机器(禁二次
    推导,契约同其 docstring)。三名单(core∪shared∪transition)皆不在
    (tier='off')的成员不入平均分母;全员集外 → 0(除零防 = 无成员在册)。
    """
    if not faction:
        return 0.0
    evicted = frozenset(evicted)
    scores: list[float] = []
    for member in chars_by_faction(faction):
        grant = GiftGrant(chars_immediate=(member.name,))
        tier = gift_hit_tier(grant, evicted)
        if tier != 'off':
            scores.append(GIFT_TIER_SCORE[tier])
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
