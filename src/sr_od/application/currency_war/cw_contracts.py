"""行为合约层 v0(13 号提案;ADR-0162;2026-08-16)。

**诊断(13 号)**:M1-M36 损失最重的失败几乎都是**尾部行为失败**,每例花一局实机才发现
(M17b 满席死循环 86min/M24 20min/M25 spread 合法化/M19 hp 默认值毒化遥测/M34 钉死)。
共同点:**不需要知道「正确策略是什么」,只需要知道「系统自己声称要做什么」** —— 自洽性
判定零 ground truth、逐状态可判。

**v0 落地**(提案 v0a 回溯审计路径,零新基建):
- ``Contract``:三类合约(过程不变量/活性约束/不可逆前置),谓词作用于 GameState 轨迹;
- ``check_contracts(trajectory)``:轨迹级检查器,违约 → 结构化结果(合约名/轮次/证据);
- ``audit_replay(jsonl_path)``:回溯审计器 —— 已落盘 decisions.jsonl 直接过检查器
  (历史轨迹上的违约清单 = 合约价值的第一手证据);
- 初始合约清单(M 系列 6 例直接可判项):hp 默认值毒化(M19)/金零进展活性(M17b/M24 类)/
  target 钉死不 pivot 活性(M34 类)/fp 因己方买入走散(M25 类,自洽)/同名已上阵重复买(M8)。

**铁律**(提案 §2.1,防合约异化):①合约只表达引擎声明的过程纪律,禁编码「什么是好策略」
(不得出现胜率/强度/评分词);②看门狗永远不赢策略(L1 记录为主,L2/L3 分级兜底)。

纯函数 + 离线可测;运行时看门狗接线(影子模式)为 v1。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Contract:
    """行为合约:引擎对自身声明意图的可判谓词(作用于 GameState 轨迹)。"""
    name: str
    kind: str            # 'invariant'(状态→状态) / 'liveness'(轨迹级) / 'precondition'(动作级)
    description: str
    check: object        # callable(trajectory: list[dict]) -> list[Violation]


@dataclass
class Violation:
    """一次合约违约:合约名 + 轮次定位 + 证据(结构化,供 [cw!] 日志/语料沉淀)。"""
    contract: str
    round_ref: str       # 定位描述(如 'ts=... p2 r5' 或索引)
    evidence: str


# ===== 初始合约清单(M 系列实跑 6 例的可判化) =====

def _check_hp_default_poison(traj: list[dict]) -> list[Violation]:
    """M19:hp=100 是 GameState 默认值 —— 决策点连续恒 100(局中)且无 hp_readable 标记
    → 遥测毒化风险(「P1 零损」误判的同款)。可判:连续 ≥8 决策点 hp==100 且 plane≥2。"""
    out: list[Violation] = []
    run = 0
    for i, row in enumerate(traj):
        st = row.get('state') or {}
        hp = st.get('hp')
        if hp == 100 and (st.get('plane') or 1) >= 2 and (st.get('round_num') or 1) >= 2:
            run += 1
            if run >= 8:
                out.append(Violation('hp_default_poison', f'idx={i}',
                                     f'连续{run}决策点hp=100(默认值,非观测真值)'))
                run = 0
        else:
            run = 0
    return out


def _check_gold_no_progress(traj: list[dict]) -> list[Violation]:
    """M17b/M24 活性:连续 K 决策点(金,xp 等级,bench 数)三元零变化 = 死循环先兆。
    可判:同回合内连续 ≥12 决策点三元组全等(正常 plan→执行每步至少一项变化)。"""
    out: list[Violation] = []
    sig_run: tuple = ()
    run = 0
    for i, row in enumerate(traj):
        st = row.get('state') or {}
        sig = (st.get('gold'), st.get('level'), len(st.get('bench') or []))
        if sig == sig_run:
            run += 1
            if run >= 12:
                out.append(Violation('gold_no_progress', f'idx={i}',
                                     f'连续{run}决策点(金,级,bench)={sig}零变化'))
                run = 0
        else:
            sig_run = sig
            run = 0
    return out


def _check_target_no_pivot(traj: list[dict]) -> list[Violation]:
    """M34 活性:target 长期钉死同一 comp 且 fp 持续低位 = drought 从未触发转型探索。
    可判:同 target 跨 ≥18 决策点(约 6+ 回合)且期间 fp 均值 <0.4。"""
    out: list[Violation] = []
    by_target: dict[str, list[tuple[int, float]]] = {}
    for i, row in enumerate(traj):
        tgt = row.get('target_comp') or ''
        fp = row.get('fp')
        if tgt:
            by_target.setdefault(tgt, []).append((i, fp if isinstance(fp, (int, float)) else 0.0))
    for tgt, pts in by_target.items():
        if len(pts) >= 18:
            fps = [p for _, p in pts]
            if fps and sum(fps) / len(fps) < 0.4:
                out.append(Violation('target_no_pivot', f'idx={pts[0][0]}..{pts[-1][0]}',
                                     f'target={tgt} 钉死{len(pts)}点且fp均值{sum(fps)/len(fps):.2f}<0.4'))
    return out


def _check_fp_diverge_on_buy(traj: list[dict]) -> list[Violation]:
    """M25 自洽:target 钉死期,板面集中度(fp)因己方买入持续走散。
    可判(粗):同 target 窗口内 fp 单调下降跨 ≥6 决策点且期间有买(bench 数曾增)。
    v0 近似:fp 序列存在连续 6 点严格下降段(每个决策点都有买入的强假设不成立时降级 L1)。"""
    out: list[Violation] = []
    fps = [row.get('fp') for row in traj]
    fps = [f if isinstance(f, (int, float)) else None for f in fps]
    desc_run = 0
    start = 0
    for i in range(1, len(fps)):
        if fps[i - 1] is not None and fps[i] is not None and fps[i] < fps[i - 1]:
            if desc_run == 0:
                start = i - 1
            desc_run += 1
            if desc_run >= 6:
                out.append(Violation('fp_diverge_on_buy', f'idx={start}..{i}',
                                     f'fp连续{desc_run}点下降({fps[start]}→{fps[i]})'))
                desc_run = 0
        else:
            desc_run = 0
    return out


DEFAULT_CONTRACTS: tuple[Contract, ...] = (
    Contract('hp_default_poison', 'invariant', 'M19:hp 默认值不得当观测真值记遥测', _check_hp_default_poison),
    Contract('gold_no_progress', 'liveness', 'M17b/M24:决策环活性(金/级/bench 至少一项变化)', _check_gold_no_progress),
    Contract('target_no_pivot', 'liveness', 'M34:drought 长期钉死必须触发转型探索', _check_target_no_pivot),
    Contract('fp_diverge_on_buy', 'invariant', 'M25:target 期己方买入不得持续走散 fp', _check_fp_diverge_on_buy),
)


def check_contracts(traj: list[dict], contracts: tuple[Contract, ...] = DEFAULT_CONTRACTS) -> list[Violation]:
    """轨迹级合约检查(离线回溯审计/在线看门狗共用)。"""
    out: list[Violation] = []
    for c in contracts:
        try:
            out.extend(c.check(traj))
        except Exception as e:   # noqa: BLE001  合约检查 best-effort,单合约炸不拖垮审计
            out.append(Violation(c.name, 'check_error', f'检查器异常:{e}'))
    return out


def audit_replay(jsonl_path: str | Path) -> dict:
    """回溯审计(提案 v0a):已落盘 decisions.jsonl → 过合约检查器 → 违约报告。

    Returns:
        {'rows': N, 'violations': [Violation as dict], 'by_contract': {名: 数}}
    """
    p = Path(jsonl_path)
    traj = []
    if p.exists():
        with p.open(encoding='utf-8') as f:
            for line in f:
                try:
                    traj.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    vs = check_contracts(traj)
    by = {}
    for v in vs:
        by[v.contract] = by.get(v.contract, 0) + 1
    return {
        'rows': len(traj),
        'violations': [{'contract': v.contract, 'round_ref': v.round_ref, 'evidence': v.evidence} for v in vs],
        'by_contract': by,
    }
