"""阵型层 v0(08 号提案;ADR-0165;2026-08-16):敌条件化槽位级排布。

**诊断(08 号)**:上阵「组合」(上谁)有整套决策,「排列」(放哪)只是 position_pref 行偏好
+按序填槽的**副产品**;但游戏机制里槽位/前后台是有数值语义的一等量(词缀 ~9 条显式
槽位/整排语义:灼热轰炸=前台第一位仇恨集火/前后台熄火系=整排锁伤;增强侧 1 号位显式绑定:
全队的希望/风暴骑士/应援团后排≥4)。**06 号搁置对位优化的前提「敌方信息暂无观测源」经
核实不成立 —— 词缀 state.enemy_affixes/效果原文注册表/已持增强效果全在生产管线里**,
缺的只是消费端。cw_comps 注释把灼热轰炸归「无交互」正是阵型层不存在的化石证据。

**v0 落地**(规则表,机制原文落地零学习;提案 §2.2):
- ``decide_formation(units, affixes, held_augments)``:槽位分配(谁前排/谁 1 号位/后排人数
  硬约束);规则只抄效果原文语义,不做推断;
- 无阵型语义词缀/增强 → **退化为现状行为(先验填序)** —— 关掉规则=与现状全同(对拍锚点);
- 排级响应(熄火系→输出去另一排)/1 号位响应(灼热轰炸→最扛者坐)/增强条件硬约束
  (应援团→后排≥4)。

F1 止损门(影响量级审计)与影子接线(PrepDirector 事件点重排)为后续;纯函数 + 离线可测。
"""
from __future__ import annotations

from dataclasses import dataclass

# ===== 词缀→阵型规则(效果原文落地;只抄显式陈述的槽位/整排语义) =====
# row_lock: 'front'|'back' —— 「X 熄火」在 → 输出尽量去另一排
ROW_LOCK_AFFIXES: dict[str, str] = {
    '前台熄火': 'front',
    '后台熄火': 'back',
    '前后台熄火': 'both',   # 两排都锁 → 无处可避,不触发排级响应
}
# slot_aggro: 前台第一位仇恨集火(灼热轰炸)→ 1 号位放最扛的
SLOT_AGGRO_AFFIXES: tuple[str, ...] = ('灼热轰炸',)
# 前台负面词缀(受击/禁锢/治疗减半类)→ carry 避前排
FRONT_HOSTILE_AFFIXES: tuple[str, ...] = ('坠入陷阱', '重症难题', '正当防卫')
# 增强阵型条件(已持 → 硬约束):应援团=后排至少 4 人
AUGMENT_FORMATION_REQ: dict[str, tuple[str, int]] = {
    '应援团': ('back_min', 4),
}


@dataclass
class FormationPlan:
    """阵型输出:排分配 + 1 号位指定 + 触发理由(决策迹)。"""
    front: list[str]          # 前排角色名(有序,首位=1 号位)
    back: list[str]
    reasons: list[str]

    def slot(self, name: str) -> tuple[str, int] | None:
        if name in self.front:
            return ('front', self.front.index(name) + 1)
        if name in self.back:
            return ('back', self.back.index(name) + 1)
        return None


def _is_front_prior(u: dict) -> bool:
    return (u.get('position_pref') or u.get('pref') or 'back') == 'front'


def _toughness(u: dict) -> float:
    """粗抗性分(坦克>辅助>输出;星级加权)。v0 不学,只做排序键。"""
    base = {'坦克': 3.0, '护盾': 2.5, '治疗': 2.0, '辅助': 1.5, '输出': 1.0}
    t = str(u.get('char_type') or u.get('type') or '输出')
    b = next((v for k, v in base.items() if k in t), 1.0)
    return b * (u.get('star') or 1)


def _is_carry(u: dict) -> bool:
    return bool(u.get('is_carry') or str(u.get('char_type') or '') .startswith('输出'))


def decide_formation(units: list[dict], affixes: list[str] | None = None,
                     held_augments: list[str] | None = None) -> FormationPlan:
    """敌条件化槽位分配(v0 规则表)。

    units: [{name, position_pref, char_type, star, is_carry?}];affixes=本局词缀;
    held_augments=已持增强名。无阵型语义触发 → 先验填序(=现状行为,对拍锚点)。
    """
    affixes = affixes or []
    held = held_augments or []
    reasons: list[str] = []

    # 1) 增强硬约束:应援团 → 后排 ≥4(8 人板 4+4 不保证自然满足,显式调配)
    back_min = 0
    for aug, (kind, n) in AUGMENT_FORMATION_REQ.items():
        if aug in held and kind == 'back_min':
            back_min = n
            reasons.append(f'增强[{aug}]硬约束:后排≥{n}')

    # 2) 排级响应:熄火系 → 输出尽量去另一排;前台负面 → carry 避前排
    lock_rows = {ROW_LOCK_AFFIXES[a] for a in affixes if a in ROW_LOCK_AFFIXES}
    front_hostile = any(a in FRONT_HOSTILE_AFFIXES for a in affixes)
    aggro1 = any(a in SLOT_AGGRO_AFFIXES for a in affixes)
    for a in affixes:
        if a in ROW_LOCK_AFFIXES:
            reasons.append(f'词缀[{a}]:输出避{ROW_LOCK_AFFIXES[a]}排')
        if a in FRONT_HOSTILE_AFFIXES:
            reasons.append(f'词缀[{a}]:carry 避前排')
        if a in SLOT_AGGRO_AFFIXES:
            reasons.append(f'词缀[{a}]:1号位放最扛者')

    # 3) 分排(先验为底,规则调整)
    front = [u for u in units if _is_front_prior(u)]
    back = [u for u in units if not _is_front_prior(u)]

    def _to_row(u: dict, prefer_back: bool) -> None:
        """把 u 从当前排挪到目标排(容量内)。"""
        nonlocal front, back
        if prefer_back and u in front and len(back) < 6:
            front.remove(u)
            back.append(u)
        elif not prefer_back and u in back and len(front) < 4:
            back.remove(u)
            front.append(u)

    # 熄火响应:输出移向未锁的排(both 锁/两排都锁时跳过)
    for u in units:
        if not _is_carry(u):
            continue
        if lock_rows == {'front'} or lock_rows == {'both'} and 'front' in lock_rows and len(lock_rows) == 1 and False:
            pass
        if 'front' in lock_rows and 'back' not in lock_rows:
            _to_row(u, prefer_back=True)
        elif 'back' in lock_rows and 'front' not in lock_rows:
            _to_row(u, prefer_back=False)
        elif front_hostile and _is_carry(u):
            _to_row(u, prefer_back=True)

    # 后排下限
    while back_min and len(back) < back_min and front:
        cand = min(front, key=_toughness)   # 挪最扛的去补后排
        front.remove(cand)
        back.append(cand)

    # 4) 1 号位(前排首位)排序
    if aggro1 and front:
        front.sort(key=lambda u: -_toughness(u))       # 最扛者坐 1 号位
    else:
        front.sort(key=lambda u: (-_toughness(u),))    # 无 aggro 也按韧性稳定排(可复现)
    back.sort(key=lambda u: (-_toughness(u),))

    return FormationPlan(front=[u['name'] for u in front],
                         back=[u['name'] for u in back],
                         reasons=reasons or ['无阵型语义词缀/增强 → 先验填序(现状行为)'])
