"""货币战争 **后排槽位布局**(cap 差驱动;ADR-0385 布局模型勘误,2026-08-26)。

机制(用户口述权威,2026-08-26 run 26 崩坏局后澄清 + 同日量化公式追加;
docs/game/currency_war/research/board_structure.md):
- **等级只定上场人数 cap,不定格子数**;正常恒 前台 4 格 + 后台 6 格;
- **后台格数 = 6 + (cap − level)**(口述公式):钻石/召唤物使 cap 超过 level,
  差值即后台扩展量——diff 0 → 6 格基线;diff ≥2 → 8 格(393-1529 带,狸猫局
  交互实拍,screen_info ``后排8槽-1..8``);diff==1(钻石+1)→ 7 格**档未建档**,
  保守退 8 格超集 + 留证(见 :func:`note_7slots_pending`)。
- 旧 level 驱动模型(ADR-0281「level≥7→8 格」)**归因错误**(其实证局狸猫局
  本身带召唤物=cap 差,不是 level),本模块勘误;level 只进 cap 板满门,
  不进布局选档。run 26(lv8 无召唤物局)按 8 格坐标拖不存在的 7/8 号格 +
  幻影空位把部署卡死在 bench = 崩坏根因①。

选档单一入口 :func:`select_back_layout`(消费方:deploy_bench 拖拽坐标 /
``cw_identity_obs.read_deployed_chars`` 槽位读取 / battle_prep_recognizer
后排装备槽):cap 源 = ``cw_observation.read_deploy_cap``(paddle 直读权威);
level 源 = 显式参或 session 等级链(单调链防毒化)。任一读不到 → diff 按 0
(退 6 格基线,失败安全侧 = run 26 崩坏形态的反向)。

单一真相源 = screen_info(6 槽 = ``后排-1..6``;8 槽 = ``后排8槽-1..8``)。
旧 9/10/11 档是循环论证幻影(ADR-0281),已删,勿再登记。
系统单位恒最右模型与布局自检(``cw_identity_obs.check_system_unit_layout``)
保留作交叉验证(公式选档与画面不符时留 layout_mismatch 证据)。
"""
from __future__ import annotations

from one_dragon.base.geometry.rectangle import Rect

#: 槽数 → screen_info 布局前缀(6 槽 = 基线「后排-N」;8 槽 = 「后排8槽-N」)。
#: ⚠️ 9/10/11 档是循环论证幻影(ADR-0281),已删;7 格待 diff==1 局交互实锤后
#: 补档(upsert 后排7槽-1..7 + 此处登记,届时 :func:`note_7slots_pending`
#: 自然不再触发)。
_LAYOUT_PREFIX: dict[int, str] = {
    6: '后排',
    8: '后排8槽',
}

#: 基线后台格数(口述:正常恒 前台 4 + 后台 6)
_BACK_SLOTS_BASE: int = 6

#: cap 差域上界(``cw_observation.DEPLOY_CAP_MAX_DIFF`` 同源;实机语料未见 >2)
_CAP_DIFF_MAX: int = 2

#: 后排 y 带(所有布局共用;槽 rect 高约 600-739)
_BACK_Y1, _BACK_Y2 = 600, 739

# 7 格留证节流(300s/源)与选档日志去重(值不变不重复打)
_pending_note_ts: dict[str, float] = {}
_last_sel_log: tuple[int, int, object, object] | None = None


def _layout_prefixes() -> dict[int, str]:
    """screen_info 里实际存在哪些布局档(静态表;screen_info 变更走 CRUD 后同步登记)。"""
    return dict(_LAYOUT_PREFIX)


def back_slots_from_cap_diff(diff: int) -> int:
    """口述公式:后台格数 = 6 + (cap − level)(纯函数,布局选档锁的测试面)。

    - diff < 0(cap<level 读错族,prep_director 另有 obs_conflict 留证)按 0;
    - diff > 2(``DEPLOY_CAP_MAX_DIFF`` 域外,实机语料未见)按 2 —— 口述公式
      与旧幻影观察自洽:cap9/10/11 的 lv7/8 局 diff ≥2 全部落 8 格档;
    - 公式值未建档(diff==1 → 7 格)→ **保守退 8 格超集**(扩展带读全不丢系统
      单位;拖到不存在的位 8 被游戏拒 = 廉价失败方向)。
    """
    d = 0 if diff < 0 else min(diff, _CAP_DIFF_MAX)
    n = _BACK_SLOTS_BASE + d
    if n in _LAYOUT_PREFIX:
        return n
    return 8   # 7 格档未建档 → 8 格超集(见模块 docstring;留证在调用侧)


def note_7slots_pending(screen, cap, level, source: str) -> None:
    """diff==1(钻石+1)7 格档未建档 → obs_conflict 留证(节流 300s/源;保守按
    8 格超集跑,ADR-0385)。

    采集指引:钻石局(cap=level+1,无召唤物)截备战帧 → 暗框检测 7 格槽位 x →
    拖角色逐位交互实锤 → upsert_screen_area 后排7槽-1..7 → ``_LAYOUT_PREFIX``
    登记 7 → 本函数自然不再触发。best-effort 不抛。
    """
    import time as _time
    try:
        now = _time.monotonic()
        if now - _pending_note_ts.get(source, -1e9) < 300.0:
            return
        _pending_note_ts[source] = now
        from sr_od.application.currency_war.cw_observe import obs_conflict
        obs_conflict(
            'back_7slots_pending', 7, 8, screen,
            verdict=('留证-钻石+1 局(cap=level+1)后台应为 7 格,档未建档'
                     '(保守按 8 格超集跑,ADR-0385;处理:该类局截备战帧,'
                     '暗框检测 7 格槽位 x → 拖角色逐位交互实锤 → '
                     'upsert 后排7槽-1..7 → _LAYOUT_PREFIX 登记 7)'),
            source=source, cap=cap, level=level)
    except Exception:   # noqa: BLE001
        pass


def select_back_layout(ctx, screen, level: int | None = None,
                       cap: int | None = None) -> tuple[int, str]:
    """布局选档单一入口(ADR-0385 口述公式)→ ``(槽数, 布局前缀)``。

    驱动 = 「后台格数 = 6 + (cap − level)」:
    - cap 未传 → ``read_deploy_cap``(paddle 直读权威,X/Y 里的 Y)现读;
    - level 未传 → session 等级链(cw_identity_obs._session_level,单调链防毒化);
    - 任一读不到 → diff 按 0(退 6 格基线;失败安全侧);
    - 公式值未建档(diff==1 → 7 格)→ 8 格超集 + :func:`note_7slots_pending` 留证。

    交叉验证:``check_system_unit_layout``(系统单位恒最右)在读板路径常设对账
    (公式值与画面不符时留 layout_mismatch 证据,公式误读的兜底网)。
    """
    try:
        if level is None or level <= 0:
            from sr_od.application.currency_war.cw_identity_obs import _session_level
            level = _session_level(ctx)
        if cap is None:
            from sr_od.application.currency_war.cw_observation import read_deploy_cap
            cap = read_deploy_cap(ctx, screen)
    except Exception:   # noqa: BLE001  读源失败 → 退基线(失败安全侧)
        cap, level = None, None
    diff = (cap - level) if (cap is not None and level) else 0
    n = back_slots_from_cap_diff(diff)
    if n == 8 and diff == 1:
        note_7slots_pending(screen, cap, level, 'select_back_layout')
    p = _layout_prefixes().get(n, _LAYOUT_PREFIX[_BACK_SLOTS_BASE])
    try:
        global _last_sel_log
        _key = (n, diff, cap, level)
        if _key != _last_sel_log:
            _last_sel_log = _key
            from one_dragon.utils.log_utils import log
            log.info('[cw][layout] 后排选档: %d 格(cap=%s lv=%s diff=%s;'
                     '口述公式 6+(cap-level),ADR-0385)', n, cap, level, diff)
    except Exception:   # noqa: BLE001
        pass
    return n, p


def back_row_slot_rects_ctx(ctx, prefix: str) -> list[tuple[int, Rect]]:
    """按布局前缀从 screen_info 枚举 ``[(slot_idx, rect), ...]``(N 升序至断档)。

    前缀来自 :func:`select_back_layout`(ADR-0385 公式选档);空档 → [](调用方
    退 :func:`fallback_back_slots` 基线)。**别在 6 槽坐标上外插**。
    """
    from sr_od.application.currency_war.cw_identity_obs import _area_rect
    out: list[tuple[int, Rect]] = []
    i = 1
    while True:
        rect = _area_rect(ctx, f'{prefix}-{i}')
        if rect is None:
            break
        out.append((i, rect))
        i += 1
    return out


def fallback_back_slots() -> list[tuple[int, Rect]]:
    """无 ctx/无档时的兜底:静态 6 槽基线(与 screen_info 基线一致的硬拷贝;仅测试用)。"""
    xs = (604, 746, 888, 1032, 1173, 1315)
    half = 71
    return [(i + 1, Rect(x - half, _BACK_Y1, x + half, _BACK_Y2)) for i, x in enumerate(xs)]
