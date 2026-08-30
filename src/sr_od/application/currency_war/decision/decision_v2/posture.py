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
    # —— 预算-回执契约授权包扩展(w921_rd_design DESIGN §1.1-A 批1;
    # ADR 落点=ADR-0504 支出回执契约)——新字段带缺省,既有消费方
    # (arbiter/scoring/posture_release/遥测)接口零改动。
    #: 成立前提枚举(已核真的前提 token;前提不成立的授权在产出侧就
    #: 不发,见 posture_release.attach_spend_authorization):
    #: - 'pop_slot':升级授权前提=bench 有等待件 ∨ cap 有空位(升级
    #:   产出可兑现的人口收益;[32] 消费有效性门/13-2 形态);
    #: - 'spend_channel':刷新授权前提=该节点商店执行通道存在(补给
    #:   等无商店循环的节点不产支出授权;20-5 形态;通道接线本体归
    #:   R-F 行为批,本契约只声明语义位)。
    premises: tuple[str, ...] = ()
    #: 买侧预算位(金):奖励节点扩张档授权量(DESIGN D2;[1]/[15]
    #: 已证的奖励节点保息多买压库语义在姿态词汇里的载体)。量级=
    #: 溢余段(g−R*,economy_cycle.reserve_cap 单一源),零新常数;
    #: 精细档量推导+sim 敏感度扫描归 D2 标定批。授权/观测面——不构
    #: 成新花钱通道,买侧消费仍走既有 EV 过滤链(DESIGN §4-3)。
    buy_budget: int = 0
    #: 授权号(轮内唯一;执行回执与对账遥测的对账挂接键)。
    auth_id: str = ''


@dataclass(slots=True)
class SpendReceipt:
    """执行层支出回执(预算-回执契约 §1.1-B;新数据面,不改过滤逻辑)。

    按渠道汇回执:``spent``=该渠道实际采纳支出(金),未兑现时
    ``reason``=四枚举之一(未兑现原因;C3 equip_alloc_empty_reason
    先例同型——判读从遥测直接归因,禁止事后人肉回放):

    - ``no_premise``:实体前提不成立(执行时点复核;授权发出后
      working 态演化使前提失效的残余面);
    - ``no_channel``:节点无执行通道(20-5 形态;接线归 R-F 行为批);
    - ``no_candidate``:候选全滤空(附 arbiter 执行 log Top1 拒因);
    - ``no_budget``:授权预算为 0(授权面存在但无预算可花)。
    """

    buy_spent: int = 0
    buy_reason: str = ''
    levelup_spent: int = 0
    levelup_reason: str = ''
    refresh_spent: int = 0
    refresh_reason: str = ''
    top_reject: str = ''

    def as_dict(self) -> dict:
        """遥测/账本可序列化形状(空串键省略,行体积有界)。"""
        d: dict = {}
        for k, v in (('buy', self.buy_spent),
                     ('levelup', self.levelup_spent),
                     ('refresh', self.refresh_spent)):
            if v:
                d[k] = v
        for k, v in (('buy_reason', self.buy_reason),
                     ('levelup_reason', self.levelup_reason),
                     ('refresh_reason', self.refresh_reason),
                     ('top_reject', self.top_reject)):
            if v:
                d[k] = v
        return d
