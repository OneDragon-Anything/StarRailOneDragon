"""货币战争对局档案 → markdown 深度复盘渲染器(op 粒度两遍式)。

## 用途

json 对局档案不便逐条阅读;本工具把单局档案渲染成一份 markdown 复盘稿。
渲染基本单元 = **一次外层循环画面 op 调用**(协议 = ``sr-od-currency-war``
skill ``references/match-review.md``;架构依据 = ``docs/develop/sr_od/application/currency_war/
flow/screen_op.md`` §1「一次画面 op 调用 = 入口观察 + 逐动作决策循环」、
``flow/outer_loop.md`` §2.2 分支序表、``flow/prep_visit.md`` §1 逻辑态直写规则):
逐节点(P×R×)分组,组内按时间戳输出 op 记录,每个 op 单独一条,尾部留三个
判定空槽,供审阅者(人/审查智能体)按「玩法文档 + 在册用户裁定」判定尺填写。

## 两遍式渲染

- **第一遍(op 序列重建)**:按 op 边界规则从档案流行重建 op 序列——
  decisions 帧动作切分(OpenShop…CloseShop 段 = 商店访问 op,其余备战动作
  按逻辑态终结规则切备战 op)、快照边界定位商店 op 起点、exogenous 行定位
  遭遇/简报等 op。op 属性 = 序号 + 分支号 + 处理类名 + 入口时间戳。
- **第二遍(分组渲染)**:节点(P×R×)分组、组内按时间戳输出 op 记录;
  每 op 最小渲染面 = 入口观察 + 逐动作与拒因 + 终结标记;商店 op 按快照
  分段;开店步无决策行的访问按快照补起点并标注「开店通道未记录」防误读。

## op 边界重建规则(与 match-review.md 阶段 2 一致,渲染器是其确定性实现)

- decisions 帧(单动作决策循环,一帧 ≈ 一动作)按词表分类:
  - ``phase`` 以 ``supply`` 开头 → 补给帧;分流帧(detour)与拾取帧(pick)
    合并为**一个补给 op**,节点归属取分流帧(拾取帧轮号有跨轮漂移先例,
    见 084421 复盘完整性审计 S5,档案 = matches/reviews/g_20260907_084421.md);
  - 动作含商店词表(BuyCard/LevelUpShop/RefreshShop/OpenShop)或行级
    ``phase`` 非空(零买入段行 acts=[] 只有 phase 可辨)→ 商店帧;
    连续商店帧合并为**一个商店访问 op**(刷新产生的多波段行同属一次访问);
  - 其余 = 备战帧;备战帧按逻辑态终结规则切 op——帧动作含
    RunDeploy/RunEquip/LevelUp/DeployMove/SellDeployed(prep_visit.md §1
    逻辑态未建模面)或 StartBattle(出战,§3 唯一完成态)→ 该帧后切分;
    无终结动作收尾 = 访问交回外循环重识别(如下一调度是商店)。
- 战斗窗/结算 = 每个 outcomes 行(合成补给行除外)一个 ``CwScreenBattleWait``
  一体 op;合成补给行(source=synthetic_supply)挂靠最近的补给 op。
- 遭遇选择 = exogenous ``event_choice`` 行 → ``CwScreenEncounter`` op;投资
  策略选卡 = invest_cards 切片按 (ts, run_id) 分组 → ``CwScreenInvestStrategy``
  op;两者无 decisions 行,节点归属 = 「下一个结算收口行」规则(节点窗口 =
  上一次结算到本次结算之间)。BOSS 简报(exogenous ``briefing``)与投资环境
  (帧 state.active_env,选项面未采集)归开局段;对局收口(endgame)归收口段。
- 无决策行的纯路由迭代(弹窗关闭类,outer_loop.md §2.2 浮层族)档案零痕迹,
  不逐条成节;CloseShop 终结结构性不入行(flow/shop_visit.md §2 申报)——
  两者在文末缺口清单声明。

## 用法(主仓根目录)

    uv run python tools/cw/replay_to_md.py --match g_20260907_084421 \
        [--run run_20260907_084421] [--out 复盘.md | --stdout] [--replay-dir <dir>]

- ``--match`` game_id(必填)。档案 = ``telemetry/matches/match_<game_id>.json``
  (matches 根与 live 流根的派生关系同 kernel/cw_observe.match_archive.matches_dir:
  传生产 live 根 → 兄弟 matches 根;传其他目录 → 其下 matches 子目录)。
- ``--run`` 只看某一段(run_id):流行按该 run_id 过滤;帧序号仍按切片全局
  行序(持久索引,便于与判读记录对帧)。档案逐轮表是跨段合并产物,不带
  run_id,故节点分组不过滤;run 不在段列表时打警告并按全段渲染。
- ``--out`` 输出文件;**缺省 = 深评固定落点 ``.debug/currency_war/deep_review/
  <game_id>.md``**(2026-09-07 用户裁定:一局一份,布局单一源);``--stdout``
  改为打印不落盘。
- ``--replay-dir`` 缺省 ``.debug/currency_war/telemetry/live``(与生产
  ``kernel/cw_observe.DEFAULT_REPLAY_DIR`` 同值,此处独立声明:本工具
  刻意零 src 导入,保持纯 stdlib、免 PYTHONPATH 即可运行)。

## 数据源(全部只读)

1. 档案 ``telemetry/matches/match_<game_id>.json``:rounds/loss_nodes/segments/
   resume_reconciliation/cw4_counters/endgame/opening/slices(六条流切片)。
   直读 json,**不做**自动重装配(需要补装配走判读 CLI ``assemble --game``)。
2. 流 ``telemetry/live/*.jsonl``:obs_conflicts 按设计不入档案切片,恒从流
   文件按 run_id 过滤;slices 缺某条流时同法回源读文件。decisions 行字段口径
   见 ``sr_od/application/currency_war/telemetry/schema.py``。

## 渲染结构

- ① 局头:结算/位面进度/策略版本/连续性注记 + 段列表(含 code_commit 与
  notes 列——跨段双码与停局原因在此可见)+ 开局面(含选卡时序)+ 恢复态
  对账。
- ② 逐 op 复盘:开局段(局前,非节点)→ 逐节点组(P×R×,组内 op 按调用
  序;组尾「轮级事实」收强化计数/血购事件/对账注记/观测冲突)→ 收口段
  (含终局面面)。战斗窗 op 渲染结算细字段(进度 fill/伤害拆解等)。
- ③ 全局:轮号连续性 / 金轨迹 / 进度 fill 轨迹 / pivot 链 / 计数分键统计。
- ④ 本次未能渲染的字段(遥测缺口清单)+ 结构性不可见声明。

判定模板槽:有策略选择的 op(备战/商店/补给/遭遇/投资选卡/投资环境)尾部
固定三行引用块,留空待审阅者填;战斗窗/简报/收口等无决策承载 op 只记观察::

    > 决策正确性:
    > 是否符合发展主线:
    > 备选与改进:

## 韧性口径(字段缺省容忍)

所有取值走 .get 型渲染:键缺/值 None 的槽打「(无此数据)」并记入缺口清单;
文档末尾「本次未能渲染的字段」即本次数据的遥测缺口清单。出现的缺口 ≠ 工具
坏,= 该字段没采到/档案版本旧——清单本身就是判读输入。渲染器对畸形行
(非 dict、坏 json)跳过不炸。两类刻意的低噪声例外:.get 容忍不逐字段记缺的
入口观察 state 面(缺整份 state 记一条,防逐字段噪声淹没信号,同盘面表
口径);None 是语义值的槽(fill 未读出/意向 null 等)渲染 '—' 不记缺。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

#: 缺省 live 流根(与生产 kernel/cw_observe.DEFAULT_REPLAY_DIR 同值;
#: 独立声明理由见模块 docstring「零 src 导入」)。matches/深评根同布局
#: 裁定(2026-09-07),派生关系与 match_archive.matches_dir 保持一致。
DEFAULT_REPLAY_DIR = Path('.debug/currency_war/telemetry/live')
DEFAULT_MATCHES_DIR = Path('.debug/currency_war/telemetry/matches')
DEEP_REVIEW_DIR = Path('.debug/currency_war/deep_review')

#: 字段缺槽的统一占位符
MISSING = '(无此数据)'

#: 判定模板槽(顺序与措辞固定,消费方按行匹配)
JUDGMENT_SLOTS: tuple[str, ...] = (
    '> 决策正确性:',
    '> 是否符合发展主线:',
    '> 备选与改进:',
)

#: 判定槽尾注(判定尺口径 = match-review.md 判定尺节:判「算法做得对不对」
#: 的尺子是玩法文档 + 在册用户裁定,禁把算法内部自洽当合格判据——渲染器
#: 只负责把口径写给填槽人)
JUDGMENT_NOTE = (
    '_(判定槽留空待审阅者填写;判定尺 = 玩法文档 + 在册用户裁定,'
    '算法内部自洽不作合格判据 —— 协议见 sr-od-currency-war-dev skill '
    'references/match-review.md 判定尺节)_'
)

#: cw4_counters 里「拒因/拦截」语义计数键的子串(分键统计的分组判据)
_REJECT_KEY_TOKENS: tuple[str, ...] = (
    'reject', 'blocked', 'skip', 'defer', 'held', 'fenced',
    'stale', 'exhausted', 'unavailable', 'abandon', 'truncat',
)

#: 每轮 obs_conflicts 明细表的行数上限(超出只给计数,防刷屏)
_CONFLICT_ROWS_CAP = 15

# ---------------------------------------------------------------------------
# op 词表与边界规则(flow/outer_loop.md §2.2 + flow/prep_visit.md §1/§3)
# ---------------------------------------------------------------------------

#: 商店动作词表(动作含其一 = 商店帧;SellBench 不入表:它在 prep_visit.md §1
#: 属建模逻辑态直写动作,且只出现在商店语境——含 SellBench 的帧必同时含其他商店
#: 动作或带段行 phase)
_SHOP_ACTION_TYPES: frozenset[str] = frozenset(
    {'OpenShop', 'BuyCard', 'LevelUpShop', 'RefreshShop'})

#: 补给帧的行级 phase 前缀(决策帧 phase=supply_detour/supply_pick)
_SUPPLY_PHASE_PREFIX = 'supply'

#: 逻辑态未建模动作(prep_visit.md §1:未建模面 → 本访问终结交回外循环重观察;
#: 出战另列)——帧动作含其一则该帧是备战 op 的终结帧
_PREP_TERM_ACTIONS: frozenset[str] = frozenset(
    {'RunDeploy', 'RunEquip', 'LevelUp', 'DeployMove', 'SellDeployed'})

#: 出战动作(prep_visit.md §3:唯一完成态,交回外循环战斗分支)
_BATTLE_ACTION = 'StartBattle'

#: op 类型 → (分支号, 名称, 处理类名)。分支号 = outer_loop.md §2.2 分支序表;
#: 战斗窗在分支序表中无数字序位(以战斗窗驻留判定接管),如实标注。
OP_LABELS: dict[str, tuple[str, str, str]] = {
    'prep': ('分支1', '备战', 'CwScreenPrep.execute'),
    'shop': ('分支0n', '备战-开商店', 'CwScreenPrep.visit_open_shop'),
    'battle': ('战斗窗', '战斗窗/结算', 'CwScreenBattleWait'),
    'supply': ('分支0e1', '补给', 'CwScreenSupplyNode'),
    'encounter': ('分支0c', '遭遇事件选择', 'CwScreenEncounter'),
    'invest': ('分支0e', '投资策略三选一', 'CwScreenInvestStrategy'),
    'env': ('分支0s', '投资环境', 'CwScreenInvestEnv'),
    'briefing': ('分支0p', 'BOSS 简报', 'CwScreenBossBriefing'),
    'closure': ('分支3c', '回大厅', '局终收口'),
}

#: 有策略选择的 op 类型(判定三槽承载面;match-review.md「判定三槽承载面」:
#: 战斗窗/简报/收口等无决策承载 op 只记观察)
_DECISION_OP_KINDS: frozenset[str] = frozenset(
    {'prep', 'shop', 'supply', 'encounter', 'invest', 'env'})

#: 外生行(exogenous)里作为独立 op 重建的 kind;其余 kind 渲染为挂靠注记
_OP_EXOG_KINDS: frozenset[str] = frozenset({'briefing', 'event_choice'})

#: 合成补给结算行标记(补给是唯一无结算屏节点,outcome 行为快照合成,
#: 「陈旧直到证伪」口径;见 docs/develop/sr_od/application/currency_war/flow/outer_loop.md §2.2
#: 分支 0e1 与 §5 补给合成 outcome 钩子)
_SYNTHETIC_SUPPLY_SOURCE = 'synthetic_supply'

#: 收口终局行标记(T-185:result=stopped/abandoned 局对局收口时点补写的
#: 末轮 outcome 行,写点 = cw_loop._write_terminal_outcome_row)。行内
#: killed=False 是**对局级**「未通关」真值非战斗结算,hp/战斗/节点真值
#: 全不发——显示面禁按战斗胜负语义渲染,专项标注分型(同合成行先例)。
_TERMINAL_CLOSURE_SOURCE = 'terminal_closure'

# ---------------------------------------------------------------------------
# 基础渲染件
# ---------------------------------------------------------------------------


class GapLog:
    """遥测缺口清单:记录「本次渲染中取不到的字段路径」及出现次数。

    field 传点分路径(如 ``rounds[].hp_delta``);同一路径多次缺只累计数。
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def miss(self, field: str) -> None:
        """记录一次字段缺口。"""
        self._counts[field] = self._counts.get(field, 0) + 1

    @property
    def fields(self) -> dict[str, int]:
        """缺口路径 → 出现次数(只读副本)。"""
        return dict(self._counts)

    def summary_lines(self) -> list[str]:
        """缺口清单 markdown 行;零缺口给一句「全部字段渲染成功」。"""
        if not self._counts:
            return ['全部字段渲染成功,无遥测缺口。']
        lines = []
        for field, n in sorted(self._counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f'- `{field}` ×{n}')
        return lines


def _fmt(v: Any) -> str:
    """值 → 单行字符串(bool 中文化,容器压成紧凑 json)。"""
    if isinstance(v, bool):
        return '是' if v else '否'
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return str(v)


def _esc(s: str) -> str:
    """markdown 表格单元格转义(竖线是列分隔符,必须换掉)。"""
    return s.replace('|', '\\|').replace('\n', ' ')


def _short(v: Any, n: int = 48) -> str:
    """值 → 截断字符串(防长 payload 刷屏)。"""
    s = _fmt(v)
    return s if len(s) <= n else s[:n] + '…'


def _dash(v: Any) -> str:
    """None/空串 → '—'(语义空值,不是遥测缺口);其余原样 fmt。"""
    if v is None or v == '':
        return '—'
    return _fmt(v)


def _num_or_dash(v: Any) -> str:
    """整数带千分位(伤害量级可读);None → '—'。"""
    if isinstance(v, int) and not isinstance(v, bool):
        return f'{v:,}'
    if v is None or v == '':
        return '—'
    return _fmt(v)


def _ts_short(ts: Any) -> str:
    """ISO 时间戳 → 时分秒(复盘行文口径;无 T 分隔原样返回)。"""
    s = str(ts or '')
    return s[11:19] if 'T' in s and len(s) >= 19 else s


def _ts_num(ts: Any) -> float:
    """ts → 可比较数值(仅用于同档案内相对排序;不可解析 → 0)。

    为什么不用 float(ts):ISO 串不能直接转;压成 YYYYMMDDHHMMSS 数字后,
    同格式串的数值序 = 字典序,且空串/缺 ts 行稳定落在最前而不是抛错。
    """
    s = str(ts or '').replace('-', '').replace('T', '').replace(':', '')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _cnum(n: int) -> str:
    """op 序号 → 带圈数字(①…⑳;超出用 (21) 形式,防组内超 20 op 炸字符)。"""
    if 1 <= n <= 20:
        return chr(0x2460 + n - 1)
    return f'({n})'


def _cell(d: dict[str, Any] | None, key: str, field: str, gaps: GapLog,
          *, none_ok: bool = False, dash_empty: bool = False) -> str:
    """.get 型取值渲染:键缺/值 None → ``(无此数据)`` 并记缺口。

    - ``none_ok=True``:None 是语义值(如 fill 未读出)→ 渲染 '—'
      不记缺口;键整个缺失仍记(缺键 = 遥测缺,值 None = 采集到但为空)。
    - ``dash_empty=True``:空串渲染 '—'(如 sess_p1_pair=''=未锁,是
      真实状态不是缺口)。
    """
    if not isinstance(d, dict):
        gaps.miss(field)
        return MISSING
    if key not in d:
        gaps.miss(field)
        return MISSING
    v = d[key]
    if v is None:
        if not none_ok:
            gaps.miss(field)
        return '—'
    if dash_empty and v == '':
        return '—'
    return _esc(_fmt(v))


def _sub(d: dict[str, Any] | None, key: str, field: str, gaps: GapLog
         ) -> dict[str, Any] | None:
    """安全取嵌套 dict;整体缺失只记一条缺口(防逐字段重复计数)。"""
    v = (d or {}).get(key)
    if isinstance(v, dict):
        return v
    gaps.miss(field)
    return None


def _trust_mark(d: dict[str, Any] | None, key: str) -> str:
    """可读位标记:字段存在且为 False → 不可信标记;缺失/True → 空串。

    缺失不记缺口(可信位是附带信息,主值缺已在主值槽记过)。
    """
    v = (d or {}).get(key)
    return ' [!不可信]' if v is False else ''


def _kv_table(rows: list[tuple[str, str]]) -> list[str]:
    """两列表格(项 | 值)。"""
    out = ['| 项 | 值 |', '|---|---|']
    out.extend(f'| {k} | {v} |' for k, v in rows)
    return out


def _read_jsonl_tolerant(p: Path) -> list[dict[str, Any]]:
    """容错读 jsonl(坏行/空行跳过;obs_conflicts journal 有截断行先例)。
    文件缺失 → 空列表(调用方负责记缺口)。"""
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _load_stream(archive: dict[str, Any], replay_dir: Path, name: str,
                 gaps: GapLog) -> list[dict[str, Any]]:
    """流行加载:档案切片优先,缺则回源 replay 目录读文件。"""
    slices = archive.get('slices')
    if isinstance(slices, dict) and name in slices:
        rows = slices.get(name)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
        gaps.miss(f'slices.{name}(切片存在但非列表)')
        return []
    rows = _read_jsonl_tolerant(replay_dir / name)
    if not rows:
        gaps.miss(f'流 {name}(档案切片缺、流文件缺或空)')
    return rows


# ---------------------------------------------------------------------------
# 数据准备
# ---------------------------------------------------------------------------


def _segment_ids(archive: dict[str, Any]) -> list[str]:
    """段 run_id 列表(顺档案段序)。"""
    out = []
    for s in archive.get('segments') or []:
        if isinstance(s, dict) and s.get('run_id'):
            out.append(str(s['run_id']))
    return out


def _row_allowed(r: dict[str, Any], allowed: set[str] | None, ts_lo: str,
                 ts_hi: str) -> bool:
    """行级 run 过滤谓词;无 run_id 键的行按局时间窗兜底(obs_conflicts 老行)。

    ``allowed=None`` = 不按 run 过滤(--run 不在段列表的「按全段渲染」,
    或档案无段元数据——此时按段过滤会静默丢掉全部带 run_id 的行)。
    """
    if allowed is None:
        return True
    rid = r.get('run_id')
    if rid:
        return str(rid) in allowed
    return ts_lo <= str(r.get('ts') or '') <= ts_hi


def _run_allow_set(seg_ids: list[str], run_filter: str | None
                   ) -> set[str] | None:
    """run 过滤白名单(--run/段元数据 → allowed 语义,见 _row_allowed)。"""
    if run_filter:
        # run 不在段列表 → 局头已打警告,按全段渲染(参数错不炸)
        return None if run_filter not in seg_ids else {run_filter}
    return set(seg_ids) if seg_ids else None


def _filter_by_run(rows: list[dict[str, Any]], allowed: set[str] | None,
                   ts_lo: str, ts_hi: str) -> list[dict[str, Any]]:
    """按 run_id 过滤(谓词见 _row_allowed;allowed=None 全放行)。"""
    return [r for r in rows if _row_allowed(r, allowed, ts_lo, ts_hi)]


def _round_anchors(rows: list[dict[str, Any]]
                   ) -> list[tuple[str, tuple[int, int]]]:
    """轮归属锚:每个 (plane, round) 的最早行 ts(决策+结算行)。

    冲突行(obs_conflicts)无轮号,归属 = 晚于本轮锚、早于下轮锚。
    """
    earliest: dict[tuple[int, int], str] = {}
    for r in rows:
        try:
            k = (int(r.get('plane') or 1), int(r.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        ts = str(r.get('ts') or '')
        if not ts:
            continue
        if k not in earliest or ts < earliest[k]:
            earliest[k] = ts
    return sorted((ts, k) for k, ts in earliest.items())


def _attr_round(anchors: list[tuple[str, tuple[int, int]]], ts: str
                ) -> tuple[int, int] | None:
    """ts → 所属轮键;早于首锚/无 ts → None(未归轮桶)。"""
    cur: tuple[int, int] | None = None
    for a_ts, k in anchors:
        if ts >= a_ts:
            cur = k
        else:
            break
    return cur


def _group_by_round(rows: list[dict[str, Any]]
                    ) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """行按 (plane, round_num) 分组(坏键行丢弃——渲染侧不猜轮号)。"""
    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in rows:
        try:
            k = (int(r.get('plane') or 0), int(r.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        out.setdefault(k, []).append(r)
    return out


# ---------------------------------------------------------------------------
# 第一遍 · op 序列重建
# ---------------------------------------------------------------------------


def _frame_kind(row: dict[str, Any]) -> str:
    """decisions 帧 → 'supply' | 'shop' | 'prep'。

    判序:补给 phase 最优先(acts=[] 心跳行只有 phase 可辨)→ 商店动作
    词表 → 行级 phase 非空(零买入段行,采集器只落 phase 标记)→ 备战。
    行级 phase 的采集语义:商店波面段行带非空 phase,备战帧 phase 恒空
    ——若未来出现新枚举,该帧落 prep 并以「无动作行」如实渲染,不静默丢弃。
    """
    phase = str(row.get('phase') or '')
    if phase.startswith(_SUPPLY_PHASE_PREFIX):
        return 'supply'
    for a in _frame_actions(row):
        if a.get('__type__') in _SHOP_ACTION_TYPES:
            return 'shop'
    if phase:
        return 'shop'
    return 'prep'


def _frame_actions(row: dict[str, Any]) -> list[dict[str, Any]]:
    """帧动作列表(非 dict 项过滤;畸形帧渲染侧兜底)。"""
    acts = row.get('actions')
    if not isinstance(acts, list):
        return []
    return [a for a in acts if isinstance(a, dict)]


def _frame_key(row: dict[str, Any]) -> tuple[int, int] | None:
    """帧 → (plane, round_num);缺/坏 → None(未归轮)。"""
    try:
        return (int(row.get('plane')), int(row.get('round_num')))
    except (TypeError, ValueError):
        return None


def _mk_op(kind: str, key: tuple[int, int] | None, ts: str, **kw: Any
           ) -> dict[str, Any]:
    """构造 op 记录 dict(字段集固定,防各构造点漂移)。"""
    op: dict[str, Any] = {
        'kind': kind, 'key': key, 'ts': ts, 'ts_end': ts,
        'frames': [],            # [(切片全局行序, 帧行)]
        'run_ids': set(),
        'snapshots': [], 'spend_rows': [], 'annots': [],
        'outcome': None, 'supply_outcome': None, 'invest_rows': [],
        'open_shop_recorded': False, 'segment': 'nodes',
    }
    op.update(kw)
    return op


def _group_frames(frames: list[tuple[int, dict[str, Any]]]
                  ) -> list[dict[str, Any]]:
    """decisions 帧 → 帧级 op(备战/商店/补给)。

    - 连续商店帧合并为一个商店访问 op;OpenShop 行在场 = 开店步已记录。
    - 连续补给帧(detour+pick)合并为一个补给 op,节点取首帧(分流帧;
      拾取帧轮号跨轮漂移先例 = 084421 复盘完整性审计 S5)。
    - 备战帧按终结动作切分(prep_visit.md §1 逻辑态直写规则/§3 出战):帧动作
      含终结词表 → 该帧闭合当前访问,下一个备战帧 = 新一次访问。
    """
    ops: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    cur_kind = ''
    for gidx, row in frames:
        kind = _frame_kind(row)
        ts = str(row.get('ts') or '')
        key = _frame_key(row)
        if kind == 'prep':
            if cur is None or cur_kind != 'prep' or cur.get('closed'):
                cur = _mk_op('prep', key, ts)
                cur_kind = 'prep'
                ops.append(cur)
            cur['frames'].append((gidx, row))
            cur['ts_end'] = ts
            if key is not None and cur['key'] is None:
                cur['key'] = key
            acts = {a.get('__type__') for a in _frame_actions(row)}
            if acts & _PREP_TERM_ACTIONS or _BATTLE_ACTION in acts:
                cur['closed'] = True
        elif kind == 'shop':
            if cur is None or cur_kind != 'shop':
                cur = _mk_op('shop', key, ts)
                cur_kind = 'shop'
                ops.append(cur)
            cur['frames'].append((gidx, row))
            cur['ts_end'] = ts
            if key is not None and cur['key'] is None:
                cur['key'] = key
            if any(a.get('__type__') == 'OpenShop'
                   for a in _frame_actions(row)):
                cur['open_shop_recorded'] = True
        else:  # supply
            if cur is None or cur_kind != 'supply':
                cur = _mk_op('supply', key, ts)
                cur_kind = 'supply'
                ops.append(cur)
            cur['frames'].append((gidx, row))
            cur['ts_end'] = ts
            # 节点归属锁在分流帧(首帧);拾取帧的轮号不采信(审计 S5)
    return ops


def _closure_keys(outcomes: list[dict[str, Any]]
                  ) -> list[tuple[str, tuple[int, int]]]:
    """结算收口锚(非合成行):节点窗口 = 上一次结算到本次结算之间。

    合成补给行不入选:其 round_num 有跨轮 +1 漂移先例(084421 审计 S5),
    拿它当窗口边界会把事件划错节点。
    """
    out = []
    for o in outcomes:
        if str(o.get('source') or '') == _SYNTHETIC_SUPPLY_SOURCE:
            continue
        try:
            k = (int(o.get('plane')), int(o.get('round_num')))
        except (TypeError, ValueError):
            continue
        out.append((str(o.get('ts') or ''), k))
    return sorted(out)


def _next_closure(closures: list[tuple[str, tuple[int, int]]], ts: str
                  ) -> tuple[int, int] | None:
    """ts → 「下一个结算收口」的节点键(遭遇/投资选卡 op 的归属规则)。"""
    for c_ts, k in closures:
        if c_ts >= ts:
            return k
    return None


def build_op_sequence(frames: list[tuple[int, dict[str, Any]]],
                      outcomes: list[dict[str, Any]],
                      exogenous: list[dict[str, Any]],
                      invest_cards: list[dict[str, Any]],
                      shop_snaps: list[dict[str, Any]],
                      spend_rows: list[dict[str, Any]]
                      ) -> list[dict[str, Any]]:
    """第一遍:重建 op 序列(时间戳升序;纯函数,不读文件不记缺口)。

    入参各流行已按 run 过滤;frames 元素 = (切片全局行序, 帧行)——行序是
    持久索引,过滤后仍保原值,便于判读记录对帧。

    输出 op 字段见 _mk_op;另含:
    - 'segment': 'open'(开局段)/ 'nodes' / 'close'(收口段)
    - 'annots': 挂靠到本 op 的外生注记行(kind 非独立 op 的 exogenous 行)
    - 'env': 投资环境 op 的选择结果值;'_unattached': 无法挂靠行虚拟桶
    """
    ops = _group_frames(frames)

    # —— 战斗窗 op:每个非合成 outcome 行一个(合成行挂补给 op) ——
    synthetic: list[dict[str, Any]] = []
    for o in outcomes:
        ts = str(o.get('ts') or '')
        try:
            key = (int(o.get('plane')), int(o.get('round_num')))
        except (TypeError, ValueError):
            key = None
        if str(o.get('source') or '') == _SYNTHETIC_SUPPLY_SOURCE:
            synthetic.append(o)
            continue
        op = _mk_op('battle', key, ts)
        op['outcome'] = o
        op['run_ids'].add(str(o.get('run_id') or ''))
        ops.append(op)

    # —— 遭遇选择 op:exogenous event_choice ——
    closures = _closure_keys(outcomes)
    for e in exogenous:
        kind = str(e.get('kind') or '')
        if kind not in _OP_EXOG_KINDS:
            continue
        ts = str(e.get('ts') or '')
        if kind == 'briefing':
            # 简报恒在局前(对局交互开始前),归开局段
            op = _mk_op('briefing', None, ts, segment='open')
            op['annots'].append(e)
            ops.append(op)
            continue
        op = _mk_op('encounter', _next_closure(closures, ts), ts)
        op['annots'].append(e)
        ops.append(op)

    # —— 投资策略选卡 op:invest_cards 按 (ts, run_id) 分组,一组一次选卡 ——
    invest_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for c in invest_cards:
        invest_groups.setdefault(
            (str(c.get('ts') or ''), str(c.get('run_id') or '')), []).append(c)
    for (_, _), rows in sorted(invest_groups.items(),
                               key=lambda kv: _ts_num(kv[0][0])):
        if not rows:
            continue
        ts = str(rows[0].get('ts') or '')
        op = _mk_op('invest', _next_closure(closures, ts), ts)
        op['invest_rows'] = rows
        op['run_ids'].add(str(rows[0].get('run_id') or ''))
        ops.append(op)

    # —— 投资环境 op(开局段):结果只在帧 state.active_env
    #    (084421 审计 S12:环境三选一的选项面未采集,判定面只有结果值) ——
    env_val = ''
    for _, row in frames:
        st = row.get('state')
        v = st.get('active_env') if isinstance(st, dict) else None
        if isinstance(v, str) and v:
            env_val = v
            break
    if env_val:
        ops.append(_mk_op('env', None, '', segment='open', env=env_val))

    # —— 收口段 op(endgame 汇总 + 终局面面) ——
    ops.append(_mk_op('closure', None, '', segment='close'))

    # —— 全序:开局段置顶、收口段垫底,节点段按入口 ts 升序 ——
    #    (open/close 段排序键恒 0 → 稳定排序保持构造序:简报先于环境)
    seg_rank = {'open': 0, 'nodes': 1, 'close': 2}
    ops.sort(key=lambda o: (seg_rank[o['segment']],
                            _ts_num(o['ts']) if o['segment'] == 'nodes' else 0.0))

    # —— 合成补给行挂靠最近补给 op(邻近阈值按压平时间戳数值近似,
    #    同分钟内精确、跨分钟偏保守;超窗落「未挂靠」桶不丢行) ——
    for o in synthetic:
        ts = _ts_num(o.get('ts'))
        best: dict[str, Any] | None = None
        best_d = float('inf')
        for op in ops:
            if op['kind'] != 'supply':
                continue
            d = abs(_ts_num(op['ts_end']) - ts)
            if d < best_d:
                best, best_d = op, d
        if best is not None and best_d <= 600:
            best['supply_outcome'] = o
        else:
            _mk_unattached(ops, 'synthetic_outcome', o, _frame_key(o))

    # —— 快照/金账行挂靠商店访问:窗口 = 本访问起到下一节点 op 起 ——
    node_ops = [o for o in ops if o['segment'] == 'nodes']
    for i, op in enumerate(node_ops):
        op['_win_hi'] = _ts_num(node_ops[i + 1]['ts']) \
            if i + 1 < len(node_ops) else float('inf')
    shop_ops = [o for o in node_ops if o['kind'] == 'shop']
    for s in shop_snaps:
        ts = _ts_num(s.get('ts'))
        win = [o for o in shop_ops
               if _ts_num(o['ts']) - 5 <= ts < o['_win_hi']]
        if win:
            win[0]['snapshots'].append(s)
            continue
        # 快照先于帧(开店步未记录形态)已由 -5s 提前量覆盖;仍无归属
        # → 挂最近的商店访问(数据不该丢,离得再远也标出来)
        best, best_d = None, float('inf')
        for op in shop_ops:
            d = min(abs(_ts_num(op['ts']) - ts), abs(_ts_num(op['ts_end']) - ts))
            if d < best_d:
                best, best_d = op, d
        if best is not None:
            best['snapshots'].append(s)
        else:
            _mk_unattached(ops, 'snapshot', s, None)
    for sp in spend_rows:
        ts = _ts_num(sp.get('ts'))
        win = [o for o in shop_ops
               if _ts_num(o['ts']) - 5 <= ts < o['_win_hi']]
        if win:
            win[0]['spend_rows'].append(sp)
        else:
            _mk_unattached(ops, 'spend', sp, _frame_key(sp))

    # —— 外生注记行(非独立 op kind)挂靠时间最近节点 op ——
    for e in exogenous:
        if str(e.get('kind') or '') in _OP_EXOG_KINDS:
            continue
        ts = _ts_num(e.get('ts'))
        best, best_d = None, float('inf')
        for op in node_ops:
            d = min(abs(_ts_num(op['ts']) - ts) if op['ts'] else float('inf'),
                    abs(_ts_num(op['ts_end']) - ts))
            if d < best_d:
                best, best_d = op, d
        if best is not None:
            best['annots'].append(e)
        else:
            _mk_unattached(ops, 'exog', e, None)

    # —— 商店访问入口时间取最早证据:开店步未记录时快照先于首帧落地,
    #     入口时间戳应反映「画面 op 真正开始」而非首条决策行(快照边界
    #     定位 op 起点,match-review.md 阶段 2) ——
    for op in shop_ops:
        snap_ts = [str(s.get('ts') or '') for s in op['snapshots']
                   if isinstance(s, dict) and s.get('ts')]
        if snap_ts:
            earliest = min(snap_ts)
            if earliest and (not op['ts'] or earliest < op['ts']):
                op['ts'] = earliest
    # 入口时间前移后重排一次,保持「组内按时间戳输出」不变式
    ops.sort(key=lambda o: (seg_rank[o['segment']],
                            _ts_num(o['ts']) if o['segment'] == 'nodes' else 0.0))

    for op in ops:
        op.pop('_win_hi', None)
        op['run_ids'] = {r for r in op['run_ids'] if r}
        for _, fr in op['frames']:
            rid = str(fr.get('run_id') or '')
            if rid:
                op['run_ids'].add(rid)
    return ops


def _mk_unattached(ops: list[dict[str, Any]], tag: str, row: dict[str, Any],
                   key: tuple[int, int] | None) -> None:
    """无法挂靠的行收集到收口 op 的虚拟桶(渲染为「未挂靠」清单,防静默丢行)。"""
    bucket: dict[str, Any] | None = None
    for op in ops:
        if op['kind'] == 'closure':
            bucket = op
            break
    if bucket is None:
        return
    bucket.setdefault('_unattached', []).append(
        {'tag': tag, 'row': row, 'key': key})


# ---------------------------------------------------------------------------
# 第二遍 · op 渲染
# ---------------------------------------------------------------------------

#: 入口观察已单独渲染的 state 键(其余字段进「state 面」行,保证字段面
#: 全量可见 —— 084421 复盘完整性审计渲染缺 R1:state 快照零消费使环境/
#: 敌难度/升级缺口等复盘关键事实不可见;出处 =
#: .debug/currency_war/deep_review/g_20260907_084421.md §C2)
_STATE_CURATED: frozenset[str] = frozenset({
    'gold', 'gold_readable', 'hp', 'hp_readable', 'hp_trusted',
    'level', 'level_readable', 'xp_progress', 'level_up_cost',
    'node_type', 'enemy_difficulty', 'enemy_difficulty_live',
    'active_env', 'active_strategies', 'deploy_cap',
    'front_max', 'back_max', 'bench_full_flag', 'streak',
    'shop', 'deployed', 'bench',
})


def _v3_brief(v3: Any) -> str:
    """意向状态机摘要(084421 审计渲染缺 R9:锁线证据链 lock_layer/
    lock_plane/lock_round/last_event 必须可见;null = 该帧无状态机记录,
    是采集常态,渲染 '—' 不记缺口)。"""
    if not isinstance(v3, dict):
        return '—'
    bits = [str(v3.get('phase') or '—'), str(v3.get('locked_comp') or '—')]
    lock_bits = []
    if v3.get('lock_layer') is not None:
        lock_bits.append(f"层{_fmt(v3.get('lock_layer'))}")
    if v3.get('lock_plane') is not None or v3.get('lock_round') is not None:
        lock_bits.append(f"P{_fmt(v3.get('lock_plane'))}"
                         f"R{_fmt(v3.get('lock_round'))}")
    if lock_bits:
        bits.append('锁 ' + '/'.join(lock_bits))
    if v3.get('last_event'):
        bits.append(f"last_event={_short(v3.get('last_event'), 24)}")
    if v3.get('forced'):
        bits.append('forced')
    return '(' + ';'.join(bits) + ')'


def _board_line(st: dict[str, Any]) -> str:
    """盘面紧凑行(前排/后排/备战栏人名清单;None 槽 = 空槽不渲染成噪声)。"""
    def names(units: Any) -> str:
        if not isinstance(units, list):
            return MISSING
        out = []
        for u in units:
            if u is None:
                continue
            if isinstance(u, dict) and u.get('char_id'):
                star = f"{_fmt(u.get('star'))}★" if u.get('star') else ''
                pos = '(前)' if u.get('position_pref') == 'front' else ''
                out.append(f"{_fmt(u.get('char_id'))}{star}{pos}")
            else:
                out.append(_short(u, 16))
        return '、'.join(out) if out else '空'

    dep = st.get('deployed')
    front = back = MISSING
    if isinstance(dep, list):
        front = names([u for u in dep if isinstance(u, dict)
                       and u.get('position_pref') == 'front'])
        back = names([u for u in dep if isinstance(u, dict)
                      and u.get('position_pref') != 'front'])
    return f"盘面:前排 {front} · 后排 {back} · 备战栏 {names(st.get('bench'))}"


def _state_face(row: dict[str, Any], gaps: GapLog) -> list[str]:
    """入口观察(备战 op;补给 op 复用其 state 行):curated 关键行 + state
    面全量行 + 盘面行。

    数据源 = 帧平铺字段 + 帧 state 快照(R1 的消费点)。state 整份缺失记
    一条缺口;state 内单字段不逐个记缺(低噪声例外,理由见模块 docstring
    「韧性口径」)。
    """
    st = row.get('state')
    if not isinstance(st, dict):
        gaps.miss('decisions[].state')
        return [f'- 入口观察:{MISSING}(帧无 state 快照)', '']
    gold = row.get('gold') if row.get('gold') is not None else st.get('gold')
    gold_s = '—' if gold is None else _fmt(gold) + _trust_mark(st, 'gold_readable')
    hp = row.get('hp') if row.get('hp') is not None else st.get('hp')
    hp_s = '—' if hp is None else _fmt(hp) + _trust_mark(st, 'hp_trusted')
    xp = st.get('xp_progress')
    xp_s = (f"{_fmt(xp[0])}/{_fmt(xp[1])}"
            if isinstance(xp, list) and len(xp) == 2 else '—')
    lvl = st.get('level')
    lvl_s = '—' if lvl is None else (
        _fmt(lvl) + f"(xp {xp_s}"
        + (f",升级 {_fmt(st.get('level_up_cost'))}金)"
           if st.get('level_up_cost') is not None else ')'))
    ed = st.get('enemy_difficulty')
    ed_s = '—' if ed is None else (
        _fmt(ed) + ('(live)' if st.get('enemy_difficulty_live') else ''))
    cap = st.get('deploy_cap')
    cap_s = '—' if cap is None else (
        f"{_fmt(cap)}(前{_fmt(st.get('front_max'))}"
        f"/后{_fmt(st.get('back_max'))})")
    strat = st.get('active_strategies')
    strat_s = ('、'.join(_fmt(x) for x in strat)
               if isinstance(strat, list) and strat
               else ('—' if strat is None else _short(strat, 40)))
    row_bits = [
        f'金 {gold_s}', f'血 {hp_s}', f'等级 {lvl_s}',
        f"节点 {_dash(st.get('node_type'))}", f'敌难度 {ed_s}',
        f"环境 {_dash(st.get('active_env'))}",
        f'持卡 {strat_s}', f'cap {cap_s}',
        f"席满 {_dash(st.get('bench_full_flag'))}",
        f"连胜 {_dash(st.get('streak'))}",
        f"配方 {_short(row.get('target_comp'), 32) if row.get('target_comp') else '—'}",
        f"意向 {_v3_brief(row.get('v3_intention'))}",
        f"锁线 pair {_dash(row.get('sess_p1_pair'))}",
    ]
    parts = ['- 入口观察:' + ' · '.join(row_bits)]
    rest = {k: v for k, v in st.items()
            if k not in _STATE_CURATED and v not in (None, '', [], {})}
    if rest:
        parts.append('- state 面:' + ' / '.join(
            f'{k}={_short(v, 36)}' for k, v in sorted(rest.items())))
    parts.append('- ' + _board_line(st))
    parts.append('')
    return parts


def _wave_face(snap: dict[str, Any]) -> str:
    """单个商店快照 → 波面行(牌名+费+星+合成预览;rho 观察尾注)。"""
    cards = snap.get('shop') if isinstance(snap.get('shop'), list) else []
    bits = []
    for c in cards:
        if not isinstance(c, dict):
            bits.append(_short(c, 12))
            continue
        b = f"{_fmt(c.get('name'))}{_fmt(c.get('cost'))}金"
        if c.get('star') not in (None, 1):
            b += f"{_fmt(c.get('star'))}★"
        if c.get('merge_preview'):
            b += f"〔合成预览 mp{_fmt(c.get('merge_preview'))}〕"
        bits.append(b)
    rho = snap.get('rho_obs')
    rho_s = ''
    if isinstance(rho, dict):
        sysd = rho.get('systems')
        if isinstance(sysd, dict) and sysd:
            rho_s = ' · rho:' + '/'.join(f'{k}{v}' for k, v in sysd.items())
    return '店面:' + ('、'.join(bits) if bits else '(空店面)') + rho_s


def _shop_entry(op: dict[str, Any], gaps: GapLog) -> list[str]:
    """商店 op 入口观察:金 + 逐波店面(快照分段)+ 金账对拍(审计渲染缺
    R3:spend_ledger 此前只在零决策轮内联,商店访问的金账对拍链断)。"""
    parts: list[str] = []
    snaps = op['snapshots']
    gold = next((s.get('gold') for s in snaps if isinstance(s, dict)
                 and s.get('gold') is not None), None)
    if gold is None and op['frames']:
        gold = op['frames'][0][1].get('gold')
    head = f"- 入口观察:金 {_dash(gold)}"
    if not snaps:
        head += f';{MISSING}(访问无快照)'
        gaps.miss('shop_snapshots(访问无快照)')
    if not op['open_shop_recorded']:
        head += ';**开店通道未记录**(开店步无决策行,起点按快照边界反推)'
    parts.append(head)
    wave_no = 0
    for s in snaps:
        if not isinstance(s, dict):
            continue
        if str(s.get('event') or '') == 'refresh':
            parts.append(f"  - 刷新@{_ts_short(s.get('ts'))}"
                         f"(金 {_dash(s.get('gold'))})")
            continue
        wave_no += 1
        parts.append(f"  - 段{wave_no}(offer@{_ts_short(s.get('ts'))}) "
                     + _wave_face(s))
    for sp in op['spend_rows']:
        bt = '可信' if sp.get('gold_before_trusted') else '不可信'
        ct = '可信' if sp.get('gold_close_trusted') else '不可信'
        parts.append(
            f"- 金账对拍(spend_ledger):[{_fmt(sp.get('boundary'))}] "
            f"{_fmt(sp.get('duration_s'))}s 金{_fmt(sp.get('gold_before'))}"
            f"({bt})→{_fmt(sp.get('gold_close'))}({ct}) · "
            f"{_esc(_short(sp.get('detail'), 90))}")
    parts.append('')
    return parts


def _supply_entry(op: dict[str, Any], gaps: GapLog) -> list[str]:
    """补给 op:入口观察(分流帧)+ 拾取 N 选 1 + 合成结算行注(数据源 =
    outcomes 行 supply_pick;拾取是真实决策,判定三槽承载,审计 T1 消解)。"""
    parts: list[str] = []
    frames = op['frames']
    if frames:
        parts.append(
            f"- 入口观察:帧 [{frames[0][0]:02d}] phase="
            f"{_fmt(frames[0][1].get('phase'))}(流程心跳行,acts=[];备战分流点)")
        # 复用备战 op 的 state 面渲染,但首行标签换成「分流帧状态」:
        # 顶层已有「入口观察」行,避免同名行嵌套重复
        face = _state_face(frames[0][1], gaps)[:-1]
        if face:
            face[0] = face[0].replace('- 入口观察:', '- 分流帧状态:', 1)
        parts += ['  ' + ln for ln in face]
    else:
        parts.append(f'- 入口观察:{MISSING}(无分流帧)')
    pick = None
    so = op.get('supply_outcome')
    if isinstance(so, dict):
        pick = so.get('supply_pick')
    if isinstance(pick, dict):
        opts = pick.get('options') if isinstance(pick.get('options'), list) else []
        opt_bits = []
        for o in opts:
            if isinstance(o, dict):
                dia = '(带钻石标)' if o.get('has_diamond') else ''
                opt_bits.append(f"{o.get('char') or '(空位)'}+{o.get('equip')}{dia}")
            else:
                opt_bits.append(_short(o, 20))
        picked = (f"{pick.get('char') or '?'}+{pick.get('equip') or '?'}"
                  + ('(带钻石标)' if pick.get('has_diamond') else ''))
        line = (f"- 决策循环:补给轮无 spend 决策(结构性);拾取 "
                f"{_dash(pick.get('n_options') or len(opts))} 选 1:"
                f"{' / '.join(opt_bits) or MISSING} → 取 {picked}")
        if pick.get('refreshed'):
            line += ' · refreshed=是(刷过 1 次)'
        if pick.get('gold') is not None:
            line += f" · 金 {_fmt(pick.get('gold'))}"
        parts.append(line)
    else:
        gaps.miss('outcomes[](补给合成行缺失,拾取结果不可见)')
        parts.append(f'- 决策循环:拾取结果 {MISSING}(无合成结算行 supply_pick)')
    if isinstance(so, dict):
        parts.append(
            f"- 结算行:source={_fmt(so.get('source'))} @{_ts_short(so.get('ts'))} "
            f"hp_after={_dash(so.get('hp_after'))} —— 合成快照非结算事件,"
            f"按「陈旧直到证伪」口径判读;其 round_num 有跨轮 +1 漂移先例"
            f"(084421 复盘审计 S5),轮归属以分流帧为准")
    parts.append('')
    return parts


def _encounter_entry(op: dict[str, Any], gaps: GapLog) -> list[str]:
    """遭遇 op:选项面 + pick + 拒因(数据源 = exogenous event_choice,
    审计渲染缺 R2:此前 22 行外生流零渲染,真实决策无处可见)。"""
    e = op['annots'][0] if op['annots'] else {}
    ch = e.get('choice')
    if not isinstance(ch, dict):
        gaps.miss('exogenous[].choice(event_choice)')
        return [f'- 入口观察:{MISSING}(event_choice 无 choice 面)', '']
    opts = ch.get('options') if isinstance(ch.get('options'), list) else []
    opt_bits = []
    for o in opts:
        if isinstance(o, dict):
            opt_bits.append(f"难度{_fmt(o.get('difficulty'))}="
                            f"{'、'.join(_fmt(x) for x in o.get('rewards') or [])}")
        else:
            opt_bits.append(_short(o, 20))
    parts = [
        f"- 入口观察:遭遇 {_dash(ch.get('n_options') or len(opts))} 选 1:"
        + (' / '.join(opt_bits) or MISSING),
        f"- 决策循环:pick=idx{_fmt(ch.get('pick_idx'))}"
        + (f" · reason={_esc(_short(ch.get('reason'), 60))}"
           if ch.get('reason') else ''),
        '',
    ]
    return parts


def _invest_entry(op: dict[str, Any], gaps: GapLog) -> list[str]:
    """投资选卡 op:候选面 + chosen(数据源 = invest_cards 切片)。"""
    rows = op['invest_rows']
    chosen = [r for r in rows if r.get('chosen')]
    if rows and not chosen:
        gaps.miss('invest_cards[](选卡组无 chosen 行)')
    cards = ' / '.join(
        f"{_fmt(r.get('name'))}"
        + (f"({_short(r.get('effect_text'), 30)})" if r.get('effect_text') else '')
        + ('✓已选' if r.get('chosen') else '')
        for r in rows if isinstance(r, dict))
    pick = chosen[0] if chosen else None
    return [
        f'- 入口观察:候选 {len(rows)} 张:{cards or MISSING}',
        '- 决策循环:' + (
            f"选「{_fmt(pick.get('name'))}」+ 确认(无 decisions 行,结果在切片 chosen 位)"
            if pick else f'{MISSING}(无 chosen 行)'),
        '',
    ]


def _battle_obs(op: dict[str, Any], ctx: dict[str, Any],
                gaps: GapLog) -> list[str]:
    """战斗窗 op 观察:结算判定 + fill/伤害拆解等细字段(审计渲染缺 R5:
    progress_fill_ratio 是「打赢但进度填不满」死因主线的核心指标)+ 掉血
    战斗腿。数据源 = outcomes 切片行(审计渲染缺 R4:不再只读
    rounds[].outcome 内嵌面,补给轮之外的结算行恒可见)。"""
    o = op['outcome'] or {}
    killed = o.get('killed')
    hp_after = o.get('hp_after')
    if str(o.get('source') or '') == _TERMINAL_CLOSURE_SOURCE:
        # 收口终局行(T-185):对局收口标记非战斗结算——killed=False 是
        # 对局级「未通关」真值,走胜负分支会把停机收口轮渲染成战斗
        # 结算(「存活(killed=False)」暗示该轮打完且活下来,同型误读);
        # 专项标注分型(先例 = 补给合成行「合成快照非结算事件」)。
        verdict = (f"收口(未通关·{str(o.get('match_result') or '') or '?'})"
                   "·非战斗结算")
    elif killed is True:
        verdict = '胜(killed)'
    elif hp_after == 0:
        verdict = '败(战后 HP=0)'
    elif killed is False:
        verdict = '存活(killed=False)'
    else:
        gaps.miss('outcomes[].killed')
        verdict = MISSING
    dmg_bits = [f'伤害 {_num_or_dash(o.get("damage_dealt"))}']
    if o.get('damage_base') is not None \
            or o.get('damage_unfinished_progress') is not None:
        dmg_bits.append(f'拆解 基础 {_num_or_dash(o.get("damage_base"))}'
                        f'+未完成 {_num_or_dash(o.get("damage_unfinished_progress"))}')
    if 'damage_breakdown_visible' in o:
        dmg_bits.append(f'屏面可见 {_fmt(o.get("damage_breakdown_visible"))}')
    key = op['key']
    losses = ctx['loss_nodes'].get(key) if key else None
    loss_s = ('、'.join(_fmt(ln.get('delta')) for ln in losses)
              if losses else '—')
    bosses = o.get('boss_names')
    affixes = o.get('enemy_affixes')
    rows = [
        ('节点', _dash(o.get('node_type'))),
        ('我方配方', _dash(o.get('comp_tag'))),
        ('敌方(boss)', _esc('、'.join(_fmt(b) for b in bosses)
                            if isinstance(bosses, list) and bosses else '—')),
        ('敌方战后 HP', _dash(o.get('enemy_hp_after'))),
        ('伤害(拆解)', _esc(' '.join(dmg_bits))),
        ('结算判定', verdict),
        ('我方战后 HP', (_dash(hp_after))
         + (f"(置信 {_fmt(o.get('hp_confidence'))})" if 'hp_confidence' in o else '')
         + (f"(source {_fmt(o.get('source'))})" if o.get('source') else '')),
        ('进度 fill', _dash(o.get('progress_fill_ratio'))),
        ('progress_delta', _dash(o.get('progress_delta'))),
        ('连胜', _dash(o.get('streak'))),
        ('敌词缀', _esc('、'.join(_fmt(x) for x in affixes)
                        if isinstance(affixes, list) and affixes else '—')),
        ('难度(结算)', _dash(o.get('selected_difficulty'))),
        ('掉血(战斗腿)', _esc(loss_s)),
        ('备战席(战后)', _dash(o.get('bench_count'))),
        ('板面(战前)', _short(o.get('board_before'), 90)),
        ('故意弃战', _fmt(o.get('intentional_fold'))
         if 'intentional_fold' in o else '—'),
    ]
    return _kv_table(rows) + ['']


def _annot_lines(op: dict[str, Any]) -> list[str]:
    """挂靠本 op 的外生注记行(kind 非独立 op 的 exogenous 行:node_enter/
    sell_income/level_up/resumed_match;R2 的全量可见面)。briefing 行渲染
    为简报 op 的观察面。detail 是采集器的字符串摘要,原样引用。"""
    out: list[str] = []
    for e in op['annots']:
        if op['kind'] == 'briefing':
            out.append(f"- 观察:{_esc(_short(e.get('detail'), 160))}"
                       "(exogenous briefing 行)")
            continue
        ch = e.get('choice')
        extra = ''
        if isinstance(ch, dict) and ch.get('gold_delta') is not None:
            extra = f"({ch.get('char')} +{_fmt(ch.get('gold_delta'))}金)"
        out.append(f"- 外生行 {_fmt(e.get('kind'))}@{_ts_short(e.get('ts'))}:"
                   f"{_esc(_short(e.get('detail'), 80))}{extra}")
    return out


def _unit_table(units: list[dict[str, Any]]) -> list[str]:
    """单位列表 → 表格(槽/角色/星级/阵营/装备)。

    容错口径:整列表在位即视为采集成功,单位内子字段缺省渲染容错值
    (不逐个刷缺口);**None = 固定槽位的空槽**(合法语义,渲染 '(空槽)',
    不渲染成「非 dict 行」噪声——084421 审计渲染缺 R12 修正)。
    """
    parts = ['| 槽 | 角色 | 星级 | 阵营 | 装备 |', '|---|---|---|---|---|']
    for u in units:
        if u is None:
            parts.append('| — | (空槽) | | | |')
            continue
        if not isinstance(u, dict):
            parts.append(f'| ? | (非 dict 行: {_esc(_short(u))}) | | | |')
            continue
        cid = u.get('char_id')
        cid_s = _esc(_fmt(cid)) if cid else '(未知)'
        equips = u.get('equips')
        eq_s = ('、'.join(_fmt(e) for e in equips)
                if isinstance(equips, list) and equips else '—')
        slot = _fmt(u.get('slot')) if u.get('slot') is not None else '—'
        star = (_fmt(u.get('star')) + '★') if u.get('star') is not None else '—'
        faction = _esc(_fmt(u.get('faction'))) if u.get('faction') else '—'
        parts.append(f'| {slot} | {cid_s} | {star} | {faction} | {_esc(eq_s)} |')
    parts.append('')
    return parts


def _closure_obs(archive: dict[str, Any]) -> list[str]:
    """收口段:endgame 汇总 + 终局面面(审计渲染缺 R6:final_snapshot 板面/
    板凳/terminal 此前零消费,死局形态只能回档案翻)。"""
    eg = archive.get('endgame')
    if not isinstance(eg, dict):
        return [f'- 观察:{MISSING}(档案无 endgame 汇总)', '']
    parts = [
        '- 观察:结局 ' + _fmt(eg.get('result'))
        + ('(弃局/中断)' if eg.get('abandoned') is True else '')
        + f" · 位面 {_dash(eg.get('plane_reached'))}"
        + f" · 存活 {_dash(eg.get('rounds_survived'))} 轮"
        + f" · 终局 HP {_dash(eg.get('final_hp'))}"
        + f" · 难度 {_dash(eg.get('difficulty'))}",
        '- 收口链:on_match_end + 假局守卫 + 假 win 守卫 + record_run_summary'
        '(final_hp 走 _last_true_hp 防 100 兜底毒化)+ 对局存档装配 + match 清空'
        '(flow/outer_loop.md §5)',
    ]
    fs = eg.get('final_snapshot')
    if isinstance(fs, dict):
        parts.append(
            f"- 终局面面(final_snapshot@{_ts_short(fs.get('ts'))},"
            f"source={_fmt(fs.get('source'))},closure={_fmt(fs.get('closure'))})"
            f" 金 {_dash(fs.get('gold'))} · 等级 {_dash(fs.get('level'))}")
        term = fs.get('terminal')
        if isinstance(term, dict):
            parts.append(
                '- 仓位(终态):'
                + f"场{_fmt(term.get('deployed_count'))}"
                  f"/备{_fmt(term.get('bench_count'))}"
                  f"/穿{_fmt(term.get('equips_worn'))}"
                  f"/持{_fmt(term.get('equips_owned'))}")
        board = fs.get('board')
        if isinstance(board, dict) and board:
            parts.append('- 板面:' + _esc(_short(board, 160)))
        dep = fs.get('deployed')
        bench = fs.get('bench')
        if isinstance(dep, list):
            front = [u for u in dep if isinstance(u, dict)
                     and u.get('position_pref') == 'front']
            back = [u for u in dep if isinstance(u, dict)
                    and u.get('position_pref') != 'front']
            parts.append('- 终局前排:' + ('、'.join(
                f"{_fmt(u.get('char_id'))}{_fmt(u.get('star'))}★"
                for u in front) or '(空)'))
            parts.append('- 终局后排:' + ('、'.join(
                f"{_fmt(u.get('char_id'))}{_fmt(u.get('star'))}★"
                for u in back) or '(空)'))
        if isinstance(bench, list):
            parts += ['- 终局备战栏(空槽 = None 槽位):'] \
                + _unit_table(bench)
    else:
        parts.append(f'- 终局面面:{MISSING}(endgame.final_snapshot 缺)')
    parts.append('')
    return parts


def _op_header(op: dict[str, Any], idx: int) -> str:
    """op 标题行:序号 + 分支号 + 名称 → 处理类名(入口时间戳,证据构成)。

    入口时间戳 = 该 op 最早证据(开店步未记录的商店访问为快照 ts,可能早于
    首帧 ts);证据构成(帧区间/快照数)如实标注,防「时间从哪来」误读。
    """
    branch, name, handler = OP_LABELS[op['kind']]
    ev: list[str] = []
    if op['frames']:
        idxs = [g for g, _ in op['frames']]
        lo, hi = min(idxs), max(idxs)
        sep = '+' if op['kind'] == 'supply' else '-'
        span = f'[{lo:02d}]'
        if hi != lo:
            span += sep + f'[{hi:02d}]'
        ev.append('帧 ' + span)
    if op['kind'] == 'shop':
        ev.append(f"快照×{len(op['snapshots'])}")
        if not op['open_shop_recorded']:
            ev.append('开店通道未记录')
    if op['kind'] == 'supply' and isinstance(op.get('supply_outcome'), dict):
        ev.append(f"合成结算行@{_ts_short(op['supply_outcome'].get('ts'))}")
    if op['kind'] == 'encounter':
        ev.append('exogenous event_choice')
    if op['kind'] == 'invest':
        ev.append('invest_cards 切片')
    if op['kind'] == 'env':
        ev.append('选择结果见 state.active_env')
    if op['ts']:
        if op['kind'] == 'battle':
            # 收口终局行的 battle op 时间戳标签用「收口」——「结算」暗示
            # 战斗走到结算屏,与观察面专项标注同口径
            _oc = op.get('outcome') or {}
            ts_label = ('收口 ' if str(_oc.get('source') or '')
                        == _TERMINAL_CLOSURE_SOURCE else '结算 ')
        else:
            ts_label = ''
        ev_s = (f'({ts_label}{_ts_short(op["ts"])}'
                + (',' + ';'.join(ev) if ev else '') + ')')
    else:
        ev_s = ('(' + ';'.join(ev) + ')') if ev else ''
    return f'#### op{_cnum(idx)} {branch} {name} → {handler}{ev_s}'


def _terminal_line(op: dict[str, Any], next_kind: str | None) -> list[str]:
    """终结标记(每 op 必有终结面;CloseShop 结构性不入行按
    flow/shop_visit.md §2 申报——渲染器把「没入行」本身标出来防误读)。"""
    if op['kind'] == 'shop':
        return ['- 终结:CloseShop(结构性不入行,收店)']
    if op['kind'] != 'prep' or not op['frames']:
        return []
    last_acts = {a.get('__type__') for a in _frame_actions(op['frames'][-1][1])}
    if _BATTLE_ACTION in last_acts:
        return ['- 终结:StartBattle 出战 → 交战斗窗']
    term = sorted(last_acts & _PREP_TERM_ACTIONS)
    if term:
        return [f'- 终结:{"、".join(term)}(逻辑态未建模,访问终结交回外循环)']
    if next_kind is None:
        return ['- 终结:流终止(截断,未见终结动作)']
    label = OP_LABELS.get(next_kind, ('', next_kind, ''))[1] or next_kind
    return [f'- 终结:访问交回外循环重识别(下一调度:{label})']


def _action_params(a: dict[str, Any]) -> str:
    """动作参数:除 __type__ 外的键值;card 子对象取人读摘要;空 reason 略。"""
    parts: list[str] = []
    for k, v in a.items():
        if k == '__type__':
            continue
        if k == 'card' and isinstance(v, dict):
            parts.append(f"card={v.get('name') or '?'}"
                         f"({_fmt(v.get('star'))}★/{_fmt(v.get('cost'))}金)")
        elif k == 'reason' and not v:
            continue
        else:
            parts.append(f'{k}={_short(v, 40)}')
    return _esc('; '.join(parts)) or '—'


def _render_op(op: dict[str, Any], idx: int, next_kind: str | None,
               ctx: dict[str, Any], gaps: GapLog) -> list[str]:
    """单个 op 记录:标题 + 入口观察 + 决策循环(逐帧动作与拒因)+ 外生注记
    + 终结 + 判定三槽(有决策承载的 op 才有,match-review.md 承载面规则)。

    决策循环逐帧渲染(审计渲染缺 R10:此前 shop_rejects 只取末帧聚合快照,
    多波访问首段拒因丢失、残留拒因误标本轮波面——逐帧原样渲染同根双修)。
    """
    parts = [_op_header(op, idx)]
    kind = op['kind']
    if kind == 'prep':
        if op['frames']:
            parts += _state_face(op['frames'][0][1], gaps)
        else:
            parts += [f'- 入口观察:{MISSING}', '']
    elif kind == 'shop':
        parts += _shop_entry(op, gaps)
    elif kind == 'supply':
        parts += _supply_entry(op, gaps)
    elif kind == 'encounter':
        parts += _encounter_entry(op, gaps)
    elif kind == 'invest':
        parts += _invest_entry(op, gaps)
    elif kind == 'env':
        parts += [f"- 入口观察:环境 {_fmt(op.get('env'))}"
                  '(选项面未采集——环境三选一候选无行,判定面只有结果值)', '']
    elif kind == 'battle':
        parts += _battle_obs(op, ctx, gaps)
    elif kind == 'closure':
        parts += _closure_obs(ctx['archive'])

    # —— 决策循环:逐帧动作与拒因(备战/商店;补给 op 的拾取面在入口节) ——
    if kind in ('prep', 'shop'):
        lines: list[str] = []
        n = 0
        for gidx, row in op['frames']:
            acts = _frame_actions(row)
            if not acts:
                lines.append(f'  - 帧 [{gidx:02d}] {_ts_short(row.get("ts"))}'
                             ' → (无动作行)')
            for a in acts:
                n += 1
                t = a.get('__type__') or '?'
                lines.append(f'  - 帧 [{gidx:02d}] {_ts_short(row.get("ts"))}'
                             f' → #{n} {_esc(_fmt(t))}'
                             f'({_action_params(a)})')
            rej = row.get('shop_rejects')
            if isinstance(rej, dict) and rej:
                rej_s = '、'.join(f'{k}={_short(v, 20)}' for k, v in rej.items())
                lines.append(f'  - 拒因(帧 [{gidx:02d}]):{_esc(rej_s)}')
        if kind == 'shop':
            lines.append('  - (开店/收店步不入决策行:OpenShop 有无见标题标注;'
                         'CloseShop 结构性不入行)')
        parts += (['- 决策循环:'] + lines + ['']) if lines \
            else ['- 决策循环:(无动作行)', '']
    parts += _annot_lines(op) if kind != 'encounter' else []
    # (encounter 的 event_choice 行已被入口观察整体消费,不再重复渲染)
    parts += _terminal_line(op, next_kind)
    if kind in _DECISION_OP_KINDS:
        parts += list(JUDGMENT_SLOTS)
        parts += [JUDGMENT_NOTE, '']
    else:
        parts.append('')
    return parts


# ---------------------------------------------------------------------------
# 节点分组与轮级事实
# ---------------------------------------------------------------------------


def _node_alias(node: Any) -> str:
    """节点类型显示别名:rounds[].node_type 有三源混写残留(084421 审计 S9:
    同表内「奖励/普通战斗」中文与 'supply' 英文枚举并存),显示统一到
    outcomes 词表;原值不改动。"""
    return {'supply': '补给'}.get(str(node or ''), str(node or '?节点'))


def _round_facts(r: dict[str, Any] | None, ctx: dict[str, Any],
                 key: tuple[int, int], gaps: GapLog) -> list[str]:
    """组尾「轮级事实」:强化计数(审计渲染缺 R11:升级两条通道都计,此前
    只数 LevelUpShop+ClickSpheres,备战 LevelUp 花钱升 6 渲染成 ×0)/ 血购
    事件 / 对账注记 / 留证 / 观测冲突。全部条件渲染(无内容零噪声)。"""
    parts: list[str] = []
    counts: dict[str, int] = {}
    if isinstance(r, dict) and isinstance(r.get('actions'), list):
        for a in r['actions']:
            t = a.get('__type__') if isinstance(a, dict) else None
            if t:
                counts[t] = counts.get(t, 0) + 1
    if counts:
        up_shop = counts.get('LevelUpShop', 0)
        up_prep = counts.get('LevelUp', 0)
        bits = []
        if up_shop or up_prep:
            bits.append(f'升级 店内×{up_shop}+备战×{up_prep}')
        if counts.get('ClickSpheres'):
            bits.append(f"点经验×{counts['ClickSpheres']}")
        if counts.get('OpenBox'):
            bits.append(f"开箱×{counts['OpenBox']}")
        rest = {k: v for k, v in counts.items()
                if k not in ('LevelUpShop', 'LevelUp', 'ClickSpheres', 'OpenBox')}
        if rest:
            bits.append(' '.join(f'{k}×{v}' for k, v in sorted(rest.items())))
        if bits:
            parts.append('**强化动作计数**(升级含店内 LevelUpShop 与备战'
                         ' LevelUp 两通道):' + ' · '.join(bits))
            parts.append('')
    if ctx['has_hp_events_col']:
        events = [e for e in ctx['hp_events']
                  if (e.get('plane'), e.get('round')) == key]
        if events:
            parts.append('血购事件(hp_events,血购击数口径):')
            for e in events:
                parts.append(
                    f"- hp_delta={_fmt(e.get('hp_delta'))}"
                    f" mode={_fmt(e.get('mode'))}"
                    f" clicks={_fmt(e.get('clicks'))}"
                    f" basis={_fmt(e.get('basis'))} ts={_fmt(e.get('ts'))}")
            parts.append('')
    else:
        # 旧档无顶层 hp_events 列:由 exogenous 流 kind='hp_pay' 兜底显影
        gaps.miss('顶层 hp_events 列(旧档案,由 exogenous 流兜底显影)')
        events = [e for e in ctx['exogenous']
                  if (e.get('kind') or '') == 'hp_pay'
                  and (e.get('choice') or {}).get('plane') == key[0]
                  and (e.get('choice') or {}).get('round_num') == key[1]]
        if events:
            parts.append('血购事件(旧档口径,exogenous.kind=hp_pay):')
            for e in events:
                ch = e.get('choice') or {}
                parts.append(f"- hp_delta={_fmt(ch.get('hp_delta'))}"
                             f" mode={_fmt(ch.get('mode'))} ts={_fmt(e.get('ts'))}")
            parts.append('')
    for row in ctx['recon_rows']:
        rf = row.get('resume_frame') if isinstance(row.get('resume_frame'), dict) else {}
        if (rf.get('plane'), rf.get('round_num')) == key:
            parts.append(
                f"恢复对账:本帧为续局段恢复帧;unexplained_delta="
                f"{_fmt(row.get('unexplained_delta'))}"
                f"(负=停机间隙真掉血;consumed_by_chain="
                f"{_fmt(row.get('consumed_by_chain'))})")
            parts.append('')
    if ctx['has_defects_col']:
        defects = [d for d in ctx['hp_pay_defects']
                   if (d.get('plane'), d.get('round')) == key]
        if defects:
            parts.append('血购对账缺陷(hp_pay_defects,建模期望 vs 结算真值):')
            for d in defects:
                parts.append(
                    f"- expected={_fmt(d.get('expected_hp'))}"
                    f" actual={_fmt(d.get('actual_hp'))}"
                    f" gap={_fmt(d.get('gap'))}"
                    f" modeled_paid={_fmt(d.get('modeled_paid'))}")
            parts.append('')
    evidence = (r or {}).get('evidence')
    if isinstance(evidence, list) and evidence:
        parts.append(f'对账留证截图 ×{len(evidence)}:'
                     + '、'.join(_fmt(x) for x in evidence[:4])
                     + ('…' if len(evidence) > 4 else ''))
        parts.append('')
    conflicts = ctx['conflicts_by_round'].get(key, [])
    if conflicts:
        parts += _conflict_table(conflicts)
    return parts


def _conflict_table(rows: list[dict[str, Any]]) -> list[str]:
    """obs_conflicts 明细表(带行数上限)。"""
    parts = [f'观测冲突 ×{len(rows)}(识别回读与账面不一致,采新对账纠漂):',
             '', '| ts | field | 判定 | 源 | 变化(old→新) |',
             '|---|---|---|---|---|']
    for c in rows[:_CONFLICT_ROWS_CAP]:
        parts.append(
            f"| {_esc(_fmt(c.get('ts')))} | {_esc(_fmt(c.get('field')))} "
            f"| {_esc(_short(c.get('verdict'), 30))} "
            f"| {_esc(_fmt(c.get('source')))} "
            f"| {_esc(_short(c.get('old'), 24))}→{_esc(_short(c.get('new'), 24))} |")
    if len(rows) > _CONFLICT_ROWS_CAP:
        parts.append(f'…另有 {len(rows) - _CONFLICT_ROWS_CAP} 条略(量 '
                     f'{len(rows)})。')
    parts.append('')
    return parts


def _render_group(no: int, key: tuple[int, int] | None,
                  ops: list[dict[str, Any]],
                  rounds_by_key: dict[tuple[int, int], dict[str, Any]],
                  ctx: dict[str, Any], gaps: GapLog) -> list[str]:
    """一个节点组:标题(节点类型;多 run 段的组如实标注「跨段」)+ 组内 op
    按调用序 + 组尾轮级事实。"""
    run_ids: set[str] = set()
    for op in ops:
        run_ids |= op['run_ids']
    r = rounds_by_key.get(key) if key else None
    node = _node_alias((r or {}).get('node_type')) if r else ''
    if key is not None:
        title = f'{no}. P{key[0]}·R{key[1]}'
    else:
        # 未归轮组(帧 plane/round 缺失):不猜轮号,如实标注
        title = f'{no}. 未归轮(op 帧缺轮键)'
    if node:
        title += f'({node}' + (';跨段)' if len(run_ids) > 1 else ')')
    elif len(run_ids) > 1:
        title += '(跨段)'
    parts = [f'### {title}', '']
    for i, op in enumerate(ops, 1):
        nxt = ops[i]['kind'] if i < len(ops) else None
        parts += _render_op(op, i, nxt, ctx, gaps)
    parts += _round_facts(r, ctx, key or (-1, -1), gaps)
    return parts


# ---------------------------------------------------------------------------
# 局头 / 开局面 / 恢复对账
# ---------------------------------------------------------------------------


def _render_header(archive: dict[str, Any], seg_ids: list[str],
                   run_filter: str | None, gaps: GapLog) -> list[str]:
    """局头:标识行 + 结算/版本/连续性表 + 段列表(含 code_commit/notes 列,
    审计渲染缺 R7:跨段双码与停局原因在此可见)+ 开局面 + 恢复对账。"""
    gid = archive.get('game_id') or '?'
    schema_v = archive.get('schema_version')
    parts = [f'# 货币战争复盘 {gid}', '']
    note = (f'工具 tools/cw/replay_to_md.py · 档案 schema_version='
            f'{schema_v if schema_v is not None else MISSING} · 段数 '
            f'{len(seg_ids)}({"+".join(seg_ids) if seg_ids else MISSING})'
            f' · 时间窗 {_cell(archive, "start_ts", "start_ts", gaps, dash_empty=True)}'
            f' ~ {_cell(archive, "end_ts", "end_ts", gaps, dash_empty=True)}')
    parts += [f'> {note}', '']
    if run_filter and run_filter not in seg_ids:
        parts += [f'> [警告] --run {run_filter} 不在段列表,流过滤无命中,'
                  '已按全段渲染。', '']

    endgame = archive.get('endgame')
    endgame = endgame if isinstance(endgame, dict) else None
    if endgame is None:
        gaps.miss('endgame')
    seg0 = (archive.get('segments') or [{}])
    seg0 = seg0[0] if seg0 and isinstance(seg0[0], dict) else {}
    summary = _sub(seg0, 'summary', 'segments[0].summary', gaps) or {}
    abandoned = endgame.get('abandoned') if endgame else None
    result = _cell(endgame, 'result', 'endgame.result', gaps, dash_empty=True)
    if abandoned is True:
        result += '(弃局/中断)'
    ver = _sub(archive, 'strategy_version', 'strategy_version', gaps) or {}
    header_rows = [
        ('结局', result),
        ('到达位面 / 存活轮',
         f"{_cell(endgame, 'plane_reached', 'endgame.plane_reached', gaps, none_ok=True)}"
         f' / {_cell(endgame, "rounds_survived", "endgame.rounds_survived", gaps, none_ok=True)}'),
        ('终局 HP(结算真值)',
         _cell(endgame, 'final_hp', 'endgame.final_hp', gaps, none_ok=True)),
        ('难度', _cell(summary, 'difficulty', 'runs.summary.difficulty',
                       gaps, dash_empty=True)),
        ('策略版本 code_commit',
         _cell(ver, 'code_commit', 'strategy_version.code_commit', gaps,
               dash_empty=True)),
        ('注册表指纹',
         _cell(ver, 'registry_fingerprint', 'strategy_version.registry_fingerprint',
               gaps, dash_empty=True)),
        ('连续性注记', _cell(archive, 'continuity_note', 'continuity_note',
                             gaps, dash_empty=True)),
    ]
    parts += ['## 1. 局头', '']
    parts += _kv_table(header_rows)

    parts += ['', '### 段列表', '',
              '| 段 run_id | code_commit | 首帧(位面,轮) | 结果 | 存活轮 | '
              '终局 HP | notes |',
              '|---|---|---|---|---|---|---|']
    for s in archive.get('segments') or []:
        if not isinstance(s, dict):
            continue
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        ff = _fmt(s.get('first_frame')) if s.get('first_frame') is not None else '—'
        parts.append(
            f"| {_cell(s, 'run_id', 'segments[].run_id', gaps)} "
            f"| {_cell(sm, 'code_commit', 'segments[].summary.code_commit', gaps, dash_empty=True)} "
            f"| {ff} "
            f"| {_cell(sm, 'result', 'segments[].summary.result', gaps, dash_empty=True)} "
            f"| {_cell(sm, 'rounds_survived', 'segments[].summary.rounds_survived', gaps, none_ok=True)} "
            f"| {_cell(sm, 'final_hp', 'segments[].summary.final_hp', gaps, none_ok=True)} "
            f"| {_cell(sm, 'notes', 'segments[].summary.notes', gaps, dash_empty=True)} |")

    parts += _render_opening(archive, gaps)
    parts += _render_recon(archive, gaps)
    return parts


def _render_opening(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """开局面:难度/已选投资卡全表(带选中位与 ts——审计渲染缺 R8:选卡
    实际发生在对应轮的投资 op,时序列防「静置开局面」误导)。"""
    opening = _sub(archive, 'opening', 'opening', gaps)
    if opening is None:
        return ['### 开局面', '', MISSING, '']
    invest = opening.get('invest_cards')
    parts = ['### 开局面', '']
    if isinstance(invest, list) and invest:
        parts += ['投资卡(投资策略环境 + 策略卡,chosen=是否选中;'
                  'ts=选卡时点,对应轮的选卡 op 见逐 op 复盘):', '',
                  '| kind | idx | ts | 名称 | 选中 | 效果摘要 |',
                  '|---|---|---|---|---|---|']
        for c in invest:
            if not isinstance(c, dict):
                continue
            parts.append(
                f"| {_cell(c, 'kind', 'opening.invest_cards[].kind', gaps, dash_empty=True)} "
                f"| {_cell(c, 'idx', 'opening.invest_cards[].idx', gaps, none_ok=True)} "
                f"| {_cell(c, 'ts', 'opening.invest_cards[].ts', gaps, dash_empty=True)} "
                f"| {_cell(c, 'name', 'opening.invest_cards[].name', gaps)} "
                f"| {_cell(c, 'chosen', 'opening.invest_cards[].chosen', gaps)} "
                f"| {_esc(_short(c.get('effect_text'), 80))} |")
        parts.append('')
    else:
        gaps.miss('opening.invest_cards')
        parts += [MISSING, '']
    chosen = opening.get('chosen_strategies')
    if isinstance(chosen, list) and chosen:
        parts.append('已选策略卡:' + '、'.join(_fmt(x) for x in chosen))
        parts.append('')
    return parts


def _render_recon(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """恢复态对账列(续局段恢复帧 vs 前段末帧;含段界重锚差)。"""
    recon = archive.get('resume_reconciliation')
    parts = ['### 恢复态对账(resume_reconciliation)', '']
    if recon is None:
        gaps.miss('resume_reconciliation')
        parts += [MISSING, '']
        return parts
    if not isinstance(recon, list) or not recon:
        parts += ['(空 = 单段局无续局段,无对账事件)', '']
        return parts
    parts += ['| 段 run_id | 恢复帧(位面,轮) | hp 恢复/前段末 | 金 | 等级 |'
              ' 重锚差 unexplained_delta |', '|---|---|---|---|---|---|']
    for row in recon:
        if not isinstance(row, dict):
            continue
        rf = row.get('resume_frame') if isinstance(row.get('resume_frame'), dict) else {}
        hp = row.get('hp') if isinstance(row.get('hp'), dict) else {}
        gold = row.get('gold') if isinstance(row.get('gold'), dict) else {}
        parts.append(
            f"| {_cell(row, 'run_id', 'resume_reconciliation[].run_id', gaps)} "
            f"| {_esc(_fmt(rf.get('plane')))}r{_esc(_fmt(rf.get('round_num')))} "
            f"| {_esc(_fmt(hp.get('resume')))} / {_esc(_fmt(hp.get('prev_final')))} "
            f"| {_esc(_fmt(gold.get('resume')))} / {_esc(_fmt(gold.get('prev_final')))} "
            f"| {_esc(_fmt(row.get('unexplained_delta')))} |")
    parts.append('')
    return parts


# ---------------------------------------------------------------------------
# 全局
# ---------------------------------------------------------------------------


def _render_gold_traj(rounds: list[dict[str, Any]], archive: dict[str, Any],
                      gaps: GapLog) -> list[str]:
    """金轨迹表:逐轮轮槽金(带可信位)+ 段摘要 gold_trajectory 原始列。"""
    parts = ['### 金轨迹', '', '| 轮 | 金 | 可信 |', '|---|---|---|']
    for r in rounds:
        if not isinstance(r, dict):
            continue
        g = _cell(r, 'gold', 'rounds[].gold(金轨迹)', gaps, none_ok=True)
        trusted = '是' if r.get('gold_readable') is not False else '[!否]'
        parts.append(f'| P{r.get("plane")}·R{r.get("round")} | {g} | {trusted} |')
    parts.append('')
    for s in archive.get('segments') or []:
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        traj = sm.get('gold_trajectory')
        if isinstance(traj, list) and traj:
            rid = s.get('run_id') if isinstance(s, dict) else '?'
            parts.append(f'段 {_esc(_fmt(rid))} gold_trajectory(段摘要):'
                         + ', '.join(_fmt(x) for x in traj))
            parts.append('')
    if not parts[-1].strip():
        parts.pop()
    return parts


def _render_fill_traj(outcomes: list[dict[str, Any]]) -> list[str]:
    """进度 fill 轨迹(审计渲染缺 R5 的全局面:「打赢但进度填不满」死因主线
    一表可见;合成补给行不入表——非结算事件;收口终局行(T-185)入表但
    胜负列专项标注「收口(未通关)」——其 killed=False 是对局级终了真值
    非该轮战斗结算,渲染成「败」会把停机收口轮误读成该轮打输)。"""
    rows = []
    for o in outcomes:
        if str(o.get('source') or '') == _SYNTHETIC_SUPPLY_SOURCE:
            continue
        try:
            key = f"P{int(o.get('plane'))}·R{int(o.get('round_num'))}"
        except (TypeError, ValueError):
            key = '—'
        killed = o.get('killed')
        if str(o.get('source') or '') == _TERMINAL_CLOSURE_SOURCE:
            verdict = f"收口(未通关·{str(o.get('match_result') or '') or '?'})"
        else:
            verdict = ('胜' if killed is True else
                       '败' if killed is False or o.get('hp_after') == 0 else '—')
        rows.append((
            key, _fmt(o.get('node_type')), verdict,
            _dash(o.get('progress_fill_ratio')),
            _dash(o.get('progress_delta')),
            _num_or_dash(o.get('damage_dealt')),
        ))
    parts = ['### 进度 fill 轨迹(结算 progress_fill_ratio)', '',
             '| 轮 | 节点 | 胜负 | fill | progress_delta | 伤害 |',
             '|---|---|---|---|---|---|']
    parts += [f'| {a} | {_esc(b)} | {c} | {d} | {e} | {f} |'
              for a, b, c, d, e, f in rows]
    if not rows:
        parts.append('(无结算行)')
    parts.append('')
    return parts


def _render_pivot(rounds: list[dict[str, Any]], archive: dict[str, Any],
                  gaps: GapLog) -> list[str]:
    """pivot 链:目标配方的变更序列(换线即 pivot)+ 段摘要计数对账。"""
    parts = ['### pivot 链(目标配方变更序列)', '']
    chain: list[str] = []
    prev: Any = None
    for r in rounds:
        if not isinstance(r, dict):
            continue
        tc = r.get('target_comp')
        if not tc or tc == prev:
            continue
        chain.append(f"P{r.get('plane')}·R{r.get('round')} {_esc(_fmt(tc))}")
        prev = tc
    parts.append(' → '.join(chain) if chain
                 else '(无目标配方记录,pivot 链不可得)')
    parts.append('')
    for s in archive.get('segments') or []:
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        committed = sm.get('comps_committed')
        if isinstance(committed, list) and committed:
            rid = s.get('run_id') if isinstance(s, dict) else '?'
            parts.append(f'段 {_esc(_fmt(rid))} comps_committed(段摘要):'
                         + '、'.join(_fmt(x) for x in committed)
                         + f'(pivot_count={_esc(_fmt(sm.get("pivot_count")))})')
            parts.append('')
        elif sm:
            gaps.miss('segments[].summary.comps_committed')
    if not parts[-1].strip():
        parts.pop()
    return parts


def _match_final_cw4_counters(archive: dict[str, Any]) -> Any:
    """新档案显影位读取:endgame.match_final.final.cw4_counters(W4 流删
    后局终级全键聚合的唯一档案显影位,装配端自局终行载荷纯读透传)。"""
    endgame = archive.get('endgame')
    match_final = (endgame.get('match_final')
                   if isinstance(endgame, dict) else None)
    final = (match_final.get('final')
             if isinstance(match_final, dict) else None)
    return (final.get('cw4_counters')
            if isinstance(final, dict) else None)


def _render_counters(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """armed 与拒因分键统计(cw4_counters 有则渲染;None=无计数载体)。

    载体两代(retirement.md §3 定谳落码形态/W4 流删):旧档案 = 顶层
    ``cw4_counters``(流装配,存量只读);新档案顶层键已拆,局终级全键
    聚合显影于 ``endgame.match_final.final.cw4_counters``——顶层缺键时
    回落该显影位,维持「局终快照→档案→复盘渲染」可见性链(W4 审计
    N3:新显影位此前在判读工具零读者)。None 与空 dict 分型语义两代一致。
    """
    parts = ['### armed 与拒因分键统计(cw4_counters 行为观测计数)', '']
    counters = archive.get('cw4_counters')
    if counters is None:
        counters = _match_final_cw4_counters(archive)
    if counters is None:
        gaps.miss('cw4_counters(无计数载体:旧档案无计数流/'
                  '新档案局终行无策略载体)')
        parts += [MISSING, '']
        return parts
    if not isinstance(counters, dict):
        gaps.miss('cw4_counters(非 dict)')
        parts += [MISSING, '']
        return parts
    if not counters:
        parts += ['(局内真实零计数。)', '']
        return parts
    armed = {k: v for k, v in counters.items() if 'armed' in k}
    rejects = {k: v for k, v in counters.items()
               if any(t in k for t in _REJECT_KEY_TOKENS)}
    rest = {k: v for k, v in counters.items()
            if k not in armed and k not in rejects}
    for title, group in (('armed(臂位/武装类)', armed),
                         ('拒因/拦截类', rejects), ('其他计数', rest)):
        parts.append(f'**{title}**' + (f' ×{len(group)}' if group else '(无)'))
        parts.append('')
        if group:
            for k, v in sorted(group.items()):
                parts.append(f'- {k}: {v}')
            parts.append('')
    return parts


def _render_round_continuity(rounds: list[dict[str, Any]],
                             covered_keys: set[tuple[int, int]]) -> list[str]:
    """轮号连续性检查,两向:①逐轮键 (plane, round) 在位面内断档 = 该轮数据
    缺失;②轮行在 rounds 表里却没有任何 op 挂靠 = 零决策帧轮或流被过滤。

    断档不是渲染器跳过,是源数据里就没有该轮的任何决策/结算行——复盘前先
    知道「少了一轮」,免得把轮序列误读成连续叙事;反向(有轮行无 op)同理,
    防止轮行被 op 粒度渲染静默吞掉。
    """
    by_plane: dict[int, set[int]] = {}
    for r in rounds:
        if not isinstance(r, dict):
            continue
        try:
            by_plane.setdefault(int(r.get('plane') or 0), set()).add(
                int(r.get('round') or 0))
        except (TypeError, ValueError):
            continue
    holes: list[str] = []
    for p, rounds_set in sorted(by_plane.items()):
        missing = sorted(set(range(min(rounds_set), max(rounds_set) + 1))
                         - rounds_set)
        if missing:
            holes.append(f'P{p} 缺轮 {missing}')
    bare: list[tuple[int, int]] = []
    for r in rounds:
        if not isinstance(r, dict):
            continue
        try:
            k = (int(r.get('plane')), int(r.get('round')))
        except (TypeError, ValueError):
            continue
        if k not in covered_keys:
            bare.append(k)
    parts = ['### 轮号连续性', '']
    lines = ['、'.join(holes)] if holes else []
    if bare:
        lines.append('有轮行但无任何 op(零决策帧轮或流被 --run 过滤):'
                     + '、'.join(f'P{p}·R{r}' for p, r in sorted(bare)))
    parts.append((';'.join(lines)) if lines else '各位面轮号连续,无断档。')
    parts.append('')
    return parts


def _render_global(archive: dict[str, Any], rounds: list[dict[str, Any]],
                   outcomes: list[dict[str, Any]],
                   covered_keys: set[tuple[int, int]],
                   gaps: GapLog) -> list[str]:
    """全局段:轮号连续性/金轨迹/进度 fill 轨迹/pivot 链/计数分键统计。"""
    parts = ['## 3. 全局', '']
    parts += _render_round_continuity(rounds, covered_keys)
    parts += _render_gold_traj(rounds, archive, gaps)
    parts += _render_fill_traj(outcomes)
    parts += _render_pivot(rounds, archive, gaps)
    parts += _render_counters(archive, gaps)
    return parts


def _unattributed_conflicts(ctx: dict[str, Any]) -> list[str]:
    """未归轮冲突(早于首锚/无 ts)集中显影,防静默丢行。"""
    rows = ctx['conflicts_by_round'].get((-1, -1), [])
    if not rows:
        return []
    return ['### 未归轮 obs_conflicts(早于首锚/缺 ts)', ''] \
        + _conflict_table(rows)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def collect_streams(archive: dict[str, Any], replay_dir: Path,
                    run_filter: str | None, gaps: GapLog) -> dict[str, Any]:
    """加载并按 run 过滤全部渲染输入流行(公开给测试与判读脚本复用)。

    decisions 元素 = (切片全局行序, 帧行):行序是持久索引,过滤后仍保
    原值,便于判读记录对帧。
    """
    seg_ids = _segment_ids(archive)
    allowed = _run_allow_set(seg_ids, run_filter)
    ts_lo = str(archive.get('start_ts') or '')
    # end_ts 缺 → 9999 兜底:ISO 串字典序比较下放行全部无 run_id 老行
    ts_hi = str(archive.get('end_ts') or '9999-12-31')

    def keep(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _filter_by_run(rows, allowed, ts_lo, ts_hi)

    decisions_raw = _load_stream(archive, replay_dir, 'decisions.jsonl', gaps)
    frames = [(i, r) for i, r in enumerate(decisions_raw)
              if _row_allowed(r, allowed, ts_lo, ts_hi)]
    return {
        'decisions': frames,
        'outcomes': keep(_load_stream(archive, replay_dir,
                                      'outcomes.jsonl', gaps)),
        'exogenous': keep(_load_stream(archive, replay_dir,
                                       'exogenous.jsonl', gaps)),
        'invest_cards': keep(_load_stream(archive, replay_dir,
                                          'invest_cards.jsonl', gaps)),
        'shop_snapshots': keep(_load_stream(archive, replay_dir,
                                            'shop_snapshots.jsonl', gaps)),
        'spend_ledger': keep(_load_stream(archive, replay_dir,
                                          'spend_ledger.jsonl', gaps)),
    }


#: 开局段/收口段标题(组序固定:开局段 → 节点组 → 收口段)
_OPEN_TITLE = '开局段(局前,非节点)'
_CLOSE_TITLE = '收口段'


def render_match(archive: dict[str, Any], replay_dir: Path,
                 run_filter: str | None = None) -> str:
    """渲染单局档案 → markdown 全文(含文末缺口清单)。

    archive = 档案 json dict;replay_dir = replay 目录(obs_conflicts 与
    切片缺失流的回源处);run_filter = 可选段 run_id 过滤。
    """
    gaps = GapLog()
    seg_ids = _segment_ids(archive)
    rounds_all = [r for r in (archive.get('rounds') or [])
                  if isinstance(r, dict)]
    if archive.get('rounds') is None:
        gaps.miss('rounds')

    streams = collect_streams(archive, replay_dir, run_filter, gaps)

    # obs_conflicts:恒走流文件(按设计不入切片)
    conflict_path = replay_dir / 'obs_conflicts.jsonl'
    conflicts_raw = _read_jsonl_tolerant(conflict_path)
    if not conflict_path.exists():
        gaps.miss('obs_conflicts.jsonl(文件缺失)')
    allowed = _run_allow_set(seg_ids, run_filter)
    ts_lo = str(archive.get('start_ts') or '')
    ts_hi = str(archive.get('end_ts') or '9999-12-31')
    conflicts = _filter_by_run(conflicts_raw, allowed, ts_lo, ts_hi)

    anchors = _round_anchors(
        [r for _, r in streams['decisions']] + streams['outcomes'])
    conflicts_by_round: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for c in conflicts:
        k = _attr_round(anchors, str(c.get('ts') or '')) or (-1, -1)
        conflicts_by_round.setdefault(k, []).append(c)

    hp_events = archive.get('hp_events')
    has_hp_events_col = isinstance(hp_events, list)
    defects = archive.get('hp_pay_defects')
    has_defects_col = isinstance(defects, list)
    recon_rows = [r for r in (archive.get('resume_reconciliation') or [])
                  if isinstance(r, dict)]
    ctx = {
        'archive': archive,
        'exogenous': streams['exogenous'],
        'hp_events': hp_events if has_hp_events_col else [],
        'has_hp_events_col': has_hp_events_col,
        'hp_pay_defects': defects if has_defects_col else [],
        'has_defects_col': has_defects_col,
        'recon_rows': recon_rows,
        'loss_nodes': _group_by_round(archive.get('loss_nodes')
                                      if isinstance(archive.get('loss_nodes'),
                                                    list) else []),
        'conflicts_by_round': conflicts_by_round,
    }
    if archive.get('loss_nodes') is None:
        gaps.miss('loss_nodes')

    # —— 第一遍:op 序列重建(两遍式;分组规则见模块 docstring) ——
    ops = build_op_sequence(streams['decisions'], streams['outcomes'],
                            streams['exogenous'], streams['invest_cards'],
                            streams['shop_snapshots'], streams['spend_ledger'])
    # 收口 op 的入口时间 = 局终收口时刻(档案 end_ts;build_op_sequence 是
    # 纯流行函数,不带档案级元数据,故在此注入)
    for op in ops:
        if op['kind'] == 'closure':
            op['ts'] = str(archive.get('end_ts') or '')

    # —— 第二遍:分组渲染 ——
    rounds_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    for r in rounds_all:
        try:
            rounds_by_key[(int(r.get('plane')), int(r.get('round')))] = r
        except (TypeError, ValueError):
            continue

    parts = _render_header(archive, seg_ids, run_filter, gaps)
    parts += ['## 2. 逐 op 复盘(外层循环画面 op 粒度)', '']
    parts += ['> op 边界重建规则:decisions 帧动作切分——OpenShop…CloseShop 段'
              ' = 商店访问 op(分支 0n),备战动作按逻辑态终结规则切备战 op'
              '(分支 1,flow/prep_visit.md §1);战斗窗/结算 = 每条 outcomes 行'
              '一个一体 op;补给/遭遇/投资选卡按各自数据面定位。协议 = '
              'sr-od-currency-war-dev skill references/match-review.md;'
              '分支序 = docs/develop/sr_od/application/currency_war/flow/outer_loop.md §2.2。', '']

    open_ops = [o for o in ops if o['segment'] == 'open']
    node_ops = [o for o in ops if o['segment'] == 'nodes']
    close_ops = [o for o in ops if o['segment'] == 'close']

    if open_ops:
        parts += [f'### {_OPEN_TITLE}', '']
        for i, op in enumerate(open_ops, 1):
            parts += _render_op(op, i, None, ctx, gaps)

    by_key: dict[tuple[int, int] | None, list[dict[str, Any]]] = {}
    for op in node_ops:
        by_key.setdefault(op['key'], []).append(op)
    node_no = 0
    for key in sorted(k for k in by_key if k is not None):
        node_no += 1
        parts += _render_group(node_no, key, by_key[key], rounds_by_key,
                               ctx, gaps)
    if None in by_key:
        parts += _render_group(node_no + 1, None, by_key[None], rounds_by_key,
                               ctx, gaps)
    if not node_ops and not rounds_all:
        parts += ['(档案无逐轮数据且流无决策帧:rounds 为空/缺失或装配失败,'
                  '判读先查装配。)', '']

    if close_ops:
        parts += [f'### {_CLOSE_TITLE}', '']
        for i, op in enumerate(close_ops, 1):
            parts += _render_op(op, i, None, ctx, gaps)
            unatt = op.get('_unattached') or []
            if unatt:
                parts += ['**未挂靠行**(挂靠不到任何 op,防静默丢行):']
                for u in unatt:
                    parts.append(f"- [{u['tag']}] key={_fmt(u['key'])} "
                                 + _esc(_short(u['row'], 160)))
                parts.append('')

    parts += _unattributed_conflicts(ctx)
    covered = {k for k in by_key if k is not None}
    parts += _render_global(archive, rounds_all, streams['outcomes'],
                            covered, gaps)
    parts += ['---', '']
    parts += ['## 4. 本次未能渲染的字段(遥测缺口清单)', '']
    parts += gaps.summary_lines()
    parts += ['', '_(缺口 = 该字段本次数据没采到或档案版本旧,不是渲染器'
              '故障;出现的路径即遥测缺口清单。)_', '']
    parts += ['**结构性不可见声明**(非遥测缺):弹窗关闭类纯路由迭代'
              '(outer_loop.md §2.2 浮层族:详情弹窗/概率表/道具详情/前进按钮'
              '等)在档案零痕迹,条数不可知,本稿无法逐条成节;CloseShop 终结'
              '结构性不入行(flow/shop_visit.md §2 申报),商店访问的收店时点'
              '以下一次 op 的入口时间为上界。', '']
    return '\n'.join(parts) + '\n'


def main(argv: list[str] | None = None) -> int:
    """CLI 入口;返回进程退出码(0=成功,2=档案缺/坏)。"""
    ap = argparse.ArgumentParser(
        description='货币战争对局档案 → markdown 深度复盘渲染器(op 粒度)')
    ap.add_argument('--match', required=True,
                    help='game_id(档案名 match_<id>.json)')
    ap.add_argument('--run', default=None,
                    help='只渲染某段 run_id 的流行(帧序号仍为切片全局行序)')
    ap.add_argument('--out', default=None,
                    help='输出 markdown 文件(缺省 = 深评固定落点 '
                         f'{DEEP_REVIEW_DIR}/<game_id>.md)')
    ap.add_argument('--stdout', action='store_true',
                    help='打印到 stdout 不落盘(覆盖 --out 缺省落盘行为)')
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR),
                    help='live 流根(缺省 .debug/currency_war/telemetry/live)')
    args = ap.parse_args(argv)

    replay_dir = Path(args.replay_dir)
    # matches 根派生与 match_archive.matches_dir 同规则:生产 live 根 →
    # 兄弟 telemetry/matches;其余目录(测试/离线自带流)→ 子目录 matches
    matches_dir = (DEFAULT_MATCHES_DIR if replay_dir == DEFAULT_REPLAY_DIR
                   else replay_dir / 'matches')
    archive_path = matches_dir / f'match_{args.match}.json'
    if not archive_path.exists():
        print(f'(档案不存在: {archive_path}——先装配:'
              f' uv run python -m sr_od.application.currency_war.telemetry.cli'
              f' assemble --game {args.match})', file=sys.stderr)
        return 2
    try:
        archive = json.loads(archive_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        print(f'(档案不可读: {archive_path}: {e})', file=sys.stderr)
        return 2
    md = render_match(archive, replay_dir, run_filter=args.run)
    if args.stdout:
        sys.stdout.write(md)
        return 0
    # 深评固定落点(2026-09-07 用户裁定):一局一份 <game_id>.md
    out = Path(args.out) if args.out else DEEP_REVIEW_DIR / f'{args.match}.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding='utf-8')
    print(f'(已写出: {out} 共 {len(md.splitlines())} 行)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
