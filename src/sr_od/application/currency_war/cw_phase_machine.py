"""货币战争 · Phase A 状态机(生产位;Phase A Day 9;redesign §5)。

**运行时消费方:LineStrategy 决策循环**。本模块是门槛③ v4
(sr-od-test/tools/cw_phaseA_statemachine_v4.py,七轮对抗收敛的
穷举资产)的生产迁移——step() 语义与其逐条一致(七性质由
sr-od-test/tools/test_phaseA_statemachine_v4.py 锁定,该测试
改为 import 本模块验证生产版不漂移)。

常量在本文件(单一源);示例值=文档口径,Step 5 遥测标定。"""
from __future__ import annotations

# ===== 常量(附录 A;示例值,遥测标定) =====
MISS_STREAK_M: int = 2      # 连续 miss 达此数→经济转战力
PASS_STREAK_M: int = 3      # 连续过达此数→战力转经济(含退出冷却)
PIVOT_GUARD_N: int = 2      # 换线守卫窗(战斗节点)
ROLL_FAIL_N: int = 3        # D 卡失败达此数→降级

#: 驱动型 → bit 位(visited 集合用;三线 Phase A)
LINE_BITS: dict[str, int] = {
    'jizi_train': 0,
    'feiying_joy': 1,
    'dot_fallback': 2,      # 兜底不进 visited(终结线语义)——
    # 但保留位以统一接口
}

MODE_ECONOMY = 'economy'
MODE_WAR = 'war'

EVENTS = ('E1_strong', 'E1_miss', 'node_pass', 'E2_pivot',
          'E2_degrade', 'E3', 'E4', 'E5', 'E6', 'E7_lock',
          'E8_restart', 'D_fail')


def step(st: tuple, ev: str, pop_low: bool = True,
         target_bit: int = 0) -> object:
    """联合转移纯函数(门槛③ v4 同语义)。

    st=(mode, emg, cat, streak_miss, streak_pass, guard_left,
        roll_fail, visited)
    返回: tuple | 'REJECT' | set[tuple](非确定:换线重采样)。
    CONTRACTS(调用侧判定,单测锚点见 v4 测试):
      pop_low: 人口 vs 位面基线(消费方算好传入)
      target_bit: 换线目标的 visited 位
      E2_degrade 目标==当前线:调用侧 no-op(不进本函数)
    """
    mode, emg, cat, sm, sp, gl, rf, vis = st
    if ev == 'E3':
        return (mode, True, False, 0, 0, gl, rf, vis)
    if emg:
        if ev == 'E8_restart':
            return {(mode, True, False, 0, 0, gl, rf, 0),
                    (mode, False, bool(pop_low), 0, 0, 0, 0, 0),
                    (mode, False, False, 0, 0, 0, 0, 0)}
        return st                    # 应急期其余事件不变(P6)
    if ev == 'E5':
        return (mode, False, bool(pop_low), sm, sp, gl, rf, vis)
    if cat and ev == 'E6':
        return (mode, False, False, sm, sp, gl, rf, vis)
    if ev in ('E2_pivot', 'E2_degrade', 'E7_lock'):
        if ev == 'E2_pivot' and gl > 0:
            return 'REJECT'          # B4 守卫拒
        if ev == 'E2_pivot' and (vis >> target_bit) & 1:
            return 'REJECT'          # 已访问(防环,耗尽态出口)
        nv = vis | (1 << target_bit) if ev != 'E7_lock' else vis
        return {(MODE_WAR, False, cat, 0, 0, PIVOT_GUARD_N, 0, nv),
                (MODE_ECONOMY, False, cat, 0, 0, PIVOT_GUARD_N, 0, nv)}
    if ev == 'E8_restart':
        return (mode, False, cat, 0, 0, 0, 0, 0)
    frozen = cat                     # 追赶期滞回冻结
    if ev == 'E1_miss':
        if frozen:
            return (mode, False, cat, sm, sp, max(0, gl - 1), rf, vis)
        sm2 = min(sm + 1, MISS_STREAK_M)
        if sm2 >= MISS_STREAK_M and mode == MODE_ECONOMY:
            return (MODE_WAR, False, cat, 0, 0,
                    max(0, gl - 1), rf, vis)   # A4 进入
        return (mode, False, cat, sm2, 0, max(0, gl - 1), rf, vis)
    if ev in ('E1_strong', 'node_pass'):
        if frozen:
            return (mode, False, cat, sm, sp, max(0, gl - 1), rf, vis)
        sp2 = min(sp + 1, PASS_STREAK_M)
        if sp2 >= PASS_STREAK_M and mode == MODE_WAR:
            return (MODE_ECONOMY, False, cat, 0, 0,
                    max(0, gl - 1), rf, vis)   # A5 退出
        return (mode, False, cat, 0, sp2, max(0, gl - 1), rf, vis)
    if ev == 'D_fail':
        rf2 = min(rf + 1, ROLL_FAIL_N)
        if rf2 >= ROLL_FAIL_N:
            return (mode, False, cat, 0, 0, PIVOT_GUARD_N, 0, vis)
        return (mode, False, cat, sm, sp, gl, rf2, vis)
    return st


def initial_state() -> tuple:
    """局初状态(economy/无应急/无追赶/全零/未访问)。"""
    return (MODE_ECONOMY, False, False, 0, 0, 0, 0, 0)
