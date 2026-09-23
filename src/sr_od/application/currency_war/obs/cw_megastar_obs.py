"""货币战争 盛会之星观察域单一文件 = reader + 标准化门(二次裁决门):

- ``read_megastar_options`` = 巨星候选检测(检测模型正本 =
  ``screens/megastar.md`` §3):弹窗标签带限定 OCR 定卡(命中数 = 候选
  数 1..N,各得位置 + 原始名)→ 逐卡立绘 SIFT 交叉验证身份 → 裁决产
  ``MegastarOption(idx, char_id=规范名, xy)``;
- ``standardize_megastar_options`` = 观察标准化门(reader 已产规范名,
  本函数承载失败裁决;规范 = ``screens/op-layer.md`` §1.1「观察标准化
  门」,家族形态镜像投资环境屏 ``cw_screen_invest_env`` 的观察标准化门)。

生产消费方唯一 = ``operations/cw_screen/cw_screen_megastar.py``(observe
node 选中半读链)。失败语义:reader 任一候选观察失败(SIFT 与 OCR 身份
不一致 → ``READ_FAILED`` 哨兵 / OCR 名转换失败 → 域外原值保留 / 重复
命中)以列表形态过 ``standardize_megastar_options`` 门 → 返回 ``None``
→ observe node round_fail 零写零上报交回重观察(现役机制,调用方零改;
失败信号不走 None 直返——调用方 fail 消息构造迭代候选列表留证)。

候选点击坐标随本读链一并观察上报(规范 = op-layer.md §1.1「选择坐标
观察上报」):xy = (该卡标签中心 x, 在册卡身线 y),每卡自带,动作 op
按 ``idx`` 自容器 ``megastar_opts[idx].xy`` 取点,零坐标现算。旧
「候选-左/右」两槽左右映射模型(idx 枚举序 → 固定槽位常量)已退役
——单候选/部分读时名字与点击位错位(两槽模型把 idx0 恒映射左槽,
候选只出现在右槽时点错卡),坐标随卡自带后该缺陷类整体灭绝。
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    chars_by_faction,
    trailblazer_form,
)
from sr_od.application.currency_war.kernel.cw_bond_equips import equip_bond_grants
from sr_od.application.currency_war.kernel.cw_events import MegastarOption
from sr_od.application.currency_war.kernel.cw_obs_core import (
    _area_rect,
    lcs_resolve_strict,
)
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# 巨星候选标题「盛会之星一X先生/女士!」→ X = 角色名(花火/星期日…)。实测 OCR 核实(2026-08-07 cw_megastar)。
# 先生/女士 + 全/半角叹号容错(OCR 渲染不一)。
_MEGASTAR_RE = re.compile(r'盛会之星一(.+?)(先生|女士)[!！]?')

_MEGASTAR_SCREEN: str = '货币战争-盛会之星'
# 标签带 area(OCR 限定 rect;归档 fixture sr-od-test/screens/货币战争-
# 盛会之星/未选择.webp 实测标定:标签文本带 y333-356,rect 取 y300-380
# 弹窗全宽,容纳 N>2 候选的更宽分布)。
_LABEL_BAND_AREA: str = '候选标签带'

# 在册卡身线 y(实机 bot 点 (822,333) 命中候选卡金边选中,2026-08-07
# cw_megastar 实测)。候选点击 y 恒此值;x = 该卡标签中心 x,每卡自带。
CANDIDATE_BODY_Y: int = 333

# 观察失败哨兵:reader 交叉验证裁决失败(SIFT 与 OCR 名不一致)时替代
# 该候选 char_id 的标记,域外恒判 → 标准化门返回 None → observe node
# round_fail。哨兵必要性:调用方 observe 的 fail 消息构造迭代候选列表
# (``cw_screen_megastar.py`` 现形),失败信号必须以列表形态过门,哨兵
# 名 = 「OCR 名本身合法但被立绘反证」场景在列表形态下的最小失败载体
# (域外/重复场景自带域外原值,无需哨兵)。细节留证(双名各值)在
# reader warn 日志。
READ_FAILED: str = '<观察失败>'

# 候选立绘裁区(相对该卡标签中心;归档 fixture 未选择.webp 实测标定:
# 卡身立绘 y ≈ 170-305,标签中心 x ± 65 完全落卡身内,卡框宽 ≈ 215px)。
_PORTRAIT_Y1: int = 170
_PORTRAIT_Y2: int = 305
_PORTRAIT_HALF_W: int = 65

IdentifyFn = Callable[[MatLike], str | None]
"""立绘身份识别注入点:(候选立绘裁片 RGB)→ 货币战争规范名;``None`` =
未命中(SIFT 通道无产出,OCR 转换名承重)。测试经 ``identify`` 形参注入
桩,禁 monkeypatch 私有。"""


def _default_identify(ctx: SrContext) -> IdentifyFn:
    """生产识别函数:SIFT 立绘库 × ``identify_character`` → 规范名。

    模板经 ``ctx.cw_portrait_templates`` 缓存,缺则按生产惯例加载
    (``cw_identity_obs.ensure_portrait_templates``,与 deploy/bench/shop
    SIFT 共用同一缓存)。库目录缺失 = SIFT 通道全程未命中(OCR 转换名
    承重,不硬依赖库;warn 留证)。
    """
    from sr_od.application.currency_war.obs.currency_war_char_id import (
        identify_character,
    )
    from sr_od.application.currency_war.obs.cw_identity_obs import (
        ensure_portrait_templates,
        resolve_char_name,
    )

    templates = ensure_portrait_templates(ctx)
    if templates is None:
        log.warning('[cw-megastar] 立绘 SIFT 模板库缺失:识别通道全程未命中,'
                    '候选身份由 OCR 转换名承重')
        return lambda _crop: None

    def _identify(crop: MatLike) -> str | None:
        avatar_id, _inliers = identify_character(crop, templates)
        return resolve_char_name(avatar_id) if avatar_id else None

    return _identify


def read_megastar_options(
        ctx: SrContext, screen: MatLike,
        *, identify: IdentifyFn | None = None,
) -> list[MegastarOption]:
    """巨星候选检测 → ``MegastarOption`` 列表(char_id = 规范名)。

    检测模型(正本 = screens/megastar.md §3,逐条落):
    ① **弹窗标签带限定 OCR 定卡**:标签带 area「候选标签带」rect 限定
       OCR → 正则「盛会之星一X先生/女士」逐命中 → N = 命中数,每 hit
       得(标签中心 x, 原始名 X)。全屏扫已退役(全屏扫会把屏上其它
       「盛会之星」字样卷入,且旧实现的坐标按枚举序硬映射左右槽)。
    ② **逐卡立绘 SIFT 交叉验证**:每 hit 按卡身相对几何裁立绘区 → SIFT
       立绘库识别 → 裁决:SIFT 命中且与 OCR 名(经双源域标准化转换)
       一致 → 用之;不一致 = 识别质量不足以区分 → 该候选 char_id 置
       ``READ_FAILED`` 哨兵(整函数观察失败信号,见 return);SIFT 未命中
       → OCR 转换名承重(库缺新角色不硬依赖);OCR 名转换失败 → 原值
       保留过门(标准化门既有判法判域外失败)。
    ③ **xy = (该卡标签中心 x, 卡身线)**:y = ``CANDIDATE_BODY_Y`` 在册
       实测卡身线,x 随卡标签中心,每卡自带坐标,无枚举映射。
    ④ **输出序**:按标签中心 x 左→右 = idx 0..N-1(与词表/策略下标同系)。

    :param identify: 立绘身份识别注入点(``IdentifyFn``;None = 生产 SIFT
        链)。测试桩经此注入,禁 monkeypatch 私有。
    :return: 候选列表(按 x 左→右,xy 每卡自带)。失败信号 = 列表内含
        ``READ_FAILED`` 哨兵 ∨ 域外原值(调用方 observe 经
        ``standardize_megastar_options`` 门判失败 → round_fail 零写零
        上报交回重观察;fail 消息构造迭代本列表,原值/哨兵自然留证)。
        空列表 = 合法空读(标签带零命中,上游按候选空语义处理)。
        纯读零副作用。
    """
    band = _area_rect(ctx, _LABEL_BAND_AREA, _MEGASTAR_SCREEN)
    if band is None:
        # 建档漂移(标签带 area 缺失)= 确定性失败,空读语义(可自愈)
        # 不适用 → 哨兵列表交门响亮停。
        log.warning(f'[cw-megastar] 标签带 area {_LABEL_BAND_AREA!r} 缺失'
                    '(建档漂移?),观察失败')
        return [MegastarOption(idx=0, char_id=READ_FAILED, xy=None)]
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=band, color_range=None, crop_first=False,
    )
    hits: list[tuple[float, str]] = []   # (标签中心 x, 原始名 X)
    for text, mrl in ocr_map.items():
        if mrl.max is None:
            continue
        m = _MEGASTAR_RE.search(text)
        if m is None:
            continue
        hits.append((mrl.max.center.x, m.group(1)))
    hits.sort(key=lambda h: h[0])
    if not hits:
        return []
    # 双源匹配域(星徽动态域,现契约):gs 经 ctx 自取(生产调用点 observe
    # 已先做局外守卫,读链只在有 gs 时进入;局外直调 = 静态域 only)。
    match = getattr(ctx, 'cw_match', None)
    gs = getattr(match, 'gs', None) if match is not None else None
    domain = _megastar_match_domain(gs)
    domain_set = set(domain)
    if identify is None:
        identify = _default_identify(ctx)
    options: list[MegastarOption] = []
    for cx, raw in hits:
        norm = _normalize_char_name(raw)
        canon_ocr = (norm if norm in domain_set
                     else _MegastarGate._lcs_resolve(norm, domain))
        if not canon_ocr:
            # OCR 名域外 = 标准化门既有判法的失败:原值留列表过门
            # (门判域外 → None → round_fail,fail 消息含原值留证),
            # 无需 SIFT 反证(已必失败,省裁片识别算力)。
            log.warning(f'[cw-megastar] 候选 OCR 名标准化失败:{raw!r}'
                        '(域外名,过门判观察失败)')
            options.append(MegastarOption(idx=len(options), char_id=raw,
                                          xy=(int(cx), CANDIDATE_BODY_Y)))
            continue
        # 立绘裁区:画面内边界钳制(标签带建档保证 cx 在弹窗内,钳制防
        # 手改 rect 后负切片回卷)。
        x1 = max(0, int(cx) - _PORTRAIT_HALF_W)
        x2 = min(int(screen.shape[1]), x1 + 2 * _PORTRAIT_HALF_W)
        crop = screen[_PORTRAIT_Y1:_PORTRAIT_Y2, x1:x2]
        char_id = canon_ocr
        sift_name = identify(crop)
        if sift_name is not None and sift_name != canon_ocr:
            log.warning(f'[cw-megastar] 立绘 SIFT 与 OCR 名不一致:'
                        f'OCR={canon_ocr!r} SIFT={sift_name!r}'
                        '(识别质量不足以区分,置失败哨兵交门判观察失败)')
            char_id = READ_FAILED
        options.append(MegastarOption(idx=len(options), char_id=char_id,
                                      xy=(int(cx), CANDIDATE_BODY_Y)))
    return options


# ===== 观察标准化门(二次裁决门;规范 = op-layer.md §1.1)=====

# 巨星匹配域的阵营名(cw_chars 注册表 faction 字段值;成员表单一源 = 注册表,
# 禁手抄——注册表版本更新域自动跟进,缺新成员 = 转换失败响亮停逼修数据)。
_MEGASTAR_FACTION: str = '盛会之星'


class _MegastarGate:
    """巨星候选名转换的常量与 LCS 兜底解析(标准化门第②③判宿主)。

    阈值/边距 = 投资环境屏观察标准化门同族起步值(命名对齐
    ``CwScreenInvestEnv.ENV_LCS_THRESHOLD``/``ENV_LCS_AMBIGUITY_MARGIN``),
    随实测误读样本校准,单一源住本类。评分判法实现 = 域级单一源
    ``cw_obs_core.lcs_resolve_strict``(阈值过滤 + 次高分差拒判,全族
    统一;本类只绑巨星匹配域常量)——原手写循环镜像副本随批退役。
    """

    # LCS 兜底过阈值线(归一候选对域名的 LCS 长度 / 域名长度;同族 0.75
    # = 短名容单字误读的下限,3 字名 2/3 ≈ 0.667 不过、4 字名 3/4 = 0.75 过)。
    MEGASTAR_LCS_THRESHOLD: ClassVar[float] = 0.75
    # 歧义边距(判据 = 过阈值的最高分与次高分之差):低于 = 域内歧义不可
    # 分辨 → 转换失败。共享词素族阈值挡不住跨名借分(近分必有误读,禁猜
    # ——投资环境对抗审实证),边距拒判为必需防线。
    MEGASTAR_LCS_AMBIGUITY_MARGIN: ClassVar[float] = 0.15

    @classmethod
    def _lcs_resolve(cls, name: str, domain: list[str]) -> str:
        """LCS 兜底解析(判法单一源 = ``cw_obs_core.lcs_resolve_strict``,
        本方法只绑本类常量):域内逐名算分,过阈值入榜;稳定排序同分保
        域序(固定序,平分取序首 = 确定性);无过阈值命中 ∨ 最高/次高
        分差 < ``MEGASTAR_LCS_AMBIGUITY_MARGIN`` → 返回 ''(转换失败),
        否则返回最高分规范名。"""
        return lcs_resolve_strict(
            name, domain,
            threshold=cls.MEGASTAR_LCS_THRESHOLD,
            ambiguity_margin=cls.MEGASTAR_LCS_AMBIGUITY_MARGIN)


def _normalize_char_name(name: str) -> str:
    """形变归一起步族(设计钉面,族增补按实测误读样本且须随测试锁):
    去首尾空白 + 全角字母数字转半角。不做更激进形变——候选名短,误读以
    单字错为主,交 LCS 评分 + 边距拒判兜底。"""
    out: list[str] = []
    for ch in name.strip():
        code = ord(ch)
        if (0xFF10 <= code <= 0xFF19           # 全角数字 ０-９
                or 0xFF21 <= code <= 0xFF3A    # 全角大写 Ａ-Ｚ
                or 0xFF41 <= code <= 0xFF5A):  # 全角小写 ａ-ｚ
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return ''.join(out)


def _megastar_match_domain(gs: GameState | None) -> list[str]:
    """巨星屏合法候选域(转换匹配域;双源并集,用户裁定 2026-09-22):

    - ①静态 = cw_chars「盛会之星」阵营成员(注册表派生);
    - ②动态 = 场上(``gs.front_row``/``gs.back_row``)穿「盛会之星」羁绊
      星徽的角色(现读;判据复用 kernel 既有装备羁绊派生语义
      ``equip_bond_grants``——「星徽 = 装备者加入该羁绊」,禁观察域手搓
      第二套羁绊逻辑;开拓者按排归一形态,与 kernel ``unit_bond_tags``
      同口径)。

    收窄域即根除跨名误标准化通道:全表域下误读恰成另一注册名时精确腿
    直接放行错误标准名,边距拒判对精确腿不生效。gs 为 None(局外)只用
    静态源。已知缺口(残余风险,与设计同册):环境卡授予的星徽穿戴只显
    于左面板、行单位 ``equips`` 为空(实机实证,``cw_game_state.py`` 注
    在册)→ 该情形合法候选域外 → 转换失败响亮停逼修观察面,方向安全非
    无声错选;缺口收口 = 观察面扩员,另批。

    序 = 固定序(静态注册表序 → 前排 → 后排,去重保首见),是 LCS 评分
    「平分取序首」确定性的基础;域成员恒为注册表规范名(动态腿未注册
    身份不入域——域外标准名出口不存在,转换不了就在门上显式失败)。"""
    domain: list[str] = [c.name for c in chars_by_faction(
        _MEGASTAR_FACTION, include_flows=False)]
    if gs is None:
        return domain
    seen = set(domain)
    for row_name, row in (('front', gs.front_row.value),
                          ('back', gs.back_row.value)):
        for unit in (row or []):
            if unit is None:
                continue   # 槽位表空槽
            equips = getattr(unit, 'equips', None) or []
            if not any(_MEGASTAR_FACTION in equip_bond_grants(eq)
                       for eq in equips):
                continue
            cid = getattr(unit, 'char_id', '') or ''
            name = trailblazer_form(cid, row_name)
            if name and name in CHARACTERS and name not in seen:
                seen.add(name)
                domain.append(name)
    return domain


def standardize_megastar_options(
        options: list[MegastarOption],
        gs: GameState | None) -> list[MegastarOption] | None:
    """观察标准化门(op-layer.md §1.1;二次裁决门)。

    ``read_megastar_options`` 已在检测流程内完成标准化(折叠语义:双源
    域转换门 = SIFT 名/OCR 名都须在域内,域外失败)。本函数承载失败裁决:
    逐候选三判(①形变归一后域内精确命中 → 标准名;②不中 → 域内 LCS
    评分兜底;③最高/次高分差 < ``_MegastarGate.MEGASTAR_LCS_AMBIGUITY_
    MARGIN`` = 边距拒判)外加失败载体两判——候选 char_id =
    ``READ_FAILED`` 哨兵(reader 交叉验证反证失败)∨ ≥2 候选命中同一
    规范名(识别质量不足以区分)→ 返回 None。reader 已转换的规范名 ∈
    域内精确命中,幂等透传(防御性二次门语义不变)。

    判失败 → 返回 None:调用方 observe node round_fail 整函数早退,零写
    容器零上报零点击,交外循环重观察重读(禁带病上报;瞬时误读下轮新
    帧自愈,持续误读 = 连续 fail 至外环重派网响亮停,逼修数据;fail 消
    息迭代候选列表,原值/哨兵自然留证)。成功返回新 ``MegastarOption``
    列表(char_id = 规范名,``idx``/``xy`` 原值保留——动作参数纯序号 +
    观察上报坐标,转换只动名字、坐标原样携带(选择坐标观察上报同进退,
    规范 = op-layer.md §1.1))。纯读零副作用。"""
    domain = _megastar_match_domain(gs)
    domain_set = set(domain)
    resolved: list[MegastarOption] = []
    seen: set[str] = set()
    for o in options:
        if o.char_id == READ_FAILED:
            return None   # reader 交叉验证反证失败(哨兵,细节在 reader warn)
        norm = _normalize_char_name(o.char_id)
        canon = (norm if norm in domain_set
                 else _MegastarGate._lcs_resolve(norm, domain))
        if not canon or canon in seen:
            return None
        seen.add(canon)
        resolved.append(MegastarOption(idx=o.idx, char_id=canon, xy=o.xy))
    return resolved
