"""货币战争动作上报:点晶矿(report_action_collect_ore_param)。

**逻辑随机态首个落地动作**(状态容器随机写语义单一源 =
:meth:`GameState.write_logic_rand`):

- **逐点顺序推演**:载荷为批式坐标列表,逐点独立守卫/独立采样/独立
  逐步写(每步一行,同组 group_id,evidence 带点序 ``#ore<k>``);
- **席满即该点无效**:该点时备战席无空位(含前点角色奖励耗席后的
  累计判)→ 晶矿留在 spheres 字段现值中(不摘除、不采样),等下轮
  重派(screen_flow_timing #16 已登记裁定同源);
- **全部字段写均为随机态**(rand = :meth:`GameState.write_logic_rand`):
  spheres 终值同样依随机链而变(后续晶矿开否取决于采样奖励是否耗席),
  本动作不存在确定面写;观察覆盖差异 = 随机效果落地预期内
  (``logic_rand_outcome`` 台账行),策略消费前必须重观察;
- **奖励来源 = ore_rewards 附着值兑现**(正本 = flow/projection_contract.md §2 晶矿族四域
  + game_state/fields.md §3.2.8a:掷骰已前移到生成侧挂接入口 ``cw_ore_channel``,点击只兑现):
  命中附着键 → 直接应用**零掷骰**;缺项(挂接入口不变量破坏的罕见态)
  → 兜底 ``kernel/cw_ore_reward.py::roll_ore_reward``(临时口径 v0,
  假设档披露键已登记),该点全部写行 evidence 前缀
  ``ore_reward_attach_missing#``;缺项 ∧ level 缺读 → 该点跳过不采
  (reason ``ore_reward_attach_missing_level``,矿留 spheres 下帧补
  生成);开成即随 spheres 摘除同点随机态写移除附着键(evidence
  ``ore_reward_detach#ore{k}``)。rng 解析口不变——实机缺省未播种
  (兜底采样是猜测),sim 传流键 rng(采样即状态副本真值,零自算)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 状态容器单向依赖。

动作分支清单:①**计数分支** = 批内开成点数经 ``gs.effects.record_ore_open``
唯一入口入账(「点开才计数」:席满/缺项∧level 缺读跳点不入账;计数载体 =
``cw_effect_inventory.ore_open_total``,消费方 = 战技点契约触发器);
②**环境条件发放分支**(``cw_investments.ENV_ORE_OPEN_GRANTS`` 已登记环境:
战技点契约) = 计数入账后尾部触发检查(``check_env_ore_open_grants``,
与 refresh_shop 环境条件发放分支同构);③**策略卡晶矿开启发放分支**
(``cw_investments.STRATEGY_ORE_OPEN_EFFECTS`` 已登记策略卡:黄晶矿工首例)
= 契约条目后独立触发检查(``check_strategy_ore_open_effects``,逐开掷
低一档条目 + 授予矿状态副本写;开成点色档列按载荷序收集,跳点不入列)——
状态副本发放域,不属计数/采样语义;sim 与生产同段 op 代码同口,单点覆盖
实机和模拟器两边。窗序确定:晶矿自身奖励写(含合并升星触发分支)→ 晶矿开启计数
入账 → 战技点契约触发分支 → 策略卡晶矿开启触发分支。
"""
from __future__ import annotations

import random
from dataclasses import replace as _dc_replace
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_env_grants import (
    check_env_ore_open_grants,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_place,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    ChannelSig,
    GameState,
    LogicOutcome,
    OreSight,
    Unit,
    _validate_sig,
    bench_view_of_working,
    deployed_indexed_of_view,
    deployed_view_of_indexed,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    _bench_sig,
    _dep_sig,
    _merge_bench,
)
from sr_od.application.currency_war.kernel.cw_ore_reward import (
    roll_ore_reward,
)

_PRODUCER = 'CwActionCollectOreParam'

#: 缺项兜底路径的点级 evidence 前缀(详设 ore-click-consume §1):不变量
#: 破坏的响亮标注——该点全部写行带前缀,判读可辨「非附着兑现」。
_MISSING_EVIDENCE_PREFIX: str = 'ore_reward_attach_missing#'
#: 缺项需兜底掷 ∧ level 缺读的跳点 reason(零写跳过不落写行,reason 是
#: 唯一可断言通道;优先于 ore_partial_open_skipped 表达具体原因)。
_MISSING_LEVEL_REASON: str = 'ore_reward_attach_missing_level'


def report_action_collect_ore_param(gs: GameState, param: Any, sig: ChannelSig,
                                    session: object = None,
                                    rng: random.Random | None = None) -> LogicOutcome:
    """点晶矿上报(逐点顺序推演 + 随机态逐步写;正本 = game_state/fields.md §3.2.8a/§4 全表)。

    - **整批拒(零写)**:spheres 未观察(现行为)/载荷无交集(现行为)/
      bench 未观察('bench_unobserved'——席满守卫与角色落点均不可判)。
      level 缺读不再整批拒(语义收窄,详设 ore-click-consume §1):
      附着命中不需 level,原 'level_unread' 守卫随采样停用到缺项兜底
      路径(见逐点守卫);
    - **逐点守卫**:该点时备战席无空位 → 该晶矿留在 spheres、不采样
      (裁决 3:满栏点击无效;前点奖励耗席累计判);缺项需兜底掷 ∧
      level 缺读 → 同族跳过不采(矿留 spheres 不摘零写,证据通道 =
      reason 'ore_reward_attach_missing_level';下帧挂接入口补生成
      后再点);
    - **写序**(每点):spheres 摘除 → 附着键移除(命中路径,随摘除
      同点随机态写,evidence 'ore_reward_detach#ore{k}')→ 未抽中域
      标记(值不变,现值非 None 才标)→ 奖励应用(金 +N/装备 +件/
      角色落位 + 3合1 连锁——每级合并后受影响域各落一行,board 派生
      随行写自动继承随机态);缺项路径该点全部写行 evidence 前缀
      'ore_reward_attach_missing#';
    - **动作级出参**:全部开成 = applied=True;混合批 =
      'ore_partial_open_skipped';全部席满跳过 = applied=False
      'bench_full_no_open';存在缺项∧level 缺读跳点 =
      'ore_reward_attach_missing_level'(优先于前两条表达具体原因——
      批内含非席满跳点即非「全部席满跳过」,全跳批亦报此 reason)。

    P1 状态容器原生(§3.2):bench 工作副本 = BenchView 槽序、deployed =
    行域下标派生表;整表写 = bench_view_of_working 直构(原
    ``_bench_view_keep_items`` 占位件保留补丁随换形口停用自然消失——
    工作表元素即状态容器 BenchSlot,占位件 kind 原样保留,零降级路径)。
    合并升星触发发放:角色奖励分支级联采集升星事实,整批全部写毕后收尾
    发火(引擎 A 内嵌发火会被后续点整表写覆盖;触发分支 best-effort 不
    阻塞上报主链)。
    晶矿开启计数与战技点契约触发发放:整批奖励写毕后 ``opened`` 经
    ``record_ore_open`` 唯一入口入账,再尾部触发检查(check_env_ore_open_
    grants;计数先入账后检查,窗序 = 矿奖励 → 计数 → 触发分支;
    opened == 0 早退路径零计数零触发——分支清单详见模块头)。策略卡晶矿
    开启触发发放条目同尾部独立调用块(契约条目后;开成点色档列消费,持卡
    掷点授予矿,check_strategy_ore_open_effects,窗序 = 契约分支后)。
    """
    _validate_sig(sig, ('logic_action',))
    from sr_od.application.currency_war.kernel.cw_action_report import (
        action_sampling_rng,
    )
    roll_rng = action_sampling_rng('collect_ore', rng)

    view = gs.spheres.value
    if view is None:
        return LogicOutcome(applied=True, reason='spheres_unobserved')
    orig_bench = gs.bench.value
    if orig_bench is None:
        return LogicOutcome(applied=False, reason='bench_unobserved')
    # level 不再整批拒(语义收窄,详设 ore-click-consume §1):附着兑现
    # 不需 level,原 'level_unread' 守卫随采样停用——缺项兜底路径的
    # level 门下沉到点级(见循环内 missing_level 跳点)
    level = gs.level.value

    # 载荷 ∩ 现值,按载荷序保序去重(同坐标重复点 = 单点)
    by_xy = {(int(p[1]), int(p[2])): p for p in view.points}
    ordered: list[tuple] = []
    seen: set[tuple[int, int]] = set()
    for x, y in param.points:
        xy = (int(x), int(y))
        if xy in by_xy and xy not in seen:
            seen.add(xy)
            ordered.append(by_xy[xy])
    if not ordered:
        return LogicOutcome(applied=True, reason='no_intersection')

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w_rand(target: Any, value: Any, evidence: str) -> None:
        gs.write_logic_rand(target, value, produced_by=_PRODUCER,
                            evidence=evidence, sig=_grp_sig)

    # 工作态(元素 frozen,浅拷贝列表即与状态容器帧断开写入别名;写回 =
    # replace 新构造,零就地变异)
    remaining = list(view.points)
    work_bench = list(orig_bench.slots)
    orig_dep_view = gs.deployed.value
    work_dep = deployed_indexed_of_view(orig_dep_view)

    opened = 0
    skipped = 0
    missing_level = 0
    merge_facts: list[tuple[str, int]] = []
    # 开成点色档列(载荷序;策略卡晶矿开启触发条目消费——席满/缺级跳点
    # 不入列,「点开才触发」与计数分支同口径)
    opened_tiers: list[str] = []

    def _collect_merge(cid: str, new_star: int) -> None:
        # 升星事实采集(合并升星触发发放;纯追加,发火在整批写毕后)
        merge_facts.append((cid, new_star))

    for k, p in enumerate(ordered, 1):
        xy = (int(p[1]), int(p[2]))
        if sum(1 for b in work_bench
               if b is None or b.kind == 'empty') <= 0:
            skipped += 1
            continue   # 席满即该点无效:晶矿留在 spheres,不摘不采

        # —— 奖励来源 = ore_rewards 附着值兑现(掷骰已前移到生成侧)——
        # 键制 'x,y' 与挂接入口 cw_ore_channel 同格(game_state/fields.md §3.2.8a 接口契约)
        attach_key = f'{xy[0]},{xy[1]}'
        attached = (gs.ore_rewards.value or {}).get(attach_key)
        if attached is not None:
            reward = attached
            ev_prefix = ''   # 命中零掷骰:附着值即生成侧已掷的结果
        elif level is None:
            # 兜底掷需 level(角色采样口径)而 level 缺读 → 该点跳过不采
            # (与席满跳过同族:矿留 spheres 不摘、零写;下帧挂接入口
            # 补生成后再点)
            missing_level += 1
            continue
        else:
            reward = roll_ore_reward(roll_rng, int(level))
            ev_prefix = _MISSING_EVIDENCE_PREFIX

        # 步1 spheres 摘除(随机态——终值依随机链而变,fields.md §3.2.8a 表注)
        remaining = [q for q in remaining
                     if (int(q[1]), int(q[2])) != xy]
        _w_rand(gs.spheres, OreSight(
            count=len(remaining),
            colors=tuple(dict.fromkeys(q[0] for q in remaining)),
            points=tuple(remaining)),
            f'{ev_prefix}proj_collect_ore_drop#ore{k}')
        # 步1b 开成即移除附着键(随spheres 摘除同点随机态写;缺项路径
        # 无键可摘零写。新 dict 构造 = 冻结帧替换语义,不污染旧引用)
        if attached is not None:
            detached = dict(gs.ore_rewards.value or {})
            detached.pop(attach_key, None)
            _w_rand(gs.ore_rewards, detached, f'ore_reward_detach#ore{k}')
        opened += 1
        opened_tiers.append(p[0])

        written = {'spheres'}
        rolled_domain = {'gold': 'gold', 'equip': 'equips',
                         'char': 'bench'}[reward.kind]

        # 步2 未抽中域标记(值不变,现值非 None 才标——None 域跳写,
        # 随机态标记对「本就未知」的域无信息增益)
        for dom, fld in (('gold', gs.gold), ('equips', gs.equips),
                         ('bench', gs.bench), ('deployed', gs.deployed)):
            if dom == rolled_domain or dom in written:
                continue
            cur = fld.value
            if cur is None:
                continue
            _w_rand(fld, cur, f'{ev_prefix}proj_ore_mark_{dom}#ore{k}')
            written.add(dom)

        # 步3 奖励应用(抽中域写采样值)
        if reward.kind == 'gold':
            g = gs.gold.value
            if g is not None:
                _w_rand(gs.gold, int(g) + int(reward.gold),
                        f'{ev_prefix}proj_ore_reward_gold#ore{k}')
                written.add('gold')
        elif reward.kind == 'equip':
            eq = gs.equips.value
            if eq is not None:
                _w_rand(gs.equips, list(eq) + [reward.equip],
                        f'{ev_prefix}proj_ore_reward_equip#ore{k}')
                written.add('equips')
        else:
            # 角色奖励:落备战席首空槽 → 3合1 连锁(每级合并后受影响域
            # 各落一行;board 派生随行写自动继承随机态)。bench 整表写
            # = 工作槽表直构(占位件 kind 原样保留,见函数头 P1 申报)
            bench_place(work_bench, BenchSlot(
                kind='unit', unit=Unit(char_id=reward.char_id,
                                       star=reward.char_star)))
            _w_rand(gs.bench, bench_view_of_working(work_bench, orig_bench),
                    f'{ev_prefix}proj_ore_reward_char#ore{k}')
            written.add('bench')
            merge_no = 0
            last_bs = _bench_sig(work_bench)
            last_ds = _dep_sig(work_dep)

            def on_step(_k: int = k,
                        _written: set[str] = written,
                        _evp: str = ev_prefix) -> None:
                # 默认参数绑定本点序/本点登记集/本点前缀(B023:回调内聚
                # 合同步调用,绑定义为调用刻值,防循环变量晚绑隐患)
                nonlocal merge_no, last_bs, last_ds
                merge_no += 1
                ev = f'{_evp}proj_ore_merge#{merge_no}#ore{_k}'
                bs = _bench_sig(work_bench)
                if bs != last_bs:
                    _w_rand(gs.bench,
                            bench_view_of_working(work_bench, orig_bench),
                            ev)
                    last_bs = bs
                    _written.add('bench')
                ds = _dep_sig(work_dep)
                if ds != last_ds:
                    _w_rand(gs.deployed,
                            deployed_view_of_indexed(work_dep, orig_dep_view),
                            ev)
                    last_ds = ds
                    _written.add('deployed')

            _merge_bench(work_bench, work_dep, on_step=on_step,
                         on_merge=_collect_merge, gs=gs)

            # 步4 合成未触及的行域标记(真值可能因角色奖励而变)
            if 'deployed' not in written:
                cur = gs.deployed.value
                if cur is not None:
                    _w_rand(gs.deployed, cur,
                            f'{ev_prefix}proj_ore_mark_deployed#ore{k}')
                    written.add('deployed')

    # —— 合并升星触发发放分支(整批级联写毕后收尾发火:引擎 A 内嵌发火会被
    #    后续点的 bench 整表写覆盖,故采集在级联、发火在顶层全部写毕后;
    #    sig 沿动作分支 _grp_sig 口径。best-effort:触发分支异常不阻塞上报
    #    主链,沿 buy_card on_buy 回调分支同纪律。kernel 反向模块级零
    #    import 契约:函数内惰性取。)——
    if merge_facts:
        try:
            from sr_od.application.currency_war.kernel.cw_env_grants import (
                check_env_merge_grants,
            )
            check_env_merge_grants(gs, tuple(merge_facts), sig=_grp_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning(f'[cw-ore] 合并升星触发发放分支失败(不阻塞):'
                        f'{merge_facts} {e}')
        # —— 策略卡合成触发发放条目(「合成2星2费角色时获得砂金」族,
        #    注册表 = STRATEGY_MERGE_GRANTS):事件源 = 本函数既有
        #    merge_facts 采集复用,判据 = 产物星级+费用双匹配。函数内
        #    自门 sim 装配(live 零写);与上方条目独立 try 互不短路。
        #    best-effort:发放分支异常不阻塞上报主链(上方条目同纪律)。——
        try:
            from sr_od.application.currency_war.kernel.cw_gain_chain import (
                check_strategy_merge_grants,
            )
            check_strategy_merge_grants(gs, tuple(merge_facts), sig=_grp_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning(f'[cw-ore] 策略卡合成发放分支失败(不阻塞):'
                        f'{merge_facts} {e}')

    # —— 晶矿开启计数分支 + 环境条件发放分支(整批奖励写毕后收尾:窗序
    #    确定 = 矿奖励写(含合并升星触发分支)→ 计数入账 → 战技点契约
    #    触发分支 → 策略卡开启触发分支;计数先入账后检查,检查时计数现值
    #    含本批。「点开才计数」:opened 只计开成点,席满/缺项∧level 缺读
    #    跳点不入账;opened == 0 早退路径零计数零触发)——
    if opened:
        gs.effects.record_ore_open(opened)
        check_env_ore_open_grants(gs, _grp_sig)
        # —— 策略卡晶矿开启触发发放条目(「开启晶矿时」族,黄晶矿工 id
        #    302101 首例,注册表 = STRATEGY_ORE_OPEN_EFFECTS):逐开掷
        #    低一档条目 + 授予矿状态副本写;live 同口掷 = 预测写(观察覆盖自愈),
        #    sim = 状态副本真值。函数内自门持卡交集(未持卡零写零流键消耗);
        #    与契约条目独立 try 互不短路。best-effort:发放分支异常不阻塞
        #    上报主链(合并升星触发分支同纪律)。kernel 反向模块级零
        #    import 契约:函数内惰性取。——
        try:
            from sr_od.application.currency_war.kernel.cw_gain_chain import (
                check_strategy_ore_open_effects,
            )
            check_strategy_ore_open_effects(gs, tuple(opened_tiers),
                                            sig=_grp_sig, level=level)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning(f'[cw-ore] 策略卡晶矿开启发放分支失败(不阻塞):'
                        f'{e}')

    if opened == 0:
        # 批内含缺项∧level 缺读跳点即非「全部席满跳过」——具体原因
        # reason 优先于 bench_full_no_open 表达(详设 ore-click-consume
        # §1:reason 是零写跳过的唯一可断言通道)
        if missing_level:
            return LogicOutcome(applied=False, reason=_MISSING_LEVEL_REASON)
        return LogicOutcome(applied=False, reason='bench_full_no_open')
    if missing_level:
        return LogicOutcome(applied=True, reason=_MISSING_LEVEL_REASON)
    if skipped:
        return LogicOutcome(applied=True, reason='ore_partial_open_skipped')
    return LogicOutcome(applied=True)
