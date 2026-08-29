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

import contextlib
import hashlib
from pathlib import Path

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils, log_utils
from one_dragon.utils.file_utils import get_project_root

_log = log_utils.log
# 仓库根经 one_dragon.utils.file_utils.get_project_root 统一定位(包内禁文件相对层级硬锚)
_SHOT_DIR = get_project_root() / '.debug' / 'temp' / 'currency_war' / 'shots'

# 默认 replay 账本目录(分包期 3 自 telemetry/cw_telemetry.py 下沉本模块:
# sim 桶消费它而 sim 禁依 telemetry,观测基础设施归 kernel——telemetry/sim
# 均可合法上行 import)。值保持原样(相对 Path,cwd 即仓根的运行口径不变)。
DEFAULT_REPLAY_DIR = Path('.debug/temp/currency_war/replay')


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


# 观测阶段上下文(ADR-0462 规范入口序列「先清场、再识别、后动作」):read_game_state
# 按调用点传入的阶段键(prep_clean/prep_shop_open/battle_or_transit)置位,obs_conflict
# 落证据行时带上(键 obs_phase)——噪声判定位的数据面:规范落地后 P0 清场期/overlay 期
# 来源的冲突行应 ≈0(这些阶段整条备战识别链不跑,物理上无冲突可留证)。
# best-effort:异常路径漏复位只影响后续冲突行的阶段标注,不影响行为;read_game_state
# 每次入口重新置位自愈。
_OBS_PHASE: str | None = None


def set_obs_phase(phase: str | None) -> None:
    """置/清当前观测阶段键(见 _OBS_PHASE 注)。"""
    global _OBS_PHASE
    _OBS_PHASE = phase


def current_obs_phase() -> str | None:
    """读当前观测阶段键(None=未置位/全量路径)。"""
    return _OBS_PHASE


# 观察冲突证据链(用户 2026-08-16 指示):新旧观察冲突时持久化结构化证据,供后续调研
# (M38 教训:lv4 毒化 3 个位面才被发现,中途无数 [cw!] 日志没人看 —— 冲突要进专属文件+截图,
# 离线可统计「哪个字段在哪个画面毒化频次最高」,驱动 reader 优先级)。
_CONFLICT_JOURNAL = get_project_root() / '.debug' / 'temp' / 'currency_war' / 'replay' / 'obs_conflicts.jsonl'

#: 冲突截图节流窗(秒;2026-08-18 治理):同 (field, verdict) 在窗内只存一张截图。
#: 实证积压 18.8GB 的根因 —— 慢性状态冲突(deployed_align「补齐」每帧触发,board
#: count 不等、level 乒乓)画面微变(gold 计数/动画帧)→ 内容哈希必新 → 每帧存 1.7MB。
#: 慢性态一例截图即代表该态,罕见类(新 verdict)不受影响照存;JSONL 证据行不受节流
#: (200B/行,统计价值保留)。300s = 每态每小时最多 ~12 张。
_CONFLICT_SHOT_THROTTLE_S: float = 300.0
_conflict_shot_ts: dict[tuple[str, str], float] = {}


#: gold_delta 分级告警门(|gap|>10 → warning 级告警行,局中可被哨兵/监控 grep;
#: ≤10 维持留证不告警)。门取 10 的依据:OCR 单帧噪声实测 ≤3(见 obs_conflicts
#: 历史行小 gap 段),常规收支误记 ±2 内被审计容差吸收;>10 已是「账面与实读
#: 系统性错位」量级(息线/花金义务判定整体失真),必须当下可见。
GOLD_DELTA_ALARM_GAP: int = 10


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
        if _OBS_PHASE:
            rec['obs_phase'] = _OBS_PHASE   # ADR-0462 噪声判定位:冲突行按阶段分类
        # W603:补 run_id 归属键(唯一汇点内部自取,调用方零改动;历史行无此键,
        # 读取端按「有键才过滤」容忍)。空串=局外冲突(进程首局前),不写假键。
        from sr_od.application.currency_war.telemetry import cw_telemetry as _cw_tel
        _rid = _cw_tel.current_run_id()
        if _rid:
            rec['run_id'] = _rid
        if shot:
            rec['shot'] = shot
        _CONFLICT_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with _CONFLICT_JOURNAL.open('a', encoding='utf-8') as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + '\n')
        cw_log('obs', 'conflict', field, attn=True, old=old, new=new,
               verdict=verdict, shot=shot)
        # gold_delta 分级消费(W489 审计建议,用户裁决落地):|gap|>10 升级为
        # warning 告警行(检索锚 ``[cw!][alarm][gold_delta]``,哨兵/监控 grep 本行
        # 即接;≤10 维持留证)。账面期望 vs 实读的大额错位意味着金模型已系统性
        # 漂移,等局后统计才发现会喂错整局的息线/花金判断。
        if field == 'gold_delta':
            try:
                _gap = abs(int(new) - int(old))
            except (TypeError, ValueError):
                _gap = None
            if _gap is not None and _gap > GOLD_DELTA_ALARM_GAP:
                _log.warning('[cw!][alarm][gold_delta] gap=%s old=%s new=%s '
                             'verdict=%s %s', _gap, old, new, verdict, ctx)
        # 统一缺陷台账旁路(纯观测):同一冲突归一落 defect_ledger.jsonl
        #(本流=原始证据层保持原样,台账行经 refs 指回本行,不复制数据;
        # 调用方零改动)。外层 try/except 已兜底,旁路失败不影响本流落盘。
        from sr_od.application.currency_war.telemetry import cw_telemetry
        cw_telemetry.bypass_obs_conflict_to_defect(rec)
    except Exception:  # noqa: BLE001  hook best-effort
        pass


# ===== W515 分级安灯 L0 自动停线·游戏侧执行器 =====
# 判定与闩锁在 cw_telemetry(纯逻辑,不碰游戏);三要素的「截图 + flag +
# stop_running」需要 ctx/controller,归本模块(可观测框架,exec 失败安灯
# 先例 = prep_director._exec_fail_hook_check 同款顺序)。

def find_running_ctx():
    """进程内定位 SrContext(安灯停线专用)。

    为什么用 gc 扫描:安灯判定在 cw_telemetry 模块级旁路里发生,调用栈
    (obs_conflict / shop 记账)各层签名都不带 ctx,而 ctx 登记点全在
    本批禁触文件(battle_loop/prep_director);服务进程内 SrContext 恒
    单实例(server.py / GUI 各只建一个),扫描定位无歧义。成本:仅 L0
    停线时刻每局至多一次,百毫秒级,不进常规路径。根治(框架级 ctx
    注册表)归后续基建批。
    """
    import gc

    from sr_od.context.sr_context import SrContext
    for obj in gc.get_objects():
        if isinstance(obj, SrContext):
            return obj
    return None


def _save_andon_frame(ctx, payload: dict) -> str:
    """停机时刻另存一张现场帧(与 exec 失败安灯同风格:save_debug_image
    带 prefix 落 .debug/images/;独立截图不污染 op 循环的帧缓存)。"""
    from one_dragon.utils import debug_utils
    if ctx.controller is None or not ctx.controller.is_game_window_ready:
        return ''
    _ts, img = ctx.controller.screenshot(independent=True)
    if img is None:
        return ''
    return debug_utils.save_debug_image(
        img, prefix=(f"l0_andon_{payload.get('run_id')}"
                     f"_p{payload.get('plane')}r{payload.get('round_num')}_stop"))


def stop_for_l0_andon(payload: dict, ctx=None) -> bool:
    """L0 安灯三要素执行(cw_telemetry 缺省 handler;返回 True=已停)。

    时序:现场帧 → flag → stop_running(证据先落盘再停,与 exec 安灯一致;
    stop 是设位信号,当前 in-flight 动作步走完后由 op 轮回顶检测退出)。
    ctx=None 时进程内定位(find_running_ctx);找不到 ctx → False 不停
    (fail-safe:无停线通道时绝不动台账以外的任何状态)。
    """
    try:
        if ctx is None:
            ctx = find_running_ctx()
        if ctx is None:
            return False
        stop_shot = ''
        with contextlib.suppress(Exception):   # 截图失败不拦停机(flag 是主哨兵,同 exec 安灯)
            stop_shot = _save_andon_frame(ctx, payload)
        from sr_od.application.currency_war.telemetry import cw_telemetry
        cw_telemetry.write_l0_andon_flag(
            cw_telemetry.l0_andon_flag_path(),
            run_id=str(payload.get('run_id') or ''),
            surface=str(payload.get('surface') or ''),
            kind=str(payload.get('kind') or ''),
            expected=str(payload.get('expected') or ''),
            observed=str(payload.get('observed') or ''),
            plane=int(payload.get('plane') or 0),
            round_num=int(payload.get('round_num') or 0),
            refs=payload.get('refs') or [],
            defect_shot=payload.get('shot'),
            stop_shot=stop_shot)
        rc = getattr(ctx, 'run_context', None)
        if rc is None:
            return False
        rc.stop_running(reason='hook:cw_l0_andon')
        return True
    except Exception:  # noqa: BLE001  安灯失败不阻断业务流
        return False
