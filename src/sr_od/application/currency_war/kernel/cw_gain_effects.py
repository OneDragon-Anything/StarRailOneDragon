"""货币战争 获得效果面(cw_gain_effects):策略卡「获得时效果」的注册表 +
效果函数体 + 骇客改件采样池。

拆分归属(获得链模块拆文件批,详设 = docs/develop/sr_od/application/
currency_war/changes/2026-09-21-invest-landing-chain/details/
gain-chain-file-split.md):本模块 = **效果内容**(表 + 采样池 + 效果体),
过程语义(链原语/合成/回调枚举)住 ``cw_gain_chain.py``。import 方向 =
链模块模块级 import 本模块的 ``PICK_INVEST_EFFECTS``(查表);本模块的
效果体**函数内惰性** import 链原语(运行时解析破环——两模块任一加载序
都无初始化死锁;惰性纪律先例 = cw_effect_inventory 函数内 import)。

自 ``kernel/cw_action_report/pick_invest.py`` 迁入(策略屏迁移批):表键、
采样池成员、效果语义逐位保留;效果体由「grant_bench_unit_cascade + 内联
后果表查」改走链原语 ``gain_character``/``gain_equipment``(回调先、升星
后;改件后果经 ``on_equipment_gained`` 回调自动消费)。
"""
from __future__ import annotations

import random
from collections.abc import Callable

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _emit_defect,
)

_PRODUCER = 'CwGainChain'

# ===== 骇客改件采样(随机腿;collect_ore 范式:采样器常量面 + 披露键 +
# ===== rng 注入,实机缺省未播种 = 采样是猜测,sim 传流键 = 采样即世界真值)

#: 骇客改件 v0 池(卡文「获得1个随机4费骇客改件」的建模口径,用户拍定
#: = 4 费装备排除 Max 件)。**池数据缺口申报(对抗审⑧)**:
#: Equipment dataclass 无 cost 字段(实证),「4 费」口径无数据源 → 池 =
#: 硬编码名单常量,显式申报的第二真相源(名单即口径本体,披露键在册)。
#: 成员 = 银狼专属 10 件(data/cw_equipment_wear_rules_data.ITEM_WEAR_GATES
#: 键集)中名字不带 Max 后缀的 5 件。**已知张力 + 用户裁定(2026-09-21:
#: 随便随机即可,接受现有名单,不排校准)**:run_074040 实读改件 =
#: 分身墨镜Max(属 Max 件),v0 池会猜错 → ``logic_rand_outcome`` 行收口
#: 兜底(不响安灯);池非类别池(「骇客改件」卡文口径 ≠ 注册表「骇客」
#: 类别),实机反例仅作口径张力留证,无后续动作。
HACKER_MOD_POOL_V0: tuple[str, ...] = (
    '分身墨镜', '数据拷贝仪', '数据拷贝仪Pro', '病毒防火墙', '破解芯片',
)

#: 建模假设档披露键(在册落点 = 本常量,随局披露面消费;校准只改池常量
#: 与披露键、不动结构)。
HACKER_MOD_ASSUMPTION_KEYS: tuple[str, ...] = (
    'hacker_mod_pool_v0_cost4_no_max',
)

#: 骇客改件链翻来源域集(对抗审⑪:按「可能受影响域」裁,禁照抄 collect_ore
#: 全域——gold 不受改件影响不翻,防噪声行)。
_HACKER_MARK_DOMAINS: tuple[str, ...] = ('equips', 'bench', 'front_row',
                                         'back_row')


def roll_hacker_mod(rng: random.Random) -> str:
    """单次骇客改件身份采样(纯函数;rng 注入,sim/live 共用同一语义)。
    池 = :data:`HACKER_MOD_POOL_V0`(等概率均匀;分布形态未实测,披露键
    ``hacker_mod_pool_v0_cost4_no_max``)。"""
    return rng.choice(HACKER_MOD_POOL_V0)


# ===== 效果函数(策略卡获得时分派 = 容器写腿;键 = 注册表规范名)=====
# 注册纪律:效果函数只辖「获得该卡后的容器写腿」(bench/装备/采样链),
# 与 cw_investments.STRATEGY_EFFECTS(持卡经济效果聚合,aggregate_economy
# 消费)职责不同不合并(对抗审⑨)。全量收录 = 推广批(gain-chain design
# §1.4),未收录卡只走注册或零效果(查无效果安静不写)。

#: 骇客专家:银狼 bench 腿的送出单位(卡文「获得专家顾问【银狼】」;
#: 星级未标 = 1★ 同句式先验,确定面语义——先验错 = 响停修因非随机)。
_HACKER_BENCH_GRANT: tuple[str, int] = ('银狼', 1)


def _apply_effect_hacker_wolf(gs: GameState, *, sig: ChannelSig,
                              rng: random.Random) -> list[str]:
    """效果函数·骇客专家:银狼(策略卡参考实现;自 pick_invest.py 迁入,
    改走链原语——策略屏迁移批,正本 = game_state/gain-chain.md §2/§3)。

    链序(逐步各落一行):
    1. **bench 腿**(确定性):银狼 1★ 经 ``gain_character`` 入席(落位 →
       回调 → 单级升星判断 → 产物递归,链式固定时序);
    2. **商店池腿**(零容器写):银狼加入本局商店池——商店池无容器字段
       (逐帧观察为真值),遥测行申报;
    3. **随机改件腿**(采样链):采样改件身份 → ``gain_equipment(rand=True)``
       入栏(采样效果对子链翻转 rand,gain-chain §5)→ 后果送单位由
       ``on_equipment_gained`` 回调自动消费(内联查表删除)。

    值不变翻来源域集(标记循环)的实现 = **调用前后值快照比对**(对抗审
    A3 定死):效果体执行中实际被写过的域(含回调子链,值快照变化)不再
    翻来源;未写域(gold 不在域集,对抗审⑪)值不变 ``write_logic_rand``
    翻来源留证。与现行 written 集语义等价(标记「暴露给随机事件但本次
    未写」的域;差一面 = 现行对银狼腿已写 bench 域的多余翻来源行被省略
    ——provenance 行级,容器值零差)。
    """
    # 惰性 import 链原语(运行时解析破环;模块 docstring import 方向声明)
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        gain_character,
        gain_equipment,
    )
    steps: list[str] = []
    r = gain_character(gs, _HACKER_BENCH_GRANT[0], _HACKER_BENCH_GRANT[1],
                       rand=False, sig=sig,
                       evidence='pick_invest_hacker_bench',
                       producer=_PRODUCER)
    steps.append(f'bench_grant:{_HACKER_BENCH_GRANT[0]}'
                 f'(placed={r.placed},merge={r.merge_levels})')
    _emit_defect(field_name='shop_pool', expected=None,
                 actual=f'{_HACKER_BENCH_GRANT[0]} 入商店池',
                 evidence='pick_invest_hacker_shop_pool', sig=sig,
                 kind='pick_invest_shop_pool_decl')
    steps.append('shop_pool_decl(零容器写)')
    # 随机改件腿(采样链;rand=True 采样子链)。前后值快照 = 标记域判定输入
    #(repr 签名:写端恒构造新值对象,值变签名必变)。
    mod = roll_hacker_mod(rng)
    pre = {dom: repr(getattr(gs, dom).value) for dom in _HACKER_MARK_DOMAINS}
    eq = gain_equipment(gs, mod, rand=True, sig=sig,
                        evidence='pick_invest_hacker_mod',
                        producer=_PRODUCER)
    if eq.placed:
        steps.append(f'mod_equip:{mod}')
    else:
        steps.append(f'mod_sampled:{mod}(equips 未观察,入栏跳写)')
    if eq.effects:
        # 后果送单位经 on_equipment_gained 回调入席(链内递归)
        steps.append(f'mod_consequence:{mod}')
    # 标记循环:本次未写域值不变翻来源(未观察域跳写,宁缺勿造)。
    # ⚠️ Field 现取禁缓存:写 = 帧替换(setattr 换新 Field 实例,cw_game_state
    # ._swap),写前捕获的 Field 引用过了首次写即失效(_field_name 身份守卫炸)。
    for dom in _HACKER_MARK_DOMAINS:
        fld = getattr(gs, dom)
        if fld.value is None:
            continue
        if repr(fld.value) != pre[dom]:
            continue   # 本次效果体(含回调子链)已写,不再翻来源
        gs.write_logic_rand(fld, fld.value, produced_by=_PRODUCER,
                            evidence=f'pick_invest_hacker_mark_{dom}',
                            sig=sig)
        steps.append(f'mark:{dom}')
    return steps


PICK_INVEST_EFFECTS: dict[str, Callable[..., list[str]]] = {
    '骇客专家:银狼': _apply_effect_hacker_wolf,
}
"""策略卡获得效果注册表(键 = 注册表规范名;自 pick_invest.py 迁入,
现役单行)。未收录名 = 零效果分派(查无效果安静不写,真值归观察覆盖)。
与 STRATEGY_EFFECTS(经济聚合面)职责分离声明见各表模块头。"""
