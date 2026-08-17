"""策略发布层 v0(redesign 47 号;ADR-0195):PVS 世代戳 + 发布注册表 + 世代分层。

**诊断(47 号)**:切流 = 位翻(无灰度/无回滚/无隔离);15 seam 各自独立翻互相拆台;
语料无世代戳 → 线强度估计被「驾驶技术代际差」混杂毒化(不报错,只产生系统性偏置)。

**v0 落地**(纯函数,离线;47 号 §2.1/§2.4 + J0/J1 判据):
- ``PolicyVersionStamp``:世代三元组(代码哈希, seam 开关向量, 权重向量哈希)+
  配置快照哈希——强制 join 键(同 (前缀, PVS) ⇒ 同决策,46 号是此前提);
- ``ReleaseRegistry``:模块级发布态机(shadow → canary-ε% → promoted → rolled-back/
  quarantined)+ 跃迁证据包链接;
- ``generation_stratified_estimate``:线强度按 (线 × 世代) 分层 + 跨代偏移共享先验
  (世代效应=驾驶技术代际差,线效应=线本身——不可分问题变显式可估分解);
- J0(测试):合成语料注入世代效应 → 不分层估计 top-3 翻转、分层恢复真排序;
- J1 考古(脚本):git 历史重建语料世代数(本仓库实测)。

灰度切流协议(指派随机化/两级 canary/tripwire/自动回滚)的执行侧挂实机批次,
预注册语义在本层常量先行。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolicyVersionStamp:
    """策略世代戳(PVS):强制 join 键,审计「未打戳记录数」恒为 0。"""

    code_hash: str
    seam_vector: tuple[bool, ...]     # 15 维 seam 开关(模块固定序)
    weight_hash: str = ''
    config_hash: str = ''

    def stable_id(self) -> str:
        return f'{self.code_hash[:8]}-seam{sum(self.seam_vector):02d}-{self.weight_hash[:6]}'


# 发布态机词汇(封闭)
RELEASE_STATES = ('shadow', 'canary', 'promoted', 'rolled_back', 'quarantined')


@dataclass
class ReleaseRegistry:
    """模块级发布注册表:seam 之上的系统级视图(29 调度器的输入)。"""

    entries: dict[str, dict] = field(default_factory=dict)

    def transition(self, module: str, to_state: str, evidence: str = '') -> None:
        if to_state not in RELEASE_STATES:
            raise ValueError(f'非法发布态: {to_state}')
        prev = self.entries.get(module, {}).get('state', '(new)')
        self.entries[module] = {'state': to_state, 'evidence': evidence, 'prev': prev}

    def system_view(self) -> dict[str, str]:
        return {m: e['state'] for m, e in self.entries.items()}


def generation_stratified_estimate(runs: list[tuple[str, str, int, int]],
                                   pool_strength: float = 8.0) -> dict:
    """世代分层的线强度估计:输入 (line, generation, wins, plays) 聚合记录。

    模型:线效应 a_line + 世代偏移 b_gen(共享先验 N(0, τ_gen));v0 用两层收缩的
    简化形式——先估世代偏移(全代际均值差的收缩),线强度在「世代去偏后的胜场」上估。
    返回 {gen_offsets, line_strengths, ranking}(对照:不分层 ranking 也在,差异即
    被纠正的偏置量,J0 断言材料)。
    """
    # 世代偏移:每代总胜率 − 全局总胜率(收缩 pool_strength)
    gen_stats: dict[str, list[int]] = {}
    line_gen: dict[tuple[str, str], list[int]] = {}
    line_all: dict[str, list[int]] = {}
    for line, gen, w, p in runs:
        gen_stats.setdefault(gen, [0, 0])
        gen_stats[gen][0] += w
        gen_stats[gen][1] += p
        lg = line_gen.setdefault((line, gen), [0, 0])
        lg[0] += w
        lg[1] += p
        la = line_all.setdefault(line, [0, 0])
        la[0] += w
        la[1] += p
    gw = sum(v[0] for v in gen_stats.values())
    gp = sum(v[1] for v in gen_stats.values())
    g_mu = gw / max(1, gp)
    gen_offsets: dict[str, float] = {}
    for g, (w, p) in gen_stats.items():
        raw = (w / p - g_mu) if p else 0.0
        shrink = p / (p + pool_strength)
        gen_offsets[g] = round(shrink * raw, 4)

    # 去偏后线强度(胜场按世代偏移平移回公共基)
    line_adj: dict[str, list[float]] = {}
    for (line, gen), (w, p) in line_gen.items():
        la = line_adj.setdefault(line, [0.0, 0.0])
        la[0] += w - gen_offsets.get(gen, 0.0) * p
        la[1] += p
    strengths = {ln: round(v[0] / max(1, v[1]), 4) for ln, v in line_adj.items()}
    naive = {ln: round(v[0] / max(1, v[1]), 4) for ln, v in line_all.items()}
    ranking = sorted(strengths, key=lambda k: -strengths[k])
    naive_ranking = sorted(naive, key=lambda k: -naive[k])
    return {'gen_offsets': gen_offsets, 'line_strengths': strengths, 'ranking': ranking,
            'naive_ranking': naive_ranking, 'naive_strengths': naive}
