"""环境条件发放:连胜/刷新次数触发检查 kernel 函数 + 宝钻获得回调(live/sim 同一单一源)。

迭代 2026-10-10-env-conditional-grants(kernel 面,详设 =
docs/develop/sr_od/application/currency_war/changes/
2026-10-10-env-conditional-grants/details/env-conditional-grant.md §1–§4;
接线归该迭代 landing 3.2(live)/3.3(sim),本模块零接线)。

为什么 kernel 单一函数(live 与 sim 都调它):结算 streak 真值链两端
同构(live = 结算覆盖写端 apply_settlement_cover 落账,sim = 结算腿
observe 落账),条件判定散落两处各写一份 = 漂移(同 ``roll_ore_reward``
live/sim 共用的单一正确性来源理由,非「通用复用」)。

通道分工(硬约束,依据 = ``cw_game_state.write_logic_rand`` docstring:

- 装备发放:财富宝钻到达的**库存落位不可观察**(装备进哪个穿戴位是
  游戏侧决定)→ :meth:`GameState.write_logic_rand` 可能世界快照;
  ``equips`` 是观察域(owned_equips 识别器整表覆盖),下一备战帧差异
  = 随机效果落地(logic_rand_outcome 台账行)自动纠偏,零持续污染;
- done 追加:登记事实,:meth:`GameState.write_logic` 直写(直写先例 =
  cw_exec_state 金腿 / cw_effect_inventory 退款腿,不属 anchor_aware
  族——本域无观察写端,登记恒真);两笔同 sig 相邻 = 同窗原子语义面;
- 回调三写(diamond_count/deploy_cap/back_layout):sim 世界数值面,
  全部 :meth:`GameState.observe`(先例 = ``_on_supply_picked`` 的
  diamond_count observe 写);**live 不调回调**——三域 live 写端 =
  观察识别器,逻辑侧禁写(投影审计在册)。

**sig 单形态**(禁 obs_sig 进触发函数)::func:`check_env_streak_grants`
的 ``sig`` 入参必须是 logic_action / logic_hook 族(obs 族进
write_logic_rand 即炸渠道族校验);live = logic_hook 族 group
'battle-wait:env-grant',sim = ``logic_sig('sim:env')``——形态归两端
接线(3.2/3.3),本模块不指定。回调 sig 由 :func:`on_diamond_acquired`
内部自构 obs 族(observe 渠道校验只收 obs 族,复用调用方 logic 族
入参首笔即炸),入参不传 sig。

**无 rng**:随机态指认知通道(落位未知、观察校准),追加位置(库存
尾部)确定,不消耗随机数。

边界披露(显式接受,详设 §3 同名节):①同窗洗白——发放后同窗口的
确定性 equips 写会把字段来源翻成纯 logic,下一 heavy 帧观察对 logic
源失配走安灯(值由观察采新,续跑即愈);②恢复局——接管局 done 为
空,首个 streak ≥ 阈值结算触发发放 = 最佳猜测;③OCR 假阳——假发放
永久占据一次性(done 不回收)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    CounterKey,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    DEPLOYED_BACK_CAPACITY_MAX,
    ChannelSig,
    GameState,
    back_capacity_of,
    level_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_REFRESH_GRANTS,
    ENV_STREAK_GRANTS,
)

#: 触发函数两写(发放/done)的写入者标识(journal/台账过滤键)。
_PRODUCER: str = 'env_conditional_grant'

#: done 域条件键:具名触发器「本局首次连胜达成」(当前唯一形状;
#: 升级类条件键各建各表各函数,不进本模块)。
FIRST_STREAK_KEY: str = 'first_streak'

#: done 域条件键:刷新次数阈值触发器(每环境至多一个刷新触发器,
#: (env, 本键) 天然唯一)。
REFRESH_THRESHOLD_KEY: str = 'refresh_threshold'

#: 回调三写证据串(判读可辨;刻意不带 ``sim:engine`` 前缀——该前缀是
#: 失配抑制登记面,语义 = sim 后端世界腿外部事件写,回调写不属该族)。
_DIAMOND_EVIDENCE: str = 'env_diamond'

#: 财富宝钻注册名(回调 cap 加成语义唯一适用装备;官方条目「拥有宝钻
#: 可以使团队规模上限 +1」= cw_equipment_data 财富宝钻行。字面量先例 =
#: cw_effect_inventory 贡献算术同款引用)。
_RICH_DIAMOND: str = '财富宝钻'

#: 回调三写的渠道签名(kernel 内构 obs 族;observe 渠道校验只收 obs 族)。
#: group_id 按详设 §4 指定形态 'sim:env-diamond'(三写同组 = 同窗事实)。
#: actor = 具名写入者(本回调),不引 sim 侧 ``SIM_ENGINE_ACTOR``——
#: kernel→sim 模块级反向边禁止(sim 依赖 kernel,反向即环)。
_DIAMOND_SIG: ChannelSig = ChannelSig(family='obs', actor='EnvDiamondGrant',
                                      mode='synthesized',
                                      group_id='sim:env-diamond')


def check_env_streak_grants(gs: GameState, streak_after: int,
                            sig: ChannelSig) -> str | None:
    """结算连胜条件发放触发检查(单一源;调用点 = streak 落账之后,
    live = ``apply_settlement_cover`` 结算覆盖调用点后 / sim = 结算腿
    streak observe 后,接线归 3.2/3.3)。

    条件矩阵(顺序即短路序,详设 §3):逐序返回 None = 未发放:

    1. 当前环境(active_env)None/空链 → None;
    2. 环境不在登记表(ENV_STREAK_GRANTS)→ None;
    3. ``streak_after <= 0``(连败/零方向,带符号口径)→ None;
    4. ``streak_after < 阈值`` → None;
    5. ``(env, first_streak) ∈ done 现值 → None``(已发;done None →
       视为空防御,沿 ore 通道 ``value or ()`` 先例);
    6. ``equips`` 现值 None(从未观察)→ **None 且不标 done**——宁缺
       勿造,条件每结算重查,下个结算自动重试(与晶矿生成集「下帧
       再试」同性质);
    7. 达标 → 发放:equips 尾部追加(write_logic_rand,evidence
       ``env_grant#<env>#streak<阈值>``)+ done 追加(write_logic,
       同 evidence 同 sig,两笔相邻),返回被发装备名(调用方据此
       决定是否调宝钻回调——sim 专用,live 忽略返回值)。

    - ``sig`` = 两写共用的渠道签名,必须 logic_action / logic_hook 族
      (obs 族即炸渠道族校验——禁 obs_sig,详设 §5 sig 单形态);
    - 本函数零 rng:随机态指认知通道,追加位置(尾部)确定。
    """
    env = gs.active_env.value
    if not env:
        return None
    grant = ENV_STREAK_GRANTS.get(env)
    if grant is None:
        return None
    if streak_after <= 0:
        return None
    threshold, equip_name = grant
    if streak_after < threshold:
        return None
    done = tuple(gs.env_grants_done.value or ())
    if (env, FIRST_STREAK_KEY) in done:
        return None
    base = gs.equips.value
    if base is None:
        # 库存从未观察:发放写出不完整库存 = 丢件,宁缺勿造不标 done
        # (下个结算 equips 已读后自动重试;done 只在发放同窗登记)
        return None
    evidence = f'env_grant#{env}#streak{threshold}'
    gs.write_logic_rand(gs.equips, list(base) + [equip_name],
                        produced_by=_PRODUCER, evidence=evidence, sig=sig)
    gs.write_logic(gs.env_grants_done,
                   done + ((env, FIRST_STREAK_KEY),),
                   produced_by=_PRODUCER, evidence=evidence, sig=sig)
    return equip_name


def check_env_refresh_grants(gs: GameState, sig: ChannelSig) -> str | None:
    """刷新次数条件发放触发检查(单一源;唯一调用点 = 刷新上报函数
    ``report_action_refresh_shop_param`` 尾部,第 N 次刷新动作窗内,
    live/sim 同一段 op 代码同口覆盖)。

    条件矩阵(顺序即短路序,逐序返回 None = 未发放):

    1. 当前环境(active_env)None/空链 → None;
    2. 环境不在登记表(ENV_REFRESH_GRANTS)→ None;
    3. ``(env, refresh_threshold) ∈ done 现值 → None``(已发,一次性
       封账;done None 视为空防御,沿 streak 通道 ``value or ()`` 先例);
    4. 计数现值 < 阈值 → None(计数键按登记表分支读
       ``gs.effects.refresh_total/refresh_paid``——两者是 EffectsInventory
       的 int 属性,``record_refresh`` 直加;计数语义单一源 =
       EffectsInventory.record_refresh docstring,本函数不复制口径注释);
    5. ``gs.gold.value`` None(从未观察)→ **None 且不标 done**——宁缺
       勿造,刷新是备战期高频动作,下次刷新自动重查(重试延迟以秒计);
    6. 装备腿非 None 且 ``gs.equips.value`` None → 同 5(缺任一承载
       即整体缓发,禁半发放——半发放 = 金已入账装备永久漏发);
    7. 达标 → 发放,**三笔相邻写同 evidence、同 sig、同 produced_by**
       (同窗原子语义面,与 streak 通道同纪律):
       - 金:``gs.write_logic(gs.gold, 现值 + 金)``;
       - 装备(仅装备腿非 None):``gs.write_logic_rand(gs.equips,
         现值尾部追加装备名)``——装备库存顺序是游戏侧决定,模型无
         顺序观察锚 → 随机态通道(宝钻同族先例);
       - done:``gs.write_logic(gs.env_grants_done, 现值 +
         ((env, REFRESH_THRESHOLD_KEY),))``;
       返回被发装备名(装备腿 None 的金-only 发放也返回 None——返回值
       仅日志面消费,员工投影仪无宝钻式世界数值回调,无行为分支)。

    - ``sig`` = 三笔共用的渠道签名,必须 logic_action 族(obs 族进
      write_logic_rand 即炸渠道族校验)。唯一调用方传入上报函数内部的
      ``_grp_sig``(logic_action 族,上报入口已把族锁死),天然满足;
      logic_hook 分支本案不可达,不写分支(T-5 live 结算接线形态,
      本案收敛点唯一);
    - 本函数零 rng:随机态指认知通道,追加位置(尾部)与金增量均确定,
      不消耗随机数。
    """
    env = gs.active_env.value
    if not env:
        return None
    grant = ENV_REFRESH_GRANTS.get(env)
    if grant is None:
        return None
    count_key, threshold, gold_amount, equip_name = grant
    done = tuple(gs.env_grants_done.value or ())
    if (env, REFRESH_THRESHOLD_KEY) in done:
        return None
    count = (gs.effects.refresh_total if count_key == CounterKey.REFRESH_TOTAL
             else gs.effects.refresh_paid)
    if count < threshold:
        return None
    gold_now = gs.gold.value
    if gold_now is None:
        # 金从未观察:发放金写出不完整账 = 断言无据,宁缺勿造不标 done
        # (下次刷新自动重查;done 只在发放同窗登记)
        return None
    if equip_name is not None and gs.equips.value is None:
        # 装备库存从未观察:缺任一承载即整体缓发(禁半发放)
        return None
    evidence = f'env_grant#{env}#refresh{threshold}'
    gs.write_logic(gs.gold, int(gold_now) + gold_amount,
                   produced_by=_PRODUCER, evidence=evidence, sig=sig)
    if equip_name is not None:
        gs.write_logic_rand(gs.equips, list(gs.equips.value) + [equip_name],
                            produced_by=_PRODUCER, evidence=evidence, sig=sig)
    gs.write_logic(gs.env_grants_done,
                   done + ((env, REFRESH_THRESHOLD_KEY),),
                   produced_by=_PRODUCER, evidence=evidence, sig=sig)
    return equip_name


def on_diamond_acquired(gs: GameState, equip_name: str) -> None:
    """宝钻获得回调(世界数值面联动;唯一调用点 = sim 深井发放路径,
    3.3 接线;**supply 补给宝钻不采纳**——钻类型未建模,归 3.3 辖;
    **live 不调**——三域 live 写端 = 观察识别器,逻辑侧禁写)。

    - ``equip_name != '财富宝钻'`` → 直接返回(cap 加成语义只属财富
      宝钻;红/蓝钻是补给视觉族同框,无 cap 语义——依据 cw_obs_core
      ``DIAMOND_EQUIP_NAMES`` 仅视觉判定族);
    - 三写全部 :meth:`GameState.observe`(sim 世界事实 = 观察通道,
      禁 logic 写——与晶矿 done 台账的直写不同,那是登记事实,这是
      世界数值面),sig 由本函数内部自构 obs 族(入参不传 sig——
      observe 渠道校验只收 obs 族,复用调用方 logic 族入参首笔即炸;
      内构先例 = ``_on_supply_picked`` 内构 ``obs_sig('sim:diamond')``):
      1. ``diamond_count`` 现值 + 1(宝钻族均计数);
      2. ``deploy_cap`` = level + equips 现值中财富宝钻计数(拥有即算、
         可叠加,D-53 实测口径;发放同窗已把新宝钻写入现值);
      3. ``back_layout`` = min(9, 现值 + 1)(值域 6-9;现值 None → 以
         机制基线 6 起算 = 后排格数读口缺省,种子后不可达防御)。
    """
    if equip_name != _RICH_DIAMOND:
        return
    diamond_after = int(gs.diamond_count.value or 0) + 1
    gs.observe(gs.diamond_count, diamond_after,
               evidence=_DIAMOND_EVIDENCE, sig=_DIAMOND_SIG)
    inv = gs.equips.value or []
    cap_after = level_of(gs) + sum(1 for e in inv if e == _RICH_DIAMOND)
    gs.observe(gs.deploy_cap, cap_after,
               evidence=_DIAMOND_EVIDENCE, sig=_DIAMOND_SIG)
    back_after = min(DEPLOYED_BACK_CAPACITY_MAX, back_capacity_of(gs) + 1)
    gs.observe(gs.back_layout, back_after,
               evidence=_DIAMOND_EVIDENCE, sig=_DIAMOND_SIG)
