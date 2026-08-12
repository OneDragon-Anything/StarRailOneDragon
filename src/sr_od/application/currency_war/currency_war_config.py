# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争配置。

策略层字段(faction/character/event 优先级等)= **meta 层,版本依赖**:游戏更新会改
阵营/角色/事件,最新数据**以米游社百科或游戏内图鉴为准**,本文件默认值仅是
2026-08 调研(`.debug/temp/currency_war/strategy_research.md`)的起步值,需随版本维护。
bot 运行时**以实机 OCR(左面板激活数、商店角色名)为真值**,本配置只做"偏好/tiebreaker"。
"""
from __future__ import annotations

from one_dragon.base.config.yaml_config import YamlConfig

# —— meta 默认值(2026-08 调研;版本更新后以米游社百科/游戏图鉴校准)——

# 成型快+稳的战力型阵营靠前(研究粗排:贝洛伯格/仙舟/盛会之星 > 巡海游侠/群攻 > 追击/狼狩)
DEFAULT_FACTION_PRIORITY: list[str] = [
    "贝洛伯格", "仙舟", "盛会之星", "昼之半神", "巡海游侠", "群攻", "追击", "狼狩",
]

# 万用核心角色(出现就抓,不限流派);费用据米游社 V4.4 权威(docs/game/currency_war/data/characters.md)
DEFAULT_CHARACTER_PRIORITY: list[str] = [
    # 5 费拼图(后期找)
    "昔涟", "云璃", "流萤",  # 流萤=5费(星核猎手/击破主 C)
    # 3-4 费核心辅助/主 C
    "星期日", "知更鸟", "白厄", "姬子·启行",  # 姬子·启行=3费(V4.4 列车同行核心)
    # 1-2 费前期基石(易升 3 星、成型快)
    "阿格莱雅", "藿藿", "桑博", "艾丝妲", "风堇", "卡芙卡",  # 藿藿=1费 / 卡芙卡=2费 / 风堇=2费
]

# 事件选项名 → 优先级分(越高越优先选,decide_event 子串匹配)。投资环境 + 投资策略 按名字打分。
# (review r1 修正:删"贝洛伯格星徽/追击星徽"——那是装备/环境奖励非投资策略;"反利+"→"返利+";
#  "模範的力量"→"榜样的力量";补棱彩 T0)
DEFAULT_EVENT_WHITELIST: dict[str, int] = {
    # —— 投资环境 T0(开局 3 选 1)——
    "昼之半神概念股": 100, "能量概念股": 100, "命运礼物": 95,
    "贝洛伯格邀请": 90, "追击邀请": 90, "战技点契约": 85, "击破概念股": 85,
    # —— 投资策略 T0(局内 3 选 1)——
    "高效决策": 93, "价值投资·彩": 92, "采购专员·彩": 92, "返利+": 90, "采购专员·金": 88,  # 凹上限后期
    # 注:「砂里淘金」(电表倒转核心,买-合-卖循环无限金)是已知场景,但**难操作+耗时,非推荐 bot 玩法**
    #     (用户 2026-08-03);不入白名单(不主动追),作"无限刷场景存在"的知识留在 economy_research.md。
    "定期福利": 90, "定点爆破": 90, "加油站": 88, "数值碾压": 88, "攻防一体": 88,
    "价值投资·金": 85, "装备方案A": 85, "榜样的力量": 85, "羁绊的力量": 87, "基本保障": 86,
    "战术义眼": 85, "武装突入": 82, "鲜血阶梯": 84, "野蛮成长": 83, "军备供应链": 80,
    "开源节流": 78, "黄金投资": 78,
    "中产阶级": 82, "黄金垃圾": 80, "难度修改器": 72,
}

# 枚举合法值(构造时校验,typo/大小写错静默落入默认)
ALLOWED_ECONOMY: set[str] = {"interest_first", "rush_level", "adaptive"}

# boss 克制 = comp-vs-boss 机制级(comp.countered_by_bosses + boss_fit + task#73 机制建模),
# 非阵营级 —— 原 DEFAULT_BOSS_COUNTER(boss→降权阵营)错模型已删(decide_boss_priority 删时一并清)。

# 克制 DoT/减益 的投资环境(遇此环境不走 DoT 路线)
DEFAULT_DOT_PUNISH_ENVS: list[str] = ["净化身心"]

# 难度 → 保血阈值覆盖(A1..A8;effective_hp_threshold 用)。
# **保守起步,待实机校准**:A1-A4 = 40(= HP_DANGER,低难不变,可适当卖血保经济);
# A5+ 升阶(高难敌人更凶 → 更早弃息保血)。detection(state.selected_difficulty)接线后生效;
DEFAULT_DIFFICULTY_HP: dict[str, int] = {
    "A1": 40, "A2": 40, "A3": 40, "A4": 40,
    "A5": 45, "A6": 50, "A7": 52, "A8": 55,
}


class CurrencyWarConfig(YamlConfig):
    """货币战争配置(入口流程 + 策略偏好)。

    策略字段都是 meta 层(版本依赖),默认值见模块顶部常量;用户可在 GUI 改,
    或版本更新后以米游社百科/游戏图鉴校准。bot 决策以实机 OCR 为主、本配置为偏好。
    """

    def __init__(self, instance_idx: int | None = None):
        YamlConfig.__init__(self, 'currency_war', instance_idx=instance_idx)
        # —— 入口/匹配(预留)——
        # —— 策略偏好(meta,版本依赖)——
        self.faction_priority: list[str] = self.get('faction_priority', DEFAULT_FACTION_PRIORITY)
        self.character_priority: list[str] = self.get('character_priority', DEFAULT_CHARACTER_PRIORITY)
        # 用户 4 轴 steer(README §A):forbid 硬过滤 + build_around 必含(cw_comps._passes_steering 读)。
        # 默认空 = 纯自适应。GUI setting card 待加(当前 yml 可改)。
        self.character_forbid: list[str] = self.get('character_forbid', [])
        self.character_build_around: list[str] = self.get('character_build_around', [])
        self.faction_forbid: list[str] = self.get('faction_forbid', [])
        # 枚举校验(review r1 #10):typo/大小写错静默落入默认,避免用户以为改了实则没生效
        econ = self.get('economy_mode', 'adaptive')
        self.economy_mode: str = econ if econ in ALLOWED_ECONOMY else 'adaptive'
        self.event_whitelist: dict = self.get('event_whitelist', DEFAULT_EVENT_WHITELIST)
        self.dot_punish_envs: list[str] = self.get('dot_punish_envs', DEFAULT_DOT_PUNISH_ENVS)
        # 可控轮数(单/多轮验证 + 采样本):跑完 N 轮停备战屏。None=跑到对局结束(现行,向后兼容)。
        # app._run_loop 透传给 CurrencyWarRunLoop。run_standalone_app 设此 yml 即跑 N 轮。
        _mr = self.get('max_rounds', None)
        self.max_rounds: int | None = int(_mr) if _mr not in (None, '', 0) else None
        # hp 保血阈值(02 §A3 单一源;A8 高难调高)。默认 40 = cw_decisions.HP_DANGER;_phase_weights /
        self.hp_safe_threshold: int = self.get('hp_safe_threshold', 40)
        # 默认 DEFAULT_DIFFICULTY_HP(A1-A4=40 不变、A5+ 升阶);空/未检测 → 回退 hp_safe_threshold。
        self.difficulty_hp_override: dict = self.get('difficulty_hp_override', DEFAULT_DIFFICULTY_HP)
        # 发现的任意 id);strategy_seed = 策略内部 rng 种子(None=真随机、固定 int=A/B 复现调试)。
        # ⚠️ 只种子化策略内部蒙特卡洛 D 牌随机;游戏侧行局演化(发牌/boss/掉血)服务端决定,种子化不到。
        self.strategy_id: str = self.get('strategy_id', 'default')
        self.strategy_seed: int | None = self.get('strategy_seed', None)

    def save(self) -> None:
        """持久化策略字段。"""
        self.data = {
            'faction_priority': self.faction_priority,
            'character_priority': self.character_priority,
            'character_forbid': self.character_forbid,
            'character_build_around': self.character_build_around,
            'faction_forbid': self.faction_forbid,
            'economy_mode': self.economy_mode,
            'event_whitelist': self.event_whitelist,
            'dot_punish_envs': self.dot_punish_envs,
            'hp_safe_threshold': self.hp_safe_threshold,
            'difficulty_hp_override': self.difficulty_hp_override,
            'strategy_id': self.strategy_id,
            'strategy_seed': self.strategy_seed,
        }
        YamlConfig.save(self)
