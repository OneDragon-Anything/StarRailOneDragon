"""【拟】未标定项 fail-closed 开关注册表(design_economy §E4.0 第 3 条)。

静态登记 NMF §3.3 清单(批时快照)+ 换线/升档器后补槽位
(θ/D_min/δ/χ/p_rec/血线阈值/N_crisis 等)。**计数口径单一声明(IMPL_ADV_R194
症3,禁三处三种组成)**:NMF §3.3 = **13 个编号行**(#1-#13);本表槽位 = 13 个,
换算式=13 行 −#11(零槽位,由 statefn/lambda_death.py λ 表承载,该条系
「分层直测表带 CI 先行」的载体指定而非【拟】None 槽位语义)+#2 拆 V_MS/V_GAP
两槽(同源单标定,禁双源)。每项一个 ``Optional`` 槽位,
**缺省 None = 对应判据分支 fail-closed**;标定值只能经本模块 ``inject``
显式注入(带 CI 对象)——「注入即开闸」事故(TUNING#1/#2)的结构性防线,
禁散落各判据文件。注入形态值(θ=1.0/δ=0.15/D_min=2、血线阈值 hp=15 等
量级论证级值)系 sim 驱动专用,显式标「注入形态,非生产开闸口径」
(R24-2/R36-2)——生产开闸须标定批 CI 验收五件套(R4-F6/§5.3 对拍 2)。

V̄ 拟合族类型级封印(R10-2):``V_BAR`` 槽位不提供数值取值接口
(``get`` 对其恒返 None 且 ``inject`` 拒绝)——未标定且永不标定开闸作闸门
 的项在类型上不暴露给闸门消费位;V_gap 不在封印清单(标定后 R1 门合法消费)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibValue:
    """标定注入值(带 CI;端点选择随消费位走——组-端对照 design_economy
    §E4.1,注入不预取端)。``injected_form=True`` = 注入形态(非生产开闸口径)。"""

    value: float
    ci_lo: float | None = None
    ci_hi: float | None = None
    injected_form: bool = False


@dataclass(frozen=True)
class _Slot:
    nmf_ref: str          # NMF §3.3 条目号或后补出处
    sealed: bool = False  # 类型级封印(V̄ 拟合族,R10-2)


#: 槽位登记表(键=符号名;NMF §3.3 批时快照 13 槽 + 后补;计数口径见模块
#: docstring 单一声明:13 编号行 −#11(零槽,λ 表承载)+#2 拆两槽 = 13 槽)
_SLOTS: dict[str, _Slot] = {
    # —— NMF §3.3 清单(13 编号行 → 13 槽;批时快照)——
    'U_X': _Slot('§3.3 #1 u_x/H_x 使用概率/需要时距;分槽/带序逐格(R17-4)'),
    'V_MS': _Slot('§3.3 #2a V_ms 成型边际价值;与 V_GAP 系同一条 #2 拆槽,同源单标定禁双源'),
    'V_GAP': _Slot('§3.3 #2b V_gap【拟·未标定】;消费位=criteria/refresh.'
                   'r1_start 的 EV 输入(经 shop.py 付费刷新发射位接线,'
                   '2026-09-03 零刷新修复批);None 期 r1 fail-closed 零刷新;'
                   '与 V_MS 同源单标定;不在封印清单(R10-2)'),
    'W_POP': _Slot('§3.3 #3 w 人口位战力当量(臂一只用 w>0,不需精确值)'),
    'RHO_IMPUTE': _Slot('§3.3 #4 ρ 摊派口径(A7);均匀摊保守首版'),
    'NBAR_ESTIMATOR': _Slot('§3.3 #5 n̄ 估计器(实估,误差二阶 A3)'),
    'T_SEARCH_A': _Slot('§3.3 #6 A/T_search 组成(活跃窗口付费份额确定性查表)'),
    'LAMBDA_S_EQUIP': _Slot('§3.3 #7 λ_s 装备来源流/partner 到位率(只有序/支配可消费)'),
    'V_FURNACE': _Slot('§3.3 #8 v_F/v_B 炉/死库存价值(sim 唯一标定通道)'),
    'C_FRAME_Q': _Slot('§3.3 #9 c_frame/q(P34-b;q plaza 先验只撑量级)'),
    'DELTA_P_WIN': _Slot('§3.3 #10 Δp(d→胜率换算;P43 只供外差项)'),
    # §3.3 #11(λ_death 连续模型)无本表槽位:该条落点=「分层直测表带 CI 先行」,
    # 载体=statefn/lambda_death.py 的 λ 表(启动必载损坏守卫,R2-4),非【拟】
    # None fail-closed 槽位语义——硬凑占位槽反而伪造「缺省 None」状态(IMPL_ADV_R194 症3)。
    'P_HIT_Q_CONV': _Slot('§3.3 #12 p_hit/q_conv(P36-b/c 危机预算阶梯)'),
    # —— 类型级封印族(R10-2:V̄ 拟合族永不作闸门)——
    'V_BAR': _Slot('§3.3 #13 V̄ 刷新价值门量;比较项不授权,禁作闸门', sealed=True),
    # —— 后补槽位(换线/升档器/窗口侧,R189 ④-2:θ/D_min/δ 系归本模块)——
    'THETA': _Slot('换线滞回 θ(R24-2;None 期 should_switch 不评估+θ_unavailable 记数)'),
    'D_MIN': _Slot('换线最小间隔 D_min(R24-2;与 θ 同批标定)'),
    # δ(P16 滞回)槽位:步4 批补齐——R23-5「θ/D_min 参数归宿=provisional
    # 【拟】槽位(δ 同槽登记)」的 δ 半边在步2 落码时未建槽(仅建 θ/D_MIN,
    # DELTA_PRIOR 系窗口平移量、与 P16 δ 撞名不同义,R34-4)。本槽 = P16
    # 滞回 δ 的唯一归宿;None 期与 θ/D_min 同 fail-closed(should_switch
    # 不评估)。加槽系缺口闭合,非数值语义变更(STEP34_REPORT 呈报项)。
    'DELTA_HYST': _Slot('P16 换线滞回 δ(R23-5 同槽登记;R34-4:与窗口 δ_prior 无关)'),
    'DELTA_PRIOR': _Slot('窗口 δ_prior(R44 系;治本拆分前不可判分量)'),
    'CONV_GOLD_PER_ROUND': _Slot(
        'χ 金→轮折算率(R44-1【拟·语料拟合】,依附 λ 表版本;None=窗口帧 C_stay/χ fail-closed)'),
    'P_REC': _Slot('换线塌缩回补概率 p_rec(R38-2【拟:0】期望形态)'),
    'BLOODLINE_HP_THRESHOLD': _Slot(
        '血线硬地板阈值(R27-1②【拟】;注入形态=hp15 血带结构锚,R36-2)'),
    'N_CRISIS': _Slot('危局阀标定输入 N_gate(R64/R65;标定账=sim 轨迹真值)'),
    'P3_LENGTH_STAT': _Slot('P3 长度统计量(R41-3【拟·语料统计】;通关语料出现前不可填)'),
    'F7_CONTINGENCY_ARMED': _Slot('应急期 F7 独立分键 f7_contingency_armed(R38-3)'),
    # λ 顾问分位参数 p(R28-1 相对分位触发;R41-5② 注入口径先例=带扫中心经
    # 本槽注入,sim 驱动专用)。步4 批补槽:None 期 λ 顾问触发信号构造性 ⊥
    # (R29-1),仅影子求值进遥测——槽缺位会使求值位两读,补齐系缺口闭合
    # (STEP34_REPORT 呈报项,非数值语义变更)。
    'P_LAMBDA_QUANTILE': _Slot('λ 顾问相对分位 p(R28-1;R29-1 None 期不评估)'),
}

#: 槽位值存储(缺省全 None = fail-closed)
_VALUES: dict[str, CalibValue | None] = dict.fromkeys(_SLOTS)


def get(name: str) -> CalibValue | None:
    """槽位读(None = fail-closed:对应判据分支不评估/不产追加动作;
    **绝不向骨架层渗漏为否决**,NMF §5.3)。封印族(V̄)恒 None。"""
    slot = _SLOTS.get(name)
    if slot is None:
        raise KeyError(f'unknown provisional slot: {name}')
    if slot.sealed:
        return None
    return _VALUES[name]


def is_none(name: str) -> bool:
    """None 期探针(θ_unavailable 等分键记数的判定入参,R24-2)。"""
    return get(name) is None


def inject(name: str, value: CalibValue) -> None:
    """显式注入(唯一开闸通道;封印族拒绝)。测试注入后须 ``reset`` 复原,
    防 session 内残留开闸状态(测试纪律:改全局态必须复原)。"""
    slot = _SLOTS.get(name)
    if slot is None:
        raise KeyError(f'unknown provisional slot: {name}')
    if slot.sealed:
        raise ValueError(f'slot {name} 系类型级封印族(R10-2),禁注入')
    _VALUES[name] = value


def reset(name: str | None = None) -> None:
    """复位(测试隔离/标定批重注入前的清场)。"""
    if name is None:
        for k in _VALUES:
            _VALUES[k] = None
    else:
        _VALUES[name] = None


def slot_names() -> tuple[str, ...]:
    """登记槽位名全集(审计/静态断言消费)。"""
    return tuple(_SLOTS)


__all__ = ['CalibValue', 'get', 'inject', 'is_none', 'reset', 'slot_names']
