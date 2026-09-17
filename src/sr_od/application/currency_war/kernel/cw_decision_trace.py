"""策略侧决策行文件发射面(两文件模型②;决策行文件落地批)。

**正本与定谳依据**(持久索引):
- 行 schema 正本 =
  ``docs/develop/sr_od/application/currency_war/design/决策行文件schema设计.md``
  (§2 行五段结构与发射契约 / §4 字段语义 / §5 写入时机与生命周期 /
  §10 锁面清单;下文 §N 即该文档节号);
- 定谳记录 =
  ``.debug/progress/2026-09-11-cw-clear-run/定谳记录-c1c8.md``
  (C1 过渡态定性 / C2 文件名目录位 / C3 派生列不发射 / C4 首批发射面 /
  C7 独立版本常量 / C8 候裁 6 联动;挂波定谳 C6 = W6 后)。

**发射面语义**(§5.1/§5.4):决策行 = 一个决策帧(入口观察→策略求值→
动作计划产出)一行,JSONL 追加写,落 ``strategy/decision_trace.jsonl``
(定谳 C2,镜像 ``state/journal.jsonl`` 布局;禁复用 decisions.jsonl——
历史档案与 sim 产物以该名为键,双载体同名 = 读面歧义)。写口在**决策帧
收口**时点被调用(策略求值完成、动作计划产出、执行未开始):求值过程
自身产生的计数写点落入本行窗口(该决策自身行为的归因);跨窗的执行侧
写点(部署 held、仲裁、耗尽臂等)归入其发生后的下一行窗口。发射频率 =
调用频率,一收口一行,无内部节流(量级论证 §5.3:~40-80 行/局)。

**窗口与锚**(§5.1):写口持有锚(上一行收口时点的容器内容快照,按局段
重置,与容器同界);本行收口时点现读策略计数容器 → 与锚逐键求差 → 发射 →
更新锚。行首窗口起点 = 局段起点(容器冷建,空 dict)。消失键按「缺席 = 0」
入账(容器重建形态),保证望远镜恒等式(§5.2)在前缀和重建口径下精确成立。

**数学契约与降格主张**(§5.2,定谳 C1):窗口增量满足望远镜恒等式——
对局段内收口时点序 t_1 < … < t_n,任意前缀 m 的行增量逐键求和 = 第 m 行
收口时点的容器内容(对差非零键精确成立,含清零/覆写键),该恒等式是
窗口增量载体的机器验证面(锁 sr-od-test 行为锁)。**残差归属按降格主张
陈述,不称数学全称证明**:「行 = 决策帧」是消费面语义不变量;末决策行
之后、局终收口之前窗口 (t_n, T] 的容器写点无行归属,在该不变量下由局终
聚合(``MatchFinal.cw4_counters``)唯一承载——尾行行型会破坏「行都是
决策帧」不变量且代价大于收益(局终聚合已是现成权威面)。单调键的终局
对账为不等式:Σ行增量 ≤ 局终聚合同键值(§5.2/锁 L3)。

**发射契约与首批发射面**(§2.2/§2.4,定谳 C4):本文件的发射契约单独于
类演进契约声明(telemetry/schema.py ``DecisionTrace`` 类保持只追加,本
模块不 import 之——桶依赖矩阵禁 kernel→telemetry,行键名以常量登记单一
源)。**首批发射面只含 cw4_counters**(§2.4);sess_* 策略披露族 14 字段
(:data:`DISCLOSURE_FAMILY_CLOSED_LIST`,成员封闭清单)按消费需求逐批
接线,未接线期不入行;退役面字段(§2.3)与派生列 refresh_trigger
(定谳 C3,判读侧离线自同行 actions 派生)恒不入行。行内容只来自容器
现读与调用方传入,禁读 journal / 决策行文件自身(§8-4,ADR-0577 写侧
延伸)。

**缺省关与装配**(注入槽模式,同 ``cw_state_journal``/``set_defect_sink``
先例):sink 缺席 = 行不落盘,写口差分与锚推进照常(记录被动,不改决策
路径语义);生产装配单点调 :func:`install_decision_trace`(run 归属复用
进程级供给槽,前置 = ``cw_state_journal.install_state_telemetry`` 已装;
槽缺席 = 行全视为局外拒写,诚实缺失)。局外(run_id 空)拒写假行(§3.2.3
同纪律)。文件寿命与 journal 按 run 段同批淘汰(§5.4,retirement.md §6-5;
两文件禁单件淘汰):淘汰判定单一源 = journal 段清理,本文件协同淘汰
journal 已淘汰的同一 run_id 集。

**确认联动(定谳 C8)**:四查消费面等价(§6)以「局终聚合渲染读链零改动」
为前提——§6① 判读恒等的读链存活挂 r5-migration-plan §7 候裁 6(考古
工具面去留)裁量;本批为纯新增发射面,零改任何既有读链。T2(判读面帧
归因视图)非义务,不落本批,归宿维持挂候裁 6 同批。

**钉面标记**:行面无钉面标记字段;历史档案如出现 ``pin_scope='board_state'``
标记行,其判读语义与字段退役依据见 schema 正本 §8-2「历史档案字段说明」。
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import weakref
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    current_run_id_safe,
    game_state_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_observe import LIVE_DIR
from sr_od.application.currency_war.kernel.cw_state_journal import (
    DEFAULT_FLUSH_EVERY,
    StateJournal,
    enforce_journal_retention,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)

# ============================================================ 常量(定谳落点)

#: 行头 schema 版本(定谳 C7):**新文件自带独立版本常量**,初值 1 独立
#: 谱系,命名对齐 ``*_SCHEMA_VERSION`` 仓内先例(kernel/cw_game_state
#: ``GAME_STATE_SCHEMA_VERSION``)。
#: 禁动 telemetry/schema.py 模块级共用 ``SCHEMA_VERSION``——该常量被
#: DecisionTrace/OutcomeRecord 等共用,模块级抬号会把未退役旧流行版本号
#: 连带抬升(C7 定谳排除项)。
DECISION_TRACE_SCHEMA_VERSION: int = 1

#: 文件目录位与名(定谳 C2):镜像 ``state/journal.jsonl`` 布局,名取自
#: schema 类名 DecisionTrace(持久索引);**禁复用 decisions.jsonl**
#: (历史档案与 sim 产物以该名为键,双载体同名 = 读面歧义)。
DECISION_TRACE_DIR_NAME: str = 'strategy'
DECISION_TRACE_FILE_NAME: str = 'decision_trace.jsonl'

#: 段淘汰 manifest 文件名(决策行文件同目录;逐段一行 archived_out 显影,
#: 语义对齐 journal 的 ``journal.retirement.jsonl``)。
DECISION_TRACE_RETIREMENT_MANIFEST_NAME: str = 'decision_trace.retirement.jsonl'

#: 首批发射面(定谳 C4/§2.4):**只含 cw4_counters**。扩面走逐批接线
#: (消费方出现时随批扩发射契约),本常量 = 发射契约的机器面单一源。
EMITTED_FIELDS: tuple[str, ...] = ('cw4_counters',)

#: sess_* 策略披露族成员封闭清单(定谳 C4/§2.4;13 个 sess_ 前缀透传字段
#: + 1 个非前缀披露字段 p1_downgrade_active,共 14;sess_p1_pair 不属本族
#: ——归行结构「决策记录」段)。**首批发射不含**,按消费需求逐批接线;
#: 成员增删 = 改本清单 + 设计终版 §2.4 同步(封闭清单禁散落第二登记)。
DISCLOSURE_FAMILY_CLOSED_LIST: tuple[str, ...] = (
    # 行结构 §2.1 已具名 5 个
    'sess_framework',
    'sess_dual_track',
    'sess_drought',
    'sess_commit_scores',
    'sess_active_env',
    # 对抗审 F-2③ 点名补齐 8 个
    'sess_blood_budget_rejects',
    'sess_blood_budget_refresh_rejects',
    'sess_terminal_release',
    'sess_reserve_cap',
    'sess_reserve_overflow',
    'sess_release_budget',
    'sess_release_reason',
    'sess_release_spent',
    # 非 sess_ 前缀披露 1 个
    'p1_downgrade_active',
)

#: 退役面字段(§2.3 逐项判据):统一 state 可算/已退役/死字段,不入新
#: 文件行(瘦身判据「凡统一 state 可算的内容不存」的适用面)。
RETIRED_FIELDS_NOT_EMITTED: tuple[str, ...] = (
    'state',            # 全量 state 快照(容器期 = serialize_state 产物,full_state_snapshot
                        # 形状;2026-09-13 状态收敛批前历史行 = 旧帧序列化形状);
                        # journal 行行自足,state_ref 钉行即含
    'hp',               # 统一 state 经济域可算(钉行现值)
    'gold',             # 同上;gold 轨迹已改流水派生
    'hp_readable',      # 读值质量维 = journal 渠道签名与来源注记职责
    'gold_readable',    # 同上
    'level_readable',   # 同上
    'active_strategies',  # 统一 state 局级事实域字段
    'form_score',       # 已退役字段(schema 自申报历史数据只读,替代披露 = b_t)
    'phase',            # 死字段(v2 相位机退役无写端;与容器 v3_phase 非同一载体)
)

#: 派生列不入行(定谳 C3):refresh_trigger 由判读侧离线自同行 actions
#: 按现役口径派生(recorder 同规则,'' 归 other 桶),行为等价零新语义。
#: 注意与披露族不同:本字段**恒不入行**(非「逐批接线」),接线通道不存在。
DERIVED_COLUMN_NOT_EMITTED: tuple[str, ...] = ('refresh_trigger',)

#: 行键发射序(§2.1 五段组织的行内平铺键序:行头 → 钉 → 策略记忆首批发射面)。
#: JSON 行键序随插入序,消费面按名访问(键序敏感读者不存在,§2.3 字段序
#: 脚注同判据);本元组 = 行形状锁(§10-L5)的断言底稿。
ROW_KEY_ORDER: tuple[str, ...] = (
    'schema_version', 'ts', 'run_id', 'difficulty', 'plane', 'round_num',
    'strategy_id', 'ev_arm',            # 行头(身份与 join key)
    'state_ref',                        # 钉(state_ref 版本钉)
    *EMITTED_FIELDS,                    # 策略记忆(首批发射面)
)


# ============================================================ 注入槽(缺省关)

#: 决策行外送钩子(进程内单槽;缺省 None = 无落盘实例——写口差分与锚
#: 推进照常,仅行不外送,记录被动)。槽契约:接收一行完整行 dict,
#: 自担序列化/缓冲/落盘(生产 = :class:`StateJournal.append`)。
_DECISION_TRACE_SINK: Callable[[dict], None] | None = None

#: 进程内现役落盘实例(reset 时收口 flush;缺省 None)。
_ACTIVE_DECISION_TRACE: StateJournal | None = None


def set_decision_trace_sink(fn: Callable[[dict], None] | None) -> None:
    """接通/复位决策行外送钩子(None = 关,缺省态;注入槽模式)。"""
    global _DECISION_TRACE_SINK
    _DECISION_TRACE_SINK = fn


def decision_trace_instance() -> StateJournal | None:
    """现役决策行落盘实例(无实例 = None;测试/诊断读口)。"""
    return _ACTIVE_DECISION_TRACE


# ============================================================ 锚(窗口差分状态)

#: 锚旁表(session 旁表模式,同 ``game_state_of`` 弱引用表 + 裸对象属性 +
#: id 表三级兜底先例):键 = 局身份 session,新 session = 新局段 = 锚冷建
#: (§5.1 局段边界:锚、行序、前缀和全部以局段为界;恢复局跨段 = 多行多段
#: 各自自洽,容器每局冷建天然保证,无跨段账务耦合)。
_ANCHOR_BY_SESSION: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_ANCHOR_ATTR: str = '_cw_decision_trace_anchor'
_ANCHOR_BY_ID: dict[int, dict[str, int]] = {}


def _anchor_get(session: object) -> dict[str, int] | None:
    """取锚(三级兜底读;无锚 = None = 首行窗口起点为局段起点)。"""
    try:
        return _ANCHOR_BY_SESSION.get(session)
    except TypeError:   # 不可弱引用对象(测试桩)
        attr = getattr(session, _ANCHOR_ATTR, None)
        if attr is not None:
            return attr
        return _ANCHOR_BY_ID.get(id(session))


def _anchor_set(session: object, anchor: dict[str, int]) -> None:
    """存锚(与 :func:`_anchor_get` 同三级兜底;值 = 浅拷贝快照)。"""
    try:
        _ANCHOR_BY_SESSION[session] = anchor
        return
    except TypeError:
        pass
    try:
        setattr(session, _ANCHOR_ATTR, anchor)
    except (AttributeError, TypeError):
        _ANCHOR_BY_ID[id(session)] = anchor


def reset_decision_trace_anchor(session: object) -> None:
    """复位某局段的锚(下一行窗口起点回到局段起点;测试与残局修复用)。

    生产路径无需调用:新 session = 新局段 = 新锚;本函数仅服务于测试
    隔离与「同 session 复用重跑」的诊断场景。"""
    with contextlib.suppress(TypeError):
        _ANCHOR_BY_SESSION.pop(session, None)
    if _ANCHOR_ATTR in vars(session):
        with contextlib.suppress(AttributeError, TypeError):
            delattr(session, _ANCHOR_ATTR)
    _ANCHOR_BY_ID.pop(id(session), None)


def reset_decision_trace_all_anchors() -> None:
    """清空锚旁表(测试隔离用;进程级全局,防跨用例残留)。"""
    _ANCHOR_BY_SESSION.clear()
    _ANCHOR_BY_ID.clear()


def _window_diff(counters: dict, anchor: dict) -> dict[str, int]:
    """窗口差分(§5.1):键 → 本行收口窗口内的内容变化量(带符号)。

    键域 = 锚与现读的并集:消失键按「缺席 = 0」入账(容器重建形态),
    保证望远镜恒等式在前缀和重建口径下精确成立;零差键省略(§4「零差
    省略,未触键缺席」)。"""
    out: dict[str, int] = {}
    for k in set(counters) | set(anchor):
        d = counters.get(k, 0) - anchor.get(k, 0)
        if d:
            out[k] = d
    return out


# ============================================================ 写口(决策帧收口)

def record_decision_frame(session: object, *,
                          state_ref_version: int | None = None,
                          strategy_id: str = '',
                          ev_arm: str = '') -> dict | None:
    """决策帧收口 → 决策行发射(两文件模型②写口;§5.1)。

    调用时点 = **决策帧收口**:策略求值完成、动作计划产出、执行未开始。
    求值过程自身产生的计数写点因此落入本行窗口;收口之后的执行侧写点归
    下一行窗口。一收口一行,无内部节流。

    - ``session`` = 局身份(:class:`StrategySession`);锚旁表按键引用,
      新 session = 新局段 = 首行窗口起点为局段起点;
    - ``state_ref_version`` = 钉版本(调用方在「决策读取完成时点」捕获后
      显式传入;R4 语义沿用:显式 int 直用零回读,观察完成与落盘之间有
      交错写入的调用点必须显式传参防钉值漂移);None 缺省 = 入口现读
      ``game_state_of(session).current_version()``(读口读不写、不占
      版本);读取失败/无 GameState = state_ref 诚实缺省 ''(不猜);
    - ``strategy_id``/``ev_arm`` = 行头身份键,调用方传入(策略状态对象
      对 kernel 黑盒,无具名字段可现读;'' = 未采诚实缺省)。

    返回本行 dict(局外拒写/无 run 归属 = None);行外送 best-effort:
    sink 异常不毒化决策链(记录层故障不阻塞业务)。

    cw4_counters 三态(§4,锁 L4):None = 无策略载体(无 match 注册/
    第三方策略未装配);{} = 本窗口零变更(显式发射,与 None 可辨);
    非空 dict = 本窗口有变更(只出现差非零键,值全 int 带符号)。"""
    run_id = current_run_id_safe()
    if not run_id:
        return None   # 局外写入拒绝(§3.2.3):不写假行,诚实缺失
    st = strategy_state_of(session) if session is not None else None
    counters = getattr(st, 'cw4_counters', None)
    cw4_payload: dict[str, int] | None
    if counters is None:
        # 无策略载体(§4 None 语义):发射 None,不猜;锚不动(无容器
        # 无窗口账务)。
        cw4_payload = None
    else:
        anchor = _anchor_get(session)
        if anchor is None:
            anchor = {}   # 局段首行:窗口起点 = 局段起点(C(t_0) = ∅)
        cw4_payload = _window_diff(counters, anchor)
        _anchor_set(session, dict(counters))   # 浅拷贝快照,后写不串
    # 钉(§2.1 state_ref = '{run_id}#{v}')
    gs = game_state_of(session)   # 单例旁表现读;行头读口统一走四读口
    pin_v: int | None
    if state_ref_version is not None:
        pin_v = int(state_ref_version)
    else:
        try:
            pin_v = int(gs.current_version())
        except Exception:   # noqa: BLE001  钉读取失败 = 诚实缺省,不猜
            pin_v = None
    row: dict[str, Any] = {
        'schema_version': DECISION_TRACE_SCHEMA_VERSION,
        'ts': datetime.now().isoformat(timespec='seconds'),
        'run_id': run_id,
        'difficulty': str((game_state_of(session).selected_difficulty.value
                           if session is not None else '') or ''),
        'plane': plane_of(gs),
        'round_num': round_num_of(gs),
        'strategy_id': str(strategy_id or ''),
        'ev_arm': str(ev_arm or ''),
        'state_ref': f'{run_id}#{pin_v}' if pin_v is not None else '',
        'cw4_counters': cw4_payload,
    }
    sink = _DECISION_TRACE_SINK
    if sink is not None:
        try:
            sink(row)
        except Exception as e:  # noqa: BLE001  记录层 best-effort
            log.debug(f'[cw-dt] decision trace row skip: {e}')
    return row


# ============================================================ 装配与寿命契约

def _retire_segments(path: Path, retired_ids: list[str], *,
                     now: datetime | None = None) -> dict[str, Any]:
    """决策行文件按 run 段协同淘汰(§5.4 寿命契约装配端)。

    **淘汰判定单一源 = journal 段清理**(:func:`enforce_journal_retention`);
    本函数只把 journal 已判淘汰的**同一 run_id 集**从决策行文件同步摘除
    ——两文件禁单件淘汰(retirement.md §6-5):禁「journal 段已清而决策
    行段残留」的半淘汰态。只摘 run_id 精确命中行;坏行/无 run_id 行原样
    保留(宁留不误删,清理面不做判定)。逐段写 manifest 一行
    ``archived_out`` 显影(判读辨「清理 vs 丢数据」);原子重写
    (临时文件 + ``os.replace``,中断读者不读半截)。

    返回 ``{'retired': [run_id...], 'rows_dropped': n}``。"""
    path = Path(path)
    summary: dict[str, Any] = {'retired': [], 'rows_dropped': 0}
    if not retired_ids or not path.exists():
        return summary
    retired = set(retired_ids)
    keep_lines: list[str] = []
    seg_rows: dict[str, list[dict]] = {}
    dropped = 0
    with path.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                keep_lines.append(stripped)   # 坏行原样保留
                continue
            rid = str(row.get('run_id') or '') if isinstance(row, dict) else ''
            if rid in retired:
                dropped += 1
                seg_rows.setdefault(rid, []).append(row)
                continue
            keep_lines.append(json.dumps(row, ensure_ascii=False))
    if not dropped:
        return summary
    # manifest 显影(逐段一行;追加,历次淘汰记录累积;失败 = 放弃本轮
    # 清理——不可发生「删了没记账」,manifest 是段存续的判别面)
    def _ts_of(rows: list[dict]) -> list[str]:
        return sorted(str(r.get('ts') or '') for r in rows)

    manifest_path = path.parent / DECISION_TRACE_RETIREMENT_MANIFEST_NAME
    retired_at = (now or datetime.now()).isoformat(timespec='seconds')
    try:
        with manifest_path.open('a', encoding='utf-8') as mf:
            for rid, rows in seg_rows.items():
                tss = _ts_of(rows)
                mf.write(json.dumps({
                    'run_id': rid, 'archived_out': True,
                    'rows': len(rows),
                    'first_ts': tss[0] if tss else '',
                    'last_ts': tss[-1] if tss else '',
                    'retired_at': retired_at,
                }, ensure_ascii=False) + '\n')
    except Exception as e:  # noqa: BLE001  显影失败 = 本轮不清理
        log.warning('[cw!][decision-trace] 淘汰 manifest 写入失败(本轮不清理): %s', e)
        return summary
    # 原子重写(保留行 = 未淘汰段行 + 原样保留的坏行)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                        suffix='.jsonl.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for ln in keep_lines:
                f.write(ln + '\n')
        os.replace(tmp_name, path)
    except Exception as e:  # noqa: BLE001  重写失败不阻塞装配(下一轮重试;
        # manifest 已记账,消费方以文件实况为准,manifest 只增不改)
        log.warning('[cw!][decision-trace] 段清理重写失败(顺延): %s', e)
        return summary
    summary['retired'] = sorted(seg_rows)
    summary['rows_dropped'] = dropped
    return summary


def install_decision_trace(path: Path | str | None = None, *,
                           flush_every: int = DEFAULT_FLUSH_EVERY,
                           journal_path: Path | str | None = None,
                           ) -> StateJournal:
    """装配决策行落盘(幂等:重入先复位再装,防双槽叠加)。

    - path = 决策行文件路径;None = 生产缺省
      ``<live 根>/strategy/decision_trace.jsonl``(定谳 C2,镜像
      ``state/journal.jsonl`` 布局);
    - flush_every = 批量落盘阈值(行数;崩溃丢失窗上界,语义同 journal);
    - journal_path = 同文件模型①的 journal 路径(给定则先跑 journal 段
      清理,再把其淘汰的同一 run_id 集从本文件协同淘汰——两文件禁单件
      淘汰,§5.4);None = 跳过寿命联动(纯测试装配形态);
    - 前置 = 进程 run 归属供给槽已装(:func:`cw_state_journal.
      install_state_telemetry` 生产装配段已注);槽缺席 = 行全视为局外
      拒写(诚实缺失,不写假行)。

    返回落盘实例(sink 已接 :func:`set_decision_trace_sink`)。"""
    global _ACTIVE_DECISION_TRACE
    reset_decision_trace()
    if path is None:
        path = LIVE_DIR / DECISION_TRACE_DIR_NAME / DECISION_TRACE_FILE_NAME
    dt = StateJournal(path, flush_every=flush_every)
    if journal_path is not None:
        # 寿命契约联动(journal 判定 → 本文件协同淘汰):装配时点单进程
        # 写端未启动,零并发窗;联动面失败不阻塞装配主路径。
        try:
            summary = enforce_journal_retention(journal_path)
        except Exception as e:  # noqa: BLE001  journal 清理面故障不波及装配
            log.warning('[cw!][decision-trace] journal 段清理失败(不阻塞装配): %s', e)
            summary = {}
        retired_ids = list(summary.get('retired') or [])
        if retired_ids:
            try:
                _retire_segments(Path(path), retired_ids)
            except Exception as e:  # noqa: BLE001  协同淘汰失败不阻塞装配
                log.warning('[cw!][decision-trace] 协同段淘汰失败(顺延): %s', e)
    _ACTIVE_DECISION_TRACE = dt
    set_decision_trace_sink(dt.append)
    log.info('[cw][decision-trace] 决策行落盘装配:path=%s flush_every=%d',
             dt.path, dt._flush_every)
    return dt


def reset_decision_trace() -> None:
    """复位决策行落盘(收口 flush + 摘 sink;测试 teardown 与重装前调)。

    收口成单点理由同 :func:`cw_state_journal.reset_state_telemetry`:
    槽 = 进程级全局,残留会把后续局的决策行带进旧句柄。"""
    global _ACTIVE_DECISION_TRACE
    dt = _ACTIVE_DECISION_TRACE
    if dt is not None:
        dt.close()
        _ACTIVE_DECISION_TRACE = None
    set_decision_trace_sink(None)
