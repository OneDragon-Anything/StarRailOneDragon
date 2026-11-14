"""货币战争 值域回调级联(deployed 逻辑写尾的阵营触发判据级联;判据/登记/簿记

回调挂 **deployed 值变更**(非动作)——部署/卖出/替换/合成落场/穿戴,
凡改场上名单或装备,同一套回调;判据只看「值从什么变成什么」。观察写
零回调(观察 = 重新确认已发生的事实与纠偏,reactive 兜底);插入位置单一 =
``GameState._write_logic_frame`` 的 deployed 分支尾(logic/logic_rand
两逻辑通道同经,获得链递归每步语义完整)。

回调族(固定位置参数,用户裁定):
- ``on_units_changed(gs, added_units, removed_units, source)``:按名
  diff 的成员增/减(事件通知层);
- ``on_equips_changed(gs, changed_pairs, source)``:同名存活单位
  (旧,新) 对中 equips 有差者(事件通知层);
- ``on_qualification_changed(gs, old_sets, new_sets, source)``:盯的
  资格名集(弹窗羁绊表 + ENV_BOND_TIER_GRANTS 羁绊,注册表
  驱动)旧/新(派生存值)→ 判 S1a 跨档
  (V4.4 的 S1b 巨星重选/S2 伙伴判据随盛会之星/列车同行羁绊消失
  退役——v4.7 换赛季,见模块头与退役标注;策略批重建);
- ``on_star_changed(gs, old_star, new_star, source)``:场上银狼星级
  (派生存值,无/1/2/3)→ 判 S3 planner;
- ``check_env_bond_tier_grants(gs, new_sets, source)``:羁绊档位条件
  发放判据(ENV_BOND_TIER_GRANTS 注册表驱动;挂 deployed 写尾**门外**
  必查,电平 + 每档一次性 done 封账,发放原语住 cw_env_grants;
  v4.7 中间态表空——击破档位换代,条目待投资域 v4.7 重采)。

资格集与羁绊计数字段(board)分立:资格集 = 名集合(判据面;出身 ∨
持徽,贡献单一源 cw_bond_equips.unit_bond_tags);
board = 多集口径(卡带系多计,策略消费口)——两者非视图关系。

level 域同款值回调见 ``cw_levelup_callbacks``(升级连锁调度器,
宿主挂 ``_write_logic_frame`` level 分支尾)。

判据簿记(住 cw_overlay_register.ScreenChanges sidecar):
祈愿首达档一次;planner 每费用档一次;占卜屋住 S4 上报点(本模块外);
(V4.4 巨星跨档无簿记/伙伴无上限两判据随弹窗羁绊退役。)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        Unit,
    )

#: 盯的羁绊 → 跨档弹窗 kind(注册表驱动小表「判据归位」表:羁绊→弹窗
#: 映射 + 羁绊注册表档位表,零硬编码档线)。
#: ⚠️ v4.7 换赛季退役:V4.4 两弹窗羁绊盛会之星(megastar,纯上穿无簿记)/
#: 命运圣杯(wish_trial,首达档一次簿记分键)均入消失档——弹窗机制已
#: 不存在,表清空退役(S1a 循环骨架保留:表驱动零迭代,策略批按 v4.7
#: 新弹窗体系重建时按需重新登记)。
_FACTION_POPUP_KINDS: dict[str, str] = {}

#: S3 planner 的星级跟踪角色(银狼 LV.999;与 deploy_move 升费分支/
#: lv999_cost_tier 同名同源;场上同名唯一 =  裁决 1 已登记守卫)。
#: v4.7 注册表在册,S3 判据不受换赛季影响,保留。
_PLANNER_CHAR: str = '银狼LV.999'

# (_PARTNER_ANCHOR_CHAR/_PARTNER_FACTION/_MEGASTAR_FIRST_TIER 与 S1b
#  巨星重选/S2 伙伴判据段随 v4.7 换赛季退役:盛会之星/列车同行羁绊
#  消失——列车同行伙伴弹窗(姬子·启行在场前提)与巨星重选弹窗机制
#  均不存在,考古走 git 历史。)

# (S1b/S2 判据段退役,保留 S1a 表驱动循环 + S3 planner + 羁绊档位
#  条件发放判据(check_env_bond_tier_grants,注册表驱动)。)


def _iter_field_units(view) -> list[Unit]:
    """视图 → 上场单位清单(空槽跳过)。"""
    if view is None:
        return []
    out: list[Unit] = []
    for sub in (view.front_slots or [], view.back_slots or []):
        for u in sub:
            if u is not None:
                out.append(u)
    return out


def _qualification_sets(view) -> dict[str, set[str]]:
    """视图 → 盯的资格名集(派生存值;注册表驱动扩容)。

    资格 = 出身 ∨ 持该羁绊星徽(装备贡献单一源 = cw_bond_equips.
    unit_bond_tags:出身/卡带/星徽全量口径;名不在注册表/未知 → 零标签,
    该名对所有羁绊无资格)。

    watched = 弹窗羁绊表(v4.7 空表,见模块头退役标注) +
    ENV_BOND_TIER_GRANTS 羁绊(羁绊档位发放判据要按资格计数判档,
    资格集一并盯;扩容零干扰 = 既有判据只读各自羁绊,不读本扩容集)。
    """
    from sr_od.application.currency_war.kernel.cw_bond_equips import (
        unit_bond_tags,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_BOND_TIER_GRANTS,
    )
    watched = [*_FACTION_POPUP_KINDS]
    for _bond, _equip in ENV_BOND_TIER_GRANTS.values():
        if _bond not in watched:
            watched.append(_bond)
    sets: dict[str, set[str]] = {f: set() for f in watched}
    for u in _iter_field_units(view):
        tags = unit_bond_tags(u)
        for f in watched:
            if f in tags:
                sets[f].add(str(u.char_id))
    return sets


def _planner_star(view) -> int | None:
    """场上银狼 LV.999 星级(派生存值;不在场 = None)。

    场上同名唯一(裁决 1 入口守卫已登记)⇒ 至多一值;防御性取首见。
    """
    for u in _iter_field_units(view):
        if str(u.char_id) == _PLANNER_CHAR:
            return int(u.star)
    return None


def _diff_by_name(old_view, new_view
                  ) -> tuple[list, list, list]:
    """一次 deployed 写按名分解三类事件(
    语义」节):成员增(名新现)/ 成员减(名消失)/ 存活对(同名且
    (星, equips) 有差的 (旧单位,新单位) 对)。"""
    old_by_name: dict[str, Unit] = {
        str(u.char_id): u for u in _iter_field_units(old_view)}
    new_by_name: dict[str, Unit] = {
        str(u.char_id): u for u in _iter_field_units(new_view)}
    added = [u for n, u in new_by_name.items() if n not in old_by_name]
    removed = [u for n, u in old_by_name.items() if n not in new_by_name]
    changed: list[tuple[Unit, Unit]] = [
        (old_by_name[n], u) for n, u in new_by_name.items()
        if n in old_by_name and old_by_name[n] != u]
    return added, removed, changed


def on_units_changed(gs, added_units, removed_units, source: str) -> None:
    """角色变动回调(事件通知层:喂资格集——资格集在派生维护入口
    按视图总量对算,本层 = 契约 seam,未来成员类消费面插入位置)。"""
    # 通知层无独立判据(回调表口径:overlay 判据不住此)。
    return


def on_equips_changed(gs, changed_pairs, source: str) -> None:
    """装备变更回调(事件通知层:喂资格集;其他装备消费面留位)。"""
    return


def on_qualification_changed(gs, old_sets, new_sets, source: str) -> None:
    """资格集变更回调 → S1a 跨档判据
    (全部资格集判据,判据归位 = 值回调单一源)。

    (V4.4 的 S1b 巨星重选/S2 伙伴判据段随盛会之星/列车同行羁绊消失
    退役,见模块头退役标注;策略批按 v4.7 新弹窗体系重建。)
    """
    # —— S1a 档位跨越:有弹窗的羁绊资格集大小上穿任一档线,单写至多
    #    一次。无来源排除(合成继承星徽致跨档同弹;经典合成名集合不变
    #    天然不进本回调)。v4.7:弹窗羁绊表空(盛会之星/命运圣杯消失)
    #    → 零迭代,S1a 语义随策略批新弹窗体系重建。
    from sr_od.application.currency_war.data.cw_traits_data import (
        trait_by_name,
    )
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        KIND_SCREEN_NAMES,
        register_screen_change,
    )
    for faction, kind in _FACTION_POPUP_KINDS.items():
        old_n = len(old_sets.get(faction, ()))
        new_n = len(new_sets.get(faction, ()))
        crossed = [t for t in trait_by_name[faction].tiers
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

    # (S1b 巨星重选〔chosen_megastar 跌出盛会之星资格集重选〕与 S2 伙伴
    #  〔列车同行资格集增减 + 姬子·启行在场前提〕两判据段已随 v4.7
    #  换赛季退役——盛会之星/列车同行羁绊消失,弹窗机制不存在,
    #  考古走 git 历史。)


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
    已登记阵营场上件/穿非羁绊装备/换位等),电平重试性要求任意板面写后
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
    from sr_od.application.currency_war.data.cw_traits_data import (
        trait_by_name,
    )
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
    for tier in trait_by_name[bond].tiers:
        if count < tier:
            continue
        if (env, f'{BOND_TIER_KEY_PREFIX}{tier}') in done:
            continue   # 每档一次性:档已发放封账(降档再回不重发)
        grant_env_bond_tier(gs, env, bond, tier, equip_name)


def on_deployed_logic_write(gs, old_view, new_view, source: str) -> None:
    """deployed 逻辑写尾的派生维护单一入口(插入位置 = cw_game_state
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
    #    必查分支——不改任何 watched 资格集的板面写(卖非已登记阵营场上件/
    #    穿非羁绊装备等)也要重查悬置补发;new_sets 复用入口现算值零额外
    #    成本,done 封账保幂等(判定语义单一源 = check_env_bond_tier_grants)。
    check_env_bond_tier_grants(gs, new_sets, source)
