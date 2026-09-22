
"""货币战争 投资环境 3 选 1 op(两 node 直继承 SrOperation)。

观察 node = 入口门(标识-投资环境,miss = round_fail 交回外循环重判)
→ **一次读全**(3 张环境卡名 + 全局刷新剩余次数,零稳定帧等待一次读
全)→ 观察标准化门(逐候选两段转换:形变归一精确匹配 → LCS 相似匹配
兜底;任一候选转换失败 ∨ 两候选命中同一注册名 = round_fail 零写零
上报,交外循环重观察——规范 = screens/op-layer.md §1.1)→
``report_screen_invest_env_obs`` 落容器(候选 ``invest_env_opts`` 值域 =
标准注册名 + ``env_refresh_left`` 观察写端)→ obs 挂实例属性。决策动作
node = 零参决策(候选自容器槽;空候选/无有效输出 = round_fail 显式失
败,零盲发 = op-layer.md §1.1 + action_ops.md §1 增补 2)→ 环境帧刷新
判据可发整组重掷(终结交回)∨ 点**最优**卡底 + 确认链经
``CwActionPickInvestOp`` 派发(上报纯 idx,名字自容器标准名单一源)→
**round_success 终结交回**(选完即交回 = op-layer.md §1.1;确认未生效
= 代码 bug,overlay 残留由外循环按当前画面重识别重派,修法 = 点击链
可靠性——action_ops.md §1 增补 2 即时上报契约)。

环境刷新 = 终结动作(刷新 = 唯一引入新事实的动作,须交回外循环重观察;
结构语义 = screens/op-layer.md §1.4):决策返回 ``refresh_slots`` 非空 ∧
剩余次数授权(obs 携带 + 容器 ``env_refresh_left``)→ 点刷新圆钮一次
(文本锚定偏移)→ 动画窗固定等待 → 零效果缺陷留证对账 → 本访问即终结
交回。

选择事实(active_env)经动作落地链写:动作 op 确认后立即自上报 →
``gain_invest_env`` 整链(active_env 注册 + portal 登记 + on_env_gained
效果枚举,正本 = game_state/gain-chain.md);画面 op 零选择写点。计数 =
屏上剩余次数观察真值(屏上数字即真值,正本 = game_state/fields.md
§3.4.3),写端 = 观察 report 摄入。局外无 match = 零决策零点击
round_success 终结交回(遭遇屏在册先例同款;画面 op 不产决策、不支持
局外单独调用——op-layer.md §1.1)。本屏 sim 腿 = 不适用(sim 端口
适配器未建),等价判据主承重 = 实机在册行为锁。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from one_dragon.utils.str_utils import longest_common_subsequence_length
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    is_known_env,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.invest_env import (
    CwScreenInvestEnvObs,
    report_screen_invest_env_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickInvestEnvParam,
    CwActionRefreshInvestCardsParam,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_invest_refresh_counts
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenInvestEnv(SrOperation):
    """投资环境 3 选 1:零参决策(候选自容器槽,策略器 ``decide_invest_env``;
    判据 kernel ``decide_event``)→ 刷新终结臂 ∨ 选卡确认链派发。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资环境'   # screen_info 画面(currency_war_invest_env.yml)
    # 卡选中点击 Y:screen_info「区域-卡牌描述行」center.y;常量=screen_info 缺失兜底。
    # 实机点验:立绘在卡顶 y≈100-400(点立绘/卡名 y390 不选中且开角色详情);
    # **描述区 y≈450 才选中**(立绘下方);卡底 y700 无效。区别 invest_strategy(描述区 y545)。
    CARD_CLICK_Y: ClassVar[int] = 450   # 兜底;首选 area_center('区域-卡牌描述行')
    # 卡名行 center-y 过滤带(排除标题 y≈98 / 描述 y≈419+ / 确认 y≈982)。
    # 卡名 y 随立绘漂移(实机见过 375-378 / 392),带宽 [360,410] 覆盖实测漂移域。
    NAME_CY_LO: ClassVar[int] = 360
    NAME_CY_HI: ClassVar[int] = 410
    # 非卡名(同 y 行可能误入或已知 UI 文本)
    _EXCLUDE: ClassVar[set[str]] = {'投资环境', '攻略', '确认', '角色', '装备', '剩余次数：1'}
    # 变异窗宽限(秒):覆盖确认动画 + 节点行刷新重试窗;超时后三票校验恢复落账。
    ENV_GRACE_S: ClassVar[float] = 45.0
    # 确认按钮:screen_info「按钮-确认」center;常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')
    # ---- 环境刷新执行链常量(执行层时序/几何常量,非策略数值,
    # ADR-0529 先例)----
    # 刷新圆钮 = 「剩余次数」文本中心 + 固定偏移(文本锚定,ADR-0600 §3.4 先例
    # ——单帧证据不足判文本漂移形态,固定 area 不可行;遭遇屏/策略屏同款)。
    # 偏移实测收口(归档帧 sr-od-test/screens/货币战争-投资环境/default.webp
    # 亮像素簇质心:钮心 x≈671、计数文本中心 x≈772,y 同带 ≈983)→ dx ≈ −101。
    # 偏移错 → 刷新未命中(计数不扣、牌不变):零效果只落缺陷台账留证;
    # 重进后计数未扣、预算仍在 → 再次刷新,每圈耗 1 次外环重进,能力退化
    # 非事故,复测即修。
    _REFRESH_BTN_DX: ClassVar[int] = -101
    # 刷新后等待(整组重掷动画覆盖;沿策略屏 REFRESH_ANIM_WAIT_S 同值先例)。
    REFRESH_ANIM_WAIT_S: ClassVar[float] = 1.5
    # 观察标准化门 LCS 兜底阈值(op-layer.md §1.1 第二段;坐标系 = 归一候选
    # 与注册表名的最长公共子序列长度 / 注册表名长度):0.75 = 4 字卡名容
    # 1 字 OCR 误读(3/4),更长名更宽——识别质量下限,非唯一防线:0.75
    # 挡不住共享词素族跨名借分(如「XX概念股」族单字误读可对两名同分
    # 0.8),该族必需防线 = 分差拒判(下常量);残余风险 = 分差内真歧义
    # 被判失败,多一轮重读(已定稿登记)。
    ENV_LCS_THRESHOLD: ClassVar[float] = 0.75
    # 歧义拒判分差(与阈值同量纲的 LCS/注册表名长度分数;判据 = 过阈值的
    # 最高分与次高分之差):低于本差 = 注册表内歧义不可分辨 → 转换失败
    #(实机形态:「击口概念股」对击破/追击概念股同分 0.8——卡面与注册表
    # 一一对应,近分 = 必有误读,禁猜)。0.15 = 真命中最小分辨差下探留
    # 裕度(5 字共享词素族 1 字误读 0.8 与后缀借分 3/5 = 0.6 差 0.2);
    # 同分/近分一律拒判交回重观察。
    ENV_LCS_AMBIGUITY_MARGIN: ClassVar[float] = 0.15

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资环境')
        # 刷新零效果留证证据(刷新臂只读不比,读数原样携带——
        # 元组 = (刷前计数, 刷前名集, 刷后计数, 刷后名集);
        # 消费点 = 刷新臂终结交回出口 ``_reconcile_refresh_no_effect``
        # 对账,消费即清;None = 无待评证据)。
        self._refresh_evidence: tuple[int, list[str],
                                      list, list[tuple[str, int]]] | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenInvestEnvObs | None = None

    def _read_options(self, screen) -> list[tuple[str, int]]:
        """OCR 3 张卡的 ``(名字, 名字 center-x)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (CwScreenInvestEnv.NAME_CY_LO <= cy <= CwScreenInvestEnv.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestEnv._EXCLUDE):
                opts.append((text, mrl.max.center.x))
        opts.sort(key=lambda t: t[1])
        return opts

    def _standardize_options(
            self, opts: list[tuple[str, int]]) -> list[tuple[str, int]] | None:
        """观察标准化门(op-layer.md §1.1;``_read_options`` 读出后、组装
        obs 前逐候选两段转换):①形变归一(``normalize_invest_name`` 单一源)
        精确命中注册表 → 标准名;②不中再 LCS 相似匹配(阈值 =
        ``ENV_LCS_THRESHOLD`` ∧ 最高分与次高分差 ≥
        ``ENV_LCS_AMBIGUITY_MARGIN``——分差过近 = 注册表内歧义不可分辨);
        两段皆不中 ∨ 歧义 = 转换失败。

        任一候选转换失败 ∨ 两候选命中同一注册名(选项互斥屏,卡面与注册
        表一一对应,重复名 = 必有误读)= 识别质量不足以区分 → 返回 None:
        观察 node round_fail 整函数早退,零写容器零上报,交外循环重观察
        重读。容器 ``invest_env_opts`` 值域自此 = 标准注册名。"""
        registry = list(INVESTMENT_ENVS)
        resolved: list[tuple[str, int]] = []
        seen: set[str] = set()
        for name, x in opts:
            canon = normalize_invest_name(name)
            if canon not in INVESTMENT_ENVS:
                canon = self._lcs_resolve(canon, registry)
            if not canon or canon in seen:
                return None
            seen.add(canon)
            resolved.append((canon, x))
        return resolved

    @classmethod
    def _lcs_resolve(cls, canon: str, registry: list[str]) -> str:
        """LCS 兜底解析(阈值过滤 + 次高分歧义拒判):评分 = LCS 长度 /
        注册表名长度(与 ``find_best_match_by_lcs`` 同式,同分取注册表序
        首个);无过阈值命中 ∨ 最高/次高分差 < ``ENV_LCS_AMBIGUITY_MARGIN``
        → 返回 ''(转换失败),否则返回最高分标准名。"""
        scored: list[tuple[float, str]] = []
        for reg_name in registry:
            pct = (longest_common_subsequence_length(canon, reg_name)
                   / len(reg_name))
            if pct >= CwScreenInvestEnv.ENV_LCS_THRESHOLD:
                scored.append((pct, reg_name))
        if not scored:
            return ''
        scored.sort(key=lambda t: t[0], reverse=True)   # 稳定排序:同分保注册表序
        if (len(scored) > 1 and scored[0][0] - scored[1][0]
                < CwScreenInvestEnv.ENV_LCS_AMBIGUITY_MARGIN):
            return ''
        return scored[0][1]

    def _match_gs(self):
        """局容器单例读口(无局/局外交回路径 = None,调用方零行为跳过)。"""
        _match = getattr(self.ctx, 'cw_match', None)
        return getattr(_match, 'gs', None) if _match is not None else None

    def _reconcile_refresh_no_effect(self) -> None:
        """刷新零效果留证对账(消费点 = 刷新臂终结交回出口):携带证据
        (刷前计数/名集 + 刷后帧机械重读)在此评「计数未扣 ∧ 名集未变」→
        落缺陷台账(零决策零改道);任一侧读缺 = 过渡帧不可判,不猜。
        消费即清(每次刷新恰评一次)。缺陷的实际触发形态 = 刷新未生效而
        overlay 残留——证据为当次刷新的机械重读快照,评点住终结交回出口
        与该形态覆盖面等价(每笔证据恰评一次)。"""
        _ev = self._refresh_evidence
        if _ev is None:
            return
        self._refresh_evidence = None
        _c, _pre_names, _counts2, _opts2 = _ev
        if not (bool(_counts2) and _counts2[0][0] >= _c
                and [n for n, _ in _opts2] == _pre_names):
            return
        try:
            from sr_od.application.currency_war.telemetry import (
                defects as cw_defects,
            )
            cw_defects.record_defect(
                'invest_env', 'refresh_no_effect',
                expected=f'计数<{_c} 或名集变化',
                observed=f'计数={_counts2[0][0]},名集未变',
                verdict='留证-刷新零效果(零决策)',
                reader_source='cw_screen_invest_env',
                note='执行侧判效已拆(判效归一),仅机械留证;'
                     '比对宿主 = 刷新臂终结交回出口对账,消费即清',
                gap_large=False,
                severity=cw_defects.SEVERITY_L2_RECORD)
        except Exception:   # noqa: BLE001  留证不阻塞交回
            pass

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 一次读全 + 观察标准化门 → report 落容器。

        门 miss = round_fail 早退交回外循环重判(现役首闸同 status)。
        零稳定帧等待;一次读全 = 环境卡名 + 全局刷新剩余计数,同一帧
        读取。标准化门任一候选转换失败(含两候选命中同名)= round_fail
        整函数早退,零写容器零上报(op-layer.md §1.1)。门后 report 摄入
        (候选 + env_refresh_left,match/gs 缺席的局外交回路径跳过
        report)。"""
        screen = self.last_screenshot
        _hit = self.round_by_find_area(screen, CwScreenInvestEnv.SCREEN_NAME,
                                       '标识-投资环境').is_success
        log.info(f'[cw-env] enter find_area(标识-投资环境)={_hit}')
        if not _hit:
            return self.round_fail('非投资环境屏')
        screen = self.screenshot()
        counts = read_invest_refresh_counts(self.ctx, screen, 'env')
        opts = self._standardize_options(self._read_options(screen))
        if opts is None:
            log.warning('[cw-env] 观察标准化门失败:候选转换不到标准注册名'
                        '(零写零上报,交回重观察)')
            return self.round_fail('投资环境候选标准化失败(零写零上报,交回重观察)')
        obs = CwScreenInvestEnvObs(
            hit=True,
            options=opts,
            refresh=(counts[0] if counts else None),
            screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_invest_env_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """零参决策 → 环境刷新终结交回 / 选卡+确认后立即终结 → round_success。

        选卡链派发后本访问即终结交回外循环(选完即交回 = op-layer.md
        §1.1;确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重
        识别重派,修法 = 点击链可靠性,action_ops.md §1 增补 2)。"""
        obs = self._obs
        return self._decide_and_act(obs)

    def _decide_and_act(self, obs: CwScreenInvestEnvObs) -> OperationRoundResult:
        """决策+动作内聚体(决策面):零参决策(候选自容器槽,观察标准化
        门已保证值域 = 标准注册名)→ 环境刷新终结动作(obs 余量授权 +
        容器 env_refresh_left)→ 点最优卡底 → 确认链派发(动作 op 内
        即时上报)→ round_success 终结交回。空候选/决策无有效输出 =
        round_fail 显式失败(零盲发 = op-layer.md §1.1 + action_ops.md
        §1 增补 2「没有选到就是代码 bug」);局外无 match = 零决策零点击
        round_success 终结交回(遭遇屏在册先例同款,op-layer.md §1.1)。"""

        opts = obs.options
        names = [n for n, _ in opts]
        if not names:
            # 空候选 = OCR 读缺 = bug 面:显式失败交外循环重观察重派
            #(零盲发,契约与局外无关,先于局外出口)。
            return self.round_fail('投资环境候选 OCR 读缺(零盲发,显式失败)')
        for _n in names:
            if not is_known_env(_n):
                log.warning(f'[cw-env] 投资环境名不在注册表(数据缺口): {_n!r} → 该项 env_fit 走中性 fallback')
        match = self.ctx.cw_match
        if match is None or getattr(match, 'gs', None) is None:
            # 局外(无对局上下文)= 零决策零点击 round_success 终结交回
            #(遭遇屏在册先例同款;决策控制分层铁律:画面 op 不产决策,
            #不设兜底决策路径——op-layer.md §1.1)。
            log.info('[cw-env] 局外无 match → 零决策零点击终结交回')
            return self.round_success('局外无 match,零决策零点击终结交回',
                                      wait=1.5)
        # 零参决策(写槽已由观察轮 report 落容器 invest_env_opts;候选 =
        # 标准注册名)。输出 = 单一 CwAction:CwActionRefreshInvestCardsParam
        #(整组刷新建议)/ CwActionPickInvestEnvParam(选卡)互斥单发。
        act = match.strategy.decide_invest_env()
        refresh_slots: tuple[int, ...] = ()
        if isinstance(act, CwActionRefreshInvestCardsParam):
            refresh_slots = act.slots
        # ===== 环境刷新 = 终结动作(刷新 = 唯一引入新事实的动作,须交回
        # 外循环重观察;环境屏 = 整组重掷:单全局钮 + 单计数。闸输入 =
        # obs.refresh(同帧一次读全,决策环零识别)+ 容器 env_refresh_left;
        # 读缺 = 无授权失败安全)=====
        if refresh_slots and obs.refresh is not None:
            _budget, _tx, _ty = obs.refresh
            # 闸:容器剩余口径对照(≤0 = 尽;键缺失由 obs 现值裁决)。
            _mgs = self._match_gs()
            _left = (_mgs.env_refresh_left.value
                     if _mgs is not None else None)
            if _budget > 0 and not (_left is not None and _left <= 0):
                # 点钮:「剩余次数」文本中心 + 固定偏移(safe_click 自带
                # mouse_move 缓解)。
                safe_click(self,
                           Point(_tx + CwScreenInvestEnv._REFRESH_BTN_DX, _ty),
                           tag='cw-env')
                # 动画窗固定等待(整组重掷动画覆盖;机械执行时序,非判效)。
                time.sleep(CwScreenInvestEnv.REFRESH_ANIM_WAIT_S)
                # 刷后帧机械重读(零比对零判效——读数原样携带进留证证据,
                # 「计数未扣 ∧ 名集未变」的零效果判定经对账评点落缺陷台账;
                # 判效权归对账)。
                _after = self.screenshot()
                _counts2 = read_invest_refresh_counts(self.ctx, _after, 'env')
                _opts2 = self._read_options(_after)
                self._refresh_evidence = (
                    _budget, [n for n, _ in opts], _counts2, _opts2)
                log.info(f'[cw-env] 环境刷新终结交回:计数 {_budget}→'
                         f'{_counts2[0][0] if _counts2 else "读缺"},'
                         f'重进后重观察重分类')
                # 零效果留证对账(消费即清)→ 终结交回:选卡/确认均不在
                # 本访问;外循环重进 = 入口重建。
                self._reconcile_refresh_no_effect()
                return self.round_success('投资环境刷新终结交回(重进重观察重分类)',
                                          wait=1)
            # 闸全败(建议帧但计数无授权)→ 同访问重调落选卡:策略侧同帧
            # 去重(建议帧首调发建议、紧随重调落选卡),零选卡漂移。
            act = match.strategy.decide_invest_env()
            if isinstance(act, CwActionRefreshInvestCardsParam):   # 防御:策略未实现去重
                act = None
        # ===== 选卡确认链(派发即即时上报,本访问终结交回)=====
        if isinstance(act, CwActionPickInvestEnvParam) and 0 <= act.idx < len(opts):
            chosen, choose_x = opts[act.idx]
            reason = act.reason
            pick_idx = act.idx
        else:
            # 决策无有效选卡输出 = bug 面:显式失败(零盲点)。
            return self.round_fail(f'投资环境决策无有效选卡输出: {act!r}')
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')
        # 选择事实零容器写(active_env 注册在动作落地获得链 gain_invest_env,
        # 动作 op 即时上报;正本 = game_state/gain-chain.md)。

        # 点最优卡底(Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底
        # CARD_CLICK_Y)+ 确认链经工厂派发。
        _sel = area_center(self.ctx, '区域-卡牌描述行', CwScreenInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)

        # 台账:确认前开「投资环境变异窗」豁免——环境选择是位面节点序列唯一
        # 变异源(用户口述),确认到节点行重读刷新之间查表与逐帧校验的不一致
        # 是合法变异,三票校验不得落缺陷台账。重读成功后关窗(置 0)。
        try:
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                get_node_ledger,
            )
            _ledger = get_node_ledger(getattr(getattr(self.ctx, 'cw_match', None), 'session', None))
            if _ledger is not None:
                _ledger.env_grace_until = time.monotonic() + CwScreenInvestEnv.ENV_GRACE_S
        except Exception:   # noqa: BLE001  观测面 best-effort
            pass

        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        # 确认钮不进 env(确认查找 = 动作 op 执行体 round_by_find_and_click_area
        # 全族统一,用户裁定 2026-09-22;env.confirm 变体随批退役)。
        _env = OverlayPickExecEnv(op=self, idx=pick_idx, target=target)
        action_op_for(CwActionPickInvestEnvParam(idx=pick_idx, reason=reason),
                      self.ctx, _env).execute()
        # 本访问终结:结果已由动作 op 即时上报写入 game state(active_env
        # 注册 + 赠卡效果;确认未生效 = 代码 bug,见类 docstring)。
        return self.round_success(f'{chosen} 已派发(结果即时上报)', wait=2.0)
