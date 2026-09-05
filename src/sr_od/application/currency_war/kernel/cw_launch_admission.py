"""达标臂发射面的纯逻辑准入核(自 cw_loop/cw_op_deploy 迁出的单一实现)。

为什么在 kernel:发射面观测(sim/engine_p1 的 LaunchBattle 建模)需要
直调生产 G1 准入判据,而包依赖矩阵(sim 桶不可依 app/operations 桶,
test_cw_package_layout LEGAL_EDGES)禁止 sim→cw_loop 直引。本模块只依
kernel(cw_line_defs/cw_state)与 data 注册表,三方消费面(sim 引擎/
cw_loop 调用面/测试)共用同一实现,零第二份。

victim 资格单一源 = offtarget_sell_allowed fenced 臂全条件(判据语义
见其 docstring,自 cw_op_deploy 迁出未改动);cw_op_deploy 保留同名
re-export,既有消费路径(生产 deploy 卖出臂/测试)零迁移。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS as _ENGINE_FENCE,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    RECIPE_FACTIONS as _RECIPE,
)

# 部署围栏集 = RECIPE ∪ ENGINE(桥派生单一源 = cw_line_defs;r357 收口:
# 围栏必须随桥派生集走,局部 frozenset 双源已被 r271 批清退)。
# cw_op_deploy._DEPLOY_FENCE 自本常量别名(消费路径兼容,实现单一)。
DEPLOY_FENCE: frozenset[str] = frozenset(_RECIPE | _ENGINE_FENCE)


def offtarget_sell_allowed(char_id: str, bonds: set[str],
                           target_factions: set[str],
                           target_cores: set[str], *,
                           fenced_offline_sellable: bool = False,
                           protect_names: frozenset[str] = frozenset()
                           ) -> bool:
    """W209/ADR-0386:off-target 卖出候选判据(纯函数,锁测试面)。

    run 26 实锤(崩坏根因②):P2 定型后 deploy 侧只按终局 ``target_comp`` 判
    off-target,把买/演进层仍在买入的引擎·配方体系件(仙舟三人组:藿藿×3/
    饮月×2/爻光×1)反复卖出——同期商店 plan 不停 ``Buy(仙舟/...)`` = 买→卖→买
    振荡(两层目标视图分歧:deploy 看终局 comp,买/演进层看意向体系对/骨架纪律)。
    振荡熔断:**引擎/配方体系件(``DEPLOY_FENCE`` = RECIPE ∪ ENGINE,与散牌
    围栏同源)恒不卖**——deploy 自己都把它们当围栏件不许留 bench,卖出判定不得
    同源反向。真要换血走演进层显式 SellDeployed/CompTransaction(有保护集分级,
    ADR-0382),不归 deploy 的机会性腾位通道管。

    换阵卖出义务臂(板满换阵死锁修复;第七局 r9 实证):
    ``fenced_offline_sellable=True`` 时,off-line 的引擎/配方件(**bonds ∌
    target、∉ protect_names**)让位可卖。依据:熔断防的振荡前提 =「买/演进层
    仍在买入该体系件」;线已成型(fp=1.00,单一源 ``cw_comps.form_progress``)
    后买侧对旧线 fenced 件已无需求,保留保护只剩闭死腾位通道的副作用
    (艾丝妲=旧线持续伤害/黑塔被护 → sold 0/2 → RunDeploy 单签名守卫停机)。
    ``protect_names`` = 新线 core∪shared(禁卖护栏不因换阵解除,P41②口径;
    core 件本就被 ``target_cores`` 挡,shared 件经本参显式兜住)。target 单位
    判定(阵营/流派交集)在两臂下都不变。
    """
    if char_id and (char_id in target_cores or char_id in protect_names):
        return False   # core/新线 core∪shared 保留(live 花火误卖根由;P41②)
    if bonds & target_factions:
        return False   # target 单位,保留
    if fenced_offline_sellable:
        return True    # 换阵卖出义务臂:off-line 引擎/配方件让位(线已成型)
    # 引擎/配方体系件恒不卖(W209 振荡熔断,ADR-0386)
    return not (bonds & DEPLOY_FENCE)


def protect_names_of(comp) -> frozenset[str]:
    """换阵卖出义务臂的保护域(新线禁卖集)= core∪shared∪替班者全集。

    替班者腿依据 = ``Comp.substitute_plan`` 字段契约原文「替班=『不卖、
    转副C沉淀』」(cw_comps)——卖替班者本就违替班语义。仅 core∪shared
    时存在保护域缺口:替班者凭 substitute_plan 直入买面义务集
    (``locked_buy_membership`` → ``_line_hoard``),不经任何羁绊检查,
    可对 comp 整体 off-line 且 fenced(P59 注册表反例:黄泉减益×卡芙卡,
    bonds={持续伤害,星核猎手} ∩ all_factions=∅)→ 义务臂判可卖,同一
    身份 M2 义务买 ↔ 换阵臂卖 = 买↔卖振荡。新增替班者自动入保护域。
    """
    names = set(getattr(comp, 'core_chars', []) or []) \
        | set(getattr(comp, 'shared_chars', []) or [])
    for sub in getattr(comp, 'substitute_plan', None) or []:
        name = sub.get('替班者') if isinstance(sub, dict) else None
        if name:
            names.add(name)
    return frozenset(names)


def launch_admission_report(state, comp, *, line_members) -> dict:
    """达标臂 G1 准入预估(§9.2 准入三元 + victim 收口,发射面显影用)。

    返回 dict(全 bool):``board_full``(三元①板满:占用部署数 ≥ 物理
    槽位总数 DEPLOYED_CAPACITY(前后排定长槽表),feed 单一源 =
    deployed_occupied)、``bench_core_waiting``(三元②:bench 存在线内
    待上场件——口径 = core∪shared(line_members)∨ 阵营交集,
    与买入/部署义务面对齐)、``victim_missing``(三元③:板上无合格
    victim)。

    victim 资格单一源 = offtarget_sell_allowed fenced 臂全条件(off-line
    ∧ 围栏 ∧ 非保护域,保护域 = core∪shared∪替班者),与执行侧
    _sell_offtarget_deployed 同款;**不附 1★ 全退门**——执行侧 swap 卖出
    无退款资格前置,提案侧多一道门只会造成 victim_missing 误显影。
    提案侧预估基于期望态现读;执行时刻以 CwOpDeploy 现读重建为准。
    三元不全/victim 缺失**只显影不拦截**(出战优先;准入是观测面,
    非第二道闸)。

    :param line_members: 线成员谓词(注入参;单一源 =
        strategies.impl.mandate_v1.statefn.predicates.line_members——
        本模块在 kernel 桶,包依赖矩阵禁 kernel→strategies 直引,由
        调用方注入同一函数对象,禁各调用面自写第二实现)。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_state import (
        DEPLOYED_CAPACITY,
        deployed_occupied,
    )
    deployed = [d for d in (state.deployed or []) if d is not None]
    bench = [b for b in (state.bench or []) if b is not None]
    cores = set(getattr(comp, 'core_chars', []) or [])
    line = set(line_members(comp))
    protect = protect_names_of(comp)
    t_factions = set(getattr(comp, 'all_factions', []) or [])
    board_full = deployed_occupied(state.deployed or []) >= DEPLOYED_CAPACITY
    bench_core_waiting = False
    for b in bench:
        name = b.char_id or ''
        if name in line:
            bench_core_waiting = True
            break
        ch = get_char(name)
        if ch is not None and (set(ch.factions) | set(ch.flows)) & t_factions:
            bench_core_waiting = True
            break
    victim_missing = True
    for d in deployed:
        name = d.char_id or ''
        if not name or name in cores or name in protect:
            continue
        ch = get_char(name)
        if ch is None:
            continue
        bonds = set(ch.factions) | set(ch.flows)
        if not offtarget_sell_allowed(name, bonds, t_factions, cores,
                                      fenced_offline_sellable=True,
                                      protect_names=protect):
            continue
        victim_missing = False
        break
    return {'board_full': board_full, 'bench_core_waiting': bench_core_waiting,
            'victim_missing': victim_missing}
