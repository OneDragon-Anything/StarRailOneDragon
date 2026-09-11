"""tracking 对账公共层(观察冲突审计 P0 #12)。

两处对账实现(deploy_bench._reconcile_tracking / cw_screen_prep._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of

# 下行守卫标定常量(值单一源 = 注册表;cw_reconcile 只消费)
from sr_od.application.currency_war.kernel.cw_opening_hp import opening_hp_prior
from sr_od.application.currency_war.kernel.cw_registry import (
    HP_LOSS_CAP_P100_BY_NODE,
    HP_SUSPECT_CONFIRM_FRAMES,
    HP_SUSPECT_WINDOW_NODES,
    HP_ZERO_LOSS_NODE_TYPES,
)

# 合成特效帧态门注入槽(分包依赖矩阵禁 kernel→obs 直依):kernel 只持槽位,
# 实现由 app 装配点(decision_assembly.install_obs_ports)从 obs 桶注入。
# 缺省关(None)= 门放行,回退直接走「连续 2 次确认采新」——与门函数自身
# 「screen=None → False 不拦」的 best-effort 语义同向,不引入新故障面。
_IS_MERGE_EFFECT_FRAME = None


def set_merge_effect_gate(fn) -> None:
    """注入合成特效帧态门实现(obs 桶 ``is_merge_effect_frame``;生产武装点接通)。"""
    global _IS_MERGE_EFFECT_FRAME
    _IS_MERGE_EFFECT_FRAME = fn


def _merge_equips(old_list, new_list) -> list:
    """对账合并语义(ADR-0387,对账覆盖装备):char_id 续接保留 equips。

    断点实锤:整批替换 ``exec_state_of(session).tracked_deployed = list(deployed)``
    时新读对象 equips=[] 默认 → ``deploy_bench._snapshot_equips_into_
    tracking`` 写入的装备在下次对账即被冲(希儿装备闪烁实证——当年经
    决策行快照显影:round6 三条快照仅一条有装备)。

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
    (教训:反复出现的 sentinel 必有活生产者,grep 写入者)。

    Args:
        session: StrategySession(tracked_bench_chars/tracked_deployed 被写回)
        bench/deployed: 新读 list[BenchChar](None = 读失败,不写该侧)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)
        ctx: SrContext(传则 star 回退停机走 run_context.stop_running;None = 离线/测试只留证)
        合成特效帧态门(采新确认前判别):实现经模块级 ``set_merge_effect_gate`` 注入
        (分包矩阵禁 kernel→obs 直依);缺省关 = 门放行,走既有连续 2 次确认主干。

    Returns:
        是否发生了写回(False = 守卫拦截保旧)
    """
    if session is None:
        return False
    _pending_evidence: list[tuple] = []   # 留证队列(对账位统一消费)
    # 形状契约(ADR-0316):tracked_bench_chars 在买牌后被
    # mutate_bench_deployed→pad_bench 就地 pad 成定长 9 槽**含 None**
    # (槽位表语义写入端)——本消费端若假设紧凑无 None 即双写冲突
    # (曾致验证局数百次 AttributeError 崩溃-重派循环)。
    # 守卫:跳过 None 槽(空槽在对账语义里=无信息,不是冲突)。
    old_b = [(bc.char_id, bc.star) for bc in exec_state_of(session).tracked_bench_chars
             if bc is not None]
    old_d = [(bc.char_id, bc.star) for bc in exec_state_of(session).tracked_deployed
             if bc is not None]
    if not bench and not deployed and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        return False
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    # star 回退留证(观察冲突审计 #13):同名 star 下降(如 2★读回 1★)= read_star
    # 漏金星 或 卖后重买边缘场景;不保旧(审计:保旧不安全)只留证统计毒化率。
    _old_stars = {(n, s) for n, s in old_b + old_d if n}
    _new_stars = {(n, s) for n, s in new_b + new_d if n}
    _reg = dict(getattr(exec_state_of(session), 'star_regression_count', {}) or {})
    # ⚖️ star 回退防抖(274 张存证全量重放实证:回退角色 40/40 在场且
    # 36/40 **同图重读为 2★**(live 读 1★)→ 真根因 = 3合1 合成动画窗
    # 识别(read_star 在特效期读 1,存证帧在动画后半段星已显),非 SIFT
    # 身份错配)。回退即采新写回 → 动画窗 1★ 毒化 tracking,下一帧又纠回
    # (往返抖)。修法:首次回退不写回(该角色 star 保旧),**连续第二次
    # 仍回退**才确认(真卖后重买/真识别问题)。
    _pend = dict(getattr(session, 'star_pending_regression', {}) or {})
    for _n, _s in _new_stars:
        # 同名多星共存时取**最高旧星**(set 无序遍历取项任意,回退判定
        # 应对 max——2★+1★ 共存读回 1★ 是回退 vs 2★,不是 vs 任意)
        _old_s = max((_os for _on, _os in _old_stars if _on == _n), default=None)
        if _old_s is not None and _s < _old_s:
            # 银狼升费机制豁免:银狼LV.999 3★拖上场→变4费1★(升费签名
            # =2★→1★×2-3 与 3★→2★ 成对同刻,文档记载的正常机制,非识别失败);
            # merge 修复实证不消银狼回退(48条/224局全为机制性),豁免防每2局误停一次
            if _n.startswith('银狼') and _old_s - _s == 1:
                log.info(f'[cw][{source}] star 回退豁免:{_n} {_old_s}★→{_s}★(升费机制,非识别失败)')
                continue
            _seen = _pend.get(_n, 0)
            if _seen == 0:
                # 首次:疑合成动画窗(特效遮挡第2星)——不写回,star 保旧防毒化;
                # 下一帧读回正常即自愈(与停机钩子「连续 2 节点」防抖同语义)。
                _pend[_n] = 1
                log.info(f'[cw][{source}] star 回退防抖:{_n} {_old_s}★→{_s}★(疑3合1动画窗)'
                         f'→ 本帧保旧 {_old_s}★,下帧确认')
                _conflict('star', _old_s, _s, screen, verdict='保旧-回退防抖(疑合成动画窗,下帧确认)',
                          source=source, char=_n)
                # 保旧只抬**一个**副本(同名多副本共存[2★+1★]时,循环会
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
                # 帧态门(ADR-0420):采新确认前先判合成特效帧——星爆动画/
                # 拖拽过渡窗可持续 ≥2 帧,「连续 2 次」防抖会被窗内第 2 帧假确认
                # (star 层抽样 2/2 采新帧全错实证)。特效帧 = 物理不可信窗:
                # 保旧同首次分支,**防抖计数冻结不推进**(非清零——动画结束后的
                # 干净回退帧仍走本分支确认;门漏检时退化为引入本门前的防抖行为)。
                _eff = False
                if screen is not None and _IS_MERGE_EFFECT_FRAME is not None:
                    _eff = _IS_MERGE_EFFECT_FRAME(screen)
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
                    # ⚖️ star 回退留证(排查结论存档 cw_dev/live_round11_diagnosis.md
                    # :根因在 SIFT 身份域,非读星;降级为高频留证——每 5 次回退存
                    # 一张证,不 stop,排查证据流保留。SIFT 身份修复后本段连同
                    # _star_stop_hook 删)。
                    # 钩子归位:留证调用经**队列记录**——真正落盘由 director 对账位
                    # 统一触发(消费统一观察;帧态门在 _star_stop_hook
                    # 内,双层保护)。reconcile 只登记,不做 IO。
                    if _old_s >= 2:
                        _reg[_n] = _reg.get(_n, 0) + 1
                        _pending_evidence.append((_n, _old_s, _s, source))
        elif _n in _pend or _n in _reg:
            _pend.pop(_n, None)   # 读回恢复(或超预估)→ 清防抖(自愈;pop 而非 del——
            # 名字可能只在 _reg 不在 _pend,del 抛 KeyError 会打断备战环,实锤 丹恒·饮月)
            _reg.pop(_n, None)   # 连续回退计数同步清零(恢复语义)
    # 离场清除 pending(角色卖出/上场后 _pend 残留 → 该角色下次登场时
    # 单次动画误读被误判「连续第二次确认」)。只在两侧都真读(非 None)时清 —— None 侧
    # 读失败不代表离场。双空读已在上方守卫早退,这里 old 非空 + 双真读 = 真离场。
    if _pend and bench is not None and deployed is not None:
        _gone = [n for n in _pend if n not in {x for x, _ in _new_stars}]
        for n in _gone:
            del _pend[n]
    session.star_pending_regression = _pend
    exec_state_of(session).star_regression_count = _reg
    # 防抖可能原地改 bench/deployed 副本 star → 纠漂判定与日志必须
    # 取**防抖后**快照(改前快照会误导排障)。bench/deployed 入参
    # 是 SIFT 紧凑列表(无 None),但入参若被上游 pad 过则守卫之(同形状契约)。
    new_b = [(bc.char_id, bc.star) for bc in (bench or []) if bc is not None]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or []) if bc is not None]
    drifted = (old_b != new_b) or (old_d != new_d)
    # 布局代次写回事实位(T-308 S3):bench 侧是否实际写回(健康门通过)。
    # drifted 分支据此决定是否递增 bench_layout_epoch——deployed 驱动的
    # 纠漂不递增(bench 布局未变);误递增无害(重播种幂等)、漏递增有害
    #(布局变化无人知晓),故取「bench 写回 ∧ drifted」。
    _bench_written = False
    if bench is not None:
        # T-308/ADR-0646 S2 主修:写回经 bench_from_compact 重建槽位表——
        # 与下方 deployed 侧 deployed_from_compact 同构(ADR-0392 单一源
        # 适配先例,bench 侧为同构修法补齐,非发明新机制)。SIFT 读的
        # slot = 画面物理槽号(read_bench_chars→identify_slots 逐槽赋值,
        # 与读序同帧同源;亲读结论见 ADR-0646),重建后列表布局=画面布局、
        # slot=下标+1 天然一致,紧凑态从写入端消失,两域播种自动同源——
        # 消灭 tracked 下标布局 vs BenchChar.slot 脱节的持续制造点
        #(本函数旧写回直拷 SIFT 紧凑列表,违反 ADR-0316 形状契约)。
        # 前置槽号健康门(与 cw_shop_action_ops._reseed_bench_layout 同式):
        # 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY——把 bench_from_compact 对
        # 无效槽号的静默 fallback(冲突走 bench_place 首空槽)在写回点升级
        # 为显式拒绝,防脏读数固化为形状自洽的槽位表(布局错而守卫恒过,
        # 比现状更难发现)。违者拒绝写回保旧+留证:经 _conflict 通道
        #(obs_conflict 行经旁路进缺陷台账;kernel 层落账走出口约束,
        # 与 _reseed 的 telemetry kind 行分属两层,语义等价留证)。
        from sr_od.application.currency_war.kernel.cw_state import (
            BENCH_CAPACITY,
            bench_from_compact,
        )
        _slots = [bc.slot for bc in bench if bc is not None]
        _healthy = (all(isinstance(s, int) and 1 <= s <= BENCH_CAPACITY
                        for s in _slots)
                    and len(set(_slots)) == len(_slots))
        if _healthy:
            exec_state_of(session).tracked_bench_chars = bench_from_compact(
                _merge_equips(exec_state_of(session).tracked_bench_chars, bench))
            _bench_written = True
        else:
            log.warning(f'[cw!][{source}] 对账写回拒绝:bench 槽号不健康'
                        f'(唯一∧1..{BENCH_CAPACITY})slots={sorted(_slots)}'
                        f' → 保旧 tracking(脏读数不固化为槽位表)')
            _conflict('bench', '占用槽号唯一∧全在1..9',
                      f'slots={sorted(_slots)}', screen,
                      verdict=('保旧-写回槽号健康门拒绝(SIFT 读 slot 重复/'
                               '越界,拒写防脏布局固化为槽位表;T-308/'
                               'ADR-0646;处理:频发→查 SIFT 槽位识别)'),
                      source=source)
    if deployed is not None:
        # ADR-0392:tracked_deployed 是槽位表——_merge_equips 出紧缩占用序,
        # 写回前经 deployed_from_compact 转槽位表(单一源适配)。
        from sr_od.application.currency_war.kernel.cw_state import deployed_from_compact
        exec_state_of(session).tracked_deployed = deployed_from_compact(
            _merge_equips(exec_state_of(session).tracked_deployed, deployed))
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
        # T-308/ADR-0646 S3:布局代次递增(churn 事件通道最小面)。对账纠漂
        # = 布局可能重排,visit 内未来消费者(单动作循环每动作消费前检差)
        # 据此截断在飞计划并按 tracked 重播种。当前架构 reconcile 均在
        # visit 外跑,恒无消费者(S2+S1 后 epoch 只递增不消费,纯未来防御:
        # 防 visit 中段未来引入读屏/对账点时布局变化无人知晓)。
        if _bench_written:
            exec_state_of(session).bench_layout_epoch += 1
    # 钩子归位——「对账&hook」位统一消费留证
    # 队列(原 reconcile 深处散调;计数节流每 5 次留一张不变,
    # _star_stop_hook 内帧态门保留=双层保护)。
    for _n, _o_s, _s, _src in _pending_evidence:
        if _reg.get(_n, 0) >= 2 and ctx is not None and _reg[_n] % 5 == 0:
            _star_stop_hook(ctx, session, _n, _o_s, _s, screen, _src,
                            stop_run=False)
    return True


#: ADR-0282:hp 同域大幅上行留证阈值。HP 只降不升(结算语义,insights 实证),
#: 备战现读较 last_hp_real 上行 ≥ 此值 = 疑 OCR 误读/特殊回复 → obs_conflict 留证
#: (仍采新:真值帧是物理读数,判读侧消费证据)。
HP_REAL_JUMP_CONFLICT: int = 30


def _battle_facts_between(session, node_t: int,
                          node_lo: int | None) -> tuple[object | None, object | None]:
    """查「上一真值帧 → 本帧」窗内已观测战斗事实(ADR-0431;2026-09-02 细分)。

    事实源 = ``session.performance.history``(RoundOutcome 行,结算屏观测
    回路写入)。返回 (窗内最新 loss 行, 窗内最新任意 outcome 行):
    - **最新 loss 行单列**:扣血只发生在战败(机制,user_playstyle [27]:
      掉血=战斗失败;gameplay.md:未在行动值内取胜扣血)——窗内存在 loss
      行,下行就有机制背书;幅度核对抗该 loss 行的节点型谱,不对
      「窗内最新行」(旧实现只看最新行:真值帧跨多个节点时,
      loss 后又打了一局胜战,最新行=win 会把机制合法的下行误判为无背书,
      实证帧 0d42c300 等 5/6 合法下行被拒即此族)。
    - 最新任意行用于「窗内打没打仗、打的结果是什么」判定(胜战/零损 =
      无损血机制事实)。
    - 两返回都可为 None(结算漏采/telemetry 断/shop 开态 OCR 恢复 = 观察缺口,
      不等于没发生战斗)。

    node_lo = 上一真值帧节点号(session.last_hp_real_node);None = 旧真值
    无节点锚(升级过渡),窗口放宽为「≤ 本帧的任意 outcome 行」。
    """
    perf = getattr(session, 'performance', None)
    hist = getattr(perf, 'history', None) or []
    latest = None
    latest_loss = None
    best_t = -1
    best_loss_t = -1
    for o in hist:
        t_o = (int(getattr(o, 'plane', None) or 1) - 1) * 9 \
            + int(getattr(o, 'round_num', None) or 0)
        if t_o > node_t:
            continue
        if node_lo is not None and t_o <= node_lo:
            continue
        if t_o >= best_t:
            latest, best_t = o, t_o
        if getattr(o, 'killed', None) is not True \
                and getattr(o, 'node_type', None) not in HP_ZERO_LOSS_NODE_TYPES \
                and t_o >= best_loss_t:
            latest_loss, best_loss_t = o, t_o
    return latest_loss, latest


def _outcome_is_no_loss(o: object) -> bool:
    """单行是否「无损失结局」:胜战(killed=True)或零损节点型(奖励/补给)。"""
    return getattr(o, 'killed', None) is True \
        or getattr(o, 'node_type', None) in HP_ZERO_LOSS_NODE_TYPES


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
                 node_t: int | None = None) -> tuple[int | None, bool]:
    """hp 对账统一入口(ADR-0282,用户三层设计·对账层)。

    hp 与 bench/deployed 不同源(SIFT 双源),它的「读失败」形态 = shop 开态
    血量区物理为空(read_hp_opt → None)——**None ≠ 漂移是读失败,保旧不写**
    (复用 ``reconcile_tracking`` 双空读守卫思想;「读不到兜底 100」会在
    遥测/决策侧毒化,故废弃兜底)。

    三层分工(用户原话要点):
    - **对账层(本函数)**:读不到 → 沿用 ``session.last_hp_real``(保旧不写);
      真值帧(非 None)才写回 last_hp_real(=「session 更新只在关态真值帧」,
      shop 开态读不到自然不写);新读非 None 且同域大幅上行(HP 只降不升)
      → obs_conflict 留证;真值帧下行须过「节点内恒定 × 战斗事实」机制守卫
      (判据详见下方下行守卫分支注释:同节点/胜战零损/超谱下行拒信,有
      loss 背书或观察缺口的跨节点下行采新留证)。
    - **决策层**:消费本函数返回的(决策用 hp, 是否真读)——沿用真值比假 100
      安全(低血先验触发保血方向对);全无真值(开局)→ None(诚实未知;
      ADR-0282 兜底 100 由 ADR-0491 废止,GameState.hp None 化)。
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
        全无真值(开局)=(初值表先验, False)——实证档 A8/108 给 82/62、
        readable=False(先验非真读,ADR-0559);无实证档 =(None, False)
        诚实未知(ADR-0491,不再 100 兜底);
        被下行守卫拒信的帧=(旧值, False)(SUSPECT 态,ADR-0431)。
    """
    if new_hp is None:
        old = getattr(session, 'last_hp_real', None) if session is not None else None
        if old is not None:
            log.info(f'[cw][{source}] hp 读不到(shop 开态/血量区空)→ '
                     f'沿用 last_hp_real={old}(保旧不写,ADR-0282)')
            return old, False
        # 开局全无真值 → 遥测实证的初值表先验(ADR-0559;实证档 A8/108:
        # 基础 82、「开局不利」62;无实证档 → None 诚实未知,ADR-0491 口径不变)。
        # 只在本分支(读不到 ∧ session 无真值)填:先验非真读,readable=False;
        # 首个真值帧经下方采新写回 last_hp_real 后自然取代先验,禁覆盖真读。
        prior = (opening_hp_prior(
            getattr(session, 'briefing_affixes', None),
            getattr(session, 'selected_difficulty', ''),
            getattr(session, 'enemy_difficulty', None))
            if session is not None else None)
        if prior is not None:
            log.info(f'[cw][{source}] hp 开局无真值 → 初值表先验 {prior}'
                     f'(词缀={sorted(set(getattr(session, "briefing_affixes", None) or []))};'
                     f'ADR-0559,readable=False,真值帧到达即被覆盖)')
            return prior, False
        return None, False   # 无实证档(其他难度/未读到难度)→ None 诚实未知(ADR-0491)
    old = getattr(session, 'last_hp_real', None) if session is not None else None
    if old is not None and new_hp - old >= HP_REAL_JUMP_CONFLICT:
        _conflict('hp', old, new_hp, screen,
                  verdict=('留证-同域大幅上行(HP只降不升,疑OCR误读/特殊回复;'
                           '处理:采新现读真值帧;频发→查血量区遮挡/误读)'),
                  source=source, node_t=node_t)
    # —— 下行守卫(ADR-0431;2026-09-02 判据重推导)——
    # 机制依据(判据的锚,非拍脑袋):扣血只发生在节点结算的战败
    #(user_playstyle [27] 最高权威口述「掉血=战斗失败」+ gameplay.md
    #「未在行动值内取胜扣血」),即 hp 在节点内恒定、只在跨节点结算时变化。
    # 故守卫锁的是「机制不可能的下行」,不是下行方向本身:
    # 1) 同节点下行:节点内 hp 恒定,任何下行必为误读 → 拒信+复现通道
    #    (ADR-0431 原保护面,遮挡/掉十位误读的挡板);
    # 2) 跨节点 + 窗内最新结局为胜战/零损:胜战不扣血是机制事实,下行无
    #    背书 → 拒信+复现通道;
    # 3) 跨节点 + 窗内有 loss 行:下行有机制背书。幅度超已标定谱 p100 →
    #    仍拒信(超物理上界疑误读,ADR-0431 原判据);谱内静默采新;
    #    节点型未标定不拍值 → 采新+留证攒标定;
    # 4) 跨节点 + 窗内无任何 outcome(结算漏采/telemetry 断):观察缺口 ≠
    #    没发生战斗,下行方向机制合法 → 采新+留证。旧实现此处拒信,把
    #    观察回路的缺口惩罚在读数上,每个合法下行都固化旧值再等 2 帧复现
    #    —— 2026-09-02 分诊实证 hp post-ADR 冲突暴涨(抽样 5/6 帧合法下行
    #    被拒)的主源即此臂,修订为留证。
    # node_t=None(离线/旧调用方)守卫不介入,既有行为逐位零漂移;
    # 上行/持平帧不经本分支。
    if session is not None and old is not None and new_hp < old \
            and node_t is not None:
        _last_node = getattr(session, 'last_hp_real_node', None)
        if _last_node is not None and node_t <= _last_node:
            # 同节点:hp 恒定是机制事实,任何下行都是误读
            return _reject_down(session, old, new_hp, node_t, screen, source)
        _loss_o, _latest_o = _battle_facts_between(session, node_t, _last_node)
        _delta = old - new_hp
        if _loss_o is not None:
            _cap = HP_LOSS_CAP_P100_BY_NODE.get(getattr(_loss_o, 'node_type', None))
            if _cap is not None and _delta > _cap:
                return _reject_down(session, old, new_hp, node_t, screen, source)
            if _cap is None:
                # 节点型未标定(精英/巨星等,无 p100 谱)不拍值:下行有
                # loss 背书即采信,幅度留证攒标定(旧实现拒信,把标定缺口
                # 惩罚在读数上,同属噪声环臂)
                _conflict('hp', old, new_hp, screen,
                          verdict=('采新-loss已观测·节点型未标定(下行有战败背书;'
                                   '幅度留证攒标定,不拍值)'),
                          source=source, node_t=node_t, direction='down')
        elif _latest_o is not None and _outcome_is_no_loss(_latest_o):
            # 窗内打的是胜战/零损:不扣血是机制事实,下行无背书 → 拒信
            return _reject_down(session, old, new_hp, node_t, screen, source)
        else:
            # 窗内无任何已观测战斗行(观察缺口):下行方向机制合法,采新+留证
            _conflict('hp', old, new_hp, screen,
                      verdict=('采新-跨节点下行·战斗事实缺观测(扣血只发生在节点'
                               '结算战败,下行方向机制合法;结算漏采不固话旧值;'
                               '频发→查结算观测回路)'),
                      source=source, node_t=node_t, direction='down')
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
        from sr_od.application.currency_war.kernel.cw_observe import obs_conflict
        obs_conflict(field, old, new, screen, verdict=verdict, source=source, **ctx)
    except Exception:  # noqa: BLE001  留证 best-effort
        pass


def _star_stop_hook(ctx, session, char: str, old_star: int, new_star: int,
                    screen, source: str, stop_run: bool = True) -> None:
    """star 回退留证钩子(用户指示;star≥2 回退触发)。

    留证模式:排查已尽策略侧所能(结论存 cw_dev/live_round11_diagnosis.md:
    根因在 SIFT 身份域,非读星)——stop_run=False 时只留证截图不停机(证流保留,
    实跑可推进);SIFT 身份修复后本段整删。
    停机保备战画面供排查星级识别(read_star 漏金星?星区被特效/光标遮挡?SIFT 身份错配?)。
    sentinel 自描述(教训:内容含「这是自己的钩子停的+删除位置」,防误判孤儿/外部拦截)。
    帧态门:留证/停机只在备战类精准帧(is_prep_like_frame)
    ——动画帧上的星读回退本就常发(升星特效窗),不留证。
    """
    from datetime import datetime
    from pathlib import Path

    from one_dragon.utils import log_utils
    try:
        # 帧态门:非备战类精准帧直接跳过(动画帧星读回退
        # 常发,留证只是噪声)。screen=None(测试/无帧上下文)
        # 不拦——留证本身是离线安全操作。
        if screen is not None:
            from sr_od.application.currency_war.kernel.cw_obs_core import (
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
