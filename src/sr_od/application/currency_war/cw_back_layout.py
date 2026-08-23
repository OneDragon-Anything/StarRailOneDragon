"""货币战争 **后排槽位布局**(level 驱动;ADR-0281 布局模型重审,2026-08-23)。

机制(用户口述权威 + 全行签名扫描终判):后排槽数由 **level 驱动**,与 deploy_cap
(宝钻叠加)无关 —— 两帧同 lv7 cap8/9 同为 8 格实证。真值布局:
- lv3-5 → **6 格**(基线 534-1386 带,多局验证,screen_info ``后排-1..6``);
- lv7-8 → **8 格**(393-1529 带,狸猫局交互实拍,screen_info ``后排8槽-1..8``);
- lv6 → 7 格**存在性未知**(待采;按用户模型 7 格时系统单位(狸猫)应在 1174/1316)——
  保守按 6 格跑 + ``obs_conflict`` 留证(见 :data:`_PENDING_7SLOT_LEVELS`)。

**旧 7/9/10/11 档全是幻影**(r84「五组实测」里 cap9/10/11 是把 SIFT 命中往外推网格
上套的循环论证:命中落在 8 格布局内,两种网格编号都解释得通;三触发帧逐格空槽签名
证明 251-393 / 1529-1671 段为无格背景)。幻影 yml area 已删,勿再登记。

**系统单位恒最右模型**(用户口述权威):狸猫(狸小虎/狸小龙)/佩佩等系统召唤单位
恒占布局**最右槽位(们)**、不可拖(cost=0)、布局格数变 → 其 x 跟着最右格移动。
落地:① 布局自检判别器(``cw_identity_obs.check_system_unit_layout``,比空槽签名便宜);
② deploy 重排候选剔除系统单位(deploy_bench,cost==0 守卫)。

**单一真相源 = screen_info**(用户 2026-08-19 定调):6 槽 = ``后排-1..6``;
8 槽 = ``后排8槽-1..8``(狸猫局实拍,交互定名:位1藿藿/位2爻光/位7蓝狸小虎/位8红狸小龙)。
选档:运行时按 level 取布局;查无该档 → 退 6 槽基线 + ``[cw!]`` 告警(现 6/8 都有档,
该分支为未来新档预留)。**别在 6 槽坐标上外插**。
"""
from __future__ import annotations

from one_dragon.base.geometry.rectangle import Rect

#: level → screen_info 布局前缀(6 槽 = 基线「后排-N」;8 槽 = 「后排8槽-N」)。
#: ⚠️ 旧 7/9/10/11 档是循环论证幻影(ADR-0281),已删 —— 7 格存在性待 lv6 采集定,
#: 定了再按交互实锤流程补档(upsert 后排7槽-1..7 + 此处登记)。
_LAYOUT_PREFIX: dict[int, str] = {
    6: '后排',
    8: '后排8槽',
}

#: 7 格存在性待采的 level(ADR-0281):lv6 布局未知 → 保守按 6 格跑 + obs_conflict
#: 留证(采集窗口 = lv6 局截备战帧,按用户模型 7 格时系统单位应在 1174/1316;
#: 交互实锤定档后清空此集合并登记 _LAYOUT_PREFIX)。
_PENDING_7SLOT_LEVELS: frozenset[int] = frozenset({6})

#: 后排 y 带(所有布局共用;槽 rect 高约 600-739)
_BACK_Y1, _BACK_Y2 = 600, 739


def _layout_prefixes() -> dict[int, str]:
    """screen_info 里实际存在哪些布局档(静态表;screen_info 变更走 CRUD 后同步登记)。"""
    return dict(_LAYOUT_PREFIX)


def effective_back_slots(level: int) -> int:
    """后排实际槽数,**level 驱动**(ADR-0281;旧 cap 驱动模型已废)。

    规则:level≤5 → 6 / level≥7 → 8 / level==6 → 暂 6(7 格存在性待采,
    调用方过 :func:`note_pending_7slots` 留证)。cap(宝钻)与布局无关
    (两帧同 lv7 cap8/9 同为 8 格实证;cap 误读不再影响选档)。
    消费方(选档/域检查)统一过此函数。
    """
    if level >= 7:
        return 8
    return 6   # ≤5 → 6;==6 → 保守 6(待采,见 _PENDING_7SLOT_LEVELS)


_pending_note_ts: dict[str, float] = {}


def note_pending_7slots(screen, level: int, source: str, extra=None) -> None:
    """lv6 待采留证(节流 300s/源):7 格存在性未知,保守按 6 格跑(ADR-0281)。

    采集指引(用户模型):7 格存在时系统单位(狸猫)应在 1174/1316(8 格时在
    1316/1458);lv6 局截备战帧 + 系统单位 x 实测即可判定。best-effort 不抛。
    """
    import time as _time
    try:
        if level not in _PENDING_7SLOT_LEVELS:
            return
        now = _time.monotonic()
        if now - _pending_note_ts.get(source, -1e9) < 300.0:
            return
        _pending_note_ts[source] = now
        from sr_od.application.currency_war.cw_observe import obs_conflict
        obs_conflict(
            'back_7slots_pending', level, 6, screen,
            verdict=('留证-lv6 后排 7 格存在性待采(保守按 6 格跑,ADR-0281;'
                     '处理:lv6 局截备战帧,按用户模型 7 格时狸猫应在 1174/1316'
                     '(8 格时 1316/1458);实锤后 upsert 后排7槽-1..7 + '
                     '_LAYOUT_PREFIX 登记 + 清 _PENDING_7SLOT_LEVELS)'),
            source=source, **(extra or {}))
    except Exception:   # noqa: BLE001
        pass


def back_prefix_for_level(level: int) -> tuple[str, int]:
    """level → ``(布局前缀, 槽数)``(无档退基线 ``('后排', 6)``;识别/装备等按前缀+数
    读取的消费方用,如 battle_prep_recognizer 的后排装备槽)。"""
    n = effective_back_slots(level)
    p = _layout_prefixes().get(n)
    return (p, n) if p is not None else ('后排', 6)


def back_row_slot_rects_ctx(ctx, level: int) -> list[tuple[int, Rect]] | None:
    """按 level 从 screen_info 取 ``[(slot_idx, rect), ...]``;无档 → None(调用方退基线)。

    ctx: ``SrContext``(screen_info 已加载)。level = 当前等级(session 单调链
    last_level_obs / last_state.level);槽数 = ``effective_back_slots(level)``。
    """
    prefix = _layout_prefixes().get(effective_back_slots(level))
    if prefix is not None:
        from sr_od.application.currency_war.cw_identity_obs import _area_rect
        out: list[tuple[int, Rect]] = []
        i = 1
        while True:
            rect = _area_rect(ctx, f'{prefix}-{i}')
            if rect is None:
                break
            out.append((i, rect))
            i += 1
        if out:
            return out
    # 无档:[cw!] 告警(可检索)。现 6/8 都有档,该分支为未来新档预留(如 lv6 实锤
    # 7 格前的过渡态理论不触发——lv6 保守 6 有档;真触发 = 布局表与 screen_info
    # 失配,按 ADR-0281 交互实锤流程补档)。本函数只返 None 退基线。
    try:
        if level and effective_back_slots(level) not in _layout_prefixes():
            from one_dragon.utils.log_utils import log
            log.warning('[cw!][layout] 后排 %d 槽布局未建档(退 6 槽基线,识别/拖拽将错位;'
                        '补档:交互实锤 → upsert 后排%d槽-1..%d → _LAYOUT_PREFIX 登记)',
                        effective_back_slots(level), effective_back_slots(level),
                        effective_back_slots(level))
    except Exception:   # noqa: BLE001
        pass
    return None


def fallback_back_slots() -> list[tuple[int, Rect]]:
    """无 ctx/无档时的兜底:静态 6 槽基线(与 screen_info 基线一致的硬拷贝;仅测试用)。"""
    xs = (604, 746, 888, 1032, 1173, 1315)
    half = 71
    return [(i + 1, Rect(x - half, _BACK_Y1, x + half, _BACK_Y2)) for i, x in enumerate(xs)]
