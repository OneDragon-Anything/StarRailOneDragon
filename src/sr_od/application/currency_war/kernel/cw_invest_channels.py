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

通用类线分 0(design §3.1:经济/规则/时代三类目——**专家类目例外**:
顾问入商店通道,批 2 落地,见 ``ENV_ADVISOR_CHARS``;顾问所赠角色
在场时另走证据分量,与通道分无冲突)。

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

#: 环境类目 → 通道档(design §3.1;经济/规则/时代三类目通用类不在表 =
#: 线分 0;**专家类目走顾问入商店通道**——见 ``_advisor_line_bonus``)。
_ENV_CATEGORY_TIER: dict[str, int] = {
    '概念股': INVEST_STRONG,   # ②定向刷新率
    '邀请': INVEST_MID,        # ③星徽
    '契约': INVEST_STRONG,     # ④期货任务链
}

#: 特邀专家顾问入商店卡 → 顾问角色名(统一阵容评分批 2;效果原文
#: 「获得专家顾问【X】,并使其在本局游戏中加入商店」直读)。
#: 通道语义判(批 2 任务「按 §3.1 商店结构语义判」):§3.1 通道②概念股
#: = 送人+入池+提率三件套(强档 +300);顾问卡 = 入池单腿(顾问不免费
#: 入席、需付费购买、不提率)——供给改写幅度弱一档,取**中档 +150**
#: (「使其加入商店」= 该角色可购性 0→1 的定向供给,0 分漏掉;强档
#: 高估——概念股的提率腿不存在)。
#: 目标线 = 顾问角色羁绊(factions∪flows)∩ 线核心键羁绊命中
#: (:func:`_faction_hit_bonus` 同一降档规则——flex 弱关联仍归 0)。
ENV_ADVISOR_CHARS: dict[str, str] = {
    '特邀专家:桑博': '桑博',
    # DOT 篇攻略「开局必须刷专家邀请环境」(桑博专家版硬依赖)的线分
    # 承载:桑博 is_expert 排除普通池,无本卡则桑博主C 不可购——
    # 可购性 0→1 即本通道语义。
    '特邀专家:加拉赫': '加拉赫',
    # 击破羁绊联动(「激活2/4/6/9击破羁绊时获得以太钻头」;ENV_FACTION
    # 例外行 '击破' 的线分消费位即此)。
    '特邀专家:停云': '停云',
    # 特邀专家:银狼**不入**:条件腿「当你首次获得【银狼LV.999】时」才
    # 获得顾问——env 持有 ≠ 顾问已解锁,持有期给分虚高;狼尊线证据由
    # 银狼LV.999 本体持有走证据分承载。
}

#: 策略侧专家顾问卡 → 顾问角色名(与 env 侧同一「顾问入商店」语义;
#: 效果原文同款句式直读)。查序在定义卡/引擎匹配/星徽之后——
#: '骇客专家:银狼' 已在 ``DEFINING_CARDS``(+500)短路,不双计。
STRATEGY_ADVISOR_CHARS: dict[str, str] = {
    '战术专家:佩拉': '佩拉',       # 佩拉=减益流派(减防输出),黄泉/千冶减益线+贝洛伯格线命中
    '潜行专家:貊泽': '貊泽',       # 狼狩/追击 → 追击飞霄命中
    '琼玉专家:青雀': '青雀',       # 仙舟/战技点 → 景元仙舟/龙丹命中
    '调饮专家:加拉赫': '加拉赫',   # 击破 → 巡海击破命中
    '贸易专家:停云': '停云',       # 仙舟/能量 → 景元仙舟/双王圣杯命中
    '锻冶专家:刃': '刃',           # 星核猎手/燃血 → 万敌单C(DOT队)命中
    '骇客专家:银狼': '银狼',       # 星核猎手/量子同频(定义卡短路备查)
    '摸个鱼吧I': '青雀',           # 「获得专家顾问【青雀】,并使其加入商店」同款句式
    # '领航专家:姬子' 不入:顾问名「姬子」不在 CHARACTERS 注册表(注册表
    # 只有姬子·启行;顾问姬子=独立形态卡)——无羁绊可查,0 分申报。
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


def _advisor_line_bonus(advisor_name: str, comp) -> int:
    """顾问入商店通道(批 2;档位与目标线语义见 ``ENV_ADVISOR_CHARS``
    表注):顾问角色羁绊 ∩ 线核心键 → 中档;仅 flex → 0(中档降档规则);
    顾问角色不在注册表 → 0(fail 方向不误伤)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    ch = CHARACTERS.get(advisor_name)
    if ch is None:
        return 0
    return max((_faction_hit_bonus(f, INVEST_MID, comp)
                for f in (*ch.factions, *ch.flows)), default=0)


def env_line_bonus(env_name: str, comp) -> int:
    """投资环境 → 单线加分(线分「投资环境分」分量;通道②③④按类目派生;
    专家类目 = 顾问入商店通道,见 :func:`_advisor_line_bonus`)。"""
    norm = normalize_invest_name(env_name)
    upgraded = EVIDENCE_UPGRADE.get((norm, comp.name))
    if upgraded is not None:
        return upgraded
    e = INVESTMENT_ENVS.get(norm)
    if e is None:
        return 0
    if e.category == '专家':
        advisor = ENV_ADVISOR_CHARS.get(norm)
        return _advisor_line_bonus(advisor, comp) if advisor else 0
    tier = _ENV_CATEGORY_TIER.get(e.category)
    if tier is None:
        return 0   # 通用类(经济/规则/时代):线分 0
    return _faction_hit_bonus(e.faction, tier, comp)


def strategy_line_bonus(strategy_name: str, comp) -> int:
    """投资策略 → 单线加分(线分「投资策略分」分量/选卡方向分)。

    查序 = 实证覆盖升档 → 定义卡 → ⑤引擎匹配手编表 → ③星徽效果原文 →
    顾问入商店通道(批 2,``STRATEGY_ADVISOR_CHARS``——与 env 侧同语义,
    定义卡/引擎表在前短路防双计);通道①送人跳过(证据分自动覆盖);
    ②④策略侧现无对应效果条目(随机/装备类未来条目按效果文本在此扩展)。
    未注册名 → 0(OCR 形变经 ``normalize_invest_name`` 先归一,
    fail 方向 = 0 分不误伤)。
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
    advisor = STRATEGY_ADVISOR_CHARS.get(norm)
    if advisor:
        return _advisor_line_bonus(advisor, comp)
    return 0


def env_line_bonuses(env_name: str) -> dict[str, int]:
    """环境名 → {线名: 加分}(全库扫描;flow 遥测/锚点诊断查询面)。"""
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    norm = normalize_invest_name(env_name)
    return {c.name: v for c in COMP_LIBRARY
            if (v := env_line_bonus(norm, c)) > 0}


def env_strong_lines(env_name: str) -> tuple[str, ...]:
    """环境名 → **全档命中**线名元组(羁绊 ∈ 线 form_tiers/or_reqs;flex
    降档线不入——flex = 弱关联,不构成「为谁服务」面)。

    消费 = 阵容冲突护栏指向集(``cw_investments.env_faction_scope`` 通道
    派生分支):护栏问强方向冲突,弱关联线(线分里 +30/0 降档)不该制造
    兼容性。与线分的 flex 降档规则分工:线分回答「值几分」(flex 弱关联
    仍值软档分),本函数回答「是否定向」(flex 不算)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    norm = normalize_invest_name(env_name)
    e = INVESTMENT_ENVS.get(norm)
    if e is None or e.category not in _ENV_CATEGORY_TIER or not e.faction:
        return ()
    out: list[str] = []
    for comp in COMP_LIBRARY:
        core_keys = set(comp.form_tiers) \
            | {f for f, _t in (getattr(comp, 'or_reqs', None) or ())}
        if e.faction in core_keys:
            out.append(comp.name)
    return tuple(out)


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
    移除后静默失联防线,沿 ENV_ECONOMY 孤儿键校验先例);顾问表卡名落
    对应注册表 + 顾问角色名 ∈ CHARACTERS(写错名 = 通道静默 0)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
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
    for card in ENV_ADVISOR_CHARS:
        if card not in INVESTMENT_ENVS:
            raise ValueError(f'env 顾问表孤儿卡名(环境注册表无此卡):{card!r}')
        if ENV_ADVISOR_CHARS[card] not in CHARACTERS:
            raise ValueError(
                f'env 顾问表角色不在 CHARACTERS:{card!r}×{ENV_ADVISOR_CHARS[card]!r}')
    for card in STRATEGY_ADVISOR_CHARS:
        if card not in INVESTMENT_STRATEGIES:
            raise ValueError(f'策略顾问表孤儿卡名(策略注册表无此卡):{card!r}')
        if STRATEGY_ADVISOR_CHARS[card] not in CHARACTERS:
            raise ValueError(
                f'策略顾问表角色不在 CHARACTERS:{card!r}×{STRATEGY_ADVISOR_CHARS[card]!r}')


def _line_exists(line_name: str) -> bool:
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    return get_comp(line_name) is not None


_validate_manual_tables()
