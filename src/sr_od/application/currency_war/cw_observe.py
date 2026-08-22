"""货币战争 可观测框架(统一日志 + 截图,CW 各模块共用)。

全局 logger(``log_utils.log``)+ shot_dir(``.debug/temp/currency_war/shots/``),CW 任何模块
(纯函数 / op / recognizer)直接调 ``cw_log`` / ``cw_shot`` 记观测,**不需透传 logger/shot_dir 参数**
(避免每加一个监测点都改签名链 read_equipped_below ← read_row_equipped ← recognizer)。

日志格式(A 族,本 helper 产出):``[cw]/[cw!]`` + ``[op][step][target]``(step/target 可空)+ fields + ``| shot=``;
两族前缀(A 识别观测层 / B ``[cw-<tag>]`` 流程层)与检索口径的**单一源 = docs/develop/currency_war/strategy/05_observation.md §6**。

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
    **采集钩子**:标定尚无 reader 的字段(星级 / 结算总伤害 / difficulty / streak 语义)——
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


# 观察冲突证据链(用户 2026-08-16 指示):新旧观察冲突时持久化结构化证据,供后续调研
# (M38 教训:lv4 毒化 3 个位面才被发现,中途无数 [cw!] 日志没人看 —— 冲突要进专属文件+截图,
# 离线可统计「哪个字段在哪个画面毒化频次最高」,驱动 reader 优先级)。
_CONFLICT_JOURNAL = Path(__file__).resolve().parents[4] / '.debug' / 'temp' / 'currency_war' / 'replay' / 'obs_conflicts.jsonl'

#: 冲突截图节流窗(秒;2026-08-18 治理):同 (field, verdict) 在窗内只存一张截图。
#: 实证积压 18.8GB 的根因 —— 慢性状态冲突(deployed_align「补齐」每帧触发,board
#: count 不等、level 乒乓)画面微变(gold 计数/动画帧)→ 内容哈希必新 → 每帧存 1.7MB。
#: 慢性态一例截图即代表该态,罕见类(新 verdict)不受影响照存;JSONL 证据行不受节流
#: (200B/行,统计价值保留)。300s = 每态每小时最多 ~12 张。
_CONFLICT_SHOT_THROTTLE_S: float = 300.0
_conflict_shot_ts: dict[tuple[str, str], float] = {}


def obs_conflict(field: str, old, new, screen: MatLike | None = None, *,
                 verdict: str = '', **ctx) -> None:
    """观察冲突 hook:追加 JSONL 证据行 + 去重截图。best-effort,失败不抛不阻塞。

    :param field: 冲突字段(level/gold/hp/board...)
    :param old: 上次观察值(session 持久)
    :param new: 本次读值
    :param screen: 冲突帧(传则存去重截图,文件名进证据行;**同 (field,verdict) 300s
        内只存一张**——慢性状态冲突截图节流,防每帧 1.7MB 积压)
    :param verdict: 仲裁结果描述(如 '保旧-单调守卫'/'采新-XP确认'/'待研')
    :param ctx: 附加上下文(plane/round/source/note...)
    """
    import datetime
    import json as _json
    import time as _time
    try:
        shot = None
        if screen is not None:
            _key = (field, verdict)
            _now = _time.monotonic()
            if _now - _conflict_shot_ts.get(_key, -1e9) >= _CONFLICT_SHOT_THROTTLE_S:
                _conflict_shot_ts[_key] = _now
                shot = cw_shot_unique(screen, f'obs_conflict_{field}')
        rec = {'ts': datetime.datetime.now().isoformat(timespec='seconds'),
               'field': field, 'old': old, 'new': new, 'verdict': verdict, **ctx}
        if shot:
            rec['shot'] = shot
        _CONFLICT_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with _CONFLICT_JOURNAL.open('a', encoding='utf-8') as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + '\n')
        cw_log('obs', 'conflict', field, attn=True, old=old, new=new,
               verdict=verdict, shot=shot)
    except Exception:  # noqa: BLE001  hook best-effort
        pass
