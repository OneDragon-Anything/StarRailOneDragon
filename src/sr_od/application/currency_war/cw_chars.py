"""货币战争 角色领域模型(Character + CHARACTERS 注册表;meta 层,V4.4)。

**来源**:米游社百科「货币战争图鉴·员工」`channel/map/209/210`(content/info API,2026-08-03;
人读 data doc 已删 2026-08-18,注册表即单一源)。

**为什么建模**(用户 2026-08-03):核心实体(角色/阵营/策略/环境/装备)应是**正规 model 类 + 注册表**
(可查询、可校验、有类型关系),而非字符串散落各处。本模块是角色域:
- ``Character``:单角色(费用/站位/类型/阵营/流派/独立羁绊)。
- ``CHARACTERS``:全量注册表(V4.4 75 名,含停云),**角色规范名单一真相源**;费用/站位/trait 已按攻略广场官方接口(plaza config,2026-08-15)全面对齐。
- ``cw_chars_data.PLAZA_ROLES``:plaza 原始条目数据(75 条,含 id/技能名/is_hide/is_expert;同名多档各一条),由 ``tools/cw/gen_plaza_chars.py`` 生成——**手写注册表与官方接口的对拍基线**(版本更新重跑生成后 diff 本表)。
- ``CHARACTER_ROSTER``:规范名集合(从 CHARACTERS 派生,供 core_chars 校验)。
- 查询:``chars_by_cost`` / ``chars_by_faction`` / ``char_position_pref``。

⚠️ 版本依赖:角色随赛季扩充变动;版本更新重抓 characters.md 后同步本表。
**规范名原则**:OCR/char_id/COMP_LIBRARY.core_chars/config.character_priority 都用规范名(非粉丝昵称)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    """单个货币战争角色(V4.4 图鉴规范数据)。"""
    name: str                   # 规范名(如 "姬子·启行"/"Archer",非"红A")
    cost: int                   # 费用 1-5(图鉴 rate;卡芙卡=2 等)
    position: str               # "front"(前台)/ "back"(后台)/ "flex"(前后台)
    char_type: str              # 类型:输出/治疗/护盾/辅助(多标签用 "、" 分隔,如 "治疗、辅助")
    factions: tuple[str, ...]   # 阵营羁绊(仙舟/贝洛伯格/…;无则空)
    flows: tuple[str, ...]      # 流派羁绊(击破/燃血/…;无则空)
    independent: str = ""       # 独立羁绊名(挚爱之人/救世主/大守护者…;无则 "")
    source: str = ""            # 米游社 content_id

    def position_pref(self) -> str:
        """部署站位偏好 → "front"/"back"(flex 默认 back,可被 comp formation 覆盖)。"""
        if self.position == "front":
            return "front"
        return "back"   # back / flex → back(flex 可前可后,默认后排放后续 comp 阵型调整)


# ===== 开拓者形态切换(用户 2026-08-16 指示:羁绊计算须注意其特殊性) =====
# 机制:同一开拓者,**前台=记忆形态 / 后台=欢愉形态**(拖到另一排即切换命途,羁绊随之变:
# 记忆=列车+能量;欢愉=列车+能量+欢愉 → 后台独有「欢愉」羁绊)。plaza switch_freq 363 次切换
# = 同局反复换排是常态操作。注册表两形态独立条目(立绘不同,SIFT 按立绘判身份),但**身份
# 计算(羁绊/计数)必须按「当前排」归一形态** —— 旧代码按 char_id 原值算,换排后:
# 欢愉形态拖上前排 → 游戏内已变记忆(欢愉羁绊消失)而 tracking 仍记欢愉 → 欢愉计数虚高、
# 记忆侧漏算。
_TRAILBLAZER_FORMS: dict[str, dict[str, str]] = {
    # 归一基名 → {排: 该排的形态规范名}
    '开拓者': {'front': '开拓者·记忆', 'back': '开拓者·欢愉'},
}


def trailblazer_form(name: str, row: str) -> str:
    """开拓者按排归一形态名:``row`` = "front"/"back";非开拓者原样返回。

    兜底:归一名缺(row 为空/异常值)→ 按注册表 position_pref 推(与排一致的那张)。
    """
    for base, forms in _TRAILBLAZER_FORMS.items():
        if base in name:
            if row in forms:
                return forms[row]
            from sr_od.application.currency_war.cw_chars import CHARACTERS as _C
            cur = _C.get(name)
            if cur is not None and cur.position_pref() == row:
                return name   # 已是目标排形态
            other = forms.get('front' if row == 'back' else 'back', '')
            return other or name
    return name


def is_trailblazer(name: str) -> bool:
    return any(base in name for base in _TRAILBLAZER_FORMS)


def _ch(name: str, cost: int, position: str, char_type: str,
        factions: str = "", flows: str = "", independent: str = "", source: str = "") -> Character:
    """构造助手:阵营/流派用"、"分隔的字符串 → tuple。空串 → 空 tuple。"""
    return Character(
        name=name, cost=cost, position=position, char_type=char_type,
        factions=tuple(f for f in factions.split("、") if f) if factions else (),
        flows=tuple(f for f in flows.split("、") if f) if flows else (),
        independent=independent, source=source,
    )


# ===== CHARACTERS 注册表(V4.4 74 名,🟢 米游社原文;开拓者按命途合并性别)=====
CHARACTERS: dict[str, Character] = {c.name: c for c in [
    # —— 1 费 ——
    _ch("阿格莱雅", 1, "front", "输出", "昼之半神", "能量", source="6552"),
    _ch("乱破", 1, "front", "输出", "巡海游侠", "击破", source="6551"),
    _ch("大丽花", 1, "flex", "输出", "盛会之星", "击破", source="6999"),
    _ch("艾丝妲", 1, "front", "辅助", "银河学者", "持续伤害", source="6536"),
    _ch("黑塔", 1, "flex", "输出", "银河学者", "群攻", source="6535"),
    _ch("青雀", 1, "front", "输出", "仙舟", "战技点", source="6534"),
    _ch("飞霄", 1, "front", "输出", "狼狩", "追击", source="6373"),
    _ch("椒丘", 1, "front", "治疗、辅助", "狼狩", "持续伤害、减益", source="6531"),  # trait 对齐 plaza:+狼狩(characters.md 阵营速查早已有,注册表漏,2026-08-15)
    _ch("加拉赫", 1, "flex", "治疗", "盛会之星", "治疗、击破", source="6522"),
    _ch("娜塔莎", 3, "flex", "治疗", "贝洛伯格", "治疗", source="6548"),  # 费用勘误 1→3(广场 config rarity+bwiki 双源,2026-08-15)
    _ch("桑博", 1, "flex", "输出", "贝洛伯格、星间旅人", "持续伤害", source="6554"),
    _ch("赛飞儿", 1, "front", "辅助", "夜之半神", "追击、减益", source="6553"),
    _ch("万敌", 1, "flex", "输出", "夜之半神", "燃血", source="6541"),
    _ch("翡翠", 1, "back", "输出、辅助", "公司", "群攻", source="6550"),
    _ch("停云", 1, "back", "辅助", "仙舟", "能量", source=""),  # 补录:plaza id=1202,is_expert 专家顾问,技能佳音降祥瑞(2026-08-15)
    _ch("藿藿", 1, "flex", "治疗、辅助", "仙舟", "治疗、能量", source="6398"),
    _ch("三月七", 1, "back", "护盾", "列车同行", "护盾", source="6537"),
    _ch("刃", 1, "back", "输出", "星核猎手", "燃血", source="6532"),
    _ch("貊泽", 1, "back", "输出、辅助", "狼狩", "追击", source="6530"),  # trait 对齐 plaza:-减益(2026-08-15)
    _ch("远坂凛", 1, "flex", "输出", "命运圣杯", "战技点", source="7879"),
    # —— 2 费 ——(卡芙卡图鉴 rate=2费,1费阵容常用)
    _ch("卡芙卡", 2, "flex", "输出、辅助", "星核猎手", "持续伤害", source="6538"),
    _ch("千冶·刃", 2, "back", "输出", "星核猎手", "燃血、减益", source="7886"),
    _ch("吉尔伽美什", 2, "flex", "输出", "命运圣杯", "能量", source="7880"),
    _ch("绯英", 2, "flex", "输出", "星间旅人", "欢愉", source="7467"),
    _ch("不死途", 2, "flex", "输出", "巡海游侠", "追击", source="7465"),
    _ch("爻光", 1, "flex", "辅助", "仙舟", "欢愉", source="7000"),  # 费用勘误 2→1(广场 config rarity+bwiki 双源,2026-08-15)
    _ch("砂金", 2, "front", "护盾、输出", "公司", "追击、护盾", source="6400"),
    _ch("阮·梅", 2, "back", "辅助", "银河学者", "击破", source="6399"),
    _ch("银枝", 2, "flex", "输出、辅助", "星间旅人", "群攻", source="6392"),  # 站位对齐 plaza Common=flex(2026-08-15)
    _ch("丹恒·饮月", 2, "front", "输出", "仙舟、列车同行", "战技点", source="6383"),
    _ch("风堇", 2, "front", "治疗、输出", "昼之半神", "治疗、燃血", source="6540"),
    _ch("丹恒·腾荒", 2, "back", "护盾", "夜之半神", "护盾", source="6539"),
    _ch("缇宝", 2, "flex", "辅助、输出", "昼之半神", "群攻、量子同频", source="6542"),
    _ch("花火", 2, "back", "辅助", "盛会之星", "战技点、量子同频", source="6401"),
    _ch("灵砂", 2, "front", "治疗、输出", "狼狩", "治疗、击破", source="6261"),
    _ch("佩拉", 2, "back", "辅助、输出", "贝洛伯格", "减益", source="6133"),  # trait 对齐 plaza:+减益(2026-08-15)
    # —— 3 费 ——
    _ch("姬子·启行", 3, "front", "输出", "列车同行", "", independent="领航员", source="7881"),
    _ch("姬子", 3, "back", "输出", "列车同行", "击破", source="6272"),
    _ch("忘归人", 3, "back", "辅助、输出", "仙舟", "击破", source="6549"),
    _ch("希儿", 3, "front", "输出", "贝洛伯格", "量子同频", source="6547"),
    _ch("Saber", 3, "flex", "输出", "命运圣杯", "能量", source="6546"),
    _ch("刻律德菈", 3, "flex", "辅助", "夜之半神", "战技点", source="6544"),
    _ch("那刻夏", 3, "back", "输出、辅助", "昼之半神", "群攻", source="6543"),
    _ch("镜流", 3, "back", "输出", "狼狩", "燃血", source="6284"),
    _ch("黄泉", 3, "front", "输出", "巡海游侠", "减益", source="6290"),
    _ch("真理医生", 3, "front", "输出", "银河学者、星间旅人", "追击", source="6285"),
    _ch("星期日", 3, "flex", "辅助", "盛会之星、列车同行", "能量", source="6185"),
    _ch("白厄", 3, "front", "输出", "", "", independent="救世主", source="6134"),
    _ch("银狼LV.999", 3, "front", "输出", "星核猎手", "欢愉", independent="头号玩家", source="7466"),  # ⚠️ 3/4/5 费三档:升星升费(3星拖上场→4费1星→同理5费,备战不升费);cost=起始费,多档建模待策略层需要时扩(广场 id 15061/15062/15063,2026-08-15)
    # —— 4 费 ——
    _ch("开拓者·欢愉", 4, "back", "辅助", "列车同行", "能量、欢愉", source="7469"),  # trait 对齐 plaza 8009:+能量(2026-08-15)
    _ch("火花", 4, "front", "输出", "星间旅人", "战技点、欢愉", source="7001"),
    _ch("长夜月", 4, "flex", "输出、辅助", "夜之半神", "燃血", source="6545"),  # trait 对齐 plaza:-战技点(2026-08-15)
    _ch("海瑟音", 4, "front", "输出", "昼之半神", "持续伤害", source="6269"),
    _ch("波提欧", 4, "front", "输出", "巡海游侠", "击破", source="6268"),
    _ch("符玄", 4, "back", "治疗、辅助", "仙舟", "治疗、量子同频", source="6259"),  # trait 对齐 plaza:-贝洛伯格(2026-08-15)
    _ch("知更鸟", 4, "back", "辅助、输出", "盛会之星", "追击", source="6250"),
    _ch("大黑塔", 4, "front", "输出", "银河学者", "群攻", source="6249"),
    _ch("遐蝶", 4, "front", "输出", "夜之半神", "燃血", source="6248"),
    _ch("开拓者·记忆", 4, "front", "辅助、输出", "列车同行", "能量", source="6247"),  # trait 对齐:+列车同行(plaza 共享模板+bwiki 记忆页;plaza 隐藏条目8007为共享壳,2026-08-15)
    _ch("银狼", 4, "flex", "辅助、输出", "星核猎手", "量子同频", source="6245"),
    _ch("杰帕德", 4, "front", "护盾、输出", "贝洛伯格", "护盾", source="6244"),
    _ch("彦卿", 4, "back", "输出", "仙舟、狼狩", "减益", source="6132"),
    # —— 5 费 ——
    _ch("流萤", 5, "front", "输出", "星核猎手", "击破", source="6452"),
    _ch("昔涟", 5, "front", "辅助、输出", "昼之半神、夜之半神", "", independent="挚爱之人", source="6190"),
    _ch("布洛妮娅", 5, "front", "辅助、输出", "", "燃血", independent="大守护者", source="6189"),  # trait 对齐 plaza 可见条目11012=燃血+大守护者(去贝洛伯格);隐藏条目11011=贝洛伯格+大守护者(变体,2026-08-15)
    _ch("Archer", 5, "front", "输出", "命运圣杯", "战技点", independent="魔术师", source="6188"),
    _ch("云璃", 5, "back", "输出", "狼狩", "能量", source="6187"),
    _ch("黑天鹅", 5, "back", "输出、辅助", "盛会之星", "持续伤害", independent="命运卜者", source="6186"),
    _ch("景元", 5, "front", "输出", "仙舟", "群攻", source="6137"),  # trait 对齐 plaza:-能量(2026-08-15)
    _ch("托帕&账账", 5, "back", "输出、辅助", "公司", "追击", source="6136"),
    _ch("瓦尔特", 5, "front", "输出、辅助", "列车同行、星间旅人", "减益", source="6135"),
    _ch("罗刹", 4, "back", "治疗", "星间旅人", "治疗", source="6252"),  # 费用勘误5→4+站位对齐 plaza Back(2026-08-15)
    # —— 特殊召唤单位(投资策略赠送;不可拖动/不可卖,固定占后排)——
    # r75 狸猫局建档:投资策略「龙虎兄弟狸」送双狸猫(弟弟狸小虎=蓝/哥哥狸小龙=红,同造型
    # 异色 → identify_character 色相仲裁区分,_RED_HUE_PAIRS)。cost=0(非购买单位);
    # 无阵营无流派(纯增益挂件,效果=【随便骰子】)。
    _ch("狸小虎", 0, "back", "", "", "", source="live:龙虎兄弟狸"),
    _ch("狸小龙", 0, "back", "", "", "", source="live:龙虎兄弟狸"),
]}

# 规范名集合(从 CHARACTERS 派生;供 COMP_LIBRARY.core_chars / config.character_priority 校验)
CHARACTER_ROSTER: frozenset[str] = frozenset(CHARACTERS.keys())


# ===== 查询 =====

def get_char(name: str) -> Character | None:
    """按规范名取 Character;无则 None。"""
    return CHARACTERS.get(name)


def chars_by_cost(cost: int) -> list[Character]:
    """某费用的全部角色。"""
    return [c for c in CHARACTERS.values() if c.cost == cost]


def chars_by_faction(faction: str, include_flows: bool = True) -> list[Character]:
    """属某阵营的角色(include_flows=True 则也匹配流派羁绊)。

    成员关系派生自 CHARACTERS(角色自报 factions/flows)—— FactionInfo.members() 调本函数。
    """
    out = [c for c in CHARACTERS.values() if faction in c.factions]
    if include_flows:
        out += [c for c in CHARACTERS.values() if faction in c.flows and c not in out]
    return out
