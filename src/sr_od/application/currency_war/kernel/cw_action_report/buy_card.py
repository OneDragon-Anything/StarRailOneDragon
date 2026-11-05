"""货币战争动作上报:买牌(report_action_buy_card_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察
写端留在原位 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。
语义权威版本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    ShopPayload,
    ShopSlot,
    Unit,
    _validate_sig,
    bench_view_of_working,
    deployed_indexed_of_view,
    deployed_view_of_indexed,
    detect_merge_upgrade,
    mark_gold_spent,
    shop_cards_to_legacy,
    shop_payload_content_cards,
)


def report_action_buy_card_param(gs: GameState, param: Any, sig: ChannelSig,
                                 executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """买牌上报:gold −单价×(k−免费张数) + bench 落位 + 合成连锁 + payload −k
    ((name, star) 计数)+ 免费购买闸(降本增效 uses 余量,按张计免
    min(k, 余量) 张,全免帧零金写)+ 购买翻星(策略卡购买翻星注册表落位星级判定,
    翻转只改 Unit 构造星,payload 匹配与 on_buy 持购买原星;applied 后
    置一次性标志位 best-effort)+ 升星分支整表覆盖(买前快照三件组基点,快照在
    本函数内第一时间取——原落地门/两驱动器三处抄写并入单点)+ 合并
    升星触发发放收尾(级联采集的升星事实交触发检查,升星分支写毕后
    best-effort 发火,触发分支异常 log 不阻塞上报主链)。

    满栏且合成不可达 = 游戏拒买(applied=False + reason='bench_full',
    零写)。k 来源:executed 给定 = 回执 k(live);None =
    理想执行自算(简单分支 1,满栏从应用机器出)。语义由
    test_gain_chain(卖/换上报 v2 族契约节)/ 测试 M1 钉住。

    P1 状态容器原生(benchchar-retirement §3.2):bench 工作副本 = BenchView
    槽序(元素即状态容器 BenchSlot)、deployed 工作副本 = 行域下标派生表
    (Unit,§2.1);合成引擎状态容器原生直写,零中间形。元素
    frozen → 浅拷贝列表即快照(推演以 replace 新构造,零别名风险)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from one_dragon.utils.log_utils import log as _log
    from sr_od.application.currency_war.kernel.cw_economy import (
        card_cost,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_place,
    )
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        check_strategy_buy_star_flip,
        check_strategy_star_merge_gold,
        expert_conditional_trigger,
        mark_strategy_buy_star_flip_consumed,
    )
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        _apply_full_bench_merge_buy,
        _dep_sig,
        _merge_bench,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        ShopCard as _LegacyShopCard,
    )

    # 买前快照两件组(升星分支比较基点;必须在简单分支写之前取——基点
    # 误取买后状态容器会重复落位,shop 视图缺失会漏满栏合成)。bench 未观察
    # = 缺省形态 [None]×9(全空可落位,非满栏拒)。
    _pre_view = gs.bench.value
    pre_bench = (list(_pre_view.slots) if _pre_view is not None
                 else [None] * 9)
    pre_dep = deployed_indexed_of_view(gs.deployed.value)

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionBuyCardParam',
                       evidence=evidence, sig=_grp_sig)

    def _legacy_card(c: Any) -> _LegacyShopCard:
        """状态容器牌 → 平移机器入参 Legacy 牌(仅 (name, star) 语义位消费)。"""
        return _LegacyShopCard(
            x=0,
            faction=str(getattr(c, 'faction', '') or '?'),
            name=str(getattr(c, 'name', '') or ''),
            cost=int(getattr(c, 'cost', 0) or 0),
            star=int(getattr(c, 'star', 1) or 1),
            cost_source=str(getattr(c, 'cost_source', '') or 'roster'))

    card = param.card
    name = str(getattr(card, 'name', '') or '')
    star = int(getattr(card, 'star', 1) or 1)
    # —— 购买翻星落位判定(「购买的下1个X费角色立刻升到N星」族,注册表
    #    = STRATEGY_BUY_STAR_FLIP_GRANTS,首例四费晋升):落位星级在 Unit
    #    构造前判定一次——「立刻」= 翻星先于合成级联,翻转件以目标星级
    #    身份参与合成判定(家族判读申报制非已定案,登记表区块注释同句申
    #    报)。翻转只改本处落位星:payload 移除匹配与 on_buy 回调持购买
    #    原星(交易对象与效果账本按购买面计,错位 = 商店按目标星匹配
    #    移除 0 张)。目标星级现役恒 2 = 表值镜像(表域 {2, 3} 预留族扩
    #    展,第二目标值卡落地批随批改读表值——「本批不预泛化」先例同
    #    款纪律);满栏合成买路径翻转面不建模(整卡入参,登记表区块注
    #    释边界申报)。best-effort:谓词异常按未翻转降级留 log 不阻塞
    #    上报主链。——
    land_star = star
    try:
        if check_strategy_buy_star_flip(gs, name=name, star=star,
                                        cost=card_cost(card), sig=_grp_sig):
            land_star = 2
    except Exception as e:  # noqa: BLE001  谓词失败不阻塞(留 log)
        _log.warning(f'[cw-buy] 购买翻星谓词分支失败(按未翻转降级): {e}')
    payload = gs.shop.value
    shop_view = shop_cards_to_legacy(shop_payload_content_cards(payload))
    # k 来源:executed 给定 = 回执 k(live);None = 理想执行自算(简单分支 1,
    # 满栏从应用机器出)。
    k_exec = (max(1, int(executed.bought_count))
              if executed is not None and executed.bought_count is not None
              else None)
    scratch_b = list(pre_bench)
    scratch_d = list(pre_dep)
    merge_facts: list[tuple[str, int]] = []

    def _collect_merge(cid: str, new_star: int) -> None:
        # 升星事实采集(合并升星触发发放;纯追加,与步写无顺序耦合)
        merge_facts.append((cid, new_star))

    # 行写判据用值签名快照(签名比较仅判「是否需要落一行」)。
    _dep_pre_sig = _dep_sig(pre_dep)
    placed = bench_place(
        scratch_b, BenchSlot(kind='unit', unit=Unit(char_id=name,
                                                    star=land_star))) is not None
    if placed:
        k = k_exec if k_exec is not None else 1
        _merge_bench(scratch_b, scratch_d, on_merge=_collect_merge, gs=gs)
    else:
        k_apply = _apply_full_bench_merge_buy(
            scratch_b, scratch_d, _legacy_card(card), shop_view,
            on_merge=_collect_merge, gs=gs)
        if k_apply is None:
            return LogicOutcome(applied=False, reason='bench_full')
        k = k_exec if k_exec is not None else max(1, int(k_apply))
    # —— 免费购买闸(降本增效「接下来6次购买角色是免费的」):名字直查
    #    同形(函数内惰性取,守 kernel 反向模块级零 import 契约;免费购买
    #    族现役单成员)。购前查在场条目余量 → 免 min(k, 余量) 张、余张照
    #    付(按张计:k 张 = k 次,on_buy 购买计数先例同判据);上报时递减
    #    (非验证落地后,免战牌先例),拒买早退不触本段(序位在上方拒买
    #    return 之后 = 零虚耗余量)。全免帧零金写(扣 0 不落行);金未读帧
    #    递减照常(游戏侧余量消耗与账面观察无关),金写照跳。——
    from sr_od.application.currency_war.kernel.cw_investments import (
        STRATEGY_EFFECTS,
    )
    _free_k = 0
    _fb_spec = STRATEGY_EFFECTS.get('降本增效')
    if _fb_spec is not None:
        _free_k = gs.effects.consume_uses_up_to(_fb_spec.id, k)
    g = gs.gold.value
    if g is not None and _free_k < k:
        _w(gs.gold, int(g) - card_cost(card) * (k - _free_k), 'proj_buy_gold')
    if payload is not None:
        slots = list(payload.cards)
        while len(slots) < 5:
            slots.append(ShopSlot(kind='empty'))
        _left = k
        for _i, s in enumerate(slots):
            if _left <= 0:
                break
            if s.kind == 'content' and s.card is not None \
                    and (s.card.name or '') == name \
                    and int(s.card.star or 1) == star:
                slots[_i] = ShopSlot(kind='empty')
                _left -= 1
        _w(gs.shop, ShopPayload(cards=slots,
                                refresh_probs=(dict(payload.refresh_probs) if payload.refresh_probs is not None else None)),
           'proj_buy_payload')
    _w(gs.bench, bench_view_of_working(scratch_b, _pre_view),
       'proj_buy_place')
    if _dep_sig(scratch_d) != _dep_pre_sig:
        _w(gs.deployed, deployed_view_of_indexed(scratch_d, gs.deployed.value),
           'proj_deployed')

    # —— 升星分支(买前快照基点;整表 write_logic 后写覆盖,与简单分支
    #    两写合计的期望态由投影测试钉住,测试 M1)——
    # 升星检测的比较基点 = 本函数主工作副本
    # (scratch_b/scratch_d 已完成 bench_place/满栏合成买/级联合成的
    # 全套应用,与买前快照 pre_bench/pre_dep 恰构成 before/after 对;
    # 原二次仿真取 after 的分支随席位第二账停用删除——同一动作同一
    # 引擎,二次仿真是第二账时代形状)。
    from types import SimpleNamespace as _NS

    _star_up = detect_merge_upgrade(_NS(bench=pre_bench, deployed=pre_dep),
                                    _NS(bench=scratch_b, deployed=scratch_d))
    if _star_up:
        gs.write_logic(gs.bench,
                       bench_view_of_working(scratch_b, _pre_view),
                       produced_by='CwActionBuyCardParam',
                       evidence='proj_merge_upgrade',
                       sig=ChannelSig(
                           family='logic_action', actor=sig.actor,
                           mode='compute',
                           group_id=(f'act:{sig.actor}@'
                                     f'{gs.write_seq + 1}')))

    # —— 合并升星触发发放分支(升星分支写毕后收尾发火:引擎 A 内嵌发火会被
    #    本函数 bench/deployed 整表写覆盖,故采集在级联、发火在顶层全部
    #    写毕后——设计 §2.4 发火时序)。sig 沿动作分支 _grp_sig 口径(触发
    #    分支行与动作分支同组同窗)。best-effort:触发分支异常不阻塞上报主链
    #    (下 on_buy 回调分支同纪律)。kernel 反向模块级零 import 契约:
    #    函数内惰性取。拒买(applied=False 早退)不可达本段。——
    if merge_facts:
        try:
            from sr_od.application.currency_war.kernel.cw_env_grants import (
                check_env_merge_grants,
            )
            check_env_merge_grants(gs, tuple(merge_facts), sig=_grp_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            _log.warning(f'[cw-buy] 合并升星触发发放分支失败(不阻塞):'
                         f'{merge_facts} {e}')
        # —— 星星相印合成金条目(角色 3 星合成事件条件金):事件源 = 本函数
        #    既有 merge_facts 采集复用,过滤 3 星产物计数——满栏分支
        #    on_merge 出口已通(T-26),与 pre/after 星级差分形行为等价,
        #    采集形免二次推演、与 env 条目共用单一事件源。函数内自门 sim
        #    装配(live 零写);sim 局金位刚经 proj_buy_gold logic 写,
        #    发放 observe 相邻异通道覆盖落 sim:engine 抑制分支 = 记账路径
        #    (T-108 同拍相邻写先例,发放函数 docstring 申报)。best-effort:
        #    发放分支异常不阻塞上报主链。——
        try:
            check_strategy_star_merge_gold(gs, tuple(merge_facts),
                                           sig=_grp_sig,
                                           producer='CwActionBuyCardParam')
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            _log.warning(f'[cw-buy] 合成金腿发放分支失败(不阻塞):'
                         f'{merge_facts} {e}')
        # —— 策略卡合成触发发放条目(「合成2星2费角色时获得砂金」族,
        #    注册表 = STRATEGY_MERGE_GRANTS):事件源 = 本函数既有
        #    merge_facts 采集复用,判据 = 产物星级+费用双匹配。函数内
        #    自门 sim 装配(live 零写);与上方两条效果条目独立 try 互不短路。
        #    best-effort:发放分支异常不阻塞上报主链。——
        try:
            from sr_od.application.currency_war.kernel.cw_gain_chain import (
                check_strategy_merge_grants,
            )
            check_strategy_merge_grants(gs, tuple(merge_facts), sig=_grp_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            _log.warning(f'[cw-buy] 策略卡合成发放分支失败(不阻塞):'
                         f'{merge_facts} {e}')

    # —— 购买回调分支(获取计算完时点):简单分支 + 合成连锁 + 升星分支全毕
    #    后触发,计数归上报单点(live/sim 同源,消除落地门计数分叉);
    #    满栏一击多买按实际张数 k 计 k 次。best-effort:记录面失败不阻塞
    #    上报链(与旧落地门 bump 同纪律)。拒买(applied=False 早退)不触。
    try:
        gs.effects.on_buy(card, star, k)
    except Exception as e:  # noqa: BLE001  记录面失败不阻塞
        _log.warning(f'[cw-buy] 效果账本 on_buy 回调失败(不阻塞): {e}')

    # —— 首购经验条目(「获得本投资策略后，首次购买X费角色时，获得Y经验」
    #    族,首例 = 孪生素数):购买事实全毕后判据一次(持卡 ∧ 费用桶域
    #    ∧ 一次性一次性标志位),费用取数 = card_cost 与本函数扣价同源零新增链。
    #    函数内自门 sim 装配(live 零写,经验条观察链覆盖);一次性标志位先于状态副本写
    #    (at-most-once,失败语义见触发函数 docstring)。一击多买 k>1 同
    #    费用桶恒单发(卡面「首次」语义,与上方 on_buy 计 k 次刻意分叉,
    #    勿照抄 k)。best-effort:发放分支异常不阻塞上报主链(上方 on_buy
    #    回调分支同纪律;下方专家触发条目为零吞错状态写,分层不同勿混)。
    #    拒买(applied=False 早退)不可达本段。kernel 反向模块级零 import
    #    契约:函数内惰性取(上方惰性块同款)。——
    try:
        from sr_od.application.currency_war.kernel.cw_gain_chain import (
            check_strategy_first_buy_xp_grants,
        )
        check_strategy_first_buy_xp_grants(gs, cost=card_cost(card),
                                           sig=_grp_sig)
    except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
        _log.warning(f'[cw-buy] 首购经验腿发放分支失败(不阻塞): {e}')

    # —— 购买翻星消费一次性标志位置位(注册表 = STRATEGY_BUY_STAR_FLIP_GRANTS):
    #    翻转事实在上方落位分支确立,此处封账「下1个」消耗(applied 后
    #    尾段,消耗 = 未落一次性标志位 ∧ 购买费用匹配,无星级轴——已达标星级购买
    #    翻转 no-op 照常消耗,置一次性标志位函数 docstring 申报分轴)。满栏合成买
    #    路径翻转面不建模(落位分支不翻转)而一次性标志位照置 = 购买事件消耗语义
    #    一致面,低频边界留证。best-effort:置一次性标志位分支异常不阻塞上报主链
    #    (上方触发条目同纪律;at-most-once 失败语义见置一次性标志位函数 docstring)。
    #    拒买(applied=False 早退)不可达本段。kernel 反向模块级零 import
    #    契约:函数内惰性取(顶部惰性块同款)。——
    try:
        mark_strategy_buy_star_flip_consumed(gs, cost=card_cost(card),
                                             sig=_grp_sig)
    except Exception as e:  # noqa: BLE001  置一次性标志位分支失败不阻塞(留 log)
        _log.warning(f'[cw-buy] 购买翻星置闩分支失败(不阻塞): {e}')

    # —— 金币花费事件置位(存款回报条件输入,fields.md §3.3.9):applied=True
    #    主路径尾段(与 on_buy 回调同区),拒买 bench_full 早退不可达本段;
    #    非免费帧才置位(同函数刷新通道「付费刷新非免费帧」同判——免费
    #    购买零金变动,误置位会让存款回报的条件输入失真);同节点多笔判
    #    等跳写收敛在 mark_gold_spent 内。——
    if _free_k < k:
        mark_gold_spent(gs, produced_by='CwActionBuyCardParam', sig=_grp_sig)

    # —— 条件形态专家触发分支(「首次获得 X 时,顾问入商店」族,首例 =
    #    特邀专家:银狼,设计 = 迭代 2026-09-23-invest-effects-calc T-42
    #    §2.3):购买事实确立后判据一次——购买 = 银狼LV.999 的现役主流
    #    获得渠道(3 费档基础池恒可刷),插入位置与 on_buy 回调分支同位
    #    (简单分支 + 合成连锁 + 升星分支全毕后,拒买 applied=False 早退
    #    不可达本段);rand=False = 购买全链确定面。状态写沿主链零吞错
    #    (判据内含条件写,与上方 on_buy 记录面 best-effort 分层——记录
    #    可弃,状态写不可静默失败)。kernel 反向模块级零 import 契约:
    #    函数内惰性取(上方惰性块同款)。
    expert_conditional_trigger(gs, name, rand=False, sig=_grp_sig,
                               evidence='buy_card:expert_trigger')
    # (事实事件广播已停用:sim
    #  呈现/登记经状态容器值回调与问询时点呈现检查承载。)
    return LogicOutcome(applied=True, bought_count=k)
