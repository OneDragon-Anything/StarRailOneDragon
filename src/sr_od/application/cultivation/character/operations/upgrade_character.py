"""角色详情页晋阶升级 operation(把角色升到 80 级满级/材料耗尽判停)。

角色养成系列 op 第四步(与负责人对齐的四步分工):前三步进详情/选角色/切
「详情」TAB 后,本步执行等级提升与晋阶,直到 80 级满级或材料不足判停。

交互模型(实机摸底:等级1角色全形态链路):
- 详情 TAB 右下按钮三态:等级未满上限 =「升级」;到上限未满 80 =「晋阶」;
  80/80 = 无按钮(已满判据)。两个按钮点开同一个「角色-等级提升」界面;
- 界面「快速升级」开关恒开(op 不动开关):材料自动预填到可达等级;
- 界面右下按钮分流(白/灰底文本直接区分,find 按 text 天然互斥):
  材料足 = 白底「快速升级」,点击直接执行;缺专属材料但通用材料(灵之珠泪,
  量大不稀缺)够 = 白底「使用通用材料补全」→「材料补全」确认框 → **确认即
  执行**(升级态补经验材料后继续升;晋阶态补晋阶材料后直接晋阶),弹对应
  结果横幅;全缺 = 灰底「材料不足」;
- 升到当前上限后界面自动切晋阶态(当前→下一阶段对比视图),晋阶材料需求
  单独列出,执行晋阶后上限提升,继续升级——升级与晋阶交替直到 80;
- 执行后横幅两种标题:升级 =「等级提升」、晋阶 =「角色晋阶」,点空白关闭;
- 右下「快速刷取」(新版交互实机摸底):点开弹「培养还需获取资源」
  窗口(缺料材料清单,每行「开拓力30 + 进入」)→ 点「进入」直达对应副本挑战
  画面 → 两条刷取路线由 use_fast_ticket 分流:True = 副本画面左下「快速刷取」
  (快速刷取券)→ 确认框「消耗开拓力30+券3」→ 确认免战斗直接领奖;
  False = 正常「挑战」→ 编队「开始挑战」→ 自动战斗 → 结算「退出关卡」。
  刷完逐层回退(副本 X → 资源窗口 X)回等级提升界面,材料齐后继续升级——
  每轮刷取次数 = farm_times_per_round(确认框内 OCR 现读 + 点「+」设置),
  材料够不够由右下按钮状态自反馈,不足再走刷取直至预算(farm_rounds_max
  轮)耗尽。

返回链差异(手动战斗兼容,与光锥线实测对照):
- 券路线:副本「关闭X」按浮层栈回退 →「培养还需获取资源」→ 角色-等级提升;
- 手动路线:进入战斗时浮层栈被游戏卸载,「退出关卡」后副本画面为重建态,
  「关闭X」直接回**大世界**——需重走入口链:大世界右上角色图标 → 角色详情
  (不记忆上次角色,显示列表首位)→ 重选角色 → 切「详情」TAB。
  角色名在入口核对时从详情页左上读名区 OCR 记下(格式「命途/名字」)。

副本类型锚(挑战副本画面左上标题):角色线缺料副本两类——拟造花萼(金,
经验材料)与凝滞虚影(晋阶材料,开拓力 30/次),标题同槽位同版式(副本详情
共用版式,凝滞虚影锚坐标经实机截图 OCR 核验与拟造花萼同位)。⚠️「挑战
按钮」area 与编队画面「开始编队挑战」坐标重叠、文本 LCS 互恰,编队态判定
必须双锚(队伍标题在 + 副本类型标题不在);锚只覆盖上述两类副本,其他类型
实机遇到时补建档再泛化。

补料路线与优先级:通用材料补全(fill_generic 默认 True,确认即执行——
通用材料非稀缺,用户裁定的最优先路线)优先于刷取——右下按钮可点时不进
刷取流程;右下全灰(「材料不足」)时由 farm_dungeon 控制:False(默认,
安全)= 判停收尾(零额外消耗);True = 走快速刷取(刷取真实消耗开拓力
30/次,消耗记账以确认框实际设到的次数为准,配置值 -1 是「拉满」指令而非
次数)。

前置:角色详情画面·详情 TAB·列表已收起(前三步保证);本 op 不选角色、
不切页签——起点不符显式失败,组合编排归调用方。
"""

import re
import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.challenge_mission.resume_from_battle_fail import ResumeFromBattleFail
from sr_od.context.sr_context import SrContext
from sr_od.operations.select_character import SelectCharacterOp
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.switch_character_tab import SwitchCharacterTabOp

_DETAIL_SCREEN: str = '角色-详情'
_ASCEND_SCREEN: str = '角色-等级提升'
_CHALLENGE_SCREEN: str = '挑战副本'
_WORLD_SCREEN: str = '大世界-普通'
_BATTLE_SCREEN: str = '战斗画面'
_BATTLE_FAIL_SCREEN: str = '大世界-战斗失败'
# 快速刷取两弹窗独立建档(选次数/结果两个弹窗,标题同名不同位,各自
# id_mark=标题;模态盖住副本 id_mark,识别与交互都走弹窗画面)
_FAST_FARM_DIALOG: str = '快速刷取弹窗'
_FAST_FARM_RESULT: str = '快速刷取结果弹窗'
_RESOURCE_WINDOW_SCREEN: str = '培养资源窗口'
_LIST_SCREEN: str = '角色-列表'

# 升级/晋阶执行的横幅+动画稳定等待(实测约 2s,点空白后再收尾)
_ASCEND_SETTLE_SEC: float = 2.5
# 通用材料补全确认后的等待:确认即执行升级/晋阶并弹横幅,横幅弹出动画
# 约 1-2s,太短会截到动画中帧(横幅文字未到位 → 横幅锚不命中 → 过渡态误判)
_FILL_SETTLE_SEC: float = 3.0
# 每次刷取的固定消耗(难度 IV 实测;两项都扣)
_FARM_TRAILBLAZE_PER: int = 30
_FARM_TICKET_PER: int = 3

# 详情页入口按钮两 area 同 rect 不同 text,OCR find 天然互斥
_ENTRY_BTN_RISE: str = '按钮-升级'
_ENTRY_BTN_ASCEND: str = '按钮-晋阶'


class UpgradeCharacterOp(SrOperation):
    """把当前角色升到 80 级满级(或材料耗尽判停),消耗养成材料与晋阶材料。
    起点:角色-详情画面·详情 TAB·列表已收起;终点:角色-详情画面(详情 TAB)。

    结果状态:MAX_LEVEL(已到 80 满级)/ MATERIAL_CAPPED(材料耗尽停在
    当前等级)/ POWER_CAPPED(开拓力+备用耗尽刷取被拦,原路清场返回详情页,
    开拓力随时间恢复,续跑即继续)。已满级起点直接成功(MAX_LEVEL)。

    界面右下按钮按文本分流:「快速升级」直接执行;「使用通用材料补全」按
    fill_generic 走确认框(消耗灵之珠泪合成补齐);灰底「材料不足」判停。
    升到上限后自动切晋阶态,晋阶执行后继续升级循环。

    fill_generic=True(默认)会消耗通用材料灵之珠泪(非稀缺,用户裁定的
    最优先路线);farm_dungeon=True 会真实刷副本,消耗随路线分列:
    - 券路线(use_fast_ticket=True,默认)= 券刷次数合计 ×(开拓力 30 +
      快速刷取券 3)——券只免战斗,开拓力照扣,券不可自然恢复;
    - 手动路线 = 手动场数 × 开拓力 30(不耗券)。
    每轮次数 farm_times_per_round:正数 = 确认框设到目标;-1(默认)= 拉
    满(滑条上限,随副本类型 8/24),消耗记账以确认框实际读数为准。
    开拓力不足部分由备用开拓力补足(玩家自存体力池,非稀有货币),两者
    都不耗星琼;备用亦耗尽时游戏弹「开拓力补充」弹窗拦截刷取:守卫识别
    后原路清场(取消弹窗/关副本;手动路线经大世界重走入口链)返回详情页,
    状态 POWER_CAPPED——**调用方发起前必须按最坏消耗向用户说明并获明确
    同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, fill_generic: bool = True,
                 farm_dungeon: bool = False, use_fast_ticket: bool = True,
                 farm_times_per_round: int = -1, farm_rounds_max: int = 1):
        """
        :param ctx: 上下文
        :param fill_generic: 缺料时是否用「使用通用材料补全」路线(消耗通用
            材料灵之珠泪合成补齐)。True(默认) = 自动确认材料补全弹窗——
            灵之珠泪量大不稀缺,是官方默认补全路径;调用方发起前向用户提示
            即可。False = 不消耗通用材料。
        :param farm_dungeon: 右下全灰(材料不足,通用材料补全不可用/未授权)
            时是否刷副本补料。False(默认,安全) = 不刷,直接判停收尾;True =
            走「快速刷取 → 资源窗口 → 进入副本」路线刷补材料继续升级
            (**真实消耗开拓力**)。启用前调用方必须向用户说明并获同意。
        :param use_fast_ticket: farm_dungeon=True 时的刷取方式。
            True(默认) = 副本内用「快速刷取」券免战斗直接领奖(**每次刷取
            消耗开拓力 30 + 快速刷取券 3,券只免战斗开拓力照扣,券不可自然
            恢复**)。False = 正常挑战自动战斗(每场消耗开拓力 30,不耗券,
            耗时约 2 分钟/轮)。
        :param farm_times_per_round: 每轮刷取次数。正数 = 确认框内设置的固定
            次数(OCR 现读 + 点「+」设到目标;滑条上限随副本类型 8/24,超出
            部分由游戏封顶)。默认 -1 = 点「^」拉满——材料是共享库存,多余
            可给其他角色或留未来用,用户裁定的默认策略。
        :param farm_rounds_max: 整个运行允许的刷取轮数上限(耗尽判停收尾,
            调用方可续跑)。默认 1 = 只刷一轮(拉满),回来不够即判停报告
            ——多轮连刷的缺口应由调用方按剩余预算显式续跑。
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
        SrOperation.__init__(self, ctx, op_name=gt('角色晋阶升级')
                             + ('(券刷取)' if farm_dungeon and use_fast_ticket else '')
                             + ('(手动刷取)' if farm_dungeon and not use_fast_ticket else '')
                             + ('' if fill_generic else '(不用通用材料)'),
                             node_max_retry_times=40)  # 升级↔晋阶交替多轮(≤6 阶晋阶+分段升级+横幅关闭),默认必中途夭折
        self._entry_btn_area: str = _ENTRY_BTN_ASCEND  #: 入口命中的按钮 area(打开界面用)
        self._char_name: str | None = None  #: 入口记下的角色名(手动刷取回大世界后重选用)
        self._capped: bool = False         #: 材料不足已判停(回详情页收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的当前等级(报告用)
        self._stop_status: str = 'MATERIAL_CAPPED'  #: 判停收尾的最终状态(材料耗尽/开拓力耗尽可恢复)
        self._farm_dialog_wait_rounds: int = 0  #: 确认框连开失败的连续等待轮数(副本刷取有界自旋用)
        self._farm_window_wait_rounds: int = 0  #: 资源窗口连开失败的连续等待轮数(快速刷取 toast 漏检兜底自旋用)
        self._squad_clicked: bool = False   #: 编队钮已点击待生效标志(计场数在离开编队态时发生,点击无效的重入轮不重计)
        self._start_level: int | None = None  #: 首入晋阶界面读到的起始等级(收尾报告「起始→结束」口径)
        self._banner_seen: bool = False    #: 横幅沿计数标志(关闭点击未生效的 WAIT 重入轮不重计)
        self._banner_upgrade_count: int = 0  #: 升级结果横幅计数(=实际完成升级次数;通用补全触发的自动升级不经按钮)
        self._banner_promotion_count: int = 0  #: 晋阶结果横幅计数(=实际完成晋阶次数)
        self._farm_rounds: int = 0         #: 本次运行已执行的刷取轮数(预算控制;券轮=1次确认框,手动轮=1场)
        self._farm_draws: int = 0          #: 券刷累计次数(券/开拓力消耗记账;确认框实际设到的次数)
        self._manual_fights: int = 0       #: 手动战斗场数(开拓力消耗记账)
        self._farm_times_set: int = 0      #: 本轮确认框实际设到的次数(_set_farm_times 写入)
        self._ascend_count: int = 0        #: 本次运行已执行的升级次数(日志统计)
        self._promotion_count: int = 0     #: 本次运行已执行的晋阶次数(日志统计)
        if farm_dungeon:
            if use_fast_ticket:
                log.info('晋阶: 缺料将刷副本,路线=券免战斗,每轮 %s 次,预算 %d 轮——'
                         '每次刷取消耗开拓力 %d + 快速刷取券 %d(券不可自然恢复)',
                         '拉满' if farm_times_per_round == -1 else str(farm_times_per_round),
                         farm_rounds_max, _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)
            else:
                log.info('晋阶: 缺料将刷副本,路线=自动战斗,预算 %d 轮——'
                         '每场消耗开拓力 %d(不耗券)',
                         farm_rounds_max, _FARM_TRAILBLAZE_PER)

    #------------------- 识别辅助 -------------------#

    def _read_ascend_level(self) -> int | None:
        """晋阶界面左侧当前等级(读区-当前等级 OCR「等级NN/MM」取当前值)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '读区-当前等级')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'(\d+)\s*/\s*\d+', str(r.data or ''))
            if m:
                return int(m.group(1))
        return None

    def _read_character_name(self) -> str | None:
        """角色详情·详情TAB 左上读名区 OCR「命途/角色名」取「/」后段。

        用途:手动刷取返回链会落到大世界,角色详情不记忆上次角色(实测显示
        列表首位),需凭此名重选。area 未建档/读不出返回 None,返回链到重选
        步时显式失败,不影响升级主流程。"""
        area = self.ctx.screen_loader.get_area(_DETAIL_SCREEN, '读名区-左上')
        if area is None:
            return None
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=self.screenshot(), rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if '/' in text:
                name = text.rsplit('/', maxsplit=1)[-1].strip()
                if name:
                    return name
        return None

    def _in_dungeon_state(self, screen) -> bool:
        """副本画面判定:副本类型标题(拟造花萼/凝滞虚影)任一在场。

        边界:只覆盖两类已建档副本标题,其他类型(侵蚀之隧等)实机遇到时
        补建档再泛化;战斗/结算画面由「按钮-退出关卡」分支先行处理。"""
        return (self.round_by_find_area(
                    screen, _CHALLENGE_SCREEN, '标题-拟造花萼').is_success
                or self.round_by_find_area(
                    screen, _CHALLENGE_SCREEN, '标题-凝滞虚影').is_success)

    def _log_final_summary(self, stop_status: str, level_text: str) -> None:
        """收尾统计日志(判停收尾与满级终态共用):按钮次数与横幅计数分列
        (通用补全触发的自动升级/晋阶不经按钮,以横幅计数与等级差呈现);
        刷取消耗按确认框实际设到的次数记账(配置 -1 是拉满指令非次数),
        手动路线不耗券、开拓力按场数计。"""
        log.info('晋阶: 收尾(%s),等级 %s,升级按钮 %d 次(横幅计 %d)/'
                 '晋阶按钮 %d 次(横幅计 %d)/刷取 %d 轮(券刷 %d 次'
                 '耗开拓力 %d 耗券 %d,手动 %d 场耗开拓力 %d)',
                 stop_status, level_text,
                 self._ascend_count, self._banner_upgrade_count,
                 self._promotion_count, self._banner_promotion_count,
                 self._farm_rounds, self._farm_draws,
                 self._farm_draws * _FARM_TRAILBLAZE_PER,
                 self._farm_draws * _FARM_TICKET_PER,
                 self._manual_fights, self._manual_fights * _FARM_TRAILBLAZE_PER)

    def _close_result_banner(self) -> OperationRoundResult:
        """关闭执行结果横幅(点空白;升级横幅「等级提升」/晋阶横幅「角色晋阶」
        两种标题,任一在即关,until=两横幅都消失)。"""
        screen = self.last_screenshot
        banner_up = (self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-升级结果').is_success
                     or self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-晋阶结果').is_success)
        if not banner_up:
            return self.round_wait('横幅已不在', wait=0.5)
        return self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '点击区-关闭横幅',
            until_not_find_all=[
                (_ASCEND_SCREEN, '标题-升级结果'),
                (_ASCEND_SCREEN, '标题-晋阶结果'),
            ],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """画面级判定分流:常规起点 = 角色-详情·详情TAB(记名 + 右下按钮
        三态);刷取链残留现场(中断遗留的等级提升界面/副本/大世界)按画面
        分流接管。

        画面判定未命中(None:模态弹窗盖住画面 id_mark/战斗结算/过渡帧)时
        逐锚接管,锚序 = 三类残留弹窗标题 → 战斗结算退出钮 → 副本挑战锚 →
        等级提升标题 → 详情页锚;全 MISS 显式失败(禁止对未知画面盲操作)。

        列表浮层开着会遮挡入口按钮(遮挡态),显式失败提示先收列表。手动
        刷取链(farm_dungeon + 非 use_fast_ticket)授权时读名失败 = 消耗前
        判停——返回链落大世界后需凭记名重选角色(角色详情不记忆上次角色),
        打完一场才发现无名会白烧开拓力。"""
        screen = self.last_screenshot
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[_DETAIL_SCREEN, _ASCEND_SCREEN,
                                      _CHALLENGE_SCREEN, _WORLD_SCREEN,
                                      '大世界', _LIST_SCREEN])
        if current == _LIST_SCREEN:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')
        if current == _ASCEND_SCREEN:
            # 中断现场直接落在等级提升界面:直入升级循环(起始等级由循环首轮补读)
            return self.round_success(status='ALREADY_ASCEND')
        if current == _CHALLENGE_SCREEN:
            # 刷取中断现场(副本画面):交返回分类收口(栈回退/大世界分流在彼端)
            return self.round_success(status='LEFTOVER')
        if current in (_WORLD_SCREEN, '大世界'):
            # 手动刷取返回链的中断落点:重走入口链(记名防线在链内)
            return self.round_success(status='BACK_TO_WORLD')
        if current is None:
            # 模态弹窗/结算/过渡帧:逐锚接管
            for probe_screen, probe_anchor, probe_status in (
                    (_FAST_FARM_DIALOG, '标题-快速刷取弹窗', 'LEFTOVER'),
                    (_FAST_FARM_RESULT, '标题-快速刷取弹窗', 'LEFTOVER'),
                    ('开拓力补充弹窗', '标题-开拓力补充弹窗', 'LEFTOVER'),
                    (_BATTLE_SCREEN, '按钮-退出关卡', 'LEFTOVER'),
                    (_CHALLENGE_SCREEN, '挑战按钮', 'LEFTOVER'),
                    (_ASCEND_SCREEN, '标题-等级提升', 'ALREADY_ASCEND'),
                    (_ASCEND_SCREEN, '标题-材料补全弹窗', 'ALREADY_ASCEND')):
                if screen_utils.find_area(
                        self.ctx, screen,
                        probe_screen, probe_anchor) == FindAreaResultEnum.TRUE:
                    return self.round_success(status=probe_status)
            if screen_utils.find_area(
                    self.ctx, screen,
                    _DETAIL_SCREEN, '按钮-属性详情') != FindAreaResultEnum.TRUE:
                return self.round_fail('画面识别失败(None)且无已知浮层锚,'
                                       '请实机确认现场')
        if current != _DETAIL_SCREEN:
            return self.round_fail(f'不在角色详情(当前画面判定: {current});'
                                   f'前置:前三步 op 保证进详情+选角色+切「详情」页签')
        self._char_name = self._read_character_name()
        if self._char_name is None and self.farm_dungeon and not self.use_fast_ticket:
            # 手动链返回后需凭记名重选角色(角色详情不记忆上次角色),读不到
            # 就在消耗前拦住——等打完一场再失败会白烧 1 场开拓力
            return self.round_fail('手动刷取链需凭入口读名在返回后重选角色,'
                                   '左上读名区 OCR 未读到——请实机确认画面,'
                                   '或改用券路线(use_fast_ticket=True)')
        if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_ASCEND).is_success:
            self._entry_btn_area = _ENTRY_BTN_ASCEND
            return self.round_success(status='CAN_ASCEND')
        if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_RISE).is_success:
            self._entry_btn_area = _ENTRY_BTN_RISE
            return self.round_success(status='CAN_UPGRADE')
        return self.round_success(status='ALREADY_MAX')

    @node_from(from_name='入口核对', status='ALREADY_MAX')
    @operation_node(name='已满级收尾')
    def already_max(self) -> OperationRoundResult:
        """已满级(80/80 无按钮):直接成功(无升级空间)。"""
        return self.round_success(status='MAX_LEVEL')

    @node_from(from_name='入口核对', status='CAN_ASCEND')
    @node_from(from_name='入口核对', status='CAN_UPGRADE')
    @operation_node(name='打开晋阶', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """详情页点入口按钮(升级/晋阶,入口核对时记录)→ 等级提升界面
        (until=标题锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, self._entry_btn_area,
            until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开晋阶')
    @node_from(from_name='入口核对', status='ALREADY_ASCEND')
    @node_from(from_name='返回养成界面')  # 刷取链收口:副本刷完回养成界面重入本循环
    @node_from(from_name='打开资源窗口', status='FARM_WINDOW_FAIL')  # 无可刷缺口(toast 正判或漏检兜底):回循环判停收尾
    @node_from(from_name='重走入口链', status='FARMED')  # 手动链收口:大世界重走入口链回到养成界面
    @operation_node(name='升级循环', node_max_retry_times=40)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:确认框 → 横幅 → 判停收尾 → 详情判 → 按钮分流。

        round_retry 内建重入本节点,不设自环出边——本节点发出的
        round_success(MATERIAL_CAPPED/MAX_LEVEL) 无出边匹配 = op 成功结束。

        每轮分类(优先级):
        ① 「材料补全」确认框在 → fill_generic 确认继续 / 未授权取消判停;
        ② 执行结果横幅(升级「等级提升」/晋阶「角色晋阶」)在 → 点空白关
           (沿计数:横幅新出现才计入统计,关闭重试重入轮不重计);
        ③ 已判停(_capped) → 返回箭头回详情页,到了就 MATERIAL_CAPPED 成功;
        ④ 不在等级提升界面 → 详情页判:入口按钮在 = 开界面,都不在 = 满 80;
        ⑤ 界面内右下按钮分流(白/灰底文本直接区分):
           「快速升级」= 材料足,点执行;「使用通用材料补全」= 缺料通用够,
           fill_generic 点(等确认框下一轮)/未授权判停;auto_farm 授权时缺料
           优先走快速刷取子流程(确认弹窗/连刷中/结果框/打开弹窗四态);
           「晋阶执行」= 晋阶态材料足,点执行;全部不命中 = 灰底全缺,判停。
        异常形态(材料足但点击没生效)由节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot
        # 起始等级(统计口径):首次抵达晋阶界面时读,收尾报「起始→结束」
        if self._start_level is None and self.round_by_find_area(
                screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            self._start_level = self._read_ascend_level()

        # ⓪ 材料返还覆盖页(晋阶后游戏返还差额材料,全屏覆盖挡住一切锚)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '文本-材料返还').is_success:
            result = self.round_by_find_and_click_area(
                screen, _ASCEND_SCREEN, '点击区-关闭返还页',
                until_not_find_all=[(_ASCEND_SCREEN, '文本-材料返还')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('材料返还页已关,重入分类', wait=1)
            return result

        # ① 材料补全确认框
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('晋阶: 确认通用材料补全(消耗灵之珠泪合成补齐)')
                return self.round_retry('通用材料补全已确认,等界面刷新', wait=_FILL_SETTLE_SEC)
            # fill_generic=False 不应到达(⑤ 已判停);防御处理 = 取消+判停
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-取消材料补全').rect.center)
            self._capped = True
            self._capped_level = self._read_ascend_level()
            return self.round_retry('取消材料补全,返回收尾', wait=1.5)

        # ② 执行结果横幅(升级/晋阶共用关闭动作;横幅计数=补全合成触发自动
        # 升级/晋阶的统计口径,这类执行不经按钮)
        upgrade_banner = self.round_by_find_area(
            screen, _ASCEND_SCREEN, '标题-升级结果').is_success
        promotion_banner = self.round_by_find_area(
            screen, _ASCEND_SCREEN, '标题-晋阶结果').is_success
        if not (upgrade_banner or promotion_banner):
            self._banner_seen = False  # 横幅消失:沿计数归位,下条新横幅重新计
        else:
            if not self._banner_seen:
                # 沿计数(新出现才计):关闭点击未生效的 WAIT 重入轮不重计
                self._banner_seen = True
                if upgrade_banner:
                    self._banner_upgrade_count += 1
                if promotion_banner:
                    self._banner_promotion_count += 1
            result = self._close_result_banner()
            if result.is_success:
                return self.round_retry('横幅已关,重入分类', wait=1.5)
            return result

        # ③ 材料耗尽已判 → 返回箭头回详情页,到了就以 _stop_status 结束(报告消耗)
        if self._capped:
            if self._capped_level is None:
                self._capped_level = self._read_ascend_level()
            if self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
                level_text = (f'{self._start_level}→{self._capped_level}'
                              if self._start_level is not None
                              else str(self._capped_level))
                self._log_final_summary(self._stop_status, level_text)
                return self.round_success(status=self._stop_status, wait=1.5)
            result = self.round_by_find_and_click_area(
                screen, _ASCEND_SCREEN, '按钮-返回箭头',
                until_find_all=[(_DETAIL_SCREEN, '按钮-属性详情')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('返回详情页,重入收尾', wait=1.5)
            return result

        # ④ 不在等级提升界面:先确认在详情页再判按钮——横幅弹出动画期间
        # 界面锚与详情按钮都不可见,无详情页锚防御会把过渡态误判成满级
        if not self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            if not self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
                return self.round_retry('不在晋阶界面也不在详情页(横幅/加载过渡态),等画面稳定',
                                        wait=1.5)
            if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_ASCEND).is_success:
                self._entry_btn_area = _ENTRY_BTN_ASCEND
            elif self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_RISE).is_success:
                self._entry_btn_area = _ENTRY_BTN_RISE
            else:
                level_text = (f'{self._start_level}→80'
                              if self._start_level is not None else '80')
                self._log_final_summary('MAX_LEVEL', level_text)
                return self.round_success(status='MAX_LEVEL')
            result = self.round_by_find_and_click_area(
                screen, _DETAIL_SCREEN, self._entry_btn_area,
                until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('晋阶界面已开,重入分类', wait=1.5)
            return result

        # ⑤ 右下按钮分流(三个白底按钮,全不命中 = 灰底缺料进刷取路线)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            self._ascend_count += 1
            return self.round_retry(f'快速升级已执行(第{self._ascend_count}次),等横幅',
                                    wait=_ASCEND_SETTLE_SEC)

        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-通用材料补全').is_success:
            if not self.fill_generic:
                # 与光锥线的差异决策:光锥缺料且未授权补全时转 NEED_FARM 刷取;
                # 角色线右下按钮可点 = 缺口可由通用材料覆盖,按补料优先级
                # (通用补全优先于刷取,见模块 docstring)直接判停不进刷取
                self._capped = True
                self._capped_level = self._read_ascend_level()
                log.info('晋阶: 缺料且 fill_generic 未授权,判停于等级 %s', self._capped_level)
                return self.round_retry('材料不足,返回详情收尾', wait=1)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-通用材料补全').rect.center)
            return self.round_retry('已点通用材料补全,等确认框', wait=1.5)

        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-晋阶执行').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-晋阶执行').rect.center)
            self._promotion_count += 1
            return self.round_retry(f'晋阶已执行(第{self._promotion_count}次),等横幅',
                                    wait=_ASCEND_SETTLE_SEC)

        # ⑥ 全部不命中 = 灰底「材料不足」全缺态 → farm_dungeon 授权走刷取,否则判停
        if not self.farm_dungeon or self._farm_rounds >= self.farm_rounds_max:
            self._capped_level = self._read_ascend_level()
            if not self.farm_dungeon:
                log.info('晋阶: 材料全缺(按钮灰底),farm_dungeon 未授权,判停于等级 %s',
                         self._capped_level)
            else:
                log.info('晋阶: 刷取预算(%d 轮)耗尽,判停于等级 %s',
                         self.farm_rounds_max, self._capped_level)
            self._capped = True
            return self.round_retry('材料不足,返回详情收尾', wait=1)
        return self.round_success(status='NEED_FARM')

    @node_from(from_name='升级循环', status='NEED_FARM')
    @operation_node(name='打开资源窗口', node_max_retry_times=3)
    def open_farm_window(self) -> OperationRoundResult:
        """界面左下点「快速刷取」→「培养还需获取资源」窗口(until=窗口标题)。

        ⚠️ 无可刷缺口形态:缺口可由合成覆盖时按钮白底可 OCR 可点,点击
        被游戏拒绝并弹 toast(实测显示 1~2s)——正判:前两个轮探测 toast
        (首轮无害预探+首次点击后的重入轮,帧落 toast 可见窗;计数 ≥2
        抑制——慢开窗时冗余二次点击被拒再弹的 toast 不得误读为无可刷
        缺口),命中即判停收口;helper 的 WAIT(not-found 的 RETRY 同)
        不计重试,toast 漏检由连等 4 轮封顶兜底判停(第 4 轮先于引擎
        重试预算生效,第 3 次 RETRY 后引擎仍重跑本节点不转 FAIL);
        is_fail 仅「区域未配置」可达(全区已建档,兜底防线)。"""
        screen = self.last_screenshot
        if self._farm_window_wait_rounds <= 1 and self.round_by_find_area(
                screen, _ASCEND_SCREEN, '提示-无可刷缺口').is_success:
            self._farm_window_wait_rounds = 0
            self._capped = True
            self._stop_status = 'MATERIAL_CAPPED'
            self.save_screenshot(prefix='快速刷取无可刷缺口')
            log.info('晋阶: 无可刷缺口(游戏 toast 命中),判停收尾——'
                     '可改用 fill_generic 通用材料补全路线')
            return self.round_success(status='FARM_WINDOW_FAIL', wait=1.5)
        result = self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '按钮-快速刷取',
            until_find_all=[(_RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
            pre_delay=0.5, success_wait=0.3, retry_wait=2,
        )
        if result.is_success:
            self._farm_window_wait_rounds = 0
            return result
        if result.is_fail or self._farm_window_wait_rounds >= 3:
            self._farm_window_wait_rounds = 0
            self._capped = True
            self._stop_status = 'MATERIAL_CAPPED'
            if result.is_fail:
                log.info('晋阶: 资源窗口打开失败(%s),判停收尾——'
                         '可改用 fill_generic 通用材料补全路线', result.status)
            else:
                self.save_screenshot(prefix='打开资源窗口')
                log.info('晋阶: 资源窗口连续未打开(toast 漏检,兜底封顶),'
                         '现场已截图,判停收尾——可改用 '
                         'fill_generic 通用材料补全路线')
            return self.round_success(status='FARM_WINDOW_FAIL', wait=1.5)
        self._farm_window_wait_rounds += 1
        return result

    @node_from(from_name='打开资源窗口')
    @operation_node(name='进入副本', node_max_retry_times=3)
    def enter_dungeon(self) -> OperationRoundResult:
        """资源窗口点缺料行的「进入」→ 直达对应副本挑战画面(until=挑战锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _RESOURCE_WINDOW_SCREEN, '按钮-进入副本',
            until_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='进入副本')
    @node_from(from_name='返回养成界面', status='失败重发')
    @operation_node(name='副本刷取')
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
                self._farm_dialog_wait_rounds = 0
                return self.round_success(status='USE_TICKET')
            # 确认框偶发不开:helper 的 WAIT 返回无重试上限,原样返回会无限
            # 自旋——连等超限 = 异常现场,留证后显式失败
            self._farm_dialog_wait_rounds += 1
            if self._farm_dialog_wait_rounds >= 4:
                self.save_screenshot(prefix='副本刷取分流')
                return self.round_fail('快速刷取确认框连续未打开,现场已截图')
            return result
        # 副本态锚(副本类型标题)在场才点挑战;否则按画面态三分——⚠️
        # 「挑战按钮」area 的 rect/text 与编队画面「开始编队挑战」坐标
        # 重叠、文本相似,无副本态前置判定会在编队画面误点开新战斗
        # (光锥线同位实测事故,资源被连环消耗)
        if not self._in_dungeon_state(screen):
            # 编队态:交手动战斗节点点开始挑战
            if self.round_by_find_area(screen, _CHALLENGE_SCREEN, '队伍标题').is_success:
                return self.round_success(status='MANUAL_FIGHT')
            # 挑战按钮在但两类副本标题都读不到 = 未识别副本类型(未建档
            # 类型/标题 OCR 持续失败):交手动路线会零消耗空转(不计场的
            # BATTLE_DONE 反复回环开窗进本)——计重试(瞬时 OCR 失败可
            # 自愈),耗尽显式失败强制补档
            if self.round_by_find_area(screen, _CHALLENGE_SCREEN, '挑战按钮').is_success:
                return self.round_retry('副本类型标题未识别(未建档类型/OCR 未读出),等重判', wait=2)
            # 战斗/结算态:交手动战斗节点分类(计场在离开编队态时发生)
            return self.round_success(status='MANUAL_FIGHT')
        result = self.round_by_find_and_click_area(
            screen, _CHALLENGE_SCREEN, '挑战按钮',
            until_find_all=[(_CHALLENGE_SCREEN, '按钮-开始编队挑战')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='MANUAL_FIGHT')
        return result

    @node_from(from_name='副本刷取', status='USE_TICKET')
    @operation_node(name='券确认刷取', node_max_retry_times=6)
    def confirm_ticket_farm(self) -> OperationRoundResult:
        """确认框内把刷取次数设到 farm_times_per_round(OCR 现读 + 点「+」
        补偿;游戏会记住上次次数,故只增不减,超滑条上限由游戏封顶)→ 点确认
        → until 结果框「关闭」按钮出现(结果框为独立画面「快速刷取结果弹窗」,
        与确认框同名不同位;结果框出现 = 领奖完成)。

        记账口径(幂等,以 _farm_times_set 非零为未记账判据):确认点击生效
        的两个等效证据 = 重入轮看到结果框(领奖完成,主记账点)/ helper 返回
        success——带 until 的 helper 一次调用只点击一次、until 验证在下一次
        调用开头,重入时结果框探测先于 helper 命中,记账必须两处共用
        _settle_farm_accounting,只挂 helper success 则生产时序下不可达
        (预算失效+统计恒 0);确认被开拓力不足拦截 = 本轮未成交未记账,
        作废本轮次数记录即可,不动历史账。"""
        screen = self.last_screenshot
        # WAIT 重入幂等:带 until 的 round_by_find_and_click_area 未等到锚时
        # 以 WAIT 返回,引擎会原样重跑本节点——重入时确认点击已发出,按画面态
        # 分流:结果框在 = 领奖完成(主记账点);开拓力补充弹窗在 = 确认被拦,
        # 本轮未成交,作废次数记录(WAIT 循环无重试上限,不判停会空转烧穿
        # 预算;补充弹窗「确认」是星琼购开拓力,永不触碰);两弹窗都不在 =
        # 刷取进行中慢询等待;只有确认框在才执行次数设置与确认点击
        if self.round_by_find_area(screen, '开拓力补充弹窗', '标题-开拓力补充弹窗').is_success:
            self._farm_times_set = 0  # 未成交未记账,本轮作废,不动历史账
            self._capped = True
            self._stop_status = 'POWER_CAPPED'
            log.info('晋阶: 确认已发出但被开拓力不足拦截,本轮未成交——'
                     '原路清场返回详情页(可待开拓力恢复后续跑)')
            return self.round_success(status='POWER_BLOCKED', wait=2)
        if self.round_by_find_area(screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果').is_success:
            self._settle_farm_accounting()
            return self.round_success(status='RESULT_OPEN', wait=1.5)
        if not self.round_by_find_area(screen, _FAST_FARM_DIALOG, '标题-快速刷取弹窗').is_success:
            return self.round_wait('刷取执行中,等结果框', wait=2)
        # 确认框在:次数未设则先设;已设(重入:确认点击未生效)跳过设次数
        # 只重发确认
        if self._farm_times_set == 0:
            set_result = self._set_farm_times(self.farm_times_per_round)
            if not set_result.is_success:
                return set_result
        result = self.round_by_find_and_click_area(
            screen, _FAST_FARM_DIALOG, '按钮-确认快速刷取',
            until_find_all=[(_FAST_FARM_RESULT, '按钮-关闭刷取结果')],
            pre_delay=0.5, success_wait=2, retry_wait=2,
        )
        if result.is_success:
            self._settle_farm_accounting()
        return result

    def _settle_farm_accounting(self) -> None:
        """本轮券刷取记账(幂等):确认点击生效的两个等效证据(重入轮看到
        结果框 / helper 返回 success)共用;以 _farm_times_set 非零为未记账
        判据,记账后归零,WAIT 重入轮不会重复计。"""
        if self._farm_times_set == 0:
            return
        self._farm_rounds += 1
        self._farm_draws += self._farm_times_set
        log.info('晋阶: 第 %d 轮券刷取 %d 次(消耗开拓力 %d + 快速刷取券 %d,'
                 '券免战斗开拓力照扣)',
                 self._farm_rounds, self._farm_times_set,
                 self._farm_times_set * _FARM_TRAILBLAZE_PER,
                 self._farm_times_set * _FARM_TICKET_PER)
        self._farm_times_set = 0

    def _set_farm_times(self, target: int) -> OperationRoundResult:
        """快速刷取确认框内把次数设到目标:target=-1 = 点「^」拉满(滑条
        上限,随副本类型 8/24);正数 = OCR 读「刷取次数 N」现值 → 点「+」
        补差值 → OCR 复核达标即成。实际设到的值写 _farm_times_set(消耗
        统计口径:配置值 -1 是拉满指令,真实消耗以读数为准)。失败显式
        返回,交由节点预算兜底。"""
        self._farm_times_set = 0
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
            log.info('晋阶: 刷取次数已拉满至 %d', current)
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
            time.sleep(0.4)  # 滑条动画:点击后立即复读会读到旧值再点,越过目标多耗开拓力
        return self.round_fail(f'刷取次数未能设到 {target}')

    def _read_farm_times(self) -> int | None:
        """确认框「刷取次数 N」OCR 取 N(打开即游戏记忆的上次值,非恒 1)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '读区-刷取次数')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'\d+', str(r.data or ''))
            if m:
                return int(m.group())
        return None

    @node_from(from_name='副本刷取', status='MANUAL_FIGHT')
    @operation_node(name='手动挑战战斗', node_max_retry_times=30)
    def manual_fight(self) -> OperationRoundResult:
        """编队态确认并点开始挑战;战斗/结算/退出交返回分类(结算分支点
        「退出关卡」)。

        ⚠️ 编队态判定必须双锚:「队伍标题」在 + 副本类型标题(拟造花萼/
        凝滞虚影)不在——「开始编队挑战」area 的 rect/text 与副本态「挑战
        按钮」坐标重叠、文本 LCS 互恰,单 area 判定会在副本画面误命中导致
        连环误开战(光锥线同位实测事故,资源被连环消耗)。"""
        screen = self.last_screenshot
        # 开拓力不足时「开始挑战」点击无反应或弹补充框拦路:识别即判停,原路
        # 清场返回——盲点重试会空烧战斗轮预算
        if self.round_by_find_area(screen,
                                   '开拓力补充弹窗', '标题-开拓力补充弹窗').is_success:
            self._squad_clicked = False  # 未开战,本旗标作废(计场在离开编队态时)
            self._capped = True
            self._stop_status = 'POWER_CAPPED'
            log.info('晋阶: 手动路线开拓力不足判停,原路清场返回详情页')
            return self.round_success(status='POWER_BLOCKED', wait=2)
        in_team = self.round_by_find_area(
            screen, _CHALLENGE_SCREEN, '队伍标题').is_success
        if not (in_team and not self._in_dungeon_state(screen)):
            # 非编队态(战斗中/结算/副本画面):交返回分类收口;计场在编队钮
            # 点击生效(离开编队态)时发生——点击无效的重入轮不重计
            if self._squad_clicked:
                self._squad_clicked = False
                self._farm_rounds += 1
                self._manual_fights += 1
                log.info('晋阶: 第 %d 场手动刷取开始(消耗开拓力 %d)',
                         self._manual_fights, _FARM_TRAILBLAZE_PER)
            log.info('晋阶: 已离开编队画面(战斗/结算态),交返回分类')
            return self.round_success(status='BATTLE_DONE', wait=2)
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_CHALLENGE_SCREEN, '按钮-开始编队挑战').rect.center)
        self._squad_clicked = True
        return self.round_retry('战斗进行中', wait=15)

    @node_from(from_name='券确认刷取')
    @node_from(from_name='手动挑战战斗')
    @node_from(from_name='手动挑战战斗', status='BATTLE_DONE')
    @node_from(from_name='入口核对', status='LEFTOVER')
    @operation_node(name='返回养成界面', node_max_retry_times=30, timeout_seconds=300)
    def back_to_ascend(self) -> OperationRoundResult:
        """刷取后返回分类(flat):每轮识别当前画面,点对应层的关闭控件,
        直到回到等级提升界面重入升级循环。手动路线与券路线落点不同——

        - 券路线:副本「关闭X」按浮层栈回退,沿途经结果框/资源窗口 → 等级提升;
        - 手动路线:浮层栈已卸载,结算「退出关卡」→ 副本「关闭X」直接回
          大世界 → BACK_TO_WORLD 交重走入口链。

        战斗期等待:手动路线整场战斗(单场约 2 分钟)落末位过渡帧分支
        (全锚 MISS),以 round_wait 慢询——不烧重试预算(30 次 retry 约
        90s 即耗尽,会战斗中途 FAIL 且战场残留游戏内继续自打污染后续
        入口判定),超时兜底交节点 timeout_seconds。

        残留弹窗两类(开拓力不足判停/中断现场遗留,盖住副本/养成锚致整帧
        识别 None):点取消清场后重入分类——补充弹窗「确认」是星琼购开拓力,
        永不触碰。编队画面(队伍标题在场,手动路线开拓力被拦/编队残留的
        落点)点右上 X 回副本画面再逐层回退。副本画面判定走挑战锚探测 +
        非编队态要求:凝滞虚影类副本无画面级精准判定(画面 id_mark 只含
        拟造花萼),而「挑战按钮」area 与编队画面「开始挑战」文本互恰,
        编队画面会误命中。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            log.info('晋阶: 刷取完成回到养成界面,已刷 %d 轮', self._farm_rounds)
            return self.round_success(status='FARMED')
        # 失败画面(新形态,标题锚):委托共享失败继续件回挑战画面。两态锚不
        # 互斥(旧结算画面的「战斗失败」大字落入标题搜索区会误命中),误命中
        # 代价 = 共享件按新形态空转 5 轮(~10s)后转旧形态恢复,行为收敛正确;
        # 形态判定真相源在共享件,本分支只做疑似失败态快筛。委托 fail 原样
        # 透传(现场交调用方)。
        if self.round_by_find_area(screen, _BATTLE_FAIL_SCREEN, '标题-战斗失败').is_success:
            op = ResumeFromBattleFail(self.ctx)
            op_result = op.execute()
            if not op_result.success:
                return self.round_by_op_result(op_result)
            if self._farm_rounds >= self.farm_rounds_max:
                # 预算检查必须内联在本分支(升级循环的预算判停对失败重发环
                # 不可达):判停出口不走新状态边——关副本回大世界,落既有
                # BACK_TO_WORLD 出口交重走入口链,由升级循环判停收尾
                screen = self.screenshot()  # 共享件已把画面交还挑战画面,重取帧
                result = self.round_by_find_and_click_area(
                    screen, _CHALLENGE_SCREEN, '按钮-关闭副本',
                    until_find_all=[(_WORLD_SCREEN, '右上图标-角色详情')],
                    pre_delay=0.5, success_wait=1.5, retry_wait=2,
                )
                if result.is_success:
                    return self.round_success(status='BACK_TO_WORLD', wait=1)
                return result
            # 预算未超:失败场已计轮(开拓力已扣),交回副本刷取分流重发
            return self.round_success(status='失败重发', wait=1)
        # 结算画面(战斗已胜/败,含退出关卡):点退出关卡回副本画面
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
        # 券确认刷取的两类残留弹窗(开拓力不足判停/中断现场遗留,盖住副本/
        # 养成锚致整帧识别 None):点取消清场后重入分类——补充弹窗「确认」是
        # 星琼购开拓力,永不触碰
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
        # 编队画面(队伍标题在场):点右上 X 回副本画面再逐层回退——手动路线
        # 开拓力被拦(补充弹窗取消后)的落点;X 与副本关闭钮同槽位,点击生效
        # 以队伍锚消失验证
        if self.round_by_find_area(screen, _CHALLENGE_SCREEN, '队伍标题').is_success:
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-关闭副本',
                until_not_find_all=[(_CHALLENGE_SCREEN, '队伍标题')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('编队画面已关,重入分类', wait=1.5)
            return result
        # 副本画面(拟造花萼精准判定在/凝滞虚影仅锚可证):关闭后按路线落点
        # 重判(券路线回资源窗口、手动路线回大世界)——编队态不进此分支
        # (挑战按钮锚与编队「开始挑战」文本互恰,队伍标题作反证)
        if (self.round_by_find_area(screen, _CHALLENGE_SCREEN, '挑战按钮').is_success
                and not self.round_by_find_area(screen, _CHALLENGE_SCREEN, '队伍标题').is_success):
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-关闭副本',
                until_not_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
                pre_delay=0.5, success_wait=2, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('副本画面已关,重入分类', wait=2)
            return result
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[_CHALLENGE_SCREEN, _WORLD_SCREEN, '大世界',
                                      _DETAIL_SCREEN])
        if current in (_WORLD_SCREEN, '大世界'):
            return self.round_success(status='BACK_TO_WORLD', wait=1)
        if current == _DETAIL_SCREEN:
            # 落在角色详情:身份不可凭画面确认(角色详情不记忆上次角色),
            # 交重走入口链凭记名重选(无记名时彼端显式失败防升错)
            return self.round_success(status='BACK_TO_CHARACTER', wait=1)
        # 战斗期(手动路线,全锚 MISS)在此慢询:wait 不计重试(见节点
        # docstring),超时兜底交节点 timeout_seconds
        return self.round_wait('返回途中未识别画面(战斗中/过渡帧),等稳定重判', wait=1.5)

    @node_from(from_name='返回养成界面', status='BACK_TO_WORLD')
    @node_from(from_name='返回养成界面', status='BACK_TO_CHARACTER')
    @node_from(from_name='入口核对', status='BACK_TO_WORLD')
    @operation_node(name='重走入口链', node_max_retry_times=30)
    def reenter_from_world(self) -> OperationRoundResult:
        """手动刷取返回链收口:副本关闭落到大世界/角色页(浮层栈已卸载),
        重走 角色详情 入口链回等级提升。

        步骤:大世界点右上角色图标(大世界锁光标,点击需 pc_alt) → 角色详情
        → SelectCharacterOp(入口记下的角色名) → 切「详情」TAB → FARMED 交回
        升级循环(入口按钮三态由循环④重探——刷取后升/晋阶态可能已变化)。

        防升错防线:无入口记名时不得接管——角色详情不记忆上次角色(显示
        列表首位),重选必须凭记名;无记名显式失败让调用方从目标角色详情
        重新发起。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            log.info('晋阶: 已回到养成界面,重入升级循环')
            return self.round_success(status='FARMED', wait=1)
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[_WORLD_SCREEN, '大世界', _DETAIL_SCREEN])
        if current in (_WORLD_SCREEN, '大世界'):
            # 大世界锁光标,点击需 pc_alt
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_WORLD_SCREEN, '右上图标-角色详情').rect.center,
                pc_alt=True)
            return self.round_retry('已点角色详情图标,等详情页', wait=2)
        if current == _DETAIL_SCREEN:
            # ⚠️ 角色详情不记忆上次角色(显示列表首位),无记名时详情页显示
            # 的角色不可知,显式失败防升错
            if self._char_name is None:
                return self.round_fail('落在角色详情但入口未读到角色名,无法安全重选'
                                       '(角色详情显示的是列表首位而非上次浏览角色)'
                                       '——请从目标角色的详情 TAB 重新发起')
            try:
                select_op = SelectCharacterOp(self.ctx, cn_name=self._char_name)
            except ValueError:
                # 读名 OCR 偏差/变体名不在角色列表:构造期校验拦截,显式失败
                # 带明确文案,不让异常走引擎兜底烧 30 轮重试
                return self.round_fail(f'入口读名 {self._char_name} 不在角色列表,'
                                       '无法安全重选(读名可能不准)——请实机确认')
            select_result = select_op.execute()
            if not select_result.success:
                return self.round_fail(f'重选角色 {self._char_name} 失败: {select_result.status}')
            tab_op = SwitchCharacterTabOp(self.ctx, tab_name='详情')
            tab_result = tab_op.execute()
            if not tab_result.success:
                return self.round_fail(f'切详情 TAB 失败: {tab_result.status}')
            return self.round_success(status='FARMED', wait=1)
        return self.round_retry(f'入口链中画面未识别(判定: {current}),等稳定重判', wait=1.5)
