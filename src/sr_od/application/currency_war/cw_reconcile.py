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
    old_b = [(bc.char_id, bc.star) for bc in session.tracked_bench_chars]
    old_d = [(bc.char_id, bc.star) for bc in session.tracked_deployed]
    if not bench and not deployed and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        return False
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    drifted = (old_b != new_b) or (old_d != new_d)
    # star 回退留证(观察冲突审计 #13,2026-08-16):同名 star 下降(如 2★读回 1★)= read_star
    # 漏金星 或 卖后重买边缘场景;不保旧(审计:保旧不安全)只留证统计毒化率。
    _old_stars = {(n, s) for n, s in old_b + old_d if n}
    _new_stars = {(n, s) for n, s in new_b + new_d if n}
    _reg = dict(getattr(session, 'star_regression_count', {}) or {})
    for _n, _s in _new_stars:
        _old_s = next((_os for _on, _os in _old_stars if _on == _n), None)
        if _old_s is not None and _s < _old_s:
            log.warning(f'[cw!][{source}] star 回退:{_n} {_old_s}★→{_s}★(read_star 漏金星?卖后重买?)')
            _conflict('star', _old_s, _s, screen, verdict='采新-read_star实读(回退留证)',
                      source=source, char=_n)
            # ⚖️ 停机钩子(star≥2 连续 2 节点回退;预估升星 vs 实机不符 = 识别可疑)
            if _old_s >= 2:
                _reg[_n] = _reg.get(_n, 0) + 1
                if _reg[_n] >= 2 and ctx is not None:
                    _star_stop_hook(ctx, session, _n, _old_s, _s, screen, source)
        elif _n in _reg:
            del _reg[_n]   # 读回恢复(或超预估)→ 清零
    session.star_regression_count = _reg
    if bench is not None:
        session.tracked_bench_chars = list(bench)
    if deployed is not None:
        session.tracked_deployed = list(deployed)
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
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
                    screen, source: str) -> None:
    """star 回退停机钩子(用户 2026-08-17 指示;连续 2 节点 star≥2 回退触发)。

    停机保备战画面供排查星级识别(read_star 漏金星?星区被特效/光标遮挡?SIFT 身份错配?)。
    sentinel 自描述(r17-r31 教训:内容含「这是自己的钩子停的+删除位置」,防误判孤儿/外部拦截)。
    """
    from datetime import datetime
    from pathlib import Path

    from one_dragon.utils import log_utils
    try:
        _p = Path('.debug/temp/currency_war/star_regression_hook.flag')
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(
            f'[{datetime.now().isoformat(timespec="seconds")}] 这是我自己的 star 回退停机钩子停的'
            f'(非手停/非外部拦截)——{char} 预估 {old_star}★(买牌 3合1 merge)连续 2 节点读回 '
            f'{new_star}★,星级识别可疑。\n'
            f'排查:①该角色槽位 read_star 实读(金星区是否被遮挡/光标压住);②SIFT 身份是否错配;'
            f'③修好后删钩子:cw_reconcile.py 搜「_star_stop_hook」整段。\n'
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
            f'[cw-hook] star 回退停机:{char} 预估{old_star}★×2节点读回{new_star}★ → '
            f'停机保画面排查星级识别(sentinel: star_regression_hook.flag;修好删 _star_stop_hook)')
        ctx.run_context.stop_running()
    except Exception:  # noqa: BLE001  停机失败不阻塞对账写回
        pass
