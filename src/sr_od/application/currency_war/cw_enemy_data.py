"""敌情注册表(15 号提案 v0;ADR-0160;2026-08-16)。

**诊断(15 号)**:对手信息「管线已建、资产为零、消费两个散件」—— boss_fit 接缝建成数周
出口接空表(comp.countered_by_bosses 用俗称「剧目/电视机」,而 state.plane_bosses 是规范
公司名「造梦兄弟影业」,**名字空间错位 → 永不命中**,task#73 遗留)。本模块 = v0:
①BOSS_NICKNAMES 俗称→规范名映射(打通 boss_fit);
②BOSS_MECHANICS 20 boss 机制 tag 注册表(bosses.md 图鉴实采,版本 V4.4);
③matchup(comp 机制属性 × boss 机制)结构层 —— 可解释 reasons 输出。

数据来源:docs/game/currency_war/data/bosses.md(游戏内数据银行图鉴 OCR,权威;
19/20 已采,1 锁待)。克制方向:competitors.md + comp_library.md 攻略对策句(🟡 多源,
E2 判据:与人类共识方向一致率 ≥85% 待实机校验)。
"""
from __future__ import annotations

# ===== ①俗称 → 规范公司名(打通 boss_fit 的名字空间错位) =====
# 来源:bosses.md 图鉴标题括注(剧目=造梦兄弟影业/蕉研组=造梦互动娱乐 实锤)+ 攻略语境。
# 电视机/红绿灯/琥珀王/死龙/酒杯怪 = 玩家对部分 boss/小怪的昵称,尚未一一定位到规范名
# (V3.7 文档语境:红绿灯/电视机=频率限制类怪,琥珀王/死龙/酒杯怪=反伤/高防类)——
# 先按**机制 tag** 映射(BOSS_MECHANIC_NICKS),规范名定位后迁移。
BOSS_NICKNAMES: dict[str, str] = {
    '剧目': '造梦兄弟影业',
    '蕉研组': '造梦互动娱乐',
    '造梦兄弟': '造梦兄弟影业',
}

# ===== ②boss 机制注册表(20 个;bosses.md 实采) =====
# tag 词汇(与 comp.mechanic_attributes/MECHANIC_COUNTERS 同本体):
#   aoe(boss 群攻多)/ summon(召唤多目标)/ dot(持续伤害)/ control(冻结/禁锢/支配)/
#   heal_cut(削治疗)/ self_heal(自我治疗)/ counter_attack(反击)/ share_hp(共享血量)/
#   break_bonus(击破利好机制)/ crit_resist(克暴击)/ shield_break(削韧克护盾)/
#   freeze_combo(冻结联动增伤)/ enrage_stack(叠层增伤)/ boss_debuff(侵蚀类降生命)
BOSS_MECHANICS: dict[str, tuple[str, ...]] = {
    '火线动力机甲': ('aoe', 'dot', 'heal_cut'),
    '银甲武装公司': ('aoe', 'summon'),
    '增熵能源集团': ('aoe', 'summon', 'self_heal', 'boss_debuff'),
    '智识实验室': ('summon', 'control', 'break_bonus'),
    '金血记忆体联盟': ('shield_break', 'summon', 'break_bonus', 'boss_debuff'),
    '虫人兵器': ('aoe', 'summon', 'crit_resist', 'dot', 'self_heal', 'break_bonus'),
    '火花网络传媒': ('control', 'summon'),
    '钢铁意志集团': ('aoe', 'summon'),
    '造梦兄弟影业': ('share_hp', 'break_bonus'),
    '造梦互动娱乐': ('share_hp', 'break_bonus'),
    '猎星资本': ('control', 'dot'),
    '纷争前线军团': ('control', 'counter_attack'),
    '灰手生命科技': ('control', 'boss_debuff', 'summon'),
    '凛冬经贸联合体': ('control', 'freeze_combo', 'summon'),
    '铁盾安保集团': ('counter_attack', 'summon'),
    '深穹智械科技': ('summon', 'control'),
    '冷锋兵器工业': ('aoe', 'control', 'freeze_combo'),
    '巨鹿生物制药': ('summon', 'self_heal'),   # 建木?(bosses.md 该节较略,tag 从简)
    '不死者联盟': ('self_heal', 'summon'),       # telemetry 实录名(图鉴 19+第20锁)
    '绘师家族产业': ('aoe',),                    # 同上(实采待补详)
}

# boss 机制 tag → 克/利我方 comp 机制属性(结构层;comp_library.md/competitors.md 攻略句)
# key=boss tag;counters=克我方属性(我方带此属性 → 打该 boss 减分);synergies=利我方属性。
BOSS_MECHANIC_NICKS: dict[str, str] = {
    # 俗称(未定位规范名)→ 机制 tag 挂钩(comp_library.md 攻略语义)
    '电视机': 'speed_lock',      # 禁速克速度依赖
    '红绿灯': 'freq_limit',      # 频率限制克高频
    '琥珀王': 'thorns',          # 反伤克高频低单次
    '死龙': 'thorns',
    '酒杯怪': 'thorns',
    '单体boss': 'single_burst',  # 单体爆发 boss(长战)
    '单体长战': 'single_burst',
    '永久创伤': 'heal_cut',      # 掉血削上限(敌人词缀,非 boss;挂 tag 复用)
}

# 我方 comp.mechanic_attributes 俗称 → 结构 tag(与上面 BOSS_MECHANIC_NICKS 对齐)
COMP_ATTR_TAGS: dict[str, str] = {
    '速度依赖': 'speed_dep',
    '高频攻击': 'freq_high',
    '治疗护盾': 'heal_shield',
    '持续伤害': 'dot_dep',
    '燃血': 'blood_burn',
    '治疗': 'heal_dep',
    '群攻': 'aoe_clear',
    '击破': 'break_dep',
    '暴击': 'crit_dep',
    '幸运一击': 'crit_dep',
    '护盾': 'shield_dep',
    '减益叠加': 'debuff_dep',
    '欢愉叠层': 'joy_stack',
    '反击': 'counter_dep',
}

# 结构克/利表(boss tag × 我方 tag;方向:boss 的该机制 克/利 我方的该机制)
# 依据:bosses.md 克制启示 + comp_library.md 攻略句(🟡 多源,待 E2 校验)
_TAG_COUNTERS: dict[str, tuple[str, ...]] = {
    'heal_cut': ('heal_dep', 'heal_shield'),      # 削治疗克治疗队
    'crit_resist': ('crit_dep',),                  # 速效进化克暴击
    'counter_attack': ('freq_high',),              # 反击克高频(每击挨反)
    'thorns': ('freq_high',),                      # 反伤克高频低单次
    'speed_lock': ('speed_dep',),                  # 禁速克速度依赖
    'freq_limit': ('freq_high',),                  # 频率限制克高频
    'freeze_combo': ('melee_front',),              # 冻结增伤(前排近战承压)
    'control': ('joy_stack',),                     # 控制(解控前)扰连携节奏
}
_TAG_SYNERGIES: dict[str, tuple[str, ...]] = {
    'summon': ('aoe_clear',),                      # 召唤多目标 → 群攻清
    'break_bonus': ('break_dep',),                 # 击破奖励机制 → 击破流利
    'share_hp': ('aoe_clear', 'single_burst_ok'),  # 共享血量 → 群攻/单点皆可
    'aoe': ('shield_dep',),                        # boss AoE → 护盾挡
}


def normalize_boss_name(name: str) -> str:
    """俗称/简称 → 规范公司名(BOSS_NICKNAMES);已规范原样返。"""
    return BOSS_NICKNAMES.get(name, name)


def boss_tags(bosses: list[str]) -> tuple[str, str]:
    """本局 boss 列表(可含俗称)→ (规范名列表 joined, 机制 tag 集 joined)。"""
    canon = [normalize_boss_name(b) for b in bosses]
    tags: set[str] = set()
    for b in canon:
        tags.update(BOSS_MECHANICS.get(b, ()))
        # 俗称直接挂 tag(电视机/琥珀王等未定位规范名的)
        t = BOSS_MECHANIC_NICKS.get(b)
        if t:
            tags.add(t)
    return ','.join(canon), ','.join(sorted(tags))


def matchup(comp_mechanics: list[str], bosses: list[str]) -> tuple[float, list[str]]:
    """结构层 matchup:我方 comp 机制属性 × 本局 boss 机制 → (score, reasons)。

    score ∈ [0,1],0.5 中性;每条克制 -0.15,每条利好 +0.12(方向先验,E2 待校);
    reasons 可解释输出(「boss机制×我方属性=克/利」),供日志/复盘/12 号问询卡消费。
    空 boss / 无机制 → (0.5, [])(中性,boss_fit None 语义由调用方处理)。
    """
    if not bosses or not comp_mechanics:
        return 0.5, []
    _canon, tags_str = boss_tags(bosses)
    tags = {t for t in tags_str.split(',') if t}
    my_tags = {COMP_ATTR_TAGS.get(m, m) for m in comp_mechanics if m}
    score = 0.5
    reasons: list[str] = []
    for bt in tags:
        for mt in _TAG_COUNTERS.get(bt, ()):
            if mt in my_tags:
                score -= 0.15
                reasons.append(f'boss[{bt}]×我方[{mt}]=克')
        for mt in _TAG_SYNERGIES.get(bt, ()):
            if mt in my_tags:
                score += 0.12
                reasons.append(f'boss[{bt}]×我方[{mt}]=利')
    return max(0.0, min(1.0, score)), reasons
