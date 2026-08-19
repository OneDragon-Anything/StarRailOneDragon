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


def _cheap_carry_walkin(target: Comp | None, state: GameState) -> bool:
    """r100f 模式B判据:终局线便宜 carry 已到手 → 过渡=终局雏形,开局直接走本线。

    plaza 二次精读实证(per_comp_transition.md 总纲):希儿(3费量子,48帖 Early 69%
    贯穿 0.70)/黄泉(3费巡海 0.75)/姬子(3费列车 0.60,混合)/万敌(1费夜神 0.63)
    ——本线 core ≤3 费开局就在商店池,「开局拿缇宝花火和希儿组3量子」零切换成本。
    判据:终局线 ≥2 个 core ≤3费(雏形羁绊可早期成型)**且已持有 ≥1**(开局拿到
    便宜 carry = 走本线的触发信号);贵 carry 线(Archer/瓦尔特 5费)永远不满足
    → 自然落回通用配方(模式A)。
    """
    if target is None or not target.core_chars:
        return False
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    cheap = [c for c in target.core_chars
             if getattr(CHARACTERS.get(c), 'cost', 9) <= 3]
    if len(cheap) < 2:
        return False
    owned = {getattr(bc, 'char_id', '') for bc in (*state.deployed, *state.bench)}
    return any(c in owned for c in cheap)


def decision_target(session, state: GameState) -> Comp | None:
    """决策中心取 target 的**单一入口**(r100):双轨期按四路线喂决策对象。

    用法:update_target/decide_prep 处把 ``session.target_comp`` 的直接读换成本函数
    (仅决策路径;遥测/结算 tag 仍读原 target_comp 记终局线名)。

    双轨期优先级(r100f 定稿,per_comp_transition.md 三模式总纲):
    1. **模式B 便宜 carry 雏形**:终局线 core ≤3费×2 且已持有 1+(希儿量子类)→
       直接喂终局 comp(买本线件即过渡,零切换;modeA 贵线永不触发);
    2. **模式A 通用配方**:框架已定 → 配方伪 comp(仙舟3/列车4;贵 carry 线的
       通用过渡包「3仙舟2DOT 扛 P1,P2 一波换」);
    3. 无框架无雏形 → 终局 comp(散件口径)。
    非双轨(定型/P2+):终局 comp。
    """
    if getattr(state, 'dual_track_phase', False):
        _tgt = getattr(session, 'target_comp', None)
        if _cheap_carry_walkin(_tgt, state):
            return _tgt
        fw = getattr(session, 'transition_framework', '')
        if fw:
            rc = _RECIPES.get(fw)
            if rc is not None:
                return rc
    return getattr(session, 'target_comp', None)
