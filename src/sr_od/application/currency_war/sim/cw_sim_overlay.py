"""sim 重做·事件 overlay 族(M22,统一队列 + 三元组框架)。

设计正本 = ``docs/develop/sr_od/application/currency_war/sim/sim-design.md``
(§4 overlay 事实触发层)现役口径:

- 事件弹窗族(巨星强化/伙伴/专家邀请函/Fate 试炼/阿哈/骇入策划/
  「我来当策划」)**纳入建模范围**,不做「不自发触发」的搁置处置;
- 建模形态 = 统一 overlay 事件队列 + 每 overlay
  ``{触发条件, 选项生成, 效果应用}`` 三元组(结构纪律借用
  ``kernel/cw_overlay_registry.py`` 的「单一声明 + 派生消费」;该文件
  本体 = 实机画面 overlay 交互注册表,不迁入 sim);
- 有档照档(Fate 按 ``research/invest_effects.md`` §0.1 补记;画面档
  在案者照画面档);**无档的触发条件/选项生成/效果数值以显式占位
  常量落地并随局结果披露** ``overlay_param_pending`` 清单,候实机
  补档回填,不猜;
- 已由 M21/M02 显式建模的骇入/变宝为废照旧(骇入 = planner 族变体;
  变宝为废属 M10 合成污染位,非 overlay)。

第一期各 overlay 的档面盘点(占位常量的依据声明):
- megastar/partner/expert:触发时机与选项池在机制文档零载 → 触发占位
  (默认不自发触发,经队列显式入队驱动)+ 选项占位(注册表角色池
  均匀);效果应用占位(选中角色落备战席按 M17 落席口;其余披露);
- fate:2F-5F 各一次二选一接取 = §0.1 攻略补记单源(唯一有档触发
  结构);激活门槛/奖励数值无档 → 占位披露;
- aha/hack/planner:选项类型 kernel 在册(Megastar/Partner/Planner
  Option);planner 二选一 = gameplay「角色升星」节有档(银狼首次升
  2 星触发,M21 挂钩)——触发由 sim 后端判据链承载(overlay-trigger
  3.5 起为容器值回调),非自发采样。

随机流键(后端侧装配):逐 overlay 独立子键 ``M22/{name}/...``。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

# (旧队列 kind 词表已随 overlay-trigger 3.5 队列退役删除——呈现态
#  在册名单一源 = kernel/cw_overlay_register 的九 kind 词表[partner/
#  megastar/planner/wish_trial/fortune/star_tome/box_card/expert_invite/
#  aha];sim 修正清单的正名[fate→wish_trial/expert→expert_invite/
#  hack→planner]随旧词表消亡即终态,fortune 由登记词表补齐。)

#: 占位参数统一披露键(随局结果消费;逐 overlay 细项入清单值)。
OVERLAY_PARAM_PENDING: str = 'overlay_param_pending'

#: 逐 overlay 占位面清单(显式声明,不猜项逐一登记;候实机补档回填)。
OVERLAY_PENDING_ITEMS: tuple[str, ...] = (
    'megastar_trigger',
    'megastar_option_pool',
    'megastar_effect',
    'partner_trigger',
    'partner_option_pool',
    'partner_effect',
    'expert_trigger',
    'expert_option_pool',
    'fate_gate_and_rewards',
    'aha_trigger',
    'aha_effect',
    'hack_trigger',
    'hack_effect',
)

#: 选项生成占位池大小(expert 五选一 = 画面档语义;megastar/partner
#: 三选一占位)。
EXPERT_OPTION_COUNT: int = 5
TRIPLE_OPTION_COUNT: int = 3


# (统一 overlay 事件队列已随 overlay-trigger 3.5 退役删除:sim 呈现
#  数据源 = 容器登记 gs.screen_changes.pending[kernel/cw_overlay_
#  register],判据 = 容器值回调[cw_faction_callbacks]。)


def pending_disclosure_items(kind: str) -> tuple[str, ...]:
    """该 overlay 的占位面清单项(后端披露面消费;按族前缀过滤)。"""
    return tuple(item for item in OVERLAY_PENDING_ITEMS
                 if item.split('_', 1)[0] == kind)


def sample_options(rng: random.Random, kind: str,
                   roster: tuple[str, ...]) -> tuple[str, ...]:
    """overlay 选项生成占位(注册表角色池均匀;选项数按族:expert 五选
    一画面档语义,其余三选一占位)。同屏不重名(不放回采样)。"""
    count = EXPERT_OPTION_COUNT if kind == 'expert' else TRIPLE_OPTION_COUNT
    pool = sorted(set(roster))
    if not pool:
        return ()
    return tuple(rng.sample(pool, min(count, len(pool))))


def apply_expert_pick(gs: GameState, char_id: str, faction: str, *,
                      place_unit) -> bool:
    """专家邀请函选卡效果(画面档语义:五选一得该角色,落备战席占
    1 槽;席满拒)。落席通道 = 调用方注入的 M17 落席口(注入理由:
    落席与席满闸单一实现,禁第二份;默认不注入 = 零副作用契约)。

    Returns:
        落席是否成功(False = 席满拒,晶矿/卡点不动语义)。
    """
    ok = bool(place_unit(char_id, faction))
    if ok:
        gs.observe(gs.chosen_expert, char_id,
                   evidence=sim_evidence('overlay:expert'),
                   sig=obs_sig(group_id='sim:overlay'))
    return ok


def apply_disclosed_pick(gs: GameState, kind: str, option: str) -> None:
    """占位效果应用(效果数值零载族:选中值写容器 chosen_* 对应位
    (在册位才写)+ 披露面消费;无战力消费面,数值候实机补档)。

    在册 chosen 位映射:megastar→chosen_megastar / partner→
    chosen_partner / planner→chosen_hack(骇入策划位;正名 =
    register-consume「sim 修正清单」:旧 kind 名 hack 与 planner 同物,
    现役 kind 词表 = kernel/cw_overlay_register);wish_trial/fortune/
    aha 无独立 chosen 位,只披露(防容器词表外写入)。
    """
    field_map = {'megastar': gs.chosen_megastar, 'partner': gs.chosen_partner,
                 'planner': gs.chosen_hack}
    sig = obs_sig(group_id='sim:overlay')
    field = field_map.get(kind)
    if field is not None:
        gs.observe(field, option, evidence=sim_evidence(f'overlay:{kind}'),
                   sig=sig)
