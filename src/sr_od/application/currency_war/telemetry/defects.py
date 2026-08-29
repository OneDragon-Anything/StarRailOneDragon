"""缺陷判定与安灯:judge_severity/record_defect/bypass_* 出口/安灯旗(自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
    SEVERITY_L0_ANDON,
    SEVERITY_L1_ALERT,
    SEVERITY_L2_RECORD,
)
from sr_od.application.currency_war.telemetry import state as _telstate
from sr_od.application.currency_war.telemetry.state import (
    _mark_defect_reproduced,
    current_run_id,
    log,
)

# ===== 统一缺陷台账(defect_ledger.jsonl;纯观测索引层,零行为变更)=====
# 把散在 obs_conflicts(感知冲突)/ exec_events(执行失败)的缺陷口径归一:
# 旧流是原始证据层保持原样,台账每行经 evidence.refs 指回原流行——审计先查
# 台账,下钻再回原流。接线方式=在 obs_conflict / record_exec_event 写入点
# 内部各加一行旁路(调用方零改动)。obs_conflicts 行内 run_id(`w603_telemetry_wiring/` 起)由
# 唯一汇点 obs_conflict() 内部自取 current_run_id 补齐——历史行无此键
# (读取端按「有键才过滤」容忍),join key 台账仍并行补齐。

#: 分级三档(severity 写入端只给初判;离线可用 judge_severity 按演进后规则
#: 重判,不重写历史)。判据(观测自检框架设计 §4,三条按序):
#: ①决策关键面吗 ②gap 大吗 ③复现了吗——L0=①∧②∧③ 且裁决未自动;
#: L1=①∧② 单次,或中相关面∧②∧③;L2=其余(非关键面/小 gap/裁决已自动)。
# 分级常量单一源自分包期 4 起在 kernel/cw_telemetry_exit(obs 显式判级调用点
# 与本模块判级同取一源;telemetry→kernel 上行合法向,见顶部 import)。

#: 决策关键面(误读直接改买/升/部署决策的观测面)。
DECISION_CRITICAL_SURFACES: frozenset[str] = frozenset(
    {'gold', 'bench', 'deployed', 'level_xp', 'shop_refresh', 'phase_round'})

#: 中决策相关面(误读改辅助判断:保血阈值/成型判定/对拍解释)。
MEDIUM_CRITICAL_SURFACES: frozenset[str] = frozenset(
    {'hp', 'equip', 'strategy', 'node_seq', 'streak'})


#: 金面大 gap 门(金):与 cw_observe.GOLD_DELTA_ALARM_GAP 同源取值
#:(OCR 单帧噪声 ≤3、审计容差 ±2,>10 = 系统性错位量级)。独立常量避免
#: 台账层反向依赖观测层。
DEFECT_GAP_LARGE_GOLD: int = 10


#: obs_conflict field → 台账 surface 映射(枚举=既有冲突点全集;未映射的
#: 新字段原样落 surface,消费端按字符串聚合,枚举外值不炸)。
OBS_FIELD_TO_SURFACE: dict[str, str] = {
    'gold': 'gold', 'gold_delta': 'gold',
    'hp': 'hp', 'level': 'level_xp',
    'board': 'deployed', 'deployed_align': 'deployed',
    'deployed_count_2src': 'deployed', 'deploy_cap_domain': 'deployed',
    'deploy_cap_vs_level': 'deployed',
    'streak': 'streak', 'phase_round': 'phase_round', 'bench': 'bench',
}


#: 裁决已自动的冲突面(对账纠漂/双帧采信/双源留证——冲突被写入端自动消化,
#: 按分级判据恒 L2,不升级):deployed_align 截断补齐、board 徽标仲裁、
#: hp 上行留证、streak 双源、cap 域外双帧采信及其同族。
AUTO_RESOLVED_OBS_FIELDS: frozenset[str] = frozenset(
    {'deployed_align', 'board', 'hp', 'streak', 'deploy_cap_domain',
     'deploy_cap_vs_level', 'deployed_count_2src'})



def judge_severity(surface: str, *, gap_large: bool, reproduced: bool,
                   auto_resolved: bool = False) -> str:
    """分级初判(纯函数,可单测;离线重判即用本函数重放)。

    判据链(三条按序,见 SEVERITY_* 注):裁决已自动 → L2(自动纠漂不算
    缺陷升级对象);决策关键 ∧ 大 gap ∧ 复现 → L0(安灯;停机接线未启,
    初判仅落账标记);决策关键 ∧ 大 gap(单次)→ L1;中相关面 ∧ 大 gap ∧
    复现 → L1;其余 → L2。非数值面的「大 gap」由调用方按硬失败形态判定
    (如「计划花费>0 金差≈0」「刷新两连全同」),经 gap_large 传入。
    """
    if auto_resolved:
        return SEVERITY_L2_RECORD
    critical = surface in DECISION_CRITICAL_SURFACES
    if critical and gap_large:
        return SEVERITY_L0_ANDON if reproduced else SEVERITY_L1_ALERT
    if surface in MEDIUM_CRITICAL_SURFACES and gap_large and reproduced:
        return SEVERITY_L1_ALERT
    return SEVERITY_L2_RECORD



def record_defect(surface: str, kind: str, expected: str, observed: str, *,
                  gap: float | None = None, plane: int = 0, round_num: int = 0,
                  unit_seq: int | None = None, verdict: str = '',
                  shot: str | None = None,
                  refs: list[dict[str, str]] | None = None,
                  reader_source: str = '', note: str = '',
                  gap_large: bool = False, auto_resolved: bool = False,
                  severity: str = '', confidence: float | None = None) -> None:
    """便捷:用 current_run_id 记一条缺陷台账(与 record_spend_unit 同模式)。

    severity 显式传入优先;否则写入端按 judge_severity 初判(带复现计数)。
    run_id 空 → no-op(与其他便捷入口同门控)。confidence 透传(§2.10)。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    sev = severity or judge_severity(
        surface, gap_large=gap_large, auto_resolved=auto_resolved,
        reproduced=_mark_defect_reproduced(surface, kind, str(expected),
                                           _telstate._CURRENT_RUN_ID))
    _telstate.get_recorder().record_defect(
        surface, kind, expected, observed, run_id=_telstate._CURRENT_RUN_ID,
        plane=plane, round_num=round_num, unit_seq=unit_seq, gap=gap,
        severity=sev, verdict=verdict, shot=shot, refs=refs,
        reader_source=reader_source, note=note, confidence=confidence)
    # `w515_l0_andon/` 分级安灯 L0 自动停线(用户裁决「确认缺陷即停实机」;先例=
    # prep_director 执行失败安灯钩子)。只认显式判级 == L0_andon(零误停
    # 偏置:judge_severity 已辖 auto_resolved→L2,不在此双保险改语义);
    # 台账行已在上一行落盘,停线不改变缺陷记录的数据形状(旧消费者不破)。
    if sev == SEVERITY_L0_ANDON:
        with contextlib.suppress(Exception):   # 安灯失败不阻断业务流
            _fire_l0_andon({
                'run_id': _telstate._CURRENT_RUN_ID, 'surface': surface, 'kind': kind,
                'expected': str(expected), 'observed': str(observed),
                'gap': gap, 'plane': plane, 'round_num': round_num,
                'verdict': verdict, 'shot': shot,
                'refs': [dict(r) for r in (refs or [])],
            })



# ===== `w515_l0_andon/` 分级安灯 L0 自动停线(观测缺陷面;纯判定在本模块,游戏侧
# 三要素执行在 cw_observe.stop_for_l0_andon——本模块「纯逻辑不碰游戏」
# 的分层边界,与 prep_director 执行失败安灯「判定与执行同文件」不同)=====

#: L0 安灯哨兵 flag 相对路径(锚仓根;.debug/ 不入 git;与 exec_fail
#: 钩子 flag 分文件,值班者按文件名即知是观测面停线还是执行失败停线)。
_L0_ANDON_FLAG_RELPATH: str = '.debug/temp/currency_war/l0_andon_hook.flag'



def install_exit_hooks() -> None:
    """分包期 4 出口钩子注入(生产武装点=CurrencyWarApp.__init__,与
    ``set_l0_andon_handler`` 同点;幂等):把本模块真实现写进
    kernel/cw_telemetry_exit 的钩子槽,使 kernel/obs/decision 三桶的
    telemetry 上行出口(落账/安灯/run_id 归属键)零直依本模块。"""
    from sr_od.application.currency_war.kernel import cw_telemetry_exit
    from sr_od.application.currency_war.telemetry.recorder import (
        record_exogenous,  # 惰性:recorder 模块级依赖本模块,防环
    )

    cw_telemetry_exit.install_exit_hooks(
        run_id_provider=current_run_id,
        record_defect=record_defect,
        record_exogenous=record_exogenous,
        bypass_obs_conflict_to_defect=bypass_obs_conflict_to_defect,
        record_exec_event=_exit_record_exec_event,
        l0_andon_flag_path=l0_andon_flag_path,
        write_l0_andon_flag=write_l0_andon_flag)



def _exit_record_exec_event(run_id: str, round_num: int, action_family: str,
                            screen: str, event: str, reason: str = '',
                            retry_count: int = 0) -> None:
    """出口钩子实现:影子执行事件 → 模块级 recorder(签名对齐 recorder 方法)。"""
    _telstate.get_recorder().record_exec_event(
        run_id=run_id, round_num=round_num, action_family=action_family,
        screen=screen, event=event, reason=reason, retry_count=retry_count)



def l0_andon_flag_path() -> Path:
    """安灯哨兵 flag 绝对路径(锚仓根;分包期 0a 起走 get_project_root 真源)。"""
    from one_dragon.utils.file_utils import get_project_root

    return get_project_root() / _L0_ANDON_FLAG_RELPATH



def write_l0_andon_flag(flag_path: Path, *, run_id: str, surface: str,
                        kind: str, expected: str, observed: str,
                        plane: int = 0, round_num: int = 0,
                        refs: list[dict[str, str]] | None = None,
                        defect_shot: str | None = None,
                        stop_shot: str = '') -> str:
    """写安灯哨兵 flag(纯 IO 可单测;三要素规范同 prep_director 执行失败
    安灯 flag——HOOK-STOP 特征行 + 发生了什么 + 处理步骤 + 删除条件,
    值班者不看代码即知发生了什么)。返回写入内容(测试断言用)。
    """
    refs_txt = ';'.join(f"{r.get('stream')}:{r.get('key')}" for r in (refs or [])) or '(无)'
    shots_txt = ' | '.join(s for s in (defect_shot or '', stop_shot) if s) or '(截图失败,以台账为准)'
    content = (
        '[HOOK-STOP] L0 分级安灯停线(观测缺陷面;常驻,cw_telemetry.record_defect 判级点)\n'
        '发生了什么:观测缺陷初判达 L0(决策关键面 ∧ 大 gap ∧ 复现 ∧ 裁决未自动)——\n'
        '  同一缺陷特征本局已第二次以上再现,继续跑会把系统性误观测喂进买/升/部署决策,\n'
        '  按用户裁决「确认缺陷即停实机」停机保现场。\n'
        f'定位:run_id={run_id} surface={surface} kind={kind} '
        f'p{plane}r{round_num} ts={datetime.now().isoformat(timespec="seconds")}\n'
        f'期望:{expected}\n'
        f'观测:{observed}\n'
        f'缺陷台账:replay/defect_ledger.jsonl 同 run_id 行(refs={refs_txt})\n'
        f'截图:{shots_txt}\n'
        '处理步骤:1. 看现场截图确认画面与缺陷面;2. 按 refs 下钻原流行\n'
        '  (obs_conflicts/decisions/exec_events 等)判 reader 误读还是观测真漂移;\n'
        '  3. 修复后重启载入代码的进程,删除本 flag 再续跑。\n'
        '删除条件:安灯钩子本体是常驻行为(用户裁决),不随单次处理删除;\n'
        '  本 flag 处理完即删,防误判为未处理的新停线。\n'
    )
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(content, encoding='utf-8')
    return content



def _fire_l0_andon(payload: dict[str, Any]) -> bool:
    """安灯触发(局级闩锁;返回是否真的执行了停线)。

    闩锁在调用执行器**之前**落位:执行器异常也保证每局至多尝试一次,
    语义 = 「首见 L0 即停,后续 L0 只补台账」。
    """
    rid = str(payload.get('run_id') or '')
    if not rid or rid in _telstate._L0_ANDON_FIRED_RUNS:
        return False
    _telstate._L0_ANDON_FIRED_RUNS.add(rid)
    handler = _telstate._L0_ANDON_HANDLER
    stopped = bool(handler(payload)) if handler is not None else False
    log.warning('[cw!][andon] L0 缺陷安灯 surface=%s kind=%s p%sr%s run=%s → %s',
                payload.get('surface'), payload.get('kind'),
                payload.get('plane'), payload.get('round_num'), rid,
                '已停线(flag=l0_andon_hook.flag)' if stopped
                else ('停线未执行(游戏侧不可达,台账已留证)' if handler is not None
                      else '停线通道未注册(缺省关,仅台账)——生产武装点=CurrencyWarApp.__init__'))
    return stopped



def bypass_obs_conflict_to_defect(rec: dict) -> None:
    """obs_conflict 写入点旁路:同一冲突归一落 defect_ledger(调用方零改动)。

    rec = obs_conflicts.jsonl 已落盘的原始行(dict)——refs 指回该行
    (field+ts 定位),本函数只做口径映射(field→surface、old/new→
    expected/observed、数值对→gap),不复制观测数据。
    """
    field = str(rec.get('field') or '')
    surface = OBS_FIELD_TO_SURFACE.get(field, field)
    old, new = rec.get('old'), rec.get('new')
    gap: float | None = None
    gap_large = False
    try:
        gap = float(new) - float(old)
        if surface == 'gold' and abs(gap) > DEFECT_GAP_LARGE_GOLD:
            gap_large = True
    except (TypeError, ValueError):
        gap = None   # 文本面:gap 不填,差用 expected/observed 表达
    # `w512_obs_surfaces/`(§2.10):原流行 ctx 里带数值 confidence 时透传进台账
    #(缺省/非数值 → None,该缺陷面无置信度语义)
    conf: float | None
    try:
        conf = float(rec['confidence']) if 'confidence' in rec else None
    except (TypeError, ValueError):
        conf = None
    record_defect(
        surface, 'perception_conflict',
        expected=f'{field}: {old}', observed=str(new),
        gap=gap, plane=int(rec.get('plane') or 0),
        round_num=int(rec.get('round_num') or 0),
        verdict=str(rec.get('verdict') or ''), shot=rec.get('shot'),
        refs=[{'stream': 'obs_conflicts',
               'key': f"field={field}|ts={rec.get('ts') or ''}"}],
        reader_source=str(rec.get('source') or ''),
        gap_large=gap_large,
        auto_resolved=field in AUTO_RESOLVED_OBS_FIELDS,
        confidence=conf,
        note='旁路自 obs_conflicts 写入点(原始证据层,refs 可下钻)')



def _exec_family_surface(family: str) -> str:
    """动作族 → 台账 surface(子串匹配族名;未映射原样落,枚举外值不炸)。"""
    f = (family or '').lower()
    if 'levelup' in f:
        return 'level_xp'
    if 'refresh' in f:
        return 'shop_refresh'
    if 'buy' in f or 'sell' in f:
        return 'bench'
    if 'deploy' in f:
        return 'deployed'
    if 'equip' in f:
        return 'equip'
    return family or 'exec'



def bypass_exec_event_to_defect(rec: dict) -> None:
    """record_exec_event 写入点旁路:失败类执行事件归一落 defect_ledger。

    仅 fail/blocked/bail 进台账(执行缺陷);success_uncharged 非缺陷不进。
    写端 severity 恒初判 L2 留证——执行失败的分级安灯由既有 prep_director
    判定钩子承载(行为不变),台账先收口证据口径,分级升级属后续期。
    """
    if str(rec.get('event') or '') not in ('fail', 'blocked', 'bail'):
        return
    family = str(rec.get('action_family') or '')
    record_defect(
        _exec_family_surface(family), 'exec_fail',
        expected=f'{family} 动作生效',
        observed=f"{rec.get('event')}: {rec.get('reason')}",
        round_num=int(rec.get('round_num') or 0),
        refs=[{'stream': 'exec_events',
               'key': (f"run={rec.get('run_id') or ''}|round={rec.get('round_num') or 0}"
                       f"|family={family}|ts={rec.get('ts') or ''}")}],
        note='旁路自 exec_events 写入点(原始证据层,refs 可下钻)',
        gap_large=False, severity=SEVERITY_L2_RECORD)


