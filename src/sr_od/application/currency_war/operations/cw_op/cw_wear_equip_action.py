"""穿装备动作 op(WearEquipOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._wear_equip`` 逐字迁移,原方法
改薄委托保持替身缝,design.md unified-action-factory §2.4)。

WearEquip 原子通路机械半(R2)。非终结。

穿戴落地像素验证(T-55;点击≠成了家族,DeployMoveOp T-22 / BuyCardOp
T-44 同族补齐):拖拽存在静默不生效形态,实机 run_20260918_075416 实证
——投影写 ``owned[分身墨镜Max] -1(穿戴)``,下一帧实读该件仍在 owned
库 → equips 失配安灯停局。本 op 拖后对 owned 网格源件格做像素差判定,
零变化(经 settle 重采仍零)= 未生效 → 置申报闩(载体 =
``strategy_state.cw4_counters``,键 ``wear_miss_skip_pending``)+ ``env.
emitted = False``:两投影腿双双跳写——容器 logic 腿(apply_op_effect 的
owned −1 / tracked +1)经执行器既有 emitted 门跳写,黑板腿
(``_project_prep_obs`` 的 owned_equips 摘件)经闩消费口
:func:`wear_miss_consume` 跳写,失真值从未写下。连续 miss 由闩消费口
计数(同键累加/异键归 1/无闩归零),触顶 :data:`WEAR_MISS_REDISPATCH_
LIMIT` 由决策循环(:func:`wear_miss_brake_status`)round_fail 显式停交
上层。缺证不可判(缺帧/形状不一致/矩形越界)与载体缺席(无局/第三方
策略面)均保守放行走既有发出即写语义——验证只采集申报事实,不做重试
治理(B1 拆除裁定「落地判定归观察侧」的观察侧即本申报闩的消费链)。
"""
from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Any

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import WearEquip
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    import numpy as np

    from sr_od.application.currency_war.prep_actions import PrepExecEnv

#: 落地像素验证阈值(owned 源件格均值绝对差;与 BuyCardOp.
#: BUY_LAND_DIFF_THRESHOLD / DeployMoveOp.DEPLOY_LAND_DIFF_THRESHOLD
#: 同量级同取向——未生效时画面静止 diff≈0,生效时 icon 消失/网格
#: reflow diff 远超阈值)。阈值偏低取向:误判「生效→未生效」= 投影
#: 跳写一拍,下一帧 heavy 实读吸收 + 策略重派重穿自愈;误判反向则退回
#: 投影失真安灯停局形态,宁可漏报不可错报。
WEAR_LAND_DIFF_THRESHOLD: float = 2.0

#: 首采无变化后的动画收敛重采延迟(拖拽回弹/装备飞行动画时长量级;
#: T-44 buy 同款 settle 处理,时序误报先例 run_20260830_071711)。
WEAR_LAND_SETTLE_RETRY_DELAY_S: float = 0.8

#: 穿戴 miss 刹车上限(对局级;取值依据同族 = T-44 BUY_MISS_REDISPATCH_
#: LIMIT / kernel DEPLOY_MISS_REDISPATCH_LIMIT 的「连续同因重试预算」:
#: 像素验证假阳是单帧噪声,单次假阳后必有成功穿戴把计数归零,永不满;
#: 连续 3 次同键 miss = 同一穿戴被系统性吞的形态(输入丢失/模板漂移),
#: 重试预算应停交上层,防「黑板仍见该件 → 策略重发 → miss」无界循环)。
WEAR_MISS_REDISPATCH_LIMIT: int = 3

#: miss 连续计数与申报闩的载体键(cw4_counters;执行控制键非纯观测:
#: 参与熔断谓词。先例 = buy_miss_streak_* 同载体同形态)。``wear_miss_
#: streak_n`` = 同键连续 miss 次数;``wear_miss_streak_key`` = 当前情节
#: 键(异键归 1 重计的键比对面);``wear_miss_skip_pending`` = 申报闩
#(单动作窗,读即清)。
CW4_KEY_WEAR_MISS_STREAK_N = 'wear_miss_streak_n'
CW4_KEY_WEAR_MISS_STREAK_KEY = 'wear_miss_streak_key'
CW4_KEY_WEAR_MISS_PENDING = 'wear_miss_skip_pending'


def wear_owned_cell_changed(pre: np.ndarray | None,
                            post: np.ndarray | None,
                            rect: Rect) -> bool | None:
    """owned 网格源件格像素变化判定(穿戴落地的可见性证据;纯函数)。

    :param pre: 拖前基线帧;:param post: 拖后帧;:param rect: 源件格
        矩形(x1/y1/x2/y2,1080p 游戏坐标)。
    :return: True = 可见变化(判落地);False = 像素零变化(判未生效);
        None = 不可判(缺帧/两帧形状不一致/矩形越界)→ 调用方按生效走
        既有行为——验证只在两帧齐备时发声,缺证不改变既有语义
        (对齐 buy_slot_region_changed / deploy _region_changed_px
        保守放行取向)。
    """
    try:
        import numpy as np
        if pre is None or post is None:
            return None
        if pre.shape[:2] != post.shape[:2]:
            return None
        x1 = max(0, int(rect.x1))
        x2 = min(int(pre.shape[1]), int(rect.x2))
        y1 = max(0, int(rect.y1))
        y2 = min(int(pre.shape[0]), int(rect.y2))
        if x2 <= x1 or y2 <= y1:
            return None
        diff = float(np.abs(pre[y1:y2, x1:x2].astype('int16')
                            - post[y1:y2, x1:x2].astype('int16')).mean())
        return diff >= WEAR_LAND_DIFF_THRESHOLD
    except Exception:   # noqa: BLE001  验证失败不改变穿戴语义(保守放行)
        return None


def wear_miss_key_of(action: WearEquip) -> str:
    """miss 情节键(同键累加/异键归 1 的键比对面)= 件名+目标排槽。

    重派重算的同一穿戴 = 同键(投影跳写后逻辑态不变,策略对同一
    owned 件重发同动作);计划更换(换了件或目标)= 异键新情节,
    从 1 起算不继承旧计数。
    """
    return f'{action.item_name}@{action.row}-{action.slot}'


def _wear_miss_counters(session: Any) -> dict | None:
    """miss 计数载体访问(防御形态;缺席 = None 无计数面,与
    _buy_miss_counters 缺席退缺省口径同)。"""
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    _st = strategy_state_of(session) if session is not None else None
    _ct = getattr(_st, 'cw4_counters', None)
    return _ct if isinstance(_ct, dict) else None


def wear_miss_pending_clear(session: Any) -> None:
    """旧闩清位(置位端 execute 入口;任何路径的穿戴动作都不消费上一
    动作的申报,闩 = 单动作窗;陈旧闩另由消费端动作匹配校验双保险兜住)。
    载体缺席 = 零动作。"""
    _ct = _wear_miss_counters(session)
    if _ct is None:
        return
    _ct.pop(CW4_KEY_WEAR_MISS_PENDING, None)


def wear_miss_pending_set(session: Any, key: str) -> None:
    """置申报闩(单动作窗;置位端 = WearEquipOp 像素验证 miss 臂)。
    载体缺席 = 零动作(缺省口径)。"""
    _ct = _wear_miss_counters(session)
    if _ct is None:
        return
    _ct[CW4_KEY_WEAR_MISS_PENDING] = key


def wear_miss_consume(session: Any, action: WearEquip) -> bool:
    """穿戴 miss 申报闩消费(投影写端唯一合法消费口;消费点 =
    ``cw_screen_prep._project_prep_obs`` WearEquip 分支,黑板投影之前;
    容器 logic 腿不经过本口——由执行器 emitted 门先行跳写)。

    语义对齐 kernel ``consume_deploy_miss_mark``,载体 = cw4_counters:

    - 载体缺席 / 闩不在 = False(照常投影)+ 计数归零(同键情节有了结,
      单次假阳永不假满);
    - 陈旧闩(闩键与本次动作不匹配)= False(不吞新动作投影,读即清)
      + 计数归零(情节已换,异键 miss 由下次消费从 1 起算);
    - 命中 = 同键计数 +1(同键累加/异键归 1)+ ``wear_miss_skip`` 台账
      行留证(防静默;豁免 ≠ 消失同纪律)+ True(调用方跳写)。

    触顶停交上层由决策循环经 :func:`wear_miss_brake_status` 判定,本口
    返回契约(bool)零变化。本口只阻止失真投影写入,不做任何 observe
    失配吸收;闩在时的观察失配照真安灯。
    """
    _ct = _wear_miss_counters(session)
    if _ct is None:
        return False
    _key = _ct.pop(CW4_KEY_WEAR_MISS_PENDING, None)
    _act_key = wear_miss_key_of(action)
    if _key != _act_key:
        # 闩不在(正常穿戴)/陈旧闩 = 同键情节有了结 → 计数归零。
        _ct[CW4_KEY_WEAR_MISS_STREAK_N] = 0
        _ct[CW4_KEY_WEAR_MISS_STREAK_KEY] = None
        return False
    _n = _ct.get(CW4_KEY_WEAR_MISS_STREAK_N, 0) + 1 \
        if _ct.get(CW4_KEY_WEAR_MISS_STREAK_KEY, None) == _act_key else 1
    _ct[CW4_KEY_WEAR_MISS_STREAK_N] = _n
    _ct[CW4_KEY_WEAR_MISS_STREAK_KEY] = _act_key
    with contextlib.suppress(Exception):
        from sr_od.application.currency_war.telemetry import defects
        defects.record_defect(
            'equips', 'wear_miss_skip',
            expected=(f'WearEquip {_act_key} 拖后 owned 格像素变化'
                      '(icon 消失/网格 reflow)'),
            observed=('owned 格像素零变化(settle 重采仍零变化),两投影'
                      '腿跳写(容器经 emitted 门,黑板经本闩),交决策'
                      '循环重派'),
            verdict='留证-穿戴未生效(点击≠成了;投影跳写)',
            reader_source='wear_landing_pixel_check',
            note='分键登记 = wear_miss_consume 注释(连续 miss 刹车载体 '
                 'cw4_counters,上限 WEAR_MISS_REDISPATCH_LIMIT)')
    log.info('[cw][wear] 穿戴拖拽未生效,投影跳写:%s(连续 %s/%s);'
             '逻辑态保持事实,决策循环重派', _act_key, _n,
             WEAR_MISS_REDISPATCH_LIMIT)
    return True


def wear_miss_brake_status(session: Any) -> str | None:
    """穿戴 miss 刹车触顶判定(纯读;文案单一源,对齐
    buy_miss_brake_status / kernel deploy_miss_brake_status 形态)。

    :return: 触顶时的 round_fail 状态文案;未触顶 = None。判定消费点 =
    决策循环(cw_screen_prep 两路径共式)miss 计数后,触顶 = round_fail
    显式停交上层(消费面按 rr 非 None 交失败收口,零改动)。
    """
    _ct = _wear_miss_counters(session)
    if _ct is None:
        return None
    n = _ct.get(CW4_KEY_WEAR_MISS_STREAK_N, 0)
    if n < WEAR_MISS_REDISPATCH_LIMIT:
        return None
    return (f"WearEquip({_ct.get(CW4_KEY_WEAR_MISS_STREAK_KEY, '?')})"
            f'连续 {n} 次拖拽未生效超上限(交上层处置)')


class WearEquipOp(ActionOp):
    """穿装备单步(WearEquip 原子通路机械半 + 拖后落地像素验证)。
    非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """穿装备单步(WearEquip 原子通路机械半)。

        流程 = 稳帧确认(动画收尾输入条件化,非判效)→ owned 网格按名
        定位源件 → 拖前基线帧 → 单次拖拽 → 拖后源件格像素验证。未生效
        → 置申报闩 + ``env.emitted = False``(两投影腿跳写,语义见模块
        头);生效/缺证/载体缺席 → 发出即登记(既有语义)。落空由下一
        入口观察重派承接(重算计划 = 天然重试)。逻辑态(owned 摘件)
        容器腿在观察侧 ``_project_prep_obs``/apply_op_effect 直写。

        [索引定义] 源件格验证矩形 = owned 网格定位点为核 ±36px 方格
        (装备区格距 75px、icon ~70px:±36 恰覆盖单格不串邻格;格心 =
        read_equips 逐格分类现读,拖前恒稳)。
        """
        action: WearEquip = self.action
        ex = env.executor
        target = ex._equip_slot_drag_point(action.row, action.slot)
        if target is None:
            env.detail, env.emitted = (
                f'装备槽位坐标缺失:{action.row}-{action.slot}'
                '(建档漂移,禁兜底坐标)', False)
            return True
        start = ex._owned_grid_locate(action.item_name)
        if start is None:
            env.detail, env.emitted = (
                f'owned 网格未定位到 {action.item_name}'
                '(模板库缺失/计划失效,下帧重派重算)', False)
            return True
        match = env.match
        session = (getattr(match, 'session', None)
                   if match is not None else None)
        # 旧闩清位(单动作窗;语义见 wear_miss_pending_clear)。
        wear_miss_pending_clear(session)
        ex._wait_stable_frame()
        # 拖前基线帧(stable 后取帧 = 画面静止态,基线与拖拽同源;取帧
        # 异常由 wear_owned_cell_changed 缺证保守放行兜住)。
        _frame = None
        with contextlib.suppress(Exception):
            _frame = env.op.screenshot()
        _land_rect = Rect(int(start.x) - 36, int(start.y) - 36,
                          int(start.x) + 36, int(start.y) + 36)
        ex._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        ex._ctx.controller.drag_to(start=start, end=target,
                                   hold_time=0.5, duration=1.5)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        ex._op.park_cursor(after_wait=0.1)
        # 落地像素验证(点击≠成了;形态逐位对齐 BuyCardOp T-44):
        # 穿戴生效 = 源件离开 owned 网格的可见变化;像素零变化 = 拖拽
        # 未生效 → 置申报闩 + emitted=False(两投影腿跳写)。首采无变化
        # 先经 settle 重采一次(回弹动画收敛);不可判 = 缺证保守放行。
        _post = None
        with contextlib.suppress(Exception):
            _post = env.op.screenshot()
        _seen = wear_owned_cell_changed(_frame, _post, _land_rect)
        if _seen is False:
            time.sleep(WEAR_LAND_SETTLE_RETRY_DELAY_S)
            with contextlib.suppress(Exception):
                _post = env.op.screenshot()
            _seen = wear_owned_cell_changed(_frame, _post, _land_rect)
        if _seen is False and _wear_miss_counters(session) is not None:
            # 载体在场:两投影腿同跳(emitted 门跳容器腿 + 申报闩跳黑板腿)。
            wear_miss_pending_set(session, wear_miss_key_of(action))
            env.detail = (f'穿戴 {action.item_name} → '
                          f'{action.char_name or "前排空槽"}'
                          f'({action.row}-{action.slot}) 未生效'
                          '(owned 格像素零变化,投影跳写)')
            env.emitted = False
            log.warning('[cw!][wear] 穿戴 %s 拖后 owned 格像素零变化'
                        '(settle 重采仍零变化)→ 判未生效:两投影腿跳写,'
                        '交决策循环重派(连续 miss 刹车 = 闩消费口计数)',
                        action.item_name)
            return True
        if _seen is False:
            # 载体缺席(无局/第三方策略面)= 缺省口径:只留痕,保持
            # 既有发出即写语义(B4 缺席退缺省;两投影腿要么同跳要么
            # 同写,半跳会造成容器/黑板分叉,比照旧失真更糟)。
            log.warning('[cw!][wear] 穿戴 %s 拖后 owned 格像素零变化'
                        '(载体缺席,无计数面)→ 按既有语义放行',
                        action.item_name)
        detail = (f'穿戴 {action.item_name} → {action.char_name or "前排空槽"}'
                  f'({action.row}-{action.slot}) 已发(零比对,落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        env.detail, env.emitted = detail, True
        return True
