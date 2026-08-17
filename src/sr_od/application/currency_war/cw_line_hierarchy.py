"""线强度层级池化引擎 v0(redesign 37 号;ADR-0179)。

**诊断(37 号)**:线强度(全栈核心潜变量)由 05(臂 Beta)/20(预注册先验)/21(Line 后验)
三处独立维护、逐线独立更新 —— A8 一局 25-35min、20 条线 = 每线永远小样本;plaza 先验靠
「封顶 ≤8」钝器压制;版本 bump 全清零。

**v0 落地**(纯函数,离线;37 号 §2 最小闭环):
- ``LineLevel``/``HierarchySpec``:两级层级(原型 → 线;L1 挂 trait 网格不挂聚类 id,聚类只是 L2 索引);
- ``fit_tau``:经验贝叶斯矩估计组间异质 τ(可借力强度);τ→0 = 线间无结构 → 平先验独立模式(=现状,降级链);
- ``pooled_posterior``:Beta-Binomial 收缩(线观测 + 原型借力 → 后验等效样本提升);
- ``version_shock``:版本 bump 信念时序(叶向结构收缩重置、结构慢衰减存活、冲击量从历次 bump 学);

消费端换源(05 臂先验/20 预注册先验/21 Line init)走影子开关批次;J1 合成恢复/J2 版本冲击
判据全离线(见测试)。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LineObs:
    """单线的累计观测(充分统计量形态)。"""

    line: str
    wins: int = 0
    plays: int = 0
    adherence: float = 1.0   # 局照线打的程度(05 号加权;0=完全没照打不算证据)


@dataclass
class HierarchySpec:
    """两级层级定义:L1 原型(结构网格:羁绊族×费用带×carry 职能)→ L2 线。"""

    prototype_of: dict[str, str]          # line → prototype(L1 分组)
    tau: float = 0.0                      # 组间异质(可借力强度;fit_tau 估)
    version_decay: float = 0.15           # 版本 bump 结构慢衰减(每 bump 衰减比例)
    # 拟合产物(经验贝叶斯)
    prototype_prior: dict[str, tuple[float, float]] = field(default_factory=dict)
    # (α, β) 每原型超先验(结构层)


def line_effective(obs: LineObs) -> tuple[float, float]:
    """线观测 → 等效 (wins, plays)×adherence(adherence 加权:局没照线打就打折)。"""
    eff_plays = obs.plays * max(0.0, min(1.0, obs.adherence))
    eff_wins = obs.wins * max(0.0, min(1.0, obs.adherence))
    return eff_wins, eff_plays


def fit_tau(spec: HierarchySpec, obs_list: list[LineObs],
            prior_strength: float = 8.0) -> HierarchySpec:
    """经验贝叶斯矩估计:原型超先验 + 组间异质 τ(方法矩,无 MCMC)。

    τ 语义:原型内线真胜率的分散度。τ 大 → 线间异质强 → 少借;τ≈0 → 同原型线可视为
    同一真值 → 全借(平先验)。prior_strength = 超先验等效样本(结构层先验强度,
    plaza 超先验数据接入前的保守默认)。
    """
    by_proto: dict[str, list[LineObs]] = {}
    for o in obs_list:
        p = spec.prototype_of.get(o.line)
        if p is None:
            continue
        by_proto.setdefault(p, []).append(o)
    proto_prior: dict[str, tuple[float, float]] = {}
    # 组间方差(原型均值的分散)→ τ 粗估
    proto_means, weights = [], []
    for p, os_ in by_proto.items():
        if len(os_) < 2:
            continue   # 单线原型无兄弟可借(借自己=虚增置信)→ 不登记,该线走独立模式
        w = sum(o.plays * max(0.0, min(1.0, o.adherence)) for o in os_)
        k = sum(o.wins * max(0.0, min(1.0, o.adherence)) for o in os_)
        if w <= 0:
            continue
        m = k / w
        # 二项噪声修正:减去组内采样方差贡献(欠采样组的均值分散含纯噪声)
        binom_var = m * (1 - m) / max(w, 1.0)
        proto_means.append((m, binom_var, w, p))
        weights.append(w)
    if not proto_means:
        spec.tau = 0.0
        spec.prototype_prior = {}
        return spec
    mbar = sum(m * w for m, _bv, w, _p in proto_means) / sum(weights)
    var_raw = sum(w * (m - mbar) ** 2 for m, _bv, w, _p in proto_means) / sum(weights)
    noise = sum(w * bv for _m, bv, w, _p in proto_means) / sum(weights)
    tau2 = max(0.0, var_raw - noise)
    spec.tau = tau2 ** 0.5
    for m, _bv, w, p in proto_means:
        # 超先验:均值 m、强度截到 prior_strength(保守:不被大原型完全主导)
        k_eff = min(w, prior_strength)
        proto_prior[p] = (max(1.0, m * k_eff), max(1.0, (1 - m) * k_eff))
    spec.prototype_prior = proto_prior
    return spec


def pooled_posterior(spec: HierarchySpec, obs: LineObs) -> tuple[float, float]:
    """收缩更新:线观测 + 原型借力 → Beta 后验 (α, β)。

    借力量 κ = f(τ):τ→0 全借(κ=∞ 退化为原型先验)、τ 大少借。κ = prior_strength / (τ·C)
    的简化形式:C=10 标定(τ=0.1 → κ=80 强借;τ=0.3 → κ≈27;τ≥0.5 → κ<16 弱借)。
    无原型登记/无组数据 → 平先验 + 自家观测(=现状独立模式,降级链)。
    """
    eff_w, eff_p = line_effective(obs)
    alpha = 1.0 + eff_w
    beta = 1.0 + max(0.0, eff_p - eff_w)
    proto = spec.prototype_of.get(obs.line)
    if proto is None:
        return alpha, beta
    pa = spec.prototype_prior.get(proto)
    if pa is None:
        return alpha, beta
    tau = max(0.0, spec.tau)
    # τ≈0:同原型可视为同真值 → 强借(保守夹借力样本 ≤60)
    kappa = 60.0 if tau < 1e-6 else min(60.0, max(0.0, 8.0 / (tau * 10.0)))
    a_borrow, b_borrow = pa
    # 归一借力到 κ 等效样本,按原型均值方向分配
    p_mean = a_borrow / max(a_borrow + b_borrow, 1e-9)
    alpha += kappa * p_mean
    beta += kappa * (1 - p_mean)
    return alpha, beta


def version_shock(spec: HierarchySpec, obs_list: list[LineObs],
                  shock_scale: float | None = None) -> dict[str, tuple[float, float]]:
    """版本 bump 信念时序:叶向结构收缩重置(非清零)、结构慢衰减存活。

    返回每线 bump 后先验 (α, β):自家观测按 decay 收缩 + 原型借力重注
    (shock_scale 从历次 bump 学为 v1;v0 用默认 decay=version_decay)。"""
    out: dict[str, tuple[float, float]] = {}
    decay = spec.version_decay if shock_scale is None else shock_scale
    for o in obs_list:
        eff_w, eff_p = line_effective(o)
        w_s = eff_w * (1.0 - decay)
        p_s = eff_p * (1.0 - decay)
        a, b = pooled_posterior(spec, LineObs(o.line, w_s, p_s, adherence=1.0))
        out[o.line] = (a, b)
    return out
