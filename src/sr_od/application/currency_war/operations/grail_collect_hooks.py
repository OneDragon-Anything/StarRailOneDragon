"""货币战争 圣杯任务(命运圣杯·祈愿试炼)采集钩子 —— [临时采集批,本文件整段可删]。

背景:圣杯任务相关画面(试炼卡选中态 / 完成提示 / 奖励发放帧 / 契约计数器)在常规
对局中不易自然出现且多数无建模,需要采集批实机留证。本文件是「圣杯任务强开·方案 B」
的两枚钩子(方案全文见当次 redesign 目录 holy_cup_force_open_plan 文档;钩子纪律
单一源 = od-dev-stop-hooks + sr-od-currency-war-dev data-collection「钩子统一使用」):

- B1 ``grail_pin_stop_hook``:钉屏停机钩子([临时捕获] 分类)。祈愿试炼 overlay 出现时
  存 sentinel(截图 + flag)→ 直调 stop_running → 不点击保画面,等 AI 现场建档。
- B2 ``grail_passive_collect``:被动哈希采集钩子。随正常决策环(备战观察帧)触发,
  内容哈希去重收一闪而过的瞬时帧,bot 继续跑,不改变任何决策行为。

生命周期(SR 约定,无开关无参数):
- **不激活态**:本文件只提供函数,调用点接线行以注释形式放在 cw_loop 0h 分支(B1)
  与 cw_screen_prep 备战观察帧(B2),取消注释即激活(diff 一次一行);
- **收尾**:采集清单(试炼卡选中态/tooltip/完成提示/奖励帧/契约计数器)建档或采齐后,
  删本文件整段 + 删两处接线行注释 + 删产物(`.debug/temp/currency_war/` 下 flag 与
  shots),不留任何开关位;
- best-effort:钩子任何异常不阻塞对局推进。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_observe import cw_shot_unique

if TYPE_CHECKING:
    from sr_od.application.currency_war.operations.cw_loop import CwLoop

# 产物统一落点(项目两级约定:临时文件 → .debug/temp/ → 玩法工作区 .debug/temp/currency_war/)
_FLAG_PATH = get_project_root() / '.debug' / 'temp' / 'currency_war' / 'grail_pin.flag'

# B2 节流下限(秒):备战帧微变(金币动画/光标/抗锯齿)会让原图字节哈希必新,
# 纯去重挡不住慢性刷屏(同源教训 = cw_observe.obs_conflict 截图节流与
# cw_screen_prep._capture_unrecognized_node_icons 的 300s 防抖)。20s = 瞬时提示
# (通常存活数秒)首现必被采到,最坏速率 ~180 帧/小时封顶,采集批 1-2 局可承受。
_MIN_INTERVAL_S: float = 20.0

# label → 上次落盘时刻(节流状态;key 恒 'grail_obs',dict 形态便于测试隔离复位)
_LAST_SHOT_TS: dict[str, float] = {}


def grail_pin_stop_hook(op: CwLoop):
    """B1 钉屏停机钩子([临时捕获] 分类,建档确认后删整段)。

    调用点:cw_loop 0h 分支「标识-祈愿试炼」命中后、CwScreenWishTrial 派发前。
    触发即:sentinel 截图(主帧 + 0.8s 后补一帧,防动画过渡帧单帧失真)→ 写 flag
    (三要素:触发定位 / 可执行处理步骤 / 删除条件)→ 直调 stop_running(不经 MCP)
    → 返回 round_wait 不点击,overlay 原样保持,下一轮 loop 顶见 STOP 退出。

    :param op: CwLoop 实例(用其 save_screenshot / last_screenshot /
        ctx.run_context / round_wait;类型仅注解,不 import 具体类防环)
    :return: op.round_wait(...) 结果(路由语义与 0h 分支原返回一致)
    """
    try:
        shot = op.save_screenshot(prefix='cw_grail_pin')
        time.sleep(0.8)
        try:
            _ts, img = op.ctx.controller.screenshot(independent=True)
            shot2 = cw_shot_unique(img, 'grail_pin_frame2') if img is not None else ''
        except Exception:  # noqa: BLE001  补帧失败不拦停机(flag+主帧已足)
            shot2 = ''
        _FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FLAG_PATH.write_text(
            f'[HOOK-STOP] 圣杯任务采集·钉屏停机钩子([临时捕获] cw_loop 0h 分支,\n'
            f'标识-祈愿试炼 命中 → 钉屏保 overlay 不点击;grail_collect_hooks.grail_pin_stop_hook)\n'
            f'时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'主帧: {shot}\n补帧: {shot2}\n'
            f'处理步骤:\n'
            f'1. 按 od-dev-stop-hooks §0/§1 现场协议:先复制保全两张截图,再交互;\n'
            f'2. 离线 analyze_screen(screenshot=<主帧路径>) + 视觉判读,采集目标:\n'
            f'   祈愿试炼选中态 / 试炼卡 objective 奖励文本带 / L3+ 档差异帧(建档走\n'
            f'   od-dev-screen-onboarding,补 area 走 MCP upsert_screen_area);\n'
            f'3. 采集清单建档确认后:删本 flag + 删 grail_collect_hooks.grail_pin_stop_hook\n'
            f'   整段 + 删 cw_loop 0h 接线行 → 重启 MCP server → relaunch。\n'
            f'删除条件: [临时捕获] 采集清单建档确认后删整段,不留开关。',
            encoding='utf-8')
        log.info('[cw-grail] 祈愿试炼 overlay → 钉屏停机采集 shot=%s flag=%s', shot, _FLAG_PATH.name)
    except Exception as e:  # noqa: BLE001  钩子失败不阻塞,仍执行停机保画面
        log.warning('[cw-grail] sentinel 落盘失败(仍停机保画面): %s', e)
    op.ctx.run_context.stop_running(reason='hook:cw_grail_pin')
    return op.round_wait(status='圣杯采集:祈愿试炼钉屏停机待建档')


def grail_passive_collect(screen: MatLike | None) -> str | None:
    """B2 被动哈希采集钩子([临时采集] 分类,采集清单采齐后删整段)。

    调用点:正常决策环的备战观察帧(cw_screen_prep),每帧传入当前截图。目标 =
    一闪而过的圣杯任务相关瞬时帧(完成提示 / 奖励发放弹窗 / 契约计数器 / L3+ 档
    overlay 差异帧)——这些态无 reader 无法点名识别,整帧哈希去重兜「不漏不重」,
    离线按文件名哈希视觉分拣。零决策影响:只存图,不读不动不阻塞。

    :param screen: 当前游戏截图(RGB);None 直接跳过
    :return: 落盘文件名;None = 节流窗内 / 哈希重复 / 落盘失败
    """
    if screen is None:
        return None
    try:
        now = time.monotonic()
        if now - _LAST_SHOT_TS.get('grail_obs', 0.0) < _MIN_INTERVAL_S:
            return None
        fn = cw_shot_unique(screen, 'grail_obs')
        if fn:
            _LAST_SHOT_TS['grail_obs'] = now
            log.info('[cw-grail] 被动采集落盘 %s', fn)
        return fn
    except Exception:  # noqa: BLE001  采集 best-effort,失败不阻塞对局
        return None
