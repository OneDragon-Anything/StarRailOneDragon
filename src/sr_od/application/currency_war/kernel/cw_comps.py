"""货币战争 阵容库 + 战略层评分(comp_score / select_comp;纯逻辑,可测,不碰游戏)。

战略层:围绕目标阵容 commit + 转型 + 巨星。
auto-chess 胜负手 = commit 哪个阵容 + 何时转型 + 巨星绑谁;本模块给**可配置 + 自适应**的选目标机制。

数据与设计依据(详 ``docs/develop/currency_war/strategy/02_comp.md`` +
``05_observation.md`` + ``docs/game/currency_war/data/plaza_meta.md``):
- ``COMP_LIBRARY``:起步 roster(20 套;ADR-0152 plaza 784 篇高难帖校准)。
  **两层架构**:``cw_plaza_comps.py``(gen_plaza_comps.py 生成)= base 事实层(实战频次/装备/节奏);
  本文件 COMP_LIBRARY = 手判层(strength/form_difficulty/level_plan 取舍)—— ``plaza_carry`` 字段
  是两层对拍锚点。覆盖易/中/难成型 + 各机制(含 debuff=buff 的燃血、augment 定义型的黑塔纪元)。
- ``comp_score`` / ``select_comp``:按场面(gold/轮次/boss/已持牌/环境/词缀)多维打分选 target。

**核心原则(用户 2026-08-03,贯彻全程)**:
1. **一切 comp 相关** —— equip/mechanics 都挂钩目标阵容,无孤立评分(不设通用 equip_score/词缀表)。
   反重力皮靴对昼神阿雅(需 2 靴)是命脉、对别的 comp 不一定;正当防卫词缀对万敌燃血是利、对阿雅是克。
2. **debuff 可能是 buff** —— 同一词缀对不同阵容方向相反(mechanics_fit 双向:counter 降 + synergy 升)。
3. **COMP_LIBRARY 多维打分 + 运行时按场面选** —— 不锁死一套,按成型难度/boss/环境/词缀灵活选易成型又够强的。
4. **经济统一论** —— 每 comp 自带 ``level_plan``(成型路线),驱动战术层花超额金(接法见 cw_economy 的经济效果拆分)。

**核心/弹性羁绊二分(ADR-0152)**:``factions`` = 核心羁绊(成型判定);``flex_factions`` = 弹性次要
(plaza 实证「核心保证四列车即可,其他自由搭配」—— 板朝 flex 铺不罚,env/策略亲和照吃)。
**augment 定义型 comp**(:``AUGMENT_COMP_AFFINITY``):黑塔纪元/飞光类棱彩策略拿到即近乎硬绑
(镜像 ENV_COMP_AFFINITY;held_strategy_fit 消费)。**全局过渡池**(:``TRANSITION_POOL``):
plaza Early 六巨头(藿藿/饮月/三月七/爻光/椒丘/艾丝妲),过渡工程(买入分级加权+卖出保留判定)消费。

⚠️ meta(版本依赖):core_chars/form_tiers/strength/form_difficulty 是 V4.4 估值(plaza 校准 +
米游社合集 76807134),replay + 实玩迭代。装备 Final-only = plaza UI 限制(时序看合成首选,非玩法事实)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    shop_payload_content_cards,
)
from sr_od.application.currency_war.data.cw_shop_odds import acquirability_factor
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    deployed_slots_of,
    gold_of,
    level_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    GiftGrant,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_economy import effective_hp_threshold

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_performance import PerformanceTracker


def clamp(x: float, lo: float, hi: float) -> float:
    """限幅(lo..hi)。"""
    return lo if x < lo else (hi if x > hi else x)


# ===== 数据结构 =====

@dataclass(frozen=True)
class EquipChoice:
    """装备到人的两档选择(C4 契约;equip_assign 值元素)。

    - ``fixed``:首选装备(choices 单元素或多件固定);
    - ``pool``:候选池(黄泉第四件类——平缓分散非双峰,按优先序全候选都是关键件)。
    教义来源:final_comps/final_huangquan_debuff.md 装备公式「第四件=池(平缓分散)」。
    """
    kind: str                       # 'fixed' | 'pool'
    choices: tuple[str, ...]        # fixed: 固定件;pool: 候选池按优先序


@dataclass
class LevelGoal:
    """某玩家等级该做什么(成型路线的一站;经济统一论驱动战术花超额金)。

    曲线随 COMP_LIBRARY 填(框架先定,曲线建库时填)。
    """
    action: str            # "level_up"(攒金升下一级,解锁更高费刷新率)/ "roll"(D 找核心)/ "stable"(稳住吃息)
    target_cost: int = 0   # roll 时重点找几费核心(0=不限;随等级升:前期1费/中期4费/后期5费)
    target_chars: list[str] = field(default_factory=list)   # 这级该找谁(core_chars 子集)
    star_goals: dict[str, int] = field(default_factory=dict)  # 角色名 → 目标星级(成型档显式要求;无显式要求的卡不设默认启发式目标,按成型档需求走——费用档默认星目标规则已废弃,M6)


@dataclass
class Comp:
    """一套目标阵容(meta 数据,V4.4 起步估值待实玩校准)。

    核心/弹性羁绊二分(ADR-0152,plaza 784 篇实证「核心保证四列车即可,其他自由搭配」):
    ``factions`` = 核心羁绊(form_tiers 键 ⊆ 它;成型判定只看核心);``flex_factions`` = 弹性
    次要羁绊(不进 form_tiers,但板面朝它铺不被 board_alignment 罚、env/策略绑定照常亲和)。
    ``plaza_carry`` = cw_plaza_comps 聚类 carry 名(对拍锚点;空 = 无 n≥5 聚类对应)。
    """
    name: str                    # "追击飞霄"/"昼神阿雅"/"万敌单C"(roster 单一源 = 本注册表)
    factions: list[str]          # 核心阵营组合 ["追击"](查 FACTIONS)
    core_chars: list[str]        # 核心角色(名)["飞霄","知更鸟"]
    form_tiers: dict[str, int]   # 成型 tier 目标 {"仙舟":5,"追击":3}(几人激活算成型;键 ⊆ factions)
    strength: str                # "S"/"A"/"B" 综合强度(版本强度;不标"邪道" —— 邪道非必需)
    form_difficulty: str         # "easy"/"medium"/"hard" 成型难度(用户:关键维度)
    early_power: str = "中"
    level_plan: dict[int, LevelGoal] = field(default_factory=dict)  # 成型路线(玩家等级→该做什么);建库时填
    key_equips: list[str] = field(default_factory=list)      # 关键装备(可含重复,如阿雅需 2 反重力皮靴)
    countered_by_bosses: list[str] = field(default_factory=list)   # 克这阵容的 boss 名(boss_fit 用)
    mechanic_attributes: list[str] = field(default_factory=list)  # comp 机械属性 tag(mechanics_fit 经 MECHANIC 表判)
    shared_chars: list[str] = field(default_factory=list)    # 与其他 comp 共享的 core(转型可复用)
    transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)
    # comp 特定站位要求(角色→"front"/"back"),覆盖命途 position_pref 默认 ——
    # 攻略实证:爻光必后台(绯英攻略反向论证:后台跑条给前台多开大,总伤更高)、万敌独前排(燃血吃受击)、
    # 知更鸟前台(追击支撑)。空 = 全按命途默认。
    char_positions: dict[str, str] = field(default_factory=dict)
    typical_form_round: int = 0  # 大致成型所需轮次(level_plan 粗估汇总)
    version_tag: str = "V4.4"    # 版本维护用
    flex_factions: list[str] = field(default_factory=list)  # 弹性次要羁绊(ADR-0152;不进 form_tiers)
    plaza_carry: str = ""        # plaza 实战聚类 carry 名(对拍锚,查 cw_plaza_comps.cluster_by_carry)
    # ⚖️ 位面强度维度:comp 在哪些位面乏力(被环境抽陀螺)。来源=攻略实证
    # (V4.0-4.4 难度攻略「DOT 队第二位面被抽陀螺」);消费端=maybe_pivot 信号 3
    # (保命转型按位面过滤——P2 危血时转 P2 乏力 comp = 转完更死,实机局实证)。
    weak_planes: tuple[int, ...] = ()

    # ===== v2 字段扩(C4 契约冻结语义;leader 裁决)=====
    # 字段语义冻结;各套填值草案级(流派统计刷新可再改)。教义级内容(禁忌/铁三角/替班不卖)
    # 逐条对 final_comps 各篇(research/final_comps/)原文,不自创。
    form_tiers_max: dict[str, int] = field(default_factory=dict)
    """区间档上限(裁决 5:form_tiers **保 int=下限**,旧窄消费零破坏)。
    键 ⊆ form_tiers 键;某键缺省 = 上限即 form_tiers 值(单点档)。
    成型判定读 form_tiers(下限);完成度上限读 form_tiers_max(新读者显式选端)。"""
    family: str = ''                # v2 家族键(9 家族;长尾套 'legacy' 保活不删,旧策略 C5 兼容)
    branch_key: str = ''            # 分岔变量描述("词条前置"/"装备口径";无流派套写"无流派(...)")
    branch_of: str | None = None    # 兄弟套指针(同 family 另一分支的 comp 名;分岔动作消费)
    sub_tiers: dict[str, int | tuple[int, int]] = field(default_factory=dict)
    """副档目标档深(参与完成度;升格过半线锚)。键 = 羁绊规范名,**不得**与 form_tiers
    键重复(那是主档);值 int 或 (下限,上限) 区间。"""
    free_slots: list[dict] = field(default_factory=list)
    """自由槽:``[{'row': 'front'|'back', 'tags': [...], '说明': str}]`` —— 带标签即坐不点名
    (量子槽"缇宝/符玄/花火凑到哪个算哪个"类)。"""
    substitute_plan: list[dict] = field(default_factory=list)
    """替班结构(C4 冻结语义:替班=「不卖、转副C沉淀」):每项
    ``{'替班者': str, '顶位': str, '身份': str(到岗后), '分岔点': str}``。
    卖出型打工归全局 TRANSITION_POOL(transition_chars 兼容视图),不进本字段。"""
    special_systems: dict[str, dict] = field(default_factory=dict)
    """特殊系统件(枚举开放,已知四键):'navigator'(领航员绑定+时间函数)/
    'grail_quest'(圣杯任务链,Archer 非购买)/'aha_slots'(阿哈装备栏)/
    'cost_escalation'(银狼升费链)。"""
    equip_assign: dict[str, list[str | EquipChoice]] = field(default_factory=dict)
    """装备到人(C4 最大新增):角色名 → 装备序列(str=fixed 首选 / EquipChoice 两档)。
    键 ⊆ core_chars ∪ shared_chars ∪ substitute_plan 替班者;**本字段一旦非空,
    ``key_equips`` 必须恒等于 ``derive_key_equips(comp)``(C5 兼容地基,恒等测试锁)。"""
    equip_taboos: list[str] = field(default_factory=list)
    """本套禁买禁合成装备/装备类(教义手编,官方机制原文;如万敌禁一切护盾件)。"""
    equip_synergy: dict[str, str] = field(default_factory=dict)
    """件间关系(铁三角:少一件链断)——描述性元数据,判断层手编。"""
    bond_signal: str | None = None
    """②类专属羁绊信号名(cw_intention detect_signals 层②消费)。
    值 = 该家族的「专属羁绊」规范名;**按设计无②信号
    的家族(希儿量子:量子/贝是放大器;白厄反甲:独立羁绊绑死单卡)= None**。"""
    global_accumulators: dict[str, str] = field(default_factory=dict)
    """全局累积型角色标注(user_playstyle [21] 定谒例外)。
    键 = 角色规范名(⊆ core_chars ∪ shared_chars),值 = 累积类型:
    - 'hp_charge_stack':场上事件(受击)驱动的全局叠层(万敌:受伤充能+
      生命上限永久提高)——适用「有空位就上」部署例外(环境条件满足时);
    - 'cost_escalation':升费链(银狼LV.999 3→4→5 费)——累积持久但由
      购买/D 驱动而非上场时间,**不适用「有空位就上」例外**,仅早买早D
      (已被 [22] 囤件与 level_plan 建模,此处只作类型区分)。
    判据与全量扫描见 ``docs/game/currency_war/research/final_comps/accumulator_family.md``。
    部署例外规则**尚未实现**——消费点应为 decision_v2/candidates._deploy_candidates
    / scoring._deploy_pipeline,实现归后续策略批;本字段目前仅数据标注,零行为改动。"""

    # ===== T-171 批序 1 形态端口(ADR-0613):OR 腿 + carry 在场条件 =====
    # 两字段缺省空 = 行为不变。生产写入方 = cw_intention.pair_target_comp
    # 希儿系对分支(P1 配方锁伪 comp)+ COMP_LIBRARY 静态套「希儿量子」
    # (P2+ 锁线路径经 get_comp 消费静态条目,ADR-0621;档位单一源 =
    # SEELE_OR_LEGS/SEELE_CARRY_CHAR)。判定/进度唯一折法 = ``form_progress``
    # (单一源契约 fp=1.0 ⟺ 成型谓词),禁消费位绕过自写 AND/OR 内联判定
    # (判据双源 = 批序 1 取代面,出处见 ADR-0613)。
    or_legs: list[tuple[str, int]] = field(default_factory=list)
    """OR 腿(析取档组):组内**任一** (羁绊, 档) 达成即该组算满——文档
    「凑到任一=成型,不设完全体门槛」(transition_combos.md:27 希儿系定义
    行;combo_methodology.md:133)。空 = 无 OR 腿(纯 AND)。进度折法:OR 组
    折叠为一条虚拟腿,腿值 = 组内各腿进度 max(取最好腿非均值,「任一即成」
    的进度语义;换最好腿只单调抬升无重置)。**OR 组承接同键档位**:键出现在
    本字段的 ``form_tiers`` 档位不入 AND 账(该键成型语义归 OR 组;档位值
    保留作线键/完全体账单结构载体——囤货采购集羁绊展开、晋升候选键面交集、
    换线距离账等结构消费读 form_tiers 键面,清空即残)。禁把 OR 腿当 AND
    写进 ``form_tiers`` 计账(键侧 AND 语义会把 OR 塌回 AND 全档——批序 1
    病灶本体)。"""
    required_deployed: tuple[str, ...] = ()
    """carry 在场条件:逐一必须**在板**(deployed;bench 在手不算)——文档
    成型判据第一合取支「希儿在场」(transition_combos.md:27)。空 = 无
    carry 条件。进度折法:逐名折一条 0/1 虚拟腿(在板=1 否则 0);state
    缺 deployed 视图的轻量假想面板按 0 计(保守向,缺读≠满成)。"""

    @property
    def all_factions(self) -> set[str]:
        """核心 + 弹性羁绊全集(亲和/过滤/板面判定用;成型判定仍只看 form_tiers)。"""
        return set(self.factions) | set(self.flex_factions)


def derive_key_equips(comp: Comp) -> list[str]:
    """key_equips 派生汇总(C4 降级 + C5 保活;**建库顺序地基:先本函数后动数据**——裁决 2)。

    语义(C4 冻结):key_equips 不再是独立维护字段,而是 equip_assign(装备到人)的
    投影——「汇总 + 去到人」:
    - equip_assign **为空**(长尾/未迁移套)→ 返回旧手编 ``comp.key_equips`` 原值
      (C5 兼容:旧策略/旧测试锁读它不炸);
    - equip_assign **非空** → 按字典序展开:fixed 条目原样,pool 条目贡献**全部候选**
      (候选池内每件都是关键件,黄泉第四件类), EquipChoice 展开顺序 = choices 优先序。

    恒等约束(C5 冻结):``comp.key_equips == derive_key_equips(comp)`` 对全库成立
    (多重集口径——equip_fit/合成材料判定消费均为多重集语义;顺序仅影响 equip_allocation
    的 carry 按序取件微差)。恒等测试锁此不变量,任何一侧单独改动即测试红(防双源漂移)。
    """
    if not comp.equip_assign:
        return list(comp.key_equips)
    out: list[str] = []
    for _person, items in comp.equip_assign.items():
        for it in items:
            if isinstance(it, EquipChoice):
                out.extend(it.choices)
            else:
                out.append(it)
    return out


@dataclass
class ScoreContext:
    """select_comp / comp_score 的每回合上下文(避免长参数列表)。"""
    bosses: list[str | None] = field(default_factory=list)      # 当前/将遇 boss 名(boss_fit;None=徽章态缺失位,ADR-0398)
    mechanics: set[str] = field(default_factory=set)             # 激活机制 tag(current_enemy_mechanics)
    env: str = ""                                                # 已选投资环境名(env_fit)
    held_strategies: list[str] = field(default_factory=list)      # 已持有投资策略(held_strategy_fit;机会型 pivot)
    plane: int = 1
    round_num: int = 1
    gold: int = 0
# 来源:docs/game/currency_war/data/competitors.md(V4.4 ~50 敌人词缀全集,米游社玩家攻略统计 🟡;词缀效果原文=affix_effects_data)+ cw_factions.FACTIONS desc(燃血角斗场原文)。
# 机制名跨版本稳;具体词缀属哪个机制随版本变(随 competitors.md 实机 OCR 更新)。
# 只建模"对某类 comp 方向相反"的词缀(策略相关);纯数值怪强化(首领强化等)无 comp 交互,不入表。

MECHANIC_COUNTERS: dict[str, list[str]] = {
    # 机制 tag → 它克制的 comp 机械属性
    "反伤": ["高频低单次"],        # 正当防卫:克高频低单次(反甲白厄式)
    "冻结": ["慢速", "战技点依赖"],  # 极速制冷/坠入陷阱/冷冻冬眠:克慢速 + 战技点消耗队
    "净化": ["DoT", "减益"],       # 净化身心:克 DoT/减益主派(cw_events decide_event 消费,机制注册表单一源;原 config dot_punish_envs 已删)
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
    # 「爆发机会→爆发速杀」行已删(ADR-0500):紧急止血词缀经三问分诊判死——十类 comp 体系
    # 无「战斗内速杀」原型(Q1 无对应物)、判据需战斗时长数据源而注册表无此维度(Q2 不可判),
    # 零携带死映射恒 0.5 空转;若未来 sim 侧建立战斗时长建模,可从观测数据重立。
    # 观测对(ADR-0500,行保留不建模):词缀方向真实(高费 +5%/低费 -5%,V4.4),但 mechanics_fit
    # 最细步进 0.20 ≈ 20% 级战力差,±5% 差异打成 0.2 步进=离散 tag 系统性过反应 ×4,会把本该
    # 近中性的选型扰动成硬 flip。挂重审条件:①出现费用差异化幅度 ≥15% 的词条;②comp_score
    # 引入连续费用分布通道使粒度错配消失。届时阈值推导按「决策规则数学先行」补出处。
    "高费审美": ["高费队"],       # 高费审美:4 费及以上 +5%(V4.4)
    "低费审美": ["低费队"],       # 低费审美:3 费及以下 +5%(V4.4)
    # ⚠️ 形单影只只建模了「免罚」半边:词条另一半 = 伤害 85%/60%/30% 落在**未激活羁绊方**
    # (1/2/3 个未激活羁绊的板,即未凑羁绊的队),该侧当前零载体零 counter 行——
    # 未成型侧伤害倍率未建模,见 ADR-0500 与 w882 攻击报告(形单影只角度)。
    # 机制后果:「单挂队」词汇不存在于携带词汇表,cw_events 避险判据(全 counter + fit<0.4
    # 刷新换批)对全表伤害量级最大的词缀反而永不触发。挂账:单挂队 tag 建模待聚类型判据批
    # (未激活羁绊数可从 factions/form_tiers 推导,但逐套判型需板面档位数据,另立批勿顺手打)。
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
    "紧急止血": "爆发机会",   # 已判死保留注记(ADR-0500):下游 synergy 行已删,tag「爆发速杀」
    # 无任何 comp 携带,此行映射后求交恒空=零行为;保留透传使未知词缀语义不丢,重立时只需回补行。
    "高费审美": "高费审美", "低费审美": "低费审美",
    "形单影只": "成型羁绊利好",   # 未成型侧(-70% 落未激活羁绊方)未建模,见 MECHANIC_SYNERGIES 同 tag 注记
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

# (W875 环境B类评分补全包已随 w875 双旗标开关族删除——旧方案清退批,
#  清查报告 OLD_MIX_AUDIT §1.3:W875_AFFIX_MECHANIC_MAP/COUNTERS/
#  SYNERGIES 增表、_W875_TAG_FLAG 与 w875_active_tags 门控删除,
#  merged_mechanic_tables 退化为基表直通(与全关零漂移行为一致)。
#  死映射防线核查记录见 w872/w875 目录;其余词缀(区别对待/霸凌弱者/
#  以人为本/挫其锋芒等)的 comp 侧建模挂账随包退役,复活须重新立项。)


def merged_mechanic_tables(registry: DecisionV2Registry | None = None,
                           ) -> tuple[dict[str, str], dict[str, list[str]], dict[str, list[str]]]:
    """生效机制三元组(词缀映射/克制/受利)= 基表直通。

    (原 W875 开关放行的合并拷贝路径已随开关族删除——旧方案清退批,
    清查报告 OLD_MIX_AUDIT §1.3;保留本函数签名,消费点
    mechanics_fit / current_enemy_mechanics / cw_events / cw_intention
    调用零改。``registry`` 参数保留占位,不再参与取值。)
    """
    return AFFIX_MECHANIC_MAP, MECHANIC_COUNTERS, MECHANIC_SYNERGIES

# ===== (原 W878 死 tag 复活 4 批已随 w878 四旗标开关族删除——旧方案
# ===== 清退批,清查报告 OLD_MIX_AUDIT §1.3)=====
# 复活包的开关门控(w878_active_tags/动态载体判据 is_mono_attribute_
# comp/ATTRIBUTE_TYPE_FACTIONS/MONO_ATTRIBUTE_MIN_TIER)删除;四个 tag
# (单属性队/成型羁绊队/慢速/依赖合成装备)按删除前默认关口径**永久
# 滤除**出评分求交——零漂移;comp 静态标注与基表行保留(结构锁口径:
# 携带词汇表不动,只不参与评分)。
_W878_RETIRED_TAGS: frozenset[str] = frozenset({
    "单属性队", "成型羁绊队", "慢速", "依赖合成装备"})


def effective_mechanic_attributes(comp: Comp,
                                  registry: DecisionV2Registry | None = None) -> list[str]:
    """comp 生效机械属性 = 原属性 − 退役 W878 tag(单一滤除口;mechanics_fit 消费)。

    (原开关门控滤除已改为无条件滤除——W878 复活包随旧方案清退批删除,
    清查报告 OLD_MIX_AUDIT §1.3;与删除前默认关行为逐位一致。)
    返回值约定(w922 审计 P3):**调用方不可变**——快速路径零分配,直接透传 comp 内部
    list,仅触发滤除时才返回新 list;消费点一律只读,禁原地改写返回值。
    """
    if not any(t in _W878_RETIRED_TAGS for t in comp.mechanic_attributes):
        return comp.mechanic_attributes
    return [a for a in comp.mechanic_attributes
            if a not in _W878_RETIRED_TAGS]

# AFFIX_EFFECTS(词缀→游戏原文效果)见 affix_effects_data.py(单独文件;运行时 write_affix_effects
# 自动写入采到的新词缀/校准)。本文件不 import 该注册表,mechanics_fit 亦不消费;
# 消费方为 cw_briefing_obs.load_affix_effects_from_file(ast 提取)。
# comp.countered_by_bosses 已按 BOSS_NICKNAMES 归一规范公司名(boss_fit 双侧
# normalize_boss_name 接通俗称归一注册表后俗称键可命中,但规范名直写消除双名空间)。

# ===== 环境 → 阵营/comp 亲和(P1-2 T0 env 近乎硬绑 + R2-9 env→faction)=====
# 累积型角色强环境机制 tag 集(`w607_affix_consumption/` H1 锁线环境判据的数据层):
# 「全局累积型阵容需特定环境才强,无环境不选」(user_playstyle [21] 例外条款);
# 万敌强环境 = 敌方多动/反伤类(docs/game/currency_war/research/final_comps/
# accumulator_family.md §3 表,证据高;§4.2 前提②「词缀 ∈ 该成员强环境集」
# 判经 AFFIX_MECHANIC_MAP 归一后与本集求交)。「灼热轰炸」等未入
# AFFIX_MECHANIC_MAP 的词缀按不命中处理(宁缺勿错,不猜映射)。
# 键 = Comp.global_accumulators 的累积类型(非角色名——判据按类型辖)。
STRONG_ENV_MECHS: dict[str, frozenset[str]] = {
    'hp_charge_stack': frozenset({'反伤', '多段惩罚'}),
}

# 库藏生锈词缀名(`w607_affix_consumption/` H2 消费钩子的词条识别名):备战席每 1 件未穿装备 →
# 敌方造成伤害 +3%、受到伤害 -4%,最多计 10 件
# (docs/game/currency_war/data/competitors.md:45,2026-08-28 游戏内实采)。
RUST_AFFIX_NAME: str = '库藏生锈'


# ===== 中期护航三套——已删除(清退评估批,2026-09) =====
# EscortComp/ESCORT_COMPS/escort_for(含「成长型不护航」GROWTH_MECHANICS,
# 仅 escort_for 消费,同链死亡)整段移除:生产消费点早已清零,清查报告
# OLD_MIX_AUDIT §7.2 裁定随先例(M6 费用档星目标)删除;测试词汇对照
# (test_cw_affix_megastar serves 对照 / test_cw_decisions escort_for 单测)
# 同批删除。本注释仅为防复活的墓碑指针。

# ENV_FACTION_MAP 从投资环境注册表派生(单一真相源:概念股/邀请的 faction 字段;改注册表自动传导)
ENV_FACTION_MAP: dict[str, list[str]] = {
    name: [e.faction] for name, e in INVESTMENT_ENVS.items() if e.faction
}
ENV_COMP_AFFINITY: dict[str, dict[str, float]] = {
    # T0 env → {comp_name: 亲和权重} —— 拿到应近乎硬绑该 comp(research §10.3:env 是 run 内最大单一决策)
    "昼之半神概念股": {"昼神阿雅": 1.0},   # 送阿雅+鞋+刷新率 → 近乎硬绑昼神
    # ↓ ADR-0152(plaza 784 篇 portal 频次校准):概念股/邀请 = 定向 comp 近硬绑;契约 = 中亲和
    "列车同行概念股": {"列车同行": 1.0},          # plaza 环境榜 #2(120 篇)
    "列车同行邀请": {"列车同行": 0.9},            # plaza #6(87 篇)
    "银河学者概念股": {"大黑塔银河学者": 1.0},    # 送黑塔族 → 黑塔纪元/银河学者线
    "银河学者邀请": {"大黑塔银河学者": 0.9},
    "仙舟概念股": {"景元仙舟": 0.9},
    "仙舟邀请": {"景元仙舟": 0.8},
    "命运圣杯邀请": {"双王圣杯": 0.9, "命运圣杯红A": 0.8},
    "命运圣杯契约": {"双王圣杯": 0.7, "命运圣杯红A": 0.7},
    "特邀专家:桑博": {"专家桑博DOT": 1.0},        # 攻略明言「开局必须刷专家邀请环境」(33k use 帖)
    "欢愉契约": {"绯英欢愉": 0.7, "狼尊欢愉": 0.6, "火花星间旅人": 0.6},
    "量子同频契约": {"希儿量子": 0.7},
    # 量子线入口亲和(59 帖聚类校准):量子邀请/贝概念股/量子星徽系列 → 量子线
    # 中高亲和(plaza:量子契约 30 帖+邀请 16+贝概念股 14;星徽系列为策略侧,见下)
    "量子同频邀请": {"希儿量子": 0.9},
    "贝洛伯格概念股": {"希儿量子": 0.7},
    "贝洛伯格邀请": {"希儿量子": 0.6},
}
# ADR-0152:augment 定义型 comp 绑定表(镜像 ENV_COMP_AFFINITY 机制;held_strategy_fit 消费)。
# plaza 实证:这类 comp 的入口是「拿到棱彩策略」而非阵营成型 —— 黑塔纪元 35 篇整族围绕它构建。
# 键 = 注册表策略名(canon);值 = {comp_name: 亲和 0..1}(1.0 = 拿到即近乎硬绑)。
AUGMENT_COMP_AFFINITY: dict[str, dict[str, float]] = {
    "黑塔纪元": {"大黑塔银河学者": 1.0},   # 216 张黑塔入商店 + 追击转圈 → comp 由它定义
    "飞光·映月": {"景元仙舟": 1.0},       # 镜流+特殊1费景元 师徒(景元 cluster 16 篇中 8 篇带它)
    "飞光·传剑": {"景元仙舟": 1.0},       # 彦卿+景元 师徒强化(14 篇中 5 篇)
    "本姑娘就是罗刹": {"列车同行": 0.8},  # 三月七单位流(罗刹帖 13.5w use;三月七 carry 45 篇中 12 篇带它)
    # 量子星徽系列 = 希儿线策略侧入口(plaza 量子帖头部标配)
    "量子同频星徽": {"希儿量子": 0.8},
    "量子同频星徽套组": {"希儿量子": 0.8},
    "量子力学": {"希儿量子": 0.6},
}


def augment_affinity(name: str) -> dict[str, float]:
    """AUGMENT_COMP_AFFINITY 规范化查询(OCR 名先归一,run_20260826_004527 缺陷链同型)。

    入参可能是 OCR 原始名(如 `飞光•传剑`——OCR 把 `·` 误读为 `•`),裸 dict 直查会
    静默 miss → 定义型 comp 解锁/评分失效。所有持卡名/候选名查本表一律走此函数,
    不直接 ``AUGMENT_COMP_AFFINITY.get(name)``(归一单一源 = cw_investments.normalize_invest_name,
    AGENTS.md「OCR 文本匹配与修复」②无歧义形变先规范化)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    return AUGMENT_COMP_AFFINITY.get(normalize_invest_name(name), {})


def augment_env_affinity(name: str) -> dict[str, float]:
    """ENV_COMP_AFFINITY 规范化查询(OCR 环境名先归一;同 augment_affinity)。"""
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    return ENV_COMP_AFFINITY.get(normalize_invest_name(name), {})


# 全局过渡池(ADR-0152,按跨阶段存活率拆两级;plaza 784 篇 P(进终局|Early在场) 实证):
#   EARLY_CORE_POOL(存活 ≥0.8):「有体系牌来就拿下」—— 买了就是开局(期权重叠,不存在过渡浪费);
#   TEMPO_POOL(存活 <0.45):纯保血打工(骨架件)—— 1星买卖近无损,毕业即卖(1-8 分界换血)。
# 消费方:过渡工程(买入分级加权 + 卖出保留判定)—— 接线前是数据先验,勿删。
EARLY_CORE_POOL: list[str] = [
    "千冶·刃",   # 存活 0.96,Early 174 篇 —— 断层级早期核心
    "姬子·启行", "远坂凛", "丹恒·腾荒", "缇宝", "三月七", "花火",
]
TEMPO_POOL: list[str] = ["藿藿", "丹恒·饮月", "爻光", "椒丘", "艾丝妲", "卡芙卡"]
# 兼容旧名(过渡池并集)
TRANSITION_POOL: list[str] = EARLY_CORE_POOL + TEMPO_POOL


# ===== 直通终局线单卡依赖型核心卡登记(C1 信号层入口;知识判据,非数值)=====
# 唯一入选规则(谓词式,非清单枚举;出处 = 设计《直通核心卡信号层入口》§3
# 【修订·B3】):
#   入选(c) ⇔ 玩法权威文档中,c 所属线的开线/成型判据以「单一具名卡牌 c
#   在手」为必要条件 ∧ c 是体系伤害主体(该线其余成员 = 放大器/凑档件,
#   非独立伤害源)。
# 证据域 = transition_combos 四体系表 + 直通线信号谱两处,逐条目带出处
# 指针;排除举证(圣杯 Archer/燃血万敌/群攻大黑塔/黄泉/仙舟DOT/列车2)
# 见设计同节,防后续误扩。
# 封闭性辖域 = 双出处(四体系表希儿系行 + 直通线信号谱 r167-r168 更新节)
# ——四体系封闭裁定(transition_combos 头部)只辖过渡体系成员增删,不辖
# 直通线名单;名单变更随玩法文档版本走。值 = 出处指针字符串(知识判据
# 载体,禁塞数值权重——00_framework 第 1 条)。
# 消费位:C1 支配性支通道候选身份判定(mandate_v1/shop.py dominance 邻位)
# 与换线机器共用本单一源(防「入口说它是核心、换线机器说它不是」双源)。
CORE_SINGLE_CARD_REGISTRY: dict[str, str] = {
    '希儿': 'transition_combos 希儿系行「希儿(3费)单卡依赖——量子/贝是她的'
            '放大器不是独立伤害源」+核心表「希儿本人」+希儿线「核心=希儿一人」',
    # 欢愉线信号卡注册名 = 银狼LV.999(升星升费 3/4/5 费档,cw_chars
    # 「银狼LV.999」行,欢愉成员);量子同频 4 费「银狼」是另一张卡,不在册。
    '银狼LV.999': 'transition_combos 欢愉线「银狼 5 费在手才开线(同希儿型)」'
                  '+直通线信号谱「核心卡到手(希儿/银狼)」',
}


# ===== 角色↔路线复用网络(ADR-0152「整体灵活」建模;plaza 实证)=====
# 方法论(用户 2026-08-16):角色池 75 个、plaza 聚类 29 个、羁绊组合 427 种 —— 多样性本身就是玩法。
# 玩家在「角色→路线」复用网络上动态导航,不是「选一套 comp 配齐它」。三个消费点:
#   ① 买牌:枢纽角色(跨路线复用度高)拿了不亏 —— plaza 终局枢纽:千冶·刃28条路线/瓦尔特26/符玄26/
#      缇宝24/花火22/开拓者·记忆17/星期日15;早期枢纽:藿藿10路线+265次Early出场/饮月/爻光/椒丘。
#   ② 板面:早期骨架 = 便宜枢纽 × 低门槛羁绊(见 skeleton_factions)。
#   ③ 转型:路线间共享角色越多转型越便宜(maybe_pivot 消费 pivot_overlap)。

def char_routes() -> dict[str, set[str]]:
    """角色 → 可走路线(comp 名)集合 —— 从 COMP_LIBRARY 派生的复用网络(core+shared 计入)。

    transition_chars 不计(那是打工后卖的,不构成路线;core/shared 是终局成员)。
    枢纽度 = len(routes);买牌 optionality / 卖牌保留判定消费。
    """
    routes: dict[str, set[str]] = {}
    for comp in COMP_LIBRARY:
        for c in set(comp.core_chars) | set(comp.shared_chars):
            routes.setdefault(c, set()).add(comp.name)
    return routes


def pivot_overlap(src: Comp, dst: Comp) -> float:
    """src→dst 转型的角色重合度 0..1(共享缓冲;maybe_pivot 转型成本因子)。

    dst 需求角色(core∪shared)中已被 src 需求覆盖的比例 —— 重合高 = 转型只是「换方向继续买」,
    重合低 = 要推翻重来(卖板重买)。同 comp 返 1.0。dst 无任何需求角色(理论不可能,core 至少 1)
    返 0.5 中性;⚠️ 反甲白厄(core 仅白厄+shared 白厄)对任何 src 恒 0.0 —— 语义正确(它不与任何
    comp 共享,转型=推翻),非 bug(评审🟡 注记)。
    """
    if src.name == dst.name:
        return 1.0
    need = set(dst.core_chars) | set(dst.shared_chars)
    if not need:
        return 0.5   # 无共享语义可算(如反甲白厄):中性
    have = set(src.core_chars) | set(src.shared_chars)
    return clamp(len(need & have) / len(need), 0.0, 1.0)


def skeleton_factions() -> set[str]:
    """过渡骨架羁绊集(方法论派生,替硬编码 TRANSITION_FACTIONS 的数据源)。

    plaza 实战开局组合(「3仙舟2DOT」「2dot2学者」「2贝洛伯格」)不是背出来的,是判据筛出来的:
    羁绊最低激活档 ≤3 人 **且** ≤2 费成员 ≥2 个(便宜+快激活+有人可买)。从 FACTIONS/CHARACTERS
    注册表派生(单一真相源,版本更新自动传导);过渡判据(kernel.cw_transition)消费。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_factions import FACTIONS

    cheap: dict[str, int] = {}
    for _name, ch in CHARACTERS.items():
        if ch.cost <= 2:
            for f in ch.factions:
                cheap[f] = cheap.get(f, 0) + 1
    # 狼狩封存(四体系封闭裁定;同 cw_bridge_pool.py 前注):不再作为
    # 过渡骨架判据候选——判据筛选合格也不入集。
    _SEALED_SKELETON_FACTIONS: frozenset[str] = frozenset({'狼狩'})
    return {name for name, info in FACTIONS.items()
            if (info.tiers and min(info.tiers) <= 3 and cheap.get(name, 0) >= 2)
            and name not in _SEALED_SKELETON_FACTIONS}


# ===== COMP_LIBRARY(起步 roster;V4.4 估值,待实玩校准)=====
# (本注册表单一源。)form_tiers 用 FACTIONS tier 设"成型"里程碑;data 待实玩精确。

# v2 家族键(9 家族;家族打法知识单一源=final_comps 各篇)
# ——长尾套 family='legacy' 保活(C5 兼容不删)。
V2_FAMILIES: tuple[str, ...] = (
    "万敌燃血", "希儿量子", "DOT卡芙卡", "姬子列车", "黄泉减益",
    "欢愉族", "圣杯双C", "大黑塔群攻", "白厄反甲",
)

# ===== 希儿系成型判据常量(注册表数据层;静态套与 pair 物化共用判据)=====
# 档位出处 = 文档定义行 transition_combos.md:27「希儿在场 ∧ (量子同频≥2 ∨
# 贝洛伯格≥2),不设完全体门槛」(combo_methodology.md:133「凑到任一=成型」/
# :143「放大器不需要最大档」);量 2 vs 量 3 的文档内部张力(combo_
# methodology.md:133/170 写量 3)挂玩家确认(ADR-0613 同一挂账口径,不由
# 落码批裁决),确认后改档动本常量(配对消费位随 import 自动跟随),
# **另须同步第三表面** `_seele_system_support` 的 ÷2 分母(挂账指针 =
# cw_intention._seele_system_support docstring「同步回改本式分母」节;
# 公式体用字面量 2 不消费本常量,接线守卫钉不住,漏改=两端口档位漂移)。
# carry = 同表行第一合取支「希儿在场」。
# ⚠️ 单一源归属声明(ADR-0621):真源归位本文件(注册表数据层——静态套
# 条目在 import 期消费,常量若留 cw_intention 会反向 import 成环)。
# cw_intention 经顶部 import 消费本常量(re-import 别名,其形态端口注
# 「禁再写本地第二份」),单一源接线由测试仓接线守卫钉死(对象身份 `is`,
# 本地第二份复发即红)。
SEELE_OR_LEGS: tuple[tuple[str, int], ...] = (('量子同频', 2), ('贝洛伯格', 2))
SEELE_CARRY_CHAR: str = '希儿'

COMP_LIBRARY: list[Comp] = [
    # ===== S 级(版本真神,V4.4 合集 76807134)=====
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/final_jizi_train.md(游戏知识,非字段镜像,无同步义务)
        name="列车同行", factions=["列车同行"], core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        form_tiers={"列车同行": 4}, strength="S", form_difficulty="easy", early_power="高",
        # V4.4 权威评级(76807134):姬子·启行 = S 级真神;A850 挂机流(76824096):全程自动/不凹开局/适应任何负面环境 → bot 默认首选
        # 成型 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝
        # ADR-0152(plaza 784 篇校准):carry 274/在场 358 篇断层级第一;双分支 —— 护盾流(152 篇,姬子带
        # 以牙还牙甲+砂金)/减益流(127 篇,冷笑话引擎+彦卿);flex_factions 全收(plaza 羁绊分布)。
        # 装备 top:风暴潮352/电锯190/以牙还牙甲116/冷笑话56 → 双风暴+电锯+以牙还牙(跨分支覆盖)。
        flex_factions=["护盾", "减益", "战技点", "量子同频", "盛会之星", "能量", "星间旅人"],
        plaza_carry="姬子·启行",
        key_equips=["火力风暴潮", "高周波电锯", "自适应外骨骼", "冷笑话引擎"],
        # v2 教义 A 流铁三角=三月七 自适应外骨骼(吸仇恨刚需)/姬子 以牙还牙甲×2-3;
        # 恒等约束(多重集不变)下以 A 流首选件(外骨骼)入表。B 流拆分批放开恒等时
        # 姬子侧补 以牙还牙甲×2。
        countered_by_bosses=[], mechanic_attributes=["治疗护盾", "成型羁绊队"],   # 成型羁绊队:战力=列车同行4 档乘区(w878 判型;tag 已永久滤除(_W878_RETIRED_TAGS))
        shared_chars=["三月七", "花火", "瓦尔特"], transition_chars=["符玄", "艾丝妲"],
        typical_form_round=5,
        # ===== v2(C4):姬子列车家族(A/B 未拆条——分岔变量=词条前置:敌方多动旺→A 反震/怕词条在→B 输出)=====
        family="姬子列车", branch_key="A/B 未拆(词条前置分岔;拆分留后续批)",
        bond_signal="列车同行",   # ②类信号:四人 100% 固定
        form_tiers_max={"列车同行": 4},
        sub_tiers={"护盾": 2, "减益": 2},   # A 流护盾2(50% 盾循环必然)/B 流减益2(58%)——分支依赖,拆分批归位
        equip_assign={"姬子·启行": ["火力风暴潮", "高周波电锯"], "三月七": ["自适应外骨骼"], "花火": ["冷笑话引擎"]},
        # ↑ v2 教义 A 流:三月七=自适应外骨骼(吸仇恨刚需;甲属姬子 A 流×2-3)。
        # B 流完整配装留 A/B 拆分批落位
        equip_synergy={"铁三角": "自适应外骨骼吸仇恨→以牙还牙甲反伤→皮靴加速,少一件链断(教义:comp_elements 三·3)"},
        # 吸仇恨互斥的攻略行(不要杰帕德)已随 heuristic_ab B3 删出 PLUGIN_DISABLE_MATRIX
        # (4/300 局触发、无劣化;官方机制行保留),此处不再指向矩阵防悬空引用
        special_systems={"navigator": {"绑定": "三月七(A 流必绑,85%+ 共识)", "时间函数": "前期保命绑三月,后期可换绑(饮月/星期日)"}},
        substitute_plan=[
            {"替班者": "瓦尔特", "顶位": "姬子·启行 主C(姬子未 3★ 时)", "身份": "2★ 杨叔主C,装备转杨叔", "分岔点": "姬子 3★ 达成即交还"},
        ],
        level_plan={
            3: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七"], star_goals={"三月七": 2}),
            4: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "花火"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"),
            # ADR-0128(阵容_列车同行:53):**停留 7 级猛 D 3星姬子**(3费 7 级概率
            # 峰值 p=0.40)—— 旧 7=level_up 直冲 8 违背「核心概率级停留」人玩节奏。
            7: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七", "花火"],
                         star_goals={"姬子·启行": 3}),
            8: LevelGoal("roll", target_cost=0, target_chars=["姬子·启行", "花火", "瓦尔特"],
                         star_goals={"姬子·启行": 3, "花火": 2}),
            # (旧注「缺 lv9 → 落通用曲线 stable 零 D」的回退已随 _DEFAULT_LEVEL_
            # GOAL 退役(「未证即退役」裁定),lv9 无 plan 时仅节点地板辖;显式 lv9 roll
            # 保留:5费概率高,找 瓦尔特/花火 升星,姬子顺带。)
            9: LevelGoal("roll", target_cost=5, target_chars=["姬子·启行", "花火", "瓦尔特"],
                         star_goals={"姬子·启行": 3, "花火": 2}),
        },
    ),
    Comp(
        name="命运圣杯红A", factions=["命运圣杯"], core_chars=["Archer", "远坂凛"],
        form_tiers={"命运圣杯": 3}, strength="S", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):Archer 95 = S 级真神;攻略(76924524):高倍率九五核心+远坂凛+圣杯→+150%攻击+战技点
        # ⚠️ core_chars 用图鉴规范名:"Archer" 非"红A"(OCR/char_id 匹配靠 cw_chars.CHARACTERS 注册表)
        # ADR-0152(plaza 62 篇):3星率 0.18(5费 carry 常驻 2 星);速升9级节奏为主
        # 评审🔴(费用勘误):圣杯四人 = Archer 5费/Saber 3费/吉尔伽美什 2费/远坂凛 1费(注册表),
        # 旧注释「4 个 5 费成型难」错 —— 费用阶梯宽,成型难度主要在 Archer 本体。
        flex_factions=["战技点", "量子同频", "列车同行", "能量", "治疗", "盛会之星"],
        plaza_carry="Archer",
        key_equips=["火力风暴潮", "动能激发剑", "动能激发剑", "碎星斩舰刀"],   # 评审🟡4:plaza 风暴潮87>电锯45(≈2:1)顺序倒置修正+补动能激发剑22(#3)
        # ↑ v2 教义:Archer=**战技点件**(动能激发剑:回合开始+消耗各回 1 战技点,
        #   战技点燃料层主C 的本命件)。闪闪侧(反重力皮靴)在双王条目同步
        mechanic_attributes=["高倍率单核"],   # 榜样激励克高倍率单核(test_mechanics_fit_honga)
        shared_chars=["远坂凛", "瓦尔特"], transition_chars=["符玄", "知更鸟", "花火"],
        typical_form_round=6,
        # ===== v2:圣杯双C家族 A Archer 战技点线(燃料线官方接力结构)=====
        family="圣杯双C", branch_key="A Archer 战技点线(~34%)", branch_of="双王圣杯",
        bond_signal="命运圣杯",   # ②类信号:2 档开任务=燃料线入口
        special_systems={"grail_quest": {"产出": "Archer(圣杯任务链产出,非商店购买)", "触发": "圣杯 2 档开任务", "接棒": "任务完成即接棒 Saber"}},
        substitute_plan=[
            {"替班者": "Saber", "顶位": "Archer 主C(前中期)", "身份": "Saber 打到 Archer 到手;Archer 不来则 Saber 一直 C(任务系统照吃)", "分岔点": "Archer 任务完成"},
        ],
        equip_assign={"Archer": ["火力风暴潮", "动能激发剑"], "远坂凛": ["动能激发剑"], "Saber": ["碎星斩舰刀"]},   # Saber 键经 substitute_plan 容纳(替班者)
        # ↑ v2:Archer=战技点件(动能激发剑;远坂凛同持第二把,战技点燃料层教义)
        level_plan={  # 5费 Archer 是唯一高费门槛:前期低费过渡保血 → 升 8-9 找 Archer(2星即战力,0.18 三星率);评审🟡6:远坂凛 1费
            4: LevelGoal("roll", target_cost=1, target_chars=["远坂凛"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=5, target_chars=["Archer", "远坂凛"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["Archer"], star_goals={"Archer": 2}),
        },
    ),
    # ===== A 级(版本强势,V4.4 合集 76807134)=====
    Comp(
        name="千冶减益", factions=["减益", "星核猎手"], core_chars=["千冶·刃", "瓦尔特", "卡芙卡", "缇宝", "符玄"],
        form_tiers={"减益": 4, "星核猎手": 2}, strength="A", form_difficulty="easy", early_power="高",
        # plaza 聚类 千冶·刃 n=29(减益26/星核19/燃血13/量子13/列车12):减益通用板大族,此前无承接
        # (29 篇里最多 5 篇可被既有 comp 覆盖,评审🟢1 点名)。千冶·刃(2费) carry,瓦尔特 24/29+卡芙卡 16
        # +缇宝 15+符玄 14 常驻减益辅助群;皮靴 30 断层第一(carry 吃鞋)+风暴潮 14+螺旋桨 13;
        # 节奏 6级搜牌 12/29(2费 → 6级停)→7级 7 → 速升9 4(瓦尔特 5费);与黄泉减益(3费/7级)错位。
        key_equips=["反重力皮靴", "火力风暴潮", "光速螺旋桨", "反卫星狙击枪"],
        mechanic_attributes=["减益叠加", "成型羁绊队"],   # 成型羁绊队:减益4 档乘区为战力主体(w878)
        shared_chars=["黄泉", "花火", "不死途", "开拓者·记忆", "椒丘"],
        transition_chars=["椒丘", "风堇", "开拓者·记忆"], typical_form_round=6,
        family="legacy", branch_key="v2 未单列(长尾保活,C5 兼容不删;减益通用板)",
        flex_factions=["燃血", "量子同频", "列车同行", "治疗", "持续伤害"],
        plaza_carry="千冶·刃",
        level_plan={
            4: LevelGoal("roll", target_cost=2, target_chars=["千冶·刃", "卡芙卡"]),
            5: LevelGoal("level_up"),
            6: LevelGoal("roll", target_cost=2, target_chars=["千冶·刃"], star_goals={"千冶·刃": 3}),
            7: LevelGoal("roll", target_cost=2, target_chars=["千冶·刃", "缇宝"], star_goals={"千冶·刃": 3}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=5, target_chars=["瓦尔特", "符玄"]),
        },
    ),
    Comp(
        # 主羁绊(依据=final_feiying_joy.md 类结构三处一致:
        # 「欢愉4-7 + 星间旅人(25/25 双100%)……星间旅人2-3 + 仙舟3/能量3 挂件」)——能量降挂件
        # (进 flex),星间旅人升主羁绊(下限 2 档,成员=绯英本人在 core 即可达成)。
        name="绯英欢愉", factions=["欢愉", "星间旅人"], core_chars=["绯英", "瓦尔特", "爻光", "开拓者·欢愉", "符玄"],
        form_tiers={"欢愉": 4, "星间旅人": 2}, strength="A", form_difficulty="medium", early_power="中",
        # 欢愉下限 4 = v2 教义「欢愉 4-6 档(≤4 档即主流)」;上限见下方 form_tiers_max 定谳注
        # V4.4 评级(76807134):绯英 = A 级;攻略(76806732):绯英大招永久+2%伤害(无限成长),3欢愉+3能量+2量子+2减益
        # 前期狼尊开 3 欢愉过渡 → 上 8 踢狼尊换主角 → 上 9 找杨叔(瓦尔特)大成。爻光穿鞋频召阿哈叠层
        key_equips=["火力风暴潮", "永动机", "冷笑话引擎", "高周波电锯"],
        mechanic_attributes=["欢愉叠层", "成型羁绊队"], shared_chars=["瓦尔特", "爻光", "火花"],   # 成型羁绊队:欢愉 4-6 档乘区(w878)
        char_positions={"爻光": "back"},   # 站位:爻光必后台(攻略反向论证:后台跑条给绯英多开大,总伤更高;前台倍率<20%残血版)
        transition_chars=["花火"], typical_form_round=6,   # 评审🟡2:爻光 25/25 常驻是 core 非 transition;常驻是火花(16/25,4费)非花火
        # ===== v2:欢愉族家族·绯英档(资源锚 6 级;无信号时的默认落点)=====
        family="欢愉族", branch_key="绯英档(资源锚 6 级;无信号默认落点)", branch_of="狼尊欢愉",
        bond_signal="欢愉",   # ②类信号:绯英/银狼两档共用主体
        form_tiers_max={"欢愉": 5},   # 欢愉档位真值=3/4/5/7 **无 6 档**(米游社图鉴 API 重采,
        # content_id=7333;「欢愉 4-6 档」系连续区间误写);上限 5 = 4-5 主流带
        # (final_feiying「不到 7 也成型」,7 特权化属银狼档语义)。
        equip_assign={"绯英": ["火力风暴潮", "永动机"], "爻光": ["冷笑话引擎"], "瓦尔特": ["高周波电锯"]},
        # ↑ v2 教义:绯英=永动机(天赋装备化)+风暴潮;全队皮靴(本批恒等约束下未单列,拆分批放开)
        flex_factions=["能量", "仙舟", "治疗", "量子同频", "战技点"],   # 能量降挂件(final_feiying 挂件层),
        plaza_carry="绯英",
        level_plan={  # 评审🟡2:labels 6级搜牌 19/25=76%(全场最集中)→ 6级停 roll,旧 5/6/7 全 level_up 缺停留
            4: LevelGoal("roll", target_cost=1, target_chars=["绯英", "爻光"]),
            5: LevelGoal("level_up"),
            6: LevelGoal("roll", target_cost=2, target_chars=["绯英"], star_goals={"绯英": 2}),
            7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["绯英"], star_goals={"绯英": 2}),
            9: LevelGoal("roll", target_cost=5, target_chars=["瓦尔特"]),
        },
    ),
    Comp(
        name="希儿量子", factions=["量子同频", "贝洛伯格"],
        # core(依据=final_seele_quantum.md「构造机理」
        # n=67 槽位构造):引擎核心组=希儿/花火/符玄/缇宝/刻律德菈;插件层=千冶·刃(掩体生成枪)/
        # 布洛妮娅/杰帕德/娜塔莎/佩拉(贝2 凑数+辅助);知更鸟/瓦尔特移出 core(P3 补位件,留 shared)。
        core_chars=["希儿", "花火", "符玄", "缇宝", "刻律德菈"],
        form_tiers={"量子同频": 4, "贝洛伯格": 2}, strength="A", form_difficulty="medium", early_power="高",
        # 成型判据 = 文档 OR 口径(transition_combos.md:27,与 ADR-0613 的
        # pair 物化路径同构,ADR-0621):form_tiers 双档由 OR 组**承接**
        # (同键档位不入 AND 账,折法见 form_progress),档位值保留作线键/
        # 完全体账单结构载体——囤货采购集/晋升候选/换线距离账等消费读其
        # 键面,清空即残(银狼/佩拉/桑博等放大器成员会掉出采购集)。
        or_legs=list(SEELE_OR_LEGS), required_deployed=(SEELE_CARRY_CHAR,),
        # V4.4 评级(76807134):希儿 = A 级(A8-50 最强轮椅);攻略(76802749 直读纠正):4量子+贝城(2贝=原4贝,引擎拉条)
        # 斩杀+70%下二战技+再现+造物引擎。希儿(双电锯+风暴潮)+杨叔(瓦尔特)+记忆主+鸟(知更鸟)+刻律+鸭鸭(布洛妮娅)+符玄
        # 前期强势(希儿无装也能换怪/胜)→ 强烈推荐希儿过渡;7级找希儿3星或先上8/9找4-5费同时找希儿
        # 装备公式(final_seele_quantum §装备公式/§5,38 篇统计):希儿=风暴潮×2-3+电锯(唯一公式),
        # B 套=特权版风暴潮(plaza 实证 特权风暴潮三件);战场进化手册**不是本套件**
        # (是小黑塔星级装备,归大黑塔条目)。
        key_equips=["火力风暴潮", "高周波电锯", "火力风暴潮·特权"],
        # boss 键规范名(俗称键经 BOSS_NICKNAMES 归位规范公司名,
        # 与 state.plane_bosses 同名字空间;出处=final_seele_quantum counter 节「蕉研组 boss」)
        countered_by_bosses=["造梦兄弟影业", "造梦互动娱乐"],
        # 单属性队:量子同频4 属性型羁绊主档 ≥4(final_comps README D3「希儿怕量子熄火」,
        # plaza 希儿聚类 36/38 篇核心羁绊=量子同频)——量子熄火局对本套是主输出瘫痪级 counter。
        # 成型羁绊队:量子同频/贝洛伯格档位乘区。两者均为 w878 复活 tag(tag 已永久滤除(_W878_RETIRED_TAGS))。
        mechanic_attributes=["量子拉条", "单属性队", "成型羁绊队"],
        # 知更鸟/瓦尔特= P3 补位件(n=67 非核心组);插件层五人(千冶·刃/布洛妮娅/
        # 杰帕德/娜塔莎/佩拉)为终局插件购买件,不入 core/shared
        shared_chars=["知更鸟", "布洛妮娅", "瓦尔特"],
        transition_chars=["刃"], typical_form_round=6,
        # ===== v2:希儿量子家族(五线最收敛,无流派)=====
        family="希儿量子", branch_key="无流派(五线最收敛)",
        form_tiers_max={"贝洛伯格": 4},   # v2:贝洛伯格 2-4(双修不分离)
        free_slots=[{"row": "back", "tags": ["量子同频", "贝洛伯格"], "说明": "量子槽:缇宝/符玄/花火凑到哪个算哪个"}],
        equip_assign={"希儿": ["火力风暴潮", "高周波电锯", "火力风暴潮·特权"]},
        # ↑ 特权三件=希儿 B 套(final_seele_quantum §5「B 套=特权版风暴潮」);
        #   布洛妮娅降插件层后无专属装备条目
        #   (n=67 插件层定位=贝成员/增益,装备优先级让渡引擎组)。恒等:key_equips=派生投影
        flex_factions=["战技点", "治疗", "盛会之星", "列车同行"],
        plaza_carry="希儿",
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["希儿"]),   # 评审🟡6:希儿 3费,旧标 2
            6: LevelGoal("roll", target_cost=3, target_chars=["希儿"], star_goals={"希儿": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["希儿"], star_goals={"希儿": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=5, target_chars=["瓦尔特", "知更鸟"]),
        },
    ),
    Comp(
        name="黄泉减益", factions=["巡海游侠", "减益"], core_chars=["黄泉", "不死途", "乱破", "千冶·刃", "瓦尔特"],
        form_tiers={"巡海游侠": 4, "减益": 4}, strength="A", form_difficulty="medium", early_power="低",
        # 巡海游侠档 = v2 教义「4」单点档(后排星级 1/3/6/12 倍放大;form_tiers_max=4)。
        # V4.4 评级(76807134):黄泉 = A 级;攻略(76826405):3游侠+4减益+3量子,2星乱破+3星不死途→280%增幅
        # ADR-0152(plaza 50 篇校准):常驻 千冶·刃48/瓦尔特45/不死途45/乱破38/椒丘32 —— core 的「刃」
        # 改「千冶·刃」(V4.4 实战常驻是千冶·刃,非本体刃);装备 top:电锯56/风暴潮28/光速螺旋桨26/永动机24。
        flex_factions=["击破", "治疗", "追击", "量子同频"],
        plaza_carry="黄泉",
        key_equips=["高周波电锯", "火力风暴潮", "光速螺旋桨", "永动机"],
        # 「单体boss」是 boss 原型描述非公司名(BOSS_NICKNAMES 不含,永不命中;且占位会
        # 屏蔽 matchup 结构层兜底)——单体乏力由 mechanic_attributes
        # 走 cw_enemy_data.matchup 的 single_burst 结构通道表达。
        countered_by_bosses=[],   # 攻略:单体 boss 黄泉输出乏力(俗称键零效,走 matchup 结构通道)
        mechanic_attributes=["减益", "成型羁绊队"], shared_chars=["刃", "乱破", "符玄"],   # 成型羁绊队:巡海4+减益4 档乘区(w878)
        transition_chars=["刃", "椒丘", "桑博"], typical_form_round=7,
        # ===== v2:黄泉减益家族(无流派;第四件=装备池)=====
        family="黄泉减益", branch_key="无流派(第四件=装备池)",
        bond_signal="减益",   # ②类信号:4-6 档主体,到前 DOT 班底共享牌桌
        form_tiers_max={"巡海游侠": 4, "减益": 6},   # v2:减益 4-6 档/巡海 4
        sub_tiers={"击破": 2},   # v2:击破 58% 升格候选
        equip_assign={"黄泉": ["高周波电锯", EquipChoice("pool", ("永动机", "光速螺旋桨", "火力风暴潮"))]},
        # ↑ v2 教义:黄泉=电锯(69% 近必选);第四件=池(永动机38/螺旋桨30/冷笑话26/风暴潮26 平缓分散)——
        # 恒等约束(与旧 key_equips 多重集相等)下池取频次前三,冷笑话并列 26% 待拆分批放开
        substitute_plan=[
            {"替班者": "卡芙卡", "顶位": "黄泉主C(黄泉 7 级到前)", "身份": "DOT 班底照打(减益件与 DOT 件共享牌桌)", "分岔点": "黄泉 7 级到手即上"},
        ],
        level_plan={
            5: LevelGoal("roll", target_cost=1, target_chars=["乱破", "不死途"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=3, target_chars=["黄泉", "不死途"]),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["黄泉"], star_goals={"黄泉": 2, "不死途": 2}),
        },
    ),
    Comp(
        name="巡海击破", factions=["击破", "巡海游侠"], core_chars=["不死途", "波提欧", "乱破", "忘归人", "大丽花", "灵砂", "阮·梅"],
        form_tiers={"击破": 6, "巡海游侠": 4}, strength="A", form_difficulty="hard", early_power="中",
        # ↺ 推翻「击破流萤」(ADR-0152,plaza 784 篇):V4.4 击破代表已换代 —— 流萤任一阶段在场仅 29 篇
        # (carry 聚类 n=8,7/8 击破形)。**锚=波提欧簇**(12 篇,击破12/巡海12 全击破形;不死途簇 n=14 的
        # 主体是减益板[减益13/巡海12/击破11 混合],不当击破锚)。常驻 忘归人12/大丽花11/灵砂11/乱破11/阮·梅10。
        # 装备:波提欧=虫洞掘进钻头16/光速螺旋桨9,不死途=反重力皮靴。
        mechanic_attributes=["击破", "成型羁绊队"], shared_chars=["黄泉", "流萤", "忘归人"],   # 成型羁绊队:击破6 档乘区(w878)
        key_equips=["虫洞掘进钻头", "光速螺旋桨", "反重力皮靴", "光速螺旋桨·特权"],   # 评审🟡7:波提欧=钻头16/螺旋桨9,不死途=皮靴24(旧空表 equip_fit 恒 None)
        transition_chars=["赛飞儿", "灵砂", "忘归人"], typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;v2 白厄A 巡海流为白厄系,非本套)",
        flex_factions=["减益", "盛会之星"],
        plaza_carry="波提欧",
        level_plan={  # 后期 6 击破:前期过渡 → 升 8-9 击破;评审🟡6:波提欧 5费/不死途 2费
            5: LevelGoal("roll", target_cost=1, target_chars=["乱破"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["不死途", "波提欧"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["波提欧", "忘归人"], star_goals={"不死途": 2}),
        },
    ),
    Comp(
        name="龙丹战技点", factions=["战技点", "列车同行"], core_chars=["丹恒·饮月", "远坂凛", "瓦尔特", "花火", "刻律德菈"],
        form_tiers={"战技点": 4, "列车同行": 4}, strength="A", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):丹恒·饮月(龙丹)= A 级;攻略(76987716 直读纠正):4战技点+4列车(周日开)
        # 凛(远坂凛)V4.4 新:宝石叠99层→第二魔法实验拐198%爆伤(+默认70%=268%);饮月双电锯+风暴潮
        # 杨叔(瓦尔特)+记忆主必备;4列车给160%前台强度;刃+符玄补。苍龙濯世破百亿
        key_equips=["高周波电锯", "动能激发剑", "火力风暴潮", "斩首行动"], mechanic_attributes=["战技点依赖", "成型羁绊队"],   # 成型羁绊队:战技点4+列车4 档乘区(w878)
        shared_chars=["远坂凛", "瓦尔特", "花火"], transition_chars=["花火", "风堇", "姬子·启行"],
        typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;战技点作副档散于各线)",
        flex_factions=["量子同频", "盛会之星"],
        plaza_carry="丹恒·饮月",
        level_plan={  # 评审🟡6:饮月 2费(旧标3);花火 2费
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("roll", target_cost=2, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
    ),
    Comp(
        name="双王圣杯", factions=["命运圣杯", "能量"], core_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄", "开拓者·记忆", "藿藿"],
        form_tiers={"命运圣杯": 3, "能量": 5}, strength="A", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):双王 = A 级;攻略(76985789 直读纠正调研误认):双王=闪闪(吉尔伽美什)+Saber(Fate圣杯联动),
        # 非大黑塔+景元(游侠源误)。闪闪+Saber 每8行动连携+回能;圣杯羁绊给经济+改件加速3星。
        # Saber主c(风暴潮+冷笑话+永动机)/闪闪后台带鞋自加速;5能量;杨叔必备;刃+缇宝+符玄(阿瓦隆+绝对热量邪修75%减伤)
        # 过渡:体系牌+花火/凛(做3圣杯任务);7-8级找3星Saber或闪闪→上9挂杨叔
        key_equips=["火力风暴潮", "永动机", "冷笑话引擎", "反重力皮靴"],   # 评审🟡4:Saber 风暴潮56/永动机44/冷笑话36/电锯31(皮靴13 降位)
        # ↑ v2 教义:闪闪=**反重力皮靴**(41%,
        #   锁轴速度载体;final_grail_dual.md 圣杯A)
        mechanic_attributes=["连携高频开大", "成型羁绊队"], shared_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄"],   # 成型羁绊队:能量5 硬约束+圣杯任务链=档位乘区(w878)
        transition_chars=["花火", "刃"], typical_form_round=7,   # 远坂凛是 core(1 星即够)
        # ===== v2:圣杯双C家族·B Saber 能量线(~25%)=====
        family="圣杯双C", branch_key="B Saber 能量线(~25%;能量 5 为硬约束——口述「哪怕下远坂凛都不能拆能量」)", branch_of="命运圣杯红A",
        bond_signal="命运圣杯",   # ②类信号:2 档开任务=燃料线入口
        special_systems={"grail_quest": {"产出": "Archer 接棒(非商店购买)", "触发": "圣杯 2 档开任务", "备注": "本线即替班形态常态化:Saber 从 P2 打到 Archer 到手;Archer 不来则 Saber 一直 C"}},
        equip_assign={"Saber": ["火力风暴潮", "永动机", "冷笑话引擎"], "吉尔伽美什": ["反重力皮靴"]},
        # ↑ v2 教义:Saber=充能件(永动机/冷笑话引擎/电光履,主C 满能自拉条伪永动)
        flex_factions=["列车同行", "战技点", "治疗", "盛会之星"],
        plaza_carry="Saber",
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=3, target_chars=["Saber"], star_goals={"Saber": 2}),
            8: LevelGoal("roll", target_cost=3, target_chars=["吉尔伽美什", "Saber"], star_goals={"Saber": 3}),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
    ),
    Comp(
        # V4.0 A级(BV1vVcLzXEN8 2026-02 转录):花火主C(吃点巧普攻+幻语记,倍率随花火等级)+星间旅人
        # 羁绊(唯一有效应=旅人转职,1转职章=43.2%幸运暴伤);6战技点不提升 → 带银狼/符玄凑3量子;
        # 前期龙丹战技点护航;上8大D找2星花火,3星质变;爻光三鞋(跑条供R回合)。
        # 怕正当防卫;极速制冷不怕(R时刻解控)。好运令牌给阿雅(装备最顶级)勿给花火/爻光。
        name="火花星间旅人", factions=["欢愉"],
        core_chars=["花火", "爻光", "开拓者·欢愉", "银狼LV.999"],
        # 名义 core 羁绊修正:core+flex 里星间成员=0(注册表口径:花火=盛会之星+战技点/量子同频,非星间;星间成员
        # =火花/桑博/瓦尔特/罗刹/银枝/绯英/真理医生)——星间4 从本套 roster 不可构造。
        # 可达成形态:欢愉3(core 爻光+开拓者·欢愉+银狼LV.999 全欢愉成员);星间旅人降 flex
        # (final_yinlang_joy 构造机理:星间 3-7 是欢愉队**顺手开出来的第二增益源**,非构造目标,
        # 62/68 Final 实证)。
        form_tiers={"欢愉": 3}, strength="A", form_difficulty="medium",
        early_power="高",
        # ADR-0152 评审🔴(火花簇 25 篇):旧 factions[星间+量子] 0/25 达标 —— 实战分布 欢愉22/战技点21/
        # 星间21 并列,量子仅 flex 位 → 核心改 星间+欢愉(花火=欢愉阵营);core 补 开拓者·欢愉(20/25 在场,
        # 欢愉形态保留不换记忆)与银狼LV.999(17/25)。
        key_equips=["火力风暴潮", "高周波电锯", "碎星斩舰刀", "动能激发剑"],   # 花火1风暴潮+暴击刀;爻光三鞋
        countered_by_bosses=[], mechanic_attributes=["幸运一击", "成型羁绊队"],   # 成型羁绊队:欢愉档乘区(w878;星间降 flex)
        shared_chars=["银狼", "符玄", "丹恒·饮月"], transition_chars=["丹恒·饮月", "银枝"],
        typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;花火线)",
        flex_factions=["星间旅人", "战技点", "列车同行", "量子同频", "星核猎手"],   # 星间=顺手增益源
        plaza_carry="火花",
        level_plan={   # 前期龙丹护航 → 上8大D 2星花火 → 有机会追3必试(质变);评审🟡6:花火 2费/饮月 2费
            5: LevelGoal("roll", target_cost=2, target_chars=["丹恒·饮月"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["花火"], star_goals={"花火": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["花火", "开拓者·记忆"], star_goals={"花火": 3}),
        },
    ),
    Comp(
        # ADR-0152 新增(plaza 大族群补缺):银河学者+群攻族 —— 大黑塔 carry 38 篇 + 小黑塔 carry 26 篇。
        # **augment 定义型 comp**:35 篇带「黑塔纪元」(棱彩,216 张黑塔入商店+追击转圈)—— 拿到即玩
        # (AUGMENT_COMP_AFFINITY 近乎硬绑);无它时靠银河学者羁绊本身(星级总量成长)亦可成型,强度降档。
        # 黑塔纪元特型:备战席囤小黑塔(强度=小黑塔合计星级,「备战席放满越多越好」)—— bench 语义特例。
        name="大黑塔银河学者", factions=["银河学者", "群攻"], core_chars=["大黑塔", "黑塔", "缇宝", "翡翠"],
        form_tiers={"银河学者": 4, "群攻": 3}, strength="A", form_difficulty="medium", early_power="中",
        # plaza:大黑塔 3星率 0.82(4费);5级搜牌 20/38 篇(小黑塔 1费 5级 D 干);装备 电锯29/永动机20/蓄能帆17/电光履16
        # 记忆主必拿(「记忆主一定要拿,后台花火防战技点不足」);后期可上花火补战技点。
        key_equips=["高周波电锯", "永动机", "蓄能帆", "电光履", "战场进化手册"],
        # ↑ 战场进化手册=小黑塔星级装备(星级→强度),归本条(v2 教义);恒等约束同步扩入。
        mechanic_attributes=["追击", "成型羁绊队"], shared_chars=["黑塔", "缇宝", "翡翠"],   # 成型羁绊队:学者档=星级总量成长乘区(w878)
        transition_chars=["艾丝妲", "丹恒·腾荒"], typical_form_round=6,   # 黑塔(小黑塔)是 core/替班C
        # ===== v2:大黑塔群攻家族(档位=连续深度谱,非流派)=====
        family="大黑塔群攻", branch_key="档位=连续深度谱(群攻3+学者2 众数 29% → 完全体群攻5+学者4 仅 19%,低档通关是常态)",
        bond_signal="银河学者",   # ②类信号:星级总量成长
        form_tiers_max={"群攻": 5, "银河学者": 4},
        equip_assign={"大黑塔": ["高周波电锯"], "黑塔": ["战场进化手册", "永动机", "蓄能帆", "电光履"]},
        # ↑ v2 教义:大黑塔=电锯+风暴潮;小黑塔=战场进化手册(星级装备,自希儿量子归位)+充能三件套
        # (电光履/永动机/蓄能帆:强化战技→人偶追击循环)
        substitute_plan=[
            {"替班者": "黑塔", "顶位": "大黑塔主C(大黑塔 9-10 级到前)", "身份": "小黑塔当 C(备战席囤星级=喂学者档一石二鸟);本线小黑塔也追星(与辅助 2★ 通则相反)", "分岔点": "大黑塔 9-10 级接 C"},
        ],
        flex_factions=["量子同频", "列车同行", "公司", "减益"],
        plaza_carry="大黑塔",
        level_plan={  # 5级 D 小黑塔(1费)→ 7级大黑塔 → 9级补队友;黑塔纪元在手时 1-3 直接 D 干
            4: LevelGoal("roll", target_cost=1, target_chars=["黑塔"]),
            5: LevelGoal("roll", target_cost=1, target_chars=["黑塔"], star_goals={"黑塔": 3}),
            6: LevelGoal("level_up"),
            7: LevelGoal("roll", target_cost=4, target_chars=["大黑塔"], star_goals={"大黑塔": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["大黑塔", "缇宝", "翡翠"],
                         star_goals={"大黑塔": 3}),
        },
    ),
    Comp(
        name="银枝群攻", factions=["群攻"], core_chars=["银枝", "翡翠", "知更鸟"],
        form_tiers={"群攻": 3}, strength="B", form_difficulty="medium", early_power="低",
        # V4.4 评级(76807134):银枝 = B 级;攻略(77006068 直读纠正):V4.4 离能量,"轮椅通拐"(杨叔/主角/缇宝/花火/千冶刃+符玄)抬
        # 银枝(风暴潮+冷笑话)+翡翠(3群攻)+鸟(拉条加攻增伤+10%幸运);必须3星银枝;适合对群,对单大降
        # ⚠️ ADR-0152(注册表对拍):银枝=**星间旅人** 2费,非贝洛伯格(24 篇银枝帖贝洛伯格激活 0 次)
        # —— 核心只有群攻,星间旅人/公司/盛会之星(翡翠/知更鸟)是 flex。
        key_equips=["火力风暴潮", "冷笑话引擎", "绝对热量"], mechanic_attributes=["群攻", "成型羁绊队"],   # 成型羁绊队:群攻档乘区+大招驱动的羁绊协同型(w878)
        countered_by_bosses=[],   # 无 countered 数据:单体长战类非公司名,走 matchup 结构层
        shared_chars=["翡翠", "知更鸟"],
        transition_chars=["椒丘", "星期日", "刃"], typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;群攻族并归大黑塔线)",
        flex_factions=["星间旅人", "公司", "盛会之星", "列车同行"],
        plaza_carry="",   # 银枝 carry 聚类 n<5(24 篇在场,长尾)
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["银枝"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["翡翠", "知更鸟"]),
        },
    ),
    Comp(
        name="反甲白厄", factions=[], core_chars=["白厄", "三月七", "姬子·启行"],
        form_tiers={}, strength="A", form_difficulty="hard", early_power="低",
        # 白厄无阵营(cw_chars:104 factions=""),独立羁绊「救世主」(获所有前台非独立羁绊效果)。
        # 反甲流靠白厄单核 + 以牙还牙甲×3 受击反伤,**不靠阵营羁绊成型** → factions/form_tiers 空。
        # comp 靠 core_char(白厄)+ equip_fit(以牙还牙甲)+ mechanics(高频低单次 反伤);
        # form_progress 恒 0 → 不靠 form commit(轮数兜底要求 fp>0,fp=0 不触发),select_comp 候选但 progress 低。
        key_equips=["以牙还牙甲", "高周波电锯", "以牙还牙甲·特权", "热血沸腾拳"],   # meta:反甲流需 3 以牙还牙甲
        # boss 键规范名(BOSS_NICKNAMES:酒杯怪=造梦兄弟影业/琥珀王=铁盾安保集团/
        # 死龙=灰手生命科技;「红绿灯」经用户确认是小怪非 boss(2026-08-17),移除不建模)
        countered_by_bosses=["造梦兄弟影业", "铁盾安保集团", "灰手生命科技"],
        # 依赖合成装备:以牙还牙甲×3 反甲链+掩体生成枪=胜利条件本身(final_baie_reflect 明文
        # 「反甲装备流」);装备依赖词条(变宝为废)的选型侧降分载体(合成侧由 junk_first 处理,
        # 两半互补)。羁绊维判非成型羁绊队:factions/form_tiers 空,装备流例外。
        mechanic_attributes=["高频低单次", "依赖合成装备"], shared_chars=["白厄"],
        transition_chars=["符玄"], typical_form_round=7,   # 白厄 core/三月七 P2 直留终局
        # ===== v2:白厄反甲家族(A 巡海流 ~64% / B 列车护盾流 ~29%;A/B 未拆条)=====
        family="白厄反甲", branch_key="A/B 未拆(副羁绊层分岔:A 巡海 64%/B 列车护盾 29%;B 实为白厄借列车骨架)",
        sub_tiers={"护盾": 2},   # B 流副档(多数停护盾 2);A 流前排法则=标签数量×星级优先
        # ↑ A 巡海流(~64%)核心副羁绊=「巡海 3+」——A/B 未拆下
        #   sub_tiers 只收了 B 流 {护盾2},巡海 3 属 A 流、现仅在 flex_factions(板面不罚但完成度不数);
        #   A/B 拆分批落位时补 sub_tiers={"护盾": 2, "巡海游侠": 3}(分支依赖,同姬子 sub_tiers 口径)
        equip_assign={"白厄": ["以牙还牙甲", "以牙还牙甲·特权", "热血沸腾拳"], "三月七": ["高周波电锯"]},
        # ↑ 完整反甲链(以牙还牙甲×3+掩体生成枪持续群盾,生存位=绝对热量)留 A/B 拆分批
        equip_synergy={"反甲链": "以牙还牙甲×3 受击反伤核心 + 掩体生成枪(千冶·刃,持续群盾);A/B 配装槽按 boss/压力切换"},
        substitute_plan=[
            {"替班者": "姬子·启行", "顶位": "白厄主C(搜不到白厄时)", "身份": "共享列车池,转姬子线=攻略明写预案;B 流领航员身份 1 星够(49% 在场沉淀)", "分岔点": "红绿灯词条/白厄到手"},
            {"替班者": "三月七", "顶位": "前排(与 星期日/开拓者 自 P2 直留终局)", "身份": "直留终局(不卖)", "分岔点": "无(全程)"},
        ],
        # ADR-0152(plaza 校准):白厄 38 篇 carry 中 33 篇实际挂在列车同行(以牙还牙甲×93 断层第一,
        # 副三月七/姬子/星期日)—— 纯反甲白厄是小众硬流派;主流是列车护盾流的副 carry 位。
        flex_factions=["列车同行", "巡海游侠", "减益", "护盾"],
        plaza_carry="白厄",
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["白厄"]),
            6: LevelGoal("level_up"),
            7: LevelGoal("roll", target_cost=3, target_chars=["白厄"], star_goals={"白厄": 2}),   # 评审🟡8:labels 7级搜牌 25/38(66%),旧 7=level_up 直跳 8 缺停留
            8: LevelGoal("roll", target_cost=0, target_chars=["白厄"], star_goals={"白厄": 3}),
        },
    ),
    # ===== B 级(强度一般,V4.4 合集 76807134)=====
    Comp(
        name="狼尊欢愉", factions=["星核猎手", "欢愉"], core_chars=["银狼LV.999", "爻光", "千冶·刃", "开拓者·欢愉", "火花", "绯英"],
        form_tiers={"欢愉": 5, "星核猎手": 2}, strength="B", form_difficulty="medium", early_power="中",
        # V4.4 评级(76807134):狼尊 = B 级;攻略(76832783 直读):5欢愉(最大利用阿哈装备),狼尊双风暴潮+爻光双鞋
        # 刃(星核猎手):刃+狼尊行动7次→狼尊释放欢愉技。强依赖鞋≥6;尽量不d全力升级;也作绯英早期过渡c
        # ADR-0152 评审🔴(狼尊簇 68 篇对拍):本体刃仅 2/68,千冶·刃 36/68 → core 刃改千冶·刃(V4.4 实战常驻)。
        key_equips=["火力风暴潮", "反重力皮靴", "反重力皮靴", "光速螺旋桨"], mechanic_attributes=["欢愉叠层", "成型羁绊队"],   # 成型羁绊队:欢愉 5-7 档乘区(w878)
        # ↑ v2 教义:银狼=风暴潮+
        #   **速度件**(升费链要行动),皮靴是速度载体;爻光本就是皮靴(攻略:爻光双鞋)
        shared_chars=["爻光", "花火"], transition_chars=["花火", "符玄"], typical_form_round=5,
        # ===== v2:欢愉族家族·银狼档(资源锚 9 级;与绯英档互含单向:银狼局含绯英 76%)=====
        family="欢愉族", branch_key="银狼档(资源锚 9 级;分流判据=升费资源是否到位)", branch_of="绯英欢愉",
        bond_signal="欢愉",   # ②类信号:绯英/银狼两档共用主体
        form_tiers_max={"欢愉": 7},   # v2:欢愉 5-7 档(阿哈装备栏全解锁=指数点)
        # v2:星核 2=笑点泵(银狼每攻 7 次放 40 笑点欢愉技)——本套已列主档 form_tiers(星核猎手2),不入 sub_tiers(不重复);绯英 76% 在场沉淀
        special_systems={
            "aha_slots": {"档位": 7, "语义": "7 人档全解锁后装备=输出,装备数量本身进阵容强度公式"},
            "cost_escalation": {"角色": "银狼LV.999", "起始": "低费(升费链)", "目标费": 5, "备注": "养成路线是阵容定义的一部分,非静态名单"},
        },
        equip_assign={"银狼LV.999": ["火力风暴潮", "反重力皮靴"], "爻光": ["反重力皮靴"], "开拓者·欢愉": ["光速螺旋桨"]},
        # ↑ v2:银狼=风暴潮+速度件(升费链要
        #   行动)。全队永动机群(阿哈装备栏全开后装备=输出)恒等约束下未单列,拆分批放开
        substitute_plan=[
            {"替班者": "绯英", "顶位": "银狼LV.999 主C(银狼 9 级到前)", "身份": "绯英当主 C 直至银狼 9 级到手;到后不卖,降副C沉淀(数据常态 76%)", "分岔点": "银狼 LV.999 到手→家族内转档"},
        ],
        flex_factions=["星间旅人", "战技点", "列车同行"],
        plaza_carry="银狼LV.999",
        # 全局累积型标注:银狼=升费链(cost_escalation)——累积持久(费用档不清零)
        # 但由购买/D 驱动非上场时间,**不适用「有空位就上」部署例外**;仅作类型区分。
        global_accumulators={"银狼LV.999": "cost_escalation"},
        level_plan={  # 评审🟡6:银狼LV.999 3费(升费到5,标3=起始找牌档)
            4: LevelGoal("roll", target_cost=3, target_chars=["银狼LV.999", "爻光"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=3, target_chars=["银狼LV.999"], star_goals={"银狼LV.999": 2}),
        },
    ),
    Comp(
        name="昼神阿雅", factions=["昼之半神"], core_chars=["阿格莱雅", "风堇", "昔涟"],
        form_tiers={"昼之半神": 4}, strength="B", form_difficulty="hard", early_power="低",
        # V4.4 评级(76807134):阿雅 = B 级(试用难玩;需反重力皮靴×2+速度投资,V3.8 最轮椅→V4.4 降 B)。
        # ADR-0152(plaza 8 篇 carry):装备 反重力皮靴×16 断层第一(「有鞋跟本输不了」);阿格莱雅 3星率
        # 0.88;实战板多为 昼神4+量子3/能量+治疗混搭(flex 已收)。强帖(「80连胜焚决」/「小伊卡」)
        # use 均 0 且依赖本体/遗器/充能绳(M11)→ **保持 B**(评审🟡:升 A 依据不足,勿按万敌标准拔高)。
        key_equips=["反重力皮靴", "反重力皮靴", "白昼·光速螺旋桨", "火力风暴潮"],
        countered_by_bosses=["电视机"], mechanic_attributes=["速度依赖", "成型羁绊队"],   # 成型羁绊队(边界套):昼之半神4 主档为战力底盘,速度件是执行载体非战力源(w878 裁注)
        shared_chars=["风堇", "昔涟", "银狼"], transition_chars=["风堇", "艾丝妲", "阿格莱雅"],
        typical_form_round=8,
        family="legacy", branch_key="v2 未单列(长尾保活;昼半并入 DOT·B 速度/昼半流的家族口径待拆分批)",
        flex_factions=["能量", "列车同行", "量子同频", "治疗"],
        plaza_carry="阿格莱雅",
        level_plan={  # 评审🟡6/🟡9:阿格莱雅 1费(旧标2);「速升9找银狼」补 9 级
            5: LevelGoal("roll", target_cost=1, target_chars=["阿格莱雅", "风堇"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=1, target_chars=["阿格莱雅"], star_goals={"阿格莱雅": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["银狼"], star_goals={"阿格莱雅": 3}),
        },
    ),
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/README.md 类索引(游戏知识,非字段镜像,无同步义务)
        char_positions={"知更鸟": "front"},   # 站位:知更鸟前台(追击攻略:鸟前台支撑中后期;砂金/灵砂/符玄等生存位也优先前台)
        name="追击飞霄", factions=["追击"], core_chars=["飞霄", "知更鸟", "那刻夏", "不死途"],
        form_tiers={"追击": 3}, strength="B", form_difficulty="medium", early_power="低",
        # V4.4 合集(76807134)追击 B 级 = 飞霄-led(纯追击);攻略(76883466):飞霄天赋追击永久+6%增伤,≥3追击=300%倍率
        # 飞霄双风暴潮+鸟(3追击关键)+缇宝/不死途/刃;2星飞霄上9(3星锁血反降);追击转→5追击60%真伤
        # ADR-0152 评审🔴(锚点对拍):飞霄 carry 仅 3 篇(<5 不在聚类)→ plaza_carry 置空;plaza 追击族
        # 真代表 = **那刻夏**(「5追击4昼之半神 后台主c之光」6444 use:「没鞋也没追击转别上那刻夏,
        # 至少得有其1」,装备优先级原文全序列)→ 补 core;追击簇 flex 常见 公司/昼之半神/群攻。
        key_equips=["火力风暴潮", "火力风暴潮", "永动机", "电磁弹射器"], mechanic_attributes=["追击", "成型羁绊队"],   # 成型羁绊队:追击档乘区(≥3追击=300%倍率,w878)
        shared_chars=["知更鸟", "缇宝", "不死途", "那刻夏"], transition_chars=["赛飞儿", "风堇", "刃"],
        typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;追击=大黑塔线的降级路径变体)",
        flex_factions=["公司", "群攻", "昼之半神"],
        plaza_carry="",   # 飞霄 carry 3 篇悬空;那刻夏(追击真代表,n=6 恰在聚类边缘)未单列 comp
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["飞霄"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["知更鸟", "不死途"]),
        },
    ),
    Comp(
        name="万敌单C", factions=["夜之半神", "燃血"], core_chars=["万敌", "千冶·刃", "长夜月", "刻律德菈", "缇宝"],
        form_tiers={"夜之半神": 2, "燃血": 4}, strength="A", form_difficulty="medium", early_power="中",
        # 燃血档 = v2 教义「4-6 档」(form_tiers_max=6 不变)。
        #   ⚠️ 行为面:form_progress 成型判定按燃血 4 判(意图内)。
        # V4.4 评级(76807134):万敌 = B 级;【debuff=buff 典型】反伤/AoE/持续伤害 利燃血;攻略(77056698)
        # ↺ ADR-0152(plaza 40 篇校准)B→A:use 榜 #2(11.2w,「万敌无脑单挂A850 7人成型」);3星率 0.93
        # 场最高;5级搜牌 26/40(1费 carry 5 级 D 标准节奏)。**form_tiers 校准(评审🔴4)**:旧 夜4+燃4
        # 仅 15% 帖达标 —— 榜首帖实跑 夜2+燃2(「7人成型」= 万敌+6弹性辅助;另一帖明言「夜神燃血也不
        # 要凑」)→ 降为 2+2(核心=万敌双标签引擎,其余 flex);千冶·刃 40/40 全勤补 core(旧漏)。
        # 遐蝶(n=6)= 同族副 carry(夜神6+燃血6),挂 shared 备转型。
        mechanic_attributes=["燃血"],
        char_positions={"万敌": "front"},   # 站位:万敌独前排(燃血角斗场吃受击掉血;弃1人口换触发密度)
        key_equips=["火力风暴潮", "热血沸腾拳", "绝对热量", "高周波电锯"],   # 评审🟡4:plaza 热血沸腾拳40>绝对热量26 顺序修正(风暴潮54 断层第一)
        countered_by_bosses=["永久创伤"],   # 掉血削上限克燃血(不可玩);利:忍无可忍/正当防卫/灼热轰炸(debuff=buff)
        shared_chars=["风堇", "长夜月", "遐蝶"], transition_chars=["椒丘", "艾丝妲"],   # 长夜月是 core(夜半记录)
        typical_form_round=5,
        # ===== v2:万敌燃血家族(无流派;装备收敛:风暴潮 95%+热血拳 90%)=====
        family="万敌燃血", branch_key="无流派(装备收敛)",
        bond_signal="夜之半神",   # ②类信号:夜半 2(96% 必配,主档)
        form_tiers_max={"燃血": 6},   # v2:燃血 4-6 档;夜之半神 2(96% 必配)=form_tiers 下限口径不变
        sub_tiers={"战技点": 2},   # v2:战技点 2(90%,第三引擎);风堇=第二记录器(治疗转伤害)
        equip_assign={"万敌": ["火力风暴潮", "热血沸腾拳", "绝对热量", "高周波电锯"]},
        # ↑ v2 教义:万敌=风暴潮+热血拳+虫洞掘进钻头(击破体系,不在旧表,拆分批补);绝对热量(唯一件)
        # 给谁=时序决策(前期万敌→后期转移)
        equip_taboos=["护盾件(类)", "以牙还牙甲", "掩体生成枪"],
        # ↑ 教义(官方原文):燃血队员无法获盾,受盾只转 2%+1000 回血=负资产;连带盾类装备全禁
        # 无替班:v2 明言万敌 1 费开局即在(56% 局 P1 板上),无空窗;P2 加深档数
        flex_factions=["群攻", "量子同频", "战技点", "治疗", "命运圣杯", "减益"],
        plaza_carry="万敌",
        # 全局累积型标注:万敌=受击驱动全局叠层(受伤充能+生命上限永久提高,
        # 用户定谒 [21] 例外)——环境满足(敌方多动/反伤类词条)时适用「有空位就上」。
        global_accumulators={"万敌": "hp_charge_stack"},
        level_plan={  # 1费 carry:5 级 D 干 3星(0.93 全场最高);boss 前成型即停
            3: LevelGoal("roll", target_cost=1, target_chars=["万敌"]),
            4: LevelGoal("roll", target_cost=1, target_chars=["万敌"], star_goals={"万敌": 2}),
            5: LevelGoal("roll", target_cost=1, target_chars=["万敌"], star_goals={"万敌": 3}),
            6: LevelGoal("roll", target_cost=2, target_chars=["千冶·刃", "长夜月"]),   # 千冶·刃 2费/长夜月 2费
            7: LevelGoal("level_up"), 8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["万敌", "千冶·刃"],
                         star_goals={"万敌": 3, "千冶·刃": 2}),
        },
    ),
    Comp(
        name="DOT队", factions=["持续伤害", "星核猎手"], core_chars=["卡芙卡", "黑天鹅", "千冶·刃", "海瑟音", "符玄"],
        form_tiers={"持续伤害": 4, "星核猎手": 2}, strength="B", form_difficulty="easy", early_power="低",
        # V4.4 评级(76807134):dot = B 级;攻略(77026641 直读):V4.4 刃加入→卡芙卡回归(刃比普通狼频繁触星核猎手额外战技)
        # 卡芙卡3风暴潮(dot不吃幸运)+黑天鹅(鹅,2dot)+刃(2星核猎手)+刻律(复制战技连动)+鸟;需自己卡芙卡
        # ⚠️ 黄泉减益已拆独立(见上);本 comp=DoT 主派(卡芙卡/鹅/刃/桑博),P1强/P2乏力/P3需转,低费过渡保血权威
        weak_planes=(2,),   # 攻略实证 P2 被抽陀螺(难度攻略:47-48)——保命 pivot P2 不选它
        # ADR-0152(plaza 卡芙卡 11/黑天鹅 11 篇校准):常驻 千冶·刃11/黑天鹅10/符玄9/瓦尔特8/海瑟音7
        # (core 的「刃」改「千冶·刃」+补海瑟音);装备 风暴潮19/反重力皮靴8。
        key_equips=["火力风暴潮", "反重力皮靴", "蓄能帆", "光速螺旋桨"],
        # 慢速:DOT 叠层×引爆磨血胜利条件(final_dot_kafka),冻结族词条的慢热载体(w878)。
        # 成型羁绊队:持续伤害档一路加深(2→4→6)是本线成长乘区(w878)。
        mechanic_attributes=["DoT", "慢速", "成型羁绊队"],
        shared_chars=["桑博", "千冶·刃", "黑天鹅"],
        transition_chars=["桑博", "艾丝妲"], typical_form_round=4,
        # ===== v2:DOT卡芙卡家族·A 引爆流(~47%;B 速度/昼半流未建条,拆分批落位)=====
        family="DOT卡芙卡", branch_key="A 引爆流(~47%;分岔变量=carry×装备×副羁绊)",
        bond_signal="持续伤害",   # ②类信号:开局即战力,前期=终局同体一路加深
        form_tiers_max={"持续伤害": 6},   # v2:DOT 6 档(A 流一路加深 2→4→6)
        sub_tiers={"减益": 2},   # v2:星核 2(57%)已在 form_tiers(星核猎手2);减益 2(43%)
        equip_assign={"卡芙卡": ["火力风暴潮"], "海瑟音": ["反重力皮靴", "光速螺旋桨"], "黑天鹅": ["蓄能帆"]},
        # ↑ v2 教义:主C 位风暴潮最优先(卡芙卡技能原文:携带装备直接提高引爆倍率=全游戏唯一装备焊进
        # 公式的角色);全队铺皮靴
        substitute_plan=[
            {"替班者": "黑天鹅", "顶位": "卡芙卡主C(卡芙卡搜不到时)", "身份": "2★ 鹅卡双C 降级;黑天鹅 9 级后段进板(E0→F22),到前靠档深+卡芙卡升星", "分岔点": "卡芙卡到手"},
        ],
        flex_factions=["减益", "量子同频", "盛会之星", "昼之半神"],
        plaza_carry="卡芙卡",
        level_plan={  # 低费 DoT:P1 快速成型保血
            3: LevelGoal("roll", target_cost=1, target_chars=["桑博"]),
            4: LevelGoal("roll", target_cost=2, target_chars=["卡芙卡", "桑博"], star_goals={"桑博": 2}),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["卡芙卡"], star_goals={"卡芙卡": 2}),
        },
    ),
    Comp(
        # ADR-0152 新增(plaza 补缺):景元仙舟族 —— 景元 carry 16 + 彦卿 14 篇。
        # **augment 强联动**:飞光·映月/传剑(各 8/5 篇,AUGMENT_COMP_AFFINITY 硬绑)—— 彦卿+景元师徒,
        # 拿到飞光 = 1费特殊景元+镜流强化;升星次序经济:「先 3星景元,否则镜流 3星后景元变 5费难刷」。
        name="景元仙舟", factions=["仙舟"], core_chars=["景元", "镜流", "彦卿", "符玄"],
        form_tiers={"仙舟": 5}, strength="B", form_difficulty="medium", early_power="中",
        # plaza:景元 3星率 0.69(5费);7级搜牌 7/16;装备 电锯13/风暴潮12/皮靴6;常驻 符玄13/爻光11/藿藿11
        key_equips=["高周波电锯", "火力风暴潮", "反重力皮靴", "电光履"],
        mechanic_attributes=["召唤追击", "成型羁绊队"],   # 神君:仙舟召唤物计数(12041/12042 变体 id 只计羁绊);成型羁绊队:仙舟5 召唤计数档乘区(w878)
        shared_chars=["符玄", "忘归人", "藿藿"], transition_chars=["藿藿", "丹恒·饮月", "符玄"],
        typical_form_round=7,
        family="legacy", branch_key="v2 未单列(长尾保活;仙舟铁三角=P1 体系卡,非 v2 终局家族)",
        flex_factions=["治疗", "减益", "量子同频", "列车同行", "燃血", "狼狩"],
        plaza_carry="景元",
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["镜流", "忘归人"]),
            6: LevelGoal("level_up"),
            7: LevelGoal("roll", target_cost=5, target_chars=["景元", "镜流"],
                         star_goals={"景元": 2, "镜流": 3}),   # 先景元后镜流(升星次序经济)
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["景元", "彦卿"], star_goals={"景元": 3}),
        },
    ),
    Comp(
        # ADR-0152 新增(plaza 补缺):专家桑博 DOT —— 33.3k use 帖(「专家老桑博,越用越有活」5级搜牌)。
        # **env 定义型**:「开局必须刷专家邀请环境」(特邀专家:桑博)—— ENV_COMP_AFFINITY 近乎硬绑;
        # 无专家 env 时强度降档(退化为 DOT队 territory)。桑博本体贝洛伯格阵营(DoT 输出位)。
        # 节奏:1-6 搜桑博2星 → 2-3 前 3星桑博(装备越早越好)→ 存钱升8 搜海瑟音 → 瓦尔特必上。
        name="专家桑博DOT", factions=["持续伤害", "贝洛伯格"], core_chars=["桑博", "卡芙卡", "千冶·刃"],
        form_tiers={"持续伤害": 4, "贝洛伯格": 2}, strength="B", form_difficulty="easy", early_power="中",
        key_equips=["火力风暴潮", "火力风暴潮", "冷笑话引擎"],   # 桑博装备越早越好;卡芙卡过渡给随便骰子
        # 慢速:DOT 磨血(桑博 DoT 越早越好,同 final_dot_kafka 磨血胜利条件,w878)。
        # 成型羁绊队:持续伤害档乘区(w878)。
        mechanic_attributes=["DoT", "慢速", "成型羁绊队"],
        shared_chars=["卡芙卡", "海瑟音", "千冶·刃"], transition_chars=["卡芙卡", "艾丝妲"],
        typical_form_round=5,
        # ===== v2:DOT卡芙卡家族·桑博专家变体(v2 明言:策略入口变体,不独立成套)=====
        family="DOT卡芙卡", branch_key="桑博专家变体(开局信号=「特邀专家:桑博」portal,C 槽换桑博+靴流;策略入口变体非兄弟分支,不设 branch_of)",
        bond_signal="持续伤害",   # ②类信号:开局即战力,前期=终局同体一路加深
        equip_assign={"桑博": ["火力风暴潮", "火力风暴潮"], "卡芙卡": ["冷笑话引擎"]},
        # ↑ 桑博装备越早越好;卡芙卡过渡给随便骰子
        flex_factions=["星核猎手", "减益", "昼之半神"],
        plaza_carry="",   # 桑博 carry 聚类 n<5(33k use 单帖在,样本量不够成簇)
        level_plan={
            3: LevelGoal("roll", target_cost=1, target_chars=["桑博"]),
            4: LevelGoal("roll", target_cost=1, target_chars=["桑博"], star_goals={"桑博": 2}),
            5: LevelGoal("roll", target_cost=1, target_chars=["桑博"], star_goals={"桑博": 3}),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=0, target_chars=["卡芙卡", "海瑟音", "瓦尔特"]),
        },
    ),
]


def get_comp(name: str) -> Comp | None:
    """按名取 Comp;无则 None。"""
    for c in COMP_LIBRARY:
        if c.name == name:
            return c
    return None


def hp_charge_stack_chars() -> frozenset[str]:
    """``hp_charge_stack`` 型全局累积角色名全集(标注派生,单一源)。

    消费点 = decision_v2.phase 兜底门豁免(ADR-0353):该型角色(万敌:受伤
    充能+生命上限永久提高)的累积由**场上事件**驱动,上场即真实累积战力,
    与过渡体系同格;``cost_escalation`` 型(银狼)累积由购买驱动,不在此集
    (Comp.global_accumulators 字段 docstring 明示其不适用部署类例外)。
    """
    return frozenset(
        char
        for c in COMP_LIBRARY
        for char, acc in (c.global_accumulators or {}).items()
        if acc == 'hp_charge_stack'
    )


def candidate_faction_universe(evicted: frozenset[str] | set[str] = frozenset(),
                               ) -> frozenset[str]:
    """候选终局阵容阵营全集 = ⋃ comp.factions(COMP_LIBRARY 派生,阵营维单一源)。

    消费点 = decide_event env 分支候选全集门(faction 非空的投资环境,faction ∉
    本全集即失格,增益无消费方)。**阵营维全集 = 环境门与策略卡门共用的同一台
    机器**——消费方只许 import 本函数,禁在门位二次建模;角色维两问不同答案
    (环境送卡型看 core∪shared,策略对齐只数 core),分立镜像函数、禁共用本函数。

    语义边界(用户裁定 2026-09-12「我们有对应的终局阵容定义,才选对应的投资
    环境」):
    - 只收 ``factions``(核心羁绊);``flex_factions`` 不入——弹性羁绊是阵容
      能临时吃的,不是可能玩的方向;
    - ``evicted`` 与 D*② 同源同义(「等同信号未发生」的 comp 名集合,
      decide_invest 从意向状态直通,零接口新增)→ 阵容被 evicted 后其独占
      阵容自动退出全集(动态收窄免费获得);
    - 全集覆盖质量责任在 COMP_LIBRARY 手判层(终局阵容研究的派生),因研究
      遗漏错杀的修正路径 = 修库,不是放松门;漂移防线 = 测试仓
      test_cw_env_universe.py 模块头全集核对断言(改库先红,重核全集咬合面)。
    """
    return frozenset(
        f
        for c in COMP_LIBRARY
        if c.name not in evicted
        for f in c.factions
    )


def candidate_char_universe(evicted: frozenset[str] | set[str] = frozenset(),
                            ) -> frozenset[str]:
    """候选终局阵容角色全集 = ⋃ (core_chars ∪ shared_chars)(COMP_LIBRARY 派生,角色维单一源)。

    消费点 = 送卡型环境判据的成员机器(所赠角色是否被候选终局阵容使用;与阵营维
    全集门 ``candidate_faction_universe`` 完全同构——「送卡没人用 = 纯浪费」是
    「加成阵营没人用 = 纯浪费」在角色粒度的镜像,2026-09-12 invest-env 迭代,
    details/env-value-models.md §2.1.2)。

    ⚠️ 跨迭代单一源边界(design.md §1.3-2 跨迭代契约):角色维两问不同答案、
    分立双函数禁共用——本函数 = core∪shared(送卡型:shared 也是终局成员,
    char_routes 同口径);策略对齐门 ``candidate_core_char_universe`` = core-only
    (兄弟迭代 2026-09-12-strategy-universe-gate S3:对齐角色维只数 core)。

    - ``evicted`` 与阵营维全集门同源同义(``decide_event`` 现有参数直通,零接口
      新增)→ 阵容被排除后其独占角色自动退出全集(动态收窄免费获得);
    - ``transition_chars`` 不入集(打工后卖,不构成路线,char_routes 注释同源);
    - 单帧单读纪律同 D* 快照:消费支(送卡档 max() 支)在循环外取一次快照,
      循环内复用,禁每候选重派生。
    """
    return frozenset(
        ch
        for c in COMP_LIBRARY
        if c.name not in evicted
        for ch in set(c.core_chars) | set(c.shared_chars)
    )


# ===== 送卡型档位阶梯(定序机器,零数值;details/env-value-models.md §2.1.2)=====
# 档 = 角色在候选套中的身份,高→低 core/shared/transition/off;_GIFT_TIER_DOWN =
# 条件降档链(规则 3:兑现概率 <1 且行为依赖,定序上只给弱一档的确定性)。
_GIFT_TIER_RANK: dict[str, int] = {'off': 0, 'transition': 1, 'shared': 2, 'core': 3}
_GIFT_TIER_DOWN: dict[str, str] = {
    'core': 'shared', 'shared': 'transition', 'transition': 'off', 'off': 'off',
}


def _char_gift_tier(char: str, evicted: frozenset[str] | set[str]) -> str:
    """单张赠卡在候选套中的最高身份档('off' = 三名单皆不在)。

    同名角色跨套身份取最高(卡芙卡 = 千冶减益/DOT队/专家桑博DOT core ×3,
    专家桑博DOT 亦列其 shared/transition——core 恒压过,与详设分档表口径一致)。
    """
    best, rank = 'off', 0
    for comp in COMP_LIBRARY:
        if comp.name in evicted:
            continue
        for names, tier in ((comp.core_chars, 'core'),
                            (comp.shared_chars, 'shared'),
                            (comp.transition_chars, 'transition')):
            if char in names and _GIFT_TIER_RANK[tier] > rank:
                best, rank = tier, _GIFT_TIER_RANK[tier]
                if rank == _GIFT_TIER_RANK['core']:
                    return best   # core 为最高档,无需继续扫
    return best


def gift_hit_tier(grant: GiftGrant, evicted: frozenset[str] | set[str] = frozenset(),
                  ) -> str:
    """送卡型环境 GiftGrant 的命中档('core'|'shared'|'transition'|'off')。

    实现详设三规则(全部定序,零数值;details/env-value-models.md §2.1.2):
    ① 即时优先——即时集非空取其最优档,不看条件集(确定性赠卡是估值承重面);
    ② 条件降档——即时集为空取条件集最优档降一档(core→shared→transition→off);
    ③ advisor 族切换由调用方做(同一套档位判定,floor 族 G/A 之差见
    ``cw_investments.GIFT_FLOOR_*`` 锚点注;本函数不读 advisor)。

    消费契约(3.5 阶段 cw_events env 分支送卡档 max() 支按此映射,禁二次推导):
    - tier=='off' ∧ 非 advisor ∧ chars_immediate 非空 → 失格 0(归因
      env-gift-off-universe;白得卡全员三名单皆不在 = 纯浪费,全集门同款失格);
    - tier=='core'/'shared' ∧ 非 advisor → max(score, GIFT_FLOOR_CORE/SHARED);
    - tier=='core' ∧ advisor → max(score, GIFT_FLOOR_ADVISOR_CORE);
    - 其余(advisor 的 shared/transition/off、条件降档后非 core/shared)→ 无 floor
      维持裸分(顾问是购买选项,off 只是不买、无浪费;条件发放未到手,同上)。
    当前注册表下 11 条无一触发失格(逐条直调核验 = 详设 §2.1.1/§2.1.2 表;
    门是 COMP_LIBRARY 演化时的结构性保障,不是现修行为)。

    evicted 传导免费获得:候选套收窄 → 档随之下调或失格(详设 §2.1.4-5 直调例:
    持续伤害契约排除三 DOT 套 → 椒丘落 transition → 裸分维持,失格门不咬
    transition 命中;宿主套再被排除才整条 'off')。
    """
    if grant.chars_immediate:
        return max((_char_gift_tier(ch, evicted) for ch in grant.chars_immediate),
                   key=_GIFT_TIER_RANK.__getitem__)
    if not grant.chars_conditional:
        return 'off'
    cond_best = max((_char_gift_tier(ch, evicted)
                     for ch, _note in grant.chars_conditional),
                    key=_GIFT_TIER_RANK.__getitem__)
    return _GIFT_TIER_DOWN[cond_best]


# ===== 评分 helper(comp 相关)=====

def _owned_chars(bs: GameState) -> set[str]:
    """已持有的角色名集合(bench + deployed)。"""
    return {bc.char_id for bc in (*bench_slots_of(bs), *deployed_slots_of(bs))
            if bc is not None and bc.char_id}


def form_progress(comp: Comp, bs: GameState) -> float:
    """成型度 0..1:各核心阵营 tier 进度的均值(min(board,form_tiers)/form_tiers)。

    10 的 helper(comp_viability 先验用);纯阵营 tier,不含角色(避免与 char_quality 三重计分)。
    入参 = 容器视图(W6 决策面切统一容器;假想面板轻量桩只需提供
    ``board.value`` 属性,见调用点 _deploy_advances_form 鸭型位)。

    OR 腿与 carry 条件折法(T-171 批序 1,ADR-0613;OR 组承接键,ADR-0621;
    本函数 = 成型判据唯一折法,fp=1.0 ⟺ 成型谓词「form_tiers 未被承接档
    全档 ∧ or_legs 组任一满 ∧ required_deployed 全在板」的单一源契约):
    - ``or_legs`` 非空 → 折为**一条**虚拟腿,腿值 = 组内各腿进度的 max
      (「凑到任一=成型」的进度语义;半成品如 量1∨贝1 如实给 0.5,取
      最好腿非均值);
    - **承接规则**(ADR-0621):``form_tiers`` 中与 OR 腿**同键**的档位
      不计入 AND 账(该键的成型语义归 OR 组,分子分母同免——静态套
      希儿量子 form_tiers={量4,贝2} 全被 ``SEELE_OR_LEGS`` 承接,成型
      判据即文档 OR 口径;pair 伪 comp 两键集恒不相交,本规则对其逐位
      零差)。档位值保留的用途见 ``Comp.or_legs`` 注;
    - ``required_deployed`` 逐名折一条 0/1 虚拟腿(在板=1;入参无
      deployed 视图(轻量假想面板)按 0 计 = 保守向,缺读≠满成)。
    两字段经 ``getattr`` 缺省空读(真实 Comp 恒有字段;测试鸭型桩与
    旧序列化载体两态按「无 OR/carry 条件」解释,与空字段同值,不炸)。
    两字段缺省空(全注册表 comp)逐位同旧式均值。禁消费位绕过本函数
    自写 min(board,tier)≥tier 内联成型判定(判据双源;内联位清单与
    取代声明见 ADR-0613)。
    """
    if (not comp.form_tiers
            and not getattr(comp, 'or_legs', None)
            and not getattr(comp, 'required_deployed', None)):
        return 0.0
    or_legs = getattr(comp, 'or_legs', None) or []
    or_owned = {f for f, _t in or_legs}   # OR 组承接键(同键档位免 AND 账)
    _board = getattr(bs, 'board', None)
    board = getattr(_board, 'value', None) or {}
    total = 0.0
    n = 0
    for f, tier in comp.form_tiers.items():
        if tier <= 0 or f in or_owned:
            continue
        total += min(board.get(f, 0), tier) / tier
        n += 1
    if or_legs:
        best = 0.0
        for f, tier in or_legs:
            if tier <= 0:
                continue
            best = max(best, min(board.get(f, 0), tier) / tier)
        total += best
        n += 1
    required = getattr(comp, 'required_deployed', None) or ()
    if required:
        # 席位经容器行读(无该属性 = 轻量假想面板,按 0 计保守向)
        _front = getattr(getattr(bs, 'front_row', None), 'value', None)
        _back = getattr(getattr(bs, 'back_row', None), 'value', None)
        deployed_names = {
            u.char_id
            for u in (*(_front or ()), *(_back or ()))
            if u is not None and getattr(u, 'char_id', None)}
        for name in comp.required_deployed:
            total += 1.0 if name in deployed_names else 0.0
            n += 1
    if n == 0:
        return 0.0
    return clamp(total / n, 0.0, 1.0)


def progress(comp: Comp, bs: GameState) -> float:
    """comp_score 用:0.6 阵营 tier 进度 + 0.4 核心角色持有(归一化 0..1)。

    与 form_progress 区别:progress 加了 core_char 持有项(选 target 时评估契合用);
    eval 驱动买牌用 target_progress(只度量剩余进度)。
    """
    fp = form_progress(comp, bs)
    owned = _owned_chars(bs)
    core_frac = (sum(1 for c in comp.core_chars if c in owned) / len(comp.core_chars)) if comp.core_chars else 0.0
    return clamp(0.6 * fp + 0.4 * core_frac, 0.0, 1.0)


def shop_supply(comp: Comp, bs: GameState) -> float:
    """comp 核心阵营的**本回合** shop 可得性 [0,1](shop-aware)。

    现仅用于 **drought bail 判定**(连续 N 回合 supply<1.0 → 弃不可达 target 重选;default 栈 drought bail 已退役,本函数保留为挂账层消费面),
    **不再驱动 select_comp**(ADR-0092:select_comp 改用理论 acquirability_factor,刷新独立 → 观察/单回合
    shop 无预测力)。保留本函数因 drought 需「本回合 shop 是否供得上核心」的实时观察。

    - 阵营在 **shop(本回合可买)** 出现 → **1.0**(本回合买得到核心牌 → drought 归 0)。
    - 仅 **board** 有、shop 无 → **0.3**(已持 1 张但本回合买不到更多 → 成型难,弱信号;非 1.0)。
    - 都无 → **0.0**(本回合刷不出 → 不可成型,累积 drought)。

    语义:shop presence 主导,board-only 为弱信号(0.3)——「board 已有 1 张 ≠ 能成型,
    要 shop 供得上核心」(若 board 有 1 张就返 1.0,会选上 shop 供不上、永不成型的 target)。
    ⚠️ **空 shop(无商店相位:奖励关/事件/战斗后无备战)≠ 断供** ——
    无观测时返回 1.0 中性值(drought 不涨不归);若空 shop 也给弱信号,
    奖励关会白涨 drought,把断供轮数记错。判据:
    ``state.shop`` 为空列表 = 本回合无商店相位(商店开态必有 5 张,空 = 没到相位)。
    """
    if not comp.factions:
        return 1.0
    _payload = bs.shop.value
    shop_cards = shop_payload_content_cards(_payload)
    if not shop_cards:
        return 1.0   # 无商店相位(奖励关/事件节点)——无观测≠断供,drought 中性
    shop_factions = {c.faction for c in shop_cards}
    # 核心阵营(form_tiers)优先:非核心阵营在 shop 不算「供得上核心」(否则 drought 误归 0,漏掉不可达 target)。
    core = set(comp.form_tiers.keys()) if comp.form_tiers else set(comp.factions)
    if any(f in shop_factions for f in core):
        return 1.0
    if any(f in shop_factions for f in comp.factions):
        return 0.5   # 仅非核心阵营在 shop → 半信号
    board = getattr(bs, 'board', None)
    board_factions = set((getattr(board, 'value', None) or {}).keys())
    if any(f in board_factions for f in comp.factions):
        return 0.3   # 仅 board 有,shop 买不到更多 → 弱成型信号
    return 0.0


def equip_fit(comp: Comp, bs: GameState) -> float | None:
    """装备契合度(comp 相关,0..1):持有 comp.key_equips 越多越高(超线性 ^0.7 奖励集齐)。

    ⚠️ comp 驱动(用户):不设通用 equip_score,一切从 target_comp.key_equips 出发。
    key_equips 可含重复(阿雅需 2 反重力皮靴)→ 按 multiplicity 匹配持有数。
    无装备数据(容器 equips 域空)/ comp 无关键装备 → **None**(动态权重:无数据不进加权,
    权重重分配给有数据项,治死重常量地板)。
    """
    equips = list(bs.equips.value or [])
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


def mechanics_fit(comp: Comp, mechanics: set[str],
                  registry: DecisionV2Registry | None = None) -> float | None:
    """机制契合(comp 相关,双向 0..1):命中 counter(克这 comp)→ 降;命中 synergy(利这 comp)→ 升。

    ⚠️ comp 驱动(用户 debuff=buff):同一词缀对不同 comp 方向相反。经 comp.mechanic_attributes
    查全局 MECHANIC_COUNTERS/SYNERGIES 判(数据驱动,comp 不必逐词缀列举;W875 补全包
    子集经 merged_mechanic_tables 按开关并表,全关=基表零漂移;W878 复活包 tag 载体经
    effective_mechanic_attributes 按开关滤除,全关=原属性集零漂移)。
    无机制信息(无敌人词缀 / comp 无生效机械属性)→ **None**(动态权重剔除,治死重)。
    典型:万敌[燃血] + 反伤 → synergy 升(debuff=buff);阿雅[速度依赖] + 禁速 → counter 降。
    """
    eff_attrs = effective_mechanic_attributes(comp, registry)
    if not mechanics or not eff_attrs:
        return None
    _, counters, synergies = merged_mechanic_tables(registry)
    score = 0.5
    for mech in mechanics:
        countered_attrs = counters.get(mech, [])
        synergy_attrs = synergies.get(mech, [])
        n_counter = sum(1 for a in eff_attrs if a in countered_attrs)
        n_synergy = sum(1 for a in eff_attrs if a in synergy_attrs)
        score -= 0.25 * n_counter    # 每命中一个 counter 降 0.25
        score += 0.20 * n_synergy    # 每命中一个 synergy 升 0.20(debuff=buff 利好)
    return clamp(score, 0.0, 1.0)


def boss_fit(comp: Comp, bosses: list[str | None]) -> float | None:
    """boss 克制(boss 名维度):命中 comp.countered_by_bosses → 降。

    无 boss 信息 / comp 无 countered_by_bosses → **None**(动态权重剔除,治死重)。
    有 boss + comp 有 countered_by_bosses 但未命中 → 0.5(真实中性:boss 在但不利害此 comp,有数据)。

    **俗称归一注册表接通**:①俗称归一(BOSS_NICKNAMES:剧目→造梦兄弟影业等,
    修名字空间错位 —— 旧 countered_by_bosses 用俗称 vs plane_bosses 规范名,永命中不了,
    task#73 遗留);②comp 无 countered_by_bosses 但有 mechanic_attributes → 退
    ``cw_enemy_data.matchup`` 结构层(boss 机制 tag × comp 属性,可解释 reasons;
    无此兜底时 20 boss 里 16 个无 countered 数据的 comp 恒 None)。
    """
    if not bosses:
        return None
    from sr_od.application.currency_war.data.cw_enemy_data import (
        matchup,
        normalize_boss_name,
    )
    # None 项 = 该位面徽章态采不到身份(ADR-0398,保位列表)→ 跳过;
    # 全 None(无任何身份信息)→ 与空表同形返 None(动态权重剔除)。
    canon = [normalize_boss_name(b) for b in bosses if b]
    if not canon:
        return None
    if comp.countered_by_bosses:
        n_hit = sum(1 for b in comp.countered_by_bosses if normalize_boss_name(b) in canon)
        return clamp(0.5 - 0.5 * n_hit, 0.0, 1.0) if n_hit else 0.5
    if comp.mechanic_attributes:
        score, _reasons = matchup(comp.mechanic_attributes, canon)
        return score
    return None


def held_strategy_fit(comp: Comp, active_strategies: list[str]) -> float | None:
    """**已持有策略**契合(机会型 pivot 核心;用户「拿到适配策略主动转阵容」)。

    每张持有策略的绑定(``strategy_bindings``,ADR-0134 派生)∩ comp(阵营/core 角色)命中 → 该策略
    对此 comp 加成。归一 0..1:0.5 中性(无策略/无命中),每命中 +0.25 封顶 1.0(星徽套组双命中
    = 三件套到手 → 1.0 满分,comp_score 显著抬 → select_comp/方向重估自然转向)。
    **augment 定义型 comp(ADR-0152)**:命中 ``AUGMENT_COMP_AFFINITY``(黑塔纪元/飞光等)按亲和
    覆盖计分(0.5 + 0.5×affinity)—— 拿到黑塔纪元对大黑塔 comp 即 1.0,近乎硬绑(env_fit 同款语义)。
    无持有策略 → None(动态权重剔除,与 env_fit 同语义)。
    与 env_fit 的分工:env = 开局定向(选环境时 comp 未定);本函数 = **局中机会**(策略到手后
    重评 comp,把「牌找阵容」反转成「阵容追牌」)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        get_strategy,
        strategy_bindings,
    )
    if not active_strategies:
        return None
    hits = 0
    best_affinity = 0.0
    for name in active_strategies:
        aff = augment_affinity(name).get(comp.name, 0.0)
        best_affinity = max(best_affinity, aff)
        s = get_strategy(name)
        if s is None:
            continue
        fs, cs = strategy_bindings(s)
        hits += len((fs & comp.all_factions) | (cs & set(comp.core_chars)))
    # ADR-0152 评审🟡:两路取 max 非覆盖 —— 定义型 affinity(0.5+0.5a)与绑定命中(0.5+0.25h)
    # 各自度量不同机会(方向定义 vs 成型加速),同策略双高时取大者不丢分;无命中无 affinity = 真实中性。
    hits_score = clamp(0.5 + 0.25 * hits, 0.0, 1.0) if hits > 0 else 0.5
    if best_affinity > 0:
        return max(clamp(0.5 + 0.5 * best_affinity, 0.0, 1.0), hits_score)
    return hits_score


def env_fit(comp: Comp, env: str) -> float | None:
    """投资环境契合:① T0 env 近乎硬绑(P1-2 ENV_COMP_AFFINITY);② env 加成对应阵营(R2-9)。

    未选投资环境(env 空)→ **None**(动态权重剔除,治死重)。env 已选但不加成此 comp → 0.5
    (真实中性:env 在但不利好此 comp,有数据)。
    ⚠️ ADR-0152 评审🔴2(T0 定向优先):env 在 affinity 表内时**非定向 comp 一律中性 0.5,不走
    faction 匹配** —— 否则 flex 全集匹配 1.0 盖过定向 0.9/0.95(实测反转:仙舟概念股下绯英欢愉
    [flex含仙舟] 1.0 > 景元仙舟 0.95)。定向 env 的 faction 加成只服务**单位获取**(送卡/刷新率),
    不改 comp 方向;非定向 env(无 affinity 条目的)才走 faction 亲和。
    """
    if not env:
        return None
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    env = normalize_invest_name(env)   # OCR 间隔号形变归一(如 •→·),run_20260826_004527 同型
    # P1-2: T0 env 近乎硬绑某 comp
    if env in ENV_COMP_AFFINITY:
        affinity = ENV_COMP_AFFINITY[env].get(comp.name, 0.0)
        if affinity > 0:
            return clamp(0.5 + 0.5 * affinity, 0.0, 1.0)
        return 0.5   # T0 定向 env:非定向 comp 中性(防 flex 反转)
    # R2-9: env 加成对应阵营(ADR-0152:弹性羁绊也吃 env 亲和 —— 姬子·启行减益流吃减益 env)
    boosted = ENV_FACTION_MAP.get(env, [])
    if boosted and any(f in comp.all_factions for f in boosted):
        return 1.0
    return 0.5


def strength_base(comp: Comp) -> float:
    """research meta 强度先验:{S:1.0, A:0.7, B:0.4}。"""
    return {"S": 1.0, "A": 0.7, "B": 0.4}.get(comp.strength, 0.5)


def current_enemy_mechanics(bs: GameState,
                            registry: DecisionV2Registry | None = None) -> set[str]:
    """当前敌人机制 tag 集合(从容器 enemy_affixes 域经 AFFIX_MECHANIC_MAP 映射;未知词缀原样透传;
    W875 补全包词缀经 merged_mechanic_tables 按开关并表,全关=基表零漂移)。"""
    affix_map, _, _ = merged_mechanic_tables(registry)
    return {affix_map.get(a, a) for a in (bs.enemy_affixes.value or [])}


def make_score_context(bs: GameState, bosses: list[str] | None = None) -> ScoreContext:
    """从容器视图快速构造 ScoreContext(常用入口)。bosses 由外部 OCR 传入。"""
    return ScoreContext(
        bosses=bosses or list(bs.plane_bosses.value or []),
        mechanics=current_enemy_mechanics(bs),
        env=(bs.active_env.value or ''),
        held_strategies=list(bs.active_strategies.value or []),   # 机会型 pivot(选完策略后方向重估)
        plane=plane_of(bs), round_num=round_num_of(bs), gold=gold_of(bs),
    )


# ===== comp_score(候选 comp 综合分)=====
# 权重 = 各维度**importance 先验**(V4.4 research meta 校准;归一化 sum=1.0)。开发者阶段 6 手调(内部)。
# 2026-08-04 实跑校准:W_PROG 0.35→0.45 / W_STR 0.10→0.05 / W_MECH 0.20→0.15。
# 根因:select_comp 卡在无 progress 的高 strength comp(列车同行 S=1.0),但商店没刷其牌 → 不收敛、
# 超长战斗。提 W_PROG 让 select_comp 偏好**可成型**(board 已有 progress,如 万敌 燃血:1)comp 而非
# 高强度不可成型。算账:万敌(progress0.125,str0.4) vs 列车同行(prog0,str1.0),旧 0.084<0.1(列车同行赢);
# 新 0.45*0.125+0.05*0.4=0.076 > 0.45*0+0.05*1.0=0.05(万敌赢)= 选可成型。
#
# 动态权重(治本 review#5 死重):权重不再因「数据未接通」而失效 —— *_fit 无数据返 None,
# weighted_mean 剔除 None 项 + 权重重分配给有数据项。故 W_BOSS 复位 0.10(早期暂置 0 的 stopgap
# 不再需要:boss 无数据时 boss_fit 返 None → 自动剔除,不再贡献死重常量;数据接通即生效)。
W_PROG: float = 0.45    # 成型进度(form + core_char)—— 偏好可成型 comp
W_MECH: float = 0.15    # 机制契合(双向 debuff=buff)
W_ENV: float = 0.15     # 投资环境契合
W_HELD: float = 0.15    # 已持有策略契合(机会型 pivot;无持有 → None 动态剔除,权重重分配)
W_BOSS: float = 0.10    # boss 克制(无数据 → boss_fit 返 None → 动态剔除;countered_by_bosses 接通即生效)
W_EQUIP: float = 0.10   # 装备契合(comp 相关)
W_STR: float = 0.05     # research meta 强度


def weighted_mean(items: list[tuple[float, float | None]]) -> float:
    """动态加权平均:None 项(无数据)剔除,权重重分配给有数据项。

    治本(review#5):消除 *_fit 无数据返 0.5 的「常量地板」—— 全 comp 同值的项不区分却仍占权重,
    挤压 progress/strength 区分力(dead weight)。None 项不进加权 → 有数据项有效权重升 → 区分力恢复。
    全 None → 0.0(理论上不会:comp_score 的 progress/strength、comp_viability 的 form/star 恒有数据)。
    """
    valid = [(w, v) for w, v in items if v is not None]
    total_w = sum(w for w, _ in valid)
    if total_w <= 0:
        return 0.0
    return sum(w * v for w, v in valid) / total_w


def comp_score(comp: Comp, bs: GameState, ctx: ScoreContext) -> float:
    """候选 comp 综合分(select_comp 评分 candidate 用;无观测项 —— 未 commit 的 candidate 无观测)。

    多维度 comp 相关(用户:一切挂钩目标阵容):成型进度 + 机制双向 + 环境 + boss + 装备 + 强度。
    动态归一:*_fit 无数据返 None → 该项剔除、权重重分配(治死重常量地板)。
    评 **current 已 commit** comp 用 cw_performance.comp_viability(加观测 blend),不用本函数。
    """
    return weighted_mean([
        (W_PROG, progress(comp, bs)),
        (W_MECH, mechanics_fit(comp, ctx.mechanics)),
        (W_ENV, env_fit(comp, ctx.env)),
        (W_HELD, held_strategy_fit(comp, ctx.held_strategies)),
        (W_BOSS, boss_fit(comp, ctx.bosses)),
        (W_EQUIP, equip_fit(comp, bs)),
        (W_STR, strength_base(comp)),
    ])


# 用户转向轴(README A / develop config.md §3):优先/禁止/build_around。getattr 防御读取(mock/旧 yml 缺字段安全)。

def _passes_steering(comp: Comp, config) -> bool:
    """用户 steer 硬过滤:build_around 必含、forbid 必不含。不满足 → 排除出候选。

    - character_build_around:any() 语义(围绕我的任一强角色);
    - faction_build_around:all() 语义(成就局要求指定阵容全在场,如 8减益 → ['减益'],
      多羁绊成就列多个 = 全部必含)。
    """
    build_around = getattr(config, 'character_build_around', []) or []
    if build_around and not any(c in comp.core_chars for c in build_around):
        return False
    faction_build = getattr(config, 'faction_build_around', []) or []
    if faction_build and not set(faction_build).issubset(comp.all_factions):
        return False
    char_forbid = getattr(config, 'character_forbid', []) or []
    if any(c in comp.core_chars for c in char_forbid):
        return False
    faction_forbid = getattr(config, 'faction_forbid', []) or []
    return not any(f in comp.all_factions for f in faction_forbid)


def _priority_boost(comp: Comp, config) -> float:
    """用户 steer 软加权:命中 priority 角色/阵营 → 加分(tiebreak 偏向用户偏好)。"""
    boost = 0.0
    char_pri = getattr(config, 'character_priority', []) or []
    for c in comp.core_chars:
        if c in char_pri:
            boost += 0.05 * (len(char_pri) - char_pri.index(c)) / max(len(char_pri), 1)
    faction_pri = getattr(config, 'faction_priority', []) or []
    for f in comp.all_factions:
        if f in faction_pri:
            boost += 0.05 * (len(faction_pri) - faction_pri.index(f)) / max(len(faction_pri), 1)
    return boost


def _difficulty_phase_factor(comp: Comp, bs: GameState) -> float:
    """阶段感知因子(用户:成型难度 + 早期战力都是关键维度):早期/穷 → 偏 easy 成型 + early_power 高。

    早期偏 easy **且** early_power 高,避免选易成型但早期弱的 comp
    (反例:DOT队 easy 但 DoT 慢热,plane1 弱)。先验待实玩校准(多局验证)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import NODES_PER_PLANE
    early = (round_num_of(bs) + (plane_of(bs) - 1) * NODES_PER_PLANE) <= 3 or gold_of(bs) < 30   # 全局 elapsed 判早期(60-A1 ×6→单一源)
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


def _board_alignment(comp: Comp, bs: GameState) -> float:
    """board-alignment boost(CW deployed-lock → 选 board 支持的 comp)。

    comp 阵营在 board 有 count≥2(deep-stack)→ ×1.2;全不在 board → ×0.3(deployed-lock 下不可成型,
    重 penalty:轻罚压不过 acq 0.15-1.0 主导 → spread;×0.3 让 board 支持主导选 comp);
    count≥1 → ×1.0(中性)。**robust to board OCR 噪声**:count≥1 判 has_any 可靠;count≥2 bonus 非 penalty。
    """
    if not comp.factions:
        return 1.0
    board = bs.board.value or {}
    factions = comp.all_factions   # ADR-0152:弹性羁绊铺板不算 off-target(核心+弹性任一在板即支持)
    if any(board.get(f, 0) >= 2 for f in factions):
        return 1.2   # deep-stack → boost
    if not board:
        return 1.0   # 空板 = 无部署证据 → 不罚(罚的前提是 deployed-lock 有错配证据;
        # 无证据惩罚会只打到 factions 非空的 comp —— 反甲白厄(factions 空,
        # 故意设计)躲过 → 早期选择被数据伪影抬轿,机会型 pivot 也被它压死)
    if not any(board.get(f, 0) >= 1 for f in factions):
        return 0.3   # 全不在 board(板有单位)→ 重 penalty(轻罚压不过 acq 主导)
    return 1.0


def _held_base_copies(bs: GameState) -> dict[str, int]:
    """玩家持有的每角色**基础副本数**(牌池消耗 j;ADR-0110 acq 牌池感知用)。

    bench + deployed 各单位按 star 折基础副本(3合1:1星=1 / 2星=3 / 3星=9 / 4星=27 张基础副本)。
    持有越多 → 牌池剩余该角色越少 → 越难再刷(牌库有限,用户根因)。
    state.bench/deployed 由 session.tracked_* seed(带 char_id+star;shop.py:185);空(首轮/无身份)→ {}。
    """
    counts: dict[str, int] = {}
    bench = bench_slots_of(bs)
    deployed = deployed_slots_of(bs)
    for bc in (*bench, *deployed):
        if bc is None:
            continue   # ADR-0316 bench 槽位表空槽
        cid = getattr(bc, 'char_id', None)
        if not cid:
            continue
        star = max(getattr(bc, 'star', 1), 1)
        counts[cid] = counts.get(cid, 0) + 3 ** (star - 1)
    return counts


def select_comp(bs: GameState, ctx: ScoreContext, config,
                top_n: int = 1) -> list[Comp]:
    """按 comp_score 选 target(分数降序,返回 top_n)。

    评分 = comp_score(多维)+ 用户 4 轴 steer(硬过滤 build_around/forbid + 软加权 priority)
    + 阶段成型难度因子(早期偏 easy)。optionality 时传 top_n=2-3 备选几套(P1-1:核心来了再 commit)。
    """
    return [c for _s, c in select_comp_scored(bs, ctx, config, top_n=top_n)]


def select_comp_scored(bs: GameState, ctx: ScoreContext, config,
                       top_n: int = 1) -> list[tuple[float, Comp]]:
    """``select_comp`` 的带分版(遥测要**实际排序分**——含 steer/acq/
    board_alignment 等乘子的最终分,非裸 comp_score;close_call 分差分析量纲对齐)。

    返回 ``[(final_score, Comp)]`` 降序;top_n 截断。排序逻辑与 select_comp 完全
    同源(单一实现,select_comp 是本函数的投影)。
    """
    held = _held_base_copies(bs)   # ADR-0110:acq 扣玩家持有副本(牌池有限)
    # 持有策略**绑定授予**的角色(星徽套组「获得1个【X】」)计入持有副本 —— 送卡 = 已持有,
    # acq 不按全牌池低估(机会型 pivot 的 acq 解锁;仅对本 comp 核心生效,他 comp 不吃这份加成)。
    _granted: dict[str, int] = {}
    from sr_od.application.currency_war.kernel.cw_investments import (
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
        s = comp_score(comp, bs, ctx) + _priority_boost(comp, config)
        s *= _difficulty_phase_factor(comp, bs)
        # 成型加速乘子:持有策略双命中(fit=1.0,套组三件套到手)→ ×1.25(期望成型提前一档);
        # 中性 0.5 → ×1.0(不加不减)。加性 W_HELD 会被 acq/难度乘子稀释,乘子保证机会信号不被淹没。
        _hf = held_strategy_fit(comp, ctx.held_strategies)
        s *= 1.0 + 0.4 * ((_hf if _hf is not None else 0.5) - 0.5) * 2
        # acquirability(ADR-0110 牌池感知):P(单次刷新≥1 张该角色),扣玩家持有副本(牌库有限,用户根因)。
        # acq 收窄口径:0.5+0.5·acq —— acq 作次级 tiebreak(非主导,board 支持优先),
        # 防选「core 易刷但 board 不支持」的 comp → spread。牌池感知后范围 ~0.005-0.3 → 乘子 0.50-0.65。
        s *= (0.5 + 0.5 * acquirability_factor(comp.core_chars, level_of(bs), _h))
        # 定义型 augment 近乎硬绑(ADR-0152):黑塔纪元类(affinity≥0.9)拿到即改写本局
        # —— ×1.5 压过板面对他 comp 的既有投入(实测:lv5 板{列车:2} 时 held ×1.4 不足以翻转
        # progress 0.45×0.5 的领先;M1 资源入口)。与 held 乘子叠乘(fit=1.0 时总 ~×2.1)。
        if any(augment_affinity(a).get(comp.name, 0.0) >= 0.9
               for a in ctx.held_strategies):
            s *= 1.5
        s *= _board_alignment(comp, bs)
        s *= _formation_cost_factor(comp)
        # B3(线组合首口,「错线 commit」的治法):boss 克线从 0.1 权重
        # 评分项升格为**开局先验冲击乘子**——matchup<0.5(克)开局即压,不会被过渡牌堆高骗过
        # form_progress 阈值。乘子语义:克(0.0-0.4)→ ×0.6-0.85;中性(0.5)→ ×1.0;利(0.6+)→
        # ×1.05-1.1(温和,防 W_BOSS 双计 —— 评分项仍在,本乘子是开局/无板面投入时的主导信号,
        # 有板面投入时被 _board_alignment 稀释)。影子安全:boss_fit None → ×1.0(=现状)。
        try:
            _bf = boss_fit(comp, list(bs.plane_bosses.value or []))
            if _bf is not None:
                s *= (0.7 + 0.6 * _bf)
        except Exception:   # noqa: BLE001  影子失败安全
            pass
        scored.append((s, comp))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[:top_n]


def comp_score_breakdown(comp: Comp, bs: GameState, ctx: ScoreContext) -> dict[str, float | None]:
    """comp_score 的特征分解(telemetry 采集用:给人肉眼复盘 + 未来 ML side door)。

    schema 稳定(字段名跨版本不变);数值随版本/实玩变。*_fit 无数据项值为 None(动态权重)。
    详 cw_telemetry。
    """
    return {
        "progress": progress(comp, bs),
        "mechanics_fit": mechanics_fit(comp, ctx.mechanics),
        "env_fit": env_fit(comp, ctx.env),
        "held_strategy_fit": held_strategy_fit(comp, ctx.held_strategies),
        "boss_fit": boss_fit(comp, ctx.bosses),
        "equip_fit": equip_fit(comp, bs),
        "strength": strength_base(comp),
        "form_progress": form_progress(comp, bs),
    }


# ===== M7 装备角色级分配(方法论 M7:装备是角色特定的,51% 文本覆盖)=====

EQUIP_CAPACITY: int = 3   # 每单位装备上限(below-avatar 最多 3 件,D-49 布局约束)


def _pairing_guard_ok(worn_basics: dict[str, list[str]], char: str, basic: str,
                      key_set: set[str], core_set: set[str], rq: set[str]) -> bool:
    """防误合成配对守卫的纯判定(ADR-0391 纪律 1 的两例外;单源判定)。

    ``equip_allocation`` 的内嵌 ``_pairing_ok`` 与 ``equip_alloc_empty_reason``
    (分配空归因)共用本函数,保证「分配语义」与「分配空诊断」永不漂移。
    ``worn_basics`` = char 名 → 已穿基础件名单(画面已穿 + 本趟已分配)。
    """
    from sr_od.application.currency_war.data.cw_synthesis import synthesize_target
    for b2 in worn_basics.get(char, ()):
        y = synthesize_target(basic, b2)
        if y is None:
            continue
        if y in key_set and char in core_set:
            return True     # 例外①:想要的配对,core 上穿着合成=快路径
        return basic in rq and b2 in rq and char not in core_set   # 例外②:回收线有意 2合1
    return True


def _wearable_gate_ok(worn_all: list[str], char: str, item: str) -> bool:
    """穿着可行性三谓词纯判定(P95 支配命题 §2-A 的分配前排除实现;单源判定)。

    命题单篇 = docs/develop/sr_od/application/currency_war/proofs/p95-allocation-feasibility-dominance.md
    (「必拒对分配前排除严格支配分配后重试」;三谓词即「必拒判定可前置」的
    机制事实)。``equip_allocation`` 的内嵌 ``_wearable_ok`` 与
    ``equip_alloc_empty_reason``(分配空归因)共用本函数,保证「分配语义」与
    「分配空诊断」永不漂移(同 ``_pairing_guard_ok`` 形态)。
    ``worn_all`` = char 名 → 已穿全名单(画面已穿 + 本趟已分配;非仅基础件)。

    - **W1 同名∧非两基础件合成图谱对 → 拒**:同名对 (item,item) ∈ 配方图
      (8 基础件全有自配配方)= 合法穿着即合成通道,**不拦**(交配对守卫
      例外①core 快路径/②回收线 2合1 既有辖域;本谓词拦域全为非基础件同名,
      例外域全为基础件交叉配对,两域交 = 空,显式互斥)。同名对 ∉ 图谱
      (非基础件同名)→ 拒——拦域判据 =「非两基础件合成图谱对」的结构
      判据,非「不可合成」断言(蓝钻/红钻自配路线注册表在册而图谱按类别
      排除)。判据形态 = ``self_advance(item) is None``:同名对只可能命中
      图谱的自配半边。推断级判据:唯一实证为「同名 + 槽满混叠」帧(同名
      单因未直证),定谳前按必拒保守拦截(P95 §3 边界②;错杀 = 件滞留
      owned,漏放 = 白拖 + 拉黑记忆,不对称),实测定谳后收窄或确证。
      输入经合成产物展开(P95 §2-A「worn = 现读 ∪ 合成产物展开」)。
    - **W2 件专属前置 → 拒**:结构化条目(data/cw_equipment_wear_rules_data,
      前置/可穿性建模单一源)声明前置(「需要空装备栏」族)∧ 不满足。
      读法定谳前取最保守「身上有任意件即拒」(真值读法空间「全空 vs
      ≥2 空槽」两读法下有件均拒,保守缺省无需先行定谳);新件漏建模由
      互检显警兜(消费点 = equip_allocation 头部,禁解析散文)。
    - **W3 骇客目标类 fail-closed → 拒**:类别可穿性门在册(同上结构化
      载体)∧ char 不在白名单。白名单 = 银狼LV.999 为假说级(四条旁证收敛
      无直接实证,禁当已证):定谳前 fail-closed 保守拒(错杀 = 件滞留;
      漏放 = 白拖 + 拉黑 + 永久滞留,前者严格小),定谳后按真值收窄或
      改写「不参与 drag 分配」。

    已知输入失真面(部分有效申报):W1/W2 的 worn 输入与容量扣减同源
    (below-avatar 画面现读),read_row_equipped mini icon 漏读(3 件读 1 实证)
    使 worn 缩水 → 漏读帧拦不全;识别面批收口前谓词部分有效,禁把漏读帧
    的漏拦读成谓词无效(P95 §2 附出辖声明)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
    from sr_od.application.currency_war.data.cw_equipment_wear_rules_data import (
        CATEGORY_WEAR_GATES,
        EQUIP_WEAR_PREREQUISITES,
        WEAR_PREREQ_EMPTY_SLOTS,
    )
    from sr_od.application.currency_war.data.cw_synthesis import (
        expand_worn_products,
        self_advance,
    )
    # W1:同名 ∧ 非两基础件合成图谱对(合成产物展开后判定)
    for w in expand_worn_products(worn_all):
        if w == item and self_advance(item) is None:
            return False
    # W2:件专属前置(定谳前保守读法 = 有任意件即拒)
    entry = EQUIP_WEAR_PREREQUISITES.get(item)
    if entry is not None and entry.predicate == WEAR_PREREQ_EMPTY_SLOTS and worn_all:
        return False
    # W3:类别可穿性门(fail-closed 白名单)
    eq = EQUIPMENTS.get(item)
    if eq is not None:
        allowed = CATEGORY_WEAR_GATES.get(eq.category)
        if allowed is not None and char not in allowed:
            return False
    return True


def equip_alloc_empty_reason(comp: Comp | None, deployed: list, owned: list[str],
                             occupied: dict[tuple[str, int], list[str]] | None = None,
                             ) -> str:
    """``equip_allocation`` 返回空时的结构化归因(纯函数)。

    返回值域:
    - ``pool_empty``:owned 穿戴池空(调用方无货可分);
    - ``no_deployed``:场上无可命名角色(无处可穿);
    - ``capacity_full``:所有在场角色的装备容量都已占满;
    - ``pairing_guard``:有货有空位,但每个 (角色, 装备) 组合都被防误合成配对守卫拦下;
    - ``wearable_gate``:有货有空位,但每个 (角色, 装备) 组合都被穿着可行性
      三谓词(同名非图谱对/件前置/类别门)拦下——与 ``pairing_guard`` 同族
      分键,stop_reason 同走「分配方案空:」前缀 → 哨兵归域 strategy_gap,
      归域枚举零改动;
    - ``unknown``:存在可行组合但分配仍返回空(不该发生,出现即分配器与诊断漂移,优先查)。

    归因前提:仅当 ``equip_allocation`` **返回空** 时调用才精确——分配一旦产出
    件,容量/已穿基础件会随分配演进,诊断函数只复现「零分配起点」的状态。
    与 ``equip_allocation`` 同输入口径(occupied/completed 前提下守卫状态一致:
    空分配 ⇔ 无任何 ``_assign`` 发生)。可行性判定与分配器共用
    ``_pairing_guard_ok``/``_wearable_gate_ok`` 单源(镜像纪律)。
    """
    occ = occupied or {}
    pool = list(owned)
    if not pool:
        return 'pool_empty'
    from sr_od.application.currency_war.data.cw_synthesis import (
        RESERVED_COMPONENTS,
        recycle_qualified,
    )
    key_set = set(comp.key_equips) if comp is not None else set()
    core_set = set(comp.core_chars) if comp is not None else set()
    rq = recycle_qualified(list(comp.key_equips) if comp is not None else None)
    is_basic = RESERVED_COMPONENTS.__contains__
    worn_basics: dict[str, list[str]] = {}
    worn_all: dict[str, list[str]] = {}
    capacity: dict[str, int] = {}
    by_name: dict[str, list] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if n:
            by_name.setdefault(n, []).append(d)
            for w in occ.get((getattr(d, 'position_pref', '') or '',
                              int(getattr(d, 'slot', 0) or 0)), []):
                worn_all.setdefault(n, []).append(w)
                if is_basic(w):
                    worn_basics.setdefault(n, []).append(w)
    for n, ds in by_name.items():
        used = sum(len(occ.get((getattr(d, 'position_pref', '') or '',
                                int(getattr(d, 'slot', 0) or 0)), [])) for d in ds)
        capacity[n] = max(0, EQUIP_CAPACITY * len(ds) - used)
    if not any(v > 0 for v in capacity.values()):
        return 'no_deployed' if not capacity else 'capacity_full'
    # 可行组合遍历:配对守卫拦下 → 记 pairing 面;穿戴可行性门拦下 → 记
    # wearable 面;两门全拦才落到函数尾——wearable 拦过即归 wearable_gate
    # (三谓词拦截族),否则为纯配对守卫拦(现行为)。存在任一可行组合 =
    # unknown(分配器与诊断漂移,优先查)。
    wearable_blocked = False
    for n, cap in capacity.items():
        if cap <= 0:
            continue
        for e in pool:
            if is_basic(e) and not _pairing_guard_ok(worn_basics, n, e,
                                                     key_set, core_set, rq):
                continue
            if not _wearable_gate_ok(worn_all.get(n, []), n, e):
                wearable_blocked = True
                continue
            return 'unknown'    # 存在可行组合,分配器本不该返回空
    return 'wearable_gate' if wearable_blocked else 'pairing_guard'


def equip_allocation(comp: Comp | None, deployed: list, owned: list[str],
                     occupied: dict[tuple[str, int], list[str]] | None = None,
                     priority_order: list[str] | None = None,
                     ) -> list[tuple[str, str]]:
    """(角色名, 装备名) 分配序列 —— carry 先拿 key_equips(按序),其余 core 次之,剩余兜底前排。

    M7 方法论(plaza 648 篇 51% 谈装备):「保证三月有一鞋一风扇,花火和杨叔的回能,姬子的双风暴」
    「那刻夏全套 > 生存装 > 弹射器 > 永动机,一定要按这个顺序」—— 装备是**角色特定的**,不是
    有装备就穿(用户 §7-9 同)。分配纪律:
    1. **carry 先拿**:comp.plaza_carry(不在场上则 core_chars 中首个场上者)按序拿
       key_equips(multiplicity 消费,不超发);
    2. **其余场上 core** 拿剩余 key_equips(core 顺序);
    3. **剩余通用 owned** 按 deployed 顺序兜底(前排在前 —— 受击/反甲类在前排生效)。
    ``occupied[(row, slot)]`` = 已穿列表(容量扣减,EQUIP_CAPACITY);deployed 元素需带
    char_id/position_pref/slot(BenchChar)。comp=None → 全走 3(通用兜底)。
    纯函数(可离线测);CwOpEquipAll 消费。

    ``priority_order``(18 号稿 §3.3 签名扩展,ADR-0526):可选分配优先序
    (list[str],角色名);None(缺省)= 现行内部派生序,**零行为漂移**。
    语义 = 词缀条件优先层(§3.2)的唯一传入通道:序的每个成员在分配侧都
    被**吃满至容量**(凑满谓词;调用方 = 策略侧 resolve_affix_priority_order,
    只放「谓词未满足成员 ∪ core」);它同时改写 key_equips 接收者序与 core
    兜底序。语义保持声明(§3.3 措辞收窄):配对守卫与星徽唯一件守卫对候选
    对的判定与遍历次序无关,重排序下逐对语义不变;occupied 容量扣减的
    **可穿件总数**与次序无关,「落在谁身上」随次序变 = priority_order 的
    语义本体,不属语义漂移。**comp=None 时强制 None**(§3.3:重排依据依赖
    阵容名单;未定型帧零重排)。**脱落预防(18 号稿 §1.2-3)**:分配器为
    fill-only——occupied 仅作容量扣减,不触碰任何已穿件(key 与否同判),
    任何重排都不可能取下已穿 key 件(装备无角色间直拖通道,10 号稿 §2.1.8)。

    ADR-0265(穿戴可逆裁决):**穿戴是可逆操作**(卖角色全额返还装备)——穿着既不锁死
    合成路线(组件可取回)也不构成资源损耗(转移成本仅为操作摩擦),
    故无「合成保留组件禁入穿戴池」过滤。组件保护由两条真实依据的防线承担:
    ①合成锁线门(方向确定性才合成,反「压注未定方向」——不可逆的金/
    组件消耗只在锁线后发生);②下方防误合成配对守卫(真实不可逆依据:
    非预期合成不可逆消耗两件组件,无确认无回退)。
    **简易件默认穿**(编排者裁决:「简易件效果不大,穿不穿随策略定」→
    采纳默认穿):组件与进阶成品同池参与分配,期望收益由磨损标定仪持续
    测量(ADR-0391 设计件:借实机/sim 对照测简易件穿戴的真实期望收益)。

    ADR-0391(P14 期望模型接入,口述「穿着即合成/囤积/回收线」):两条新纪律——
    1. **防误合成配对守卫**(全 plane):同一角色身上不得出现互为配方的两件
       基础件,除非 ①配对产物 ∈ key_equips 且穿者是 core(=想要的配对,
       穿着触发合成即快路径),或 ②两件都是回收合格死库存且穿者非 core
       (回收线 2合1 的有意触发)。口述依据:穿着触发自动合成无确认,「会被
       角色身上的残留件带偏,可能合出非预期产物」——非预期合成不可逆地
       消耗两件组件。
    2. **死库存回收去向**(全 plane 生效):回收合格基础件(P14 定理 3:
       不是任何目标进阶的组件)优先发非 core 工具人、每人至多 2 件(有意
       触发 2合1,产物=无用进阶,等冶金炉 3 件同刷);发不完留在 owned
       囤着(口述囤积原则「没什么用就先不装备囤着」)。死库存不穿 core
       ——穿着合成产物落在 core 身上=后续转移摩擦。

    **穿着可行性三谓词**(P95 支配命题 §2-A 的分配前排除实现;判定单源 =
    模块级 ``_wearable_gate_ok``,docstring 载三谓词全文与证据分级):对游戏
    以概率 1 拒收的 (件,角色) 对,分配前排除严格支配分配后重试——W1 同名∧
    非两基础件合成图谱对 / W2 件专属前置(「需要空装备栏」族,结构化载体
    data/cw_equipment_wear_rules_data)/ W3 骇客目标类 fail-closed。与
    ``_pairing_ok``/``_emblem_ok`` 同构并列,被拦件**留 pool**(跳过=留
    owned,不 pop 丢弃);W1 拦域与配对守卫例外①②辖域显式互斥(两域交=空,
    同名自配对合法穿着即合成通道不拦)。消费位 = key 环/core 吃满/非 core
    保底/comp=None 轮转四处候选过滤(与 _emblem_ok 挂载点全集一致;P95
    命题主语 = (件,角色) 对,必拒对全分配通道排除)。死库存回收线不挂:
    池域 = 基础件,三谓词对基础件恒放行。
    """
    occ = occupied or {}
    pool = list(owned)
    if comp is None:
        priority_order = None   # 18 号稿 §3.3:未定型帧词缀谓词集合退化,强制零重排
    by_name: dict[str, list] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if n:
            by_name.setdefault(n, []).append(d)
    capacity: dict[str, int] = {}
    for n, ds in by_name.items():
        used = sum(len(occ.get((getattr(d, 'position_pref', '') or '',
                                int(getattr(d, 'slot', 0) or 0)), [])) for d in ds)
        capacity[n] = max(0, EQUIP_CAPACITY * len(ds) - used)

    # ===== ADR-0391:防误合成守卫 + 回收去向(P14 定理 3/4)=====
    from sr_od.application.currency_war.data.cw_synthesis import (
        RESERVED_COMPONENTS,
        recycle_qualified,
    )
    _key_set = set(comp.key_equips) if comp is not None else set()
    _core_set = set(comp.core_chars) if comp is not None else set()
    _rq = recycle_qualified(list(comp.key_equips) if comp is not None else None)
    # 基础件判定 = RESERVED_COMPONENTS(7 标准 ∪ 光能电池,恰为全 8 件基础件
    # ——别用 SYNTHESIS_BASES,它漏光能电池,而光能电池系配方全部经它)
    _is_basic = RESERVED_COMPONENTS.__contains__
    # 各角色已穿名单(occupied 画面已穿 + 本趟已分配):worn_basics = 基础件
    # 子视图(配对守卫输入,口径不变);worn_all = 全名单(穿着可行性三谓词
    # 的 W1/W2 输入,经合成产物展开消费)
    worn_basics: dict[str, list[str]] = {}
    worn_all: dict[str, list[str]] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        for w in occ.get((getattr(d, 'position_pref', '') or '',
                          int(getattr(d, 'slot', 0) or 0)), []):
            worn_all.setdefault(n, []).append(w)
            if _is_basic(w):
                worn_basics.setdefault(n, []).append(w)

    # 穿戴规则互检显警(结构化载体 ↔ 注册表散文;漏建模/孤儿/措辞漂移 →
    # 显警不拦截,防新件静默漏消费。每次分配评估一次,量级 = 注册表件数)
    from sr_od.application.currency_war.data.cw_equipment_wear_rules_data import (
        check_equipment_wear_rule_coverage,
    )
    for _cov in check_equipment_wear_rule_coverage():
        log.warning('[cw-equip] 装备穿戴规则互检显警: %s', _cov)

    def _pairing_ok(char: str, basic: str) -> bool:
        """基础件 basic 发给 char 是否安全(判定单源在模块级 ``_pairing_guard_ok``)。"""
        return _pairing_guard_ok(worn_basics, char, basic, _key_set, _core_set, _rq)

    def _wearable_ok(char: str, item: str) -> bool:
        """穿着可行性三谓词(判定单源在模块级 ``_wearable_gate_ok``)。"""
        return _wearable_gate_ok(worn_all.get(char, []), char, item)

    def _emblem_ok(char: str, item: str) -> bool:
        """阵营星徽 → 排除已自报同阵营角色(复盘 g_20260902_181254 定谳)。

        星徽 = add-if-absent 羁绊授予(equipment_mechanics §6),给已自报
        同阵营角色时游戏装备不上(拖拽 diff=0,四轮连败实证)。星徽命名
        统一「X星徽」→ X = 授予阵营;非星徽件恒 True。
        """
        if not item.endswith('星徽') or len(item) <= 2:
            return True
        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        _info = CHARACTERS.get(char)
        return _info is None or item[:-2] not in _info.factions

    def _assign(char: str, item: str) -> None:
        out.append((char, item))
        capacity[char] -= 1
        if _is_basic(item):
            worn_basics.setdefault(char, []).append(item)
        worn_all.setdefault(char, []).append(item)

    out: list[tuple[str, str]] = []
    if comp is not None and comp.key_equips:
        # 接收者顺序:priority_order(词缀优先层重排序)优先,缺省 = 内部派生序
        # (plaza_carry 优先,再 core_chars 顺序);只发给场上且容量 >0 者。
        # key 件绑定裁决(18 号稿 §3.2,ADR-0526):谓词层只重排候选序,
        # 不改 key 件绑定——key 接收者在优先层下仍限于 carry∪core
        # (非 core 凑谓词只走通用件吃满)。
        if priority_order:
            _core_pref = set(comp.core_chars) | (
                {comp.plaza_carry} if comp.plaza_carry else set())
            order: list[str] = [c for c in priority_order if c in _core_pref]
        else:
            order = []
            if comp.plaza_carry:
                order.append(comp.plaza_carry)
            for c in comp.core_chars:
                if c not in order:
                    order.append(c)
        recipients = [c for c in order if capacity.get(c, 0) > 0]
        for r in recipients:
            for w in list(comp.key_equips):
                if capacity.get(r, 0) <= 0 or not pool:
                    break
                if w in pool:
                    # ADR-0391:key 豁免的基础件同样过配对守卫(防非预期合成)
                    if _is_basic(w) and not _pairing_ok(r, w):
                        continue
                    if not _emblem_ok(r, w):
                        continue    # 阵营星徽 → 同阵营角色 = 装备不上,换目标
                    if not _wearable_ok(r, w):
                        continue    # 穿着可行性门(必拒对排除)→ 件留 pool
                    pool.remove(w)
                    _assign(r, w)
            if not pool:
                break
    # 通用兜底:剩余 pool 按场上顺序(deployed 原序,前排先)分完
    # 身份过滤:非 target 角色穿满通用件 = 换血时一件件拆(即时小收益换后期摩擦)。
    # 规则:comp 有 core 在场时,兜底优先发 core(哪怕 deployed 序靠后);
    # 非 core 每人只兜底 1 件(防裸奔),core 吃满。
    # comp=None:**按轮转**(每人 1 件轮一圈再回头,而非按 deployed 序灌满一人
    # ——否则前排 capacity 全被第一人吃光);comp 有 core 时行为不变。
    if comp is not None:
        # core 兜底序:priority_order 在列时按其序吃满(凑满谓词语义,契约 =
        # 调用方只放「谓词未满足成员 ∪ core」);缺省 = core_chars 序(零漂移)
        if priority_order:
            _cores = [c for c in priority_order if capacity.get(c, 0) > 0]
        else:
            _cores = [c for c in comp.core_chars if capacity.get(c, 0) > 0]
        _others = [d for d in deployed
                   if getattr(d, 'char_id', '') and d.char_id not in comp.core_chars]
        # ADR-0391 死库存回收去向:先于 core 兜底抽取(防 core 盲吃死库存),
        # 非 core 工具人每人至多 2 件(两件互为配对 → 游戏自动 2合1 =
        # 回收线有意触发;发不完留 owned 囤着)
        _dead = [e for e in pool if e in _rq]
        if _dead:
            for _pass in range(2):
                if not _dead:
                    break
                for d in _others:
                    if not _dead:
                        break
                    n = d.char_id
                    if capacity.get(n, 0) <= 0:
                        continue
                    e = _dead[0]
                    if not _pairing_ok(n, e):
                        continue    # 该工具人身上有会配错的残留件 → 换人
                    _dead.pop(0)
                    pool.remove(e)
                    _assign(n, e)
        # core 先吃满(跳过会触发非预期合成的基础件 → 留 owned)
        for cn in _cores:
            while pool and capacity.get(cn, 0) > 0:
                # 只取「可安全穿」的首件;被配对守卫/穿戴可行性门拦下的件
                # **留在 pool**(交给 _others 兜底/最终留 owned)——旧实现
                # pop 后丢弃,一个穿残留基础件的 core 就能把整池吃光,身后
                # 无残留件的角色一件分不到(分配空但 diag 判「存在可行组合」
                # 的 unknown 漂移由此而来;违背上方「跳过=留 owned」注释与
                # 本函数 docstring「发不完留在 owned 囤着」,缺陷语义修复)。
                _k = next((i for i, e in enumerate(pool)
                           if not (_is_basic(e) and not _pairing_ok(cn, e))
                           and _emblem_ok(cn, e)
                           and _wearable_ok(cn, e)),
                          None)
                if _k is None:
                    break   # 该 core 对整池都被守卫拦 → 一件不取,整池留 owned
                _assign(cn, pool.pop(_k))
        # 非 core:每人 1 件保底(同样过配对守卫与穿戴可行性门)
        for d in _others:
            n = d.char_id
            if pool and capacity.get(n, 0) > 0:
                idx = next((i for i, e in enumerate(pool)
                            if not (_is_basic(e) and not _pairing_ok(n, e))
                            and _emblem_ok(n, e)
                            and _wearable_ok(n, e)), None)
                if idx is not None:
                    _assign(n, pool.pop(idx))
        return out
    # comp=None:轮转分配;配对守卫生效
    # (comp=None 无豁免信息 → 任何互为配方的基础件对不同人发)
    _names = [d.char_id for d in deployed if getattr(d, 'char_id', '')]
    _round = 0
    while pool:
        _gave = False
        for n in _names:
            if not pool:
                break
            if capacity.get(n, 0) > 0:
                # 同 core 分配侧的修法:被配对守卫/穿戴可行性门拦的件留
                # pool(轮转给下一个人),不 pop 丢弃——否则一个有残留件的
                # 人会把整池吃光,后面的人一件分不到。
                _k = next((i for i, e in enumerate(pool)
                           if not (_is_basic(e) and not _pairing_ok(n, e))
                           and _emblem_ok(n, e)
                           and _wearable_ok(n, e)),
                          None)
                if _k is None:
                    continue    # 该人对整池都被拦 → 跳过此人(件留 pool)
                _assign(n, pool.pop(_k))
                _gave = True
        _round += 1
        if not _gave and not pool:
            break
        if _round > EQUIP_CAPACITY:
            break
    return out


# ===== 转型(pivot)+ 巨星(select_megastar)=====

# T#97 commitment(单一定义,maybe_pivot 强粘 + cw_events 买牌 prefilter 拒 off-target 共用):
# commit = 已成型(form_progress≥COMMIT_FRAC)**或**累计轮达 COMMIT_ROUND(spread board 的 form_progress
# 永不达 COMMIT_FRAC → 轮数兜底)。commit 后:① maybe_pivot 提阈不弃成型 comp;② cw_events prefilter
# 拒 off-target(commit 后买散牌 = spread 根因 → 该 Refresh 找 target / 攒金,drought bail 处理真不可达)。
COMMIT_FRAC: float = 0.4           # form_progress ≥0.4 算已 commit(2 阵营 comp 约 1 阵营过半)
COMMIT_ROUND: int = 2
COMMIT_STICK_FACTOR: float = 1.5   # 已 commit → pivot 阈值 ×1.5(0.10→0.15),更难弃成型 comp
PIVOT_GAP_FLOOR: float = 0.05      # 信号1 阈值绝对下限(评审🟡6:easier/losing/overlap 叠乘最低
#                                   0.039 < comp_score 单轮自然抖动 ~0.06-0.1 → losing 窗口噪声级 churn)


def target_committed(target: Comp, bs: GameState) -> bool:
    """target 是否已 commit。单一真相源(T#97);maybe_pivot(强粘)+ cw_events prefilter(拒 off-target)共用。

    commit = 已成型(form_progress≥COMMIT_FRAC)**或** 轮数兜底(累计轮≥COMMIT_ROUND **且** form_progress>0)。
    轮数兜底要求 form_progress>0 —— 防零投入误锁:board 全倒在别的 comp 上(target 零投入)时不应算 commit
    (明显错配,该 pivot;轮数兜底若不要求 fp>0,COMMIT_ROUND=2 绝对兜底会误杀信号1,
    test_maybe_pivot_better_comp_emerges 锁此)。
    spread board(target 有零星投入但散)轮数兜底仍生效 → 防散板振荡。
    """
    fp = form_progress(target, bs)
    from sr_od.application.currency_war.kernel.cw_plane_table import NODES_PER_PLANE
    return (fp >= COMMIT_FRAC
            or ((plane_of(bs) - 1) * NODES_PER_PLANE + round_num_of(bs) >= COMMIT_ROUND and fp > 0))


# pivot 冷却(防过度换线):换线漂移会让 P1 后段板面永远半成型——
# 每次 pivot 把已买核心推倒重买,板面强度清半程;A8 敌强度随轮涨 → 换线窗口=最弱时撞最强怪。
# 转线后 cooldown 轮内信号 1/2 不再触发(信号 3 保命豁免——危机永远允许转)。
# 冷却状态宿主 StrategySession.pivot_cooldown_until 已随 default 栈退役删除
# (唯一写端=default 栈战略层,已随 ADR-0583 出基类);maybe_pivot 挂账层的冷却守卫随之惰性化
# (session 冷却字段不再存在,守卫恒不触发)。
# 保命 pivot 也设冷却(1 轮/次,弱于信号1/2 的 3 轮,审计 cc119c14):危机允许转,
# 但「信号3→转线→板面清零→更弱→又信号3」的连续翻转自激会被冷却掐断
# (否则板面 14 阵营各×1 永不成型)。保命优先级仍最高(hp 危险时信号1/2 不参与),
# 已在该 comp 或刚转过 1 轮内 → 保持(板面不推倒,靠买牌/升人口补强度)。
PIVOT_COOLDOWN_ROUNDS: int = 3
PIVOT_SURVIVAL_COOLDOWN_ROUNDS: int = 1   # 保命 pivot 冷却(防连续翻转自激)


def maybe_pivot(bs: GameState, ctx: ScoreContext, config, target: Comp | None,
                tracker: PerformanceTracker | None = None) -> Comp | None:
    """是否转型到新 target(返回新 Comp 或 None 不转)。
    转型信号(比较型,03 正确性-4):**信号 3(保命)优先于 1/2**():
    3. **保命转型(最优先)**:hp < 0.75×effective_hp_threshold → 切最快成型的 easy comp
       (typical_form_round 最小,**稳定不 churn**)。hp 危险时信号 1/2 不参与(防振荡死亡螺旋)。
    1. 更优 comp 涌现:存在 B 使 comp_score(B) > target + PIVOT_SCORE_GAP(本回合单次比较)。
    2. ceiling 不可达:target.typical_form_round > 剩余轮次估算(已成型豁免)。

    ⚠️ hp 危险时信号 3 独占:低 HP 下信号 1 的 best 随 board/shop 每轮变 → target 振荡 churn
    + 选到高难度 comp → 永不成型 → 死亡螺旋;故信号 3 提前 + 独占(返回稳定最快 easy,不让 1/2 churn)。
    ⚠️ 启发式边界:转型成本用规则估算,不用多步搜索(03 正确性-5)。tracker 用于保命判断的观测(已接:``is_losing_streak`` 解锁 commit 锁做保命转型,L791)。
    """
    PIVOT_SCORE_GAP: float = 0.10   # 更优涌现阈值(占位,待实玩校准)
    # ⚖️ 不变量统一守卫(用户定调治本):
    # **不变量:任意两次 pivot 之间至少间隔 cooldown 轮,无例外**(含危机信号)。
    # 守卫放**函数最顶部**(所有信号路径的唯一必经点)——分散检查会被未覆盖的
    # 信号路径绕过(危机豁免路径实证绕过过分散检查)。单一入口后调用侧的
    # 冷却门只是省算力优化,不再是守卫。
    _sess_inv = getattr(ctx, 'session', None)

    def _committed_inv(_sess, _bs) -> bool:
        """committed(非双轨期)派生读(单一源 = cw_intention
        .committed_authority;原 ``bs.dual_track_phase`` 字段直读随容器
        化退役——容器无此字段,getattr 恒 False = 方向层判定静默漂移
        实位,T-96 验收承接②。函数级懒 import 防环:本模块与
        cw_intention 互相消费)。"""
        from sr_od.application.currency_war.kernel.cw_intention import (
            committed_authority,
        )
        return committed_authority(_bs, _sess)
    _cd_inv = getattr(_sess_inv, 'pivot_cooldown_until', 0) if _sess_inv else 0
    if round_num_of(bs) <= _cd_inv:
        log.info('[cw-pivot] p=%s r=%s 冷却中(至r%s,不变量:两次pivot至少隔冷却轮,'
                 '无例外;板面靠买牌/合星/升级补)',
                 plane_of(bs), round_num_of(bs), _cd_inv)
        return None
    # 双轨期(P1 未定型)信号1/2 全关(用户定调,实机四线摇摆实证):
    # target_comp 是从近空板上按分选的(分=噪声),每来一张牌重排 → 每 1-4 轮 pivot →
    # 四条零共享核心线各推倒一次 → 板永不成型 → P1 全输过去。
    # 用户模型:P1 玩的 = 过渡框架(列车+仙舟)持续加深;终局线由贯穿件信号锁
    # (CommitSignals,方向重估定型路径);涌现/ceiling 分差在双轨期无信息量。
    # target 变更路径收敛为:①CommitSignals 定型(ADR-0209)②drought 弃线重 select
    # ③定义型 augment(贯穿件级资源信号,下方 _defining_new)④定型后信号 1/2 照常。
    # (易 comp 成型快 → 少掉血;实测出现过 easy/medium gap 0.097 卡 0.10 没转、
    # 慢成型持续掉血的案例;fewer 卡 + S 强的 easy comp 转了更快成型)。target 已成型不降(不弃已完成 comp)。
    PIVOT_EASIER_FACTOR: float = 0.7   # best 更易成型时阈值 ×0.7(0.10→0.07),倾向转易 comp
    # F1(commit 强粘):已 commit(判据见模块级 ``target_committed`` / COMMIT_FRAC / COMMIT_ROUND)
    # 不因易 comp 降阈被弃(COMMIT_* 为 maybe_pivot + cw_events prefilter 共用)。
    _diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    candidates = select_comp(bs, ctx, config, top_n=len(COMP_LIBRARY))
    if not candidates:
        return None
    best = candidates[0]
    # 保命独占语义:hp 危险时只认最快 easy comp,信号 1/2 不参与(防 churn:
    # best 随 board/shop 每轮变 → target 振荡 + 高难度 comp 永不成型 → 死亡螺旋)。
    # 阈值域直传容器帧(effective_hp_threshold 波 2 已切 GameState 签名,
    # 过渡期 _HpShim 手抄镜像字段桥已随之消亡——输入字段职级/位面/轮次/
    # 等级容器侧全就绪,禁再新增同型鸭子桥)。
    _pivot_hp = int(0.75 * effective_hp_threshold(bs))
    # 信号3保命优先于一切(含定型;实机 P2 振荡实证)——P2 hp 常驻<阈值
    # → 保命每步触发「切 board progress 更高的 easy 线(列车)」,而 CommitSignals
    # 定型每步又切回终局(反甲白厄 10.53 ready)→ 同轮内 3-4 次翻转,买牌方向
    # 混乱(白厄+姬子/爻光/风堇混杂),P2 战力永远起不来。
    # 修:**定型后保命 pivot 需落点 form_progress 显著更高**(≥当前+0.25,一次
    # 性大步换线),不再是「有任何 progress 的最快 easy」——平级/略优不换,
    # 消除与定型的每步拉锯;血线危机交买牌/装备侧加速(不弃线)。
    # [挂账读点·hp 政策层申报] 本函数现属挂账层(生产调用面空,测试仓经
    # 桥调用),hp 读约束照旧:重挂生产消费**必经政策层读口**——门后值 =
    # kernel/cw_hp_policy.decision_hp(bs, session),可信位 =
    # hp_decision_trusted_of(bs),禁按下方直读形态旁路(消费同门,
    # ADR-0583 §2.4)。本行直读仅挂账期原样保留,行为零变化。
    _hp = bs.hp.value
    _committed_target = (target is not None and target_committed(target, bs))
    if _hp is not None and _hp < _pivot_hp:   # None=无真值:不触发保命 pivot(可信位门在决策侧)
        # 冷却守卫已提函数顶(不变量单一入口),危机路径不再自查。
        # 位面过滤:当前位面乏力的 comp 不进保命候选(转过去 = 更死);
        # 全被滤光时回退原池(比「无候选」好)。DOT队 P2 被抽陀螺是首个案例。
        # 下一位面预转:过滤扩到 next_plane —— P1 末段保命转线若转进「下位面弱」的
        # comp(如 DOT队 weak_planes=(2,)),等于把死期从本节点推迟到 P2 首战。
        # 收窄:仅本位面末段(round≥7)生效 —— 早段(P2 还远)保命只看当前位面,
        # 别为远期弱项否决当下救急线。
        # 当前+下一位面都 OK 才是合格落点;全滤光仍回退原池(有落点好过无)。
        _next_plane = min(plane_of(bs) + 1, 3)
        _plane_ok = [c for c in candidates if plane_of(bs) not in c.weak_planes
                     and (round_num_of(bs) < 7 or _next_plane not in c.weak_planes)]
        _pool = _plane_ok or candidates
        # 双轨期保命**严格 easy(不回退原池)** ——
        # hard 0-progress = 换个姿势死;
        # 且要求**与当前板共享阵营**(min reset:保命转线别推倒仅有的羁绊)。
        # 非双轨(已定型/已进 P2)保 fallback 原语义(有落点好过无)。
        if not _committed_inv(_sess_inv, bs):
            _board_factions = set(bs.board.value or {})
            easy = [c for c in _pool if c.form_difficulty == 'easy'
                    and _board_factions & set(c.factions)]
            if not easy:
                log.info('[cw-pivot] p=%s r=%s hp=%s<%s 双轨期保命无 strict-easy 共享线 → '
                         '保持现状(板面靠买牌/合星/升级补,不推倒)',
                         plane_of(bs), round_num_of(bs), _hp, _pivot_hp)
                return None
        else:
            easy = [c for c in _pool if c.form_difficulty == "easy"] or _pool
        with_progress = [c for c in easy if form_progress(c, bs) > 0]
        if with_progress:
            fastest = min(with_progress, key=lambda c: c.typical_form_round or 99)
            if target is None or fastest.name != target.name:
                # 定型后保命换线门槛——落点 progress 须显著更高(≥当前+0.25)
                if _committed_target:
                    _cur_fp = form_progress(target, bs)
                    _new_fp = form_progress(fastest, bs)
                    if _new_fp < _cur_fp + 0.25:
                        log.info('[cw-pivot] p=%s r=%s hp=%s 信号3保命:已定型(%s fp=%.2f) '
                                 '落点 %s fp=%.2f 未显著更高 → 保持(危机交买牌/装备侧;r118)',
                                 plane_of(bs), round_num_of(bs), _hp,
                                 target.name, _cur_fp, fastest.name, _new_fp)
                        return None
                log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 %s->%s [board有progress优先]',
                         plane_of(bs), round_num_of(bs), _hp, _pivot_hp,
                         target.name if target else 'None', fastest.name)
                return fastest
            return None   # 已在该 easy comp → 保持(不让信号 1/2 churn 切走)
        # 有 progress)被 easy 过滤排除,旧 fallback `pool=with_progress if with_progress else easy` → 选最快
        if target is not None and form_progress(target, bs) > 0:
            # target 有 progress(medium 也算)→ 保持(不弃有 progress 的去追 0-progress easy;转 0-foundation 必死)。
            log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 无easy有progress → 保持 %s(有progress,不转0-foundation)',
                     plane_of(bs), round_num_of(bs), _hp, _pivot_hp, target.name)
            return None
        fastest = min(easy, key=lambda c: c.typical_form_round or 99)
        if target is None or fastest.name != target.name:
            log.info('[cw-pivot] p=%s r=%s hp=%s<%s 信号3保命 无progress → 最快easy %s',
                     plane_of(bs), round_num_of(bs), _hp, _pivot_hp, fastest.name)
            return fastest
        return None
    # commit 锁:已 commit 的 target **不被信号1(涌现)翻转**。comp_score 随 board 每 round 抖动(board 因
    # buy 变)→ 信号1 反复越阈值 → target 振荡 → buy 每轮
    # 为不同 comp 买 → 永不集中 → 散板。COMMIT_STICK_FACTOR×1.5(0.15 阈)压不住(大 board 波动 gap 仍超)。
    # commit 即锁定:只有信号3(HP 危机,上方已优先处理)/信号2(ceiling 不可达)/drought_bail(连续无供给)
    # /losing-streak(obs 驱动保命)能解锁。人玩同理:commit 后不因「略优 comp」弃成型,只危机才转。
    if target is None or best.name != target.name:
        _committed = target is not None and target_committed(target, bs)
        _losing = tracker is not None and target is not None and tracker.is_losing_streak(target.name)
        # 定义型 augment 解锁 commit 锁(ADR-0152):黑塔纪元类(affinity≥0.9)到手 =
        # 局内最大机会事件(M1 资源入口),与 losing streak 同级解锁 —— 否则 commit 后 augment
        # 定义型 comp 永远进不来(中心卖点静默失效)。
        _defining_new = any(augment_affinity(a).get(best.name, 0.0) >= 0.9
                            for a in ctx.held_strategies)
        # 换线供给门(防「转进死线」):换线出口(定义型/信号1)先查 best 线供给——
        # shop 无+board 无(完全断供 0.0)则拒转(否则该线零供给 → form 卡死 →
        # 装备过渡期持有永不过渡 → 旧残留+新全攒),弱信号 0.3(board 已有)放行。
        # 与 drought 重选供给门同款。
        # 空 shop(无观测,常见于离线/测试)= 不判(数据不足非断供)。
        _best_supply = shop_supply(best, bs) if bs.shop.value else 1.0
        if _best_supply <= 0.0:
            log.info('[cw-pivot] p=%s r=%s 换线供给门:%s 完全断供(shop+board 无核心)→ 拒转(保持 %s;防转进死线锁死 form/装备)',
                     plane_of(bs), round_num_of(bs), best.name,
                     target.name if target else 'None')
            if target is not None:
                best = target   # 保持现线(gap=0 → 信号1不转)
            else:
                return None     # 无 target + 断供线不直选(下轮 emergent 重看)
        elif _defining_new:
            log.info('[cw-pivot] p=%s r=%s hp=%s 定义型augment解锁 %s->%s (资源入口,绕过 gap/commit 锁)',
                     plane_of(bs), round_num_of(bs), _hp,
                     target.name if target else 'None', best.name)
            return best
        if _committed and not _losing:
            log.info('[cw-pivot] p=%s r=%s hp=%s target=%s 已commit → 锁定,跳过信号1(防振荡;best=%s 不转)',
                     plane_of(bs), round_num_of(bs), _hp,
                     target.name if target else 'None', best.name)
        elif not _committed_inv(_sess_inv, bs):
            # 双轨期信号1/2 关(实机四线摇摆实证):未成型板上 comp_score 分差是噪声,
            # 每 1-4 轮 pivot 推倒重来 = P1 全输。target 由定型(CommitSignals)/drought/
            # 定义型augment(上方已处理)管;涌现分差不构成换线证据。
            log.info('[cw-pivot] p=%s r=%s hp=%s 双轨期 → 信号1/2 关(target=%s 保持;涌现分差'
                     '在未成型板上是噪声,防四线摇摆)',
                     plane_of(bs), round_num_of(bs), _hp,
                     target.name if target else 'None')
        else:
            if target is None:
                # 无 target(尚未承诺)→ 无忠诚对象,signal1 的 gap 检查不适用(它为防「弃 current target
                # churn」而设,target=None 无可弃)→ 直接选 best。动态权重让 comp_score 诚实化
                # (无数据不再注水 0.5 常量)→ 早期诚实低分也该有 target,不该卡 gap 阈留 None。
                log.info('[cw-pivot] p=%s r=%s hp=%s 无 target → 直接选 best %s(未承诺,gap 检查不适用)',
                         plane_of(bs), round_num_of(bs), _hp, best.name)
                return best
            target_score = comp_score(target, bs, ctx) if target is not None else 0.0
            best_score = comp_score(best, bs, ctx)
            gap = best_score - target_score
            _required_gap = PIVOT_SCORE_GAP
            _easier = (target is not None
                       and _diff_rank.get(best.form_difficulty, 1) < _diff_rank.get(target.form_difficulty, 1)
                       and form_progress(target, bs) < 1.0)
            if _easier:
                _required_gap = PIVOT_SCORE_GAP * PIVOT_EASIER_FACTOR   # 未 commit + 易 comp → 降阈
            _tag = ' [易comp降阈]' if _easier else ''
            if _losing:
                _required_gap *= 0.7
                _tag += ' [viability losing]'
            # ADR-0152 转型成本(复用网络):best 与 target 角色重合低 = 推翻重买 → 需更大 gap;
            # 重合高 = 换方向继续买(便宜)→ 降阈。乘子范围 0.8(overlap≥0.5)~ 1.3(overlap<0.1)。
            _overlap = pivot_overlap(target, best) if target is not None else 1.0
            _required_gap *= (0.8 if _overlap >= 0.5 else (1.3 if _overlap < 0.1 else 1.0))
            if _overlap >= 0.5:
                _tag += f' [共享高{_overlap:.2f}降阈]'
            elif _overlap < 0.1:
                _tag += f' [共享低{_overlap:.2f}加阈]'
                # 评审🟡5:form_tiers 空的 comp(反甲白厄)fp 恒 0 → 永不 commit → 信号 1 是它
                # 唯一出路,再吃 ×1.3 加阈 = 最难逃的 comp(与 commit 锁的防振荡初衷相反 ——
                # 那是给"已成型"的保护,它从没成型过)。降回 1.0。
                if target is not None and not target.form_tiers:
                    _required_gap /= 1.3
                    _tag += '[无form_tiers回1.0]'
            # 评审🟡6:叠乘下限(0.10×0.7×0.7×0.8=0.039 < comp_score 单轮自然抖动 ~0.06-0.1
            # → losing 窗口内在重叠 comp 间噪声级来回切)。设绝对下限防 churn。
            _required_gap = max(_required_gap, PIVOT_GAP_FLOOR)
            if gap > _required_gap:
                log.info('[cw-pivot] p=%s r=%s hp=%s 信号1涌现 %s->%s (best %.3f vs tgt %.3f, gap %+.3f>%.2f%s; bd=%s)',
                         plane_of(bs), round_num_of(bs), _hp,
                         target.name if target else 'None', best.name,
                         best_score, target_score, gap, _required_gap, _tag,
                         {k: round(v, 2) for k, v in comp_score_breakdown(best, bs, ctx).items() if v is not None})
                return best
            log.info('[cw-pivot] p=%s r=%s hp=%s 信号1未达 %s vs %s (gap %+.3f<=%.2f%s 保持)',
                     plane_of(bs), round_num_of(bs), _hp,
                     best.name, target.name if target else 'None', gap, _required_gap, _tag)
    # 信号 2:ceiling 不可达(target 成型轮次 > 剩余轮次)
    if target is not None and target.typical_form_round > 0:
        # remaining 须按 plane_table 节点单一源算:固定 18-elapsed 会在 P3 早段归 0 →
        # 未成型 target 反复触发信号 2 pivot easy comp(真实还剩 7-9 节点)
        from sr_od.application.currency_war.kernel.cw_plane_table import (
            NODES_PER_PLANE,
            TOTAL_NODES,
        )
        elapsed = round_num_of(bs) + (plane_of(bs) - 1) * NODES_PER_PLANE
        remaining = max(TOTAL_NODES - elapsed, 0)
        if target.typical_form_round > remaining and form_progress(target, bs) < 1.0:
            # 切成型最快的(easy 优先);已成型(form_progress=1.0)豁免 —— 不该放弃已完成的 comp
            easy = [c for c in candidates if c.form_difficulty == "easy"] or candidates
            new = min(easy, key=lambda c: c.typical_form_round or 99)
            log.info('[cw-pivot] p=%s r=%s 信号2ceiling %s->%s (form_round %s>剩%s)',
                     plane_of(bs), round_num_of(bs), target.name, new.name,
                     target.typical_form_round, remaining)
            return new
    return None


# 盛会之星巨星 buff 表(米游社原文;2→6 档;select_megastar 按绑定选):
#   星期日:前台首位前台强度+后台首位后台强度(24%→132%)——前台单核乘法直乘
#   黑天鹅:每个5费角色伤害增幅(5%→28%)——5费成群的高费队最大乘区(5个=+140%)
#   知更鸟:幸运一击率(10%→55%)——暴击引擎(群攻/欢愉/追击)
#   花火:进战5战技点+普攻/战技伤害增幅(12%→66%)——战技点引擎
#   大丽花|加拉赫:击破伤害增幅+治疗强度(12%→66%)——击破专属(效果相同,谁在阵选谁)
#   星徽:每星徽前后台强度(8%→44%)——依赖星徽套组,罕见(不进偏好表)
MEGASTAR_BUFF: dict[str, str] = {
    '知更鸟': '幸运一击率+55%', '花火': '战技点5+普战技伤害+66%',
    '星期日': '前后台首位强度+132%', '黑天鹅': '每5费+28%伤害',
    '大丽花': '击破伤害+66%+治疗', '加拉赫': '击破伤害+66%+治疗',
    '星徽': '每星徽强度+44%',
}
# comp 级巨星偏好(序 = 优先;按「comp 引擎 × 巨星乘区」绑定(详 strategy/02_comp §7),
# 替代旧 3 条属性键粗映射。未列的 comp 走 core/在场优先)
COMP_MEGASTAR_PREFERENCE: dict[str, tuple[str, ...]] = {
    # 前台单核族:carry 站前台 1 号位,星期日 132% 直乘
    '反甲白厄': ('星期日', '知更鸟'),
    '万敌单C': ('星期日', '知更鸟'),
    '命运圣杯红A': ('星期日', '花火'),
    '双王圣杯': ('星期日', '花火'),
    '昼神阿雅': ('星期日', '花火'),
    # 暴击引擎族(群攻/欢愉/追击 = 幸运一击)
    '追击飞霄': ('知更鸟', '星期日'),
    '银枝群攻': ('知更鸟', '星期日'),
    '大黑塔银河学者': ('知更鸟', '黑天鹅'),
    '希儿量子': ('知更鸟', '星期日'),
    '绯英欢愉': ('知更鸟', '花火'),
    '狼尊欢愉': ('知更鸟', '花火'),
    '火花星间旅人': ('花火', '知更鸟'),   # 花火 core;欢愉引擎次之
    # 战技点族
    '龙丹战技点': ('花火', '知更鸟'),
    '列车同行': ('花火', '星期日'),        # 花火 core;姬子前台次之
    # 击破族
    '巡海击破': ('大丽花', '加拉赫', '知更鸟'),
    # 5费堆叠(DoT 队天然堆 5费黑天鹅/卡芙卡;黑天鹅 core 双保险)
    'DOT队': ('黑天鹅', '知更鸟'),
    '专家桑博DOT': ('黑天鹅', '知更鸟'),
}
MEGASTAR_BY_ATTRIBUTE: dict[str, str] = {
    # 兜底(偏好表未列的 comp):comp 机械属性 → 巨星
    '幸运一击': '知更鸟', '击破': '大丽花', '高倍率单核': '星期日',
    '群攻': '知更鸟', '欢愉叠层': '知更鸟', '追击': '知更鸟', '战技点依赖': '花火',
}


def select_megastar(bs: GameState, target: Comp | None,
                    available_megastars: list[str]) -> str | None:
    """选 1 名盛会之星作巨星(盛会之星羁绊核心决策;按 target_comp 选,不单独评分)。

    选择序(按 comp 引擎 × 巨星乘区,详 strategy/02_comp §7):
    1. target.core_chars 里的盛会之星(在阵 core 天然绑定,如追击飞霄×知更鸟);
    2. COMP_MEGASTAR_PREFERENCE[target.name](comp 级偏好序);
    3. 机械属性兜底(MEGASTAR_BY_ATTRIBUTE);
    4. 首个可选(naive)。
    4. 首个可选(naive)。
    候选空 → None;无 target 且候选非空 → 返回首个可选(naive 兜底)。
    """
    if not available_megastars:
        return None
    if target is not None:
        for c in target.core_chars:
            if c in available_megastars:
                return c
        for star in COMP_MEGASTAR_PREFERENCE.get(target.name, ()):
            if star in available_megastars:
                return star
        for attr in target.mechanic_attributes:
            star = MEGASTAR_BY_ATTRIBUTE.get(attr)
            if star and star in available_megastars:
                return star
    return available_megastars[0]


# (select_megastar_enhance「强化角色」意向已随 megastar_enhance_enabled
#  开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;机制语义
#  本就是待证假设(ADR-0482),证据链见原函数注释的 git 历史。)
