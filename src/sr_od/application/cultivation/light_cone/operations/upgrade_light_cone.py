"""光锥升级 operation(升级+晋阶到满级,材料不足可走通用补全/快速刷取补料)。

交互链(2026-11-13 新版快速刷取实机摸底,详见探索目录 screen-flow 与
docs/game/screens/光锥-等级提升.md):
光锥 TAB 点「强化」→ 光锥-等级提升(左列「详情/升级|晋阶/叠影」,第三项随
光锥是否到上限动态切换) → 右下按钮分流 → 缺料时「培养还需获取资源」窗口
→ 进入对应副本 → 券免战斗/手动挑战 → 逐层或回大世界返回。

右下按钮形态(实测):
- 材料全齐:白底「快速升级」执行钮(旧形态,area 保留);
- 缺可合成材料:白底「使用通用材料补全」+左侧「快速刷取」;
- 通用材料不可合成且缺可刷材料:仅「快速刷取」;
- 「可提升至80级」badge 与快速刷取相互独立:badge 在但原始材料已足够
  (缺口可由合成覆盖,无需副本刷取)时,点快速刷取静默无反应——游戏提示
  「当前并未缺少可以通过快速刷取获取的材料」。因此 open_farm_window 的
  until 超时 = 无可刷缺口,判停并提示改走通用材料补全(fill_generic)。

快速刷取链(照 UpgradeCharacterOp 新版结构):
点「快速刷取」→「培养还需获取资源」窗口(缺料行:材料+开拓力10+「进入」)
→ 点「进入」直达副本挑战画面 → use_fast_ticket 分流:True = 副本画面
「快速刷取」券免战斗(确认框次数 OCR 现读+点「+」设到目标,-1 = 点「^」
拉满)→ 确认 → 结果框「关闭」;False = 「挑战」→编队「开始挑战」→自动
战斗→结算「退出关卡」。

返回链差异(手动战斗兼容,实测对照):
- 券路线:副本「关闭X」按浮层栈回退 →「培养还需获取资源」→ 光锥-等级提升;
- 手动路线:进入战斗时浮层栈被游戏卸载,「退出关卡」后副本画面为重建态,
  「关闭X」直接回**大世界**——需重走入口链:大世界右上角色图标 → 角色详情
  (不记忆上次角色,显示列表首位)→ 重选角色 → 光锥 TAB → 强化。
  角色名在入口核对时从光锥 TAB 左上读名区 OCR 记下(格式「命途/名字」)。

消耗(拟造花萼·赤实测):每次刷取开拓力 10 + 快速刷取券 1(与角色晋阶线
30+3 不同,券耗随副本类型变化);开拓力不足部分由备用开拓力补足(消耗行
实证:开拓力先结、备用补差额),不耗星琼/燃料。确认框滑条上限 24;次数
不记忆(重开=1)。
开拓力不足时快速刷取/挑战按钮静默无反应(白底与可用态无视觉差异)——
open_farm_window/手动挑战的重试预算耗尽即判停,不空烧轮次。

补料路线与优先级:通用材料补全(fill_generic,默认开)优先于刷取
(farm_dungeon)优先于手动刷——通用材料非稀缺,用户裁定为默认授权的
最优先路线;刷取类真实消耗开拓力与快速刷取券,发起前调用方必须向用户
说明并获同意。

前置:光锥 TAB(列表浮层已收);终点:光锥 TAB(升满或材料判停)。
"""

import re
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.select_character import SelectCharacterOp
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.switch_character_tab import SwitchCharacterTabOp

_LC_TAB_SCREEN: str = '角色-光锥'
_LC_ASCEND_SCREEN: str = '光锥-等级提升'
_REPLACE_SCREEN: str = '光锥-替换'
_LIST_SCREEN: str = '角色-列表'
_WORLD_SCREEN: str = '大世界-普通'
_DETAIL_SCREEN: str = '角色-详情'
_RESOURCE_WINDOW_SCREEN: str = '培养资源窗口'
_CHALLENGE_SCREEN: str = '挑战副本'
# 快速刷取两弹窗独立建档(模态盖住副本 id_mark,识别必须走弹窗自身锚):
# 选次数与结果是两个弹窗,标题同名「快速刷取」但位置不同(y≈304 / y≈249),
# 各自画面 id_mark=标题,坐标互斥不误判
_FAST_FARM_DIALOG: str = '快速刷取弹窗'
_FAST_FARM_RESULT: str = '快速刷取结果弹窗'
_BATTLE_SCREEN: str = '战斗画面'
_LC_PROMO_BANNER_SCREEN: str = '光锥-等级提升-晋阶横幅'
_LC_RETURN_SCREEN: str = '光锥-等级提升-材料返还'

# 升级执行后横幅+动画的稳定等待
_LC_ASCEND_SETTLE_SEC: float = 2.5
# 每次刷取消耗(拟造花萼·赤难度VI实测:资源窗口行内开拓力10,券耗1;与角色
# 晋阶线 30+3 不同——券耗随副本类型变化,勿复用角色线常量)
_LC_FARM_TRAILBLAZE_PER: int = 10
_LC_FARM_TICKET_PER: int = 1
# 手动挑战单场战斗的单轮等待(自动战斗实测约1分钟,重入轮慢询)
_LC_FIGHT_POLL_SEC: float = 15.0
# farm_dungeon 单次运行最多刷取轮数(防开拓力/券无限烧;每轮=确认框执行
# farm_times_per_round 次或手动战斗一场)
_LC_FARM_ROUNDS_MAX: int = 10

# 详情页入口按钮(光锥 TAB 强化,常驻不因满级消失)
_ENTRY_BTN_STRENGTHEN: str = '按钮-强化'


class UpgradeLightConeOp(SrOperation):
    """把当前角色的光锥升到 80 级满级(经验升级+晋阶突破),材料不足时按授权
    走通用材料补全或快速刷取补料继续。起点:角色-光锥 TAB(列表浮层已收);
    终点:角色-光锥 TAB。结果状态:LIGHT_CONE_CAPPED(已满级 / 材料耗尽停在
    当前等级,日志注明等级与消耗)。

    ⚠️ farm_dungeon=True 真实刷副本:券路线(use_fast_ticket=True)消耗 =
    券刷次数合计 × (开拓力 10 + 券 1)——券只免战斗,开拓力照扣:先扣开拓
    力再以备用开拓力补足(确认框消耗行实证),不耗星琼/燃料;手动路线消耗
    = 手动场数 × 开拓力 10(不耗券)。farm_rounds_max 限制刷取轮数(券轮=
    一次确认框执行、手动轮=一场战斗)。开拓力+备用亦尽时游戏弹「开拓力
    补充」弹窗,本 op 不处理、预算内轮次失败判停。**发起前调用方必须按
    最坏消耗向用户说明并获同意**(通用材料默认授权,见 fill_generic)。

    :param ctx: 上下文
    :param fill_generic: 缺料时用「使用通用材料补全」路线(通用材料合成
        命途专属晋阶材料)。True(默认,通用材料非稀缺,用户裁定的最优先
        路线) = 自动确认补全弹窗;False = 不消耗通用材料。
    :param farm_dungeon: 缺可刷材料(快速刷取按钮有效)时刷副本补料。False
        (默认,安全) = 不刷,材料不足判停;True = 走快速刷取链(**真实消耗
        开拓力与券**)。
    :param use_fast_ticket: farm_dungeon=True 时的刷取方式。True(默认) =
        副本内用快速刷取券免战斗直接领奖;False = 正常挑战自动战斗(每场
        约1分钟)。
    :param farm_times_per_round: 每轮确认框内设置的刷取次数(OCR 现读+点
        「+」补偿,游戏封顶滑条上限24)。默认 -1 = 点「^」拉满——材料是
        共享库存,多余可给其他角色或留未来用,用户裁定的默认策略。
    :param farm_rounds_max: 整个运行允许的刷取轮数上限(耗尽判停,可续跑)。
        默认 1 = 只刷一轮(拉满),回来不够即判停报告——多轮连刷的缺口应
        由调用方按剩余预算显式续跑。
    """

    def __init__(self, ctx: SrContext, fill_generic: bool = True,
                 farm_dungeon: bool = False, use_fast_ticket: bool = True,
                 farm_times_per_round: int = -1, farm_rounds_max: int = 1):
        """
        参数语义见类 docstring;此处仅做取值校验。
        """
        if farm_times_per_round == 0 or farm_times_per_round < -1:
            raise ValueError(f'farm_times_per_round 须为正数或 -1(拉满), 得到 {farm_times_per_round}')
        if farm_rounds_max < 1:
            raise ValueError(f'farm_rounds_max 必须 >= 1, 得到 {farm_rounds_max}')
        self.fill_generic: bool = fill_generic
        self.farm_dungeon: bool = farm_dungeon
        self.use_fast_ticket: bool = use_fast_ticket
        self.farm_times_per_round: int = farm_times_per_round
        self.farm_rounds_max: int = farm_rounds_max
        SrOperation.__init__(self, ctx, op_name=gt('光锥晋阶升级')
                             + ('(券刷取)' if farm_dungeon and use_fast_ticket else '')
                             + ('(手动刷取)' if farm_dungeon and not use_fast_ticket else '')
                             + ('' if fill_generic else '(不用通用材料)'),
                             node_max_retry_times=40)
        self._char_name: str | None = None  #: 入口记下的角色名(手动刷取回大世界后重选用)
        self._capped: bool = False          #: 材料不足已判停(回光锥 TAB 收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的光锥等级(报告用)
        self._farm_rounds: int = 0          #: 已执行的刷取轮数(预算控制;券轮=1次确认框,手动轮=1场)
        self._farm_draws: int = 0           #: 券刷累计次数(券消耗;确认框实际设到的次数)
        self._manual_fights: int = 0        #: 手动战斗场数(开拓力消耗)
        self._farm_times_set: int = 0       #: 本轮确认框实际设到的次数(_set_farm_times 写入)
        self._upgrade_count: int = 0        #: 升级执行次数(日志统计)
        if farm_dungeon:
            log.info('光锥晋阶: farm_dungeon 已启用——缺可刷材料将刷副本,路线=%s,'
                     '每轮 %s 次,预算 %d 轮——每次刷取消耗开拓力 %d + 快速刷取券 %d',
                     '券免战斗' if use_fast_ticket else '自动战斗',
                     '拉满' if farm_times_per_round == -1 else str(farm_times_per_round),
                     farm_rounds_max, _LC_FARM_TRAILBLAZE_PER, _LC_FARM_TICKET_PER)

    #------------------- 识别辅助 -------------------#

    def _read_lc_level(self, screen_name: str = _LC_TAB_SCREEN) -> int | None:
        """等级读数(「等级NN/MM」取当前值);光锥 TAB 与等级提升界面读区各自建档。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(screen_name, '读区-等级'
                                               if screen_name == _LC_TAB_SCREEN else '读区-当前等级')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'(\d+)\s*/\s*\d+', str(r.data or ''))
            if m:
                return int(m.group(1))
        return None

    def _read_character_name(self) -> str | None:
        """光锥 TAB / 等级提升 左上读名区 OCR「命途/角色名」取「/」后段
        (两界面左上布局相同,分别建档)。

        用途:手动刷取返回链会落到大世界,角色详情不记忆上次角色(实测显示
        列表首位),需凭此名重选。area 未建档/读不出返回 None,返回链到重选
        步时显式失败,不影响升级主流程。"""
        for screen_name in (_LC_TAB_SCREEN, _LC_ASCEND_SCREEN):
            area = self.ctx.screen_loader.get_area(screen_name, '读名区-左上')
            if area is None:
                continue
            results = self.ctx.ocr_service.get_ocr_result_list(
                image=self.screenshot(), rect=area.pc_rect, crop_first=True)
            for r in results:
                text = str(r.data or '').strip()
                if '/' in text:
                    name = text.rsplit('/', maxsplit=1)[-1].strip()
                    if name:
                        return name
        return None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """画面级判定:光锥 TAB(强化入口)或已在等级提升(中断接管);记下角色
        名(手动刷取返回链用)。

        列表浮层开着会遮挡强化按钮,识别浮层态显式失败提示先收列表;现场已在
        等级提升(如上次运行中断/弹窗浮层)时直入升级循环接管。手动刷取链
        (farm_dungeon + 非 use_fast_ticket)授权时读名失败 = 消耗前判停——
        返回链需凭记名重选角色,打完一场才发现无名会白烧开拓力。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot,
            screen_name_list=[_LC_TAB_SCREEN, _LC_ASCEND_SCREEN, _CHALLENGE_SCREEN,
                              _WORLD_SCREEN, '大世界',
                              _REPLACE_SCREEN, _LIST_SCREEN])
        if current in (_REPLACE_SCREEN, _LIST_SCREEN):
            return self.round_fail(f'{current} 浮层开着(遮挡态):先收列表'
                                   f'(替换列表点右上返回箭头)')
        if current == _CHALLENGE_SCREEN:
            # 刷取中断现场(战斗/结算/重建副本画面):直入返回分类收口
            return self.round_success(status='IN_CHALLENGE')
        if current in (_WORLD_SCREEN, '大世界'):
            # 手动刷取返回链的中断落点:从大世界重走入口链
            return self.round_success(status='BACK_TO_WORLD')
        if current is None:
            # 浮层/过渡帧整帧画面识别失败:逐锚接管——材料补全弹窗开启查弹窗
            # 自身锚;刷取中断(结算画面/重建副本画面/升级过渡帧)查等级提升
            # 左上锚与战斗结算退出钮;快速刷取确认框/结果框态(挑战按钮被
            # 模态遮住,副本 id_mark 不命中)查弹窗标题锚
            for anchor in ('标题-材料补全弹窗', '标题-光锥详情'):
                if screen_utils.find_area(
                        self.ctx, self.last_screenshot,
                        _LC_ASCEND_SCREEN, anchor) == FindAreaResultEnum.TRUE:
                    return self.round_success(status='ALREADY_ASCEND')
            if screen_utils.find_area(
                    self.ctx, self.last_screenshot,
                    _BATTLE_SCREEN, '按钮-退出关卡') == FindAreaResultEnum.TRUE:
                return self.round_success(status='IN_CHALLENGE')
            # 券确认刷取链的三类弹窗残留(选次数/结果/开拓力补充)按各自画面
            # 标题识别接管,交返回分类逐层清场
            for dialog_screen, dialog_title in (
                    (_FAST_FARM_DIALOG, '标题-快速刷取弹窗'),
                    (_FAST_FARM_RESULT, '标题-快速刷取弹窗'),
                    ('开拓力补充弹窗', '标题-开拓力补充弹窗')):
                if screen_utils.find_area(
                        self.ctx, self.last_screenshot,
                        dialog_screen, dialog_title) == FindAreaResultEnum.TRUE:
                    return self.round_success(status='IN_CHALLENGE')
            return self.round_fail('画面识别失败(None)且无已知浮层锚,请实机确认现场')
        if current == _LC_ASCEND_SCREEN:
            return self.round_success(status='ALREADY_ASCEND')
        if current != _LC_TAB_SCREEN:
            return self.round_fail(f'不在光锥 TAB(当前画面判定: {current};'
                                   f'前置:进详情 + 选角色 + 切「光锥」页签)')
        self._char_name = self._read_character_name()
        if self._char_name is None and self.farm_dungeon and not self.use_fast_ticket:
            # 手动链返回后需凭记名重选角色(角色详情不记忆上次角色),读不到
            # 就在消耗前拦住——等打完一场再失败会白烧 1 场开拓力
            return self.round_fail('手动刷取链需凭入口读名在返回后重选角色,'
                                   '左上读名区 OCR 未读到——请实机确认画面,'
                                   '或改用券路线(use_fast_ticket=True)')
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN) == FindAreaResultEnum.TRUE:
            return self.round_success(status='CAN_UPGRADE')
        return self.round_fail('光锥 TAB 无强化按钮(画面状态未知),请实机确认')

    @node_from(from_name='入口核对', status='CAN_UPGRADE')
    @operation_node(name='打开等级提升', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """光锥 TAB 点「强化」→ 等级提升界面(until=标题锚:标题唯一,且左列
        第三项随晋阶状态在 升级/晋阶 间改名,不能作 until 锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN,
            until_find_all=[(_LC_ASCEND_SCREEN, '标题-光锥详情')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开等级提升')
    @node_from(from_name='入口核对', status='ALREADY_ASCEND')
    @node_from(from_name='刷取返回分类', status='FARMED')
    @node_from(from_name='重走入口链', status='FARMED')
    @operation_node(name='升级循环', node_max_retry_times=40)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:补全弹窗 → 横幅浮层 → 判停收尾 → 界面重开 → 满级判 →
        按钮分流。

        每轮分类(优先级):
        ① 「材料补全」确认弹窗在 → fill_generic 确认继续 / 未授权取消判停;
        ② 晋阶横幅/材料返还页(全屏浮层)在 → 点空白关闭——必须先于界面
           重开判定:浮层盖住等级提升锚,后置会被④误判过渡帧空转到预算耗尽;
        ③ 已判停(_capped) → 关 X 回光锥 TAB,到了就 LIGHT_CONE_CAPPED 成功;
        ④ 不在等级提升界面 → 光锥 TAB 判:强化在 = 重开界面;
        ⑤ 「已提升至最高阶」在 = 满级 → 判停收尾归档;
        ⑥ 「快速升级」执行钮命中(材料全齐) → 点执行;
        ⑦ 「使用通用材料补全」/「材料合成」命中(缺料两形态,点后均弹同款
           确认框) → fill_generic 点(弹窗交①下轮确认);「通用材料补全」
           形态未授权但 farm_dungeon 可用 → NEED_FARM 直接刷,「材料合成」
           形态未授权直接判停(该形态快速刷取无效);
        ⑧ 无补全钮 → farm_dungeon 可用且「快速刷取」钮在 = 缺可刷材料 →
           NEED_FARM;否则判停(经验书足+晋阶不可刷/不可合成的常见形态)。
        异常形态由节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot

        # ① 材料补全确认弹窗
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('光锥晋阶: 确认通用材料补全(消耗通用材料合成缺失材料)')
                return self.round_retry('通用材料补全已确认,等界面刷新', wait=3.0)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-取消材料补全').rect.center)
            self._capped = True
            self._capped_level = self._read_lc_level()
            return self.round_retry('取消材料补全,返回收尾', wait=1.5)

        # ② 晋阶横幅/材料返还页(升满/晋阶成功时先后出现的全屏浮层,点击
        # 空白处关闭;实测顺序:晋阶横幅 → 材料返还 → 回等级提升)
        for banner in ((_LC_PROMO_BANNER_SCREEN, '标题-晋阶横幅'),
                       (_LC_RETURN_SCREEN, '标题-材料返还')):
            if self.round_by_find_area(screen, banner[0], banner[1]).is_success:
                self.ctx.controller.click(Point(960, 120))
                return self.round_retry(f'{banner[1]}已点空白关闭,等下页', wait=2.0)

        # ③ 已判停 → 关 X 回光锥 TAB → 到了就结束
        if self._capped:
            if self.round_by_find_area(screen, _LC_TAB_SCREEN, '标题-角色光锥').is_success:
                log.info('光锥晋阶: 收尾,当前光锥等级 %s,升级 %d 次/刷取 %d 轮'
                         '(券刷 %d 次耗券 %d,手动 %d 场耗开拓力 %d)',
                         self._capped_level, self._upgrade_count, self._farm_rounds,
                         self._farm_draws, self._farm_draws * _LC_FARM_TICKET_PER,
                         self._manual_fights, self._manual_fights * _LC_FARM_TRAILBLAZE_PER)
                return self.round_success(status='LIGHT_CONE_CAPPED', wait=1.5)
            result = self.round_by_find_and_click_area(
                screen, _LC_ASCEND_SCREEN, '按钮-关闭X',
                until_find_all=[(_LC_TAB_SCREEN, '标题-角色光锥')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('返回光锥页,重入收尾', wait=1.5)
            return result

        # ④ 界面重开(打开前/收尾途中不在等级提升)
        if not self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-光锥详情').is_success:
            if self.round_by_find_area(screen, _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN).is_success:
                result = self.round_by_find_and_click_area(
                    screen, _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN,
                    until_find_all=[(_LC_ASCEND_SCREEN, '标题-光锥详情')],
                    pre_delay=0.5, success_wait=1.5, retry_wait=2,
                )
                if result.is_success:
                    return self.round_retry('等级提升已开,重入分类', wait=1.5)
                return result
            # 详情与强化钮同时不可见 = 升级执行动画/横幅过渡帧:等稳定重判
            # (真异常由节点重试预算兜底耗尽显式失败)
            return self.round_retry('界面过渡中,等稳定重判', wait=2.0)

        # ⑤ 满级态:右下「已提升至最高阶」→ 判停收尾归档
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '文本-已提升至最高阶').is_success:
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 光锥已满级(已提升至最高阶,等级 %s)', self._capped_level)
            return self.round_retry('满级,关闭回光锥页收尾', wait=1)

        # ⑥ 材料全齐:白底「快速升级」执行钮(与⑦同位不同文,OCR 天然互斥)
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            self._upgrade_count += 1
            return self.round_retry(f'快速升级已执行(第{self._upgrade_count}次),等横幅',
                                    wait=_LC_ASCEND_SETTLE_SEC)

        farm_budget_left = self.farm_dungeon and self._farm_rounds < self.farm_rounds_max

        # ⑦ 缺料态执行钮:「使用通用材料补全」(通用可覆盖缺口,消耗通用
        # 材料) /「材料合成」(不需通用材料的合成:原始材料满足或通用材料
        # 不够)——两者点击均弹同款「材料补全」确认框,fill_generic 路线
        # 处理一致;fill_generic=False 时「材料合成」形态直接判停——该形态
        # 原始材料已足够,按快速刷取机制(无可刷缺口)预期无收益,走刷取链
        # 只会空烧重试预算
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-通用材料补全').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-通用材料补全').rect.center)
                return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)
            if farm_budget_left:
                return self.round_success(status='NEED_FARM')
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 缺料且 fill_generic/farm_dungeon 均未授权,判停于等级 %s',
                     self._capped_level)
            return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)

        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-材料合成').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-材料合成').rect.center)
                return self.round_retry('已点材料合成,等确认弹窗', wait=1.5)
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 材料合成形态(快速刷取无效)且 fill_generic 未授权,'
                     '判停于等级 %s', self._capped_level)
            return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)

        # ⑧ 无补全钮:仅剩刷取路线(缺可刷材料时「快速刷取」钮在场)
        if farm_budget_left and self.round_by_find_area(
                screen, _LC_ASCEND_SCREEN, '按钮-快速刷取').is_success:
            return self.round_success(status='NEED_FARM')

        # ⑨ 判停:「材料不足」灰字(全缺:晋阶与合成原料均不足)显式识别,
        # 其余(缺不可刷材料或未授权)走通用兜底——两者都是不可推进终态,
        # 仅日志文案区分
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '文本-材料不足').is_success:
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 右下「材料不足」灰字(全缺),判停于等级 %s', self._capped_level)
            return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)
        self._capped = True
        self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
        log.info('光锥晋阶: 无可推进路径(缺不可刷材料或未授权),判停于等级 %s', self._capped_level)
        return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)

    @node_from(from_name='升级循环', status='NEED_FARM')
    @operation_node(name='打开资源窗口', node_max_retry_times=3)
    def open_farm_window(self) -> OperationRoundResult:
        """点「快速刷取」→「培养还需获取资源」窗口(until=窗口标题)。

        ⚠️ 按钮禁用盲区:缺不可刷材料时按钮白底可 OCR 但点击静默无反应
        (游戏提示「当前并未缺少可以通过快速刷取获取的材料」)——until 超时
        即此形态,失败消息提示改走 fill_generic。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _LC_ASCEND_SCREEN, '按钮-快速刷取',
            until_find_all=[(_RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return result
        if result.is_fail:
            return self.round_fail('打开快速刷取资源窗口失败——大概率缺不可刷材料'
                                   '(游戏判定无可刷缺口),改用 fill_generic 通用材料补全')
        return result

    @node_from(from_name='打开资源窗口')
    @operation_node(name='进入副本', node_max_retry_times=3)
    def enter_dungeon(self) -> OperationRoundResult:
        """资源窗口点缺料行「进入」→ 直达对应副本挑战画面(until=挑战锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _RESOURCE_WINDOW_SCREEN, '按钮-进入副本',
            until_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='进入副本')
    @operation_node(name='副本刷取分流')
    def farm_in_dungeon(self) -> OperationRoundResult:
        """副本画面按 use_fast_ticket 分流:券免战斗 / 正常挑战自动战斗。"""
        screen = self.last_screenshot
        if self.use_fast_ticket:
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-快速刷取副本',
                until_find_all=[(_FAST_FARM_DIALOG, '标题-快速刷取弹窗')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_success(status='USE_TICKET')
            return result
        # 副本态锚(「拟造花萼」标题)在场才点挑战;否则(编队态/战斗态/结算态)
        # 直接交手动战斗节点分类——⚠️「挑战按钮」area 的 rect/text 与编队画面
        # 「开始挑战」坐标巧合重叠,无副本态前置判定会在编队画面误点开新战斗
        # (实测 23 场事故,星琼被自动购开拓力)。边界:锚只覆盖拟造花萼类副本,
        # 其他副本类型(侵蚀之隧等)实机遇到时补建档再泛化。
        if not self.round_by_find_area(
                screen, _CHALLENGE_SCREEN, '标题-拟造花萼').is_success:
            return self.round_success(status='MANUAL_FIGHT')
        result = self.round_by_find_and_click_area(
            screen, _CHALLENGE_SCREEN, '挑战按钮',
            until_find_all=[(_CHALLENGE_SCREEN, '按钮-开始编队挑战')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='MANUAL_FIGHT')
        return result

    @node_from(from_name='副本刷取分流', status='USE_TICKET')
    @operation_node(name='券确认刷取', node_max_retry_times=6)
    def confirm_ticket_farm(self) -> OperationRoundResult:
        """确认框内把刷取次数设到 farm_times_per_round → 点确认 → until
        结果框「关闭」出现(结果框为独立画面「快速刷取结果弹窗」,出现 =
        领奖完成)。

        次数设置注意:光锥确认框次数不记忆(重开恒 1,与角色晋阶线不同),
        现读+补偿式设置两种情况天然兼容。"""
        screen = self.last_screenshot
        # WAIT 重入幂等:带 until 的 round_by_find_and_click_area 未等到锚时
        # 以 WAIT 返回,引擎会原样重跑本节点——重入时确认点击已发出,按画面态
        # 分流:开拓力补充弹窗在 = 券已扣但开拓力不够,刷取被拦,显式判停
        # (WAIT 循环无重试上限,不判停会空转烧穿预算);结果框在 = 刷取完成
        # 交返回分类;两弹窗都不在 = 刷取进行中慢询等待;只有确认框在才执行
        # 次数设置与确认点击
        if self.round_by_find_area(screen, '开拓力补充弹窗', '标题-开拓力补充弹窗').is_success:
            self._farm_draws -= self._farm_times_set  # 本轮未成交,回滚确认前计数
            return self.round_fail('开拓力不足:游戏弹「开拓力补充」弹窗拦截刷取,'
                                   '判停待开拓力/备用开拓力恢复')
        if self.round_by_find_area(screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果').is_success:
            return self.round_success(status='RESULT_OPEN', wait=1.5)
        if not self.round_by_find_area(screen, _FAST_FARM_DIALOG, '标题-快速刷取弹窗').is_success:
            return self.round_wait('刷取执行中,等结果框', wait=2)
        self._farm_rounds += 1
        set_result = self._set_farm_times(self.farm_times_per_round)
        if not set_result.is_success:
            return set_result
        self._farm_draws += self._farm_times_set
        log.info('光锥晋阶: 第 %d 轮券刷取 %d 次(消耗开拓力 %d + 券 %d,'
                 '券免战斗开拓力照扣)',
                 self._farm_rounds, self._farm_times_set,
                 self._farm_times_set * _LC_FARM_TRAILBLAZE_PER,
                 self._farm_times_set * _LC_FARM_TICKET_PER)
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _FAST_FARM_DIALOG, '按钮-确认快速刷取',
            until_find_all=[(_FAST_FARM_RESULT, '按钮-关闭刷取结果')],
            pre_delay=0.5, success_wait=2, retry_wait=2,
        )

    def _set_farm_times(self, target: int) -> OperationRoundResult:
        """确认框内把次数设到目标:target=-1 = 点「^」拉满(滑条上限随副本
        类型,拟造花萼实测24);正数 = OCR 读「刷取次数 N」现值 → 点「+」补
        差值 → 达标即成。失败显式返回,交由节点预算兜底。"""
        if target == -1:
            max_area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-刷取次数拉满')
            self.ctx.controller.click(max_area.rect.center)
            time.sleep(1)  # 滑条动画
            current = self._read_farm_times()
            if current is None:
                time.sleep(1)
                current = self._read_farm_times()
            if current is None:
                return self.round_fail('拉满后无法读取刷取次数')
            self._farm_times_set = current
            log.info('光锥晋阶: 刷取次数已拉满至 %d', current)
            return self.round_success()
        plus_area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-刷取次数加')
        for _ in range(target + 3):  # 点数上界 = 目标+3(防 OCR 偏差死循环)
            current = self._read_farm_times()
            if current is None:
                return self.round_fail('无法读取确认框刷取次数')
            if current >= target:
                self._farm_times_set = current
                return self.round_success()
            self.ctx.controller.click(plus_area.rect.center)
            time.sleep(0.4)  # 滑条动画
        return self.round_fail(f'刷取次数未能设到 {target}')

    def _read_farm_times(self) -> int | None:
        """确认框「刷取次数 N」OCR 取 N。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '读区-刷取次数')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'\d+', str(r.data or ''))
            if m:
                return int(m.group())
        return None

    @node_from(from_name='副本刷取分流', status='MANUAL_FIGHT')
    @operation_node(name='手动挑战战斗', node_max_retry_times=30)
    def manual_fight(self) -> OperationRoundResult:
        """编队态确认并点开始挑战;战斗/结算/退出交回返回分类(结算分支点
        「退出关卡」)。⚠️ 编队态判定必须双锚:「队伍标题」在 + 「拟造花萼」
        标题(副本态锚)不在——「开始编队挑战」area 的 rect/text 与副本态
        「挑战按钮」坐标巧合重叠,单 area 判定会在副本画面误命中导致无限
        开战(实测 23 场事故,星琼被自动购开拓力)。"""
        screen = self.last_screenshot
        in_team = self.round_by_find_area(
            screen, _CHALLENGE_SCREEN, '队伍标题').is_success
        in_dungeon = self.round_by_find_area(
            screen, _CHALLENGE_SCREEN, '标题-拟造花萼').is_success
        if not (in_team and not in_dungeon):
            # 非编队态(战斗中/结算/副本画面):交回返回分类收口
            log.info('光锥晋阶: 已离开编队画面(战斗/结算态),交返回分类')
            return self.round_success(status='BATTLE_DONE', wait=2)
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_CHALLENGE_SCREEN, '按钮-开始编队挑战').rect.center)
        self._farm_rounds += 1
        self._manual_fights += 1
        log.info('光锥晋阶: 第 %d 场手动刷取开始(消耗开拓力 %d)',
                 self._manual_fights, _LC_FARM_TRAILBLAZE_PER)
        return self.round_retry('战斗进行中', wait=_LC_FIGHT_POLL_SEC)

    @node_from(from_name='券确认刷取')
    @node_from(from_name='手动挑战战斗')
    @node_from(from_name='手动挑战战斗', status='BATTLE_DONE')
    @node_from(from_name='入口核对', status='IN_CHALLENGE')
    @operation_node(name='刷取返回分类', node_max_retry_times=30)
    def back_after_farm(self) -> OperationRoundResult:
        """刷取后返回分类(flat):手动路线与券路线的落点不同——

        - 券路线:副本「关闭X」按栈回退,沿途经结果框/资源窗口 → 等级提升;
        - 手动路线:浮层栈已卸载,副本「关闭X」直接回大世界 → BACK_TO_WORLD
          交 reenter_from_world 重走入口链。

        每轮识别当前画面,点对应层的关闭控件,直到回到等级提升。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-光锥详情').is_success:
            log.info('光锥晋阶: 刷取完成回到等级提升,已刷 %d 轮', self._farm_rounds)
            return self.round_success(status='FARMED', wait=1)
        # 结算画面(战斗已胜,含退出关卡/再来一次):点退出关卡回副本画面
        if self.round_by_find_area(screen, _BATTLE_SCREEN, '按钮-退出关卡').is_success:
            result = self.round_by_find_and_click_area(
                screen, _BATTLE_SCREEN, '按钮-退出关卡',
                until_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('结算已退出,重入分类', wait=2)
            return result
        if self.round_by_find_area(screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果').is_success:
            result = self.round_by_find_and_click_area(
                screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果',
                until_not_find_all=[(_FAST_FARM_RESULT, '按钮-关闭刷取结果')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('刷取结果框已关,重入分类', wait=1)
            return result
        # 券确认刷取的两类残留弹窗(开拓力不足判停/中断现场遗留,盖住副本
        # 锚致整帧识别 None,不走此分支会落进过渡帧兜底空转烧预算):点取消
        # 清场后重入分类——补充弹窗「确认」是星琼购开拓力,永不触碰
        if self.round_by_find_area(screen, '开拓力补充弹窗', '标题-开拓力补充弹窗').is_success:
            result = self.round_by_find_and_click_area(
                screen, '开拓力补充弹窗', '按钮-取消',
                until_not_find_all=[('开拓力补充弹窗', '标题-开拓力补充弹窗')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('开拓力补充弹窗已关,重入分类', wait=1.5)
            return result
        if self.round_by_find_area(screen, _FAST_FARM_DIALOG, '标题-快速刷取弹窗').is_success:
            result = self.round_by_find_and_click_area(
                screen, _FAST_FARM_DIALOG, '按钮-取消',
                until_not_find_all=[(_FAST_FARM_DIALOG, '标题-快速刷取弹窗')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('选次数确认框已取消,重入分类', wait=1.5)
            return result
        if self.round_by_find_area(screen, _RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口').is_success:
            result = self.round_by_find_and_click_area(
                screen, _RESOURCE_WINDOW_SCREEN, '按钮-关闭资源窗口',
                until_not_find_all=[(_RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('资源窗口已关,重入分类', wait=1)
            return result
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[_CHALLENGE_SCREEN, _WORLD_SCREEN, _DETAIL_SCREEN,
                                      _LC_TAB_SCREEN, '大世界'])
        if current == _CHALLENGE_SCREEN:
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-关闭副本',
                until_not_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
                pre_delay=0.5, success_wait=2, retry_wait=2,
            )
            if result.is_success:
                # 手动路线:副本画面为重建态,关闭后落大世界;券路线:按栈回
                # 退到等级提升——两种落点都交回本分类重判
                return self.round_retry('副本画面已关,重入分类', wait=2)
            return result
        if current in (_WORLD_SCREEN, '大世界'):
            return self.round_success(status='BACK_TO_WORLD', wait=1)
        if current in (_DETAIL_SCREEN, _LC_TAB_SCREEN):
            return self.round_success(status='BACK_TO_CHARACTER', wait=1)
        return self.round_retry('返回途中未识别画面(过渡帧),等稳定重判', wait=1.5)

    @node_from(from_name='刷取返回分类', status='BACK_TO_WORLD')
    @node_from(from_name='刷取返回分类', status='BACK_TO_CHARACTER')
    @node_from(from_name='入口核对', status='BACK_TO_WORLD')
    @operation_node(name='重走入口链', node_max_retry_times=30)
    def reenter_from_world(self) -> OperationRoundResult:
        """手动刷取返回链收口:副本关闭落到大世界/角色页(浮层栈已卸载),
        重走 光锥TAB 入口链回等级提升。

        步骤:大世界点右上角色图标 → 详情 → SelectCharacterOp(入口记下的
        角色名) → 切光锥 TAB → 点强化 → until 等级提升 → FARMED 交回升级
        循环。

        防升错防线:无入口记名时不得接管——角色详情不记忆上次角色(显示
        列表首位)、光锥 TAB 归属不可凭画面确认,显式失败让调用方从目标
        角色的光锥 TAB 重新发起;落在光锥 TAB 时有记名还须读名区一致才
        接管点强化。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-光锥详情').is_success:
            log.info('光锥晋阶: 已回到等级提升,重入升级循环')
            return self.round_success(status='FARMED', wait=1)

        current = self.check_and_update_current_screen(
            screen, screen_name_list=[_WORLD_SCREEN, '大世界', _DETAIL_SCREEN,
                                      _LC_TAB_SCREEN])
        if current in (_WORLD_SCREEN, '大世界'):
            # 大世界锁光标,点击需 pc_alt
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_WORLD_SCREEN, '右上图标-角色详情').rect.center,
                pc_alt=True)
            return self.round_retry('已点角色详情图标,等详情页', wait=2)
        if current == _LC_TAB_SCREEN:
            # ⚠️ 角色页记忆的位置不一定是目标角色(实测记忆的是最近战斗编队
            # 首位,非中断前的目标角色)——落在光锥 TAB 时须校验:有记名且
            # 读名区读出的角色一致才接管点强化,否则不可盲点强化,否则会升错
            # 人的光锥
            if self._char_name is not None:
                seen = self._read_character_name()
                if seen == self._char_name:
                    result = self.round_by_find_and_click_area(
                        self.last_screenshot, _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN,
                        until_find_all=[(_LC_ASCEND_SCREEN, '标题-光锥详情')],
                        pre_delay=0.5, success_wait=1.5, retry_wait=2,
                    )
                    if result.is_success:
                        return self.round_success(status='FARMED', wait=1)
                    return result
            return self.round_fail('落在光锥 TAB 但无法确认是目标角色的光锥'
                                   '(入口未记名或读名不一致),为防升错放弃接管'
                                   '——请从目标角色的光锥 TAB 重新发起')
        if current != _DETAIL_SCREEN:
            return self.round_retry(f'入口链中画面未识别(判定: {current}),等稳定重判', wait=1.5)

        # 已在详情页:有入口记名才重选——⚠️角色详情不记忆上次角色(显示列表
        # 首位),无记名时切 TAB 升的是谁不可知,显式失败防升错(实测角色页
        # 记忆≠目标角色的反例见上方 LC_TAB 分支注释)
        if self._char_name is None:
            return self.round_fail('落在角色详情但入口未读到角色名,无法安全重选'
                                   '(角色详情显示的是列表首位而非上次浏览角色)'
                                   '——请从目标角色的光锥 TAB 重新发起')
        select_op = SelectCharacterOp(self.ctx, cn_name=self._char_name)
        select_result = select_op.execute()
        if not select_result.success:
            return self.round_fail(f'重选角色 {self._char_name} 失败: {select_result.status}')
        tab_op = SwitchCharacterTabOp(self.ctx, tab_name='光锥')
        tab_result = tab_op.execute()
        if not tab_result.success:
            return self.round_fail(f'切光锥 TAB 失败: {tab_result.status}')
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _LC_TAB_SCREEN, _ENTRY_BTN_STRENGTHEN,
            until_find_all=[(_LC_ASCEND_SCREEN, '标题-光锥详情')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='FARMED', wait=1)
        return result
