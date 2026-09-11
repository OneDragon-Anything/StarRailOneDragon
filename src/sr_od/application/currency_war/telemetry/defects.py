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
    journal_refs,
)
from sr_od.application.currency_war.telemetry import state as _telstate
from sr_od.application.currency_war.telemetry.state import (
    _mark_defect_reproduced,
    current_run_id,
    log,
)

# ===== 统一缺陷台账(defect_ledger.jsonl;纯观测索引层,零行为变更)=====
# 把散在观察冲突/执行失败的缺陷口径归一:台账每行经 evidence.refs 指回证据行
# ——审计先查台账,下钻再回证据行。R5 W7 refs 迁移(retirement.md §2
# defect_ledger 行,候裁 4 定谳):旧流(decisions/outcomes/obs_conflicts)
# 写面已随删除波 1 退役,refs 统一改指 journal ``(run_id,v)`` 锚(构造
# 单一源 = kernel.cw_telemetry_exit.journal_refs;无账本媒体时诚实省略)。
# 证据行现役归宿 = journal obs_event arbitrate 行(field 对账);exec 失败
# 旁路已随 exec_events 流退役消失(见文件尾注)。obs_conflicts 历史行内
# run_id 由唯一汇点自取补齐——历史行无此键(读取端按「有键才过滤」容忍)。

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
#: 新字段原样落 surface,消费端按字符串聚合,枚举外值不炸)。R5 W1 依
#: 迁移规划 obs_event 收编条目对齐调用点全集:deploy_paddle(部署 paddle
#: 识别)与 back_layout_*/layout_mismatch 系(后排布局选档)补入——证据
#: 行收编 journal 后 field 键仍沿本枚举聚合台账 surface(R5 W1/ADR-0634)。
#: tracking/star(cw_reconcile 对账域)同为活键补入:surface 保持 field
#: 同名——冲突值跨 bench|deployed 两侧(账面整体快照/跨侧角色星),归并
#: 任一单侧域会错置漂移归因;补枚举前经兜底 `get(field, field)` 即落同名,
#: 行为零变,补入仅闭合键清单(R5 W1 键封闭判据)。
OBS_FIELD_TO_SURFACE: dict[str, str] = {
    'gold': 'gold', 'gold_delta': 'gold',
    'hp': 'hp', 'level': 'level_xp',
    'board': 'deployed', 'deployed_align': 'deployed',
    'deployed_count_2src': 'deployed', 'deploy_cap_domain': 'deployed',
    'deploy_cap_vs_level': 'deployed', 'deploy_paddle': 'deployed',
    'back_layout_channel_conflict': 'deployed',
    'back_layout_unknown': 'deployed',
    'back_layout_cv_transient': 'deployed',
    'back_layout_unarchived_grid': 'deployed',
    'layout_mismatch_by_system_unit': 'deployed',
    'tracking': 'tracking', 'star': 'star',
    'streak': 'streak', 'phase_round': 'phase_round', 'bench': 'bench',
}


#: 裁决已自动的冲突面(对账纠漂/双帧采信/双源留证——冲突被写入端自动消化,
#: 按分级判据恒 L2,不升级):deployed_align 截断补齐、board 徽标仲裁、
#: hp 上行留证、streak 双源、cap 域外双帧采信及其同族。
AUTO_RESOLVED_OBS_FIELDS: frozenset[str] = frozenset(
    {'deployed_align', 'board', 'hp', 'streak', 'deploy_cap_domain',
     'deploy_cap_vs_level', 'deployed_count_2src'})


#: deployed 计数双源分歧**独立分键**(防静默;观测仲裁批新增)。
#: 语义:paddle X(游戏计数器真值)vs CV 槽位占用,分歧仲裁(取低值)
#: 触发一次计一行,不一致率 = 本 kind 行数 / 局。与旁路自 obs_conflicts 的通用
#: ``perception_conflict`` 行分键(通用行是证据层,本键是裁决事件层,
#: 判读「CV 占用源漂移率」直接查本键,不用下钻证据流行)。
#: 仲裁规则与依据 = ``cw_observation.arbitrate_deployed_count`` docstring。
DEFECT_KIND_DEPLOYED_COUNT_2SRC: str = 'deployed_count_2src_divergence'

#: 同局分歧**持续显影阈值**(逐次行数达此值再落一条 L1 升级行——真结构性
#: CV 坏死要响铃不只留痕)。取值依据 = 留证 verdict 既有口径「同局 ≥3 次
#: 排期修源」的代码化,非新拍阈值。
DEPLOYED_COUNT_2SRC_SUSTAINED_N: int = 3

#: 分歧持续显影升级行 kind(与逐次行分键:逐次行 = 每次仲裁事件恒 L2;
#: 升级行 = 每局至多一条的「持续」状态事件 L1,判读侧不合并计数)。
DEFECT_KIND_DEPLOYED_COUNT_2SRC_SUSTAINED: str = 'deployed_count_2src_sustained'

#: paddle 失读退化行独立分键(与真分歧拆分:退化帧无 paddle 真值,
#: gap 无差值语义,且不计入持续显影阈值——真分歧率不被失读帧污染,
#: 归因不单向指向 CV 占用源)。
DEFECT_KIND_DEPLOYED_COUNT_2SRC_DEGRADED: str = 'deployed_count_2src_degraded'

#: 双账槽位布局漂移分键(期望态 vs tracked 多集等价、仅槽序分歧):
#: 守卫降级不炸环,但漂移事实落台账(判读工具可查频次/局分布);
#: 处置 = 按 tracked 真值重播种投影 bench(见 cw_shop_action_ops)。
DEFECT_KIND_BENCH_SLOT_LAYOUT_DRIFT: str = 'bench_slot_layout_drift'

#: tracked 槽号健康门拦截分键:占用槽号重复/越界(对账 churn 家族的
#: 无守卫数据)→ 拒绝重播种,维持旧布局防坏槽号进不可逆卖出链。
DEFECT_KIND_BENCH_SLOT_UNHEALTHY: str = 'bench_slot_unhealthy'

#: 分歧逐次计数器驻留上限(模块级全局生命周期:常驻进程跨局累积无界;
#: 超限后清空只保当前局——历史局计数无跨局消费面,清零无损)。
_DEPLOYED_2SRC_RUN_COUNTS_MAX: int = 32

#: 分歧逐次计数器(模块级全局;run_id → 本局已记逐次行数,只计真分歧
#: ——paddle 失读退化行走独立分键不入本计数)。测试须经
#: monkeypatch 清空(测试纪律:被测路径含模块级全局时 setup 一并桩化)。
_DEPLOYED_2SRC_RUN_COUNTS: dict[str, int] = {}


def record_deployed_count_2src_divergence(paddle_n: int | None, cv_n: int,
                                          source: str) -> None:
    """记一条 deployed 计数双源分键行(best-effort;run_id 缺省 no-op)。

    真分歧(paddle 有读值):仲裁已在本侧完成(取低值),逐次行恒 L2
    留证(auto_resolved=True,不进安灯——决策面已不消费污染源);同局
    真分歧逐次行数达 ``DEPLOYED_COUNT_2SRC_SUSTAINED_N`` 再落一条 L1
    升级行(持续显影,每局至多一条,升级行不进逐次计数)。
    paddle 失读退化帧(paddle_n=None):单源 CV 行动(向板满侧),无
    paddle 真值 ⇒ gap 无差值语义——走 ``_DEGRADED`` 独立分键、gap 不填、
    不入逐次计数(退化帧不污染真分歧率,也不触发持续显影)。
    证据层(journal obs_event arbitrate 行)由调用方的 obs_conflict 留证
    并行承载,本行 refs 指认来源便于归因。
    """
    rid = _telstate._CURRENT_RUN_ID
    if not rid:
        return
    if paddle_n is None:
        record_defect(
            'deployed', DEFECT_KIND_DEPLOYED_COUNT_2SRC_DEGRADED,
            expected='paddle_x=失读(检测链退化,单源 CV 行动,向板满侧)',
            observed=f'cv_occupied={int(cv_n)}',
            gap=None, gap_large=False,
            auto_resolved=True,
            verdict=('留证-paddle 失读退化帧(单源 CV 行动,无差值语义;'
                     '不计入双源分歧持续显影,检测链恢复后自消失;'
                     '若 CV 占用源同时坏,由真分歧分键独立显影)'),
            refs=journal_refs({'stream': 'arbitration',
                               'key': f'source={source}|degraded=1'}),
            reader_source=str(source or ''),
            note='paddle 失读退化行(与真分歧分键拆分;证据层 = journal '
                 'obs_event arbitrate 行,field=deployed_count_2src 对账)')
        return
    gap = float(int(cv_n)) - float(int(paddle_n))
    record_defect(
        'deployed', DEFECT_KIND_DEPLOYED_COUNT_2SRC,
        expected=(f'paddle_x={int(paddle_n)}' if paddle_n is not None
                  else 'paddle_x=失读'),
        observed=f'cv_occupied={int(cv_n)}',
        gap=gap, gap_large=abs(gap) > 1,
        auto_resolved=True,
        verdict=('留证-deployed 计数双源分歧,已按取低值仲裁'
                 '(规则与依据见 cw_observation.arbitrate_deployed_count;'
                 '本键计数=不一致率,同局 ≥3 次排期修 CV 占用源)'),
        refs=journal_refs({'stream': 'arbitration',
                           'key': f'source={source}'}),
        reader_source=str(source or ''),
        note='deployed 计数双源仲裁分键(裁决事件层;证据层 = journal '
             'obs_event arbitrate 行,field=deployed_count_2src 对账)')
    # 计数器生命周期:新局首条且历史局积压超限 ⇒ 清空只保当前局
    #(常驻进程跨局累积无界;历史局计数无跨局消费面,清零无损)。
    if (rid not in _DEPLOYED_2SRC_RUN_COUNTS
            and len(_DEPLOYED_2SRC_RUN_COUNTS)
            >= _DEPLOYED_2SRC_RUN_COUNTS_MAX):
        _DEPLOYED_2SRC_RUN_COUNTS.clear()
    _DEPLOYED_2SRC_RUN_COUNTS[rid] = _DEPLOYED_2SRC_RUN_COUNTS.get(rid, 0) + 1
    if _DEPLOYED_2SRC_RUN_COUNTS[rid] == DEPLOYED_COUNT_2SRC_SUSTAINED_N:
        log.warning(
            '[cw!][obs] deployed 计数双源真分歧本局已 %d 次(逐次已仲裁取低值,'
            '决策未消费污染源)→ 持续显影升 L1:归因双向——CV 占用源结构性'
            '漂移 或 paddle X 检测链退化致对拍失真', DEPLOYED_COUNT_2SRC_SUSTAINED_N)
        record_defect(
            'deployed', DEFECT_KIND_DEPLOYED_COUNT_2SRC_SUSTAINED,
            expected=f'本局真分歧行数 <{DEPLOYED_COUNT_2SRC_SUSTAINED_N}',
            observed=(f'本局真分歧行数 ={_DEPLOYED_2SRC_RUN_COUNTS[rid]}'
                      f'(最近一次 paddle_x={paddle_n} cv_occupied={cv_n})'),
            gap=gap, gap_large=abs(gap) > 1,
            severity=SEVERITY_L1_ALERT,
            verdict=('持续显影-同局真分歧达阈值(逐次行恒 L2 因仲裁已消化'
                     '决策面,但持续分歧要响铃;归因双向,先查本局 '
                     'deployed_count_2src_degraded 退化行占比——高=对拍失真'
                     '归 paddle 检测链,低=CV 占用源结构性漂移;处置=哨兵帧'
                     '对拍 CV 占用实数与 paddle X,修 CV 阈值/遮挡误漏或'
                     '后排布局档)'),
            refs=[{'stream': 'arbitration',
                   'key': f'sustained_n={DEPLOYED_COUNT_2SRC_SUSTAINED_N}'}],
            reader_source=str(source or ''),
            note='分歧持续显影升级行(每局至多一条;逐次明细见逐次行)')



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
    # cw_screen_prep 执行失败安灯钩子)。只认显式判级 == L0_andon(零误停
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
# 的分层边界,与 cw_screen_prep 执行失败安灯「判定与执行同文件」不同)=====

#: L0 安灯哨兵 flag 相对路径(锚仓根;.debug/ 不入 git;与 exec_fail
#: 钩子 flag 分文件,值班者按文件名即知是观测面停线还是执行失败停线)。
_L0_ANDON_FLAG_RELPATH: str = '.debug/temp/currency_war/l0_andon_hook.flag'



def install_exit_hooks() -> None:
    """分包期 4 出口钩子注入(生产武装点=CurrencyWarApp.__init__,与
    ``set_l0_andon_handler`` 同点;幂等):把本模块真实现写进
    kernel/cw_telemetry_exit 的钩子槽,使 kernel/obs/decision 三桶的
    telemetry 上行出口(落账/安灯/run_id 归属键)零直依本模块。

    删除波 1:exogenous/exec_events 实现槽随旧流写入端退役移除——
    install_exit_hooks 不再注入两流实现(kernel 侧访问器一为 no-op 桩、
    一已删除)。缺陷台账/obs 旁路/安灯/run_id 四槽照常。"""
    from sr_od.application.currency_war.kernel import cw_telemetry_exit

    cw_telemetry_exit.install_exit_hooks(
        run_id_provider=current_run_id,
        record_defect=record_defect,
        bypass_obs_conflict_to_defect=bypass_obs_conflict_to_defect,
        l0_andon_flag_path=l0_andon_flag_path,
        write_l0_andon_flag=write_l0_andon_flag)



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
    """写安灯哨兵 flag(纯 IO 可单测;三要素规范同 cw_screen_prep 执行失败
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
        f'缺陷台账:telemetry/live/defect_ledger.jsonl 同 run_id 行(refs={refs_txt})\n'
        f'截图:{shots_txt}\n'
        '处理步骤:1. 看现场截图确认画面与缺陷面;2. 按 refs 下钻证据行\n'
        '  (journal (run_id,v) 锚 = obs_event/写入行;历史行为冻结档案只读\n'
        '  考古)判 reader 误读还是观测真漂移;\n'
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
        # refs = journal (run_id,v) 锚(W7 refs 迁移,retirement.md §2
        # defect_ledger 行):锚恰为上方汇点刚写入的 obs_event 证据行版本
        #(obs_conflict 先 note_obs_event 后旁路,同栈无间写);旧
        # obs_conflicts 流指针已随删除波 1 退役,新行按其下钻扑空。
        refs=journal_refs(),
        reader_source=str(rec.get('source') or ''),
        gap_large=gap_large,
        auto_resolved=field in AUTO_RESOLVED_OBS_FIELDS,
        confidence=conf,
        note='旁路自 obs_conflict 汇点(证据行 = journal obs_event '
             'arbitrate,refs 锚即该行;历史冻结档案只读考古)')



# `w512_obs_surfaces/` exec 失败旁路(bypass_exec_event_to_defect)已随
# exec_events 流写入端退役(删除波 1):发射语义下动作 op 无成败知识
# (receipts 零成败字段 + 观察侧 reconcile 对比),执行失败证据面随之
# 消失;缺陷台账保留面的现役供给 = obs 冲突旁路 + 各显式判级点。
# _exec_family_surface 映射随之删除(唯一消费方 = 该旁路)。




# ===== 布局档分键(15 号稿批 C;T-6 互不混流)=====
# 字符串单一源 = kernel.cw_telemetry_exit(obs 布局面经出口上行,双侧同引)。


