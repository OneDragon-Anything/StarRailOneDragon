"""战略假设审判层 v0(20 号提案;ADR-0171;2026-08-16)。

**诊断(20 号)**:五族战略去留门(commit FRAC/ROUND 双轨、pivot GAP_FLOOR+streak 解锁、
drought 计数、roll 停手、3★ 追逐**无机制**)是同一个统计检验——「不完全观测下证据是否
足以否定当前战略假设」——的五种手工近似,六代补丁化石(D-90/🟡6/0147/drought brake);
两类错误同局双发(M38 既有 fp<0.4 永不 commit 又有 4 次 pivot = 无统一判决机制最硬证据);
M22「再等等说不定来了」的合理化拖延无表示可拦。

**v0 落地**(core 纯函数,提案 §2.3+S;消费端逐口切流后续):
- ``LineHypothesis``:预注册假设(证据通道 × 期望曲线 × 检查点 × deadline)+ 证据账本
  (只追加,判决可整体回放);**登记即冻结判据**——不许用新理由事后合理化;
- ``evidence_lr``:多通道似然比合并(**保守合并 min 而非乘积**——通道相关性未知时防
  双计高估,显式保守条款);
- ``decision_threshold``:门限由两侧错误代价定价——K = C(错弃)/C(错守),代价结构从
  已落模块推导(06 交互值+17 转线成本 vs 18 λ_hp×掉队节点+03 金边际),非魔法常数;
- ``verdict``:三态判决(守/弃/**amended**——现五门表达不了的中间判决:M32「线对但窗口
  该停」正缺它);血健康→门宽多守,边缘区→早弃(18 的输出是本层输入);
- ``HypothesisRegistry``:登记簿(commit/开窗/起追逐时登记;逐节点序贯更新)。

与 13 号对称闭环:13 判行为是否违背声明(ex-post),本层判声明该不该被证据推翻(ex-ante
前向);审判记录是 13 的新合约语料。J1 影子回放(13 号管线复用)与 J2 注入(sim_env)
为切流判据,待消费端接线窗口。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LineHypothesis:
    """一条预注册的战略线假设。"""
    hyp_id: str
    line: str                        # 目标线(comp 名/家族/追逐单位)
    kind: str                        # 'commit' | 'search_window' | 'star_chase' | 'transition'
    checkpoints: list[int]           # 检查点节点(期望进度在此验收)
    deadline: int                    # deadline 节点(到此后验不够 → 自动弃,防拖延)
    expected: dict[int, float]       # 期望进度曲线 p(t)(plaza 实证导出;节点→进度)
    # 判决门限(登记时定价;随局面每节点重算由 verdict 的 cost 参数承担)
    registered_at: int = 0
    ledger: list[tuple] = field(default_factory=list)   # [(node, 通道, 观测, lr)]

    def add_evidence(self, node: int, channel: str, obs: str, lr: float) -> None:
        """证据入账(只追加;LR = P(证据|线死)/P(证据|线活),>1 指向死)。"""
        self.ledger.append((node, channel, obs, lr))

    @property
    def cumulative_lr(self) -> float:
        """账本合成:**保守合并 min(累计逐通道 LR)而非乘积** —— 通道相关(池缺席与
        时间线掉队同受 rival 驱动)时乘积双计高估证据强度 → 过度弃。显式保守条款。"""
        by_channel: dict[str, float] = {}
        for _n, ch, _o, lr in self.ledger:
            by_channel[ch] = by_channel.get(ch, 1.0) * max(lr, 1e-6)
        if not by_channel:
            return 1.0
        return min(by_channel.values())

    def progress_lag(self, node: int, actual: float) -> float:
        """时间线掉队量(期望曲线 − 实际;检查点上取)。"""
        exp = self.expected.get(node)
        return max(0.0, (exp - actual)) if exp is not None else 0.0


def evidence_lr(channel_lrs: dict[str, float]) -> float:
    """多通道 LR 合并入口(独立函数形态,消费端/测试用;保守 min)。"""
    if not channel_lrs:
        return 1.0
    return min(max(v, 1e-6) for v in channel_lrs.values())


def decision_threshold(cost_abandon: float, cost_hold: float) -> float:
    """Wald 式判决门限 K = C(错弃)/C(错守)。

    cost_abandon(错弃):沉没交互值(06)+ 转线重入成本(17 formation_cost 差);
    cost_hold(错守):λ_hp×掉队期望掉血(18)+ 金边际(03)。血健康 → C(hold) 低 →
    K 大 → 门宽多守;边缘区 → K 小 → 早弃。**门限从代价结构推导,非手调常数**。
    """
    if cost_hold <= 1e-9:
        return 1e9   # 错守几乎免费(血满金足)→ 永不弃
    return max(0.01, cost_abandon / cost_hold)


@dataclass
class Verdict:
    """三态判决 + 可解释理由。"""
    action: str        # 'hold' | 'abandon' | 'amended'
    lr: float
    threshold: float
    reason: str


def verdict(hyp: LineHypothesis, node: int, *, cost_abandon: float, cost_hold: float,
            amendment_lr: float | None = None) -> Verdict:
    """序贯判决:LR vs 门限;三态(守/弃/amended)。

    amended:LR 落在 [0.5×K, K) 区间——证据偏负但不足弃,改附着计划(关窗/停追逐)
    不改线;M32「线对但窗口该停」的中间判决。deadline 到而 LR 不足 → 强制弃(防
    「再等等」的病理性拖延,预注册语义)。
    """
    lr = hyp.cumulative_lr
    k = decision_threshold(cost_abandon, cost_hold)
    if amendment_lr is not None:
        # 调用方提供的 amended 专属 LR(如关窗判据);None → 用 0.5K 默认带
        if lr >= k:
            return Verdict('abandon', lr, k, f'LR={lr:.1f} ≥ K={k:.1f}(错弃代价 {cost_abandon:.1f}/错守 {cost_hold:.1f})')
        if lr >= amendment_lr:
            return Verdict('amended', lr, k, f'LR={lr:.1f} 落 amended 带(≥{amendment_lr:.1f})——线活但附着计划该改(关窗/停追逐)')
        return Verdict('hold', lr, k, f'LR={lr:.1f} 证据不足以动线(门 K={k:.1f})')
    if lr >= k:
        return Verdict('abandon', lr, k, f'LR={lr:.1f} ≥ K={k:.1f}(错弃代价 {cost_abandon:.1f}/错守 {cost_hold:.1f})')
    if lr >= 0.5 * k:
        return Verdict('amended', lr, k, f'LR={lr:.1f} 落 amended 带(0.5K={0.5 * k:.1f})——不改线,改附着计划')
    if node >= hyp.deadline and lr > 1.0:
        return Verdict('abandon', lr, k, f'deadline={hyp.deadline} 到且 LR>1(预注册防拖延:判据冻结时已含此门)')
    return Verdict('hold', lr, k, f'LR={lr:.1f} < 0.5K(证据弱,守)')


class HypothesisRegistry:
    """线假设登记簿(登记即冻结判据;逐节点序贯判决)。"""

    def __init__(self) -> None:
        self.active: dict[str, LineHypothesis] = {}

    def register(self, hyp: LineHypothesis) -> None:
        self.active[hyp.hyp_id] = hyp

    def judge_all(self, node: int, cost_abandon: float, cost_hold: float) -> dict[str, Verdict]:
        return {hid: verdict(h, node, cost_abandon=cost_abandon, cost_hold=cost_hold)
                for hid, h in self.active.items()}

    def close(self, hyp_id: str) -> None:
        self.active.pop(hyp_id, None)
