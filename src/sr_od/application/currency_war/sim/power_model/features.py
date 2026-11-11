"""战力模型特征面(双侧同源;sim-power-model §4.2 契约的落地件)。

**单侧算术 + 双侧适配**:特征核心 :func:`compute_features` 只写一次,
输入收敛为「板面计数 dict + 上阵槽位视图 + 等级」三要素——sim 侧由
:meth:`features_from_game_state` 从 GameState 状态容器取,实机侧由
:meth:`features_from_decision_row` 从 decisions 行 dict 取;任何一侧都
不另写第二份特征算术(双侧同源契约 = sim-power-model §4.2
;对齐测试 = 同一板面输入 → 两侧同一特征向量)。

特征全集 = sim-power-model §4.1 特征集+§4.3 分配表(13 维向量,训练期另加截距):

=== 定义与单一源(值域/出处)===
- rung_1/rung_2/rung_3:过渡达成度分档 one-hot 三位(参考档 rung0 并入
  截距),单一源 = ``kernel/cw_battle_calib._settle_rung``(四体系达成数,
  0-4);分档域钉四档(0-3,sim-power-model §3/§4.1「rung 四档(0-3)」+ 前代
  cw_coarse_battle ``_win_cell`` 的 ``min(max(rung,0),3)`` 钳位先例),
  实现为 ``min(_settle_rung, RUNG_MAX)``——rung4(四体系全达成)并入
  rung3 位,与「r>=3 置位」逐位等价,无行为歧义。
- final_form_progress:终局阵容达成度(连续 0~1)=
  ``max(form_progress(comp, 板面)) over COMP_LIBRARY``,取大线见
  :func:`best_line`;用户 2026-10-19 裁定(达成度须含终局阵容)。
- total_star_depth:净星深 Σ(star−1),单一源 =
  ``kernel/cw_battle_calib.deployed_star_depth``。
- core_star_depth:核心星深 = 取大线 ``Comp.core_chars`` 名单内单位的
  Σ(star−1)(用户 2026-10-19 裁定:星深须区分核心)。
- enemy_difficulty / enemy_difficulty_missing:敌难度数值 + 缺失指示;
  缺失口径 = None ∨ 合理带 [20,300] 外(sim-power-model §4.1 上下文组
  既定约定),缺失时数值按 0 载入、指示位置 1(sim-power-model §4.3 缺失指示位)。
- plane_not_first:位面二值(P1 vs 非P1;P3 语料并入非P1,低置信披露)。
- node_encounter / node_boss:node_type one-hot 两位,参考档 = 普通战斗
  (并入截距;one-hot 参考档选择只是重参数化,不改变模型表达族)。
  node_type 判定以 outcomes 为准(权威版本 §5.1-2),由调用方传入,本模块
  不读帧的 node_type(快照不问帧类型规则)。
- round_num:节点在位面内的轮次序位(原值)。
- deployed_minus_level:上场数 − 人口等级;上场数 = 上阵条目中
  ``char_id`` 非空者计数(空槽过滤,sim-power-model §4.1 组 A:
  char_id 为空的槽位条目不计入任何单位计数)。

=== 板面双源口径(如实声明)===
rung 经 ``_settle_rung`` 从上阵行**重算**板面(其内部走
``_recount_board`` 单一源);form_progress 读板面状态容器现值(实机行 =
观测的 ``state.board`` 左面板真值,sim = GameState.board)。两特征各随
其单一源的既定输入,不互相改写。

=== 实机行未识别单位的入账口径 ===
decisions 行 ``state.deployed`` 条目可带 char_id=''(识别失败件,约占
deployed 条目 7.8%)。特征核心的行侧适配**不携带**条目的 faction 字段
——``_recount_board`` 的 faction 兜底仅 faction 载体鸭子输入可达,
sim 的 ``Unit`` 无 faction 位(状态容器「阵营不存」红线),不携带才使两侧
结构同形;依据 = sim-power-model §4.1 组 A「char_id 为空的槽位条目不
计入任何单位计数」。观测板面(state.board)不受此影响(它记录左面板
所见,含未识别件的阵营贡献)。

边界:开拓者的排敏感形态归一(前排=记忆/后排=欢愉)随
``unit_bond_tags`` 单一源走,行侧按条目 ``position_pref``、sim 侧按
``Unit`` 缺省(后排)——「前排开拓者」在 sim Unit 表示域内不可表达,
属两侧公共输入域之外,不在对齐断言内。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _settle_rung,
    deployed_star_depth,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    Comp,
    form_progress,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    DeployedView,
    GameState,
)

#: 难度数值合理带(sim-power-model §4.1:缺失口径 = None ∨ 带外)。
DIFFICULTY_VALID_RANGE: tuple[int, int] = (20, 300)

#: rung 分档上界(rung 四档 0-3;钳位依据见模块 docstring)。
RUNG_MAX: int = 3

#: 战斗类节点词表(outcomes 映射后的英文规范名;node_type one-hot 的域)。
BATTLE_NODE_TYPES: frozenset[str] = frozenset({'battle', 'encounter', 'boss'})

#: node_type one-hot 的参考档(并入截距,不出现在向量位中)。
NODE_TYPE_REFERENCE: str = 'battle'

#: outcomes node_type 中文 → 英文规范名映射(权威版本 §5.1-2:映射常量
#: 单一源落代码;中文→英文 + ASCII 恒等——查不到的键原样返回)。
NODE_TYPE_CN_TO_EN: dict[str, str] = {
    '普通战斗': 'battle',
    '遭遇': 'encounter',
    '奖励': 'reward',
    '补给': 'supply',
}


def normalize_node_type(raw: Any) -> str:
    """outcomes/帧的 node_type 原值 → 英文规范名(ASCII 恒等;查不到
    原样透传,调用方按 BATTLE_NODE_TYPES 判战斗类)。"""
    raw_str = str(raw) if raw is not None else ''
    return NODE_TYPE_CN_TO_EN.get(raw_str, raw_str)


@dataclass(frozen=True)
class FeatureVector:
    """一场战斗的 13 维特征向量(sim-power-model §4.1;训练期另加截距)。

    字段序 = 向量位序(:meth:`to_list` 的输出序);训练脚本按
    :data:`FEATURE_NAMES` 对齐列,禁按位置隐式耦合。
    """

    rung_1: float
    rung_2: float
    rung_3: float
    final_form_progress: float
    total_star_depth: float
    core_star_depth: float
    enemy_difficulty: float
    enemy_difficulty_missing: float
    plane_not_first: float
    node_encounter: float
    node_boss: float
    round_num: float
    deployed_minus_level: float

    def to_list(self) -> list[float]:
        """特征向量(字段声明序;与 FEATURE_NAMES 同序)。"""
        return [float(getattr(self, name)) for name in FEATURE_NAMES]

    def as_dict(self) -> dict[str, float]:
        """具名特征 dict(训练样本行的 features 域)。"""
        return {name: float(getattr(self, name)) for name in FEATURE_NAMES}


#: 特征名序(单一源;训练脚本与产物消费按名对齐)。
FEATURE_NAMES: tuple[str, ...] = tuple(
    f.name for f in FeatureVector.__dataclass_fields__.values()  # type: ignore[attr-defined]
)


@dataclass
class _FeatureView:
    """特征核心的 duck GameState 视图(三要素:板面/上阵/等级)。

    kernel 特征函数(``_settle_rung``/``deployed_star_depth``/
    ``form_progress``)按状态容器鸭子类型读取(``gs.board.value`` 等),本视图
    以真实状态容器类型(Field/DeployedView)承载,两侧适配产物同构。
    """

    board: Any = field(default=None)   # Field 形(.value = dict)
    deployed: Any = field(default=None)   # Field 形(.value = DeployedView)
    level: Any = field(default=None)   # Field 形(.value = int)


def row_deployed_view(entries: list[dict[str, Any]] | None) -> DeployedView:
    """decisions 行 ``state.deployed`` 条目列表 → 上阵槽位视图。

    - 槽位语义:条目 ``slot`` = 排内槽号(前排 1-4/后排 1-6 独立编号,
      实测见生产行),``position_pref`` 分排('front'/'back')——分排
      以 position_pref 为准,排内按 slot 升序落位;
    - 条目 → duck Unit 适配(char_id/star/equips/position_pref 透传;
      **不携带 faction**,依据见模块 docstring「实机行未识别单位的入账
      口径」)——kernel 特征函数按属性鸭子类型读取,与 sim Unit 同形;
    - 空槽(None)显式保留位置语义;非 dict 条目(历史行容忍)跳过。
    """
    front: list[Any] = []
    back: list[Any] = []
    for e in (entries or []):
        if not isinstance(e, dict):
            continue
        pref = str(e.get('position_pref') or 'back')
        unit = SimpleUnit(
            char_id=str(e.get('char_id') or ''),
            star=int(e.get('star') or 1),
            equips=list(e.get('equips') or []),
            position_pref=pref,
        )
        (front if pref == 'front' else back).append((int(e.get('slot') or 0), unit))

    def _fill(row: list[tuple[int, Any]]) -> list[Any]:
        row.sort(key=lambda x: x[0])
        return [u for _slot, u in row]

    return DeployedView(front_slots=_fill(front), back_slots=_fill(back))


class SimpleUnit:
    """decisions 行条目的 duck Unit 适配(属性面与状态容器 Unit 对齐)。

    只带 kernel 特征链读取的属性(char_id/star/equips/position_pref);
    故意**无 faction 位**——``_recount_board`` 的 faction 兜底不触发,
    两侧结构同形(依据见模块 docstring)。"""

    def __init__(self, char_id: str, star: int,
                 equips: list[str], position_pref: str) -> None:
        self.char_id = char_id
        self.star = star
        self.equips = equips
        self.position_pref = position_pref


def best_line(board_value: dict[str, int] | None,
              deployed: DeployedView | None) -> tuple[Comp, float]:
    """取大线(取大定义的形式化):
    ``best_line(B) = argmax_{comp ∈ COMP_LIBRARY} form_progress(comp, B)``,
    平局破缺 = COMP_LIBRARY 注册序首个最大值(确定性,两侧一致)。

    返回 (阵容, 达成度);板面状态容器值为 None/缺键按空板计(form_progress
    内部 ``or {}`` 同口径)。
    """
    view = _FeatureView(
        board=SimpleNamespaceValue(board_value or {}),
        deployed=SimpleNamespaceValue(deployed),
        level=SimpleNamespaceValue(0),
    )
    best_comp = COMP_LIBRARY[0]
    best_fp = -1.0
    for comp in COMP_LIBRARY:
        fp = form_progress(comp, view)
        # 严格大于:平局保注册序首个(遍历序即注册序)。
        if fp > best_fp:
            best_fp = fp
            best_comp = comp
    return best_comp, best_fp


class SimpleNamespaceValue:
    """``.value`` 载体(特征链鸭子类型读取的最小面)。"""

    def __init__(self, value: Any) -> None:
        self.value = value


def compute_features(board_value: dict[str, int] | None,
                     deployed: DeployedView | None,
                     level: int | None,
                     *,
                     plane: int,
                     round_num: int,
                     node_type: str,
                     enemy_difficulty: float | int | None) -> FeatureVector:
    """特征核心(双侧唯一算术;定义与单一源见模块 docstring)。

    :param board_value: 板面计数状态容器值(sim = GameState.board.value /
        实机行 = state.board 观测左面板真值)。
    :param deployed: 上阵槽位视图(sim = GameState.deployed.value /
        实机行 = :func:`row_deployed_view` 产物)。
    :param level: 人口等级(实机行 = state.level;None 按域缺省 0,
        仅防御路径——现盘实机行该字段无缺失)。
    :param plane: 位面(join 键;outcomes 权威侧)。
    :param round_num: 位面内轮次(join 键)。
    :param node_type: 战斗类规范名(outcomes 判定为准,由调用方传入
        :func:`normalize_node_type` 产物;快照不问帧类型)。
    :param enemy_difficulty: 敌难度数值(实机行 = state.enemy_difficulty;
        None ∨ [20,300] 外 = 缺失)。
    """
    view = _FeatureView(
        board=SimpleNamespaceValue(board_value or {}),
        deployed=SimpleNamespaceValue(deployed),
        level=SimpleNamespaceValue(int(level) if level is not None else 0),
    )
    rung = min(_settle_rung(view), RUNG_MAX)
    best_comp, best_fp = best_line(board_value, deployed)
    total_depth = float(deployed_star_depth(view))

    rows = deployed_rows(view)
    core_set = set(best_comp.core_chars)
    core_depth = float(sum(int(getattr(u, 'star', 1) or 1) - 1
                           for u in rows
                           if getattr(u, 'char_id', '') in core_set))
    deployed_n = float(sum(1 for u in rows if getattr(u, 'char_id', '')))

    diff = None if enemy_difficulty is None else float(enemy_difficulty)
    lo, hi = DIFFICULTY_VALID_RANGE
    diff_missing = diff is None or not (lo <= diff <= hi)
    diff_val = 0.0 if diff_missing else float(diff)

    return FeatureVector(
        rung_1=1.0 if rung == 1 else 0.0,
        rung_2=1.0 if rung == 2 else 0.0,
        rung_3=1.0 if rung >= 3 else 0.0,
        final_form_progress=float(best_fp),
        total_star_depth=total_depth,
        core_star_depth=core_depth,
        enemy_difficulty=diff_val,
        enemy_difficulty_missing=1.0 if diff_missing else 0.0,
        plane_not_first=1.0 if int(plane) >= 2 else 0.0,
        node_encounter=1.0 if node_type == 'encounter' else 0.0,
        node_boss=1.0 if node_type == 'boss' else 0.0,
        round_num=float(int(round_num)),
        deployed_minus_level=deployed_n - float(int(level) if level is not None else 0),
    )


def deployed_rows(view: _FeatureView | GameState) -> list[Any]:
    """上阵紧缩行(前排在前;duck 读取,两侧同式)。"""
    dep_value = getattr(view.deployed, 'value', None)
    if dep_value is None:
        return []
    front = [u for u in (getattr(dep_value, 'front_slots', None) or [])
             if u is not None]
    back = [u for u in (getattr(dep_value, 'back_slots', None) or [])
            if u is not None]
    return [*front, *back]


def features_from_game_state(gs: GameState, *,
                             node_type: str,
                             enemy_difficulty: float | int | None,
                             ) -> FeatureVector:
    """sim 侧适配:GameState 状态容器 → 特征向量(读状态容器三要素后进核心)。"""
    return compute_features(
        getattr(gs.board, 'value', None) or {},
        getattr(gs.deployed, 'value', None),
        getattr(gs.level, 'value', None),
        plane=int(getattr(getattr(gs.node, 'value', None), 'plane', 1) or 1),
        round_num=int(getattr(getattr(gs.node, 'value', None),
                              'round_num', 1) or 1),
        node_type=node_type,
        enemy_difficulty=enemy_difficulty,
    )


def features_from_decision_row(row: dict[str, Any],
                               *,
                               node_type: str) -> FeatureVector:
    """实机行侧适配:decisions 快照行 → 特征向量。

    字段映射按实况(state.board/state.deployed,**无**
    board_factions——该键仅见于 sim 批产物):板面 = ``state.board``、
    上阵 = ``state.deployed``、等级 = ``state.level``、难度 =
    ``state.enemy_difficulty``、位面/轮次 = 行顶层(快照行即 join 键的
    末帧,顶层键值 = 键值)。``node_type`` 以 outcomes 判定为准,由调用
    方传 :func:`normalize_node_type` 产物。
    """
    state = row.get('state') or {}
    return compute_features(
        state.get('board') or {},
        row_deployed_view(state.get('deployed')),
        state.get('level'),
        plane=int(row.get('plane') or 0),
        round_num=int(row.get('round_num') or 0),
        node_type=node_type,
        enemy_difficulty=state.get('enemy_difficulty'),
    )
