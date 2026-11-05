"""货币战争 阵容库(纯逻辑,可测,不碰游戏)。

战略层:围绕目标阵容 commit + 转型 + 巨星。
auto-chess 胜负手 = commit 哪个阵容 + 何时转型 + 巨星绑谁;本模块给**可配置 + 自适应**的选目标机制。

数据与设计依据(阵容知识源 = ``docs/game/currency_war/research/final_comps/`` 系列 +
``docs/game/currency_war/data/plaza_meta.md``;观察设计权威版本 = strategy-docs 15 号篇;
字段设计方法论 = skill sr-od-dev-currency-war references/comp-definition.md):
- ``COMP_LIBRARY``:起步 roster(21 套,姬子列车 A/B 拆分后;plaza 784 篇高难帖校准)。
  **两层架构**:``cw_plaza_comps.py``(gen_plaza_comps.py 生成)= base 事实层(实战频次/装备/节奏);
  本文件 COMP_LIBRARY = 手判层(深入游戏理解逐个敲定,统计只给候选)—— ``plaza_carry`` 字段
  是两层交叉核对基准。覆盖易/中/难成型 + 各机制(含 debuff=buff 的燃血、augment 定义型的黑塔纪元)。
(旧 comp_score 多维评分器已随 select_comp 入口整族移除;锁定 = 候选-锁定制。)。

**核心原则(用户 2026-08-03,贯彻全程)**:
1. **一切阵容相关** —— equip/mechanics 都挂钩目标阵容,无孤立评分(不设通用 equip_score/词缀表)。
   反重力皮靴对昼神阿雅(需 2 靴)是命脉、对别的阵容不一定;正当防卫词缀对万敌燃血是利、对阿雅是克。
2. **COMP_LIBRARY 运行时按场面选** —— 不锁死一套,按成型难度/boss/环境/词缀灵活选易成型又够强的。
3. **Comp = 目标态快照**(comp-definition 第一条,2026-11-04):终局形态定义,不含时间过程
   ——节奏由「位面-轮骨架 × 刷新率真值 × 目标态」三层组合自适应涌现(旧 level_plan 手编曲线已废)。

**核心/弹性羁绊二分**:``factions`` = 核心羁绊键集(faction_reqs 档 0 派生;成型判定);``flex_factions`` = 弹性次要
(plaza 实证「核心保证四列车即可,其他自由搭配」—— 板朝 flex 铺不罚,env/策略亲和照吃)。
**投资↔阵容关联**(augment/env 定义型近硬绑类):运行时单一源 = 效果原文通道派生
``kernel/cw_invest_channels.py``(统一阵容评分迭代起,旧两亲和表已退役)。

⚠️ meta(版本依赖):core_chars/faction_reqs 档 0 是 V4.4 估值(plaza 校准 +
米游社合集 76807134),replay + 实玩迭代。装备 Final-only = plaza UI 限制(时序看合成首选,非玩法事实)。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    GiftGrant,
)
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    bond_members,
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
class Comp:
    """一套目标阵容(目标态快照:终局是什么;时间/过程归策略机制层,
    comp-definition 第一条)。

    核心/弹性羁绊二分(plaza 784 篇实证「核心保证四列车即可,其他自由搭配」):
    ``factions`` = 核心羁绊键集(faction_reqs 档 0 派生,成型判定只看它);
    ``flex_factions`` = 弹性次要羁绊(不进 faction_reqs,但板面朝它铺不被
    board_alignment 罚、env/策略绑定照常亲和)。
    ``plaza_carry`` = cw_plaza_comps 聚类 carry 名(交叉核对基准;空 = 无 n≥5 聚类对应)。
    """
    name: str                    # "追击飞霄"/"昼神阿雅"/"万敌单C"(roster 单一源 = 本注册表)
    core_chars: list[str]        # 核心角色(名)["飞霄","知更鸟"]
    faction_reqs: dict[int, dict[str, int]] = field(default_factory=dict)
    """羁绊要求(优先级结构):键 = 优先级档(0 最高,档号小 = 重要),
    值 = {羁绊规范名: 目标人数(几人激活算达标)}。
    - 档 0 = 核心羁绊层:同档多键 = 需要多个核心羁绊,等权、全部凑齐才成型;
    - 档 ≥1 = 加分层:进部署次层与采购面,不进成型判定;
    - 档 0 可缺席(非羁绊成型阵容,如反甲白厄——空 dict)。
    档内键书写顺序零语义(结构契约:changes/2026-11-04-comp-structure-
    unification details/faction-priority.md §2;唯一过渡期例外 =
    cw_intention 面板主羁绊名首键读法,随配方机器退役)。"""

    @property
    def key_equips(self) -> list[str]:
        """关键装备清单 = equip_assign 投影(汇总+去到人;C4/C5 完成态;
        可含重复,如阿雅需 2 反重力皮靴)。实现单一源 =
        :func:`derive_key_equips`,恒等由构造保证(无独立数据字段);
        消费端读法零改动(字段退役为读口)。"""
        return derive_key_equips(self)

    shared_chars: list[str] = field(default_factory=list)
    """第二档终局成员(进终局成员集/采购面/送卡 shared 档;
    身份行为包——装备 key 件绑定/不卖保护/优先级 0 档——
    只挂 core,这是与 core 的语义边界)。"""
    transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)
    # 阵容特定站位要求(角色→排级或槽位级),覆盖注册表 position_pref 默认
    # (CW 玩法每角色的可选站位真值,cw_chars.position:技能效果绑定站位)——
    # 值域:'front'/'back'(排级,自适应选槽)| 'front@0'-'front@3'/
    # 'back@4'-'back@9'(槽位级,@n = board_index 全局槽位坐标,与攻略
    # 记号同源:0-3=前排槽1-4、4-9=后排槽1-6;解析见 parse_char_position)。
    # 槽位级语义 = 落位优先占该槽(被占/超容 → 该排自适应回退,软约束)。
    # 攻略实证:爻光必后台(后台跑条给绯英多开大,总伤更高)、万敌独前排
    # (燃血吃受击)、知更鸟前台(追击支撑)、万敌/绯英@0 一号位(标准式)、
    # 三月七@4-6 后排中段(护盾相邻覆盖最大化)。空 = 全按注册表默认。
    char_positions: dict[str, str] = field(default_factory=dict)
    flex_factions: list[str] = field(default_factory=list)  # 弹性次要羁绊(不进 faction_reqs)
    plaza_carry: str = ""        # plaza 实战聚类 carry 名(交叉核对基准,查 cw_plaza_comps.cluster_by_carry)

    # ===== 字段扩(C4 契约冻结语义;leader 裁决)=====
    # 字段语义冻结;各套填值草案级(流派统计刷新可再改)。教义级内容(禁忌/铁三角/替班不卖)
    # 逐条对 final_comps 各篇(research/final_comps/)原文,不自创。
    equip_assign: dict[str, list[str | EquipChoice]] = field(default_factory=dict)
    """装备到人(C4 最大新增;C5 完成态 = 关键装备唯一真源):角色名 → 装备序列
    (str=fixed 首选 / EquipChoice 两档)。键 ⊆ core_chars ∪ shared_chars(替班者
    并入成员名单承载,建库期 ``__post_init__`` 校验);``key_equips`` 为本字段的
    投影读口(委托 :func:`derive_key_equips`,恒等由构造保证——无独立数据字段);
    终局条目非空由库级建库校验钉住(防新条目开空账)。"""
    equip_taboos: list[str] = field(default_factory=list)
    """本套禁买禁合成装备/装备类(教义手编,官方机制原文;如万敌禁一切护盾件)。"""

    # required_deployed 缺省空 = 行为不变。写方 = 终局条目直写(希儿量子)
    # 与过渡组合条目生成期显式填(_build_transition_combos)。判定/进度
    # 唯一折法 = ``form_progress``(单一源契约 fp=1.0 ⟺ 成型谓词),禁
    # 消费位绕过自写内联判定(判据单一源契约)。
    required_deployed: tuple[str, ...] = ()
    """carry 在场条件:逐一必须**在板**(deployed;bench 在手不算)——文档
    成型判据第一合取支「希儿在场」(transition_combos.md:27)。空 = 无
    carry 条件。进度折法:逐名折一条 0/1 虚拟分支(在板=1 否则 0);state
    缺 deployed 视图的轻量假想面板按 0 计(保守向,缺读≠满成)。"""

    # ===== 知识卡字段(选线/升级的共用知识地基;设计口径 =
    # strategy-docs/12_line_and_intention.md §1)。玩法知识(终局阵容的客观
    # 定义——攻略数据,换策略不变其值),非策略层立场数据(宪法第 5 条对账
    # 申报见 12 号篇 §1.1)。=====
    # (旧 lock_rules 字段〔角色型/策略型锁定条件查表〕已随统一阵容评分迭代
    #  整字段退役〔2026-11-03 用户裁定:全部即时锁退役,分数说话〕;旧
    #  entry_signals 字段〔上线窗口信号表〕亦整体退役〔2026-11 用户终裁
    #  「可退役」:万敌 1 条/白厄 3 条知识真空接受损失,上场时机 = 部署
    #  搜索骨架/L1 完成度自适应〕——沿革与登记口径考古走 git 历史。)
    need_star: dict[str, int] = field(default_factory=dict)
    """每角色必要星级(锁定后星级目标单一源;12 号篇 §1.4;停留门/
    刷新判据消费)。键 = 角色规范名(线终局成员:核心输出位 + core_chars +
    攻略明文星级成员),值 = 必要星级;定义 3★ 就追到底无降档、定义 2★ 即完成
    (12 号篇 §1.4)。定值规则:核心输出位按线攻略明文,无明文线按星级饥饿两档表定为
    (final_comps README A4:高饥渴线 Final 3★ 占 80-94% 标 3★/低饥渴线 ≤2★ 过半
    标 2★);辅助 1★(A4 辅助普适档——D 牌预算全落核心,辅助升星只吃自然来牌);
    攻略明文更高者以明文为准。(旧双源 level_plan.star_goals「对拍基准」已随
    level_plan 退役删除——对拍测试从未存在,消费单一源 = 本字段。)"""
    key_items: list[str] = field(default_factory=list)
    """骨架件/贯穿件名单(持有证据分的中档;12 号篇 §1.1;候选分数消费)。
    坐标系 = 角色规范名;数据源 = final_comps 各篇构造机理「槽位构造」的引擎/贯穿/
    常驻件登记(线核心输出位以外的结构成员,可含 shared/transition 层的贯穿件——
    姬子线饮月类)。与 CARRY 档成员全集(``carry_set`` 合流口径)可能相交,持有
    证据分档的消费序归线分数(12 号篇 §1.1)。插件档 = 线成员 − CARRY − 本名单(派生,不入表)。"""
    def __post_init__(self) -> None:
        # 双列回声建库校验(core∩shared = ∅):终局成员身份由 core 列
        # 单列承载,shared 列重复登记 = 数据噪声(所有消费面被 core 覆盖)
        # ——回声数据重现 import 即炸
        _echo = set(self.core_chars) & set(self.shared_chars)
        if _echo:
            raise ValueError(
                f'{self.name}: shared_chars 与 core_chars 交集非空 '
                f'{sorted(_echo)}(双列回声;终局成员身份由 core 列承载,'
                'shared 只登记第二档终局成员)')
        # 站位值域建库期校验(排级/槽位级;消费端信任值合法,解析
        # 单一源 = parse_char_position)
        for _who, _pos in self.char_positions.items():
            if _pos not in _VALID_CHAR_POSITIONS:
                raise ValueError(
                    f'{self.name}: char_positions[{_who!r}] = {_pos!r} '
                    '不在合法值域(front/back/front@0-3/back@4-9)')
        # 羁绊要求结构建库期校验(faction-priority.md §5;非法数据
        # import 即炸,消费端信任结构合法)
        from sr_od.application.currency_war.data.cw_factions import FACTIONS
        seen_bonds: dict[str, int] = {}
        prios = sorted(self.faction_reqs)
        # ④ 档号非负、不跳档(连续 0..max;档 0 缺席 = 全空 dict)
        if prios and (prios[0] != 0
                      or prios != list(range(prios[-1] + 1))):
            raise ValueError(
                f'{self.name}: faction_reqs 档号须非负且连续 0..max,'
                f'实得 {prios}')
        for prio in prios:
            layer = self.faction_reqs[prio]
            for bond, need in layer.items():
                # ① 羁绊名 ∈ 注册表白名单
                if bond not in FACTIONS:
                    raise ValueError(
                        f'{self.name}: faction_reqs[{prio}] 羁绊名未注册'
                        f' {bond!r}(白名单 = cw_factions.FACTIONS 键全集)')
                # ② 同一羁绊不得跨档
                if bond in seen_bonds:
                    raise ValueError(
                        f'{self.name}: 羁绊 {bond!r} 同时出现在档 '
                        f'{seen_bonds[bond]} 与 {prio}(禁跨档)')
                seen_bonds[bond] = prio
                # ⑤ 值恒为正整数(几人激活算达标;区间形态不合法)
                if not isinstance(need, int) or isinstance(need, bool) \
                        or need <= 0:
                    raise ValueError(
                        f'{self.name}: faction_reqs[{prio}][{bond!r}] '
                        f'= {need!r} 须为正整数(几人激活算达标)')
        # 装备到人键域建库期校验(键 ⊆ core ∪ shared——替班者并入成员名单
        # 承载;非法数据 import 即炸,消费端信任键合法)
        for _who in self.equip_assign:
            if _who not in self.core_chars and _who not in self.shared_chars:
                raise ValueError(
                    f'{self.name}: equip_assign 键 {_who!r} ∉ '
                    'core_chars ∪ shared_chars(替班者须并入成员名单承载)')

    @property
    def core_faction_reqs(self) -> dict[str, int]:
        """档 0:核心羁绊层(成型判据层)。"""
        return self.faction_reqs.get(0, {})

    @property
    def bonus_faction_reqs(self) -> dict[str, int]:
        """档 ≥1 合并:加分层(部署次层/采购面)。档号升序合并——同一羁绊
        不跨档(建库校验②),故合并顺序不产生覆盖歧义,仅为确定的遍历序。"""
        out: dict[str, int] = {}
        for p in sorted(self.faction_reqs):
            if p:
                out.update(self.faction_reqs[p])
        return out

    @property
    def factions(self) -> list[str]:
        """核心羁绊键集(档 0 派生;单一源 = faction_reqs 档 0)。
        成型判定/集合消费语义;序 = 档 0 插入序(零序敏感消费,
        消费面全是集合语义)。"""
        return list(self.core_faction_reqs.keys())

    @property
    def all_factions(self) -> set[str]:
        """阵容轮廓:核心 ∪ 副档 ∪ 弹性羁绊全集(亲和/过滤/板面判定用;
        成型判定仍只看档 0)。副档键计入轮廓 = 副档语义修正
        (comp-structure-unification 3.1 变化②——旧读法不含副档键,
        属消费面未接副档字段的历史遗留,非设计裁定)。"""
        return (set(self.factions) | set(self.bonus_faction_reqs)
                | set(self.flex_factions))

    @property
    def members(self) -> tuple[str, ...]:
        """终局成员集：core ∪ shared，注册表声明序去重（core 位在前）；
        transition_chars 不计（打工后卖，不构成终局成员）。
        消费语义锚 = strategy-docs/12_line_and_intention.md §2（line_members_view
        读口/禁第二读口径）与 strategy-telemetry `k_members` 行（锁定帧语义）。
        集合消费写 ``set(comp.members)``；序 = 注册表声明序（截断/排序 tie-break 消费）。"""
        return tuple(dict.fromkeys(tuple(self.core_chars)
                                   + tuple(self.shared_chars)))


#: char_positions 合法值域(排级两值 + 槽位级;@n = board_index 全局坐标)
_VALID_CHAR_POSITIONS: frozenset[str] = frozenset({'front', 'back'}) | {
    f'front@{i}' for i in range(4)} | {f'back@{i}' for i in range(4, 10)}


def parse_char_position(value: str) -> tuple[str, int | None]:
    """char_positions 值解析 → (排, 排内槽号或 None)。

    值域与坐标系(字段值 = board_index 全局槽位坐标,与攻略记号同源):
    - ``'front'``/``'back'``:排级 → ``(排, None)``(落位自适应选槽);
    - ``'front@0'``-``'front@3'``/``'back@4'``-``'back@9'``:槽位级 →
      返回**排内 1 基槽号**(``front@0``→``('front', 1)``、
      ``back@5``→``('back', 2)``——@4=后排槽1,依此类推 @n-3);
      语义 = 落位优先占该槽(被占/超容 → 该排自适应回退,软约束)。
    值合法性由 ``Comp.__post_init__`` 建库期校验;本函数对未校验值
    raise ValueError(数据错误早暴露,禁静默降级)。"""
    if value in ('front', 'back'):
        return value, None
    if '@' in value:
        row, _, num = value.partition('@')
        if row in ('front', 'back') and num.isdigit():
            slot = int(num)
            if row == 'front' and 0 <= slot <= 3:
                return row, slot + 1
            if row == 'back' and 4 <= slot <= 9:
                return row, slot - 3
    raise ValueError(f'char_positions 非法值: {value!r}'
                     '(合法: front/back/front@0-3/back@4-9)')


def derive_key_equips(comp: Comp) -> list[str]:
    """关键装备清单 = equip_assign 投影(汇总 + 去到人;C4/C5 迁移完成态的唯一实现体)。

    展开规则:按 equip_assign 字典序逐人逐件——fixed 条目原样,pool 条目
    (:class:`EquipChoice`)贡献**全部候选**(候选池内每件都是关键件,
    黄泉第四件类),展开顺序 = choices 优先序。equip_assign 为空(过渡组合
    条目/手构桩)→ 空表;终局条目非空由库级建库校验
    :func:`_validate_comp_equip_assign` 钉住。

    顺序语义:展开序 = 到人配方序(字典序)即教义序,仅影响
    ``equip_allocation`` 的 carry 按序取件在容量紧张帧的先后微差(合成材料
    判定/囤货缺口消费为多重集语义);``Comp.key_equips`` property 委托本函数,
    恒等由构造保证(独立手编字段已退役,无第二源)。
    """
    out: list[str] = []
    for _person, items in comp.equip_assign.items():
        for it in items:
            if isinstance(it, EquipChoice):
                out.extend(it.choices)
            else:
                out.append(it)
    return out


def _validate_comp_equip_assign(library: list[Comp]) -> None:
    """终局条目装备到人配方库级建库校验(C5 完成态;非法 raise ValueError)。

    逐条目 equip_assign 非空——空账即回退「清单无到人真源」的双源形态,
    且 key_equips 已是纯投影,import 期即炸(防新条目开空账)。过渡组合条目
    (TRANSITION_LIBRARY)不在本库,空配方合法;键 ⊆ core ∪ shared 由
    ``Comp.__post_init__`` 逐实例校验,本函数不重复。
    """
    for comp in library:
        if not comp.equip_assign:
            raise ValueError(
                f'{comp.name}: equip_assign 为空(终局条目必须登记装备到人配方)')


def derive_member_priority(comp: Comp) -> dict[str, int]:
    """成员优先级两档派生(core 0/第二档终局成员 1;序数小 = 优先级高)。

    core 先填 0,shared 再 setdefault 1(先到先得,同名不覆盖)——注册表
    条目 core∩shared 恒空(``Comp.__post_init__`` 建库校验),setdefault
    分支在库内条目上不触发,仅为库外构造的 Comp 保持函数稳健。两档序数 =
    统一让位序的底层档内①键(消费规格 = strategy-docs/
    32_unified_sell_priority.md;装配读口 :func:`member_rank_of`);
    逐角色线内全序精调若立项,再升显式字段。"""
    rank: dict[str, int] = dict.fromkeys(comp.core_chars, 0)
    for n in comp.shared_chars:
        rank.setdefault(n, 1)
    return rank


def member_rank_of(comp: Comp) -> dict[str, int]:
    """成员优先级序数表读口(档 2/3/4/5/7 档内①键单一源,消费端 =
    mandate_v1/criteria/priority.py 装配)。

    两档派生(core 0/其余 1)由 :func:`derive_member_priority` 现算——
    字段化形态已退役(20/20 恒派生值零手编,「精调登记」从未发生);
    逐角色线内全序精调若立项,再升显式字段。
    """
    return derive_member_priority(comp)


# ===== 环境 → 阵营/阵容亲和(P1-2 T0 env 近乎硬绑 + R2-9 env→faction)=====
# 库藏生锈词缀名(`w607_affix_consumption/` H2 消费钩子的词条识别名):备战席每 1 件未穿装备 →
# 敌方造成伤害 +3%、受到伤害 -4%,最多计 10 件
# (docs/game/currency_war/data/competitors.md:45,2026-08-28 游戏内实采)。
RUST_AFFIX_NAME: str = '库藏生锈'


# (旧 ENV_COMP_AFFINITY/AUGMENT_COMP_AFFINITY 两亲和表与 augment_affinity/
#  augment_env_affinity 查询口已随统一阵容评分迭代退役删除〔2026-11-03,
#  design §7 退役清单〕——投资↔阵容关联的运行时单一源 = 效果原文通道派生
#  kernel/cw_invest_channels(env_line_bonus/strategy_line_bonus,实证覆盖升档
#  +定义卡+引擎匹配手编表);查询归一防线随迁(入口先 normalize_invest_name)。
#  沿革与 plaza 频次校准数据考古走 git 历史。)


# (全局过渡池三常量(EARLY_CORE_POOL/TEMPO_POOL/TRANSITION_POOL,按跨阶段存活率
#  两级的 plaza 实证)与 char_routes()「角色→路线复用网络」已删:全库零消费
#  ——「接入调用前数据先验」的接入调用方(旧过渡工程/买牌 optionality)未建即被
#  BRIDGE_POOL 配方体系与统一让位序取代;知识底稿在 plaza_meta/final_comps,
#  将来立项按版本重跑流程重derive。)


# (CORE_SINGLE_CARD_REGISTRY 直通终局线单卡依赖型核心登记已随 C1
#  单卡核心囤积规则退役删除——统一让位优先级迭代 3.4,总纲 §2.5:
#  C1 直购支配性支/恒买腾位/买面保护消费全退役后该登记无生产消费面,
#  随批退役;登记值 = 知识判据出处指针,沿革与排除举证见 git 历史。)


# ===== COMP_LIBRARY(起步 roster;V4.4 估值,待实玩校准)=====
# (本注册表单一源。)faction_reqs 档 0 用 FACTIONS tier 设"成型"里程碑;data 待实玩精确。

# 家族键(9 键;plaza 统计分组命名空间——cw_plugins 过半统计/cw_system_cards
# 意向映射的键空间,绯英/银狼同归欢愉族为统计分组口径)。
# 旧 Comp.family 字段(v2 候选过滤链)已退役:该链消费函数早已零调用(死代码),
# 8 条 legacy 线实际一直正常参与选线——排除行为随 v2 候选机制消亡(git 可溯)。
V2_FAMILIES: tuple[str, ...] = (
    "万敌燃血", "希儿量子", "DOT卡芙卡", "姬子列车", "黄泉减益",
    "欢愉族", "圣杯双C", "大黑塔群攻", "白厄反甲",
)

COMP_LIBRARY: list[Comp] = [
    # ===== S 级(版本真神,V4.4 合集 76807134)=====
    # —— 姬子列车 A/B 拆分(统一阵容评分迭代批 3,design §5):拆分证据 =
    # 装备/副档分岔(外骨骼+以牙还牙甲族+护盾2 vs 风暴潮+电锯+冷笑话+减益2);
    # A/B 同 core 不同引擎结算方向(final_jizi §5 装备原理「同一引擎本体的
    # 两种伤害结算方向(助战技直伤 vs 受击反伤),切换件不改引擎」)——
    # core_chars/faction_reqs 档 0/need_star/key_items/站位 全共享,
    # equip_assign/档 1/key_equips 分岔。特化 15% 不拆挂(LINE_HEAT
    # 表注归属声明,版本重跑校准)。——
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/final_jizi_train.md(游戏知识,非字段镜像,无同步义务)
        name="列车同行·反震", core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        faction_reqs={0: {"列车同行": 4}, 1: {"护盾": 2}},   # 档1 加分层 = A 流护盾2(50% 盾循环必然)
        # V4.4 权威评级(76807134):姬子·启行 = S 级真神;A850 挂机流(76824096):全程自动/不凹开局/适应任何负面环境 → bot 默认首选
        # 成型 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝
        # (plaza 784 篇校准):carry 274/在场 358 篇断层级第一;flex_factions 全收(plaza 羁绊分布)。
        # A 流主体(底稿 A 反震姬子 ~60%):领航员绑三月七=全队 500% 反伤,受击结算。
        flex_factions=["护盾", "减益", "战技点", "量子同频", "盛会之星", "能量", "星间旅人"],
        plaza_carry="姬子·启行",
        # A 流铁三角(final_jizi A 节):三月七第一件=自适应外骨骼(刚需:前排
        # 减伤25%+受击概率大增=吸仇恨)+姬子以牙还牙甲×2-3(取 ×2 底稿口径;
        # 反甲×3 完全体留给实装校准)+三月七鞋(速度=盾循环)——反重力皮靴=
        # 通用速度件,不入 key_equips 分化面(A/B 均可穿,装备证据按分化件计);
        # 机制:反震吃「受击」,吸仇恨件互斥(攻略:「不要杰帕德,分受击概率」)。
        char_positions={"三月七": "back@5"},   # 站位:三月七后排中段(攻略 @4-6,星3「低血+相邻目标也获得护盾」→中段=相邻覆盖最大化,final_jizi_train 关键站位节;取中值@5)
        # 双列回声清理:三月七/花火/瓦尔特 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[], transition_chars=["符玄", "艾丝妲"],
        # ===== 姬子列车家族·A 反震 =====   # ②类信号:四人 100% 固定(A/B 共用)
        equip_assign={"姬子·启行": ["以牙还牙甲", "以牙还牙甲"], "三月七": ["自适应外骨骼"]},
        # ===== 知识卡字段(A/B 共享;数据源=final_comps/final_jizi_train.md)=====
        need_star={
            # 姬子 3★=「停留 7 级猛 D 3星姬子」(升星非线性回报,§1 第二环)+A4 姬子 74;
            # 三月七/花火 2★=攻略口径;瓦尔特辅助普适档 1★(A4)
            '姬子·启行': 3, '三月七': 2, '花火': 2, '瓦尔特': 1,
        },
        # 骨架=三月七(引擎触发器/贯穿件)+饮月(仙舟∩列车焊点,构造机理§2 贯穿件行)
        key_items=['三月七', '丹恒·饮月'],
        # 主羁绊=列车同行,成型档 4 → synergy 4
    ),
    Comp(
        name="列车同行·直伤", core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        faction_reqs={0: {"列车同行": 4}, 1: {"减益": 2}},   # 档1 加分层 = B 流减益2(58%)
        # B 流(底稿 B 输出姬子 ~25%):装备公式=火力风暴潮×2+高周波电锯
        # (B套=冷笑话/动能剑/特权件等变化);领航员三月(默认)/饮月(战技点
        # 复制动能剑)/星期日(直伤)——助战技直伤结算方向。
        flex_factions=["护盾", "减益", "战技点", "量子同频", "盛会之星", "能量", "星间旅人"],
        plaza_carry="姬子·启行",
        # B 流装备公式(final_jizi B 节 L42 明文「火力风暴潮×2+高周波电锯」;
        # B套=冷笑话/动能剑/特权件等变化——括号变体件无主,不入册):姬子风暴潮
        # ×2+电锯;三月七外骨骼归 A 铁三角不随 B。
        char_positions={"三月七": "back@5"},   # 站位:三月七后排中段(同 A;领航员载体共享)
        # 双列回声清理:三月七/花火/瓦尔特 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[], transition_chars=["符玄", "艾丝妲"],
        # ===== 姬子列车家族·B 直伤 =====
        equip_assign={"姬子·启行": ["火力风暴潮", "火力风暴潮", "高周波电锯"],
                      "花火": ["蓄能帆"]},
        # ↑ 到人出处:姬子行 = final_jizi B 节「装备:火力风暴潮×2+高周波电锯」;
        #   花火行 = 同篇构造机理装备字段统计(388 篇 Final)「蓄能帆(花火 40/瓦尔特
        #   152)——能量引擎,喂星期日/姬子终结技循环」。冷笑话引擎行删:L42 括号
        #   「B套=冷笑话/动能剑/特权件等变化」系无主变体件,原文无花火归属
        #   (直读到人门槛不满足)。
        # ===== 知识卡字段(A/B 共享;数据源=final_comps/final_jizi_train.md)=====
        need_star={
            '姬子·启行': 3, '三月七': 2, '花火': 2, '瓦尔特': 1,
        },
        key_items=['三月七', '丹恒·饮月'],
    ),
    Comp(
        name="命运圣杯红A", core_chars=["Archer", "远坂凛"],
        faction_reqs={0: {"命运圣杯": 3}},
        # V4.4 评级(76807134):Archer 95 = S 级真神;攻略(76924524):高倍率九五核心+远坂凛+圣杯→+150%攻击+战技点
        # ⚠️ core_chars 用图鉴规范名:"Archer" 非"红A"(OCR/char_id 匹配靠 cw_chars.CHARACTERS 注册表)
        # (plaza 62 篇):3星率 0.18(5费 carry 常驻 2 星);速升9级节奏为主
        # 交叉核对注(费用勘误):圣杯四人 = Archer 5费/Saber 3费/吉尔伽美什 2费/远坂凛 1费(注册表),
        # 旧注释「4 个 5 费成型难」错 —— 费用阶梯宽,成型难度主要在 Archer 本体。
        flex_factions=["战技点", "量子同频", "列车同行", "能量", "治疗", "盛会之星"],
        plaza_carry="Archer",
        # 双列回声清理:远坂凛 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["瓦尔特", "Saber"], transition_chars=["符玄", "知更鸟", "花火"],   # Saber = 替班者转成员(「Archer 不来 Saber 一直 C,不卖转副C」,替班叙事见 final_grail_dual)
        # ===== 圣杯双C家族 A Archer 战技点线(燃料线官方接力结构)=====   # ②类信号:2 档开任务=燃料线入口
        equip_assign={"Archer": ["火力风暴潮", "高周波电锯", "动能激发剑"],
                      "远坂凛": ["火力风暴潮", "动能激发剑"],
                      "Saber": ["碎星斩舰刀"]},   # Saber 键经 substitute_plan 容纳(替班者)
        # ↑ 到人出处 = final_grail_dual 装备节:「Archer 装备: 火力风暴潮(87)+高周波
        #   电锯(38)+动能激发剑(17)——战技点爆发流」(序=频次)、「远坂凛装备: 风暴潮
        #   +动能激发剑(攻略:『三件装备全做好才能切阵容』试用门槛)」;动能激发剑 =
        #   战技点燃料层本命件(回合开始+消耗各回 1 战技点);闪闪侧(反重力皮靴)在
        #   双王条目同步;榜样激励克高倍率单核
        # ===== 知识卡字段(数据源=final_comps/final_grail_dual.md)=====
        need_star={
            # Archer 2★=「红A必须得有二星」出手门槛(#68)+A4 Archer 71% 低饥渴线;
            # 远坂凛 1★=「1星即够」(构造机理§2 触发器行,1星占绝对多数)
            'Archer': 2, '远坂凛': 1,
        },
        # 骨架=远坂凛(触发器)+花火/刻律德菈(战技点线燃料生产端,构造机理§2)
        key_items=['远坂凛', '花火', '刻律德菈'],
    ),
    # ===== A 级(版本强势,V4.4 合集 76807134)=====
    Comp(
        name="千冶减益", core_chars=["千冶·刃", "瓦尔特", "卡芙卡", "缇宝", "符玄"],
        faction_reqs={0: {"减益": 4, "星核猎手": 2}},
        # plaza 聚类 千冶·刃 n=29(减益26/星核19/燃血13/量子13/列车12):减益通用板大族,此前无承接
        # (29 篇里最多 5 篇可被既有阵容覆盖,交叉核对注点名)。千冶·刃(2费) carry,瓦尔特 24/29+卡芙卡 16
        # +缇宝 15+符玄 14 常驻减益辅助群;皮靴 30 断层第一(carry 吃鞋)+风暴潮 14+螺旋桨 13;
        # 节奏 6级搜牌 12/29(2费 → 6级停)→7级 7 → 速升9 4(瓦尔特 5费);与黄泉减益(3费/7级)错位。
        # 成型羁绊队:减益4 档乘区为战力主体
        shared_chars=["黄泉", "花火", "不死途", "开拓者·记忆", "椒丘"],
        transition_chars=["椒丘", "风堇", "开拓者·记忆"],
        flex_factions=["燃血", "量子同频", "列车同行", "治疗", "持续伤害"],
        plaza_carry="千冶·刃",
        equip_assign={"千冶·刃": ["反重力皮靴"]},
        # ↑ 到人出处 = 本条 plaza 校准注(n=29):「皮靴 30 断层第一(carry 吃鞋)」→
        #   千冶·刃;风暴潮14/螺旋桨13/反卫星狙击枪9 系簇级聚合统计、无到人线索,
        #   单件级不入册(宁缺毋滥:假归属污染采购/穿戴决策的损失 > 装备证据面变小)。
        # ===== 知识卡字段(长尾线无 final_comps 专篇,数据源=本条 plaza 校准注 n=29)=====
        need_star={
            # 千冶·刃 3★=A4 高饥渴线 94%(饥饿表榜首);其余辅助普适档 1★(A4)
            '千冶·刃': 3, '瓦尔特': 1, '卡芙卡': 1, '缇宝': 1, '符玄': 1,
        },
        # 骨架=plaza n=29 常驻辅助群(瓦尔特 24/卡芙卡 16/缇宝 15/符玄 14,本条注)
        key_items=['瓦尔特', '卡芙卡', '缇宝', '符玄'],
    ),
    Comp(
        # 主羁绊(依据=final_feiying_joy.md 类结构三处一致:
        # 「欢愉4-7 + 星间旅人(25/25 双100%)……星间旅人2-3 + 仙舟3/能量3 挂件」)——能量降挂件
        # (进 flex),星间旅人升主羁绊(下限 2 档,成员=绯英本人在 core 即可达成)。
        name="绯英欢愉", core_chars=["绯英", "瓦尔特", "爻光", "开拓者·欢愉", "符玄"],
        faction_reqs={0: {"欢愉": 4, "星间旅人": 2}},
        # 欢愉下限 4 = 教义「欢愉 4-6 档(≤4 档即主流)」;档位谱真值 = FACTIONS.tiers
        # V4.4 评级(76807134):绯英 = A 级;攻略(76806732):绯英大招永久+2%伤害(无限成长),3欢愉+3能量+2量子+2减益
        # 前期狼尊开 3 欢愉过渡 → 上 8 踢狼尊换主角 → 上 9 找杨叔(瓦尔特)大成。爻光穿鞋频召阿哈叠层
        # 成型羁绊队:欢愉 4-6 档乘区
        # 双列回声清理:瓦尔特/爻光 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["火花"],
        char_positions={"爻光": "back", "绯英": "front@0"},   # 站位:爻光必后台(攻略反向论证:后台跑条给绯英多开大,总伤更高;前台倍率<20%残血版);绯英前排1号位(攻略 Final 标准式@0,25 帖归纳,2026-11-04 Common 全量审查登记)
        transition_chars=["花火"],   # 交叉核对注:爻光 25/25 常驻是 core 非 transition;常驻是火花(16/25,4费)非花火
        # ===== 欢愉族家族·绯英档(资源基准 6 级;无信号时的默认落点)=====   # ②类信号:绯英/银狼两档共用主体
        # content_id=7333;「欢愉 4-6 档」系连续区间误写);上限 5 = 4-5 主流带
        # (final_feiying「不到 7 也成型」,7 特权化属银狼档语义)。
        equip_assign={"绯英": ["火力风暴潮", "火力风暴潮", "永动机"],
                      "爻光": ["反重力皮靴", "反重力皮靴"]},
        # ↑ 到人出处 = final_feiying_joy 装备公式(25 篇统计)+构造机理§5 同口径:
        #   「绯英: 火力风暴潮×2(39 次)+永动机(20)——大招流双件」(攻略「只要保证
        #   绯英有两个火力风暴潮,输出不会低的」)、「爻光: 反重力皮靴×2-3(靴=阿哈
        #   时刻触发)」。爻光取区间下界 ×2(Final 标准式样本为靴×3 上端形态;姬子
        #   「以牙还牙甲×2-3 取×2 底稿口径」同构先例);藿藿(绝对热量)/符玄(分摊
        #   三件)公式行有到人,藿藿不在本套成员名单、符玄行未授权改动,均不入册。
        flex_factions=["能量", "仙舟", "治疗", "量子同频", "战技点"],   # 能量降挂件(final_feiying 挂件层),
        plaza_carry="绯英",
        # ===== 知识卡字段(数据源=final_comps/final_feiying_joy.md)=====
        need_star={
            # 绯英 3★=节奏基准「6级 D 三星绯英+爻光」(19/25 帖)+A4 高饥渴线 89%;
            # star_goals 2★=底稿降级语录口径(#12「两星即可稳定上分」)——交叉核对冲突
            # 以攻略重述为准取 3;爻光 2★=姊妹线明文(银狼篇 #7「开局追爻光2星」,
            # 共享引擎件);其余辅助普适档 1★
            '绯英': 3, '爻光': 2, '瓦尔特': 1, '开拓者·欢愉': 1, '符玄': 1,
        },
        # 骨架=定轨引擎爻光+能量环藿藿(18/25,插件排序首位,构造机理§2——
        # 绯英线比银狼线更依赖能量经济的差异件)
        key_items=['爻光', '藿藿'],
    ),
    Comp(
        name="希儿量子", # core(依据=final_seele_quantum.md「构造机理」
        # n=67 槽位构造):引擎核心组=希儿/花火/符玄/缇宝/刻律德菈;插件层=千冶·刃(掩体生成枪)/
        # 布洛妮娅/杰帕德/娜塔莎/佩拉(贝2 凑数+辅助);知更鸟/瓦尔特移出 core(P3 补位件,留 shared)。
        core_chars=["希儿", "花火", "符玄", "缇宝", "刻律德菈"],
        faction_reqs={
            # 档 0 = 终局完全体(纯 AND):类结构「量子4+贝4 双修」36/35 篇几乎
            # 不分离——量子同频=易伤乘区(四档,过半上 4 档 57/67)× 贝洛伯格=
            # 造物引擎拉条(伤害最多的贝成员立即行动 → 希儿拉条正循环),两层
            # 乘法即唯一主流终局形态(出处 = final_seele_quantum.md 构造机理,
            # n=67);贝取 4 =「2贝起步,至少 2 尽量追 4」的终局值,贝 2 过渡
            # 判据归过渡层组合条目承载,两层各自单一。
            0: {"量子同频": 4, "贝洛伯格": 4},
            # 档 1 = Final 标准式「量子4+贝4+战技点2-3+治疗2」的分层映射:
            # 战技点2/治疗2 实证 53/67 与 36/67(final_seele_quantum 构造
            # 机理),不到档 0 成型定义强度(对比量子/贝 96%+)。
            1: {"战技点": 2, "治疗": 2},
        },
        required_deployed=("希儿",),   # 成型判据第一合取支「希儿在场」,到手即开线
        # V4.4 评级(76807134):希儿 = A 级(A8-50 最强轮椅);攻略(76802749 直读纠正):4量子+贝城(2贝=原4贝,引擎拉条)
        # 斩杀+70%下二战技+再现+造物引擎。希儿(双电锯+风暴潮)+杨叔(瓦尔特)+记忆主+鸟(知更鸟)+刻律+鸭鸭(布洛妮娅)+符玄
        # 前期强势(希儿无装也能换怪/胜)→ 强烈推荐希儿过渡;7级找希儿3星或先上8/9找4-5费同时找希儿
        # 装备公式(final_seele_quantum §装备公式/§5,38 篇统计):希儿=风暴潮×2-3+电锯(唯一公式),
        # B 套=特权版风暴潮(plaza 实证 特权风暴潮三件);战场进化手册**不是本套件**
        # (是小黑塔星级装备,归大黑塔条目)。
        # boss×线克制单一源 = cw_affinity_table.BOSS_AFFINITY(希儿×蕉研组
        # 登记在彼;出处 = final_seele_quantum counter 节「蕉研组 boss」)
# 单属性队:量子同频4 属性型羁绊主档 ≥4(final_comps README D3「希儿怕量子熄火」,
        # plaza 希儿聚类 36/38 篇核心羁绊=量子同频)——量子熄火局对本套是主输出瘫痪级 counter。
        # 成型羁绊队:量子同频/贝洛伯格档位乘区。两者均为复活 tag(已永久滤除,见 ``_W878_RETIRED_TAGS``)。
# 知更鸟/瓦尔特= P3 补位件(n=67 非核心组);插件层五人(千冶·刃/布洛妮娅/
        # 杰帕德/娜塔莎/佩拉)为终局插件购买件,不入 core/shared
        shared_chars=["知更鸟", "布洛妮娅", "瓦尔特"],
        transition_chars=["刃"],
        # ===== 希儿量子家族(五线最收敛,无流派)=====
        equip_assign={"希儿": ["火力风暴潮", "高周波电锯", "火力风暴潮·特权"]},
        # ↑ 到人出处 = final_seele_quantum 装备公式「希儿: 火力风暴潮×2-3(64 次!)+
        #   高周波电锯(33)——几乎唯一公式」(风暴潮取下界×2 之一挂特权版,B 套=
        #   特权三件通道)+「B 套=战场手册/斩首/杀红眼(输出备选)或特权三件(攻略)」。
        #   特权件数保守裁定=×1:「特权三件」系整组替代形态(B 套换装,逐件枚举无
        #   原文,银狼篇结构类比而已),现登记=主公式上挂 1 特权槽;特权件产自特权
        #   阶级环境、获取面窄,证据面保守 1 件=fail-safe(少列→线分证据略保守,
        #   多列→囤货/合成面追不可得件)。布洛妮娅降插件层后无专属装备条目
        #   (n=67 插件层定位=贝成员/增益,装备优先级让渡引擎组)。
        # 弹性挂件 = 盛会之星/列车同行(实证 33/67 与 31/67,final_seele_quantum
        # 构造机理——频次低于档 1 两键,免 board_alignment 罚即可,不进加分层)
        flex_factions=["盛会之星", "列车同行"],
        plaza_carry="希儿",
        # ===== 知识卡字段(数据源=final_comps/final_seele_quantum.md)=====
        need_star={
            # 希儿 3★=「终局几乎必追三星」(构造机理§4:3星 62/67)+A4 希儿 81% 高饥渴线;
            # star_goals 2★=lv6-7 停留档口径——交叉核对冲突以攻略重述为准取 3;
            # 辅助普适档 1★(「辅助以 2星 为主」=自然来牌实况,非必要星级)
            '希儿': 3, '花火': 1, '符玄': 1, '缇宝': 1, '刻律德菈': 1,
        },
        # 骨架=引擎核心组非 carry 四件(构造机理§2:花火 63/符玄 62/缇宝 58/刻律德菈 53)
        key_items=['花火', '符玄', '缇宝', '刻律德菈'],
    ),
    Comp(
        name="黄泉减益", core_chars=["黄泉", "不死途", "乱破", "千冶·刃", "瓦尔特"],
        faction_reqs={0: {"减益": 4, "巡海游侠": 4}, 1: {"击破": 2}},   # 档0 键序:减益为主羁绊(原 bond_signal 语义,同值键序对齐);档1 加分层 = 击破 58% 升格候选
        # 巡海游侠档 = 教义「4」单点档(后排星级 1/3/6/12 倍放大)。
        # V4.4 评级(76807134):黄泉 = A 级;攻略(76826405):3游侠+4减益+3量子,2星乱破+3星不死途→280%增幅
        # (plaza 50 篇校准):常驻 千冶·刃48/瓦尔特45/不死途45/乱破38/椒丘32 —— core 的「刃」
        # 改「千冶·刃」(V4.4 实战常驻是千冶·刃,非本体刃);装备 top:电锯56/风暴潮28/光速螺旋桨26/永动机24。
        flex_factions=["击破", "治疗", "追击", "量子同频"],
        plaza_carry="黄泉",
        # 单体乏力不登 boss 行(「单体boss」是原型描述非公司名;boss 吃怕
        # 单一源 = cw_affinity_table.BOSS_AFFINITY,攻略无黄泉×具体公司名
        # boss 记载,版本重跑补登)。
# 攻略:单体 boss 黄泉输出乏力(无公司名指向,待实机核)
        # 双列回声清理:乱破 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["刃", "符玄", "卡芙卡"],   # 成型羁绊队:巡海4+减益4 档乘区;卡芙卡 = 替班者转成员(黄泉缺席时顶 C,不卖转副C;DOT 队核心亦常驻此线)
        transition_chars=["刃", "椒丘", "桑博"],
        # ===== 黄泉减益家族(无流派;第四件=装备池)=====   # ②类信号:4-6 档主体,到前 DOT 班底共享牌桌
        equip_assign={"黄泉": ["高周波电锯", EquipChoice("pool", ("永动机", "光速螺旋桨", "火力风暴潮"))],
                      "不死途": ["反重力皮靴", "反重力皮靴", "反重力皮靴"]},
        # ↑ 教义:黄泉=电锯(69% 近必选);第四件=池(永动机38/螺旋桨30/冷笑话26/风暴潮26 平缓分散)——
        # 池取频次前三,冷笑话并列 26% 待拆分放开。不死途行到人出处 = final_huangquan
        # 装备公式「不死途: 反重力皮靴×2-3(充能泵的速度件)」+攻略引文「必须要有
        # 三星不死途同时配上三双鞋」(靴×3 标配——引文明确件数,不取统计区间下界);
        # 机制 = 高速不死途=黄泉充能泵(饲饵标记喂充能,速度→行动次数→回能频率)。
        # ===== 知识卡字段(数据源=final_comps/final_huangquan_debuff.md)=====
        need_star={
            # 黄泉 3★=「7级 D 三星黄泉」节奏共识+A4 黄泉 87%;不死途 3★=「必须要有
            # 三星不死途」(#41;本线核心件 3★ 38%=A4 唯一例外档);乱破 2★=攻略
            # 「2星乱破+3星不死途」(76826405);star_goals 2★ 交叉核对冲突以攻略重述为准
            '黄泉': 3, '不死途': 3, '乱破': 2, '千冶·刃': 1, '瓦尔特': 1,
        },
        # 骨架=充能/生存/放大插件头名(构造机理§2:不死途>千冶·刃;椒丘隐形奶;瓦尔特 45/50)
        key_items=['不死途', '千冶·刃', '椒丘', '瓦尔特'],
    ),
    Comp(
        name="巡海击破", core_chars=["不死途", "波提欧", "乱破", "忘归人", "大丽花", "灵砂", "阮·梅"],
        faction_reqs={0: {"击破": 6, "巡海游侠": 4}},
        # ↺ 推翻「击破流萤」(plaza 784 篇):V4.4 击破代表已换代 —— 流萤任一阶段在场仅 29 篇
        # (carry 聚类 n=8,7/8 击破形)。**基准=波提欧簇**(12 篇,击破12/巡海12 全击破形;不死途簇 n=14 的
        # 主体是减益板[减益13/巡海12/击破11 混合],不当击破基准)。常驻 忘归人12/大丽花11/灵砂11/乱破11/阮·梅10。
        # 装备:波提欧=虫洞掘进钻头16/光速螺旋桨9,不死途=反重力皮靴。
        # 双列回声清理:忘归人 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["黄泉", "流萤"],   # 成型羁绊队:击破6 档乘区
        transition_chars=["赛飞儿", "灵砂", "忘归人"],
        flex_factions=["减益", "盛会之星"],
        plaza_carry="波提欧",
        equip_assign={"波提欧": ["虫洞掘进钻头", "光速螺旋桨"], "不死途": ["反重力皮靴"]},
        # ↑ 到人出处 = 本条 plaza 校准注(波提欧簇 n=12:「波提欧=虫洞掘进钻头16/
        #   光速螺旋桨9,不死途=反重力皮靴」;不死途簇 n=14 皮靴×24 互证);
        #   光速螺旋桨·特权×5 系簇级聚合、无到人线索,单件级不入册。
        # ===== 知识卡字段(长尾线无专篇,数据源=本条 plaza 校准注 n=12 波提欧簇)=====
        need_star={
            # 波提欧 2★=A4 低饥渴线 56%(≤2★ 过半;无攻略明文按饥饿表人为定为);
            # 不死途 2★=攻略口径;其余辅助普适档 1★
            '波提欧': 2, '不死途': 2, '乱破': 1, '忘归人': 1, '大丽花': 1, '灵砂': 1, '阮·梅': 1,
        },
        # 骨架=巡海后排结构:不死途(巡海引擎件+lv8 搜索目标,黄泉篇同构后排——
        # 本簇 n=12 常驻名单未列不死途,入册按结构非按簇统计)/乱破/忘归人/阮·梅
        # (簇内常驻 10-12/12);大丽花/灵砂(常驻 11)不入=巡海4 只需 4 名巡海成员、
        # 槽位弹性,常驻率相近的成员间不点名骨架(选择理由登记=交叉核对记录§四R4)
        key_items=['不死途', '乱破', '忘归人', '阮·梅'],
    ),
    Comp(
        name="龙丹战技点", core_chars=["丹恒·饮月", "远坂凛", "瓦尔特", "花火", "刻律德菈"],
        faction_reqs={0: {"战技点": 4, "列车同行": 4}},
        # V4.4 评级(76807134):丹恒·饮月(龙丹)= A 级;攻略(76987716 直读纠正):4战技点+4列车(周日开)
        # 凛(远坂凛)V4.4 新:宝石叠99层→第二魔法实验拐198%爆伤(+默认70%=268%);饮月双电锯+风暴潮
        # 杨叔(瓦尔特)+记忆主必备;4列车给160%前台强度;刃+符玄补。苍龙濯世破百亿
        # 成型羁绊队:战技点4+列车4 档乘区
        # 双列回声清理:远坂凛/瓦尔特/花火 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[], transition_chars=["花火", "风堇", "姬子·启行"],
        flex_factions=["量子同频", "盛会之星"],
        plaza_carry="丹恒·饮月",
        equip_assign={"丹恒·饮月": ["高周波电锯", "高周波电锯", "火力风暴潮"]},
        # ↑ 到人出处 = 攻略直读注 76987716「饮月双电锯+风暴潮」(final_longtail_others.md
        #   龙丹节装备 key 同文);构造机理 V4.4 复核「饮月电锯 10/10(首位)」,V3.8 史料
        #   「电锯无用、3 把暴击刀更优」标⚠️不采。动能激发剑(装备层供点引擎 8/10,套级
        #   统计)/斩首行动均无到人线索,单件级不入册。
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 龙丹节)=====
        need_star={
            # 饮月 2★=攻略口径(「6级停 roll 追 2星」;A4 无饮月
            # 条目,无明文不拍 3★);其余辅助普适档 1★
            '丹恒·饮月': 2, '远坂凛': 1, '瓦尔特': 1, '花火': 1, '刻律德菈': 1,
        },
        # 骨架=战技点燃料系统(远坂凛宝石/花火产点=龙丹节攻略原文细节补记〔史料级〕;
        # 瓦尔特必备=龙丹节正文;刻律复制=刻律星3 技能文本〔final_seele/final_wandi
        # 已登记〕——龙丹节通篇无刻律德菈,复制能力出处不在彼处)
        key_items=['远坂凛', '瓦尔特', '花火', '刻律德菈'],
    ),
    Comp(
        name="双王圣杯", core_chars=["吉尔伽美什", "Saber", "瓦尔特", "符玄", "开拓者·记忆", "藿藿"],
        faction_reqs={0: {"命运圣杯": 3, "能量": 5}},
        # V4.4 评级(76807134):双王 = A 级;攻略(76985789 直读纠正调研误认):双王=闪闪(吉尔伽美什)+Saber(Fate圣杯联动),
        # 非大黑塔+景元(游侠源误)。闪闪+Saber 每8行动连携+回能;圣杯羁绊给经济+改件加速3星。
        # Saber主c(风暴潮+冷笑话+永动机)/闪闪后台带鞋自加速;5能量;杨叔必备;刃+缇宝+符玄(阿瓦隆+绝对热量邪修75%减伤)
        # 过渡:体系牌+花火/凛(做3圣杯任务);7-8级找3星Saber或闪闪→上9挂杨叔
        # ↑ 教义:闪闪=**反重力皮靴**(41%,
        #   锁轴速度载体;final_grail_dual.md 圣杯A)
        # 双列回声清理:吉尔伽美什/Saber/瓦尔特/符玄 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[],   # 成型羁绊队:能量5 硬约束+圣杯任务链=档位乘区
        transition_chars=["花火", "刃"],   # 远坂凛是 core(1 星即够)
        # ===== 圣杯双C家族·B Saber 能量线(~25%)=====   # ②类信号:2 档开任务=燃料线入口
        equip_assign={"Saber": ["火力风暴潮", "永动机", "冷笑话引擎"], "吉尔伽美什": ["反重力皮靴"]},
        # ↑ 教义:Saber=充能件(永动机/冷笑话引擎/电光履,主C 满能自拉条伪永动)
        flex_factions=["列车同行", "战技点", "治疗", "盛会之星"],
        plaza_carry="Saber",
        # ===== 知识卡字段(数据源=final_comps/final_grail_dual.md)=====
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
    ),
    Comp(
        # V4.0 A级(BV1vVcLzXEN8 2026-02 转录):花火主C(吃点巧普攻+幻语记,倍率随花火等级)+星间旅人
        # 羁绊(唯一有效应=旅人转职,1转职章=43.2%幸运暴伤);6战技点不提升 → 带银狼/符玄凑3量子;
        # 前期龙丹战技点护航;上8大D找2星花火,3星质变;爻光三鞋(跑条供R回合)。
        # 怕正当防卫;极速制冷不怕(R时刻解控)。好运令牌给阿雅(装备最顶级)勿给花火/爻光。
        name="火花星间旅人", core_chars=["花火", "爻光", "开拓者·欢愉", "银狼LV.999"],
        # 名义 core 羁绊修正:core+flex 里星间成员=0(注册表口径:花火=盛会之星+战技点/量子同频,非星间;星间成员
        # =火花/桑博/瓦尔特/罗刹/银枝/绯英/真理医生)——星间4 从本套 roster 不可构造。
        # 可达成形态:欢愉3(core 爻光+开拓者·欢愉+银狼LV.999 全欢愉成员);星间旅人降 flex
        # (final_yinlang_joy 构造机理:星间 3-7 是欢愉队**顺手开出来的第二增益源**,非构造目标,
        # 62/68 Final 实证)。
        faction_reqs={0: {"欢愉": 3}},
        # 交叉核对注(火花簇 25 篇):旧 factions[星间+量子] 0/25 达标 —— 实战分布 欢愉22/战技点21/
        # 星间21 并列,量子仅 flex 位 → 核心改 星间+欢愉(花火=欢愉阵营);core 补 开拓者·欢愉(20/25 在场,
        # 欢愉形态保留不换记忆)与银狼LV.999(17/25)。
        # 成型羁绊队:欢愉档乘区(星间降 flex);教义为准重写:旧手编清单未到人
        # 且与「爻光三鞋」教义矛盾,以装备公式节到人行为准(详设 equip-projection §1)。
        shared_chars=["银狼", "符玄", "丹恒·饮月"], transition_chars=["丹恒·饮月", "银枝"],
        flex_factions=["星间旅人", "战技点", "列车同行", "量子同频", "星核猎手"],   # 星间=顺手增益源
        plaza_carry="火花",
        equip_assign={"花火": ["火力风暴潮"], "爻光": ["反重力皮靴", "反重力皮靴", "反重力皮靴"]},
        # ↑ 到人出处:花火=火力风暴潮×1(本条攻略注「花火 1 风暴潮」手判层);爻光=反重力
        #   皮靴×3 = final_yinlang_joy.md 装备公式「爻光: 反重力皮靴×3(速度=阿哈触发)」
        #   + 本条 BV 转录注「爻光三鞋(跑条供R回合)」双源。旧手编的电锯27/碎星斩舰刀5/
        #   动能激发剑4 系火花簇聚合统计、无到人线索,单件级不入册。
        # ===== 知识卡字段(数据源=本条 BV 转录注+plaza 火花簇 25 篇校准注)=====
        need_star={
            # 花火 3★=「上8大D找2星花火,3星质变/有机会追3必试」(攻略明文);
            # 其余辅助普适档 1★
            '花火': 3, '爻光': 1, '开拓者·欢愉': 1, '银狼LV.999': 1,
        },
        # 骨架=core 非花火三件(爻光引擎/开拓者·欢愉 20-25/银狼LV.999 17-25,簇校准注)
        key_items=['爻光', '开拓者·欢愉', '银狼LV.999'],
        # 银狼LV.999 = 升费链累积型但「不适用有空位就上例外」,按线 synergy 窗
    ),
    Comp(
        # 新增(plaza 大族群补缺):银河学者+群攻族 —— 大黑塔 carry 38 篇 + 小黑塔 carry 26 篇。
        # **augment 定义型阵容**:35 篇带「黑塔纪元」(棱彩,216 张黑塔入商店+追击转圈)—— 拿到即玩
        # (定义卡通道 +500,见 kernel/cw_invest_channels);无它时靠银河学者羁绊本身(星级总量成长)亦可成型,强度降档。
        # 黑塔纪元特型:备战席囤小黑塔(强度=小黑塔合计星级,「备战席放满越多越好」)—— bench 语义特例。
        name="大黑塔银河学者", core_chars=["大黑塔", "黑塔", "缇宝", "翡翠"],
        faction_reqs={0: {"银河学者": 4, "群攻": 3}},
        # plaza:大黑塔 3星率 0.82(4费);5级搜牌 20/38 篇(小黑塔 1费 5级 D 干);装备 电锯29/永动机20/蓄能帆17/电光履16
        # 记忆主必拿(「记忆主一定要拿,后台花火防战技点不足」);后期可上花火补战技点。
        # ↑ 战场进化手册=小黑塔星级装备(星级→强度),归本条(教义)。
        # 双列回声清理:黑塔/缇宝/翡翠 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[],   # 成型羁绊队:学者档=星级总量成长乘区
        transition_chars=["艾丝妲", "丹恒·腾荒"],   # 黑塔(小黑塔)是 core/替班C
        # ===== 大黑塔群攻家族(档位=连续深度谱,非流派)=====   # ②类信号:星级总量成长
        equip_assign={"大黑塔": ["高周波电锯", "永动机", "电光履", "蓄能帆"],
                      "黑塔": ["战场进化手册", "高周波电锯"]},
        # ↑ 到人出处 = final_daheita_aoe 三重到人:大黑塔装备公式「充能三件套:
        #   高周波电锯(24)+永动机(16)+电光履(14)+蓄能帆(13)——『保证开大效率』
        #   (攻略要点)」+Final 标准式「大黑塔×3C@0(永动机+电光履+蓄能帆)」+装备
        #   实证(电锯41/永动机20/电光履23/蓄能帆19)=大招流 C;小黑塔=「双电锯+
        #   星级手册(攻略要点:『小黑塔需要输出』)」+标准式「小黑塔×4(电锯+手册)」
        #   +实证(手册20/电锯15)——电锯取 1(双电锯系攻略要点上端形态,标准式/
        #   实证口径 1),战场进化手册=星级装备(星级→速度+伤害,自希儿量子归位)。
        #   大黑塔实证风暴潮 26 不在公式行,不入册。
        flex_factions=["量子同频", "列车同行", "公司", "减益"],
        plaza_carry="大黑塔",
        # ===== 知识卡字段(数据源=final_comps/final_daheita_aoe.md)=====
        need_star={
            # 大黑塔 3★=3星 39/52+A4 大黑塔 84%;黑塔 3★=「本类小黑塔也追 3星(与
            # 其他类辅助 2★ 通则相反)」(构造机理§2)+备战席星级=学者档强度源;
            # 缇宝/翡翠辅助普适档 1★
            '大黑塔': 3, '黑塔': 3, '缇宝': 1, '翡翠': 1,
        },
        # 骨架=黑塔(联动引擎件)+缇宝(46/52)/翡翠(31/52,学者4 档件)(构造机理§2)
        key_items=['黑塔', '缇宝', '翡翠'],
        # 小黑塔(黑塔)「备战席放满越多越好」的 bench 语义特例与窗口适用范围
        # 天然一致——银河学者档齐前囤不上
    ),
    Comp(
        name="银枝群攻", core_chars=["银枝", "翡翠", "知更鸟"],
        faction_reqs={0: {"群攻": 3}},
        # V4.4 评级(76807134):银枝 = B 级;攻略(77006068 直读纠正):V4.4 离能量,"轮椅通拐"(杨叔/主角/缇宝/花火/千冶刃+符玄)抬
        # 银枝(风暴潮+冷笑话)+翡翠(3群攻)+鸟(拉条加攻增伤+10%幸运);必须3星银枝;适合对群,对单大降
        # ⚠️ (注册表交叉核对):银枝=**星间旅人** 2费,非贝洛伯格(24 篇银枝帖贝洛伯格激活 0 次)
        # —— 核心只有群攻,星间旅人/公司/盛会之星(翡翠/知更鸟)是 flex。
        # 成型羁绊队:群攻档乘区+大招驱动的羁绊协同型
# (银枝×单体长战类非公司名,不登 boss 吃怕表——同黄泉条目处置,待实机核)
        # 双列回声清理:翡翠/知更鸟 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[],
        transition_chars=["椒丘", "星期日", "刃"],
        flex_factions=["星间旅人", "公司", "盛会之星", "列车同行"],
        plaza_carry="",   # 银枝 carry 聚类 n<5(24 篇在场,长尾)
        equip_assign={"银枝": ["火力风暴潮", "冷笑话引擎"]},
        # ↑ 到人出处 = 攻略直读注 77006068「银枝(风暴潮+冷笑话)」到人明文;绝对热量
        #   无归属线索(套级清单件),单件级不入册。
        # ===== 知识卡字段(数据源=本条攻略直读注 77006068)=====
        need_star={
            # 银枝 3★=攻略明文「必须3星银枝」(77006068;star_goals 2★ 交叉核对冲突
            # 以攻略重述为准);翡翠/知更鸟辅助普适档 1★
            '银枝': 3, '翡翠': 1, '知更鸟': 1,
        },
        # 骨架=翡翠(3群攻结构件)+知更鸟(拉条件,攻略句内明示)
        key_items=['翡翠', '知更鸟'],
    ),
    Comp(
        name="反甲白厄", core_chars=["白厄", "三月七", "姬子·启行"],
        faction_reqs={0: {}, 1: {"护盾": 2}},   # 档0 空=非羁绊成型(装备流例外);档1 = B 流护盾 2(多数停此)
        # 白厄无阵营(cw_chars:104 factions=""),独立羁绊「救世主」(获所有前台非独立羁绊效果)。
        # 反甲流靠白厄单核 + 以牙还牙甲×3 受击反伤,**不靠阵营羁绊成型** → factions/档 0 皆空。
        # 阵容靠 core_char(白厄)+ equip_fit(以牙还牙甲)+ mechanics(高频低单次 反伤);
        # form_progress 恒 0 → 不靠 form commit(轮数兜底要求 fp>0,fp=0 不触发),选靶候选但 progress 低。
        # meta:反甲流需 3 以牙还牙甲
        # boss 克制登记在 cw_affinity_table:史瓦罗(深穹智械科技)=重开级;
        # 「红绿灯」= 小怪非 boss(用户确认 2026-08-17),走非 boss 强敌段
        # (简报词缀行通道)重开级。
# 依赖合成装备:以牙还牙甲×3 反甲链+掩体生成枪=胜利条件本身(final_baie_reflect 明文
        # 「反甲装备流」);装备依赖词条(变宝为废)的选型侧降分载体(合成侧由 junk_first 处理,
        # 两半互补)。羁绊维判非成型羁绊队:factions/档 0 皆空,装备流例外。
        # 双列回声清理:白厄 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=[],
        transition_chars=["符玄"],   # 白厄 core/三月七 P2 直留终局
        # ===== 白厄反甲家族(A 巡海流 ~64% / B 列车护盾流 ~29%;A/B 未拆条)=====
        # ↑ 档 1 只收了 B 流 {护盾2};A 流前排法则=标签数量×星级优先,A 巡海流(~64%)
        #   核心副羁绊=「巡海 3+」——A/B 未拆下巡海 3 属 A 流、现仅在 flex_factions
        #   (板面不罚但完成度不数);A/B 拆分落位时档 1 补齐 {护盾2, 巡海游侠3}(分支依赖,同姬子家族口径)
        equip_assign={"白厄": ["以牙还牙甲", "以牙还牙甲·特权", "热血沸腾拳"], "三月七": ["胜利之旗", "很硬的甲"]},
        # ↑ 白厄行出处 = final_baie_reflect 装备体系「白厄 A 套: 以牙还牙甲×3
        #   (24+/38 篇标准式)」(现登记普通+特权两把,完全体×3 留 A/B 拆分校准)
        #   +热血沸腾拳(能量3 变体输出件);三月七行到人出处 = 同节「三月七:
        #   胜利之旗+很硬的甲(标准)/靴×2+光能盾牌(罗刹式)/掩体枪×3(攻略变体)」
        #   取标准式;完整反甲链(以牙还牙甲×3+掩体生成枪持续群盾,生存位=绝对热量)
        #   留 A/B 拆分
        # (plaza 校准):白厄 38 篇 carry 中 33 篇实际挂在列车同行(以牙还牙甲×93 断层第一,
        # 副三月七/姬子/星期日)—— 纯反甲白厄是小众硬流派;主流是列车护盾流的副 carry 位。
        flex_factions=["列车同行", "巡海游侠", "减益", "护盾"],
        plaza_carry="白厄",
        # ===== 知识卡字段(数据源=final_comps/final_baie_reflect.md)=====
        need_star={
            # 白厄 3★=主流追三星(3星 72/78)+A4 白厄 92%(「2星即可开线,3星是上限」
            # ——need_star 锁完成态);三月七/姬子辅助普适档 1★(姬子明文 1星 30/38 生效)
            '白厄': 3, '三月七': 1, '姬子·启行': 1,
        },
        # 骨架=三月七(护盾/反震插件 46/78)+姬子·启行(领航员工具 38/78)(构造机理§2)
        key_items=['三月七', '姬子·启行'],
        # 位面段;README C4「白厄 B 套特权反甲 = 满编后期的常态」——
        # 装备流战力随装备合成累积,前中期上 = 裸装白厄送战损)
    ),
    # ===== B 级(强度一般,V4.4 合集 76807134)=====
    Comp(
        name="狼尊欢愉", core_chars=["银狼LV.999", "爻光", "千冶·刃", "开拓者·欢愉", "火花", "绯英"],
        faction_reqs={0: {"欢愉": 5, "星核猎手": 2}},
        # V4.4 评级(76807134):狼尊 = B 级;攻略(76832783 直读):5欢愉(最大利用阿哈装备),狼尊双风暴潮+爻光双鞋
        # 刃(星核猎手):刃+狼尊行动7次→狼尊释放欢愉技。强依赖鞋≥6;尽量不d全力升级;也作绯英早期过渡c
        # 交叉核对注(狼尊簇 68 篇交叉核对):本体刃仅 2/68,千冶·刃 36/68 → core 刃改千冶·刃(V4.4 实战常驻)。
        # 成型羁绊队:欢愉 5-7 档乘区
        # 双列回声清理:爻光 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["花火"], transition_chars=["花火", "符玄"],
        # ===== 欢愉族家族·银狼档(资源基准 9 级;与绯英档互含单向:银狼局含绯英 76%)=====   # ②类信号:绯英/银狼两档共用主体
        # 星核 2=笑点泵(银狼每攻 7 次放 40 笑点欢愉技)——本套已列档 0(星核猎手2),不入档 1(不重复);绯英 76% 在场沉淀
        equip_assign={"银狼LV.999": ["火力风暴潮", "火力风暴潮", "高周波电锯"],
                      "爻光": ["反重力皮靴", "反重力皮靴"]},
        # ↑ 到人出处 = final_yinlang_joy 装备公式「银狼: 火力风暴潮×2-3(86 次!)+
        #   高周波电锯(58)」(区间取下界×2;电锯到人 58 次)+攻略 76832783 直读
        #   「狼尊双风暴潮+爻光双鞋」(爻光×2;公式统计口径靴×3 系上端形态)。
        #   银狼皮靴行删(「皮靴是速度载体」系条目注泛型推理,非直读到人);开拓者
        #   行删(光速螺旋桨无出处)。全队永动机群(阿哈装备栏全开后装备=输出)
        #   未入到人表。
        flex_factions=["星间旅人", "战技点", "列车同行"],
        plaza_carry="银狼LV.999",
        # 但由购买/D 驱动非上场时间,**不适用「有空位就上」部署例外**;仅作类型区分。
        # ===== 知识卡字段(数据源=final_comps/final_yinlang_joy.md)=====
        need_star={
            # 银狼LV.999 2★=A4 低饥渴线 48%(≤2★ 过半;强度轴在升费链 5 费完全体
            # 非星级);爻光 2★=「开局追爻光2星」(#7);其余辅助普适档 1★
            '银狼LV.999': 2, '爻光': 2, '千冶·刃': 1, '开拓者·欢愉': 1, '火花': 1, '绯英': 1,
        },
        # 骨架=铁三角非 carry(爻光 100% 阿哈引擎/绯英 84% 副C沉淀)+插件前二
        # (开拓者 65/68/火花 57/68,构造机理§2)
        key_items=['爻光', '绯英', '开拓者·欢愉', '火花'],
        # synergy 5;银狼LV.999 = cost_escalation 不适用早上例外(字段注)
    ),
    Comp(
        name="昼神阿雅", core_chars=["阿格莱雅", "风堇", "昔涟"],
        faction_reqs={0: {"昼之半神": 4}},
        # V4.4 评级(76807134):阿雅 = B 级(试用难玩;需反重力皮靴×2+速度投资,V3.8 最轮椅→V4.4 降 B)。
        # (plaza 8 篇 carry):装备 反重力皮靴×16 断层第一(「有鞋跟本输不了」);阿格莱雅 3星率
        # 0.88;实战板多为 昼神4+量子3/能量+治疗混搭(flex 已收)。强帖(「80连胜焚决」/「小伊卡」)
        # use 均 0 且依赖本体/遗器/充能绳(M11)→ **保持 B**(交叉核对注:升 A 依据不足,勿按万敌标准拔高)。
        # 成型羁绊队(边界套):昼之半神4 主档为战力底盘,速度件是执行载体非战力源(裁注)
        # 双列回声清理:风堇/昔涟 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["银狼"], transition_chars=["风堇", "艾丝妲", "阿格莱雅"],
        flex_factions=["能量", "列车同行", "量子同频", "治疗"],
        plaza_carry="阿格莱雅",
        equip_assign={"阿格莱雅": ["反重力皮靴", "反重力皮靴", "白昼·光速螺旋桨"]},
        # ↑ 到人出处:皮靴×2 = final_longtail_others.md 昼神节「阿格莱雅(1费)速度流核心
        #   角色;**需反重力皮靴×2**+速度投资」(本条 V4.4 评级注同文,plaza 8 篇 carry
        #   皮靴×16 断层第一互证);白昼·光速螺旋桨 = 同节 V3.7 史料成型阵容句「阿雅(双鞋
        #   +光速螺旋桨+昼神风扇)」到人,速度→强度机制链经 V4.4 构造机理采信(皮靴 41 件次
        #   +白昼·光速螺旋桨 10,n=21)。火力风暴潮(簇×2)无到人出处,单件级不入册。
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 昼神节)=====
        need_star={
            # 阿格莱雅 3★=3星率 0.88(本条 plaza 校准注);昔涟/银狼 3★=plaza 帖文
            # 「除阿格莱雅/昔涟/银狼外不必追任何三星」同句点名(银狼 = shared 终局
            # 成员+lv9 搜索目标,经「攻略明文星级成员」通道入册);风堇辅助普适档 1★
            '阿格莱雅': 3, '风堇': 1, '昔涟': 3, '银狼': 3,
        },
        # 骨架=昔涟(诗篇刷新商店经济引擎)+风堇(core 内非 carry)
        key_items=['昔涟', '风堇'],
    ),
    Comp(
        # 打法知识:docs/game/currency_war/research/final_comps/README.md 类索引(游戏知识,非字段镜像,无同步义务)
        char_positions={"知更鸟": "front"},   # 站位:知更鸟前台(追击攻略:鸟前台支撑中后期;砂金/灵砂/符玄等生存位也优先前台)
        name="追击飞霄", core_chars=["飞霄", "知更鸟", "那刻夏", "不死途"],
        faction_reqs={0: {"追击": 3}},
        # V4.4 合集(76807134)追击 B 级 = 飞霄-led(纯追击);攻略(76883466):飞霄天赋追击永久+6%增伤,≥3追击=300%倍率
        # 飞霄双风暴潮+鸟(3追击关键)+缇宝/不死途/刃;2星飞霄上9(3星锁血反降);追击转→5追击60%真伤
        # 交叉核对注(基准交叉核对):飞霄 carry 仅 3 篇(<5 不在聚类)→ plaza_carry 置空;plaza 追击族
        # 真代表 = **那刻夏**(「5追击4昼之半神 后台主c之光」6444 use:「没鞋也没追击转别上那刻夏,
        # 至少得有其1」,装备优先级原文全序列)→ 补 core;追击簇 flex 常见 公司/昼之半神/群攻。
        # 成型羁绊队:追击档乘区(≥3追击=300%倍率)
        # 双列回声清理:知更鸟/不死途/那刻夏 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["缇宝"], transition_chars=["赛飞儿", "风堇", "刃"],
        flex_factions=["公司", "群攻", "昼之半神"],
        plaza_carry="",   # 飞霄 carry 3 篇悬空;那刻夏(追击真代表,n=6 恰在聚类边缘)未单列阵容
        equip_assign={"飞霄": ["火力风暴潮", "火力风暴潮"],
                      "那刻夏": ["追击星徽", "白昼·光速螺旋桨", "反重力皮靴"],
                      "知更鸟": ["电磁弹射器", "电磁弹射器"]},
        # ↑ 到人出处:飞霄=风暴潮×2 = 攻略直读注 76883466「飞霄双风暴潮」到人明文;
        #   那刻夏全序列(原序即优先级)= 6444 use 帖(cw_plaza_posts 6a34280f)equips
        #   字段「那刻夏: 追击星徽→白昼·光速螺旋桨→反重力皮靴」,与簇注门槛句
        #   「没鞋也没追击转别上那刻夏,至少得有其1」互证;知更鸟=电磁弹射器×2 =
        #   同帖 equips 到人。永动机系 M7 方法论套级序句(「那刻夏全套>生存装>弹射器
        #   >永动机」)无到人线索(同帖永动机在昔涟=非本套成员),单件级不入册。
        # ===== 知识卡字段(数据源=本条攻略直读注 76883466+plaza 追击簇注)=====
        need_star={
            # 飞霄 2★=攻略明文「2星飞霄上9(3星锁血反降)」——3★ 有害线,封顶 2★;
            # 知更鸟/那刻夏/不死途辅助普适档 1★
            '飞霄': 2, '知更鸟': 1, '那刻夏': 1, '不死途': 1,
        },
        # 骨架=知更鸟(3追击关键)+那刻夏(plaza 追击族真代表,簇注)+不死途(攻略句内)
        key_items=['知更鸟', '那刻夏', '不死途'],
    ),
    Comp(
        name="万敌单C", core_chars=["万敌", "千冶·刃", "长夜月", "刻律德菈", "缇宝"],
        faction_reqs={0: {"夜之半神": 2, "燃血": 4}, 1: {"战技点": 2}},   # 档1 = 战技点 2(90%,第三引擎);风堇=第二记录器(治疗转伤害)
        # 燃血档 = 教义「4-6 档」(下限 4;档位谱真值 = FACTIONS.tiers)。
        #   ⚠️ 行为面:form_progress 成型判定按燃血 4 判(意图内)。
        # V4.4 评级(76807134):万敌 = B 级;【debuff=buff 典型】反伤/AoE/持续伤害 利燃血;攻略(77056698)
        # ↺ (plaza 40 篇校准)B→A:use 榜 #2(11.2w,「万敌无脑单挂A850 7人成型」);3星率 0.93
        # 场最高;5级搜牌 26/40(1费 carry 5 级 D 标准节奏)。**档 0 校准(交叉核对注)**:旧 夜4+燃4
        # 仅 15% 帖达标 —— 榜首帖实跑 夜2+燃2(「7人成型」= 万敌+6弹性辅助;另一帖明言「夜神燃血也不
        # 要凑」)→ 降为 2+2(核心=万敌双标签引擎,其余 flex);千冶·刃 40/40 全勤补 core(旧漏)。
        # 遐蝶(n=6)= 同族副 carry(夜神6+燃血6),挂 shared 备转型。

        char_positions={"万敌": "front@0"},   # 站位:万敌永远前排1号位(攻略硬约束,final_wandi_burn「万敌@0 独占前排」;燃血吃受击)
# 掉血削上限克燃血(不可玩);利:忍无可忍/正当防卫/灼热轰炸(debuff=buff)
        # 双列回声清理:长夜月 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["风堇", "遐蝶"], transition_chars=["椒丘", "艾丝妲"],   # 长夜月是 core(夜半记录)
        # ===== 万敌燃血家族(无流派;装备收敛:风暴潮 95%+热血拳 90%)=====   # ②类信号:夜半 2(96% 必配,主档)
        equip_assign={"万敌": ["火力风暴潮", "热血沸腾拳", "绝对热量", "高周波电锯"]},
        # ↑ 到人出处 = final_wandi_burn 装备公式(40 篇统计):A 套①三件 = 绝对热量
        #   (刚需第一,攻略「没有就别玩」)+火力风暴潮+热血沸腾拳,高周波电锯 =
        #   B 套备选输出(「B 套=电锯/杀红眼/手册/斩首(备选输出)」);登记序 =
        #   plaza 簇频次(风暴潮54/热血拳40/绝对热量26)非公式优先序(绝对热量
        #   第一),容量紧张帧取件先后按登记序。显式转移时序件 = 生命之环(奶瓶,
        #   攻略「前期给万敌自己,双奶瓶后换给别人」),不在本表。
        equip_taboos=["护盾件(类)", "以牙还牙甲", "掩体生成枪"],
        # ↑ 教义(官方原文):燃血队员无法获盾,受盾只转 2%+1000 回血=负资产;连带盾类装备全禁
        # 无替班:文档明言万敌 1 费开局即在(56% 局 P1 板上),无空窗;P2 加深档数
        flex_factions=["群攻", "量子同频", "战技点", "治疗", "命运圣杯", "减益"],
        plaza_carry="万敌",
        # 用户定案 [21] 例外)——环境满足(敌方多动/反伤类词条)时适用「有空位就上」。
        # ===== 知识卡字段(数据源=final_comps/final_wandi_burn.md)=====
        need_star={
            # 万敌 3★=3星率 0.93 全场最高+A4 万敌 90%;千冶·刃 2★=攻略
            # star_goals 攻略口径;长夜月/刻律德菈/缇宝辅助普适档 1★
            '万敌': 3, '千冶·刃': 2, '长夜月': 1, '刻律德菈': 1, '缇宝': 1,
        },
        # 骨架=千冶·刃(全勤通用插件)+刻律德菈(复制插件)+长夜月(夜半记录器,core 内)
        key_items=['千冶·刃', '刻律德菈', '长夜月'],
        # 羁绊有空位就上)→ always_on
    ),
    Comp(
        name="DOT队", core_chars=["卡芙卡", "黑天鹅", "千冶·刃", "海瑟音", "符玄"],
        faction_reqs={0: {"持续伤害": 4, "星核猎手": 2}, 1: {"减益": 2}},   # 档1 = 减益 2(43%);星核 2(57%)已在档 0(星核猎手2)
        # V4.4 评级(76807134):dot = B 级;攻略(77026641 直读):V4.4 刃加入→卡芙卡回归(刃比普通狼频繁触星核猎手额外战技)
        # 卡芙卡3风暴潮(dot不吃幸运)+黑天鹅(鹅,2dot)+刃(2星核猎手)+刻律(复制战技连动)+鸟;需自己卡芙卡
        # ⚠️ 黄泉减益已拆独立(见上);本阵容=DoT 主派(卡芙卡/鹅/刃/桑博),P1强/P2乏力/P3需转,低费过渡保血权威
        # (plaza 卡芙卡 11/黑天鹅 11 篇校准):常驻 千冶·刃11/黑天鹅10/符玄9/瓦尔特8/海瑟音7
        # (core 的「刃」改「千冶·刃」+补海瑟音);装备 风暴潮19/反重力皮靴8。
        # 慢速:DOT 叠层×引爆磨血胜利条件(final_dot_kafka),冻结族词条的慢热载体。
        # 成型羁绊队:持续伤害档一路加深(2→4→6)是本线成长乘区。

        # 双列回声清理:千冶·刃/黑天鹅 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["桑博"],
        transition_chars=["桑博", "艾丝妲"],
        # ===== DOT卡芙卡家族·A 引爆流(~47%;B 速度/昼半流未建条,拆分落位)=====   # ②类信号:开局即战力,前期=终局同体一路加深
        equip_assign={"卡芙卡": ["火力风暴潮", "火力风暴潮"],
                      "海瑟音": ["蓄能帆", "碎星斩舰刀"],
                      "黑天鹅": ["天基轨道炮", "天基轨道炮", "反重力皮靴"]},
        # ↑ 到人出处 = final_dot_kafka 装备公式(20 篇统计):「卡芙卡: 火力风暴潮
        #   ×3(主流!攻略:『风暴潮至少两把,蓄能帆优先度大于第二把』)」——取攻略
        #   引文下界×2(构造机理§5:主核心名下 3 件仅 6/34 帖,×3 系精选强帖表述);
        #   「海瑟音: 蓄能帆+碎星斩舰刀(追击/速度)」「黑天鹅: 天基轨道炮×2(后台)
        #   +反重力皮靴」。机制注脚:卡芙卡星3 携带装备直接提高引爆倍率=全游戏唯一
        #   装备焊进公式的角色;全队铺皮靴(§5 全队层皮靴 53>风暴潮 50,速度→行动
        #   次数→触发引爆,黑天鹅行已含 1 双)。
        flex_factions=["减益", "量子同频", "盛会之星", "昼之半神"],
        plaza_carry="卡芙卡",
        # ===== 知识卡字段(数据源=final_comps/final_dot_kafka.md)=====
        need_star={
            # 卡芙卡 2★=A4 低饥渴线 DOT 52%(≤2★ 过半;「2星上9」降级路径常在);
            # 黑天鹅/千冶·刃/海瑟音/符玄辅助普适档 1★
            '卡芙卡': 2, '黑天鹅': 1, '千冶·刃': 1, '海瑟音': 1, '符玄': 1,
        },
        # 骨架=黑天鹅(层数机器)/海瑟音(副输出)/千冶·刃(星核副产品+群盾)/符玄(生存)
        key_items=['黑天鹅', '海瑟音', '千冶·刃', '符玄'],
        # 一路加深」——DOT 件无「囤而不上」阶段(P1 即终局形态)→ 全员
        # always_on
    ),
    Comp(
        # 新增(plaza 补缺):景元仙舟族 —— 景元 carry 16 + 彦卿 14 篇。
        # **augment 强联动**:飞光·映月/传剑(各 8/5 篇,定义卡通道 +500)—— 彦卿+景元师徒,
        # 拿到飞光 = 1费特殊景元+镜流强化;升星次序经济:「先 3星景元,否则镜流 3星后景元变 5费难刷」。
        name="景元仙舟", core_chars=["景元", "镜流", "彦卿", "符玄"],
        faction_reqs={0: {"仙舟": 5}},
        # plaza:景元 3星率 0.69(5费);7级搜牌 7/16;装备 电锯13/风暴潮12/皮靴6;常驻 符玄13/爻光11/藿藿11
        # 神君:仙舟召唤物计数(12041/12042 变体 id 只计羁绊);成型羁绊队:仙舟5 召唤计数档乘区
        # 双列回声清理:符玄 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["忘归人", "藿藿"], transition_chars=["藿藿", "丹恒·饮月", "符玄"],
        flex_factions=["治疗", "减益", "量子同频", "列车同行", "燃血", "狼狩"],
        plaza_carry="景元",
        equip_assign={"景元": ["火力风暴潮", "高周波电锯"], "镜流": ["反重力皮靴"]},
        # ↑ 到人出处 = final_longtail_others.md 景元节构造机理装备行「景元 风暴潮 19=
        #   电锯 19>皮靴 12;镜流 皮靴 7(速度→神君叠段频率)」到人明文(n=24);
        #   电光履×4 系簇级聚合、无到人线索,单件级不入册。
        # ===== 知识卡字段(数据源=final_comps/final_longtail_others.md 景元节)=====
        need_star={
            # 景元/镜流 3★=「必须先 3星景元,再追镜流 3星」(升星次序经济,攻略明文)
            # +镜流全 12 帖皆 3★;彦卿/符玄辅助普适档 1★
            '景元': 3, '镜流': 3, '彦卿': 1, '符玄': 1,
        },
        # 骨架=镜流(双三星结构件)+彦卿(传剑搭档)+符玄(19/24 常驻)+藿藿
        # (仙舟三人组 P1→Final 原样保留,构造机理「加法不换件的最纯样本」)
        key_items=['镜流', '彦卿', '符玄', '藿藿'],
    ),
    Comp(
        # 新增(plaza 补缺):专家桑博 DOT —— 33.3k use 帖(「专家老桑博,越用越有活」5级搜牌)。
        # **env 定义型**:「开局必须刷专家邀请环境」(特邀专家:桑博;专家类目通用 0,所赠角色走证据分);
        # 无专家 env 时强度降档(退化为 DOT队 territory)。桑博本体贝洛伯格阵营(DoT 输出位)。
        # 节奏:1-6 搜桑博2星 → 2-3 前 3星桑博(装备越早越好)→ 存钱升8 搜海瑟音 → 瓦尔特必上。
        name="专家桑博DOT", core_chars=["桑博", "卡芙卡", "千冶·刃"],
        faction_reqs={0: {"持续伤害": 4, "贝洛伯格": 2}},
        # 慢速:DOT 磨血(桑博 DoT 越早越好,同 final_dot_kafka 磨血胜利条件)。
        # 成型羁绊队:持续伤害档乘区。

        # 双列回声清理:卡芙卡/千冶·刃 core 列在册;members 读口去重(core 位在前),全消费面输出不变
        shared_chars=["海瑟音"], transition_chars=["卡芙卡", "艾丝妲"],
        # ===== DOT卡芙卡家族·桑博专家变体(文档明言:策略入口变体,不独立成套)=====   # ②类信号:开局即战力,前期=终局同体一路加深
        equip_assign={"桑博": ["反重力皮靴", "反重力皮靴", "物质分解液"]},
        # ↑ 桑博行按 final_dot_kafka 教义登记:装备公式「桑博: 靴×2+物质分解液(速度
        #   引爆)」适用于专家版语境——桑博在该族文档的定位即专家版主核心(「低费引爆器
        #   (专家版主核心)」),该行本就是专家版装备行;构造机理装备实证(n=54)桑博=皮靴
        #   12+物质分解液 4,与公式行互证。速度引爆机制 = 桑博星3「风化满层后额外触发
        #   风化」,速度→行动次数→触发频率;「携带装备提高引爆倍率」的技能文本在卡芙卡
        #   星3(装备焊进引爆公式),桑博星3 无此缩放——族级「主核心=风暴潮」口径不移植
        #   到桑博。卡芙卡行已删:final_dot_kafka 全文无冷笑话引擎归属(公式卡芙卡行=
        #   风暴潮×3 主流/速度流变体=靴×2+贝星徽),无到人出处不入册(宁缺毋滥)。
        flex_factions=["星核猎手", "减益", "昼之半神"],
        plaza_carry="",   # 桑博 carry 聚类 n<5(33k use 单帖在,样本量不够成簇)
        # ===== 知识卡字段(数据源=final_comps/final_dot_kafka.md 桑博专家版节)=====
        need_star={
            # 桑博 3★=「1-6 搜桑博2星 → 2-3 前 3星桑博(装备越早越好)」(攻略明文);
            # 卡芙卡/千冶·刃辅助普适档 1★
            '桑博': 3, '卡芙卡': 1, '千冶·刃': 1,
        },
        # 骨架=卡芙卡(过渡共享引爆器)+千冶·刃(core 内非 carry)
        key_items=['卡芙卡', '千冶·刃'],
        # 同体」→ 全员 always_on
    ),
]

# 终局条目装备到人配方非空建库校验(import 期防线;键域校验在
# Comp.__post_init__ 逐实例)——判据见 _validate_comp_equip_assign docstring
_validate_comp_equip_assign(COMP_LIBRARY)


# ===== TRANSITION_LIBRARY(P1 过渡组合条目库;or-reqs-retirement 3.2)=====
# 用户裁定(2026-11-05):锁定域 = 组合条目——一个过渡阵容 = 两个过渡
# 羁绊构造块的完整组合(C(5,2)=10 条),组合条目 fp ≥ 1.0(两羁绊都凑齐
# ∧点名件全在板)才锁定;单羁绊构造块不是阵容、不进库、永不锁定(单
# 羁绊局保持软方向——候选继续活动、买面双向,直到组合凑齐或终局锁定
# 统一退役)。语义权威版本 = strategy-docs/12_line_and_intention.md §3
# (过渡阵容库与条目候选机器)。
#
# 组合实证(game/research/transition_combos.md 两两组合实证表,Early
# 647 帖):三过渡互组 3 种 + 希儿系×三过渡 3 种均有实证;含希儿组合的
# 实证粒度只到希儿系级(量/贝归属未分),按希儿系实证整体拆分全枚举
# C(5,2)=10;「没有希儿时量子/贝不能独立当过渡(28 帖全部含希儿)」
# ——量子/贝构造块必须点名希儿(混合型),不可做纯羁绊块。
#
# 旧 4 单体系条目(仙舟铁三角/廉价DOT/列车骨架/希儿引擎)随之退役;
# 旧条目名在 transition_locked/transition_candidates 槽与遥测
# sess_p1_pair 的历史数据经 transition_entry_of 返 None、
# transition_active_entries 跳过自然兼容,勿加兼容层。
# 三型知识(点名/羁绊/混合)收进构造块字段(named/hybrid),组合条目
# 恒为 combo 型(TRANSITION_ENTRY_KIND 表删除)。


@dataclass(frozen=True)
class TransitionBond:
    """过渡羁绊构造块:组合条目的生成原料;不是阵容、不进 TRANSITION_LIBRARY、不可锁定。"""
    name: str                        # 块短名(组合条目名与 parts 索引的组成部分)
    bond: str                        # 羁绊规范名(组合条目 faction_reqs 档 0 键)
    tier: int                        # 达标人数阈值(体系判据档 = FACTIONS[...].tiers[0] 口径)
    named: tuple[str, ...]           # 点名件(空 = 羁绊型:不限定人)
    need_star: tuple[tuple[str, int], ...]   # 点名件星级目标(键 ⊆ named;frozen 结构用 tuple 对)
    hybrid: bool                     # 羁绊半边是否计入持有分(点名型 False / 羁绊型与混合型 True)


#: 五块数值表(知识源 = 旧 3.3 条目表 + game/research/transition_combos.md
#: 四体系表;依据逐块就地标注)。tier 口径 = 体系卡判据档
#: (FACTIONS[...].tiers[0]:仙舟 3/持续伤害 2/列车同行 2/量子同频 2/
#: 贝洛伯格 2)。费段已核 CHARACTERS.cost(点名件 1-3 费,位面 1 可刷;
#: 校验⑤表达——费段解锁真值 = cw_shop_odds 的 REFRESH_PROB:等级 1-3
#: 仅 1 费/4 级起解锁 1-3 费/5 级起 4 费)。
TRANSITION_BONDS: tuple[TransitionBond, ...] = (
    TransitionBond(
        # 点名型:「仙舟3 = 三人组的同义词,95% 帖含全三人组」;凑数仙舟
        # 件非证据(hybrid=False → 羁绊半边不计持有分)。名单与星级就地
        # 复制自体系卡(cw_system_cards 的 xianzhou3 行,数据层保留)
        name='仙舟3', bond='仙舟', tier=3,
        named=('爻光', '藿藿', '丹恒·饮月'),
        need_star=(('爻光', 2), ('藿藿', 2), ('丹恒·饮月', 2)),
        hybrid=False,
    ),
    TransitionBond(
        # 羁绊型:无引擎、凑出就能用(用户 2026-11-04 裁定「DOT 不限定人」)
        name='DOT2', bond='持续伤害', tier=2,
        named=(), need_star=(), hybrid=True,
    ),
    TransitionBond(
        # 点名型:「线定义件引导(姬子·启行在场才值得朝列车走)」;
        # 任意列车成员非证据
        name='列车2', bond='列车同行', tier=2,
        named=('姬子·启行', '三月七'), need_star=(), hybrid=False,
    ),
    TransitionBond(
        # 混合型:「没有希儿时量子不能独立当过渡(28 帖全部含希儿)」;
        # 放大器经羁绊半边覆盖。星级取自体系卡 star_goal(seele 行希儿追 3★)
        name='希儿量2', bond='量子同频', tier=2,
        named=('希儿',), need_star=(('希儿', 3),), hybrid=True,
    ),
    TransitionBond(
        # 混合型:同上(贝洛伯格侧)
        name='希儿贝2', bond='贝洛伯格', tier=2,
        named=('希儿',), need_star=(('希儿', 3),), hybrid=True,
    ),
)

#: 组合条目名 → 两块名(transition_member_set 的 combo 展开单一源;
#: 由 ``_build_transition_combos`` 建库期填入,与 TRANSITION_LIBRARY
#: 同轮生成——一致性由 ``_validate_transition_combos`` ①钉死)
TRANSITION_COMBO_PARTS: dict[str, tuple[str, str]] = {}


def _build_transition_combos() -> list[Comp]:
    """建库期组合条目生成器:``TRANSITION_BONDS`` 两两组合 → C(n,2) 条 Comp。

    字段合并规则:core/required = 两块点名件保序去重(希儿双修两块点名
    合并为一人);档 0 = 两块键 AND(五块 bond 互斥,无键冲突——校验②);
    need_star = 两块星级目标合批;其余 Comp 字段缺省空(过渡语义 =
    低门槛快锁,过渡条目只填档 0;档位推进属「成型后的场况插件」,归
    部署/买牌机器状态驱动,不预枚举)。生成期显式填 required_deployed
    (点名件全部在板),旧建库自动填循环随之退役。
    """
    out: list[Comp] = []
    for a, b in itertools.combinations(TRANSITION_BONDS, 2):
        core = list(dict.fromkeys((*a.named, *b.named)))
        name = f'{a.name}+{b.name}'
        TRANSITION_COMBO_PARTS[name] = (a.name, b.name)
        out.append(Comp(
            name=name,
            core_chars=core,
            faction_reqs={0: {a.bond: a.tier, b.bond: b.tier}},
            required_deployed=tuple(core),
            need_star={n: s for blk in (a, b) for n, s in blk.need_star},
        ))
    return out


def _validate_transition_combos(bonds: tuple[TransitionBond, ...],
                                parts: dict[str, tuple[str, str]],
                                library: list[Comp]) -> None:
    """建库校验五条(or-reqs-retirement 3.2 设计 §4;非法 raise ValueError)。

    模块级对真值调用一次 = import 期防线(手改五块表或生成器破坏约定
    即炸);测试负面用例直接以非法构造调本函数断言 ValueError。校验面:
    ① 库长 = C(len(bonds),2) 且 parts 键集 = 条目名集;
    ② 五块 bond 互斥(两两组合无键冲突——生成器结构保证,校验防御手改);
    ③ named ∪ need_star 键 ∈ CHARACTERS 注册表;
    ④ need_star 键 ⊆ named;
    ⑤ 点名件费段位面 1 可刷(cost ≤ 3,费段真值对应关系:
       lv1-3 仅 1 费/lv4 起解锁 1-3 费/lv5 起 4 费——cw_shop_odds 的
       REFRESH_PROB;位面 1 等级覆盖区间 = cw_economy 位面-等级骨架)。
    """
    if len(library) != len(bonds) * (len(bonds) - 1) // 2:
        raise ValueError(
            f'过渡组合库长 {len(library)} != C({len(bonds)},2) = '
            f'{len(bonds) * (len(bonds) - 1) // 2}')
    if set(parts) != {e.name for e in library}:
        raise ValueError('TRANSITION_COMBO_PARTS 键集 != 条目名集')
    if len({b.bond for b in bonds}) != len(bonds):
        raise ValueError('五块 bond 键冲突(组合档 0 两键同名将互相覆盖)')
    for b in bonds:
        star_keys = {n for n, _s in b.need_star}
        if not star_keys <= set(b.named):
            raise ValueError(f'{b.name}: need_star 键 ⊄ named')
        for n in (*b.named, *star_keys):
            if n not in CHARACTERS:
                raise ValueError(f'{b.name}: 点名件 {n} 不在 CHARACTERS 注册表')
        for n in b.named:
            if CHARACTERS[n].cost > 3:
                raise ValueError(
                    f'{b.name}: 点名件 {n} 费段 {CHARACTERS[n].cost} > 3,'
                    f'位面 1 商店不可刷')


TRANSITION_LIBRARY: list[Comp] = _build_transition_combos()   # 恒 C(5,2)=10 条
_validate_transition_combos(TRANSITION_BONDS, TRANSITION_COMBO_PARTS,
                            TRANSITION_LIBRARY)


def transition_bond_of(name: str) -> TransitionBond | None:
    """块名 → ``TRANSITION_BONDS`` 构造块;未知名返 None(combo 展开的块解析口)。"""
    for b in TRANSITION_BONDS:
        if b.name == name:
            return b
    return None


def bond_score_members(block: TransitionBond) -> set[str]:
    """块的计分成员域:named ∪ (羁绊全体注册成员,若 hybrid 或无名件)。

    点名型(named 非空 ∧ 非 hybrid)= 羁绊半边不计(仙舟凑数件/任意列车
    成员不是证据);羁绊型(named 空)与混合型 = 羁绊半边计入。成员口径 =
    :func:`bond_members` 的阵营∪流派全集(过渡条目成员展开同式单一源)。
    """
    out: set[str] = set(block.named)
    if block.hybrid or not block.named:
        out |= bond_members(block.bond)
    return out


# ===== CARRY 基准派生(12 号篇 §1.1「plaza_carry ∪ core_chars 合流」)=====
# CARRY 档口径分两层:**合流全集** = ``carry_set``(单名基准 ∪ core_chars 全员,
# 3.7 持有证据 CARRY 档按「持有任一档内成员」判定)——「无单一直接字段,
# 派生申报」的完整实现;**单名基准** = plaza_carry(聚类注册表基准,层间交叉核对面),
# 3 条空值线(「空 = 无 n≥5 聚类对应」本身是聚类覆盖度信息)按攻略明文逐线
# 补全如下——不改 plaza_carry 字段值,覆写即破坏两层交叉核对基准语义:
CARRY_ANCHOR_FALLBACK: dict[str, str] = {
    # 银枝:攻略明文「必须3星银枝」(77006068 直读;银枝 carry 聚类 n<5 置空)
    '银枝群攻': '银枝',
    # 飞霄:V4.4 合集 76807134「追击 B 级 = 飞霄-led(纯追击)」+76883466 飞霄天赋
    # 追击主C;plaza 追击族真代表=那刻夏为簇注分歧,基准按攻略重述取飞霄
    '追击飞霄': '飞霄',
    # 桑博:33k use 帖「专家老桑博」低费引爆器主C(桑博 carry 聚类 n<5 置空)
    '专家桑博DOT': '桑博',
}


def carry_anchor(comp: Comp) -> str:
    """线 CARRY 单名基准(聚类交叉核对基准;CARRY 档全集见 ``carry_set``——本函数只供
    基准名消费面:聚类交叉核对/空值线补全/基准分歧登记;持有证据分档勿单用本名)。

    plaza_carry 非空 → 直接用(聚类交叉核对基准);空值线查 ``CARRY_ANCHOR_FALLBACK``
    (攻略明文补全,依据就地注释);两者皆缺 → ''(基准缺失申报态,消费侧按无基准处理)。
    ⚠️ 基准与攻略核心输出位存在个别分歧(火花星间旅人:plaza_carry='火花' vs
    攻略明文花火主C)——分歧登记在 知识卡建表交叉核对记录,基准字段保持聚类真值不覆写。
    """
    if comp.plaza_carry:
        return comp.plaza_carry
    return CARRY_ANCHOR_FALLBACK.get(comp.name, '')


def carry_set(comp: Comp) -> set[str]:
    """线 CARRY 档成员全集(持有证据分 CARRY 档口径;12 号篇 §1.1
    「plaza_carry ∪ core_chars 合流」的派生落地;3.7 消费)。

    = {``carry_anchor`` 单名基准} ∪ ``core_chars`` 全员——基准是聚类交叉核对基准(层间
    校准面),core_chars 是核心角色另册;合流后**任一成员在手都计入 CARRY 档**
    (大头档,与 key_items 骨架档/插件档三分,§1.2)。空值 3 线经 fallback
    补全后同样并入。core 至少 1 人 → 返回恒非空;消费侧禁自拼合流集(判据双源)。
    """
    anchor = carry_anchor(comp)
    return ({anchor} if anchor else set()) | set(comp.core_chars)


# (旧 char_lock_hit/strategy_lock_hit 锁定判定原语已随 lock_rules 字段整字段
#  退役删除〔统一阵容评分迭代,2026-11-03:全部即时锁退役,锁定 = P2 时点
#  兜底唯一路径〕——角色/策略到手的线关联由线分证据分量(carry_set)与
#  投资通道派生(kernel/cw_invest_channels)数值承载,沿革考古走 git 历史。)


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
    """已持有的角色名集合(bench + deployed;状态容器单位域现读)。"""
    front, back = deployed_rows_of(gs)
    return {u.char_id for u in (*front, *back, *bench_units_of(gs))
            if u is not None and u.char_id}


def form_progress(comp: Comp, gs: GameState) -> float:
    """成型度 0..1:档 0 各羁绊进度的均值 + required 逐名 0/1 折条的均值。

    comp_viability 先验用的 helper;纯阵营羁绊,不含角色(避免与 char_quality 三重计分)。
    入参 = 状态容器视图(决策面切统一状态容器;假想面板轻量桩只需提供
    ``board.value`` 属性,见调用点 _deploy_advances_form 鸭型位)。

    单一源契约:fp = 1.0 ⟺ 档 0 全键达标 ∧ required_deployed 全在板。
    档 1 不进(加分层归部署次层/采购面)。``required_deployed`` 逐名折
    一条 0/1 虚拟分支(在板=1;入参无 deployed 视图(轻量假想面板)
    按 0 计 = 保守向,缺读≠满成),并经 ``getattr`` 缺省空读(真实 Comp
    恒有字段;测试鸭型桩与旧序列化载体按「无 carry 条件」解释,与空
    字段同值,不炸)。
    档 0 空(非羁绊成型阵容,如反甲白厄)→ fp 恒 0(装备流走轮数兜底)。
    禁消费位绕过本函数自写 min(board,tier)≥tier 内联成型判定
    (判据双源;内联位清单与取代声明)。
    """
    core = comp.core_faction_reqs
    required = getattr(comp, 'required_deployed', None) or ()
    if not core and not required:
        return 0.0
    _board = getattr(gs, 'board', None)
    board = getattr(_board, 'value', None) or {}
    total = 0.0
    n = 0
    for f, tier in core.items():
        if tier <= 0:
            continue
        total += min(board.get(f, 0), tier) / tier
        n += 1
    if required:
        # 席位经状态容器视图读(无该属性 = 轻量假想面板,按 0 计保守向;
        # 行域合卷为 deployed 单字段,鸭型位同名)
        _view = getattr(getattr(gs, 'deployed', None), 'value', None)
        _front = getattr(_view, 'front_slots', None)
        _back = getattr(_view, 'back_slots', None)
        deployed_names = {
            u.char_id
            for u in (*(u for u in (_front or ()) if u is not None),
                      *(u for u in (_back or ()) if u is not None))
            if getattr(u, 'char_id', None)}
        for name in required:
            total += 1.0 if name in deployed_names else 0.0
            n += 1
    if n == 0:
        return 0.0
    return clamp(total / n, 0.0, 1.0)


# (shop_supply「本回合 shop 可得性」观察函数已删:全库零调用——drought
#  断供计数的现行载体是 cw_intention.shop_supply_streak(同名独立机制,
#  不经本函数);「弃不可达 target 重选」若立项按供给门重derive。)


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
    1. **carry 先拿**:``carry_anchor(comp)``(空值线经攻略明文 fallback 补全,
       同样有装备优先人;不在场上则 core_chars 中首个场上者)按序拿
       key_equips(multiplicity 消费,不超发);
    2. **其余场上 core** 拿剩余 key_equips(core 顺序);
    3. **剩余通用 owned** 按 deployed 顺序兜底(前排在前 —— 受击/反甲类在前排生效)。
    ``occupied[(row, slot)]`` = 已穿列表(容量扣减,EQUIP_CAPACITY);
    ``view`` = 上阵视图 :class:`DeployedView`(元素 = 状态容器 ``Unit``,
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
        # (carry_anchor 优先,再 core_chars 顺序);只发给场上且容量 >0 者。
        # key 件绑定裁决(18 号稿 §3.2):谓词层只重排候选序,
        # 不改 key 件绑定——key 接收者在优先层下仍限于 carry∪core
        # (非 core 凑谓词只走通用件吃满)。
        anchor = carry_anchor(comp)
        if priority_order:
            _core_pref = set(comp.core_chars) | (
                {anchor} if anchor else set())
            order: list[str] = [c for c in priority_order if c in _core_pref]
        else:
            order = []
            if anchor:
                order.append(anchor)
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
    '列车同行·反震': ('花火', '星期日'),   # 花火 core;姬子前台次之(A/B 同 core 同偏好)
    '列车同行·直伤': ('花火', '星期日'),   # 同 A(引擎结算方向不影响巨星乘区绑定)
    # 击破族
    '巡海击破': ('大丽花', '加拉赫', '知更鸟'),
    # 5费堆叠(DoT 队天然堆 5费黑天鹅/卡芙卡;黑天鹅 core 双保险)
    'DOT队': ('黑天鹅', '知更鸟'),
    '专家桑博DOT': ('黑天鹅', '知更鸟'),
}


def select_megastar(gs: GameState, target: Comp | None,
                    available_megastars: list[str]) -> str | None:
    """选 1 名盛会之星作巨星(盛会之星羁绊核心决策;按 target_comp 选,不单独评分)。

    选择序(按阵容引擎 × 巨星乘区,详 strategy/02_comp §7):
    1. target.core_chars 里的盛会之星(在阵 core 天然绑定,如追击飞霄×知更鸟);
    2. COMP_MEGASTAR_PREFERENCE[target.name](阵容级偏好序,21 套全覆盖);
    3. 首个可选(naive)。
    候选空 → None;无 target 且候选非空 → 返回首个可选(naive 兜底)。
    (旧第 3 序「机械属性兜底」读 mechanic_attributes——该字段已随评分器族
    删除,悬空消费即本批修复;MEGASTAR_BY_ATTRIBUTE 表随之退役,git 可溯。)
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
    return available_megastars[0]


# (select_megastar_enhance「强化角色」意向已停用——机制语义
#  本就是待证假设,证据链见原函数注释的 git 历史,勿复活。)

