"""tracking 对账公共层(观察冲突审计 P0 #12,2026-08-16)。

两处对账实现(deploy_bench._reconcile_tracking / prep_director._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log


def reconcile_tracking(session, bench, deployed, screen=None, *,
                       source: str = 'reconcile') -> bool:
    """tracking 对账统一入口:新 SIFT 读 vs 旧 session tracking,守卫后写回。

    守卫(审计 #11/#12):
    - **双空读守卫**(M14 实锤):新读 bench/deployed 双空 + 前值非空 = 疑 SIFT 过渡帧
      → 保旧不写(空读是读失败,不是「板真没了」);
    - **漂移留证**:新旧不一致 → obs_conflict(裁决=采新-对账纠漂)+ [cw!] 日志;
      一致 → 静默(常态无噪声)。

    Args:
        session: StrategySession(tracked_bench_chars/tracked_deployed 被写回)
        bench/deployed: 新读 list[BenchChar](None = 读失败,不写该侧)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)

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
    for _n, _s in _new_stars:
        _old_s = next((_os for _on, _os in _old_stars if _on == _n), None)
        if _old_s is not None and _s < _old_s:
            log.warning(f'[cw!][{source}] star 回退:{_n} {_old_s}★→{_s}★(read_star 漏金星?卖后重买?)')
            _conflict('star', _old_s, _s, screen, verdict='采新-read_star实读(回退留证)',
                      source=source, char=_n)
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
