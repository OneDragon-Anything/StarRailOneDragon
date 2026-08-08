# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 简报屏观测(对局开始):敌人词缀 + 位面首领。

简报屏(``货币战争-简报``)OCR reads:``read_affixes``/``read_bosses``/``read_affix_effect``
+ 词缀效果采集落盘(``affix_effects_data.py`` 运行时自写,HandleBriefing 采到新词缀/不一致 → 写入)。
下游:``state.enemy_affixes`` → ``mechanics_fit``(cw_comps);``state.bosses`` → ``boss_fit``。

共享 helper(``_area_rect``/``_ocr``/``BRIEFING_SCREEN``)在 ``cw_obs_core``。本模块被
``cw_observation`` re-export(向后兼容 ``from cw_observation import read_affixes``)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.utils.cv2_utils import save_image
from sr_od.application.currency_war.cw_obs_core import BRIEFING_SCREEN, _area_rect, _ocr
from sr_od.context.sr_context import SrContext


def read_affixes_with_pos(ctx: SrContext, screen: MatLike) -> list[tuple[str, Point]]:
    """简报词缀行 → ``(词缀名, center)`` 列表(center 用于 click 弹 tooltip 采效果)。

    读简报「区域-词缀行」area OCR → 词缀文字(滤数字/符号/短噪声)+ 其 center。下游
    ``AFFIX_MECHANIC_MAP``(cw_comps)映射机制 tag;未知词缀透传(mechanics_fit 中性)。
    读不到 / area 缺 → [](不覆盖 state.enemy_affixes)。

    OCR 名 vs competitors 数据名可能差(如 OCR「后台熄火」= competitors「前后台熄火」),
    透传原名,匹配在 AFFIX_MECHANIC_MAP(待实机校准补全,见 competitors.md 待确定)。
    """
    rect = _area_rect(ctx, '区域-词缀行', BRIEFING_SCREEN)
    if rect is None:
        return []
    out: list[tuple[str, Point]] = []
    for r in _ocr(ctx, screen, rect):
        name = r.data.strip()
        # 词缀名:中文为主,2-7 字(第二位面强化6/前后台熄火5/火之熄火4/同步行动4);滤数字/符号/短噪声
        if 2 <= len(name) <= 7 and re.search(r'[一-鿿]', name) and not re.search(r'\d', name):
            out.append((name, r.center))
    return out


def read_affixes(ctx: SrContext, screen: MatLike) -> list[str]:
    """简报词缀行 → 敌人词缀 OCR 原名列表(``read_affixes_with_pos`` 派生,只取名)。

    保留 ``list[str]`` 签名兼容下游(ctx.cw_briefing_affixes / session / state.enemy_affixes)。
    需要 center 点词缀采效果 → 用 ``read_affixes_with_pos``。
    """
    return [name for name, _ in read_affixes_with_pos(ctx, screen)]


def read_bosses(ctx: SrContext, screen: MatLike) -> list[str]:
    """简报首领行 → 3 个位面 boss 名列表(每局固定 3 boss,如 增熵能源集团/火线动力机甲/银甲武装公司)。

    3 个位面是货币战争的玩法结构(每局 3 位面 × 每位面 1 boss),**所有难度(A5/A8/A850)都 3 个,
    不随难度变**(2026-08-05 攻略 + 官方确认;难度只改敌人强度/词缀,不改位面数)。

    简报屏 3 boss 横排卡片(立绘 + 阵营标签 + 名字);读「区域-首领行」area OCR → boss 名
    (滤数字/符号/短噪声/「阵营」2 字 label)。下游 ``state.bosses`` → ``boss_fit(comp, bosses)``
    命中 ``comp.boss_weakness`` 打分。读不到 / area 缺 → [](不覆盖 state.bosses)。

    ⚠️ 数据层待补(同 competitors.md,后续浏览器/图鉴采):boss 机制 + 哪些 comp 怕哪个 boss
    (``comp.boss_weakness``)。当前 ``comp.boss_weakness`` 多为空 → boss_fit 中性 0.5;识别链路先通,
    数据层后续接上即生效。boss 阵营(红色标签内)OCR 暂不读(红底干扰,待视觉核实后再决定是否采)。
    """
    rect = _area_rect(ctx, '区域-首领行', BRIEFING_SCREEN)
    if rect is None:
        return []
    bosses: list[str] = []
    for r in _ocr(ctx, screen, rect):
        name = r.data.strip()
        # boss 名:6 字中文为主(增熵能源集团/火线动力机甲/银甲武装公司);滤「阵营」label(2字)/数字/符号
        if 4 <= len(name) <= 8 and re.search(r'[一-鿿]', name) and not re.search(r'\d', name):
            bosses.append(name)
    return bosses


def read_affix_effect(ctx: SrContext, screen: MatLike, affix_name: str) -> str:
    """点词缀后的 tooltip 截图 → 该词缀的效果原文(**纯 OCR 解析,不 click**)。

    调用前已 ``click(词缀 center)`` + sleep + ``screenshot()`` 弹出 tooltip。本函数 OCR 全屏
    → 找 tooltip 标题(同名文本中**最上方**一个 —— 词缀行 y965 也有同名,tooltip 标题在它上方)
    → 取标题下方**紧邻连续**的行(按 y 排序,与上一行 dy ≤ 45 纳入,遇大 gap 停)拼接 = 效果原文。
    找不到标题 / 无下行 → ''(调用方写 yml 待人工同步)。

    tooltip 机制(2026-08-05 A8 实机点 4 词缀验证):点词缀弹 tooltip(切换不关旧),水平居中词缀,
    y 850-920(词缀行上方);内容 = 词缀名标题(y最小)+ 描述(+ 数值/续句,行高 ~25-30,dy 递增)。
    效果确定在标题正下方,故不靠固定 y 上界,靠**连续性**(dy≤45)取,遇 Gap(到词缀行/难度/下一步)
    即停 —— 分辨率/布局微变也鲁棒。
    """
    ocr = ctx.ocr_service.get_ocr_result_list(image=screen, rect=None, crop_first=False)
    same_name = [r for r in ocr if affix_name in (r.data or '')]
    if not same_name:
        return ''
    y0 = min(r.center.y for r in same_name)            # tooltip 标题 = 同名最上方(词缀行同名在下方)
    below = sorted((r for r in ocr if r.data and r.center.y > y0), key=lambda r: r.center.y)
    lines: list[str] = []
    last_y = y0
    for r in below:
        if r.center.y - last_y > 45:                    # 大 gap = 效果文本结束(下一组是词缀行/难度等)
            break
        lines.append(r.data)
        last_y = r.center.y
    return ''.join(lines)


# 词缀效果采集落盘(.debug/ 不入 git)。注册表 AFFIX_EFFECTS 在 affix_effects_data.py(单独文件,
# 运行时 write_affix_effects 自动写入);tooltip 截图存 affix_shots/(对账用)。
_CW_DEBUG_DIR: Path = Path(__file__).resolve().parents[4] / '.debug' / 'temp' / 'currency_war'
_AFFIX_SHOTS_DIR: Path = _CW_DEBUG_DIR / 'affix_shots'   # 词缀效果 tooltip 截图(对账用)
# 词缀效果注册表 py 文件(与本文件同目录 currency_war 包;运行时 write_affix_effects 写入)
_AFFIX_EFFECTS_PATH: Path = Path(__file__).resolve().parent / 'affix_effects_data.py'


def load_affix_effects_from_file() -> dict[str, str]:
    """读 ``affix_effects_data.py`` 文件 → ``AFFIX_EFFECTS`` dict(**文件最新**,采集对比用)。

    对比目标 = 文件最新(跨轮 + 本轮内都准,避免重复写);下游 mechanics_fit 用内存 import(本轮启动时旧值,
    **下轮重新 import 生效**)。用 ``exec`` 解析 py(自己生成的文件,安全)。

    TODO: exec 解析不优雅(真实使用时),后续换 importlib.reload / ast 解析 / 数据文件格式后删除本函数。
    """
    if not _AFFIX_EFFECTS_PATH.exists():
        return {}
    ns: dict = {}
    try:
        exec(_AFFIX_EFFECTS_PATH.read_text(encoding='utf-8'), ns)   # exec 解析自己生成的注册表文件(安全)
        result = ns.get('AFFIX_EFFECTS', {})
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def save_affix_screenshot(screen: MatLike, name: str) -> str:
    """存词缀效果 tooltip 截图到 ``affix_shots/<name>.png``(对账用:回查确认 OCR 采的效果对不对)。

    命名 = 词缀名(重采覆盖留最新)。返回文件名(对账回查)。
    """
    _AFFIX_SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f'{name}.png'
    save_image(screen, str(_AFFIX_SHOTS_DIR / filename))
    return filename


def write_affix_effects(updates: dict[str, str]) -> bool:
    """merge ``updates`` 进 ``affix_effects_data.py`` 注册表(新名新增 / 不一致覆盖)。

    读文件最新(``load_affix_effects_from_file``)→ merge ``updates`` → 写回(``json.dumps`` 生成合法 py
    dict literal,中文保留)。**写入不影响已加载内存**(下游本轮用旧值)→ **下轮启动重新 import 生效**。
    ``updates`` 空 → 不写。返回是否写入。
    """
    if not updates:
        return False
    current = load_affix_effects_from_file()
    current.update(updates)
    content = (
        '"""敌人词缀 → 游戏原文效果注册表(数据层 ground truth)。\n'
        '\n'
        '**本文件由 HandleBriefing 运行时自动维护**(``cw_briefing_obs.write_affix_effects`` 采到新词缀 /\n'
        '与现有不一致 → 写入)。运行时写入**不影响已加载内存**(下游 mechanics_fit 用 import 时的旧值)\n'
        '→ **下轮启动重新 import 生效**。人工也可直接编辑本文件(校准/补全)。\n'
        '\n'
        '格式 = ``AFFIX_EFFECTS: dict[str, str] = {...}``(json 兼容,双引号)。词缀分类见 competitors.md。\n'
        'mechanics_fit 接线(词缀→tag→comp 克制评分)已在 cw_comps.AFFIX_MECHANIC_MAP + MECHANIC_COUNTERS/SYNERGIES\n'
        '落地(D-49/55,接 comp_score W_MECH);本文件只采 effect 原文(ground truth,不参策略)。\n'
        '"""\n'
        'from __future__ import annotations\n\n'
        'AFFIX_EFFECTS: dict[str, str] = ' + json.dumps(current, ensure_ascii=False, indent=4) + '\n'
    )
    _AFFIX_EFFECTS_PATH.write_text(content, encoding='utf-8')
    return True
