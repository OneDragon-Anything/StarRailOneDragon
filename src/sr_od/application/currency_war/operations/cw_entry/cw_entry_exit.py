# r279/r302/r303 实战验证(战斗中/胜利结算/失败链三路 ✓);
# 投资策略屏分支 r303b 手动链验证(画面档齐)。
# r317(第三次实录 W71):投资策略屏退局卡点机制根修——
#   ① 分支顺序:投资策略屏(独立屏,右上「返回备战界面」按钮)必须**先**走
#      「选卡+确认」(area 定位,手动实证有效);若先走 :73「返回备战界面」
#      全屏 OCR 点击,该按钮热区与 OCR 框中心偏移(~60px)→ 点击落空 →
#      round_wait 死循环 141x/444s(2026-08-25 实录),且短路 :78 正确分支;
#   ② 结算按钮 OCR 统一收紧 lcs_percent=0.8(与 cw_loop 3b 同款):
#      「继续挑战」默认 0.5 与战斗暂停屏「继续战斗」ratio=0.75 误匹配
#      → 点「继续战斗」恢复战斗 → 退局打转 2min(实录 03:59:35-04:01:35)。
# 锁光标恢复态加固(2026-09-02 一条龙恢复链事故,同 BackToNormalWorldPlus
#   大厅/兜底分支注释):机器重启后游戏直接恢复进 UI 时光标锁定,不带 Alt 的
#   点击全部落空——本 op 所有 UI 坐标点击统一带 pc_alt=True。
# ESC 清零(2026-09-08):备战/overlay 两处 ESC 换建档点击(退局发起=左上
#   门形「退出对局」图标;overlay 族各走建档关闭控件),依据见各分支注释。

"""从货币战争对局中退出(放弃+结算)回大厅。

高频重复操作(测试/刷开局/回滚),手动做很繁琐(Esc→放弃→结算3页→大厅)→ 建成 op 一键调用。
支持入口:备战阶段 / 战斗中 / **事件 overlay**(投资策略/环境/补给/遭遇/巨星/详情浮层)
(任何可识别的对局内态)→ 中断挑战弹窗「放弃并结算」→ 结算 3 页 → 大厅。
全链零 ESC:退局发起 = 备战左上门形「退出对局」图标(建档点击,点开中断挑战
弹窗,与 ESC 等价;overlay 族各走建档关闭控件,依据见各分支注释)。
"""
import difflib
import time
from collections.abc import Callable
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwEntryExit(SrOperation):
    """放弃当前货币战争对局,返回大厅。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='退出货币战争对局')

    @operation_node(name='退出对局', is_start_node=True, node_max_retry_times=30)
    def exit_match(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 已在大厅 → 完成
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            return self.round_success(CwEntryExit.STATUS_AT_LOBBY)

        # 放弃提示 → 放弃并结算
        if self._ocr_click_pc_alt(screen, '放弃并结算'):
            log.info('[cw-exit] 放弃并结算 → 结算页')
            return self.round_wait(wait=2)

        # 结算页 1:挑战失败/下一步。胜利结算屏(局30 实证卡点):
        # 按钮文案是「继续挑战」——先试它,再「下一步」
        # r309b(局31 卡点):「结算-失败」屏(挑战进度屏)按钮是
        # 「前往结算」——第三种文案,先试
        # r317:结算按钮 OCR 统一 lcs_percent=0.8(cw_loop 3b 同款)——
        # 防「继续挑战」误匹配战斗暂停屏「继续战斗」(ratio 0.75,默认 0.5 会命中)。
        if self._ocr_click_pc_alt(screen, '前往结算', lcs_percent=0.8):
            log.info('[cw-exit] 进度结算屏 → 前往结算')
            return self.round_wait(wait=2)
        if self._ocr_click_pc_alt(screen, '继续挑战', lcs_percent=0.8):
            log.info('[cw-exit] 胜利结算 → 继续挑战')
            return self.round_wait(wait=2)
        if self._ocr_click_pc_alt(screen, '下一步', lcs_percent=0.8):
            return self.round_wait(wait=2)

        # 结算页 2:下一页
        if self._ocr_click_pc_alt(screen, '下一页', lcs_percent=0.8):
            return self.round_wait(wait=2)

        # 结算页 3:返回货币战争
        if self._ocr_click_pc_alt(screen, '返回货币战争', lcs_percent=0.8):
            return self.round_wait(wait=2)

        # 结算-失败 步骤1(战败演出未完帧):「挑战结束+挑战进度+点击空白加速」
        # 同屏,「前往结算」尚未出现——旧版全分支 miss 落尾部分支连点右上 X,
        # 演出自动完成前 >10 轮即有界 fail 交外层(退局链实录缺陷,真帧
        # 存档 sr-od-test/screens/货币战争-结算-失败/轮败-点击空白加速.webp)。识别 = 双 area 判定:标识-挑战进度
        # (战败独有 id_mark)+ 提示-点击空白加速(步骤1 独有,演出完即被
        # 「前往结算」按钮同槽顶替)。必须 area 判定而非全屏 OCR:位面过渡屏
        # 「点击空白处继续」与本词共享子序列 4/6(LCS 0.67 过默认阈值),区分
        # 全靠 rect 不相交(其提示 y930 起,本提示 rect y≤922),判据见
        # docs/game/screens/currency_war_settlement_fail.md「状态流转」。
        # 动作 = 点「货币战争-位面过渡/区域-空白点击」中心(1505,950):该坐标
        # 的建档单一源,对局内主路径 CwScreenBattleWait.BLANK 同 Rect 在本结算
        # 族帧上实证加速有效(右下真空档,避开中央演出元素)。
        # 推进与「继续挑战」分支同型:点击即 round_wait;演出完成提示消失后由
        # 上方「前往结算」分支接管,演出自然完成兜底(提示态非持久,无永动面)。
        if (self.round_by_find_area(screen, '货币战争-结算-失败',
                                    '标识-挑战进度').is_success
                and self.round_by_find_area(screen, '货币战争-结算-失败',
                                            '提示-点击空白加速').is_success):
            if self._click_screen_area_center('货币战争-位面过渡', '区域-空白点击'):
                log.info('[cw-exit] 结算-失败步骤1 → 点空白加速')
                return self.round_wait(wait=2)
            return self.round_fail('区域-空白点击 area 缺失,步骤1 加速无法发起')

        # 备战/对局中(无放弃提示)→ 点门形「退出对局」图标弹中断挑战弹窗
        # r317:「备战阶段」旧裸 OCR 必须收紧 lcs=0.8(find_by_ocr 直接 LCS 匹配
        # (无 difflib 前置过滤),默认 0.5 时在投资策略屏误命中「返回备战界面」)
        # T#103 area 化(标识-备战阶段,prep fixture 实帧建档):positional rect
        # 结构性消灭误配面 —— 投资策略屏该 rect 位置不会出现备战阶段文本,
        # lcs 收紧的补丁不再必要。
        if (self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success       # 备战
                or self.round_by_find_area(screen, '货币战争-备战', '标识-备战阶段').is_success   # T#103:原「备战阶段」裸 OCR(lcs=0.8)→ area
                or self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success):
            # 退局发起:点左上门形「退出对局」图标 → 中断挑战弹窗(替代旧 ESC)。
            # 依据:中断挑战弹窗 doc 记「两个入口」(2026-08-17 实测:ESC / 点左上角
            # ~(100,70));左上实为两枚相邻控件——门形退出图标(本 area,视觉中心
            # ≈(61,63),doc 的 (100,70) 落其热区右缘)与难度徽标(按钮-敌人难度
            # 95-180,点它弹的是敌方信息浮层,见 货币战争-敌人信息浮层 doc 入口①),
            # 点门形图标才到放弃链。ESC 语义随画面漂移(无面板时落备战=误弹本弹窗,
            # runtime-ops 运行坑),故以建档点击等价替换。
            if self._click_exit_door():
                return self.round_wait(wait=2)
            return self.round_fail('按钮-退出对局 area 缺失,退局链无法发起(ESC 已禁用)')

        # r303b(局30 实证):「返回备战界面」点后可能弹投资策略
        # 三选一(退局途中绕不过)→ 选左卡+确认(任意策略都行,
        # 本局反正要弃)→ 回备战再走退出对局链
        # r317 顺序修正:本分支(round_by_find_area area 定位)必须**在**
        # 「返回备战界面」(round_by_ocr_and_click 全屏 OCR)**之前**——
        # 投资策略屏是独立屏,右上角也有「返回备战界面」按钮文字:若
        # OCR 分支在前,会命中该文字并点击 OCR 框中心 (1790,57),但按钮
        # 热区中心 ≈ (1850,60)(像素实测,OCR 框 1717-1863 vs 底框
        # 1780-1920)→ 点击落空 → round_wait 死循环 141x/444s(2026-08-25
        # 实录,零分支推进),且短路本分支(选卡+确认,手动实证有效)。
        if self.round_by_find_area(screen, '货币战争-投资策略',
                                   '标识-请选择投资策略').is_success:
            # W62 件3(ADR-0329):确认按钮点击不落地修复——旧版
            # ``round_by_ocr_and_click(scr2, '确认')`` 全屏 OCR 搜「确认」
            # 对 stylized 按钮静默失配(验证局清场 748s 卡行;手动
            # (460,475)+(978,984) 两击解锁,(978,984) = screen_info
            # 「按钮-确认」area 中心)→ 改用 area 中心点击,与生产路径
            # CwScreenInvestStrategy 同源(同屏同按钮 area 中心,实机验证可靠);
            # 点击带 bug#1 mouse_move 缓解(partner reset 根因同类)。
            _confirm = (area_center(self.ctx, '按钮-确认', '货币战争-投资策略')
                        or Point(978, 983))   # 兜底常量 = CwScreenInvestStrategy.CONFIRM
            # ⚠️ 待实机核(坐标单一源清点项):左卡 (460,475) 为实测字面量未
            # area 化(本批实机纪律不可测,建档挂账实机批)。
            self.ctx.controller.mouse_move(Point(460, 475))   # 左卡
            self.ctx.controller.click(Point(460, 475), pc_alt=True)
            time.sleep(1.2)
            self.ctx.controller.mouse_move(_confirm)
            self.ctx.controller.click(_confirm, pc_alt=True)
            log.info('[cw-exit] 投资策略三选一(退局途中)→ 左卡+确认(area 定位)')
            return self.round_wait(wait=2)

        # 事件 overlay(投资策略/环境 有「返回备战界面」)→ 点回备战,下轮走备战分支点「退出对局」弃局。
        # 修 bug:事件屏无「放弃并结算」/备战文本 → 全分支不命中 → retry 死循环(2026-08-04 实测卡 210s+)。
        # r317 顺序修正:本分支**必须在投资策略分支之后**(投资策略屏也是独立屏,
        # 右上角同有「返回备战界面」按钮文字;全屏 OCR 点击其 OCR 框中心落空——
        # 按钮热区 vs OCR 框中心偏移 ~60px,实录 141x 等待零推进)→ 此处仅处理
        # 非投资策略的事件 overlay(环境等)。lcs_percent=0.8 同 cw_loop 3b
        # (防「返回备战界面」与「返回货币战争」共享子序列 0.5 误匹配)。
        if self._ocr_click_pc_alt(screen, '返回备战界面', lcs_percent=0.8):
            return self.round_wait(wait=2)
        # 事件 overlay 族兜底(:128 全屏 OCR 未命中时)→ 各自建档点击,零 ESC。
        # 每子态的替代控件与依据:
        # - 补给/遭遇:屏上「返回备战界面」按钮 area(货币战争-补给 / 货币战争-遭遇
        #   节点建档),与上一分支同目的的 area 化兜底腿(按钮热区 vs OCR 框中心
        #   偏移史见 r317 注释,area 中心直达热区);
        # - 盛会之星:档内无关闭控件(仅候选卡+确认选择),浮层不遮左上门形图标
        #   (cw_megastar 实拍帧核验)→ 直点「退出对局」进中断挑战弹窗——退局
        #   语境目标是弃局,无需先关浮层回备战;
        # - 可合成列表(装备详情浮窗)/角色详情:点面板外空白关闭 = 选中驱动
        #   deselect(装备详情浮窗 2026-08-14 live 验「点空白 → 关闭回备战」;
        #   建档 货币战争-备战/区域-空白关闭,与主消费路径 CwScreenRoleDetailOverlay
        #   同源同控件),连续未关升级门图标兜底。
        # 有界性见 _overlay_branch(K1:retry 化,预算归节点 30)。
        # 有界性(K1 拆除自带上界,验证废除 2026-09-10):overlay 分支改
        # round_retry(计节点 retry 预算,node_max_retry_times=30)——原
        # OVERLAY_ACTION_MAX=5 自带计数上界因「round_wait 不消耗预算」而生,
        # retry 化后预算机制原生兜底(同分支每轮重命中 = 每轮耗 1 预算,
        # 耗尽 FAIL 交外层重新导航,有界终止单保持);分支动作本身不再判
        # 「未生效」(动作 op 禁验证,重入即基于新观察重判)。
        if self.round_by_ocr(screen, '补给阶段').is_success:
            return self._overlay_branch(
                '补给阶段',
                lambda: self._click_screen_area_center(
                    '货币战争-补给', '按钮-返回备战界面'))
        if self.round_by_ocr(screen, '遭遇其一').is_success:
            return self._overlay_branch(
                '遭遇其一',
                lambda: self._click_screen_area_center(
                    '货币战争-遭遇节点', '按钮-返回备战界面'))
        if self.round_by_ocr(screen, '盛会之星').is_success:
            return self._overlay_branch('盛会之星', self._click_exit_door)
        if self.round_by_ocr(screen, '可合成列表').is_success:
            return self._overlay_branch('可合成列表', self._click_blank_close)
        if self.round_by_ocr(screen, '角色详情').is_success:
            return self._overlay_branch('角色详情', self._click_blank_close)

        # r279(用户交办,分支③实证建档 2026-08-23):战斗中(不可识别
        # 画面)→ 右上角 X → 「货币战争-战斗暂停」(新档)→「撤退」→
        # 中断挑战弹窗(上方「放弃并结算」分支接管)。修战斗中 retry
        # 死循环(旧版全分支不命中)。
        if self.round_by_find_area(screen, '货币战争-战斗暂停',
                                   '标识-战斗暂停').is_success:
            # 锁光标恢复态加固:框架 round_by_find_and_click_area 用 area.pc_alt
            # (默认 False,operation.py 不透传 pc_alt),故命中后取 area 中心
            # 显式 pc_alt=True 点击(同本文件 _ocr_click_pc_alt 注释)。
            retreat_area = self.ctx.screen_loader.get_area(
                '货币战争-战斗暂停', '按钮-撤退')
            if retreat_area is not None:
                self.ctx.controller.click(retreat_area.center, pc_alt=True)
            log.info('[cw-exit] 战斗暂停→撤退 → 中断挑战弹窗')
            return self.round_wait(wait=2)
        # 战斗中(未暂停态):点右上角 X 弹暂停(实证 2026-08-23)
        # r302:controller.click 需 Point 对象(裸 int 坐标在
        # game2win_pos 坐标转换层炸 'int' has no .x——op 异常+
        # 采集钩子 skip 的共同根因)
        # 全分支 miss 计数上限(2026-09-03,第三局实录:退出途中落大世界
        # 角色详情页,「角色详情」OCR 漏读 → 尾部兜底点 X 坐标错位 →
        # round_wait 死循环 8min+(文件头 141x/444s 同款问题换分支复发)
        # ——全分支连续 miss 达限 = 帧已非 CW 域,fail 交外层重新导航,
        # 不再无限 round_wait。
        self._miss_rounds = getattr(self, '_miss_rounds', 0) + 1
        if self._miss_rounds >= 10:   # 本次退出尝试内累计 10 次全分支 miss(保守:含穿插命中,仍表明退出受阻)
            return self.round_fail('退出流程连续 10 轮全分支未命中(帧非 CW 域),交外层重新导航')
        # ⚠️ 待实机核(坐标单一源清点项):战斗中右上 X (1843,42) 为实测字面量
        # (实证 2026-08-23)未 area 化(本批实机纪律不可测,建档挂账实机批)。
        self.ctx.controller.click(Point(1843, 42), pc_alt=True)
        return self.round_wait(wait=1.5)

    def _click_screen_area_center(self, screen_name: str, area_name: str) -> bool:
        """取建档 area 中心并 pc_alt=True 点击;area 缺失返回 False(fail-closed)。

        不走框架 round_by_find_and_click_area:其点击不透传 pc_alt(本文件头
        锁光标恢复态注释),且此处分支判定已由 OCR/id_mark 完成,点击目标
        恒在,属「已知可点、直接点」形态。mouse_move 为 bug#1 缓解(同
        投资策略分支,点击前先移锚,否则首击被吃)。
        """
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        if area is None:
            log.error('[cw-exit] area 缺失:%s / %s', screen_name, area_name)
            return False
        self.ctx.controller.mouse_move(area.center)
        self.ctx.controller.click(area.center, pc_alt=True)
        return True

    def _click_exit_door(self) -> bool:
        """点备战左上门形「退出对局」图标 → 中断挑战弹窗。why 见备战分支注释。"""
        return self._click_screen_area_center('货币战争-备战', '按钮-退出对局')

    def _click_blank_close(self) -> bool:
        """点面板外空白(建档 区域-空白关闭)关闭选中驱动详情面板(浮窗/角色详情)。

        关闭机制依据:装备详情浮窗 2026-08-14 live 验「点画面空白处 → 关闭回
        备战」;area 中心 (960,530) = 前排 y467 底~后排 y600 顶之间的真空档
        (2026-08-14 实测修正,旧 700,400 前排有人时=前排-1 槽会误开角色详情)。
        与 CwScreenRoleDetailOverlay 同源同控件(原恢复原语 try_recovery
        已随验证拆除退役,同款空白关闭语义由本方法与环入口清场承载)。
        """
        return self._click_screen_area_center('货币战争-备战', '区域-空白关闭')

    def _overlay_branch(self, key: str, act: Callable[[], bool]) -> OperationRoundResult:
        """overlay 子态定向动作的统一出口:动作已发 → round_retry(计节点
        预算);area 缺失 → round_fail。

        K1 拆除(验证废除,用户裁定 2026-09-10:动作 op 禁「未生效」检出):
        原 OVERLAY_ACTION_MAX 连续计数上界删除——round_wait 改 round_retry 后,
        分支每轮重命中 = 每轮耗 1 次节点 retry 预算(exit_match 预算 30),
        耗尽框架原生 FAIL 交外层重新导航(有界终止单,不再依赖自带上界)。
        重试与否 = 每轮基于新观察的分支重判,非动作层验证重试。
        """
        if not act():
            return self.round_fail(f'{key} 关闭动作 area 缺失(ESC 已禁用),交外层重新导航')
        log.info('[cw-exit] overlay[%s] 建档点击已发(重入观察重判,计节点预算)', key)
        return self.round_retry(wait=2)

    def _ocr_click_pc_alt(self, screen, target_cn: str,
                          lcs_percent: float = 0.5) -> bool:
        """OCR 找到 target_cn 并以 pc_alt=True 点击其中心;找到且点中返回 True。

        框架 round_by_ocr_and_click 的点击是裸 controller.click(operation.py
        不透传 pc_alt),锁光标恢复态(机器重启后游戏直接恢复进 UI)下会全部
        落空(2026-09-02 一条龙恢复链事故,见文件头注释)。匹配逻辑与框架
        helper 同源:OCR map → difflib 最近匹配 → LCS 阈值 → 点 OCR 框中心;
        调用方保持既有 round 语义(命中即 round_wait 等画面推进,未命中落
        下一分支)。
        """
        ocr_result_map = self.ctx.ocr_service.get_ocr_result_map(image=screen)
        # OCR 服务偶发产出无文本词条,进 difflib 会 len(None) 崩(框架同款守卫)
        ocr_result_list = [k for k in ocr_result_map if k is not None]
        results = difflib.get_close_matches(
            gt(target_cn, 'game'), ocr_result_list, n=1)
        if not results:
            return False
        mrl = ocr_result_map.get(results[0])
        if mrl is None or mrl.max is None:
            return False
        if not str_utils.find_by_lcs(
                gt(target_cn, 'game'), results[0], percent=lcs_percent):
            return False
        return self.ctx.controller.click(mrl.max.center, pc_alt=True)
