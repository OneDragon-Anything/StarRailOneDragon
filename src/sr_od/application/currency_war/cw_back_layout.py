"""货币战争 **后排槽位布局**(双通道对账:公式 + CV 实测;ADR-0385,
2026-08-26 W209 事故响应批 + 同日口述双通道指令修订)。

机制(用户口述权威,docs/game/currency_war/research/board_structure.md):
- **等级只定上场人数 cap,不定格子数**;正常恒 前台 4 格 + 后台 6 格;
- **后台格数 = 6 + (cap − level)**(口述公式):钻石/召唤物使 cap 超过 level,
  差值即后台扩展量——diff 0 → 6 格基线;diff ≥2 → 8 格(393-1529 带,狸猫局
  交互实拍,screen_info ``后排8槽-1..8``);diff==1(钻石+1)→ 7 格**档未建档**,
  保守退 8 格超集 + 留证(见 :func:`note_7slots_pending`)。

**双通道对账**(口述指令 2026-08-26 追加,两通道都做):

1. **公式通道**::func:`back_slots_from_cap_diff`「6+(cap−level)」——cap =
   ``read_deploy_cap``(paddle 直读权威),level = session 等级链(单调链防毒化)。
   「钻石局检测」由此消解(无需识别钻石图标,两 OCR 读数相减即扩展量)。
2. **CV 通道**::func:`cv_back_slots` 画面实测——后排 y 带槽位存在性签名
   (空槽暗框 vs 无格背景的灰度 std 判别,标定见 :data:`_CV_SLOT_STD_MIN`)。
3. **对账语义**(口述裁决):一致 → 公式值;**不一致 → CV 实测值**
   (画面事实 > 推导——公式依赖的两个 OCR 读数可能错)+
   ``obs_conflict('back_layout_channel_conflict')`` 留证(带两值,便于判读);
   CV 不可判(帧越界/锚缺失,如 overlay 遮挡/非备战帧)→ 退公式值
   (公式 = CV 偶发失效时的兜底 + 低成本快速路径)。
4. 7 格档未建档 → 8 格超集(读全扩展带;拖到不存在格被游戏拒 = 廉价失败
   方向)+ :func:`note_7slots_pending` 采集留证。

旧 level 驱动模型(ADR-0281「level≥7→8 格」)**归因错误**(其实证局狸猫局
本身带召唤物=cap 差,不是 level),本模块勘误;level 只进 cap 板满门,
不进布局选档。run 26(lv8 无召唤物局)按 8 格坐标拖不存在的 7/8 号格 +
幻影空位把部署卡死在 bench = 崩坏根因①。

单一真相源 = screen_info(6 槽 = ``后排-1..6``;8 槽 = ``后排8槽-1..8``)。
旧 9/10/11 档是循环论证幻影(ADR-0281),已删,勿再登记;「后排7槽-P2开局局」
实拍帧经 CV 复核两端扩展位均为背景(旧 7 槽观察同属幻影,实为 6 格)。
系统单位恒最右模型与布局自检(``cw_identity_obs.check_system_unit_layout``)
保留作交叉验证。CV 通道与该自检同为 1080p 原生坐标(项目基准,同款假设)。
"""
from __future__ import annotations

from one_dragon.base.geometry.rectangle import Rect

#: 槽数 → screen_info 布局前缀(6 槽 = 基线「后排-N」;8 槽 = 「后排8槽-N」)。
#: ⚠️ 9/10/11 档是循环论证幻影(ADR-0281),已删;7 格待交互实锤后补档
#: (upsert 后排7槽-1..7 + 此处登记,届时 :func:`note_7slots_pending`
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

# 7 格留证/双通道冲突节流(300s/源)与选档日志去重(值不变不重复打)
_pending_note_ts: dict[str, float] = {}
_channel_conflict_ts: dict[str, float] = {}
_last_sel_log: tuple | None = None

# ===== CV 通道:槽位存在性签名(ADR-0385 双通道件2) =====

#: 候选槽中心 x(8 格档全列;6 格基线 = 其中 606..1316 六列——两档共享中段,
#: 差异只在两端扩展格 464/1458;6 格档 xs 604..1315 与 8 格中段 606..1316
#: 差 ≤2px,±71 半格宽裁切覆盖)。1080p 原生坐标(同 check_system_unit_layout
#: 假设;非 1080p 帧 :func:`cv_back_slots` 越界守卫返 None)。
_CV_CAND_XS: tuple[int, ...] = (464, 606, 748, 889, 1031, 1174, 1316, 1458)
#: 两端扩展位(6 格态此二位 = 无格背景;有扩展才呈现槽框/立绘)
_CV_EXTRA_XS: tuple[int, ...] = (464, 1458)
#: 锚位(共享中段两列)——任一锚无槽签名 = 帧不可用(overlay/非备战态)→ None
_CV_ANCHOR_XS: tuple[int, ...] = (606, 1031)
#: 裁切半宽(槽 rect 宽 142 的半径,同既有槽建模)
_CV_HALF: int = 71
#: 槽存在判据:裁切灰度 std ≥ 本值。标定(W209 探针,sr-od-test 6 帧 6 格态
#: ×2 端扩展位 = 12 个背景样本 std ≤ 2.9;空槽暗框 std ≥ 10.5,占位立绘
#: 50-67;「后排7槽-P2开局局」帧两端 2.8/2.1 = 背景实为 6 格):阈值 6.0 =
#: 背景上限 2.9 的 2.07×、空槽下限 10.5 的 0.57×,双向余量均 >1.7×。
_CV_SLOT_STD_MIN: float = 6.0


def _cv_slot_std(screen, cx: int) -> float | None:
    """候选位裁切灰度 std(槽框/立绘 → 高;无格背景 → 近 0);越界 → None。"""
    import cv2
    import numpy as np
    h, w = screen.shape[:2]
    x1, x2 = cx - _CV_HALF, cx + _CV_HALF
    if x1 < 0 or x2 > w or h < _BACK_Y2:
        return None
    crop = screen[_BACK_Y1:_BACK_Y2, x1:x2]
    g = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    return float(np.asarray(g, dtype=np.float32).std())


def cv_back_slots(screen) -> int | None:
    """CV 通道:实测当前帧后台格数(ADR-0385 双通道件2)→ ``6 + 扩展位数`` | None。

    方法:对两端扩展位(464/1458)逐位判「槽签名存在」(裁切灰度 std ≥
    :data:`_CV_SLOT_STD_MIN`,依据见其注释);格数 = 6 + 存在数(6/7/8,
    扩展几何 = 基线两端追加——6/8 两档共享中段的实证推论,单端扩展即 7 格)。
    锚位(606/1031)任一无槽签名 → 帧不可判(overlay 遮挡/非备战态/非 1080p)
    → None(调用方退公式通道)。纯读 best-effort,异常 → None 不抛。
    """
    try:
        anchors = [_cv_slot_std(screen, x) for x in _CV_ANCHOR_XS]
        if any(a is None or a < _CV_SLOT_STD_MIN for a in anchors):
            return None
        extras = 0
        for x in _CV_EXTRA_XS:
            s = _cv_slot_std(screen, x)
            if s is not None and s >= _CV_SLOT_STD_MIN:
                extras += 1
        return _BACK_SLOTS_BASE + extras
    except Exception:   # noqa: BLE001  CV best-effort,失败退公式
        return None


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
    """7 格档未建档(公式 diff==1 或 CV 单端扩展)→ obs_conflict 留证
    (节流 300s/源;保守按 8 格超集跑,ADR-0385)。

    采集指引:钻石局(cap=level+1,无召唤物)截备战帧 → 交互实锤 7 格槽位 x →
    upsert_screen_area 后排7槽-1..7 → ``_LAYOUT_PREFIX`` 登记 7 → 本函数自然
    不再触发。best-effort 不抛。
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


def note_channel_conflict(screen, formula_n: int, cv_n: int,
                          cap, level, source: str) -> None:
    """双通道不一致留证(节流 300s/源;ADR-0385 对账语义件3)。

    采 CV 值运行 + 留证两值(公式依赖的 cap/level OCR 读数可能错;CV 是画面
    真值)。best-effort 不抛。
    """
    import time as _time
    try:
        now = _time.monotonic()
        if now - _channel_conflict_ts.get(source, -1e9) < 300.0:
            return
        _channel_conflict_ts[source] = now
        from sr_od.application.currency_war.cw_observe import obs_conflict
        obs_conflict(
            'back_layout_channel_conflict', formula_n, cv_n, screen,
            verdict=('采 CV 实测值(画面事实>推导,ADR-0385 双通道对账);'
                     '公式值依赖的 cap/level OCR 读数疑有误——核对截图'
                     '「区域-部署数」X/Y 与等级,确认哪侧读错则修对应 reader;'
                     'CV 侧判据=槽位 std 签名,若画面被特效/overlay 污染也可能'
                     ' CV 错,复现 ≥3 次再排期'),
            source=source, cap=cap, level=level)
    except Exception:   # noqa: BLE001
        pass


def select_back_layout(ctx, screen, level: int | None = None,
                       cap: int | None = None) -> tuple[int, str]:
    """布局选档单一入口(ADR-0385 双通道对账)→ ``(槽数, 布局前缀)``。

    通道①公式:cap 未传 → ``read_deploy_cap``(paddle 直读权威)现读;
    level 未传 → session 等级链(单调链防毒化);任一读不到 → diff 按 0。
    通道②CV:``cv_back_slots(screen)`` 实测(锚缺失/越界 → None 退公式)。
    对账:一致 → 公式值;不一致 → **CV 值** + :func:`note_channel_conflict`
    留证(带两值);公式值 7(未建档)→ 8 格超集 + :func:`note_7slots_pending`。

    交叉验证:``check_system_unit_layout``(系统单位恒最右)在读板路径常设对账
    (公式选档与画面不符时留 layout_mismatch 证据,公式误读的兜底网)。
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
    d = 0 if diff < 0 else min(diff, _CAP_DIFF_MAX)
    raw_formula = _BACK_SLOTS_BASE + d          # 未映射真值(7 = 未建档档)
    formula_n = back_slots_from_cap_diff(diff)  # 映射后(7 → 8 格超集)
    cv_n = cv_back_slots(screen) if screen is not None else None
    if cv_n is not None and cv_n != formula_n:
        # 对账不一致:CV 实测优先(画面事实>推导,ADR-0385)+ 留证两值
        note_channel_conflict(screen, formula_n, cv_n, cap, level,
                              'select_back_layout')
        n_raw = cv_n
    else:
        n_raw = raw_formula
    if n_raw == 7:
        note_7slots_pending(screen, cap, level, 'select_back_layout')
    n = n_raw if n_raw in _LAYOUT_PREFIX else 8   # 7 → 8 格超集(模块 docstring)
    p = _layout_prefixes().get(n, _LAYOUT_PREFIX[_BACK_SLOTS_BASE])
    try:
        global _last_sel_log
        _key = (n, formula_n, cv_n, cap, level)
        if _key != _last_sel_log:
            _last_sel_log = _key
            from one_dragon.utils.log_utils import log
            log.info('[cw][layout] 后排选档: %d 格(公式 %s/cv %s;'
                     'cap=%s lv=%s diff=%s;双通道对账 ADR-0385)',
                     n, formula_n, cv_n, cap, level, diff)
    except Exception:   # noqa: BLE001
        pass
    return n, p


def back_row_slot_rects_ctx(ctx, prefix: str) -> list[tuple[int, Rect]]:
    """按布局前缀从 screen_info 枚举 ``[(slot_idx, rect), ...]``(N 升序至断档)。

    前缀来自 :func:`select_back_layout`(ADR-0385 双通道选档);空档 → [](调用方
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
