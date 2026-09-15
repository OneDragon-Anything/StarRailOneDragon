"""货币战争 **备战屏 视觉身份观测**(SIFT,非 OCR)。

与 ``cw_observation``(OCR 字段)互补:本模块读 OCR 看不见的**身份** —— 备战栏 / 舞台槽内角色
立绘 → 规范名(``read_deployed_chars`` / ``read_bench_chars``),用 ``currency_war_char_id`` 的
SIFT 匹配器对模板库(生产用 ``currency_war/portrait_plaza`` 官方立绘库,见 ``currency_war_char_id`` docstring)。

**与 bot 跟踪的关系**(设计):``CwSimFrame.deployed`` / ``bench`` 默认由 **bot 跟踪**(buy/deploy
动作推演,``simulate`` 维护,见 ``cw_state``)—— plan-time 快、无需 SIFT。本模块的视觉 reads 是
**独立旁路**,用途:① 离线从截图重建 CwSimFrame(测试 / replay,无需跑 bot);② bot 跟踪漂移时
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

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.data.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
from sr_od.application.currency_war.obs.currency_war_char_id import (
    AvatarTemplates,
    identify_character,
    load_avatar_templates,
)
from sr_od.application.currency_war.obs.cw_equipment import read_equipped_below
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
        base = get_project_root() / 'assets' / 'template'
        portrait_dir = base / 'currency_war' / 'portrait_plaza'   # 官方立绘库(plaza big_icon 烘焙,含 mask;唯一库,旧手采库已删 2026-08-17)
        if not portrait_dir.is_dir():
            return None
        templates = load_avatar_templates(portrait_dir)
        ctx.cw_portrait_templates = templates
    return templates


# 金星(亮金色五角星)HSV 范围(CV 采样 4 样本 star_front_1..4 标定 2026-08-11;crop=RGB)。
# 亮金色 ≈ #FFD700:H 黄~橙(OpenCV 0-180),高 S 高 V。立绘金色装饰(衣服/腰带)也命中 → 靠位置(底部)过滤。
# HSV 金色范围;**V>150** 只抓自发光亮金星,滤暗金衣服装饰(2026-08-13 实测标定):
# 前排角色立绘底部有大量暗金衣服(V80-150)淹没金星,旧 V>80 把衣服抓成 area1279 大块致检测崩溃。
_STAR_GOLD_LO: tuple[int, int, int] = (10, 40, 150)
_STAR_GOLD_HI: tuple[int, int, int] = (45, 255, 255)
# TM 匹配阈值(2026-08-13:0.45)。**根因实测(ADR-0116)**:第2星 TM val 系统性低于第1星(第1 0.62-0.69 / 第2
# 0.45-0.58)—— 两星**紧贴遮挡**,第2星 mask 不完整 → val 偏低;各排一致(星尺寸 17-19px 跨排相同,**非缩放
# 失配**,多模板 per 排无用,ADR-0116 实测推翻)。val 随紧贴程度变(后排-6 最紧 val~0.45 / 后排-3 0.51)。
# thresh 0.45 = **真第2星(≥0.45)与噪声装饰(<0.40)的分界**,非打地鼠补丁。验:立绘库 0/71 + 全 fixture
# 无新 FP + 所有 2★ 槽读 2(0.40 才过数噪声,余量 ~0.05)。迭代史:0.55→0.50(后排-3)→0.45(后排-6)。
_STAR_TM_THRESH: float = 0.45
# peak 轮廓圆度下限(2026-08-13 实测标定:0.25)。原 0.35 太紧 —— 真金星 circ 实测 0.34-0.50(随槽位
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
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'star' / 'star_gold_tmpl.png'
        if p.exists():
            _STAR_TMPL_CACHE = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    return _STAR_TMPL_CACHE


def read_star(crop: MatLike) -> int:
    """数角色立绘底部金星(星级);``crop`` = 槽位 RGB crop(含立绘 + 底部金星)。

    金星 = **四角星**(十字星 ✦,自发光亮金黄),立绘**底部中央**(y > 0.65h);1/2/3 星 = N 颗并排。
    **TM 模板匹配法**(替旧轮廓法):HSV V>150 抓亮金星(滤暗金衣服)→ 四角星模板
    matchTemplate → NMS 分离紧贴(2 星 gap 小)→ peak 局部 area/aspect/circ 验证滤残余装饰。

    旧轮廓法对 **2 星紧贴**(连通成大域 area>600 上限漏)+ **前排衣服淹没**(area1279
    把金星淹没)结构性失效。TM 各星独立滑窗匹配,紧贴亦分,V>150 滤衣服让 mask 干净 —— 治本。
    验证(2026-08-13):立绘库 71 张 0 误判 + 各位置 2星(前排-3/后排-3/备战-4)读 2 + 三月七 2星 +
    1星各槽稳读 1。**thresh 0.45(终值标定见 ADR-0116)**:第2星 TM val 系统性低于第1星(第1 0.62-0.69 / 第2 0.45-0.58)——
    两星**紧贴遮挡**致第2星 mask 不完整 → val 偏低;**各排星尺寸 17-19px 相同(非缩放失配,多模板 per 排实测无用,
    ADR-0116 推翻该假设)**。val 随紧贴程度变(后排-6 最紧 ~0.45)。0.45 = 真第2星(≥0.45)与噪声(<0.40)分界。
    验:立绘库 0/71 + 全 fixture 无新 FP + 所有 2★ 读 2(含各排边槽)。
    **circ 放宽(0.35→0.25)**:原 circ>0.35 太紧 —— 备战-9 边槽同颗金星 circ 渲染到 0.34 被误拒 → 2星读 1;
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
    # circ 下限见 _STAR_CIRC_MIN(0.35→0.25,原误拒备战-9 边槽真金星)。
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


# ===== 升星预览✦(商店牌头顶;W104 发现 / W282 接线,ADR-0416)=====
# 商店牌 art 顶部「已持同名同星副本数」✦显影 = merge_progress 份数的游戏内视觉印证
# (迭代档案 W104:买第 3 张即 3合1 升星,✦ 数 = 已持份数)。
# ⚠️ 不能复用金星 _STAR_GOLD(10-45/V>150):fixture 实测该窗口把亮色立绘背景/金发全部吃进
# (card5 顶带 mask 连成 146px 大域,card1 砂金金发 3 个大域)。✦ 是自发光更烈的橙金:
# 核心样本 H=25-30 / S≥60 / **V=255 饱和截断**(背景 V 163-198 / 金发 V≤243),独立严窗口。
_PREVIEW_GOLD_LO: tuple[int, int, int] = (22, 60, 248)
_PREVIEW_GOLD_HI: tuple[int, int, int] = (40, 255, 255)
# ✦ 只出现在牌 art 顶部(裁切 rect y1=70,✦ 带本地 y 0-25 / 全高 190 → 0.25 倍冗余盖动态偏移)。
_PREVIEW_BAND_RATIO: float = 0.25
# 2026-09-12 浮动动画漏检事故裁决(用户供帧 _886595/_886604,650ms 相位对):
# ✦ 上下浮动+明暗脉动 → 严窗口 mask 掉半(577→284px)、刚性 TM 相关性崩
# (0.93→0.28 < 0.60)漏检 2/4 帧态;shop_open card5 金域 646px 当年被 TM
# 标定误判「金发噪声」负样本,实为漏检 ✦(用漏检分布定阈值 = 循环论证)。
# 治本 = 连通域几何计数替代刚性 TM(下游 compare_merge_preview 只消费 >0 布尔;
# ✦ 粘连体按域宽估份数:单✦宽 ~29 / 双✦粘连宽 ~58,暗相位高度变薄宽度不变)。
_PREVIEW_AREA_MIN: int = 60
_PREVIEW_AREA_MAX: int = 700
_PREVIEW_DOMAIN_W_MAX: int = 70
_PREVIEW_SINGLE_W_MAX: int = 40
_PREVIEW_MAX_COUNT: int = 2


def read_merge_preview(crop: MatLike) -> int:
    """数商店牌头顶升星预览✦(= 已持同名同星副本份数;买第 3 张即 3合1,W104/ADR-0416)。

    ``crop`` = 商店牌-N area 的 RGB crop(read_shop_cards 同源裁切)。算法 =
    HSV 严自发光窗口 → 顶部带二值 mask → **连通域几何计数**(2026-09-12 起,
    替换刚性 TM:✦ 上下浮动+明暗脉动使 mask 形变,TM 相关性崩 → 漏检 2/4
    帧态,见常量块事故注)——合格域(面积/宽度门)计数,粘连双✦按域宽估值。
    **无合格域返 0 非 fallback**——0 = 「无✦」是合法语义(该牌无已持副本),
    与 read_star「角色必有星」的 fallback 1 性质不同。

    :return: ✦ 指示份数(0-2);空图 → 0。
    """
    if crop is None or crop.size == 0:
        return 0
    h, w = crop.shape[:2]
    band = crop[0:int(h * _PREVIEW_BAND_RATIO), :]
    hsv = cv2.cvtColor(band, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, _PREVIEW_GOLD_LO, _PREVIEW_GOLD_HI)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    count = 0
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        dom_w = int(stats[i, cv2.CC_STAT_WIDTH])
        if not (_PREVIEW_AREA_MIN <= area <= _PREVIEW_AREA_MAX):
            continue
        if dom_w > _PREVIEW_DOMAIN_W_MAX:
            continue
        count += 1 if dom_w <= _PREVIEW_SINGLE_W_MAX else 2
    return min(count, _PREVIEW_MAX_COUNT)


# ===== 合成特效帧态门(W292/ADR-0420,W285 抽样批3)=====
# 病灶(W285 §三 star 层,抽样 2/2 采新帧全错):read_star 会采在 3合1 合成
# 星爆动画/拖拽过渡窗内(特效遮挡第 2 星 → 读 1),对账侧「连续 2 次回退才采新」
# 防抖会被**持续 ≥2 帧的动画窗**骗过(第 2 帧仍在窗内 → 假确认采新 1★ 毒化)。
# 修法:回退**采新确认前**先过本帧态门——特效帧在场上 = 读数不可信窗,保旧且
# **不推进**防抖计数(冻结,非清零:动画结束后的干净回退帧仍能确认)。
# 与既有回退防抖(r34/W292 前是逐角色计数)的关系:防抖管「时间维」(单帧疑云
# 下帧确认),本门管「帧态维」(本帧物理上不可信)——正交合并,防抖主干不动。
#
# 两签名均 4 帧正样本(W285 判读)+ 全部可用负样本标定(RGB 约定,生产
# read_image 同约定;2026-09-05 离线标定,脚本 .debug/temp/cw_w292_calib5.py):
#
# 1. **合成星爆粒子**(正样本 obs_conflict_star__a61848f0:前排带金色四角星
#    爆点):前排棋盘带内严橙金窗口(复用升星预览✦的 _PREVIEW_GOLD,自发光
#    V≥248)连通域(≥9px)计数。标定:星爆帧 460px/8 个 ≥9px 域;负样本
#    4 帧(稳定×2/8 格局/7 格局)gold_px 0-50 但 **≥9px 域全为 0**(卡面
#    金色装饰被窗口与面积双门滤净)→ 阈 3 = 正样本下限 8 的 0.375×、负样本
#    上限 0 之上,不贴任何一侧。
# 2. **「备战席已满」红色警告横幅**(正样本 obs_conflict_star__46d292eb:
#    拖拽合成过渡帧,拖拽中浮空卡 + 满席红斜纹空槽 + 横幅):横幅带内
#    R−max(G,B)>40 像素占比。标定:拖拽帧 0.138;其余 6 帧全部 ≤0.013
#    (红发角色卡不与横幅带重叠)→ 阈 0.06 居中(正 2.3×/负 4.6× 余量)。
# 边界(如实):两签名各只有 1 个正样本帧,阈值留了倍数余量但属**单正样本
# 标定**;星爆若发生在后排/拖拽过渡无满席横幅的形态未采到 —— 漏检时既有
# 防抖仍兜底(门是加强不是替代),误检代价 = 多保旧一帧(自愈)。复现新形态
# 再扩签名。
_MERGE_EFFECT_FRONT_BAND: tuple[int, int, int, int] = (400, 420, 1500, 580)
#: 星爆粒子连通域面积下限(px;负样本卡面金装饰最大域 8px,真爆点 12-133)
_MERGE_EFFECT_COMP_MIN_AREA: int = 9
#: ≥9px 粒子域数阈值(星爆帧 8 / 负样本全 0;取 3 居中)
_MERGE_EFFECT_GOLD_MIN_COMPS: int = 3
#: 满席警告横幅带(1080p;x1,y1,x2,y2;46d292eb 实测横幅位置)
_BENCH_FULL_BANNER_RECT: tuple[int, int, int, int] = (470, 515, 1450, 555)
#: 横幅红主导判定:R − max(G,B) > 本值算红主导像素(横幅深红底+红字实测)
_BANNER_RED_DOM_DIFF: int = 40
#: 横幅红主导占比阈值(拖拽帧 0.138 / 负样本 ≤0.013;取 0.06 居中)
_BANNER_RED_DOM_MIN: float = 0.06


def is_merge_effect_frame(screen: MatLike | None) -> bool:
    """合成特效帧态判定(W292/ADR-0420):当前帧是否处于 3合1 星爆动画/拖拽
    合成过渡窗内 → True(read_star 读数不可信,消费方保旧)。

    判据 = 两签名任一命中(标定数字与边界见上方常量块注释):
    ① 前排棋盘带严橙金窗口连通域(≥``_MERGE_EFFECT_COMP_MIN_AREA``)计数
      ≥ ``_MERGE_EFFECT_GOLD_MIN_COMPS``(星爆粒子);
    ② 满席警告横幅带红主导占比 ≥ ``_BANNER_RED_DOM_MIN``(拖拽合成过渡)。

    ``screen`` = 全帧 RGB(None → False,离线/读失败不拦);非 1080p 帧越界
    裁切自动收缩为空 → False。best-effort:任何异常 → False(不拦,防抖
    主干仍兜底——门失效的代价回到 W292 前行为,不引入新故障面)。
    """
    if screen is None:
        return False
    try:
        h, w = screen.shape[:2]
        # ① 星爆粒子:前排带严橙金连通域计数
        x1, y1, x2, y2 = _MERGE_EFFECT_FRONT_BAND
        if y2 <= h and x2 <= w:
            band = screen[y1:y2, x1:x2]
            hsv = cv2.cvtColor(band, cv2.COLOR_RGB2HSV)
            mask = cv2.inRange(hsv, _PREVIEW_GOLD_LO, _PREVIEW_GOLD_HI)
            nlab, lab = cv2.connectedComponents(mask)
            big = sum(1 for i in range(1, nlab)
                      if int((lab == i).sum()) >= _MERGE_EFFECT_COMP_MIN_AREA)
            if big >= _MERGE_EFFECT_GOLD_MIN_COMPS:
                return True
        # ② 满席警告横幅:红主导像素占比
        bx1, by1, bx2, by2 = _BENCH_FULL_BANNER_RECT
        if by2 <= h and bx2 <= w:
            reg = screen[by1:by2, bx1:bx2].astype(np.int32)
            r, g, b = reg[:, :, 0], reg[:, :, 1], reg[:, :, 2]
            if float(((r - np.maximum(g, b)) > _BANNER_RED_DOM_DIFF).mean()) \
                    >= _BANNER_RED_DOM_MIN:
                return True
        return False
    except Exception:   # noqa: BLE001  判据 best-effort;异常=不拦
        return False


def identify_slots(
    screen: MatLike,
    templates: AvatarTemplates,
    slots: list[tuple[int, Rect]],
    row: str,
    min_inliers: int = 10,
    live_only: bool = False,
    center_gate: bool = False,
    variant_keys: set[str] | None = None,
) -> list[BenchChar]:
    """纯 CV:按槽位裁切 → SIFT 识别 → BenchChar 列表(离线可测,无 ctx 依赖)。

    :param slots: ``[(slot_idx, rect), ...]``;rect = 1080p 槽位矩形(来自 screen_info 或硬编码)。
    :param row: ``"front"`` / ``"back"``(已上阵排)→ BenchChar.position_pref;``""``(备战栏)→ 用
        角色固有偏好(未上阵)。
    :param min_inliers: 识别门槛(identify_character 透传)。部署排(有场景背景)传更高
        (``_DEPLOYED_MIN_INLIERS``);备战栏卡槽背景干净,保持默认。
    :param live_only: 部署排专用(2026-08-26 定策,同日居中勘误后语义微调):
        plaza 官方 art(插画)对棋盘 3D 站立小人是**跨域匹配**,分数不稳
        (错位窗口时代曾出 0-26 弱命中/假阳带,真窗口下空槽已零假阳但跨域
        弱命中风险仍在,run20 商店卡同型);**现场采集 art(raw_board 变体/
        纯现场主档)才是同域信号**(真窗口实测强命中,空槽 0 假阳)。True 时:
        命中主档且该角色存在现场变体 → 拒(漏读走「未知」对账可见,好过跨域
        弱命中毒板面);命中变体键或纯现场主档角色(佩佩/狸猫对)→ 收。
        例外(ADR-0452):主档内点 ≥ :data:`_LIVE_ONLY_PLAZA_STRONG` 时收 ——
        跨域弱命中带实测上限 29(33 帧板面基准,空槽全库最高内点),强主档
        (如开拓者·欢愉 73 内点)远超弱带,按「有变体即拒」误杀。
        ⚠️ 变体必须真窗口采(旧错位残片变体会在正位帧上输给 plaza 主档 →
        live_only 假阴丢读,2026-08-26 万敌@s2 实证后已全量重采)。
    :param center_gate: 部署排专用(ADR-0452,**位置感知识别**)。角色卡宽
        (~170px) > 槽窗宽(~142px),槽裁片必然渗入邻卡边缘;同名邻窗双命中
        由既有幽灵去重吸收,**异名**渗漏(邻卡残条命中邻卡同款饰品)会以弱
        内点压过本窗真身。True 时改走中心归属门:每槽在**横向扩展窗**
        (:data:`_DEPLOYED_EXPAND_PAD`)内取全库假设列表
        (:func:`identify_hypotheses`),homography 投影模板中心落在**本槽核**
        (原 rect)内才认领,再过同一套阈值/歧义语义
        (:func:`currency_war_char_id._resolve_best`)—— 渗漏假设的中心在邻槽,
        几何直接出局,与内点数无关。 False(默认)= 旧逐槽裁片路径
        (备战栏/商店卡窗与卡同宽无渗漏,保持不变)。
    :return: 命中角色的 BenchChar 列表(空槽 / 低内点 / 歧义 / 非 roster → 跳过,不进列表)。

    每槽:裁 ``screen[y1:y2, x1:x2]`` → ``identify_character``(SIFT 对脸库)→ ``resolve_char_name``
    → 规范名。faction 取角色首阵营(粗;权威阵营计数看 board OCR);star = ``read_star``(立绘底部
    金星计数)。

    **相邻幽灵去重**:部署位的角色卡牌比槽窗宽(实测约 170 vs 142px,VLM
    量测),单张卡的立绘可能渗进相邻窗口 → 同名角色相邻两窗双命中(真身
    高分 + 渗出残影低分)。规则:同名相邻双命中且低分 < 高分×0.5 → 判低分
    为残影剔除;其余(分数相近 = 真双副本 / 不相邻)保留。真窗口帧(佩佩局
    双帧)暂未复现幽灵——规则作廉价保险存在,标定数字见 :data:`_GHOST_RATIO`。
    """
    out: list[BenchChar] = []
    hits: list[tuple[int, BenchChar, int]] = []   # (slot_idx, char, inliers) 去重用
    _has_variant: set[str] | None = None
    if live_only:
        # P4R4 漏斗批:变体主档集可由调用方注入(全库口径)——漏斗传的是
        # 缩小子集模板字典,子集内推导会漏「主档在子集、变体不在」的拒收
        # 判定 → live_only 语义必须恒基于全库(默认 None = 从传入 templates
        # 推导,旧调用零变化)。
        _has_variant = variant_keys if variant_keys is not None else \
            {k.split('#')[0] for k in templates if '#' in k}
    for slot_idx, rect in slots:
        if center_gate:
            crop, avatar_id, inliers = _identify_center_gated(
                screen, rect, templates, min_inliers, live_only, _has_variant)
        else:
            crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
            avatar_id, inliers = identify_character(
                crop, templates, min_inliers=min_inliers, return_key=live_only)
            if avatar_id is not None and live_only:
                # 主档命中但该角色有现场变体(变体没赢)→ 跨域弱命中拒(见 live_only 参数说明)
                if '#' not in avatar_id and avatar_id in _has_variant:
                    avatar_id = None
                else:
                    avatar_id = avatar_id.split('#')[0]
        if avatar_id is None:
            # 三态判定面增态(裁定①):亮度≥50 的 miss =
            # 应有内容但识别失败 → unknown 显态落缺陷台账(§7.2 豁免
            # 延后:写端仍沿用不写,本记录只解除「失读与真空」沉默二义);
            # <50 = 确证空位,良性 miss 不留痕(与 shop 亮度判定表同源)。
            try:
                _mean = float(screen[rect.y1:rect.y2,
                                     rect.x1:rect.x2].mean())
            except Exception:   # noqa: BLE001  裁剪越界等,留证降级
                _mean = -1.0
            if _mean >= 50:
                try:
                    from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                        record_defect,
                    )
                    record_defect(
                        'confidence', 'perception_conflict',
                        expected=f'{row or "deployed"} 槽{slot_idx} SIFT 识别出身份',
                        observed=f'miss(inliers={inliers}, 均值{_mean:.1f})',
                        reader_source='identify_slots',
                        confidence=float(_mean),
                        note='deployed 槽级 unknown 显态(§7 判定面增态)')
                except Exception:   # noqa: BLE001  遥测 best-effort
                    pass
            continue
        name = resolve_char_name(avatar_id)
        if name is None:
            continue
        # 开拓者形态按排归一(用户 2026-08-16):前台=记忆/后台=欢愉;立绘库两形态覆盖不均时
        # SIFT 可能按旧立绘判成另一形态 —— 已上阵排是权威(row 即真实排),归一消歧。
        from sr_od.application.currency_war.data.cw_chars import (
            is_trailblazer,
            trailblazer_form,
        )
        if row and name and is_trailblazer(name):
            name = trailblazer_form(name, row)
        ch = get_char(name)
        hits.append((slot_idx, BenchChar(
            slot=slot_idx,
            char_id=name,
            # '?'=未知(名不在注册表);''=已知无阵营(白厄类,复制效果不计阵营人数)
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
            star=read_star(crop),            # 立绘底部金星计数(1/2/3 星;见 read_star)
            position_pref=row if row else (ch.position_pref() if ch is not None else 'back'),
        ), inliers))
    # 相邻幽灵去重(见 docstring):同名相邻双命中,低分 < 高分×0.5 → 剔低分
    drop: set[int] = set()
    for i, (s1, c1, n1) in enumerate(hits):
        for j, (s2, c2, n2) in enumerate(hits):
            if i >= j or c1.char_id != c2.char_id or abs(s1 - s2) != 1:
                continue
            lo, hi = (i, j) if n1 < n2 else (j, i)
            if hits[lo][2] < _GHOST_RATIO * hits[hi][2]:
                drop.add(lo)
    out = [c for k, (_s, c, _n) in enumerate(hits) if k not in drop]
    return out


#: 相邻幽灵判定比(同名相邻双命中,低分 < 高分×本值 → 剔低分)。机制依据:
#: 角色卡比槽窗宽(约 170 vs 142px),立绘渗入邻窗只会是残片 → 分数远低于
#: 真身;真双副本两窗各自完整、分数相近,不受影响。0.5 取「同角色两完整
#: 视图分数比」与「残片比」之间的保守值(真窗口帧暂未复现幽灵,规则为
#: 防御性保险,非实测标定——错位时代的 86/19 数字随伪象作废)。
_GHOST_RATIO: float = 0.5

#: 部署排识别门槛(identify_character min_inliers 覆盖值)。真窗口实测:空槽
#: 全库最高 0 分(错位时代的 11-26 假阳带是窗口切到邻卡残影的伪影,ADR-0390),
#: 占用位命中 ≥30(变体强命中/plaza 主档跨域也能到 33)。15 取两者之间的
#: 防御值(拦裁边残影/跨域弱命中),非紧标定;备战栏卡槽背景同样干净
#: (真命中 35-57),保持默认 10 不抬高。
_DEPLOYED_MIN_INLIERS: int = 15

#: 部署排只认现场 art(live_only;2026-08-26 佩佩局定策):plaza 官方 art 跨域
#: 弱命中(插画 vs 3D 站立小人,run20 商店卡同型问题)不做部署排身份依据;
#: 现场变体(真窗口 raw_board)同域强命中,空槽零假阳。漏读代价(未知位,
#: 对账可见)< 跨域弱命中毒化代价。**变体必须真窗口采**(居中勘误前错位
#: 残片变体致 live_only 假阴,万敌@s2 丢读实证;已全量重采)。
_DEPLOYED_LIVE_ONLY: bool = True

#: 部署排中心归属门开关(ADR-0452;前置 = 卡宽>槽窗的渗漏几何事实,见
#: identify_slots center_gate 参数说明)。生产部署排恒开;备战栏/商店走旧路径。
_DEPLOYED_CENTER_GATE: bool = True

#: 中心归属门的横向扩展量(px)。卡宽~170 − 槽窗宽~142 ≈ 28px 渗漏 → 35 覆盖
#: 整卡渗漏带并留余量;过大把隔壁邻卡整卡拉进窗徒增假设数,不改判别。
_DEPLOYED_EXPAND_PAD: int = 35

#: live_only 强主档例外门槛(内点)。跨域弱命中带实测上限 29(33 帧板面基准,
#: 空槽全库最高内点;ADR-0452),真命中中位数 ~45 → 40 居中:高于弱带上限
#: 11px,低于中位数;真命中 30-39 的变体角色仍被拒(漏读方向,对账可见)。
_LIVE_ONLY_PLAZA_STRONG: int = 40


def _identify_center_gated(
    screen: MatLike,
    rect: Rect,
    templates: AvatarTemplates,
    min_inliers: int,
    live_only: bool,
    has_variant: set[str] | None,
) -> tuple[MatLike, str | None, int]:
    """部署排单槽中心归属识别(ADR-0452):扩展窗全库假设 → 槽核内认领 → 统一决策。

    ① 横向扩展窗(``_DEPLOYED_EXPAND_PAD``,y 不扩 —— 渗漏只在 x 向;上下邻带
       是 HUD/场景,拉入徒增噪声);② :func:`identify_hypotheses` 全库假设;
    ③ 双重位置门(ADR-0452):homography 投影模板中心 x 落在本槽核(原 rect)
       内**且**裁决计**核内内点**(证据落点须在本槽)—— 邻卡渗漏假设的中心在
       邻槽核,几何出局;跨域噪声假设中心可能贴核边缘蹭进(佩佩局空槽
       忘归人 21 内点案),其证据大多在核外,核内计数不过阈值;
    ④ 认领后的假设表走 :func:`currency_war_char_id._resolve_best`(阈值/歧义比/
       色相仲裁与旧路径同一语义;色相仲裁喂**原槽窗**裁片 —— 扩展窗含邻卡
       会带偏同型异色对的色相符号,狸猫对实测翻案);
    ⑤ live_only 强主档例外(≥``_LIVE_ONLY_PLAZA_STRONG``)。

    :return: ``(crop, 模板键 or None, 内点)``;crop = **原槽窗**裁片
        (star 读取等后续消费与旧路径同几何,不吃扩展窗);内点 = 胜出假设核内数。
    """
    from sr_od.application.currency_war.obs.currency_war_char_id import (
        _resolve_best,
        identify_hypotheses,
    )
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    pad = _DEPLOYED_EXPAND_PAD
    ex1 = max(0, rect.x1 - pad)
    ex2 = min(int(screen.shape[1]), rect.x2 + pad)
    exp = screen[rect.y1:rect.y2, ex1:ex2]
    hyps = identify_hypotheses(
        exp, templates,
        core_range=(rect.x1 - ex1, rect.x2 - ex1))
    # 中心归属:投影中心(扩展窗坐标)→ 全图 x ∈ 本槽核才认领;计分=核内内点
    owned = [(cid, inl_core) for cid, _inl, cx, inl_core in hyps
             if rect.x1 <= ex1 + cx <= rect.x2]
    key, inliers = _resolve_best(owned, crop, min_inliers, 1.5, True)
    if key is not None and live_only:
        if '#' not in key and has_variant and key in has_variant \
                and inliers < _LIVE_ONLY_PLAZA_STRONG:
            return crop, None, inliers
        key = key.split('#')[0]
    return crop, key, inliers


def _ctx_slots(ctx: SrContext, prefix: str, count: int) -> list[tuple[int, Rect]]:
    """从 ctx screen_info 取 ``{prefix}-1..{count}`` 的 (slot_idx, rect);area 缺失 → 跳过。"""
    out: list[tuple[int, Rect]] = []
    for i in range(1, count + 1):
        rect = _area_rect(ctx, f'{prefix}-{i}')
        if rect is not None:
            out.append((i, rect))
    return out


def _session_level(ctx: SrContext) -> int | None:
    """session 等级链(``last_level_obs`` 单调链 vs 容器 level 取大)→ 无 session/无值 → None。

    布局选档的 level 源(ADR-0281:后排槽数由 level 驱动;``_resolve_level`` 维护的
    单调链已防毒化)。离线/无 session 场景返 None(调用方退 6 槽基线)。
    **单一源可信门**(15 号稿 §2.3/§6):启发式兜底帧的 level 值**不参与
    取大**——「兜底 4」与「真读 4」可分后,兜底值不得混进单调链。容器侧该
    门由喂入结构性满足(``_feed_board_state`` 仅 authoritative 帧观察写
    level,兜底帧走 carry 沿用),故取容器值直取即可信域(last_state 链
    退役换源;level_readable 显式位不入容器,quality 语义由 Field.source
    承载)。
    """
    try:
        m = ctx.cw_match
        if m is None or m.session is None:
            return None
        lv = getattr(m.session, 'last_level_obs', 0) or 0
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )
        st_lv = board_state_of(m.session).level.value
        if st_lv:
            lv = max(lv, int(st_lv))
        return lv or None
    except Exception:   # noqa: BLE001
        return None


def _level_trusted(ctx: SrContext) -> bool | None:
    """level authoritative 位单一读口(15 号稿 §2.3/§3.2①)→ 三态:

    ``True`` = 容器 level 当前值来自真读观察(Field.source='observation');
    ``False`` = 沿用态(source='carried',启发式兜底帧不写容器,沿用值非
    新证);无 session / level 从未观察 → ``None`` = 未声明(布局公式通道
    维持现行为,零行为变更)。last_state 链退役换源:旧帧显式位
    ``level_readable`` 的 observed/兜底两态由容器 source 镜像(喂入口
    ``_feed_board_state`` 观察写=真读/carry=兜底帧),布局公式与 14 号稿
    level 消费门共用本定义,不得各写一份「什么算可信 level」。"""
    try:
        m = ctx.cw_match
        if m is None or m.session is None:
            return None
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )
        _lv = board_state_of(m.session).level
        if _lv.value is None:
            return None
        return _lv.source == 'observation'
    except Exception:   # noqa: BLE001
        return None


def read_deployed_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates,
                        level: int | None = None) -> list[BenchChar]:
    """舞台已上阵角色(前排 4 + 后排 N)→ list[BenchChar](position_pref=front/back)。

    空槽 / 未识别 → 不进列表。用途:离线重建 / 漂移恢复(**不进 read_game_state**;见模块 docstring)。
    布局选档 **cap 差公式 + CV 双通道**(ADR-0385,旧 level 驱动已废——run 26
    lv8 无召唤物局按 8 格读板失真实证):select_back_layout 现读 read_deploy_cap
    (未传 level 时 session 等级链);读不到 → 6 槽基线。
    **布局未知态**(15 号稿 §3.2④):单帧未知 → 只返前排(跳过后排读);
    冻结帧(连续 3 未知)→ 读类退 6 档基线继续读;每帧 JSONL 留证在
    resolve 侧。level_trusted 接线:未显式传 level 时取容器 level
    authoritative 位(``_level_trusted``,derived 帧公式通道弃权)。
    """
    from sr_od.application.currency_war.obs.cw_back_layout import (
        back_row_slot_rects_ctx,
        fallback_back_slots,
        resolve_back_slots,
    )
    # 消费接线(15 号稿 §3.2①):显式传 level = 调用方自declare的读数,可信位
    # 不越权代判(None=现行为);未传 = 走 session 等级链 → 接容器 level
    # authoritative 位可信门(derived/启发式帧公式通道弃权)。
    _lt = None if level is not None else _level_trusted(ctx)
    _lay = resolve_back_slots(ctx, screen, level=level, level_trusted=_lt)
    if _lay.get('unknown') and not _lay.get('frozen'):
        # 单帧未知(§3.2④):跳过后排身份读(宁缺勿造,同 paddle None
        # 对齐跳过先例);JSONL 留证(resolve 侧每帧落证)。
        front = identify_slots(screen, templates, _ctx_slots(ctx, '前排', 4),
                               'front',
                               min_inliers=_DEPLOYED_MIN_INLIERS,
                               live_only=_DEPLOYED_LIVE_ONLY,
                               center_gate=_DEPLOYED_CENTER_GATE)
        return front
    if _lay.get('unknown'):
        # 冻结帧读类(§3.2④ B2):退 6 档基线继续读(读面可重读可纠正,
        # 下一帧覆盖;写类冻结在消费面 cw_op_deploy 侧)。
        back_slots = fallback_back_slots()
    else:
        back_slots = back_row_slot_rects_ctx(ctx, _lay['prefix']) or fallback_back_slots()
    # 布局留证采集钩子(ADR-0385 决策 12,W209i 降级:原停机钩子废弃;
    # 2026-08-26 佩佩局 7 格坐标档已建档 → 钩子对 7 静默,只对未来**未建档**
    # 新档位(diff≥3 域外/CV 新观察)留证):
    # 触发 = 对账原始格数 n_raw 未建档(∉ _LAYOUT_PREFIX)→ **obs_conflict 留证
    # + 去重截图,不停机**。
    # 降级依据(run 27 停机事故实证):货币战争备战阶段是**实时倒计时**,
    # 战斗自动开打——停 bot ≠ 停游戏,run 27 hook 停机后画面自行推进到
    # 首领战败结算(14:09 停 → 14:16 结算,截图 20260826_141613),「停机
    # 保画面待采集」对实时制游戏是虚假承诺;误停代价(烧一局 + 世界状态
    # 不可控)>> 采集收益。7 格坐标 2026-08-26 经 MCP 交互实锤采集完成
    # (后排7槽-1..7 upsert + _LAYOUT_PREFIX 登记),本钩子自然静默。
    # 帧态门(is_prep_like_frame)辖**留证**触发(过渡/动画帧不留证,
    # 判定素材 = 本函数入参 screen = 当前处理帧,非缓存——run 27 复盘:
    # 触发帧确为备战态,门本身有效,失效的是「停机能保画面」的假设)。
    # 帧态门 + obs_conflict 自带 300s 节流;升级路径 = 框架原生 PAUSE
    # (方案 C,未暴露;真需要现场采集时人工经 MCP 驱动)。
    try:
        from sr_od.application.currency_war.obs.cw_back_layout import _LAYOUT_PREFIX
        # 未知帧 n_raw=None 不辖本钩子(未知态留证已在 resolve 侧另落)
        if _lay['n_raw'] is not None and _lay['n_raw'] not in _LAYOUT_PREFIX:
            from sr_od.application.currency_war.kernel.cw_obs_core import (
                is_prep_like_frame,
            )
            if not is_prep_like_frame(ctx, screen):
                from one_dragon.utils.log_utils import log as _log0
                _log0.info('[cw-hook][layout] 后排 %s 格无档但帧非备战态'
                           '→ 跳过(过渡帧防误触)', _lay['n_raw'])
            else:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict(
                    'back_layout_unarchived_grid', _lay['n_raw'], _lay['cv_n'], screen,
                    verdict=('留证采集-后排档未建档(W209i 降级不停机:实时制'
                             '游戏停 bot 不停游戏,run 27 停机画面自行推进到'
                             '结算实证);本行含去重截图,坐标采集需人工在场'
                             '经 MCP 交互(拖角色逐位实锤),画面可能已推进'
                             '——以截图为准;流程:暗框初测槽位 x → 拖角色'
                             '逐位验证 → upsert 对应档 area → _LAYOUT_PREFIX'
                             ' 登记档位 → 本留证自然停发(2026-08-26 佩佩局'
                             ' 7 格即按此流程闭合)'),
                    source='read_deployed_chars', cap=_lay['cap'],
                    level=_lay['level'], formula=_lay['formula_raw'],
                    cv_readings=_lay.get('cv_readings'))
    except Exception:   # noqa: BLE001  钩子 best-effort,绝不阻塞身份读取
        pass
    front = identify_slots(screen, templates, _ctx_slots(ctx, '前排', 4), 'front',
                           min_inliers=_DEPLOYED_MIN_INLIERS,
                           live_only=_DEPLOYED_LIVE_ONLY,
                           center_gate=_DEPLOYED_CENTER_GATE)
    back = identify_slots(screen, templates, back_slots, 'back',
                          min_inliers=_DEPLOYED_MIN_INLIERS,
                          live_only=_DEPLOYED_LIVE_ONLY,
                          center_gate=_DEPLOYED_CENTER_GATE)
    # 系统单位恒最右布局自检(ADR-0281 件3):便宜的常设布局判别器,best-effort
    check_system_unit_layout(screen, back, back_slots, templates,
                             source='read_deployed_chars')
    return front + back


# 系统单位布局自检:实测 x 与所选档右格中心的容差(px;ADR-0281 用户口述模型:
# 系统单位恒最右,差 >40 = 选错档)。40 < 半格宽 71,一个格位错(142)必超。
_SYSTEM_UNIT_LAYOUT_TOL_PX: int = 40
# 自检扫描带(x 带:覆盖 6/8 格全部布局 + 幻影时代的假想范围;y = 后排槽带)
_SYS_CHECK_X1, _SYS_CHECK_X2 = 250, 1700
_SYS_CHECK_Y1, _SYS_CHECK_Y2 = 600, 740
_sysunit_conflict_ts: dict[str, float] = {}


def _sift_locate_x(band: MatLike, templates: AvatarTemplates, char_id: str,
                   x_off: int) -> float | None:
    """SIFT 单点定位:在 band(后排带灰度)里定位 ``char_id`` 模板 → 画面 x 坐标。

    同 ``identify_character`` 的 SIFT 机制,但用 homography 投影模板中心(部分
    可见也能定位,优于 TM——TM 要求模板 ≤ band 且狸猫兄弟灰度互撞)。定位失败 → None。
    """
    from sr_od.application.currency_war.obs.currency_war_char_id import (
        _SIFT,
        _ratio_good,
        ransac_locate_x,
    )
    entry = templates.get(char_id)
    if entry is None:
        return None
    _g, tkp, tdesc = entry
    skp, sdesc = _SIFT.detectAndCompute(band, None)
    if sdesc is None or tdesc is None or len(skp) < 4 or len(tkp) < 4:
        return None
    good = _ratio_good(tdesc, sdesc)
    if len(good) < 8:
        return None
    return ransac_locate_x(tkp, skp, good, _g, x_off)


def check_system_unit_layout(
    screen: MatLike,
    back_chars: list[BenchChar],
    back_slots: list[tuple[int, Rect]],
    templates: AvatarTemplates,
    source: str = 'read_deployed_chars',
) -> None:
    """系统单位恒最右布局自检(ADR-0281 件3,常设判别器)。

    模型(用户口述权威):狸猫(狸小虎/狸小龙)/佩佩类系统召唤单位恒占布局**最右
    槽位(们)**,布局格数变 → 其 x 跟着最右格移动。判别:后排读到系统单位
    (char_id 判定 = roster cost==0 段)时,SIFT 实测其 x,与所选档最右 k 格中心
    (k=系统单位数)对拍;任一差 > ``_SYSTEM_UNIT_LAYOUT_TOL_PX`` →
    ``obs_conflict('layout_mismatch_by_system_unit')``(节流 300s)。

    与空槽签名法交叉实证过(三触发帧狸猫@1329/1467 只与 8 格自洽)。纯读
    best-effort,失败不抛。佩佩暂无 roster/模板条目 → 现覆盖狸猫对(有模板者)。
    """
    import time as _time

    try:
        sys_units = []
        for c in back_chars:
            ch = get_char(c.char_id) if c.char_id else None
            if ch is not None and ch.cost == 0:
                sys_units.append(c.char_id)
        if not sys_units:
            return
        band = cv2.cvtColor(screen[_SYS_CHECK_Y1:_SYS_CHECK_Y2,
                                   _SYS_CHECK_X1:_SYS_CHECK_X2],
                            cv2.COLOR_RGB2GRAY)
        located = []
        for cid in sys_units:
            x = _sift_locate_x(band, templates, cid, _SYS_CHECK_X1)
            if x is not None:
                located.append((cid, x))
        if not located:
            return
        located.sort(key=lambda t: t[1])
        centers = sorted((r.x1 + r.x2) / 2 for _i, r in back_slots)
        k = min(len(located), len(centers))
        for (cid, x), exp in zip(located[-k:], centers[-k:], strict=True):
            if abs(x - exp) > _SYSTEM_UNIT_LAYOUT_TOL_PX:
                now = _time.monotonic()
                if now - _sysunit_conflict_ts.get(source, -1e9) < 300.0:
                    return
                _sysunit_conflict_ts[source] = now
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict(
                    'layout_mismatch_by_system_unit', exp, round(x, 1), screen,
                    verdict=(f'留证-系统单位({cid})实测 x={x:.0f} 与所选档右格中心 '
                             f'{exp:.0f} 差>{_SYSTEM_UNIT_LAYOUT_TOL_PX}px → 布局选错档'
                             f'(ADR-0281 恒最右模型);处理:核该局 level 与所用档,'
                             f'交互实锤(拖角色/详情面板)后校正 screen_info 布局'),
                    source=source, char_id=cid)
                return
    except Exception:   # noqa: BLE001  自检 best-effort,绝不阻塞身份读取
        pass


def read_bench_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates) -> list[BenchChar]:
    """备战栏角色(9 槽)→ list[BenchChar](position_pref=角色固有偏好,未上阵)。

    空槽 / 未识别 → 不进列表;已建档物品(箱/典籍/书册卡)占用的槽位以
    ``is_item_slot=True`` 空名位入列表(占 1 席,见
    :func:`_merge_item_occupied_slots`)。用途:离线重建 / 漂移恢复。
    """
    chars = identify_slots(screen, templates, _ctx_slots(ctx, '备战栏', 9), '')
    _summon_unknown_hook(ctx, screen, chars)
    _merge_item_occupied_slots(ctx, screen, chars)
    return chars


def _summon_unknown_hook(ctx: SrContext, screen: MatLike,
                         chars: list[BenchChar]) -> None:
    """召唤物/物品停机钩子(偏常驻兜底,hook审计 S3):占用但全部识别路径
    不认识的备战席槽 → 停机保画面留现场建档。

    为什么读链双路径都必须挂:身份读链有旧路径(:func:`read_bench_chars`)
    与漏斗路径(:func:`read_bench_chars_tiered`,P4R4 heavy 批起的生产主路径)
    两条,钩子段原本只内联在旧路径——漏斗路径「占用未识别」的槽被静默
    丢弃,跟踪席数少 1 → 席满被当有空位,策略照幻影空位发买牌、游戏全拒
    且金不动(实机局:黄泉槽整槽丢读后 2 张连发全拒,2026-09-14
    run_20260914_210200 停机钩子 exec_fail_mismatch)。本函数即原旧路径
    内联段原样抽出,双路径共用单一源。
    """
    # [触发=「占用且全部识别路径不认识」= 兜一切未知物品变体,比临时建档
    # 面宽——真删了,下个新物品变体会被当空槽乱操作,比停机贵;保留,识别
    # 覆盖新变体时自然不再触发]
    # 召唤物/特殊形态建档(用户 2026-08-18 定调):
    # 槽位占用(slot_occupied CV)真 + SIFT 认不出 = 未建档单位现身 → **停机保画面**,
    # AI 现场点该槽 → 右侧详情面板出角色名(身份 ground truth 源)+ 外观对照 → 定名建档
    # (portrait_plaza/<名>/raw.png 白框法裁剪 + roster 核条目)→ 处理完删 flag
    # (钩子段在识别覆盖该物品变体前保留)。
    # ⚠️ r78 新误触模式守卫:**角色详情面板开着时跳过** —— 详情面板(x1400+)盖住 bench
    # 右端(slot7-9),被遮槽 SIFT 看到的是面板 UI(实锤:summon_unknown__e1fb06c8 帧
    # slot9 裁出的是搜索图标,详情面板上还明晃晃写着「藿藿」本尊)→ 假「占用未识别」
    # 反复停机。详情面板 OCR 锚(装备推荐/出售按钮区)在场 → 本帧不判。
    # ⚠️ 防抖(r17-r31 教训):同内容哈希只停一次(cw_shot_unique 返 None = 已采过 → 不再停),
    # 防同一单位整局反复停机;哨兵文件自描述。
    try:
        from sr_od.application.currency_war.kernel.cw_obs_core import _ocr
        from sr_od.application.currency_war.kernel.cw_observe import cw_shot_unique
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
            return
        # r100j 修正(用户纠偏:商店开态**不**挤压备战席;slot1「开启」=占槽物品的
        # 开启按钮,非购买经验 UI)。撤掉昨天的商店开态静默跳过(它掩盖真问题:
        # 真召唤物在商店开时占槽也永远发现不了)。真根因 = 该占槽物品是箱/卡包的
        # **变体渲染**,find_supply_boxes/find_tomes/宽松互斥全没认出 → 漏到本钩子。
        # r100k:书册卡已建档(find_bookcards)进 _obj_slots → 本钩子不再拦它。
        # 书册卡开启语义已确认(2026-08-30 实机:点槽 → 「专家邀请函」五选一),
        # 原确认停机钩子退役,自动处理链见 operations/cw_screen/cw_screen_expert_invite.py
        # (备战环预清场 + loop 0k 弹窗分支接线)。
        # 排除集单一源(部署伪槽修复批 ①):原内联段(find_* 族 ∪ 泛 TM 低阈
        # 扫描)整体迁入 bench_item_slots,本钩子消费模糊档(精确 ∪ 泛扫描,
        # 行为与原内联段等价);停机钩子其余段(面板守卫/帧态门/ADR-0263 锚
        # 排除/防抖)是停机判定语义,不进该函数、留在钩子内。
        _bench_slots9 = _ctx_slots(ctx, '备战栏', 9)
        _obj_slots = bench_item_slots(ctx, screen, fuzzy=True)
        _named = {c.slot for c in chars} if chars else set()
        for _slot, _rect in _bench_slots9:
            if _slot in _named or _slot in _obj_slots:
                continue
            from sr_od.application.currency_war.obs.currency_war_cv import slot_occupied
            if slot_occupied(screen, _rect.x1 + (_rect.x2 - _rect.x1) // 2,
                             _rect.y1 + (_rect.y2 - _rect.y1) // 2):
                # r330 帧态门(同 layout/bookcard:停机只在备战类
                # 精准帧;过渡帧跳过防误采)
                from sr_od.application.currency_war.kernel.cw_obs_core import (
                    is_prep_like_frame,
                )
                if not is_prep_like_frame(ctx, screen):
                    from one_dragon.utils.log_utils import log as _lg0
                    _lg0.info('[cw-hook][summon] slot%s 占用未识别但帧非备战态'
                              '→ 跳过(过渡帧防误触)', _slot)
                    break
                # ADR-0263 Revision 第三段(金币说明锚):右侧奖励/金币说明
                # overlay 是 C 类无档案 overlay(无独立 screen 档案,进不了
                # is_prep_like_frame 两段式的 UPPER_SCREENS)→ 停机前以锚 OCR
                # 判定补充排除:overlay 开着时盖住备战栏右端,固定 slot rect
                # 裁到 overlay 内容 → SIFT 零匹配 → 假「占用未识别」停机
                # (局69 实证)。锚命中 → 本帧跳过识别判定(不 flag 不停机),
                # 等下一帧 overlay 关了再判。其余 overlay(阿哈大悦等全屏类)
                # 由两段式第一段天然覆盖:全屏 UI 盖 id_mark → 备战屏不命中。
                from sr_od.application.currency_war.kernel.cw_obs_core import (
                    gold_info_overlay_open,
                )
                if gold_info_overlay_open(ctx, screen):
                    from one_dragon.utils.log_utils import log as _lg1
                    _lg1.info('[cw-hook][summon] slot%s 占用未识别但金币说明'
                              'overlay 开着 → 跳过(ADR-0263 rev 锚段)', _slot)
                    break
                _shot = cw_shot_unique(screen, 'summon_unknown')
                if _shot is not None and ctx.run_context is not None:
                    from pathlib import Path as _P

                    from one_dragon.utils.log_utils import log as _log
                    _cx = (_rect.x1 + _rect.x2) // 2
                    _cy = (_rect.y1 + _rect.y2) // 2   # r256 修:原式 (y1+y2-y1)//2 = y2//2 是 bug
                    _P('.debug/temp/currency_war/summon_stop_hook.flag').write_text(
                        '召唤物/物品停机钩子:备战栏 slot'
                        f'{_slot} 占用但 SIFT 未识别(非角色非已知箱/典籍)。\n'
                        f'现场处理流程(必须当天做完,别降级绕过):\n'
                        f'1. 点槽位 ({_cx},{_cy}) → 看内容(物品会直接开启/弹面板,角色出详情)\n'
                        f'2. 若为物品变体:截图 → 补进 find_supply_boxes/find_tomes 模板或新增物品类目\n'
                        f'   (r100j 教训:卡包变体 TM 0.54 漏检;物品占槽是常态,识别不全就停机等建档)\n'
                        f'3. 若为真召唤物:portrait_plaza/<名>/raw.png 建模板(白框裁 '
                        f'{(_rect.x1, _rect.y1, _rect.x2, _rect.y2)})→ roster 核条目\n'
                        f'4. 建档完成 → 处理完删本 flag;钩子段在识别覆盖该物品变体前'
                        f'保留(偏常驻兜底,hook审计 S3);别把钩子降级留证——'
                        f'未建档物品被当空槽/普通占用乱操作比停机更贵(2026-08-20 用户纠偏)。\n'
                        f'截图: {_shot}', encoding='utf-8')
                    _log.warning('[cw!][summon] 备战 slot%s 占用未识别(物品变体或召唤物)'
                                 '→ 停机现场建档(别降级;处理流程见 flag): %s', _slot, _shot)
                    ctx.run_context.stop_running(reason='hook:summon_unknown')
                break
    except Exception:   # noqa: BLE001  采集 best-effort,绝不阻塞身份读取
        pass


def _merge_item_occupied_slots(ctx: SrContext, screen: MatLike,
                               chars: list[BenchChar]) -> None:
    """已建档物品(补给箱/秘密典籍/书册卡)占用的备战席槽位并入身份读链结果
    (就地追加 ``is_item_slot=True`` 空名位)。

    为什么必须:SIFT 只产角色位,而物品同样占备战席 1 槽(补给球掉箱实机
    语义,见下方「补给箱识别」节首注)——漏记 = 席满帧被当成有空位,策略照
    幻影空位发买牌、游戏侧全部拒买且金不动(实机局:点球奖励「开启」箱补满
    末槽后 3 张连发全拒)。识别面 = ``bench_item_slots`` 精确档(与部署装配
    路径同源,同函数同档);泛扫描档不入账,留召唤物停机钩子兜未建档变体。
    坐标系:slot = 备战栏物理槽 1..9(与 ``BenchChar.slot`` 同系);已识别
    角色位跳过;异常静默(本模块采集面 best-effort 纪律)。
    """
    try:
        named = {c.slot for c in chars}
        for slot in sorted(bench_item_slots(ctx, screen, fuzzy=False)):
            if slot in named:
                continue
            chars.append(BenchChar(slot=slot, char_id='', star=1,
                                   is_item_slot=True))
    except Exception:   # noqa: BLE001  采集 best-effort,绝不阻塞身份读取
        pass


# ===== SIFT 三层漏斗(session 优先匹配;P4R4 heavy 性能批) =====
#
# cProfile 实证(离线 shop_open 帧,10 槽 deployed):findHomography(RANSAC)
# 284ms(48%)+ ratio/knnMatch 239ms(40%)——center_gate 路径每槽对全库
# ~36 个候选假设全量跑 RANSAC,其中注定不命中的候选占绝大多数。漏斗 =
# 按局内先验缩搜索空间,**每层门槛不降**(min_inliers/live_only/中心门/
# 歧义比全部原样,只缩候选集):
#   L1 位置连续性:该槽上帧识别结果(棋盘角色位置连续性强先验);
#   L2 本局已见集:本局出现过的角色(小候选集,覆盖槽位换位/换人);
#   L3 全库兜底:新角色首次上场(= 旧全库路径)。
# 状态读取与写回均挂 session(``cw_idfunnel_last``/``cw_idfunnel_seen``),
# 不引入模块级全局;无 session(离线/测试)→ 直接 L3 全库,行为等价。
# 实现手法 = **传缩小后的 templates 子字典**;裁决代码零改动。
# ⚠️ 子集仲裁的固有缺陷(实机实证,2026-09-14 run_20260914_210200
# 停机钩子 exec_fail_mismatch):歧义比在子集里失真——真身不在子集时,
# 基准线上的跨身份弱命中即可称王(黄泉卡全库 27 内点为冠军,子集里被
# 10~18 内点的忘归人/不死途弱命中顶替),毒化 last/seen 后整槽丢读 →
# 席满被当有空位,策略发幻影买牌被游戏全拒。故 L1/L2 子集命中须清
# 加严线(:data:`_FUNNEL_SUBSET_MIN_INLIERS_FACTOR`),弱命中一律下探
# L3 全库仲裁兜底——子集只做「强信号快配」,不做裁决。

#: 漏斗 session 状态字段名(session 上动态挂;对象由本层独占读写)。
_FUNNEL_LAST: str = 'cw_idfunnel_last'
_FUNNEL_SEEN: str = 'cw_idfunnel_seen'

#: L1/L2 子集命中的加严倍数(子集命中门槛 = 调用方 min_inliers × 本值;
#: 基准档 10 → 20,部署排 15 → 30)。为什么存在:子集仲裁无法复现全局
#: 歧义比(缺席的高分真身不进比较),基准线上的弱命中在子集内恒称王;
#: 实测跨身份弱命中带 10~18 内点、同帧干净真身 ≥27(黄泉 27/其余槽
#: 29~61,离线对拍停机帧)→ 2× 线把弱命中全部压到 L3 仲裁,真身快配
#: 通路不受影响。代价:内点在 [基准线, 2× 线) 窗的真命中多付一次全库
#: 扫描(性能面,非正确性)。边界:①真身内点本帧跌破加严线时也下探 L3,
#: L3 同阈值再败则该槽丢读——单帧丢读的防线在召唤物停机钩子
#: (``_summon_unknown_hook``,占用未识别 → 停机保画面),不在本参数;
#: ②跨身份第二名内点在加严线之上时,子集仍可能误收(全局歧义比无法在
#: 子集复现,属本机制残余风险),由对账留证(obs_conflict)与钩子兜底。
_FUNNEL_SUBSET_MIN_INLIERS_FACTOR: int = 2


def _funnel_state(session) -> tuple[dict, set]:
    """读漏斗状态(缺容器惰性建);返回 (last 映射, seen 集合)。"""
    last = getattr(session, _FUNNEL_LAST, None)
    if last is None:
        last = {}
        setattr(session, _FUNNEL_LAST, last)
    seen = getattr(session, _FUNNEL_SEEN, None)
    if seen is None:
        seen = set()
        setattr(session, _FUNNEL_SEEN, seen)
    return last, seen


def _sub_templates(templates: AvatarTemplates,
                   names: set[str] | list[str]) -> AvatarTemplates:
    """全库 → 子集字典(主档名 + 其全部 '#' 现场变体键;live_only 语义由
    identify_slots 的 variant_keys 全库注入保障,不靠子集推导)。"""
    names = set(names)
    return {k: v for k, v in templates.items() if k.split('#')[0] in names}


def _full_variant_keys(templates: AvatarTemplates) -> set[str]:
    """全库变体主档集(子集模板下 live_only 判定的正确口径)。"""
    return {k.split('#')[0] for k in templates if '#' in k}


def identify_slots_tiered(
    session,
    screen: MatLike,
    templates: AvatarTemplates,
    slots: list[tuple[int, Rect]],
    row: str,
    min_inliers: int = 10,
    live_only: bool = False,
    center_gate: bool = False,
) -> list[BenchChar]:
    """三层漏斗识别(L1/L2 子集命中走加严线,弱命中下探 L3;见模块漏斗注释)。

    :param session: 局 session(漏斗状态挂载点);None = 直接全库(行为等价旧路径)。
    :return: 同 :func:`identify_slots`;命中结果同步写回漏斗状态。
    """
    if session is None:
        return identify_slots(screen, templates, slots, row,
                              min_inliers=min_inliers, live_only=live_only,
                              center_gate=center_gate)
    last, seen = _funnel_state(session)
    variant_keys = _full_variant_keys(templates) if live_only else None
    # 子集命中的加严线(见 _FUNNEL_SUBSET_MIN_INLIERS_FACTOR 注):子集
    # 冠军 ≠ 全局冠军,弱命中必须下探 L3 仲裁。
    _subset_min = min_inliers * _FUNNEL_SUBSET_MIN_INLIERS_FACTOR
    out: list[BenchChar] = []
    for slot_idx, rect in slots:
        ch: BenchChar | None = None
        row_key = (row or '', slot_idx)
        # L1:该槽上帧识别结果(单模板快配)
        prev = last.get(row_key)
        if prev:
            sub = _sub_templates(templates, [prev])
            if sub:
                hits = identify_slots(screen, sub, [(slot_idx, rect)], row,
                                      min_inliers=_subset_min,
                                      live_only=live_only, center_gate=center_gate,
                                      variant_keys=variant_keys)
                if hits:
                    ch = hits[0]
        # L2:本局已见集(排除 L1 已试候选)
        if ch is None and seen:
            l2 = sorted(seen - ({prev} if prev else set()))
            sub = _sub_templates(templates, l2)
            if sub:
                hits = identify_slots(screen, sub, [(slot_idx, rect)], row,
                                      min_inliers=_subset_min,
                                      live_only=live_only, center_gate=center_gate,
                                      variant_keys=variant_keys)
                if hits:
                    ch = hits[0]
        # L3:全库兜底(新角色首次上场;= 旧路径原样)
        if ch is None:
            hits = identify_slots(screen, templates, [(slot_idx, rect)], row,
                                  min_inliers=min_inliers, live_only=live_only,
                                  center_gate=center_gate)
            if hits:
                ch = hits[0]
        if ch is not None:
            out.append(ch)
            last[row_key] = ch.char_id
            seen.add(ch.char_id)
        else:
            last.pop(row_key, None)   # 上帧占用本帧消失(卖出/合成)→ 失效
    return out


def read_deployed_chars_tiered(session, ctx: SrContext, screen: MatLike,
                               templates: AvatarTemplates,
                               level: int | None = None) -> list[BenchChar]:
    """:func:`read_deployed_chars` 的漏斗版(签名多 session;布局解析/
    留证钩子/系统单位自检全部复用旧实现,仅 front/back 识别走三层漏斗)。
    布局未知态语义与旧实现同款(§3.2④):单帧未知只返前排;冻结帧
    读类退 6 档基线。"""
    from sr_od.application.currency_war.obs.cw_back_layout import (
        back_row_slot_rects_ctx,
        fallback_back_slots,
        resolve_back_slots,
    )
    _lt = None if level is not None else _level_trusted(ctx)
    _lay = resolve_back_slots(ctx, screen, level=level, level_trusted=_lt)
    if _lay.get('unknown'):
        back_slots = (fallback_back_slots() if _lay.get('frozen') else [])
    else:
        back_slots = back_row_slot_rects_ctx(ctx, _lay['prefix']) or fallback_back_slots()
    front = identify_slots_tiered(session, screen, templates,
                                  _ctx_slots(ctx, '前排', 4), 'front',
                                  min_inliers=_DEPLOYED_MIN_INLIERS,
                                  live_only=_DEPLOYED_LIVE_ONLY,
                                  center_gate=_DEPLOYED_CENTER_GATE)
    if _lay.get('unknown') and not _lay.get('frozen'):
        return front   # 单帧未知:跳过后排读
    back = identify_slots_tiered(session, screen, templates, back_slots, 'back',
                                 min_inliers=_DEPLOYED_MIN_INLIERS,
                                 live_only=_DEPLOYED_LIVE_ONLY,
                                 center_gate=_DEPLOYED_CENTER_GATE)
    check_system_unit_layout(screen, back, back_slots, templates,
                             source='read_deployed_chars')
    return front + back


def read_bench_chars_tiered(session, ctx: SrContext, screen: MatLike,
                            templates: AvatarTemplates) -> list[BenchChar]:
    """:func:`read_bench_chars` 的漏斗版(识别走三层漏斗;召唤物停机钩子
    双路径共用单一源——本路径是 heavy 生产主路径,占用未识别的槽若只静默
    丢弃,跟踪席数失真会直通策略决策,见 :func:`_summon_unknown_hook`)。"""
    chars = identify_slots_tiered(session, screen, templates,
                                  _ctx_slots(ctx, '备战栏', 9), '',
                                  min_inliers=10)
    _summon_unknown_hook(ctx, screen, chars)
    _merge_item_occupied_slots(ctx, screen, chars)
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
# 秘密典籍(2026-08-16 M45 建档,用户指导):投资策略「秘密典籍」给的道具,
# 占备战席 1 槽(类补给箱);点两次(选中→开启)→ 星徽四选一(loop 0i 接管)。
# 实机渲染 = 金色票券卡(票面星纹 + 底部「开启」钮),模板即自该实机真值帧
# (sr-od-test/screens/货币战争-备战/shop_closed_lowhp.webp slot7)内窗裁剪;
# 模板必须小于全部槽裁片(最小 111x131),否则 shape 守卫会跳过该槽(判盲)。
# 互斥判定:典籍命中需典籍分 > 箱分(同槽双模板对拍,防箱被认成典籍)。
_tome_gray: MatLike | None = None
_tome_loaded: bool = False
# 书册卡(r100k 建档,2026-08-20):青蓝卡片+白色书册/文件夹 icon+底部「开启」,
# 占备战席 1 槽。四帧实测 TM 0.975-1.0(模板=停机帧 slot1 裁剪);与典籍/补给箱
# 互撞 0.505/0.462(分离度足够)。开启语义已确认(2026-08-30 实机:点槽 →
# 「专家邀请函」五选一,选后专家入商店;处理链 = cw_screen_expert_invite.py)。模板名
# 「书册卡_未知」为历史占位,改名需同步 _get_bookcard_gray 路径与测试锁,暂保留。
_bookcard_gray: MatLike | None = None
_bookcard_loaded: bool = False
_BOOKCARD_TM_THR: float = 0.75   # 自身帧 0.975+,留选中态余量;vs 典籍 0.505 分离充足

# shape 守卫观测器:槽裁片小于模板尺寸时 matchTemplate 无法进行,守卫跳过该槽。
# 历史:113x134 整槽尺寸模板在 111x131 的小槽上被守卫静默跳过 = 该槽对此物品判盲
# (证据链与修复=模板收进槽内,见 assets/template/currency_war/supply/ 模板尺寸约定)。
# 这里只做记数+日志(可见性),不改跳过语义——静默跳过曾让漏检无从排查。
_shape_guard_skip_count: int = 0


def _note_shape_skip(where: str, idx: int, crop_h: int, crop_w: int,
                     tm_h: int, tm_w: int) -> None:
    """记一次 shape 守卫跳过(debug 日志;判盲可见,不影响任何判定结果)。"""
    global _shape_guard_skip_count
    _shape_guard_skip_count += 1
    from one_dragon.utils import log_utils
    log_utils.log.debug(
        f'[cw!][{where}] 槽{idx} 裁片{crop_h}x{crop_w}小于模板{tm_h}x{tm_w},'
        f'跳过匹配(累计{_shape_guard_skip_count}次;模板尺寸应小于全部槽裁片)')


def _get_tome_gray() -> MatLike | None:
    """加载秘密典籍模板灰度图(模块级缓存;``assets/template/currency_war/supply/秘密典籍.png`` 缺 → None)。

    ⚠️ 换模板文件需重启 server(module 级缓存;与节点模板/yml 同型坑)。
    """
    global _tome_gray, _tome_loaded
    if not _tome_loaded:
        _tome_loaded = True
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'supply' / '秘密典籍.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _tome_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _tome_gray


def _get_bookcard_gray() -> MatLike | None:
    """加载书册卡模板灰度图(r100k;``assets/template/currency_war/supply/书册卡_未知.png``)。

    模板 = 建档帧 slot1 真值裁片的中心内窗(97x118,< 全部槽裁片,防 shape 守卫判盲;
    渲染同源)。无实机重放帧,阈值 0.75 的自身命中维持建档时实测(0.975+)背书。
    """
    global _bookcard_gray, _bookcard_loaded
    if not _bookcard_loaded:
        _bookcard_loaded = True
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'supply' / '书册卡_未知.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _bookcard_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _bookcard_gray


def find_bookcards(screen: MatLike, slots: list[tuple[int, Rect]]) -> list[tuple[int, Point]]:
    """纯 CV 核心:槽位内 TM 匹配书册卡(r100k 建档)→ ``[(slot_idx, center)]``。

    自身帧 0.975+,阈值 0.75(选中态余量);典籍/箱互撞 ≤0.505 不需互斥。
    """
    tm = _get_bookcard_gray()
    if tm is None:
        return []
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    out: list[tuple[int, Point]] = []
    for idx, rect in slots:
        crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
        if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
            _note_shape_skip('find_bookcards', idx, crop.shape[0], crop.shape[1],
                             tm.shape[0], tm.shape[1])
            continue
        r = cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED)
        if cv2.minMaxLoc(r)[1] >= _BOOKCARD_TM_THR:
            out.append((idx, Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)))
    return out


def _get_supply_box_gray() -> MatLike | None:
    """加载补给箱模板灰度图(模块级缓存;``assets/template/currency_war/supply/补给箱.png`` 缺 → None)。"""
    global _supply_box_gray, _supply_box_loaded
    if not _supply_box_loaded:
        _supply_box_loaded = True
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'supply' / '补给箱.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _supply_box_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _supply_box_gray


_crate_gray: MatLike | None = None
_crate_loaded: bool = False


def _get_crate_gray() -> MatLike | None:
    """加载简易武装箱模板灰度图(r256;军火贸易类投资策略给的占槽物品,
    summon_stop_hook 首捕建档——证据 summon_unknown__42d15804.png,
    红卡金星+开启钮;与补给箱模板互斥 0.45)。"""
    global _crate_gray, _crate_loaded
    if not _crate_loaded:
        _crate_loaded = True
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'supply' / '简易武装箱.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _crate_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _crate_gray


def find_supply_boxes(screen: MatLike, slots: list[tuple[int, Rect]]) -> list[tuple[int, Point]]:
    """纯 CV 核心:槽位 rect 列表内 TM 匹配可开启物品箱
    (补给箱 + 简易武装箱 r256)→ ``[(slot_idx, 槽 center)]``(点「开启」用)。

    模板 ~97x118 < 槽 rect ~113x134 → 逐槽 matchTemplate。空槽/角色槽远低于阈值不命中。
    可离线硬编码 rect 测(同 ``identify_slots`` 分层约定)。
    """
    tms = [t for t in (_get_supply_box_gray(), _get_crate_gray())
           if t is not None]
    if not tms:
        return []
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    out: list[tuple[int, Point]] = []
    for idx, rect in slots:
        crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
        best = 0.0
        for tm in tms:
            if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
                _note_shape_skip('find_supply_boxes', idx, crop.shape[0], crop.shape[1],
                                 tm.shape[0], tm.shape[1])
                continue
            r = cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED)
            _, mx, _, _ = cv2.minMaxLoc(r)
            best = max(best, mx)
        if best >= _SUPPLY_BOX_TM_THR:
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
            _note_shape_skip('find_tomes', idx, crop.shape[0], crop.shape[1],
                             tm.shape[0], tm.shape[1])
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


# ===== 试用角色揭示卡(备战栏槽位;summon 停机钩子首捕建档)=====
# 机制(2026-08-30 局22 2-4 实机确认):备战栏偶现**发光金色神秘卡**(非角色立绘,
# 金光粒子特效)。点击即揭示为**试用角色 2★ 卡**(无任何代价,揭示后原地变普通角色卡,
# 详情带「试用」徽标)。证据帧:.debug/temp/currency_war/shots/summon_unknown__9ab94f70.png
# (slot3 发光卡)+ 揭示后帧(.debug/sr_od_mcp/screenshot/screenshot_20260829_120411_171833.png)。
# 识别 = **双通道 OR**(单正样本帧标定,两通道各留倍数余量;发光动画会变,双通道互补):
# ① 灰度 TM:模板 = 揭示前帧 slot3 内窗 91x114(< 全槽 111x134 防 shape 守卫判盲)。
#    标定(47 张备战 fixture 全部 slot3 负样本):自身 1.0 / 生产加载路径自命中 0.958 /
#    负样本 max 0.254 → 阈 0.5 居中。
# ② 亮金发光签名:槽内 HSV 亮橙金窗口(V≥200 自发光带)像素占比。正样本 0.441 /
#    负样本 max 0.076 → 阈 0.25(正 0.57×、负 3.3× 余量)。TM 兜「光弱但卡面在」,
#    发光签名兜「粒子闪烁致 TM 掉分」——双通道都单正样本标定,漏检时 summon 兜底
#    钩子仍会停机(安全网在,不静默)。
_TRIAL_REVEAL_TM_THR: float = 0.5
_TRIAL_GLOW_LO: tuple[int, int, int] = (15, 80, 200)
_TRIAL_GLOW_HI: tuple[int, int, int] = (35, 255, 255)
_TRIAL_GLOW_RATIO_THR: float = 0.25
_trial_reveal_gray: MatLike | None = None
_trial_reveal_loaded: bool = False


def _get_trial_reveal_gray() -> MatLike | None:
    """加载试用角色揭示卡模板灰度图(``assets/template/currency_war/supply/试用角色揭示卡.png``)。

    模板 = 建档帧 slot3 真值裁片内窗(91x114,< 全部槽裁片,防 shape 守卫判盲);
    单正样本帧标定,阈值数字见常量块注释。
    """
    global _trial_reveal_gray, _trial_reveal_loaded
    if not _trial_reveal_loaded:
        _trial_reveal_loaded = True
        p = get_project_root() / 'assets' / 'template' / 'currency_war' / 'supply' / '试用角色揭示卡.png'
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _trial_reveal_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _trial_reveal_gray


def find_trial_reveal_cards(screen: MatLike, slots: list[tuple[int, Rect]]) -> list[tuple[int, Point]]:
    """纯 CV 核心:槽位内检测试用角色揭示卡(双通道 OR)→ ``[(slot_idx, 槽 center)]``。

    点该中心即揭示(免费得 2★ 试用角色,原地变普通角色卡 → 自然被 SIFT 识别,
    无需后续处理;揭示动作由备战环派发前统一做,见 cw_loop 备战分支接线)。
    可离线硬编码 rect 测(同 ``find_supply_boxes`` 分层约定)。
    """
    tm = _get_trial_reveal_gray()
    hsv = cv2.cvtColor(screen, cv2.COLOR_RGB2HSV)
    glow_mask = cv2.inRange(hsv, _TRIAL_GLOW_LO, _TRIAL_GLOW_HI)
    out: list[tuple[int, Point]] = []
    for idx, rect in slots:
        hit = False
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        # 裁片可能为空(rect 越出小尺寸测试帧):cvtColor 对空阵抛错,守卫跳过
        if crop.size == 0:
            continue
        if tm is not None:
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
            if gray_crop.shape[0] >= tm.shape[0] and gray_crop.shape[1] >= tm.shape[1]:
                r = cv2.matchTemplate(gray_crop, tm, cv2.TM_CCOEFF_NORMED)
                hit = cv2.minMaxLoc(r)[1] >= _TRIAL_REVEAL_TM_THR
            else:
                _note_shape_skip('find_trial_reveal_cards', idx, crop.shape[0], crop.shape[1],
                                 tm.shape[0], tm.shape[1])
        if not hit:
            # 通道② 亮金发光占比(HSV 全帧算一次,逐槽只做裁片均值,便宜)
            gr = glow_mask[rect.y1:rect.y2, rect.x1:rect.x2]
            if gr.size and float((gr > 0).mean()) >= _TRIAL_GLOW_RATIO_THR:
                hit = True
        if hit:
            out.append((idx, Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)))
    return out


# ===== 占槽物品排除集·单一源(部署伪槽修复批 ①)=====
# 双源缺口(方案 .debug/temp/currency_war/deploy_pseudo_slot/方案.md §0):
# 已知物品(find_* 族)的排除集此前只内联在 read_bench_chars 的 summon 停机
# 钩子里,部署扫描(cw_op_deploy bench_occ 纯像素占用)完全没消费 → 物件槽
# 被装配成 char_id='' 伪槽进部署计划 → 游戏「无法移动该目标至场上」白耗
# (局34 实证)。抽本函数后钩子与部署共用同一份名单,禁再各写一份。


def bench_item_slots(ctx: SrContext, screen: MatLike, *, fuzzy: bool) -> set[int]:
    """备战栏占槽物品槽位集(单一源,双置信档)→ **1-based** 槽号集合。

    **坐标系与取值时机(注释规范硬门)**:返回值与 ``BenchChar.slot`` 同系
    (备战栏 1-based);消费方转 0-based 须显式 −1(部署面 ``bench_occ``
    为 0-based,勿混)。取值时机 = 生成期现读快照(调用方持帧自洽,跨帧失效)。

    **双置信档**(方案 A1:两处消费的置信要求不同,禁止一个全集合两处共用):
    - 精确档(``fuzzy=False``)= find_supply_boxes(补给箱/简易武装箱)
      ∪ find_tomes(秘密典籍)∪ find_bookcards(书册卡)∪ find_trial_reveal_cards
      (试用角色揭示卡)。部署面**只许**消费本档:泛扫描是模糊判据,真角色
      立绘在极端帧可能弱匹配过阈 → 部署面误排真角色 = 战力真空(贵方向,
      r60 同型),比伪槽白拖更贵。
    - 模糊档(``fuzzy=True``)= 精确档 ∪ 泛 TM 低阈扫描(0.45 阈,箱/典籍
      互斥对拍)。仅 summon 停机钩子消费:best-effort 包在 try/except,误排
      最多少停机一次(下帧重判,便宜方向)。

    :param fuzzy: True = 精确 ∪ 泛扫描(钩子档);False = 仅精确识别族(部署档)。
    """
    slots9 = _ctx_slots(ctx, '备战栏', 9)
    out: set[int] = {i for i, _p in find_supply_boxes(screen, slots9)}
    out |= {i for i, _p in find_tomes(screen, slots9)}
    out |= {i for i, _p in find_bookcards(screen, slots9)}
    # 试用角色揭示卡(summon 钩子首捕建档):发光金卡点开即免费得 2★ 试用角色,
    # 揭示动作由备战环派发前统一做(cw_loop 备战分支接线)→ 视为已知物品。
    out |= {i for i, _p in find_trial_reveal_cards(screen, slots9)}
    if fuzzy:
        # 泛 TM 低阈扫描(原 read_bench_chars 内联段逐行搬移,判定零变化):
        # 兜已知形态全部漏认的低分渲染物品变体(r100j:卡包变体 TM 0.54 漏检型)。
        _item_tms = [t for t in (_get_supply_box_gray(), _get_crate_gray())
                     if t is not None]
        _tm_g = _get_tome_gray()
        if _item_tms:
            _gray_full = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
            for _i, _rect in slots9:
                if _i in out:
                    continue
                _c = _gray_full[_rect.y1:_rect.y2, _rect.x1:_rect.x2]
                _bs = 0.0
                for _it in _item_tms:
                    if _c.shape[0] < _it.shape[0] or _c.shape[1] < _it.shape[1]:
                        continue
                    _bs = max(_bs, cv2.minMaxLoc(
                        cv2.matchTemplate(_c, _it, cv2.TM_CCOEFF_NORMED))[1])
                if _bs <= 0.45:
                    continue
                _ts = (cv2.minMaxLoc(cv2.matchTemplate(_c, _tm_g, cv2.TM_CCOEFF_NORMED))[1]
                       if (_tm_g is not None and _c.shape[0] >= _tm_g.shape[0]
                           and _c.shape[1] >= _tm_g.shape[1]) else 0.0)
                if _bs >= _ts:
                    out.add(_i)   # 箱/卡包/武装箱类物件(低分渲染),排除
    return out


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
# 检测域 = screen_info「区域-奖励」rect 单一真相源;区域缺档 → 空读数
# (不抛不猜,语义见 read_reward_spheres),禁回退硬编码 rect。

# ===== 幻检交叉验证(奖励域读取防幻检批;实机停机局实证:×12 礼盒蝴蝶结/
# 扣饰被 Hough 幻检为 2 球,点击零消失 → ClickSpheres 同签名死循环
# 停机;同族第 2 件,前件 = W261 装备 icon 越界假圆)=====
# 三道门全部标定自 18 样本离线对拍(3 真球 fixture reward_spheres_4/5/8 共
# 16 真球 + 礼盒停机帧 2 幻球;标定脚本口径 = 圆内 r−4 mask 的 Canny 边缘
# 占比与 HSV V 均值):
#: 真球内部纹理:16 真球样本 Canny 边缘占比 0.000-0.145(发光平滑球面)
#: / 礼盒幻球 0.205-0.324(蝴蝶结缎带纹理)。阈值 0.17 双向余量 ≥0.025。
_SPHERE_EDGE_RATIO_MAX: float = 0.17
#: 真球亮度:真球为自发光体,16 样本圆内 V 均值 164-252(灰球最暗 ~164)
#: / 礼盒幻球 112-116(哑光实体)。阈值 140 双向余量 ≥24,与纹理门独立维度。
_SPHERE_V_MEAN_MIN: float = 140
#: 真球半径带(2026-08-14 建档:gold~44/blue~32/gray~18);礼盒幻球 r56
#: 超带。上限 48 = gold 带 +1 呼吸余量;仅作第三道辅助门(纹理/亮度为主门)。
_SPHERE_R_MAX: int = 48
#: 两帧持存圆心/半径容差(px;Hough 亚像素抖动 + 发光呼吸效应)。
_SPHERE_PERSIST_POS_TOL: int = 12
_SPHERE_PERSIST_R_TOL: int = 6
#: 点击后幻球黑名单命中容差(px;点击坐标 → 复现检测圆心的匹配带宽)。
_SPHERE_PHANTOM_MATCH_TOL: int = 18


def _sphere_texture_gate(hsv: MatLike, edges: MatLike, ix: int, iy: int,
                         r: int) -> bool:
    """单圆幻检门(纯函数):纹理 + 亮度 + 半径三道,任一不过 = 非真球。

    标定数字见上方常量块注释(18 样本:16 真球全过 / 2 礼盒幻球全杀,
    两主门独立维度双向余量充足)。真球 = 自发光平滑球面;面板内非球实体
    (礼盒蝴蝶结/装备 icon 等哑光高纹理物)两主门同杀 —— 属 W261 家族
    通用排除,非单点补丁。
    """
    if r > _SPHERE_R_MAX:
        return False
    h, w = edges.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.circle(m, (ix, iy), max(3, r - 4), 255, -1)
    n = int((m > 0).sum())
    if n <= 0:
        return True   # 退化(圆越界):不因门误杀,交后续逻辑
    if float((edges[m > 0] > 0).mean()) > _SPHERE_EDGE_RATIO_MAX:
        return False
    return float(hsv[:, :, 2][m > 0].mean()) >= _SPHERE_V_MEAN_MIN


def filter_persistent_spheres(
        cur: list[tuple[str, Point, int]],
        prev: list[tuple[str, Point, int]] | None,
        pos_tol: int = _SPHERE_PERSIST_POS_TOL,
        r_tol: int = _SPHERE_PERSIST_R_TOL,
) -> list[tuple[str, Point, int]]:
    """两帧持存交叉验证(纯函数):cur 中与 prev 某球同位置同半径的才采信。

    依据:真球在面板停留期间逐帧稳定(位置/半径仅 Hough 抖动级浮动);
    瞬态特效/动画帧的偶发假圆下一帧即消失。``prev=None``(首帧/无历史)
    → 原样返回(宁缺勿造的反向:首帧采信由纹理门 + 点击后零消失检测兜底,
    不因缺历史而漏球)。"""
    if not prev:
        return list(cur)
    out: list[tuple[str, Point, int]] = []
    for c in cur:
        _color, pt, r = c
        if any(abs(pt.x - p.x) <= pos_tol and abs(pt.y - p.y) <= pos_tol
               and abs(r - pr) <= r_tol for _pc, p, pr in prev):
            out.append(c)
    return out


def _session_phantom_points(ctx: SrContext) -> list[Point]:
    """会话幻球黑名单(局级生命周期;读侧过滤用)。无 session(离线/局外)→ 空。"""
    try:
        m = ctx.cw_match
        s = m.session if m is not None else None
        return getattr(s, 'reward_sphere_phantom_points', None) or []
    except Exception:   # noqa: BLE001  黑名单读侧 best-effort,缺失 = 不过滤
        return []


def note_phantom_sphere(ctx: SrContext, pt: Point) -> None:
    """点击后零消失的球登记为幻球(会话黑名单 + 分键留证;best-effort)。

    黑名单 = session 动态挂 ``reward_sphere_phantom_points``(局级生命周期,
    与漏斗/期望账本同款挂载模式);读侧 ``read_reward_spheres`` 按位置容差
    过滤 → 后续环不再把该目标派给 ClickSpheres(禁无限循环的唯一出口,
    黑名单守卫不再是唯一出路)。重复登记同一位置幂等。"""
    try:
        m = ctx.cw_match
        s = m.session if m is not None else None
        if s is None:
            return
        lst = getattr(s, 'reward_sphere_phantom_points', None)
        if lst is None:
            lst = []
            s.reward_sphere_phantom_points = lst
        if any(abs(pt.x - q.x) <= _SPHERE_PHANTOM_MATCH_TOL
               and abs(pt.y - q.y) <= _SPHERE_PHANTOM_MATCH_TOL for q in lst):
            return
        lst.append(pt)
        # telemetry 上行走出口钩子位(kernel;分包桶依赖矩阵 obs 禁直依
        # telemetry,与 obs_conflict 同款出口形态)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )
        from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
            SEVERITY_L2_RECORD,
            record_defect,
        )
        # 分键坐标 = 容器节点读口(last_state 链退役换源;未观察 = 0 缺省,
        # best-effort 留证面不炸)。
        _nd = board_state_of(s).node.value
        record_defect(
            'reward_sphere', 'reward_sphere_phantom',
            expected='点击后球消失(真球)',
            observed=f'点击后同位置仍检出幻球({pt.x},{pt.y})',
            plane=int(_nd.plane if _nd is not None else 0),
            round_num=int(_nd.round_num if _nd is not None else 0),
            gap_large=False, severity=SEVERITY_L2_RECORD,
            verdict=('留证-奖励域幻球(点击零消失):已入会话黑名单,后续读侧'
                     '过滤放弃该目标;同族=面板内非球物幻检(W261 装备 icon/'
                     '礼盒蝴蝶结),复现新形态先跑纹理门标定再扩证据'),
            refs=[{'stream': 'arbitration', 'key': f'point={pt.x},{pt.y}'}],
            reader_source='click_spheres_verify',
            note='奖励域幻球分键(幻检无交叉验证家族第 3 道:点击后验证)')
    except Exception:   # noqa: BLE001  幻球登记 best-effort,不阻塞点球
        pass


def find_reward_spheres(screen: MatLike, panel_rect: Rect) -> list[tuple[str, Point, int]]:
    """纯 CV 核心:奖励面板内 HoughCircles 检球 → ``[(颜色, center, radius)]``(点球用)。

    颜色 = 'gold' | 'blue' | 'gray'(圆心 HSV 分类;gold=高价值晶矿)。radius 可辅助优先级
    (金球大)。可离线硬编码 rect 测(同 ``find_supply_boxes`` 分层约定)。

    **幻检交叉验证**(三道门,标定与依据见常量块注释):纹理(圆内 Canny
    边缘占比)+ 亮度(圆内 V 均值)+ 半径带 —— 面板内非球实体(礼盒蝴蝶结
    /装备 icon 等哑光高纹理物)被 Hough 检出的圆在此淘汰;真球 16 fixture
    样本全过。点击后零消失检测(``note_phantom_sphere`` 黑名单)为第三道
    独立防线,不在本纯函数(需要点击交互上下文)。"""
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
    edges = cv2.Canny(gray, 80, 160)   # 幻检纹理门(与 Hough 共用同 blur 灰度)
    out: list[tuple[str, Point, int]] = []
    for cx, cy, r in circles[0]:
        ix, iy = int(cx), int(cy)
        if not (0 <= ix < panel.shape[1] and 0 <= iy < panel.shape[0]):
            continue
        if not _sphere_texture_gate(hsv, edges, ix, iy, int(r)):
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


def read_reward_spheres(ctx: SrContext, screen: MatLike,
                        prev: list[tuple[str, Point, int]] | None = None,
                        ) -> list[tuple[str, Point, int]]:
    """奖励面板晶矿球(screen_info「区域-奖励」)→ ``[(颜色, center, radius)]``(点球 op 用)。

    ``prev`` = 上一帧原始读数(两帧持存交叉验证;None = 首帧单帧采信,
    语义见 ``filter_persistent_spheres``)。另:会话幻球黑名单
    (``note_phantom_sphere`` 登记,点击后零消失的坐标)在此读侧过滤 ——
    黑名单坐标不再进返回值,点球环由此获得「放弃该目标」的出口。"""
    rect = _area_rect(ctx, '区域-奖励')
    if rect is None:
        # 区域缺档(建档漂移/档案损坏)→ 空读数:reader 既有 no-read 语义
        # (不抛不猜,点球环自然无目标),禁回退硬编码 rect 对陈旧区域
        # Hough 检测(坐标单一真相源)。
        return []
    spheres = find_reward_spheres(screen, rect)
    if prev is not None:
        spheres = filter_persistent_spheres(spheres, prev)
    phantom = _session_phantom_points(ctx)
    if phantom:
        spheres = [s for s in spheres
                   if not any(abs(s[1].x - q.x) <= _SPHERE_PHANTOM_MATCH_TOL
                              and abs(s[1].y - q.y) <= _SPHERE_PHANTOM_MATCH_TOL
                              for q in phantom)]
    return spheres


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
