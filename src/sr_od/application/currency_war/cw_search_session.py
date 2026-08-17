"""搜牌会话层 v0(redesign 38 号;ADR-0191):窗内序贯搜索的信念 DP + 停止规则导出。

**诊断(38 号)**:商店「刷新→看面→买→再刷/收手」是决策频率最高、烧金最集中的位点,
现状 = 单步 MC 估值(A1)+ 外生 cap 截断;计数器型刷新经济(长线利好 30 刷后 1 金/刷、
二手市场 20 刷返金、采购专员每 N 刷全同费)使「再刷一次」的边际价值依赖历史刷次——
一维 cap 旋钮结构上表达不了跨刷次投资。

**v0 落地**(纯函数,离线;38 号 §2 的最小闭环):
- ``SearchState``:会话状态(金/刷次计数器/目标进度/当前刷新价);
- ``solve_session``:有限期信念 DP(终值 = 线性金效用 + 进度残值——03 值函数接消费批次;
  面转移 = 目标命中概率 hit_p 摘要[16 号分位接入点];计数器转移显式[降价线/返金线]);
- ``decide_shop_face``:运行时决策(离线表查询语义;v0 直接小规模求解即答)→
  {refresh, buy, stop, reason};
- 降级链:hit_p 满池点估计/计数器 off/终值线性 —— 全 off = 单步贪心(现状,零漂移锚)。

J0(测试):满池无计数器退化配置 → 与单步贪心一致;J2 切片:计数器注入(30 刷降价)
→ 解表现出「解锁线附近主动烧刷」的跨刷次投资(基线单步估值结构上不能)。
"""
from __future__ import annotations

from dataclasses import dataclass

# 计数器经济摘要(机制常量;23 号注册表接入点)
DISCOUNT_AT_REFRESH = 30    # 长线利好:付费刷满 30 次 → 本局刷新 1 金
DISCOUNT_PRICE = 1
NORMAL_PRICE = 2
PROGRESS_RESIDUE = 6.0      # 单张目标进度残值(线性金效用近似;终值接 03 批次校准)


@dataclass(frozen=True)
class SearchState:
    """会话状态(运行时查表输入;全为已有/可派生字段)。"""

    gold: int
    refresh_count: int          # 本局累计付费刷新
    target_left: int            # 还差几张目标卡
    hit_p: float                # 单刷至少命中 1 张目标摘要概率(16 号信念接入点)
    refresh_price: int = NORMAL_PRICE   # 当前刷价(计数器效果后)


def _progress_value(target_left: int) -> float:
    """进度残值:差 0 张 = 0;每差 1 张 −PROGRESS_RESIDUE(买齐的终值增益)。"""
    return -PROGRESS_RESIDUE * target_left


def _session_value(s: SearchState, horizon: int, memo: dict) -> float:
    """有限期信念 DP:V(s) = max{收手: gold·1 + 进度残值, 刷: −price + E[V(s')] }。"""
    if horizon <= 0:
        return s.gold + _progress_value(s.target_left)
    key = (s.gold, s.refresh_count, s.target_left, horizon)
    if key in memo:
        return memo[key]
    stop_v = s.gold + _progress_value(s.target_left)
    best = stop_v
    # 刷分支:付当前价(金在转移状态里扣,**外层不再重复扣**)→ 命中(hit_p)进度−1;
    # 未命中进度不变。计数器转移:跨降价线后价降。
    if s.gold >= s.refresh_price:
        g2 = s.gold - s.refresh_price
        nxt_price = DISCOUNT_PRICE if (s.refresh_count + 1) >= DISCOUNT_AT_REFRESH else s.refresh_price
        hit_left = max(0, s.target_left - 1)
        v_refresh = (s.hit_p * _session_value(
                         SearchState(g2, s.refresh_count + 1, hit_left, s.hit_p, nxt_price), horizon - 1, memo)
                     + (1 - s.hit_p) * _session_value(
                         SearchState(g2, s.refresh_count + 1, s.target_left, s.hit_p, nxt_price), horizon - 1, memo))
        best = max(best, v_refresh)
    memo[key] = best
    return best


def decide_shop_face(state: SearchState, horizon: int = 8) -> dict:
    """运行时决策:刷 vs 收手(买子集挂 06 接受子程序批次;v0 单目标)。

    返回 {refresh: bool, stop: bool, reason: str};v_refresh > stop_v 差值供阈值消费。
    """
    memo: dict = {}
    stop_v = state.gold + _progress_value(state.target_left)
    best_refresh_v = -1e18
    if state.gold >= state.refresh_price:
        g2 = state.gold - state.refresh_price
        nxt_price = DISCOUNT_PRICE if (state.refresh_count + 1) >= DISCOUNT_AT_REFRESH else state.refresh_price
        hit_left = max(0, state.target_left - 1)
        best_refresh_v = (state.hit_p * _session_value(
                              SearchState(g2, state.refresh_count + 1, hit_left, state.hit_p, nxt_price), horizon - 1, memo)
                          + (1 - state.hit_p) * _session_value(
                              SearchState(g2, state.refresh_count + 1, state.target_left, state.hit_p, nxt_price), horizon - 1, memo))
    refresh = best_refresh_v > stop_v
    edge = best_refresh_v - stop_v if refresh else stop_v - best_refresh_v
    reason = ('命中期望×进度残值 > 刷价' if refresh else '搜索期望低于金保留值')
    if state.refresh_count + 1 >= DISCOUNT_AT_REFRESH and refresh:
        reason = '跨降价线:解锁后 1 金/刷,边际价值抬升'
    return {'refresh': refresh, 'stop': not refresh,
            'edge': round(edge, 2), 'reason': reason}
