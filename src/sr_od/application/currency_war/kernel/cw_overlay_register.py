"""货币战争 overlay 登记簿记(design.md 契约 C-登记/C-簿记;详设 overlay 生命周期契约)。

三口(固定位置参数,用户裁定):
- ``register_screen_change(gs, kind, screen_name, source)``:登记一条
  待处理弹窗(pending FIFO,同 kind 在册去重);
- ``consume_screen_change(gs, kind)``:按 kind 匹配移除(与顺序无关——
  弹出顺序不可枚举,用户裁定不强断言);
- ``clear_screen_changes(gs)``:整列清空(识别回备战底屏的兜底清)。

存处 = ``GameState.screen_changes`` 容器簿记 sidecar(overlay 生命周期契约
「存处」节裁定):单局生命周期随容器建亡、实机/sim 字面同一份存储、
判据点全在 kernel 手里有 gs;先例 = 非 Field 簿记组(node_books 族)。

kind 词表(九项,锚 = 现役选卡动作/画面名,禁新造同物异名;
overlay 生命周期契约 kind 表):partner / megastar / planner / wish_trial /
fortune / star_tome / box_card / expert_invite / aha。sim 现役旧名
('fate'/'expert'/'hack')随 3.4 消费面切换正名,本模块不提供别名。

触发簿记(契约 C-簿记;与 pending 同住 sidecar):
- 祈愿档位集合(命运圣杯首达档一次,降档再回不弹——用户裁定);
- planner 费用档集合(银狼 LV.999 每费用档首 2★ 一次);
- 占卜屋战斗计数(黑天鹅在场,每 2 场弹一次);
- 巨星跨档**无簿记**(每次上穿档线即弹,降档再升也弹——用户裁定;
  overlay 生命周期契约「sim 修正清单」)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: kind 词表封闭集(九项;集外登记炸错 = 防拼写漂移)。
SCREEN_CHANGE_KINDS: frozenset[str] = frozenset({
    'partner',        # 列车同行选伙伴(pick_partner)
    'megastar',       # 盛会之星选巨星(pick_megastar)
    'planner',        # 银狼升星「我来当策划」(pick_planner)
    'wish_trial',     # 祈愿试炼二选一(pick_wish_trial)
    'fortune',        # 命运卜者强化三选一(pick_fortune)
    'star_tome',      # 星徽秘典四选一(pick_star_tome)
    'box_card',       # 武装箱四选一(pick_box_card)
    'expert_invite',  # 专家邀请函五选一(pick_expert_invite)
    'aha',            # 阿哈简易装备选择(无上报动作;锚 = 备战.标识-简易装备)
})

#: kind → 分发档名单一源(检测提示锚 = 画面档;aha 无独立画面档,
#: 锚 = 备战屏上的标识区,档名取底层备战屏)。
KIND_SCREEN_NAMES: dict[str, str] = {
    'partner': '货币战争-列车同行',
    'megastar': '货币战争-盛会之星',
    'planner': '货币战争-银狼升星',
    'wish_trial': '货币战争-祈愿试炼',
    'fortune': '货币战争-命运卜者强化',
    'star_tome': '货币战争-星徽秘典弹窗',
    'box_card': '货币战争-备战-武装箱选择',
    'expert_invite': '货币战争-备战-专家邀请函',
    'aha': '货币战争-备战',
}


@dataclass(frozen=True)
class PendingScreen:
    """一条待处理弹窗登记(pending 条目)。

    [索引定义] kind ∈ SCREEN_CHANGE_KINDS(封闭集);screen_name = 分发
    档名(检测提示单一源);source = 来源注记(判据/写点,诊断与对账用,
    如 's1a_upcross:盛会之星'/'open_box')。
    """

    kind: str
    screen_name: str
    source: str


@dataclass
class ScreenChanges:
    """overlay 登记簿记 sidecar(GameState.screen_changes 值载体)。

    - pending:登记队列(FIFO;同 kind 去重——多判据同帧命中同屏只留
      一条,弹出顺序不可枚举);
    - wish_tiers_fired:祈愿已触发档位集合(命运圣杯首达档一次);
    - planner_tiers_fired:planner 已触发费用档集合(银狼每费用档一次);
    - fortune_battles:占卜屋战斗计数(黑天鹅在场场次;达 2 倍数弹一次,
      弹后计数保留继续累计)。
    """

    pending: list[PendingScreen] = field(default_factory=list)
    wish_tiers_fired: set[int] = field(default_factory=set)
    planner_tiers_fired: set[int] = field(default_factory=set)
    fortune_battles: int = 0


def register_screen_change(gs, kind: str, screen_name: str,
                           source: str) -> None:
    """登记一条待处理弹窗(同 kind 在册不重复)。

    kind 集外 = 编程错误,响亮炸出(词表封闭集纪律)。
    """
    if kind not in SCREEN_CHANGE_KINDS:
        raise ValueError(
            f'screen_change kind 集外: {kind!r}'
            f'(封闭集 = {sorted(SCREEN_CHANGE_KINDS)})')
    sc = gs.screen_changes
    if any(p.kind == kind for p in sc.pending):
        return   # 同 kind 去重(多判据同帧命中同屏)
    sc.pending.append(PendingScreen(kind=kind, screen_name=screen_name,
                                    source=source))


def consume_screen_change(gs, kind: str) -> None:
    """消费:按 kind 匹配移除(与顺序无关;不在册 = no-op)。"""
    sc = gs.screen_changes
    sc.pending = [p for p in sc.pending if p.kind != kind]


def clear_screen_changes(gs) -> None:
    """整列清空(识别回备战底屏的兜底清;簿记不清——簿记生命周期 = 局)。"""
    gs.screen_changes.pending.clear()
