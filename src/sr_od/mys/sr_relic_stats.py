"""遗器词条语义常量层（MCP 评估与游戏内 op 共用的单一实现点）。

五表三函数原下沉自 ``sr_od.backend.mcp.relic_eval_tools``（下沉取舍 =
别名表/口径包双份必漂移，语义只有一个消费者集合但两个调用场景；归属层 =
``sr_od/mys/`` 与 ``sr_codes.PROPERTY_INFO_SNAPSHOT`` 同层的既有惯例，
出处 = docs/develop/sr_od/application/cultivation/changes/2026-11-12-relic-equip-flow
design.md §2.2 下沉清单）。

标准名口径（名册核对定稿结论；依据 = 两份在库真实名册产物：
``sr_od.mys.sr_codes.PROPERTY_INFO_SNAPSHOT``（实测词典 56 码词条名快照）与
真实响应 fixture ``sr-od-test/test/fixtures/mys/hkrpg_avatar_info_detail_sample.json``
的 property_info 词条侧名及其经 ``sr_mys_client`` 映射的断言样例）：

- 生命值/攻击力/防御力三词在名册词条名（name_cn）中**平坦与百分比同名**
  （词条码 27/32 同名「生命值」、29/33 同名「攻击力」、31/34 同名「防御力」；
  fixture pt=33 词条侧名实证「攻击力」）——flat/% 只能由 value 的 ``%``
  后缀判别。名册侧标准名按「name_cn + % 后缀」消歧：带 % → 「生命值提高/
  攻击力提高/防御力提高」（百分比标准名），不带 % → 名词本体（平坦）。
  命中分桶与求和按消歧后标准名，flat 与 % 因此不混。
- 名册词条 name_cn 全集（relics/ornaments 六件域，据上两源核对定稿）：
  生命值/攻击力/防御力/速度/暴击率/暴击伤害/效果命中/效果抵抗/击破特攻/
  能量恢复效率/治疗量加成/七属性伤害提高（物理/火/冰/雷/风/量子/虚数）。
  未入标准名全集的词由调用方显式报告，不静默错数。
- 游戏内 OCR 词条文本与名册 name_cn 同为官方文本，与名册侧共用同一套
  解析（``resolve_roster_stat`` 的 % 后缀消歧同样适用于游戏内数值串）。

零 IO、零副作用：本模块只做词条词/词条名/数值串 → 标准名与数值的纯解析。
"""

#: 词条标准名全集（别名/口径包展开与同名直通的命中判据；全集核对出处见
#: 模块 docstring）
STANDARD_STAT_NAMES: frozenset[str] = frozenset({
    '生命值', '攻击力', '防御力',  # 平坦值（名册同名直通）
    '生命值提高', '攻击力提高', '防御力提高',  # 百分比值（名册侧经 % 后缀消歧）
    '速度', '暴击率', '暴击伤害', '效果命中', '效果抵抗', '击破特攻',
    '能量恢复效率', '治疗量加成',
    '物理属性伤害提高', '火属性伤害提高', '冰属性伤害提高',
    '雷属性伤害提高', '风属性伤害提高', '量子属性伤害提高', '虚数属性伤害提高',
})

#: 平坦/百分比同名异义的三词（名册 name_cn 无法区分，靠 value 的 % 后缀
#: 消歧；出处见模块 docstring 名册核对结论）
FLAT_PERCENT_HOMONYM_NAMES: frozenset[str] = frozenset({'生命值', '攻击力', '防御力'})

#: 同名异义三词的百分比标准名
PERCENT_STANDARD_BY_NAME: dict[str, str] = {
    '生命值': '生命值提高',
    '攻击力': '攻击力提高',
    '防御力': '防御力提高',
}

#: 速记别名表：口径入参用词 → 标准名（用词依据 = mys_get_roster_detail
#: 字段名与 game-coach 角色档措辞）
STAT_NAME_ALIASES: dict[str, str | list[str]] = {
    '攻击%': '攻击力提高',
    '大攻击': '攻击力提高',
    '攻击力百分比': '攻击力提高',
    '生命%': '生命值提高',
    '大生命': '生命值提高',
    '防御%': '防御力提高',
    '大防御': '防御力提高',
    '暴击': '暴击率',
    '暴伤': '暴击伤害',
    '爆伤': '暴击伤害',
    '命中': '效果命中',
    '抵抗': '效果抵抗',
    '击破': '击破特攻',
    '充能': '能量恢复效率',
    '回能': '能量恢复效率',
    '治疗': '治疗量加成',
    '双暴': ['暴击率', '暴击伤害'],
    '速度': '速度',  # 同名直通
}

#: 口径包表：速记 → 标准名集合（定稿判据 =
#: 验收名单 12 人角色档口径行实际用到的包，与名册词条名全集无关）
STAT_PACKS: dict[str, list[str]] = {
    '双暴攻': ['暴击率', '暴击伤害', '攻击力提高'],
    '速双暴': ['速度', '暴击率', '暴击伤害'],
    '双暴生': ['暴击率', '暴击伤害', '生命值提高'],
    '击破速': ['击破特攻', '速度'],
    '命中速': ['效果命中', '速度'],
    '生命双暴': ['生命值提高', '暴击率', '暴击伤害'],
}


def resolve_criteria_word(word: object) -> list[str] | None:
    """口径入参词条词 → 标准名列表（口径包 → 别名 → 标准名直通）。

    返回 None = 三表都归不上（未识别词；调用方显式报告并按无效处理）。
    """
    if not isinstance(word, str):
        return None
    pack = STAT_PACKS.get(word)
    if pack is not None:
        return list(pack)
    alias = STAT_NAME_ALIASES.get(word)
    if alias is not None:
        return [alias] if isinstance(alias, str) else list(alias)
    if word in STANDARD_STAT_NAMES:
        return [word]
    return None


def resolve_roster_stat(name_cn: object, value: object) -> str | None:
    """词条名 → 标准名（同名异义三词按 value 的 % 后缀消歧）。

    名册词条名与游戏内 OCR 词条文本均为官方文本，共用本解析。返回
    None = 未识别词条名（调用方显式报告；该条不进命中/统计）。
    """
    if not isinstance(name_cn, str):
        return None
    if name_cn in FLAT_PERCENT_HOMONYM_NAMES:
        value_text = value if isinstance(value, str) else str(value)
        if value_text.endswith('%'):
            return PERCENT_STANDARD_BY_NAME[name_cn]
        return name_cn
    if name_cn in STANDARD_STAT_NAMES:
        return name_cn
    return None


def parse_stat_value(value: object) -> tuple[float, str | None]:
    """词条数值字符串 → (数值, 警告文案 | None)。

    带 % 结尾 → 去后缀按百分数值；无 % → flat 数值；解析失败按 0 计并返回
    警告文案（由调用方追加进对应告警列表）。
    """
    text = value if isinstance(value, str) else ('' if value is None else str(value))
    try:
        if text.endswith('%'):
            return float(text[:-1]), None
        return float(text), None
    except ValueError:
        return 0.0, f'数值「{text}」解析失败，按 0 计'
