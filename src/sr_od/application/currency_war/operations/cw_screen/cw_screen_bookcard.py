"""货币战争 星徽秘典四选一画面 op。

OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关);入口 id_mark 校验 +
出口由重入裁决判落地(弹窗不在 = 选卡落地)+ 完成承诺固定时长
``CW_OVERLAY_SETTLE_S``。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。观察 node = 入口门(标识-星徽秘典,miss = round_fail
交回外循环重判)+ 卡阵营名一次读(全屏 OCR「X星徽」去后缀,x 升序;入口帧
一次读,与现役决策体读同帧等价)→ 观察标准化门(阵营名经 FACTIONS 注册表
两段转换:精确命中 → LCS 相似 + 次高分差拒判;任一候选转换失败/歧义/
多候选命中同一注册名 = 观察失败 round_fail 零写零上报交回重读,
op-layer.md §1.1 观察标准化门)+
候选点解算(点 = OCR x 中心 + x 近邻「星徽卡-N」建档中心 y;任一建档缺失
= 观察失败 round_fail 双域零写)→ ``report_screen_bookcard_obs`` 落容器
``star_tome_opts`` / ``star_tome_opts_xy``(空候选不写,闸在 report 内,
双域一体,同门同写,op-layer.md §1.1 :35)→ obs 挂实例属性进决策 node。
决策动作 node = 重入裁决顶部(选卡点击已发 → 弹窗不在 = 选卡落地 → 此刻
才写 chosen_tome + 到账登记 + success 交回;在 = 点击未落地 → 清标志重走
重选)→ 决策出口守卫(无 match 局外不设早退支,用户裁决 2026-09-22
全族删门;候选空/返回 None/词表外 = 具名 fail 零盲发[出口③];idx 越界
= 守卫断言[§1.3])→ 决策从容器零参读 → 点卡
(坐标 = 动作 op 自容器 ``star_tome_opts_xy`` 按 idx 取,op-layer.md §1.1
:35)→ round_wait 循环(不烧节点重试预算,无防御上限)。chosen_tome 与
ConfirmTome 到账登记 = 重入裁决点留守(动作事实边界,不进 report;
ConfirmTome 逻辑推进 = owned 本体直推);本屏 sim 腿 = 不适用(sim 无对应
画面段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_game_state_consume chosen_tome 锁 +
test_cw_screen_two_node_family 形态锁;典籍通道真 op 锁补档 =
开放设计注,见 screens/bookcard.md §9)。
"""
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_obs_core import (
    area_center,
    lcs_resolve_strict,
)
from sr_od.application.currency_war.kernel.cw_screen_report.bookcard import (
    CwScreenBookcardObs,
    report_screen_bookcard_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickStarTomeParam,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: FACTIONS 注册表键集定序列表(观察标准化门第二段 LCS 兜底的遍历域;
#: sorted 定序保证同分取注册表序首个,确定性不随 dict 迭代序漂移)。
_FACTION_NAMES: list[str] = sorted(FACTIONS)

#: 观察标准化门第二段 LCS 相似阈值(LCS 占比,相对注册表名长度;取值同
#: 装备名收敛批门槛 = 0.75——阵营名「昼之半神/夜之半神」仅一字差,降阈值
#: = 放行邻项错配,点卡即选不可逆)。
_FACTION_LCS_THRESHOLD: float = 0.75

#: 观察标准化门第二段歧义拒判分差(与阈值同量纲;判据 = 过阈值的最高
#: 分与次高分之差,低于本差 = 注册表内歧义不可分辨 → 转换失败,禁直接
#: 取最高分):「昼之半神/夜之半神」共享词素族,单字误读可对两名同分
#: 0.75(阈值为横杆),近分必有误读禁猜——点卡即选不可逆;取值同投资
#: 环境屏先例 0.15。
_FACTION_LCS_AMBIGUITY_MARGIN: float = 0.15


class CwScreenBookcard(SrOperation):
    """星徽秘典四选一:OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关)。

    决策面 = 策略器零参决策(打分:target 阵营/board 已有/配方框架;单一
    源 = ``strategies/impl/flow.py::decide_star_tome``),本 op 零选卡倾向
    判断——决策出口守卫:无 match 局外不设早退支(用户裁决 2026-09-22
    全族删门);候选空/返回 None/词表外 = 具名 fail 零盲发(出口③);
    pick idx 越界 = 守卫断言(§1.3)。选卡坐标 = 动作 op 自容器 ``star_tome_opts_xy`` 按 idx
    取(坐标单一真相源 = 观察上报,op-layer.md §1.1 :35)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-星徽秘典弹窗'
    MARK_AREA: ClassVar[str] = '标识-星徽秘典'
    CARD_AREAS: ClassVar[tuple[str, ...]] = ('星徽卡-1', '星徽卡-2', '星徽卡-3', '星徽卡-4')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-星徽秘典')
        # 选卡点击已发待重入裁决的星徽名(验证废除形态):重入裁决由决策
        # 动作 node 顶部承载(弹窗不在 = 选卡落地)→ 此刻才写 chosen_tome
        # + 到账登记;弹窗仍在 = 点击未落地 → 重走重选(不留幻影登记)。
        self._pick_pending: str | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费)与候选名读数
        # (坐标生产输入 x 近邻锚留观察侧;坐标经 obs ``option_points``
        # 入容器 ``star_tome_opts_xy``,op-layer.md §1.1 :35)。
        self._obs: CwScreenBookcardObs | None = None
        self._cards: list[tuple[str, int]] = []

    def _read_card_factions(self, screen: MatLike) -> list[tuple[str, int]]:
        """全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右;x 中心随
        观察上报入 ``star_tome_opts_xy``(y = 「星徽卡-N」建档中心,观察期
        现取;op-layer.md §1.1 :35,坐标单一真相源 = 观察上报)。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        cards: list[tuple[str, int]] = []
        for o in ocr:
            t = (o.data or '').strip()
            if t.endswith('星徽') and len(t) > 2:
                cards.append((t[:-2], o.x + o.w // 2))
        cards.sort(key=lambda c: c[1])
        return cards

    def _standardize_card_factions(
            self, cards: list[tuple[str, int]]) -> list[tuple[str, int]] | None:
        """观察标准化门(op-layer.md §1.1 观察标准化门):``_read_card_factions``
        读出后、组装 obs 前逐候选两段转换——①形变归一(去「星徽」后缀 +
        空白剥离,读链既有)后精确命中 ``data/cw_factions.py::FACTIONS``;
        ②不中再 LCS 相似(``lcs_resolve_strict``,阈值 =
        ``_FACTION_LCS_THRESHOLD`` ∧ 最高分与次高分差 ≥
        ``_FACTION_LCS_AMBIGUITY_MARGIN``——分差过近 = 注册表内歧义不可
        分辨,禁直接取最高分);两段皆不中 ∨ 歧义 = 转换失败,返回 None
        (调用方 round_fail 整函数早退,零写零上报交回重读,禁带病上报)。

        星徽四选一为选项互斥屏:多候选命中同一注册名 = 识别质量不足以
        区分,同判转换失败(op-layer.md §1.1 在册互斥判);容器
        ``star_tome_opts`` 值域自此 = FACTIONS 标准注册名(标准化后决策
        消费标准名,动作上报只携 idx)。"""
        resolved: list[tuple[str, int]] = []
        for name, x in cards:
            canon = name if name in FACTIONS else ''
            if not canon:
                canon = lcs_resolve_strict(
                    name, _FACTION_NAMES,
                    threshold=_FACTION_LCS_THRESHOLD,
                    ambiguity_margin=_FACTION_LCS_AMBIGUITY_MARGIN)
            if not canon:
                return None
            resolved.append((canon, x))
        if len({n for n, _ in resolved}) != len(resolved):
            return None
        return resolved

    def _resolve_option_points(
            self, cards: list[tuple[str, int]]) -> list[tuple[int, int]] | None:
        """候选点观察期一次解算(坐标生产半,op-layer.md §1.1 :35):每候选
        点 = (OCR x 中心,x 近邻「星徽卡-N」建档中心 y)——x 近邻锚防 area
        序与画面序错位(锚半自决策半迁观察侧);任一「星徽卡-N」area 缺失
        (``area_center`` 返 None)= 观察失败,返回 None(调用方 round_fail
        早退、``star_tome_opts`` / ``star_tome_opts_xy`` 双域零写交回外
        循环,与转换失败同格,名字与坐标同进退)。值形状 = 1080p 平铺
        元组,与候选名同序等长。"""
        centers: list[Point] = []
        for area in self.CARD_AREAS:
            pt = area_center(self.ctx, area, self.SCREEN_NAME)
            if pt is None:
                return None
            centers.append(pt)
        return [(x, centers[min(range(len(centers)),
                                key=lambda i: abs(centers[i].x - x))].y)
                for _, x in cards]

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 卡阵营名一次读(标准化门 + 解点)→ report 落容器。

        门 miss = round_fail 早退(与现役首闸同 status,交回外循环重判)。
        门后卡名 OCR 一次读 → 观察标准化门(任一候选转换失败/多候选同名
        = 观察失败 round_fail 早退、零写零上报交回重读)→ 候选点解算
        (任一「星徽卡-N」建档缺失 = 观察失败 round_fail 早退、双域零写)
        → ``report_screen_bookcard_obs`` 同门双写容器 ``star_tome_opts`` /
        ``star_tome_opts_xy``(空候选不写,闸在 report 内,双域一体);
        match/gs 缺席的局外兜底路径跳过 report(候选空 = 具名 fail 零
        盲发;report 局外豁免面与决策出口互不辖;无 match 局外不设早退
        支,用户裁决 2026-09-22 全族删门)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非星徽秘典画面')
        cards = self._standardize_card_factions(
            self._read_card_factions(screen))
        if cards is None:
            log.warning('[cw-flow-bookcard] 观察标准化门失败:阵营名转换不到'
                        'FACTIONS 标准注册名(零写零上报,交回重观察)')
            return self.round_fail('阵营名标准化失败(零写零上报,交回重观察)')
        points = self._resolve_option_points(cards)
        if points is None:
            return self.round_fail(
                '星徽秘典缺「星徽卡-N」建档(观察侧解点,双域零写)')
        obs = CwScreenBookcardObs(on_screen=True,
                                  options=[c[0] for c in cards],
                                  option_points=points,
                                  screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_bookcard_obs(_gs, obs)
        self._obs = obs
        self._cards = cards
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 决策出口守卫 → 零参决策 → 派发 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮选卡已发 → 弹窗不在 =
        选卡落地 → 补写 chosen_tome + 到账登记 + success 交回;弹窗仍在 =
        点击未落地 → 重走(重读重选)。

        决策出口守卫(次序:候选空臂 → 返回契约 → 值域;各守卫均在任何
        点击之前——派发即点卡、弹窗自关,选择不可逆,必须派发前拦):
        无 match 局外不设早退支(op-layer.md §1.1;用户裁决 2026-09-22
        全族删门),单跑缺上下文沿正常链路失败即预期——原「盲点卡 1」
        退役申报;候选空 = 具名 fail 零盲发(出口③);返回 None/词表外
        = 具名 fail 零盲发(出口③,消息含原值);idx 越界 = 守卫断言
        AssertionError(op-layer.md §1.3,禁钳位——原「静默钳 0」退役
        申报)。"""
        if self._pick_pending is not None:
            _p = self._pick_pending
            self._pick_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, self.SCREEN_NAME, self.MARK_AREA,
                    crop_first=False).is_success:
                self._settle_picked_tome(_p)
                return self.round_success('星徽秘典选卡完成(重入观察裁决)',
                                          wait=CW_OVERLAY_SETTLE_S)
        cards = self._cards
        # 决策出口守卫(次序 = 候选空臂 → 返回契约 → 值域;均在任何点击
        # 之前):候选空 = 具名 fail 零盲发(op-layer.md §1.1 出口③)/
        # 返回 None/词表外 = 具名 fail 零盲发(出口③)/idx 越界 = 守卫
        # 断言(op-layer.md §1.3)。
        _match = getattr(self.ctx, 'cw_match', None)
        # 无 match 局外不设早退支(画面 op 不支持局外单独调用,op-layer.md
        # §1.1;用户裁决 2026-09-22 全族删门):单跑缺上下文沿正常链路
        # 在此失败即预期,禁回填此类单跑防御分支。
        if not cards:
            return self.round_fail(
                f'决策无有效输出零盲发(候选={len(cards)})')
        pick = _match.strategy.decide_star_tome()
        if not isinstance(pick, CwActionPickStarTomeParam):
            return self.round_fail(
                f'decide_star_tome 决策无有效输出(词表外/None): {pick!r}')
        if not (0 <= pick.idx < len(cards)):
            raise AssertionError(
                f'pick idx 越界(策略器 bug,禁钳位): '
                f'idx={pick.idx} len(候选)={len(cards)} pick={pick!r}')
        pick_name = cards[pick.idx][0]
        log.info('[cw-flow-bookcard] 候选=%s → 选 %s → idx=%d',
                 [c[0] for c in cards], pick_name, pick.idx)
        # 机械交回(验证废除):弹窗关没关由下一轮重入裁决(本方法顶部
        # _pick_pending 分支),chosen_tome/ConfirmTome 到账随裁决出口。
        # round_wait 推进循环(不烧节点重试预算,无防御上限)。
        self._pick_pending = pick_name
        # 选卡链经工厂(点卡即选机械链在 ``CwActionPickStarTomeOp`` 内,
        # 本 op 只决策;定位点 = 动作 op 自容器 ``star_tome_opts_xy`` 按
        # idx 取,op-layer.md §1.1 :35)。派发 = 直发策略产实例(idx 即
        # 策略产值;守卫①②③派发前置)。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=pick.idx)
        action_op_for(pick, self.ctx, _env).execute()
        return self.round_wait('选卡点击已发,重入观察裁决')

    def _settle_picked_tome(self, pick_name: str) -> None:
        """重入裁决出口的登记面(弹窗已关 = 选卡落地):到账登记(ConfirmTome:
        owned += 星徽)+ chosen_tome 写端。装备名与注册表对齐
        「X星徽」(标准化阵营名回拼;已是全名则原样)。"""
        if not pick_name:
            return
        from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
            register_confirm_arrival,
        )
        _eq_name = pick_name if pick_name.endswith('星徽') else f'{pick_name}星徽'
        _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        register_confirm_arrival(_sess, 'ConfirmTome', _eq_name,
                                 produced_by='CwScreenBookcard')
        # GameState 写端(chosen_tome = 卡名,选卡落地后写;单次逻辑写入,
        # 申报豁免;CwScreenMegastar chosen_megastar 同式)。候选读取链在役
        # +建档在册,tome 非「暂无画面建档」屏——写端自此接通。
        if _sess is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            # 渠道②签名(②类属 = op 类名;sig 必填,校验单一源 =
            # ``kernel/cw_game_state.py::_validate_sig``)
            game_state_of(_sess).write_logic(
                game_state_of(_sess).chosen_tome,
                pick_name,
                produced_by='CwScreenBookcard',
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenBookcard', mode='compute'))
