"""sim 重做·节点事件面(M16 遭遇 / M17 晶矿·扑满·补给箱 / M18 补给)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M16/M17/M18,U22/U23/U24
第一期定稿口径:

- **M16 遭遇**:进入遭遇节点 → encounter_offer 相位,策略器经
  kernel ``decide_encounter`` 选档 → 按 M13 结算(所选难度加成进 M19
  难度账)。档位结构 = {1..N 档:难度加成 + 奖励包}(U22);遭遇等级
  加成四档 0/10/20/30 = ``research/economy.md`` §9 定谳真值;档位数/
  奖励包数值候实机数据(占位常量随局披露)。流键
  ``M16/offer/{plane}``(实机档位集随机性候实机数据,首版固定档位集);
- **M17 晶矿**:奖励节点走 M12 战斗框架,胜后进 reward_ore 相位
  逐晶矿入账(金/装备直接加,角色/箱落备战席占 1 槽;席满晶矿点不动)。
  面板结构以实测样本单例为唯一锚(U23:1 大金晶矿+5 蓝晶矿+2 灰晶矿);
  内容数值无档 → 显式占位常量 + 披露,禁拍值伪装实证。扑满替换 =
  经济过热/严重过热环境(容器 ``active_env`` × ``PIGGY_ENV_NAMES``
  单一源)把奖励节点替换为次元扑满——扑满不掉血(gameplay「节点
  类型×战力要求」节),M14 扣血豁免位。补给箱 4 选 1 装备、不可卖
  (入 M09 物品槽语义);箱内容池候实机数据(U24,占位 = 8 基础件);
- **M18 补给**:supply_pick 相位;3 选 1 装备 = 8 基础件池均匀采样
  (均匀为定稿占位口径,U24);免费刷新一次(实机两步 decide_supply
  语义:先刷新后选);带钻选项给宝钻(获取通道,M09;槽位分布占位
  均匀,披露)。自身金发放 = 基础奖励+息(U05,归 M04 收入面,不在
  本模块);不参与连胜(M15 收入分支承载)。

随机流键(引擎侧装配):``M16/offer/{plane}``、``M17/ores/{plane}/
{round}``、``M17/box/{plane}/{round}``、``M18/opts/{plane}/{round}``。

⚠️ 改名申报(2026-09-20 晶矿标识符 ore 治本收口):本模块 ball 族
(reward_ball_panel/apply_ball_pick/RewardOre/流键 M17/balls→M17/ores/
披露键 reward_ball_content_pending_u23→ore_content_pending_u23)随
「晶矿=球」旧名一并改为 ore——**流键改名使 M17 采样序列重排**,旧种子
复现的局自本点起不再逐位一致(sim 行为变化申报,非缺陷);披露键同步
新名,历史 sim 段披露面按旧键。 sim 内部旧名「ball」此后不再使用。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_synthesis import SYNTHESIS_BASES
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_free_slots,
    node_kind_of,
)
from sr_od.application.currency_war.kernel.cw_reward_node import (
    PIGGY_ENV_NAMES,
)
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence
from sr_od.application.currency_war.sim.cw_sim_phase import RewardOre

# ============================================================ M16 遭遇

#: 遭遇档位数(U22 占位:实机「其一/其二/其三/其四」四档旁证 + 加成表
#: 四档定谳,档位数值集候实机数据回填)。
ENCOUNTER_TIER_COUNT: int = 4

#: 遭遇等级加成四档真值(其一0/其二10/其三20/其四30;
#: research/economy.md §9 定谳——进 M19 难度账的唯一有档数值)。
ENCOUNTER_TIER_BONUS: tuple[int, ...] = (0, 10, 20, 30)

#: 遭遇奖励包金占位(U22:奖励包先按「金 + 概率装备」占位;数值候实机)。
ENCOUNTER_REWARD_GOLD_PLACEHOLDER: int = 20

#: 遭遇奖励包装备概率占位(U22+U24:首版 0 = 不发装备,发放引擎空表
#: 同构;候实机回填)。
ENCOUNTER_REWARD_EQUIP_CHANCE: float = 0.0

#: 遭遇占位参数披露键(U22)。
ENCOUNTER_PARAMS_PENDING_U22: str = 'encounter_tier_params_pending_u22'

#: 遭遇档位集固定披露键(实机档位集随机性候实机数据,首版固定集)。
ENCOUNTER_OFFER_FIXED: str = 'encounter_offer_fixed_set_pending_u22'


def encounter_options() -> tuple[EncounterOption, ...]:
    """遭遇档位集生成(M16;首版固定四档集,奖励包占位文本随披露)。

    ``EncounterOption.difficulty`` 坐标系 = kernel 档位序 1 基(1=易..
    4=难,与 ``decide_encounter`` 的 diff_norm 归一同域);idx = 档位集
    0 基下标(策略器 CwActionPickEventParam option_idx 消费)。实机档位含敌人词缀
    构成(战后才显,cw_screen_encounter 在案)不建模——词缀对战斗的
    数值影响随第一期随机输出面无消费(设计稿 M20)。
    """
    return tuple(
        EncounterOption(idx=i, difficulty=i + 1,
                        rewards=[f'金+{ENCOUNTER_REWARD_GOLD_PLACEHOLDER}'
                                 f'(占位,{ENCOUNTER_PARAMS_PENDING_U22})'])
        for i in range(ENCOUNTER_TIER_COUNT))


def apply_encounter_pick(gs: GameState, option_idx: int) -> tuple[int, str]:
    """遭遇选档入账(写容器 ``chosen_encounter``)。

    Returns:
        ``(难度档 1 基, 奖励文本)``——难度档供引擎把
        :data:`ENCOUNTER_TIER_BONUS` 对应加成进 M19 难度账。
    """
    options = encounter_options()
    opt = options[option_idx]
    reward_text = opt.rewards[0] if opt.rewards else ''
    gs.observe(gs.chosen_encounter, (opt.difficulty, reward_text),
               evidence=sim_evidence('encounter:pick'),
               sig=obs_sig(group_id='sim:encounter'))
    return opt.difficulty, reward_text


# ============================================================ M17 晶矿/扑满/箱

#: 晶矿面板单例锚(U23:实测 1-8 清关样本 1 大金晶矿+5 蓝晶矿+2 灰晶矿;颜色
#: 结构 = 唯一有据面,分布参数候实机数据)。
REWARD_ORE_PANEL_ANCHOR: tuple[tuple[str, int], ...] = (
    ('金', 1), ('蓝', 5), ('灰', 2),
)

#: 逐色档内容占位(U23 无档:金=金币 30/蓝=装备 1 件/灰=金币 5,显式
#: 占位常量禁作实机外推;披露键见 :data:`ORE_CONTENT_PENDING_U23`)。
REWARD_ORE_CONTENT_PLACEHOLDER: dict[str, tuple[str, int]] = {
    '金': ('gold', 30),
    '蓝': ('equip', 1),
    '灰': ('gold', 5),
}

#: 晶矿内容占位披露键(U23)。
ORE_CONTENT_PENDING_U23: str = 'ore_content_pending_u23'

#: 扑满节点战力要求语义披露键(扑满关有战力要求、不掉血;第一期随机
#: 输出面下战力维无消费,不掉血 = M14 豁免位由引擎承载)。
PIGGY_NO_HP_LOSS: str = 'piggy_node_no_hp_loss_u01_face'

#: 箱候选数(4 选 1,U23 画面语义)。
BOX_CANDIDATES: int = 4

#: 箱内容池占位披露键(U24 箱内容池候实机数据,占位 = 8 基础件均匀)。
BOX_POOL_PENDING_U24: str = 'box_pool_pending_u24'


def is_piggy_node(gs: GameState) -> bool:
    """当前奖励节点是否被扑满环境替换(单一源 = ``PIGGY_ENV_NAMES`` ×
    容器 ``active_env``;非奖励节点恒 False)。"""
    return (str(node_kind_of(gs) or '') == 'reward'
            and str(gs.active_env.value or '') in PIGGY_ENV_NAMES)


def reward_ore_panel() -> tuple[RewardOre, ...]:
    """晶矿面板(U23 单例锚展开;晶矿序 = 色档序内先大后小,点选按
    面板下标)。内容占位随局披露 :data:`ORE_CONTENT_PENDING_U23`。"""
    ores: list[RewardOre] = []
    for color, count in REWARD_ORE_PANEL_ANCHOR:
        kind, amount = REWARD_ORE_CONTENT_PLACEHOLDER[color]
        for _ in range(count):
            ores.append(RewardOre(
                color=color,
                content=(f'{kind}+{amount}' if kind == 'gold'
                         else f'{kind}x{amount}')))
    return tuple(ores)


def apply_ore_pick(gs: GameState, ball_index: int, *,
                    rng: random.Random) -> tuple[str, int]:
    """逐晶矿入账(采晶矿即时语义:金币直加金账,装备直入装备栏;角色/
    箱类内容落备战席占 1 槽——首版占位内容不含角色/箱,席满闸为
    占位内容扩展预留,渠道对齐 gameplay「奖励节点清关奖励」节)。

    Returns:
        ``(内容种别, 数量)``(引擎披露/轨迹消费;装备种别返回时已入账,
        装备名由引擎按 M10 发放通道披露)。
    """
    panel = reward_ore_panel()
    ball = panel[ball_index]
    color = ball.color
    kind, amount = REWARD_ORE_CONTENT_PLACEHOLDER.get(
        color, ('gold', 0))
    sig = obs_sig(group_id='sim:ball')
    if kind == 'gold':
        gold_after = int(gs.gold.value or 0) + amount
        gs.observe(gs.gold, gold_after, evidence=sim_evidence('ball:gold'),
                   sig=sig)
    elif kind == 'equip':
        equip = sorted(SYNTHESIS_BASES)[rng.randrange(len(SYNTHESIS_BASES))]
        gs.observe(gs.equips, list(gs.equips.value or []) + [equip],
                   evidence=sim_evidence('ball:equip'), sig=sig)
        return 'equip', 1
    return kind, amount


def box_options() -> tuple[str, ...]:
    """补给箱 4 选 1 装备候选(U24 箱内容池候实机数据,占位 = 8 基础件
    取前 4 定序——箱生成随机性候实机数据,首版固定候选集,披露
    :data:`BOX_POOL_PENDING_U24`;引擎流键 ``M17/box/{plane}/{round}``
    预留,占位集不消费随机)。"""
    return tuple(sorted(SYNTHESIS_BASES)[:BOX_CANDIDATES])


def apply_box_pick(gs: GameState, equip_name: str) -> None:
    """开箱入账:选中装备直入装备栏(箱不可卖 = M09 物品槽语义,装备
    一经入账即 owned;箱体本身不入备战席——开箱即腾席,cw_vocab
    CwActionOpenBoxParam 执行语义)。"""
    gs.observe(gs.equips, list(gs.equips.value or []) + [equip_name],
               evidence=sim_evidence('box:equip'),
               sig=obs_sig(group_id='sim:box'))


# ============================================================ M18 补给

#: 补给选项数(3 选 1,画面语义)。
SUPPLY_OPTION_COUNT: int = 3

#: 带钻槽位分布占位披露键(U24:实机补给屏随机一带钻选项,槽位分布
#: 无档 → 三槽均匀占位)。
SUPPLY_DIAMOND_SLOT_PENDING: str = 'supply_diamond_slot_pending_u24'


def supply_options(rng: random.Random) -> tuple[SupplyOption, ...]:
    """补给 3 选项采样(M18:8 基础件池均匀取 3 + 带钻槽均匀占位)。

    ``SupplyOption.char`` 恒空(补给 = 装备选;kernel 选项结构的角色
    维是实机读屏兼容面,补给无角色内容);``idx`` = 选项 0 基下标
    (CwActionPickEventParam option_idx 消费)。offer 内不重名(同屏 3 件互异装备,
    画面语义;不放回采样)。
    """
    pool = sorted(SYNTHESIS_BASES)
    equips = rng.sample(pool, min(SUPPLY_OPTION_COUNT, len(pool)))
    diamond_slot = rng.randrange(len(equips))
    return tuple(
        SupplyOption(idx=i, char='', equip=name,
                     has_diamond=(i == diamond_slot))
        for i, name in enumerate(equips))


def apply_supply_pick(gs: GameState, option: SupplyOption) -> bool:
    """补给选卡入账:装备入装备栏;带钻选项给宝钻。

    Returns:
        本选项是否带钻(引擎宝钻计数消费;宝钻 = sim 引擎自有状态,
        容器无承载字段,M09/U24 同款披露形态)。
    """
    if option.equip:
        gs.observe(gs.equips, list(gs.equips.value or []) + [option.equip],
                   evidence=sim_evidence('supply:equip'),
                   sig=obs_sig(group_id='sim:supply'))
    return option.has_diamond


def bench_has_space(gs: GameState) -> bool:
    """备战席是否有空槽(晶矿角色内容落席/箱落席的席满闸;pad 视图派生,
    None 视图 = 未写席,按有空槽处理——开局写端保证非 None,防御面)。"""
    view = gs.bench.value
    if view is None:
        return True
    return (bench_free_slots(gs) or 0) > 0


def place_bench_unit_placeholder(gs: GameState, char_id: str, faction: str,
                                 ) -> bool:
    """角色类奖励落备战席(占 1 槽;席满拒 = 晶矿点不动语义,先开箱腾席)。

    首版占位内容不含角色晶矿,本函数为 M17 内容扩展预留的统一落席口
    (渠道对齐 gameplay「备战席溢出」节:席满不丢,溢出悬挂由容器
    overflow 面承载,非本 sim 辖域)。容器 BenchView 槽序 ↔ 9 槽定长
    表转换后经 ``bench_place`` 找空位落件。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        BenchChar,
        bench_place,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_of_slots,
    )
    view = gs.bench.value
    if view is None or not bench_has_space(gs):
        return False
    ordered: list[BenchChar | None] = [None] * len(view.slots)
    for i, s in enumerate(view.slots):
        if s is not None and s.kind == 'unit' and s.unit is not None:
            u = s.unit
            ordered[i] = BenchChar(slot=i + 1, char_id=u.char_id,
                                   faction='', star=u.star)
    placed_at = bench_place(ordered, BenchChar(slot=0, char_id=char_id,
                                               faction=faction, star=1))
    if placed_at is None:
        return False
    gs.observe(gs.bench, bench_view_of_slots(ordered),
               evidence=sim_evidence('ball:bench'),
               sig=obs_sig(group_id='sim:ball'))
    return True
