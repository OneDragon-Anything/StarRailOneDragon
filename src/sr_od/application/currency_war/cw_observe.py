# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 可观测框架(统一日志 + 截图,CW 各模块共用)。

全局 logger(``log_utils.log``)+ shot_dir(``.debug/temp/currency_war/shots/``),CW 任何模块
(纯函数 / op / recognizer)直接调 ``cw_log`` / ``cw_shot`` 记观测,**不需透传 logger/shot_dir 参数**
(避免每加一个监测点都改签名链 read_equipped_below ← read_row_equipped ← recognizer)。

日志格式(CLAUDE.md CW 节「日志格式标准」):
- ``[cw][op][step][target] fields`` —— 普通(常规识别/流程)
- ``[cw!][op][step][target] fields`` —— 需关注(漏检 MISS / 顺序异常 / UNKNOWN 未建档画面);``attn=True``
- ``| shot=<名>`` —— 配对截图(``cw_shot`` 返名),grep 漏检后看截图定位根因

检索:漏检 ``grep "[cw!].*MISS"`` / 未建档画面 ``grep "[cw!].*UNKNOWN"`` / 全 CW ``grep "[cw]"``(grep 方括号是字符类,引号或转义字面匹配)。

并发安全:logger 只读(全局配置,``info`` 不写状态);``cw_shot`` 存文件(副作用,但 MISS/异常罕见,
同名覆盖最新,并发竞争可接受)。纯函数可用(不写 ctx/session 状态,与 ``recognize`` 纯读原则兼容)。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils, log_utils

_log = log_utils.log
# cw_observe.py 在 src/sr_od/application/currency_war/,parents[4]=REPO
_SHOT_DIR = Path(__file__).resolve().parents[4] / '.debug' / 'temp' / 'currency_war' / 'shots'


def cw_log(
    op: str,
    step: str = '',
    target: str = '',
    *,
    attn: bool = False,
    shot: str | None = None,
    **fields,
) -> None:
    """记 CW 结构化日志。``[cw]/[cw!]`` + ``[op][step][target]`` + fields + ``| shot=``。

    :param op: 模块(read_equipped / read_equips / deploy / recognize ...)。
    :param step: 节点/步骤(可空)。
    :param target: 对象(slot=前排-1 / screen=备战 / char=飞霄;可空)。
    :param attn: True → ``[cw!]`` 需关注(漏检/异常/未知画面);False → ``[cw]`` 普通。
    :param shot: ``cw_shot`` 返的截图名,grep MISS 后看截图定位根因(可空)。
    :param fields: 任意 key=value(equips / val_top / MISS / UNKNOWN_screen ...)。
    """
    prefix = '[cw!]' if attn else '[cw]'
    tags = f'[{op}]' + (f'[{step}]' if step else '') + (f'[{target}]' if target else '')
    body = ' '.join(f'{k}={v}' for k, v in fields.items())
    tail = f' | shot={shot}' if shot else ''
    _log.info(f'{prefix}{tags} {body}{tail}'.strip())


def cw_shot(image: MatLike, name: str) -> str:
    """存截图(crop / 整图,RGB)到 ``shots/<name>.png``,返截图名(供 ``cw_log shot=``)。

    同名覆盖(最新);路径 ``.debug/temp/currency_war/shots/<name>.png``。
    """
    _SHOT_DIR.mkdir(parents=True, exist_ok=True)
    cv2_utils.save_image(image, str(_SHOT_DIR / f'{name}.png'))
    return f'{name}.png'


def cw_shot_unique(image: MatLike, label: str) -> str | None:
    """存截图(**内容哈希去重**,采集钩子用;best-effort 不抛)。

    视觉相同的只存一次,不同视觉(如不同星级 / 不同总伤害)各存一份。返文件名 / None(去重跳过或失败)。
    **采集钩子**(CLAUDE.md 方案):标定尚无 reader 的字段(星级 / 结算总伤害 / difficulty / streak 语义)——
    运行时采样本,离线设计 reader;**reader 设计好后直接删各调用处钩子**(临时代码,不留开关)。
    """
    try:
        _h = hashlib.md5(image.tobytes()).hexdigest()[:8]
        fp = _SHOT_DIR / f'{label}__{_h}.png'
        if fp.exists():
            return None
        _SHOT_DIR.mkdir(parents=True, exist_ok=True)
        cv2_utils.save_image(image, str(fp))
        return fp.name
    except Exception:  # noqa: BLE001  采集 best-effort,失败不阻塞识别/对局
        return None
