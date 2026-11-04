"""晶矿掉落奖励采样器(logic-rand-sampling 迭代;纯函数离线可测,sim/live 共用)。

**临时建模口径 v0**(design §0 裁决 2/§0.1:用户 2026-09-20 临时人为定为,
**非核实游戏事实,待实机采集数据优化**):点开晶矿 = 金币/装备/角色 三选一。
规则参数全部集中本模块常量面(各带披露键),采集校准只改常量与披露键、
不动结构;校准数据源 = 随机态观察收尾的 ``logic_rand_outcome`` 行(采样值
vs 实读真值逐局积累)。

已登记冲突调和(design §0 裁决 2):screen_flow_timing #16 三形态佐证本口径;
fields.md §4.2 的「箱」与 final_wandi_burn 的「稀有物」为 v0 有意不建模
——采样错形态时观察收尾兜底(安全的不准确),代价由席满让路门 + 观察
回补既有裁定承担。

采样语义(design §2.1):实机上采样是猜测(标随机态,观察校准);sim 里
采样即状态副本真值——同一采样函数两副面孔。

矿批附着生成(详设
details/ore-reward-channel.md §3)::func:`generate_ore_rewards` = 矿进入
世界时的附着奖励单一生成入口(声明金先占席、归属 rng 掷、其余逐矿采样),
live/sim 共用,禁第二实现。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from sr_od.application.currency_war.data.cw_chars import chars_by_cost
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
from sr_od.application.currency_war.data.cw_shop_odds import REFRESH_PROB

# ===== 规则参数常量面(采集校准唯一改点;各带披露键,与 design §0.1 一一对应) ==-

#: 类型权重(临时口径:三选一等概率,权重未实测;披露键 ore_type_uniform)
REWARD_TYPE_WEIGHTS: dict[str, float] = {'gold': 1.0, 'equip': 1.0, 'char': 1.0}

#: 金币掉落区间(临时口径:1..5;分布形态未实测按均匀;披露键 ore_gold_uniform_1_5)
GOLD_DROP_MIN: int = 1
GOLD_DROP_MAX: int = 5

#: 掉落角色星级(临时口径:恒 1★;直出高星无记载,同 sim 发牌 U12 口径;
#: 披露键 ore_char_star1)
CHAR_DROP_STAR: int = 1

#: 简易装备池(category='简易' 全集,字母序确定性;池口径随装备注册表传导)
_SIMPLE_EQUIP_POOL: tuple[str, ...] = tuple(sorted(
    name for name, eq in EQUIPMENTS.items() if eq.category == '简易'))

#: 建模假设档披露键汇总(design §0.1;已登记落点 = 本常量,随局披露面消费)
ORE_ASSUMPTION_KEYS: tuple[str, ...] = (
    'ore_type_uniform',
    'ore_gold_uniform_1_5',
    'ore_char_star1',
    'ore_no_rotation_tier',
)


@dataclass(frozen=True)
class OreReward:
    """一次晶矿掉落采样结果。kind ∈ ``gold``/``equip``/``char``;
    载荷按 kind 取对应字段(gold 金额 / equip 件名 / char_id 规范名 +
    char_star 星级口径)。"""

    kind: str
    gold: int = 0
    equip: str = ''
    char_id: str = ''
    char_star: int = 1


def roll_ore_reward(rng: random.Random, level: int) -> OreReward:
    """单点晶矿掉落采样(纯函数;rng 注入,sim/live 共用同一采样语义)。

    - level = 当前玩家等级(经济域观察值;报告层守卫保证非 None)。
      概率表覆盖 Lv1-10,表外档(注册表/状态不一致)显式炸——响亮暴露,
      禁静默兜底档(采样错档 = 校准数据全废)。
    - 多点批 = 每点独立调用一次,同一 rng 实例顺序推进(design §2.3:
      批内序列不重置,跨批经流键 uses 坐标隔离)。
    """
    if level not in REFRESH_PROB:
        raise ValueError(
            f'晶矿采样等级 {level!r} 不在概率表档 {sorted(REFRESH_PROB)}'
            '(临时口径 v0:基线 REFRESH_PROB[level],不挂轮岗翻倍档,'
            '披露键 ore_no_rotation_tier)')
    kinds = list(REWARD_TYPE_WEIGHTS)
    kind = rng.choices(kinds,
                       weights=[REWARD_TYPE_WEIGHTS[k] for k in kinds],
                       k=1)[0]
    if kind == 'gold':
        return OreReward(kind='gold',
                         gold=rng.randint(GOLD_DROP_MIN, GOLD_DROP_MAX))
    if kind == 'equip':
        return OreReward(kind='equip', equip=rng.choice(_SIMPLE_EQUIP_POOL))
    probs = REFRESH_PROB[level]
    costs = list(probs)
    cost = rng.choices(costs, weights=[probs[c] for c in costs], k=1)[0]
    return OreReward(kind='char',
                     char_id=rng.choice(chars_by_cost(cost)).name,
                     char_star=CHAR_DROP_STAR)


def generate_ore_rewards(
        declared_gold: tuple[int, ...],
        coords: tuple[tuple[int, int], ...],
        level: int,
        rng: random.Random) -> dict[str, OreReward]:
    """矿批附着奖励生成(纯函数;rng 注入,live/sim 共用单一入口,禁第二实现)。

    矿进入世界时点的内容分配(详设
    details/ore-reward-channel.md §3):待兑现声明金**逐个先占一席**
    (``rng.choice`` 剩余坐标不放回——归属不可观察,用户裁定 2026-10-10,
    占哪个矿必须掷随机),其余坐标逐个 :func:`roll_ore_reward` 采样
    (临时口径 v0 原状,披露键 ``ORE_ASSUMPTION_KEYS``)。

    - ``declared_gold`` 长度 ≤ ``len(coords)``(构造方 = 挂接入口
      ``report_spheres_observed`` 保证,按生成集大小截断出队;违者
      ValueError——静默丢声明 = 声明金蒸发);
    - ``coords`` 须无重复坐标(输入域由 Hough ``minDist=35`` + 两帧持存
      排除;重复坐标坍缩同键会静默丢矿,构造方不自检);
    - ``level`` 不在 ``REFRESH_PROB`` → 沿 ``roll_ore_reward`` 显式
      ValueError(口径错档禁静默兜底,先例同函数);全部坐标被声明占满时
      无采样发生,level 不参与判定;
    - 返回键 = ``'x,y'`` 字符串(与状态容器 ``ore_rewards`` 键制同格);
    - 掷序契约:声明占位在先、逐矿采样在后(同 rng 实例顺序推进,
      sim 侧流键确定性依赖此序,改序 = 掷序漂移)。
    """
    if len(declared_gold) > len(coords):
        raise ValueError(
            f'声明金条数 {len(declared_gold)} 超矿批坐标数 {len(coords)}'
            '(构造方须保证 declared_gold ≤ coords;静默丢声明 = 声明金蒸发)')
    remaining: list[tuple[int, int]] = list(coords)
    out: dict[str, OreReward] = {}
    for gold in declared_gold:
        xy = rng.choice(remaining)
        remaining.remove(xy)
        out[f'{int(xy[0])},{int(xy[1])}'] = OreReward(kind='gold',
                                                      gold=int(gold))
    for xy in remaining:
        out[f'{int(xy[0])},{int(xy[1])}'] = roll_ore_reward(rng, level)
    return out
