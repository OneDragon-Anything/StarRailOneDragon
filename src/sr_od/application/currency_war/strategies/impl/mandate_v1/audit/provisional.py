"""【拟】未标定项 fail-closed 开关注册表(01_math_framework §6 第 3 形态;
原 design_economy §E4.0 第 3 条已删除,沿革见 git 历史)。

静态登记 【拟】清单 + 后补槽位。**计数口径单一声明**:
本表槽位 = 逐槽实存集:消费面停用即撤槽(已撤条目 = BLOODLINE_HP_THRESHOLD/
F7_CONTINGENCY_ARMED/P_LAMBDA_QUANTILE〔血线地板/λ 顾问删除〕、
V_MS/P_REC/THETA/D_MIN/DELTA_HYST/DELTA_PRIOR/CONV_GOLD_
PER_ROUND/N_CRISIS/V_GAP〔换线机器与换线窗口侧〕、
V_C_MINUS_V_F/E2_CONCENTRATION_BAND〔P76 两槽〕、
LEVELUP_MISSING_SET_AGG〔升级概率账臂删除〕、
W_POP〔人口位臂删除〕、MERGE_PROGRESS_X2〔旧卖出价值函数退役,
统一让位优先级批〕
——候选-锁定制无定型门标定项,槽位不迁移,停用面申报)。
每项一个 ``Optional`` 槽位,
**缺省 None = 对应判据分支 fail-closed**;标定值只能经本模块 ``inject``
显式注入(带 CI 对象)——「注入即开闸」事故(TUNING#1/#2)的结构性防线,
禁散落各判据文件。

V̄ 拟合族类型级封印(R10-2):``V_BAR`` 槽位不提供数值取值接口
(``get`` 对其恒返 None 且 ``inject`` 拒绝)——未标定且永不标定开闸作闸门
 的项在类型上不暴露给闸门消费位;V_gap 不在封印清单(标定后 R1 门合法消费)。
"""
from __future__ import annotations

# 遭遇选档判据的标定注入面 = 策略层
# strategies/impl/mandate_v1/encounter_pick.apply_calibration(fill 双键;
# 判据与标定面已迁策略层,宪法五)——与本模块槽位物理隔离,互不可见。
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CalibValue:
    """标定注入值(带 CI;端点选择随消费位走——组-端取端纪律,原 design_economy
    §E4.1 组-端对照表已删除,沿革见 git 历史,注入不预取端)。``injected_form=True`` = 注入形态(非生产开闸口径)。"""

    value: float
    ci_lo: float | None = None
    ci_hi: float | None = None
    injected_form: bool = False


@dataclass(frozen=True)
class _Slot:
    nmf_ref: str          # 【拟】清单 条目号或后补出处
    sealed: bool = False  # 类型级封印(V̄ 拟合族,R10-2)


#: 槽位登记表(键=符号名;随消费面停用撤槽/登记后补,现状清单见模块
#: docstring 单一声明)
_SLOTS: dict[str, _Slot] = {
    # —— 【拟】清单快照的存活槽(下列已随换线机器/换线窗口侧消费面
    #    撤槽:V_MS/V_GAP/THETA/D_MIN/DELTA_HYST/DELTA_PRIOR/CONV_GOLD_
    #    PER_ROUND/P_REC/N_CRISIS;撤槽申报;零槽位
    #    由 statefn/lambda_death.py λ 表承载)——
    'U_X': _Slot('#1 u_x/H_x 使用概率/需要时距;分槽/带序逐格(R17-4)'),
    'RHO_IMPUTE': _Slot('#4 ρ 摊派口径(A7);均匀摊保守首版'),
    'NBAR_ESTIMATOR': _Slot('#5 n̄ 估计器(实估,误差二阶 A3)'),
    'T_SEARCH_A': _Slot('#6 A/T_search 组成(活跃窗口付费份额确定性查表)'),
    'LAMBDA_S_EQUIP': _Slot('#7 λ_s 装备来源流/partner 到位率(只有序/支配可消费)'),
    'V_FURNACE': _Slot('#8 v_F/v_B 炉/死库存价值(sim 唯一标定通道)'),
    'C_FRAME_Q': _Slot('#9 c_frame/q(P34-b;q plaza 先验只撑量级)'),
    'DELTA_P_WIN': _Slot('#10 Δp(d→胜率换算;P43 只供外差项)'),
    # —— 类型级封印族(R10-2:V̄ 拟合族永不作闸门)——
    'V_BAR': _Slot('#13 V̄ 刷新价值门量;比较项不授权,禁作闸门', sealed=True),
    'P3_LENGTH_STAT': _Slot('P3 长度统计量(R41-3【拟·语料统计】;通关语料出现前不可填)'),
    # —— 卖出价值函数槽已撤(统一让位优先级迭代 3.4:旧价值函数
    #    sell_gold_equivalent 与 MERGE_PROGRESS_X2 登记槽随旧判据退役
    #    删除——排序由统一让位序列承载,无标定项;原【拟】登记沿革见
    #    git 历史)——
}

#: 槽位值存储(缺省全 None = fail-closed)
_VALUES: dict[str, CalibValue | None] = dict.fromkeys(_SLOTS)


def get(name: str) -> CalibValue | None:
    """槽位读(None = fail-closed:对应判据分支不评估/不产追加动作;
    **绝不向骨架层渗漏为否决**,同 strategy-docs/01_math_framework.md §6
    fail-closed 缺省)。封印族(V̄)恒 None。"""
    slot = _SLOTS.get(name)
    if slot is None:
        raise KeyError(f'unknown provisional slot: {name}')
    if slot.sealed:
        return None
    return _VALUES[name]


def is_none(name: str) -> bool:
    """None 期探针(θ_unavailable 等分键记数的判定入参,R24-2)。"""
    return get(name) is None


# ===== 槽位值域守卫 =====
# 位置论证:inject 系唯一开闸通道(provisional.py 头注),值域防线放
# 消费位防不住其他槽位、放调用方防不住绕行——结构防线只能在通道本体
# 做写入前校验(不合法拒绝)。未登记槽位 = 既有语义不变(无值域知识
# 不装假守卫);守卫只覆盖 ``value``,CI 端点系消费位扫描用信息不入守卫。
# (P76 两槽守卫 _guard_delta_positive/_guard_e2_probability_band 已随
# 证据门撤除;合成进度系数守卫 _guard_merge_progress_coef 已随
# MERGE_PROGRESS_X2 撤槽删除——统一让位优先级迭代 3.4。)

#: 守卫登记表(键 = 槽位名;随各槽标定逐个登记;现役空表 = 全部槽位
#: 无值域守卫)
_VALUE_GUARDS: dict[str, Callable[[CalibValue], str | None]] = {
}


def inject(name: str, value: CalibValue) -> None:
    """显式注入(唯一开闸通道;封印族拒绝;值域守卫槽越域即拒)。
    测试注入后须 ``reset`` 复原,防 session 内残留开闸状态(测试纪律:
    改全局态必须复原)。"""
    slot = _SLOTS.get(name)
    if slot is None:
        raise KeyError(f'unknown provisional slot: {name}')
    if slot.sealed:
        raise ValueError(f'slot {name} 系类型级封印族(R10-2),禁注入')
    guard = _VALUE_GUARDS.get(name)
    if guard is not None:
        violation = guard(value)
        if violation:
            raise ValueError(
                f'槽位 {name} 值域守卫拒绝注入:{violation}(T-214/)')
    _VALUES[name] = value


def reset(name: str | None = None) -> None:
    """复位(测试隔离/重注入前的清场)。"""
    if name is None:
        for k in _VALUES:
            _VALUES[k] = None
    else:
        _VALUES[name] = None


def slot_names() -> tuple[str, ...]:
    """登记槽位名全集(审计/静态断言消费)。"""
    return tuple(_SLOTS)


__all__ = ['CalibValue', 'get', 'inject', 'is_none', 'reset', 'slot_names']
