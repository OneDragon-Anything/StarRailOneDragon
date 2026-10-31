"""货币战争 获得效果面(cw_gain_effects):策略卡「获得时效果」的注册表 +
效果函数体 + 骇客改件采样池。

拆分归属:本模块 = **效果内容**(表 + 采样池 + 效果体),
过程语义(链原语/合成/回调枚举)住 ``cw_gain_chain.py``。import 方向 =
链模块模块级 import 本模块的 ``PICK_INVEST_EFFECTS``(查表);本模块的
效果体**函数内惰性** import 链原语(运行时解析破环——两模块任一加载序
都无初始化死锁;惰性纪律先例 = cw_effect_inventory 函数内 import)。

表键、
采样池成员、效果语义逐位保留;效果体由「grant_bench_unit_cascade + 内联
后果表查」改走链原语 ``gain_character``/``gain_equipment``(回调先、升星
后;改件后果经 ``on_equipment_gained`` 回调自动消费)。
"""
from __future__ import annotations

import random
from collections.abc import Callable

from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _emit_defect,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_DELAYED_GRANTS,
    STRATEGY_DELAYED_OFFERS,
    RandomCharSpec,
    random_char_pool,
)

_PRODUCER = 'CwGainChain'

# ===== 骇客改件采样(随机分支;collect_ore 范式:采样器常量面 + 披露键 +
# ===== rng 注入,实机缺省未播种 = 采样是猜测,sim 传流键 = 采样即世界真值)

#: 骇客改件 v0 池(卡文「获得1个随机4费骇客改件」的建模口径,用户拍定
#: = 4 费装备排除 Max 件)。**池数据缺口申报(对抗审查⑧)**:
#: Equipment dataclass 无 cost 字段(实证),「4 费」口径无数据源 → 池 =
#: 硬编码名单常量,显式申报的第二真相源(名单即口径本体,披露键已登记)。
#: 成员 = 银狼专属 10 件(data/cw_equipment_wear_rules_data.ITEM_WEAR_GATES
#: 键集)中名字不带 Max 后缀的 5 件。**已知张力 + 用户裁定(2026-09-21:
#: 随便随机即可,接受现有名单,不排校准)**:run_074040 实读改件 =
#: 分身墨镜Max(属 Max 件),v0 池会猜错 → ``logic_rand_outcome`` 行收束
#: 兜底(不响失配告警);池非类别池(「骇客改件」卡文口径 ≠ 注册表「骇客」
#: 类别),实机反例仅作口径张力留存证据,无后续动作。
HACKER_MOD_POOL_V0: tuple[str, ...] = (
    '分身墨镜', '数据拷贝仪', '数据拷贝仪Pro', '病毒防火墙', '破解芯片',
)

#: 建模假设档披露键(已登记落点 = 本常量,随局披露面消费;校准只改池常量
#: 与披露键、不动结构)。
HACKER_MOD_ASSUMPTION_KEYS: tuple[str, ...] = (
    'hacker_mod_pool_v0_cost4_no_max',
)

#: 骇客改件链翻来源域集(对抗审查⑪:按「可能受影响域」裁,禁照抄 collect_ore
#: 全域——gold 不受改件影响不翻,防噪声行;行域合卷
#: 为 deployed 单字段)。
_HACKER_MARK_DOMAINS: tuple[str, ...] = ('equips', 'bench', 'deployed')


def roll_hacker_mod(rng: random.Random) -> str:
    """单次骇客改件身份采样(纯函数;rng 注入,sim/live 共用同一语义)。
    池 = :data:`HACKER_MOD_POOL_V0`(等概率均匀;分布形态未实测,披露键
    ``hacker_mod_pool_v0_cost4_no_max``)。"""
    return rng.choice(HACKER_MOD_POOL_V0)


# ===== 效果函数(策略卡获得时分派 = 容器写分支;键 = 注册表规范名)=====
# 注册纪律:效果函数只覆盖「获得该卡后的容器写分支」(bench/装备/采样链),
# 与 cw_investments.STRATEGY_EFFECTS(持卡经济效果聚合,aggregate_economy
# 消费)职责不同不合并(对抗审查⑨)。全量收录 = 推广批(gain-chain design
# §1.4),未收录卡只走注册或零效果(查无效果安静不写)。


def _apply_effect_hacker_wolf(gs: GameState, *, sig: ChannelSig,
                              rng: random.Random) -> list[str]:
    """效果函数·骇客专家:银狼(策略卡,改走链原语,
    正本 = game_state/gain-chain.md §2/§3)。

    链序(逐步各落一行):
    1. **商店池分支**(权威状态):银狼解锁入池——官方卡文「获得专家顾问
       【银狼】,并使其在本局游戏中加入商店」= 入池可刷,非直接送单位;
       容器权威字段 = ``gs.unlocked_experts``,写入端 = 获得链 advisor 道
       (:func:`cw_gain_chain.on_strategy_gained`,本效果体注册于其效果体
       分支之后,解锁先于本函数执行),本函数零写该分支;
    2. **随机改件分支**(采样链):采样改件身份 → ``gain_equipment(rand=True)``
       入栏(采样效果对子链翻转 rand,gain-chain §5)→ 后果送单位由
       ``on_equipment_gained`` 回调自动消费(内联查表删除)。

    值不变翻来源域集(标记循环)的实现 = **调用前后值快照比对**(对抗审查
    A3 定死):效果体执行中实际被写过的域(含回调子链,值快照变化)不再
    翻来源;未写域(gold 不在域集,对抗审查⑪)值不变 ``write_logic_rand``
    翻来源留存证据。与现行 written 集语义等价(标记「暴露给随机事件但本次
    未写」的域)。
    """
    # 惰性 import 链原语(运行时解析破环;模块 docstring import 方向声明)
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        gain_equipment,
    )
    steps: list[str] = ['shop_pool_unlock:银狼(advisor 道权威写,零本体重写)']
    # 随机改件分支(采样链;rand=True 采样子链)。前后值快照 = 标记域判定输入
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


# ===== 开箱分支效果(策略卡获得时点占席道具发放;进阶武装箱首例,迭代
# ===== 2026-09-24-advanced-armory-box design §2.3)=====

#: 开箱分支卡发放名单单一源(卡规范名 → 发放道具名;登记面镜像 =
#: cw_investments.STRATEGY_GRANTS 五卡 items_immediate,一致性测试逐对
#: 相等——attack.md A4 阻断修订:禁效果体闭包常量与登记表两处独立字面量,
#: 名字漂移在备战断言不可见[BenchSlot kind 与道具名解耦],唯本测试 +
#: 席满溢出落位真值可暴露)。注册表条目由下方工厂从本表生成,禁另写字面量。
_STRATEGY_BOX_GRANTS: dict[str, str] = {
    '战术义眼++': '进阶武装箱',
    '保守派': '进阶武装箱',
    '快请专家·彩': '进阶武装箱',
    '军火贸易': '简易武装箱',
    '军火贸易+': '简易武装箱',
}


def _make_box_grant_effect(item: str) -> Callable[..., list[str]]:
    """开箱分支效果体工厂(闭包销 = 发放道具名,单源取自
    :data:`_STRATEGY_BOX_GRANTS`)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained);``rng`` 不消费——开箱分支确定发放
    (rand=False,gain-chain.md §5),无采样面。效果体只覆盖获得时点容器写分支:
    三卡的战斗被动分支(能量恢复/伤害减免)非获得时点效果,不在本体
    (design §1 明确不解决,归策略效果建模批)。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客卡先例,模块 docstring
        # import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_bench_item,
        )
        _ = rng   # 开箱分支确定发放,无采样面(rng 形参沿注册表分派契约保留)
        placed = gain_bench_item(gs, item, rand=False, sig=sig,
                                 evidence='pick_invest_box_grant',
                                 producer=_PRODUCER)
        return [f'box_grant:{item}(placed={placed})']

    return _effect


# ===== 援军族效果(策略卡获得时点随机同费角色群发:费用档注册池内均匀
# ===== 掷骰 count 名 → 逐名 gain_character(rand=True) 入席,升星/溢出/
# ===== 回调沿链现役;采样池复用随机赠卡家族载体 random_char_pool,禁直读
# ===== chars_by_cost 另立第二采样源——先到者立形、后到复用)=====

#: 建模假设档披露键(在册落点 = 本常量,随局披露面消费;校准只改采样口径
#: 与披露键、不动结构;键形态沿骇客/晶矿同区先例):
#: - uniform: 费用档注册池内均匀 v0(游戏真分布未知,是否受牌库剩余约束
#:   未证;校准源 = logic_rand_outcome 行按效果串前缀 ``strategy_gift_
#:   random:`` 归组;「随机」字样缺席的卡(扩充团队:desc 明写各档数量、
#:   构成零随机仅进席身份随机)同键覆盖——先验依据 = fields.md 效果发牌
#:   族随机组正本定性 + RandomCharSpec docstring 先验语义);
#: - star_prior: desc 未标星 → star=1 先验非结构值(实机直出高星时 bench
#:   观察星级覆盖模型值,随机态不响灯);
#: - with_replacement: 4 抽放回假设申报(实机放回性证据缺,归档帧/实采
#:   校准通道)。
REINFORCEMENT_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_gift_random_char_uniform',
    'strategy_gift_random_char_star_prior',
    'strategy_gift_random_char_with_replacement',
)

#: 援军族发放表单一源(卡规范名 → (费用档, 名数) 对序列;单档卡写单对
#: 字面 = 一档发放,多档混合卡按卡文语序逐对排列)。卡文「获得N个随机
#: X费角色」直读单对;多档混合卡(扩充团队「获得2个1费角色，2个2费角色
#: 和1个3费角色」)各档数量与费用档全为 desc 明写结构值——发放的档位×
#: 数量构成零随机,随机面仅在各档池内的进席身份(抽样先验例外,uniform
#: 披露键载义)。掷序 = 表内对序:工厂按对序循环、同 rng 实例顺序推进,
#: 非「按费用排序」隐式重排(隐式排序会随卡文语序漂移)。效果体条目
#: 由下方工厂从本表生成,禁另写字面量(箱腿先例同纪律:表与效果体两处
#: 独立字面量的漂移在备战断言不可见,唯一致性测试与落位真值可暴露)。
_STRATEGY_REINFORCEMENT_GRANTS: dict[str, tuple[tuple[int, int], ...]] = {
    '二费援军': ((2, 4),),
    '三费援军': ((3, 4),),
    '四费援军': ((4, 4),),
    '扩充团队': ((1, 2), (2, 2), (3, 1)),
}


def roll_reinforcement_names(rng: random.Random, cost: int,
                             count: int) -> list[str]:
    """援军族身份采样(纯函数;rng 注入,sim/live 共用同一语义)。

    池 = 随机赠卡家族载体 :func:`random_char_pool` 派生(规格
    ``RandomCharSpec(cost, star=1)``,type_tag 空 = 费用档全档;uniform
    v0,分布形态未实测,披露键 ``strategy_gift_random_char_uniform``)。

    **前置值域校验**:cost ∉ 1..5 → ValueError——cost=0 档系统单位
    (狸猫对/佩佩族召唤)在册且非空,「池非空」哨防不住误传 0;值域限定
    是系统单位不入随机发放池的唯一保证(发放口径 = 玩家可持有单位域)。

    count 次独立 ``rng.choice`` **放回**(批内同 rng 实例顺序推进不重置,
    晶矿掷序契约同口径:改序 = 掷序漂移;抽重可复现为设计语义非缺陷,
    披露键 ``strategy_gift_random_char_with_replacement``)。
    """
    if cost not in (1, 2, 3, 4, 5):
        raise ValueError(f'援军族费用档越界:cost={cost!r}(合法域 1-5;'
                         f'cost=0 系统单位不入随机发放池)')
    pool = random_char_pool(RandomCharSpec(cost=cost, star=1))
    return [rng.choice(pool) for _ in range(count)]


def _make_reinforcement_effect(
        pairs: tuple[tuple[int, int], ...]) -> Callable[..., list[str]]:
    """援军族效果体工厂(闭包销 = (费用档, 名数) 对序列,单源取自
    :data:`_STRATEGY_REINFORCEMENT_GRANTS`;形态镜像 _make_box_grant_effect)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained)。外层按表内对序循环,逐档
    ``roll_reinforcement_names`` 采样 → 逐名 ``gain_character`` 入席:
    同一 rng 实例跨档顺序推进不重置(掷序契约,改序 = 掷序漂移);采样
    效果对子链传 rand=True(gain-chain.md §5 效果自身性质传参),升星
    级联(单级 3 合 1)/席满溢出/bench 未观察拒落全部沿链现役记账。星级
    1 = desc 未标星的句式先验(先验错走随机态观察覆盖,不响灯)。效果串
    = ``strategy_gift_random:<名>@1star``,前缀 + @ 后缀一体登记——
    @ 后缀 = 随机态校准数据归组键,只断前缀会漏校准分组;发放事实与落位
    成败解耦,效果串恒 Σcount 条(on_env_gained 赠卡通道同口径)。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_character,
        )
        steps: list[str] = []
        for cost, count in pairs:
            for name in roll_reinforcement_names(rng, cost, count):
                gain_character(gs, name, 1, rand=True, sig=sig,
                               evidence='pick_invest_reinforcement',
                               producer=_PRODUCER)
                steps.append(f'strategy_gift_random:{name}@1star')
        return steps

    return _effect


# ===== 随机简易装备族效果(策略卡获得时点随机简易装备发放:简易池均匀
# ===== v0 掷骰 count 件 → 逐件 gain_equipment(rand=True) 入栏,骇客
# ===== roll_hacker_mod + gain_equipment 现役同构;腿族首例 = 打捞人才库+
# =====(id 100702 句 2 装备腿),同族 15 卡后续批各自领取复用本表)=====

#: 建模假设档披露键(在册落点 = 本常量,随局披露面消费;键形态沿骇客/
#: 援军同区先例):
#: - instant_reading: 句 2「获得1个随机简易装备和4金币」按获得时点即时腿
#:   建模(instant_gold 注册口径「选牌当场给金」+ 同句式家族金币成分全
#:   instant 在册——武装支援+/军火贸易族;裁 R-recurring 则改值/退役,
#:   实采判据 = 拿卡后未进任何补给阶段前物品栏是否已多 1 件简易装备);
#: - uniform_simple_pool: 池 = category='简易' 全集均匀 v0(「随机」分布
#:   未标,采样先验例外;游戏真分布未知,是否受已有装备约束未证;校准源
#:   = logic_rand_outcome 行按效果串前缀 ``strategy_random_equip:``
#:   归组)。
STRATEGY_SALVAGE_PLUS_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_salvage_plus_instant_reading',
    'strategy_random_equip_uniform_simple_pool',
)

#: 随机简易装备族发放表单一源(卡规范名 → 件数;卡文「获得1个随机简易
#: 装备」直读)。效果体条目由下方工厂从本表生成,禁另写字面量(箱腿/
#: 援军表先例纪律:表与效果体两处独立字面量的漂移在备战断言不可见,
#: 唯一致性测试与落位真值可暴露)。
_STRATEGY_RANDOM_EQUIP_GRANTS: dict[str, int] = {
    '打捞人才库+': 1,
}

#: 随机简易装备池(category='简易' 全集,字母序确定性;池口径随装备注册
#: 表传导)。与晶矿 cw_ore_reward._SIMPLE_EQUIP_POOL 同表达式同口径,
#: 独立定义互指不跨模块引私有名(晶矿池为模块私有名;两池口径漂移由
#: 测试侧同集断言守住)。
_RANDOM_SIMPLE_EQUIP_POOL: tuple[str, ...] = tuple(sorted(
    name for name, eq in EQUIPMENTS.items() if eq.category == '简易'))


def roll_random_simple_equip(rng: random.Random) -> str:
    """单次随机简易装备身份采样(纯函数;rng 注入,sim/live 共用同一语义)。
    池 = :data:`_RANDOM_SIMPLE_EQUIP_POOL`(等概率均匀;分布形态未实测,
    披露键 ``strategy_random_equip_uniform_simple_pool``)。"""
    return rng.choice(_RANDOM_SIMPLE_EQUIP_POOL)


def _make_random_equip_effect(count: int) -> Callable[..., list[str]]:
    """随机简易装备效果体工厂(闭包销 = 件数,单源取自
    :data:`_STRATEGY_RANDOM_EQUIP_GRANTS`;形态镜像 _make_reinforcement_effect)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained)。逐件采样 → ``gain_equipment``
    入栏:采样效果对子链传 rand=True(gain-chain.md §5 效果自身性质
    传参),装备获得后果经 on_equipment_gained 回调自动消费;equips 未
    观察 = 原语现役拒落跳写(detail='equips_unobserved')。装备无星级,
    效果串不带 @<N>star 后缀:``strategy_random_equip:<名>``(落位)/
    ``strategy_random_equip:<名>(skipped)``(跳写,骇客 mod_equip/
    mod_sampled 两形态同构);发放事实与落位成败解耦,效果串恒 count 条。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿/援军先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_equipment,
        )
        steps: list[str] = []
        for _ in range(count):
            name = roll_random_simple_equip(rng)
            eq = gain_equipment(gs, name, rand=True, sig=sig,
                                evidence='pick_invest_random_equip',
                                producer=_PRODUCER)
            if eq.placed:
                steps.append(f'strategy_random_equip:{name}')
            else:
                steps.append(f'strategy_random_equip:{name}(skipped)')
        return steps

    return _effect


# ===== 具名装备授予族效果(策略卡获得时点具名装备确定发放:逐件
# ===== gain_equipment(rand=False) 入栏,随机简易装备工厂同构、差异 =
# ===== 无采样;族模式卡 = 全员晋升(拆装扳手×2),同族后继卡(精密拆装
# ===== 族/冶金炉/垃圾袋/星徽秘典等)按 (item, count) 直呼本工厂登记)=====

#: 精密金面 fail-closed 申报行 kind(独立小块非 DEFECT_ 词表成员:语义
#: 申报非缺陷告警,沿 cw_gain_chain.ENV_REROLL_DECL 先例形态)。金面
#: 未建模期本腿拒入栏的留证通道;金面接线批落地时随前置分支一并退役。
NAMED_EQUIP_PRECISE_DECL: str = 'named_equip_grant_precise_decl'

#: 具名装备授予的精密金面判据映射(装备名 → 触发金面改道的在场判据物):
#: 官方规则「已持精密拆装扳手后再获得拆装扳手,改为获得 1 金币」
#: (cw_equipment_data 拆装扳手条目)属性挂在**物**上——按物判不按卡判,
#: 后继卡直呼工厂发放同物时规则自动生效,卡级前置分支禁内嵌闭包
#: (工厂泛化硬要求,否则卡级分支遗传会给不携金面规则的发放物误拒)。
_NAMED_EQUIP_PRECISE_GATES: dict[str, str] = {
    '拆装扳手': '精密拆装扳手',
}


def _make_named_equip_grant_effect(
        item: str, count: int) -> Callable[..., list[str]]:
    """具名装备授予效果体工厂(闭包销 = (装备名, 件数),登记行直书形参即
    单一源;形态镜像 _make_random_equip_effect,差异 = 具名确定发放,
    零采样面)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained);``rng`` 不消费——具名发放确定
    (rand=False,gain-chain.md §5:卡文无随机词;与环境侧即时装备支
    rand=True 随机态〔2026-10-17 用户裁定,猜测写 + 观察覆盖纠偏〕系
    两通道分野,正本注记 = fields.md §3.2.15 获得链写入方段)。逐件
    ``gain_equipment`` 入栏,装备获得后果经 on_equipment_gained 回调
    自动消费;equips 未观察 = 原语现役拒落零写。效果串逐件一条
    ``named_equip_grant:<名>(placed=<bool>)``(沿箱腿 placed 形态,
    拒落可审计;前缀与 box_grant=占席道具 / equip_grant=延时装备 /
    strategy_random_equip=随机装备 分域,审计可独立过滤)。

    **幂等不设防申报**:同局重复获得同卡(策略去重后注册段跳写、效果
    腿照常分派)= 每次获得各发 count 件,现役不设判重闸——与全部注册
    效果腿同规,不另立闸。

    **精密金面前置(fail-closed)**:发放物命中
    :data:`_NAMED_EQUIP_PRECISE_GATES` 且判据物在场
    (held_equip_count ≥ 1,惰性 import,沿骇客卡先例)→ 整腿零容器写
    + 申报行留证(:data:`NAMED_EQUIP_PRECISE_DECL`)+ 效果串仍逐件
    登记(placed=False)。理由:官方真值 = 改 +1 金不进栏
    (cw_effect_inventory.settle_wrench_duplicate_gold 窗口语义),
    而金面组合写未建模、生产接线归获得回执覆盖批(接线归属注记 =
    cw_affix_effects.py EQUIP_REWRITE_DECLARATIONS 精密拆装扳手行)
    ——无条件入栏会在锚定态产假失配行、在未锚定态静默写假值;真值
    归观察覆盖,覆盖批落地时回改本分支(金面生效 = 不入栏改入金)。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_equipment,
        )
        _ = rng   # 具名确定发放,无采样面(rng 形参沿注册表分派契约保留)
        gate = _NAMED_EQUIP_PRECISE_GATES.get(item)
        if gate is not None:
            # 计数底座惰性 import(贡献算术模块头反向依赖链模块,函数内取
            # 同骇客卡避环纪律;纯读零写)
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                held_equip_count,
            )
            if held_equip_count(gs, gate) >= 1:
                _emit_defect(field_name='equips',
                             expected=f'{count}件{item}(精密在场,官方改道'
                                      f'+{count}金)',
                             actual='零容器写(fail-closed,金面未建模,'
                                    '真值归观察/接线覆盖批)',
                             evidence=f'pick_invest_named_equip:{item}',
                             sig=sig, kind=NAMED_EQUIP_PRECISE_DECL)
                return [f'named_equip_grant:{item}(placed=False)'
                        for _ in range(count)]
        steps: list[str] = []
        for _ in range(count):
            outcome = gain_equipment(gs, item, rand=False, sig=sig,
                                     evidence='pick_invest_named_equip',
                                     producer=_PRODUCER)
            steps.append(f'named_equip_grant:{item}'
                         f'(placed={outcome.placed})')
        return steps

    return _effect


# ===== 策略延时 offer 族效果(策略卡获得时点入延迟队列:拿卡即登记
# ===== 倒计时,到点呈现归 sim 专用腿,本模块零采样面)=====

def _make_delayed_offer_effect(name: str) -> Callable[..., list[str]]:
    """延时 offer 登记腿效果体工厂(闭包销 = 规范卡名,登记值单源取自
    cw_investments.STRATEGY_DELAYED_OFFERS;形态镜像 _make_box_grant_effect
    的「惰性 import 链原语 + 薄壳」分工——handler 只做注册表查行 +
    原语调用,写通道单一收束在链模块)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained);``rng`` 不消费——登记腿零采样,
    倒计时按登记值确定推算。入队即写(唯一登记写端),到期呈现归
    sim 呈现腿(不对称申报,live 队列恒悬置)。效果串 =
    ``strategy_offer_scheduled:<品质>@<节拍>``(@ 形态沿定时道具
    ``item_scheduled`` 家族先例)。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿箱腿/援军先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            queue_delayed_invest_offer,
        )
        _ = rng   # 登记腿零采样,倒计时推算确定(rng 形参沿分派契约保留)
        return [queue_delayed_invest_offer(gs, name, sig=sig)]

    return _effect


# ===== 策略延时发放族效果(策略卡获得时点双腿:即时装备腿 + 延时入队
# ===== 腿;到点发放归 sim 专用腿,本模块零采样面)=====

def _make_delayed_grant_effect(name: str) -> Callable[..., list[str]]:
    """延时发放登记腿效果体工厂(闭包销 = 规范卡名,登记值单源取自
    cw_investments.STRATEGY_DELAYED_GRANTS;形态镜像
    _make_delayed_offer_effect 的「惰性 import 链原语 + 薄壳」分工——
    handler 只做注册表查行 + 原语调用,写通道单一收束在链模块)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参);``rng``
    不消费——两腿零采样(具名发放 = 确定发放,gain-chain.md §5
    rand=False 纪律)。两步:

    1. 即时腿:gain_equipment 具名入栏(equips 未观察 = 拒落零写
       placed=False,gain_equipment 既有语义);
    2. 延时入队腿:queue_delayed_strategy_grant 唯一登记写端,到点
       发放归 sim 专用腿(不对称申报)。

    效果串 = ``equip_grant:<item>(placed=<bool>)``(沿 box_grant 形态)/
    ``strategy_grant_scheduled:<item>@<节拍>``(沿 offer 登记腿
    @ 形态)。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿箱腿/援军先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_equipment,
            queue_delayed_strategy_grant,
        )
        _ = rng   # 两腿零采样,具名确定发放(rng 形参沿分派契约保留)
        spec = STRATEGY_DELAYED_GRANTS[name]
        outcome = gain_equipment(gs, spec.item, rand=False, sig=sig,
                                 evidence='strategy_grant_instant',
                                 producer=_PRODUCER)
        return [f'equip_grant:{spec.item}(placed={outcome.placed})',
                queue_delayed_strategy_grant(gs, name, sig=sig)]

    return _effect


# ===== 多腿组合效果(混发卡专属:策略卡获得时点双腿/多腿组合发放,族首 =====
# ===== 卡 = 武装支援;各腿复用单族工厂,组合卡不入任何单族表——表行生成 =====
# ===== 的是单腿效果体,与组合体同名键经 dict 字面量顺序覆盖静默丢腿, =====
# ===== 组合登记行 = 腿参数唯一出现点,单一源成立)=====

def _compose_grant_legs(
        *legs: Callable[..., list[str]]) -> Callable[..., list[str]]:
    """多腿组合效果体工厂(闭包销 = 腿效果体序列,依组合登记行形参序)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained)。按形参序逐腿调用,各腿共享同一
    ``(gs, sig, rng)``——同 rng 实例跨腿顺序推进不重置(掷序契约:
    改序 = 掷序漂移,晶矿同口径);腿序 = 卡文语序(表内对序「禁隐式
    重排」纪律同源),效果串按腿序拼接。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        steps: list[str] = []
        for leg in legs:
            steps.extend(leg(gs, sig=sig, rng=rng))
        return steps

    return _effect


# ===== 具名角色发放族效果(策略卡获得时点具名角色确定发放:gain_character
# ===== (rand=False) 入席,落位/回调/升星/席满溢出全沿链现役;现役成员 =
# ===== 溜佩佩/溜佩佩+(族首落)/招财狗(佩佩召唤族,世界腿),后继卡
# ===== (佩佩驾到/艾丝妲的猛犬!)+1 行复用本表)=====

#: 具名角色发放名单单一源(卡规范名 → 发放角色;登记面镜像 =
#: cw_investments.STRATEGY_GRANTS 对应卡 chars_immediate,一致性测试
#: 逐对相等,箱腿 _STRATEGY_BOX_GRANTS 同构)。注册表条目由下方工厂从
#: 本表生成,禁另写字面量(表与效果体两处独立字面量的漂移在备战断言
#: 不可见,箱腿 A4 教训同纪律)。
_STRATEGY_CHAR_GRANTS: dict[str, str] = {
    '溜佩佩': '佩佩',
    '溜佩佩+': '佩佩',
    '招财狗': '佩佩',
}


def _make_char_grant_effect(char: str) -> Callable[..., list[str]]:
    """具名角色发放效果体工厂(闭包销 = 发放角色名,单源取自
    :data:`_STRATEGY_CHAR_GRANTS`;形态镜像 _make_box_grant_effect,
    差异 = 发放对象是角色,走 gain_character)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained);``rng`` 不消费——具名确定发放
    (rand=False,gain-chain.md §5:卡文无随机词、选卡确认 = 确定性入口)。
    星级实参恒 1 = 占位非先验:佩佩系 cost0 系统召唤单位无星级概念
    (cw_chars 在册),链签名必填星参落占位值,环境侧佩佩发放已立同判。
    落位/回调/升星/席满溢出语义全部沿 gain_character 现役,零新增链为。
    效果串 ``char_grant:<名>(placed=<bool>,merge=<int>)``——前缀独立
    分域(box_grant=占席道具/named_equip_grant=装备/strategy_gift_
    random=随机角色群发),审计可独立过滤;merge = 本次获得链上升星
    级数(单发恒 0,升星级联随串留证)。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_character,
        )
        _ = rng   # 具名确定发放,无采样面(rng 形参沿注册表分派契约保留)
        r = gain_character(gs, char, 1, rand=False, sig=sig,
                           evidence='pick_invest_char_grant',
                           producer=_PRODUCER)
        return [f'char_grant:{char}(placed={r.placed},merge={r.merge_levels})']

    return _effect


PICK_INVEST_EFFECTS: dict[str, Callable[..., list[str]]] = {
    '骇客专家:银狼': _apply_effect_hacker_wolf,
    **{name: _make_box_grant_effect(item)
       for name, item in _STRATEGY_BOX_GRANTS.items()},
    **{name: _make_reinforcement_effect(pairs)
       for name, pairs in _STRATEGY_REINFORCEMENT_GRANTS.items()},
    **{name: _make_random_equip_effect(count)
       for name, count in _STRATEGY_RANDOM_EQUIP_GRANTS.items()},
    # 武装支援 = 双腿混发组合卡(卡文「获得1件随机简易装备和2个随机3费
    # 角色。」):直书登记行(非表生成),不入援军/随机简易装备两族表
    # (入表 = 表生成的单腿效果体与组合体同名键顺序覆盖丢腿);腿序 =
    # 卡文语序装备腿先/角色腿后,腿参数在此单次出现(单一源)。
    '武装支援': _compose_grant_legs(_make_random_equip_effect(1),
                                    _make_reinforcement_effect(((3, 2),))),
    # 武装支援+ = 三腿分层组合卡(卡文「获得1件随机简易装备和1个随机4费
    # 角色，获得6金币。」):效果体双腿同上(装备腿先/角色腿后,4 费池
    # 放回抽 1);金腿分层 = STRATEGY_ECONOMY 注册行(instant_gold=6)在册
    # 承载,金面禁直写不进效果体(sim 金发放写端缺口归 T-112 族级待办);
    # 不入两族表同上(同名键顺序覆盖丢腿)。
    '武装支援+': _compose_grant_legs(_make_random_equip_effect(1),
                                     _make_reinforcement_effect(((4, 1),))),
    # 全员晋升 = 具名装备授予族模式卡(卡文「获得2个【拆装扳手】」):
    # 直书登记行(沿组合卡字面项区式样;族内后继卡同形直呼工厂,精密金面
    # 前置按物判内嵌工厂、卡级分支零遗传)。拆装扳手 = 工具类装备
    # (cw_equipment_data category='工具'),归 equips 装备库存域——禁入
    # 占席道具通道(BENCH_ITEM_KINDS 全量显式映射无此物,错入 items 会
    # 伪造占席身份);板面重写腿(同卡另一句)零改动在册,STRATEGY_
    # EFFECTS 注册行 board_rewrite 分派承载,本腿只辖装备句。
    '全员晋升': _make_named_equip_grant_effect('拆装扳手', 2),
    # 无伤通关 = 具名装备授予族后继(卡文「立即获得1个【生命之花】」):
    # 直书登记行直呼工厂;生命之花 = 简易类装备(cw_equipment_data),不在
    # 精密金面判据映射内(gate 恒 None)走纯发放循环,精密在场不受污染。
    # 条件金腿(战斗结束时无角色陷入无法战斗 → +1金)双端真值皆盲零建模
    # (正本 = invest_effects.md §8 型③成员;估值失真口径由 STRATEGY_
    # ECONOMY 注册行 instant_gold=1 在册承载,fields.md §4.1/§5.2),
    # 金面禁直写不进效果体,本行只辖装备句。
    '无伤通关': _make_named_equip_grant_effect('生命之花', 1),
    **{name: _make_char_grant_effect(char)
       for name, char in _STRATEGY_CHAR_GRANTS.items()},
    **{name: _make_delayed_offer_effect(name)
       for name in STRATEGY_DELAYED_OFFERS},
    **{name: _make_delayed_grant_effect(name)
       for name in STRATEGY_DELAYED_GRANTS},
}
"""策略卡获得效果注册表(键 = 注册表规范名;骇客单行自 pick_invest.py 迁入,
开箱分支五条由工厂自 _STRATEGY_BOX_GRANTS 生成,援军族由工厂自
_STRATEGY_REINFORCEMENT_GRANTS 生成,随机简易装备族由工厂自
_STRATEGY_RANDOM_EQUIP_GRANTS 生成,组合卡(武装支援/武装支援+)直书登记行
由组合子组合双腿(非表生成),具名装备授予族(全员晋升/无伤通关)直书登记行由
_make_named_equip_grant_effect 生成闭包,具名角色发放族(溜佩佩/溜佩佩+/
招财狗)由工厂自 _STRATEGY_CHAR_GRANTS 生成,策略延时 offer 族由工厂自
cw_investments.STRATEGY_DELAYED_OFFERS 派生,策略延时发放族由工厂自
cw_investments.STRATEGY_DELAYED_GRANTS 派生——登记表 +1 行即自动获得
登记腿,键集封闭断言守住两表面零漂移)。未收录名 = 零效果分派(查无
效果安静不写,真值归观察覆盖)。与 STRATEGY_EFFECTS(经济聚合面)职责分离
声明见各表模块头。"""
