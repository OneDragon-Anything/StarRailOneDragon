"""货币战争 阵容库(纯逻辑,可测,不碰游戏)。

战略层:围绕目标阵容 commit + 转型 + 巨星。
auto-chess 胜负手 = commit 哪个阵容 + 何时转型 + 巨星绑谁;本模块给**可配置 + 自适应**的选目标机制。

数据与设计依据(阵容知识源 = ``docs/game/currency_war/research/final_comps/`` 系列 +
``docs/game/currency_war/data/plaza_meta.md``;观察设计正本 = strategy-docs 15 号篇):
- ``COMP_LIBRARY``:起步 roster(20 套;plaza 784 篇高难帖校准)。
  **两层架构**:``cw_plaza_comps.py``(gen_plaza_comps.py 生成)= base 事实层(实战频次/装备/节奏);
  本文件 COMP_LIBRARY = 手判层(level_plan 取舍)—— ``plaza_carry`` 字段
  是两层交叉核对锚点。覆盖易/中/难成型 + 各机制(含 debuff=buff 的燃血、augment 定义型的黑塔纪元)。
(旧 comp_score 多维评分器已随 select_comp 入口整族移除;锁定 = 候选-锁定制。)。

**核心原则(用户 2026-08-03,贯彻全程)**:
1. **一切阵容相关** —— equip/mechanics 都挂钩目标阵容,无孤立评分(不设通用 equip_score/词缀表)。
   反重力皮靴对昼神阿雅(需 2 靴)是命脉、对别的阵容不一定;正当防卫词缀对万敌燃血是利、对阿雅是克。
2. **debuff 可能是 buff** —— 同一词缀对不同阵容方向相反(关系表 = MECHANIC_COUNTERS/SYNERGIES)。
3. **COMP_LIBRARY 多维打分 + 运行时按场面选** —— 不锁死一套,按成型难度/boss/环境/词缀灵活选易成型又够强的。
4. **经济统一论** —— 每阵容自带 ``level_plan``(成型路线),驱动战术层花超额金(接法见 cw_economy 的经济效果拆分)。

**核心/弹性羁绊二分**:``factions`` = 核心羁绊(成型判定);``flex_factions`` = 弹性次要
(plaza 实证「核心保证四列车即可,其他自由搭配」—— 板朝 flex 铺不罚,env/策略亲和照吃)。
**augment 定义型阵容**(:``AUGMENT_COMP_AFFINITY``):黑塔纪元/飞光类棱彩策略拿到即近乎硬绑
(镜像 ENV_COMP_AFFINITY)。**全局过渡池**(:``TRANSITION_POOL``):
plaza Early 六巨头(藿藿/饮月/三月七/爻光/椒丘/艾丝妲),过渡工程(买入分级加权+卖出保留判定)消费。

⚠️ meta(版本依赖):core_chars/form_tiers 是 V4.4 估值(plaza 校准 +
米游社合集 76807134),replay + 实玩迭代。装备 Final-only = plaza UI 限制(时序看合成首选,非玩法事实)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    GiftGrant,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)


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

    核心/弹性羁绊二分(plaza 784 篇实证「核心保证四列车即可,其他自由搭配」):
    ``factions`` = 核心羁绊(form_tiers 键 ⊆ 它;成型判定只看核心);``flex_factions`` = 弹性
    次要羁绊(不进 form_tiers,但板面朝它铺不被 board_alignment 罚、env/策略绑定照常亲和)。
    ``plaza_carry`` = cw_plaza_comps 聚类 carry 名(交叉核对锚点;空 = 无 n≥5 聚类对应)。
    """
    name: str                    # "追击飞霄"/"昼神阿雅"/"万敌单C"(roster 单一源 = 本注册表)
    factions: list[str]          # 核心阵营组合 ["追击"](查 FACTIONS)
    core_chars: list[str]        # 核心角色(名)["飞霄","知更鸟"]
    form_tiers: dict[str, int]   # 成型 tier 目标 {"仙舟":5,"追击":3}(几人激活算成型;键 ⊆ factions)
    level_plan: dict[int, LevelGoal] = field(default_factory=dict)  # 成型路线(玩家等级→该做什么);建库时填
    key_equips: list[str] = field(default_factory=list)      # 关键装备(可含重复,如阿雅需 2 反重力皮靴)
    shared_chars: list[str] = field(default_factory=list)    # 与其他阵容共享的 core(转型可复用)
    transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)
    # 阵容特定站位要求(角色→"front"/"back"),覆盖注册表 position_pref 默认
    # (CW 玩法每角色的可选站位真值,cw_chars.position:技能效果绑定站位)——
    # 攻略实证:爻光必后台(绯英攻略反向论证:后台跑条给前台多开大,总伤更高)、万敌独前排(燃血吃受击)、
    # 知更鸟前台(追击支撑)。空 = 全按注册表默认。
    char_positions: dict[str, str] = field(default_factory=dict)
    version_tag: str = "V4.4"    # 版本维护用
    flex_factions: list[str] = field(default_factory=list)  # 弹性次要羁绊(不进 form_tiers)
    plaza_carry: str = ""        # plaza 实战聚类 carry 名(交叉核对锚,查 cw_plaza_comps.cluster_by_carry)

    # ===== 字段扩(C4 契约冻结语义;leader 裁决)=====
    # 字段语义冻结;各套填值草案级(流派统计刷新可再改)。教义级内容(禁忌/铁三角/替班不卖)
    # 逐条对 final_comps 各篇(research/final_comps/)原文,不自创。
    family: str = ''                # v2 家族键(9 家族;长尾套 'legacy' 保活不删,旧策略 C5 兼容)
    sub_tiers: dict[str, int | tuple[int, int]] = field(default_factory=dict)
    """副档目标档深(参与完成度;升格过半线锚)。键 = 羁绊规范名,**不得**与 form_tiers
    键重复(那是主档);值 int 或 (下限,上限) 区间。"""
    substitute_plan: list[dict] = field(default_factory=list)
    """替班结构(C4 冻结语义:替班=「不卖、转副C沉淀」):每项
    ``{'替班者': str, '顶位': str, '身份': str(到岗后), '分岔点': str}``。
    卖出型打工归全局 TRANSITION_POOL(transition_chars 兼容视图),不进本字段。"""
    equip_assign: dict[str, list[str | EquipChoice]] = field(default_factory=dict)
    """装备到人(C4 最大新增):角色名 → 装备序列(str=fixed 首选 / EquipChoice 两档)。
    键 ⊆ core_chars ∪ shared_chars ∪ substitute_plan 替班者;**本字段一旦非空,
    ``key_equips`` 必须恒等于 ``derive_key_equips(comp)``(C5 兼容地基,恒等测试)。"""
    equip_taboos: list[str] = field(default_factory=list)
    """本套禁买禁合成装备/装备类(教义手编,官方机制原文;如万敌禁一切护盾件)。"""
    bond_signal: str | None = None
    """②类专属羁绊信号名(cw_intention detect_signals 层②消费)。
    值 = 该家族的「专属羁绊」规范名;**按设计无②信号
    的家族(希儿量子:量子/贝是放大器;白厄反甲:独立羁绊绑死单卡)= None**。"""

    # ===== 形态端口:OR 分支 + carry 在场条件 =====
    # 两字段缺省空 = 行为不变。生产写入方 = cw_intention.pair_target_comp
    # 希儿系对分支(P1 配方锁伪阵容)+ COMP_LIBRARY 静态套「希儿量子」
    # (P2+ 锁定路径经 get_comp 消费静态条目;档位单一源 =
    # SEELE_OR_REQS/SEELE_CARRY_CHAR)。判定/进度唯一折法 = ``form_progress``
    # (单一源契约 fp=1.0 ⟺ 成型谓词),禁消费位绕过自写 AND/OR 内联判定
    # (判据单一源契约)。
    or_reqs: list[tuple[str, int]] = field(default_factory=list)
    """OR 分支(析取档组):组内**任一** (羁绊, 档) 达成即该组算满——文档
    「凑到任一=成型,不设完全体门槛」(transition_combos.md:27 希儿系定义
    行;combo_methodology.md:133)。空 = 无 OR 分支(纯 AND)。进度折法:OR 组
    折叠为一条虚拟分支,分支值 = 组内各分支进度 max(取最好分支非均值,「任一即成」
    的进度语义;换最好分支只单调抬升无重置)。**OR 组承接同键档位**:键出现在
    本字段的 ``form_tiers`` 档位不入 AND 账(该键成型语义归 OR 组;档位值
    保留作线键/完全体账单结构载体——囤货采购集羁绊展开、晋升候选键面交集、
    换线距离账等结构消费读 form_tiers 键面,清空即残)。禁把 OR 分支当 AND
    写进 ``form_tiers`` 计账(键侧 AND 语义会把 OR 塌回 AND 全档——前置命题
    病灶本体)。"""
    required_deployed: tuple[str, ...] = ()
    """carry 在场条件:逐一必须**在板**(deployed;bench 在手不算)——文档
    成型判据第一合取支「希儿在场」(transition_combos.md:27)。空 = 无
    carry 条件。进度折法:逐名折一条 0/1 虚拟分支(在板=1 否则 0);state
    缺 deployed 视图的轻量假想面板按 0 计(保守向,缺读≠满成)。"""

    # ===== 知识卡字段(选线/升级/窗口适用范围的共用知识地基;设计口径 =
    # strategy-docs/12_line_and_intention.md §1)。玩法知识(终局阵容的客观
    # 定义——攻略数据,换策略不变其值),非策略层立场数据(宪法第 5 条对账
    # 申报见 12 号篇 §1.1)。=====
    lock_rules: dict[str, list[str]] = field(default_factory=dict)
    """每线锁定条件(候选-锁定制硬规则查表;12 号篇 §1.3;锁定判定单一消费端 =
    mandate_v1/line_select.hard_lock_hit_lines)。
    键固定两枚,值均为注册表 canonical 名:
    - '策略型':强关联策略/环境名(``cw_invest_data`` PLAZA_AUGMENTS/PLAZA_PORTALS 键;
      augment 与 portal 混编——§1.4 例本身含概念股/圣杯契约)——**任一**到手即命中。
      登记口径 = ``ENV_COMP_AFFINITY``/``AUGMENT_COMP_AFFINITY`` 亲和 ≥0.7 条目 +
      final_comps 各篇「类专属策略」明文 + 注册表效果文本直赠线核心的条目;通用
      经济/装备件(超光速提拔/公司军火更新类)与阵营徽章不登记。策略-线关联
      单一源 = 本字段(亲和表保留评分用途;锁线级关联以本表为准)。
    - '角色型':'「核心到手」组合成员名单(线核心输出位 + 攻略明示关键骨架)——
      **全员**在手即命中;件数由攻略语义定(查表登记,非连续阈值)。名单坐标系 =
      角色规范名(``cw_chars.CHARACTERS`` 键,与 ``core_chars`` 同名空间);取值时机 =
      建库静态登记。
    单帧判定单一源 = ``char_lock_hit``/``strategy_lock_hit``(禁消费位自写子集判定
    ——判据双源);空列表 = 该线无此型条件(锁定走另一型或时点兜底,12 号篇 §1.3 表)。"""
    need_star: dict[str, int] = field(default_factory=dict)
    """每角色必要星级(锁定后星级目标单一源;12 号篇 §1.4;停留门/
    刷新判据消费)。键 = 角色规范名(线终局成员:核心输出位 + core_chars +
    攻略明文星级成员),值 = 必要星级;定义 3★ 就追到底无降档、定义 2★ 即完成
    (12 号篇 §1.4)。定值规则:核心输出位按线攻略明文,无明文线按星级饥饿两档表拍定
    (final_comps README A4:高饥渴线 Final 3★ 占 80-94% 标 3★/低饥渴线 ≤2★ 过半
    标 2★);辅助 1★(A4 辅助普适档——D 牌预算全落核心,辅助升星只吃自然来牌);
    攻略明文更高者以明文为准。对拍基准 = ``level_plan`` 各级 ``star_goals`` 并集
    (冲突以攻略重述为准;star_goals 保留为对拍基准不进决策链,消费单一源 =
    本字段——12 号篇 §1.1 双源申报)。"""
    key_items: list[str] = field(default_factory=list)
    """骨架件/贯穿件名单(持有证据分的中档;12 号篇 §1.1;候选分数消费)。
    坐标系 = 角色规范名;数据源 = final_comps 各篇构造机理「槽位构造」的引擎/贯穿/
    常驻件登记(线核心输出位以外的结构成员,可含 shared/transition 层的贯穿件——
    姬子线饮月类)。与 CARRY 档成员全集(``carry_set`` 合流口径)可能相交,持有
    证据分档的消费序归线分数(12 号篇 §1.1)。插件档 = 线成员 − CARRY − 本名单(派生,不入表)。"""
    entry_signals: dict[str, tuple[str, int]] = field(default_factory=dict)
    """上线窗口信号表(部署窗口辖域数据地基;22 号篇 §1 第 6 步;
    [21] 2026-08-26 定谳「该角色的羁绊组齐了才上」的形式化载体——单上
    没什么作用,凑够羁绊才上去替换,保证战斗力)。键 = 角色规范名(线
    终局成员 core ∪ shared),值 = ``(信号类, 阈值)``,信号类闭集:
    - ``'synergy'``:该线主羁绊(``bond_signal``;缺省取 form_tiers 首键)
      板面计数 ≥ 阈值 → 窗口到——定谳主形态,阈值 = 主羁绊成型档
      (form_tiers);白厄 4 击破齐原型([21]);
    - ``'level'``:玩家等级 ≥ 阈值 → 窗口到(核心等级窗,值域保留——
      现表无登记行,[21] 定谳后孤立等级数字不独立作窗);
    - ``'plane_end'``:终局位面段已启动(窗口谓词形态,消费端 =
      ``session_scope.plane2_started_of``;满编后期形态线,README C4
      「白厄 B 套特权反甲 = 满编后期的常态」)→ 窗口到;
    - ``'always_on'``:恒可上——「前期 = 终局同体」线成员
      ([21]「越早越好」;bond_signal 行内注释在案),阈值不消费(占 0)。
    fail 读法:缺行(角色无登记)→ 窗口谓词恒假 = 窗口永不到(纯终局件
    只囤不上,保守侧,22 号篇 §1 第 6 步 fail 方向声明)。判定消费端
    = mandate_v1 部署窗口辖域(数据 kernel / 判据策略层,宪 5 合宪申报
    同知识卡三字段)。"""
    member_priority: dict[str, int] = field(default_factory=dict)
    """阵容内成员优先级序数表(档 2/3/4/5/7 档内①键的知识卡单一源;序数取值
    规格正本 = strategy-docs/32_unified_sell_priority.md §2,
    消费端 = mandate_v1/criteria/priority.py 装配)。
    键 = 角色规范名(线终局成员 core ∪ shared),值 = 序数,
    **小 = 优先级高**(与统一价值序「档位编号小 = 优先级高」同轴)。
    迁移期形态【拍】= core 0/其余 1(:func:`derive_member_priority`
    按 core_chars 派生,本字段不逐行手编;逐角色线内全序精调外溢
    下一迭代)。空表由 ``__post_init__`` 落成即派生补齐——每个 Comp
    实例(含 pair_target_comp 配方伪阵容)都带显式字段,「隐式两档 →
    知识卡显式字段」的数据迁移本体;显式登记非空则原样保留(精调
    迭代的填值载体)。跨线成员的合成(取最高优先)在消费端装配,
    本字段只承载单线内取值。版本联动:阵容重跑时随知识层重核
    (compo-knowledge 版本重跑流程清点范围)。"""

    def __post_init__(self) -> None:
        # 迁移期默认派生:空表 = 建库未显式登记 → 按 core_chars 两档
        # 补齐(非空 = 精调登记,不覆写)。派生在构造期完成,消费端
        # 经 member_rank_of 读到的恒是显式表。
        if not self.member_priority:
            self.member_priority = derive_member_priority(self)

    @property
    def all_factions(self) -> set[str]:
        """核心 + 弹性羁绊全集(亲和/过滤/板面判定用;成型判定仍只看 form_tiers)。"""
        return set(self.factions) | set(self.flex_factions)


def derive_key_equips(comp: Comp) -> list[str]:
    """key_equips 派生汇总(C4 降级 + C5 保活;**建库顺序地基:先本函数后动数据**——裁决 2)。

    语义(C4 冻结):key_equips 不再是独立维护字段,而是 equip_assign(装备到人)的
    投影——「汇总 + 去到人」:
    - equip_assign **为空**(长尾/未迁移套)→ 返回旧手编 ``comp.key_equips`` 原值
      (C5 兼容:旧策略/旧测试读它不炸);
    - equip_assign **非空** → 按字典序展开:fixed 条目原样,pool 条目贡献**全部候选**
      (候选池内每件都是关键件,黄泉第四件类), EquipChoice 展开顺序 = choices 优先序。

    恒等约束(C5 冻结):``comp.key_equips == derive_key_equips(阵容)`` 对全库成立
    (多重集口径——合成材料判定消费为多重集语义;顺序仅影响 equip_allocation
    的 carry 按序取件微差)。恒等测试此不变量,任何一侧单独改动即测试红(防双源漂移)。
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


def derive_member_priority(comp: Comp) -> dict[str, int]:
    """成员优先级两档派生(迁移期默认形态:core 0/其余 1)。

    数据依据 = 统一让位优先级迭代 design §2.1.1【拍】:本迭代先按
    core/shared 二元标记映射两档,逐角色线内全序精调外溢下一迭代。
    同名双列(core_chars 与 shared_chars 交集,列车同行三月七类)
    core 优先——序数小 = 优先级高,与旧装配「0 if n in cores else 1」
    的并集口径一致(迁移前后等价的基准式)。"""
    rank: dict[str, int] = dict.fromkeys(comp.core_chars, 0)
    for n in comp.shared_chars:
        rank.setdefault(n, 1)
    return rank


def member_rank_of(comp: Comp) -> dict[str, int]:
    """成员优先级序数表读口(字段直读 + 旧数据回退;档 2/3/4/5/7 档内①键
    单一源,消费端 = mandate_v1/criteria/priority.py 装配)。

    - ``member_priority`` 非空 → 字段直读副本(防消费位原地改写注册表
      内表);
    - 空表(旧数据/未走构造器派生的动态形态)→ :func:`derive_member_priority`
      两档回退——消费端无需感知字段新旧,向后兼容。
    """
    if comp.member_priority:
        return dict(comp.member_priority)
    return derive_member_priority(comp)


MECHANIC_COUNTERS: dict[str, list[str]] = {
    # 机制 tag → 它克制的阵容机械属性
    "反伤": ["高频低单次"],        # 正当防卫:克高频低单次(反甲白厄式)
    "冻结": ["慢速", "战技点依赖"],  # 极速制冷/坠入陷阱/冷冻冬眠:克慢速 + 战技点消耗队
    "净化": ["DoT", "减益"],       # 净化身心:克 DoT/减益主派(消费 = 策略层 pick_common.counters_dot 自拆台排除,机制注册表单一源)
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
    # 机制 tag → 它受利的阵容机械属性(用户:debuff=buff)
    "反伤": ["燃血"],             # 正当防卫:反伤让燃血掉血 → 角斗场记录 → 伤害更高(万敌例,debuff=buff 典型)
    # 观测对:词缀方向真实(高费 +5%/低费 -5%,V4.4),但 mechanics_fit
    # 最细步进 0.20 ≈ 20% 级战力差,±5% 差异打成 0.2 步进=离散 tag 系统性过反应 ×4,会把本该
    # 近中性的选型扰动成硬 flip。挂重审条件:①出现费用差异化幅度 ≥15% 的词条;②comp_score
    # 引入连续费用分布通道使粒度错配消失。届时阈值推导按「决策规则数学先行」补出处。
    "高费审美": ["高费队"],       # 高费审美:4 费及以上 +5%(V4.4)
    "低费审美": ["低费队"],       # 低费审美:3 费及以下 +5%(V4.4)
    # ⚠️ 形单影只只建模了「免罚」半边:词条另一半 = 伤害 85%/60%/30% 落在**未激活羁绊方**
    # (1/2/3 个未激活羁绊的板,即未凑羁绊的队),该侧当前零载体零 counter 行——
    # 未成型侧伤害倍率未建模,见 攻击报告(形单影只角度)。
    # 机制后果:「单挂队」词汇不存在于携带词汇表,cw_events 避险判据(全 counter + fit<0.4
    # 刷新换批)对全表伤害量级最大的词缀反而永不触发。待办:单挂队 tag 建模待聚类型判据批
    # (未激活羁绊数可从 factions/form_tiers 推导,但逐套判型需板面档位数据,另立批勿顺手打)。
    "成型羁绊利好": ["成型羁绊队"],  # 形单影只:羁绊全则不受罚(V4.4)
    "皮糙肉厚": ["击破"],          # 皮糙肉厚:未被击破受伤-30% → 利击破阵容(击破流萤 不受罚)
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
    "紧急止血": "爆发机会",   # 保留透传:tag「爆发速杀」无阵容携带,
    # 此行映射后求交恒空=零行为;重立时只需回补行。
    "高费审美": "高费审美", "低费审美": "低费审美",
    "形单影只": "成型羁绊利好",   # 未成型侧(-70% 落未激活羁绊方)未建模,见 MECHANIC_SYNERGIES 同 tag 注记
    # 属性熄火(7):对应属性我方伤害 1 点(4 次后解除),克纯色队
    "风之熄火": "属性熄火", "火之熄火": "属性熄火", "冰之熄火": "属性熄火",
    "雷之熄火": "属性熄火", "物理熄火": "属性熄火", "量子熄火": "属性熄火", "虚数熄火": "属性熄火",
    "皮糙肉厚": "皮糙肉厚",   # 利击破阵容(未被击破受伤-30% → 击破流不受罚)
    "榜样激励": "榜样激励",   # 克单核(伤害第一的 75%)
    "忍无可忍": "多段惩罚",   # 敌受 7 次攻击提前 100% → 克高频低单次(反甲白厄)
    "沉重脚步": "行动延后",   # 受击行动延后 8% → 克速度依赖
    # 其余词缀(首领强化/复仇心切/倒计时类/灼热轰炸等)为纯数值/无阵容交互(灼热轰炸:前排受击+DoT
    # 均匀影响,无阵容翻转),不入表;实机 OCR 按需补
}

def merged_mechanic_tables(registry: DecisionV2Registry | None = None,
                           ) -> tuple[dict[str, str], dict[str, list[str]], dict[str, list[str]]]:
    """生效机制三元组(词缀映射/克制/受利)= 基表直通。

    (保留本函数签名,消费点 mechanics_fit /
    cw_events / cw_intention 调用零改。``registry`` 参数保留占位,
    不再参与取值。)
    """
    return AFFIX_MECHANIC_MAP, MECHANIC_COUNTERS, MECHANIC_SYNERGIES


# ===== 环境 → 阵营/阵容亲和(P1-2 T0 env 近乎硬绑 + R2-9 env→faction)=====
# 库藏生锈词缀名(`w607_affix_consumption/` H2 消费钩子的词条识别名):备战席每 1 件未穿装备 →
# 敌方造成伤害 +3%、受到伤害 -4%,最多计 10 件
# (docs/game/currency_war/data/competitors.md:45,2026-08-28 游戏内实采)。
RUST_AFFIX_NAME: str = '库藏生锈'


# ENV_FACTION_MAP 从投资环境注册表派生(单一真相源:概念股/邀请的 faction 字段;改注册表自动传导)
ENV_FACTION_MAP: dict[str, list[str]] = {
    name: [e.faction] for name, e in INVESTMENT_ENVS.items() if e.faction
}
ENV_COMP_AFFINITY: dict[str, dict[str, float]] = {
    # T0 env → {comp_name: 亲和权重} —— 拿到应近乎硬绑该阵容(research §10.3:env 是 run 内最大单一决策)
    "昼之半神概念股": {"昼神阿雅": 1.0},   # 送阿雅+鞋+刷新率 → 近乎硬绑昼神
    # ↓ (plaza 784 篇 portal 频次校准):概念股/邀请 = 定向阵容近硬绑;契约 = 中亲和
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
# :augment 定义型阵容绑定表(镜像 ENV_COMP_AFFINITY 机制;投资选卡方向分消费)。
# plaza 实证:这类阵容的入口是「拿到棱彩策略」而非阵营成型 —— 黑塔纪元 35 篇整族围绕它构建。
# 键 = 注册表策略名(canon);值 = {comp_name: 亲和 0..1}(1.0 = 拿到即近乎硬绑)。
AUGMENT_COMP_AFFINITY: dict[str, dict[str, float]] = {
    "黑塔纪元": {"大黑塔银河学者": 1.0},   # 216 张黑塔入商店 + 追击转圈 → 阵容由它定义
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
    静默 miss → 定义型阵容解锁/评分失效。所有持卡名/候选名查本表一律走此函数,
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


# 全局过渡池(按跨阶段存活率拆两级;plaza 784 篇 P(进终局|Early在场) 实证):
#   EARLY_CORE_POOL(存活 ≥0.8):「有体系牌来就拿下」—— 买了就是开局(期权重叠,不存在过渡浪费);
#   TEMPO_POOL(存活 <0.45):纯保血打工(骨架件)—— 1星买卖近无损,毕业即卖(1-8 分界换人)。
# 消费方:过渡工程(买入分级加权 + 卖出保留判定)—— 接线前是数据先验,勿删。
EARLY_CORE_POOL: list[str] = [
    "千冶·刃",   # 存活 0.96,Early 174 篇 —— 断层级早期核心
    "姬子·启行", "远坂凛", "丹恒·腾荒", "缇宝", "三月七", "花火",
]
TEMPO_POOL: list[str] = ["藿藿", "丹恒·饮月", "爻光", "椒丘", "艾丝妲", "卡芙卡"]
# 兼容旧名(过渡池并集)
TRANSITION_POOL: list[str] = EARLY_CORE_POOL + TEMPO_POOL


# (CORE_SINGLE_CARD_REGISTRY 直通终局线单卡依赖型核心登记已随 C1
#  单卡核心囤积规则退役删除——统一让位优先级迭代 3.4,总纲 §2.5:
#  C1 直购支配性支/恒买腾位/买面保护消费全退役后该登记无生产消费面,
#  随批退役;登记值 = 知识判据出处指针,沿革与排除举证见 git 历史。)


# ===== 角色↔路线复用网络(「整体灵活」建模;plaza 实证)=====
# 方法论(用户 2026-08-16):角色池 75 个、plaza 聚类 29 个、羁绊组合 427 种 —— 多样性本身就是玩法。
# 玩家在「角色→路线」复用网络上动态导航,不是「选一套阵容配齐它」。两个消费点:
#   ① 买牌:枢纽角色(跨路线复用度高)拿了不亏 —— plaza 终局枢纽:千冶·刃28条路线/瓦尔特26/符玄26/
#      缇宝24/花火22/开拓者·记忆17/星期日15;早期枢纽:藿藿10路线+265次Early出场/饮月/爻光/椒丘。
#   ② 板面:早期骨架 = 便宜枢纽 × 低门槛羁绊(见 skeleton_factions)。

def char_routes() -> dict[str, set[str]]:
    """角色 → 可走路线(阵容名)集合 —— 从 COMP_LIBRARY 派生的复用网络(core+shared 计入)。

    transition_chars 不计(那是打工后卖的,不构成路线;core/shared 是终局成员)。
    枢纽度 = len(routes);买牌 optionality / 卖牌保留判定消费。
    """
    routes: dict[str, set[str]] = {}
    for comp in COMP_LIBRARY:
        for c in set(comp.core_chars) | set(comp.shared_chars):
            routes.setdefault(c, set()).add(comp.name)
    return routes


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
# methodology.md:133/170 写量 3)挂玩家确认(同一待办口径,不由
# 实现批裁决),确认后改档动本常量(配对消费位随 import 自动跟随),
# **另须同步第三表面** `_seele_system_support` 的 ÷2 分母(待办指针 =
# cw_intention._seele_system_support docstring「同步回改本式分母」节;
# 公式体用字面量 2 不消费本常量,接线守卫钉不住,漏改=两端口档位漂移)。
# carry = 同表行第一合取支「希儿在场」。
# ⚠️ 单一源归属声明:真源归位本文件(注册表数据层——静态套
# 条目在 import 期消费,常量若留 cw_intention 会反向 import 成环)。
# cw_intention 经顶部 import 消费本常量(re-import 别名,其形态端口注
# 「禁再写本地第二份」),单一源接线由测试仓接线守卫钉死(对象身份 `is`,
# 本地第二份复发即红)。
SEELE_OR_REQS: tuple[tuple[str, int], ...] = (('量子同频', 2), ('贝洛伯格', 2))
SEELE_CARRY_CHAR: str = '希儿'

COMP_LIBRARY: list[Comp] = [
    # ===== S 级(版本真神,V4.4 合集 76807134)=====
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/final_jizi_train.md(游戏知识,非字段镜像,无同步义务)
        name="列车同行", factions=["列车同行"], core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        form_tiers={"列车同行": 4},
        # V4.4 权威评级(76807134):姬子·启行 = S 级真神;A850 挂机流(76824096):全程自动/不凹开局/适应任何负面环境 → bot 默认首选
        # 成型 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝
        # (plaza 784 篇校准):carry 274/在场 358 篇断层级第一;双分支 —— 护盾流(152 篇,姬子带
        # 以牙还牙甲+砂金)/减益流(127 篇,冷笑话引擎+彦卿);flex_factions 全收(plaza 羁绊分布)。
        # 装备 top:风暴潮352/电锯190/以牙还牙甲116/冷笑话56 → 双风暴+电锯+以牙还牙(跨分支覆盖)。
        flex_factions=["护盾", "减益", "战技点", "量子同频", "盛会之星", "能量", "星间旅人"],
        plaza_carry="姬子·启行",
        key_equips=["火力风暴潮", "高周波电锯", "自适应外骨骼", "冷笑话引擎"],
        # 教义 A 流铁三角=三月七 自适应外骨骼(吸仇恨刚需)/姬子 以牙还牙甲×2-3;
        # 恒等约束(多重集不变)下以 A 流首选件(外骨骼)入表。B 流拆分放开恒等时
        # 姬子侧补 以牙还牙甲×2。
        # 成型羁绊队:战力=列车同行4 档乘区(评分求交侧已随评分器族删除,知识载体 = MECHANIC 表)
        shared_chars=["三月七", "花火", "瓦尔特"], transition_chars=["符玄", "艾丝妲"],
        # ===== 姬子列车家族(A/B 未拆条——分岔变量=词条前置:敌方多动旺→A 反震/怕词条在→B 输出)=====
        family="姬子列车",
        bond_signal="列车同行",   # ②类信号:四人 100% 固定
        sub_tiers={"护盾": 2, "减益": 2},   # A 流护盾2(50% 盾循环必然)/B 流减益2(58%)——分支依赖,拆分归位
        equip_assign={"姬子·启行": ["火力风暴潮", "高周波电锯"], "三月七": ["自适应外骨骼"], "花火": ["冷笑话引擎"]},
        # ↑ 教义 A 流:三月七=自适应外骨骼(吸仇恨刚需;甲属姬子 A 流×2-3)。
        # B 流完整配装留 A/B 拆分落位
        # 吸仇恨互斥的攻略行(不要杰帕德)已停用 PLUGIN_DISABLE_MATRIX
        # (4/300 局触发、无劣化;官方机制行保留),此处不再指向矩阵防悬空引用
        substitute_plan=[
            {"替班者": "瓦尔特", "顶位": "姬子·启行 主C(姬子未 3★ 时)", "身份": "2★ 杨叔主C,装备转杨叔", "分岔点": "姬子 3★ 达成即交还"},
        ],
        level_plan={
            3: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七"], star_goals={"三月七": 2}),
            4: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "花火"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"),
            # (阵容_列车同行:53):**停留 7 级猛 D 3星姬子**(3费 7 级概率
            # 峰值 p=0.40)—— 旧 7=level_up 直冲 8 违背「核心概率级停留」人玩节奏。
            7: LevelGoal("roll", target_cost=3, target_chars=["姬子·启行", "三月七", "花火"],
                         star_goals={"姬子·启行": 3}),
            8: LevelGoal("roll", target_cost=0, target_chars=["姬子·启行", "花火", "瓦尔特"],
                         star_goals={"姬子·启行": 3, "花火": 2}),
            # (旧「缺 lv9 → 落通用曲线 stable 零 D」回退已停用(_DEFAULT_LEVEL_
            # GOAL,「未证即停用」裁定),lv9 无 plan 时仅节点地板覆盖;显式 lv9 roll
            # 保留:5费概率高,找 瓦尔特/花火 升星,姬子顺带。)
            9: LevelGoal("roll", target_cost=5, target_chars=["姬子·启行", "花火", "瓦尔特"],
                         star_goals={"姬子·启行": 3, "花火": 2}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_jizi_train.md)=====
        lock_rules={
            # 类专属策略信号最强一类:概念股 130/388+邀请 90(构造机理§3 开局信号层);
            # 罗刹开局=策略改变三月七身份（直通线信号谱「策略驱动」层）
            '策略型': ['列车同行概念股', '列车同行邀请', '本姑娘就是罗刹'],
            # 引擎核心组=姬子·启行(388 篇 100%)+三月七(76%,引擎触发器;领航员
            # 必绑 85%+ 共识)——「核心到手使过渡板保留率翻倍」的最小组合(§3)
            '角色型': ['姬子·启行', '三月七'],
        },
        need_star={
            # 姬子 3★=「停留 7 级猛 D 3星姬子」(升星非线性回报,§1 第二环)+A4 姬子 74;
            # 三月七/花火 2★=level_plan star_goals 攻略口径;瓦尔特辅助普适档 1★(A4)
            '姬子·启行': 3, '三月七': 2, '花火': 2, '瓦尔特': 1,
        },
        # 骨架=三月七(引擎触发器/贯穿件)+饮月(仙舟∩列车焊点,构造机理§2 贯穿件行)
        key_items=['三月七', '丹恒·饮月'],
        # 上线窗口(4.0b 同批建表;[21] 定案「羁绊组齐才上」主形态):
        # 主羁绊 bond_signal=列车同行,成型档 4 → synergy 4
        entry_signals=dict.fromkeys(('姬子·启行', '三月七', '花火', '瓦尔特'), ('synergy', 4)),
    ),
    Comp(
        name="命运圣杯红A", factions=["命运圣杯"], core_chars=["Archer", "远坂凛"],
        form_tiers={"命运圣杯": 3},
        # V4.4 评级(76807134):Archer 95 = S 级真神;攻略(76924524):高倍率九五核心+远坂凛+圣杯→+150%攻击+战技点
        # ⚠️ core_chars 用图鉴规范名:"Archer" 非"红A"(OCR/char_id 匹配靠 cw_chars.CHARACTERS 注册表)
        # (plaza 62 篇):3星率 0.18(5费 carry 常驻 2 星);速升9级节奏为主
        # 交叉核对注(费用勘误):圣杯四人 = Archer 5费/Saber 3费/吉尔伽美什 2费/远坂凛 1费(注册表),
        # 旧注释「4 个 5 费成型难」错 —— 费用阶梯宽,成型难度主要在 Archer 本体。
        flex_factions=["战技点", "量子同频", "列车同行", "能量", "治疗", "盛会之星"],
        plaza_carry="Archer",
        key_equips=["火力风暴潮", "动能激发剑", "动能激发剑", "碎星斩舰刀"],   # 交叉核对注:plaza 风暴潮87>电锯45(≈2:1)顺序倒置修正+补动能激发剑22(#3)
        # ↑ 教义:Archer=**战技点件**(动能激发剑:回合开始+消耗各回 1 战技点,
        #   战技点燃料层主C 的本命件)。闪闪侧(反重力皮靴)在双王条目同步
        # 榜样激励克高倍率单核(关系载体 = MECHANIC_COUNTERS 表)
        shared_chars=["远坂凛", "瓦尔特"], transition_chars=["符玄", "知更鸟", "花火"],
        # ===== 圣杯双C家族 A Archer 战技点线(燃料线官方接力结构)=====
        family="圣杯双C",
        bond_signal="命运圣杯",   # ②类信号:2 档开任务=燃料线入口
        substitute_plan=[
            {"替班者": "Saber", "顶位": "Archer 主C(前中期)", "身份": "Saber 打到 Archer 到手;Archer 不来则 Saber 一直 C(任务系统照吃)", "分岔点": "Archer 任务完成"},
        ],
        equip_assign={"Archer": ["火力风暴潮", "动能激发剑"], "远坂凛": ["动能激发剑"], "Saber": ["碎星斩舰刀"]},   # Saber 键经 substitute_plan 容纳(替班者)
        # ↑ v2:Archer=战技点件(动能激发剑;远坂凛同持第二把,战技点燃料层教义)
        level_plan={  # 5费 Archer 是唯一高费门槛:前期低费过渡保血 → 升 8-9 找 Archer(2星即战力,0.18 三星率);交叉核对注:远坂凛 1费
            4: LevelGoal("roll", target_cost=1, target_chars=["远坂凛"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=5, target_chars=["Archer", "远坂凛"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["Archer"], star_goals={"Archer": 2}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_grail_dual.md)=====
        lock_rules={
            # 类级信号最强:契约=完成两次试炼固定得 Archer(供给结构改变,构造机理§3)
            # +邀请 54/196;星徽 47/「都是这家伙的错!」30(同节 196 篇口径;
            # 底稿开局策略节数字为 26/21,118 篇口径——引用按口径区分)
            '策略型': ['命运圣杯契约', '命运圣杯邀请', '命运圣杯星徽', '都是这家伙的错！'],
            # A 线核心=Archer(任务系统产出,到手即接棒)+远坂凛(81%,体系粘合剂/触发器)
            '角色型': ['Archer', '远坂凛'],
        },
        need_star={
            # Archer 2★=「红A必须得有二星」出手门槛(#68)+A4 Archer 71% 低饥渴线;
            # 远坂凛 1★=「1星即够」(构造机理§2 触发器行,1星占绝对多数)
            'Archer': 2, '远坂凛': 1,
        },
        # 骨架=远坂凛(触发器)+花火/刻律德菈(战技点线燃料生产端,构造机理§2)
        key_items=['远坂凛', '花火', '刻律德菈'],
        # 上线窗口:主羁绊 bond_signal=命运圣杯,成型档 3 → synergy 3
        entry_signals=dict.fromkeys(('Archer', '远坂凛', '瓦尔特'), ('synergy', 3)),
    ),
    # ===== A 级(版本强势,V4.4 合集 76807134)=====
    Comp(
        name="千冶减益", factions=["减益", "星核猎手"], core_chars=["千冶·刃", "瓦尔特", "卡芙卡", "缇宝", "符玄"],
        form_tiers={"减益": 4, "星核猎手": 2},
        # plaza 聚类 千冶·刃 n=29(减益26/星核19/燃血13/量子13/列车12):减益通用板大族,此前无承接
        # (29 篇里最多 5 篇可被既有阵容覆盖,交叉核对注点名)。千冶·刃(2费) carry,瓦尔特 24/29+卡芙卡 16
        # +缇宝 15+符玄 14 常驻减益辅助群;皮靴 30 断层第一(carry 吃鞋)+风暴潮 14+螺旋桨 13;
        # 节奏 6级搜牌 12/29(2费 → 6级停)→7级 7 → 速升9 4(瓦尔特 5费);与黄泉减益(3费/7级)错位。
        key_equips=["反重力皮靴", "火力风暴潮", "光速螺旋桨", "反卫星狙击枪"],   # 成型羁绊队:减益4 档乘区为战力主体
        shared_chars=["黄泉", "花火", "不死途", "开拓者·记忆", "椒丘"],
        transition_chars=["椒丘", "风堇", "开拓者·记忆"],
        family="legacy",
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
        # ===== 知识卡字段(长尾线无 final_comps 专篇,数据源=本条 plaza 校准注 n=29)=====
        lock_rules={
            # 减益通用板无类专属策略(无千冶专篇;减益星徽=通用阵营徽章,效果文本
            # 无线定义语义)——锁定走角色型/时点兜底
            '策略型': [],
            # 千冶·刃 carry(n=29 聚类)+瓦尔特 24/29 次高常驻(本条 plaza 校准注)
            '角色型': ['千冶·刃', '瓦尔特'],
        },
        need_star={
            # 千冶·刃 3★=A4 高饥渴线 94%(饥饿表榜首);其余辅助普适档 1★(A4)
            '千冶·刃': 3, '瓦尔特': 1, '卡芙卡': 1, '缇宝': 1, '符玄': 1,
        },
        # 骨架=plaza n=29 常驻辅助群(瓦尔特 24/卡芙卡 16/缇宝 15/符玄 14,本条注)
        key_items=['瓦尔特', '卡芙卡', '缇宝', '符玄'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(减益),档 4
        entry_signals=dict.fromkeys(('千冶·刃', '瓦尔特', '卡芙卡', '缇宝', '符玄', '黄泉', '花火', '不死途', '开拓者·记忆', '椒丘'), ('synergy', 4)),
    ),
    Comp(
        # 主羁绊(依据=final_feiying_joy.md 类结构三处一致:
        # 「欢愉4-7 + 星间旅人(25/25 双100%)……星间旅人2-3 + 仙舟3/能量3 挂件」)——能量降挂件
        # (进 flex),星间旅人升主羁绊(下限 2 档,成员=绯英本人在 core 即可达成)。
        name="绯英欢愉", factions=["欢愉", "星间旅人"], core_chars=["绯英", "瓦尔特", "爻光", "开拓者·欢愉", "符玄"],
        form_tiers={"欢愉": 4, "星间旅人": 2},
        # 欢愉下限 4 = 教义「欢愉 4-6 档(≤4 档即主流)」;档位谱真值 = FACTIONS.tiers
        # V4.4 评级(76807134):绯英 = A 级;攻略(76806732):绯英大招永久+2%伤害(无限成长),3欢愉+3能量+2量子+2减益
        # 前期狼尊开 3 欢愉过渡 → 上 8 踢狼尊换主角 → 上 9 找杨叔(瓦尔特)大成。爻光穿鞋频召阿哈叠层
        key_equips=["火力风暴潮", "永动机", "冷笑话引擎", "高周波电锯"], shared_chars=["瓦尔特", "爻光", "火花"],   # 成型羁绊队:欢愉 4-6 档乘区
        char_positions={"爻光": "back", "绯英": "front"},   # 站位:爻光必后台(攻略反向论证:后台跑条给绯英多开大,总伤更高;前台倍率<20%残血版);绯英前排一号位(攻略 Final 标准式 25 帖归纳 @0,2026-11-04 Common 全量审查登记)
        transition_chars=["花火"],   # 交叉核对注:爻光 25/25 常驻是 core 非 transition;常驻是火花(16/25,4费)非花火
        # ===== 欢愉族家族·绯英档(资源锚 6 级;无信号时的默认落点)=====
        family="欢愉族",
        bond_signal="欢愉",   # ②类信号:绯英/银狼两档共用主体
        # content_id=7333;「欢愉 4-6 档」系连续区间误写);上限 5 = 4-5 主流带
        # (final_feiying「不到 7 也成型」,7 特权化属银狼档语义)。
        equip_assign={"绯英": ["火力风暴潮", "永动机"], "爻光": ["冷笑话引擎"], "瓦尔特": ["高周波电锯"]},
        # ↑ 教义:绯英=永动机(天赋装备化)+风暴潮;全队皮靴(恒等约束下未单列,拆分放开)
        flex_factions=["能量", "仙舟", "治疗", "量子同频", "战技点"],   # 能量降挂件(final_feiying 挂件层),
        plaza_carry="绯英",
        level_plan={  # 交叉核对注:labels 6级搜牌 19/25=76%(全场最集中)→ 6级停 roll,旧 5/6/7 全 level_up 缺停留
            4: LevelGoal("roll", target_cost=1, target_chars=["绯英", "爻光"]),
            5: LevelGoal("level_up"),
            6: LevelGoal("roll", target_cost=2, target_chars=["绯英"], star_goals={"绯英": 2}),
            7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["绯英"], star_goals={"绯英": 2}),
            9: LevelGoal("roll", target_cost=5, target_chars=["瓦尔特"]),
        },
        # ===== 知识卡字段(数据源=final_comps/final_feiying_joy.md)=====
        lock_rules={
            # 绯英线无专属策略(开局策略节明言「无专属策略——通用欢愉开局,门槛最低」;
            # 欢愉契约送银狼=姊妹银狼线信号,不登记本线)
            '策略型': [],
            # 引擎核心组=绯英+爻光(定轨对,构造机理§2「可显式定义」;爻光 25/25 双 100%)
            '角色型': ['绯英', '爻光'],
        },
        need_star={
            # 绯英 3★=节奏锚点「6级 D 三星绯英+爻光」(19/25 帖)+A4 高饥渴线 89%;
            # star_goals 2★=底稿降级语录口径(#12「两星即可稳定上分」)——交叉核对冲突
            # 以攻略重述为准取 3;爻光 2★=姊妹线明文(银狼篇 #7「开局追爻光2星」,
            # 共享引擎件);其余辅助普适档 1★
            '绯英': 3, '爻光': 2, '瓦尔特': 1, '开拓者·欢愉': 1, '符玄': 1,
        },
        # 骨架=定轨引擎爻光+能量环藿藿(18/25,插件排序首位,构造机理§2——
        # 绯英线比银狼线更依赖能量经济的差异件)
        key_items=['爻光', '藿藿'],
        # 上线窗口:主羁绊 bond_signal=欢愉,成型档 4 → synergy 4
        entry_signals=dict.fromkeys(('绯英', '瓦尔特', '爻光', '开拓者·欢愉', '符玄', '火花'), ('synergy', 4)),
    ),
    Comp(
        name="希儿量子", factions=["量子同频", "贝洛伯格"],
        # core(依据=final_seele_quantum.md「构造机理」
        # n=67 槽位构造):引擎核心组=希儿/花火/符玄/缇宝/刻律德菈;插件层=千冶·刃(掩体生成枪)/
        # 布洛妮娅/杰帕德/娜塔莎/佩拉(贝2 凑数+辅助);知更鸟/瓦尔特移出 core(P3 补位件,留 shared)。
        core_chars=["希儿", "花火", "符玄", "缇宝", "刻律德菈"],
        form_tiers={"量子同频": 4, "贝洛伯格": 2},
        # 成型判据 = 文档 OR 口径(transition_combos.md:27,与 的
        # pair 物化路径同构):form_tiers 双档由 OR 组**承接**
        # (同键档位不入 AND 账,折法见 form_progress),档位值保留作线键/
        # 完全体账单结构载体——囤货采购集/晋升候选/换线距离账等消费读其
        # 键面,清空即残(银狼/佩拉/桑博等放大器成员会掉出采购集)。
        or_reqs=list(SEELE_OR_REQS), required_deployed=(SEELE_CARRY_CHAR,),
        # V4.4 评级(76807134):希儿 = A 级(A8-50 最强轮椅);攻略(76802749 直读纠正):4量子+贝城(2贝=原4贝,引擎拉条)
        # 斩杀+70%下二战技+再现+造物引擎。希儿(双电锯+风暴潮)+杨叔(瓦尔特)+记忆主+鸟(知更鸟)+刻律+鸭鸭(布洛妮娅)+符玄
        # 前期强势(希儿无装也能换怪/胜)→ 强烈推荐希儿过渡;7级找希儿3星或先上8/9找4-5费同时找希儿
        # 装备公式(final_seele_quantum §装备公式/§5,38 篇统计):希儿=风暴潮×2-3+电锯(唯一公式),
        # B 套=特权版风暴潮(plaza 实证 特权风暴潮三件);战场进化手册**不是本套件**
        # (是小黑塔星级装备,归大黑塔条目)。
        key_equips=["火力风暴潮", "高周波电锯", "火力风暴潮·特权"],
        # boss 键规范名(俗称键经 BOSS_NICKNAMES 归位规范公司名,
        # 与 state.plane_bosses 同名字空间;出处=final_seele_quantum counter 节「蕉研组 boss」)
# 单属性队:量子同频4 属性型羁绊主档 ≥4(final_comps README D3「希儿怕量子熄火」,
        # plaza 希儿聚类 36/38 篇核心羁绊=量子同频)——量子熄火局对本套是主输出瘫痪级 counter。
        # 成型羁绊队:量子同频/贝洛伯格档位乘区。两者均为复活 tag(已永久滤除,见 ``_W878_RETIRED_TAGS``)。
# 知更鸟/瓦尔特= P3 补位件(n=67 非核心组);插件层五人(千冶·刃/布洛妮娅/
        # 杰帕德/娜塔莎/佩拉)为终局插件购买件,不入 core/shared
        shared_chars=["知更鸟", "布洛妮娅", "瓦尔特"],
        transition_chars=["刃"],
        # ===== 希儿量子家族(五线最收敛,无流派)=====
        family="希儿量子",
        equip_assign={"希儿": ["火力风暴潮", "高周波电锯", "火力风暴潮·特权"]},
        # ↑ 特权三件=希儿 B 套(final_seele_quantum §5「B 套=特权版风暴潮」);
        #   布洛妮娅降插件层后无专属装备条目
        #   (n=67 插件层定位=贝成员/增益,装备优先级让渡引擎组)。恒等:key_equips=派生投影
        flex_factions=["战技点", "治疗", "盛会之星", "列车同行"],
        plaza_carry="希儿",
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["希儿"]),   # 交叉核对注:希儿 3费,旧标 2
            6: LevelGoal("roll", target_cost=3, target_chars=["希儿"], star_goals={"希儿": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["希儿"], star_goals={"希儿": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=5, target_chars=["瓦尔特", "知更鸟"]),
        },
        # ===== 知识卡字段(数据源=final_comps/final_seele_quantum.md)=====
        lock_rules={
            # 类专属策略:量子力学/钢铁美学(开局策略节「希儿类专属策略」);量/贝
            # 契约·邀请·概念股·星徽=双放大器入口(ENV/AUGMENT 亲和表 ≥0.7 条目)
            '策略型': ['量子同频契约', '量子同频邀请', '贝洛伯格概念股',
                       '量子同频星徽', '量子同频星徽套组', '量子力学', '钢铁美学'],
            # 引擎核心组=希儿(67/67 载体C)+花火(63/67 第二引擎——星3 一人供
            # 战技点+暴伤+易伤+自充能,构造机理§2);量/贝 OR 引擎细节归 3.7
            # 锁定判定按需展开(本表为 AND 近似)
            '角色型': ['希儿', '花火'],
        },
        need_star={
            # 希儿 3★=「终局几乎必追三星」(构造机理§4:3星 62/67)+A4 希儿 81% 高饥渴线;
            # star_goals 2★=lv6-7 停留档口径——交叉核对冲突以攻略重述为准取 3;
            # 辅助普适档 1★(「辅助以 2星 为主」=自然来牌实况,非必要星级)
            '希儿': 3, '花火': 1, '符玄': 1, '缇宝': 1, '刻律德菈': 1,
        },
        # 骨架=引擎核心组非 carry 四件(构造机理§2:花火 63/符玄 62/缇宝 58/刻律德菈 53)
        key_items=['花火', '符玄', '缇宝', '刻律德菈'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(量子同频),档 4
        entry_signals=dict.fromkeys(('希儿', '花火', '符玄', '缇宝', '刻律德菈', '知更鸟', '布洛妮娅', '瓦尔特'), ('synergy', 4)),
    ),
    Comp(
        name="黄泉减益", factions=["巡海游侠", "减益"], core_chars=["黄泉", "不死途", "乱破", "千冶·刃", "瓦尔特"],
        form_tiers={"巡海游侠": 4, "减益": 4},
        # 巡海游侠档 = 教义「4」单点档(后排星级 1/3/6/12 倍放大)。
        # V4.4 评级(76807134):黄泉 = A 级;攻略(76826405):3游侠+4减益+3量子,2星乱破+3星不死途→280%增幅
        # (plaza 50 篇校准):常驻 千冶·刃48/瓦尔特45/不死途45/乱破38/椒丘32 —— core 的「刃」
        # 改「千冶·刃」(V4.4 实战常驻是千冶·刃,非本体刃);装备 top:电锯56/风暴潮28/光速螺旋桨26/永动机24。
        flex_factions=["击破", "治疗", "追击", "量子同频"],
        plaza_carry="黄泉",
        key_equips=["高周波电锯", "火力风暴潮", "光速螺旋桨", "永动机"],
        # 「单体boss」是 boss 原型描述非公司名(BOSS_NICKNAMES 不含,永不命中;且占位会
        # 屏蔽 matchup 结构层兜底)——单体乏力由 mechanic_attributes
        # 走 cw_enemy_data.matchup 的 single_burst 结构通道表达。
# 攻略:单体 boss 黄泉输出乏力(俗称键零效,走 matchup 结构通道)
        shared_chars=["刃", "乱破", "符玄"],   # 成型羁绊队:巡海4+减益4 档乘区
        transition_chars=["刃", "椒丘", "桑博"],
        # ===== 黄泉减益家族(无流派;第四件=装备池)=====
        family="黄泉减益",
        bond_signal="减益",   # ②类信号:4-6 档主体,到前 DOT 班底共享牌桌
        sub_tiers={"击破": 2},   # 击破 58% 升格候选
        equip_assign={"黄泉": ["高周波电锯", EquipChoice("pool", ("永动机", "光速螺旋桨", "火力风暴潮"))]},
        # ↑ 教义:黄泉=电锯(69% 近必选);第四件=池(永动机38/螺旋桨30/冷笑话26/风暴潮26 平缓分散)——
        # 恒等约束(与旧 key_equips 多重集相等)下池取频次前三,冷笑话并列 26% 待拆分放开
        substitute_plan=[
            {"替班者": "卡芙卡", "顶位": "黄泉主C(黄泉 7 级到前)", "身份": "DOT 班底照打(减益件与 DOT 件共享牌桌)", "分岔点": "黄泉 7 级到手即上"},
        ],
        level_plan={
            5: LevelGoal("roll", target_cost=1, target_chars=["乱破", "不死途"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=3, target_chars=["黄泉", "不死途"]),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["黄泉"], star_goals={"黄泉": 2, "不死途": 2}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_huangquan_debuff.md)=====
        lock_rules={
            # 离火燎原=黄泉专属增伤策略(开局策略节「大招增幅使黄泉大招回到巅峰」);
            # 减益星徽/套组=通用阵营徽章,不登记
            '策略型': ['离火燎原'],
            # 充能对=黄泉(载体)+不死途(饲饵充能泵,第二核心)+千冶·刃(48/50 刚需级,
            # 构造机理§2)
            '角色型': ['黄泉', '不死途', '千冶·刃'],
        },
        need_star={
            # 黄泉 3★=「7级 D 三星黄泉」节奏共识+A4 黄泉 87%;不死途 3★=「必须要有
            # 三星不死途」(#41;本线核心件 3★ 38%=A4 唯一例外档);乱破 2★=攻略
            # 「2星乱破+3星不死途」(76826405);star_goals 2★ 交叉核对冲突以攻略重述为准
            '黄泉': 3, '不死途': 3, '乱破': 2, '千冶·刃': 1, '瓦尔特': 1,
        },
        # 骨架=充能/生存/放大插件头名(构造机理§2:不死途>千冶·刃;椒丘隐形奶;瓦尔特 45/50)
        key_items=['不死途', '千冶·刃', '椒丘', '瓦尔特'],
        # 上线窗口:主羁绊 bond_signal=减益,成型档 4 → synergy 4
        entry_signals=dict.fromkeys(('黄泉', '不死途', '乱破', '千冶·刃', '瓦尔特', '刃', '符玄'), ('synergy', 4)),
    ),
    Comp(
        name="巡海击破", factions=["击破", "巡海游侠"], core_chars=["不死途", "波提欧", "乱破", "忘归人", "大丽花", "灵砂", "阮·梅"],
        form_tiers={"击破": 6, "巡海游侠": 4},
        # ↺ 推翻「击破流萤」(plaza 784 篇):V4.4 击破代表已换代 —— 流萤任一阶段在场仅 29 篇
        # (carry 聚类 n=8,7/8 击破形)。**锚=波提欧簇**(12 篇,击破12/巡海12 全击破形;不死途簇 n=14 的
        # 主体是减益板[减益13/巡海12/击破11 混合],不当击破锚)。常驻 忘归人12/大丽花11/灵砂11/乱破11/阮·梅10。
        # 装备:波提欧=虫洞掘进钻头16/光速螺旋桨9,不死途=反重力皮靴。
        shared_chars=["黄泉", "流萤", "忘归人"],   # 成型羁绊队:击破6 档乘区
        key_equips=["虫洞掘进钻头", "光速螺旋桨", "反重力皮靴", "光速螺旋桨·特权"],   # 交叉核对注:波提欧=钻头16/螺旋桨9,不死途=皮靴24(旧空表 equip_fit 恒 None)
        transition_chars=["赛飞儿", "灵砂", "忘归人"],
        family="legacy",
        flex_factions=["减益", "盛会之星"],
        plaza_carry="波提欧",
        level_plan={  # 后期 6 击破:前期过渡 → 升 8-9 击破;交叉核对注:波提欧 5费/不死途 2费
            5: LevelGoal("roll", target_cost=1, target_chars=["乱破"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["不死途", "波提欧"]),
            9: LevelGoal("roll", target_cost=5, target_chars=["波提欧", "忘归人"], star_goals={"不死途": 2}),
        },
        # ===== 知识卡字段(长尾线无专篇,数据源=本条 plaza 校准注 n=12 波提欧簇)=====
        lock_rules={
            # 击破概念股=通用阵营入口(无击破专篇;击破6 泛阵营板)——锁定走角色型/时点兜底
            '策略型': [],
            # 波提欧簇锚(12 篇全击破形)+忘归人 12/12 簇内全勤(本条 plaza 校准注)
            '角色型': ['波提欧', '忘归人'],
        },
        need_star={
            # 波提欧 2★=A4 低饥渴线 56%(≤2★ 过半;无攻略明文按饥饿表拍定);
            # 不死途 2★=level_plan star_goals(攻略口径);其余辅助普适档 1★
            '波提欧': 2, '不死途': 2, '乱破': 1, '忘归人': 1, '大丽花': 1, '灵砂': 1, '阮·梅': 1,
        },
        # 骨架=巡海后排结构:不死途(巡海引擎件+lv8 搜索目标,黄泉篇同构后排——
        # 本簇 n=12 常驻名单未列不死途,入册按结构非按簇统计)/乱破/忘归人/阮·梅
        # (簇内常驻 10-12/12);大丽花/灵砂(常驻 11)不入=巡海4 只需 4 名巡海成员、
        # 槽位弹性,常驻率相近的成员间不点名骨架(选择理由登记=交叉核对记录§四R4)
        key_items=['不死途', '乱破', '忘归人', '阮·梅'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(击破),档 6
        entry_signals=dict.fromkeys(('不死途', '波提欧', '乱破', '忘归人', '大丽花', '灵砂', '阮·梅', '黄泉', '流萤'), ('synergy', 6)),
    ),
    Comp(
        name="龙丹战技点", factions=["战技点", "列车同行"], core_chars=["丹恒·饮月", "远坂凛", "瓦尔特", "花火", "刻律德菈"],
        form_tiers={"战技点": 4, "列车同行": 4},
        # V4.4 评级(76807134):丹恒·饮月(龙丹)= A 级;攻略(76987716 直读纠正):4战技点+4列车(周日开)
        # 凛(远坂凛)V4.4 新:宝石叠99层→第二魔法实验拐198%爆伤(+默认70%=268%);饮月双电锯+风暴潮
        # 杨叔(瓦尔特)+记忆主必备;4列车给160%前台强度;刃+符玄补。苍龙濯世破百亿
        key_equips=["高周波电锯", "动能激发剑", "火力风暴潮", "斩首行动"],   # 成型羁绊队:战技点4+列车4 档乘区
        shared_chars=["远坂凛", "瓦尔特", "花火"], transition_chars=["花火", "风堇", "姬子·启行"],
        family="legacy",
        flex_factions=["量子同频", "盛会之星"],
        plaza_carry="丹恒·饮月",
        level_plan={  # 交叉核对注:饮月 2费(旧标3);花火 2费
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("roll", target_cost=2, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["丹恒·饮月"], star_goals={"丹恒·饮月": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 龙丹节)=====
        lock_rules={
            # 战技点契约效果直赠核心 饮月+花火(cw_invest_data 128)——效果文本级线关联
            '策略型': ['战技点契约'],
            # 饮月(载体,唯一把点数上限转倍率的卡,龙丹节构造机理机制链)+瓦尔特
            # (攻略明言「杨叔必备」,龙丹节正文)+花火(「人造大奖」核爆核心,
            # 龙丹节攻略原文细节补记——史料级信源,V4.4 在跑口径未推翻该机制描述)
            '角色型': ['丹恒·饮月', '瓦尔特', '花火'],
        },
        need_star={
            # 饮月 2★=level_plan star_goals 攻略口径(「6级停 roll 追 2星」;A4 无饮月
            # 条目,无明文不拍 3★);其余辅助普适档 1★
            '丹恒·饮月': 2, '远坂凛': 1, '瓦尔特': 1, '花火': 1, '刻律德菈': 1,
        },
        # 骨架=战技点燃料系统(远坂凛宝石/花火产点=龙丹节攻略原文细节补记〔史料级〕;
        # 瓦尔特必备=龙丹节正文;刻律复制=刻律星3 技能文本〔final_seele/final_wandi
        # 已登记〕——龙丹节通篇无刻律德菈,复制能力出处不在彼处)
        key_items=['远坂凛', '瓦尔特', '花火', '刻律德菈'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(战技点),档 4
        entry_signals=dict.fromkeys(('丹恒·饮月', '远坂凛', '瓦尔特', '花火', '刻律德菈'), ('synergy', 4)),
    ),
    Comp(
        name="双王圣杯", factions=["命运圣杯", "能量"], core_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄", "开拓者·记忆", "藿藿"],
        form_tiers={"命运圣杯": 3, "能量": 5},
        # V4.4 评级(76807134):双王 = A 级;攻略(76985789 直读纠正调研误认):双王=闪闪(吉尔伽美什)+Saber(Fate圣杯联动),
        # 非大黑塔+景元(游侠源误)。闪闪+Saber 每8行动连携+回能;圣杯羁绊给经济+改件加速3星。
        # Saber主c(风暴潮+冷笑话+永动机)/闪闪后台带鞋自加速;5能量;杨叔必备;刃+缇宝+符玄(阿瓦隆+绝对热量邪修75%减伤)
        # 过渡:体系牌+花火/凛(做3圣杯任务);7-8级找3星Saber或闪闪→上9挂杨叔
        key_equips=["火力风暴潮", "永动机", "冷笑话引擎", "反重力皮靴"],   # 交叉核对注:Saber 风暴潮56/永动机44/冷笑话36/电锯31(皮靴13 降位)
        # ↑ 教义:闪闪=**反重力皮靴**(41%,
        #   锁轴速度载体;final_grail_dual.md 圣杯A)
        shared_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄"],   # 成型羁绊队:能量5 硬约束+圣杯任务链=档位乘区
        transition_chars=["花火", "刃"],   # 远坂凛是 core(1 星即够)
        # ===== 圣杯双C家族·B Saber 能量线(~25%)=====
        family="圣杯双C",
        bond_signal="命运圣杯",   # ②类信号:2 档开任务=燃料线入口
        equip_assign={"Saber": ["火力风暴潮", "永动机", "冷笑话引擎"], "吉尔伽美什": ["反重力皮靴"]},
        # ↑ 教义:Saber=充能件(永动机/冷笑话引擎/电光履,主C 满能自拉条伪永动)
        flex_factions=["列车同行", "战技点", "治疗", "盛会之星"],
        plaza_carry="Saber",
        level_plan={
            5: LevelGoal("roll", target_cost=2, target_chars=["花火", "远坂凛"]),
            6: LevelGoal("level_up"), 7: LevelGoal("roll", target_cost=3, target_chars=["Saber"], star_goals={"Saber": 2}),
            8: LevelGoal("roll", target_cost=3, target_chars=["吉尔伽美什", "Saber"], star_goals={"Saber": 3}),
            9: LevelGoal("roll", target_cost=0, target_chars=["瓦尔特", "符玄"]),
        },
        # ===== 知识卡字段(数据源=final_comps/final_grail_dual.md)=====
        lock_rules={
            # 圣杯家族类级信号(同红A 条目):契约/邀请/星徽/「都是这家伙的错!」
            '策略型': ['命运圣杯契约', '命运圣杯邀请', '命运圣杯星徽', '都是这家伙的错！'],
            # B 线核心=Saber(能量线主C)+吉尔伽美什(锁轴速度载体,Final 127/196)
            # +远坂凛(81% 触发器)
            '角色型': ['Saber', '吉尔伽美什', '远坂凛'],
        },
        need_star={
            # Saber 3★=「7级 D 三星Saber」节奏共识+A4 Saber 87%;远坂凛 1★(本条注
            # 「远坂凛是 core(1 星即够)」——star_goals 无凛条目,按攻略口径入册);
            # 其余辅助普适档 1★
            'Saber': 3, '吉尔伽美什': 1, '瓦尔特': 1, '符玄': 1, '开拓者·记忆': 1,
            '藿藿': 1, '远坂凛': 1,
        },
        # 骨架=闪闪锁轴速度载体(README B9)+远坂凛触发器+记忆主拉条(锁轴前置+本体
        # 配对)+生存件(符玄 60%/藿藿 43%,构造机理§2)
        key_items=['吉尔伽美什', '远坂凛', '开拓者·记忆', '符玄', '藿藿'],
        # 上线窗口:主羁绊 bond_signal=命运圣杯,成型档 3 → synergy 3
        entry_signals=dict.fromkeys(('吉尔伽美什', 'Saber', '瓦尔特', '符玄', '开拓者·记忆', '藿藿'), ('synergy', 3)),
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
        form_tiers={"欢愉": 3},
        # 交叉核对注(火花簇 25 篇):旧 factions[星间+量子] 0/25 达标 —— 实战分布 欢愉22/战技点21/
        # 星间21 并列,量子仅 flex 位 → 核心改 星间+欢愉(花火=欢愉阵营);core 补 开拓者·欢愉(20/25 在场,
        # 欢愉形态保留不换记忆)与银狼LV.999(17/25)。
        key_equips=["火力风暴潮", "高周波电锯", "碎星斩舰刀", "动能激发剑"],   # 花火1风暴潮+暴击刀;爻光三鞋
# 成型羁绊队:欢愉档乘区(星间降 flex)
        shared_chars=["银狼", "符玄", "丹恒·饮月"], transition_chars=["丹恒·饮月", "银枝"],
        family="legacy",
        flex_factions=["星间旅人", "战技点", "列车同行", "量子同频", "星核猎手"],   # 星间=顺手增益源
        plaza_carry="火花",
        level_plan={   # 前期龙丹护航 → 上8大D 2星花火 → 有机会追3必试(质变);交叉核对注:花火 2费/饮月 2费
            5: LevelGoal("roll", target_cost=2, target_chars=["丹恒·饮月"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=2, target_chars=["花火"], star_goals={"花火": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["花火", "开拓者·记忆"], star_goals={"花火": 3}),
        },
        # ===== 知识卡字段(数据源=本条 BV 转录注+plaza 火花簇 25 篇校准注)=====
        lock_rules={
            # 无类专属策略(火花簇散见文档无专篇;欢愉契约送银狼=狼尊线信号不登记)
            '策略型': [],
            # 攻略明文核心=花火主C(吃点巧普攻,倍率随花火等级)+爻光三鞋(跑条供R回合);
            # ⚠️ plaza_carry='火花'(聚类锚)与攻略主C=花火 双源分歧——角色型按攻略
            # 重述定,锚保持聚类真值,分歧登记在 知识卡建表交叉核对记录
            '角色型': ['花火', '爻光'],
        },
        need_star={
            # 花火 3★=「上8大D找2星花火,3星质变/有机会追3必试」(攻略明文);
            # 其余辅助普适档 1★
            '花火': 3, '爻光': 1, '开拓者·欢愉': 1, '银狼LV.999': 1,
        },
        # 骨架=core 非花火三件(爻光引擎/开拓者·欢愉 20-25/银狼LV.999 17-25,簇校准注)
        key_items=['爻光', '开拓者·欢愉', '银狼LV.999'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(欢愉),档 3;
        # 银狼LV.999 = 升费链累积型但「不适用有空位就上例外」,按线 synergy 窗
        entry_signals=dict.fromkeys(('花火', '爻光', '开拓者·欢愉', '银狼LV.999', '银狼', '符玄', '丹恒·饮月'), ('synergy', 3)),
    ),
    Comp(
        # 新增(plaza 大族群补缺):银河学者+群攻族 —— 大黑塔 carry 38 篇 + 小黑塔 carry 26 篇。
        # **augment 定义型阵容**:35 篇带「黑塔纪元」(棱彩,216 张黑塔入商店+追击转圈)—— 拿到即玩
        # (AUGMENT_COMP_AFFINITY 近乎硬绑);无它时靠银河学者羁绊本身(星级总量成长)亦可成型,强度降档。
        # 黑塔纪元特型:备战席囤小黑塔(强度=小黑塔合计星级,「备战席放满越多越好」)—— bench 语义特例。
        name="大黑塔银河学者", factions=["银河学者", "群攻"], core_chars=["大黑塔", "黑塔", "缇宝", "翡翠"],
        form_tiers={"银河学者": 4, "群攻": 3},
        # plaza:大黑塔 3星率 0.82(4费);5级搜牌 20/38 篇(小黑塔 1费 5级 D 干);装备 电锯29/永动机20/蓄能帆17/电光履16
        # 记忆主必拿(「记忆主一定要拿,后台花火防战技点不足」);后期可上花火补战技点。
        key_equips=["高周波电锯", "永动机", "蓄能帆", "电光履", "战场进化手册"],
        # ↑ 战场进化手册=小黑塔星级装备(星级→强度),归本条(教义);恒等约束同步扩入。
        shared_chars=["黑塔", "缇宝", "翡翠"],   # 成型羁绊队:学者档=星级总量成长乘区
        transition_chars=["艾丝妲", "丹恒·腾荒"],   # 黑塔(小黑塔)是 core/替班C
        # ===== 大黑塔群攻家族(档位=连续深度谱,非流派)=====
        family="大黑塔群攻",
        bond_signal="银河学者",   # ②类信号:星级总量成长
        equip_assign={"大黑塔": ["高周波电锯"], "黑塔": ["战场进化手册", "永动机", "蓄能帆", "电光履"]},
        # ↑ 教义:大黑塔=电锯+风暴潮;小黑塔=战场进化手册(星级装备,自希儿量子归位)+充能三件套
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
        # ===== 知识卡字段(数据源=final_comps/final_daheita_aoe.md)=====
        lock_rules={
            # 黑塔纪元=策略驱动直通线(32/38 篇用它开局,「没有黑塔纪元这条线基本
            # 不存在」);银河学者概念股/邀请=ENV 亲和 1.0/0.9 条目
            '策略型': ['黑塔纪元', '银河学者概念股', '银河学者邀请'],
            # 引擎核心=大黑塔(52/52)+黑塔(49/52)双 3★ 联动(构造机理§2「双 3星联动」)
            '角色型': ['大黑塔', '黑塔'],
        },
        need_star={
            # 大黑塔 3★=3星 39/52+A4 大黑塔 84%;黑塔 3★=「本类小黑塔也追 3星(与
            # 其他类辅助 2★ 通则相反)」(构造机理§2)+备战席星级=学者档强度源;
            # 缇宝/翡翠辅助普适档 1★
            '大黑塔': 3, '黑塔': 3, '缇宝': 1, '翡翠': 1,
        },
        # 骨架=黑塔(联动引擎件)+缇宝(46/52)/翡翠(31/52,学者4 档件)(构造机理§2)
        key_items=['黑塔', '缇宝', '翡翠'],
        # 上线窗口:主羁绊 bond_signal=银河学者,成型档 4 → synergy 4;
        # 小黑塔(黑塔)「备战席放满越多越好」的 bench 语义特例与窗口适用范围
        # 天然一致——银河学者档齐前囤不上
        entry_signals=dict.fromkeys(('大黑塔', '黑塔', '缇宝', '翡翠'), ('synergy', 4)),
    ),
    Comp(
        name="银枝群攻", factions=["群攻"], core_chars=["银枝", "翡翠", "知更鸟"],
        form_tiers={"群攻": 3},
        # V4.4 评级(76807134):银枝 = B 级;攻略(77006068 直读纠正):V4.4 离能量,"轮椅通拐"(杨叔/主角/缇宝/花火/千冶刃+符玄)抬
        # 银枝(风暴潮+冷笑话)+翡翠(3群攻)+鸟(拉条加攻增伤+10%幸运);必须3星银枝;适合对群,对单大降
        # ⚠️ (注册表交叉核对):银枝=**星间旅人** 2费,非贝洛伯格(24 篇银枝帖贝洛伯格激活 0 次)
        # —— 核心只有群攻,星间旅人/公司/盛会之星(翡翠/知更鸟)是 flex。
        key_equips=["火力风暴潮", "冷笑话引擎", "绝对热量"],   # 成型羁绊队:群攻档乘区+大招驱动的羁绊协同型
# 无 countered 数据:单体长战类非公司名,走 matchup 结构层
        shared_chars=["翡翠", "知更鸟"],
        transition_chars=["椒丘", "星期日", "刃"],
        family="legacy",
        flex_factions=["星间旅人", "公司", "盛会之星", "列车同行"],
        plaza_carry="",   # 银枝 carry 聚类 n<5(24 篇在场,长尾)
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["银枝"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["银枝"], star_goals={"银枝": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["翡翠", "知更鸟"]),
        },
        # ===== 知识卡字段(数据源=本条攻略直读注 77006068)=====
        lock_rules={
            # 群攻概念股=通用阵营入口(无银枝专篇;群攻族并归大黑塔线)——锁定走
            # 角色型/时点兜底
            '策略型': [],
            # 攻略结构三件套=银枝+翡翠(3群攻)+知更鸟(拉条加攻增伤+10%幸运,
            # 77006068 直读)
            '角色型': ['银枝', '翡翠', '知更鸟'],
        },
        need_star={
            # 银枝 3★=攻略明文「必须3星银枝」(77006068;star_goals 2★ 交叉核对冲突
            # 以攻略重述为准);翡翠/知更鸟辅助普适档 1★
            '银枝': 3, '翡翠': 1, '知更鸟': 1,
        },
        # 骨架=翡翠(3群攻结构件)+知更鸟(拉条件,攻略句内明示)
        key_items=['翡翠', '知更鸟'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(群攻),档 3
        entry_signals=dict.fromkeys(('银枝', '翡翠', '知更鸟'), ('synergy', 3)),
    ),
    Comp(
        name="反甲白厄", factions=[], core_chars=["白厄", "三月七", "姬子·启行"],
        form_tiers={},
        # 白厄无阵营(cw_chars:104 factions=""),独立羁绊「救世主」(获所有前台非独立羁绊效果)。
        # 反甲流靠白厄单核 + 以牙还牙甲×3 受击反伤,**不靠阵营羁绊成型** → factions/form_tiers 空。
        # 阵容靠 core_char(白厄)+ equip_fit(以牙还牙甲)+ mechanics(高频低单次 反伤);
        # form_progress 恒 0 → 不靠 form commit(轮数兜底要求 fp>0,fp=0 不触发),选靶候选但 progress 低。
        key_equips=["以牙还牙甲", "高周波电锯", "以牙还牙甲·特权", "热血沸腾拳"],   # meta:反甲流需 3 以牙还牙甲
        # boss 键规范名(BOSS_NICKNAMES:酒杯怪=造梦兄弟影业/琥珀王=铁盾安保集团/
        # 死龙=灰手生命科技;「红绿灯」经用户确认是小怪非 boss(2026-08-17),移除不建模)
# 依赖合成装备:以牙还牙甲×3 反甲链+掩体生成枪=胜利条件本身(final_baie_reflect 明文
        # 「反甲装备流」);装备依赖词条(变宝为废)的选型侧降分载体(合成侧由 junk_first 处理,
        # 两半互补)。羁绊维判非成型羁绊队:factions/form_tiers 空,装备流例外。
        shared_chars=["白厄"],
        transition_chars=["符玄"],   # 白厄 core/三月七 P2 直留终局
        # ===== 白厄反甲家族(A 巡海流 ~64% / B 列车护盾流 ~29%;A/B 未拆条)=====
        family="白厄反甲",
        sub_tiers={"护盾": 2},   # B 流副档(多数停护盾 2);A 流前排法则=标签数量×星级优先
        # ↑ A 巡海流(~64%)核心副羁绊=「巡海 3+」——A/B 未拆下
        #   sub_tiers 只收了 B 流 {护盾2},巡海 3 属 A 流、现仅在 flex_factions(板面不罚但完成度不数);
        #   A/B 拆分落位时补 sub_tiers={"护盾": 2, "巡海游侠": 3}(分支依赖,同姬子 sub_tiers 口径)
        equip_assign={"白厄": ["以牙还牙甲", "以牙还牙甲·特权", "热血沸腾拳"], "三月七": ["高周波电锯"]},
        # ↑ 完整反甲链(以牙还牙甲×3+掩体生成枪持续群盾,生存位=绝对热量)留 A/B 拆分
        substitute_plan=[
            {"替班者": "姬子·启行", "顶位": "白厄主C(搜不到白厄时)", "身份": "共享列车池,转姬子线=攻略明写预案;B 流领航员身份 1 星够(49% 在场沉淀)", "分岔点": "红绿灯词条/白厄到手"},
            {"替班者": "三月七", "顶位": "前排(与 星期日/开拓者 自 P2 直留终局)", "身份": "直留终局(不卖)", "分岔点": "无(全程)"},
        ],
        # (plaza 校准):白厄 38 篇 carry 中 33 篇实际挂在列车同行(以牙还牙甲×93 断层第一,
        # 副三月七/姬子/星期日)—— 纯反甲白厄是小众硬流派;主流是列车护盾流的副 carry 位。
        flex_factions=["列车同行", "巡海游侠", "减益", "护盾"],
        plaza_carry="白厄",
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["白厄"]),
            6: LevelGoal("level_up"),
            7: LevelGoal("roll", target_cost=3, target_chars=["白厄"], star_goals={"白厄": 2}),   # 交叉核对注:labels 7级搜牌 25/38(66%),旧 7=level_up 直跳 8 缺停留
            8: LevelGoal("roll", target_cost=0, target_chars=["白厄"], star_goals={"白厄": 3}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_baie_reflect.md)=====
        lock_rules={
            # 轮回不止效果直赠白厄+装备(cw_invest_data 332201)——效果文本级线关联;
            # 公司军火更新=通用装备流,不登记
            '策略型': ['轮回不止'],
            # 载体C 白厄(78/78)+三月七(护盾/反震插件+领航员绑三月七)+姬子·启行
            # (领航员工具,身份级绑定 1星板凳即可生效,构造机理§2)
            '角色型': ['白厄', '三月七', '姬子·启行'],
        },
        need_star={
            # 白厄 3★=主流追三星(3星 72/78)+A4 白厄 92%(「2星即可开线,3星是上限」
            # ——need_star 锁完成态);三月七/姬子辅助普适档 1★(姬子明文 1星 30/38 生效)
            '白厄': 3, '三月七': 1, '姬子·启行': 1,
        },
        # 骨架=三月七(护盾/反震插件 46/78)+姬子·启行(领航员工具 38/78)(构造机理§2)
        key_items=['三月七', '姬子·启行'],
        # 上线窗口:反甲装备流无羁绊主档(form_tiers 空)→ plane_end(终局
        # 位面段;README C4「白厄 B 套特权反甲 = 满编后期的常态」——
        # 装备流战力随装备合成累积,前中期上 = 裸装白厄送战损)
        entry_signals=dict.fromkeys(('白厄', '三月七', '姬子·启行'), ('plane_end', 0)),
    ),
    # ===== B 级(强度一般,V4.4 合集 76807134)=====
    Comp(
        name="狼尊欢愉", factions=["星核猎手", "欢愉"], core_chars=["银狼LV.999", "爻光", "千冶·刃", "开拓者·欢愉", "火花", "绯英"],
        form_tiers={"欢愉": 5, "星核猎手": 2},
        # V4.4 评级(76807134):狼尊 = B 级;攻略(76832783 直读):5欢愉(最大利用阿哈装备),狼尊双风暴潮+爻光双鞋
        # 刃(星核猎手):刃+狼尊行动7次→狼尊释放欢愉技。强依赖鞋≥6;尽量不d全力升级;也作绯英早期过渡c
        # 交叉核对注(狼尊簇 68 篇交叉核对):本体刃仅 2/68,千冶·刃 36/68 → core 刃改千冶·刃(V4.4 实战常驻)。
        key_equips=["火力风暴潮", "反重力皮靴", "反重力皮靴", "光速螺旋桨"],   # 成型羁绊队:欢愉 5-7 档乘区
        # ↑ 教义:银狼=风暴潮+
        #   **速度件**(升费链要行动),皮靴是速度载体;爻光本就是皮靴(攻略:爻光双鞋)
        shared_chars=["爻光", "花火"], transition_chars=["花火", "符玄"],
        # ===== 欢愉族家族·银狼档(资源锚 9 级;与绯英档互含单向:银狼局含绯英 76%)=====
        family="欢愉族",
        bond_signal="欢愉",   # ②类信号:绯英/银狼两档共用主体
        # 星核 2=笑点泵(银狼每攻 7 次放 40 笑点欢愉技)——本套已列主档 form_tiers(星核猎手2),不入 sub_tiers(不重复);绯英 76% 在场沉淀
        equip_assign={"银狼LV.999": ["火力风暴潮", "反重力皮靴"], "爻光": ["反重力皮靴"], "开拓者·欢愉": ["光速螺旋桨"]},
        # ↑ v2:银狼=风暴潮+速度件(升费链要
        #   行动)。全队永动机群(阿哈装备栏全开后装备=输出)恒等约束下未单列,拆分放开
        substitute_plan=[
            {"替班者": "绯英", "顶位": "银狼LV.999 主C(银狼 9 级到前)", "身份": "绯英当主 C 直至银狼 9 级到手;到后不卖,降副C沉淀(数据常态 76%)", "分岔点": "银狼 LV.999 到手→家族内转档"},
        ],
        flex_factions=["星间旅人", "战技点", "列车同行"],
        plaza_carry="银狼LV.999",
        # 全局累积型标注:银狼=升费链(cost_escalation)——累积持久(费用档不清零)
        # 但由购买/D 驱动非上场时间,**不适用「有空位就上」部署例外**;仅作类型区分。
        level_plan={  # 交叉核对注:银狼LV.999 3费(升费到5,标3=起始找牌档)
            4: LevelGoal("roll", target_cost=3, target_chars=["银狼LV.999", "爻光"]),
            5: LevelGoal("level_up"), 6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=3, target_chars=["银狼LV.999"], star_goals={"银狼LV.999": 2}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_yinlang_joy.md)=====
        lock_rules={
            # 骇客专家:银狼=银狼专属开局策略(开局策略节,10 篇);欢愉契约效果
            # 直赠核心 银狼LV.999(cw_invest_data 1201)
            '策略型': ['骇客专家:银狼', '欢愉契约'],
            # Early 铁三角=银狼+爻光+绯英(27/27 篇,transition_combos 欢愉线节)
            '角色型': ['银狼LV.999', '爻光', '绯英'],
        },
        need_star={
            # 银狼LV.999 2★=A4 低饥渴线 48%(≤2★ 过半;强度轴在升费链 5 费完全体
            # 非星级);爻光 2★=「开局追爻光2星」(#7);其余辅助普适档 1★
            '银狼LV.999': 2, '爻光': 2, '千冶·刃': 1, '开拓者·欢愉': 1, '火花': 1, '绯英': 1,
        },
        # 骨架=铁三角非 carry(爻光 100% 阿哈引擎/绯英 84% 副C沉淀)+插件前二
        # (开拓者 65/68/火花 57/68,构造机理§2)
        key_items=['爻光', '绯英', '开拓者·欢愉', '火花'],
        # 上线窗口:主羁绊 bond_signal=欢愉,成型档 5(欢愉 5 = 特权化银狼档)→
        # synergy 5;银狼LV.999 = cost_escalation 不适用早上例外(字段注)
        entry_signals=dict.fromkeys(('银狼LV.999', '爻光', '千冶·刃', '开拓者·欢愉', '火花', '绯英', '花火'), ('synergy', 5)),
    ),
    Comp(
        name="昼神阿雅", factions=["昼之半神"], core_chars=["阿格莱雅", "风堇", "昔涟"],
        form_tiers={"昼之半神": 4},
        # V4.4 评级(76807134):阿雅 = B 级(试用难玩;需反重力皮靴×2+速度投资,V3.8 最轮椅→V4.4 降 B)。
        # (plaza 8 篇 carry):装备 反重力皮靴×16 断层第一(「有鞋跟本输不了」);阿格莱雅 3星率
        # 0.88;实战板多为 昼神4+量子3/能量+治疗混搭(flex 已收)。强帖(「80连胜焚决」/「小伊卡」)
        # use 均 0 且依赖本体/遗器/充能绳(M11)→ **保持 B**(交叉核对注:升 A 依据不足,勿按万敌标准拔高)。
        key_equips=["反重力皮靴", "反重力皮靴", "白昼·光速螺旋桨", "火力风暴潮"],   # 成型羁绊队(边界套):昼之半神4 主档为战力底盘,速度件是执行载体非战力源(裁注)
        shared_chars=["风堇", "昔涟", "银狼"], transition_chars=["风堇", "艾丝妲", "阿格莱雅"],
        family="legacy",
        flex_factions=["能量", "列车同行", "量子同频", "治疗"],
        plaza_carry="阿格莱雅",
        level_plan={  # 交叉核对注:阿格莱雅 1费(旧标2);「速升9找银狼」补 9 级
            5: LevelGoal("roll", target_cost=1, target_chars=["阿格莱雅", "风堇"]),
            6: LevelGoal("level_up"), 7: LevelGoal("level_up"),
            8: LevelGoal("roll", target_cost=1, target_chars=["阿格莱雅"], star_goals={"阿格莱雅": 2}),
            9: LevelGoal("roll", target_cost=0, target_chars=["银狼"], star_goals={"阿格莱雅": 3}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 昼神节)=====
        lock_rules={
            # 昼之半神概念股=ENV 亲和 1.0 条目(送昼神角色+刷新率提升)
            '策略型': ['昼之半神概念股'],
            # 载体=阿格莱雅(3星 20/21)+昔涟(19/21,诗篇+终结技双引擎插件)
            '角色型': ['阿格莱雅', '昔涟'],
        },
        need_star={
            # 阿格莱雅 3★=3星率 0.88(本条 plaza 校准注);昔涟/银狼 3★=plaza 帖文
            # 「除阿格莱雅/昔涟/银狼外不必追任何三星」同句点名(银狼 = shared 终局
            # 成员+lv9 搜索目标,经「攻略明文星级成员」通道入册);风堇辅助普适档 1★
            '阿格莱雅': 3, '风堇': 1, '昔涟': 3, '银狼': 3,
        },
        # 骨架=昔涟(诗篇刷新商店经济引擎)+风堇(core 内非 carry)
        key_items=['昔涟', '风堇'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(昼之半神),档 4
        entry_signals=dict.fromkeys(('阿格莱雅', '风堇', '昔涟', '银狼'), ('synergy', 4)),
    ),
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/README.md 类索引(游戏知识,非字段镜像,无同步义务)
        char_positions={"知更鸟": "front"},   # 站位:知更鸟前台(追击攻略:鸟前台支撑中后期;砂金/灵砂/符玄等生存位也优先前台)
        name="追击飞霄", factions=["追击"], core_chars=["飞霄", "知更鸟", "那刻夏", "不死途"],
        form_tiers={"追击": 3},
        # V4.4 合集(76807134)追击 B 级 = 飞霄-led(纯追击);攻略(76883466):飞霄天赋追击永久+6%增伤,≥3追击=300%倍率
        # 飞霄双风暴潮+鸟(3追击关键)+缇宝/不死途/刃;2星飞霄上9(3星锁血反降);追击转→5追击60%真伤
        # 交叉核对注(锚点交叉核对):飞霄 carry 仅 3 篇(<5 不在聚类)→ plaza_carry 置空;plaza 追击族
        # 真代表 = **那刻夏**(「5追击4昼之半神 后台主c之光」6444 use:「没鞋也没追击转别上那刻夏,
        # 至少得有其1」,装备优先级原文全序列)→ 补 core;追击簇 flex 常见 公司/昼之半神/群攻。
        key_equips=["火力风暴潮", "火力风暴潮", "永动机", "电磁弹射器"],   # 成型羁绊队:追击档乘区(≥3追击=300%倍率)
        shared_chars=["知更鸟", "缇宝", "不死途", "那刻夏"], transition_chars=["赛飞儿", "风堇", "刃"],
        family="legacy",
        flex_factions=["公司", "群攻", "昼之半神"],
        plaza_carry="",   # 飞霄 carry 3 篇悬空;那刻夏(追击真代表,n=6 恰在聚类边缘)未单列阵容
        level_plan={
            5: LevelGoal("roll", target_cost=3, target_chars=["飞霄"]),
            6: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            7: LevelGoal("roll", target_cost=3, target_chars=["飞霄"], star_goals={"飞霄": 2}),
            8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["知更鸟", "不死途"]),
        },
        # ===== 知识卡字段(数据源=本条攻略直读注 76883466+plaza 追击簇注)=====
        lock_rules={
            # 追击概念股=通用阵营入口(无追击专篇;追击=大黑塔线降级路径变体)——
            # 锁定走角色型/时点兜底
            '策略型': [],
            # 攻略结构=飞霄(天赋追击增伤主C,76883466)+知更鸟(3追击关键);
            # ⚠️ plaza 追击族真代表=那刻夏(6444 use)与本线核心=飞霄(攻略明文)
            # 分歧——角色型按攻略重述定,登记在 知识卡建表交叉核对记录
            '角色型': ['飞霄', '知更鸟'],
        },
        need_star={
            # 飞霄 2★=攻略明文「2星飞霄上9(3星锁血反降)」——3★ 有害线,封顶 2★;
            # 知更鸟/那刻夏/不死途辅助普适档 1★
            '飞霄': 2, '知更鸟': 1, '那刻夏': 1, '不死途': 1,
        },
        # 骨架=知更鸟(3追击关键)+那刻夏(plaza 追击族真代表,簇注)+不死途(攻略句内)
        key_items=['知更鸟', '那刻夏', '不死途'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(追击),档 3
        entry_signals=dict.fromkeys(('飞霄', '知更鸟', '那刻夏', '不死途', '缇宝'), ('synergy', 3)),
    ),
    Comp(
        name="万敌单C", factions=["夜之半神", "燃血"], core_chars=["万敌", "千冶·刃", "长夜月", "刻律德菈", "缇宝"],
        form_tiers={"夜之半神": 2, "燃血": 4},
        # 燃血档 = 教义「4-6 档」(下限 4;档位谱真值 = FACTIONS.tiers)。
        #   ⚠️ 行为面:form_progress 成型判定按燃血 4 判(意图内)。
        # V4.4 评级(76807134):万敌 = B 级;【debuff=buff 典型】反伤/AoE/持续伤害 利燃血;攻略(77056698)
        # ↺ (plaza 40 篇校准)B→A:use 榜 #2(11.2w,「万敌无脑单挂A850 7人成型」);3星率 0.93
        # 场最高;5级搜牌 26/40(1费 carry 5 级 D 标准节奏)。**form_tiers 校准(交叉核对注)**:旧 夜4+燃4
        # 仅 15% 帖达标 —— 榜首帖实跑 夜2+燃2(「7人成型」= 万敌+6弹性辅助;另一帖明言「夜神燃血也不
        # 要凑」)→ 降为 2+2(核心=万敌双标签引擎,其余 flex);千冶·刃 40/40 全勤补 core(旧漏)。
        # 遐蝶(n=6)= 同族副 carry(夜神6+燃血6),挂 shared 备转型。

        char_positions={"万敌": "front"},   # 站位:万敌独前排(燃血角斗场吃受击掉血;弃1人口换触发密度)
        key_equips=["火力风暴潮", "热血沸腾拳", "绝对热量", "高周波电锯"],   # 交叉核对注:plaza 热血沸腾拳40>绝对热量26 顺序修正(风暴潮54 断层第一)
# 掉血削上限克燃血(不可玩);利:忍无可忍/正当防卫/灼热轰炸(debuff=buff)
        shared_chars=["风堇", "长夜月", "遐蝶"], transition_chars=["椒丘", "艾丝妲"],   # 长夜月是 core(夜半记录)
        # ===== 万敌燃血家族(无流派;装备收敛:风暴潮 95%+热血拳 90%)=====
        family="万敌燃血",
        bond_signal="夜之半神",   # ②类信号:夜半 2(96% 必配,主档)
        sub_tiers={"战技点": 2},   # 战技点 2(90%,第三引擎);风堇=第二记录器(治疗转伤害)
        equip_assign={"万敌": ["火力风暴潮", "热血沸腾拳", "绝对热量", "高周波电锯"]},
        # ↑ 教义:万敌=风暴潮+热血拳+虫洞掘进钻头(击破体系,不在旧表,拆分补);绝对热量(唯一件)
        # 给谁=时序决策(前期万敌→后期转移)
        equip_taboos=["护盾件(类)", "以牙还牙甲", "掩体生成枪"],
        # ↑ 教义(官方原文):燃血队员无法获盾,受盾只转 2%+1000 回血=负资产;连带盾类装备全禁
        # 无替班:文档明言万敌 1 费开局即在(56% 局 P1 板上),无空窗;P2 加深档数
        flex_factions=["群攻", "量子同频", "战技点", "治疗", "命运圣杯", "减益"],
        plaza_carry="万敌",
        # 全局累积型标注:万敌=受击驱动全局叠层(受伤充能+生命上限永久提高,
        # 用户定案 [21] 例外)——环境满足(敌方多动/反伤类词条)时适用「有空位就上」。
        level_plan={  # 1费 carry:5 级 D 干 3星(0.93 全场最高);boss 前成型即停
            3: LevelGoal("roll", target_cost=1, target_chars=["万敌"]),
            4: LevelGoal("roll", target_cost=1, target_chars=["万敌"], star_goals={"万敌": 2}),
            5: LevelGoal("roll", target_cost=1, target_chars=["万敌"], star_goals={"万敌": 3}),
            6: LevelGoal("roll", target_cost=2, target_chars=["千冶·刃", "长夜月"]),   # 千冶·刃 2费/长夜月 2费
            7: LevelGoal("level_up"), 8: LevelGoal("level_up"),
            9: LevelGoal("roll", target_cost=0, target_chars=["万敌", "千冶·刃"],
                         star_goals={"万敌": 3, "千冶·刃": 2}),
        },
        # ===== 知识卡字段(数据源=final_comps/final_wandi_burn.md)=====
        lock_rules={
            # 开局信号=数量信号(「万敌7只以上可玩,不然重开」#13,构造机理§3)非策略;
            # 超光速提拔(9+/40 篇第一策略,README A3 归类「类专属策略」)**不登记**:
            # 效果=随机1费升4星(cw_invest_data 350301),定向依赖「场上唯一1费」的
            # 操作前提,非「拿到即定线」——与量子力学(获得【希儿】)/骇客专家:银狼
            # (点名银狼)的效果文本直赠线核心不同通道;裁决留痕=知识卡建表交叉核对记录§四。
            # 星魂升华=通用补偿件同理
            '策略型': [],
            # 万敌(40/40 载体)+千冶·刃(40/40 全勤)+刻律德菈(38/40 复制插件=第二万敌)
            '角色型': ['万敌', '千冶·刃', '刻律德菈'],
        },
        need_star={
            # 万敌 3★=3星率 0.93 全场最高+A4 万敌 90%;千冶·刃 2★=level_plan
            # star_goals 攻略口径;长夜月/刻律德菈/缇宝辅助普适档 1★
            '万敌': 3, '千冶·刃': 2, '长夜月': 1, '刻律德菈': 1, '缇宝': 1,
        },
        # 骨架=千冶·刃(全勤通用插件)+刻律德菈(复制插件)+长夜月(夜半记录器,core 内)
        key_items=['千冶·刃', '刻律德菈', '长夜月'],
        # 上线窗口:主羁绊 bond_signal=夜之半神,档 2;万敌本人 = hp_charge_stack
        # 全局累积型([21] 例外「越早越好」——受伤充能全局叠层,先上过渡
        # 羁绊有空位就上)→ always_on
        entry_signals={
            '万敌': ('always_on', 0),
            **dict.fromkeys(('千冶·刃', '长夜月', '刻律德菈', '缇宝', '风堇', '遐蝶'), ('synergy', 2)),
        },
    ),
    Comp(
        name="DOT队", factions=["持续伤害", "星核猎手"], core_chars=["卡芙卡", "黑天鹅", "千冶·刃", "海瑟音", "符玄"],
        form_tiers={"持续伤害": 4, "星核猎手": 2},
        # V4.4 评级(76807134):dot = B 级;攻略(77026641 直读):V4.4 刃加入→卡芙卡回归(刃比普通狼频繁触星核猎手额外战技)
        # 卡芙卡3风暴潮(dot不吃幸运)+黑天鹅(鹅,2dot)+刃(2星核猎手)+刻律(复制战技连动)+鸟;需自己卡芙卡
        # ⚠️ 黄泉减益已拆独立(见上);本阵容=DoT 主派(卡芙卡/鹅/刃/桑博),P1强/P2乏力/P3需转,低费过渡保血权威
        # (plaza 卡芙卡 11/黑天鹅 11 篇校准):常驻 千冶·刃11/黑天鹅10/符玄9/瓦尔特8/海瑟音7
        # (core 的「刃」改「千冶·刃」+补海瑟音);装备 风暴潮19/反重力皮靴8。
        key_equips=["火力风暴潮", "反重力皮靴", "蓄能帆", "光速螺旋桨"],
        # 慢速:DOT 叠层×引爆磨血胜利条件(final_dot_kafka),冻结族词条的慢热载体。
        # 成型羁绊队:持续伤害档一路加深(2→4→6)是本线成长乘区。

        shared_chars=["桑博", "千冶·刃", "黑天鹅"],
        transition_chars=["桑博", "艾丝妲"],
        # ===== DOT卡芙卡家族·A 引爆流(~47%;B 速度/昼半流未建条,拆分落位)=====
        family="DOT卡芙卡",
        bond_signal="持续伤害",   # ②类信号:开局即战力,前期=终局同体一路加深
        sub_tiers={"减益": 2},   # 星核 2(57%)已在 form_tiers(星核猎手2);减益 2(43%)
        equip_assign={"卡芙卡": ["火力风暴潮"], "海瑟音": ["反重力皮靴", "光速螺旋桨"], "黑天鹅": ["蓄能帆"]},
        # ↑ 教义:主C 位风暴潮最优先(卡芙卡技能原文:携带装备直接提高引爆倍率=全游戏唯一装备焊进
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
        # ===== 知识卡字段(数据源=final_comps/final_dot_kafka.md)=====
        lock_rules={
            # 持续伤害契约效果直赠卡芙卡+椒丘,计数 180 得黑天鹅(cw_invest_data 127)
            # ——效果文本级线关联;持续伤害星徽=通用阵营徽章不登记
            '策略型': ['持续伤害契约'],
            # 叠层×引爆双C三件套≈固定(构造机理§2:卡芙卡 50+黑天鹅 50+海瑟音 44)
            '角色型': ['卡芙卡', '黑天鹅', '海瑟音'],
        },
        need_star={
            # 卡芙卡 2★=A4 低饥渴线 DOT 52%(≤2★ 过半;「2星上9」降级路径常在);
            # 黑天鹅/千冶·刃/海瑟音/符玄辅助普适档 1★
            '卡芙卡': 2, '黑天鹅': 1, '千冶·刃': 1, '海瑟音': 1, '符玄': 1,
        },
        # 骨架=黑天鹅(层数机器)/海瑟音(副输出)/千冶·刃(星核副产品+群盾)/符玄(生存)
        key_items=['黑天鹅', '海瑟音', '千冶·刃', '符玄'],
        # 上线窗口:本线 bond_signal 行内注释「开局即战力,前期 = 终局同体
        # 一路加深」——DOT 件无「囤而不上」阶段(P1 即终局形态)→ 全员
        # always_on
        entry_signals=dict.fromkeys(('卡芙卡', '黑天鹅', '千冶·刃', '海瑟音', '符玄', '桑博'), ('always_on', 0)),
    ),
    Comp(
        # 新增(plaza 补缺):景元仙舟族 —— 景元 carry 16 + 彦卿 14 篇。
        # **augment 强联动**:飞光·映月/传剑(各 8/5 篇,AUGMENT_COMP_AFFINITY 硬绑)—— 彦卿+景元师徒,
        # 拿到飞光 = 1费特殊景元+镜流强化;升星次序经济:「先 3星景元,否则镜流 3星后景元变 5费难刷」。
        name="景元仙舟", factions=["仙舟"], core_chars=["景元", "镜流", "彦卿", "符玄"],
        form_tiers={"仙舟": 5},
        # plaza:景元 3星率 0.69(5费);7级搜牌 7/16;装备 电锯13/风暴潮12/皮靴6;常驻 符玄13/爻光11/藿藿11
        key_equips=["高周波电锯", "火力风暴潮", "反重力皮靴", "电光履"],   # 神君:仙舟召唤物计数(12041/12042 变体 id 只计羁绊);成型羁绊队:仙舟5 召唤计数档乘区
        shared_chars=["符玄", "忘归人", "藿藿"], transition_chars=["藿藿", "丹恒·饮月", "符玄"],
        family="legacy",
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
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 景元节)=====
        lock_rules={
            # 飞光双策略=augment 硬绑(AUGMENT_COMP_AFFINITY 1.0;「拿到=近乎硬绑」);
            # 仙舟概念股/邀请=ENV 亲和 0.9/0.8 条目
            '策略型': ['飞光·映月', '飞光·传剑', '仙舟概念股', '仙舟邀请'],
            # 载体对=景元(24/24)+镜流(12/24 全 3★,映月硬绑的双三星结构);
            # 传剑变体(景元+彦卿)走策略型锁定,不入本 AND 名单
            '角色型': ['景元', '镜流'],
        },
        need_star={
            # 景元/镜流 3★=「必须先 3星景元,再追镜流 3星」(升星次序经济,攻略明文)
            # +镜流全 12 帖皆 3★;彦卿/符玄辅助普适档 1★
            '景元': 3, '镜流': 3, '彦卿': 1, '符玄': 1,
        },
        # 骨架=镜流(双三星结构件)+彦卿(传剑搭档)+符玄(19/24 常驻)+藿藿
        # (仙舟三人组 P1→Final 原样保留,构造机理「加法不换件的最纯样本」)
        key_items=['镜流', '彦卿', '符玄', '藿藿'],
        # 上线窗口:无 bond_signal → 主羁绊取 form_tiers 首键(仙舟),档 5
        entry_signals=dict.fromkeys(('景元', '镜流', '彦卿', '符玄', '忘归人', '藿藿'), ('synergy', 5)),
    ),
    Comp(
        # 新增(plaza 补缺):专家桑博 DOT —— 33.3k use 帖(「专家老桑博,越用越有活」5级搜牌)。
        # **env 定义型**:「开局必须刷专家邀请环境」(特邀专家:桑博)—— ENV_COMP_AFFINITY 近乎硬绑;
        # 无专家 env 时强度降档(退化为 DOT队 territory)。桑博本体贝洛伯格阵营(DoT 输出位)。
        # 节奏:1-6 搜桑博2星 → 2-3 前 3星桑博(装备越早越好)→ 存钱升8 搜海瑟音 → 瓦尔特必上。
        name="专家桑博DOT", factions=["持续伤害", "贝洛伯格"], core_chars=["桑博", "卡芙卡", "千冶·刃"],
        form_tiers={"持续伤害": 4, "贝洛伯格": 2},
        key_equips=["火力风暴潮", "火力风暴潮", "冷笑话引擎"],   # 桑博装备越早越好;卡芙卡过渡给随便骰子
        # 慢速:DOT 磨血(桑博 DoT 越早越好,同 final_dot_kafka 磨血胜利条件)。
        # 成型羁绊队:持续伤害档乘区。

        shared_chars=["卡芙卡", "海瑟音", "千冶·刃"], transition_chars=["卡芙卡", "艾丝妲"],
        # ===== DOT卡芙卡家族·桑博专家变体(文档明言:策略入口变体,不独立成套)=====
        family="DOT卡芙卡",
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
        # ===== 知识卡字段(数据源=final_comps/final_dot_kafka.md 桑博专家版节)=====
        lock_rules={
            # 特邀专家:桑博=env 定义型(「开局必须刷专家邀请环境」33k use 帖;ENV 亲和 1.0)
            '策略型': ['特邀专家:桑博'],
            # 专家版核心=桑博(低费引爆器天花板)+卡芙卡+千冶·刃(本线 core 全三件)
            '角色型': ['桑博', '卡芙卡', '千冶·刃'],
        },
        need_star={
            # 桑博 3★=「1-6 搜桑博2星 → 2-3 前 3星桑博(装备越早越好)」(攻略明文);
            # 卡芙卡/千冶·刃辅助普适档 1★
            '桑博': 3, '卡芙卡': 1, '千冶·刃': 1,
        },
        # 骨架=卡芙卡(过渡共享引爆器)+千冶·刃(core 内非 carry)
        key_items=['卡芙卡', '千冶·刃'],
        # 上线窗口:同 DOT队——bond_signal 行内注释「开局即战力,前期 = 终局
        # 同体」→ 全员 always_on
        entry_signals=dict.fromkeys(('桑博', '卡芙卡', '千冶·刃', '海瑟音'), ('always_on', 0)),
    ),
]


# ===== CARRY 锚派生(12 号篇 §1.1「plaza_carry ∪ core_chars 合流」)=====
# CARRY 档口径分两层:**合流全集** = ``carry_set``(单名锚 ∪ core_chars 全员,
# 3.7 持有证据 CARRY 档按「持有任一档内成员」判定)——「无单一直接字段,
# 派生申报」的完整实现;**单名锚** = plaza_carry(聚类注册表锚,层间交叉核对面),
# 3 条空值线(「空 = 无 n≥5 聚类对应」本身是聚类覆盖度信息)按攻略明文逐线
# 补全如下——不改 plaza_carry 字段值,覆写即破坏两层交叉核对锚语义:
CARRY_ANCHOR_FALLBACK: dict[str, str] = {
    # 银枝:攻略明文「必须3星银枝」(77006068 直读;银枝 carry 聚类 n<5 置空)
    '银枝群攻': '银枝',
    # 飞霄:V4.4 合集 76807134「追击 B 级 = 飞霄-led(纯追击)」+76883466 飞霄天赋
    # 追击主C;plaza 追击族真代表=那刻夏为簇注分歧,锚按攻略重述取飞霄
    '追击飞霄': '飞霄',
    # 桑博:33k use 帖「专家老桑博」低费引爆器主C(桑博 carry 聚类 n<5 置空)
    '专家桑博DOT': '桑博',
}


def carry_anchor(comp: Comp) -> str:
    """线 CARRY 单名锚(聚类交叉核对锚;CARRY 档全集见 ``carry_set``——本函数只供
    锚名消费面:聚类交叉核对/空值线补全/锚分歧登记;持有证据分档勿单用本名)。

    plaza_carry 非空 → 直接用(聚类交叉核对锚);空值线查 ``CARRY_ANCHOR_FALLBACK``
    (攻略明文补全,依据就地注释);两者皆缺 → ''(锚缺失申报态,消费侧按无锚处理)。
    ⚠️ 锚与攻略核心输出位存在个别分歧(火花星间旅人:plaza_carry='火花' vs
    攻略明文花火主C)——分歧登记在 知识卡建表交叉核对记录,锚字段保持聚类真值不覆写。
    """
    if comp.plaza_carry:
        return comp.plaza_carry
    return CARRY_ANCHOR_FALLBACK.get(comp.name, '')


def carry_set(comp: Comp) -> set[str]:
    """线 CARRY 档成员全集(持有证据分 CARRY 档口径;12 号篇 §1.1
    「plaza_carry ∪ core_chars 合流」的派生落地;3.7 消费)。

    = {``carry_anchor`` 单名锚} ∪ ``core_chars`` 全员——锚是聚类交叉核对锚(层间
    校准面),core_chars 是核心角色另册;合流后**任一成员在手都计入 CARRY 档**
    (大头档,与 key_items 骨架档/插件档三分,§1.2)。空值 3 线经 fallback
    补全后同样并入。core 至少 1 人 → 返回恒非空;消费侧禁自拼合流集(判据双源)。
    """
    anchor = carry_anchor(comp)
    return ({anchor} if anchor else set()) | set(comp.core_chars)


def char_lock_hit(comp: Comp, held_chars: set[str] | frozenset[str]) -> bool:
    """角色型锁定条件单帧判定(知识卡原语;3.7 硬规则锁定的单一判定源)。

    ``held_chars`` = 持有角色名集(bench + deployed 姓名并集,容器单位域现读);
    名单全员在手即命中(AND 语义,§1.4「关键角色组合到手」)。无角色型条件 →
    False(未命中≠错误,该线走策略型/时点兜底)。
    """
    combo = (comp.lock_rules or {}).get('角色型') or []
    return bool(combo) and all(name in held_chars for name in combo)


def strategy_lock_hit(comp: Comp, held_names: set[str] | frozenset[str]) -> bool:
    """策略型锁定条件单帧判定(知识卡原语;3.7 硬规则锁定的单一判定源)。

    ``held_names`` = 已持有投资策略名 + 已选投资环境名的并集(消费侧组好传入);
    名字经 ``normalize_invest_name`` 归一后比对(OCR 间隔号形变防线,与
    ``augment_affinity`` 同源逻辑)。任一强关联名到手即命中(OR 语义,§1.4
    「策略定义线的形态」)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    rules = (comp.lock_rules or {}).get('策略型') or []
    if not rules:
        return False
    canon_held = {normalize_invest_name(n) for n in held_names}
    return any(normalize_invest_name(r) in canon_held for r in rules)


def get_comp(name: str) -> Comp | None:
    """按名取 Comp;无则 None。"""
    for c in COMP_LIBRARY:
        if c.name == name:
            return c
    return None


# (本文件不含 candidate_faction_universe/candidate_char_universe:
# 环境屏候选线集 = 策略层 invest_env 方向分构造侧求值;「送卡所赠角色是否被
# 候选套使用」的成员判定单一源 = ``gift_hit_tier`` 档位机器,消费位 =
# 策略层 strategies/impl/mandate_v1/gift_value.py。)


# ===== 送卡型档位阶梯(定序机器,零数值;详设原文已删,git 历史可溯)=====
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

    实现三规则(全部定序,零数值;详设原文已删,git 历史可溯):
    ① 即时优先——即时集非空取其最优档,不看条件集(确定性赠卡是估值支撑面);
    ② 条件降档——即时集为空取条件集最优档降一档(core→shared→transition→off);
    ③ advisor 族切换由调用方做(同一套档位判定;本函数不读 advisor)。

    消费位(2026-09-23 迁移迭代 3.2 起)= 策略层
    ``strategies/impl/mandate_v1/gift_value.py``(档→分映射 GIFT_TIER_SCORE
    与 advisor 折减在彼处;本函数只产档,禁消费侧二次推导档位)。
    evicted 传导免费获得:候选套收窄 → 档随之下调或失格(详设 §2.1.4-5
    直调例:持续伤害契约排除三 DOT 套 → 椒丘落 transition;宿主套再被
    排除才整条 'off')。
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


# ===== 评分 helper(阵容相关)=====

def _owned_chars(gs: GameState) -> set[str]:
    """已持有的角色名集合(bench + deployed;容器单位域现读)。"""
    front, back = deployed_rows_of(gs)
    return {u.char_id for u in (*front, *back, *bench_units_of(gs))
            if u is not None and u.char_id}


def form_progress(comp: Comp, gs: GameState) -> float:
    """成型度 0..1:各核心阵营 tier 进度的均值(min(board,form_tiers)/form_tiers)。

    10 的 helper(comp_viability 先验用);纯阵营 tier,不含角色(避免与 char_quality 三重计分)。
    入参 = 容器视图(决策面切统一容器;假想面板轻量桩只需提供
    ``board.value`` 属性,见调用点 _deploy_advances_form 鸭型位)。

    OR 分支与 carry 条件折法(OR 组承接键;
    本函数 = 成型判据唯一折法,fp=1.0 ⟺ 成型谓词「form_tiers 未被承接档
    全档 ∧ or_reqs 组任一满 ∧ required_deployed 全在板」的单一源契约):
    - ``or_reqs`` 非空 → 折为**一条**虚拟分支,分支值 = 组内各分支进度的 max
      (「凑到任一=成型」的进度语义;半成品如 量1∨贝1 如实给 0.5,取
      最好分支非均值);
    - **承接规则**:``form_tiers`` 中与 OR 分支**同键**的档位
      不计入 AND 账(该键的成型语义归 OR 组,分子分母同免——静态套
      希儿量子 form_tiers={量4,贝2} 全被 ``SEELE_OR_REQS`` 承接,成型
      判据即文档 OR 口径;pair 伪阵容两键集恒不相交,本规则对其逐位
      零差)。档位值保留的用途见 ``Comp.or_reqs`` 注;
    - ``required_deployed`` 逐名折一条 0/1 虚拟分支(在板=1;入参无
      deployed 视图(轻量假想面板)按 0 计 = 保守向,缺读≠满成)。
    两字段经 ``getattr`` 缺省空读(真实 Comp 恒有字段;测试鸭型桩与
    旧序列化载体两态按「无 OR/carry 条件」解释,与空字段同值,不炸)。
    两字段缺省空(全注册表阵容)逐位同旧式均值。禁消费位绕过本函数
    自写 min(board,tier)≥tier 内联成型判定(判据双源;内联位清单与
    取代声明)。
    """
    if (not comp.form_tiers
            and not getattr(comp, 'or_reqs', None)
            and not getattr(comp, 'required_deployed', None)):
        return 0.0
    or_reqs = getattr(comp, 'or_reqs', None) or []
    or_owned = {f for f, _t in or_reqs}   # OR 组承接键(同键档位免 AND 账)
    _board = getattr(gs, 'board', None)
    board = getattr(_board, 'value', None) or {}
    total = 0.0
    n = 0
    for f, tier in comp.form_tiers.items():
        if tier <= 0 or f in or_owned:
            continue
        total += min(board.get(f, 0), tier) / tier
        n += 1
    if or_reqs:
        best = 0.0
        for f, tier in or_reqs:
            if tier <= 0:
                continue
            best = max(best, min(board.get(f, 0), tier) / tier)
        total += best
        n += 1
    required = getattr(comp, 'required_deployed', None) or ()
    if required:
        # 席位经容器视图读(无该属性 = 轻量假想面板,按 0 计保守向;
        # 行域合卷为 deployed 单字段,鸭型位同名)
        _view = getattr(getattr(gs, 'deployed', None), 'value', None)
        _front = getattr(_view, 'front_slots', None)
        _back = getattr(_view, 'back_slots', None)
        deployed_names = {
            u.char_id
            for u in (*(u for u in (_front or ()) if u is not None),
                      *(u for u in (_back or ()) if u is not None))
            if getattr(u, 'char_id', None)}
        for name in comp.required_deployed:
            total += 1.0 if name in deployed_names else 0.0
            n += 1
    if n == 0:
        return 0.0
    return clamp(total / n, 0.0, 1.0)


def shop_supply(comp: Comp, gs: GameState) -> float:
    """阵容核心阵营的**本回合** shop 可得性 [0,1](shop-aware)。

    现仅用于 **drought bail 判定**(连续 N 回合 supply<1.0 → 弃不可达 target 重选;default 栈 drought bail 已停用,本函数保留为待办层消费面),
    **不进选靶评分**(原 select_comp 消费位及其理论可得性读口 `acquirability_factor`
    已随死代码清偿移除——shop 可得性对选靶刷新独立 → 观察/单回合
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
    _payload = gs.shop.value
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
    board = getattr(gs, 'board', None)
    board_factions = set((getattr(board, 'value', None) or {}).keys())
    if any(f in board_factions for f in comp.factions):
        return 0.3   # 仅 board 有,shop 买不到更多 → 弱成型信号
    return 0.0


W_PROG: float = 0.45    # 成型进度(form + core_char)—— 偏好可成型阵容
W_MECH: float = 0.15    # 机制契合(双向 debuff=buff)
W_ENV: float = 0.15     # 投资环境契合
W_HELD: float = 0.15    # 已持有策略契合(机会型 pivot;无持有 → None 动态剔除,权重重分配)
W_BOSS: float = 0.10    # boss 克制(无数据 → boss_fit 返 None → 动态剔除;countered_by_bosses 接通即生效)
W_EQUIP: float = 0.10   # 装备契合(阵容相关)
W_STR: float = 0.05     # research meta 强度


# ===== M7 装备角色级分配(方法论 M7:装备是角色特定的,51% 文本覆盖)=====

EQUIP_CAPACITY: int = 3   # 每单位装备上限(below-avatar 最多 3 件,D-49 布局约束)


def _pairing_guard_ok(worn_basics: dict[str, list[str]], char: str, basic: str,
                      key_set: set[str], core_set: set[str], rq: set[str]) -> bool:
    """防误合成配对守卫的纯判定(纪律 1 的两例外;单源判定)。

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

    - ** 同名∧非两基础件合成图谱对 → 拒**:同名对 (item,item) ∈ 配方图
      (8 基础件全有自配配方)= 合法穿着即合成通道,**不拦**(交配对守卫
      例外①core 快路径/②回收线 2合1 既有适用范围;本谓词拦域全为非基础件同名,
      例外域全为基础件交叉配对,两域交 = 空,显式互斥)。同名对 ∉ 图谱
      (非基础件同名)→ 拒——拦域判据 =「非两基础件合成图谱对」的结构
      判据,非「不可合成」断言(蓝钻/红钻自配路线注册表已登记而图谱按类别
      排除)。判据形态 = ``self_advance(item) is None``:同名对只可能命中
      图谱的自配半边。推断级判据:唯一实证为「同名 + 槽满混叠」帧(同名
      单因未直证),定案前按必拒保守拦截(P95 §3 边界②;错杀 = 件滞留
      owned,漏放 = 白拖 + 拉黑记忆,不对称),实测定案后收窄或确证。
      谓词一输入经合成产物展开(P95 §2-A「worn = 现读 ∪ 合成产物展开」)。
    - **谓词二(件专属前置)→ 拒**:结构化条目(data/cw_equipment_wear_rules_data,
      前置/可穿性建模单一源)声明前置(「需要空装备栏」族)∧ 不满足。
      读法定案前取最保守「身上有任意件即拒」(真值读法空间「全空 vs
      ≥2 空槽」两读法下有件均拒,保守缺省无需先行定案);新件漏建模由
      互检显警兜(消费点 = equip_allocation 头部,禁解析散文)。
    - **谓词三(件级/类别专属可穿性门)→ 拒**:fail-closed 白名单双键(结构化
      载体 data/cw_equipment_wear_rules_data)。件级门 ``ITEM_WEAR_GATES``
      先查(更具体层):银狼专属 10 件,白名单 = 银狼 + 银狼LV.999
      【口述·权威 2026-09-18 定案 + 实机实证:run_20260918_075416 分身
      墨镜Max 拖丹恒·饮月静默不生效→失配告警停局;拖错角色 = 游戏静默拒
      无反馈,装备滞留 owned】。类别门 ``CATEGORY_WEAR_GATES`` 后查:
      骇客类,同源定案(假说期「仅银狼LV.999」按口述扩圈为两角色)。
      任一命中且 char 不在名单即拒;白名单外恒拒(fail-closed 结构不变:
      错杀 = 件滞留 owned;漏放 = 白拖 + 拉黑记忆污染 + 永久滞留,
      前者严格小)。

    已知输入失真面(部分有效申报):谓词一/二的 worn 输入与容量扣减同源
    (below-avatar 画面现读),read_row_equipped mini icon 漏读(3 件读 1 实证)
    使 worn 缩水 → 漏读帧拦不全;识别面批收束前谓词部分有效,禁把漏读帧
    的漏拦读成谓词无效(P95 §2 附加范围外声明)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
    from sr_od.application.currency_war.data.cw_equipment_wear_rules_data import (
        CATEGORY_WEAR_GATES,
        EQUIP_WEAR_PREREQUISITES,
        ITEM_WEAR_GATES,
        WEAR_PREREQ_EMPTY_SLOTS,
    )
    from sr_od.application.currency_war.data.cw_synthesis import (
        expand_worn_products,
        self_advance,
    )
    # 谓词一:同名 ∧ 非两基础件合成图谱对(合成产物展开后判定)
    for w in expand_worn_products(worn_all):
        if w == item and self_advance(item) is None:
            return False
    # 谓词二:件专属前置(定案前保守读法 = 有任意件即拒)
    entry = EQUIP_WEAR_PREREQUISITES.get(item)
    if entry is not None and entry.predicate == WEAR_PREREQ_EMPTY_SLOTS and worn_all:
        return False
    # 谓词三:件级专属门(per-item 白名单,先查更具体层)→ 类别可穿性门
    # (fail-closed 白名单);任一命中且 char 不在名单即拒
    _gate = ITEM_WEAR_GATES.get(item)
    if _gate is not None and char not in _gate:
        return False
    eq = EQUIPMENTS.get(item)
    if eq is not None:
        allowed = CATEGORY_WEAR_GATES.get(eq.category)
        if allowed is not None and char not in allowed:
            return False
    return True


def _iter_deployed_rows(view) -> list[tuple[str, int, object]]:
    """上阵视图 → ``(行名, 排内 1 基槽号, Unit)`` 序列(分配器与诊断共用
    同一展开,禁第二份;位置 = DeployedView 子表
    下标派生,视图缺席 = 空序)。"""
    if view is None:
        return []
    out: list[tuple[str, int, object]] = []
    for row_name, sub in (('front', view.front_slots),
                          ('back', view.back_slots)):
        for i, u in enumerate(sub or []):
            if u is not None:
                out.append((row_name, i + 1, u))
    return out


def equip_alloc_empty_reason(comp: Comp | None,
                             view,
                             owned: list[str],
                             occupied: dict[tuple[str, int], list[str]] | None = None,
                             ) -> str:
    """``equip_allocation`` 返回空时的结构化归因(纯函数)。

    返回值域:
    - ``pool_empty``:owned 穿戴池空(调用方无货可分);
    - ``no_deployed``:场上无可命名角色(无处可穿);
    - ``capacity_full``:所有在场角色的装备容量都已占满;
    - ``pairing_guard``:有货有空位,但每个 (角色,装备) 组合都被防误合成配对守卫拦下;
    - ``wearable_gate``:有货有空位,但每个 (角色,装备) 组合都被穿着可行性
      三谓词(同名非图谱对/件前置/类别门)拦下——与 ``pairing_guard`` 同族
      分键,stop_reason 同走「分配方案空:」前缀 → 哨兵归域 strategy_gap,
      归域枚举零改动;
    - ``unknown``:存在可行组合但分配仍返回空(不该发生,出现即分配器与诊断漂移,优先查)。

    归因前提:仅当 ``equip_allocation`` **返回空** 时调用才精确——分配一旦产出
    件,容量/已穿基础件会随分配演进,诊断函数只复现「零分配起点」的状态。
    与 ``equip_allocation`` 同输入口径(occupied/completed 前提下守卫状态一致:
    空分配 ⇔ 无任何 ``_assign`` 发生)。可行性判定与分配器共用
    ``_pairing_guard_ok``/``_wearable_gate_ok`` 单源(镜像纪律)。
    ``view`` = 上阵视图 :class:`DeployedView`(位置 =
    子表下标派生,排归属由子表承载,occupied 键 (row,行内槽号))。
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
    for row_name, slot_no, d in _iter_deployed_rows(view):
        n = getattr(d, 'char_id', None)
        if n:
            by_name.setdefault(n, []).append((row_name, slot_no, d))
            for w in occ.get((row_name, slot_no), []):
                worn_all.setdefault(n, []).append(w)
                if is_basic(w):
                    worn_basics.setdefault(n, []).append(w)
    for n, ds in by_name.items():
        used = sum(len(occ.get((_rn, _sn), [])) for _rn, _sn, _d in ds)
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


def equip_allocation(comp: Comp | None,
                     view,
                     owned: list[str],
                     occupied: dict[tuple[str, int], list[str]] | None = None,
                     priority_order: list[str] | None = None,
                     ) -> list[tuple[str, str]]:
    """(角色名,装备名) 分配序列 —— carry 先拿 key_equips(按序),其余 core 次之,剩余兜底前排。

    M7 方法论(plaza 648 篇 51% 谈装备):「保证三月有一鞋一风扇,花火和杨叔的回能,姬子的双风暴」
    「那刻夏全套 > 生存装 > 弹射器 > 永动机,一定要按这个顺序」—— 装备是**角色特定的**,不是
    有装备就穿(用户 §7-9 同)。分配纪律:
    1. **carry 先拿**:comp.plaza_carry(不在场上则 core_chars 中首个场上者)按序拿
       key_equips(multiplicity 消费,不超发);
    2. **其余场上 core** 拿剩余 key_equips(core 顺序);
    3. **剩余通用 owned** 按 deployed 顺序兜底(前排在前 —— 受击/反甲类在前排生效)。
    ``occupied[(row, slot)]`` = 已穿列表(容量扣减,EQUIP_CAPACITY);
    ``view`` = 上阵视图 :class:`DeployedView`(元素 = 容器 ``Unit``,
    char_id/star/equips 直读,排归属与行内槽号由子表下标派生——
)。阵容=None → 全走 3(通用兜底)。纯函数(可离线测);
    消费面 = `kernel/cw_equip_env.py`(判据求值位)。

    ``priority_order``(18 号稿 §3.3 签名扩展):可选分配优先序
    (list[str],角色名);None(缺省)= 现行内部派生序,**零行为漂移**。
    语义 = 词缀条件优先层(§3.2)的唯一传入通道:序的每个成员在分配侧都
    被**吃满至容量**(凑满谓词;调用方 = 策略侧 resolve_affix_priority_order,
    只放「谓词未满足成员 ∪ core」);它同时改写 key_equips 接收者序与 core
    兜底序。语义保持声明(§3.3 措辞收窄):配对守卫与星徽唯一件守卫对候选
    对的判定与遍历次序无关,重排序下逐对语义不变;occupied 容量扣减的
    **可穿件总数**与次序无关,「落在谁身上」随次序变 = priority_order 的
    语义本体,不属语义漂移。**阵容=None 时强制 None**(§3.3:重排依据依赖
    阵容名单;未定型帧零重排)。**脱落预防(18 号稿 §1.2-3)**:分配器为
    fill-only——occupied 仅作容量扣减,不触碰任何已穿件(key 与否同判),
    任何重排都不可能取下已穿 key 件(装备无角色间直拖通道,10 号稿 §2.1.8)。

    (穿戴可逆裁决):**穿戴是可逆操作**(卖角色全额返还装备)——穿着既不锁死
    合成路线(组件可取回)也不构成资源损耗(转移成本仅为操作摩擦),
    故无「合成保留组件禁入穿戴池」过滤。组件保护由两条真实依据的防线承担:
    ①合成终局阵容锁定门(方向确定性才合成,反「压注未定方向」——不可逆的金/
    组件消耗只在终局阵容锁定后发生);②下方防误合成配对守卫(真实不可逆依据:
    非预期合成不可逆消耗两件组件,无确认无回退)。
    **简易件默认穿**(编排者裁决:「简易件效果不大,穿不穿随策略定」→
    采纳默认穿):组件与进阶成品同池参与分配,期望收益由磨损标定仪持续
    测量(设计件:借实机/sim 对照测简易件穿戴的真实期望收益)。

    (P14 期望模型接入,口述「穿着即合成/囤积/回收线」):两条新纪律——
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
    以概率 1 拒收的 (件,角色) 对,分配前排除严格支配分配后重试——谓词一:同名∧
    非两基础件合成图谱对 / 谓词二:件专属前置(「需要空装备栏」族,结构化载体
    data/cw_equipment_wear_rules_data)/ 谓词三:件级/类别专属可穿性门 fail-closed(银狼专属 10 件白名单 = 银狼 + 银狼LV.999,
     2026-09-18 口述定案)。与
    ``_pairing_ok``/``_emblem_ok`` 同构并列,被拦件**留 pool**(跳过=留
    owned,不 pop 丢弃);谓词一拦域与配对守卫例外①②适用范围显式互斥(两域交=空,
    同名自配对合法穿着即合成通道不拦)。消费位 = key 环/core 吃满/非 core
    保底/阵容=None 轮转四处候选过滤(与 _emblem_ok 挂载点全集一致;P95
    命题主语 = (件,角色) 对,必拒对全分配通道排除)。死库存回收线不挂:
    池域 = 基础件,三谓词对基础件恒放行。
    """
    occ = occupied or {}
    pool = list(owned)
    if comp is None:
        priority_order = None   # 18 号稿 §3.3:未定型帧词缀谓词集合退化,强制零重排
    _units = _iter_deployed_rows(view)
    by_name: dict[str, list] = {}
    for row_name, slot_no, d in _units:
        n = getattr(d, 'char_id', None)
        if n:
            by_name.setdefault(n, []).append((row_name, slot_no, d))
    capacity: dict[str, int] = {}
    for n, ds in by_name.items():
        used = sum(len(occ.get((_rn, _sn), [])) for _rn, _sn, _d in ds)
        capacity[n] = max(0, EQUIP_CAPACITY * len(ds) - used)

    # =====:防误合成守卫 + 回收去向(P14 定理 3/4)=====
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
    # 的谓词一/二输入,经合成产物展开消费)
    worn_basics: dict[str, list[str]] = {}
    worn_all: dict[str, list[str]] = {}
    for row_name, slot_no, d in _units:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        for w in occ.get((row_name, slot_no), []):
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
        """阵营星徽 → 排除已自报同阵营角色(复盘 g_20260902_181254 定案)。

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
        # key 件绑定裁决(18 号稿 §3.2):谓词层只重排候选序,
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
                    # :key 豁免的基础件同样过配对守卫(防非预期合成)
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
    # 身份过滤:非 target 角色穿满通用件 = 换人时一件件拆(即时小收益换后期摩擦)。
    # 规则:阵容有 core 在场时,兜底优先发 core(哪怕 deployed 序靠后);
    # 非 core 每人只兜底 1 件(防裸奔),core 吃满。
    # 阵容=None:**按轮转**(每人 1 件轮一圈再回头,而非按 deployed 序灌满一人
    # ——否则前排 capacity 全被第一人吃光);阵容有 core 时行为不变。
    if comp is not None:
        # core 兜底序:priority_order 在列时按其序吃满(凑满谓词语义,契约 =
        # 调用方只放「谓词未满足成员 ∪ core」);缺省 = core_chars 序(零漂移)
        if priority_order:
            _cores = [c for c in priority_order if capacity.get(c, 0) > 0]
        else:
            _cores = [c for c in comp.core_chars if capacity.get(c, 0) > 0]
        # (_units 元素 = (行名,槽号, Unit) 三元组,_iter_deployed_rows 契约;
        #  构造解包吃掉槽号位——下游消费(死库存回收/保底)全按 (rn, d)
        #  二元组,曾按二元组解包 _units 即此处崩点,持有阵容的局走到
        #  通用兜底段必炸。)
        _others = [(rn, d) for rn, _sn, d in _units
                   if getattr(d, 'char_id', '')
                   and d.char_id not in comp.core_chars]
        # 死库存回收去向:先于 core 兜底抽取(防 core 盲吃死库存),
        # 非 core 工具人每人至多 2 件(两件互为配对 → 游戏自动 2合1 =
        # 回收线有意触发;发不完留 owned 囤着)
        _dead = [e for e in pool if e in _rq]
        if _dead:
            for _pass in range(2):
                if not _dead:
                    break
                for _rn, d in _others:
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
        for _rn, d in _others:
            n = d.char_id
            if pool and capacity.get(n, 0) > 0:
                idx = next((i for i, e in enumerate(pool)
                            if not (_is_basic(e) and not _pairing_ok(n, e))
                            and _emblem_ok(n, e)
                            and _wearable_ok(n, e)), None)
                if idx is not None:
                    _assign(n, pool.pop(idx))
        return out
    # 阵容=None:轮转分配;配对守卫生效
    # (阵容=None 无豁免信息 → 任何互为配方的基础件对不同人发)
    _names = [d.char_id for _rn, _sn, d in _units
              if getattr(d, 'char_id', '')]
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


# ===== 巨星(select_megastar)与 commit 判据 =====

# T#97 commitment(COMMIT_FRAC 单一定义;消费 = cw_equip_env 工具激活面
# 的「未 commit」半支)。commit = 已成型(form_progress>=COMMIT_FRAC)。
COMMIT_FRAC: float = 0.4           # form_progress >=0.4 算已 commit(2 阵营阵容约 1 阵营过半)


# 阵容级巨星偏好(序 = 优先;按「阵容引擎 × 巨星乘区」绑定(详 strategy/02_comp §7),
# 替代旧 3 条属性键粗映射。未列的阵容走 core/在场优先)
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
    # 兜底(偏好表未列的阵容):阵容机械属性 → 巨星
    '幸运一击': '知更鸟', '击破': '大丽花', '高倍率单核': '星期日',
    '群攻': '知更鸟', '欢愉叠层': '知更鸟', '追击': '知更鸟', '战技点依赖': '花火',
}


def select_megastar(gs: GameState, target: Comp | None,
                    available_megastars: list[str]) -> str | None:
    """选 1 名盛会之星作巨星(盛会之星羁绊核心决策;按 target_comp 选,不单独评分)。

    选择序(按阵容引擎 × 巨星乘区,详 strategy/02_comp §7):
    1. target.core_chars 里的盛会之星(在阵 core 天然绑定,如追击飞霄×知更鸟);
    2. COMP_MEGASTAR_PREFERENCE[target.name](阵容级偏好序);
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


# (select_megastar_enhance「强化角色」意向已停用——机制语义
#  本就是待证假设,证据链见原函数注释的 git 历史,勿复活。)

