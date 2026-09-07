"""配方等待件谓词 kernel 单一源(P39 臂一触发信号 + P72 支A 兑现链)。

单一源收口(ADR-0516 下沉先例):``arm1_existence`` 实现自
statefn/predicates 下沉本模块(kernel 判据消费它须保持「kernel 禁
import strategies」桶依赖矩阵),statefn 侧改 import 重定向、三在役
消费位(mandate.py/shop.py/entry.py)调用零改。收敛裁决与域论证见
ADR-0592:判定域 = [33] 精确化裁定(2026-09-01,判定域=阵营相关单位
不限星级、不限锁定线名单;历史「star≥2 ∧ 目标线名单」双收窄判废)
的板面域读法——bench 件与当前板面共享任一羁绊键即域内。

依赖方向:仅 import 数据注册表(CHARACTERS/FACTIONS)与 cw_state 槽表
常数;不 import 任何决策/策略符号。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_state import DEPLOYED_CAPACITY


def arm1_existence(deployed_count: int, bench_names: list[str],
                   deployed_names: list[str],
                   deploy_cap: int | None = None) -> bool:
    """P39 臂一三元触发信号(自 statefn/predicates 下沉,ADR-0516 先例;
    M3 消费,板面可观测量,非 EV 项)。

    ①板满:``deployed_count == deploy_cap``——**cap 口径 = 当前可上阵数**
    (GameState.max_units() / MandateFrame.deploy_cap:level+宝钻、封顶
    10),非固定槽表常数 ``DEPLOYED_CAPACITY``(=10,ADR-0392 定长槽表
    的物理长度)。结论出处:2026-09-03 零刷新诊断批(ZERO_REFRESH_DIAG
    §4.2)实证 M3 升级门 13/13 波恒 False 的根因即此——旧条件拿 10 当
    板满阈值,而板面实际上板量受等级驱动 cap 约束(P1 期 3→5 量级),
    ``deployed_count`` 构造性不可达 10 ⇒ 触发面恒空;按 cap 口径重算
    同语料 10/13、5/12 波真(``.debug/temp/currency_war/core_swap/
    arm1_diag.py``)。边界:``deploy_cap=None``(观察帧缺 cap 读数)时
    兜底固定槽表常数 10——**该分支在生产消费位(run_mandate/商店线)
    经 ensure_contract 前提 ``_arm1_cap_level_driven``(deploy_cap=None
    ⇒ 违例弃权)已不可达**(契约层弃权优先于函数内兜底,IMPL_ADV_R200
    OBS-3 收口);保留仅作函数局部完备性(直调/测试面),非生产语义。
    cap>10 时按 10 封顶(max_units 同款)。②③见下,不变。
    ②阵营相关等待件:bench 存在与当前板面共享阵营/流派羁绊的单位
    ([33] 裁定宽域:不限星级);③上场边际贡献>0:由①②结构承载
    (w>0 板面谓词,NMF §3.3 #3——臂一只需 w>0,无需 w 精确值,
    【拟】#3 的 w 标定面不触发)。
    """
    cap = (DEPLOYED_CAPACITY if deploy_cap is None
           else min(deploy_cap, DEPLOYED_CAPACITY))
    if deployed_count < cap or not bench_names:
        return False
    board_tags: set[str] = set()
    for name in deployed_names:
        ch = CHARACTERS.get(name)
        if ch is not None:
            board_tags.update(ch.factions)
            board_tags.update(ch.flows)
    if not board_tags:
        return False
    for name in bench_names:
        ch = CHARACTERS.get(name)
        if ch is None:
            continue
        if board_tags & (set(ch.factions) | set(ch.flows)):
            return True
    return False


#: 等待件收紧模式(C1 候裁显式参数化,ADR-0590 ``REDEPLOY_TRANSITION_
#: ENABLED`` 同款;候裁行 = 进度账本 T-139,用户候裁中,翻本常量即切):
#: - ``'gap'``(缺省,口径 a/B「配方缺口成员」):候选件与板面共享的
#:   羁绊键中任一键的板面计数 < 该键基础激活档(FACTIONS[key].tiers[0],
#:   N6 档位单一源 = FACTIONS 注册表首档;kernel/cw_deploy_logic 的
#:   TRANSITION_TRAITS 挂账副本禁 import)——即板面还缺该配方档的人头;
#: - ``'ignition'``(口径 b):收紧到「上阵即点火」——候选件与板面共享
#:   键中任一键上阵后恰达激活档(tier_completes 同语义;窄:首件帧
#:   不点火,解冻残留);
#: - ``'board'``(口径 c):纯板面域无缺口排除(宽:纯冗余件无排除,
#:   与 [35]③ 排除语义冲突,C1 候选集如实保留)。
#: 用户裁决落地后按裁决值改写本常量并同步 ADR-0592 候裁节回写。
RECIPE_WAITING_MODE: str = 'gap'


def _recipe_base_tier(key: str) -> int | None:
    """羁绊键的基础激活档(配方基础形态所需人头;单一源 = FACTIONS
    注册表 tiers 首档)。未注册键(如跨表伪键)返 None = 无档位证据。"""
    info = FACTIONS.get(key)
    if info is None or not info.tiers:
        return None
    return info.tiers[0]


def board_bond_counts(deployed_names: list[str]) -> dict[str, int]:
    """板面羁绊计数(factions+flows 逐项 +1;deployed_bond_counts 同口径
    的名单版;未注册名不计——无名可判即无阵营信号)。"""
    out: dict[str, int] = {}
    for name in deployed_names:
        ch = CHARACTERS.get(name) if name else None
        if ch is None:
            continue
        for f in tuple(ch.factions or ()) + tuple(ch.flows or ()):
            out[f] = out.get(f, 0) + 1
    return out


def _qualifies(cid: str, shared: set[str], counts: dict[str, int],
               deployed_cids: set[str]) -> bool:
    """单件候选资格(谓词规格 ADR-0592:

    ``qualifies(x) := 共享板面羁绊键 ∧ 收紧模式判定 ∧ ¬name_dup(x)``

    - name_dup 排除(E1,C2 裁决「char_id∉deployed_cids 零参数轻量合取」
      先行;完整 has_deployable 部署语境接线候后续批):候选件已在板上
      ⇒ 部署被同名围栏拦,升级人口位当帧不可兑现;
    - 收紧模式按 ``RECIPE_WAITING_MODE``:'gap' = 任一共享键板面计数
      < 基础档(任一/全部量词与 E2 对偶自洽——全部档饱和即纯冗余排除);
      'ignition' = 任一共享键上阵后恰达激活档;'board' = 无缺口排除。
      未注册键无档位证据,不参与 'gap'/'ignition' 判定(证据不足不放行
      旁路,保守向)。
    """
    if cid and cid in deployed_cids:
        return False
    if RECIPE_WAITING_MODE == 'board':
        return bool(shared)
    for key in shared:
        base = _recipe_base_tier(key)
        if base is None:
            continue
        now = counts.get(key, 0)
        if RECIPE_WAITING_MODE == 'gap':
            if now < base:
                return True
        else:   # 'ignition':上阵后(now+1)恰达任一激活档
            info = FACTIONS.get(key)
            if info is not None and (now + 1) in info.tiers:
                return True
    return False


def recipe_waiting(deployed: list, bench: list, cap: int | None) -> bool:
    """P72 支A 兑现链谓词(C_realize=1 判定;三消费位单一源,ADR-0592)。

    谓词规格(方案 v3 §3.3;命题 = proofs P82-c 双向差分,候册:证明批候立、
    P82 行候补入 math_proofs——见账本 T-139 跟踪):

    ```
    recipe_waiting(deployed, bench, cap) :=
        arm1_existence(deployed_count, bench_names, deployed_names, cap)
          # ①板满(cap 口径)∧ ②板面域不限星级;③边际贡献>0 由①②结构承载
      ∧ ∃ x ∈ bench: qualifies(x)
    ```

    与旧三副本(板满 ∧ bench 任意 2★,cw_economy.py 两处 + criteria/
    levelup.py 一处,ADR-0576 落码批写入)的差分是**对称差**(P82-c):
    放宽 = bench 1★ 配方缺口件(历史上被 star 合取拒,语义依据见下)
    现放行;收窄 = bench 线外 2★/纯冗余件(现行放行,无 [33] 域与
    [35]③ 排除依据)现不放行。star 合取移除的依据 = 兑现链三件
    (人口位增量/羁绊档按在场人头计数/部署合格拒因闭集)均无星级依赖;
    域/缺口合取的依据 = [33] 裁定字面「能加入当前阵容羁绊体系」+
    [35]③ 纯冗余排除 + C1 口径 B(配方缺口成员,候裁挂账见
    ``RECIPE_WAITING_MODE``)。

    消费位(改谓词改本函数,禁判据体外平行实现):kernel
    ``schedule_upgrade`` ①臂 / ``_upgrade_ul_threshold_ok`` ΔV_pop
    指示项 / criteria ``levelup._realize_chain_ready``(委托)/ 引擎
    LevelUp 执行点披露 ``dec_recipe_waiting`` / 检查器
    ``check_levelup_budget_gate`` 支A 镜像(同源消费)。

    边界:``cap=None`` 恒 False(cap 缺读对齐生产谓词 fail-closed,
    ADR-0589 同款;arm1_existence 函数内兜底仅其直调面保留)。槽表
    None 位跳过(deployed 计数与名单均按占用件现读)。
    """
    if cap is None:
        return False
    dep_names = [d.char_id or '' for d in (deployed or []) if d is not None]
    bench_names = [b.char_id or '' for b in (bench or []) if b is not None]
    if not arm1_existence(len(dep_names), bench_names, dep_names, cap):
        return False
    counts = board_bond_counts(dep_names)
    board_tags = set(counts)
    deployed_cids = set(dep_names)
    for cid in bench_names:
        ch = CHARACTERS.get(cid)
        if ch is None:
            continue
        shared = board_tags & (set(ch.factions) | set(ch.flows))
        if shared and _qualifies(cid, shared, counts, deployed_cids):
            return True
    return False


__all__ = [
    'RECIPE_WAITING_MODE', 'arm1_existence', 'board_bond_counts',
    'recipe_waiting',
]
