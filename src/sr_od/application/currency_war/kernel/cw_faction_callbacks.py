"""货币战争 值域回调级联(deployed 逻辑写尾的阵营触发判据级联;判据/登记/簿记

回调挂 **deployed 值变更**(非动作)——部署/卖出/替换/合成落场/穿戴,
凡改场上名单或装备,同一套回调;判据只看「值从什么变成什么」。观察写
零回调(观察 = 重锚已发生的事实与纠偏,reactive 兜底);挂点单一 =
``GameState._write_logic_frame`` 的 deployed 分支尾(logic/logic_rand
两逻辑通道同经,获得链递归每步语义完整)。

回调族(固定位置参数,用户裁定):
- ``on_units_changed(gs, added_units, removed_units, source)``:按名
  diff 的成员增/减(事件通知层);
- ``on_equips_changed(gs, changed_pairs, source)``:同名存活单位
  (旧,新) 对中 equips 有差者(事件通知层);
- ``on_qualification_changed(gs, old_sets, new_sets, source)``:盯的
  资格名集(弹窗两阵营 + 伙伴 + ENV_BOND_TIER_GRANTS 羁绊,注册表
  驱动)旧/新(派生存值)→ 判 S1a 跨档 / S1b 巨星重选 / S2 伙伴;
- ``on_star_changed(gs, old_star, new_star, source)``:场上银狼星级
  (派生存值,无/1/2/3)→ 判 S3 planner;
- ``check_env_bond_tier_grants(gs, new_sets, source)``:羁绊档位条件
  发放判据(ENV_BOND_TIER_GRANTS 注册表驱动;挂 deployed 写尾**门外**
  必查,电平 + 每档一次性 done 封账,发放原语住 cw_env_grants)。

资格集与羁绊计数字段(board)分立:资格集 = 名集合(判据面;出身 ∨
持徽,贡献单一源 cw_bond_equips.unit_bond_tags,开拓者按排形态);
board = 多集口径(卡带系多计,策略消费口)——两者非视图关系。

判据簿记(住 cw_overlay_register.ScreenChanges sidecar):
巨星跨档无簿记(每次上穿即弹,降档再升也弹——用户裁定);祈愿首达档
一次;planner 每费用档一次;伙伴无上限;占卜屋住 S4 上报点(本模块外)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        Unit,
    )

#: 盯的阵营 → 跨档弹窗 kind(注册表驱动小表
#: 「判据归位」表:阵营→弹窗映射 + FACTIONS 档位表,零硬编码档线)。
#: 盛会之星 = 纯上穿无簿记;命运圣杯 = 首达档一次(簿记分键见下)。
_FACTION_POPUP_KINDS: dict[str, str] = {
    '盛会之星': 'megastar',
    '命运圣杯': 'wish_trial',
}

#: S2 伙伴判据的在场前提角色(列车同行核心; §1.2
#: 用户裁定「姬子·启行在场 ∧ 另有成员」)。
_PARTNER_ANCHOR_CHAR: str = '姬子·启行'

#: S2 伙伴的阵营名。
_PARTNER_FACTION: str = '列车同行'

#: S3 planner 的星级跟踪角色(银狼 LV.999;与 deploy_move 升费分支/
#: lv999_cost_tier 同名同源;场上同名唯一 =  裁决 1 已登记守卫)。
_PLANNER_CHAR: str = '银狼LV.999'

#: S1b 巨星重选的首档门槛(盛会之星 tiers 首档 = 2;用户裁定:场上
#: 只剩一个/零个盛会之星角色不弹)。
_MEGASTAR_FIRST_TIER: int = 2


def _iter_field_units(view) -> list[tuple[str, Unit]]:
    """视图 → (排, Unit) 占用清单(排 = 子表名,开拓者形态归一的
    判据输入;空槽跳过)。"""
    if view is None:
        return []
    out: list[tuple[str, Unit]] = []
    for row, sub in (('front', view.front_slots or []),
                     ('back', view.back_slots or [])):
        for u in sub:
            if u is not None:
                out.append((row, u))
    return out


def _qualification_sets(view) -> dict[str, set[str]]:
    """视图 → 盯的资格名集(派生存值;注册表驱动扩容)。

    资格 = 出身 ∨ 持该阵营星徽(装备贡献单一源 = cw_bond_equips.
    unit_bond_tags:出身/卡带/星徽全量口径;名不在注册表/未知 → 零标签,
    该名对所有阵营无资格)。开拓者按所在排形态(
    「资格集语义」节)。选边型双羁绊角色(布洛妮娅,
    cw_chars.SIDE_PICK_DUAL_BONDS)标签经 peers 透传选边单边化 →
    其资格集自动单边(计入边一侧有资格、另一侧无)。

    watched = 弹窗两阵营 + 伙伴 + ENV_BOND_TIER_GRANTS 羁绊(羁绊档位
    发放判据要按资格计数判档,资格集一并盯;扩容零干扰 = 既有 S1a/
    S1b/S2 判据只读各自阵营,不读本扩容集)。
    """
    from sr_od.application.currency_war.kernel.cw_bond_equips import (
        unit_bond_tags,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_BOND_TIER_GRANTS,
    )
    watched = [*_FACTION_POPUP_KINDS, _PARTNER_FACTION]
    for _bond, _equip in ENV_BOND_TIER_GRANTS.values():
        if _bond not in watched:
            watched.append(_bond)
    sets: dict[str, set[str]] = {f: set() for f in watched}
    # 选边型双羁绊角色(布洛妮娅)经 peers 透传按图鉴逻辑单边计入——
    # 标签单边化后其资格集自动单边(同聚合单一源口径)。
    units = list(_iter_field_units(view))
    for row, u in units:
        tags = unit_bond_tags(u, row=row,
                              peers=[u2 for _r2, u2 in units if u2 is not u])
        for f in watched:
            if f in tags:
                sets[f].add(str(u.char_id))
    return sets


def _planner_star(view) -> int | None:
    """场上银狼 LV.999 星级(派生存值;不在场 = None)。

    场上同名唯一(裁决 1 入口守卫已登记)⇒ 至多一值;防御性取首见。
    """
    for _row, u in _iter_field_units(view):
        if str(u.char_id) == _PLANNER_CHAR:
            return int(u.star)
    return None


def _diff_by_name(old_view, new_view
                  ) -> tuple[list, list, list]:
    """一次 deployed 写按名分解三类事件(
    语义」节):成员增(名新现)/ 成员减(名消失)/ 存活对(同名且
    (星, equips,排面) 有差的 (旧单位,新单位) 对——名含排面时
    开拓者换形态按名消失+名新增进前两类,资格集总对比仍正确)。"""
    old_by_name: dict[str, tuple[str, Unit]] = {
        str(u.char_id): (row, u) for row, u in _iter_field_units(old_view)}
    new_by_name: dict[str, tuple[str, Unit]] = {
        str(u.char_id): (row, u) for row, u in _iter_field_units(new_view)}
    added = [u for n, (_r, u) in new_by_name.items() if n not in old_by_name]
    removed = [u for n, (_r, u) in old_by_name.items() if n not in new_by_name]
    changed: list[tuple[Unit, Unit]] = [
        (old_by_name[n][1], u) for n, (_r, u) in new_by_name.items()
        if n in old_by_name and old_by_name[n][1] != u]
    return added, removed, changed


def on_units_changed(gs, added_units, removed_units, source: str) -> None:
    """角色变动回调(事件通知层:喂资格集——资格集在派生维护入口
    按视图总量对算,本层 = 契约 seam,未来成员类消费面挂点)。"""
    # 通知层无独立判据(回调表口径:overlay 判据不住此)。
    return


def on_equips_changed(gs, changed_pairs, source: str) -> None:
    """装备变更回调(事件通知层:喂资格集;其他装备消费面留位)。"""
    return


def on_qualification_changed(gs, old_sets, new_sets, source: str) -> None:
    """资格集变更回调 → S1a 跨档 / S1b 巨星重选 / S2 伙伴判据
    (全部资格集判据,判据归位 = 值回调单一源)。"""
    # —— S1a 档位跨越:有弹窗的阵营资格集大小上穿任一档线,单写至多
    #    一次。无来源排除(合成继承星徽致跨档同弹;经典合成名集合不变
    #    天然不进本回调)。巨星 = 纯上穿无簿记(降档再升也弹,用户裁定);
    #    祈愿 = 首达档一次(降档再回不弹,簿记分键)。
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        KIND_SCREEN_NAMES,
        register_screen_change,
    )
    for faction, kind in _FACTION_POPUP_KINDS.items():
        old_n = len(old_sets.get(faction, ()))
        new_n = len(new_sets.get(faction, ()))
        crossed = [t for t in FACTIONS[faction].tiers
                   if old_n < t <= new_n]
        if not crossed:
            continue
        if kind == 'wish_trial':
            fresh = [t for t in crossed
                     if t not in gs.screen_changes.wish_tiers_fired]
            if not fresh:
                continue   # 降档再回:档已弹过,不弹(用户裁定)
            gs.screen_changes.wish_tiers_fired.update(fresh)
        register_screen_change(
            gs, kind, KIND_SCREEN_NAMES[kind],
            source=f's1a_upcross:{faction}@{source}')

    # —— S1b 巨星重选:chosen_megastar 跌出盛会之星资格集(名消失 或
    #    卸徽致出身∨持徽两失)∧ 写后资格计数仍达首档(用户裁定)。
    chosen = gs.chosen_megastar.value
    if chosen:
        _ms = '盛会之星'
        if chosen in old_sets.get(_ms, ()) \
                and chosen not in new_sets.get(_ms, ()) \
                and len(new_sets.get(_ms, ())) >= _MEGASTAR_FIRST_TIER:
            register_screen_change(
                gs, 'megastar', KIND_SCREEN_NAMES['megastar'],
                source=f's1b_reselect@{source}')

    # —— S2 伙伴:列车同行资格集元素增减(无来源排除;合成继承获资格
    #    同弹,经典合成集合不变天然不弹)∧ 写后前提现读(姬子·启行
    #    在场 ∧ 另有成员)。
    _pf = _PARTNER_FACTION
    if old_sets.get(_pf) != new_sets.get(_pf):
        _ns = new_sets.get(_pf, set())
        if _PARTNER_ANCHOR_CHAR in _ns and len(_ns) >= 2:
            register_screen_change(
                gs, 'partner', KIND_SCREEN_NAMES['partner'],
                source=f's2_member_change@{source}')


def on_star_changed(gs, old_star, new_star, source: str) -> None:
    """星级回调 → S3 planner 判据:新值 ≥ 2 ∧ 该费用档未弹过
    (旧值无关——覆盖无→2 / 1→2 / 无→3[暂按会弹,实机复核标注 =
     §4]/ 2→3 不弹[档已弹];口径同上
    值域回调级联表)。费用档读 ``gs.lv999_cost_tier``(未观察 None =
    语义起始档 3,与 cw_economy.effective_cost 同缺省口径)。"""
    if new_star is None or new_star < 2:
        return
    tier = int(gs.lv999_cost_tier.value or 3)
    if tier in gs.screen_changes.planner_tiers_fired:
        return   # 每费用档首 2★ 一次(错过不补,用户裁定)
    gs.screen_changes.planner_tiers_fired.add(tier)
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        KIND_SCREEN_NAMES,
        register_screen_change,
    )
    register_screen_change(
        gs, 'planner', KIND_SCREEN_NAMES['planner'],
        source=f's3_star{new_star}@tier{tier}@{source}')


def check_env_bond_tier_grants(gs, new_sets, source: str) -> None:
    """羁绊档位条件发放判据(ENV_BOND_TIER_GRANTS 注册表驱动;调用点 =
    ``on_deployed_logic_write`` 尾部**门外**——on_qualification_changed
    的 sets-changed 门辖不到「不改任何 watched 资格集的板面写」(卖非
    在册阵营场上件/穿非羁绊装备/换位等),电平重试性要求任意板面写后
    必查,done 封账保幂等;new_sets 复用入口无条件现算值,零额外派生
    成本)。

    判定 = **电平 + 每档一次性**(用户裁定 2026-10-24「每个档位只发
    一次奖励」):new_sets 资格计数 ≥ 档位 ∧ (env, bond_tier_{档位})
    ∉ env_grants_done → 发 1 件;降档再回不重发(祈愿「首达档一次」
    同口径,本模块祈愿簿记先例)。equips 未观察跳过不标 done,下一次
    任意板面写自动重试(宁缺勿造守卫住发放原语 grant_env_bond_tier)。

    - env 门(active_env 读法沿 cw_env_grants.check_env_streak_grants
      先例)→ 表门 → 逐档电平判定;
    - ``source`` = 宿主写 produced_by(契约对称形参,本判据零消费面
      ——发放证据串已含 env/bond/tier 三维,归因走写台账 evidence,
      预留按来源排除的扩展位);
    - 资格集口径披露:资格集 = 按名去重(出身 ∨ 持星徽);击破现无
      卡带类装备,资格集与 board 多集计数对击破恒相等;未来出现「击破
      计数+1」类装备时本判据口径需复审(资格集会少计)。
    """
    env = gs.active_env.value
    if not env:
        return
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    from sr_od.application.currency_war.kernel.cw_env_grants import (
        BOND_TIER_KEY_PREFIX,
        grant_env_bond_tier,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_BOND_TIER_GRANTS,
    )
    grant = ENV_BOND_TIER_GRANTS.get(env)
    if grant is None:
        return
    bond, equip_name = grant
    count = len(new_sets.get(bond, ()))
    done = tuple(gs.env_grants_done.value or ())
    for tier in FACTIONS[bond].tiers:
        if count < tier:
            continue
        if (env, f'{BOND_TIER_KEY_PREFIX}{tier}') in done:
            continue   # 每档一次性:档已发放封账(降档再回不重发)
        grant_env_bond_tier(gs, env, bond, tier, equip_name)


def on_deployed_logic_write(gs, old_view, new_view, source: str) -> None:
    """deployed 逻辑写尾的派生维护单一入口(挂点 = cw_game_state
    ``_write_logic_frame`` deployed 分支;观察写不经此)。

    数据流(「资格集语义」):按名分解 diff →
    事件回调(通知层)→ 资格集一次提交 → 资格集回调一次(三判据);
    银狼星级同为派生存值 → 星级回调。值等(两视图占用全等)零回调。
    羁绊档位条件发放判据挂尾部**门外**(任意板面写必查——sets-changed
    门辖不到的板面写也要重查悬置补发,done 封账保幂等)。

    事件面契约:``on_equips_changed`` 只收 equips 有差的存活对(裁决 =
    按契约过滤;纯星变/开拓者形态变对不进该口——星级面归
    ``on_star_changed`` 存值路径,资格集在下方按视图总量对算,两者
    均不受此过滤影响)。
    """
    added, removed, changed = _diff_by_name(old_view, new_view)
    if added or removed:
        on_units_changed(gs, added, removed, source)
    equip_pairs = [(old_u, new_u) for old_u, new_u in changed
                   if list(old_u.equips or []) != list(new_u.equips or [])]
    if equip_pairs:
        on_equips_changed(gs, equip_pairs, source)
    old_sets = _qualification_sets(old_view)
    new_sets = _qualification_sets(new_view)
    if old_sets != new_sets:
        on_qualification_changed(gs, old_sets, new_sets, source)
    old_star = _planner_star(old_view)
    new_star = _planner_star(new_view)
    if old_star != new_star:
        on_star_changed(gs, old_star, new_star, source)
    # —— 羁绊档位条件发放(ENV_BOND_TIER_GRANTS):sets-changed 门外的
    #    必查分支——不改任何 watched 资格集的板面写(卖非在册阵营场上件/
    #    穿非羁绊装备等)也要重查悬置补发;new_sets 复用入口现算值零额外
    #    成本,done 封账保幂等(判定语义单一源 = check_env_bond_tier_grants)。
    check_env_bond_tier_grants(gs, new_sets, source)
