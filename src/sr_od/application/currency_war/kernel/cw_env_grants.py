"""环境条件发放:连胜/刷新次数/利息累计/首领节点/合并升星/晶矿开启计数触发检查 kernel 函数 + 持续伤害契约条件腿(猜测写+证实)+ 宝钻获得回调(live/sim 同一单一源)。

迭代 2026-10-10-env-conditional-grants(kernel 面,详设 =
docs/develop/sr_od/application/currency_war/changes/
2026-10-10-env-conditional-grants/details/env-conditional-grant.md §1–§4;
接线归该迭代 landing 3.2(live)/3.3(sim),本模块零接线)。

为什么 kernel 单一函数(live 与 sim 都调它):结算 streak 真值链两端
同构(live = 结算覆盖写端 apply_settlement_cover 落账,sim = 结算腿
observe 落账),条件判定散落两处各写一份 = 漂移(同 ``roll_ore_reward``
live/sim 共用的单一正确性来源理由,非「通用复用」)。首领节点触发
(check_env_boss_grants)两端不同构(「进入首领节点」真值生产点分居
live 简报屏观察 / sim 节点窗收口,两段代码不同口)——仍归单一函数,
条件判定/done 语义不漂移,接线形态归两端调用点。

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
  观察识别器,逻辑侧禁写(投影审计已登记)。

**sig 单形态**(禁 obs_sig 进触发函数)::func:`check_env_streak_grants`
的 ``sig`` 入参必须是 logic_action / logic_hook 族(obs 族进
write_logic_rand 即炸渠道族校验);live = logic_hook 族 group
'battle-wait:env-grant',sim = ``logic_sig('sim:env')``——形态归两端
接线(3.2/3.3),本模块不指定。回调 sig 由 :func:`on_diamond_acquired`
内部自构 obs 族(observe 渠道校验只收 obs 族,复用调用方 logic 族
入参首笔即炸),入参不传 sig。

**无 rng**(逐函数标注)::func:`check_env_streak_grants` /
:func:`check_env_refresh_grants` / :func:`check_env_interest_grants` /
:func:`check_env_dot_grants`
零 rng——随机态指认知通道(落位未知、
观察校准),追加位置(库存尾部/席面落位)确定,不消耗随机数;
:func:`check_env_boss_grants` 含采样(rng 形参:角色名 ``rng.choice``
采样,缺省回退自掷 = 采样是猜测口径,live 观察校准;sim 传流键 =
世界真值);
:func:`check_env_merge_grants` 含采样(注入槽:函数内
``action_sampling_rng('env_merge_grant', None)`` 解析——四发火点跨
上报函数/效果族/链原语三类调用方,集中函数内解析单点最少;注入槽 =
sim 世界真值,回退自掷 = live 猜测口径);
:func:`check_env_ore_open_grants` 含采样(注入槽:函数内
``action_sampling_rng('env_ore_open_grant', None)`` 解析——接线点虽
在 rng 在场的采晶矿上报函数内,采样腿独立具名键使两腿流键分离,
重放归因更净;具名腿零 rng 消耗,掷名仅随机腿一笔)。

边界披露(显式接受,详设 §3 同名节):①同窗洗白——发放后同窗口的
确定性 equips 写会把字段来源翻成纯 logic,下一 heavy 帧观察对 logic
源失配走失配告警(值由观察采新,续跑即愈);②恢复局——中断恢复对局 done 为
空,首个 streak ≥ 阈值结算触发发放 = 最佳猜测;③OCR 假阳——假发放
永久占据一次性(done 不回收)。
"""
from __future__ import annotations

import random

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import chars_by_faction
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    CounterKey,
)
from sr_od.application.currency_war.kernel.cw_gain_chain import (
    GAIN_CHAIN_PRODUCER,
    _node_frame,
    gain_character,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    DEPLOYED_BACK_CAPACITY_MAX,
    BenchView,
    ChannelSig,
    GameState,
    back_capacity_of,
    level_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_BOSS_GRANTS,
    ENV_INTEREST_GRANTS,
    ENV_MERGE_GRANTS,
    ENV_ORE_OPEN_GRANTS,
    ENV_REFRESH_GRANTS,
    ENV_STREAK_GRANTS,
)

#: 触发函数两写(发放/done)的写入者标识(journal/台账过滤键)。
_PRODUCER: str = 'env_conditional_grant'

#: done 域条件键:具名触发器「本局首次连胜达成」(当前唯一形状;
#: 升级类条件键各建各表各函数,不进本模块)。
FIRST_STREAK_KEY: str = 'first_streak'

#: done 域条件键:刷新次数阈值触发器(每环境至多一个刷新触发器,
#: (env,本键) 天然唯一)。
REFRESH_THRESHOLD_KEY: str = 'refresh_threshold'

#: done 域条件键:利息累计阈值触发器(每环境至多一个,
#: (env, 本键) 天然唯一;消费注册表 = ENV_INTEREST_GRANTS)。
INTEREST_THRESHOLD_KEY: str = 'interest_threshold'

#: done 域条件键:随机星徽授予腿(键值携带发放装备名,格式
#: 'star_grant#<装备名>'——腿2 绑定解析的唯一源;# 后载荷是条件键的
#: 本卡新立扩展形态(fields.md §3.5.5 在册仅纯具名值,随本卡登记)),
#: 写端 = cw_gain_chain.on_env_gained 随机装备绑定腿(两模块分工见
#: cw_game_state.env_grants_done 字段注释)。
STAR_GRANT_KEY_PREFIX: str = 'star_grant#'

#: done 域条件键:首领节点周期发放(每节点一键,格式
#: 'boss#<位面>-<轮>';周期性 = 不同节点不同键,一次性通道的
#: (env, 键) 形状不变)。
BOSS_NODE_KEY_PREFIX: str = 'boss#'

#: 持续伤害契约条件腿的注册环境名(条件门与锚键分支共用注册名;字面量
#: 先例 = _RICH_DIAMOND 同款引用)。本卡**不入五张条件发放登记表**——
#: 建模形状不同(计数源无世界真值生产点 → 猜测写+证实,非条件检查型;
#: 反向锁测试钉住防误登记)。
DOT_CONTRACT_ENV: str = '持续伤害契约'

#: 持续伤害契约条件腿发放物注册名(猜测写/幂等守卫/证实判据共用身份)。
_DOT_CHAR: str = '黑天鹅'

#: done 域条件键:持续伤害契约条件腿证实((env, 本键) ∈ env_grants_done
#: = 已证实封账,猜测写永久短路;一次性通道既有语义——卖出后不重发,
#: done 不回收;live 证实 = 备战观察含黑天鹅即证不区分来源〔v2-5 裁定〕,
#: sim 证实 = 进度键计数达阈值)。
DOT_CONFIRM_KEY: str = 'dot_confirm'

#: done 域锚键前缀:'dot_anchor#<位面>-<轮>'(纯登记件**非门控**,写入端
#: = cw_gain_chain.on_env_gained 获得刻;开局三选一获取时 sim 节点尚未
#: 进窗不写 = 预期形态,缺锚不影响猜测写/计数/证实任何一步——键形态
#: 先例 = boss#<位面>-<轮>,载荷键登记先例 = star_grant#)。
DOT_ANCHOR_KEY_PREFIX: str = 'dot_anchor#'

#: done 域进度键前缀:'dot_battle#<k>'(k 从 1 起;append-only 逐战斗结算
#: 追加,对账可数,先例 = boss# 逐节点键;进度腿 sim 专用,live 不追加——
#: live 计数真值由现实本身决定,猜测写自愈循环每场对一次)。
DOT_BATTLE_KEY_PREFIX: str = 'dot_battle#'

#: done 域条件键:晶矿开启阈值触发器(阈值嵌键,格式 'ore_open#<阈值>';
#: 重复型通道,每阈值一键,(env, 键) 天然唯一;键形先例 = star_grant#/
#: boss# 前缀携载荷形态)。
ORE_OPEN_THRESHOLD_KEY_PREFIX: str = 'ore_open#'

#: sim 条件腿证实的战斗结算数(结论 = active_env 门真后第 8 个战斗结算
#: 追加证实;出处 = 用户拍板值 2026-10-17〔单位 = 战斗结算次数,轮锚
#: 弃用〕,**非机制推导**——180 计数在 sim 无世界真值生产点,8 是该阈值
#: 的代理口径;边界 = 样本积累后重估常量/单位均须用户拍板,计数单一源
#: = done 域 dot_battle# 键数)。
ENV_DOT_CONFIRM_BATTLES: int = 8

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
       - done:``gs.write_logic(gs.env_grants_done,现值 +
         ((env, REFRESH_THRESHOLD_KEY)))``;
       返回被发装备名(装备腿 None 的金-only 发放也返回 None——返回值
       仅日志面消费,员工投影仪无宝钻式世界数值回调,无行为分支)。

    - ``sig`` = 三笔共用的渠道签名,必须 logic_action 族(obs 族进
      write_logic_rand 即炸渠道族校验)。唯一调用方传入上报函数内部的
      ``_grp_sig``(logic_action 族,上报入口已把族锁死),天然满足;
      logic_hook 分支本案不可达,不写分支( live 结算接线形态,
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


def check_env_interest_grants(gs: GameState, sig: ChannelSig) -> str | None:
    """利息累计条件发放触发检查(单一源;调用点 = sim 收入应用两处
    ``apply_round_start_income``/扑满结算腿 + live 三来源计数刻——来源 A
    结算覆盖窗「获得金币总览」息行读数后 / 来源 B 1f 败局行写点推算后 /
    来源 C 领取补给完成刻推算后,T-27 迭代设计 §2.4/§2.5)。各收入刻
    先 ``gs.effects.record_interest_earned`` 落账再调本检查(record 先于
    check,同组相邻)。

    条件矩阵(顺序即短路序,镜像 check_env_refresh_grants):

    1. 当前环境(active_env)None/空链 → None;
    2. 环境不在登记表(ENV_INTEREST_GRANTS)→ None;
    3. ``(env, interest_threshold) ∈ done 现值 → None``(已发,一次性
       封账「累计获得40利息后获得」;done None 视为空防御,沿 streak
       通道 ``value or ()`` 先例);
    4. ``gs.effects.interest_earned < 阈值`` → None(计数单一源 =
       ActiveEffectInventory.record_interest_earned,本函数不复制口径);
    5. ``gs.bench.value`` None → None 且不标 done(宁缺勿造族;bench 为
       开局种子底座字段,冷建即 9 空槽空视图,生产域 live/sim 恒非
       None,本分支 = 直构测试域防御,且 gain_character 本体另有拒落
       防线);
    6. 达标 → **发放两笔相邻写,同 evidence、同 sig、同 produced_by**
       (同窗原子语义面,streak/refresh 通道同纪律):
       - :func:`gain_character`(发放角色, 1★ 先验族, rand=False——
         具名单名无采样,环境发放 = 确定发放,gain-chain.md §5,
         特权阶级到点发放同款);
       - done 追加 ``(env, INTEREST_THRESHOLD_KEY)``(write_logic 登记
         事实直写);
       返回发放角色名(日志面消费,无行为分支)。

    - ``sig`` = 两写共用的渠道签名,必须 logic_action / logic_hook 族
      (obs 族进写通道即炸渠道族校验——禁 obs_sig;形态归两端接线:
      sim = ``logic_sig('sim:env')``,live = logic_hook 族随宿主 op);
    - 本函数零 rng:具名单名确定发放,随机态指认知通道(落位未知、
      观察校准),不消耗随机数。
    """
    env = gs.active_env.value
    if not env:
        return None
    grant = ENV_INTEREST_GRANTS.get(env)
    if grant is None:
        return None
    threshold, char_name = grant
    done = tuple(gs.env_grants_done.value or ())
    if (env, INTEREST_THRESHOLD_KEY) in done:
        return None
    if gs.effects.interest_earned < threshold:
        return None
    if gs.bench.value is None:
        # 席面从未观察:发放角色写出不完整席 = 丢人,宁缺勿造不标 done
        # (生产不可达,开局种子底座;下个收入刻自动重查,done 只在
        # 发放同窗登记)
        return None
    evidence = f'env_grant#{env}#interest{threshold}'
    gain_character(gs, char_name, 1, rand=False, sig=sig, evidence=evidence,
                   producer=_PRODUCER)
    gs.write_logic(gs.env_grants_done,
                   done + ((env, INTEREST_THRESHOLD_KEY),),
                   produced_by=_PRODUCER, evidence=evidence, sig=sig)
    return char_name


def check_env_boss_grants(gs: GameState, *, node_pos: tuple[int, int] | None,
                          rng: random.Random | None,
                          sig: ChannelSig) -> str | None:
    """首领节点条件发放触发检查(单一源;「进入首领节点」的双端真值
    生产点分居两端 → 两点接线:live = ``CwScreenBossBriefing.
    _observe_live`` 观察上报后 best-effort 调用(hist = settle_confirm
    推进后的 boss 坐标),sim = ``cw_sim_backend._begin_node_window``
    的 boss 分支(窗口幂等守卫内)——两支天然互斥,done 短路兜第二层)。

    条件矩阵(顺序即短路序,逐序返回 None = 未发放):

    1. 当前环境(active_env)None/空链 → None;
    2. 环境不在登记表(ENV_BOSS_GRANTS)→ None;
    3. ``node_pos`` None → None(live hist 未建,坐标不可知禁猜);
    4. 坐标即入参:``node_pos`` = (位面, 轮) NodePos 二元组,拆包后
       int 归一(纯防御,两端调用点现值均为 int,转换不涉「序号反解」);
       节点序列按环境派生,本触发器收坐标入参,对序列修饰天然免疫;
    5. ``(env, 'boss#<位面>-<轮>') ∈ done 现值 → None``(本节点已发;
       同节点重复观察幂等短路;done None 视为空防御,沿 streak 通道
       ``value or ()`` 先例);
    6. done 现值无本环境 ``star_grant#`` 前缀键 → None(**绑定缺失,宁缺
       勿造**——无快照接管局腿1 不重放则绑定永久缺失,后续 boss 一律
       零写,显式接受);
    7. ``gs.bench.value`` None → None 不标 done(生产不可达,直构/测试
       形态防御;本 boss 窗一次性无自动重试 = 该节点漏发);
    8. 达标 → 发放:绑定星徽名 = 前缀键解出 → 羁绊名 = 星徽名去「星徽」
       后缀 → 池 = ``chars_by_faction(羁绊名)``(默认参数含 flows,与
       FactionInfo.members 同源)→ ``rng.choice`` 采样 →
       ``gain_character(gs, 名, 1, rand=True, sig, evidence, producer)``
       (星级 1 = 先验,晶矿 CHAR_DROP_STAR 同句式)→ done 追加 boss 键
       (write_logic,同 evidence 同 sig)——两段写同 evidence 同 sig 同
       produced_by(与 streak/refresh 通道同窗原子纪律),返回角色名
       (仅日志面消费)。池空 = 注册表漂移(构建期校验保证非空),运行期
       再空 → None 短路留 log,不标 done。

    - ``sig`` = 两写共用的渠道签名,必须 logic_action / logic_hook 族
      (obs 族即炸渠道族校验——禁 obs_sig;形态归两端接线:live =
      logic_hook 族 group 'boss-briefing:env-grant',sim =
      logic_sig('sim:env'),与环境金/定时道具发放同组同窗);
    - 本函数含采样(本模块唯一消费 rng 的触发函数):``rng`` 缺省回退
      自掷(采样是猜测口径,live 观察校准;sim 传流键 = 世界真值)。
    """
    env = gs.active_env.value
    if not env:
        return None
    if env not in ENV_BOSS_GRANTS:
        return None
    if node_pos is None:
        return None
    plane, round_num = int(node_pos[0]), int(node_pos[1])
    done = tuple(gs.env_grants_done.value or ())
    boss_key = f'{BOSS_NODE_KEY_PREFIX}{plane}-{round_num}'
    if (env, boss_key) in done:
        return None
    bind_keys = [k for e, k in done
                 if e == env and k.startswith(STAR_GRANT_KEY_PREFIX)]
    if not bind_keys:
        # 绑定缺失(腿1 未发放,典型 = 无快照接管局):宁缺勿造零写
        return None
    if gs.bench.value is None:
        # 席面从未观察:发放角色写出不完整席 = 丢人,宁缺勿造不标 done
        # (生产不可达,开局种子底座;本 boss 窗一次性,无自动重试)
        return None
    star_name = bind_keys[0][len(STAR_GRANT_KEY_PREFIX):]
    faction = (star_name[:-len('星徽')] if star_name.endswith('星徽')
               else '')
    pool = [c.name for c in chars_by_faction(faction)]
    if not pool:
        # 构建期已闸(_validate_env_gifts '星徽' 池闸 + 派生链非空),
        # 运行期再空 = 注册表漂移;零写留 log 防御分支(不标 done)
        log.warning(f'[cw-env-grants] 首领节点羁绊池空(注册表漂移?):'
                    f'{env} star={star_name!r} faction={faction!r}')
        return None
    roll_rng = rng if rng is not None else random.Random()
    name = roll_rng.choice(pool)
    evidence = f'env_grant#{env}#boss{plane}-{round_num}'
    gain_character(gs, name, 1, rand=True, sig=sig, evidence=evidence,
                   producer=_PRODUCER)
    gs.write_logic(gs.env_grants_done, done + ((env, boss_key),),
                   produced_by=_PRODUCER, evidence=evidence, sig=sig)
    return name


#: 合并升星触发发放的采样腿具名键(模块尾近函数,消费点唯一 =
#: :func:`check_env_merge_grants`)。
ENV_MERGE_GRANT_RNG_TOOL: str = 'env_merge_grant'


def check_env_merge_grants(gs: GameState, facts: tuple[tuple[str, int], ...],
                           *,
                           sig: ChannelSig) -> tuple[str, ...]:
    """合并升星触发发放检查(单一源;事件携带事实,非窗口条件,无 done
    ——每次升星事件恰好经过发火点一次,与 streak/refresh/boss 的
    「观察点重入」done 幂等场景不同型)。调用点 = 四发火点收尾(买牌
    上报/补给单位腿 grant_bench_unit_cascade/晶矿角色腿/获得链顶层
    gain_character,均在各自全部容器写毕后调用;deploy_move/pick_planner
    级联不可达不设,拷贝臂 spawn_equip_bench_unit 无级联不设——
    cw_investments.ENV_MERGE_GRANTS 区块注释)。

    条件矩阵(顺序即短路序,逐序返回空 = 零发放):

    1. 当前环境(active_env)None/空链 → 空;
    2. 环境不在登记表(ENV_MERGE_GRANTS)→ 空;
    3. facts 逐条 (char_id, new_star) 过滤触发角色集,空 → 空(rng 未
       解析:无命中不消耗采样流键,保持 sim 动作序列逐位不变);
    4. 每条命中 → 发放池内均匀采样 1 名 →
       :func:`gain_character`(名, 1★ 先验, rand=True 采样支——本函数
       恒采样,rand 固定 True 不设形参)→ 效果串一条
       ``env_merge_grant:<名>``(与落位成败解耦,on_env_gained
       item_gift 通道同阶口径);同窗多条 facts 逐条发(级联两级 =
       两次发放,逐级触发判例)。

    - ``sig`` = 链写共用渠道签名,必须 logic_action / logic_hook 族
      (obs 族进写通道即炸渠道族校验——禁 obs_sig);
    - 本函数含采样:rng = ``action_sampling_rng('env_merge_grant', None)``
      函数内解析(注入槽优先,缺省回退自掷)。选注入槽而非显式 rng 形参
      (check_env_boss_grants 风格)的理由 = 四发火点跨上报函数/效果族/
      链原语三类调用方,集中函数内解析单点最少;sim 注入槽即世界真值,
      live 回退自掷 = 采样是猜测口径(bench 首观察静默覆盖);
    - bench 未观察/席满溢出位占 = :func:`gain_character` 链内既有
      拒落/留证语义,本函数不另设闸;
    - 递归安全:发放物(符玄/希儿)不在触发集,发放角色自身若再合并
      升星,其 facts 过滤后零发放,链天然终止(无环,不设额外闸)。
    """
    env = gs.active_env.value
    if not env:
        return ()
    grant = ENV_MERGE_GRANTS.get(env)
    if grant is None:
        return ()
    triggers, pool = grant
    hits = [cid for cid, _new_star in facts if cid in triggers]
    if not hits:
        return ()
    # kernel 反向模块级零 import 契约:action_sampling_rng 住上报函数族
    # 包,函数内惰性取(gain-chain.md §8 单向破环先例)。
    from sr_od.application.currency_war.kernel.cw_action_report import (
        action_sampling_rng,
    )
    roll_rng = action_sampling_rng(ENV_MERGE_GRANT_RNG_TOOL, None)
    effects: list[str] = []
    for _cid in hits:
        name = roll_rng.choice(pool)
        gain_character(gs, name, 1, rand=True, sig=sig,
                       evidence=f'env_merge_grant:{env}',
                       producer=GAIN_CHAIN_PRODUCER)
        effects.append(f'env_merge_grant:{name}')
    return tuple(effects)


#: 晶矿开启触发发放的采样腿具名键(模块内近函数,消费点唯一 =
#: :func:`check_env_ore_open_grants`;先例 = ENV_MERGE_GRANT_RNG_TOOL
#: 同形态)。
ORE_OPEN_GRANT_RNG_TOOL: str = 'env_ore_open_grant'


def check_env_ore_open_grants(gs: GameState, sig: ChannelSig
                              ) -> tuple[str, ...]:
    """晶矿开启计数触发发放检查(单一源;唯一调用点 = 采晶矿上报函数
    ``report_action_collect_ore_param`` 尾部,批内计数入账后、同动作窗
    内,live/sim 同一段 op 代码同口覆盖)。触发注册表 =
    ``cw_investments.ENV_ORE_OPEN_GRANTS``,计数载体 =
    ``gs.effects.ore_open_total``(record_ore_open 单口)。
    返回本次发放角色名列表(仅日志面消费,调用方不分支)。

    条件矩阵(顺序即短路序,逐序返回空 = 零发放):

    1. 当前环境(active_env)None/空链 → 空;
    2. 环境不在登记表(ENV_ORE_OPEN_GRANTS)→ 空;
    3. ``gs.bench.value`` None(从未观察)→ 空且不标 done(宁缺勿造,
       与 check_env_interest_grants 同款;晶矿开启可重现,下次开启自动
       重查,done 只在发放同窗登记);
    4. 阈值 loop:``t`` 从登记表首阈值起,若 ``ore_open#<t>`` ∈ done
       现值则 ``t += 步长`` 推进跳过(已封账);``t > ore_open_total``
       = 未达标,停止。loop 保留 = 一般形态:单次上报 opened ≤ 3
       (ORE_CLICK_BATCH_MAX_K = 3,strategies/impl/mandate_v1/entry.py),
       步长 10 > 3,生产单批跨阈值不可达;呈现批 ≠ 上报批,防未来扩面
       静默漏发;
    5. 承载守卫:计数是 int 属性恒有值直接可比;发放不涉金/装备承载,
       角色承载 = bench(条 3 已守);
    6. **先守卫后发放**(守卫先于该阈值的任何一腿,禁半发放):随机腿
       池现查 = ``chars_by_faction(随机羁绊名)`` 非空——空 = 注册表
       漂移(import 期校验后生产不可达,纯防御分支),整体缓发返回空
       不标 done——「具名腿已发、done 未封」的半发放态会在下批重触发
       同一阈值时重复发放具名腿,重复发放比漏发更劣;
    7. 达标发放(每阈值一次,loop 逐阈值重复本条):具名角色逐个 +
       随机腿池内均匀采样 1 名,各自 :func:`gain_character`(1★ 先验
       族,晶矿 CHAR_DROP_STAR 同句式);done 追加
       ``(env, ore_open#<t>)``(write_logic,簿记封账不在随机态面,
       与 check_env_refresh_grants 的金/装备/done 相邻写同纪律)。
       ``t += 步长`` 回到条 4。

    - **两腿发放恒随机态写入(两腿 gain_character 一律 rand=True,
      函数不设 rand 形参)**:触发前提 = 晶矿开启计数为未验证推演
      (打开可能失败/计数可能错),发放按随机态定级走台账纠偏 + bench
      首观察覆盖,用户裁定 2026-10-17;rand 形参仅通道定级,具名腿名字
      确定、rng 不在本腿消耗,随机腿 ``rng.choice`` 掷名是唯一一笔
      rng 消耗;
    - **done 记账与落位解耦**(显式接受):done 在发放窗内恒登记,不
      逐腿检查 placed——「全员落位才封账」在部分落位态(部分腿溢出位
      被占零写)下重试会重复发放已落位腿,无法事后回退;落位失败本身有
      DEFECT_OVERFLOW_TAKEN 留证链,live 侧 bench 观察覆盖兜底;溢出位
      被占时该阈值第二腿漏发 = 接受面;
    - ``sig`` = 全部写共用的渠道签名,必须 logic_action / logic_hook 族
      (obs 族进写通道即炸渠道族校验——禁 obs_sig);唯一调用方传入
      上报函数内部的 ``_grp_sig``(logic_action 族),天然满足;
    - 本函数含采样:rng = ``action_sampling_rng(ORE_OPEN_GRANT_RNG_TOOL,
      None)`` 函数体内惰性解析(kernel 反向模块级零 import 契约),
      首个未封账达标阈值确认后才取(无命中不消耗采样流键,保持 sim
      动作序列逐位不变);注入槽 = sim 世界真值,回退自掷 = live 猜测
      口径(采样猜测态下掷名 ≠ 实机真名 → bench 首观察静默覆盖)。
    """
    env = gs.active_env.value
    if not env:
        return ()
    grant = ENV_ORE_OPEN_GRANTS.get(env)
    if grant is None:
        return ()
    if gs.bench.value is None:
        # 席面从未观察:发放角色写出不完整席 = 丢人,缓发不标 done
        # (下个开矿窗自动重查;done 只在发放同窗登记)
        return ()
    first_threshold, step, named_chars, random_faction = grant
    done = tuple(gs.env_grants_done.value or ())
    total = gs.effects.ore_open_total
    roll_rng: random.Random | None = None
    granted: list[str] = []
    t = first_threshold
    while t <= total:
        key = f'{ORE_OPEN_THRESHOLD_KEY_PREFIX}{t}'
        if (env, key) in done:
            t += step   # 已封账:推进找下一个未封账阈值(断档续发)
            continue
        pool = [c.name for c in chars_by_faction(random_faction)]
        if not pool:
            # 整体缓发(先守卫后发放,禁半发放;生产不可达,纯防御分支)
            break
        if roll_rng is None:
            # kernel 反向模块级零 import 契约:action_sampling_rng 住
            # 上报函数族包,函数内惰性取(gain-chain.md §8 单向破环先例)
            from sr_od.application.currency_war.kernel.cw_action_report import (
                action_sampling_rng,
            )
            roll_rng = action_sampling_rng(ORE_OPEN_GRANT_RNG_TOOL, None)
        evidence = f'env_grant#{env}#ore_open{t}'
        for name in named_chars:
            gain_character(gs, name, 1, rand=True, sig=sig,
                           evidence=evidence, producer=_PRODUCER)
            granted.append(name)
        random_name = roll_rng.choice(pool)
        gain_character(gs, random_name, 1, rand=True, sig=sig,
                       evidence=evidence, producer=_PRODUCER)
        granted.append(random_name)
        gs.write_logic(gs.env_grants_done, done + ((env, key),),
                       produced_by=_PRODUCER, evidence=evidence, sig=sig)
        done = done + ((env, key),)
        t += step
    return tuple(granted)


def _dot_char_in_bench_view(view: BenchView | None) -> bool:
    """备战席视图是否含黑天鹅(观察证实判据与幂等守卫的 bench 侧共用扫描;
    kind='unit' 且身份命中才算——占席道具/空槽不计)。"""
    if view is None:
        return False
    return any(s.kind == 'unit' and s.unit is not None
               and s.unit.char_id == _DOT_CHAR for s in view.slots)


def _dot_char_in_full_view(gs: GameState) -> bool:
    """全视图(备战 ∪ 上阵 ∪ 溢出)是否已含黑天鹅(猜测写幂等守卫)。

    扫描域与 :func:`gain_character` 3 合 1 扫描域同域(bench 槽表 +
    上阵两排 + 溢出位身份串);bench/deployed 未观察(None)= 视为不含
    ——此时猜测写照发,链内 bench 未观察拒落档零写兜底,宁缺勿造无
    缺陷发出。"""
    if _dot_char_in_bench_view(gs.bench.value):
        return True
    dep = gs.deployed.value
    if dep is not None:
        for u in list(dep.front_slots or []) + list(dep.back_slots or []):
            if u is not None and u.char_id == _DOT_CHAR:
                return True
    return str(gs.overflow_card.value or '') == _DOT_CHAR


def check_env_dot_grants(gs: GameState, sig: ChannelSig, *,
                         count_battle: bool = False,
                         bench_observation: BenchView | None = None,
                         ) -> str | None:
    """持续伤害契约条件腿触发检查(猜测写 + 证实单一源;三个接线点共用
    本函数,条件判定不漂移):live 结算覆盖窗猜测写 / live 备战屏观察证实
    / sim 结算腿猜测写+进度累计+证实(设计 = T-28 设计稿 §2.2/§2.3,
    迭代 2026-09-23-invest-effects-calc)。建模动机:计数源(敌方 DoT
    状态)双端皆盲无世界真值生产点 → 不可数但可假设、可证实——每次结算
    「假设获得黑天鹅」随机态垫入,live 由备战观察收敛、sim 由固定战斗数
    收敛。

    **结算窗腿**(默认;``bench_observation`` 为 None 时):条件矩阵
    (顺序即短路序):

    1. active_env 非持续伤害契约 → None;
    2. ``(env, dot_confirm) ∈ done`` → None(已证实,猜测写永久短路;
       done None 视为空防御,沿 streak 通道 ``value or ()`` 先例);
    3. 幂等守卫:全视图(bench ∪ deployed ∪ 溢出)已含黑天鹅 → 跳过
       猜测写(不叠写;若在场的是观察同步来的真身,证实腿同窗已处理);
    4. → 猜测写::func:`gain_character`(黑天鹅, 1★ 先验族,rand=True
       猜测态通道——认知通道随机态非采样身份,首观察静默覆盖是
       write_logic_rand 通道自有契约;evidence ``env_dot_speculate#<帧>``
       可辨;拒落/溢出/席满语义全继承链内防线,bench 未观察拒落零写);
    5. ``count_battle=True``(sim 接线专用,进度腿 live 不追加):进度键
       ``dot_battle#<k>`` 追加 done(k = 已有 dot_battle# 键数 + 1,
       append-only 对账可数);``k == ENV_DOT_CONFIRM_BATTLES`` 的那笔
       同窗相邻追加证实 done ``(env, dot_confirm)``,evidence
       ``env_dot_confirm#sim``。非战斗轮(商店/事件)不经结算腿 = 不
       计数(结构性,接线点在结算腿内)。进度键**按环境连续累计,不随
       同局内重获得重置**(蓝海卷随机再入同卡的极低概率形态:k 跨获得
       期续计,合计 8 个战斗结算证实 = 「总拥有 8 战斗」口径,对账时
       勿当漂移查)。

    **观察证实腿**(live 独有;``bench_observation`` 非 None 时,挂点 =
    备战屏 bench 整表观察同步点,观察写之后同帧):观察值含黑天鹅 &&
    env active && 未证实 → done 追加 ``(env, dot_confirm)``,evidence
    ``env_dot_confirm#obs``。证实来源不区分(v2-5 裁定:观察到即证,
    席面真值由观察整表同步自兜);观察无黑天鹅 → 零写(猜测态由观察
    覆盖契约无声抹除,下次结算重写 = 自愈循环)。live 无定时保底
    (v2-2 裁定:证实只认备战观察,猜测写无时间/次数上限)。

    锚键 ``dot_anchor#<位面>-<轮>`` 纯登记件**非门控**,写入端 =
    cw_gain_chain.on_env_gained 获得刻(开局三选一获取时 node 未进窗
    不写 = 预期形态,缺锚不影响本函数任何一步)。

    - ``sig`` = 全部写共用的渠道签名,必须 logic_action / logic_hook 族
      (obs 族进写通道即炸渠道族校验——禁 obs_sig;形态归两端接线);
    - 本函数零 rng:身份具名单名、进度计数比较确定,随机态指认知通道
      (落位未知、观察校准),不消耗随机数;
    - 返回 ``_DOT_CHAR`` 当本调用发生过写(猜测/进度/证实任一),None
      = 零写(调用方仅日志面消费,无行为分支——本卡无宝钻式回调)。
    """
    env = gs.active_env.value
    if env != DOT_CONTRACT_ENV:
        return None
    done = tuple(gs.env_grants_done.value or ())
    if (env, DOT_CONFIRM_KEY) in done:
        return None
    if bench_observation is not None:
        # 观察证实腿(条件面 = 观察含黑天鹅 && env active && 未证实,
        # 前两门已在上方短路)
        if not _dot_char_in_bench_view(bench_observation):
            return None
        gs.write_logic(gs.env_grants_done,
                       done + ((env, DOT_CONFIRM_KEY),),
                       produced_by=_PRODUCER,
                       evidence='env_dot_confirm#obs', sig=sig)
        return _DOT_CHAR
    # 结算窗腿:猜测写(幂等守卫先行)
    wrote = False
    if not _dot_char_in_full_view(gs):
        frame = _node_frame(gs)
        gain_character(gs, _DOT_CHAR, 1, rand=True, sig=sig,
                       evidence=(f'env_dot_speculate#{frame}'
                                 if frame else 'env_dot_speculate'),
                       producer=_PRODUCER)
        wrote = True
    if count_battle:
        # 进度腿(sim 专用):k = 已有 dot_battle# 键数 + 1(append-only,
        # 第 k 笔与证实同窗相邻写——登记事实两行各自带 evidence 可分事件)
        k = sum(1 for e, key in done if e == env
                and key.startswith(DOT_BATTLE_KEY_PREFIX)) + 1
        progress_key = (env, f'{DOT_BATTLE_KEY_PREFIX}{k}')
        gs.write_logic(gs.env_grants_done, done + (progress_key,),
                       produced_by=_PRODUCER,
                       evidence=f'env_dot_progress#{k}', sig=sig)
        wrote = True
        if k == ENV_DOT_CONFIRM_BATTLES:
            gs.write_logic(gs.env_grants_done,
                           done + (progress_key, (env, DOT_CONFIRM_KEY)),
                           produced_by=_PRODUCER,
                           evidence='env_dot_confirm#sim', sig=sig)
    return _DOT_CHAR if wrote else None


def on_diamond_acquired(gs: GameState, equip_name: str) -> None:
    """宝钻获得回调(世界数值面联动;唯一调用点 = sim 深井发放路径,
    3.3 接线;**supply 补给宝钻不采纳**——钻类型未建模,归 3.3 覆盖;
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
      3. ``back_layout`` = min(9,现值 + 1)(值域 6-9;现值 None → 以
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
