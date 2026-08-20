# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 阵营/羁绊(factions)数据库。

**来源**:米游社百科「货币战争图鉴」(V4.4,2026-08-03 抓取,权威 🟢 原文),详见
`docs/game/currency_war/data/factions.md`(31 羁绊逐层效果)。
**版本依赖**:羁绊构成与激活阈值随赛季更新变动,以米游社百科/游戏图鉴为准、实机左面板
OCR 为真值;本表是 V4.4 快照,供策略 eval 用。

羁绊分类:
- **combat**(战力/伤害/强度型):直接提升战斗能力,eval 权重最高。
- **economy**(经济/资源型):给金币/晶矿/月光精华等资源。
- **support**(辅助/机制/生存型):治疗/护盾/能量/战技点/属性增益等。
- **independent**(独立羁绊,单角色专属):1 层,eval 权重低(非买牌目标)。

每个羁绊的 ``tiers`` = 激活阈值(几人激活第 N 层),如仙舟 (3,5,7,10)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FactionInfo:
    """单个阵营/羁绊信息(model 类;成员从 CHARACTERS 反查,单一真相源)。"""
    cn: str  # 中文名
    category: str  # "combat" | "economy" | "support" | "independent"
    tiers: tuple[int, ...]  # 激活阈值(几人激活第 N 层)
    note: str = ""  # 简述效果(自 data/traits_full.md 官方原文派生,版本对拍更新)
    desc: str = ""  # 效果原文(官方 config API 逐字;r155 起,源=data/traits_full.md)

    def members(self, include_flows: bool = True) -> list[str]:
        """该羁绊的成员角色名(从 CHARACTERS 反查;include_flows=True 含流派羁绊成员)。

        成员关系是**派生**的(角色自报 factions/flows),不在 FactionInfo 重复硬编码 ——
        改 CHARACTERS 自动传导,单一真相源(工程化原则)。
        """
        from sr_od.application.currency_war.cw_chars import chars_by_faction
        return [c.name for c in chars_by_faction(self.cn, include_flows=include_flows)]


# 米游社百科 V4.4 权威(docs/game/currency_war/data/traits_full.md 为源数据存档,
# 官方 config API 逐字 desc 由 r155 灌入;版本升级→重抓 config→对拍更新)。
# 分类按效果归类;tiers 为逐层激活人数。
FACTIONS: dict[str, FactionInfo] = {
    # ===== 阵营羁绊(13)=====
    # —— combat(战力/召唤/伤害)——
    "仙舟": FactionInfo("仙舟", "combat", (3, 5, 7, 10), "召唤神君(全体雷伤),高层极强;3/5/7/10 人",
                        "【仙舟】召唤【神君】。【仙舟】队员行动后为【神君】叠加段数并使其行动提前。【仙舟】队员的前/后台强度和速度提高。"),
    "贝洛伯格": FactionInfo("贝洛伯格", "combat", (2, 4), "造物引擎(满能拉条伤害最多者立即行动),2/4 人;成型快",
                            "【贝洛伯格】队员行动后为【造物引擎】充能,能量充满后攻击敌人并让本场战斗中造成伤害最多的贝洛伯格角色立即行动。贝洛伯格队员和【造物引擎】的强度提高。"),
    "星核猎手": FactionInfo("星核猎手", "combat", (2, 3, 4), "猎星人协助,伤害+生命增幅;2/3/4 人",
                            "装备最多的【星核猎手】成为【猎星人】,【星核猎手】会协助【猎星人】作战。【星核猎手】的强度和速度提高。"),
    "狼狩": FactionInfo("狼狩", "combat", (3, 5, 6, 8), "召唤步离人(按装备成长),3/5/6/8 人",
                        "召唤【步离人】协同战斗,其在参与战斗后可以获得经验并升级。我方队员携带更多装备会使其额外获得经验。【狼狩】队员的前/后台强度提高,【步离人】每次升级后使该加成提高50%。"),
    "盛会之星": FactionInfo("盛会之星", "combat", (2, 3, 4, 5, 6), "选巨星给独特加成,高层(5/6)极强",
                            "选择1名【盛会之星】角色作为【巨星】,使我方小队获得独特加成。"),
    "列车同行": FactionInfo("列车同行", "combat", (2, 4, 6), "星穹列车撞击+光轨强度,2/4/6 人(V4.4 姬子·启行核心)",
                            "召唤【星穹列车】撞击敌人并留下【光轨】,使我方小队的前/后台强度提高。"),
    "巡海游侠": FactionInfo("巡海游侠", "combat", (1, 2, 3, 4), "伤害+速度增幅,后台星级加成前台;1/2/3/4 人",
                            "【巡海游侠】们获得伤害和速度提高。若将【巡海游侠】放置于后台,则位于后台的【巡海游侠】的星级会使前台【巡海游侠】额外获得伤害和速度提高。"),
    "命运圣杯": FactionInfo("命运圣杯", "combat", (2, 3, 4, 5), "祈愿试炼(难度换奖励)+强度;2/3/4/5 人",
                            "【命运圣杯】提供祈愿试炼,完成试炼以获得各种奖励。祈愿试炼的难度和奖励随羁绊等级提升。【命运圣杯】成员的前/后台强度提高。"),
    # —— economy(经济/资源)——
    "昼之半神": FactionInfo("昼之半神", "combat", (3, 4, 6, 9), "白昼装备(速度↔强度,纯战力曲线),阿格莱雅轮椅流核心;3/4/6/9 人(boss 电视机克;review r1 从 economy 改 combat)",
                            "获得仅供【昼之半神】穿戴的白昼装备。【昼之半神】队员的前/后台强度和速度提高。"),
    "夜之半神": FactionInfo("夜之半神", "economy", (2, 4, 7, 9), "月光精华→晶矿(完胜翻倍);2/4/7/9 人",
                            "每个战斗阶段后生成【月光精华】,完胜后获得2倍【月光精华】。获得足够的【月光精华】后可以获取晶矿奖励。【夜之半神】队员的前/后台强度提高。"),
    "银河学者": FactionInfo("银河学者", "economy", (2, 4, 6), "猫猫糕(回血+减伤)+DNA 奖励;2/4/6 人",
                            "基于【银河学者】们的星级叠加【猫猫糕】,并根据层数获得额外奖励。"),
    # —— support(辅助/机制/生存)——
    "公司": FactionInfo("公司", "support", (2, 3), "后台强度+护盾+每节点金币;2/3 人",
                        "【公司】队员的后台强度和护盾提高;每个节点获得金币。"),
    "星间旅人": FactionInfo("星间旅人", "support", (1, 2, 3, 4, 5, 6, 7), "按人数线性加成(1→7 层),双倍收益",
                            "【星间旅人】角色会为你的小队提高特定属性,随场上【星间旅人】角色数量而提升。【星间旅人】队员获得双倍收益。"),
    "量子同频": FactionInfo("量子同频", "support", (2, 3, 4, 5), "敌方受伤提高+同频强化技能;2/3/4/5 人",
                            "敌人受到的伤害提高。【量子同频】角色获得可强化技能效果的【同频】。"),

    # ===== 流派羁绊(12)=====
    # —— combat ——
    "追击": FactionInfo("追击", "combat", (3, 5, 7, 9), "追加攻击+连动总攻击(真伤);3/5/7/9 人"),
    "击破": FactionInfo("击破", "combat", (2, 4, 6, 9), "超击破+冲击波(全体真伤);2/4/6/9 人(V4.4:姬子成专家顾问, tiers 由 2/4/6/8/10 调至 2/4/6/9,见赛季文 76641553)"),
    "持续伤害": FactionInfo("持续伤害", "combat", (2, 4, 6), "DoT 增幅+超激发;2/4/6 人(遇'净化身心'环境别玩)"),
    "群攻": FactionInfo("群攻", "combat", (3, 5, 7, 9), "幸运一击+借力球(转移伤害)+激光;3/5/7/9 人"),
    "减益": FactionInfo("减益", "combat", (2, 4, 6, 8), "离火(造伤降+真伤);2/4/6/8 人"),
    "燃血": FactionInfo("燃血", "combat", (2, 4, 6, 8), "生命/伤害增幅+燃血角斗场(记录损失生命造伤);2/4/6/8 人"),
    # —— support ——
    "能量": FactionInfo("能量", "support", (3, 5, 7, 10), "终结技增幅+能量地块;3/5/7/10 人"),
    "战技点": FactionInfo("战技点", "support", (2, 4, 6, 8), "战技点上限+伤害+抽奖;2/4/6/8 人"),
    "治疗": FactionInfo("治疗", "support", (2, 4, 6), "治疗强度+小队生命/伤害;2/4/6 人"),
    "护盾": FactionInfo("护盾", "support", (2, 4), "护盾强度+伤害增幅+特殊护盾;2/4 人"),
    "欢愉": FactionInfo("欢愉", "support", (3, 4, 5, 7), "幸运一击+召唤阿哈(穿装备强化);3/4/5/7 人(V4.2 核心)"),

    # ===== 独立羁绊(6,单角色专属,1 层;eval 权重低,非买牌目标)=====
    "挚爱之人": FactionInfo("挚爱之人", "independent", (1,), "昔涟专属:诗篇刷新商店"),
    "魔术师": FactionInfo("魔术师", "independent", (1,), "Archer 专属:投影临时装备"),
    "大守护者": FactionInfo("大守护者", "independent", (1,), "布洛妮娅专属:召唤可可利亚"),
    "命运卜者": FactionInfo("命运卜者", "independent", (1,), "黑天鹅专属:占卜屋启示卡"),
    "救世主": FactionInfo("救世主", "independent", (1,), "白厄专属:获所有前台非独立羁绊效果"),
    "头号玩家": FactionInfo("头号玩家", "independent", (1,), "银狼LV.999 专属:升费/骇客改件"),
    "领航员": FactionInfo("领航员", "independent", (1,), "姬子·启行专属(V4.4):选列车同行角色获其流派+复制首件装备"),
}

# 从 character_const 映射:角色命途 → 大致定位(前排生存 / 后排输出)
# 货币战争「站位」(前台/后台/前后台)是独立系统,与命途不完全绑定,但命途决定角色赋能触发位。
SURVIVAL_PATHS = {"preservation", "abundance"}  # 存护、丰饶 → 前排坦克
DPS_PATHS = {"destruction", "hunt", "erudition"}  # 毁灭、巡猎、智识 → 后排输出
SUPPORT_PATHS = {"harmony", "nihility"}  # 同谐、虚无 → 后排辅助


def get_role_position(character_id: str) -> str:
    """根据角色 id 返回定位("front"=前排坦克 / "back"=后排输出/辅助)。

    用 character_const 的命途映射:存护/丰饶=front,其余=back。
    ⚠️ 货币战争实际站位以实机 OCR(角色页/商店牌的「前台/后台」标签)为准,命途只是近似。
    """
    from sr_od.config import character_const
    char = character_const.get_character_by_id(character_id)
    if char is None:
        return "back"
    return "front" if char.path.id in SURVIVAL_PATHS else "back"


# 货币战争推荐策略(米游社/攻略总结):
# 1. 前期(1-4 轮):凑低费成型羁绊(贝洛伯格 2 / 巡海游侠 / 仙舟起步),买低费快速成型。
# 2. 中期(5-7 轮):升等级(6-7 级),找高费补强,存金吃利息(gold ≥ 50)。
# 3. 后期(8-9 轮):升 8-9 级,凑齐高阶羁绊(盛会之星 5/6、击破 8/10、仙舟 7/10),锁血。
# 经济:每 10 金 → +1 利息(上限 5 金/50 金);连胜额外金币;凑整吃息。
INTEREST_THRESHOLD = 50  # 存金吃利息阈值(满息 50 金)
INTEREST_RATE = 0.1  # 每轮利息 = 持有金 × 10%(满 50 金 = 5 金/轮)
LEVEL_UP_GOLD_COST = {7: 36, 8: 48, 9: 70}  # 升级到 N 级大致金币(粗估,实机校准)
