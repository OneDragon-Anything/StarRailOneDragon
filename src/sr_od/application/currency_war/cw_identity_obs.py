# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏 视觉身份观测**(SIFT,非 OCR)。

与 ``cw_observation``(OCR 字段)互补:本模块读 OCR 看不见的**身份** —— 备战栏 / 舞台槽内角色
立绘 → 规范名(``read_deployed_chars`` / ``read_bench_chars``),用 ``currency_war_char_id`` 的
SIFT 匹配器对模板库(生产用 ``currency_war/portrait_plaza`` 官方立绘库,见 ``currency_war_char_id`` docstring)。

**与 bot 跟踪的关系**(设计):``GameState.deployed`` / ``bench`` 默认由 **bot 跟踪**(buy/deploy
动作推演,``simulate`` 维护,见 ``cw_state``)—— plan-time 快、无需 SIFT。本模块的视觉 reads 是
**独立旁路**,用途:① 离线从截图重建 GameState(测试 / replay,无需跑 bot);② bot 跟踪漂移时
从画面恢复 / 校验。故**不**接进 ``read_game_state``(避免每帧 SIFT + 与 bot 跟踪双写冲突)。

槽位坐标 = screen_info 固定 area(``前排-1..4`` / ``后排-1..6`` / ``备战栏-1..9``),经
``cw_obs_core._area_rect`` 读 —— 改坐标改 yml 即可。空槽位 SIFT 内点低 → 自然落 None
(无需「槽位是否填充」预判)。

**架构:纯 CV 核心 + ctx 薄包装** —— ``identify_slots`` 只吃 (screen, templates, slots, row),
可离线硬编码 rect 测;``read_deployed_chars`` / ``read_bench_chars`` 从 ctx screen_info 取 rect
再调核心。与 ``currency_war_char_id`` 同样的「纯 CV + 外部接线」分层。

**可靠性:实测初步可用(2026-08-09 D-22)**:r1-8 备战截图 SIFT 立绘库 **6/6 有角色槽命中**(inliers
29-48)+ 空槽不误 → 立绘库可用,推翻脸库旧结论。待补:共脸变体样本 + 角色名 ground truth(见
``currency_war_char_id`` docstring)。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.currency_war_char_id import (
    AvatarTemplates,
    identify_character,
    load_avatar_templates,
)
from sr_od.application.currency_war.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.cw_equipment import read_equipped_below
from sr_od.application.currency_war.cw_obs_core import _area_rect
from sr_od.application.currency_war.cw_state import BenchChar
from sr_od.config.character_const import get_character_by_id
from sr_od.context.sr_context import SrContext


def resolve_char_name(avatar_id: str) -> str | None:
    """SIFT 的 avatar_id(模板目录名)→ 货币战争规范名(``CHARACTER_ROSTER`` 成员)。

    **半身立绘库(``currency_war/portrait_plaza``)key = 中文规范名**(官方 plaza 烘焙,含变体独立模板,如
    ``姬子·启行`` / ``千冶·刃``)→ ``identify_character`` 返回的 avatar_id 已是规范名 → 本函数
    第 54 行 ``avatar_id in CHARACTER_ROSTER`` 直接命中返。变体**可被 SIFT 区分**(D-54 验:
    deployed_p1r9 后排-2 姬子·启行 inliers=38,基础姬子 <7 连 top3 未进 —— 共脸对分数拉开,
    非无法区分;旧「脸库归一·SIFT 无法区分变体」结论是脸库时代产物,已废)。

    56-65 行(``get_character_by_id`` 英文 id→cn + 子串消歧)是 **legacy 脸库路径**(英文 id),
    半身立绘库基本不走;留作兜底。仍无 → None(SIFT 命中但不在货币战争 roster,如开拓者 roster 缺、
    脸库误匹配)。
    """
    if avatar_id in CHARACTER_ROSTER:
        return avatar_id   # CW 立绘库 key 是中文规范名(plaza 烘焙),直接返(非主游英文 id)
    c = get_character_by_id(avatar_id)
    if c is None:
        return None
    cn = c.cn
    if cn in CHARACTER_ROSTER:
        return cn
    for name in CHARACTER_ROSTER:          # 变体消歧:roster 含此 cn 名的成员
        if cn in name:
            return name
    return None


def ensure_portrait_templates(ctx: SrContext) -> AvatarTemplates | None:
    """确保 ctx 缓存 ``currency_war/portrait_plaza`` 立绘 SIFT 模板;返 templates 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_portrait_templates``;后续读缓存。**shop SIFT**(D-55,``read_shop_cards``)
    + deployed/bench SIFT 身份识别的模板加载点(deploy_bench 也读写此缓存)。**幂等**:同值重 load 无害。

    **并发安全**:只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争(同 ensure_equip_tm_templates)。
    buy 在 deploy 之前(BattlePrepCycle: buy→deploy),故 shop 不能依赖 deploy 才加载的模板 → 本函数按需加载。
    """
    templates = getattr(ctx, 'cw_portrait_templates', None)
    if templates is None:
        base = Path(__file__).resolve().parents[4] / 'assets' / 'template'
        portrait_dir = base / 'currency_war' / 'portrait_plaza'   # 官方立绘库(plaza big_icon 烘焙,含 mask;唯一库,旧手采库已删 2026-08-17)
        if not portrait_dir.is_dir():
            return None
        templates = load_avatar_templates(portrait_dir)
        ctx.cw_portrait_templates = templates
    return templates


# 金星(亮金色五角星)HSV 范围(CV 采样 4 样本 star_front_1..4 标定 2026-08-11;crop=RGB)。
# 亮金色 ≈ #FFD700:H 黄~橙(OpenCV 0-180),高 S 高 V。立绘金色装饰(衣服/腰带)也命中 → 靠位置(底部)过滤。
# HSV 金色范围;**V>150** 只抓自发光亮金星,滤暗金衣服装饰(ADR-0114,2026-08-13):
# 前排角色立绘底部有大量暗金衣服(V80-150)淹没金星,旧 V>80 把衣服抓成 area1279 大块致检测崩溃。
_STAR_GOLD_LO: tuple[int, int, int] = (10, 40, 150)
_STAR_GOLD_HI: tuple[int, int, int] = (45, 255, 255)
# TM 匹配阈值(2026-08-13:0.45)。**根因实测(ADR-0116)**:第2星 TM val 系统性低于第1星(第1 0.62-0.69 / 第2
# 0.45-0.58)—— 两星**紧贴遮挡**,第2星 mask 不完整 → val 偏低;各排一致(星尺寸 17-19px 跨排相同,**非缩放
# 失配**,多模板 per 排无用,ADR-0116 实测推翻)。val 随紧贴程度变(后排-6 最紧 val~0.45 / 后排-3 0.51)。
# thresh 0.45 = **真第2星(≥0.45)与噪声装饰(<0.40)的分界**,非打地鼠补丁。验:立绘库 0/71 + 全 fixture
# 无新 FP + 所有 2★ 槽读 2(0.40 才过数噪声,余量 ~0.05)。迭代史:0.55→0.50(后排-3)→0.45(后排-6)。
_STAR_TM_THRESH: float = 0.45
# peak 轮廓圆度下限(ADR-0115,2026-08-13:0.25)。原 0.35 太紧 —— 真金星 circ 实测 0.34-0.50(随槽位
# 渲染微变),备战-9 边槽把同颗星 circ 压到 0.34<0.35 被误拒 → 2星读 1(假阴)。**立绘库 0/71 误判
# 不靠 circ**(area+aspect+V>150+TM 已挡死,circ>0.0 仍 0/71)+ 全 fixture 无新 FP → 放宽到 0.25 留足余量。
_STAR_CIRC_MIN: float = 0.25
# 四角星 TM 模板(单星 mask,19x19 area190,从备战栏-1 单星提取);模块级缓存避免每帧 imread。
_STAR_TMPL_CACHE: MatLike | None = None


def _load_star_tmpl() -> MatLike | None:
    """加载四角星 TM 模板(模块级缓存,首次 imread 后复用);缺失返 None(read_star fallback 1)。"""
    global _STAR_TMPL_CACHE
    if _STAR_TMPL_CACHE is None:
        # 模板统一目录(2026-08-16 用户规范:assets/template/currency_war/<类型>/;star 金星模板在 star/)
        p = Path(__file__).resolve().parents[4] / 'assets' / 'template' / 'currency_war' / 'star' / 'star_gold_tmpl.png'
        if p.exists():
            _STAR_TMPL_CACHE = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    return _STAR_TMPL_CACHE


def read_star(crop: MatLike) -> int:
    """数角色立绘底部金星(星级);``crop`` = 槽位 RGB crop(含立绘 + 底部金星)。

    金星 = **四角星**(十字星 ✦,自发光亮金黄),立绘**底部中央**(y > 0.65h);1/2/3 星 = N 颗并排。
    **TM 模板匹配法**(ADR-0114,替 ADR-0113 轮廓法):HSV V>150 抓亮金星(滤暗金衣服)→ 四角星模板
    matchTemplate → NMS 分离紧贴(2 星 gap 小)→ peak 局部 area/aspect/circ 验证滤残余装饰。

    轮廓法(ADR-0113)对 **2 星紧贴**(连通成大域 area>600 上限漏)+ **前排衣服淹没**(area1279
    把金星淹没)结构性失效。TM 各星独立滑窗匹配,紧贴亦分,V>150 滤衣服让 mask 干净 —— 治本。
    验证(2026-08-13):立绘库 71 张 0 误判 + 各位置 2星(前排-3/后排-3/备战-4)读 2 + 三月七 2星 +
    1星各槽稳读 1。**thresh 0.45(ADR-0114→0116)**:第2星 TM val 系统性低于第1星(第1 0.62-0.69 / 第2 0.45-0.58)——
    两星**紧贴遮挡**致第2星 mask 不完整 → val 偏低;**各排星尺寸 17-19px 相同(非缩放失配,多模板 per 排实测无用,
    ADR-0116 推翻该假设)**。val 随紧贴程度变(后排-6 最紧 ~0.45)。0.45 = 真第2星(≥0.45)与噪声(<0.40)分界。
    验:立绘库 0/71 + 全 fixture 无新 FP + 所有 2★ 读 2(含各排边槽)。
    **circ 放宽(ADR-0115)**:原 circ>0.35 太紧 —— 备战-9 边槽同颗金星 circ 渲染到 0.34 被误拒 → 2星读 1;
    放宽到 0.25(立绘库仍 0/71 + 全 fixture 无新 FP),备战-9 读回 2。

    :return: 星级(≥1);空图/无匹配/模板缺 → 1(角色必有星,fallback)。
    ⚠️ **offline 旁路**(live 走 bot tracking ``BenchChar.star``,非 read_star):comp_viability 离线
    校验用(cw_performance:185),不影响 live star_achievement。3星待 live 样本(逻辑同,数金星)。
    """
    if crop is None or crop.size == 0:
        return 1
    tmpl = _load_star_tmpl()
    if tmpl is None:
        return 1
    h, w = crop.shape[:2]
    region = crop[int(h * 0.65):, int(w * 0.15):int(w * 0.85)]  # 底部中央带(cy>0.65,盖前排0.72)
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, _STAR_GOLD_LO, _STAR_GOLD_HI)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    th, tw = tmpl.shape[:2]
    if mask.shape[0] < th or mask.shape[1] < tw:
        return 1
    res = cv2.matchTemplate(mask, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    if max_val < _STAR_TM_THRESH:
        return 1  # 无金星匹配 → fallback(角色必有星)
    # NMS:收集 ≥_STAR_TM_THRESH 的 peak,互距 > tw*0.6(分离紧贴 2星)
    min_dist = tw * 0.6
    ys, xs = np.where(res >= _STAR_TM_THRESH)
    pts = sorted(zip(ys, xs, strict=True), key=lambda p: res[p[0], p[1]], reverse=True)
    peaks: list[tuple[int, int]] = []
    for y, x in pts:
        if all((y - py) ** 2 + (x - px) ** 2 > min_dist ** 2 for py, px in peaks):
            peaks.append((int(y), int(x)))
    # peak 局部形状验证:四角星 area 80-320 + aspect 近方 0.80-1.20 + circ>_STAR_CIRC_MIN(滤细长/碎装饰)。
    # circ 下限见 _STAR_CIRC_MIN(ADR-0115:0.35→0.25,原误拒备战-9 边槽真金星)。
    # ⚖️ 行对齐验证(2026-08-16,用户实锤星徽秘典画面 star2 误标追因):真金星 N 颗 = **水平一排**
    # (同 y ±4px,间距规律);服饰装饰(肩部金色领结/饰带)形状碰巧过形状门(实测 TM 0.51 + area/aspect/circ
    # 全过)但 y 偏上离真星行远 → 行对齐杀此类误报。实现:过形状门的 peak 取**最大聚类行**(同 y 带
    # 内数量多者优先;单峰自成一行的场景=1 星照常)。
    count = 0
    _passed: list[tuple[int, int]] = []   # (py, px) 过形状门的峰
    for py, px in peaks:
        local = mask[py:py + th, px:px + tw]
        if local.size < th * tw:
            continue
        lc, _ = cv2.findContours(local, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cc = max(lc, key=cv2.contourArea) if lc else None
        if cc is None:
            continue
        la = cv2.contourArea(cc)
        perim = cv2.arcLength(cc, True)
        bx, by, bw, bh = cv2.boundingRect(cc)
        aspect = bw / bh if bh > 0 else 0
        circ = 4 * np.pi * la / perim / perim if perim > 0 else 0
        if 80 <= la <= 320 and 0.80 <= aspect <= 1.20 and circ > _STAR_CIRC_MIN:
            _passed.append((py, px))
    if _passed:
        # 行聚类:y 差 ≤4 的峰聚一行;取峰最多的行(平局取 y 大者——星行在底部)。
        _rows: list[list[tuple[int, int]]] = []
        for py, px in sorted(_passed, key=lambda p: p[0]):
            if _rows and abs(py - _rows[-1][0][0]) <= 4:
                _rows[-1].append((py, px))
            else:
                _rows.append([(py, px)])
        _best = max(_rows, key=lambda r: (len(r), r[0][0]))
        count = len(_best)
    return max(count, 1)


def identify_slots(
    screen: MatLike,
    templates: AvatarTemplates,
    slots: list[tuple[int, Rect]],
    row: str,
) -> list[BenchChar]:
    """纯 CV:按槽位裁切 → SIFT 识别 → BenchChar 列表(离线可测,无 ctx 依赖)。

    :param slots: ``[(slot_idx, rect), ...]``;rect = 1080p 槽位矩形(来自 screen_info 或硬编码)。
    :param row: ``"front"`` / ``"back"``(已上阵排)→ BenchChar.position_pref;``""``(备战栏)→ 用
        角色固有偏好(未上阵)。
    :return: 命中角色的 BenchChar 列表(空槽 / 低内点 / 歧义 / 非 roster → 跳过,不进列表)。

    每槽:裁 ``screen[y1:y2, x1:x2]`` → ``identify_character``(SIFT 对脸库)→ ``resolve_char_name``
    → 规范名。faction 取角色首阵营(粗;权威阵营计数看 board OCR);star = ``read_star``(立绘底部
    金星计数)。
    """
    out: list[BenchChar] = []
    for slot_idx, rect in slots:
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        avatar_id, _inliers = identify_character(crop, templates)
        if avatar_id is None:
            continue
        name = resolve_char_name(avatar_id)
        if name is None:
            continue
        # 开拓者形态按排归一(用户 2026-08-16):前台=记忆/后台=欢愉;立绘库两形态覆盖不均时
        # SIFT 可能按旧立绘判成另一形态 —— 已上阵排是权威(row 即真实排),归一消歧。
        from sr_od.application.currency_war.cw_chars import (
            is_trailblazer,
            trailblazer_form,
        )
        if row and name and is_trailblazer(name):
            name = trailblazer_form(name, row)
        ch = get_char(name)
        out.append(BenchChar(
            slot=slot_idx,
            char_id=name,
            # '?'=未知(名不在注册表);''=已知无阵营(白厄类;与 shop._tracked_bench_chars 同语义)
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
            star=read_star(crop),            # 立绘底部金星计数(1/2/3 星;见 read_star)
            position_pref=row if row else (ch.position_pref() if ch is not None else 'back'),
        ))
    return out


def _ctx_slots(ctx: SrContext, prefix: str, count: int) -> list[tuple[int, Rect]]:
    """从 ctx screen_info 取 ``{prefix}-1..{count}`` 的 (slot_idx, rect);area 缺失 → 跳过。"""
    out: list[tuple[int, Rect]] = []
    for i in range(1, count + 1):
        rect = _area_rect(ctx, f'{prefix}-{i}')
        if rect is not None:
            out.append((i, rect))
    return out


def read_deployed_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates,
                        deploy_cap: int | None = None) -> list[BenchChar]:
    """舞台已上阵角色(前排 4 + 后排 N)→ list[BenchChar](position_pref=front/back)。

    空槽 / 未识别 → 不进列表。用途:离线重建 / 漂移恢复(**不进 read_game_state**;见模块 docstring)。
    deploy_cap(r75 布局表):后排槽位数,选 ``cw_back_layout.BACK_ROW_LAYOUTS`` 布局 ——
    **槽位变化时布局整体重排非尾部追加**(用户 2026-08-19 口述;8 槽实拍位1 x428 vs
    6 槽 x604),旧固定「后排-1..6」在 7/8 槽局全错位。None → 从帧读 ``read_deploy_cap``,
    读不到 → 6 槽基线(旧行为)。
    """
    from sr_od.application.currency_war.cw_back_layout import (
        back_row_slot_rects_ctx,
        fallback_back_slots,
    )
    from sr_od.application.currency_war.cw_observation import read_deploy_cap
    if deploy_cap is None:
        deploy_cap = read_deploy_cap(ctx, screen)
    back_slots = back_row_slot_rects_ctx(ctx, deploy_cap or 6) or fallback_back_slots()
    # r77d 布局停机钩子(用户 2026-08-20 定调:7/9 槽**要停机 + 现场拖角色验证**):
    # 无档布局 ≠ 只存帧离线测 —— 离线暗框检测有背景噪声风险(8 槽首版 grounding
    # 误换算教训),真值坐标必须现场交互闭环(拖角色到各槽 → 逐槽识别 → 详情面板
    # 锚定)。遇无档 cap → 存帧(哈希去重)+ sentinel flag + **停机保画面**,AI 现场按
    # flag 流程执行;档位补齐(upsert 后排N槽-1..N + _LAYOUT_PREFIX 登记)后不再触发。
    try:
        from sr_od.application.currency_war.cw_back_layout import (
            _layout_prefixes,
            effective_back_slots,
        )
        _cap = deploy_cap or 6
        # r81:后排槽数 = max(6, cap)(cap=5 实测仍 6 槽,花火/姬子 SIFT 命中基线)→
        # 只对「有效槽数无档」停机(cap≤6 恒基线,不停机 —— 旧 `>4 且 ≠6` 会误停 cap5)。
        _slots_n = effective_back_slots(_cap)
        if ctx.run_context is not None and _slots_n not in _layout_prefixes():
            from pathlib import Path as _P

            from one_dragon.utils.log_utils import log as _log
            from sr_od.application.currency_war.cw_observe import cw_shot_unique
            _shot = cw_shot_unique(screen, f'back_layout_{_slots_n}slots')
            if _shot is not None:
                _P('.debug/temp/currency_war/back_layout_stop_hook.flag').write_text(
                    f'后排布局停机钩子(用户 2026-08-20 指示):deploy_cap={_cap}'
                    f'(有效后排 {_slots_n} 槽)布局未建档。\n'
                    f'现场验证流程(参照 8 槽闭环 r76):\n'
                    f'1. 暗框检测初测槽位 x(空槽矩形 center 序列);\n'
                    f'2. 关商店 → 拖 bench 角色到各槽(阵容满则拖前排/横拖挪位)逐位识别验证;\n'
                    f'3. 点 1-2 个占位槽开详情面板锚定(交互实锤);\n'
                    f'4. upsert_screen_area 后排{_slots_n}槽-1..{_slots_n}(真值);\n'
                    f'5. cw_back_layout._LAYOUT_PREFIX 登记;\n'
                    f'6. 删本 flag + 重启 MCP server。\n'
                    f'截图: {_shot}', encoding='utf-8')
                _log.info('[cw-hook][layout] 后排 %d 槽无档(cap=%s)→ 停机现场拖拽验证(截图 %s)',
                          _slots_n, _cap, _shot)
                ctx.run_context.stop_running()
    except Exception:   # noqa: BLE001  钩子 best-effort,绝不阻塞身份读取
        pass
    return (identify_slots(screen, templates, _ctx_slots(ctx, '前排', 4), 'front')
            + identify_slots(screen, templates, back_slots, 'back'))


def read_bench_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates) -> list[BenchChar]:
    """备战栏角色(9 槽)→ list[BenchChar](position_pref=角色固有偏好,未上阵)。

    空槽 / 未识别 → 不进列表。用途:离线重建 / 漂移恢复。
    """
    chars = identify_slots(screen, templates, _ctx_slots(ctx, '备战栏', 9), '')
    # [停机钩子·临时,建档后删(用户 2026-08-18 定调)]召唤物/特殊形态建档:
    # 槽位占用(slot_occupied CV)真 + SIFT 认不出 = 未建档单位现身 → **停机保画面**,
    # AI 现场点该槽 → 右侧详情面板出角色名(身份 ground truth 源)+ 外观对照 → 定名建档
    # (portrait_plaza/<名>/raw.png 白框法裁剪 + roster 核条目)→ 删本钩子。
    # ⚠️ r78 新误触模式守卫:**角色详情面板开着时跳过** —— 详情面板(x1400+)盖住 bench
    # 右端(slot7-9),被遮槽 SIFT 看到的是面板 UI(实锤:summon_unknown__e1fb06c8 帧
    # slot9 裁出的是搜索图标,详情面板上还明晃晃写着「藿藿」本尊)→ 假「占用未识别」
    # 反复停机。详情面板 OCR 锚(装备推荐/出售按钮区)在场 → 本帧不判。
    # ⚠️ 防抖(r17-r31 教训):同内容哈希只停一次(cw_shot_unique 返 None = 已采过 → 不再停),
    # 防同一单位整局反复停机;哨兵文件自描述。
    try:
        from sr_od.application.currency_war.cw_obs_core import _ocr
        from sr_od.application.currency_war.cw_observe import cw_shot_unique
        # r82 守卫修正:「按钮-装备推荐」area 在「货币战争-备战-角色详情」子屏,
        # _area_rect 默认查备战屏恒 None → 旧守卫形同虚设(r82 实锤:停机帧上面板
        # 开着仍停机)。枚举两屏查,任一命中即面板开 → 本帧不判。
        _panel_open = False
        for _scr_name in ('货币战争-备战-角色详情', '货币战争-备战'):
            _r = _area_rect(ctx, '按钮-装备推荐', _scr_name)
            if _r is not None and _ocr(ctx, screen, _r):
                _panel_open = True
                break
        if _panel_open:
            return chars
        # r100j 修正(用户纠偏:商店开态**不**挤压备战席;slot1「开启」=占槽物品的
        # 开启按钮,非购买经验 UI)。撤掉昨天的商店开态静默跳过(它掩盖真问题:
        # 真召唤物在商店开时占槽也永远发现不了)。真根因 = 该占槽物品是箱/卡包的
        # **变体渲染**,find_supply_boxes/find_tomes/宽松互斥全没认出 → 漏到本钩子。
        # 处理:承认「占用但非角色非已知物品」的判定职责就在本钩子(它就是干这个的),
        # 但停机策略降级为**留证不停机**(对齐 r34 shop_unknown 先例:反复停机阻断
        # 实跑,留证给 AI 离线补模板后再恢复停机)。已采 4 帧足已定位,恢复运行优先。
        # r85b:补给箱/典籍槽排除 —— 箱/典籍占 bench 槽是已知常态(掉箱占席),SIFT
        # 认不出它们是设计内(非角色)→ 不停机(VLM 实锤:第4局 slot2「蓝色卡片叠放
        # +开启」= 卡包/补给箱,旧钩子反复停机骚扰)。
        # r85c:find_supply_boxes 的 0.6 硬门漏检**低分渲染**(卡包变体 TM 0.541 实锤)
        # → 钩子内用宽松互斥对拍:箱分 > 0.45 且 ≥ 典籍分 = 物件槽(比 0.6 门宽,只
        # 用于排除停机;read_supply_boxes 生产口径不变,防典籍误判由互斥保证)。
        _bench_slots9 = _ctx_slots(ctx, '备战栏', 9)
        _obj_slots: set[int] = {i for i, _p in find_supply_boxes(screen, _bench_slots9)}
        _obj_slots |= {i for i, _p in find_tomes(screen, _bench_slots9)}
        _bx_g, _tm_g = _get_supply_box_gray(), _get_tome_gray()
        if _bx_g is not None:
            _gray_full = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
            for _i, _rect in _bench_slots9:
                if _i in _obj_slots:
                    continue
                _c = _gray_full[_rect.y1:_rect.y2, _rect.x1:_rect.x2]
                if _c.shape[0] < _bx_g.shape[0] or _c.shape[1] < _bx_g.shape[1]:
                    continue
                _bs = cv2.minMaxLoc(cv2.matchTemplate(_c, _bx_g, cv2.TM_CCOEFF_NORMED))[1]
                if _bs <= 0.45:
                    continue
                _ts = (cv2.minMaxLoc(cv2.matchTemplate(_c, _tm_g, cv2.TM_CCOEFF_NORMED))[1]
                       if (_tm_g is not None and _c.shape[0] >= _tm_g.shape[0]
                           and _c.shape[1] >= _tm_g.shape[1]) else 0.0)
                if _bs >= _ts:
                    _obj_slots.add(_i)   # 箱/卡包类物件(低分渲染),排除
        _named = {c.slot for c in chars} if chars else set()
        for _slot, _rect in _bench_slots9:
            if _slot in _named or _slot in _obj_slots:
                continue
            from sr_od.application.currency_war.currency_war_cv import slot_occupied
            if slot_occupied(screen, _rect.x1 + (_rect.x2 - _rect.x1) // 2,
                             _rect.y1 + (_rect.y2 - _rect.y1) // 2):
                _shot = cw_shot_unique(screen, 'summon_unknown')
                if _shot is not None and ctx.run_context is not None:
                    from pathlib import Path as _P

                    from one_dragon.utils.log_utils import log as _log
                    _cx = (_rect.x1 + _rect.x2) // 2
                    _cy = (_rect.y1 + (_rect.y2) - _rect.y1) // 2
                    _P('.debug/temp/currency_war/summon_stop_hook.flag').write_text(
                        '召唤物/物品停机钩子:备战栏 slot'
                        f'{_slot} 占用但 SIFT 未识别(非角色非已知箱/典籍)。\n'
                        f'现场处理流程(必须当天做完,别降级绕过):\n'
                        f'1. 点槽位 ({_cx},{_cy}) → 看内容(物品会直接开启/弹面板,角色出详情)\n'
                        f'2. 若为物品变体:截图 → 补进 find_supply_boxes/find_tomes 模板或新增物品类目\n'
                        f'   (r100j 教训:卡包变体 TM 0.54 漏检;物品占槽是常态,识别不全就停机等建档)\n'
                        f'3. 若为真召唤物:portrait_plaza/<名>/raw.png 建模板(白框裁 '
                        f'{(_rect.x1, _rect.y1, _rect.x2, _rect.y2)})→ roster 核条目\n'
                        f'4. 建档完成 → 本钩子自然不再触发(flag 自删);别把钩子降级留证——'
                        f'未建档物品被当空槽/普通占用乱操作比停机更贵(2026-08-20 用户纠偏)。\n'
                        f'截图: {_shot}', encoding='utf-8')
                    _log.warning('[cw!][summon] 备战 slot%s 占用未识别(物品变体或召唤物)'
                                 '→ 停机现场建档(别降级;处理流程见 flag): %s', _slot, _shot)
                    ctx.run_context.stop_running()
                break
    except Exception:   # noqa: BLE001  采集 best-effort,绝不阻塞身份读取
        pass
    return chars


# ===== 补给箱识别(备战栏槽位;2026-08-14 首见实机) =====
# 奖励节点清关后右侧面板出「奖励球」(=晶矿,factions 晶矿条目:开启后可能获金币/角色/装备/稀有物品)。点球开启:
# 内容即时入账(金币/装备),或掉「补给箱」**落备战席占 1 槽**(箱子手提箱 icon + 「开启」文字 + 蓝底,
# 点它开箱 → 腾槽 + 得内容)。备战席满时球点不动(球可能给角色/箱,都要占席)→ **开箱优先于点球**。
# 箱子是固定 UI icon → 灰度 TM 足够(SIFT 无必要);分离度(2026-08-14 实测):箱槽 1.0 vs 角色槽 ≤0.242。
# ⚠️ 拖动后选中态(蓝光效环)降 TM 至 ~0.65-0.69(2026-08-14 拖动实测;点空白取消选中 → 0.931 恢复,跨槽位稳)
# → 阈值取 0.6:覆盖选中态,噪声槽 0.242 仍有 ~2.4× 分离。bench 满判定:箱占席但非角色,read_bench_chars 读不到
# → 硬信号以「备战席已满」OCR 为准。
_SUPPLY_BOX_TM_THR: float = 0.6
_supply_box_gray: MatLike | None = None
_supply_box_loaded: bool = False
# 秘密典籍(2026-08-16 M45 建档,用户指导):投资策略「秘密典籍」给的道具,红金典籍 icon+
# 「开启」,占备战席 1 槽(类补给箱);点两次(选中→开启)→ 星徽四选一(loop 0i 接管)。
# 分离度实测:典籍 vs 补给箱互 TM 0.481(阈值 0.6 下互不误认);同读法同槽位模型。
_tome_gray: MatLike | None = None
_tome_loaded: bool = False


def _get_tome_gray() -> MatLike | None:
    """加载秘密典籍模板灰度图(模块级缓存;``assets/template/currency_war/supply/秘密典籍.png`` 缺 → None)。

    ⚠️ 换模板文件需重启 server(module 级缓存;与节点模板/yml 同型坑)。
    """
    global _tome_gray, _tome_loaded
    if not _tome_loaded:
        _tome_loaded = True
        p = Path(__file__).resolve().parents[4] / 'assets' / 'template' / 'currency_war' / 'supply' / '秘密典籍.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _tome_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _tome_gray


def _get_supply_box_gray() -> MatLike | None:
    """加载补给箱模板灰度图(模块级缓存;``assets/template/currency_war/supply/补给箱.png`` 缺 → None)。"""
    global _supply_box_gray, _supply_box_loaded
    if not _supply_box_loaded:
        _supply_box_loaded = True
        p = Path(__file__).resolve().parents[4] / 'assets' / 'template' / 'currency_war' / 'supply' / '补给箱.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _supply_box_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _supply_box_gray


def find_supply_boxes(screen: MatLike, slots: list[tuple[int, Rect]]) -> list[tuple[int, Point]]:
    """纯 CV 核心:槽位 rect 列表内 TM 匹配补给箱 → ``[(slot_idx, 槽 center)]``(点「开启」用)。

    模板 ~97x118 < 槽 rect ~113x134 → 逐槽 matchTemplate。空槽/角色槽远低于阈值不命中。
    可离线硬编码 rect 测(同 ``identify_slots`` 分层约定)。
    """
    tm = _get_supply_box_gray()
    if tm is None:
        return []
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    out: list[tuple[int, Point]] = []
    for idx, rect in slots:
        crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
        if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
            continue
        r = cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED)
        _, mx, _, _ = cv2.minMaxLoc(r)
        if mx >= _SUPPLY_BOX_TM_THR:
            out.append((idx, Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)))
    return out


def read_supply_boxes(ctx: SrContext, screen: MatLike) -> list[tuple[int, Point]]:
    """备战栏补给箱(``备战栏-1..9``)→ ``[(slot_idx, 开启 center)]``(开箱 op 用;2026-08-14 首见机制)。"""
    return find_supply_boxes(screen, _ctx_slots(ctx, '备战栏', 9))


def find_tomes(screen: MatLike, slots: list[tuple[int, Rect]]) -> list[tuple[int, Point]]:
    """纯 CV 核心:槽位 rect 内 TM 匹配秘密典籍 → ``[(slot_idx, 槽 center)]``(点开启用)。

    与 ``find_supply_boxes`` 同法,外加**互斥判定**(r11 修,M55 P2 活锁根因):典籍命中需
    同时 ①典籍 TM ≥ 0.6 且 ②典籍分 > 箱分(同槽双模板对拍)。实测误检帧(补给箱槽):
    典籍 0.558/箱 0.926 —— 旧版 0.558<0.6 本就该拦,但光照/选中态可抬分,双条件保证
    箱永远不被认成典籍(0.926>0.558 互斥性强)。典籍点两次(选中→开启)→ 星徽四选一
    弹窗(loop 0i 接管选卡)。
    """
    tm = _get_tome_gray()
    bx = _get_supply_box_gray()
    if tm is None:
        return []
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    out: list[tuple[int, Point]] = []
    for idx, rect in slots:
        crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
        if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
            continue
        r = cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED)
        tome_score = cv2.minMaxLoc(r)[1]
        if tome_score < _SUPPLY_BOX_TM_THR:
            continue
        if bx is not None and bx.shape[0] <= crop.shape[0] and bx.shape[1] <= crop.shape[1]:
            rb = cv2.matchTemplate(crop, bx, cv2.TM_CCOEFF_NORMED)
            box_score = cv2.minMaxLoc(rb)[1]
            if box_score >= tome_score:   # 箱分更高 = 这是箱不是典籍
                # r15 review 留证(选中态真典籍余量薄 0.06-0.14):拒绝时记双分数——若真典籍被
                # 选中态光效不对称抬升箱分误拒(delta<0.15 时),日志可见即可闭环(margin/取消选中复读)。
                if tome_score - box_score < 0.15:
                    from one_dragon.utils import log_utils
                    log_utils.log.info(
                        f'[cw!][find_tomes] 槽{idx} 互斥拒绝(余量薄): '
                        f'tome={tome_score:.3f} box={box_score:.3f}(选中态真典疑?采到即修)')
                continue
        out.append((idx, Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)))
    return out


def read_tomes(ctx: SrContext, screen: MatLike) -> list[tuple[int, Point]]:
    """备战栏秘密典籍(``备战栏-1..9``)→ ``[(slot_idx, center)]``(点两次开启 → 星徽四选一)。"""
    return find_tomes(screen, _ctx_slots(ctx, '备战栏', 9))


# 备战席溢出带(奖励角色悬浮位;2026-08-16 用户实证 star2__540a8be3):备战栏正上方
# y 700-845 带,溢出立绘挂最右槽上方(实测赛飞儿 x~1362-1430)。
_OVERFLOW_BAND: tuple[int, int, int, int] = (370, 700, 1500, 845)


def count_overflow_chars(screen: MatLike) -> int:
    """备战席溢出角色数(奖励给角色在席满时悬浮于备战栏上方;机制见 gameplay doc)。

    检测:溢出带 Canny 边缘 x 投影 → 宽 >30px 的高密度段数 = 立绘数(实测赛飞儿段
    x1362-1430 宽 68px;空带无段)。纯 CV(无 ctx);读不清 → 0(保守,不误报腾席)。
    腾席决策用:破满需卖 ≥(溢出数+1)(卖 1 个溢出落 1 个,净空位 0)。
    """
    x1, y1, x2, y2 = _OVERFLOW_BAND
    band = cv2.cvtColor(screen[y1:y2, x1:x2], cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(band, 60, 150)
    col = edges.mean(axis=0)
    th = col.mean() + col.std()
    runs = []
    in_run = False
    for i, v in enumerate(col):
        if v > th and not in_run:
            start, in_run = i, True
        elif v <= th and in_run:
            if i - start > 30:
                runs.append((start, i))
            in_run = False
    return len(runs)


# ===== 奖励球识别(奖励节点清关后 区域-奖励 面板;2026-08-14 live 建档) =====
# 奖励球 = 晶矿(factions 晶矿条目:开启后可能获金币/角色/装备/稀有物品)。通关奖励节点后备战右侧
# 面板出现球形奖励(实测 1-8 清关:1 大金球[r~44] + 5 蓝球[r~32] + 2 灰球[r~18])。点球即开启:
# 金币/装备即时入账;角色/补给箱落备战席占槽;**备战席满时球点不动**(先开箱腾席再点球)。
#
# 检测 = HoughCircles(颜色分割不可行:**背景与蓝球 HSV 几乎同值** —— 实测 蓝球 H111-113 S195-209
# V253-255 vs 背景 H119-120 S172-175 V224-225,mask 无分离度)。球是圆形发光体,背景是点阵纹理
# 无大圆 → 圆检测天然分离。空面板实测 0 误报(点阵/按钮均不触发)。
# 颜色分类(圆心 HSV):金 H15-35+S>80 / 灰 S<70 / 其余=蓝。r 可辅助(金~44/蓝~32/灰~18)。
_REWARD_HOUGH_DP: float = 1.2
_REWARD_HOUGH_PARAM2: float = 40
_REWARD_MIN_R: int = 15
_REWARD_MAX_R: int = 60
# 兜底 rect = screen_info「区域-奖励」缺时用(2026-08-14 实测;shop 关态面板主体)。
# ⚠️ 已知未验边界(用户 2026-08-14 提示):右侧 owned 装备很多时会溢出覆盖奖励区(装备多列
# 网格 col1-5 左溢 → 遮球)→ 本检测可能漏球/误报。**该场景难触发,待用户提供截图验证后再定防护**
# (候选:检测装备区占用列数收窄 panel rect / 装备 icon TM 排除域)。未验证前消费方保持保守。
_REWARD_PANEL_FALLBACK: tuple[int, int, int, int] = (1257, 140, 1662, 493)


def find_reward_spheres(screen: MatLike, panel_rect: Rect) -> list[tuple[str, Point, int]]:
    """纯 CV 核心:奖励面板内 HoughCircles 检球 → ``[(颜色, center, radius)]``(点球用)。

    颜色 = 'gold' | 'blue' | 'gray'(圆心 HSV 分类;gold=高价值晶矿)。radius 可辅助优先级
    (金球大)。可离线硬编码 rect 测(同 ``find_supply_boxes`` 分层约定)。
    """
    x1, y1, x2, y2 = panel_rect.x1, panel_rect.y1, panel_rect.x2, panel_rect.y2
    panel = screen[y1:y2, x1:x2]
    if panel.size == 0:
        return []
    gray = cv2.medianBlur(cv2.cvtColor(panel, cv2.COLOR_RGB2GRAY), 3)  # 框架 screen RGB(⚠️ 非 BGR;HoughCircles 形状检测对权重不敏感)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=_REWARD_HOUGH_DP, minDist=35,
        param1=100, param2=_REWARD_HOUGH_PARAM2,
        minRadius=_REWARD_MIN_R, maxRadius=_REWARD_MAX_R,
    )
    if circles is None:
        return []
    hsv = cv2.cvtColor(panel, cv2.COLOR_RGB2HSV)  # RGB 输入必须 RGB2HSV(BGR2HSV 红/蓝 H 错位 → gold 分类失败,2026-08-14 webp fixture 实测)
    out: list[tuple[str, Point, int]] = []
    for cx, cy, r in circles[0]:
        ix, iy = int(cx), int(cy)
        if not (0 <= ix < panel.shape[1] and 0 <= iy < panel.shape[0]):
            continue
        h, s, _v = hsv[iy, ix]
        if 15 <= h <= 35 and s > 80:
            color = 'gold'
        elif s < 70:
            color = 'gray'
        else:
            color = 'blue'
        out.append((color, Point(ix + x1, iy + y1), int(r)))
    out.sort(key=lambda t: (t[1].x, t[1].y))
    return out


def read_reward_spheres(ctx: SrContext, screen: MatLike) -> list[tuple[str, Point, int]]:
    """奖励面板晶矿球(screen_info「区域-奖励」)→ ``[(颜色, center, radius)]``(点球 op 用)。"""
    rect = _area_rect(ctx, '区域-奖励')
    if rect is None:
        rect = Rect(*_REWARD_PANEL_FALLBACK)
    return find_reward_spheres(screen, rect)


# ===== 穿戴装备识别(below-avatar mini icon;D-45/D-46)=====
def avatar_to_below(rect: Rect, half_w: int = 70, dy: int = 14, half_h: int = 33) -> Rect:
    """槽位 avatar rect → below-avatar icon 搜索 rect(avatar 底部下方;穿戴装备 icon 显示处)。

    前排 avatar ``[.,329,.,467]`` → below center cy=481(=y2+14;D-49 CV 实测 icon y 中心);后排/备战席
    avatar 底部 y2 不同,below 自动跟随(dy 相对 avatar 底部)。搜索区 ±half_w/half_h 覆盖固定 ~32px icon
    (D-49:icon 不随装备数变)。**half_w=70**:3件 icon 横排跨度 ~86px(cx±43),55 会切边缘 icon(D-49 修);
    70 覆盖3件且不含邻槽(front-2 在 cx+~144 外)。
    """
    cx = (rect.x1 + rect.x2) // 2
    cy = rect.y2 + dy
    return Rect(cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def read_row_equipped(
    ctx: SrContext,
    screen: MatLike,
    tmpl_grays: dict[str, MatLike],
    prefix: str,
    count: int,
) -> dict[int, list[str]]:
    """某排(前排/后排/备战栏)每槽 below-avatar 已穿装备 → ``{slot_idx: [装备名]}``(纯读)。

    从 ctx screen_info 取 ``{prefix}-1..{count}`` avatar rect → ``avatar_to_below`` → ``read_equipped_below``。
    空槽 / 无命中 → 该 slot 不在 dict。与 ``read_deployed_chars``(角色身份)互补:角色 + 装备 = 完整槽位态。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer(并发安全)。
    """
    below_rects = [(idx, avatar_to_below(r)) for idx, r in _ctx_slots(ctx, prefix, count)]
    return read_equipped_below(screen, tmpl_grays, below_rects)
