"""货币战争 可观测框架(统一日志 + 截图,CW 各模块共用)。

全局 logger(``log_utils.log``)+ shot_dir(运行时截图目录),CW 任何模块
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
from sr_od.application.currency_war.kernel import cw_telemetry_exit

_log = log_utils.log
# 仓库根经 one_dragon.utils.file_utils.get_project_root 统一定位(包内禁文件相对层级硬锚)
_SHOT_DIR = get_project_root() / '.debug' / 'temp' / 'currency_war' / 'shots'

# ===== CW 遥测/深评固定落盘根(单一源;2026-09-07 用户裁定)=====
# 结构:telemetry/{live,matches,sim} 三层——live = 实时追加流(统一
# state journal 等 jsonl,跨局追加行内带 run_id,不按局拆文件;op_journal
# 已随 2026-09-15 用户裁定退役,op 调用流归宿 = server 主日志 [cw-op] 行);
# matches = 按局装配档案(局终旁路装配器写,见 telemetry/match_archive);
# sim = sim 批账本(每批一目录)。深评报告根独立于 telemetry(消费面是人读的
# 复盘 md):.debug/currency_war/deep_review/。
# 旧根 .debug/temp/currency_war/{replay,sim_runs} 同期退役:该处历史
# 材料已迁新树,旧路径不再有任何活跃写点(存量数据一次性迁移见
# tools/cw/migrate_telemetry_tree.py,可重跑补迁运行中局的终局产物)。
# 全部经 get_project_root 仓根锚定:旧的相对 Path 形态 cwd 敏感
# (非仓根 cwd 启动即指错目录,sim/pool 审查#7 同因先改绝对,此处统一)。
TELEMETRY_ROOT: Path = (get_project_root() / '.debug' / 'currency_war'
                        / 'telemetry')
LIVE_DIR: Path = TELEMETRY_ROOT / 'live'
MATCHES_ROOT: Path = TELEMETRY_ROOT / 'matches'
SIM_ROOT: Path = TELEMETRY_ROOT / 'sim'
DEEP_REVIEW_ROOT: Path = (get_project_root() / '.debug' / 'currency_war'
                          / 'deep_review')

#: 实时流根(遥测 recorder/query/match_archive 的 replay_dir 语义 = 本目录;
#: 保留旧符号名作别名,「replay_dir」参数名在 query/cli 全链沿用,整体
#: 更名是独立重构不属本批——路径才是用户裁定面,符号名不是)。
DEFAULT_REPLAY_DIR: Path = LIVE_DIR

# ===== 退役旧根(布局裁定前的落点;写端守卫拒写面)=====
# 为什么升为常量:2026-09-07 22:20:52 实证——write_batch_ledger 的禁写
# 守卫只锚当前生产根时,以旧根为 out_dir 的空批把历史三流整份截断
# (事故对账与守卫裁决 = ADR-0586「单一源与守卫」节
# 及其 2026-09-07 22:20:52 空批截断记载)。退役根必须与生产根同级受守卫辖,直到旧根目录物理清除为止。
#: 字面量按路径分段拼装(不写成可被墓碑扫描命中的连续串):本声明是
#: 「否定式退役背书」,墓碑扫描辖的是回流写点,不是本声明本身。
RETIRED_STREAMS_ROOT: Path = (get_project_root() / '.debug' / 'temp'
                              / 'currency_war' / 'replay')
RETIRED_SIM_ROOT: Path = (get_project_root() / '.debug' / 'temp'
                          / 'currency_war' / 'sim_runs')


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

    同名覆盖(最新);路径为运行时截图目录下 ``<name>.png``。
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
# 删除波 1(用户 2026-09-10 直迁裁定):独立证据文件的写入端退役,证据归宿
# = 统一 state 账本行型 2(obs_event,GameState
# .note_obs_event;同流占版本内嵌当时 state),行结构/截图节流/告警门语义
# 原样收编(retirement.md §2 obs_conflicts 行)。存档只读:历史冲突行仍可
# 经判读 CLI 旧视图读(不迁移)。

#: 冲突截图节流窗(秒):同 (field, verdict) 在窗内只存一张截图。
#: 实证积压 18.8GB 的根因 —— 慢性状态冲突(deployed_align「补齐」每帧触发,board
#: count 不等、level 乒乓)画面微变(gold 计数/动画帧)→ 内容哈希必新 → 每帧存 1.7MB。
#: 慢性态一例截图即代表该态,罕见类(新 verdict)不受影响照存;证据行不受节流
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
    """观察冲突 hook:证据行进统一 state 账本(obs_event)+ 去重截图。best-effort,失败不抛不阻塞。

    :param field: 冲突字段(level/gold/hp/board...)
    :param old: 上次观察值(session 持久)
    :param new: 本次读值
    :param screen: 冲突帧(传则存去重截图,文件名进证据行;**同 (field,verdict) 300s
        内只存一张**——慢性状态冲突截图节流,防每帧 1.7MB 积压)
    :param verdict: 仲裁结果描述(如 '保旧-单调守卫'/'采新-XP确认'/'待研')
    :param ctx: 附加上下文(plane/round/source/note...)
    """
    import datetime
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
        # 补 run_id 归属键(唯一汇点内部自取,调用方零改动;历史行无此键,
        # 读取端按「有键才过滤」容忍)。空串=局外冲突(进程首局前),不写假键。
        # run_id 读取经 kernel/cw_telemetry_exit 钩子位(零直依 telemetry)。
        _rid = cw_telemetry_exit.current_run_id()
        if _rid:
            rec['run_id'] = _rid
        if shot:
            rec['shot'] = shot
        # 证据归宿 = 账本行型 2(obs_event;占版本内嵌当时 state)。供给槽
        # 缺省关(未装配/无会话)= 行不落——与账本自身「无 sink 拒写」语义
        # 一致;旁路缺陷台账行不受此门照常供给。渠道签名(§3.2.1 ①类属):
        # actor = 本仲裁汇点,行内身份可对账(签名必填纪律 R5 W1,ADR-0634)。
        _gs = cw_telemetry_exit.obs_event_board()
        if _gs is not None:
            with contextlib.suppress(Exception):
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                _gs.note_obs_event(
                    'arbitrate', str(field),
                    {'old': old, 'new': new, **ctx},
                    verdict=str(verdict or ''),
                    obs_phase=str(_OBS_PHASE or ''),
                    sig=ChannelSig(family='obs', actor='obs_conflict',
                                   mode='read'),
                    evidence_refs=([{'shot': str(shot)}] if shot else []))
        cw_log('obs', 'conflict', field, attn=True, old=old, new=new,
               verdict=verdict, shot=shot)
        # gold_delta 分级消费(审计建议,用户裁决落地):|gap|>10 升级为
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
        #(缺陷台账 = 保留专用流;台账行 refs 指 state journal (run_id,v) 锚行
        #(构造单一源 = cw_telemetry_exit.journal_refs,无账本媒体时诚实省略),
        # 不复制数据;调用方零改动)。外层 try/except 已兜底,旁路失败不影响证据行。
        # 落账经 kernel/cw_telemetry_exit 钩子位(缺省关,生产在
        # CurrencyWarApp.__init__ 注入真实现)。
        cw_telemetry_exit.bypass_obs_conflict_to_defect(rec)
    except Exception:  # noqa: BLE001  hook best-effort
        pass


# ===== 策略激活对拍暂存槽(消费者=obs.cw_observation 构建 state 读
# session.active_strategies 处(obs→kernel 合法向)——槽模式与 _OBS_PHASE
# 同族:生产→消费紧邻、消费即清。原生产者(投资策略卡采集遥测)已随
# invest_cards 流写入端退役删除(删除波 1);槽与消费
# 面保留,候 strategy_offer 收编批重接生产端)=====
_PENDING_STRATEGY_PICK: str | None = None


def stage_pending_strategy_pick(name: str) -> None:
    """生产者:暂存「声明选中策略名」(识别失败/非策略类不暂存,写入端判)。"""
    global _PENDING_STRATEGY_PICK
    _PENDING_STRATEGY_PICK = name


def consume_pending_strategy_pick() -> str | None:
    """消费者:取走暂存的声明选中策略名并清槽(无暂存 → None)。"""
    global _PENDING_STRATEGY_PICK
    pick = _PENDING_STRATEGY_PICK
    _PENDING_STRATEGY_PICK = None
    return pick
