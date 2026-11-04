"""λ_death 分层表(PL 键位面键)。

单一源与键结构(PL 键=位面键,R26-H1 重写;键结构与消费语义以
P51_V3_REBUILD v3.3+本模块为单一源):
- 加载对象 = P51 v3.3 **PL 键(位面键)主表**:键 = 难度带(2)×血带(3)×
  位面(P1/P2+)×节点类型(4),共 48 格(非空 38 / 空格 10);板面/bench 维
  **不入键**(PL 键实证,旧 v3.1/v3.2 板面键表系对照存档,禁再被消费位引用)。
- 表数据 = ``data/lambda_death_pl_v33.json``(由 tools/cw/proofs/p51/
  gen_pl_v33_json.py 从 P51_V3_REBUILD v3.3 运行产物生成,含逐格消费标签
  与空格回退处置)。**启动必载**(R2-4):import 时即加载;加载失败或格值
  None = 运行时损坏守卫 + 报警,不作合法缺省姿态。
- **现行消费面 = 查表基础设施**(difficulty_band 派生审计登记/
  HP_BAND_NEAR_DEATH 血带结构基准 predicates 观测件消费):λ 表本体
  保留为 P51 标定工件;原决策消费族(λ 顾问/exposure 比较/差分复合项/
  升档器排序键/floor_eff 保利息门)已随血线地板/λ 顾问/升档器删除链与
  拦截层删除链停用,键构造维(四维键串与血带映射)已随 hp 判据删除面
  孤儿化撤除(R-6 裁定:λ 表血带维孤儿化申报)——新增决策消费须先过
  λ 表使用纪律审查(区间敞口比较 + 保守端 + 单调约束;禁边际引用、
  禁闸门,R30-4)。
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

#: 濒死带边界(血带结构基准单一源;消费 = statefn/predicates p1/p2_blood_floor
#: 濒死带观测谓词阈值,R-7 保留面。血带维其余键结构已随 hp 判据删除面
#: 撤除,R-6 孤儿化申报)
HP_BAND_NEAR_DEATH: int = 15
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

    难度维=局内敌方难度读数读取真值优先(语料覆盖 90%)+公式 interim 兜底(残差中位 0,
    P51_V3_REBUILD §2);真值缺失(None)时**返回 None 交由键查询落域外**,
    不在本函数内静默兜底——interim 公式系数系【推·语料拟合】量(随语料分布
    漂移,R29-6),其形态登记在 audit/derived.py,标定批注入前禁产假真值。
    """
    if difficulty_value is None:
        return None
    return 'D0' if difficulty_value < DIFFICULTY_BAND_BOUND else 'D1'


def cell(key: str | None) -> LambdaCell | None:
    """键 → 表格(查表唯一入口;None=域外/空键/损坏态,三态同判 R52-4a)。"""
    if key is None or not _LAMBDA_TABLE:
        return None
    return _LAMBDA_TABLE.get(key)


__all__ = [
    'DIFFICULTY_BAND_BOUND', 'HP_BAND_NEAR_DEATH',
    'LambdaCell', 'LambdaTableCorruptError', 'cell', 'difficulty_band',
    'table_loaded',
]
