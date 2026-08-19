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
# ⚠️ core 含 partial(爻光/缇宝/符玄)不含 drop(卡芙卡/椒丘 = 应急战力件,买了就上但不追;
# 瓦尔特/腾荒 r100 已从 TRANSITION_PACK 移除,勿引用)。
# form_tiers:仙舟 = 3仙舟(攻略口径 3仙舟+2DOT 的主羁绊档;DOT 由 flows 自然带);
#             列车 = 4列车(数据口径主流档);量子 = 3量子+2贝(r102)。
_RECIPES: dict[str, Comp] = {
    '仙舟': Comp(
        name='过渡·仙舟配方', factions=['仙舟'],
        core_chars=[n for n, (fw, tier) in TRANSITION_PACK.items()
                    if fw == '仙舟' and tier in ('carry', 'partial')],
        form_tiers={'仙舟': 3},
        strength='A', form_difficulty='easy',
        # r100 审计必修②:过渡期站位(爻光必后台,ADR-0139 规则住在终局 comp,
        # 配方伪 comp 需自带;漏了 → _pick_deploy_row 落 position_pref 兜底)
        char_positions={'爻光': 'back'},
    ),
    '列车': Comp(
        name='过渡·列车配方', factions=['列车同行'],
        core_chars=[n for n, (fw, tier) in TRANSITION_PACK.items()
                    if fw == '列车' and tier in ('carry', 'partial')],
        form_tiers={'列车同行': 4},
        strength='A', form_difficulty='easy',
    ),
    # r102 量子框架(希儿线统一化:walkin 特例通道删除,量子=第三过渡配方;
    # 「过渡=终局雏形」由统一公式自然表达——转变成本 0,定型时恒等衔接)
    '量子': Comp(
        name='过渡·量子配方', factions=['量子同频', '贝洛伯格'],
        core_chars=[n for n, (fw, tier) in TRANSITION_PACK.items()
                    if fw == '量子' and tier in ('carry', 'partial')],
        form_tiers={'量子同频': 3, '贝洛伯格': 2},
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


# r102 统一化(用户定调):walkin 特例通道**整体删除**——希儿量子并入第三过渡配方
# (量子),「过渡=终局雏形」由统一公式自然表达:框架计数(量子件持有)决定配方选择,
# 策略/环境加分统一走 env/augment affinity,定型时转变成本≈0 → 恒等衔接。
# 删除物:WALKIN_ALLOWED_COMPS 白名单 / _cheap_carry_walkin 判据 / walkin_latched
# 滞回 / decision_target 优先级分支——全部是为特例服务的复杂度。
# (r100f/g/h 教训留 git 历史:特例通道引入触发面失控(局21 散板)、滞回缺失
# (拆雏形)两个 bug 各修一轮——统一框架一次性消解。)


def decision_target(session, state: GameState) -> Comp | None:
    """决策中心取 target 的**单一入口**(r100;消费方零改动)。

    用法:update_target/decide_prep 处把 ``session.target_comp`` 的直接读换成本函数
    (仅决策路径;遥测/结算 tag 仍读原 target_comp 记终局线名)。

    双轨期(配方驱动):框架已定 → 配方伪 comp(仙舟/列车/量子三选一,
    pick_framework 按持有计数+portal 偏置选);无框架 → 终局 comp(散件口径)。
    非双轨(定型/P2+):终局 comp。

    r102:量子配方=希儿线的过渡形态;终局衔接走统一公式——CommitSignals 定型时,
    量子板面→希儿量子 final 转变成本≈0(板面即雏形),env/augment 的量子向加分
    (量子契约/量子星徽/贝概念股)同时抬高配方选择与终局选择。
    """
    if getattr(state, 'dual_track_phase', False):
        fw = getattr(session, 'transition_framework', '')
        if fw:
            rc = _RECIPES.get(fw)
            if rc is not None:
                return rc
    return getattr(session, 'target_comp', None)
