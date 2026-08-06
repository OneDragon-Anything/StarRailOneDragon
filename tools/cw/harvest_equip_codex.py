"""货币战争 · **装备图鉴**批量采集(专用;独立 SrContext 驱动,绕开 MCP 往返)。

本脚本只采**装备**(简易/进阶/特权/星徽/白昼/命运/骇客 各 tier tab),不采角色/投资策略。
配套离线裁切工具见 ``harvest_equip_icons.py``(从截图裁固定框图标)。

== ⚠️ 前置:手动进到这个画面再跑 ==
1. 游戏内:从「备战」点「数据银行」(非破坏性 overlay,对局保留)→ 进「装备图鉴」。
2. 点目标 **tier tab**(次级 tab,画面 y≈170 那一行图标:简易/进阶/特权/星徽/白昼/命运/骇客),
   让该 tier 的装备网格显示出来(左侧 7 列 × 3 行)。
3. 然后跑本脚本(见用法)。脚本会从当前 tier tab 开始:点格 → 截图 → OCR 右侧装备名 →
   存图标(固定框)+ 全图 → 滚动翻页 → 按名去重 → 整页 0 新增即停。

== ⚠️ 必须在与游戏同一个 session 运行(2026-08-06 踩坑)==
游戏跑在 **Session 1**(交互桌面)。本脚本用 ``SrContext.controller`` 经
``pyautogui.getWindowsWithTitle`` 找游戏窗口 —— 该调用**只在同 session 能看到窗口**。
从 **Session 0**(SSH/服务/Bash 工具默认会话)跑 → 找不到窗口 → ``is_win_valid=False`` 报
「游戏窗口未就绪」(同 [[record-via-mcp-backend]] 的 Session 0 BitBlt 拒是一类问题)。
→ 必须在 Session 1 跑(交互桌面终端 / 经 backend 拉起),Session 0 的 Bash 跑不了。
代码正确,Session 1 下可正常工作(待用户验证)。

== 为什么要独立 SrContext(用户 2026-08-06)==
MCP 逐件 click+capture 慢(每件 2+ 调用 × 155 件 = 300+ 往返)。本脚本在本进程另起一个
``SrContext``,直接用 ``controller`` 操作游戏窗口(backend 空闲时不冲突),一次跑完一个 tier。
可复用,版本更新重跑。

== 用法 ==
    # 已手动进到目标 tier tab 的装备图鉴画面后,在 Session 1 跑:
    uv run python tools/cw/harvest_equip_codex.py 进阶
    # 或脚本自己点 tier tab(传次级 tab 的 x 坐标,y 固定 170):
    uv run python tools/cw/harvest_equip_codex.py 进阶 --tab-x 338

== 几何(1080p,固定;跨 tier tab 不变)==
- 网格 7 列 × 3 可见行(行间距 233)。
- 右侧详情面板:装备名 OCR 区 + 选中装备图标固定框(CV squares 验证,跨 tab 不变)。
- 完整效果正文 / 合成公式也在右侧固定区(存全图后离线 OCR)。

== 去重 + 停止 ==
按 OCR 装备名去重;每「页」(21 格点一遍)统计新增,整页 0 新增 → 该 tier 采全。
滚动不要求精确对齐行 —— 点固定格位选中任意 equip,OCR 名去重,多次滚动后必收敛。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from one_dragon.base.geometry.point import Point  # noqa: E402
from one_dragon.utils import cv2_utils  # noqa: E402

# 固定几何(1080p 游戏坐标;简易 tab CV 校准,跨 tier tab 不变)
GRID_COLS = [131, 307, 482, 657, 832, 1006, 1183]   # 7 列 x 中心
GRID_ROWS = [348, 581, 814]                          # 3 可见行 y 中心(行间距 233)
ICON_BOX = (1443, 125, 1541, 223)                   # 右侧详情「选中装备图标」固定框 98×98
NAME_REGION = (1540, 115, 1780, 160)                # 右侧装备名 OCR 区(含 ·特权 后缀)
SCROLL_FROM = Point(600, 800)                       # 上滑翻页:从底拖向顶(往下看更多行)
SCROLL_TO = Point(600, 520)

ICON_DIR = REPO / "assets/template/cw_equip"
SHOT_DIR = REPO / ".debug/temp/cw_shots"


def save_png(img, path: Path) -> None:
    """RGB 图存盘(cv2_utils.save_image 自动 RGB→BGR;中文路径安全)。"""
    cv2_utils.save_image(img, str(path))


def ocr_name(ctx, img) -> str:
    """OCR 右侧装备名区,取最长(最像装备名)的文本。"""
    x0, y0, x1, y1 = NAME_REGION
    crop = img[y0:y1, x0:x1]
    res = ctx.ocr_service.get_ocr_result_list(image=crop, crop_first=False)
    texts = [r.data.strip() for r in res if r.data and r.w > 20]
    return max(texts, key=len) if texts else ""


def harvest_tier(ctx, tier: str, tab_x: int | None) -> list[str]:
    """采集当前(或 tab_x 指定的)tier tab 的全部装备图标 + 全图。"""
    ctrl = ctx.controller
    ctrl.active_window()

    # 可选:点 tier tab(次级 tab,y≈170)
    if tab_x is not None:
        ctrl.click(Point(tab_x, 170), press_time=0.1, pc_alt=False)
        time.sleep(1.0)

    (SHOT_DIR / tier).mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    pass_no = 0
    while pass_no < 8:
        pass_no += 1
        new_this = 0
        for ry in GRID_ROWS:
            for cx in GRID_COLS:
                ctrl.click(Point(cx, ry), press_time=0.1, pc_alt=False)
                time.sleep(0.4)
                img = ctrl.get_screenshot(independent=False)
                if img is None:
                    continue
                img = ctrl.fill_uid_black(img)
                nm = ocr_name(ctx, img)
                if not nm or nm in seen:
                    continue
                seen.add(nm)
                new_this += 1
                x0, y0, x1, y1 = ICON_BOX
                save_png(img[y0:y1, x0:x1], ICON_DIR / f"{nm}.png")
                save_png(img, SHOT_DIR / tier / f"{nm}.png")
                print(f"[pass{pass_no}] +{nm}")
        print(f"pass{pass_no}: +{new_this} new (total {len(seen)})")
        if new_this == 0:
            break
        # 滚动翻页(整页都有新增才滚;0 新增已 break)
        ctrl.drag_to(SCROLL_TO, start=SCROLL_FROM, duration=0.5)
        time.sleep(0.6)
    return sorted(seen)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    tier = args[0]
    tab_x = None
    if "--tab-x" in args:
        tab_x = int(args[args.index("--tab-x") + 1])

    from sr_od.context.sr_context import SrContext
    ctx = SrContext()
    ctx.init()
    ctrl = ctx.controller
    if ctrl is None or not ctrl.is_game_window_ready:
        print("游戏窗口未就绪,先 check_game_window")
        sys.exit(2)

    found = harvest_tier(ctx, tier, tab_x)
    print(f"\n== {tier} 采集完成: {len(found)} 件 ==")
    for n in found:
        print(" ", n)


if __name__ == "__main__":
    main()
