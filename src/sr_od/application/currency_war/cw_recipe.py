"""过渡配方一等公民模型(r100;user_playstyle [20]-[23]/[26] 定稿模型落码)。

不变量:**P1 双轨期,板面(买/上/卖)只由过渡配方驱动;终局件只囤不上场;
终局线 P1 内冻结换线(定义型 augment 除外)。**

架构:双 slot 解耦——
- ``session.transition_framework``(已有):过渡框架(仙舟/列车,pick_framework 滞后选择)
- ``session.target_comp``:终局线(P1 内冻结;CommitSignals 定型/进 P2 解锁)
- 决策中心(plan/deploy/骨架门)在双轨期拿到的 ``target_comp`` = **本模块的配方伪 comp**
  (RecipeComp:以框架羁绊为 form_tiers,TRANSITION_PACK carry/partial 为 core)——
  消费方零改动,评分自动转向配方完成度(缺什么买什么)。

配方完成度即 P1 胜利条件(user_playstyle[20]:过渡框架就是 P1 的通关阵容);
交接(P1 末/P2):drop 件卖、carry 件继承进终局(plaza 数据:三月七/千冶刃/
姬子/花火 Final 保留 36-64%)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_comps import Comp
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_transition import TRANSITION_PACK

# 配方伪 comp 注册表(框架 → Comp;core = 该框架 carry+partial 件;form_tiers = 配方目标档)。
# ⚠️ core 含 partial(爻光/瓦尔特/腾荒)不含 drop(卡芙卡/椒丘 = 应急战力件,买了就上但不追)。
# form_tiers:仙舟 = 3仙舟(攻略口径 3仙舟+2DOT 的主羁绊档;DOT 由 flows 自然带);
#             列车 = 4列车(数据口径主流档)。
_RECIPES: dict[str, Comp] = {
    '仙舟': Comp(
        name='过渡·仙舟配方', factions=['仙舟'],
        core_chars=[n for n, (fw, tier) in TRANSITION_PACK.items()
                    if fw == '仙舟' and tier in ('carry', 'partial')],
        form_tiers={'仙舟': 3},
        strength='A', form_difficulty='easy',
    ),
    '列车': Comp(
        name='过渡·列车配方', factions=['列车同行'],
        core_chars=[n for n, (fw, tier) in TRANSITION_PACK.items()
                    if fw == '列车' and tier in ('carry', 'partial')],
        form_tiers={'列车同行': 4},
        strength='A', form_difficulty='easy',
    ),
}


def recipe_comp(framework: str) -> Comp | None:
    """框架 → 配方伪 comp(未定框架返 None,消费方退现行为)。"""
    return _RECIPES.get(framework)


def recipe_char_wanted(char_id: str, framework: str) -> bool:
    """该角色是否当前配方的目标件(carry/partial/drop 全算——drop 是应急战力,
    在店且金宽时也买;但「追买/刷新找它」只对 carry/partial)。"""
    ent = TRANSITION_PACK.get(char_id)
    if ent is None:
        return False
    fw, _tier = ent
    return fw == framework or fw == '通用'


def decision_target(session, state: GameState) -> Comp | None:
    """决策中心取 target 的**单一入口**(r100):双轨期喂配方伪 comp,否则喂终局。

    用法:update_target/decide_prep 处把 ``session.target_comp`` 的直接读换成本函数
    (仅决策路径;遥测/结算 tag 仍读原 target_comp 记终局线名)。
    """
    if getattr(state, 'dual_track_phase', False) and getattr(session, 'transition_framework', ''):
        rc = _RECIPES.get(session.transition_framework)
        if rc is not None:
            return rc
    return getattr(session, 'target_comp', None)
