"""货币战争 位面情报采集 op(2026-08-26 佩佩局实证链的产品化)。

职责:在备战画面开位面详情,一次采集三类情报:
- **三位面 boss**:依次点三张位面卡 → 每卡点最右(boss)节点 → 详情条
  类型名标签验「首领」→ 大图标 SIFT 对拍 boss_avatar 20 模板(用户方案:
  「点击最后的节点,下方会有更大的图标」——锁态小图 SIFT 特征塌缩认不出,
  大图标破局:增熵 9:1、绘师 5:2 断层命中)。**boss 节点两种渲染态
  (ADR-0398,run 29/30 同夜实证)**:头像态(节点=红框头像,大图标
  SIFT 断层命中)与**徽章态**(节点=通用金色徽章、详情条=「首领节点」+
  通用描述,**本屏无任何身份信息**——run 30 位面 1 带内 9 圆逐圆 SIFT
  全拒 + 大图标 SIFT 未命中 12 次实证)→ 徽章态位面记 None 跳过
  (``conclude_plane_boss`` 分流),不 retry 空转;
- **敌人词缀**:位面详情词缀横条随采(词缀只在简报/位面详情/敌人信息
  浮层三画面,备战无此条——首版误判备战常驻,空读两轮后用户纠正);
- **位面节点带**:``read_plane_detail_nodes`` 读选中位面节点(类型/序)。

为什么需要(ADR-0397 勘误节):
- **接管场景重采**:对局进行中但 session 无位面序真值(MCP 重启丢内存 / bot 未走
  过简报链)时,位面详情实采是唯一补真值通道(cw_loop 备战稳定帧触发 + 独立
  takeover 入口)。简报读数本身即位面序真值(用户 2026-08-28 裁决,ADR-0397 原结论
  已勘误),开局局简报读得时不走本 op;本 op 采集结果兼作**对账真值源**——采集完成
  后与简报读数逐位面 LCS 比对存证(``cw_briefing_obs.reconcile_briefing_vs_plane_intel``)。

入口/出口契约:
- 入口:备战屏(检测 id_mark 备战标识-购买经验);由调用方在备战态调起。
  ⚠️ 必须是**定型备战帧**——boss 战后位面过场的半开备战帧点不开详情
  (22:17/22:22 两轮实跑 12 retry 全空证);调用方(cw_loop 接管补采)
  自带 2 次重试账,过场帧首试失败后下个稳定备战帧再试。
- **起始位面裁剪**(2026-09-03 用户裁决,接管时序修正):接管链在进详情
  **之前**先在备战帧识别当前节点(顶栏 X-Y,如 2-2)得当前位面,经
  ``start_plane`` 构造参数传入(或本 op 备战入口现读);详情内只采当前
  及之后的位面,之前的位面跳过(已通过节点变暗 ⇒ 详情条识别退化是
  正常态,不是「动画中」)。起始位面全程未取得 → 回退全量采集(保底)。
- 出口:回备战屏(X 点击后验位面详情 id_mark 消失=真转移);采集结果经
  ``ctx.cw_plane_bosses``/``cw_plane_affixes`` 中转(与 ``cw_briefing_*``
  同模式;消费接线批待做,本 op 只负责采集)。
  失败语义分层(W901):详情条静止读不出 = **该位面**情报不可得(记 None
  推进下一位面),不整场失败;仅备战侧读不出/详情开不成/动画超宽上限
  才 op 级失败(留给调用方重试账)。

节点图:两节点,round 语义驱动(同 HandleBriefing 形态):
- ``采集``(start):入口核对(备战→点节点图标开详情 / 已在详情续采;点
  **任意**节点图标都开——不依赖 current 锚,1-7 帧当前槽 V 未过亮门无锚
  实证)→ 三位面循环(点卡→点boss节点→读大图标 SIFT,状态在 self,
  round_wait 自环)→ 三位面齐 → 转 ``关闭``。
- ``关闭``:点 X → 验 id_mark 消失 → 写 ctx 中转 → success。

坐标全走 screen_info area(位面卡×3/boss大图标/词缀横条/关闭/两屏
id_mark/两个节点条);boss 节点圆由 ``read_plane_detail_nodes`` 动态定位
(节点数随位面/投资策略变:位面1=9,位面2/3=7,不硬编码)。
"""
import contextlib
import logging
import time
from typing import Any, ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)

#: 位面详情屏(画面档 docs/game/screens/货币战争-位面详情.md)
_PD_SCREEN: str = '货币战争-位面详情'
_PREP_SCREEN: str = '货币战争-备战'
#: 三张位面卡 area(点位面卡中心切换选中;节点带随选中位面切换)
_PLANE_CARD_AREAS: tuple[str, ...] = ('按钮-位面卡1', '按钮-位面卡2', '按钮-位面卡3')


#: 详情条节点类型名 area(位面详情屏;boss 定位验证锚)
_LABEL_AREA: str = '文本-节点类型名'

# ---- 非clean帧等待门 ---------------------------------------------------
# 背景:2026-08-27 两触发点同签名(run 22:05:23 P1 收尾 / 22:10:16 P2 转换):
# 位面转换/加载动画窗内节点条是残影,短窗连读(~2.5s 3 帧)全部非clean → op
# 失败。治本=「等到 clean 为止 + 宽上限兜底」:非clean 读不再短窗即弃,而是
# 间隔重读给动画时间,超宽上限才真失败(覆盖最慢加载)。
_NODE_BAR_READ_INTERVAL_S: float = 2.0   # 两次重读的间隔(给转换/加载动画时间)
_NODE_BAR_WAIT_CAP_S: float = 90.0       # 非clean 总等待上限,超限才真失败

# 用户定值等待(2026-09-03 第六局接管时序裁决):
# - 进位面详情的开屏等待 ~3s(点节点图标 → 详情开 + 动画落定);
# - 详情内点**位面卡切换**后等 2s 即读,不足再排查识别效率(不在此预加等待)。
_DETAIL_OPEN_WAIT_S: float = 3.0
_PLANE_SWITCH_WAIT_S: float = 2.0

# 静止帧提前放弃(2026-08-30 哨兵 20:22:36 实证:变暗静态条被判「切卡动画中」
# 硬等 90s 后放弃,采集从未通过此门)。区分信号=帧稳定性:真动画(位面转换/
# 加载)帧间必有变化;连续 2 帧零变化(隔一个重读间隔)= 静止渲染态(变暗条/
# 特效遮蔽),继续等不会变 clean → 提前放弃,不等满上限。
_GATE_STATIC_FAIL_FRAMES: int = 2        # 连续 N 帧零变化 → 判静止
_FRAME_DIFF_TOL: float = 1.0             # 降采样灰度平均绝对差 ≤ 该值 = 零变化


def _frame_thumbnail(screen: MatLike) -> Any:
    """截图 → 96x54 灰度缩略图(帧差比较的降采样表示;RGB 输入)。"""
    import cv2 as _cv2
    gray = _cv2.cvtColor(screen, _cv2.COLOR_RGB2GRAY)
    return _cv2.resize(gray, (96, 54))


def _frames_identical(a: Any, b: Any) -> bool:
    """两缩略图是否零变化(平均绝对差 ≤ :data:`_FRAME_DIFF_TOL`;容忍编码/压缩噪声)。"""
    import cv2 as _cv2
    import numpy as _np
    return float(_cv2.absdiff(
        _np.asarray(a, dtype=_np.uint8),
        _np.asarray(b, dtype=_np.uint8)).mean()) <= _FRAME_DIFF_TOL


def conclude_plane_boss(label: str | None, sift_name: str | None) -> tuple[str, str | None]:
    """单位面 boss 读取结论(纯函数,ADR-0398 测试锁锚)。

    输入:详情条节点类型名 OCR(``label``)+ boss 大图标 SIFT 结果(``sift_name``)。
    返回 ``(action, value)``:
    - ``('record', boss名)``:标签=首领 且 SIFT 命中 → 头像态(run29 型)真值;
    - ``('skip', None)``:标签=首领 但 SIFT 未命中 → **徽章态**(run30 型:最右
      节点=通用金色徽章,详情条只有「首领节点」+通用描述,本屏无身份信息;
      渲染确定性,重点也不会变)→ 记 None 跳过,不 retry 空转;
    - ``('retry', 原因)``:标签未读出(过渡帧/OCR 失败)或非首领(点到的不是
      boss 节点——节点带误读/布局变的兜底,位置先验失效信号)。
    """
    if not label:
        return 'retry', '详情条类型名未读出(过渡帧/OCR失败)'
    if '首领' not in label.replace(' ', ''):
        return 'retry', f'点到的非首领节点(标签={label}),位置先验失效兜底'
    if sift_name is None:
        return 'skip', None
    return 'record', sift_name


def node_seq_cross_mismatch(prep_seq: list[str | None],
                            detail_seq: list[str | None]) -> list[int] | None:
    """备战帧 vs 位面详情帧节点序列互证(观测自检框架设计 §1 矩阵行11/§5-B5;
    纯函数可单测)。

    判据(设计原文唯一给到的口径):两读法(read_node_sequence 备战条 /
    read_plane_detail_nodes 详情条,同 CV 核心)对**同一位面**的序列做对拍,
    常态化留证。两读法均已识别的位次类型不一致 → 不一致位次清单(留证);
    任一序列空(非 clean 帧/模板未加载)→ None 不可判不猜;无同识别位 →
    None(无可比位);全可比位一致 → [](对拍通过,不落任何行)。

    边界:两序列长度可不同(备战行含 invest-env 增槽、详情带按位面 9/7 圆),
    只在双方类型均非 None 的位次上对拍、长度差不判(设计未定义长度判据);
    boss 槽两读法均置 None(头像态 Hu 对头像圆无意义,见 cw_node_reader)
    → 自然落入「未识别跳过」,不产生伪不一致。
    """
    if not prep_seq or not detail_seq:
        return None
    mism: list[int] = []
    compared = False
    for i, (a, b) in enumerate(zip(prep_seq, detail_seq, strict=False)):
        if a is None or b is None:
            continue
        compared = True
        if a != b:
            mism.append(i)
    return mism if compared else None


def decide_plane_skip(plane_no: int,
                      start_plane: int | None) -> tuple[bool, str]:
    """单位面「是否跳过采集」判据(纯函数,可单测)。

    语义(2026-09-03 用户裁决,DD-023;第六局接管实证):时序反过来——进位面详情
    **之前**先在备战画面识别当前节点(如 2-2)得当前位面,由此裁剪采集范围:
    **当前位面之前的位面一律跳过**(已通过节点变暗导致详情节点条识别退化
    是正常态,不是「动画中」,重采浪费且低置信;session 侧这些位面本来就该
    有旧数据或不可知)。当前及之后位面正常采集;起始位面无真值(None/0)
    → 不跳,回退全量采集(备战识别失败的保底语义)。

    :param start_plane: 起始采集位面(1-based;None/0 = 未取得,全采回退)。
        来源优先级:调用方传入(接管链备战帧现读)> 本 op 备战帧现读 >
        位面详情顶栏 OCR;全无 = 全采。
    :return: ``(skip, note)``;skip=True 时 note 说明跳过原因,否则为空串。
    """
    if not start_plane or plane_no >= start_plane:
        return False, ''
    return True, f'跳过(位面{plane_no}<起始位面{start_plane},已通过位面不重采)'


class CwScreenPlaneIntel(SrOperation):
    """位面详情:一次采集位面情报(三 boss 大图标 SIFT + 词缀横条 + 节点带;
    接管局补采主通道,亦开局校准通用)。"""

    SCREEN_NAME: ClassVar[str] = _PD_SCREEN

    def __init__(self, ctx: SrContext, start_plane: int = 0):
        """``start_plane``:起始采集位面(1-based;0=未知 → 全采回退)。

        来源 = 接管链在进详情**之前**的备战帧现读(2026-09-03 用户裁决:
        时序反过来,先识别当前节点得当前位面再进详情);调用方没算出时
        本 op 在备战入口自行现读,仍无则全量采集(保底)。
        """
        SrOperation.__init__(self, ctx, op_name='货币战争-位面情报采集')
        self._plane_bosses: list[str | None] = [None, None, None]   # 位面1..3
        self._cur_plane: int = 0          # 0-based 当前采集位面索引
        self._start_plane: int = max(0, int(start_plane))   # 1-based;0=未知全采
        self._affixes: list[str] = []     # 词缀横条(位面详情屏,随 boss 同开读取)
        self._nonclean_wait_start: float | None = None   # 非clean帧等待起点(time.monotonic 时刻;None=未在等)
        # 节点序列互证输入(观测自检框架设计 §1 行11/§5-B5):备战帧的节点类型
        # 序列与所在位面(入口过备战屏时快照);None=未取得(非 clean 帧)不互证。
        self._prep_node_types: list[str | None] | None = None
        self._prep_plane: int = 0                 # 备战帧所在位面(1-based;0=未知)
        self._prep_cross_done: bool = False       # 互证一次即止(op 短生命周期,防重跑重复落行)
        # 位面节点序列台账写点①的采集面(权威依据=用户口述:位面内节点类型
        # 与数量只有投资环境选择能改变 → 进位面时读一次建档,此后查表):
        # 逐位面详情条序列(键=位面号 1-based;值=槽类型序,下标 i = 第 i+1 轮)。
        self._detail_seqs: dict[int, list[str | None]] = {}
        # 会话位面真值(1-based;0=未知)→ skip 过去位面判据输入。来源:入口
        # 备战帧快照(:attr:`_prep_plane`)或位面详情屏顶栏 OCR(read_phase_round,
        # 自带单调守卫);读不到保持 0 = 不跳过全量采集(无真值不发明跳过)。
        self._session_plane: int = 0
        # 逐位面采集计时(观测缺口补齐:用户观察到 P2 停留无法从日志诊断)。
        self._plane_start: float | None = None      # 当前位面计时起点(monotonic)
        self._plane_start_plane: int = 0            # 计时起点对应的位面号(1-based)
        # 非clean等待门的帧稳定性追踪(静止帧提前放弃,见 _GATE_STATIC_FAIL_FRAMES):
        # 上一次进门时的缩略图(None=本等待幕尚无前帧)+ 连续零变化帧计数。
        self._gate_prev_thumb: Any = None
        self._gate_static_streak: int = 0

    # ---- 内部工具 -------------------------------------------------------

    def _area_center(self, area_name: str, screen_name: str = _PD_SCREEN) -> Point | None:
        """screen_info area → 中心点(坐标单一源;无 area → None)。"""
        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, area_name, screen_name)
        if r is None:
            return None
        return Point((r.x1 + r.x2) // 2, (r.y1 + r.y2) // 2)

    def _boss_node_center(self, slots: list | None = None) -> Point | None:
        """当前位面节点条的最右(boss)节点圆心(read_plane_detail_nodes 动态定位)。

        位置先验(最右=首领):run 30 反例帧反而证实——点最右圆详情条显
        「1-9 首领节点」(徽章态身份缺失但**位置仍是首领**,ADR-0398);
        点击后再由详情条标签验证(conclude_plane_boss),先验失效走 retry 兜底。
        ``slots`` 可传调用方已读的详情条槽列表(采集循环同帧复用,免双读);
        None 时就地读。
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

    def _read_boss_big_icon(self) -> str | None:
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
            _log.info('[cw-plane-intel] 位面%d 大图标 SIFT 未命中(拒判保守)',
                      self._cur_plane + 1)
            return None
        name, good = hit
        _log.info('[cw-plane-intel] 位面%d boss=%s(SIFT 好匹配 %d)',
                  self._cur_plane + 1, name, good)
        return name

    def _nonclean_read_gate(self, reason: str) -> OperationRoundResult:
        """非clean帧等待门(**仅备战入口路径**;详情侧不走此门)。

        ① 帧在变(真动画:过场/加载)→ 间隔重读等动画窗,超宽上限
           (:data:`_NODE_BAR_WAIT_CAP_S`)才 op 级失败(2026-08-27 过场帧
           实证:动画窗远长于短窗连读);
        ② 帧静止(连续 :data:`_GATE_STATIC_FAIL_FRAMES` 帧零变化)→ 非动画,
           读不出是渲染态问题,等下去不会变 clean → op 级提前放弃(备战侧
           读不出 = 连详情都开不了,没有"下一位面"可推进,op 级失败留给
           调用方重试账;2026-08-30 哨兵实证:变暗静态条被当「切卡动画中」
           硬等 90s)。

        详情侧(采集循环内)的「节点条读不出」**不经此门**:2026-09-03
        用户裁决——已通过节点变暗=正常态,直接位面级结论记 None 推进,
        不再间隔重试(见 :meth:`_conclude_plane_unreadable`)。

        clean 判定语义不变(读出即 clean);上限与静止判定都是墙钟/帧序
        计时,与 round retry 账解耦——备战入口重试预算须 ≥ 上限/间隔
        (node_max_retry_times=60),否则预算先耗尽。
        """
        now = time.monotonic()
        if self._nonclean_wait_start is None:
            self._nonclean_wait_start = now
            self._gate_prev_thumb = None    # 新等待幕:帧稳定性账清零
            self._gate_static_streak = 0
        # 帧稳定性:与本等待幕上一帧比(每轮 round_retry 后框架刷新截图,
        # 同帧=静止;真动画帧间必有变化,不受影响);无截图(异常态)不判静止,
        # 保守走上限路径。
        if self.last_screenshot is not None:
            thumb = _frame_thumbnail(self.last_screenshot)
            if self._gate_prev_thumb is not None and _frames_identical(
                    thumb, self._gate_prev_thumb):
                self._gate_static_streak += 1
            else:
                self._gate_static_streak = 0
            self._gate_prev_thumb = thumb
            if self._gate_static_streak + 1 >= _GATE_STATIC_FAIL_FRAMES:
                _static_frames = self._gate_static_streak + 1
                self._nonclean_wait_start = None
                self._gate_prev_thumb = None
                self._gate_static_streak = 0
                self._best_effort_close_detail()
                return self.round_fail(
                    f'节点条非clean({reason})但画面已静止'
                    f'(连续{_static_frames}帧零变化,非动画;'
                    f'变暗/渲染态读不出)——提前放弃,不等'
                    f'{_NODE_BAR_WAIT_CAP_S:.0f}s')
        if now - self._nonclean_wait_start > _NODE_BAR_WAIT_CAP_S:
            self._nonclean_wait_start = None
            self._best_effort_close_detail()
            return self.round_fail(
                f'节点条非clean({reason})持续超 {_NODE_BAR_WAIT_CAP_S:.0f}s,放弃采集')
        time.sleep(_NODE_BAR_READ_INTERVAL_S)
        return self.round_retry(f'节点条未读出({reason}),间隔重读等动画窗')

    def _best_effort_close_detail(self) -> None:
        """失败退出前尽力关位面详情(op 出口契约=回备战屏):单击关闭键、不验
        转移、失败不抛——关不掉由主循环位面详情 overlay 分支兜底。残留教训
        (2026-08-30 判读):非clean 超限放弃采集时详情屏滞留画面,主循环当时
        无对应分支 → 未识别兜底自停,对局中断。
        """
        with contextlib.suppress(Exception):
            screen = self.screenshot()
            if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                       crop_first=False).is_success:
                x = self._area_center('按钮-关闭位面详情')
                if x is not None:
                    self.ctx.controller.click(x)
                    time.sleep(1.5)

    def _conclude_plane_unreadable(self, reason: str) -> OperationRoundResult:
        """位面级「情报不可得」结论(详情侧节点条读不出的唯一出口,W901 治本;
        2026-09-03 起采集循环读不出即直接进此结论,不经等待门重试)。

        语义:已确在位面详情(调用方守卫)+ 节点条读不出(变暗/渲染态,
        等不会变 clean)⇒ 只结论「该位面情报不可得」(记 None,同徽章态语义线),
        推进下一位面,不整场 round_fail——三现根因 = 部分失败被升格为
        全场失败,调用方 2 次重试无退避同窗烧光。
        守卫:若此刻已不在位面详情(详情没开成/被弹回,如半开备战帧),
        静止结论不成立 → 维持 op 级失败,留给调用方在后续稳定帧重试。
        """
        screen = self.screenshot()
        if not self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                       crop_first=False).is_success:
            self._best_effort_close_detail()
            return self.round_fail(
                f'节点条非clean({reason})且画面已静止,且不在位面详情'
                f'(详情未开成)——放弃采集,待稳定帧重试')
        plane_no = self._cur_plane + 1
        self._plane_bosses[self._cur_plane] = None
        _log.info('[cw-plane-intel] 位面%d 节点条静止不可读(%s;在详情内,等不会变'
                  'clean)→ 结论=该位面情报不可得(记 None),推进下一位面',
                  plane_no, reason)
        self._cur_plane += 1
        return self.round_wait(
            f'位面{plane_no} 节点条静止不可读({reason}),结论=情报不可得,'
            f'推进下一位面')

    # ---- 节点图(round 语义驱动,同 HandleBriefing 形态) -----------------

    @operation_node(name='采集', is_start_node=True, node_max_retry_times=60)
    def collect(self) -> OperationRoundResult:
        """入口核对 + 三位面采集循环(状态在 self;round_wait 自环推进)。

        分支序:①已在位面详情(重跑/续采)→ 采集循环;②备战 → 点当前
        节点图标开详情(round_wait 等开);③其它屏 → retry 等。
        采集循环(每位面):点卡 → 点 boss 节点(最右,位置先验)→ 详情条
        标签验「首领」+ 大图标 SIFT → 头像态命中记录 / 徽章态记 None 跳过 /
        标签异常 retry;三位面齐 → success(转关闭)。
        """
        screen = self.last_screenshot
        _in_pd = self.round_by_find_area(
            screen, _PD_SCREEN, '标识-位面详情标题', crop_first=False).is_success
        if not _in_pd:
            if self.round_by_find_area(screen, _PREP_SCREEN, '备战标识-购买经验',
                                       crop_first=False).is_success:
                from sr_od.application.currency_war.obs.cw_observation import (
                    read_node_sequence,
                )
                slots = read_node_sequence(self.ctx, screen)
                # 互证输入快照(观测自检框架设计 §1 行11):备战帧的节点类型
                # 序列 + 所在位面(read_phase_round 顶栏 OCR);非 clean 帧
                # (slots None)不快照,等下个 clean 备战帧。
                if slots:
                    # getattr 槽位结构演进兜底(测试桩/旧槽对象可无 node_type 字段)
                    self._prep_node_types = [getattr(s, 'node_type', None)
                                             for s in slots]
                    from sr_od.application.currency_war.obs.cw_observation import (
                        read_phase_round,
                    )
                    with contextlib.suppress(Exception):
                        _pp = read_phase_round(self.ctx, screen)
                        if _pp and _pp[0]:
                            self._prep_plane = int(_pp[0])
                    # 起始采集位面(2026-09-03 用户裁决:时序反过来——进详情
                    # 之前先由备战帧定当前位面,详情内只采当前及之后的位面)。
                    # 调用方已传(更早的备战帧)则不覆盖;备战识别失败(顶栏
                    # 也没读出)保持 0 = 全采回退。
                    if not self._start_plane and self._prep_plane:
                        self._start_plane = self._prep_plane
                    # 台账写点①·备战行源(两源之一):备战节点行先按位合并进表
                    # (详情条源稍后整面覆盖;合并语义=None 位保旧,见 ledger_update_plane)。
                    with contextlib.suppress(Exception):
                        from sr_od.application.currency_war.kernel.cw_state import (
                            ledger_update_plane,
                        )
                        _sess = getattr(getattr(self.ctx, 'cw_match', None),
                                        'session', None)
                        if _sess is not None and self._prep_plane:
                            ledger_update_plane(_sess, self._prep_plane,
                                                list(self._prep_node_types),
                                                'prep_row')
                # 点**任意节点图标**都开位面详情(建档实锤;入口不依赖 current
                # 锚——22:09 实跑 1-7 帧当前槽 V 未过亮门无锚,首版依赖 current
                # retry 耗尽失败)。优先 current,无则首个检出圆。
                cur = next((s for s in (slots or []) if s.state == 'current'), None) or (
                    slots[0] if slots else None)
                if cur is None:
                    return self._nonclean_read_gate('非clean帧')
                self._nonclean_wait_start = None   # 读出=clean,重置等待账
                from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
                r = _area_rect(self.ctx, '区域-节点条', _PREP_SCREEN)
                # 兜底字面量:area 缺失(离线/档案损坏)时的节点条原点(1080p 实测值)
                ox, oy = (r.x1, r.y1) if r is not None else (544, 24)
                self.ctx.controller.click(Point(cur.cx + ox, cur.cy + oy))
                time.sleep(_DETAIL_OPEN_WAIT_S)   # 用户定值 ~3s:开屏动画落定再读
                return self.round_wait('已点节点图标,等位面详情开')
            return self.round_retry('非备战非位面详情,等画面')

        # —— 在位面详情:采集循环 ——
        # 词缀横条(位面详情屏底部):首位面采集时同帧读一次(词缀不随位面
        # 卡切换变;备战画面无此条,词缀只在简报/位面详情/敌人信息浮层)。
        if not self._affixes and self._cur_plane == 0:
            from sr_od.application.currency_war.obs.cw_briefing_obs import (
                read_detail_affixes,
            )
            self._affixes = read_detail_affixes(self.ctx, screen)
            if self._affixes:
                _log.info('[cw-plane-intel] 词缀随采(位面详情横条):%s', self._affixes)
        if self._cur_plane >= 3:
            _miss = [str(i + 1) for i, b in enumerate(self._plane_bosses) if b is None]
            if _miss:
                _log.info('[cw-plane-intel] 位面%s boss 未取得(徽章态/读取失败),'
                          'boss_fit 对应位面走中性(尽力采披露)', ','.join(_miss))
            return self.round_success('三位面采集完')
        # 会话位面真值(日志语境用):优先入口备战帧快照,无则位面详情屏
        # 顶栏 OCR 读一次(read_phase_round 自带 last-known-good + 单调守卫);
        # 读不到保持 0。**跳过判据不用它**,用 _start_plane(备战帧定,见上)。
        if self._session_plane == 0:
            if self._prep_plane:
                self._session_plane = self._prep_plane
            else:
                with contextlib.suppress(Exception):
                    from sr_od.application.currency_war.obs.cw_observation import (
                        read_phase_round,
                    )
                    _sp = read_phase_round(self.ctx, screen)
                    if _sp and _sp[0]:
                        self._session_plane = int(_sp[0])
        # 起始位面兜底:调用方与备战帧都没拿到 → 详情顶栏 OCR 补一次;
        # 仍无(=0)→ decide_plane_skip 不跳,全采回退。
        if not self._start_plane and self._session_plane:
            self._start_plane = self._session_plane
        plane_no = self._cur_plane + 1
        # skip 过滤(判据=:func:`decide_plane_skip`,备战帧定的起始位面;
        # 跳过位面不点卡不重采,close_and_report 只落 _detail_seqs 里实际
        # 采过的位面,跳过位面自然不覆写台账)。
        _skip, _note = decide_plane_skip(plane_no, self._start_plane or None)
        if _skip:
            _log.info('[cw-plane-intel] 位面%d:%s(start_plane=%d)',
                      plane_no, _note, self._start_plane)
            self._cur_plane += 1
            return self.round_wait(f'位面{plane_no}跳过(已通过位面),下一位面')
        # 逐位面计时起点(retry 重入同位面不重置——耗时含 retry 空转,正要暴露)
        if self._plane_start is None or self._plane_start_plane != plane_no:
            self._plane_start = time.monotonic()
            self._plane_start_plane = plane_no
        # ① 点位面卡(选中当前采集位面)
        card = self._area_center(_PLANE_CARD_AREAS[self._cur_plane])
        if card is None:
            self._best_effort_close_detail()
            return self.round_fail(f'位面卡 area 缺失:{_PLANE_CARD_AREAS[self._cur_plane]}')
        self.ctx.controller.click(card)
        time.sleep(_PLANE_SWITCH_WAIT_S)   # 用户定值 2s:切卡动画短,等 2s 即读
        # ② 点该位面 boss 节点(动态定位;节点带随选中位面变)
        screen = self.screenshot()
        from sr_od.application.currency_war.obs.cw_observation import (
            read_plane_detail_nodes,
        )
        _detail_slots = read_plane_detail_nodes(self.ctx, screen)
        # 节点序列互证(观测自检框架设计 §1 行11/§5-B5):同帧详情条与备战帧
        # 序列对拍(同位面才比,见 _cross_check_node_seq);纯记账,无行为分支。
        self._cross_check_node_seq(_detail_slots)
        # 台账写点①·详情条源(两源之二):该位面全节点预览序列随采随存
        # (关闭节点统一落账并回填 boss 位)。
        if _detail_slots:
            self._detail_seqs[self._cur_plane + 1] = [
                getattr(s, 'node_type', None) for s in _detail_slots]
            # 敌人难度参考值(位面详情底部明文):随选中位面变,逐位面读;
            # **只存参考**,生产难度主源 = 备战旗牌两级管线(ADR-0449)不变。
            with contextlib.suppress(Exception):
                from sr_od.application.currency_war.kernel.cw_state import (
                    get_node_ledger,
                )
                from sr_od.application.currency_war.obs.cw_observation import (
                    read_plane_detail_difficulty,
                )
                _sess = getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None)
                _ledger = get_node_ledger(_sess)
                if _ledger is not None:
                    _dv = read_plane_detail_difficulty(self.ctx, screen)
                    if _dv is not None:
                        _ledger.difficulty_ref[self._cur_plane + 1] = _dv
                        _log.info('[cw-plane-intel] 位面%d 敌人难度参考=%d',
                                  self._cur_plane + 1, _dv)
        boss_pt = self._boss_node_center(_detail_slots)
        if boss_pt is None:
            # 已通过节点变暗=正常态(2026-09-03 用户裁决),等 2s 后仍读不出
            # ⇒ 该位面情报不可得,直接位面级结论记 None 推进——不进等待门
            # 间隔重试(第六局实证:切卡动画重试等待烧 7s 后才放弃)。
            return self._conclude_plane_unreadable(
                '节点条读不出(已通过节点变暗为正常态)')
        self._nonclean_wait_start = None   # 读出=clean,重置等待账
        self.ctx.controller.click(boss_pt)
        time.sleep(1.5)
        # ③ 读详情条:类型名标签验「首领」→ 大图标 SIFT → 结论分流(ADR-0398)
        self.screenshot()
        from sr_od.application.currency_war.obs.cw_observation import (
            read_detail_node_type_label,
        )
        label = read_detail_node_type_label(self.ctx, self.last_screenshot)
        name: str | None = None
        if label and '首领' in label.replace(' ', ''):
            name = self._read_boss_big_icon()
            if name is None:
                # 半更新帧防误跳:skip 是终局结论(徽章态恒 None,重试无意义),
                # 但「标签已更新而大图标未换」的过渡帧会把头像态误判 skip →
                # 再截一帧复读一次(零点击成本)仍 miss 才下徽章态结论。
                time.sleep(0.5)
                self.screenshot()
                name = self._read_boss_big_icon()
        action, val = conclude_plane_boss(label, name)
        if action == 'retry':
            return self.round_retry(f'位面{self._cur_plane + 1} {val}')
        if action == 'skip':
            _log.info('[cw-plane-intel] 位面%d 首领节点=徽章态(无头像无名,本屏无身份)'
                      '→ 记 None 跳过,不空转重试(ADR-0398)', self._cur_plane + 1)
        self._plane_bosses[self._cur_plane] = val
        _dt = time.monotonic() - self._plane_start if self._plane_start else 0.0
        _log.info('[cw-plane-intel] 位面%d 采集完成(耗时 %.1fs,session_plane=%s):%s',
                  plane_no, _dt, self._session_plane or '?', self._plane_bosses)
        self._cur_plane += 1
        return self.round_wait(f'位面{self._cur_plane}完成,下一位面')

    def _cross_check_node_seq(self, detail_slots: list) -> None:
        """备战帧与位面详情帧同位面节点序列互证(观测自检框架设计 §1 行11/
        §5-B5「备战/位面详情节点序列互证」;纯记账零决策)。

        仅当:①详情条已读出;②详情位面 = 备战帧所在位面(跨位面无对应序列,
        设计未定义,不发明);③本次 op 尚未对拍过。不一致 → 台账留证一次
        (node_seq 属中相关面,单次 L2 留证;无 retry/无行为分支)。
        """
        if (self._prep_cross_done or not self._prep_node_types
                or not detail_slots or self._prep_plane != self._cur_plane + 1):
            return
        self._prep_cross_done = True
        from sr_od.application.currency_war.telemetry import defects as cw_telemetry
        _prep = [getattr(s, 'node_type', None) for s in self._prep_node_types]
        _det = [getattr(s, 'node_type', None) for s in detail_slots]
        mism = node_seq_cross_mismatch(_prep, _det)
        if not mism:
            _log.info('[cw-plane-intel] 节点序列互证通过(位面%d,%d 可比位)',
                      self._prep_plane,
                      sum(1 for a, b in zip(_prep, _det, strict=False)
                          if a is not None and b is not None))
            return
        with contextlib.suppress(Exception):
            cw_telemetry.record_defect(
                'node_seq', 'perception_conflict',
                expected=f'备战帧序列:{_prep}',
                observed=f'位面详情帧序列:{_det}(不一致位次(0基):{mism})',
                plane=self._prep_plane,
                verdict=('留证-同位面节点序列同位类型不一致(同 CV 核心跨输入域'
                         '互证:备战彩色/详情彩带读法域不同)'),
                reader_source='prep_vs_plane_detail_seq',
                gap_large=False,
                refs=[{'stream': 'decisions',
                       'key': f'plane={self._prep_plane}'}],
                note='观测自检框架设计 §1 行11:备战帧与位面详情帧序列对拍;'
                     'boss 槽/未识别位自然跳过不判')
        _log.info('[cw-plane-intel] 节点序列互证不一致(位面%d)位次%s → 台账留证',
                  self._prep_plane, mism)

    @node_from(from_name='采集')   # 首跑教训:无显式边时「采集」success 被当 op 终点,关闭节点漏跑(画面留在位面详情)
    @operation_node(name='关闭并回写', node_max_retry_times=6)
    def close_and_report(self) -> OperationRoundResult:
        """点 X 关位面详情(验 id_mark 消失=真转移)→ 结果写 ctx 中转 → success。"""
        screen = self.screenshot()
        if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                   crop_first=False).is_success:
            x = self._area_center('按钮-关闭位面详情')
            if x is None:
                return self.round_fail('关闭按钮 area 缺失')
            self.ctx.controller.click(x)
            time.sleep(1.5)
            screen = self.screenshot()
            if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                       crop_first=False).is_success:
                return self.round_retry('点X未关,重试')
        # 已离开位面详情 → 写中转(消费接线批挂账)
        self.ctx.cw_plane_bosses = list(self._plane_bosses)   # type: ignore[attr-defined]
        self.ctx.cw_plane_affixes = list(self._affixes)   # type: ignore[attr-defined]
        # 台账写点①落账(session 权威表;详情条源为主——该位面全节点彩色预览,
        # boss 位按「首领=位面最后节点」位置先验回填,回填依据 = 本 op 详情条
        # 「首领节点」标签验证语义;备战行源已在入口合并,此处再并一次兜全)。
        with contextlib.suppress(Exception):
            from sr_od.application.currency_war.kernel.cw_state import (
                fill_boss_by_position,
                ledger_update_plane,
            )
            _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
            if _sess is not None:
                for _p, _seq in sorted(self._detail_seqs.items()):
                    _changed = ledger_update_plane(
                        _sess, _p, fill_boss_by_position(_seq), 'plane_detail')
                    _log.info('[cw-plane-intel] 台账落账 p%d(%s)%s:%s',
                              _p, 'plane_detail',
                              '(有变更)' if _changed else '(无变更)',
                              fill_boss_by_position(_seq))
                if self._prep_node_types and self._prep_plane:
                    ledger_update_plane(_sess, self._prep_plane,
                                        list(self._prep_node_types), 'prep_row')
        _log.info('[cw-plane-intel] 采集完成 plane_bosses=%s affixes=%s(ctx 中转)',
                  self._plane_bosses, self._affixes)
        return self.round_success(f'位面情报采集:boss={self._plane_bosses} 词缀={self._affixes}')
