# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 阵容库 + 战略层评分(comp_score / select_comp;纯逻辑,可测,不碰游戏)。

战略层(阶段 2,A2):从「reactive 加深领先」升级到「围绕目标阵容 commit + 转型 + 巨星」。
auto-chess 胜负手 = commit 哪个阵容 + 何时转型 + 巨星绑谁;本模块给**可配置 + 自适应**的选目标机制。

数据与设计依据(详 ``docs/develop/currency_war/strategy/03_comp_planning.md`` +
``10_battle_and_enemies.md`` + ``docs/game/currency_war/data/comp_library.md``):
- ``COMP_LIBRARY``:起步 roster(~8 套,覆盖易/中/难成型 + 各机制,含 debuff=buff 的燃血)。
  依据 strategy_research §10(meta 横评)+ docs/game/currency_war/data/characters.md / factions.md(米游社 V4.4)。
- ``comp_score`` / ``select_comp``:按场面(gold/轮次/boss/已持牌/环境/词缀)多维打分选 target。

**核心原则(用户 2026-08-03,贯彻全程)**:
1. **一切 comp 相关** —— equip/mechanics 都挂钩目标阵容,无孤立评分(不设通用 equip_score/词缀表)。
   反重力皮靴对昼神阿雅(需 2 靴)是命脉、对别的 comp 不一定;正当防卫词缀对万敌燃血是利、对阿雅是克。
2. **debuff 可能是 buff** —— 同一词缀对不同阵容方向相反(mechanics_fit 双向:counter 降 + synergy 升)。
3. **COMP_LIBRARY 多维打分 + 运行时按场面选** —— 不锁死一套,按成型难度/boss/环境/词缀灵活选易成型又够强的。
4. **经济统一论** —— 每 comp 自带 ``level_plan``(成型路线),驱动战术层花超额金(接法见 cw_decisions,待接)。

⚠️ meta(版本依赖):core_chars/form_tiers/strength/form_difficulty 是 V4.4 起步估值,replay + 实玩迭代。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_investments import INVESTMENT_ENVS
from sr_od.application.currency_war.cw_shop_odds import acquirability_factor
from sr_od.application.currency_war.cw_state import GameState, effective_hp_threshold

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_performance import PerformanceTracker


def clamp(x: float, lo: float, hi: float) -> float:
    """限幅(lo..hi)。"""
    return lo if x < lo else (hi if x > hi else x)


# ===== 数据结构 =====

@dataclass
class LevelGoal:
    """某玩家等级该做什么(成型路线的一站;经济统一论驱动战术花超额金)。

    曲线随 COMP_LIBRARY 填(用户选 B:框架先定,曲线建库时填)。
    """
    action: str            # "level_up"(攒金升下一级,解锁更高费刷新率)/ "roll"(D 找核心)/ "stable"(稳住吃息)
    target_cost: int = 0   # roll 时重点找几费核心(0=不限;随等级升:前期1费/中期4费/后期5费)
    target_chars: list[str] = field(default_factory=list)   # 这级该找谁(core_chars 子集)
    star_goals: dict[str, int] = field(default_factory=dict)  # 角色名 → 目标星级(如 1费→3星、5费→2星)


@dataclass
class Comp:
    """一套目标阵容(meta 数据,V4.4 起步估值待实玩校准)。"""
    name: str                    # "追击飞霄"/"昼神阿雅"/"万敌单C"(roster 见 docs/game/currency_war/data/comp_library.md)
    factions: list[str]          # 核心阵营组合 ["追击"](查 FACTIONS)
    core_chars: list[str]        # 核心角色(名)["飞霄","知更鸟"]
    form_tiers: dict[str, int]   # 成型 tier 目标 {"仙舟":5,"追击":3}(几人激活算成型)
    strength: str                # "S"/"A"/"B" 综合强度(版本强度;2026-08-03:不标"邪道" —— 邪道非必需)
    form_difficulty: str         # "easy"/"medium"/"hard" 成型难度(用户:关键维度)
    early_power: str = "中"
    level_plan: dict[int, LevelGoal] = field(default_factory=dict)  # 成型路线(玩家等级→该做什么);建库时填
    key_equips: list[str] = field(default_factory=list)      # 关键装备(可含重复,如阿雅需 2 反重力皮靴)
    countered_by_bosses: list[str] = field(default_factory=list)   # 克这阵容的 boss 名(boss_fit 用)
    mechanic_attributes: list[str] = field(default_factory=list)  # comp 机械属性 tag(mechanics_fit 经 MECHANIC 表判)
    shared_chars: list[str] = field(default_factory=list)    # 与其他 comp 共享的 core(转型可复用)
    transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)
    typical_form_round: int = 0  # 大致成型所需轮次(level_plan 粗估汇总)
    version_tag: str = "V4.4"    # 版本维护用


@dataclass
class ScoreContext:
    """select_comp / comp_score 的每回合上下文(避免长参数列表)。"""
    bosses: list[str] = field(default_factory=list)              # 当前/将遇 boss 名(boss_fit)
    mechanics: set[str] = field(default_factory=set)             # 激活机制 tag(current_enemy_mechanics)
    env: str = ""                                                # 已选投资环境名(env_fit)
    held_strategies: list[str] = field(default_factory=list)      # 已持有投资策略(ADR-0135 held_strategy_fit;机会型 pivot)
    plane: int = 1
    round_num: int = 1
    gold: int = 0
# 来源:docs/game/currency_war/data/competitors.md(V4.4 ~50 敌人词缀全集,米游社玩家攻略统计 🟡)+ factions.md(燃血角斗场原文)。
# 机制名跨版本稳;具体词缀属哪个机制随版本变(随 competitors.md 实机 OCR 更新)。
# 只建模"对某类 comp 方向相反"的词缀(策略相关);纯数值怪强化(首领强化等)无 comp 交互,不入表。

MECHANIC_COUNTERS: dict[str, list[str]] = {
    # 机制 tag → 它克制的 comp 机械属性
    "反伤": ["高频低单次"],        # 正当防卫:克高频低单次(反甲白厄式)
    "冻结": ["慢速", "战技点依赖"],  # 极速制冷/坠入陷阱/冷冻冬眠:克慢速 + 战技点消耗队
    "净化": ["DoT", "减益"],       # 净化身心:克 DoT/减益主派(config dot_punish_envs)
    "掉血削上限": ["燃血"],        # 永久创伤:克燃血(掉血→减上限双损)⚠️ 燃血的反例 counter
    "治疗削弱": ["治疗护盾"],      # 重症难题:克治疗/护盾主坦队
    "幸运削弱": ["幸运一击"],      # 丢失幸运:克幸运一击/群攻(知更鸟)
    "属性熄火": ["单属性队"],      # 风/火/冰/雷/物理/量子/虚数熄火:克纯色/单属性队
    "速度抑制": ["速度依赖"],      # 忽快忽慢:克极端高速(昼神阿雅鞋队)
    "装备依赖": ["依赖合成装备"],  # 变宝为废:克依赖合成的装备流
    "榜样激励": ["高倍率单核"],   # 榜样激励:伤害第一的 75%(其他 110%)→ 克单核(命运圣杯红A 高倍率单核)
    "多段惩罚": ["高频低单次"],   # 忍无可忍:敌受 7 次攻击后提前 100% → 克高频低单次(反甲白厄多段打→频触→敌频动)
    "行动延后": ["速度依赖"],     # 沉重脚步:受击我方行动延后 8% → 克速度依赖(鞋队/速度 tuning 被打乱)
}
MECHANIC_SYNERGIES: dict[str, list[str]] = {
    # 机制 tag → 它受利的 comp 机械属性(用户:debuff=buff)
    "反伤": ["燃血"],             # 正当防卫:反伤让燃血掉血 → 角斗场记录 → 伤害更高(万敌例,debuff=buff 典型)
    "爆发机会": ["爆发速杀"],     # 紧急止血:敌进战受 20% 上限伤 → 利爆发速杀
    "高费审美": ["高费队"],       # 高费审美:4 费及以上 +5%(V4.4)
    "低费审美": ["低费队"],       # 低费审美:3 费及以下 +5%(V4.4)
    "成型羁绊利好": ["成型羁绊队"],  # 形单影只:羁绊全则不受罚(V4.4)
    "皮糙肉厚": ["击破"],          # 皮糙肉厚:未被击破受伤-30% → 利击破 comp(击破流萤 不受罚)
}

# 敌人词缀(OCR 原名)→ 机制 tag 映射(V4.4 competitors.md;未知词缀原样当 tag 透传)
AFFIX_MECHANIC_MAP: dict[str, str] = {
    "正当防卫": "反伤", "反伤": "反伤",
    "极速制冷": "冻结", "急速制冷": "冻结",   # 急速制冷=旧称/笔误变体,兼容
    "坠入陷阱": "冻结", "冷冻冬眠": "冻结",
    "净化身心": "净化",
    "永久创伤": "掉血削上限",
    "重症难题": "治疗削弱",
    "丢失幸运": "幸运削弱",
    "忽快忽慢": "速度抑制",
    "变宝为废": "装备依赖",
    "紧急止血": "爆发机会",
    "高费审美": "高费审美", "低费审美": "低费审美",
    "形单影只": "成型羁绊利好",
    # 属性熄火(7):对应属性我方伤害 1 点(4 次后解除),克纯色队
    "风之熄火": "属性熄火", "火之熄火": "属性熄火", "冰之熄火": "属性熄火",
    "雷之熄火": "属性熄火", "物理熄火": "属性熄火", "量子熄火": "属性熄火", "虚数熄火": "属性熄火",
    "皮糙肉厚": "皮糙肉厚",   # 利击破 comp(未被击破受伤-30% → 击破流不受罚)
    "榜样激励": "榜样激励",   # 克单核(伤害第一的 75%)
    "忍无可忍": "多段惩罚",   # 敌受 7 次攻击提前 100% → 克高频低单次(反甲白厄)
    "沉重脚步": "行动延后",   # 受击行动延后 8% → 克速度依赖
    # 其余词缀(首领强化/复仇心切/倒计时类/灼热轰炸等)为纯数值/无 comp 交互(灼热轰炸:前排受击+DoT
    # 均匀影响,无 comp flip),不入表;实机 OCR 按需补
}

# AFFIX_EFFECTS(词缀→游戏原文效果)见 affix_effects_data.py(单独文件;运行时 write_affix_effects
# 自动写入采到的新词缀/校准)。本文件顶部 import 重导出 → 下游用 cw_comps.AFFIX_EFFECTS 不变。
# comp.countered_by_bosses 俗称→规范公司名对齐是 task#73 剩余,boss_fit 暂永不命中,待实机核对)。

# ===== 环境 → 阵营/comp 亲和(P1-2 T0 env 近乎硬绑 + R2-9 env→faction)=====
# ENV_FACTION_MAP 从投资环境注册表派生(单一真相源:概念股/邀请的 faction 字段;改注册表自动传导)
ENV_FACTION_MAP: dict[str, list[str]] = {
    name: [e.faction] for name, e in INVESTMENT_ENVS.items() if e.faction
}
ENV_COMP_AFFINITY: dict[str, dict[str, float]] = {
    # T0 env → {comp_name: 亲和权重} —— 拿到应近乎硬绑该 comp(research §10.3:env 是 run 内最大单一决策)
    "昼之半神概念股": {"昼神阿雅": 1.0},   # 送阿雅+鞋+刷新率 → 近乎硬绑昼神
    # 其余 T0 env 待实玩补
}


# ===== COMP_LIBRARY(起步 roster;V4.4 估值,待实玩校准)=====
# 详 docs/game/currency_war/data/comp_library.md。form_tiers 用 FACTIONS tier 设"成型"里程碑;data 待实玩精确。

COMP_LIBRARY: list[Comp] = [
    # ===== S 级(版本真神,V4.4 合集 76807134)=====
    Comp(
        # playbook:docs/develop/currency_war/playbook/列车同行.md(改此条目须同步)
        name="列车同行", factions=["列车同行"], core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        form_tiers={"列车同行": 4}, strength="S", form_difficulty="easy", early_power="高",
        # V4.4 权威评级(76807134):姬子·启行 = S 级真神;A850 挂机流(76824096):全程自动/不凹开局/适应任何负面环境 → bot 默认首选
        # 成型 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝
        key_equips=["冷笑话引擎", "火力风暴潮", "高周波电锯", "掩体生成枪"],   # 输出装(非反甲;攻略明言"不需要刷反甲")
        countered_by_bosses=[], mechanic_attributes=["治疗护盾"],
        shared_chars=["三月七", "花火", "瓦尔特"], transition_chars=["三月七", "符玄", "艾丝妲"],
        typical_form_round=5,
        level_plan={
            3: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七"], star_goals={"三月七": 2}),
            4: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "花火"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"),
            # ADR-0128(攻略复查 #8,阵容_列车同行:53):**停留 7 级猛 D 3星姬子**(3费 7 级概率
            # 峰值 p=0.40)—— 旧 7=level_up 直冲 8 违背「核心概率级停留」人玩节奏。
            7: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七", "花火"],
                         star_goals={"姬子·启行": 3}),
            8: LevelGoal("roll", target_cost=0, target_chars=["姬子·启行", "花火", "瓦尔特"],
                         star_goals={"姬子·启行": 3, "花火": 2}),
        },
    ),
    Comp(
        name="命运圣杯红A", factions=["命运圣杯"], core_chars=["Archer", "远坂凛"],
        form_tiers={"命运圣杯": 3}, strength="S", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):Archer 95 = S 级真神;攻略(76924524):高倍率九五核心+远坂凛+圣杯→+150%攻击+战技点
        # ⚠️ core_chars 用图鉴规范名:"Archer" 非"红A"(OCR/char_id 匹配靠 characters.md)
        key_equips=["高周波电锯", "高周波电锯", "火力风暴潮"],
        mechanic_attributes=["高倍率单核"],   # 榜样激励克高倍率单核(test_mechanics_fit_honga)
        shared_chars=["远坂凛", "瓦尔特"], transition_chars=["符玄", "知更鸟", "花火"],
        typical_form_round=6,
        level_plan={  # 4 个 5 费成型难:前期低费过渡保血 → 升 8-9 找 5 费
            4: LevelGoal("roll", target_cost=2, target_chars=["远坂凛"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=5, target_chars=["Archer", "远坂凛"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["Archer"], star_goals={"Archer": 2}),
        },
    ),
    # ===== A 级(版本强势,V4.4 合集 76807134)=====
    Comp(
        name="绯英欢愉", factions=["欢愉", "能量"], core_chars=["绯英", "瓦尔特", "爻光"],
        form_tiers={"欢愉": 3, "能量": 3}, strength="A", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):绯英 = A 级;攻略(76806732):绯英大招永久+2%伤害(无限成长),3欢愉+3能量+2量子+2减益
        # 前期狼尊开 3 欢愉过渡 → 上 8 踢狼尊换主角 → 上 9 找杨叔(瓦尔特)大成。爻光穿鞋频召阿哈叠层
        key_equips=["火力风暴潮", "永动机", "冷笑话引擎", "反重力皮靴"],
        mechanic_attributes=["欢愉叠层"], shared_chars=["瓦尔特", "爻光", "花火"],
        transition_chars=["银狼LV.999", "爻光", "花火"], typical_form_round=6,
        level_plan={  # 低费欢愉:前期 roll 欢愉 → 升 8-9 找杨叔
            4: LevelGoal("roll", target_cost=1, target_chars=["绯英", "爻光"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["绯英"], star_goals={"绯英": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特"]),
        },
    ),
    Comp(
        name="希儿量子", factions=["量子同频", "贝洛伯格"], core_chars=["希儿", "瓦尔特", "知更鸟", "布洛妮娅"],
        form_tiers={"量子同频": 4, "贝洛伯格": 2}, strength="A", form_difficulty="medium", early_power="高",
        # V4.4 评级(76807134):希儿 = A 级(A8-50 最强轮椅);攻略(76802749 直读纠正):4量子+贝城(2贝=原4贝,引擎拉条)
        # 斩杀+70%下二战技+再现+造物引擎。希儿(双电锯+风暴潮)+杨叔(瓦尔特)+记忆主+鸟(知更鸟)+刻律+鸭鸭(布洛妮娅)+符玄
        # 前期强势(希儿无装也能换怪/胜)→ 强烈推荐希儿过渡;7级找希儿3星或先上8/9找4-5费同时找希儿
        key_equips=["高周波电锯", "高周波电锯", "火力风暴潮"],
        countered_by_bosses=["剧目", "蕉研组"],   # 攻略:剧目/蕉研组 boss 希儿难度大
        mechanic_attributes=["量子拉条"], shared_chars=["知更鸟", "布洛妮娅", "瓦尔特"],
        transition_chars=["希儿", "刃", "符玄"], typical_form_round=6,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["希儿"]),
            6: LevelGoal("roll", target_cost=2, target_chars=["希儿"], star_goals={"希儿": 2}),
            7: LevelGoal("roll", target_cost=2, target_chars=["希儿"], star_goals={"希儿": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "知更鸟"]),
        },
    ),
    Comp(
        name="黄泉减益", factions=["巡海游侠", "减益"], core_chars=["黄泉", "不死途", "乱破", "刃"],
        form_tiers={"巡海游侠": 3, "减益": 4}, strength="A", form_difficulty="medium", early_power="低",
        # V4.4 评级(76807134):黄泉 = A 级;攻略(76826405):3游侠+4减益+3量子,2星乱破+3星不死途→280%增幅
        # V4.4 加刃提升残梦效率。前期 4 减益降敌伤过渡 → 7 级 d 找黄泉+不死途 → 上 9 补符玄杨叔
        # ⚠️ 与 DOT队(卡芙卡持续伤害)不同,黄泉是减益/巡海游侠主派,独立
        key_equips=["火力风暴潮", "冷笑话引擎"],
        countered_by_bosses=["单体boss"],   # 攻略:单体 boss 黄泉输出乏力
        mechanic_attributes=["减益"], shared_chars=["刃", "乱破", "符玄"],
        transition_chars=["刃", "椒丘", "桑博"], typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["乱破", "不死途"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=3, target_chars=["黄泉", "不死途"]),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["黄泉"], star_goals={"黄泉": 2, "不死途": 2}),
        },
    ),
    Comp(
        name="击破流萤", factions=["击破", "巡海游侠"], core_chars=["流萤", "波提欧"],
        form_tiers={"击破": 6, "巡海游侠": 4}, strength="A", form_difficulty="hard", early_power="中",
        # V4.4 评级(76807134):击破(波提欧)= A 级(V4.4 加强);攻略(76852576 直读):6击破+4游侠(全两星+波提欧前台=300%增幅)
        mechanic_attributes=["击破"], shared_chars=["波提欧"],
        transition_chars=["波提欧", "符玄", "艾丝妲"], typical_form_round=7,
        level_plan={  # 后期 6 击破:前期过渡 → 升 8-9 凑击破
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=4, target_chars=["流萤", "波提欧"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["流萤"], star_goals={"流萤": 2}),
        },
    ),
    Comp(
        name="龙丹战技点", factions=["战技点", "列车同行"], core_chars=["丹恒·饮月", "远坂凛", "瓦尔特", "花火"],
        form_tiers={"战技点": 4, "列车同行": 4}, strength="A", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):丹恒·饮月(龙丹)= A 级;攻略(76987716 直读纠正):4战技点+4列车(周日开)
        # 凛(远坂凛)V4.4 新:宝石叠99层→第二魔法实验拐198%爆伤(+默认70%=268%);饮月双电锯+风暴潮
        # 杨叔(瓦尔特)+记忆主必备;4列车给160%前台强度;刃+符玄补。苍龙濯世破百亿
        key_equips=["高周波电锯", "高周波电锯", "火力风暴潮"], mechanic_attributes=["战技点依赖"],
        shared_chars=["远坂凛", "瓦尔特", "花火"], transition_chars=["花火", "风堇", "姬子·启行"],
        typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
    ),
    Comp(
        name="双王圣杯", factions=["命运圣杯", "能量"], core_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄"],
        form_tiers={"命运圣杯": 3, "能量": 5}, strength="A", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):双王 = A 级;攻略(76985789 直读纠正调研误认):双王=闪闪(吉尔伽美什)+Saber(Fate圣杯联动),
        # 非大黑塔+景元(游侠源误)。闪闪+Saber 每8行动连携+回能;圣杯羁绊给经济+改件加速3星。
        # Saber主c(风暴潮+冷笑话+永动机)/闪闪后台带鞋自加速;5能量;杨叔必备;刃+缇宝+符玄(阿瓦隆+绝对热量邪修75%减伤)
        # 过渡:体系牌+花火/凛(做3圣杯任务);7-8级找3星Saber或闪闪→上9挂杨叔
        key_equips=["火力风暴潮", "冷笑话引擎", "永动机", "反重力皮靴"],
        mechanic_attributes=["连携高频开大"], shared_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄"],
        transition_chars=["花火", "远坂凛", "刃"], typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=4, target_chars=["Saber"], star_goals={"Saber": 2}),
            8: LevelGoal("roll", target_cost=4, target_chars=["吉尔伽美什", "Saber"], star_goals={"Saber": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
    ),
    Comp(
        # playbook:docs/develop/currency_war/playbook/火花星间旅人.md(改此条目须同步)
        # V4.0 A级(BV1vVcLzXEN8 2026-02 转录):花火主C(吃点巧普攻+幻语记,倍率随花火等级)+星间旅人
        # 羁绊(唯一有效应=旅人转职,1转职章=43.2%幸运暴伤);6战技点不提升 → 带银狼/符玄凑3量子;
        # 前期龙丹战技点护航;上8大D找2星花火,3星质变;爻光三鞋(跑条供R回合)。
        # 怕正当防卫;极速制冷不怕(R时刻解控)。好运令牌给阿雅(装备最顶级)勿给花火/爻光。
        name="火花星间旅人", factions=["星间旅人", "量子同频"],
        core_chars=["花火", "爻光", "开拓者·记忆", "银狼"],
        form_tiers={"星间旅人": 4, "量子同频": 3}, strength="A", form_difficulty="medium",
        early_power="高",
        key_equips=["火力风暴潮", "高周波电锯", "反重力皮靴"],   # 花火1风暴潮+暴击刀;爻光三鞋
        countered_by_bosses=[], mechanic_attributes=["幸运一击"],
        shared_chars=["银狼", "符玄", "丹恒·饮月"], transition_chars=["丹恒·饮月", "银枝"],
        typical_form_round=7,
        level_plan={   # 前期龙丹护航 → 上8大D 2星花火 → 有机会追3必试(质变)
            5: LevelGoal("roll", target_cost=2, target_chars=["丹恒·饮月"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=4, target_chars=["花火"], star_goals={"花火": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["花火", "开拓者·记忆"], star_goals={"花火": 3}),
        },
    ),
    Comp(
        name="银枝群攻", factions=["贝洛伯格", "群攻"], core_chars=["银枝", "翡翠", "知更鸟"],
        form_tiers={"贝洛伯格": 4, "群攻": 3}, strength="B", form_difficulty="medium", early_power="低",
        # V4.4 评级(76807134):银枝 = B 级;攻略(77006068 直读纠正):V4.4 离能量,"轮椅通拐"(杨叔/主角/缇宝/花火/千冶刃+符玄)抬
        # 银枝(风暴潮+冷笑话)+翡翠(3群攻)+鸟(拉条加攻增伤+10%幸运);必须3星银枝;适合对群,对单大降
        # ⚠️ 旧"贝洛伯格召唤"(布洛妮娅 core)误:布洛妮娅是通用辅助非 comp lead;V4.4 贝洛伯格代表=银枝
        key_equips=["火力风暴潮", "冷笑话引擎", "绝对热量"], mechanic_attributes=["群攻"],
        countered_by_bosses=["单体长战"], shared_chars=["翡翠", "知更鸟"],
        transition_chars=["椒丘", "星期日", "刃"], typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["银枝"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["翡翠", "知更鸟"]),
        },
    ),
    Comp(
        name="反甲白厄", factions=[], core_chars=["白厄"],
        form_tiers={}, strength="A", form_difficulty="hard", early_power="低",
        # 白厄无阵营(cw_chars:104 factions=""),独立羁绊「救世主」(获所有前台非独立羁绊效果)。
        # 反甲流靠白厄单核 + 以牙还牙甲×3 受击反伤,**不靠阵营羁绊成型** → factions/form_tiers 空。
        # (原 ["毁灭"]/{"毁灭":4} 错:毁灭是命途(destruction)非阵营,form_progress 恒 0 → 死 comp 污染候选池。)
        # comp 靠 core_char(白厄)+ equip_fit(以牙还牙甲)+ mechanics(高频低单次 反伤);
        # form_progress 恒 0 → 不靠 form commit(轮数兜底要求 fp>0,fp=0 不触发),select_comp 候选但 progress 低。
        key_equips=["以牙还牙甲", "以牙还牙甲", "以牙还牙甲"],   # meta:反甲流需 3 以牙还牙甲
        countered_by_bosses=["红绿灯", "酒杯怪", "琥珀王", "死龙"],
        mechanic_attributes=["高频低单次"], shared_chars=["白厄"],
        transition_chars=["白厄", "符玄", "三月七"], typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["白厄"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["白厄"], star_goals={"白厄": 2}),
        },
    ),
    # ===== B 级(强度一般,V4.4 合集 76807134)=====
    Comp(
        name="狼尊欢愉", factions=["星核猎手", "欢愉"], core_chars=["银狼LV.999", "爻光", "刃"],
        form_tiers={"欢愉": 5, "星核猎手": 2}, strength="B", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):狼尊 = B 级;攻略(76832783 直读):5欢愉(最大利用阿哈装备),狼尊双风暴潮+爻光双鞋
        # 刃(星核猎手):刃+狼尊行动7次→狼尊释放欢愉技。强依赖鞋≥6;尽量不d全力升级;也作绯英早期过渡c
        key_equips=[], mechanic_attributes=["欢愉叠层"],
        shared_chars=["爻光", "花火"], transition_chars=["爻光", "花火", "符玄"], typical_form_round=5,
        level_plan={
            4: LevelGoal("roll", target_cost=2, target_chars=["银狼LV.999", "爻光"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["银狼LV.999"], star_goals={"银狼LV.999": 2}),
        },
    ),
    Comp(
        name="昼神阿雅", factions=["昼之半神"], core_chars=["阿格莱雅", "风堇", "昔涟"],
        form_tiers={"昼之半神": 4}, strength="B", form_difficulty="hard", early_power="低",
        # V4.4 评级(76807134):阿雅 = B 级(试用难玩;需反重力皮靴×2+速度投资,V3.8 最轮椅→V4.4 降 B)
        key_equips=["反重力皮靴", "反重力皮靴"],
        countered_by_bosses=["电视机"], mechanic_attributes=["速度依赖"],
        shared_chars=["风堇", "昔涟"], transition_chars=["风堇", "艾丝妲", "阿格莱雅"], typical_form_round=8,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["阿格莱雅", "风堇"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["阿格莱雅"], star_goals={"阿格莱雅": 2}),
        },
    ),
    Comp(
        # playbook:docs/develop/currency_war/playbook/追击飞霄.md(改此条目须同步)
        name="追击飞霄", factions=["追击"], core_chars=["飞霄", "知更鸟", "缇宝", "不死途"],
        form_tiers={"追击": 3}, strength="B", form_difficulty="medium", early_power="低",
        # V4.4 合集(76807134)追击 B 级 = 飞霄-led(纯追击);攻略(76883466):飞霄天赋追击永久+6%增伤,≥3追击=300%倍率
        # 飞霄双风暴潮+鸟(3追击关键)+缇宝/不死途/刃;2星飞霄上9(3星锁血反降);追击转→5追击60%真伤
        key_equips=["火力风暴潮", "火力风暴潮", "永动机"], mechanic_attributes=["追击"],
        shared_chars=["知更鸟", "缇宝", "不死途"], transition_chars=["赛飞儿", "风堇", "刃"],
        typical_form_round=7,
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["飞霄"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["知更鸟", "不死途"]),
        },
    ),
    Comp(
        name="万敌单C", factions=["夜之半神", "燃血"], core_chars=["万敌", "长夜月"],
        form_tiers={"夜之半神": 4, "燃血": 4}, strength="B", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):万敌 = B 级;【debuff=buff 典型】反伤/AoE/持续伤害 利燃血;攻略(77056698)
        mechanic_attributes=["燃血"],
        key_equips=["火力风暴潮", "绝对热量", "热血沸腾拳"],   # 攻略(77056698):万敌风暴潮+绝对热量+热血沸腾拳;吃装备
        countered_by_bosses=["永久创伤"],   # 掉血削上限克燃血(不可玩);利:忍无可忍/正当防卫/灼热轰炸(debuff=buff)
        shared_chars=["风堇", "长夜月"], transition_chars=["长夜月", "符玄", "风堇"], typical_form_round=6,
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["万敌", "长夜月"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["万敌"], star_goals={"万敌": 2}),
        },
    ),
    Comp(
        name="DOT队", factions=["持续伤害", "星核猎手"], core_chars=["卡芙卡", "黑天鹅", "刃", "桑博"],
        form_tiers={"持续伤害": 4, "星核猎手": 2}, strength="B", form_difficulty="easy", early_power="低",
        # V4.4 评级(76807134):dot = B 级;攻略(77026641 直读):V4.4 刃加入→卡芙卡回归(刃比普通狼频繁触星核猎手额外战技)
        # 卡芙卡3风暴潮(dot不吃幸运)+黑天鹅(鹅,2dot)+刃(2星核猎手)+刻律(复制战技连动)+鸟;需自己卡芙卡
        # ⚠️ 黄泉减益已拆独立(见上);本 comp=DoT 主派(卡芙卡/鹅/刃/桑博),P1强/P2乏力/P3需转,低费过渡保血权威
        key_equips=["火力风暴潮", "火力风暴潮", "火力风暴潮"], mechanic_attributes=["DoT"],
        shared_chars=["桑博", "刃", "黑天鹅"],
        transition_chars=["桑博", "卡芙卡", "艾丝妲"], typical_form_round=4,
        level_plan={  # 低费 DoT:P1 快速成型保血
            3: LevelGoal("roll", target_cost=1, target_chars=["桑博"]),
            4: LevelGoal("roll", target_cost=2, target_chars=["卡芙卡", "桑博"], star_goals={"桑博": 2}),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["卡芙卡"], star_goals={"卡芙卡": 2}),
        },
    ),
]


def get_comp(name: str) -> Comp | None:
    """按名取 Comp;无则 None。"""
    for c in COMP_LIBRARY:
        if c.name == name:
            return c
    return None


# ===== 评分 helper(comp 相关)=====

def _owned_chars(state: GameState) -> set[str]:
    """已持有的角色名集合(bench + deployed)。"""
    return {bc.char_id for bc in (*state.bench, *state.deployed) if bc.char_id}


def form_progress(comp: Comp, state: GameState) -> float:
    """成型度 0..1:各核心阵营 tier 进度的均值(min(board,form_tiers)/form_tiers)。

    10 的 helper(comp_viability 先验用);纯阵营 tier,不含角色(避免与 char_quality 三重计分)。
    """
    if not comp.form_tiers:
        return 0.0
    total = 0.0
    n = 0
    for f, tier in comp.form_tiers.items():
        if tier <= 0:
            continue
        total += min(state.board.get(f, 0), tier) / tier
        n += 1
    if n == 0:
        return 0.0
    return clamp(total / n, 0.0, 1.0)


def progress(comp: Comp, state: GameState) -> float:
    """comp_score 用:0.6 阵营 tier 进度 + 0.4 核心角色持有(归一化 0..1)。

    与 form_progress 区别:progress 加了 core_char 持有项(选 target 时评估契合用);
    eval 驱动买牌用 target_progress(只度量剩余进度,去三重,详 cw_decisions 待接)。
    """
    fp = form_progress(comp, state)
    owned = _owned_chars(state)
    core_frac = (sum(1 for c in comp.core_chars if c in owned) / len(comp.core_chars)) if comp.core_chars else 0.0
    return clamp(0.6 * fp + 0.4 * core_frac, 0.0, 1.0)


def shop_supply(comp: Comp, state: GameState) -> float:
    """comp 核心阵营的**本回合** shop 可得性 [0,1](shop-aware,task#25 + I14)。

    现仅用于 **drought bail 判定**(default_strategy:连续 N 回合 supply<1.0 → 弃不可达 target 重选),
    **不再驱动 select_comp**(ADR-0092:select_comp 改用理论 acquirability_factor,刷新独立 → 观察/单回合
    shop 无预测力)。保留本函数因 drought 需「本回合 shop 是否供得上核心」的实时观察。

    - 阵营在 **shop(本回合可买)** 出现 → **1.0**(本回合买得到核心牌 → drought 归 0)。
    - 仅 **board** 有、shop 无 → **0.3**(已持 1 张但本回合买不到更多 → 成型难,弱信号;非 1.0)。
    - 都无 → **0.0**(本回合刷不出 → 不可成型,累积 drought)。

    ⚠️ I14(2026-08-05):旧版 board 有 1 张就返 1.0 → 选了成型不了的 target(board 有但 shop 供不上)
    → 永不成型。改:shop presence 主导,board-only 降为弱信号(0.3)——「board 已有 1 张 ≠ 能成型,
    要 shop 供得上核心」。
    """
    if not comp.factions:
        return 1.0
    shop_factions = {c.faction for c in state.shop}
    # 核心阵营(form_tiers)优先:非核心阵营在 shop 不算「供得上核心」(否则 drought 误归 0,漏掉不可达 target)。
    core = set(comp.form_tiers.keys()) if comp.form_tiers else set(comp.factions)
    if any(f in shop_factions for f in core):
        return 1.0
    if any(f in shop_factions for f in comp.factions):
        return 0.5   # 仅非核心阵营在 shop → 半信号
    board_factions = set(state.board.keys())
    if any(f in board_factions for f in comp.factions):
        return 0.3   # 仅 board 有,shop 买不到更多 → 弱成型信号(I14)
    return 0.0


def equip_fit(comp: Comp, state: GameState) -> float | None:
    """装备契合度(comp 相关,0..1):持有 comp.key_equips 越多越高(超线性 ^0.7 奖励集齐)。

    ⚠️ comp 驱动(用户):不设通用 equip_score,一切从 target_comp.key_equips 出发。
    key_equips 可含重复(阿雅需 2 反重力皮靴)→ 按 multiplicity 匹配持有数。
    无装备数据(state.equips 空)/ comp 无关键装备 → **None**(ADR-0107 动态权重:无数据不进加权,
    权重重分配给有数据项,治死重常量地板)。
    """
    equips = list(getattr(state, 'equips', []) or [])
    if not comp.key_equips or not equips:
        return None
    remaining = list(equips)
    held = 0
    for ke in comp.key_equips:
        if ke in remaining:
            held += 1
            remaining.remove(ke)
    if held == 0:
        return 0.3   # 持有装备但无该 comp 关键件 → 略低(装备不契合)
    return clamp((held / len(comp.key_equips)) ** 0.7, 0.0, 1.0)


def mechanics_fit(comp: Comp, mechanics: set[str]) -> float | None:
    """机制契合(comp 相关,双向 0..1):命中 counter(克这 comp)→ 降;命中 synergy(利这 comp)→ 升。

    ⚠️ comp 驱动(用户 debuff=buff):同一词缀对不同 comp 方向相反。经 comp.mechanic_attributes
    查全局 MECHANIC_COUNTERS/SYNERGIES 判(数据驱动,comp 不必逐词缀列举)。
    无机制信息(无敌人词缀 / comp 无 mechanic_attributes)→ **None**(ADR-0107 动态权重剔除,治死重)。
    典型:万敌[燃血] + 反伤 → synergy 升(debuff=buff);阿雅[速度依赖] + 禁速 → counter 降。
    """
    if not mechanics or not comp.mechanic_attributes:
        return None
    score = 0.5
    for mech in mechanics:
        countered_attrs = MECHANIC_COUNTERS.get(mech, [])
        synergy_attrs = MECHANIC_SYNERGIES.get(mech, [])
        n_counter = sum(1 for a in comp.mechanic_attributes if a in countered_attrs)
        n_synergy = sum(1 for a in comp.mechanic_attributes if a in synergy_attrs)
        score -= 0.25 * n_counter    # 每命中一个 counter 降 0.25
        score += 0.20 * n_synergy    # 每命中一个 synergy 升 0.20(debuff=buff 利好)
    return clamp(score, 0.0, 1.0)


def boss_fit(comp: Comp, bosses: list[str]) -> float | None:
    """boss 克制(boss 名维度):命中 comp.countered_by_bosses → 降。

    无 boss 信息 / comp 无 countered_by_bosses → **None**(ADR-0107 动态权重剔除,治死重)。
    有 boss + comp 有 countered_by_bosses 但未命中 → 0.5(真实中性:boss 在但不利害此 comp,有数据)。
    """
    if not bosses or not comp.countered_by_bosses:
        return None
    n_hit = sum(1 for b in comp.countered_by_bosses if b in bosses)
    return clamp(0.5 - 0.5 * n_hit, 0.0, 1.0) if n_hit else 0.5


def held_strategy_fit(comp: Comp, active_strategies: list[str]) -> float | None:
    """**已持有策略**契合(ADR-0135 机会型 pivot 核心;用户「拿到适配策略主动转阵容」)。

    每张持有策略的绑定(``strategy_bindings``,ADR-0134 派生)∩ comp(阵营/core 角色)命中 → 该策略
    对此 comp 加成。归一 0..1:0.5 中性(无策略/无命中),每命中 +0.25 封顶 1.0(星徽套组双命中
    = 三件套到手 → 1.0 满分,comp_score 显著抬 → select_comp/update_target 自然转向)。
    无持有策略 → None(动态权重剔除,与 env_fit 同语义)。
    与 env_fit 的分工:env = 开局定向(选环境时 comp 未定);本函数 = **局中机会**(策略到手后
    重评 comp,把「牌找阵容」反转成「阵容追牌」)。
    """
    from sr_od.application.currency_war.cw_investments import (
        get_strategy,
        strategy_bindings,
    )
    if not active_strategies:
        return None
    hits = 0
    for name in active_strategies:
        s = get_strategy(name)
        if s is None:
            continue
        fs, cs = strategy_bindings(s)
        hits += len((fs & set(comp.factions)) | (cs & set(comp.core_chars)))
    if hits == 0:
        return 0.5   # 有策略但都不绑此 comp:真实中性(非无数据)
    return clamp(0.5 + 0.25 * hits, 0.0, 1.0)


def env_fit(comp: Comp, env: str) -> float | None:
    """投资环境契合:① T0 env 近乎硬绑(P1-2 ENV_COMP_AFFINITY);② env 加成对应阵营(R2-9)。

    未选投资环境(env 空)→ **None**(ADR-0107 动态权重剔除,治死重)。env 已选但不加成此 comp → 0.5
    (真实中性:env 在但不利好此 comp,有数据)。
    """
    if not env:
        return None
    # P1-2: T0 env 近乎硬绑某 comp
    if env in ENV_COMP_AFFINITY:
        affinity = ENV_COMP_AFFINITY[env].get(comp.name, 0.0)
        if affinity > 0:
            return clamp(0.5 + 0.5 * affinity, 0.0, 1.0)
    # R2-9: env 加成对应阵营
    boosted = ENV_FACTION_MAP.get(env, [])
    if boosted and any(f in comp.factions for f in boosted):
        return 1.0
    return 0.5


def strength_base(comp: Comp) -> float:
    """research meta 强度先验:{S:1.0, A:0.7, B:0.4}。"""
    return {"S": 1.0, "A": 0.7, "B": 0.4}.get(comp.strength, 0.5)


def current_enemy_mechanics(state: GameState) -> set[str]:
    """当前敌人机制 tag 集合(从 state.enemy_affixes 经 AFFIX_MECHANIC_MAP 映射;未知词缀原样透传)。"""
    return {AFFIX_MECHANIC_MAP.get(a, a) for a in state.enemy_affixes}


def make_score_context(state: GameState, bosses: list[str] | None = None) -> ScoreContext:
    """从 GameState 快速构造 ScoreContext(常用入口)。bosses 由外部 OCR 传入。"""
    return ScoreContext(
        bosses=bosses or list(state.plane_bosses),
        mechanics=current_enemy_mechanics(state),
        env=state.active_env,
        held_strategies=list(state.active_strategies),   # ADR-0135 机会型 pivot(选完策略后 update_target 重评)
        plane=state.plane, round_num=state.round_num, gold=state.gold,
    )


# ===== comp_score(候选 comp 综合分)=====
# 权重 = 各维度**importance 先验**(V4.4 research meta 校准;归一化 sum=1.0)。开发者阶段 6 手调(内部)。
# 2026-08-04 实跑校准:W_PROG 0.35→0.45 / W_STR 0.10→0.05 / W_MECH 0.20→0.15。
# 根因:select_comp 卡在无 progress 的高 strength comp(列车同行 S=1.0),但商店没刷其牌 → 不收敛、
# 超长战斗。提 W_PROG 让 select_comp 偏好**可成型**(board 已有 progress,如 万敌 燃血:1)comp 而非
# 高强度不可成型。算账:万敌(progress0.125,str0.4) vs 列车同行(prog0,str1.0),旧 0.084<0.1(列车同行赢);
# 新 0.45*0.125+0.05*0.4=0.076 > 0.45*0+0.05*1.0=0.05(万敌赢)= 选可成型。
#
# 动态权重(ADR-0107,治本 review#5 死重):权重不再因「数据未接通」而失效 —— *_fit 无数据返 None,
# weighted_mean 剔除 None 项 + 权重重分配给有数据项。故 W_BOSS 复位 0.10(ADR-0106 暂置 0 的 stopgap
# 不再需要:boss 无数据时 boss_fit 返 None → 自动剔除,不再贡献死重常量;数据接通即生效)。
W_PROG: float = 0.45    # 成型进度(form + core_char)—— 偏好可成型 comp
W_MECH: float = 0.15    # 机制契合(双向 debuff=buff)
W_ENV: float = 0.15     # 投资环境契合
W_HELD: float = 0.15    # 已持有策略契合(ADR-0135 机会型 pivot;无持有 → None 动态剔除,权重重分配)
W_BOSS: float = 0.10    # boss 克制(无数据 → boss_fit 返 None → 动态剔除;countered_by_bosses 接通即生效)
W_EQUIP: float = 0.10   # 装备契合(comp 相关)
W_STR: float = 0.05     # research meta 强度


def weighted_mean(items: list[tuple[float, float | None]]) -> float:
    """动态加权平均(ADR-0107):None 项(无数据)剔除,权重重分配给有数据项。

    治本(review#5):消除 *_fit 无数据返 0.5 的「常量地板」—— 全 comp 同值的项不区分却仍占权重,
    挤压 progress/strength 区分力(dead weight)。None 项不进加权 → 有数据项有效权重升 → 区分力恢复。
    全 None → 0.0(理论上不会:comp_score 的 progress/strength、comp_viability 的 form/star 恒有数据)。
    """
    valid = [(w, v) for w, v in items if v is not None]
    total_w = sum(w for w, _ in valid)
    if total_w <= 0:
        return 0.0
    return sum(w * v for w, v in valid) / total_w


def comp_score(comp: Comp, state: GameState, ctx: ScoreContext) -> float:
    """候选 comp 综合分(select_comp 评分 candidate 用;无观测项 —— 未 commit 的 candidate 无观测)。

    多维度 comp 相关(用户:一切挂钩目标阵容):成型进度 + 机制双向 + 环境 + boss + 装备 + 强度。
    动态归一(ADR-0107):*_fit 无数据返 None → 该项剔除、权重重分配(治死重常量地板)。
    评 **current 已 commit** comp 用 cw_performance.comp_viability(加观测 blend),不用本函数。
    """
    return weighted_mean([
        (W_PROG, progress(comp, state)),
        (W_MECH, mechanics_fit(comp, ctx.mechanics)),
        (W_ENV, env_fit(comp, ctx.env)),
        (W_HELD, held_strategy_fit(comp, ctx.held_strategies)),
        (W_BOSS, boss_fit(comp, ctx.bosses)),
        (W_EQUIP, equip_fit(comp, state)),
        (W_STR, strength_base(comp)),
    ])


# 用户 4 轴 steer(README A):优先/禁止/build_around。阶段 2 用 getattr 防御读取(config 字段待加)。

def _passes_steering(comp: Comp, config) -> bool:
    """用户 steer 硬过滤:build_around 必含、forbid 必不含。不满足 → 排除出候选。"""
    build_around = getattr(config, 'character_build_around', []) or []
    if build_around and not any(c in comp.core_chars for c in build_around):
        return False
    char_forbid = getattr(config, 'character_forbid', []) or []
    if any(c in comp.core_chars for c in char_forbid):
        return False
    faction_forbid = getattr(config, 'faction_forbid', []) or []
    return not any(f in comp.factions for f in faction_forbid)


def _priority_boost(comp: Comp, config) -> float:
    """用户 steer 软加权:命中 priority 角色/阵营 → 加分(tiebreak 偏向用户偏好)。"""
    boost = 0.0
    char_pri = getattr(config, 'character_priority', []) or []
    for c in comp.core_chars:
        if c in char_pri:
            boost += 0.05 * (len(char_pri) - char_pri.index(c)) / max(len(char_pri), 1)
    faction_pri = getattr(config, 'faction_priority', []) or []
    for f in comp.factions:
        if f in faction_pri:
            boost += 0.05 * (len(faction_pri) - faction_pri.index(f)) / max(len(faction_pri), 1)
    return boost


def _difficulty_phase_factor(comp: Comp, state: GameState) -> float:
    """阶段感知因子(用户:成型难度 + 早期战力都是关键维度):早期/穷 → 偏 easy 成型 + early_power 高。

    弱阵实验:原只偏 form_difficulty easy(DOT队 easy 被选),但 DOT队 DoT 慢热 plane1 弱死。
    加 early_power 维度(列车同行 A850 挂机=高 / DOT队=低)→ 早期偏 easy **且** early_power 高,
    避免选易成型但早期弱的 comp。先验待实玩校准(多局验证)。
    """
    early = (state.round_num + (state.plane - 1) * 6) <= 3 or state.gold < 30   # 全局 elapsed 判早期(位面内 round_num 1-6 循环 → per-plane 判会误把 plane2/3 r1-3 当早期)
    if not early:
        return 1.0
    form_fac = {"easy": 1.15, "medium": 1.0, "hard": 0.85}.get(comp.form_difficulty, 1.0)
    power_fac = {"高": 1.15, "中": 1.0, "低": 0.85}.get(comp.early_power, 1.0)
    return form_fac * power_fac


def _formation_cost_factor(comp: Comp) -> float:
    """成型成本因子 —— 低 form_tiers sum(易成型)→ ×>1;高 sum(难成型)→ ×<1。

    分析 COMP_LIBRARY 发现:命运圣杯红A sum=3(3 人激活)vs 龙丹战技点 sum=8(4+4 人激活)。后者成型
    需 ~16 rounds(plane1+plane2 18 rounds 几乎全用),前者 ~6 rounds(plane1 内成型)。plane1 成型
    = 进 plane2 时 comp 强 → 能活。旧码 form_progress 不含 total cost(2 阵营部分成型 progress 可能
    > 1 阵营满成型,但后者只需再几人 vs 前者再多人)。
    """
    if not comp.form_tiers:
        return 1.0
    total = sum(comp.form_tiers.values())
    # sum=3 → ×1.15;sum=4 → ×1.1;sum=6 → ×0.95;sum=8 → ×0.85(low cost boost, high cost penalty)
    return max(0.85, 1.3 - total * 0.055)


def _board_alignment(comp: Comp, state: GameState) -> float:
    """board-alignment boost(CW deployed-lock → 选 board 支持的 comp)。

    comp 阵营在 board 有 count≥2(deep-stack)→ ×1.2;全不在 board → ×0.3(deployed-lock 下不可成型,
    review🔴 重 penalty:原 ×0.7 压不过 acq 0.15-1.0 主导 → spread;改 ×0.3 让 board 支持主导选 comp);
    count≥1 → ×1.0(中性)。**robust to board OCR 噪声**:count≥1 判 has_any 可靠;count≥2 bonus 非 penalty。
    """
    if not comp.factions:
        return 1.0
    board = state.board
    if any(board.get(f, 0) >= 2 for f in comp.factions):
        return 1.2   # deep-stack → boost
    if not board:
        return 1.0   # ADR-0135:空板 = 无部署证据 → 不罚(罚的前提是 deployed-lock 有错配证据;
        # 旧版空板全罚 ×0.3 = 无证据惩罚,且只打到 factions 非空的 comp —— 反甲白厄(factions 空,
        # 故意设计)永远躲过 → 早期选择被数据伪影抬轿,机会型 pivot 也被它压死)
    if not any(board.get(f, 0) >= 1 for f in comp.factions):
        return 0.3   # 全不在 board(板有单位)→ 重 penalty(review🔴:原0.7 压不过 acq,改0.3)
    return 1.0


def _held_base_copies(state: GameState) -> dict[str, int]:
    """玩家持有的每角色**基础副本数**(牌池消耗 j;ADR-0110 acq 牌池感知用)。

    bench + deployed 各单位按 star 折基础副本(3合1:1星=1 / 2星=3 / 3星=9 / 4星=27 张基础副本)。
    持有越多 → 牌池剩余该角色越少 → 越难再刷(牌库有限,用户根因)。
    state.bench/deployed 由 session.tracked_* seed(带 char_id+star;shop.py:185);空(首轮/无身份)→ {}。
    """
    counts: dict[str, int] = {}
    bench = list(getattr(state, 'bench', []) or [])
    deployed = list(getattr(state, 'deployed', []) or [])
    for bc in (*bench, *deployed):
        cid = getattr(bc, 'char_id', None)
        if not cid:
            continue
        star = max(getattr(bc, 'star', 1), 1)
        counts[cid] = counts.get(cid, 0) + 3 ** (star - 1)
    return counts


def select_comp(state: GameState, ctx: ScoreContext, config,
                top_n: int = 1) -> list[Comp]:
    """按 comp_score 选 target(分数降序,返回 top_n)。

    评分 = comp_score(多维)+ 用户 4 轴 steer(硬过滤 build_around/forbid + 软加权 priority)
    + 阶段成型难度因子(早期偏 easy)。optionality 时传 top_n=2-3 备选几套(P1-1:核心来了再 commit)。
    """
    held = _held_base_copies(state)   # ADR-0110:acq 扣玩家持有副本(牌池有限)
    # ADR-0135:持有策略**绑定授予**的角色(星徽套组「获得1个【X】」)计入持有副本 —— 送卡 = 已持有,
    # acq 不按全牌池低估(机会型 pivot 的 acq 解锁;仅对本 comp 核心生效,他 comp 不吃这份加成)。
    _granted: dict[str, int] = {}
    from sr_od.application.currency_war.cw_investments import (
        get_strategy,
        strategy_bindings,
    )
    for _n in ctx.held_strategies:
        _s = get_strategy(_n)
        if _s is None:
            continue
        _gfs, _gcs = strategy_bindings(_s)
        for _c in _gcs:
            _granted[_c] = _granted.get(_c, 0) + 1
    scored: list[tuple[float, Comp]] = []
    for comp in COMP_LIBRARY:
        if not _passes_steering(comp, config):
            continue
        _h = dict(held)
        for _c, _k in _granted.items():
            if _c in comp.core_chars:
                _h[_c] = _h.get(_c, 0) + _k
        s = comp_score(comp, state, ctx) + _priority_boost(comp, config)
        s *= _difficulty_phase_factor(comp, state)
        # ADR-0135 成型加速乘子:持有策略双命中(fit=1.0,套组三件套到手)→ ×1.25(期望成型提前一档);
        # 中性 0.5 → ×1.0(不加不减)。加性 W_HELD 会被 acq/难度乘子稀释,乘子保证机会信号不被淹没。
        _hf = held_strategy_fit(comp, ctx.held_strategies)
        s *= 1.0 + 0.4 * ((_hf if _hf is not None else 0.5) - 0.5) * 2
        # acquirability(ADR-0110 牌池感知):P(单次刷新≥1 张该角色),扣玩家持有副本(牌库有限,用户根因)。
        # review🔴 收窄(ADR-0105):0.5+0.5·acq —— acq 作次级 tiebreak(非主导,board 支持优先),
        # 防选「core 易刷但 board 不支持」的 comp → spread。牌池感知后范围 ~0.005-0.3 → 乘子 0.50-0.65。
        s *= (0.5 + 0.5 * acquirability_factor(comp.core_chars, state.level, _h))
        s *= _board_alignment(comp, state)
        s *= _formation_cost_factor(comp)
        scored.append((s, comp))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _s, c in scored[:top_n]]


def comp_score_breakdown(comp: Comp, state: GameState, ctx: ScoreContext) -> dict[str, float | None]:
    """comp_score 的特征分解(telemetry 采集用:给人肉眼复盘 + 未来 ML side door)。

    schema 稳定(字段名跨版本不变);数值随版本/实玩变。*_fit 无数据项值为 None(ADR-0107)。
    详 cw_telemetry。
    """
    return {
        "progress": progress(comp, state),
        "mechanics_fit": mechanics_fit(comp, ctx.mechanics),
        "env_fit": env_fit(comp, ctx.env),
        "held_strategy_fit": held_strategy_fit(comp, ctx.held_strategies),
        "boss_fit": boss_fit(comp, ctx.bosses),
        "equip_fit": equip_fit(comp, state),
        "strength": strength_base(comp),
        "form_progress": form_progress(comp, state),
    }


# ===== 转型(pivot)+ 巨星(select_megastar)=====

# T#97 commitment(单一定义,maybe_pivot 强粘 + cw_decisions 买牌 prefilter 拒 off-target 共用):
# commit = 已成型(form_progress≥COMMIT_FRAC)**或**累计轮达 COMMIT_ROUND(spread board 的 form_progress
# 永不达 COMMIT_FRAC → 轮数兜底)。commit 后:① maybe_pivot 提阈不弃成型 comp;② cw_decisions prefilter
# 拒 off-target(commit 后买散牌 = spread 根因 → 该 Refresh 找 target / 攒金,drought bail 处理真不可达)。
COMMIT_FRAC: float = 0.4           # form_progress ≥0.4 算已 commit(2 阵营 comp 约 1 阵营过半)
COMMIT_ROUND: int = 2
COMMIT_STICK_FACTOR: float = 1.5   # 已 commit → pivot 阈值 ×1.5(0.10→0.15),更难弃成型 comp


def target_committed(target: Comp, state: GameState) -> bool:
    """target 是否已 commit。单一真相源(T#97);maybe_pivot(强粘)+ cw_decisions prefilter(拒 off-target)共用。

    commit = 已成型(form_progress≥COMMIT_FRAC)**或** 轮数兜底(累计轮≥COMMIT_ROUND **且** form_progress>0)。
    轮数兜底要求 form_progress>0 —— 防零投入误锁:board 全倒在别的 comp 上(target 零投入)时不应算 commit
    (明显错配,该 pivot;修 D-9 COMMIT_ROUND=2 绝对兜底误杀信号1 → test_maybe_pivot_better_comp_emerges fail)。
    spread board(target 有零星投入但散)轮数兜底仍生效 → 防散板振荡。
    """
    fp = form_progress(target, state)
    return (fp >= COMMIT_FRAC
            or ((state.plane - 1) * 6 + state.round_num >= COMMIT_ROUND and fp > 0))


def maybe_pivot(state: GameState, ctx: ScoreContext, config, target: Comp | None,
                tracker: PerformanceTracker | None = None) -> Comp | None:
    """是否转型到新 target(返回新 Comp 或 None 不转)。

    转型信号(比较型,03 正确性-4):**信号 3(保命)优先于 1/2**():
    3. **保命转型(最优先)**:hp < 0.75×effective_hp_threshold → 切最快成型的 easy comp
       (typical_form_round 最小,**稳定不 churn**)。hp 危险时信号 1/2 不参与(防振荡死亡螺旋)。
    1. 更优 comp 涌现:存在 B 使 comp_score(B) > target + PIVOT_SCORE_GAP(本回合单次比较)。
    2. ceiling 不可达:target.typical_form_round > 剩余轮次估算(已成型豁免)。

    ⚠️ 2026-08-05 实跑,低 HP 时信号 1 先触发选 select_comp best(随 board/shop 每轮变)→ target
    振荡 churn(列车同行→追击飞霄→DOT队→昼神阿雅)+ 选到高难度 comp → 死亡螺旋。改:信号 3 提前 +
    hp 危险时独占(返回稳定最快 easy,不让 1/2 churn)。
    ⚠️ 阶段 2 启发式:转型成本用规则估算,不用多步搜索(03 正确性-5)。tracker 用于保命判断的观测(已接:``is_losing_streak`` 解锁 commit 锁做保命转型,L791)。
    """
    PIVOT_SCORE_GAP: float = 0.10   # 更优涌现阈值(占位,待实玩校准)
    # (易 comp 成型快 → 少掉血;实跑 r3 列车同行[easy,S] vs 追击飞霄[medium] gap 0.097 卡 0.10 没转,
    # 追击飞霄 慢成型持续掉血。列车同行 fewer 卡 + S 强,转了更快成型)。target 已成型不降(不弃已完成 comp)。
    PIVOT_EASIER_FACTOR: float = 0.7   # best 更易成型时阈值 ×0.7(0.10→0.07),倾向转易 comp
    # F1(commit 强粘):已 commit(判据见模块级 ``target_committed`` / COMMIT_FRAC / COMMIT_ROUND)→ pivot
    # (已 commit 不因易 comp 降阈被弃)。COMMIT_* 已提模块级(maybe_pivot + cw_decisions prefilter 共用)。
    _diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    candidates = select_comp(state, ctx, config, top_n=len(COMP_LIBRARY))
    if not candidates:
        return None
    best = candidates[0]
    # 2026-08-05 实跑,低 HP 时信号 1(更优涌现)先触发 → 选 select_comp best(随 board/shop 每轮变 →
    # target 振荡 churn:列车同行→追击飞霄→DOT队→昼神阿雅)+ 选到高难度 comp(昼神阿雅)→ 永不成型 →
    # 死亡螺旋。保命须让位:hp 危险时只认最快 easy comp,信号 1/2 不参与(防 churn)。
    _pivot_hp = int(0.75 * effective_hp_threshold(state, config))
    if state.hp < _pivot_hp:
        easy = [c for c in candidates if c.form_difficulty == "easy"] or candidates
        with_progress = [c for c in easy if form_progress(c, state) > 0]
        if with_progress:
            fastest = min(with_progress, key=lambda c: c.typical_form_round or 99)
            if target is None or fastest.name != target.name:
                log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 %s->%s [board有progress优先]',
                         state.plane, state.round_num, state.hp, _pivot_hp,
                         target.name if target else 'None', fastest.name)
                return fastest
            return None   # 已在该 easy comp → 保持(不让信号 1/2 churn 切走)
        # 有 progress)被 easy 过滤排除,旧 fallback `pool=with_progress if with_progress else easy` → 选最快
        if target is not None and form_progress(target, state) > 0:
            # target 有 progress(medium 也算)→ 保持(不弃有 progress 的去追 0-progress easy;转 0-foundation 必死)。
            log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 无easy有progress → 保持 %s(有progress,不转0-foundation)',
                     state.plane, state.round_num, state.hp, _pivot_hp, target.name)
            return None
        fastest = min(easy, key=lambda c: c.typical_form_round or 99)
        if target is None or fastest.name != target.name:
            log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 无progress → 最快easy %s',
                     state.plane, state.round_num, state.hp, _pivot_hp, fastest.name)
            return fastest
        return None
    # D-9:已 commit 的 target **不被信号1(涌现)翻转**。comp_score 随 board 每 round 抖动(board 因
    # buy 变)→ 信号1 反复越阈值 → target 振荡(实测 r1-7 击破流萤↔r1-8 DOT队,均 committed)→ buy 每轮
    # 为不同 comp 买 → 永不集中 → 散板。COMMIT_STICK_FACTOR×1.5(0.15 阈)压不住(大 board 波动 gap 仍超)。
    # commit 即锁定:只有信号3(HP 危机,上方已优先处理)/信号2(ceiling 不可达)/drought_bail(连续无供给)
    # /losing-streak(obs 驱动保命)能解锁。人玩同理:commit 后不因「略优 comp」弃成型,只危机才转。
    if target is None or best.name != target.name:
        _committed = target is not None and target_committed(target, state)
        _losing = tracker is not None and target is not None and tracker.is_losing_streak(target.name)
        if _committed and not _losing:
            log.info('[cw-pivot] p=%s r=%s hp=%s target=%s 已commit → 锁定,跳过信号1(防振荡;best=%s 不转)',
                     state.plane, state.round_num, state.hp,
                     target.name if target else 'None', best.name)
        else:
            if target is None:
                # 无 target(尚未承诺)→ 无忠诚对象,signal1 的 gap 检查不适用(它为防「弃 current target
                # churn」而设,target=None 无可弃)→ 直接选 best。动态权重(ADR-0107)让 comp_score 诚实化
                # (无数据不再注水 0.5 常量)→ 早期诚实低分也该有 target,不该卡 gap 阈留 None。
                log.info('[cw-pivot] p=%s r=%s hp=%s 无 target → 直接选 best %s(未承诺,gap 检查不适用)',
                         state.plane, state.round_num, state.hp, best.name)
                return best
            target_score = comp_score(target, state, ctx) if target is not None else 0.0
            best_score = comp_score(best, state, ctx)
            gap = best_score - target_score
            _required_gap = PIVOT_SCORE_GAP
            _easier = (target is not None
                       and _diff_rank.get(best.form_difficulty, 1) < _diff_rank.get(target.form_difficulty, 1)
                       and form_progress(target, state) < 1.0)
            if _easier:
                _required_gap = PIVOT_SCORE_GAP * PIVOT_EASIER_FACTOR   # 未 commit + 易 comp → 降阈
            _tag = ' [易comp降阈]' if _easier else ''
            if _losing:
                _required_gap *= 0.7
                _tag += ' [viability losing]'
            if gap > _required_gap:
                log.info('[cw-pivot] p=%s r=%s hp=%s 信号1涌现 %s->%s (best %.3f vs tgt %.3f, gap %+.3f>%.2f%s; bd=%s)',
                         state.plane, state.round_num, state.hp,
                         target.name if target else 'None', best.name,
                         best_score, target_score, gap, _required_gap, _tag,
                         {k: round(v, 2) for k, v in comp_score_breakdown(best, state, ctx).items() if v is not None})
                return best
            log.info('[cw-pivot] p=%s r=%s hp=%s 信号1未达 %s vs %s (gap %+.3f<=%.2f%s 保持)',
                     state.plane, state.round_num, state.hp,
                     best.name, target.name if target else 'None', gap, _required_gap, _tag)
    # 信号 2:ceiling 不可达(target 成型轮次 > 剩余轮次)
    if target is not None and target.typical_form_round > 0:
        # 位面内剩余轮次粗估(每位面 6 轮,3 位面 = 18 轮;已过 round_num + (plane-1)*6)
        elapsed = state.round_num + (state.plane - 1) * 6
        remaining = max(18 - elapsed, 0)
        if target.typical_form_round > remaining and form_progress(target, state) < 1.0:
            # 切成型最快的(easy 优先);已成型(form_progress=1.0)豁免 —— 不该放弃已完成的 comp
            easy = [c for c in candidates if c.form_difficulty == "easy"] or candidates
            new = min(easy, key=lambda c: c.typical_form_round or 99)
            log.info('[cw-pivot] p=%s r=%s 信号2ceiling %s->%s (form_round %s>剩%s)',
                     state.plane, state.round_num, target.name, new.name,
                     target.typical_form_round, remaining)
            return new
    return None


# 盛会之星巨星 buff 表(米游社 factions.md 原文;select_megastar 按 target_comp 选,不单独评分)
MEGASTAR_BUFF: dict[str, str] = {
    # 巨星角色 → 适合的 comp 机械属性(粗估,实玩校准)
    "知更鸟": "幸运一击", "花火": "战技点", "星期日": "前后台强度",
    "黑天鹅": "5费增伤", "大丽花": "击破",
}
MEGASTAR_BY_ATTRIBUTE: dict[str, str] = {
    # comp 机械属性 → 推荐巨星(反向;粗估)
    "幸运一击": "知更鸟", "击破": "大丽花", "5费增伤": "黑天鹅",
}


def select_megastar(state: GameState, target: Comp | None,
                    available_megastars: list[str]) -> str | None:
    """选 1 名盛会之星作巨星(盛会之星羁绊核心决策;按 target_comp 选,不单独评分)。

    - 若 target.core_chars 含盛会之星且在可选里 → 绑该角色(如「知更鸟 comp」→ 知更鸟)。
    - 否则按 buff 契合 target.mechanic_attributes 推。
    - 无 target / 无可选 → None(退回 naive 默认,调用方处理)。
    """
    if not available_megastars:
        return None
    if target is not None:
        for c in target.core_chars:
            if c in available_megastars:
                return c
        for attr in target.mechanic_attributes:
            star = MEGASTAR_BY_ATTRIBUTE.get(attr)
            if star and star in available_megastars:
                return star
    return available_megastars[0]
