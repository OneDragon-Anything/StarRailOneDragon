"""货币战争 盛会之星观察域单一文件 = reader + standardizer:

- ``read_megastar_options`` = OCR 读巨星候选(原始 OCR 名,零转换,只报读数);
- ``standardize_megastar_options`` = 观察标准化门(候选名 → cw_chars 规范名;
  规范 = ``screens/op-layer.md`` §1.1「观察标准化门」,家族形态镜像投资环境
  屏 ``cw_screen_invest_env`` 的观察标准化门)。

巨星观察自 ``cw_node_obs.py`` 迁入独立文件:正本 op-layer.md §5 卷首
「一屏一解析器」,同 ``cw_briefing_obs.py``/``cw_settlement_obs.py`` 惯例;
生产消费方唯一 = ``operations/cw_screen/cw_screen_megastar.py``(observe
node 选中半读链)。

候选点击坐标随本读链一并观察上报(规范 = op-layer.md §1.1「选择坐标
观察上报」):本文件 = 候选兜底常量宿主(坐标生产半住观察域),动作 op
按 ``idx`` 自容器 ``megastar_opts[idx].xy`` 取点,零坐标现算。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.utils.str_utils import longest_common_subsequence_length
from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    chars_by_faction,
    trailblazer_form,
)
from sr_od.application.currency_war.kernel.cw_bond_equips import equip_bond_grants
from sr_od.application.currency_war.kernel.cw_events import MegastarOption
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# 巨星候选标题「盛会之星一X先生/女士!」→ X = 角色名(花火/星期日…)。实测 OCR 核实(2026-08-07 cw_megastar)。
# 先生/女士 + 全/半角叹号容错(OCR 渲染不一)。
_MEGASTAR_RE = re.compile(r'盛会之星一(.+?)(先生|女士)[!！]?')

# 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边);名位置 = 卡身选中区。
# 常量 = screen_info 缺失兜底;首选 area_center('候选-左')。
CANDIDATE_LEFT: Point = Point(822, 333)
# 右候选(星期日)位 —— OCR 名 @x1061 y334(cw_megastar 实测 2026-08-07);同 y。
# 常量 = 兜底;首选 area_center('候选-右')。
CANDIDATE_RIGHT: Point = Point(1061, 333)


def read_megastar_options(ctx: SrContext, screen: MatLike) -> list[MegastarOption]:
    """OCR 巨星节点候选 → ``MegastarOption`` 列表(char_id 从「盛会之星一X先生/女士!」解析)。

    巨星候选 = 盛会之星 bond(花火/星期日…)给全队 buff。按候选名 center-x 左→右排序 → ``idx``。
    候选点击坐标随观察一并上报(选择坐标观察上报,规范 = op-layer.md §1.1):
    idx 0 = 左候选、其余 = 右候选(本屏左右各一候选的两候选布局),取值 =
    screen_info ``currency_war_megastar`` 的「候选-左」/「候选-右」area 中心,
    area 缺失回退本文件兜底常量 ``CANDIDATE_LEFT``/``CANDIDATE_RIGHT``;产出
    ``tuple[int, int]``(1080p 游戏空间)。decide_megastar 按 target.core_chars
    选(含盛会之星 → 绑该角色;否则 buff 契合)。本函数只报读数(原始 OCR
    名,零转换),读不到 → []。标准化契约 = 观察侧转换门(调用方 observe 调
    ``standardize_megastar_options``;规范 = op-layer.md §1.1「观察标准化
    门」),转换失败 = 观察失败 round_fail 零写零上报。
    """
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=None, color_range=None, crop_first=False,
    )
    cands: list[tuple[int, str]] = []   # (center_x, char_id)
    for text, mrl in ocr_map.items():
        if mrl.max is None:
            continue
        m = _MEGASTAR_RE.search(text)
        if m is None:
            continue
        cands.append((mrl.max.center.x, m.group(1)))
    cands.sort(key=lambda c: c[0])
    options: list[MegastarOption] = []
    for i, (_cx, name) in enumerate(cands):
        area_pt = (area_center(ctx, '候选-左', '货币战争-盛会之星') if i == 0
                   else area_center(ctx, '候选-右', '货币战争-盛会之星'))
        fallback = CANDIDATE_LEFT if i == 0 else CANDIDATE_RIGHT
        pt = area_pt if area_pt is not None else fallback
        options.append(MegastarOption(idx=i, char_id=name,
                                      xy=(int(pt.x), int(pt.y))))
    return options


# ===== 观察标准化门(候选名 → 规范名;规范 = op-layer.md §1.1)=====

# 巨星匹配域的阵营名(cw_chars 注册表 faction 字段值;成员表单一源 = 注册表,
# 禁手抄——注册表版本更新域自动跟进,缺新成员 = 转换失败响亮停逼修数据)。
_MEGASTAR_FACTION: str = '盛会之星'


class _MegastarGate:
    """巨星候选名转换的常量与 LCS 兜底评分(标准化门第②③判宿主)。

    阈值/边距 = 投资环境屏观察标准化门同族起步值(命名对齐
    ``CwScreenInvestEnv.ENV_LCS_THRESHOLD``/``ENV_LCS_AMBIGUITY_MARGIN``),
    随实测误读样本校准,单一源住本类。评分原语 = 手写循环逐名算分,禁
    ``find_best_match_by_lcs``:后者只返回唯一下标、无次高分,歧义边距腿
    (第③判)经它不可实现。
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
        """LCS 兜底解析(镜像投资环境 ``_lcs_resolve`` 实形):域内逐名
        算分,过阈值入榜;稳定排序同分保域序(固定序,平分取序首 = 确定
        性);无过阈值命中 ∨ 最高/次高分差 < ``MEGASTAR_LCS_AMBIGUITY_
        MARGIN`` → 返回 ''(转换失败),否则返回最高分规范名。"""
        scored: list[tuple[float, str]] = []
        for reg_name in domain:
            pct = (longest_common_subsequence_length(name, reg_name)
                   / len(reg_name))
            if pct >= cls.MEGASTAR_LCS_THRESHOLD:
                scored.append((pct, reg_name))
        if not scored:
            return ''
        scored.sort(key=lambda t: t[0], reverse=True)   # 稳定排序:同分保域序
        if (len(scored) > 1 and scored[0][0] - scored[1][0]
                < cls.MEGASTAR_LCS_AMBIGUITY_MARGIN):
            return ''
        return scored[0][1]


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
                continue   # ADR-0392 槽位表空槽
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
    """观察标准化门(op-layer.md §1.1;``read_megastar_options`` 读出后、
    组装 obs 前逐候选三判转换):匹配域 = 屏合法候选域(双源并集,见
    ``_megastar_match_domain``)。逐候选:①形变归一(``_normalize_char_
    name``)后域内精确命中 → 标准名;②不中 → 域内 LCS 评分兜底 → 过
    阈值命中 = 标准名;③歧义边距拒判:最高/次高分差 <
    ``_MegastarGate.MEGASTAR_LCS_AMBIGUITY_MARGIN`` = 域内歧义不可分辨
    → 转换失败。

    判失败集 = 任一候选①②③皆不中 ∨ ≥2 候选命中同一规范名(识别质量
    不足以区分)→ 返回 None:调用方 observe node round_fail 整函数早退,
    零写容器零上报零点击,交外循环重观察重读(禁带病上报;瞬时误读下轮
    新帧自愈,持续误读 = 连续 fail 至外环重派网响亮停,逼修数据)。成功
    返回新 ``MegastarOption`` 列表(char_id = 规范名,``idx``/``xy`` 原
    值保留——动作参数纯序号 + 观察上报坐标,转换只动名字、坐标原样携带
    (选择坐标观察上报同进退,规范 = op-layer.md §1.1),容器
    ``megastar_opts`` 值域自此 = 规范名 + 观察期坐标)。纯读零副作用。"""
    domain = _megastar_match_domain(gs)
    domain_set = set(domain)
    resolved: list[MegastarOption] = []
    seen: set[str] = set()
    for o in options:
        norm = _normalize_char_name(o.char_id)
        canon = (norm if norm in domain_set
                 else _MegastarGate._lcs_resolve(norm, domain))
        if not canon or canon in seen:
            return None
        seen.add(canon)
        resolved.append(MegastarOption(idx=o.idx, char_id=canon, xy=o.xy))
    return resolved
