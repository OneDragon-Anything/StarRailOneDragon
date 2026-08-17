"""预案层 v0(redesign 22 号;ADR-0206):条件响应分支表 + 触发即执行承诺。

**诊断(22 号)**:摆振(姿态在门间拉扯)与僵住(该定不定)的根因 = 每门每回合
独立重评估,局部 eval 可反复否决全局正确的响应;13 号回溯 5016 行抓 56 处违约
(金零进展 38/钉死不 pivot 8/hp 毒化 10)。正确响应知识已存在(散在门与 ADR),
缺「触发即执行、不被局部信号再否决」的执行结构。人的协议成本从「事中每决策
打断」移到「开局一次批量批准」。

**v0 落地**(纯函数,离线;22 号 §2.1 核心):
- ``Branch``:trigger 谓词(开局可知+已有 reader 的输入)+ response 响应包
  (参数/模式切换,非单点动作)+ provenance 出处 + 修订门语义;
- ``Playbook``:10-20 条高利害分支(只收 M 案例/plaza 纪律句/用户权威级证据,
  防过拟合)+ 触发查询(命中即执行,该分支不再逐回合重评估);
- ``forward_check``:前向合约(触发未响应/未触发现响应 = 违约)——13 号前向
  合约的结构化载体;
- J1 覆盖率审计:56 处违约逐例映射「表内分支本可拦截?」(挂 M 语料回放批)。

批量批准 UI/局中执行接线/表-实对照 telemetry 挂实机批次。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BranchCondition:
    """触发谓词(受限输入:开局可知 + 已有 reader 的 GameState 字段)。"""

    field: str          # 'hp' / 'gold' / 'plane' / 'round_num' / 'level' / 'streak'
    op: str             # 'lt' / 'gt' / 'eq'
    value: float = 0.0
    extra_field: str = ''       # 第二条件(如 nodes_left)
    extra_op: str = ''
    extra_value: float = 0.0


@dataclass(frozen=True)
class Branch:
    """一条预授权响应(触发即执行;修订须走预注册证据判决,不静默漂移)。"""

    branch_id: str
    trigger: BranchCondition
    response: str               # 响应包描述(参数/模式切换;非单点动作)
    provenance: str             # 'M案例' / '用户权威' / 'plaza纪律' / '17号派生'
    response_kind: str = 'posture_override'   # posture_override/param_shift/bail_routine


def _cond_ok(c: BranchCondition, state) -> bool:
    """谓词判定(r2 review#3:非法 op 字典直查 KeyError → .get 带 False 兜底)。"""
    v = getattr(state, c.field, None)
    if v is None:
        return False
    ok = {'lt': v < c.value, 'gt': v > c.value, 'eq': v == c.value}.get(c.op, False)
    if ok and c.extra_field:
        ev = getattr(state, c.extra_field, None)
        if ev is not None:
            ok = {'lt': ev < c.extra_value, 'gt': ev > c.extra_value,
                  'eq': ev == c.extra_value}.get(c.extra_op, False)
    return ok


@dataclass
class Playbook:
    """一局的预授权分支表(开局 briefing 后生成;触发即执行)。"""

    branches: list[Branch] = field(default_factory=list)
    fired: dict[str, int] = field(default_factory=dict)   # branch_id → 触发次数
    _fired_once: set[str] = field(default_factory=set)    # r2#3:已触发抑制( fired 计真实首触)

    def match(self, state) -> Branch | None:
        """查询**未触发过**的首个命中分支(r2#3:触发即执行承诺 = 每分支只 fire 一次;
        已 fire 分支不再重复返回——fired 是触发计数非轮询计数,表-实对照不污染)。"""
        for b in self.branches:
            if b.branch_id in self._fired_once:
                continue
            if _cond_ok(b.trigger, state):
                self.fired[b.branch_id] = self.fired.get(b.branch_id, 0) + 1
                self._fired_once.add(b.branch_id)
                return b
        return None

    def forward_violations(self, fired_branch: Branch | None,
                           actual_response: str) -> list[str]:
        """前向合约检查(13 号载体):fired 分支的 response 与实际响应比对。

        调用序:每回合先 match() 得 fired_branch(可能 None),把策略实际执行的
        response_kind 传入。违约两类:触发未响应(fired 非 None 但 actual 不符)/
        未触发现响应(actual 是 posture_override 但无 fired)。
        """
        out: list[str] = []
        if fired_branch is not None and actual_response and \
                actual_response != fired_branch.response_kind:
            out.append(f'触发未响应:{fired_branch.branch_id} 期望 {fired_branch.response_kind} 实际 {actual_response}')
        if fired_branch is None and actual_response == 'posture_override':
            out.append(f'未触发现响应:{actual_response}(无 fired 分支的 posture 覆写来源?)')
        return out


# ===== 初始条目(手写门降级为表初始条目;出处标注) =====
# 用户权威五条/plaza 纪律句/M 案例的高利害响应;阈值待分布校准(J1 批)。
INITIAL_PLAYBOOK: tuple[Branch, ...] = (
    Branch('blood_emergency', BranchCondition('hp', 'lt', 30),
           '弃追三+搜牌等级降档+经济模式→保血(应急:允许弃表走现状栈)',
           provenance='M案例(金零进展38处)', response_kind='posture_override'),
    Branch('streak_guard', BranchCondition('streak', 'gt', 1),
           '连胜≥2:锁血凑齐阵容(保连胜>吃息)', provenance='plaza纪律',
           response_kind='posture_override'),
    Branch('boss_pre_clear', BranchCondition('plane', 'eq', 2,
                                             extra_field='gold', extra_op='gt',
                                             extra_value=60),
           '进 boss 前花尽清算(超 60 金 P2 边界)', provenance='17号派生',
           response_kind='param_shift'),
    Branch('p3_encounter_low', BranchCondition('plane', 'eq', 3),
           'P3 遭遇恒低难度(ADR-0130)', provenance='M案例',
           response_kind='posture_override'),
)


def build_initial_playbook() -> Playbook:
    """开局生成初始表(briefing 后;批量批准卡 = 本表整体呈现)。"""
    return Playbook(branches=list(INITIAL_PLAYBOOK))
