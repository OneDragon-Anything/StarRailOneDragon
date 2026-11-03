"""货币战争 投资通道派生(环境 83/策略 335 → 线加分;design §3.1/§3.2)。

替代退役的 ``ENV_COMP_AFFINITY``/``AUGMENT_COMP_AFFINITY`` 两亲和表
(design §7 退役清单):投资-线关联的运行时单一源改为本模块的效果原文
通道派生。通道与档值(design §3.1/§3.2 + §2 数量级表):

- ①送人(立即):跳过——赠达角色入持有面,线分证据分量自动覆盖
  (选卡侧另有赠卡分承载;通道自身 0 分);
- ②定向刷新率(概念股类目):强档 +300;
- ③星徽(邀请类目/策略效果「【X星徽】」原文):中档 +150(实证近硬绑
  条目升强档 +750,见 ``EVIDENCE_UPGRADE``);
- ④期货任务链(契约类目):强档 +300;
- ⑤引擎匹配(策略侧手编知识表):中档 +150——效果原文解析不了的逐条
  人工判(必查源 = lock_rules 现登记 + final_comps README A3;解析不了
  的登记于此,随机类记 0)。

通用类 41 个线分 0(design §3.1:经济 15/规则 10/时代 6/专家 10——
专家类含特邀专家族,其价值经所赠角色走证据分,通道 0)。

**加分目标线**(design §3.1):通道②③④⑤按羁绊命中——羁绊 ∈ 目标线
``form_tiers``/``or_reqs`` 键 = 全档;仅 ∈ ``flex_factions`` = 降档
(强→+30 软档/中→0);未命中 0。``EVIDENCE_UPGRADE``/``DEFINING_CARDS``
为点名登记(线名直指,不走羁绊命中,不降档)。

查询防线:入口一律先 ``normalize_invest_name``(OCR 间隔号形变不静默
miss,run_20260826_004527 缺陷链先例;沿 augment_affinity 查表口径)。
"""
from __future__ import annotations

import re

from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    INVESTMENT_STRATEGIES,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_line_scales import (
    EVIDENCE_UPGRADE_BONUS,
    INVEST_DEFINING,
    INVEST_MID,
    INVEST_SOFT,
    INVEST_STRONG,
)

#: 实证覆盖升档表(design §2「实证覆盖升档」行:量子星徽×3→希儿
#: (0.9 近硬绑)/罗刹→列车)。键 = (规范卡名, 线名);值升强档 +750,
#: 覆盖通道③默认 +150。出处 = final_comps/README.md A3 开局信号分层
#: (类专属策略/策略驱动层)——「直接记载 > 类间概括 > 机制推定」的实证半边。
EVIDENCE_UPGRADE: dict[tuple[str, str], int] = {
    # 量子星徽三张(量子同频邀请〔环境〕+ 量子同频星徽 + 套组〔策略〕)
    ('量子同频邀请', '希儿量子'): EVIDENCE_UPGRADE_BONUS,
    ('量子同频星徽', '希儿量子'): EVIDENCE_UPGRADE_BONUS,
    ('量子同频星徽套组', '希儿量子'): EVIDENCE_UPGRADE_BONUS,
    # 罗刹开局改变三月七身份 = 列车线策略驱动信号(final_jizi_train
    # 直通线信号谱「策略驱动」层;final_comps README A3)。
    ('本姑娘就是罗刹', '列车同行'): EVIDENCE_UPGRADE_BONUS,
}

#: 定义卡表(design §2「投资强档·定义卡」:黑塔纪元/专家邀请/飞光——
#: 「拿到即定义线」的手编登记,效果原文解析不出,逐条人工判定)。
#: 键 = 策略规范名;值 = (线名, 依据)。环境侧无定义卡条目(专家类目 10
#: 个全属通用类 0,design §3.1 类目计数)。
DEFINING_CARDS: dict[str, tuple[tuple[str, ...], str]] = {
    # 「没有黑塔纪元这条线基本不存在」(final_daheita_aoe 构造机理,
    # 32/38 篇用它开局):216 张黑塔入商店的供给结构改写。
    '黑塔纪元': (('大黑塔银河学者',),
               'final_daheita_aoe 构造机理「没有黑塔纪元这条线基本不存在」'),
    # 师徒羁绊机制 = 景元线入口(飞光·映月=镜流+特殊1费景元/传剑=彦卿+
    # 景元;final_longtail_others 景元节「拿到=近乎硬绑」)。
    '飞光·映月': (('景元仙舟',), 'final_longtail_others 景元节:师徒机制=线入口'),
    '飞光·传剑': (('景元仙舟',), 'final_longtail_others 景元节:师徒机制=线入口'),
    # 专家邀请族(design §2 定义卡例「专家邀请」):银狼主题专家策略,
    # lock_rules 现登记(final_yinlang_joy 开局策略节,10 篇)+
    # README A3 类专属策略层。
    '骇客专家:银狼': (('狼尊欢愉',),
                  'final_yinlang_joy 开局策略节银狼专属;README A3 类专属策略'),
}

#: ⑤引擎匹配手编表(design §3.2 通道⑤:战斗增益 × 引擎类型,键 = 羁绊,
#: 走羁绊命中/降档规则;姬子拆分前双轴任一 hit 即中档归批 3)。
#: 登记口径 = 效果原文绑定某羁绊成员/引擎的战斗增益策略(必查源 =
#: lock_rules 现登记 + README A3;随机类记 0)。批 1 三张:
ENGINE_SYNERGY_FACTIONS: dict[str, tuple[str, ...]] = {
    # 希儿引擎(同频层数×造物引擎再现):README A3 类专属策略(希儿)。
    '量子力学': ('量子同频',),
    # 造物引擎伤害 400%:引擎直绑(README A3 类专属策略,希儿)。
    '钢铁美学': ('量子同频',),
    # 减益成员攻击/终结技增伤 = 减益系引擎增益(黄泉减益 lock_rules 现登记
    # 「黄泉专属增伤策略」;羁绊键派生使千冶减益同享——纯加权零特例,
    # 两线主派同为减益,机制上面板同效)。
    '离火燎原': ('减益',),
}

#: 环境类目 → 通道档(design §3.1;经济/规则/时代/专家四类目 41 个通用
#: 类不在表 = 线分 0)。
_ENV_CATEGORY_TIER: dict[str, int] = {
    '概念股': INVEST_STRONG,   # ②定向刷新率
    '邀请': INVEST_MID,        # ③星徽
    '契约': INVEST_STRONG,     # ④期货任务链
}

#: 策略效果原文的星徽授予模式(通道③:「获得…【X星徽】」直读)。
_EMBLEM_PATTERN = re.compile(r'【(.{1,8}?)星徽】')


def _faction_hit_bonus(faction: str, tier: int, comp) -> int:
    """羁绊命中档判定(design §3.1「加分目标」):

    - ``faction`` ∈ 目标线 ``form_tiers``/``or_reqs`` 键 → 全档值;
    - 仅 ∈ ``flex_factions`` → 降档(强档 → 软档 +30/中档 → 0);
    - 未命中 → 0(通用卡)。
    """
    if not faction:
        return 0
    core_keys = set(comp.form_tiers) \
        | {f for f, _t in (getattr(comp, 'or_reqs', None) or ())}
    if faction in core_keys:
        return tier
    if faction in (comp.flex_factions or ()):
        return INVEST_SOFT if tier >= INVEST_STRONG else 0
    return 0


def env_line_bonus(env_name: str, comp) -> int:
    """投资环境 → 单线加分(线分「投资环境分」分量;通道②③④按类目派生)。"""
    norm = normalize_invest_name(env_name)
    upgraded = EVIDENCE_UPGRADE.get((norm, comp.name))
    if upgraded is not None:
        return upgraded
    e = INVESTMENT_ENVS.get(norm)
    if e is None:
        return 0
    tier = _ENV_CATEGORY_TIER.get(e.category)
    if tier is None:
        return 0   # 通用类 41 个(经济/规则/时代/专家):线分 0
    return _faction_hit_bonus(e.faction, tier, comp)


def strategy_line_bonus(strategy_name: str, comp) -> int:
    """投资策略 → 单线加分(线分「投资策略分」分量/选卡方向分)。

    查序 = 实证覆盖升档 → 定义卡 → ⑤引擎匹配手编表 → ③星徽效果原文;
    通道①送人跳过(证据分自动覆盖);②④策略侧现无对应效果条目(随机/
    装备类未来条目按效果文本在此扩展)。未注册名 → 0(OCR 形变经
    ``normalize_invest_name`` 先归一,fail 方向 = 0 分不误伤)。
    """
    norm = normalize_invest_name(strategy_name)
    upgraded = EVIDENCE_UPGRADE.get((norm, comp.name))
    if upgraded is not None:
        return upgraded
    defining = DEFINING_CARDS.get(norm)
    if defining is not None and comp.name in defining[0]:
        return INVEST_DEFINING
    st = INVESTMENT_STRATEGIES.get(norm)
    if st is None:
        return 0
    factions = ENGINE_SYNERGY_FACTIONS.get(norm)
    if factions:
        return max((_faction_hit_bonus(f, INVEST_MID, comp)
                    for f in factions), default=0)
    emblems = set(_EMBLEM_PATTERN.findall(st.effect))
    if emblems:
        return max((_faction_hit_bonus(f, INVEST_MID, comp)
                    for f in emblems), default=0)
    return 0


def env_line_bonuses(env_name: str) -> dict[str, int]:
    """环境名 → {线名: 加分}(全库扫描;flow 遥测/锚点诊断查询面)。"""
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    norm = normalize_invest_name(env_name)
    return {c.name: v for c in COMP_LIBRARY
            if (v := env_line_bonus(norm, c)) > 0}


def strategy_line_bonuses(strategy_name: str) -> dict[str, int]:
    """策略名 → {线名: 加分}(全库扫描;flow 遥测喂入的替换查询口,
    替代退役的 ``augment_affinity``;判读口径 = 通道派生线分加分,
    非 0..1 亲和权重)。"""
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    norm = normalize_invest_name(strategy_name)
    return {c.name: v for c in COMP_LIBRARY
            if (v := strategy_line_bonus(norm, c)) > 0}


def _validate_manual_tables() -> None:
    """构建校验(import 即炸):手编表卡名必须落在对应注册表(版本改名/
    移除后静默失联防线,沿 ENV_ECONOMY 孤儿键校验先例)。"""
    for card, line in EVIDENCE_UPGRADE:
        if card not in INVESTMENT_ENVS and card not in INVESTMENT_STRATEGIES:
            raise ValueError(f'实证覆盖升档表孤儿卡名(注册表无此卡):{card!r}')
        if not _line_exists(line):
            raise ValueError(f'实证覆盖升档表孤儿线名:{line!r}')
    for card, (lines, _why) in DEFINING_CARDS.items():
        if card not in INVESTMENT_STRATEGIES:
            raise ValueError(f'定义卡表孤儿卡名(策略注册表无此卡):{card!r}')
        for line in lines:
            if not _line_exists(line):
                raise ValueError(f'定义卡表孤儿线名:{line!r}')
    for card in ENGINE_SYNERGY_FACTIONS:
        if card not in INVESTMENT_STRATEGIES:
            raise ValueError(f'引擎匹配表孤儿卡名(策略注册表无此卡):{card!r}')


def _line_exists(line_name: str) -> bool:
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    return get_comp(line_name) is not None


_validate_manual_tables()
