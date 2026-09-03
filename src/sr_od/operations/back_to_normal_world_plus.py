import time

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_screen_state
from sr_od.application.currency_war.operations.cw_entry.cw_entry_exit import (
    CwEntryExit,
)
from sr_od.application.currency_war.operations.cw_entry.cw_entry_start import (
    try_handle_train_supply_popup,
)
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.application.sim_universe.operations.bless.sim_uni_choose_bless import (
    SimUniChooseBless,
)
from sr_od.application.sim_universe.operations.bless.sim_uni_drop_bless import (
    SimUniDropBless,
)
from sr_od.application.sim_universe.operations.curio.sim_uni_choose_curio import (
    SimUniChooseCurio,
    SimUniDropCurio,
)
from sr_od.application.sim_universe.operations.sim_uni_event import SimUniEvent
from sr_od.application.sim_universe.operations.sim_uni_exit import SimUniExit
from sr_od.context.sr_context import SrContext
from sr_od.operations.interact.talk_interact import TalkInteract
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state

# NPC 对话态脱困用的「告别」类选项词表(LCS 高阈值匹配,防同屏其他选项误配)。
# 词表是设计先行的保守集:2026-08-26 事故现场选项为「告别」(用户口述);
# 后续按 od-dev-screen-onboarding 用守卫采集的截图样本核对/扩充,再考虑建 screen_info 档。
NPC_DIALOG_FAREWELL_WORDS: list[str] = ['告别', '离开', '再见']
NPC_DIALOG_FAREWELL_LCS: float = 0.7


class BackToNormalWorldPlus(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        返回普通大世界 增强版
        需要在任何情况下使用都能顺利地返回手机菜单 用于应用结束后 确保不会卡死下一个应用
        已考虑场景如下
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('返回普通大世界'))

    @operation_node(name='画面识别', node_max_retry_times=20, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 覆盖层/面板类分支必须在全屏分支之前:半屏面板(如本面板)旁边露出
        # 大世界背景时,「角色图标」等全屏特征会误命中导致误报 SUCCESS。
        # 模拟宇宙/差分宇宙的「退出确认」面板(2026-08-31 实证):上一 app 在
        # 模拟宇宙楼层内异常退出时,本 op 起手点「右上角返回」→ 弹出本面板 →
        # 角色图标分支误报成功 → app 带着面板继续乱点,循环 40 分钟。
        # 面板 area 早已建档(sim_uni.yml 菜单-暂离/结束并结算),纯分发表缺条目。
        # 点「暂离」:保进度退出(下次模拟宇宙 app 从进度续跑,同 2026-08-30 续跑判例)。
        # round_retry 同判例(点击可能不落地,逐帧重识别)。
        result = self.round_by_find_area(screen, '模拟宇宙', '菜单-暂离')
        if result.is_success:
            self.round_by_find_and_click_area(screen, '模拟宇宙', '菜单-暂离')
            return self.round_retry('模拟宇宙-退出确认面板', wait=2)

        # 先看看左上角是否退出按钮
        result = self.round_by_find_area(screen, '模拟宇宙', '大世界返回按钮')
        if result.is_success:
            # 判断是否在模拟宇宙内
            sim_uni_level_type = sim_uni_screen_state.get_level_type(self.ctx, screen)
            if sim_uni_level_type is not None:
                return self.sim_uni_exit(False)

            # 如果有返回按钮 又不是在模拟宇宙 则就是在逐光捡金内
            result = self.round_by_find_and_click_area(screen, '模拟宇宙', '大世界返回按钮')
            if result.is_success:
                return self.round_wait(wait=1)

            # 都不在的话 暂时不支持返回大世界
            return self.round_fail('未支持的副本画面')

        # 在可以移动的画面 - 普通大世界
        result = self.round_by_find_area(screen, '大世界', '角色图标')
        if result.is_success:  # 右上角有角色图标
            # 检测弹窗 "点击空白处关闭" 弹窗不会遮挡角色图标 需要先关闭
            result = self.round_by_find_and_click_area(screen, '大世界', '点击空白处关闭')
            if result.is_success:
                return self.round_wait(wait=1)
            return self.round_success()

        # 手机菜单
        result = self.round_by_find_area(screen, '菜单', '开拓等级')
        if result.is_success:
            self.round_by_click_area('菜单', '右上角返回')
            return self.round_wait(wait=1)

        # 模拟宇宙内的画面
        sim_uni_state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            event=True,
            bless=True,
            drop_bless=True,
            curio=True,
            drop_curio=True
        )
        if sim_uni_state is not None:
            # region 差分宇宙4.0
            if sim_uni_state == sim_uni_screen_state.ScreenState.SELECT_STATION.value:  # 选择站点卡
                self.ctx.controller.click(Point(160, 343))  # 第一个
                time.sleep(0.2)
                self.ctx.controller.click(Point(1626, 939))  # 确认
                return self.round_wait(sim_uni_state, wait=2)
            if sim_uni_state == sim_uni_screen_state.ScreenState.SELECT_NEXT_STATION.value:  # 选择下一站
                self.ctx.controller.click(Point(867, 589))  # 中间偏左
                time.sleep(0.1)
                self.ctx.controller.click(Point(701, 589))  # 第一个
                time.sleep(0.1)
                self.ctx.controller.click(Point(1152, 969))  # 确认
                return self.round_wait(sim_uni_state, wait=3)
            if sim_uni_state == sim_uni_screen_state.ScreenState.CHOOSE_WILL_POWER.value:  # 选择奇迹
                self.ctx.controller.click(Point(867, 589))  # 中间偏左
                time.sleep(0.1)
                self.ctx.controller.click(Point(475, 483))  # 第一个
                time.sleep(0.1)
                self.ctx.controller.click(Point(953, 969))  # 确认
                return self.round_wait(sim_uni_state, wait=1)
            if sim_uni_state == sim_uni_screen_state.ScreenState.AHA_MASK.value:  # 选择面具
                self.ctx.controller.click(Point(314, 914))  # 第一个
                time.sleep(1)
                self.ctx.controller.click(Point(1576, 982))  # 确认
                return self.round_wait(sim_uni_state, wait=1)
            # endregion

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_BLESS.value:
                return self.sim_uni_choose_bless()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_BLESS.value:
                return self.sim_uni_drop_bless()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_CURIOS.value:
                return self.sim_uni_choose_curio()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value:
                return self.sim_uni_drop_curio()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_EVENT.value:
                return self.sim_uni_event()

        # 对话框 - 逐光捡金 退出确认
        result = self.round_by_find_and_click_area(screen, '逐光捡金', '退出对话框确认')
        if result.is_success:
            return self.round_wait(wait=5)

        # 列车补给 - 点击空白处继续
        if common_screen_state.is_express_supply(self.ctx, screen):
            common_screen_state.claim_express_supply(self.ctx)
            return self.round_wait(wait=2)

        # 战斗中 点击右上角后出现的画面 需要需要退出
        battle_exit_area_list = [
            ('模拟宇宙', '终止战斗并结算'),  # 模拟宇宙
        ]
        for area in battle_exit_area_list:
            result = self.round_by_find_and_click_area(screen, area[0], area[1])
            if result.is_success:
                return self.round_wait(result.status, wait=1)

        # 战斗结束后 出现的退出关卡
        result = self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮')
        if result.is_success:
            return self.round_wait(result.status, wait=2)

        # 大世界-战斗失败(2026-08-30 实证):app 异常退出遗留的战败结算屏。
        # 该屏无右上角返回按钮,唯一交互是「点击空白区域继续」→ 回各副本的
        # 战前画面(副本入口/模式首页),由本链既有分支或右上角返回兜底继续。
        # 此前兜底只会反复点右上角死循环至 FAIL,卡死下一个应用的起手
        # (现场:.log/mcp_server.log 当日 00:31 段,开拓力 FAIL 遗留战败屏)。
        # 与上述大厅分支同构:id_mark 正面识别(normal_world_battle_fail.yml)
        # → area 点击 + round_retry 逐帧重识别(点击可能不落地,同判例拒 WAIT 永动)。
        result = self.round_by_find_area(screen, '大世界-战斗失败', '标题-战斗失败')
        if result.is_success:
            self.round_by_find_and_click_area(screen, '大世界-战斗失败', '点击空白区域继续')
            return self.round_retry('大世界-战斗失败', wait=2)

        # 货币战争-大厅(2026-08-27 run 46 事故根修):全屏 UI 叠在大世界场景上,
        # 前序分支全不命中,守卫的 INTERACT_RECT 恰罩住大厅右面板静态文字(数据银行/
        # 预期收益等)→ 曾被误判为对话态死循环。id_mark 精确命中即正面识别本画面 →
        # 点右上角关闭 X 返回大世界。
        # 本分支同时覆盖「上局结束回大厅」的残留态:残留态与开局前大厅共用同一
        # screen_info 档,其开始按钮不响应任何点击(app 重试与手动双击均无效),
        # 右上角关闭 X 才是真退出——关 X 露出世界场景后由「角色图标」分支 SUCCESS。
        # 实证与真帧锁见 docs/game/screens/currency_war_lobby.md「残留态」备注与
        # 测试仓 test_back_to_normal_world_plus 的 CW 大厅残留态真帧测试。
        # 实证退出链(2026-08-27 实机):大厅 → 点关闭 X →「大世界-普通」(多数路径
        # 一步直达);实机验证亦见中间态:误触 X 邻点(裸坐标 1857,63,与攻略
        # 入口热区相邻)会打开「角色攻略详情」页,点该页右上同款 X 才回大世界——
        # 故本分支必须走模板 area 点击(拒绝裸坐标)且用逐帧重识别的 retry 结构,
        # 多跳中间态天然容忍(每轮重新识别当前画面)。
        # 项目规则:操作禁用 ESC,返回/关闭一律点坐标(本分支走 screen_info area)。
        # 用 round_retry 而非 round_wait:点击可能不落地,WAIT 不消耗 retry 会死循环
        # (同本节点兜底分支既有判例);点掉后面下一轮命中「角色图标」分支 SUCCESS。
        result = self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南')
        if result.is_success:
            # 锁光标恢复态加固:机器重启后游戏直接恢复进本 UI 时光标处于锁定态,
            # 不带 Alt 的点击全部落空(2026-09-02 一条龙恢复链事故实证:id_mark 命中
            # 正常、点「按钮-关闭」不带 Alt → round_retry×20 有界 FAIL,6 应用速挂;
            # 人工带 Alt 点一次即关闭)。框架 round_by_find_and_click_area 用
            # area.pc_alt(yml 未设即 False,且 MCP 无法设 area 级 pc_alt),故命中后
            # 取 area 中心显式 pc_alt=True 点击;自由光标下 Alt+点击无害
            # (check_npc_dialog 点对话选项同款先例)。命中判据与 round_retry
            # 逐帧重识别结构不变。
            close_area = self.ctx.screen_loader.get_area('货币战争-大厅', '按钮-关闭')
            if close_area is not None:
                self.ctx.controller.click(close_area.center, pc_alt=True)
            return self.round_retry('货币战争-大厅', wait=2)

        # 货币战争-对局中画面(2026-09-01 孤儿对局事故根修):孤儿对局 = 上一
        # CW app 被 stop 后残留的对局画面(如备战),一条龙各应用开场的本 op
        # 既有分支全不认识它 → 落兜底点「菜单-右上角返回」(CW 画面无此控件,
        # 点击不改变画面)→ round_retry×20 有界 FAIL,9 个应用全部速挂。
        # 用户裁定修法:识别到货币战争对局画面,都走货币战争的退出 op
        # (CwEntryExit:放弃+结算 3 页回大厅,支持备战/战斗中/
        # 事件 overlay/结算全入口)。判定单一源 = cw_screen_state.in_match_screen_names,
        # 与 CurrencyWarApp._in_match 第①层(screen_info 画面匹配)同源,
        # 新对局画面建档即自动生效。成功出口=大厅,大厅 → 大世界由上方
        # 「货币战争-大厅」分支(点右上角关闭 X)接管——链路天然衔接,
        # 下一轮逐帧重识别命中大厅分支。
        cw_match_screen = cw_screen_state.get_in_match_screen_name(self.ctx, screen)
        if cw_match_screen is not None:
            log.info('[返回普通大世界] 命中货币战争对局画面 %s → 委托退出对局 op', cw_match_screen)
            return self.cw_exit()

        # 列车补给每日弹窗(盖在大厅/大世界之上,无 X 关闭钮,点中央徽章领取):
        # 被白名单排除在 cw_screen_state 对局中判定之外,须在此单独接——
        # 不接住则退大厅/大世界后弹窗仍盖着,其余分支全不命中落兜底死循环。
        # 复用 CW 入口链共享助手(单一源:app/enter/start与本链同一实现)。
        popup_result = try_handle_train_supply_popup(self, screen)
        if popup_result is not None:
            return popup_result

        # 无名勋礼购买推广页 / 等级加速弹窗 / 主面板(2026-08-27):
        # 版本更新(2026-08-26 周期)后周期内第一次进无名勋礼,先落在整屏「购买推广页」
        # (用户口述裁决:点「开启无名勋礼」是查看/继续语义,**不会付费**)。实证退出链
        # (2026-08-27 实机四步全走通):
        #   推广页 → 点「开启无名勋礼」→「无名勋礼等级加速」说明弹窗(点弹窗内
        #   「点击空白处关闭」提示位关闭;点弹窗外无效)→ 无名勋礼主面板 → 点右上角
        #   「按钮-关闭」→ 菜单页(既有「菜单」分支接管:开拓等级→右上角返回→大世界)。
        # 与上方货币战争-大厅分支同构:id_mark 精确命中即正面识别 → area 点击 + round_retry
        # 逐帧重识别(点击可能不落地,WAIT 不消耗 retry 会死循环);中间态(弹窗/主面板)
        # 靠逐帧重识别天然容忍,无需跨轮状态。项目规则:操作禁用 ESC,关闭一律点
        # screen_info area。
        result = self.round_by_find_area(screen, '无名勋礼-购买推广页', '按钮-开启无名勋礼')
        if result.is_success:
            self.round_by_find_and_click_area(screen, '无名勋礼-购买推广页', '按钮-开启无名勋礼')
            return self.round_retry('无名勋礼-购买推广页', wait=2)

        result = self.round_by_find_area(screen, '无名勋礼-等级加速弹窗', '标识-等级加速')
        if result.is_success:
            self.round_by_find_and_click_area(screen, '无名勋礼-等级加速弹窗', '按钮-点击空白处关闭')
            return self.round_retry('无名勋礼-等级加速弹窗', wait=2)

        result = self.round_by_find_area(screen, '无名勋礼', '标识-无名勋礼')
        if result.is_success:
            self.round_by_find_and_click_area(screen, '无名勋礼', '按钮-关闭')
            return self.round_retry('无名勋礼', wait=2)

        # 版本公告轮播(「贪饕」侵蚀,2026-08-26 版本):游戏级版本公告弹窗,
        # 待机自动弹出、盖在任意画面上(非任何 app 触发)。实证结构(2026-08-27
        # 实机走通 + fixture 已存):两页轮播,第 1 页无任何出口(只有
        # 右箭头翻页);第 2 页底部中央出「关闭」钮 → 点关闭露出底下原画面。
        # 实锤后果:无此分支时 CW 独立 app 首跑 52s 失败(兜底空转耗尽)。
        # 与上述大厅/无名勋礼分支同构:标题 id_mark(两页共享)正面识别本屏 → 子态区分 =
        # 「按钮-关闭」可见与否(第 2 页独有):可见点关闭,否则点右箭头翻页 →
        # round_retry 逐帧重识别(点击可能不落地,RETRY 计入 node_max_retry_times
        # 有界 FAIL,拒 WAIT 永动;多跳中间态靠逐帧重识别天然容忍)。项目规则:
        # 零 ESC 键输入,关闭一律 screen_info area 点击。
        if self.round_by_find_area(screen, '版本公告轮播', '标识-贪饕侵蚀').is_success:
            if self.round_by_find_area(screen, '版本公告轮播', '按钮-关闭').is_success:
                self.round_by_find_and_click_area(screen, '版本公告轮播', '按钮-关闭')
            else:
                # 右箭头为纯图形无文字,area 只建 pc_rect(no_method 定位区),
                # round_by_click_area 直接点 area 中心,不做识别。
                self.round_by_click_area('版本公告轮播', '按钮-下一页')
            return self.round_retry('版本公告轮播', wait=1)

        # 对话态守卫(2026-08-26 实机事故根修,NPC 对话态下兜底点击会命中对话隐藏按钮):
        # 登录落点等活动摊位 NPC 对话态时,右上角图标全被对话 UI 遮蔽,前面所有分支
        # 都不命中,原兜底直接点「菜单-右上角返回」——该坐标与对话的隐藏按钮重叠,
        # 一点就把对话 UI 收掉 → 裸场景假象 + 键盘输入被吞 → 后续判断全乱。
        # 守卫在兜底之前先检测对话态并走脱困序,检测不命中才落回原兜底。
        dialog_result = self.check_npc_dialog(screen)
        if dialog_result is not None:
            return dialog_result

        # 其他情况 - 均点击右上角触发返回上一级
        # 锁光标恢复态加固(同上方「货币战争-大厅」分支,2026-09-02 事故实证):
        # 兜底是任何未知态的最后出口,必须按最坏光标态点——机器重启恢复进未知 UI
        # 时光标可能锁定,不带 Alt 的点击全部落空;自由光标下 Alt+点击无害。框架
        # round_by_click_area 用 area.pc_alt(默认 False),故取 area 中心显式
        # pc_alt=True 点击;round_retry 有界语义不变(点击可能不落地,逐帧重识别)。
        fallback_area = self.ctx.screen_loader.get_area('菜单', '右上角返回')
        if fallback_area is not None:
            self.ctx.controller.click(fallback_area.center, pc_alt=True)
        # 兜底分支必须用 round_retry（计入 node_max_retry_times）而非 round_wait：
        # 框架中 WAIT 不消耗 retry（operation.py 循环里 WAIT 直接 continue、且任何非 RETRY
        # 结果会把 node_retry_times 清零），兜底点击无法改变画面时会无限循环
        # （2026-08-24 实跑：战斗结算画面点右上角无效，兜底卡约 2 小时拖垮整条龙）。
        # 正常「连续退多级菜单」不受影响：每退一级后画面变化、check_screen 命中其他
        # 分支返回 WAIT/SUCCESS，node_retry_times 被清零，不会累计到 20 次上限。
        return self.round_retry('右上角返回', wait=1)

    def check_npc_dialog(self, screen: MatLike) -> OperationRoundResult | None:
        """
        对话态守卫：检测当前是否处于 NPC 对话态，是则走脱困序（推进/告别），否则返回 None 落回兜底。

        检测与动作坐标全部复用 TalkInteract 的既有已验证常量（交谈交互区 + 空白推进点击点），
        不引入未验证的新坐标。脱困序为逐帧反应式（本方法每轮重跑，无跨轮状态）：

        1. 告别类选项可见（高阈值 LCS）→ 点它退出对话（对完后续帧由「角色图标」分支接管）；
        2. 交互区无告别词 → 返回 None 落回原兜底。

        状态门加严(2026-08-27):「交互区有字」是弱证据不再单独构成对话态——
        该区域是普通画面右侧面板文字的常落区,曾把货币战争-大厅静态面板文字误判成
        「未知对话选项」→ 点空白推进(选项态下推进无效)→ round_retry 永动(run 46
        卡 8+ 分钟实证实录)。真对话态下告别词未收录时落到兜底也只是有界失败,
        不会再提供无推进的重试风暴;词表扩充走守卫采集钩子的样本核对。

        :param screen: 游戏画面
        :return: 命中告别选项时返回对应的 round 结果；否则 None
        """
        part = cv2_utils.crop_image_only(screen, TalkInteract.INTERACT_RECT)

        farewell_map = self.ctx.ocr.match_words(
            part, words=NPC_DIALOG_FAREWELL_WORDS, lcs_percent=NPC_DIALOG_FAREWELL_LCS,
        )
        if len(farewell_map) > 0:
            # 采集钩子(临时,对话态建档后整段删除):守卫首次实证命中时留截图样本,
            # 供 od-dev-screen-onboarding 离线核对选项词表/坐标。
            self.save_screenshot(prefix='npc_dialog_guard')
            log.info('[对话态守卫] 命中告别类选项 %s,点击退出对话', list(farewell_map.keys()))
            for r in farewell_map.values():
                to_click: Point = r.max.center + TalkInteract.INTERACT_RECT.left_top
                # 与 TalkInteract 同款:先移上去停留再点,提高选项选中稳定性
                self.ctx.controller.mouse_move(to_click)
                time.sleep(0.1)
                if self.ctx.controller.click(press_time=0.1, pc_alt=True):
                    return self.round_wait('对话态-告别', wait=1)

        # 无告别词:交互区文字不构成对话态证据(run 46 大厅误判根因),返回 None 落回原兜底。
        return None

    def cw_exit(self) -> OperationRoundResult:
        """委托货币战争退出对局 op(仿 sim_uni_exit 既有范式)。

        成功=已回货币战争大厅(该 op 的唯一成功出口)→ round_wait 让下一轮
        逐帧重识别,由「货币战争-大厅」分支点右上角关闭 X 接管;失败(如
        对局画面不识别)→ round_retry 保留在分支内重试(计入节点 retry 预算,
        有界 FAIL 不永动)。
        """
        op = CwEntryExit(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_exit(self, is_in_x: bool) -> OperationRoundResult:
        op = SimUniExit(self.ctx, is_in_x, temporarily_leave=True)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_event(self) -> OperationRoundResult:
        op = SimUniEvent(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_bless(self) -> OperationRoundResult:
        op = SimUniChooseBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_bless(self) -> OperationRoundResult:
        op = SimUniDropBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_curio(self) -> OperationRoundResult:
        op = SimUniChooseCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_curio(self) -> OperationRoundResult:
        op = SimUniDropCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_ocr()
    ctx.init_by_config()

    ctx.start_running()
    op = BackToNormalWorldPlus(ctx)
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()
