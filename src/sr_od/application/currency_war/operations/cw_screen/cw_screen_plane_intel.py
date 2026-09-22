"""货币战争 位面情报采集 op(位面详情屏纯识别,6 node 管线)。

职责:在「货币战争-位面详情」屏恒全采三位面情报:
- **三位面 boss**:每识别 node 点该位面卡 → ``read_plane_detail_nodes``
  动态定位 boss 节点(最右,位置先验)→ 详情条类型名标签验「首领」→
  大图标 SIFT 对拍 boss_avatar 模板库(锁态小图 SIFT 特征塌缩认不出,
  大图标增熵破局)。**boss 节点两种渲染态**:头像态(节点=红框头像,
  大图标 SIFT 命中)与纹章风头像渲染变体(节点=金色纹章图案,图案即
  boss 的纹章风头像——模板库缺该风格致 SIFT 未命中,属**识别能力缺口**
  非「游戏侧不透露身份」,证据帧 = sr-od-test/screens/货币战争-位面详情/
  位面详情-纹章风头像-run30.png)。两种态统一走同一失败语义:**识别
  失败 = node 重试,耗尽 = op fail 响亮暴露,无 None/占位/降级分支**
  (把识别失败降级为 None 违反对账真值纪律;纹章风模板采集批外立项前,
  含该类 boss 的对局接管会响亮失败,属预期失败显影);
- **敌人词缀**:位面详情词缀横条随采(位面1 同帧读一次,词缀不随位面卡
  切换变;空 = 无词缀,上报走幂等门);
- **位面节点带**/难度参考值:节点序列随采存(node6 统一落账);难度
  参考值每个识别 node 同帧顺带读(node6 逐位面落账;生产难度主源 =
  备战旗牌两级管线不变)。

入口/出口契约:
- 入口:已在位面详情屏(前提;开/关转场归编排 op CwEntryPlaneIntel,
  本 op 不开屏不关屏)。node1 内置门:非位面详情屏 = round_fail +
  存证截图(调用时机错误,不进重试空转);
- 出口:留在位面详情屏(关闭归编排 op);上报经
  :func:`report_screen_plane_intel_obs` 写门落容器(唯一一份写门住
  kernel 屏文件),台账/难度/词缀登记走 session 通道(node6 簇,
  best-effort 不阻塞上报主链)。

节点图(6 node,@node_from 显式边):识别位面1 → 点开位面2 → 识别位面2
→ 点开位面3 → 识别位面3 → 上报。点开节点带转移证据(详情条联动:
节点编号 OCR 位面段 = 目标位面);识别失败重试预算:识别 node = 3、
点开 node = 2,耗尽 = op fail(瞬时噪声由框架重试覆盖)。

坐标全走 screen_info area;boss 节点圆由 ``read_plane_detail_nodes``
动态定位(节点数随位面/投资策略变,不硬编码)。
"""
import contextlib
import logging
import re
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_game_state import (
    gs_of_ctx,
)
from sr_od.application.currency_war.kernel.cw_screen_report.plane_intel import (
    CwScreenPlaneIntelObs,
    report_screen_plane_intel_obs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)

#: 位面详情屏(画面档 docs/game/screens/货币战争-位面详情.md)
_PD_SCREEN: str = '货币战争-位面详情'
#: 三张位面卡 area(点位面卡中心切换选中;节点带随选中位面切换)
_PLANE_CARD_AREAS: tuple[str, ...] = ('按钮-位面卡1', '按钮-位面卡2', '按钮-位面卡3')

# 用户定值等待(切卡动画短):点位面卡/boss 节点后等动画落定再读。
_PLANE_SWITCH_WAIT_S: float = 2.0
_BOSS_CLICK_WAIT_S: float = 1.5


class CwScreenPlaneIntel(SrOperation):
    """位面详情纯识别(6 node 管线;接管局补采识别本体,编排归
    CwEntryPlaneIntel)。"""

    SCREEN_NAME: ClassVar[str] = _PD_SCREEN

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面情报采集')
        # 三位面 boss 身份(3 槽保位;识别 node 只落非 None 值,失败即 op
        # 级响亮失败——到上报节点时三槽恒全有值,容器侧 None 槽语义 =
        # 简报源未读得,不由本 op 产生)。
        self._plane_bosses: list[str | None] = [None, None, None]
        self._affixes: list[str] = []     # 词缀横条(位面1 同帧读一次)
        # 位面节点序列采集面(键 = 位面号 1 基;值 = 槽类型序,下标 i =
        # 第 i+1 轮;node6 经台账口统一落账并回填 boss 位)。
        self._detail_seqs: dict[int, list[str | None]] = {}
        # 敌人难度参考值采集面(键 = 位面号 1 基;识别 node 同帧顺带读,
        # node6 逐位面落账)。
        self._difficulty_refs: dict[int, int] = {}
        # 上报节点产物(统一形态观察类,挂实例属性供测试与留证)。
        self._obs: CwScreenPlaneIntelObs | None = None

    # ---- 内部工具 -------------------------------------------------------

    def _area_center(self, area_name: str, screen_name: str = _PD_SCREEN) -> Point | None:
        """screen_info area → 中心点(坐标单一源;无 area → None)。"""
        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, area_name, screen_name)
        if r is None:
            return None
        return Point((r.x1 + r.x2) // 2, (r.y1 + r.y2) // 2)

    def _plane_no_on_detail_bar(self, screen) -> int | None:
        """详情条联动证据:节点编号「位面-轮次」OCR → 位面号(1 基)| None。

        节点详情条随选中位面卡联动(编号首位 = 当前选中位面);读不出
        (过渡帧/OCR 失败)→ None,由调用方按未联动处置。
        """
        from sr_od.application.currency_war.kernel.cw_obs_core import (
            _area_rect,
            _ocr,
        )
        rect = _area_rect(self.ctx, '文本-节点编号', _PD_SCREEN)
        if rect is None:
            return None
        for r in _ocr(self.ctx, screen, rect):
            m = re.match(r'\s*(\d+)\s*[-—–]\s*\d+', r.data or '')
            if m:
                return int(m.group(1))
        return None

    def _select_plane(self, plane_no: int) -> OperationRoundResult | None:
        """点位面卡切换选中位面 + 转移证据(详情条联动)。

        点「已生效」必须验联动:点击可能没落,下一个识别节点会在错误
        位面上继续跑。证据 = 节点编号 OCR 位面段 == 目标位面;未联动 =
        round_retry(点开 node 重试账),None = 已选中继续。
        """
        card = self._area_center(_PLANE_CARD_AREAS[plane_no - 1])
        if card is None:
            return self.round_fail(
                f'位面卡 area 缺失:{_PLANE_CARD_AREAS[plane_no - 1]}')
        self.ctx.controller.click(card)
        time.sleep(_PLANE_SWITCH_WAIT_S)
        screen = self.screenshot()
        if self._plane_no_on_detail_bar(screen) == plane_no:
            return None
        return self.round_retry(
            f'位面{plane_no}卡已点但详情条未联动(节点编号位面段不符),重重点')

    def _boss_node_center(self, slots: list | None = None) -> Point | None:
        """当前位面节点条的最右(boss)节点圆心(read_plane_detail_nodes 动态定位)。

        位置先验(最右=首领):详情条标签验证承接先验失效(标签非首领
        → node 重试账)。``slots`` 可传调用方已读的详情条槽列表(同帧
        复用,免双读);None 时就地读。
        """
        from sr_od.application.currency_war.obs.cw_observation import (
            read_plane_detail_nodes,
        )
        if slots is None:
            slots = read_plane_detail_nodes(self.ctx, self.last_screenshot)
        if not slots:
            return None
        s = slots[-1]
        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, '区域-节点条', _PD_SCREEN)
        # 兜底字面量:area 缺失(离线/档案损坏)时的节点条原点(1080p 实测值)
        ox, oy = (r.x1, r.y1) if r is not None else (385, 514)
        return Point(s.cx + ox, s.cy + oy)

    def _read_boss_big_icon(self, plane_no: int) -> str | None:
        """详情条 boss 大图标 → SIFT 对拍 boss_avatar 库 → boss 名 | None。

        大图标 area「区域-boss大图标」(~107px,特征 70+ vs 节点小图 ~17);
        未命中 → None(记日志留证;SIFT 断层判据防次名撞分)。
        """
        import cv2 as _cv2

        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        from sr_od.application.currency_war.obs.cw_node_reader import match_boss_sift
        r = _area_rect(self.ctx, '区域-boss大图标', _PD_SCREEN)
        if r is None:
            return None
        from sr_od.application.currency_war.obs import cw_observation as _cwo
        if not _cwo._BOSS_TEMPLATES:
            _cwo.read_plane_detail_nodes(self.ctx, self.last_screenshot)   # 懒加载预热
            if not _cwo._BOSS_TEMPLATES:
                return None
        patch = self.last_screenshot[r.y1:r.y2, r.x1:r.x2]
        gray = _cv2.cvtColor(patch, _cv2.COLOR_RGB2GRAY)
        hit = match_boss_sift(gray, _cwo._BOSS_TEMPLATES)
        if hit is None:
            _log.info('[cw-plane-intel] 位面%d 大图标 SIFT 未命中(拒判保守;'
                      '模板库缺该风格亦落此,响亮失败待模板批补)', plane_no)
            return None
        name, good = hit
        _log.info('[cw-plane-intel] 位面%d boss=%s(SIFT 好匹配 %d)',
                  plane_no, name, good)
        return name

    def _recognize_current_plane(self, plane_no: int) -> OperationRoundResult:
        """单位面识别(现机制复用,识别 node 1/3/5 共用体)。

        流程:读节点条 → 点 boss 节点 → 详情条标签验「首领」→ 大图标
        SIFT。失败语义(响亮暴露,无 None/占位/降级分支):节点条读不出 /
        标签未读出 / 非首领 / SIFT 未命中 = round_retry(识别 node 重试账,
        耗尽 = op fail)。同帧顺带采集:词缀横条(仅位面1)、敌人难度
        参考值(逐位面)、节点序列采集面(node6 统一落账)。
        """
        screen = self.screenshot()
        from sr_od.application.currency_war.obs.cw_observation import (
            read_plane_detail_nodes,
        )
        slots = read_plane_detail_nodes(self.ctx, screen)
        boss_pt = self._boss_node_center(slots)
        if boss_pt is None:
            return self.round_retry(f'位面{plane_no} 节点条未读出(过渡帧/渲染态)')
        if not self._affixes and plane_no == 1:
            from sr_od.application.currency_war.obs.cw_briefing_obs import (
                read_detail_affixes,
            )
            self._affixes = read_detail_affixes(self.ctx, screen)
            if self._affixes:
                _log.info('[cw-plane-intel] 词缀随采(位面详情横条):%s',
                          self._affixes)
        # 敌人难度参考值(同帧顺带;只存参考,生产难度主源 = 备战旗牌
        # 两级管线不变;读缺/异常不阻塞识别主链)。
        with contextlib.suppress(Exception):
            from sr_od.application.currency_war.obs.cw_observation import (
                read_plane_detail_difficulty,
            )
            _dv = read_plane_detail_difficulty(self.ctx, screen)
            if _dv is not None:
                self._difficulty_refs[plane_no] = _dv
        # 节点序列采集面:该位面全节点预览序列随采随存(node6 统一落账
        # 并按位置先验回填 boss 位)。
        if slots:
            self._detail_seqs[plane_no] = [
                getattr(s, 'node_type', None) for s in slots]
        self.ctx.controller.click(boss_pt)
        time.sleep(_BOSS_CLICK_WAIT_S)
        self.screenshot()
        from sr_od.application.currency_war.obs.cw_observation import (
            read_detail_node_type_label,
        )
        label = read_detail_node_type_label(self.ctx, self.last_screenshot)
        if not label:
            return self.round_retry(
                f'位面{plane_no} 详情条类型名未读出(过渡帧/OCR失败)')
        if '首领' not in label.replace(' ', ''):
            return self.round_retry(
                f'位面{plane_no} 点到的非首领节点(标签={label}),位置先验失效兜底')
        name = self._read_boss_big_icon(plane_no)
        if name is None:
            return self.round_retry(
                f'位面{plane_no} 大图标 SIFT 未命中(模板库缺该风格或瞬态噪声)')
        self._plane_bosses[plane_no - 1] = name
        return self.round_success(f'位面{plane_no} boss={name}')

    # ---- 节点图(6 node 管线) -------------------------------------------

    @operation_node(name='识别位面1', is_start_node=True, node_max_retry_times=3)
    def recognize_plane_1(self) -> OperationRoundResult:
        """入口门(非位面详情屏 = 调用时机错误,存证后 fail 不空转)→
        选中位面卡1(进屏初始选中位面随接管时点变,恒点卡1 保证从
        位面1起采)→ 识别位面1。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, _PD_SCREEN, '标识-位面详情标题',
                crop_first=False).is_success:
            self.save_screenshot()   # 存证:调用者看 status 即知画面错在哪
            return self.round_fail(
                f'不在{_PD_SCREEN}(调用时机错误:编排 op 须先打开位面详情)')
        rs = self._select_plane(1)
        if rs is not None:
            return rs
        return self._recognize_current_plane(1)

    @node_from(from_name='识别位面1')
    @operation_node(name='点开位面2', node_max_retry_times=2)
    def open_plane_2(self) -> OperationRoundResult:
        """点开位面卡2(带转移证据:详情条节点编号联动到 2-x)。"""
        rs = self._select_plane(2)
        return rs if rs is not None else self.round_success('位面2已选中')

    @node_from(from_name='点开位面2')
    @operation_node(name='识别位面2', node_max_retry_times=3)
    def recognize_plane_2(self) -> OperationRoundResult:
        """识别位面2(同识别体)。"""
        return self._recognize_current_plane(2)

    @node_from(from_name='识别位面2')
    @operation_node(name='点开位面3', node_max_retry_times=2)
    def open_plane_3(self) -> OperationRoundResult:
        """点开位面卡3(带转移证据:详情条节点编号联动到 3-x)。"""
        rs = self._select_plane(3)
        return rs if rs is not None else self.round_success('位面3已选中')

    @node_from(from_name='点开位面3')
    @operation_node(name='识别位面3', node_max_retry_times=3)
    def recognize_plane_3(self) -> OperationRoundResult:
        """识别位面3(同识别体)。"""
        return self._recognize_current_plane(3)

    @node_from(from_name='识别位面3')
    @operation_node(name='上报')
    def report(self) -> OperationRoundResult:
        """整理观察数据上报:写门落容器(gs 通道)+ 台账/难度/词缀登记
        (session 通道,与写门同居本簇但分通道;异常口径 = best-effort,
        台账/登记异常不阻塞上报主链)。

        写门 = :func:`report_screen_plane_intel_obs`(唯一一份,住 kernel
        屏文件):boss 已有真值不覆写、词缀幂等门。session 缺席(不在对局)
        = 无处落真值,响亮 fail 不静默丢。
        """
        sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        if sess is None:
            self.save_screenshot()
            return self.round_fail('上报时无对局 session(不在对局中),真值无处落')
        obs = CwScreenPlaneIntelObs(on_screen=True, screen=self.last_screenshot,
                                    plane_bosses=list(self._plane_bosses),
                                    enemy_affixes=list(self._affixes))
        self._obs = obs
        report_screen_plane_intel_obs(gs_of_ctx(self.ctx, sess), obs)
        # 节点序列台账落账(session 通道):详情条源 + boss 位按「首领 =
        # 位面最后节点」位置先验回填(回填依据 = 本 op 标签验证语义)。
        with contextlib.suppress(Exception):
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                fill_boss_by_position,
                ledger_update_plane,
            )
            for _p, _seq in sorted(self._detail_seqs.items()):
                _changed = ledger_update_plane(
                    sess, _p, fill_boss_by_position(_seq), 'plane_detail')
                _log.info('[cw-plane-intel] 台账落账 p%d(%s)%s:%s',
                          _p, 'plane_detail',
                          '(有变更)' if _changed else '(无变更)',
                          fill_boss_by_position(_seq))
        # 敌人难度参考值逐位面落账(session 通道)。
        with contextlib.suppress(Exception):
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                get_node_ledger,
            )
            _ledger = get_node_ledger(sess)
            if _ledger is not None:
                for _p, _dv in sorted(self._difficulty_refs.items()):
                    _ledger.difficulty_ref[_p] = _dv
                    _log.info('[cw-plane-intel] 位面%d 敌人难度参考=%d', _p, _dv)
        # 词缀效果账本登记(上报后登记;接管局这是词缀登记唯一活源——
        # 简报侧登记挂点在接管局不运行)。命中结构化注册才入账本,登记
        # 体按在册条目幂等(补采重跑不双登记;登记面纪律 =
        # effect-domain.md §7.6 词缀源节)。
        if self._affixes:
            with contextlib.suppress(Exception):
                from sr_od.application.currency_war.kernel.cw_affix_effects import (
                    register_affixes_from_names,
                )
                _reg = register_affixes_from_names(sess, list(self._affixes))
                if _reg:
                    _log.info('[cw-plane-intel] 词缀效果账本登记: %s', _reg)
        return self.round_success(
            f'位面情报上报:boss={obs.plane_bosses} 词缀={obs.enemy_affixes}')
