"""λ_death 分层表(PL 键位面键)+ 区间敞口比较 + 差分复合项(第三口)。

单一源与键结构(PL 键=位面键,R26-H1 重写;键结构与消费语义以
P51_V3_REBUILD v3.3+本模块为单一源):
- 加载对象 = P51 v3.3 **PL 键(位面键)主表**:键 = 难度带(2)×血带(3)×
  位面(P1/P2+)×节点类型(4),共 48 格(非空 38 / 空格 10);板面/bench 维
  **不入键**(PL 键实证,旧 v3.1/v3.2 板面键表系对照存档,禁再被消费位引用)。
- 表数据 = ``data/lambda_death_pl_v33.json``(由 tools/cw/proofs/p51/
  gen_pl_v33_json.py 从 P51_V3_REBUILD v3.3 运行产物生成,含逐格消费标签
  与空格回退处置)。**启动必载**(R2-4):import 时即加载;加载失败或格值
  None = 运行时损坏守卫 + 报警,不作合法缺省姿态(P51 工件主表采集物带 CI,
  连续模型标定后退役)。
- λ 合法消费形态(P51 §5-11 / 00_framework §6 λ 表使用纪律):区间敞口比较 + 保守端
  + 单调约束;禁边际引用、禁闸门;阈值类消费一律扫描带形态(辖未来新消费位,
  现存消费位=空集,R30-4)。本模块对外只暴露:
  ① λ CI 端点查询(lambda_ci / cell)②区间敞口比较 API(布尔)③差分复合项
  算子(第三口,不透明对象)。全量 W_floor/W_flow 数值模块私有,类型上不对外
  暴露(R5-7 接口收口)。
- floor_eff:0.1 死阈值段分类投影已随三段管辖退役(R26-H1/R10-1);现行
  floor_eff = **arm2 结构守息门金下限 10×cap_resolved**(零 λ 依赖,R8-4
  参数化:默认局 cap=5 还原 50;买断制 cap=0 ⇒ 门=0,息恒 0 无可守)。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    pass

#: 表工件路径(与本模块同目录 data/ 下;启动必载,R2-4)
_TABLE_PATH: Path = Path(__file__).parent / 'data' / 'lambda_death_pl_v33.json'

#: 血带边界(PL 键血带维=P51_V3_REBUILD v3.3 键结构:hp≤15 / 15<hp≤40 / hp>40;
#: hp 入路由键与「hp 不作因果输入」两条分写并存——用户裁定二,R27-3)
HP_BAND_NEAR_DEATH: int = 15
HP_BAND_MID: int = 40
#: 难度带分界(P51 v3.3 Part 1 难度带定界数据分布驱动:(103,108)/(108,132))
DIFFICULTY_BAND_BOUND: int = 108


@dataclass(frozen=True)
class LambdaCell:
    """λ3 表单格(3 轮窗累积危险率的单调 PAV 估计 + cluster bootstrap CI)。

    label 取值:``可消费`` / ``仅方向`` / ``禁用`` / ``空格``(空格=表状态机
    第四态,空格≠域外≠损坏,R31-1;fallback=表侧权威回退处置文案)。
    """

    n: int
    mono: float | None
    ci_lo: float | None
    ci_hi: float | None
    label: str
    fallback: str = ''


class LambdaTableCorruptError(RuntimeError):
    """λ 表损坏守卫(R2-4):启动必载失败/格值缺失时抛出并报警。

    消费纪律:判据侧捕获后按「缺输入=最保守信号面」处置(§2.0-3 规格③:
    动作面降 signal-only,R55-3);本模块只负责守卫与报警,不替判据定行为。
    """


def _load_table() -> dict[str, LambdaCell]:
    """启动必载 + 损坏守卫(R2-4):import 期执行,失败即报警并置损坏态。

    损坏态的载体选择:抛错会打断整个包 import(把「表损坏」升级成「核不存在」,
    两态不可辨),故损坏态=空 dict + 一次性 ``[cw!][lambda]`` 报警——查表返回
    None(与域外同判,R52-4a:缺输入=同判,不另立第三读),守卫测试经
    ``_ALARM_FIRED`` 探针断言报警确发。
    """
    global _ALARM_FIRED
    try:
        raw = json.loads(_TABLE_PATH.read_text(encoding='utf-8'))
        cells: dict[str, LambdaCell] = {}
        for key, c in raw['cells'].items():
            if c['label'] in ('可消费', '仅方向'):
                # 可消费格必须有完整 CI 端点——缺任一端=损坏(禁伪精度格混入消费)
                if c['ci_lo'] is None or c['ci_hi'] is None or c['mono'] is None:
                    raise ValueError(f'consumable cell missing CI: {key}')
            cells[key] = LambdaCell(
                n=c['n'], mono=c['mono'], ci_lo=c['ci_lo'], ci_hi=c['ci_hi'],
                label=c['label'], fallback=c.get('fallback', ''))
        if len(cells) != 48:
            raise ValueError(f'expect 48 cells, got {len(cells)}')
        return cells
    except Exception as e:  # noqa: BLE001 - 损坏守卫须兜住一切载入失败形态
        _ALARM_FIRED = True
        log.error('[cw!][lambda] λ_death PL 键主表(v3.3)启动必载失败=%s;'
                  '查表将恒返 None(域外同判),判据侧按缺输入最保守信号面处置', e)
        return {}


#: 损坏报警探针(True=本次进程内已发过损坏报警;测试断言用,生产行为不变)
_ALARM_FIRED: bool = False

#: 启动必载的表(R2-4;损坏态=空 dict + 报警,见 _load_table)
_LAMBDA_TABLE: dict[str, LambdaCell] = _load_table()


def table_loaded() -> bool:
    """表健康探针:启动必载成功且非损坏态(测试/遥测消费)。"""
    return bool(_LAMBDA_TABLE) and not _ALARM_FIRED


def difficulty_band(difficulty_value: int | None) -> str | None:
    """难度→难度带(D0/D1)。

    难度维=局内旗牌读取真值优先(语料覆盖 90%)+公式 interim 兜底(残差中位 0,
    P51_V3_REBUILD §2);真值缺失(None)时**返回 None 交由键查询落域外**,
    不在本函数内静默兜底——interim 公式系数系【推·语料拟合】量(随语料分布
    漂移,R29-6),其形态登记在 audit/derived.py,标定批注入前禁产假真值。
    """
    if difficulty_value is None:
        return None
    return 'D0' if difficulty_value < DIFFICULTY_BAND_BOUND else 'D1'


def hp_band(hp: int | None) -> str | None:
    """血量→血带(hp<=15 / hp15-40 / hp>40);hp 经 λ 间接入卖面价值数值合法
    (裁定二/R27-3:hp 不入账本/不入金流,入概率路由键)。缺读 None→None。"""
    if hp is None:
        return None
    if hp <= HP_BAND_NEAR_DEATH:
        return 'hp<=15'
    if hp <= HP_BAND_MID:
        return 'hp15-40'
    return 'hp>40'


def make_key(difficulty: int | None, hp: int | None, plane: int,
             node_type: str) -> str | None:
    """四维观测量 → PL 键串(``D*|hp*|P*|node``)。

    plane:位面序号 1/2/3(P2 起并入 ``P2+`` 键维,P51 v3.3 主表位面维二值化)。
    任一维缺失(None/空)→ 返回 None(键观测量缺失=域外同款不卖/不判,
    R27-2 断言③)。
    """
    d = difficulty_band(difficulty)
    h = hp_band(hp)
    if d is None or h is None or not node_type:
        return None
    pl = 'P1' if plane <= 1 else 'P2+'
    return f'{d}|{h}|{pl}|{node_type}'


def cell(key: str | None) -> LambdaCell | None:
    """键 → 表格(查表唯一入口;None=域外/空键/损坏态,三态同判 R52-4a)。"""
    if key is None or not _LAMBDA_TABLE:
        return None
    return _LAMBDA_TABLE.get(key)


def lambda_ci(key: str | None) -> tuple[float, float] | None:
    """键 → (CI 下端, CI 上端)。

    仅 ``可消费`` 格返回端点;禁用/仅方向/空格/域外 → None(消费端 fail-closed)。
    消费纪律:端点随消费位分键(λ̄_detection/λ̄_gate 同端不同计数值域,R52-2/
    R55-1 定谳两端同取 CI 下端;卖面 V_power 系数取 CI 上端——组-端取端纪律,
    原 design_economy §E4.1 组-端对照表已删档,考古走 git 历史)。**本函数只供 statefn 层内部与已登记复合形态消费**,
    判据模块禁自持端点构造 d̂(R19-3)。
    """
    c = cell(key)
    if c is None or c.label != '可消费':
        return None
    return (c.ci_lo, c.ci_hi)  # type: ignore[return-value]——可消费格载入期已验非 None


def floor_eff(cap_resolved: int) -> int:
    """arm2 结构守息门金下限 = 10×cap_resolved(R8-4 参数化)。

    0.1 死阈值的二值投影已随三段管辖退役(R26-H1);默认局 cap=5 还原 50,
    买断制 cap=0 ⇒ 门=0(息恒 0 无可守,语义正确)。零 λ 依赖的结构安全阀。
    """
    return 10 * cap_resolved


def exposure_ge(key: str | None, gold: int, ibar_remaining_product: float,
                threshold: float) -> bool | None:
    """区间敞口比较 API(P51 §5-11 合法消费形态;布尔返回,R5-7 收口①)。

    语义:``λ_U(key) × (g + Ī×R_剩余) ≥ threshold`` 是否成立——W_floor 的
    **区间比较形态**(消费侧拿不到 W 全量数值,只能问布尔)。取 CI 上端 =
    敞口上界(保守端:卖面门槛上偏方向,L-R3-1 推论 2)。域外/损坏/不可消费
    格 → None(调用方按缺输入最保守处置,§2.0-3 规格③)。
    """
    ci = lambda_ci(key)
    if ci is None:
        return None
    return ci[1] * (gold + ibar_remaining_product) >= threshold


class ExposureComposite:
    """第三口差分复合项(R15-2/R16-3/R19-3):d̂×(g+Φ̂_full) 的不透明封装。

    输出数值 ≡ 权威式 d̂×(g+Ī×R_剩余) 水平值;**裸 Φ̂/全量 Φ/W 数值在类型上
    不可达**(R5-7)。合法运算白名单 = 加法与比较仅两种(R19-3):减法/乘法/
    除法/数值取值接口在类型上不可达——乘常数亦不开(1/d̂ 系运行时算得值,
    开乘常数即重开反解口 Φ̂=复合项×(1/d̂)−g)。防线强度=约定+评审面
    (比较二分泄露封装数值不可防,登记表 R19);判据侧自持 λ 端点构造 d̂
    或直算 d̂×(g+·) 形态 = 模式审计红。
    """

    __slots__ = ('_value',)

    def __init__(self, value: float) -> None:
        object.__setattr__(self, '_value', float(value))

    def __add__(self, other: object) -> ExposureComposite:
        if isinstance(other, ExposureComposite):
            return ExposureComposite(self._value + other._value)
        if isinstance(other, (int, float)):
            return ExposureComposite(self._value + float(other))
        return NotImplemented

    __radd__ = __add__

    def __lt__(self, other: object) -> bool:
        return self._cmp(other) < 0

    def __le__(self, other: object) -> bool:
        return self._cmp(other) <= 0

    def __gt__(self, other: object) -> bool:
        return self._cmp(other) > 0

    def __ge__(self, other: object) -> bool:
        return self._cmp(other) >= 0

    def _cmp(self, other: object) -> int:
        ov = other._value if isinstance(other, ExposureComposite) else float(other)  # type: ignore[arg-type]
        if self._value < ov:
            return -1
        return 0 if self._value == ov else 1

    # —— 白名单外运算:类型不可达(白名单=add/compare,R19-3)——
    def __sub__(self, other: object) -> float:  # pragma: no cover——守卫路径
        raise TypeError('ExposureComposite 白名单外运算:减法不可达(R19-3)')

    def __mul__(self, other: object) -> float:  # pragma: no cover
        raise TypeError('ExposureComposite 白名单外运算:乘法不可达(R19-3)')

    __rmul__ = __mul__

    def __truediv__(self, other: object) -> float:  # pragma: no cover
        raise TypeError('ExposureComposite 白名单外运算:除法不可达(R19-3)')

    def __float__(self) -> float:  # pragma: no cover
        raise TypeError('ExposureComposite 数值取值接口不可达(裸 Φ̂ 反解封印,R15-2)')


def differential_composite(key: str | None, gold: int,
                           ibar: int, r_remaining: int) -> ExposureComposite | None:
    """第三口算子入口(R16-5 对拍锚对象):模块内直算 d̂×(g+Ī×R_剩余)。

    d̂ 构造收在模块内(R19-3):**R29-3 定谳——λ_L 取表内同格 CI 下端 ⇒
    d̂ = 同格 CI 宽度(λ_U−λ_L)**(PL 键下卖出不动键,平移在差分中抵消;
    旧 λ_L:=0 形态落码即红=过保守形态锚)。Φ̂_full = Ī×R_剩余(基础流
    组成下界估计器,R2-8)仅模块内部使用。域外/损坏/不可消费格 → None
    (该件不卖,fail-closed,R6-5 同款方向)。
    """
    ci = lambda_ci(key)
    if ci is None:
        return None
    d_hat = max(0.0, ci[1] - ci[0])
    return ExposureComposite(d_hat * (gold + ibar * r_remaining))


def consumable_keys() -> tuple[str, ...]:
    """C 集合(可消费格键全集;λ 顾问分位参考分布的定义域,§2.0-3 规格①)。"""
    return tuple(k for k, c in _LAMBDA_TABLE.items() if c.label == '可消费')


def lambda_u_order() -> tuple[float, ...]:
    """C 集合 λ_U 降序全序(R31-6:λ_U=1.000 饱和截断格按 CI 下端次键,n 大者
    优先——并列打破后 tie-break 值,升档器排序键消费位)。"""
    items: list[tuple[float, float, int]] = []
    for k in consumable_keys():
        c = _LAMBDA_TABLE[k]
        assert c.ci_lo is not None and c.ci_hi is not None
        items.append((c.ci_hi, c.ci_lo, c.n))
    items.sort(key=lambda t: (-t[0], -t[1], -t[2]))
    return tuple(t[0] for t in items)


__all__ = [
    'DIFFICULTY_BAND_BOUND', 'ExposureComposite', 'HP_BAND_MID',
    'HP_BAND_NEAR_DEATH', 'LambdaCell', 'LambdaTableCorruptError',
    'cell', 'consumable_keys', 'differential_composite', 'difficulty_band',
    'exposure_ge', 'floor_eff', 'hp_band', 'lambda_ci', 'lambda_u_order',
    'make_key', 'table_loaded',
]

def _private_table_view() -> dict[str, LambdaCell]:
    """审计钩子(derived.py 登记用;禁判据侧直接消费私有表 dict)。"""
    return dict(_LAMBDA_TABLE)
