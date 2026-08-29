"""轮姿态载体(预算收权批(ADR-0465)后的新供给形状;原 DP 模块 Posture 形状平移)。

字段形状与旧 DP 姿态载体逐位同构(save/level_up/refresh_budget/v/tag)
——消费方(arbiter/scoring/posture_release/遥测)接口零改动,只有
**生产者**从 DP 逆向递推送为确定性预算核(economy_cycle 排程/预算
两接缝,BLUEPRINT §3.4 R4 单一址)。本模块纯数据契约,零逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Posture:
    """轮姿态载体(轮内派生量,经 ``ev.round_posture`` 轮缓存共享)。

    - ``level_up``:排程升级判据(schedule_upgrade 查表核,含预告态);
    - ``refresh_budget``:刷新 EV 授权刷数(refresh_ev_budget 预算式,
      值域 [0, REFRESH_ROLL_CAP];0=合法零预算帧:储备段 g≤R* 与应急带
      ——血预算带不在预算层辖域,停付由 arbiter 拒付层兜底,`w635_batch3_attack/` F1);
    - ``tag``:姿态标签词汇表 v2(判前锁,生产者=ev.build_round_posture):
      '升级' / '升级+D<刷数>' / '+D<刷数>' / '存息',经 release 包装后
      恒 'release'(posture_release.wrap_posture)。旧 DP 词汇
      ('存息'/'+D2/4/6' 离散码)随 DP 退役;'升级+D<任意刷数>' 的
      连续刷数是查表预算的值域形状(`w623_batch3_pre-mortem/` D2:离散动作码假设退役)。
    """

    save: bool = True
    level_up: bool = False
    refresh_budget: int = 0
    v: float = 0.0
    tag: str = ''
