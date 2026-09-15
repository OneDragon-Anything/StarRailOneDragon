"""出战动作 op(StartBattleOp)——出战域重设计(用户裁定,T-286):出战
op 只管「点击出战和弹窗」,零策略语义、零转移验证——流程卡死监控归外部
哨兵(runtime-ops 哨兵栈现役),op 内不建。

执行序(单一语义;备战环 / 达标臂发射核 ``launch_prepared_battle`` /
恢复局锁定直出战三路径经同一注册表分派到达本 op,禁各写一套点击段):
  1. 找按钮「按钮-出战」(备战 + 开商店两屏查;叠加帧现状逻辑)——
     免战子态 fallback 查「按钮-跳过」(同语义点它);
  2. mouse_move + click(基本单击);
  3. sleep 1.0(弹窗渲染窗);
  4. 截图一次:「货币战争-未达上限警告」→ 点「勾选-本局不再提示」
     (幂等,已勾无害)→ 点「按钮-确认」;「货币战争-提示-前台无角色」
     → 点「按钮-确认」;都没有 → 完成。点出战后的真弹窗全清单已排查,
     仅此两类(免战牌「跳过(N/N)」是按钮换形态非弹窗,属步 1);
  5. 完成 = 上报动作事实(env.detail + env.skip_substate)→ 返回交回
     (备战画面 op 正常终结,terminal/terminal_wait 语义不变)。

**基类契约在册例外**(例外登记口落款):``execute`` 返回值 = **点击序列
已执行**(找不到按钮 / area 缺失 = False),消费面 = runner 包络
``last_launch_ok`` 旁路(prep_actions 执行器单一写点)。旧发射家族
(6×0.5s 转移轮询 / 备战标识消失验证 / POST_LAUNCH_BLOCKERS 拦截弹窗
守卫 / 重发长按下 / 失焦守卫 / launch_dead 连败停机)随出战域重设计
整删:op 不判效,交回后画面状态由外循环下一帧重判(「货币战争-未达上限
警告」「货币战争-提示-前台无角色」画面分支现役,未知帧由未知兜底接)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import (
        PrepExecEnv,
    )


class StartBattleOp(ActionOp):
    """出战点击(点击出战/跳过 → 弹窗确认 → 上报交回;语义见模块头)。

    终结动作:发出即本备战访问终结(交回外循环战斗分支);终结等待 =
    ``terminal_wait``(消费点经注册表读类属性)。
    """

    terminal = True

    #: 终结交回等待秒数(备战画面 op 交回节奏,现状等价锁 =
    #: test_cw_unified_action_3 终结集锁)。
    terminal_wait = 3

    #: 出战点击后的弹窗渲染等待(步 3)。单帧截图判定,不轮询(op 零判效):
    #: 弹窗未就位的帧由外循环下一帧画面分支接住(画面档现役)。
    POST_CLICK_WAIT_S: float = 1.0

    def execute(self, env: PrepExecEnv) -> bool:
        """出战点击序列(返回值契约 = 点击序列已执行,见模块头在册例外)。

        免战子态(2026-08-17 M72 实锤建档):「免战牌」策略激活时出战按钮变
        「跳过(N/N)」(直跳战斗,免战 2 次)——查不到「出战」时查子态
        「按钮-跳过」,同语义点它(推进节点)。跳过子态标记经
        ``env.skip_substate`` 上报;免战次数递减归 game state 上报路径
        (apply_op_effect,op 零 game state 直写),递减语义 = 上报时
        (非「验证落地后」——op 已零验证)。

        ⚠️ 正交态查找(子态建模四问③,skill feedback 案例库):免战与
        「商店开」**可叠加**(跳过按钮 + 牌区展开同帧)——叠加帧识别为
        货币战争-备战-开商店(它盖基态 id_mark),按单一屏查「按钮-跳过」
        会落空。跳过/出战按钮在两屏同一位置 → 查找不锁死单一屏(备战 +
        开商店都查);按钮 area 单源归备战屏,不复制双源。

        找不到按钮 = 动作未执行(上报「未执行:找不到按钮」)→ 交回外循环
        重判(不炸;画面真未知由未知兜底链接)。
        """
        ex = env.executor
        screen = ex._op.screenshot()
        btn_screens: list[str] = [SCREEN_NAME, '货币战争-备战-开商店']
        btn_area = '按钮-出战'
        btn_found = any(
            ex._op.round_by_find_area(screen, _sc, btn_area).is_success
            for _sc in btn_screens)
        if not btn_found:
            if any(ex._op.round_by_find_area(screen, _sc, '按钮-跳过',
                                             crop_first=False).is_success
                   for _sc in btn_screens):
                btn_area = '按钮-跳过'
                log.info('[cw][battle] 出战按钮为子态「跳过」(免战牌激活)→ 点跳过')
            else:
                env.detail = '未执行:找不到按钮'
                env.emitted = False
                log.warning('[cw!][battle] %s(备战+开商店两屏查空)'
                            '→ 交回外循环重判', env.detail)
                return False
        btn = area_center(ex._ctx, btn_area)
        if btn is None:
            # area 缺失 = 建档漂移,显式失败禁兜底坐标(坐标单一真相源)。
            env.detail = f'area 缺失:{btn_area}({SCREEN_NAME}),禁兜底坐标'
            env.emitted = False
            log.warning('[cw!][battle] %s', env.detail)
            return False
        env.skip_substate = btn_area == '按钮-跳过'
        ex._ctx.controller.mouse_move(btn)
        ex._ctx.controller.click(btn)
        time.sleep(self.POST_CLICK_WAIT_S)
        env.detail = self._settle_post_click_popup(ex)
        env.emitted = not env.detail.startswith('area 缺失')
        if not env.emitted:
            log.warning('[cw!][battle] %s', env.detail)
            return False
        log.info('[cw][battle] %s%s → 交回外循环', env.detail,
                 '(跳过子态)' if env.skip_substate else '')
        return True

    def _settle_post_click_popup(self, ex) -> str:
        """出战点击后的弹窗收口(步 4,单帧截图判定):两类真弹窗点确认,
        都没有 = 完成。返回机械摘要(detail;「area 缺失」前缀 = 弹窗
        确认点击未执行,调用方按序列未完成上报)。

        勾选幂等依据 = M16 死循环根因修复(ADR-0136)同款行为:只点确认
        不勾「本局不再提示」→ 人口不足时每次出战都弹此窗;对齐
        CwScreenDeployNotFull 完整行为(勾选 → 确认)。
        """
        scr = ex._op.screenshot()
        if ex._op.round_by_find_area(scr, '货币战争-未达上限警告',
                                     '标识-未达上限警告').is_success:
            check = area_center(ex._ctx, '勾选-本局不再提示',
                                '货币战争-未达上限警告')
            if check is None:
                return ('area 缺失:勾选-本局不再提示'
                        '(货币战争-未达上限警告),禁兜底坐标')
            ex._ctx.controller.mouse_move(check)
            ex._ctx.controller.click(check)
            time.sleep(0.3)
            confirm = area_center(ex._ctx, '按钮-确认', '货币战争-未达上限警告')
            if confirm is None:
                return ('area 缺失:按钮-确认'
                        '(货币战争-未达上限警告),禁兜底坐标')
            ex._ctx.controller.mouse_move(confirm)
            ex._ctx.controller.click(confirm)
            return '出战已点击(未达上限警告:勾选+确认)'
        if ex._op.round_by_find_area(scr, '货币战争-提示-前台无角色',
                                     '标识-无角色提示').is_success:
            confirm = area_center(ex._ctx, '按钮-确认',
                                  '货币战争-提示-前台无角色')
            if confirm is None:
                return ('area 缺失:按钮-确认'
                        '(货币战争-提示-前台无角色),禁兜底坐标')
            ex._ctx.controller.mouse_move(confirm)
            ex._ctx.controller.click(confirm)
            return '出战已点击(前台无角色提示:确认)'
        return '出战已点击(无弹窗)'
