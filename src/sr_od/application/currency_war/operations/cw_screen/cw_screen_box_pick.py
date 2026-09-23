"""货币战争 备战-武装箱选择 四选一画面 op。

武装箱 4 选 1 的访问面 = **独立建档画面**「货币战争-备战-武装箱选择」,
外循环阶段一身份分发进本 op(分发判定单一源 = ``flow/outer_loop.md``
§2.2);武装箱选卡不属备战动作词表(单选族例外:选卡即终结,判据 =
``screens/README.md`` §3)。链路:备战环 ``CwActionOpenBoxParam`` 点开启
(**终结化**——开箱即交回)→ 外循环按本画面分发本 op → OCR 卡名 →
选卡决策(局内策略 ``decide_box_card`` 契约面;无 match 局外不设早退
支,用户裁决 2026-09-22 全族删门)→ 点卡 → 固定动画等待 → **选卡即终结交回**
(选卡落地由下一帧观察覆盖)。

决策分层纪律:打分只住机器——策略契约 ``decide_box_card``
(``strategies/impl/cw_strategy.py`` abstract 零参 + ``strategies/impl/flow.py``
实现)与 kernel 机器 ``pick_equipment``(``kernel/cw_equip_value.py``)
是仅有的两处决策面,本 op 禁第二打分实现;``decide_box_card`` 异常留证
(完整栈)后显式上抛、返回越界索引同 fail-closed 上抛——两者都禁无声
回落内联打分(策略 bug 禁遮蔽;正本 = ``flow/README.md`` §1 决策控制
分层铁律 + ``screens/op-layer.md`` §1.1 出口三语义)。无 match 局外
不设早退支(op-layer.md §1.1「画面 op 不支持局外单独调用」;用户裁决
2026-09-22 全族删门),本 op 不设任何兜底决策路径;
``pick_equipment`` 打分单一源留守策略器 ``decide_box_card`` 消费(策略
器自限域)。

单选族交互(实机实测口径):点卡选中即确认(单步,无独立确认钮);
点卡名带下方一点(y=290,避「查看详情」按钮)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation):
观察 node = 入口锚复验(「标识-请选择」,分发即门,op 内机械复验防误派;
miss 未发 = round_fail 交回外循环按画面重分发)+ OCR 卡名行读数(2-8 字
过滤,x 升序;空 = 变体字型/动画帧读缺 = 未发出通道 round_fail 交回
外循环重派,禁盲点首卡兜底——选错不可逆,读数闸属观察处理)→ 观察
标准化门(卡名经装备注册表两段转换:形变归一精确命中 → LCS 相似匹配,
阈值常量住代码;任一候选转换失败 = 观察失败 round_fail 零写零上报交回
重读,名字与坐标同进退;重复名合法逐候选独立归一——屏契约 =
``screens/box_pick.md`` §3)+ 坐标解点(候选 x + CARD_Y 避让几何,观察
期一次解出)→ ``CwScreenBoxPickObs`` → ``report_screen_box_pick_obs``
写槽 ``box_card_names`` / ``box_card_names_xy`` 落容器(「写槽以本访问
将决策为前提」由门 + 非空闸保证,桩无 gs(有 match)→ 跳过写、决策
照走)。obs 读数(名 + x)与坐标
一并上报入容器(同门双写,坐标单一真相源 = 观察上报,op-layer.md
§1.1 :35);决策动作 node 零坐标现算。决策动作 node = 选卡决策
(``_decide_card_index`` 局内专用,fail-closed 契约)→ 选卡链经 ``CwActionPickBoxCardOp`` 派发(点卡选中即确认 +
动画等待 + 自上报住动作 op,机械链契约 = ``flow/action_exec.md`` §2;
点击坐标 = 容器 ``box_card_names_xy[idx]`` 动作 op 自取)→ 选卡即终结
交回(单选族例外,判据 = ``screens/README.md`` §3;选卡落地由下一帧
观察覆盖,无重入裁决旗标)。
"""
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from one_dragon.utils.str_utils import find_best_match_by_lcs
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENT_ROSTER
from sr_od.application.currency_war.kernel.cw_events import (
    normalize_registry_equip_name,
)
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect, _ocr
from sr_od.application.currency_war.kernel.cw_screen_report.box_pick import (
    CwScreenBoxPickObs,
    report_screen_box_pick_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickBoxCardParam,
)
from sr_od.application.currency_war.prep_actions import _OVERLAY_ANIM_WAIT_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 装备注册表键集定序列表(观察标准化门第二段 LCS 兜底的遍历域;
#: sorted 定序保证同分取注册表序首个,确定性不随 frozenset 迭代序漂移)。
_EQUIP_ROSTER_LIST: list[str] = sorted(EQUIPMENT_ROSTER)

#: 观察标准化门第二段 LCS 相似阈值(LCS 占比,相对注册表名长度;取值
#: 同装备名归一相似层门槛 = kernel/cw_events ``_EQUIP_NORM_LCS_FLOOR``,
#: 段一唯一命中与段二最高分同门槛——降阈值 = 放行低质错配,选错不可逆)。
_EQUIP_LCS_THRESHOLD: float = 0.75


class CwScreenBoxPick(SrOperation):
    """武装箱 4 选 1 选卡画面 op(选卡即终结;单选族例外,判据 = screens/README.md §3)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-备战-武装箱选择'
    #: 卡身点击 y(点卡名下方一点避「查看详情」按钮;2026-08-14 实测)
    CARD_Y: ClassVar[int] = 290

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=CwScreenBoxPick.SCREEN_NAME)
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenBoxPickObs | None = None
        # 标准化读数 [(标准注册名, 卡 x 中心), ...](x 升序;卡名与坐标
        # 一并上报入容器 ``box_card_names`` / ``box_card_names_xy``
        # (op-layer.md §1.1 :35 坐标单一真相源 = 观察上报),本 op 零
        # 坐标现算,读数 x 仅供观察侧解点)。
        self._cards: list[tuple[str, int]] = []

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口锚复验 + OCR 卡名 → 标准化门/解点 → report 落容器。

        两道闸(入口锚/读数,均在观察 node):锚 miss = 非本画面;
        卡名空 = 未发出通道(变体字型/动画帧)——都 fail 交回外循环重派
        (重观察语境禁猜,禁盲点首卡),report 不调(容器不进盲值)。
        标准化门任一候选转换失败同 fail 早退(零写零上报,与「读空」闸
        同型并列;名字与坐标同进退)。"""
        screen = self.last_screenshot
        # 入口锚复验(分发即门,op 内机械复验防误派;锚 miss = 非本画面
        # → fail 交回外循环按画面重分发)
        if not self.round_by_find_area(
                screen, CwScreenBoxPick.SCREEN_NAME, '标识-请选择',
                crop_first=False).is_success:
            return self.round_fail('非武装箱选择画面(标识-请选择 miss)')
        cards = self._read_card_names(screen)
        if not cards:
            # OCR 未读卡名(变体字型/动画帧)= 未发出通道:交回外循环
            # 重派(重观察语境禁猜),禁盲点首卡兜底(选错不可逆)。
            return self.round_fail('OCR 未读到卡名(变体/动画帧),交回重派')
        # 观察标准化门(op-layer.md §1.1 条款①):任一候选转换失败 =
        # 观察失败——round_fail 早退、零写零上报,交外循环重观察重读
        # (禁带病上报);失败时坐标域随名字域同进退一并零写。
        cards = self._standardize_card_names(cards)
        if cards is None:
            log.warning('[cw][boxpick] 观察标准化门失败:卡名转换不到标准'
                        '注册名(零写零上报,交回重观察)')
            return self.round_fail('卡名标准化失败(零写零上报,交回重观察)')
        # 坐标解点(观察期一次解出;y = CARD_Y 卡名带下方避让几何)。
        points = [(x, CwScreenBoxPick.CARD_Y) for _, x in cards]
        self._cards = cards
        obs = CwScreenBoxPickObs(on_screen=True,
                                 card_names=[n for n, _ in cards],
                                 points=points,
                                 screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            # 写槽调用(report 落容器:同访问覆盖写,写点前提「本访问将
            # 决策」由两道闸保证;桩无 gs(有 match)→ 跳过写,决策照走;
            # 名字与坐标同门双写)。
            report_screen_box_pick_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """选卡决策 → 选卡链经工厂派发 → 选卡即终结交回。

        点卡选中即确认 + 动画等待 + 自上报住 ``CwActionPickBoxCardOp``
        (机械链契约 = flow/action_exec.md §2;点击坐标 = 容器
        ``box_card_names_xy[idx]`` 动作 op 自取,选卡落地归下一帧观察
        覆盖);本 op 只决策(局内;fail-closed 契约)与交回;无 match
        局外不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门)。
        派发实例携真实选中下标(上报 param 即真实选择)。"""
        # 无 match 局外不设早退支(画面 op 不支持局外单独调用,op-layer.md
        # §1.1;用户裁决 2026-09-22 全族删门):单跑缺上下文沿正常链路
        # 在此失败即预期,禁回填此类单跑防御分支。
        idx = self._decide_card_index([n for n, _ in self._cards])
        chosen = self._cards[idx][0]
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=idx)
        action_op_for(CwActionPickBoxCardParam(idx=idx), self.ctx,
                      _env).execute()
        log.info(f'[cw][boxpick] 选卡 {chosen} → 点击已发(选卡即终结,'
                 '交回外循环)')
        return self.round_success(
            f'选卡 {chosen}(选卡即终结,交回外循环)',
            wait=_OVERLAY_ANIM_WAIT_S)

    def _read_card_names(self, screen: MatLike) -> list[tuple[str, int]]:
        """OCR 卡名行 → [(卡名, 卡 x 中心)] 按 x 升序(2-8 字过滤,与原
        执行器读卡半逐位同式;识别域 = screen_info 区域-卡名行单一源)。"""
        rect = _area_rect(self.ctx, '区域-卡名行', CwScreenBoxPick.SCREEN_NAME)
        names: list[tuple[str, int]] = []
        if rect is not None:
            for r in _ocr(self.ctx, screen, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        return names

    def _standardize_card_names(
            self, cards: list[tuple[str, int]]) -> list[tuple[str, int]] | None:
        """观察标准化门(op-layer.md §1.1 条款①):``_read_card_names``
        读出后、组装 obs 前逐候选两段转换——①形变归一
        (``normalize_registry_equip_name`` 注册表分层归一单一源,产出必
        为注册名)精确命中;②不中(归一返回 '')再 LCS 相似匹配
        (``find_best_match_by_lcs``,阈值 = ``_EQUIP_LCS_THRESHOLD``)取
        最高分;两段皆不中 = 转换失败,返回 None(调用方 round_fail 整
        函数早退,零写零上报交回重读)。

        四卡可能同名(同装备多张)= 重复名合法观察面:逐候选独立归一,
        不适用「多候选命中同一注册名 = 转换失败」互斥判(该判辖选项
        互斥屏);容器 ``box_card_names`` 值域自此 = 标准注册名。"""
        resolved: list[tuple[str, int]] = []
        for name, x in cards:
            canon = normalize_registry_equip_name(name)
            if canon not in EQUIPMENT_ROSTER:
                best = find_best_match_by_lcs(
                    name, _EQUIP_ROSTER_LIST,
                    lcs_percent_threshold=_EQUIP_LCS_THRESHOLD)
                canon = _EQUIP_ROSTER_LIST[best] if best is not None else ''
            if not canon:
                return None
            resolved.append((canon, x))
        return resolved

    def _decide_card_index(self, names: list[str]) -> int:
        """选卡决策(局内专用;容器写归观察 node 的
        ``report_screen_box_pick_obs`` 调用,本方法只决策):策略契约
        ``decide_box_card``(fail-closed:异常留证上抛/越界上抛,禁
        无声回落)。无 match 局外不设早退支(op-layer.md §1.1;用户
        裁决 2026-09-22 全族删门),本方法无兜底臂。"""
        try:
            idx = self.ctx.cw_match.strategy.decide_box_card().idx
        except Exception:   # noqa: BLE001  留证后显式上抛,禁无声回落
            import traceback

            log.error('[cw!][boxpick] decide_box_card 异常(留证后上抛):\n%s',
                      traceback.format_exc())
            raise
        if not (0 <= idx < len(names)):
            raise ValueError(
                f'decide_box_card 返回越界索引 {idx}(实读卡数 '
                f'{len(names)});策略契约违约 fail-closed,禁回落内联选卡')
        return idx
