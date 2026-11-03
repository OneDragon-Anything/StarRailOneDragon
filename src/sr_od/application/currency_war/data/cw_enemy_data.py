"""敌情注册表(boss 俗称映射 + 机制 tag 观察分组)。

①BOSS_NICKNAMES 俗称→规范名映射(简报 boss 读数两段转换第一段;
白厄重开级 boss 记载用俗称「史瓦罗」,2026-11 统一阵容评分批 2 补映射);
②BOSS_MECHANICS 20 boss 机制 tag 注册表(bosses.md 图鉴实采,版本 V4.4)
——tag 只作观察分组,**不参线分**(线侧 boss 克制单一源 =
``kernel/cw_affinity_table.BOSS_AFFINITY`` 攻略实证吃怕表)。

数据来源:docs/game/currency_war/data/bosses.md(游戏内数据银行图鉴 OCR,权威;
**2026-08-17 重采 20/20 全量**,原始截图 .debug/temp/currency_war/boss_shots_0817/)。
"""
from __future__ import annotations

# ===== ①俗称 → 规范公司名(简报 boss 读数归一;bosses.md 旧档遗留说明) =====
# 来源:bosses.md 图鉴标题括注 + 用户核对(2026-08-17):
#   电视机=造梦互动娱乐 / 死龙=灰手生命科技 / 酒杯怪=造梦兄弟影业(荒宴醉/欢宴罪酒宴主题)。
#   琥珀王=铁盾安保集团(V3.7 攻略"杰帕德反击=模拟宇宙琥珀王回归"+用户确认;以牙还牙反击)。
#   红绿灯=小怪非 boss(用户确认,忽略)。
#   史瓦罗=深穹智械科技( bosses.md 图鉴括注「代表:史瓦罗」;白厄重开级 boss
#   记载用此名——统一阵容评分批 2 入表,final_baie_reflect「史瓦罗 = 重开级」)。
#   ⚠️ 祸源萨姆→虫人兵器**不入**(待实机校验:虫人兵器代表「示死祸源:深魇蝗灾」
#   vs 火线动力机甲代表「星核猎手·萨姆」词素两可,登记在
#   cw_affinity_table.BOSS_NAME_PENDING 待验证表)。
BOSS_NICKNAMES: dict[str, str] = {
    '剧目': '造梦兄弟影业',
    '蕉研组': '造梦互动娱乐',
    '造梦兄弟': '造梦兄弟影业',
    '电视机': '造梦互动娱乐',     # 用户确认(2026-08-17)
    '死龙': '灰手生命科技',        # 用户确认(2026-08-17)
    '酒杯怪': '造梦兄弟影业',      # 用户确认(2026-08-17)
    '琥珀王': '铁盾安保集团',      # 用户确认(2026-08-17;反击=琥珀王回归语境)
    '史瓦罗': '深穹智械科技',      # bosses.md 图鉴括注(代表:史瓦罗);批 2 入表
}

# ===== ②boss 机制注册表(20 个;bosses.md 实采,2026-08-17 重采校准) =====
# tag 词汇(观察分组用;线侧克制方向不消费本表——单一源 =
# kernel/cw_affinity_table.BOSS_AFFINITY 攻略实证吃怕表):
#   aoe(boss 群攻多)/ summon(召唤多目标)/ dot(持续伤害)/ control(冻结/禁锢/支配)/
#   heal_cut(削治疗)/ self_heal(自我治疗)/ counter_attack(反击)/ share_hp(共享血量)/
#   break_bonus(击破利好机制)/ crit_resist(克暴击)/ shield_break(削韧克护盾)/
#   freeze_combo(冻结联动增伤)/ enrage_stack(叠层增伤)/ boss_debuff(侵蚀类降生命)
BOSS_MECHANICS: dict[str, tuple[str, ...]] = {
    '火线动力机甲': ('aoe', 'dot', 'heal_cut', 'break_bonus'),   # 熔火引擎:弱点击破解除次级燃烧+回战技点
    '银甲武装公司': ('aoe', 'summon'),
    '增熵能源集团': ('aoe', 'summon', 'self_heal', 'boss_debuff'),
    '智识实验室': ('summon', 'control', 'break_bonus'),
    '金血记忆体联盟': ('shield_break', 'summon', 'break_bonus', 'boss_debuff'),
    '虫人兵器': ('aoe', 'summon', 'crit_resist', 'dot', 'self_heal', 'break_bonus'),
    '火花网络传媒': ('control', 'summon'),                        # 连麦PK隔离+主场免控
    '钢铁意志集团': ('aoe', 'summon', 'break_bonus'),             # 合金保姆剥抗菌层=击破窗口;蓄力弱点无效
    '造梦兄弟影业': ('share_hp', 'break_bonus'),
    '造梦互动娱乐': ('share_hp', 'break_bonus'),
    '猎星资本': ('control', 'dot'),
    '纷争前线军团': ('control', 'counter_attack'),
    '灰手生命科技': ('control', 'boss_debuff', 'summon', 'dot'),  # 汝不能停步:特殊DoT按当前生命百分比
    '凛冬经贸联合体': ('control', 'freeze_combo', 'summon'),
    '铁盾安保集团': ('counter_attack', 'summon'),
    '深穹智械科技': ('summon', 'control'),
    '冷锋兵器工业': ('aoe', 'control', 'freeze_combo'),
    '巨鹿生物制药': ('summon', 'aoe'),                           # 枝梢数放大斑龙触;蕉覆韧性锁(时窗性)
    '不死者联盟': ('aoe', 'control', 'self_heal'),               # 幸福6层傀儡化+凶梦汲取吸血(2026-08-17 采)
    '绘师家族产业': ('aoe', 'dot', 'summon'),                     # 怨火灼身DoT高覆盖+吞神子嗣(2026-08-17 采)
}

BOSS_MECHANIC_NICKS: dict[str, str] = {
    # 俗称→机制 tag 挂钩(俗称已全部定位规范名或确认为小怪,此表只剩非 boss 词缀类)
    '单体boss': 'single_burst',  # 单体爆发 boss(长战)
    '单体长战': 'single_burst',
    '永久创伤': 'heal_cut',      # 掉血削上限(敌人词缀,非 boss;挂 tag 复用)
}


def normalize_boss_name(name: str) -> str:
    """俗称/简称 → 规范公司名(BOSS_NICKNAMES);已规范原样返。"""
    return BOSS_NICKNAMES.get(name, name)


def boss_tags(bosses: list[str]) -> tuple[str, str]:
    """本局 boss 列表(可含俗称)→ (规范名列表 joined,机制 tag 集 joined)。"""
    canon = [normalize_boss_name(b) for b in bosses]
    tags: set[str] = set()
    for b in canon:
        tags.update(BOSS_MECHANICS.get(b, ()))
        # 俗称直接挂 tag(电视机/琥珀王等未定位规范名的)
        t = BOSS_MECHANIC_NICKS.get(b)
        if t:
            tags.add(t)
    return ','.join(canon), ','.join(sorted(tags))


