"""tracking 对账公共层(观察冲突审计 P0 #12,2026-08-16)。

两处对账实现(deploy_bench._reconcile_tracking / prep_director._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log

# 下行守卫标定常量(值单一源 = 注册表;cw_reconcile 只消费)
from sr_od.application.currency_war.kernel.cw_registry import (
    HP_LOSS_CAP_P100_BY_NODE,
    HP_SUSPECT_CONFIRM_FRAMES,
    HP_SUSPECT_WINDOW_NODES,
    HP_ZERO_LOSS_NODE_TYPES,
)


def _merge_equips(old_list, new_list) -> list:
    """对账合并语义(W209g 断点①修法,ADR-0387 追加):char_id 续接保留 equips。

    断点(run 26 实锤):旧版 ``session.tracked_deployed = list(deployed)``
    整批替换,新读对象 equips=[] 默认 → ``deploy_bench._snapshot_equips_into_
    tracking`` 写入的装备在下次对账即被冲(run 26 布局错乱→纠漂狂刷→反复
    清零,decisions.jsonl 希儿装备闪烁实证:round6 三条快照仅一条有装备)。

    修法:按 char_id 把**旧 tracking 的 equips 续接到新读对象**(同名多副本
    逐个配对消耗,次序无关);新读自带的非空 equips(画面真值,如 deploy_bench
    快照后传参)优先保留不覆盖;旧有新无(角色离场)自然丢弃。
    """
    old_eq: dict[str, list[list[str]]] = {}
    for bc in (old_list or []):
        if bc is not None and bc.char_id:
            old_eq.setdefault(bc.char_id, []).append(
                list(getattr(bc, 'equips', None) or []))
    out = []
    for bc in (new_list or []):
        if bc is not None and getattr(bc, 'char_id', ''):
            if not getattr(bc, 'equips', None):
                pools = old_eq.get(bc.char_id)
                if pools:
                    bc.equips = pools.pop(0)   # 同名逐个配对消耗
        out.append(bc)
    return out


def reconcile_tracking(session, bench, deployed, screen=None, *,
                       source: str = 'reconcile', ctx=None) -> bool:
    """tracking 对账统一入口:新 SIFT 读 vs 旧 session tracking,守卫后写回。

    守卫(审计 #11/#12):
    - **双空读守卫**(M14 实锤):新读 bench/deployed 双空 + 前值非空 = 疑 SIFT 过渡帧
      → 保旧不写(空读是读失败,不是「板真没了」);
    - **漂移留证**:新旧不一致 → obs_conflict(裁决=采新-对账纠漂)+ [cw!] 日志;
      一致 → 静默(常态无噪声)。

    ⚖️ star 回退停机钩子(用户 2026-08-17 指示):买牌 merge 预估升星(tracking)后,实机
    read_star 回读更低 = 星级识别可疑(read_star 漏金星/星区被遮挡)——**star≥2 的回退连续
    2 个节点仍现 → 停机保画面排查**(第 1 次可能是升星特效遮挡过渡帧,一节点内消;防抖
    同 M35 shop_unknown 模式)。sentinel 自描述(删钩子位置/排查项),防「孤儿残留」误判
    (r17-r31 教训:反复出现的 sentinel 必有活生产者,grep 写入者)。

    Args:
        session: StrategySession(tracked_bench_chars/tracked_deployed 被写回)
        bench/deployed: 新读 list[BenchChar](None = 读失败,不写该侧)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)
        ctx: SrContext(传则 star 回退停机走 run_context.stop_running;None = 离线/测试只留证)

    Returns:
        是否发生了写回(False = 守卫拦截保旧)
    """
    if session is None:
        return False
    _pending_evidence: list[tuple] = []   # r336:留证队列(对账位统一消费)
    # W68 根修(ADR-0316 形状契约):tracked_bench_chars 在买牌后被
    # mutate_bench_deployed→pad_bench 就地 pad 成定长 9 槽**含 None**
    # (槽位表语义写入端)——本消费端假设紧凑无 None 是双写冲突,曾致
    # 验证局 206 次 AttributeError 崩溃-重派循环(2026-08-25 实录)。
    # 守卫:跳过 None 槽(空槽在对账语义里=无信息,不是冲突)。
    old_b = [(bc.char_id, bc.star) for bc in session.tracked_bench_chars
             if bc is not None]
    old_d = [(bc.char_id, bc.star) for bc in session.tracked_deployed
             if bc is not None]
    if not bench and not deployed and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        return False
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    # star 回退留证(观察冲突审计 #13,2026-08-16):同名 star 下降(如 2★读回 1★)= read_star
    # 漏金星 或 卖后重买边缘场景;不保旧(审计:保旧不安全)只留证统计毒化率。
    _old_stars = {(n, s) for n, s in old_b + old_d if n}
    _new_stars = {(n, s) for n, s in new_b + new_d if n}
    _reg = dict(getattr(session, 'star_regression_count', {}) or {})
    # ⚖️ star 回退防抖(2026-08-18 离线复现实证治本):274 张存证全量重放 —— 回退角色
    # 40/40 在场且 36/40 **同图重读为 2★**(live 读 1★)→ 真根因 = 3合1 合成动画窗口
    # 识别(read_star 在特效期读 1,存证帧在动画后半段星已显)——**推翻 r17「SIFT 身份
    # 错配」结论**。旧版回退即采新写回 → 动画窗 1★ 毒化 tracking,下一帧又纠回(往返抖;
    # r34 停机钩子有同款防抖所以停机侧无误触,但对账侧漏了)。修:首次回退不写回
    # (该角色 star 保旧),**连续第二次仍回退**才确认(真卖后重买/真识别问题)。
    _pend = dict(getattr(session, 'star_pending_regression', {}) or {})
    for _n, _s in _new_stars:
        # 同名多星共存时取**最高旧星**(r6 review 小瑕疵:set 无序 next() 任意项;
        # 回退判定应对 max——2★+1★ 共存读回 1★ 是回退 vs 2★,不是 vs 任意)
        _old_s = max((_os for _on, _os in _old_stars if _on == _n), default=None)
        if _old_s is not None and _s < _old_s:
            # 61-A1/72-A1 修(银狼升费机制豁免):银狼LV.999 3★拖上场→变4费1★(升费签名
            # =2★→1★×2-3 与 3★→2★ 成对同刻,文档记载的正常机制,非识别失败);
            # merge 修复实证不消银狼回退(48条/224局全为机制性),豁免防每2局误停一次
            if _n.startswith('银狼') and _old_s - _s == 1:
                log.info(f'[cw][{source}] star 回退豁免:{_n} {_old_s}★→{_s}★(升费机制,非识别失败)')
                continue
            _seen = _pend.get(_n, 0)
            if _seen == 0:
                # 首次:疑合成动画窗(特效遮挡第2星)——不写回,star 保旧防毒化;
                # 下一帧读回正常即自愈(与 r34 停机钩子「连续 2 节点」同语义)。
                _pend[_n] = 1
                log.info(f'[cw][{source}] star 回退防抖:{_n} {_old_s}★→{_s}★(疑3合1动画窗)'
                         f'→ 本帧保旧 {_old_s}★,下帧确认')
                _conflict('star', _old_s, _s, screen, verdict='保旧-回退防抖(疑合成动画窗,下帧确认)',
                          source=source, char=_n)
                # 保旧只抬**一个**副本(r58 review P1:同名多副本共存[2★+1★]时,循环会
                # 把所有 star==_s 的副本集体抬到旧最大星 → 真实 1★ 副本变假 2★,污染
                # merge/卖牌决策;数量守恒 = 只抬第一个命中)。
                _bumped = False
                for _lst in (bench, deployed):
                    if not _lst or _bumped:
                        continue
                    for _bc in _lst:
                        if _bc.char_id == _n and _bc.star == _s:
                            _bc.star = _old_s   # 保旧(动画窗读数不进 tracking)
                            _bumped = True
                            break
            else:
                # W292 帧态门(ADR-0420):采新确认前先判合成特效帧——星爆动画/
                # 拖拽过渡窗可持续 ≥2 帧,「连续 2 次」防抖会被窗内第 2 帧假确认
                # (W285 star 层抽样 2/2 采新帧全错实证)。特效帧 = 物理不可信窗:
                # 保旧同首次分支,**防抖计数冻结不推进**(非清零——动画结束后的
                # 干净回退帧仍走本分支确认;门漏检时退化为 W292 前防抖行为)。
                _eff = False
                if screen is not None:
                    from sr_od.application.currency_war.cw_identity_obs import (
                        is_merge_effect_frame,
                    )
                    _eff = is_merge_effect_frame(screen)
                if _eff:
                    log.info(f'[cw][{source}] star 回退帧态门:{_n} {_old_s}★→{_s}★'
                             f'(合成特效帧,读数不可信)→ 保旧 {_old_s}★,防抖冻结')
                    _conflict('star', _old_s, _s, screen,
                              verdict='保旧-合成特效帧态门(采新确认被拦,防抖冻结;'
                                      'W292/ADR-0420)',
                              source=source, char=_n)
                    _bumped = False
                    for _lst in (bench, deployed):
                        if not _lst or _bumped:
                            continue
                        for _bc in _lst:
                            if _bc.char_id == _n and _bc.star == _s:
                                _bc.star = _old_s   # 保旧(特效帧读数不进 tracking)
                                _bumped = True
                                break
                else:
                    # 连续第二次:确认真回退(卖后重买/真识别问题)→ 采新写回。
                    log.warning(f'[cw!][{source}] star 回退确认:{_n} {_old_s}★→{_s}★(连续2次,真回退)')
                    _conflict('star', _old_s, _s, screen, verdict='采新-回退确认(连续2次)',
                              source=source, char=_n)
                    # ⚖️ star 回退留证(2026-08-18 r17 降级:原停机钩子三度触发阻断实跑——排查结论
                    # 已存档 cw_dev/live_round11_diagnosis.md;降级为高频留证(每 5 次回退存一张证,
                    # 不 stop),排查证据流保留,goal 实跑可推进。SIFT 身份修复后本段连同 _star_stop_hook 删)。
                    # r336(批次4:钩子归位):留证调用从 reconcile 深处
                    # 改**队列记录**——真正落盘由 director 对账位统一
                    # 触发(消费统一观察;r330 帧态门在 _star_stop_hook
                    # 内,双层保护)。reconcile 只登记,不做 IO。
                    if _old_s >= 2:
                        _reg[_n] = _reg.get(_n, 0) + 1
                        _pending_evidence.append((_n, _old_s, _s, source))
        elif _n in _pend or _n in _reg:
            _pend.pop(_n, None)   # 读回恢复(或超预估)→ 清防抖(自愈;r79:pop 防抖——
            # 名字可能只在 _reg 不在 _pend,原 del 抛 KeyError 打断备战环,实锤 丹恒·饮月)
            _reg.pop(_n, None)   # 连续回退计数同步清零(恢复语义)
    # 离场清除 pending(r58 review P2①:角色卖出/上场后 _pend 残留 → 该角色下次登场时
    # 单次动画误读被误判「连续第二次确认」)。只在两侧都真读(非 None)时清 —— None 侧
    # 读失败不代表离场。双空读已在上方守卫早退,这里 old 非空 + 双真读 = 真离场。
    if _pend and bench is not None and deployed is not None:
        _gone = [n for n in _pend if n not in {x for x, _ in _new_stars}]
        for n in _gone:
            del _pend[n]
    session.star_pending_regression = _pend
    session.star_regression_count = _reg
    # 防抖可能原地改 bench/deployed 副本 star(r58 review P2②)→ 纠漂判定与日志必须
    # 取**防抖后**快照(旧快照记的是改前值,误导排障)。W68:bench/deployed 入参
    # 是 SIFT 紧凑列表(无 None),但入参若被上游 pad 过则守卫之(同形状契约)。
    new_b = [(bc.char_id, bc.star) for bc in (bench or []) if bc is not None]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or []) if bc is not None]
    drifted = (old_b != new_b) or (old_d != new_d)
    if bench is not None:
        session.tracked_bench_chars = _merge_equips(session.tracked_bench_chars, bench)
    if deployed is not None:
        # ADR-0392:tracked_deployed 是槽位表——_merge_equips 出紧缩占用序,
        # 写回前经 deployed_from_compact 转槽位表(单一源适配)。
        from sr_od.application.currency_war.cw_state import deployed_from_compact
        session.tracked_deployed = deployed_from_compact(
            _merge_equips(session.tracked_deployed, deployed))
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
    # r336(批次4:钩子归位)——「对账&hook」位统一消费留证
    # 队列(原 reconcile 深处散调;计数节流每 5 次留一张不变,
    # _star_stop_hook 内 r330 帧态门保留=双层保护)。
    for _n, _o_s, _s, _src in _pending_evidence:
        if _reg.get(_n, 0) >= 2 and ctx is not None and _reg[_n] % 5 == 0:
            _star_stop_hook(ctx, session, _n, _o_s, _s, screen, _src,
                            stop_run=False)
    return True


#: ADR-0282:hp 同域大幅上行留证阈值。HP 只降不升(结算语义,insights 实证),
#: 备战现读较 last_hp_real 上行 ≥ 此值 = 疑 OCR 误读/特殊回复 → obs_conflict 留证
#: (仍采新:真值帧是物理读数,判读侧消费证据)。
HP_REAL_JUMP_CONFLICT: int = 30


def _battle_fact_between(session, node_t: int,
                         node_lo: int | None) -> tuple[str, str | None]:
    """查「上一真值帧 → 本帧」窗内最新已观测战斗事实(ADR-0431)。

    事实源 = ``session.performance.history``(RoundOutcome 行,结算屏观测
    回路写入)。返回 (fact, node_type):fact ∈ 'win'(killed=True,v5 权威
    口径)/ 'zero'(零损节点型:奖励/补给,无战斗损血机制)/ 'loss'
    (有战斗、非胜)/ 'none'(窗内无已观测战斗行)。节点型未标定不在此
    分类,由调用方按无标定处理。

    node_lo = 上一真值帧节点号(session.last_hp_real_node);None = 旧真值
    无节点锚(升级过渡),窗口放宽为「≤ 本帧的任意 outcome 行」——保守向
    采信分支倾斜(不把真掉血误判为无战斗事实),残留面由复现通道兜底。
    """
    perf = getattr(session, 'performance', None)
    hist = getattr(perf, 'history', None) or []
    best = None
    best_t = -1
    for o in hist:
        t_o = (int(getattr(o, 'plane', None) or 1) - 1) * 9 \
            + int(getattr(o, 'round_num', None) or 0)
        if t_o > node_t:
            continue
        if node_lo is not None and t_o <= node_lo:
            continue
        if t_o >= best_t:
            best, best_t = o, t_o
    if best is None:
        return 'none', None
    nt = getattr(best, 'node_type', None)
    if nt in HP_ZERO_LOSS_NODE_TYPES:
        return 'zero', nt
    if getattr(best, 'killed', None) is True:
        return 'win', nt
    return 'loss', nt


def _reject_down(session, old: int, new_hp: int, node_t: int, screen,
                 source: str) -> tuple[int, bool]:
    """下行拒信 + 复现确认通道状态机一步(ADR-0431;返回沿用 (o, False))。

    - 首拒/换候选/超窗 → 建或重置 suspect(count=0,计**拒信后**的复现
      真值帧数),留证;
    - 同候选再现 → count+1;累计达 HP_SUSPECT_CONFIRM_FRAMES →
      确认真掉血,采新写回并出窗(返回 (n, True));
    - 留证节流:同候选只首帧 + 每 5 次一条(同 _conflict 既有口径),
      防毒化窗内遥测刷屏。

    采新确认帧返回 (n, True) 的语义:确认后的读数是「跨帧复现的物理
    读数」,等同真值帧——出窗即恢复正常采信路径。
    """
    sus = getattr(session, 'hp_suspect', None)
    if sus is not None and sus.get('value') == new_hp \
            and node_t - int(sus.get('node', node_t)) <= HP_SUSPECT_WINDOW_NODES:
        rep = int(sus.get('count', 0)) + 1
        sus['count'] = rep
        if rep >= HP_SUSPECT_CONFIRM_FRAMES:
            log.warning(
                f'[cw!][{source}] hp 下行确认真掉血:{old} → {new_hp}'
                f'(拒信后连续 {rep} 真值帧低位复现)→ 采新出窗')
            session.hp_suspect = None
            session.last_hp_real = new_hp
            session.last_hp_real_node = node_t
            return new_hp, True
    else:
        rep = 0
        sus = {'value': new_hp, 'node': node_t, 'count': 0}
        session.hp_suspect = sus
    if rep == 0 or (rep + 1) % 5 == 0:
        _conflict('hp', old, new_hp, screen,
                  verdict=('拒信-下行疑OCR读低(无合法战斗事实背书该幅度下行;'
                           'ADR-0431:沿用旧值+复现确认通道,2 真值帧低位一致'
                           '才采新;处理:频发→查血量区遮挡形态)'),
                  source=source, node_t=node_t, direction='down',
                  suspect_count=rep)
    log.info(f'[cw][{source}] hp 下行拒信:{old} → {new_hp}(疑OCR读低)→ '
             f'沿用 {old},复现计数 {rep}/{HP_SUSPECT_CONFIRM_FRAMES}')
    return old, False


def reconcile_hp(session, new_hp: int | None, screen=None, *,
                 source: str = 'read_game_state',
                 node_t: int | None = None) -> tuple[int, bool]:
    """hp 对账统一入口(ADR-0282,用户三层设计·对账层;run165501 毒化案根治)。

    hp 与 bench/deployed 不同源(SIFT 双源),它的「读失败」形态 = shop 开态
    血量区物理为空(read_hp_opt → None)——**None ≠ 漂移是读失败,保旧不写**
    (复用 ``reconcile_tracking`` 双空读守卫思想,2026-08-03 安全设计「读不到
    兜底 100」在遥测/决策侧毒化的根治)。

    三层分工(用户原话要点):
    - **对账层(本函数)**:读不到 → 沿用 ``session.last_hp_real``(保旧不写);
      真值帧(非 None)才写回 last_hp_real(=「session 更新只在关态真值帧」,
      shop 开态读不到自然不写);新读非 None 且同域大幅上行(HP 只降不升)
      → obs_conflict 留证;真值帧下行须过「幅度 × 战斗事实」联合守卫
      (ADR-0431:win/零损帧下行一律拒信,loss 帧按损血谱 p100 分档采信,
      无战斗事实帧拒信+复现确认通道 ≤2 节点自愈)。
    - **决策层**:消费本函数返回的(决策用 hp, 是否真读)——沿用真值比假 100
      安全(低血先验触发保血方向对);全无真值(开局)才兜底 100。
    - **记录层**:遥测按返回的 readable 位分字段记(hp_readable=False=读不到,
      hp=沿用值),不把兜底/沿用值混进「真 100」。

    Args:
        session: StrategySession(last_hp_real/last_hp_real_node/hp_suspect 被写回;
            None=离线/测试,只透传)
        new_hp: read_hp_opt 现读(None=读不到,shop 开态血量区空)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记
        node_t: 全局节点号((plane-1)*9+round;下行守卫的帧间事实窗锚 +
            hp_trusted 帧龄门锚。None = 守卫不介入(退 ADR-0282 行为,
            兼容离线/既有调用))

    Returns:
        (决策用 hp, 是否真读):真值帧=(新读, True);读不到=(last_hp_real, False);
        全无真值(开局)=(100, False) 健康先验兜底;被下行守卫拒信的帧
        =(旧值, False)(SUSPECT 态,ADR-0431)。
    """
    if new_hp is None:
        old = getattr(session, 'last_hp_real', None) if session is not None else None
        if old is not None:
            log.info(f'[cw][{source}] hp 读不到(shop 开态/血量区空)→ '
                     f'沿用 last_hp_real={old}(保旧不写,ADR-0282)')
            return old, False
        return 100, False   # 开局全无真值 → 兜底 100(健康先验;readable=False 披露)
    old = getattr(session, 'last_hp_real', None) if session is not None else None
    if old is not None and new_hp - old >= HP_REAL_JUMP_CONFLICT:
        _conflict('hp', old, new_hp, screen,
                  verdict=('留证-同域大幅上行(HP只降不升,疑OCR误读/特殊回复;'
                           '处理:采新现读真值帧;频发→查血量区遮挡/误读)'),
                  source=source, node_t=node_t)
    # —— 下行守卫(ADR-0431:幅度 × 战斗事实联合判据)——
    # HP 的合法下行只有「帧间发生了败战且幅度在损血谱内」一种物理来源;
    # 误读读低不属于任何合法类。node_t=None(离线/旧调用方)守卫不介入,
    # 既有行为逐位零漂移;上行/持平帧不经本分支。
    if session is not None and old is not None and new_hp < old \
            and node_t is not None:
        fact, fact_nt = _battle_fact_between(
            session, node_t, getattr(session, 'last_hp_real_node', None))
        _delta = old - new_hp
        _allow = False
        if fact in ('win', 'zero'):
            _allow = False   # 胜战/零损节点不损血是机制事实,任何下行都无背书
        elif fact == 'loss':
            _cap = HP_LOSS_CAP_P100_BY_NODE.get(fact_nt)
            # 节点型未标定(精英/巨星等,无 p100 谱)→ 不拍值,走拒信+复现通道
            _allow = _cap is not None and _delta <= _cap
        # fact == 'none'(结算漏采/telemetry 断/shop 开态 OCR 恢复):
        # 物理上不存在合法下行,无幅度豁免;真掉血经复现通道 ≤2 节点自愈。
        if not _allow:
            return _reject_down(session, old, new_hp, node_t, screen, source)
    if session is not None:
        session.last_hp_real = new_hp
        session.last_hp_real_node = node_t
        # 采新即出窗:任何被采信的真值帧(含误读确认帧读回旧值)都否定
        # 活跃 suspect 的候选毒性。
        session.hp_suspect = None
    return new_hp, True


def _conflict(field: str, old, new, screen, *, verdict: str, source: str,
              **ctx) -> None:
    """obs_conflict 封装(best-effort,导入失败/异常不阻塞)。**ctx 透传(如 char=)。"""
    try:
        from sr_od.application.currency_war.cw_observe import obs_conflict
        obs_conflict(field, old, new, screen, verdict=verdict, source=source, **ctx)
    except Exception:  # noqa: BLE001  留证 best-effort
        pass


def _star_stop_hook(ctx, session, char: str, old_star: int, new_star: int,
                    screen, source: str, stop_run: bool = True) -> None:
    """star 回退留证钩子(用户 2026-08-17 指示;star≥2 回退触发)。

    r17 降级(2026-08-18):排查已尽策略侧所能(结论存 cw_dev/live_round11_diagnosis.md:
    根因在 SIFT 身份域,非读星)——stop_run=False 时只留证截图不停机(证流保留,
    实跑可推进);SIFT 身份修复后本段整删。
    停机保备战画面供排查星级识别(read_star 漏金星?星区被特效/光标遮挡?SIFT 身份错配?)。
    sentinel 自描述(r17-r31 教训:内容含「这是自己的钩子停的+删除位置」,防误判孤儿/外部拦截)。
    r330 帧态门:留证/停机只在备战类精准帧(is_prep_like_frame)
    ——动画帧上的星读回退本就常发(升星特效窗),不留证。
    """
    from datetime import datetime
    from pathlib import Path

    from one_dragon.utils import log_utils
    try:
        # r330 帧态门:非备战类精准帧直接跳过(动画帧星读回退
        # 常发,留证只是噪声)。screen=None(测试/无帧上下文)
        # 不拦——留证本身是离线安全操作。
        if screen is not None:
            from sr_od.application.currency_war.cw_obs_core import (
                is_prep_like_frame,
            )
        if screen is not None and ctx is not None \
                and not is_prep_like_frame(ctx, screen):
            return
        _p = Path('.debug/temp/currency_war/star_regression_hook.flag')
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(
            f'[{datetime.now().isoformat(timespec="seconds")}] star 回退{"停机" if stop_run else "留证(r17 降级,不阻断)"}——'
            f'{char} 预估 {old_star}★(买牌 3合1 merge)多次读回 '
            f'{new_star}★,星级/身份识别可疑。\n'
            f'处理流程(r100k 补):\n'
            f'1. 对截图 shots/star_regress_{char}_*.png 肉眼核星级(金框/角标);\n'
            f'2. ①星读对预估错(merge 逻辑)→ 修 cw_reconcile 预估;②星读错(read_star)\n'
            f'   → 核星区遮挡/光标;③SIFT 身份错配 → 核 portrait 模板;\n'
            f'3. 修好后删钩子:cw_reconcile.py 搜「_star_stop_hook」整段 + 删本 flag。\n'
            f'画面态:备战(角色在板上,星区可见);来源:{source}',
            encoding='utf-8')
        try:
            import cv2
            if screen is not None and screen.size:
                _ok, _arr = cv2.imencode('.png', cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))
                if _ok:
                    _arr.tofile(str(Path('.debug/temp/currency_war/shots')
                                    / f'star_regress_{char}_{datetime.now():%H%M%S}.png'))
        except Exception:  # noqa: BLE001  截图 best-effort
            pass
        log_utils.log.warning(
            f'[cw-hook] star 回退{"停机" if stop_run else "留证(r17 降级,不阻断)"}:'
            f'{char} 预估{old_star}★×多节点读回{new_star}★ → '
            f'保画面排查星级识别(sentinel: star_regression_hook.flag;修好删 _star_stop_hook)')
        if stop_run:
            ctx.run_context.stop_running(reason='hook:star_regression')
    except Exception:  # noqa: BLE001  停机失败不阻塞对账写回
        pass
