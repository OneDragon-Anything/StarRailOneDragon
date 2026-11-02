"""货币战争 获得效果面(cw_gain_effects):策略卡「获得时效果」的注册表 +
效果函数体 + 骇客改件采样池 + 随机装备泛化发放表((category, count) 行,
池 = 装备注册表按类别派生单一源)。

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

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _emit_defect,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_DELAYED_GRANTS,
    STRATEGY_DELAYED_OFFERS,
    RandomCharSpec,
    dakuozhao_deduction_plan,
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
    '步狸村之谜': '简易武装箱',
    # 阿哈大悦:箱腿直读「获得1个【简易武装箱】」(获得时点 = 激活链
    # 尾段,时点差系猜测写+观察纠偏先例,sim 严格等价差异窗无决策消费;
    # 40% 伤害增幅/拆散回栏 = 召唤物战斗数值面零建模 T-205 裁定同判)。
    '阿哈大悦': '简易武装箱',
}


def _make_all_cost_chars_effect(cost: int) -> Callable[..., list[str]]:
    """全员同费档发放效果体工厂(闭包销 = 费用档;「获得所有N费角色各一
    个」族首例 = 广聚天下英才)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参);
    ``rng`` 零消费——全员确定性发放(rand=False,无采样面),显式丢弃。
    池 = ``chars_by_cost(cost)`` 注册表派生全集(静态池,含专家——策略
    侧发放族家族口径,披露键 ``strategy_all_chars_pool_includes_expert``
    承载改判挂点);逐名 ``gain_character(rand=False)`` 入席(升星/溢出/
    级联沿链现役,零特判);效果串逐名一条恒 Σ池数条(发放事实与落位
    成败解耦,零写名带落位失败标注)。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿先例)
        _ = rng  # 零随机面(全员确定性发放)
        from sr_od.application.currency_war.data.cw_chars import (
            chars_by_cost,
        )
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_character,
        )
        steps: list[str] = []
        for ch in chars_by_cost(cost):
            name = ch.name
            gain_character(gs, name, 1, rand=False, sig=sig,
                           evidence='pick_invest_all_chars',
                           producer=_PRODUCER)
            steps.append(f'all_cost_chars:{name}@1star')
        return steps

    return _effect

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


# ===== 变量计数随机角色腿(策略卡获得时点按持金现算发放只数:卡文
# ===== 「每损失N金币,获得一个随机X费角色」族首例 = 大扩招;差异于援军
# ===== 族 = 表载常量名数,本族发放只数非表载,按拿卡拍持金现算,故
# ===== 不入 _STRATEGY_REINFORCEMENT_GRANTS 表、专用效果体直书)=====

def _apply_effect_recruit_drain(gs: GameState, *, sig: ChannelSig,
                                rng: random.Random) -> list[str]:
    """效果函数·大扩招(策略卡,变量计数随机角色腿)。

    发放只数按拿卡拍持金现算(:func:`dakuozhao_deduction_plan` 角色数
    分量,单一源住 cw_investments)——卡文「每损失4金币,获得一个随机
    4费角色」= 扣金与发放同判据,数量随持金线性变化(0..10)。本函数
    **只取 n 零扣金**:扣金归 sim 选卡落地拍负腿世界真值(sim 专用,
    live 游戏自扣观察覆盖,金面禁逻辑直写),效果体写金会让 live 误写
    实机自扣的金面;双端发放量无差(公式读同一持金基数,本函数零写金)。
    持金读数缺(None)= 按 0 现算 → n=0 零发放(fail-closed 缺播防御,
    与 sim 侧读法同形)。

    链序:池 = ``random_char_pool(RandomCharSpec(cost=4, star=1))``
    (星级 desc 未标 = 1 先验,RandomCharSpec 家族口径)→ 同 rng 实例
    n 抽**放回**(可重复同名,批内同 rng 顺序推进不重置,援军族掷序
    契约同口径)→ 逐只 ``gain_character(rand=True)``,落位/升星级联/
    席满溢出沿链四态记账(随机态写入走台账纠偏 + bench 观察覆盖)。

    假设面(池内均匀 v0 / star=1 先验 / n 抽放回)语义与策略侧随机
    赠卡族级披露键 :data:`REINFORCEMENT_ASSUMPTION_KEYS` 三键同构,
    零新增独立键;扣金取整读法由正本 invest_effects.md B 类裁定行
    承载。效果串 ``strategy_gift_random:<名>@1star`` 逐只一条(发放
    事实与落位成败解耦)。
    """
    # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿/援军先例,模块
    # docstring import 方向声明)
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        gain_character,
    )
    _, n = dakuozhao_deduction_plan(int(gs.gold.value or 0))
    steps: list[str] = []
    pool = random_char_pool(RandomCharSpec(cost=4, star=1))
    for _ in range(n):
        name = rng.choice(pool)
        gain_character(gs, name, 1, rand=True, sig=sig,
                       evidence='pick_invest_recruit_drain',
                       producer=_PRODUCER)
        steps.append(f'strategy_gift_random:{name}@1star')
    return steps


# ===== 绑定型随机角色授予族效果(策略卡获得时点随机角色发放 + 名字绑定:
# ===== 采样池/掷序复用援军族单一源,差异 = 到手星级表载 + 采样后 sim 门
# ===== 控写绑定域,供每节点复制发放腿消费;族首卡 = 价值投资·金(卡面
# ===== cw_invest_data.py 200401:「获得1个随机的2星1费角色。每次进入新
# ===== 节点时,获得1星的该角色,补给后额外获得2个,持续至本局游戏结束。」),
# ===== 姊妹价值投资·彩(2星2费同构)+1 行复用本表)=====

#: 随机角色授予族采样分布披露键(家族常量,收编援军族在册两键——uniform
#: v0 = 费用档注册池内均匀未实测 / with_replacement = 放回抽样申报;本卡
#: 零新增键内容。star 维不随本族设键:绑定卡到手星级 = desc 明写结构值
#: 非先验,star 先验键 ``strategy_gift_random_char_star_prior`` 仍属援军
#: 族三键常量 :data:`REINFORCEMENT_ASSUMPTION_KEYS`,不随本族携带。消费
#: 面 = 实测校准与披露清单,在册先例 = 同区家族常量形)。
STRATEGY_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_gift_random_char_uniform',
    'strategy_gift_random_char_with_replacement',
)

#: 绑定型随机角色授予表单一源(卡规范名 → (费用档, 名数, 到手星级)):
#: 援军族表形 (费用档, 名数) 的显式 star 维扩展(星级行 = 卡文「2星」
#: 明写结构值,非援军族未标星先验;末元星级的族形修订由族首例卡携带)。
#: 效果体条目由下方工厂从本表
#: 生成,禁另写字面量(援军/箱腿同纪律:表与效果体两处独立字面量的漂移
#: 在备战断言不可见,唯一致性测试与落位真值可暴露)。绑定名消费面 =
#: 每节点复制发放腿(cw_gain_chain.check_strategy_node_char_grants),
#: 绑定承载域 = GameState.strategy_char_grant_bindings。
_STRATEGY_CHAR_GRANT_BINDINGS: dict[str, tuple[int, int, int]] = {
    '价值投资·金': (1, 1, 2),
}


def _make_bound_char_grant_effect(
        card: str, cost: int, count: int, star: int) -> Callable[..., list[str]]:
    """绑定型随机角色授予效果体工厂(闭包销 = (卡规范名, 费用档, 名数,
    到手星级),单源取自 :data:`_STRATEGY_CHAR_GRANT_BINDINGS`;形态镜像
    _make_reinforcement_effect,差异 = 星级表载 + 采样后写绑定域)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained)。逐名采样 → ``gain_character``
    入席:采样 = :func:`random_char_pool` 注册表派生池(规格
    ``RandomCharSpec(cost, star=star)``,禁 chars_by_cost 第二采样源,
    援军族 import 方向声明同款)内均匀放回抽 count 名(援军族掷序契约:
    批内同 rng 顺序推进不重置,抽重可复现为设计语义);前置值域校验
    cost ∈ 1..5 ∧ star ∈ 1..3 → ValueError(cost=0 系统单位不入随机
    发放池,援军族同款哨;star 值域 = Unit.star 合法域,越界 = 表行
    笔误响应亮);采样效果对子链传 rand=True(gain-chain.md §5),升星
    级联/席满溢出/bench 未观察拒落全沿链现役。效果串
    ``strategy_gift_random:<名>@<star>star``(前缀 + @ 后缀一体登记:
    @ 后缀 = 随机态校准数据归组键,只断前缀会漏校准分组)。

    **采样后 sim 门控写绑定**(本族独有腿,每节点复制发放腿的唯一发放
    判据):kernel→sim.ports 函数内惰性 import(在码先例 =
    cw_gain_chain.check_strategy_star_merge_gold/check_strategy_first_
    buy_xp_grants)——``sim_backend_installed()`` True → 绑定即世界
    真值,``gs.write_logic`` 直写 ``gs.strategy_char_grant_bindings``
    合并 ``{卡名: 名}``(多卡同局双持各键并存;evidence
    ``value_invest_bind:<卡名>:<名>``);False(live)→ 零写绑定:live
    掷骰是猜测(效果串面下一备战帧观察纠偏),假绑定即使无消费面也禁
    入容器——绑定域无观察纠偏通道且为复制发放腿唯一判据,假绑定静默
    存续不可接受(同码先例 = cw_gain_chain.on_env_gained 随机装备绑定
    分支无条件双端写,其域有 done 键随写可对账,本域刻意更严)。

    **拿卡当节点不发**(申报为读法非缺陷):选卡发生在该节点窗 offer
    段,窗已开、本窗复制发放腿已走完,绑定写入晚于本窗腿 = 自然从下一
    节点起发放,「每次进入新节点时」文义自洽。
    """

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿/援军先例,
        # 模块 docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_character,
        )
        if cost not in (1, 2, 3, 4, 5) or star not in (1, 2, 3):
            raise ValueError(
                f'绑定型随机角色授予表值越界:cost={cost!r} star={star!r}'
                f'(合法域 cost 1-5 / star 1-3;cost=0 系统单位不入随机'
                f'发放池,star 值域 = Unit.star 合法域)')
        steps: list[str] = []
        picked: list[str] = []
        pool = random_char_pool(RandomCharSpec(cost=cost, star=star))
        for _ in range(count):
            name = rng.choice(pool)
            picked.append(name)
            gain_character(gs, name, star, rand=True, sig=sig,
                           evidence='pick_invest_bound_char',
                           producer=_PRODUCER)
            steps.append(f'strategy_gift_random:{name}@{star}star')
        # 采样后 sim 门控写绑定(放在发放循环后:掷序契约 = 采样全部
        # 完成再落账,掷点顺序与援军族同构可复现;live 零写禁假绑定入
        # 容器——复制发放腿唯一判据,假值静默存续不可接受)
        from sr_od.application.currency_war.sim.cw_sim_ports import (
            sim_backend_installed,
        )
        if sim_backend_installed():
            # 绑定名 = 现役表行 count=1 的采样名;count>1 行「该角色」
            # 指代未载(卡文单数),绑定语义归其登记批裁,禁 picked[0]
            # 静默代答——届时在登记面显式补语义。
            merged = dict(gs.strategy_char_grant_bindings.value or {})
            merged[card] = picked[0]
            gs.write_logic(gs.strategy_char_grant_bindings, merged,
                           produced_by=_PRODUCER,
                           evidence=f'value_invest_bind:{card}:{picked[0]}',
                           sig=sig)
        return steps

    return _effect


# ===== 随机装备族效果(策略卡获得时点随机装备发放:类别池均匀 v0 掷骰
# ===== count 件 → 逐件 gain_equipment(rand=True) 入栏,骇客
# ===== roll_hacker_mod + gain_equipment 现役同构;首例 = 打捞人才库+
# =====(id 100702 句 2 装备腿,简易行),第二类别首例 = 买彩票(id 110101
# ===== 星徽行,泛化 (category, count) 表一次成形防类别碎片),同族后继卡
# ===== 各自领取按 (category, count) +1 行复用本表)=====

#: 建模假设档披露键(在册落点 = 本常量,随局披露面消费;键形态沿骇客/
#: 援军同区先例):
#: - instant_reading: 打捞人才库+ 句 2「获得1个随机简易装备和4金币」按获得
#:   时点即时腿建模(instant_gold 注册口径「选牌当场给金」+ 同句式家族金币
#:   成分全 instant 在册——武装支援+/军火贸易族;裁 R-recurring 则改值/
#:   退役,实采判据 = 拿卡后未进任何补给阶段前物品栏是否已多 1 件简易装备)。
#:   本常量辖该卡面金腿读法;全族采样分布假设另键,见
#:   :data:`STRATEGY_RANDOM_EQUIP_ASSUMPTION_KEYS`。
STRATEGY_SALVAGE_PLUS_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_salvage_plus_instant_reading',
)

#: 随机装备族采样分布披露键(家族单键,类别无关 uniform v0):池 =
#: ``equips_by_category(表值类别)`` 注册表派生全集均匀(「随机」分布
#: 未标,采样先验例外;游戏真分布未知——实机「随机星徽」是否全池、
#: 是否受持有约束均未证,「随机简易」同案;校准源 = logic_rand_outcome
#: 行按效果串前缀 ``strategy_random_equip:`` 归组)。键类别无关:池派生
#: 方式按类别同构、假设同一;简易行首例期的专项键
#: ``strategy_random_equip_uniform_simple_pool`` 语义被本键覆盖,随表
#: 泛化归并退役。
STRATEGY_RANDOM_EQUIP_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_random_equip_uniform',
)

#: 随机装备族发放表单一源(卡规范名 → (装备类别名, 件数);卡文「获得
#: N个随机X装备」直读,类别 ∈ EQUIPMENTS category 词表)。效果体条目由
#: 下方工厂从本表生成,禁另写字面量(箱腿/援军表先例纪律:表与效果体
#: 两处独立字面量的漂移在备战断言不可见,唯一致性测试与落位真值可暴露)。
#: 泛化表不加专设 import 期校验(沿族既定裁定:池随注册表传导,池空属
#: 数据面事故非本腿职责;'星徽' 行搭环境侧 import 期独立闸便车 =
#: cw_investments._validate_env_gifts,单一闸两消费者),运行期池空走
#: 工厂 log 防御分支零写兜底。
_STRATEGY_RANDOM_EQUIP_GRANTS: dict[str, tuple[str, int]] = {
    '打捞人才库+': ('简易', 1),
    '买彩票': ('星徽', 1),
    '公司军火更新·银': ('简易', 1),
    # 自由市场(id 130601)腿2「获得1个随机的简易装备」直读行;腿1 转换
    # 腿不辖本表(「改为获得」条件改写另表
    # cw_investments.STRATEGY_EQUIP_GAIN_CONVERSIONS 在获得原语顶段拦截),
    # 两腿分治。自我交互属卡面字面:选卡先注册后跑本效果,掷得的采样名
    # 经原语时被转换腿拦截消费——净得 1 箱,rng 消耗序不变(先掷后转),
    # 非特例豁免(设计 designs/T-143-ziyou-shichang.md §2.1)。
    '自由市场': ('简易', 1),
    # 枪在手(id 200501)「立刻获得1件随机简易装备」即时腿直读行(cw_
    # invest_data.PLAZA_AUGMENTS 同 id 行);同卡战后腿「首领战后,获得
    # 1件随机简易装备」触发时点非选卡拍,不入本表——另立
    # cw_investments.STRATEGY_BOSS_BATTLE_GRANTS(扩形状各建各表)。
    '枪在手': ('简易', 1),
    # 枪在手+(id 200502)「立刻获得2件随机简易装备」即时腿直读行;count=2
    # 放回语义首个实成员(两次独立掷可重复同件,工厂 docstring 放回口径的
    # 兑现点——卡面无「不同」限定,放回即 v0 直读);战后腿与模式卡同句
    # 同值,另立 cw_investments.STRATEGY_BOSS_BATTLE_GRANTS 行。
    '枪在手+': ('简易', 2),
    # 空仓(id 202401)「获得1件随机的简易装备」即时腿直读行(cw_invest_
    # data.PLAZA_AUGMENTS 同 id 行);同卡条件腿「进入新节点时,如果物品栏
    # 和备战席没有任何装备(消耗品除外),则获得2经验值」触发时点非选卡拍,
    # 不入本表——另立 cw_investments.STRATEGY_EMPTY_EQUIP_XP_GRANTS(节点
    # 条件 XP 通道,判定 = check_strategy_empty_equip_xp)。
    '空仓': ('简易', 1),
    '空仓+': ('简易', 1),
}


def roll_random_equip(rng: random.Random, category: str) -> str:
    """单次随机装备身份采样(纯函数;rng 注入,sim/live 共用同一语义)。
    池 = ``cw_investments.equips_by_category(category)`` 注册表派生单源
    (函数内惰性 import,沿本模块效果体惰性纪律——公开注册表函数,零新增
    模块级边;注册表构建序确定性,种子可复现)。等概率均匀;分布形态未
    实测,披露键 ``strategy_random_equip_uniform``。池空 = 注册表漂移,
    防御归工厂(本函数纯采样,零容器零日志面)。"""
    from sr_od.application.currency_war.kernel.cw_investments import (
        equips_by_category,
    )
    return rng.choice(equips_by_category(category))


def _make_random_equip_effect(
        category: str, count: int) -> Callable[..., list[str]]:
    """随机装备效果体工厂(闭包销 = (装备类别名, 件数),单源取自
    :data:`_STRATEGY_RANDOM_EQUIP_GRANTS`;形态镜像 _make_reinforcement_effect)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained)。逐件采样 → ``gain_equipment``
    入栏:采样效果对子链传 rand=True(gain-chain.md §5 效果自身性质
    传参),装备获得后果经 on_equipment_gained 回调自动消费;equips 未
    观察 = 原语现役拒落跳写(detail='equips_unobserved')。装备无星级,
    效果串不带 @<N>star 后缀:``strategy_random_equip:<名>``(落位)/
    ``strategy_random_equip:<名>(skipped)``(跳写,骇客 mod_equip/
    mod_sampled 两形态同构);发放事实与落位成败解耦,效果串恒 count 条。
    count>1 放回语义为 v0 口径(每次独立掷,可重复件名),后继多件卡另案
    复核。池空 = 注册表漂移 → log 防御分支零写(不炸链,环境侧随机装备支
    on_env_gained 同款)。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿/援军先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_equipment,
        )

        # 池空防御同源取池(泛化表不设 import 期闸,运行期 log 兜底,环境
        # 侧随机装备支同款;正常路径与采样器同源,零第二表达式)
        from sr_od.application.currency_war.kernel.cw_investments import (
            equips_by_category,
        )
        if not equips_by_category(category):
            log.warning(f'[cw-gain] 策略随机装备类别池空(注册表漂移?):'
                        f'category={category!r}')
            return []
        steps: list[str] = []
        for _ in range(count):
            name = roll_random_equip(rng, category)
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


def _make_delayed_only_grant_effect(name: str) -> Callable[..., list[str]]:
    """延时-only 登记腿效果体工厂(卡文纯延时单句卡专属:族内直用两腿
    工厂会把即时装备腿错发给无即时句的卡——拿卡当场多发一件即时发放物,
    行为级错误,故姊妹工厂并列、按卡文句式分流)。闭包销 = 规范卡名,
    登记值单源取自 cw_investments.STRATEGY_DELAYED_GRANTS;形态镜像
    _make_delayed_offer_effect 的「惰性 import 链原语 + 薄壳」分工。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参);
    ``rng`` 不消费——登记 = 确定事件(倒计时按登记值推算,零采样)。
    单腿 = 仅入队腿:queue_delayed_strategy_grant 唯一登记写端,按
    ``spec.count`` 循环逐条入队(数量单一源 = 注册表 count 字段,禁
    效果体闭包另写字面;default 1 与单次入队逐位一致 = 既有卡零扰动),
    同拍多条目逐条独立倒计时/到点独立发放。效果串 = 原语返回值
    ``strategy_grant_scheduled:<item>@<节拍>`` 逐条枚(构造点唯一住链
    模块,本工厂零字面量);零即时腿零 equip_grant 串。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿两腿工厂先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            queue_delayed_strategy_grant,
        )
        _ = rng   # 登记腿零采样,倒计时推算确定(rng 形参沿分派契约保留)
        spec = STRATEGY_DELAYED_GRANTS[name]
        return [queue_delayed_strategy_grant(gs, name, sig=sig)
                for _entry in range(spec.count)]

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
# ===== (rand=False) 入席,落位/回调/升星/席满溢出全沿链现役;名单值形 =
# ===== (发放角色, 发放只数),只数 = 卡面明写结构值缺省 1,工厂逐次发放;
# ===== 现役成员 = 溜佩佩/溜佩佩+(族首落)/招财狗/艾丝妲的猛犬!(佩佩族)/
# ===== 狸职手续(狸职狸狸×3,召唤临时工),后继卡 +1 行复用本表)=====

#: 具名角色发放名单单一源(卡规范名 → (发放角色, 发放只数);登记面镜像 =
#: cw_investments.STRATEGY_GRANTS 对应卡 chars_immediate——只数不进登记,
#: 估值档位按「角色是否被候选终局阵容使用」判档与只数无关——一致性测试
#: 逐对相等,箱腿 _STRATEGY_BOX_GRANTS 同构)。注册表条目由下方工厂从
#: 本表生成,禁另写字面量(表与效果体两处独立字面量的漂移在备战断言
#: 不可见,箱腿 A4 教训同纪律)。
_STRATEGY_CHAR_GRANTS: dict[str, tuple[str, int]] = {
    '溜佩佩': ('佩佩', 1),
    '溜佩佩+': ('佩佩', 1),
    '招财狗': ('佩佩', 1),
    # 艾丝妲的猛犬!(卡文「获得一个穿戴【穿刺死棘之枪】的【佩佩】」):
    # 发放对象 = 佩佩(佩戴腿零建模 = 用户裁定 2026-10-15 环境侧同判,
    # 披露键 strategy_worn_equip_unmodeled 申报;枪战斗数值归装备注册表
    # 在册单一源)。
    '艾丝妲的猛犬！': ('佩佩', 1),
    # 狸职手续(卡文「获得3个穿着1件简易装备的【狸狸】」):发放对象按
    # 实机录名归一 = 狸职狸狸(cw_chars 该员 source 注记逐字辖本卡,卡面
    # 用名「狸狸」∉ CHARACTER_ROSTER),只数 3 = 卡面明写;穿戴句与周期
    # 离场句零建模 = cw_investments.STRATEGY_DESC_UNMODELED_KEYS 两键
    # 申报;同名三连发触发链现役合成级联如实记账(见工厂 docstring)。
    '狸职手续': ('狸职狸狸', 3),
}


def _make_char_grant_effect(char: str, count: int = 1) -> Callable[..., list[str]]:
    """具名角色发放效果体工厂(闭包销 = 发放角色名 + 发放只数,单源取自
    :data:`_STRATEGY_CHAR_GRANTS`;形态镜像 _make_box_grant_effect,
    差异 = 发放对象是角色,走 gain_character)。

    签名沿现役效果体 ``(gs, *, sig, rng)``(注册表分派统一传参,
    cw_gain_chain.on_strategy_gained);``rng`` 不消费——具名确定发放
    (rand=False,gain-chain.md §5:卡文无随机词、选卡确认 = 确定性入口)。
    发放只数 = count(卡面明写结构值,如「获得3个」),循环逐次发放,
    每发独立过一遍落位/回调/升星判断/席满溢出链语义。
    星级实参恒 1 = 占位非先验:佩佩/狸职狸狸系 cost0 系统召唤单位无星级
    概念(cw_chars 在册),链签名必填星参落占位值,环境侧佩佩发放已立同判。
    落位/回调/升星/席满溢出语义全部沿 gain_character 现役,零新增链为。
    效果串 ``char_grant:<名>(placed=<bool>,merge=<int>)`` 逐发一条——
    前缀独立分域(box_grant=占席道具/named_equip_grant=装备/strategy_gift_
    random=随机角色群发),审计可独立过滤;merge = 该次获得链上升星级数
    (单发卡恒 0;count>1 同名连发凑三触发链现役合成级联,触发串
    merge>0 随串留证——链上如实记账,sim 交付态与实拍召唤单位多只共存
    的分歧由本串留证申报,零特判)。"""

    def _effect(gs: GameState, *, sig: ChannelSig,
                rng: random.Random) -> list[str]:
        # 惰性 import 链原语(运行时解析破环;沿骇客/箱腿先例,模块
        # docstring import 方向声明)
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            gain_character,
        )
        _ = rng   # 具名确定发放,无采样面(rng 形参沿注册表分派契约保留)
        steps: list[str] = []
        for _i in range(count):
            r = gain_character(gs, char, 1, rand=False, sig=sig,
                               evidence='pick_invest_char_grant',
                               producer=_PRODUCER)
            steps.append(
                f'char_grant:{char}(placed={r.placed},merge={r.merge_levels})')
        return steps

    return _effect


#: 延时发放族两腿成员(卡文「获得1个【X】，N个节点后…」带即时短句的
#: 已注册卡 → PICK_INVEST_EFFECTS 内两腿工厂派生;卡文纯延时单句的注册卡
#: 不入本集,走注册表内显式单行登记延时-only 载体——全表无差别派生会
#: 错发即时腿。新展开卡注册 = 本集扩员或单行登记二选一随批显式做,漏做
#: 由 PICK_INVEST_EFFECTS 键集闭集锁注册即红兜住)
_STRATEGY_DELAYED_TWO_LEG_GRANTS: tuple[str, ...] = ('人才激励', '人才激励+')

PICK_INVEST_EFFECTS: dict[str, Callable[..., list[str]]] = {
    '骇客专家:银狼': _apply_effect_hacker_wolf,
    **{name: _make_box_grant_effect(item)
       for name, item in _STRATEGY_BOX_GRANTS.items()},
    **{name: _make_reinforcement_effect(pairs)
       for name, pairs in _STRATEGY_REINFORCEMENT_GRANTS.items()},
    **{name: _make_random_equip_effect(cat, n)
       for name, (cat, n) in _STRATEGY_RANDOM_EQUIP_GRANTS.items()},
    # 买彩票+ = 双腿组合展开卡(卡文「获得1个随机星徽和1个【冶金炉】。」,
    # 随机腿×具名腿双族交叉):直书登记行(非表生成),不入随机装备泛化表
    # (同名键 dict 顺序覆盖丢腿)、不入具名装备授予族(该族无表,工厂直呼);
    # 腿序 = 卡文语序随机腿先/具名腿后,腿参数在此单次出现(单一源);rng
    # 恰消费 1 次(仅腿1 采样,腿2 具名确定发放零采样面);冶金炉 ∉ 精密
    # 金面判据映射(gate 恒 None)走纯发放循环。
    '买彩票+': _compose_grant_legs(_make_random_equip_effect('星徽', 1),
                                   _make_named_equip_grant_effect('冶金炉', 1)),
    # 五百强 = 双具名组合登记行(卡文「立即获得【折叠小刀】、【和平手枪】。」,
    # 具名腿×具名腿):同卡两件不同具名、条件金腿(首次 500 强度 +30 金)零
    # 建模归属型③、获得零级联;两件 ∉ 精密金面判据映射(gate 恒 None)走纯
    # 发放循环,零随机面(rng 不消费);腿序 = 卡文语序。
    '五百强': _compose_grant_legs(_make_named_equip_grant_effect('折叠小刀', 1),
                                  _make_named_equip_grant_effect('和平手枪', 1)),

    # 广聚天下英才 = 全员同费档直书登记行(卡文「获得所有2费角色各一个。」,
    # 池 = chars_by_cost(2) 注册表派生全集,静态池含专家——策略侧发放族
    # 家族口径,披露键承载改判挂点;零随机面 rng 不消费;不入泛化随机表——
    # 同名键 dict 顺序覆盖丢腿,本卡全员确定发放非采样)。
    '广聚天下英才': _make_all_cost_chars_effect(2),

    # 欢愉星徽 = 具名装备×具名角色双腿组合登记行(卡文「获得1个【欢愉星徽】，
    # 和1个【绯英】。」):腿1 星徽 = 具名确定发放(rand=False——策略卡侧
    # 具名腿通道归属,fields.md §3.2.15 族级分野注记禁跨通道对齐);腿2
    # 绯英 = 具名角色发放(char_grant: 前缀,星级 1 占位非先验);两腿 ∉
    # 精密金面判据映射(gate 恒 None)走纯发放循环;腿序 = 卡文语序。
    '欢愉星徽': _compose_grant_legs(_make_named_equip_grant_effect('欢愉星徽', 1),
                                   _make_char_grant_effect('绯英')),

    # 列车同行星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 丹恒·饮月 1★——卡文
    # 无星级词,1★ 先验家族口径,T-203 星级披露键同源)。
    '列车同行星徽': _compose_grant_legs(_make_named_equip_grant_effect('列车同行星徽', 1),
                                    _make_char_grant_effect('丹恒·饮月')),

    # 银河学者星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 艾丝妲 1★ 先验家族
    # 口径)。
    '银河学者星徽': _compose_grant_legs(_make_named_equip_grant_effect('银河学者星徽', 1),
                                    _make_char_grant_effect('艾丝妲')),

    # 贝洛伯格星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 希儿 1★ 先验家族
    # 口径)。
    '贝洛伯格星徽': _compose_grant_legs(_make_named_equip_grant_effect('贝洛伯格星徽', 1),
                                    _make_char_grant_effect('希儿')),

    # 星间旅人星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 银枝 1★ 先验家族
    # 口径)。
    '星间旅人星徽': _compose_grant_legs(_make_named_equip_grant_effect('星间旅人星徽', 1),
                                    _make_char_grant_effect('银枝')),

    # 仙舟星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 藿藿 1★ 先验家族
    # 口径)。
    '仙舟星徽': _compose_grant_legs(_make_named_equip_grant_effect('仙舟星徽', 1),
                                    _make_char_grant_effect('藿藿')),

    # 狼狩星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 椒丘 1★ 先验家族
    # 口径)。
    '狼狩星徽': _compose_grant_legs(_make_named_equip_grant_effect('狼狩星徽', 1),
                                    _make_char_grant_effect('椒丘')),

    # 盛会之星星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 花火 1★ 先验家族
    # 口径)。
    '盛会之星星徽': _compose_grant_legs(_make_named_equip_grant_effect('盛会之星星徽', 1),
                                    _make_char_grant_effect('花火')),

    # 昼之半神星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 风堇 1★ 先验家族
    # 口径)。
    '昼之半神星徽': _compose_grant_legs(_make_named_equip_grant_effect('昼之半神星徽', 1),
                                    _make_char_grant_effect('风堇')),

    # 夜之半神星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 万敌 1★ 先验家族
    # 口径)。
    '夜之半神星徽': _compose_grant_legs(_make_named_equip_grant_effect('夜之半神星徽', 1),
                                    _make_char_grant_effect('万敌')),

    # 命运圣杯星徽 = 具名装备×具名角色双腿组合登记行(卡文语序徽→人;
    # 腿1 rand=False 策略卡侧具名腿通道归属;腿2 远坂凛 1★ 先验家族
    # 口径;星级点双套 need_star=1 旁证 = 族内最强档)。
    '命运圣杯星徽': _compose_grant_legs(_make_named_equip_grant_effect('命运圣杯星徽', 1),
                                    _make_char_grant_effect('远坂凛')),
    # 精密拆装·银 = 双腿组合展开卡(卡文「获得1个【精密拆装扳手】。获得1个
    # 随机简易武装。」,具名腿×随机腿双族交叉):直书登记行(非表生成),不入
    # 随机装备泛化表(同名键 dict 顺序覆盖丢腿)、不入具名装备授予族(该族无
    # 表,工厂直呼);腿序 = 卡文语序具名腿先/随机腿后,腿参数在此单次出现
    # (单一源);rng 恰消费 1 次(仅腿2 采样,腿1 具名确定发放零采样面);
    # 「随机简易武装」= 同 '简易' 池(类别词表无「简易武装」第二候选,家族
    # 在册先例 = 打捞人才库+/武装支援/自由市场/枪在手+/公司军火更新·金);
    # 精密拆装扳手 ∉ 精密金面判据映射(gate 恒 None)走纯发放循环——本卡
    # 发放精密自身,二次持有照常入栏零自我拦截(金面规则只辖「再获得拆装
    # 扳手」)。
    '精密拆装·银': _compose_grant_legs(
        _make_named_equip_grant_effect('精密拆装扳手', 1),
        _make_random_equip_effect('简易', 1)),
    # 武装支援 = 双腿混发组合卡(卡文「获得1件随机简易装备和2个随机3费
    # 角色。」):直书登记行(非表生成),不入援军/随机装备两族表
    # (入表 = 表生成的单腿效果体与组合体同名键顺序覆盖丢腿);腿序 =
    # 卡文语序装备腿先/角色腿后,腿参数在此单次出现(单一源)。
    '武装支援': _compose_grant_legs(_make_random_equip_effect('简易', 1),
                                    _make_reinforcement_effect(((3, 2),))),
    # 武装支援+ = 三腿分层组合卡(卡文「获得1件随机简易装备和1个随机4费
    # 角色，获得6金币。」):效果体双腿同上(装备腿先/角色腿后,4 费池
    # 放回抽 1);金腿分层 = STRATEGY_ECONOMY 注册行(instant_gold=6)在册
    # 承载,金面禁直写不进效果体(sim 金发放写端缺口归 T-112 族级待办);
    # 不入两族表同上(同名键顺序覆盖丢腿)。
    '武装支援+': _compose_grant_legs(_make_random_equip_effect('简易', 1),
                                     _make_reinforcement_effect(((4, 1),))),
    # 大扩招 = 变量计数随机角色腿 + 具名装备腿组合卡(卡文「每损失4金币,
    # 获得一个随机4费角色，最多扣除40金币。获得1个【完美投影仪】」):
    # 直书登记行(非表生成——援军族表载常量名数,本卡发放只数按拿卡拍
    # 持金现算,表形 (费用档, 名数) 装不下变量计数,专用效果体直书);
    # 腿序 = 卡文语序随机角色腿先/具名腿后,腿参数在此单次出现(单一源)。
    # 扣金腿不入本效果体:金面禁逻辑直写,扣金归 sim 选卡落地拍负腿
    # 世界真值(live 游戏自扣观察覆盖);+16 金腿 = STRATEGY_ECONOMY 注册
    # 行 instant_gold=16 在册承载,发放写端缺口维持族级待办。
    '大扩招': _compose_grant_legs(_apply_effect_recruit_drain,
                                   _make_named_equip_grant_effect(
                                       '完美投影仪', 1)),
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
    # 星星相印 = 具名装备授予族后继(卡文「立刻获得1个【员工投影仪】」):
    # 直书登记行直呼工厂;员工投影仪 = 工具类装备(cw_equipment_data
    # category='工具'),归 equips 装备库存域禁入占席道具通道,不在精密
    # 金面判据映射内(gate 恒 None)走纯发放循环;获得零级联
    # (∉ EQUIP_ACQUIRE_CONSEQUENCES)。卡文前半句合成金腿 = STRATEGY_
    # EFFECTS ON_MERGE 条目 + 合成事件发放腿另路(kernel),两腿异族,
    # 本行只辖装备句。
    '星星相印': _make_named_equip_grant_effect('员工投影仪', 1),
    # 小复制 = 具名装备授予族后继(卡文「获得2个【员工投影仪】。获得7金
    # 币。」,cw_invest_data.py:116):直书登记行直呼工厂;员工投影仪 =
    # 工具类装备(cw_equipment_data category='工具'),归 equips 装备库存域
    # 禁入占席道具通道,不在精密金面判据映射内(gate 恒 None)走纯发放循环;
    # 获得零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES);同物 ×2 = 族内首例
    # (同物 ×1 先例 = 星星相印),count=2 循环逐件一条(全员晋升拆装扳手
    # ×2 同款语义);金腿「获得7金币」= STRATEGY_ECONOMY instant_gold=7
    # 在册承载,金面禁直写不进效果体,写端缺口归 T-112 族级待办。
    '小复制': _make_named_equip_grant_effect('员工投影仪', 2),
    # 小复制+ = 具名装备授予族后继(卡文「获得2个【员工投影仪】。获得13
    # 金币。」,cw_invest_data.py:117):直书登记行直呼工厂;员工投影仪 =
    # 工具类装备(cw_equipment_data category='工具'),归 equips 装备库存域
    # 禁入占席道具通道,不在精密金面判据映射内(gate 恒 None)走纯发放循环;
    # 获得零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES);同物 ×2(姊妹小复制同款,
    # 两腿同构双卡,唯一差异 = 金腿数值 7/13);金腿「获得13金币」=
    # STRATEGY_ECONOMY instant_gold=13 在册承载,金面禁直写不进效果体,
    # 写端缺口归 T-112 族级待办。
    '小复制+': _make_named_equip_grant_effect('员工投影仪', 2),
    # 赌神·银 = 具名装备授予族后继(卡文「获得一个【随便骰子】。」,
    # cw_invest_data:88):直书登记行直呼工厂;随便骰子 = 进阶类装备
    # (cw_equipment_data category='进阶'),归 equips 装备库存域禁入
    # 占席道具通道,不在精密金面判据映射内(gate 恒 None)走纯发放循环;
    # 获得零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES)。
    '赌神·银': _make_named_equip_grant_effect('随便骰子', 1),
    # 无害垃圾 = 具名装备授予族后继(卡文「获得一个【垃圾袋】并获得8
    # 金币。」,cw_invest_data.py:97):直书登记行直呼工厂;垃圾袋 = 特殊类
    # 普通可穿件(cw_equipment_data.py:56 category='特殊';wear_rules 件级
    # 专属门名单无它 = 全角色通用,穿戴面零涉),归 equips 装备库存域禁入
    # 占席道具通道,不在精密金面判据映射内(gate 恒 None)走纯发放循环;
    # 获得零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES);金腿「并获得8金币」=
    # STRATEGY_ECONOMY instant_gold=8 在册承载,金面禁直写不进效果体,
    # 写端缺口归 T-112 族级待办。
    '无害垃圾': _make_named_equip_grant_effect('垃圾袋', 1),
    **{name: _make_char_grant_effect(char, count)
       for name, (char, count) in _STRATEGY_CHAR_GRANTS.items()},
    # 绑定型随机角色授予族(价值投资·金 = 族首例,卡文「获得1个随机的
    # 2星1费角色。每次进入新节点时,获得1星的该角色,补给后额外获得2个」):
    # 生成式注册条由工厂自 _STRATEGY_CHAR_GRANT_BINDINGS 生成(表与效果体
    # 禁两处字面量,援军族同纪律);获得时点腿 = 采样发放 + sim 门控写
    # 绑定域,每节点复制腿归 sim 节点窗收口(check_strategy_node_char_
    # grants),两腿分治。
    **{name: _make_bound_char_grant_effect(name, *spec)
       for name, spec in _STRATEGY_CHAR_GRANT_BINDINGS.items()},
    **{name: _make_delayed_offer_effect(name)
       for name in STRATEGY_DELAYED_OFFERS},
    **{name: _make_delayed_grant_effect(name)
       for name in _STRATEGY_DELAYED_TWO_LEG_GRANTS},
    # 许诺特权 = 延时-only 单腿展开卡首例(卡文「在进入7个节点后，获得
    # 1个【特权武装箱】。」纯延时单句,零即时腿):显式单行登记延时-only
    # 载体;效果串单枚 strategy_grant_scheduled(构造点住链原语)。
    '许诺特权': _make_delayed_only_grant_effect('许诺特权'),
    # 先亏后盈 = 延时-only 单腿展开卡后继(卡文「损失20点小队生命值，
    # 4个节点后获得2个【简易武装箱】。」混合形):登记腿只辖延时句,
    # count=2 循环入队两枚效果串;伴随损血腿不入登记效果体——kernel 无
    # hp 轨迹追加可调,链内写 hp 破「hp 写流 ↔ hp_trail 全序同构」不变
    # 式,损血腿结构性只能在 sim 通道(apply_strategy_pick_hp 负值支),
    # 本行零 hp 写防将来误并。
    '先亏后盈': _make_delayed_only_grant_effect('先亏后盈'),
    # 好运令牌·银 = 延时-only 单腿展开卡(卡文「进入3个节点后，获得
    # 1个【好运令牌】。」纯延时单句,零即时腿):显式单行登记延时-only
    # 载体,效果串单枚 strategy_grant_scheduled(构造点住链原语);
    # 发放物「好运令牌」与卡名异名(族内首例,物名单源住注册表 item);
    # 禁入两腿成员集(入集 = 拿卡错发即时装备腿)。
    '好运令牌·银': _make_delayed_only_grant_effect('好运令牌·银'),
    # 是钻石总会发光 = 延时-only 单腿展开卡 + 族内首个随机发放行(卡文
    # 「2个节点后，获得【红钻】或【蓝钻】。」纯延时单句,零即时腿):
    # 显式单行登记延时-only 载体;效果串 choice-set 形
    # strategy_grant_scheduled:红钻|蓝钻@2(item 段 = 封闭集竖线连接,
    # 单一构造点住链原语按 item or '|'.join(item_choices) 取段,本工厂
    # 零字面量);登记腿零采样(掷骰时点 = 到点发放窗现掷,拿卡入队
    # 预掷被否:队列只存卡名,live 队列不携永不兑现的预掷值);
    # 禁入两腿成员集(入集 = 拿卡错发即时装备腿)。
    '是钻石总会发光': _make_delayed_only_grant_effect('是钻石总会发光'),
}
"""策略卡获得效果注册表(键 = 注册表规范名;骇客单行自 pick_invest.py 迁入,
开箱分支五条由工厂自 _STRATEGY_BOX_GRANTS 生成,援军族由工厂自
_STRATEGY_REINFORCEMENT_GRANTS 生成,随机装备族由工厂自
_STRATEGY_RANDOM_EQUIP_GRANTS 生成(泛化 (category, count) 行,池 =
装备注册表按类别派生),组合卡(买彩票+/武装支援/武装支援+/
精密拆装·银/大扩招)直书登记行
由组合子组合双腿(非表生成),具名装备授予族(全员晋升/无伤通关/星星相印/
小复制/小复制+/赌神·银/无害垃圾)直书登记行由
_make_named_equip_grant_effect 生成闭包,具名角色发放族(溜佩佩/溜佩佩+/
招财狗/艾丝妲的猛犬!/狸职手续,名单值形 (发放角色, 发放只数))由工厂自
_STRATEGY_CHAR_GRANTS 生成,策略延时 offer 族由工厂自
cw_investments.STRATEGY_DELAYED_OFFERS 派生,策略延时发放族按卡文句式
分流:带即时短句的成员经两腿成员集走两腿工厂派生,纯延时单句卡显式单行
登记延时-only 载体(直用两腿工厂 = 拿卡错发即时腿)——新展开卡注册随批
二选一显式登记,键集封闭断言守住两表面零漂移)。未收录名 = 零效果分派
(查无效果安静不写,真值归观察覆盖)。与 STRATEGY_EFFECTS(经济聚合面)
职责分离声明见各表模块头。"""
