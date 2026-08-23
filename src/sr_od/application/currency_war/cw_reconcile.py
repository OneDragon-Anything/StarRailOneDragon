"""tracking 对账公共层(观察冲突审计 P0 #12,2026-08-16)。

两处对账实现(deploy_bench._reconcile_tracking / prep_director._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log


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
    old_b = [(bc.char_id, bc.star) for bc in session.tracked_bench_chars]
    old_d = [(bc.char_id, bc.star) for bc in session.tracked_deployed]
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
    # 取**防抖后**快照(旧快照记的是改前值,误导排障)。
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    drifted = (old_b != new_b) or (old_d != new_d)
    if bench is not None:
        session.tracked_bench_chars = list(bench)
    if deployed is not None:
        session.tracked_deployed = list(deployed)
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
