"""货币战争 **后排槽位布局**(双通道对账:公式 + CV 实测;ADR-0385,
2026-08-26 W209 事故响应批 + 同日口述双通道指令修订)。

机制(用户口述权威,docs/game/currency_war/research/board_structure.md):
- **等级只定上场人数 cap,不定格子数**;正常恒 前台 4 格 + 后台 6 格;
- **后台格数 = 6 + (cap − level)**(口述公式):钻石/召唤物使 cap 超过 level,
  差值即后台扩展量——diff 0 → 6 格基线;diff ≥2 → 8 格(393-1529 带,狸猫局
  交互实拍,screen_info ``后排8槽-1..8``);diff==1(钻石+1)→ 7 格**已建档**
  (2026-08-26 佩佩局交互实锤+覆盖拖测;几何=**整排居中重排** 中心
  534..1386,screen_info ``后排7槽-1..7``;居中勘误见 :data:`_LAYOUT_PREFIX`
  注与 ADR-0390)。

**双通道对账**(口述指令 2026-08-26 追加,两通道都做):

1. **公式通道**::func:`back_slots_from_cap_diff`「6+(cap−level)」——cap =
   ``read_deploy_cap_debounced``(paddle 直读 + ADR-0286 域防抖:域外重读一帧,
   仍域外拒信退基线,W218/ADR-0395 接线;显式传 cap 的调用方自担防抖),
   level = session 等级链(单调链防毒化)。
   「钻石局检测」由此消解(无需识别钻石图标,两 OCR 读数相减即扩展量)。
2. **CV 通道**::func:`cv_back_slots` 画面实测——后排 y 带槽位存在性签名
   (空槽暗框 vs 无格背景的灰度 std 判别,标定见 :data:`_CV_SLOT_STD_MIN`)。
3. **对账语义**(口述裁决):一致 → 公式值;**不一致 → CV 实测值**
   (画面事实 > 推导——公式依赖的两个 OCR 读数可能错)+
   ``obs_conflict('back_layout_channel_conflict')`` 留证(带两值,便于判读);
   CV 不可判(帧越界/锚缺失,如 overlay 遮挡/非备战帧)→ 退公式值
   (公式 = CV 偶发失效时的兜底 + 低成本快速路径)。
4. 7 格档已建档(2026-08-26 佩佩局,用户口述真值 + 点击面板/拖拽交互实锤 +
   246 覆盖拖测)→ diff==1 直读 7 格。**未建档新档位**(diff≥3 域外/CV 新
   观察)→ 8 格超集运行(读全扩展带;拖到不存在格被游戏拒 = 廉价
   失败方向)+ 留证钩子(``cw_identity_obs.read_deployed_chars``,n_raw 未
   建档时 obs_conflict 留证+去重截图引导人工经 MCP 采集;ADR-0385 件①,
   7 格即按此流程闭合后钩子自然静默)。旧「lv6=7 格待采」留证机器
   (note_pending_7slots/_PENDING_7SLOT_LEVELS)随 level 驱动模型作废清理
   (ADR-0385 件②)。

旧 level 驱动模型(ADR-0281「level≥7→8 格」)**归因错误**(其实证局狸猫局
本身带召唤物=cap 差,不是 level),本模块勘误;level 只进 cap 板满门,
不进布局选档。run 26(lv8 无召唤物局)按 8 格坐标拖不存在的 7/8 号格 +
幻影空位把部署卡死在 bench = 崩坏根因①。

单一真相源 = screen_info(6 槽 = ``后排-1..6``;7 槽 = ``后排7槽-1..7``;
8 槽 = ``后排8槽-1..8``)。
旧 9/10/11 档是循环论证幻影(ADR-0281),已删,勿再登记;「后排7槽-P2开局局」
实拍帧经 CV 复核两端扩展位均为背景(旧 7 槽观察同属幻影,实为 6 格)。
系统单位恒最右模型与布局自检(``cw_identity_obs.check_system_unit_layout``)
保留作交叉验证。CV 通道与该自检同为 1080p 原生坐标(项目基准,同款假设)。
"""
from __future__ import annotations

from one_dragon.base.geometry.rectangle import Rect

#: 槽数 → screen_info 布局前缀(6 槽 = 基线「后排-N」;8 槽 = 「后排8槽-N」;
#: 7 槽 = 「后排7槽-N」)。7 格几何 = **整排居中重排**(排中心恒 960):
#: 7 格中心 534/676/818/960/1102/1244/1386(带 463-1457);6 格 604..1316;
#: 8 格 464..1458——三档各自居中,不共享列位。**旧记「7 格=6 格右扩一格,
#: 佩佩中心 1458」错位 +71px**(2026-08-26 勘误:点击面板交互实锤——点真
#: 中心 534/1390 开详情,点旧记中心 604/746/1458 全无响应;占用台座扫峰
#: 左缘 -70 校正后全落 534/818/1102/1386;万敌 246 覆盖拖测逐位验证)。
#: ⚠️ 9/10/11 档是循环论证幻影(ADR-0281),已删。
_LAYOUT_PREFIX: dict[int, str] = {
    6: '后排',
    7: '后排7槽',
    8: '后排8槽',
}

#: 基线后台格数(口述:正常恒 前台 4 + 后台 6)
_BACK_SLOTS_BASE: int = 6

#: cap 差域上界(``cw_observation.DEPLOY_CAP_MAX_DIFF`` 同源;实机语料未见 >2)
_CAP_DIFF_MAX: int = 2

#: 后排 y 带(所有布局共用;槽 rect 高约 600-739)
_BACK_Y1, _BACK_Y2 = 600, 739

# 双通道冲突节流(300s/源)与选档日志去重(值不变不重复打)
_channel_conflict_ts: dict[str, float] = {}
_last_sel_log: tuple | None = None

# ===== CV 通道:槽位存在性签名(ADR-0385 双通道件2) =====

#: 探针位 x(信息量在两端 464/1458;606/1031 作帧可用性锚,见
#: :data:`_CV_ANCHOR_XS`)。探针**固定不随档挪**:两端位 = 8 格档 1/8 号格
#: 中心,三档居中重排后它们在 6 格=排外背景、7 格=端格半覆盖、8 格=端格
#: 全覆盖——判别语义与重叠带的图解见 :data:`_CV_LEFT_STD_MIN` 注。
#: 1080p 原生坐标(非 1080p 帧 :func:`cv_back_slots` 越界守卫返 None)。
_CV_CAND_XS: tuple[int, ...] = (464, 606, 748, 889, 1031, 1174, 1316, 1458)
#: 两端探针位(数格用):6 格态此二位 = 排外背景;7 格 = 端格半覆盖;
#: 8 格 = 端格全覆盖
_CV_EXTRA_XS: tuple[int, ...] = (464, 1458)
#: 锚位(606/1031):帧可用性检查——三档几何下探针窗都落在格带上
#: (6/8 格盖格心,7 格跨 1/2 号格交界),真备战帧必有槽签名;任一锚
#: std < 6 = overlay 遮挡/非备战态/非 1080p → 整体不可判返 None。
_CV_ANCHOR_XS: tuple[int, ...] = (606, 1031)
#: 裁切半宽(槽 rect 宽 142 的半径,同既有槽建模)
_CV_HALF: int = 71
#: 槽存在判据(右端 1458 与锚位通用):裁切灰度 std ≥ 本值。标定(W209 探针,
#: sr-od-test 6 帧 6 格态 ×2 端扩展位 = 12 个背景样本 std ≤ 2.9;空槽暗框
#: std ≥ 10.5,占位立绘 50-67):阈值 6.0 = 背景上限 2.9 的 2.07×、空槽
#: 下限 10.5 的 0.57×,双向余量均 >1.7×。
_CV_SLOT_STD_MIN: float = 6.0
#: **左端探针(x=464)三值判据**。
#:
#: 背景:左端探针固定在 x=464(**8 格档 1 号格的中心**,探针位不随档挪动),
#: 裁 464±71 = [393,535] 窗算灰度 std(有格子/立绘 → 高,纯背景 → 近 0)。
#: 三档**居中重排**(ADR-0390)后,同一个 [393,535] 窗在三种局里盖到的东西
#: 完全不同:
#:
#: :``6 格``:真 1 号格在 [533,675],窗全在排外背景            → std ≤ 2.9
#: :``7 格``:真 1 号格在 [463,605],窗只盖它的**左半** [463,535] → std 26-44
#: :          (72/142px;随格上立绘大小浮动)
#: :``8 格``:真 1 号格在 [393,535],窗正好**盖满整格**          → 有人 62.5-148
#: :          / 空槽只有暗框 38.8
#:
#: 致命重叠:**7 格的「左半片」(26-44)与 8 格的「空槽暗框」(38.8)在
#: [26,48] 区间撞车**——std 单值分不开 7 格和 8 格。故三值:
#: ≥48 → 左端格存在(8 格);≤12 → 无左端格(6 格);[12,48] → **不可判,
#: cv_back_slots 返 None 退公式**(7/8 由公式通道 diff=cap−level 定,见
#: :func:`cv_back_slots`)。
#: (旧解释「羁绊面板渗入」已作废:羁绊面板最右只到 x=258,渗不到 464——
#: 该 26-44 信号就是 7 格真 1 号格的左半片。)
_CV_LEFT_STD_MIN: float = 48.0
#: 左端不可判带下界:12(6 格背景实测上限 2.9 的 ~4 倍,且在 7 格左半片
#: 实测下限 26.2 之下留足间隔)
_CV_LEFT_STD_AMBIG_LO: float = 12.0


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
    """CV 通道:实测当前帧后台格数(ADR-0385 双通道件2)→ ``6 + 两端探针存在数`` | None。

    方法:在后排两端各放一个**固定探针**(x=464 与 x=1458,即 8 格档 1/8 号格
    中心;探针位不随档挪动),各裁 ±71px 窗算灰度 std,判「该处有没有格子」;
    格数 = 6 + 存在数。三档居中重排(ADR-0390)后探针盖到的东西随档不同:

    - **右端 1458**:std ≥ 6 即算有格子(8 格盖满真 8 号格、7 格盖真 7 号格
      [1315,1457] 的右半 [1387,1457],两种都是高 std;6 格态 1458 在排外
      背景 ≤2.9)。
    - **左端 464 三值**:≥48 有格子 / ≤12 无格子 / **[12,48] 不可判**——
      7 格局窗 [393,535] 只盖真 1 号格 [463,605] 的左半(std 26-44),与
      8 格空槽暗框(38.8)重叠分不开;完整图解见 :data:`_CV_LEFT_STD_MIN`。
    - **不可判 → 整体返 None 退公式通道**(7/8 由公式 diff=cap−level 定:
      cap 是 OCR 直读,等级漏读有经验条反推兜底——ADR-0389 后批)。
    - 锚位(606/1031)任一无槽签名 → 帧不可判(overlay 遮挡/非备战态/
      非 1080p)→ None(调用方退公式通道)。

    三档几何(居中重排,排中心恒 960,互不共享列位):6 格中心 604..1314 /
    7 格 534..1386 / 8 格 464..1458。纯读 best-effort,异常 → None 不抛。
    """
    try:
        anchors = [_cv_slot_std(screen, x) for x in _CV_ANCHOR_XS]
        if any(a is None or a < _CV_SLOT_STD_MIN for a in anchors):
            return None
        left = _cv_slot_std(screen, 464)
        if left is not None and _CV_LEFT_STD_AMBIG_LO < left < _CV_LEFT_STD_MIN:
            return None   # 左端不可判带(重叠带):退公式,不硬猜
        extras = 0
        if left is not None and left >= _CV_LEFT_STD_MIN:
            extras += 1
        s = _cv_slot_std(screen, 1458)
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
    - 公式值未建档(diff≥3 域外族)→ **保守退 8 格超集**(扩展带读全不丢系统
      单位;拖到不存在的位 8 被游戏拒 = 廉价失败方向);diff==1 → 7 格已建档
      直读(2026-08-26 佩佩局)。
    """
    d = 0 if diff < 0 else min(diff, _CAP_DIFF_MAX)
    n = _BACK_SLOTS_BASE + d
    if n in _LAYOUT_PREFIX:
        return n
    return 8   # 7 格档未建档 → 8 格超集(见模块 docstring;留证在调用侧)


#: **公式-历史实证张力(ADR-0385 件3,待召唤物局数据解)**:唯一历史 8 格
#: 实证(狸猫局 lv7 cap8/9 两帧同为 8 格)与公式 6+(8−7)=7 冲突。候选解释:
#: ①召唤物加格不加 cap(公式需补召唤物项)/②当年 cap 读数有误/③召唤物局
#: 两帧实为 cap9。批内不硬解:双通道对账天然覆盖(CV 为真值,公式不符 →
#: ``back_layout_channel_conflict`` 留证);run 27+ 锚点「钻石/召唤物局记录
#: cap/level/CV 格数三点对」攒数据后定公式是否需修正项。
FORMULA_SUMMON_TENSION_NOTED: bool = True


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

    委托 :func:`resolve_back_slots`(详见其对账语义与各返回字段);
    消费方只需格数+前缀。停机钩子/留证消费 raw 字段请直调后者。
    """
    r = resolve_back_slots(ctx, screen, level=level, cap=cap)
    return r['n'], r['prefix']


def _cv_confirm_readings(ctx, screen, first_cv: int, formula_n: int) -> list[int | None]:
    """W209h 防抖重读(ADR-0385 决策 11;run 27 停机事故:CV 瞬态假阳——
    特效/粒子把 1458 位单帧 std 顶到 6.5(阈值 6.0 擦线过,真槽 ≥10.5/
    背景 ≤2.9 之间无人带),公式 6 与 fixture 复测一致)。

    触发条件:CV 读数产生「新格数」(≠公式值 且 ∉ 已建档档 {6,8}——即会
    触发 7 格采集/停机的读数)。house 先例 = shop 未识别卡 r34:重读 2 帧
    仍 miss 才真停。本处:隔 ~1s 重读 2 次,**三次一致才按 CV 值行动**;
    任一不一致 = 瞬态自愈,退公式值。重读帧由 ``ctx`` 现截(生产)/测试
    monkeypatch ``ctx.screenshot``(不可截 = None,按不一致处理)。

    返回三次读数序列 ``[first, r2, r3]``(None = 该次不可读,视为不一致)
    ——留证/判读消费。
    """
    readings = [first_cv]
    try:
        import time as _time
        for _ in range(2):
            _time.sleep(1.0)   # 隔帧重读(~1s,同 r34 house 先例节奏)
            _scr = None
            try:
                if ctx is not None and hasattr(ctx, 'screenshot'):
                    _scr = ctx.screenshot()
            except Exception:   # noqa: BLE001  重截失败按不可读
                _scr = None
            readings.append(cv_back_slots(_scr) if _scr is not None else None)
    except Exception:   # noqa: BLE001  防抖 best-effort,失败退公式
        pass
    return readings


def resolve_back_slots(ctx, screen, level: int | None = None,
                       cap: int | None = None) -> dict:
    """双通道对账全量解析(ADR-0385;选档与钩子共用的单一判定源)→ dict:

    - ``formula_raw``/``formula_n``:公式原始格数/映射后格数(**未建档**值
      (9+)映射 8 格超集;已建档的 6/7/8 原样返回);
    - ``cv_n``:CV 实测格数(None=不可判;防抖未通过时为 None 语义=退公式);
    - ``cv_readings``:防抖重读序列(W209h;仅新格数读数触发时非 None);
    - ``n_raw``:对账后原始格数(不一致采 CV;未建档值保留原值供钩子判档);
    - ``n``/``prefix``:运行值(未建档档 → 8 格超集,已建档档直读);
    - ``cap``/``level``/``diff``:读数快照(判读/留证)。

    对账:一致 → 公式值;CV 实测存在且不符 → **CV 值**(画面事实>推导)+
    :func:`note_channel_conflict` 留证两值;CV None → 公式值兜底。
    **防抖(W209h/决策 11)**:CV 读出**未建档**新格数(≠公式 且 ∉ 已建档
    档 {6,7,8})单帧不行动——重读 2 次三次一致才采 CV 值;任一不一致 =
    瞬态,退公式值 + 留证(阈值不动,瞬态用重读解)。
    """
    try:
        if level is None or level <= 0:
            from sr_od.application.currency_war.cw_identity_obs import _session_level
            level = _session_level(ctx)
        if cap is None:
            # W218(ADR-0395):cap 瞬态误读(过渡帧旧值残影,run 27 型)会直接改
            # diff → 公式通道选错档(格数类高危点);改走 read_deploy_cap_debounced
            # (ADR-0286 域防抖:域外重读一帧,仍域外 → None → 下方 diff=0 退 6 格
            # 基线,失败安全侧;level 未知时域不可判,退原直读语义)。
            from sr_od.application.currency_war.cw_observation import (
                read_deploy_cap_debounced,
            )
            cap = read_deploy_cap_debounced(ctx, screen, level)
    except Exception:   # noqa: BLE001  读源失败 → 退基线(失败安全侧)
        cap, level = None, None
    diff = (cap - level) if (cap is not None and level) else 0
    d = 0 if diff < 0 else min(diff, _CAP_DIFF_MAX)
    formula_raw = _BACK_SLOTS_BASE + d            # 未映射真值(7 = 未建档档)
    formula_n = back_slots_from_cap_diff(diff)    # 映射后(7 → 8 格超集)
    cv_n = cv_back_slots(screen) if screen is not None else None
    cv_readings: list[int | None] | None = None
    if cv_n is not None and cv_n != formula_n:
        # 对账不一致:CV 实测优先(画面事实>推导,ADR-0385)+ 留证两值
        note_channel_conflict(screen, formula_n, cv_n, cap, level,
                              'select_back_layout')
        if cv_n not in _LAYOUT_PREFIX:
            # W209h 防抖:新格数读数(会触发 7 格采集/停机)单帧不行动——
            # 重读 2 次三次一致才采;任一不一致 = 瞬态自愈退公式 + 留证序列
            cv_readings = _cv_confirm_readings(ctx, screen, cv_n, formula_n)
            if not (len(cv_readings) == 3
                    and all(r == cv_n for r in cv_readings)):
                from one_dragon.utils.log_utils import log
                log.info('[cw][layout] CV 新格数 %s 防抖未过(重读序列 %s;'
                         '疑特效/粒子瞬态,W209h)→ 退公式值 %s',
                         cv_n, cv_readings, formula_n)
                try:
                    from sr_od.application.currency_war.cw_observe import obs_conflict
                    obs_conflict(
                        'back_layout_cv_transient', cv_n, formula_n, screen,
                        verdict=('瞬态自愈-退公式值(W209h 防抖重读;'
                                 '重读序列见 ctx.cv_readings;阈值不动'
                                 '(6.0 标定有据),单帧擦线读数不行动)'),
                        source='select_back_layout', cap=cap, level=level)
                except Exception:   # noqa: BLE001
                    pass
                cv_n = None   # 退公式(下游 n_raw = 公式真值)
        n_raw = cv_n if cv_n is not None else formula_raw
    else:
        n_raw = formula_raw
    n = n_raw if n_raw in _LAYOUT_PREFIX else 8   # 未建档新档位 → 8 格超集(模块 docstring 条4)
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
    return {'formula_raw': formula_raw, 'formula_n': formula_n, 'cv_n': cv_n,
            'cv_readings': cv_readings,
            'n_raw': n_raw, 'n': n, 'prefix': p, 'cap': cap, 'level': level,
            'diff': diff}


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
