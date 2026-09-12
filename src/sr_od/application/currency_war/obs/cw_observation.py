"""货币战争 **备战屏**观测:备战截图 → ``GameState``(``read_game_state``)。

本模块只管**备战屏** reads(gold/hp/level/phase_round/board[+next_tier]/shop/bench_full)+ 组合入口
``read_game_state``。简报 reads 在 ``cw_briefing_obs``、结算 reads 在 ``cw_settlement_obs``、
共享 helper/常量在 ``cw_obs_core``(消费方一律直连 owner 模块 import,本模块不再 re-export)。

备战字段采集按 doc 06(``strategy/06_input_model.md``)逐簇推进(board tier 已接,余待采:
active_strategies/enemy_difficulty/level_up_cost/inventory 等;icon/身份类阻塞于 vision/SIFT 库)。

**区域单一真相源 = screen_info**(用户 2026-08-03):``assets/game_data/screen_info/currency_war_battle_prep.yml``
(screen「货币战争-备战」),经 ``cw_obs_core._area_rect`` 读 area 的 pc_rect —— 改区域改 yml 即可,不动代码。

设计原则(strategy/05_observation(签名+失败语义+sanity bounds)):
- 每字段用 ``_ocr(rect=...)`` 定区域读(**不塌缩重复文本** —— 地图版 get_ocr_result_map 按文本聚合,
  两张同阵营牌会撞键丢一张;list 版保留全部)。
- OCR 失败 / 越界(sanity bounds)→ 安全默认,不抛错(plan 对默认安全降级:
  gold 默认 0 → 不买;hp 默认 100 → 不触发保血)。越界读(gold 读成 500)比读不到更危险。

v1 OCR 可读性(2026-08-03,实机多样本 + 诊断脚本确认):
- **level**:``read_level`` OCR 优先 + ``_expected_level`` 兜底;telemetry level 跨样本合理(✓)。
- **hp**:⚠️ **plan-time 读不到(保血原本未武装),根因已确认 = shop 开启时右上角 HP 区空,非读取器坏**。
  ``BuyShopCards`` 在 shop 关闭帧读 hp → 覆盖 state.hp(见 shop.buy)。
- **board**:count 解析曾脆(全屏 OCR 把 "2/3" 误读 "213");改用 ``_board_pairs`` 聚焦解析 X/Y,
  count=X + next_tier=Y(``read_board_next_tier``),根因(全屏密度)解决。
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_BOARD,
    A_GOLD,
    A_PHASE,
    A_SHOP_CARD_PREFIX,
    GOLD_MAX,
    GOLD_MIN,
    HP_MAX,
    HP_MIN,
    LEVEL_MAX,
    LEVEL_MIN,
    SHOP_SCREEN_NAME,
    _area_rect,
    _first_int,
    _ocr,
    is_prep_like_frame,
)
from sr_od.application.currency_war.kernel.cw_observe import obs_conflict
from sr_od.application.currency_war.kernel.cw_economy import (
    REFRESH_COST_BASE,
    XP_TO_NEXT_LEVEL,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    get_node_ledger,
    ledger_node_type,
    rebuild_deployed_from_board,
)
from sr_od.application.currency_war.kernel.cw_state import GameState, ShopCard
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    identify_character,
    read_merge_preview,
    resolve_char_name,
)
from sr_od.context.sr_context import SrContext


def _expected_level(plane: int, round_num: int) -> int:
    """阶段期望等级(**单一源 cw_economy._expected_level**;参数序 (plane, round_num) 转接)。

    level 不可 OCR 时作兜底:≈ 真实等级,使 economy level_val≈0(不误判欠等级 → 不滥升)
    + max_units≈ 真实(deploy_cap 真值优先、level 兜底;ADR-0286/D-53:
    cap=level+宝钻数,兜底仅宝钻局偏差)。
    ⚠️ r90 审计必修:此副本曾与 economy 侧漂移(改刻度忘了这里)——统一 import 单一源,
    本函数只做参数序转接(消费方按 (plane, round) 调)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        _expected_level as _econ_expected_level,
    )
    return _econ_expected_level(round_num, plane)


# ===== 备战单字段读取(失败 → 安全默认)=====
def read_gold_opt(ctx: SrContext, screen: MatLike) -> int | None:
    """当前金币(r319:miss→None 保真版;契约伴生 read_gold 仍返 0)。

    保留裁剪读 + 3x 放大(2026-08-24 crop-first 审计):小目标 stylized 数字,全图 det 几乎
    总漏——放大破 det 天花板,与全图帧缓存不兼容;理由详见 ``read_gold`` docstring。
    """
    rect = _area_rect(ctx, A_GOLD)
    if rect is None:
        return None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None
    up = cv2.resize(crop, (crop.shape[1] * 3, crop.shape[0] * 3), interpolation=cv2.INTER_CUBIC)
    v = _first_int([r.data for r in ctx.ocr_service.get_ocr_result_list(image=up)])
    if v is None or not (GOLD_MIN <= v <= GOLD_MAX):
        return None
    return v


def read_gold(ctx: SrContext, screen: MatLike) -> int:
    """当前金币(底部右侧数字)。读不到 / 越界 → 0(plan 不买,安全保守)。

    gold 数字小 + stylized,paddle native det 几乎总漏(读 0/空,实锤见 process_log)→
    裁 area 后 **放大 3x** 再 OCR(破小目标 det 天花板)。area 已收紧到只含 gold 数字
    (排除隔壁 G0/0 货币;2026-08-07 实测 [1610,890,1690,945] 放大后稳读 3/2)。
    读值走 ``read_gold_settled`` 稳定门(见其 docstring:读金瞬间数字在动的场景,
    单帧读会拿到入账前旧值)。
    """
    v = read_gold_settled(ctx, screen)
    return 0 if v is None else v


#: 金稳定门补采帧数上限(首帧之外最多再采 3 帧,间隔见下;最坏 ~1.5s,
#: 只在「帧间读数不一致」时花满,静止屏首两帧一致即返,零额外成本)。
GOLD_SETTLE_MAX_POLLS: int = 3
#: 金稳定门补采间隔(秒)。局收入入账计数器从起跳到停约 1s 量级
#: (run_20260828_074721 P3 r1 开店连读 73→75 实测计数器在动),0.5s
#: 步长下 3 帧覆盖 ~1.5s,足够越过入账窗;再长会拖慢每个 read_game_state。
GOLD_SETTLE_INTERVAL_S: float = 0.5

#: 难度旗牌徽记带上沿(裁片内 y,1080p 像素):「文本-难度」旗牌上半是徽记图案、
#: 下半是数字。像素亲测(58 帧 fixture 裁片,2026-08-28):徽记占 y 0..45、
#: 数字带 y>=55,取 48 留双向安全距。``_ocr_difficulty_binarized`` 据此抹带。
_DIFFICULTY_EMBLEM_BAND_Y: int = 48

#: 难度合理带下限(根除单帧噪声:OTSU 纹理噪声/徽记残影可读出 0/1 类一位数)。
#: 推导:难度恒为两至三位数;观测最小真值 39(低职级局 fixture 实读);
#: 压低类词缀叠加最坏情形(难度修改器 -4 + 简单模式 -3 + 退化 -5)自 base
#: ~40 最低探到 ~30 一带,20 留足裕量仍远高于一位数噪声。
_DIFFICULTY_MIN: int = 20
#: 难度合理带上限:沿用简报解析 ``parse_enemy_difficulty`` 的越界线 300
#: (>300 视为读坏)。**刻意不取 200**:敌方溢出 bug 阈值 200(cw_difficulty_account
#: OVERFLOW_THRESHOLD,V4.4 实测 211)是合法游戏态,200 封顶会恰在难度账本
#: 最需要读数的溢出区致盲。
_DIFFICULTY_MAX: int = 300


def read_gold_settled(ctx: SrContext, screen: MatLike) -> int | None:
    """带稳定门的金读数(读不到/越界 → None,契约同 ``read_gold_opt``)。

    根因(实机 12 局 20 条 gold_delta 冲突对拍,`w489_sim_real_gap/` 审计感知面):局收入在
    轮/位面切换后**入账计数器仍在跳**(实锤 run_20260828_074721 P3 r1:开店
    连读 73→75,同一读点数字在动;下轮开店读 90 = 本轮关店读 79 + 常规收入
    11,反推关店实读正确、开店读系统性偏低 = 读在入账前/入账中)→ 单帧读
    把「未入账旧值」当真值喂给 plan,息线/花金义务整体错位(大额漂 16-40 金)。

    修法(读链根因环,不做「读数再猜」):同读点补采新帧重读,两帧一致才采信;
    不一致(计数器在跳)→ 取**末帧**(新帧更接近当下;入账计数器单调向上,末帧
    ≥ 首帧即入账后真值)+ ``obs_conflict('gold', ...)` 留证 + warning(不静默:
    采了哪个值、为何采,判读侧可见)。补采走 ``ctx.controller.screenshot()``
    (同 ``read_deploy_cap_debounced`` 先例);控制器不可得(离线/单测)退单帧读,
    行为与修前完全一致。
    """
    v = read_gold_opt(ctx, screen)
    if v is None:
        return None
    controller = getattr(ctx, 'controller', None)
    if controller is None or not hasattr(controller, 'screenshot'):
        return v   # 离线/单测:无真控制器,单帧读即全部能力
    last = v
    final = v
    disagreed = False
    for _ in range(GOLD_SETTLE_MAX_POLLS):
        try:
            time.sleep(GOLD_SETTLE_INTERVAL_S)
            nxt = read_gold_opt(ctx, controller.screenshot())
        except Exception:   # noqa: BLE001  补采帧不可得 → 保留已读值
            break
        if nxt is None:
            break
        final = nxt
        if nxt == last:
            break
        last = nxt
        disagreed = True
    if not disagreed:
        return final
    obs_conflict('gold', v, final, screen,
                 verdict=('采新-多帧稳定门(读金期间数字在动:局收入入账计数器/'
                          '动画,单帧读会拿入账前旧值;取末帧=入账后真值;'
                          '复现高频回查收入入账时序)'),
                 source='gold_settle_gate')
    log.warning('[cw!] gold 稳定门:首帧=%s 末帧=%s(帧间在动,采末帧)', v, final)
    return final


def read_refresh_probs(ctx: SrContext, screen: MatLike) -> dict[int, float] | None:
    """商店开态的概率条 → {费用档 1-5: 概率}(r77 轮岗接线;读不到 → None 退基线)。

    **为什么读屏**(用户 2026-08-19 点题「轮岗」):投资环境轮岗每备战阶段随机翻倍
    一个费用档(基线 lv6 30/40/25/5 → 1费翻倍变 60/22/15/3,实测吻合)——概率条
    直接印在商店面板上,OCR 即真值,无需建模哪个档被随机翻倍、也覆盖其他概率类
    环境。消费方:plan._sample_cost(D 牌蒙特卡洛)/ refresh 价值评估。
    """
    from sr_od.application.currency_war.kernel.cw_obs_core import (
        SHOP_SCREEN_NAME,
        _area_rect,
    )
    rect = _area_rect(ctx, '按钮-刷新概率表', SHOP_SCREEN_NAME)   # 概率条在开商店子态屏
    if rect is None:
        return None
    from sr_od.application.currency_war.data.cw_shop_odds import parse_prob_bar
    # 全图 OCR + rect 过滤(2026-08-24 crop-first 审计转换;fixture shop_open.webp 对拍
    # 与裁剪读逐字等价)。read_game_state 链同帧多 reader 共享一次全图识别(帧级缓存)。
    texts = [r.data for r in _ocr(ctx, screen, rect)]
    return parse_prob_bar(texts)


def read_hp_opt(ctx: SrContext, screen: MatLike) -> int | None:
    """read_hp 的保真版:读不到/越界 → None(默认值由调用方定)。

    遥测用(insights 2026-08-15「hp=100 默认值毒化遥测」):read_hp 的 100 默认是决策层
    安全设计(不触发保血),但遥测记录里「真 100」与「读不到兜底 100」不可区分 → 复盘误判
    (M19 曾误读「P1 零损」)。遥测/复盘侧用本函数区分。

    两通道对账(原生 + 3x 放大,不一致以放大通道为准并留证):
    hp 数字为美术字,笔画断续时**原生分辨率 det/rec 偶发丢十位**(如 47 读成 4、
    12 读成 2;2026-09-02 obs_conflict 分诊帧 40e3354a/e4746213 离线复现实证:
    同帧原生读 4/2、3x CUBIC 放大读 47/12,均与画面真值一致)。旧实现「原生命中
    即短路」让这类错值直接采信——掉十位把健康读成濒死,且错值恰落在下行守卫的
    拒信/复现通道里制造证据噪声。修法:放大通道**常开**作第二读,两通道一致才
    静默;不一致 → obs_conflict 留证并采放大值。放大通道更可信的依据 = 本函数
    既有失明回退先例(低血小数值原生 det 漏检、3x 放大即恢复,局21 P2 r4 离线
    对拍)+ 上述掉十位帧的离线复现。代价:每真值帧多一次小裁片(90×80)放大
    OCR,百毫秒级。
    """
    rect = _area_rect(ctx, '文本-剩余血量')
    v_native = _first_int([r.data for r in _ocr(ctx, screen, rect)])
    if v_native is not None and not (HP_MIN <= v_native <= HP_MAX):
        v_native = None
    v_up = _first_int([r.data for r in _ocr_upscaled(ctx, screen, rect)])
    if v_up is not None and not (HP_MIN <= v_up <= HP_MAX):
        v_up = None
    if v_native is not None and v_up is not None and v_native != v_up:
        obs_conflict('hp', v_native, v_up, screen,
                  verdict=('采新-双通道对账采放大值(原生/放大不一致:hp 美术字笔画'
                           '断续,原生通道偶发丢十位,放大通道离线复现全对;'
                           '处理:采放大值,频发→查原生通道遮挡形态)'),
                  source='hp_dual_pass')
        log.warning(f'[cw!] hp 双通道不一致:原生={v_native} 放大={v_up} → 采放大值')
        return v_up
    v = v_native if v_up is None else v_up
    if v is None:
        v = _first_int([r.data for r in _ocr_upscaled_binarized(ctx, screen, rect)])
        if v is None or not (HP_MIN <= v <= HP_MAX):
            return None
    return v


def _ocr_upscaled(ctx: SrContext, screen: MatLike, rect: Rect | None,
                  scale: int = 3) -> list:
    """裁剪 + 放大后 OCR(read_gold 实证的小目标 det 天花板手法)。

    小字区域(XP 条 / 等级数字)原生分辨率下 paddle det 漏检 → 双失读级联:
    等级 OCR 与 XP 反推同帧皆空 → 决策落 ``_expected_level`` 启发式(假设已买经验,
    P1 早期系统性偏高 +2)→ cap<level 域守卫拒信 deploy_cap(冲突帧
    6f41536e/23dee97a 实锤:画面 Lv.3/3、Lv.4/4 自洽,虚高全在 level 侧)。
    3x CUBIC 放大后三张冲突帧 XP 与等级全恢复读数(离线对拍)。
    """
    if rect is None:
        return []
    if screen is None:
        # 测试注入态(mock ocr_service,screen 不承载像素;仓内既有约定)→ 不裁剪直接透传
        return ctx.ocr_service.get_ocr_result_list(image=screen, rect=rect, crop_first=False)
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return []
    up = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                    interpolation=cv2.INTER_CUBIC)
    return ctx.ocr_service.get_ocr_result_list(image=up)


def _ocr_upscaled_binarized(ctx: SrContext, screen: MatLike, rect: Rect | None,
                            scale: int = 3) -> list:
    """裁剪 + 放大 + OTSU 二值化后 OCR(``_ocr_upscaled`` 的对比度增强变体)。

    只作 ``_ocr_upscaled`` 读空后的第二级重试:低对比背景上金色费用数字原生 det 漏检,
    放大仍漏时 OTSU 全局阈值把数字从蓝底金饰中分离。⚠️ 二值化对彩色小字有信息损失,
    不可作为第一级(会伤及放大即可读的帧)。
    """
    if rect is None:
        return []
    if screen is None:
        return ctx.ocr_service.get_ocr_result_list(image=screen, rect=rect, crop_first=False)
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return []
    up = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                    interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return ctx.ocr_service.get_ocr_result_list(image=cv2.cvtColor(bw, cv2.COLOR_GRAY2RGB))


def read_level_raw_opt(ctx: SrContext, screen: MatLike) -> int | None:
    """「文本-等级」区直读等级(**无任何兜底**;None=失读,调用方决定退路)。

    放大读(失读根因与手法见 ``_ocr_upscaled``)。值域 ``LEVEL_MIN..LEVEL_MAX`` 外按失读处理。
    read_level(决策)与 read_game_state(三源解析基值)共用本直读,prep_actions
    ``_read_level_raw``(完成验证)同源语义,不再各写一份裁剪 OCR。
    """
    v = _first_int([r.data for r in _ocr_upscaled(ctx, screen, _area_rect(ctx, '文本-等级'))])
    if v is not None and (LEVEL_MIN <= v <= LEVEL_MAX):
        return v
    return None


def _parse_xp_pair(blob: str, expected_level: int | None = None) -> tuple[int, int] | None:
    """XP 文本 → ``(cur, next)``;解析不出 → None(纯函数可单测)。

    两级解析(字段先验:格式恒为 "X/Y",next ∈ ``XP_TO_NEXT_LEVEL.values()``):
    1. 斜杠误识兜底(D-53 同款):数字间非数字单字符 normalize 成 ``/`` 再正则;
    2. **斜杠被识成数字 '1'**("2/4"→"214"、"4/6"→"416",冲突帧实测):
       遍历 '1' 位插入 '/' 拆分,仅当**分子分母同时合法**(两侧皆数字、cur≤next、
       next 落在等级表分母集合)且**上下文等级先验一致**时才采信。

    :param expected_level: 上下文等级先验(session.last_level_obs;None=无先验)。
      仅约束第 2 级 '1' 拆分路径:分母 4 是 lv3 独有分母且与短数字天然易混
      (真 lv4 帧 OCR 退化成 "34" 之类被拆成 (3,4) → 反推 lv3,是 lv 3↔4
      乒乓的潜在源),拆分结果反推的等级与先验不一致 → 判失读(返回 None),
      不采信;无先验(新局 last=0)保持旧行为。第 1 级 normalize 路径有显式
      '/' 分隔不受此疑,不做先验收紧(XP 纠正 OCR 误读的主权通道,ADR-0129)。
    """
    norm = re.sub(r'(?<=\d)\D(?=\d)', '/', blob)
    m = re.search(r'(\d+)\s*/\s*(\d+)', norm)
    if m:
        return int(m.group(1)), int(m.group(2))
    _valid_next = set(XP_TO_NEXT_LEVEL.values())
    _denom_to_lv = {v: k for k, v in XP_TO_NEXT_LEVEL.items()}
    for i, ch in enumerate(blob):
        if ch != '1':
            continue
        cur_s, nxt_s = blob[:i], blob[i + 1:]
        if cur_s.isdigit() and nxt_s.isdigit():
            cur, nxt = int(cur_s), int(nxt_s)
            if nxt in _valid_next and cur <= nxt:
                # 上下文先验一致才采信(分母 4 单数字易混;先验 None=无历史放行)
                if expected_level is not None and _denom_to_lv.get(nxt) != expected_level:
                    continue
                return cur, nxt
    return None


def read_level(ctx: SrContext, screen: MatLike, plane: int, round_num: int) -> int:
    """玩家等级(= 可上阵数上限,封顶 10)。

    OCR ``文本-等级``(screen_info 区域已排除下方 XP "0/6" 与「购买经验金币」,
    仅含等级数字 + "LV." 标签)→ 取首个数字。读不到 → **经验条反推**
    (``read_xp_progress`` 的 xp_to_next 经 ``XP_TO_NEXT_LEVEL`` 倒查,如
    "0/4" → lv3;2026-08-26 佩佩局实弹:OCR 漏读 Lv.3 小字 → 旧 ``_expected_level``
    兜底 4 → cap−level=0 → 后排选 6 格档丢佩佩@7 —— 期望曲线假设已买经验,
    P1 早期系统性偏高);仍读不到 → ``_expected_level`` 启发式兜底(≈ 真实等级,
    使 economy level_val≈0 不误判欠等级)。

    注:部分截图 OCR 漏读等级数字(如测试图 currency_war_shop.png 只出 "LV."),
    此时走反推/兜底。
    """
    v = read_level_raw_opt(ctx, screen)
    if v is not None:
        return v
    # XP 反推的先验 = session 上次观测等级(与 read_game_state 同源;'1' 拆分
    # 收紧防 lv 3↔4 乒乓,见 _parse_xp_pair)。无历史(0)→ None 旧行为。
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    _prior = getattr(_sess, 'last_level_obs', 0) or None
    xp = read_xp_progress(ctx, screen, expected_level=_prior)
    if xp is not None:
        from sr_od.application.currency_war.kernel.cw_economy import XP_TO_NEXT_LEVEL
        for lv, need in XP_TO_NEXT_LEVEL.items():
            if need == xp[1]:
                return lv
    return _expected_level(plane, round_num)


# 备战顶部节点类型标签 → 关键词。doc 13 §13.2A node_type。⚠️ 仅 boss(首领)实机核实;
# 其它节点类型(补给/遭遇/巨星/投资/战斗/精英/奖励)的标签措辞待多子态实机核实补全。
_NODE_TYPE_KEYWORDS: dict[str, str] = {
    '首领': 'boss', '补给': 'supply', '遭遇': 'encounter', '巨星': 'megastar',
    '战斗': 'battle', '精英': 'elite', '奖励': 'reward', '投资': 'invest',
}


def _node_type_label(ctx: SrContext, screen: MatLike) -> tuple[str | None, int | None]:
    """节点行标签带 OCR → ``(node_type, 标签中心 x 全屏)``;无已知关键词 → (None, None)。

    r80(审计 P0-1):标签**不止出现在当前节点下方** —— 2-7 备战实证「首领」出现在
    **即将到来的 boss 节点**下方(x≈1341,当前节点在行中部 x≈900)→ 旧 read_node_type
    只查关键词不看位置,把非 boss 轮误判 boss(boss_spend 提前花光资源,HP17 惨胜实证)。
    本函数带位置返回,调用方做锚定校验。
    """
    results = _ocr(ctx, screen, Rect(500, 65, 1700, 115))
    for r in results:
        for kw, nt in _NODE_TYPE_KEYWORDS.items():
            if kw in r.data:
                return nt, int(r.x + r.w / 2)
    return None, None


#: 标签 x 与当前槽 cx 容差(节点槽距 ~90px + 标签中心偏差;超过 = 标签属于别的节点)
_NODE_LABEL_X_TOL: int = 110
#: boss 语义门:首领 = 位面**最后**节点(基础 9 轮,boss=第 9;r80 审计 a 收紧:人身意外险
#: 在首领前+补给 → boss ≥10)→ round < 9 时读到的「首领」必是**即将到来**的 boss 节点
#: 标签(2-7 实证),不是当前节点。取 9(非 10)= 无环境加节点时的下限,宁紧勿松。
_BOSS_MIN_ROUND: int = 9


def gate_node_type(node_type: str | None, round_num: int | None,
                   label_x: int | None = None, current_cx: int | None = None) -> str | None:
    """无锚定 OCR 读到的 node_type 语义门(r80 审计 P0;纯函数可测)。

    两道门,任一不过 → None(不覆盖):
    1. **boss 轮次门**:node_type=='boss' 且 round_num < ``_BOSS_MIN_ROUND`` → 即将到来
       的 boss 节点标签(2-7 实证),非当前节点 → None。
    2. **标签位置门**(给了锚点时):|label_x - current_cx| > ``_NODE_LABEL_X_TOL`` →
       标签在别的节点下方(张冠李戴)→ None。
    """
    if node_type is None:
        return None
    if node_type == 'boss' and (round_num or 0) < _BOSS_MIN_ROUND:
        return None
    if label_x is not None and current_cx is not None \
            and abs(label_x - current_cx) > _NODE_LABEL_X_TOL:
        return None
    return node_type


def read_node_type(ctx: SrContext, screen: MatLike) -> str | None:
    """备战顶部「当前节点类型」标签 → node_type(boss/补给/遭遇/...;doc 13 §13.2A)。

    ⚠️ **无锚定的宽松读**(r80):「首领」等标签也会出现在**即将到来的节点**下方
    (2-7 实证)→ 本函数返回值**不可直接当当前节点类型**;消费方必须过
    ``gate_node_type`` 语义门(read_game_state boss 轮次门 / read_node_sequence
    标签位置门)。仅 boss(首领)实机核实;其它节点类型标签措辞待多子态实机核实。
    """
    t, _lx = _node_type_label(ctx, screen)
    return t


# 节点类型模板 Hu 矩缓存(module-level;``read_node_sequence`` 首调从 assets 加载)。
_NODE_TYPE_TEMPLATES: dict | None = None
_BOSS_TEMPLATES: dict | None = None
# clean 备战帧的最少圆数门:基础行 8 槽 + invest-env 增(人身意外险+1 → 9);shop 开 / 过渡 / overlay
# 遮挡时 HoughCircles 只检出 1-3 个。n < 此 → 非 clean 帧(reader 数据不可信:坏帧 Hu 畸变 → 假未识别),
# 返 None 跳过等下轮重读。容许 2 漏检(8→6),排除所有观测到的坏帧(n≤3)。
_MIN_CLEAN_CIRCLES: int = 6


def _classify_node_row(ctx: SrContext, screen: MatLike) -> tuple[list | None, tuple[int, int, int, int]]:
    """节点行 CV 核心(HoughCircles + 三态 + Hu + boss SIFT)+ 行矩形。

    返回 ``(slots, (x0, y0, x1, y1))``:slots 为**行裁图坐标**的 NodeSlot 列表
    (``cw_node_reader.classify_node_row`` 产物);行矩形 = 行区域的全屏坐标
    (screen_info「区域-节点条」或常量兜底)。三票校验的动态 ROI 从该几何
    推导,不写死坐标(投资环境会增删节点改变节点行,固定坐标无意义)。
    None = 模板未加载 / 非 clean 备战帧(圆数 < ``_MIN_CLEAN_CIRCLES``:
    shop 开 / 过渡 / overlay 遮挡 → 坏帧数据不可信)。
    """
    global _NODE_TYPE_TEMPLATES, _BOSS_TEMPLATES

    from sr_od.application.currency_war.obs.cw_node_reader import (
        NODE_ROW_RECT,
        classify_node_row,
        load_boss_templates,
        load_node_type_templates,
    )
    if _NODE_TYPE_TEMPLATES is None:
        _d = get_project_root() / 'assets' / 'game_data' / 'cw_node_types'
        _NODE_TYPE_TEMPLATES = load_node_type_templates(_d) or {}
    if not _NODE_TYPE_TEMPLATES:
        return None, (0, 0, 0, 0)
    if _BOSS_TEMPLATES is None:
        _bd = get_project_root() / 'assets' / 'template' / 'currency_war' / 'boss_avatar'
        _BOSS_TEMPLATES = load_boss_templates(_bd) if _bd.is_dir() else {}
    # 节点行区域单一源 = screen_info「区域-节点条」(2026-08-26 boss 识别批:
    # yml 扩到含 boss 圆 ~x1354;常量仅兜底,漂移以 yml 为准)
    _rect = _area_rect(ctx, '区域-节点条')
    _x0, _y0, _x1, _y1 = (
        (_rect.x1, _rect.y1, _rect.x2, _rect.y2) if _rect is not None
        else NODE_ROW_RECT)
    _slots = classify_node_row(screen[_y0:_y1, _x0:_x1], _NODE_TYPE_TEMPLATES,
                               boss_templates=_BOSS_TEMPLATES or None)
    if len(_slots) < _MIN_CLEAN_CIRCLES:
        return None, (_x0, _y0, _x1, _y1)   # 非 clean 备战帧(shop 开 / 过渡 / overlay 遮挡 → 圆数少);数据不可信,跳过等下轮重读
    return _slots, (_x0, _y0, _x1, _y1)


def read_node_sequence(ctx: SrContext, screen: MatLike) -> list | None:
    """备战顶部「节点行」→ 节点槽列表(``cw_node_reader.NodeSlot``);每次备战调(invest-env 增/改节点 → 重识别)。

    组装纯 CV 核心(``_classify_node_row`` → ``cw_node_reader.classify_node_row``):
    HoughCircles 动态定圆 + HSV 三态(已过/当前/未来)+ 未来 Hu 矩匹配 4 模板;
    **当前节点**类型用 OCR 标签(``read_node_type``,只有当前节点有文字标签)覆盖。
    **首领** = 位面最后节点(按位置判,不在节点行模板内;调用方按 round 推断)。未来圆 Hu 距离 >
    ``cw_node_reader.HU_DIST_UNRECOGNIZED`` → 未识别(扑满/新类型,调用方可触发采集)。

    ⚠️ screen 为框架 RGB;S/V/Hu 对 RGB/BGR 无关 → 直传 classify。
    返回 None:模板未加载 / 非 clean 备战帧(圆数 < ``_MIN_CLEAN_CIRCLES``:shop 开 / 过渡 / overlay
    遮挡 → 坏帧 Hu 畸变不可信)。调用方遇 None 跳过,等下个 clean 备战帧重读。详 ``cw_node_reader`` docstring。
    """
    _slots, (_x0, _y0, _x1, _y1) = _classify_node_row(ctx, screen)
    if _slots is None:
        return None
    # r80(审计 P0-1):OCR 标签**带位置**锚定校验 —— 「首领」等标签会出现在即将到来的
    # 节点下方(2-7 实证 x1341 vs 当前槽 cx≈900)→ 标签 x 与当前槽 cx 对拍,错位不覆盖。
    _t, _lx = _node_type_label(ctx, screen)
    if _t:
        _cur_slot = next((s for s in _slots if s.state == 'current'), None)
        if _cur_slot is None:
            pass   # 无当前锚(罕见)→ 不覆盖
        elif gate_node_type(_t, None, label_x=_lx,
                            current_cx=_cur_slot.cx + _x0) is None:
            log.info('[cw!][nodeseq] 标签x错位不覆盖:type=%s 标签x=%d vs 当前槽cx=%d'
                      '(标签属即将到来的节点,如 boss 前夕「首领」)', _t, _lx or -1,
                      _cur_slot.cx + _x0)
        else:
            _cur_slot.node_type = _t
    return _slots


#: 三票·票A 动态 ROI 半径:当前槽圆心 ±60px 小窗(标签在圆下方行带内,
#: 60px 覆盖圆 + 标签且远小于全行 → 邻槽标签不入窗)。
_VOTE_ROI_HALF: int = 60


def _node_label_in_roi(ctx: SrContext, screen: MatLike,
                       cx: int, cy: int) -> str | None:
    """三票·票A:当前槽圆心 ±``_VOTE_ROI_HALF`` 小窗 OCR → 节点类型 token | None。

    ROI 从检测圆几何推导(cx/cy = 检测圆心 + 行偏移),不写死坐标
    (投资环境会改变节点行布局)。窗口内命中多个关键词时取第一个
    (60px 窗内正常只容一个标签;真混入按噪声,靠多数票纪律兜)。
    """
    results = _ocr(ctx, screen, Rect(cx - _VOTE_ROI_HALF, cy - _VOTE_ROI_HALF,
                                     cx + _VOTE_ROI_HALF, cy + _VOTE_ROI_HALF))
    for r in results:
        for kw, nt in _NODE_TYPE_KEYWORDS.items():
            if kw in r.data:
                return nt
    return None


def node_vote_verdict(table_type: str, votes: dict[str, str | None]) -> str:
    """三票裁决(纯函数可测):'ok' = 无反对;'noise' = 单票异议(不落账);
    'defect' = ≥2 非弃权票一致反对表值(落缺陷台账)。

    噪声纪律:单票反对(如高亮 Hu 对渲染态敏感、ROI OCR 漏读邻字)不落账,
    防逐帧台账刷屏;≥2 张**独立通道**票一致才构成识别错误候选。
    """
    cast = [v for v in votes.values() if v is not None]
    against = [v for v in cast if v != table_type]
    with_t = [v for v in cast if v == table_type]
    if len(against) >= 2 and len(against) >= len(with_t):
        return 'defect'
    if against:
        return 'noise'
    return 'ok'


def verify_node_type_votes(ctx: SrContext, screen: MatLike,
                           plane: int | None, round_num: int | None) -> None:
    """当前节点类型三票校验(**纯记账,零行为**)。

    查表值(session 台账,权威)vs 三张独立票:
    - 票A 动态 ROI 文本 OCR:当前槽圆心 ±60px 小窗(``_node_label_in_roi``);
    - 票B 序列位置推断:已过槽数 p → 表序列第 p 位(应 = 查表值);
      未来图标 Hu 类型对表不符位数一并记进 observed(佐证);
    - 票C 当前槽高亮态图标 Hu 对模板(``cw_node_reader.current_slot_hu_type``)。

    ≥2 张非弃权票一致反对表值 → 落缺陷台账(``cw_telemetry.record_defect``,
    中相关面;复现升 L0 由既有安灯通道承接)。**投资环境变异窗豁免**
    (``ledger.env_grace_until``):窗内节点行合法变异中,不一致是预期而非
    识别错误,不落。同一 (plane, round) 只落一行(逐帧校验每帧跑,去重防刷屏)。
    任何前置不满足(无表值 / 非 clean 帧 / 无当前槽)→ 静默跳过。
    """
    _match = getattr(ctx, 'cw_match', None)
    _sess = getattr(_match, 'session', None)
    if _sess is None:
        return
    ledger = get_node_ledger(_sess)
    if ledger is None:
        return
    table_t = ledger_node_type(_sess, plane, round_num)
    if table_t is None:
        return   # 无表值可校(表缺/该位次未识别)
    if time.monotonic() < ledger.env_grace_until:
        return   # 投资环境变异窗:合法变异中,豁免
    slots, (rx0, ry0, rx1, ry1) = _classify_node_row(ctx, screen)
    if not slots:
        return   # 非 clean 帧(shop 开/过渡),票全弃权
    cur = next((s for s in slots if s.state == 'current'), None)
    if cur is None:
        return
    seq = ledger.seq_by_plane.get(int(plane or 0)) or []
    # 票A:动态 ROI OCR(当前槽圆心 ±60px,几何来自检测圆 + 行偏移)
    vote_a = _node_label_in_roi(ctx, screen, cur.cx + rx0, cur.cy + ry0)
    # 票B:位置推断(已过槽数 p → 表第 p 位应 = 查表值)+ 未来图标 Hu 对表佐证:
    # 第 j 个 upcoming 槽对应表位 past_n+1+j(节点行左→右递进既有先验)。
    past_n = sum(1 for s in slots if s.state == 'past')
    vote_b = seq[past_n] if 0 <= past_n < len(seq) else None
    _upcoming = sorted((s for s in slots if s.state == 'upcoming'), key=lambda s: s.idx)
    _future_bad = sum(
        1 for j, s in enumerate(_upcoming)
        if s.node_type is not None
        and past_n + 1 + j < len(seq)
        and seq[past_n + 1 + j] is not None
        and seq[past_n + 1 + j] != s.node_type)
    # 票C:当前槽高亮态图标 Hu 对模板(行裁图同源,几何来自检测行)
    from sr_od.application.currency_war.obs.cw_node_reader import current_slot_hu_type
    vote_c, hu_dist = current_slot_hu_type(
        screen[ry0:ry1, rx0:rx1], cur, _NODE_TYPE_TEMPLATES or {})
    votes = {'roi_ocr': vote_a, 'position': vote_b, 'cur_hu': vote_c}
    _verdict = node_vote_verdict(table_t, votes)
    _key = f'{plane}:{round_num}'
    if _verdict == 'defect' and _key not in ledger.defect_seen:
        ledger.defect_seen.add(_key)
        log.warning('[cw!][node_votes] 查表=%s vs 三票=%s(past=%d hu_dist=%.2f 未来对表不符=%d)'
                    ' → 落缺陷台账(识别错误候选,复现升 L0)', table_t, votes,
                    past_n, hu_dist, _future_bad)
        try:
            # 分包期 4:落账经 kernel/cw_telemetry_exit 出口钩子位(零直依 telemetry)
            from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                journal_refs,
                record_defect,
            )
            record_defect(
                'node_type', 'perception_conflict',
                expected=f'台账序列[{int(round_num) - 1}]={table_t}(source='
                         f'{ledger.seq_source.get(int(plane or 0))})',
                observed=f'三票={votes}(past_n={past_n}, 高亮Hu距={hu_dist:.2f},'
                         f' 未来图标对表不符位={_future_bad})',
                plane=int(plane or 0), round_num=int(round_num or 0),
                verdict=('留证-≥2 独立票一致反对权威表值(投资环境窗外)=识别错误候选;'
                         '复现升 L0 由安灯通道承接'),
                reader_source='node_ledger_three_vote',
                gap_large=False,
                # refs 旧挂点清理(W7 refs 迁移):decisions 流已退役,
                # 改指 journal (run_id,v) 锚(plane/round 已在行参内联)。
                refs=journal_refs(),
                note='节点类型台账制:表=权威(位面详情采集+投资环境后重读两写点,'
                     '证据=journal 行内嵌 state),'
                     '逐帧三票降为校验;boss 轮次门等语义门不变')
        except Exception:   # noqa: BLE001  观测 best-effort,不阻塞对局
            pass
    elif _verdict == 'noise':
        log.info('[cw][node_votes] 单票异议不落账(噪声纪律):表=%s 票=%s past=%d',
                 table_t, votes, past_n)


def read_plane_detail_difficulty(ctx: SrContext, screen: MatLike) -> int | None:
    """位面详情底部明文「敌人难度 N」→ N | None(**只存参考**)。

    生产难度主源 = 备战旗牌两级管线(``read_enemy_difficulty``,ADR-0449)
    不变;本读法服务位面详情采集时的参考值落账(离线对拍/缺口排查)。
    明文正读(非艺术字)→ 全屏 OCR 按「敌人难度」前缀正则提取,不依赖
    固定坐标(位面详情布局随内容变,正则锚文本比锚坐标稳)。
    """
    try:
        results = ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=None, color_range=None, crop_first=False)
    except Exception:   # noqa: BLE001  best-effort 参考值
        return None
    for r in results:
        m = re.search(r'敌人难度\s*(\d+)', r.data or '')
        if m:
            v = int(m.group(1))
            if 1 <= v <= 999:
                return v
    return None


def read_plane_detail_nodes(ctx: SrContext, screen: MatLike) -> list | None:
    """位面详情画面「节点条」(当前选中位面的全节点预览)→ ``NodeSlot`` 列表 | None。

    与 ``read_node_sequence`` 同一 CV 核心(``classify_node_row``:定圆/判态/
    Hu 类型/boss SIFT),差异只在输入域:
    - 带 = screen_info「货币战争-位面详情」屏的「区域-节点条」area
      (用户权威坐标 385,514,1596,661;2026-08-26 实锺 9 圆全检出,最右
      SIFT boss 巨鹿生物制药=6 断层命中——与备战条同源互证);
    - 该带是**选中位面的彩色渲染态**(位面详情里位面 2/3 也可选中展开,
      非备战的锁灰态)→ **接管局三位面 boss 全量采集通道**:依次点三张
      位面卡,每选中一张调本函数,boss 槽 SIFT 认该位面 boss;
      ⚠️ 选中**过去位面**(位面号 < 会话当前位面)时节点全部变暗(灰态),
      本读法在该渲染下识别可能退化(实机 P2 采位面 1 长停留实证)——
      消费方 CwScreenPlaneIntel 按 ``decide_plane_skip`` 跳过过去位面,
      仅台账缺值时降级补采一次;
    - clean 门同 ``_MIN_CLEAN_CIRCLES``。
    返回 None:模板未加载 / 非该画面 / 圆数不足(坏帧)。
    """
    from sr_od.application.currency_war.obs.cw_node_reader import classify_node_row
    global _NODE_TYPE_TEMPLATES, _BOSS_TEMPLATES
    if _NODE_TYPE_TEMPLATES is None:
        from sr_od.application.currency_war.obs.cw_node_reader import (
            load_node_type_templates,
        )
        _d = get_project_root() / 'assets' / 'game_data' / 'cw_node_types'
        _NODE_TYPE_TEMPLATES = load_node_type_templates(_d) or {}
    if _BOSS_TEMPLATES is None:
        from sr_od.application.currency_war.obs.cw_node_reader import (
            load_boss_templates,
        )
        _bd = get_project_root() / 'assets' / 'template' / 'currency_war' / 'boss_avatar'
        _BOSS_TEMPLATES = load_boss_templates(_bd) if _bd.is_dir() else {}
    if not _NODE_TYPE_TEMPLATES:
        return None
    # 带:位面详情屏的「区域-节点条」(坐标单一源 yml)
    _rect = _area_rect(ctx, '区域-节点条', '货币战争-位面详情')
    if _rect is None:
        return None
    _row = screen[_rect.y1:_rect.y2, _rect.x1:_rect.x2]
    _slots = classify_node_row(_row, _NODE_TYPE_TEMPLATES,
                               boss_templates=_BOSS_TEMPLATES or None)
    if len(_slots) < _MIN_CLEAN_CIRCLES:
        return None
    return _slots


def read_detail_node_type_label(ctx: SrContext, screen: MatLike) -> str | None:
    """位面详情屏 详情条「文本-节点类型名」OCR → 类型名(如 首领节点/奖励节点)| None。

    boss 定位验证锚(迁移审计 w221(git 历史)/ADR-0398):boss 节点有**两种渲染态**——头像态
    (run29 型,大图标 SIFT 可认)与徽章态(run30 型:最右节点=通用金色徽章、
    详情条=「首领节点」+通用描述,本屏无身份信息)。类型名稳定可 OCR
    (run30 实锺「首领节点」全字命中),作「点到的确是 boss 节点」验证 +
    徽章态分流依据(消费方 ``cw_screen_plane_intel.conclude_plane_boss``)。
    读不到 → None(过渡帧/OCR 失败,调用方 retry,勿当徽章态)。
    """
    rect = _area_rect(ctx, '文本-节点类型名', '货币战争-位面详情')
    if rect is None:
        return None
    blob = ''.join(r.data for r in _ocr(ctx, screen, rect))
    t = blob.strip()
    return t or None


def read_xp_progress(ctx: SrContext, screen: MatLike,
                     expected_level: int | None = None) -> tuple[int, int] | None:
    """购买经验进度 ``(cur_xp, xp_to_next_level)``,购买经验按钮下方 "X/Y"(备战字段采集)。

    OCR 购买经验(y848)下方 ~y935 的 "X/Y"(如 "4/20")→ (4, 20)。读不到 / 越界 → None。
    level 升级时机决策用(cur 接近 next → 即将升级,影响 level_plan/买经验优先级)。

    OCR ``文本-升级所需经验`` 的 "X/Y"(如 "4/20")→ (4, 20)。读不到 / 越界 → None。

    :param expected_level: 上下文等级先验(透传 ``_parse_xp_pair`` 的 '1' 拆分
      收紧;None=无先验旧行为。先验来源 = session.last_level_obs)。
    """
    blob = ''.join(r.data for r in _ocr_upscaled(ctx, screen, _area_rect(ctx, '文本-升级所需经验')))
    pair = _parse_xp_pair(blob, expected_level=expected_level)
    if pair is not None:
        cur, nxt = pair
        if 0 <= cur <= nxt <= 100:      # sanity:cur≤next,XP 上限合理(封顶 10 级,每级 XP 个位~十几)
            return cur, nxt
    return None


def _ocr_difficulty_binarized(ctx: SrContext, screen: MatLike, rect: Rect | None,
                              scale: int = 4) -> list:
    """难度旗牌专用预处理 OCR:裁剪 → 放大 → OTSU → 反转 → 徽记 y 分带剔除。

    为什么整链不可省(2026-08-28 58 帧 fixture 离线对拍,产物
    ``.debug/temp/currency_war/w526_difficulty_reader/``):
    - 白色艺术字数字 + 深色纹理旗底 + 顶部徽记贴边,原生直读 0/58;
    - OTSU 把数字从纹理旗底分离;反转成黑字白底(paddle 对白底黑字稳);
    - 徽记在同区域上半(裁片 y<48,像素亲测:徽记占 y 0..45、数字带 y>=55),
      不剔除会被 OCR 混入图形噪声;按 y 分带即可,无需连通域。
    """
    if rect is None:
        return []
    if screen is None:
        # 测试注入态(mock ocr_service,screen 不承载像素;仓内既有约定)→ 不裁剪直接透传
        return ctx.ocr_service.get_ocr_result_list(image=screen, rect=rect, crop_first=False)
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return []
    up = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                    interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - bw
    inv[:_DIFFICULTY_EMBLEM_BAND_Y * scale, :] = 255   # 徽记带抹白(黑字白底)
    return ctx.ocr_service.get_ocr_result_list(image=cv2.cvtColor(inv, cv2.COLOR_GRAY2RGB))


def read_enemy_difficulty(ctx: SrContext, screen: MatLike) -> int | None:
    """当前敌人难度(左上角 ``文本-难度`` 旗牌;boss 血量 ≈ base×1.052^难度,doc 13 §13.7)。

    难度数字是白色艺术字 + 深色纹理旗底,原生直读必失(58 帧对拍 0/58,全是 0/1 类
    垃圾或空)→ 走旗牌专用两级管线(与 ``read_level_up_cost`` 两级形状一致,便于维护;
    本场景二级二值化为主、一级放大为辅):
    1. ``_ocr_difficulty_binarized``(OTSU+反转+徽记剔除,41/41 有旗牌帧全读对);
    2. 读空 → ``_ocr_upscaled``(4x 放大,保底防 OTSU 在异常背景下反转失效)。
    合理带守卫 ``_DIFFICULTY_MIN.._DIFFICULTY_MAX`` 外 → None:根除单帧噪声读数
    (推导见常量注释)。无旗牌帧(补给节点等)区域空白 → 两级皆空 → None(正确语义)。
    """
    rect = _area_rect(ctx, '文本-难度')
    v = _first_int([r.data for r in _ocr_difficulty_binarized(ctx, screen, rect)])
    if v is None:
        v = _first_int([r.data for r in _ocr_upscaled(ctx, screen, rect, scale=4)])
    if v is not None and _DIFFICULTY_MIN <= v <= _DIFFICULTY_MAX:
        return v
    return None


def read_level_up_cost(ctx: SrContext, screen: MatLike) -> int | None:
    """买一次经验的花费(``文本-购买经验金币数``;替代 ``LEVEL_UP_COST_TABLE`` 估,doc 13 §13.2C)。

    费用数字与 XP/等级同属备战屏原生分辨率下 paddle det 漏检的小字目标——画面档
    ``docs/game/screens/currency_war_prep.md``「不可行」结论系放大手法引入前所下。
    58 张备战 fixture 离线对拍:3x 放大读 55/58 → 加 OTSU 二值化二级重试 57/58;
    唯一残留帧数字在场但两级均未检出,走 None 兜底。
    两级管线:``_ocr_upscaled`` 读空 → ``_ocr_upscaled_binarized`` 重试。
    读不到 → None(plan 用 ``LEVEL_UP_COST_TABLE`` 兜底)。
    """
    rect = _area_rect(ctx, '文本-购买经验金币数')
    v = _first_int([r.data for r in _ocr_upscaled(ctx, screen, rect)])
    if v is None:
        v = _first_int([r.data for r in _ocr_upscaled_binarized(ctx, screen, rect)])
    if v is not None and 0 <= v <= 20:
        return v
    return None


def _parse_coin_fee_digit(texts: list[str]) -> int | None:
    """刷价 rect 文本 → int(字段先验:rect 内恒为 金币图标+一位费用数字)。

    金币图标被 OCR 系统性并入前缀(实测 'GO'/'G0'/'G2',G=图标):先归一大写、
    把残留的字母 O 映射成 0(图标旁数字 0 的形变),再取首个整数。
    无数字(两级管线全空)→ None。
    """
    for t in texts:
        m = re.search(r'\d+', (t or '').upper().replace('O', '0'))
        if m:
            return int(m.group())
    return None


def read_shop_refresh_cost(ctx: SrContext, screen: MatLike) -> int | None:
    """商店面板「↻ N」徽标读数(``文本-刷新金币数`` rect)——**非刷价,仅旁证**。

    `w577_refresh_fee_and_andon/` 定谳(ADR-0456):rect 内容 = 商店折叠面板徽标,数值 = min(gold//10,5)
    (= 利息公式),与实付刷新费无关——多局干净对账实付恒 2(基价
    ``cw_state.REFRESH_COST_BASE``)而徽标随金位变。本函数保留作旁证/测试用,
    已退出 ``read_game_state`` 主链(决策热路径少一次 OCR)。

    实现维持 `w559_p0p1_fix/` 后的放大两级管线与 0..10 守卫;两级读空 → None。
    """
    rect = _area_rect(ctx, '文本-刷新金币数')
    v = _parse_coin_fee_digit([r.data for r in _ocr_upscaled(ctx, screen, rect)])
    if v is None:
        v = _parse_coin_fee_digit([r.data for r in _ocr_upscaled_binarized(ctx, screen, rect)])
    if v is not None and 0 <= v <= 10:
        return v
    return None


def read_streak(ctx: SrContext, screen: MatLike) -> int | None:
    """连胜/连败数(``文本-连胜数``;**正负语义待核**(正=连胜?),现读 magnitude;None=未读到)。

    放大读(与同屏小字字段同管线;native 直读在渲染变异帧失读实证:rect 内
    数字清晰但 det 漏检,3x 放大可读)。
    """
    v = _first_int([r.data for r in _ocr_upscaled(ctx, screen, _area_rect(ctx, '文本-连胜数'))])
    if v is not None and 0 <= v <= 20:      # magnitude(符号待核);连胜/连败一般 ≤20
        return v
    return None


# 难度确认屏 reader(开局读本局职级;非备战屏,放本模块集中 OCR readers)
_DIFFICULTY_CONFIRM_SCREEN: str = '货币战争-难度确认'


def parse_selected_difficulty(texts: list[str]) -> str:
    """难度确认屏 OCR 文字 → 本局职级(``A\\d+(-\\d+)?``,如 A8 / A5 / A8-1..A8-50)。

    正则 + 全匹配过滤非职级文字(财富造物主 / 当前职级难度效果 等)。纯函数可单测。
    无匹配 → ""(``effective_hp_threshold`` 回退默认阈值,行为不变;cw_state:253)。
    """
    for t in texts:
        m = re.fullmatch(r'A(\d+)(?:-(\d+))?', t.strip())
        if m:
            return t.strip()
    return ''


def read_selected_difficulty(ctx: SrContext, screen: MatLike) -> str:
    """难度确认屏 → 本局职级(``标识-当前难度职级`` area OCR → parse)。

    AX label 在画面左上(x~87,y~305,紧邻「财富造物主」)。A8 高难 → ``effective_hp_threshold``
    保血阈值调高(D-32;单一源 = cw_state.DIFFICULTY_HP_TABLE 代码常量)。读不到 → ""(回退默认)。
    接线已通(3.5.1,d841d1a1):CwEntryStart 难度确认段调本函数 → ctx.cw_selected_difficulty
    → cw_loop copy session → 策略层填 state → effective_hp_threshold D-32 激活。
    """
    rect = _area_rect(ctx, '标识-当前难度职级', _DIFFICULTY_CONFIRM_SCREEN)
    texts = [r.data for r in _ocr(ctx, screen, rect)]
    return parse_selected_difficulty(texts)


# last-known-good (plane, round):plane 单调递增、round 同位面内递增;过渡帧 OCR 失败时
# 返回上次成功值,避免 fallback (1,1) 误导 level_plan/支出 gate(2026-08-04 实跑发现:
# plane=4 lv=9 后过渡帧读成 plane=1 lv=4 兜底)。跨局由 reset_phase_round_cache 清空。
_last_phase_round: tuple[int, int] | None = None

#: 回退修正确认态({'value': (plane, round), 'count': n});语义见 read_phase_round
#: 回退分支注释。reset_phase_round_cache 随 last-known-good 一并清(防跨局复用)。
_phase_round_suspect: dict | None = None
#: 回退修正确认帧数。依据:hp 下行复现确认(HP_SUSPECT_CONFIRM_FRAMES=2)与
#: star 回退防抖「连续 2 次」同族先例;复现压单帧噪声。
_PHASE_ROUND_CONFIRM_FRAMES: int = 2


def reset_phase_round_cache() -> None:
    """新对局开始时清空 last-known-good(防跨局复用上局 plane/round)。"""
    global _last_phase_round, _phase_round_suspect
    _last_phase_round = None
    _phase_round_suspect = None


def read_phase_round(ctx: SrContext, screen: MatLike) -> tuple[int, int]:
    """位面 + 轮次(顶栏「X-Y」= 位面-轮次,如 "1-3" = 位面1 第3轮)。

    :return: (plane, round_num)。读不到 → 返回上次成功值(过渡帧兜底);无历史 → (1, 1)。

    单调守卫(审计 P0,2026-08-16,M38 同款毒化面):plane 局内单调递增、round 同位面内递增,
    读到**倒退值**(如 plane3 → plane2)= OCR 假阳 → 保旧 + obs_conflict 留证(毒化面:
    level_plan/支出 gate/P2P3 概率表/_expected_level 兜底全歪)。

    数字 fallback 分支已停用(w891 延迟审计候选③):该分支唯一合法产出 (1,1) 与
    无历史兜底返回值完全重合,结构上不可能改变任何返回值;近两日 868 次被拒全为
    纯浪费的 OCR 判读(被拒数字是 A8 难度/Lv 泄漏的错源,不是可修复的形变真值,
    上下文规则修复无对象)→ 整段删除即治本。blob 无 X-Y/第X位面 匹配 → 直接走
    last-known-good/(1,1) 兜底。值域守卫(source=ocr_range)不属 fallback,是
    M70 假 win 防毒化守卫,保留。
    """
    global _last_phase_round
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    m = re.search(r'(\d)\s*-\s*(\d)', blob)          # "1-3"
    if m:
        new = (int(m.group(1)), int(m.group(2)))
    else:
        plane_m = re.search(r'第\s*(\d)\s*位面', blob)
        new = (int(plane_m.group(1)), int(plane_m.group(1))) if plane_m else None
    if new is not None:
        # ⚠️ 值域守卫(2026-08-17 M70 假 win 根因):plane 只有 1-3,读出 8(恢复对局时顶栏被
        # overlay 遮,OCR 抓到 A8 难度/Lv.8 的"8")→ last_state.plane=8 → 局终判定 8>=3 →
        # 假 win 假通关。值域外 = OCR 假阳,当 miss 处理(走 last-known/兜底),不进缓存。
        if not (1 <= new[0] <= 3 and 1 <= new[1] <= 9):
            obs_conflict('phase_round', _last_phase_round, new, screen,
                         verdict='拒-值域外(plane∈1-3/round≤9,OCR抓错源如A8难度)', source='ocr_range')
            new = None
    if new is not None:
        if _last_phase_round is not None and (new[0] < _last_phase_round[0]
                                              or (new[0] == _last_phase_round[0] and new[1] < _last_phase_round[1])):
            # 回退修正确认通道(分诊 F 根修):单调守卫只锁「非机制性跳变」
            #(单帧倒退=OCR 噪声),不锁「修正」——前帧错读过守卫被缓存后,
            # 真值每帧被拒 = 错读固化(分诊 §2:9/10 冲突帧同 [x,6]→[x,5] 模式)。
            # 判据:连续 _PHASE_ROUND_CONFIRM_FRAMES 帧读到**同一**倒退值才采新
            #(依据:hp 下行复现确认 HP_SUSPECT_CONFIRM_FRAMES=2 与 star 回退
            # 防抖「连续 2 次」同族先例;复现压单帧噪声)。前进/正常读自愈清挂起。
            global _phase_round_suspect
            sus = _phase_round_suspect
            if sus is not None and sus.get('value') == new:
                sus['count'] = int(sus.get('count', 0)) + 1
            else:
                sus = {'value': new, 'count': 1}
                _phase_round_suspect = sus
            if sus['count'] >= _PHASE_ROUND_CONFIRM_FRAMES:
                obs_conflict('phase_round', _last_phase_round, new, screen,
                             verdict='采新-回退修正确认(连续2帧同值倒退,前值疑错读固化)',
                             source='ocr')
                _last_phase_round = new
                _phase_round_suspect = None
                return _last_phase_round
            obs_conflict('phase_round', _last_phase_round, new, screen,
                         verdict='保旧-回退防抖(单帧倒退疑OCR噪声,连续2帧同值才修正)',
                         source='ocr')
            return _last_phase_round
        _phase_round_suspect = None   # 倒退消失(前进/正常读)→ 挂起自愈
        _last_phase_round = new
        return _last_phase_round
    # OCR 失败(过渡帧/错源单数字)→ 返回上次成功值,避免 (1,1) 误导 level_plan
    if _last_phase_round is not None:
        return _last_phase_round
    return 1, 1


#: 连通域字形几何阈值(1080p「区域-部署数」裁片,58 帧 fixture 连通域亲测,
#: 产物 ``.debug/temp/currency_war/w529_xy_reader_impl/``):
#: 数字与斜杠字形连通域全高 h≥45;人形图标两块(头 h≈19 + 身 h≈39)恒低于线,
#: 据此剔图标 —— 实验证明图标/数字起点逐帧漂移,固定偏移蒙版不可用([0:55] 条带
#: 在 0/3 帧切掉 '0' 左缘),形状过滤是唯一可靠面。
_PADDLE_GLYPH_MIN_H: int = 45
#: 斜杠判别:细长斜笔画连通域面积 < 450,数字(含 '1')实心面积 ≥550
#: (斜杠实测 356-370,'1' 实测 ~550,'7' ~640,'8' ~1060)。
_PADDLE_SLASH_MAX_AREA: int = 450


def _paddle_glyph_strip(crop: MatLike) -> list[tuple[int, int, int, int]]:
    """「X/Y」裁片二值化 → 连通域字形清单(剔图标/噪声)。

    返回按 x 排序的 ``[(x, w, h, area), ...]``(裁片内坐标,数字+斜杠字形)。
    OTSU 极性取「白像素少数派」为前景(数字浅色平底,占比恒小);h<``_PADDLE_GLYPH_MIN_H``
    的连通域(图标头/身、overlay 小字、噪点)剔除。
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() > 127:                     # 前景恒为少数派(字形面积 << 底)
        bw = 255 - bw
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    glyphs = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        if area < 30 or h < _PADDLE_GLYPH_MIN_H:
            continue
        glyphs.append((x, w, h, area))
    glyphs.sort()
    return glyphs


def _paddle_binary_stripped(crop: MatLike) -> MatLike:
    """「X/Y」裁片 → OTSU 二值化 + 图标/噪声抹白(黑字白底,二级重 OCR 用)。

    与 ``_paddle_glyph_strip`` 同一套几何阈值;抹白对象 = h<``_PADDLE_GLYPH_MIN_H``
    或面积 <30 的连通域(人形图标头/身、overlay 小字、噪点),数字/斜杠字形保留。
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() > 127:                         # 前景恒为少数派
        bw = 255 - bw
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    for i in range(1, n):
        x, _, _, h, area = (int(v) for v in stats[i])
        if area < 30 or h < _PADDLE_GLYPH_MIN_H:
            bw[labels == i] = 255
    return bw


def _resolve_paddle_digits(text_digits: str, glyph_digit_n: int, slash_idx: int | None,
                           level: int | None,
                           text_has_slash: bool = False) -> tuple[int | None, int | None,
                                                                  list[tuple[int, int, bool]]]:
    """位置感知解析核心(纯逻辑,可构造测试)。

    ``text_digits``:OCR 框文本里的数字串(斜杠可能被读成数字,图标可能贡献前缀数字);
    ``glyph_digit_n``:连通域数字字形个数(几何真值,图标已剔除);
    ``slash_idx``:数字字形序列中斜杠的下标(None=斜杠字形未识别,走候选拆分);
    ``text_has_slash``:OCR 文本里是否出现 '/'(斜杠读对时才为 True);
    ``level``:当前等级(提供时约束 y≥level)。

    返回 ``(x, y, candidates)``。对齐候选(出处=58 帧逐框 OCR + 二值化抹图标重 OCR
    实测,见 ``_read_deploy_paddle``):
    - **直接对齐**:文本数字数 == 字形数 → 按「斜杠前=x、后=y」切(direct=True);
    - **去首对齐**:文本多 1 个数字 = 左侧图标被 rec 读成 '1' 并进数字
      (迁移审计 w287(git 历史)/a8 实证 '10/3'=0/3)或空心字形(0/6/8)被 rec 加幻影前缀 '1'
      (抹图标后仍现 '16/7'=6/7 实证,非图标独有)→ 去首个再切;
    - **去斜杠位对齐**:文本无 '/' 且多 1 个数字 = 斜杠被读成数字
      ('717'=7/7 实证)→ 去掉斜杠位置上的那个数字再切。
    全部候选过 ``_validate_paddle_xy`` 约束验证;裁决:有 direct 候选取 direct
    (唯一),否则候选唯一才采,多候选歧义 → (None, None, 候选清单) 交调用方留证。
    """
    x_n: int | None = None if slash_idx is None else slash_idx
    y_n: int | None = None if x_n is None else glyph_digit_n - x_n
    cands: list[tuple[int, int, bool]] = []

    def _try(drop_idx: int | None, direct: bool) -> None:
        """按「去掉文本数字串中 drop_idx 处字符(None=不去) + 斜杠位切分」生成并验证候选。"""
        if x_n is None or y_n is None or y_n <= 0:
            return
        seg = text_digits if drop_idx is None else \
            text_digits[:drop_idx] + text_digits[drop_idx + 1:]
        if len(seg) != x_n + y_n or len(seg[:x_n]) == 0:
            return
        x, y = int(seg[:x_n]), int(seg[x_n:])
        if _validate_paddle_xy(x, y, level):
            if (x, y, direct) not in cands:
                cands.append((x, y, direct))

    if slash_idx is not None:
        _try(None, True)                        # 直接对齐
        _try(0, False)                          # 去首(图标/幻影前缀)
        if not text_has_slash:
            _try(slash_idx, False)              # 去斜杠位(斜杠被读成数字)
    else:
        # 斜杠字形未识别:按数字字形拆分点枚举(约束唯一才采)
        for cut in range(1, glyph_digit_n):
            x_s, y_s = text_digits[:cut], text_digits[cut:]
            if len(y_s) == glyph_digit_n - cut and x_s:
                x, y = int(x_s), int(y_s)
                if _validate_paddle_xy(x, y, level):
                    cands.append((x, y, False))

    directs = [c for c in cands if c[2]]
    if len(directs) == 1:
        return directs[0][0], directs[0][1], cands
    distinct = {(c[0], c[1]) for c in cands}
    if len(distinct) == 1:
        x, y = distinct.pop()
        return x, y, cands
    return None, None, cands


def _validate_paddle_xy(x: int, y: int, level: int | None) -> bool:
    """「X/Y」语义约束验证器(玩法先验,用户口述权威):x≤y;1≤y≤13(前台 4+后台 9);
    y≥level(cap=level+宝钻,宝钻只增不减;level 未提供时跳过该条)。
    """
    return 0 <= x <= y and 1 <= y <= 13 and (level is None or y >= level)


def _parse_paddle_positional(crop: MatLike, ocr_results: list, level: int | None,
                             screen: MatLike | None) -> tuple[int | None, int | None]:
    """单次 OCR 结果 → 位置感知解析(与 ``_read_deploy_paddle`` 守卫分层:本函数只管解析)。

    流程:连通域字形(剔图标)→ 斜杠=细长字形 → OCR 文本数字串对齐字形 → 约束验证。
    全部失败 → (None, None);唯一候选歧义/约束拒绝时 obs_conflict 留证(证据行节流由
    obs_conflict 自带)。``screen`` 供留证截图(None=纯解析,不留证)。
    """
    glyphs = _paddle_glyph_strip(crop)
    if not glyphs:
        return None, None
    blob = ''.join(r.data for r in ocr_results)
    text_digits = re.sub(r'\D', '', blob)
    if not text_digits:
        return None, None
    slash_idx: int | None = None
    digit_n = 0
    for _, _, _h, area in glyphs:           # glyphs 已按 x 排序
        if area < _PADDLE_SLASH_MAX_AREA:
            if slash_idx is None:
                slash_idx = digit_n         # 只认首个细长字形为斜杠
        else:
            digit_n += 1
    x, y, cands = _resolve_paddle_digits(text_digits, digit_n, slash_idx, level,
                                         text_has_slash='/' in blob)
    if x is not None:
        return x, y
    # level 先验修正通道(分诊 C 根修;帧证据 obs_conflict_deploy_paddle__d9f64136:
    # 画面 4/4、字形干净,level 先验 ≥5 时 y≥level 把唯一合法候选拒空)。level 来自
    # 三源解析(自身可误读/毒化),不该让间接先验一票否决直接几何读——全部候选仅
    # 因 y≥level 被拒时,用绝对域(x≤y,1≤y≤13)重解析一次,采回 + 留证(cap 侧
    # 与 level 的一致性由 _debounce_cap 双帧通道终审,判据同 ADR-0420)。
    if level is not None:
        x, y, cands = _resolve_paddle_digits(text_digits, digit_n, slash_idx, None,
                                             text_has_slash='/' in blob)
        if x is not None:
            if screen is not None:
                obs_conflict('deploy_paddle', None, {'text': blob, 'candidates': cands},
                             screen, verdict=('采-y<level(唯一合法候选被 level 先验拒;'
                                              '对照 level 疑毒化,修正不锁,cap 侧双帧终审)'),
                             source='paddle_positional')
            return x, y
    if screen is not None:
        obs_conflict('deploy_paddle', None, {'text': blob, 'candidates': cands},
                     screen, verdict=('拒-位置感知解析约束不过(斜杠丢失/图标混入后'
                                      '候选歧义或语义域外;详见 candidates)'),
                     source='paddle_positional')
    return None, None


def _read_deploy_paddle(ctx: SrContext, screen: MatLike,
                        level: int | None = None) -> tuple[int | None, int | None]:
    """舞台上方中央「X/Y」指示 → (X 已部署角色数, Y deploy cap);读不到 → (None, None)。

    **两级管线 + 位置感知解析**(ADR-0450;替换旧「整串拼接 + 正则」解析层;旧层死穴:
    "/" 被 OCR 读成数字时拼接串成纯数字正则全崩,及左侧人形图标被并入致 X 虚高
    如 "0/3"→"10/3")。守卫层(前缀剥离/域守卫/``read_deploy_cap_debounced``)
    全保留,作为解析之上的第二层继续生效。

    1. 原生 OCR 裁片(不放大,D-53 同旧)→ ``_parse_paddle_positional``:连通域
       字形按位置使用 —— h≥``_PADDLE_GLYPH_MIN_H`` 留数字/斜杠字形(剔逐帧漂移的
       人形图标),细长字形判斜杠,OCR 文本数字串按「斜杠前后」对齐,
       ``_validate_paddle_xy`` 语义约束(x≤y、y≤13、y≥level)终审;
    2. 一级无数字框/解析失败 → ``_paddle_glyph_strip`` 二值化抹图标后重 OCR 再解析
       (与 ``read_enemy_difficulty`` 两级形状一致;实拍斜杠变异 '717'=7/7、
       图标前缀 '10/3'=0/3 一级即可解,二级防原生 det 整体漏检)。

    **cap = level + 宝钻数**(D-53 实测核正):无加成时 deploy cap = 团队等级
    (5 fixture 跨 lv3/4/5/7 核:Y 恒=level)。财富宝钻 +1 团队槽且**可叠加**——
    官方效果原文「拥有宝钻可以使团队规模上限+1,无论是否被角色穿戴」
    (cw_equipment_data)= 按拥有计数非按穿戴(局38 r2 实证 cap5/lv3=两宝钻)。
    ⚠️ 旧注「cap≠level(lv4-5 3/3、lv6 5/5)」自主推进期错数据,已废;旧「+1 封顶」
    假设同废(叠加无上界,消费端域检查见 cw_screen_prep 审计#15 已反转)。

    零重帧原则:解析失败只返 (None, None) 并留证,不在解析层重截帧;
    重帧仍归 ``read_deploy_cap_debounced`` 的域外防抖(瞬时误读须跨帧才能识别,
    同帧源不可替代)。

    保留裁剪读(2026-08-24 crop-first 审计):X/Y 指示同 ``_board_pairs`` 的全屏密度问题;
    裁切(padding 给足)是稳读前提。
    """
    rect = _area_rect(ctx, '区域-部署数')
    if rect is None:
        return None, None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None, None
    results = ctx.ocr_service.get_ocr_result_list(image=crop)
    x, y = _parse_paddle_positional(crop, results, level, screen)
    if x is not None:
        return x, y
    # 一级解析失败(原生 det 漏检/斜杠读成数字后候选歧义)→ 二值化抹图标后重 OCR:
    # 图标移除后 rec 对「斜杠 + 数字」还原率显著提升(58 帧实测 '717'→'7/7'),同帧
    # 源内重试,不重截帧。
    results2 = ctx.ocr_service.get_ocr_result_list(
        image=cv2.cvtColor(_paddle_binary_stripped(crop), cv2.COLOR_GRAY2RGB))
    return _parse_paddle_positional(crop, results2, level, screen)


def read_deployed_count(ctx: SrContext, screen: MatLike) -> int | None:
    """舞台上方中央「X/Y」指示 → X(已部署角色数);读不到 → None。

    CwOpDeploy 用它定位**空位**:d(cap_remaining)+ e(offset)依赖它;读不到 → fallback
    → 部分 churn。实现见 ``_read_deploy_paddle``(同时给 cap Y,见 ``read_deploy_cap``)。
    """
    return _read_deploy_paddle(ctx, screen)[0]


def read_deploy_cap(ctx: SrContext, screen: MatLike,
                    level: int | None = None) -> int | None:
    """舞台上方中央「X/Y」指示 → Y(deploy cap 真值);读不到 → None(调用方退 level 估)。

    实机 **cap=level+宝钻数**(D-53 实测核正:无加成时 5 fixture 跨 lv3/4/5/7,Y 恒=level)。
    财富宝钻 +1 团队槽且**可叠加**(官方「拥有即+1 无论穿戴」,局38 r2 实证 cap5/lv3;
    详见 ``_read_deploy_paddle`` docstring)。
    CwOpDeploy 应用本 Y 非 level 估 cap_remaining。读不到 → 退 level 估(fallback;cap=level 故 fallback 仍准)。
    旧注「cap≠level(lv4-5 3/3、lv6 5/5)」自主推进期错数据,已废。reader 实现细节/根因见 ``_read_deploy_paddle``。
    ``level`` 提供时参与解析层约束验证(y≥level,cap 只增不减),不改变返回契约。
    """
    return _read_deploy_paddle(ctx, screen, level)[1]


# cap 真值防抖门(ADR-0286,迁移审计批 F5 前置):cap 与 level 的合法域 = level ≤ cap ≤ level+2
# (宝钻可叠加;cap<level 不可能——唯一合法 diff=−1 形态是诅咒泽尔里奇
# −1 cap,未见实例,先按域拒)。|cap−level|>2 或 cap<level = paddle 误读族(ADR-0281
# 15 行 old=5/6→new=3/4 实测),直接进决策 = 把读错抬到决策层 → 重读一帧再核,仍异拒信。
# 迁移审计 w292(git 历史) 修订(ADR-0420):diff>2 **不再是绝对禁区**——迁移审计 w285(git 历史) #41 实拍帧
# obs_conflict_deploy_cap_out_of_range__e4972b43(2-2,paddle 12/13 + 经验面板
# Lv.8/2-72 双读数实锤 + 后台 9 格实画)= diff=5 真实高档,旧域把它拒信 →
# resolve_back_slots diff=0 退 6 槽基线在 9 格板上跑 = 迁移审计 w285(git 历史) 指认的「6 槽降级
# 错误兜底」。现:域外值重读一帧,**两帧一致且在绝对板面上界内 → 采信**(瞬时
# 误读族仍被「重读不等」拦住——12槽误档事故 8a56db39 是单帧读数,无两帧一致
# 实证);留证不消失(采信也留,判读可见)。cap<level 同走双帧一致通道
# (对照 level 先验疑毒化分支,见 _debounce_cap 注)。
DEPLOY_CAP_MAX_DIFF: int = 2
#: cap 绝对板面上界(实拍上限:前台 4 + 后台 9 = 13,e4972b43;超界即使两帧
#: 一致也拒——OCR 结构性误读如「8/8→12」级别前缀噪声可能跨帧复现)
DEPLOY_CAP_ABS_MAX: int = 13


def _debounce_cap(ctx: SrContext, screen: MatLike, cap: int | None,
                  level: int) -> int | None:
    """cap 真值防抖门核(ADR-0286/ADR-0420;首读值已得时复用,避免重跑整条
    paddle 管线——``read_deploy_cap_debounced`` 与 ``resolve_paddle_pair``
    共用本核,防抖语义单一源)。域/守卫/留证语义与原实现逐行一致。"""
    if cap is None or level <= 0:
        return cap
    if level <= cap <= level + DEPLOY_CAP_MAX_DIFF:
        return cap
    cap2 = None
    try:
        screen2 = ctx.controller.screenshot()
        cap2 = read_deploy_cap(ctx, screen2)
    except Exception:   # noqa: BLE001  重读帧不可得(控制器异常)按未读到处理
        cap2 = None
    if cap2 is not None and level <= cap2 <= level + DEPLOY_CAP_MAX_DIFF:
        return cap2
    if (cap2 is not None and cap2 == cap
            and 1 <= cap2 <= DEPLOY_CAP_ABS_MAX):
        # 域外双帧一致采信(上下两向同判据,ADR-0420 判据镜像):瞬时误读被
        # 「两帧一致」概率压住;留证让判读侧可见本次采信,复现异常高频则回头收紧。
        # 下向(cap<level)不再恒拒——域判据的对照集 level 自身可误读/毒化
        #(帧证据 obs_conflict_deploy_paddle__d9f64136:画面 4/4、level 先验 5,
        # 旧恒拒把真值锁死;cap=level+宝钻机制里 cap<level 的唯一现实来源就是
        # level 读错,采真值比拒信退 level 兜底更接近画面事实)。
        obs_conflict('deploy_cap_domain', cap, cap2, screen,
                     verdict=('采信-域外双帧一致('
                              + ('cap<level:对照 level 先验疑毒化' if cap2 < level
                                 else '真实高档,迁移审计 w292(git 历史)/ADR-0420:e4972b43 实拍 diff=5 真档')
                              + ';本行供判读核对 paddle X/Y 与经验面板等级;'
                                '复现高频则回查读链)'),
                     source='paddle_cap_debounce')
        return cap2
    obs_conflict('deploy_cap_domain', cap, cap2, screen,
                 verdict=('拒信-域外(cap<level 不可能/|cap−level|>2 且重读'
                          '不一致或超绝对上界 13;重读一帧仍异 → None,决策'
                          '兜底 level;复现 ≥3 次排查 read_deploy_cap/level 读链'),
                 source='paddle_cap_debounce')
    return None


def read_deploy_cap_debounced(ctx: SrContext, screen: MatLike,
                              level: int) -> int | None:
    """cap 真值防抖读(ADR-0286,与 r414 域判定同族):域外值重读一帧,仍域外 → None 拒信。

    域 = ``level ≤ cap ≤ level + DEPLOY_CAP_MAX_DIFF``;域外时独立再截一帧重读:
    重读入域 → 采重读值;**重读与首读一致且 level ≤ cap ≤ DEPLOY_CAP_ABS_MAX
    → 采信(域外双帧一致,真实高档 迁移审计 w292(git 历史)/ADR-0420,e4972b43 diff=5 实拍)**
    + obs_conflict 留证;其余(重读仍域外且不一致/cap<level/超绝对上界)→
    留证 + None(调用方 max_units 兜底 level,与「未读到」同态)。
    截图失败(异常)按重读不可得处理。防抖核=``_debounce_cap``(单一源)。
    """
    cap = read_deploy_cap(ctx, screen, level)
    return _debounce_cap(ctx, screen, cap, level)


def arbitrate_deployed_count(paddle_n: int | None,
                             cv_n: int | None) -> tuple[int | None, bool]:
    """deployed 计数双源仲裁(纯函数)→ (采信值, 是否结构性分歧)。

    两源:``paddle_n`` = 舞台上方「X/Y」指示的 X(``read_deployed_count``,
    游戏自带计数器,构造上即真值);``cv_n`` = CV 槽位占用实测
    (front+back ``slot_occupied`` 计数,像素推断,特效/布局档错位可虚高)。

    **规则(无新阈值;两条依据)**:
    1. 两源都可读 → **取低值 min**(fail-closed 向「板未满」侧)。依据 =
       代价不对称(本仓既有 r60/r64 取舍口径):计数偏高 → 「板满」假判 →
       合法化 no-op → 零推进死锁(实证:备战环 CV 幻影占用合法化 no-op 的
       实机停机局,``deployed_count_2src`` 留证三连);计数偏低 →
       多试一次拖拽被游戏拒(源槽弹回,廉价可观测)。取 min 恒落在廉价侧,
       单调规则不依赖任何拍定分界。
    2. 分歧告警带沿用既有留证判据 |paddle−cv|>1(spread≤1 属两源合法
       读数差:CV 采样边沿/动画残影,单帧 ±1 不行动);>1 = 结构性分歧,
       调用方须留证 + 记 ``telemetry.defects.DEFECT_KIND_DEPLOYED_COUNT_2SRC``
       分键(防静默;不一致率按该 kind 计数)。

    **单源缺席(显式申报的退化语义;注意与主方向相反)**:
    一源缺失时无仲裁语义,返另一源——**paddle 缺席时退化 = 按 CV 行动 =
    向「板满」侧 fail**(与 min 的廉价方向相反;两害相权:此帧改「放行」
    会把「真板满 ∧ OCR 抖动」变成白拖耗环)。调用方契约:paddle 缺席帧
    **必须**先重读一帧(stylized 数字 det 单帧间歇漏在案)仍失读才接受
    退化,且**必须**记 ``DEPLOYED_COUNT_2SRC`` 分键申报(不得静默)。
    双缺席 → (None, False)。

    **注册面迁移(15 号稿批 A)**:裁决内核已迁
    ``cw_arbitration.combine_deployed_count``(注册键 ``deployed_count``,
    计数类);本函数保留签名与 docstring 作既有消费面单一入口,内核转调,
    前后行为逐字节等价(T-2 对拍锁)。
    """
    from sr_od.application.currency_war.obs.cw_arbitration import (
        combine_deployed_count,
    )
    return combine_deployed_count(paddle_x=paddle_n, cv_occupied=cv_n)


def resolve_paddle_pair(ctx: SrContext, screen: MatLike,
                        level: int) -> tuple[int | None, int | None]:
    """「X/Y」指示**单读** → (deployed_count X, deploy_cap Y)。

    背景(ADR-0462):read_game_state 现行链对同一指示跑两条完整 paddle
    管线(read_deploy_cap_debounced + read_deployed_count),fixture 实测
    42-182ms×2/帧;本函数一次解析产出两值,cap 过同一防抖核
    (``_debounce_cap``),语义与逐个读等价(仅省一次重复识别)。
    阶段 gate 路径用本函数;phase=None 全量路径保持两读不变(零行为变更基线)。
    """
    x, cap = _read_deploy_paddle(ctx, screen, level)
    return x, _debounce_cap(ctx, screen, cap, level)


#: 徽标列右界(1080p):阵营图标旁计数徽标 x≈66-102,名称列/档位链 x≥104
#(证据帧 obs_conflict_board__f1173e2d 离线 OCR 实测:徽标"3"@x=73,链"2/4/6"@x=107)。
_BOARD_BADGE_X_MAX = 104


def _board_rescue_xy(faction: str, data: str, max_count: int) -> tuple[int, int] | None:
    """斜杠丢失容错:OCR 把 "X/Y" 的 '/' 误读丢/误读成 '1'("2/3"→"213"、"2/4"→"24")时还原 (X, Y)。

    还原方式 = 原串直拆 + 删一个 '1' 后拆两数,X∈[1,max_count] 且 Y 必须是该阵营
    注册表 tiers 中的某个更高激活档(Y∈tiers 是防裸数字/档位链误配的硬校验;
    档位链如持续伤害 "2/4/6"→"21416"/"246" 拆不出合法对 → 自然拒绝)。
    """
    if not data.isdigit() or len(data) < 2:
        return None
    tiers = FACTIONS[faction].tiers if faction in FACTIONS else ()
    candidates = [data] + [data[:i] + data[i + 1:] for i, ch in enumerate(data) if ch == '1']
    for trimmed in candidates:
        for k in range(1, len(trimmed)):
            a, b = trimmed[:k], trimmed[k:]
            if not (a.isdigit() and b.isdigit()):
                continue
            x, y = int(a), int(b)
            if 1 <= x <= max_count and y in tiers and y > x:
                return x, y
    return None


def _read_badge_cell(ctx: SrContext, screen: MatLike | None, row_y: float) -> int | None:
    """单个阵营行的徽标小格放大重读 → count;失读 → None。

    第四级兜底:整面板原生分辨率 OCR 常漏读小徽标(证据帧 3db91784:持续伤害
    徽标"3"整体失读,仅档位链 "21416" 可读)。徽标几何 = 名称行下方固定偏移
    (f1173e2d 实测:徽标框 y≈名称行+21..+48、x≈66-108,白字深色圆底)。
    小格裁切 + 3x 放大复用 ``_ocr_upscaled`` 的 det 天花板手法(3db91784 实帧
    对拍:3x 读 '3' conf=1.0);3x 空读再试 5x。纯数字 1-12 之外按失读处理。
    screen=None(测试注入态,无像素)→ None。
    """
    if screen is None:
        return None
    cell = Rect(66, int(row_y) + 10, 108, int(row_y) + 58)
    for scale in (3, 5):
        for r in _ocr_upscaled(ctx, screen, cell, scale=scale):
            data = (r.data or '').strip()
            if data.isdigit():
                v = int(data)
                if 1 <= v <= 12:
                    return v
    return None


def _board_pairs(ctx: SrContext, screen: MatLike, max_count: int = 9,
                 expected: dict[str, int] | None = None) -> tuple[dict[str, tuple[int, int]], bool]:
    """OCR 左面板 → ({阵营: (count, next_tier)}, honest)。

    聚焦裁切 OCR 才稳读 "X/Y"(全屏把 "2/3" 误读 "213"→ 旧 read_board 显脆,实为全屏密度问题;
    区域裁切可读对)。next_tier 未解析到 → 记 0(未知,read_board_next_tier 滤掉)。

    count 优先级(board 计数系统性低估修复,DD-021;证据帧 obs_conflict_board__f1173e2d/
    3db91784/86ce9fd1:徽标"3"+链"2/4/6" 被旧链读成 1~2、"2/3" 斜杠丢失读成 1):
    ① 图标旁徽标数字(画面事实:纯数字 token 且位于名称列左侧,``_BOARD_BADGE_X_MAX``);
    ② "X/Y" 正则的 X(斜杠读全时);
    ③ 斜杠丢失容错还原(``_board_rescue_xy``);
    ④ 徽标小格放大重读(``_read_badge_cell``,仅兜底行触发);
    ⑤ expected(身份 computed 底座;档位链阵营徽标整体失读时 OCR 侧证据穷尽,
       恒 1 兜底是低估最后一环——此时无画面事实反证,身份推算即最优估计;
       证据帧 86ce9fd1:持续伤害/护盾 徽标失读真值 2,旧链恒 1)。
    ①-④ 全 miss 且无 expected → count=1 兜底(动画期只显档位链,至少 1 人在场)。

    r319(ADR-0213 批次2):第二返回值 honest=**至少一行 OCR 真解析**(①-④)——
    全靠兜底 = 帧不可信(board_readable 消费);dict 契约不变(键仍在,值是兜底)。
    """
    results = _ocr(ctx, screen, _area_rect(ctx, A_BOARD))
    results.sort(key=lambda r: r.center.y)
    pairs: dict[str, tuple[int, int]] = {}
    fallback_rows: list[tuple[str, float, int | None]] = []   # (阵营, 名称行 y, expected 兜底值|None)
    honest = False
    for i, r in enumerate(results):
        faction = next((f for f in FACTIONS if f in (r.data or '')), None)
        if faction is None or faction in pairs:
            continue
        badge_cnt: int | None = None
        xy: tuple[int, int] | None = None
        rescued: tuple[int, int] | None = None
        for r2 in results[i + 1:]:
            dy = r2.center.y - r.center.y
            if dy > 45:
                break
            if dy <= 0:
                continue
            data = (r2.data or '').replace(' ', '')
            # 徽标计数:纯数字小 token 且在名称列左侧(徽标恒在图标右、名称列左的固定列)
            if (badge_cnt is None and data.isdigit() and len(data) <= 2
                    and getattr(r2, 'x', r2.center.x) < _BOARD_BADGE_X_MAX):
                v = int(data)
                if 1 <= v <= max(max_count, 1):
                    badge_cnt = v
                continue
            # count 显示为 "X/Y"(X=在场人数,Y=下个 tier 阈值,如 仙舟"1/3")
            if xy is None:
                m_xy = re.search(r'(\d+)\s*/\s*(\d+)', r2.data or '')
                if m_xy:
                    xy = (int(m_xy.group(1)), int(m_xy.group(2)))
                    continue
                # 斜杠丢失容错(仅 X/Y 正则未命中时尝试;注册表 tiers 校验)
                if rescued is None:
                    rescued = _board_rescue_xy(faction, data, max_count)
        if badge_cnt is not None:
            cnt = badge_cnt
            honest = True
        elif xy is not None:
            cnt = xy[0]
            honest = True
        elif rescued is not None:
            honest = True
            pairs[faction] = rescued
            continue
        else:
            # OCR 侧证据穷尽(徽标失读/动画帧)→ expected(身份 computed)兜底,恒 1 是
            # 低估最后一环(见 docstring ⑤);徽标小格重读(④)在后统一翻案。
            exp = expected.get(faction) if expected else None
            if exp is not None and 1 <= exp <= max(max_count, 1):
                nt_exp = next((t for t in FACTIONS[faction].tiers if t > exp), 0) \
                    if faction in FACTIONS else 0
                pairs[faction] = (exp, nt_exp)
            else:
                exp = None
                pairs[faction] = (1, 0)
            fallback_rows.append((faction, r.center.y, exp))
            continue
        # sanity:count 1-max_count(默认 9;read_game_state 传 level —— faction count ≤ deployed ≤ level,
        # count>level 必是 OCR 误读,如 狼狩:7@lv4);next_tier 1-12。越界 → 兜底 count=1。
        cnt = cnt if 1 <= cnt <= max(max_count, 1) else 1
        nt = xy[1] if (xy is not None and 1 <= xy[1] <= 12) else 0
        if nt == 0 and faction in FACTIONS:
            # 徽标/容错源无 Y → 注册表 tiers 推下一档(>count 的最小档;无更高档 → 0)
            nt = next((t for t in FACTIONS[faction].tiers if t > cnt), 0)
        pairs[faction] = (cnt, nt)
    # 第四级:逐兜底行徽标小格放大重读,只翻兜底行的案(有徽标/X/Y/容错行的帧零额外开销)。
    if fallback_rows:
        for faction, row_y, _exp in fallback_rows:
            badge = _read_badge_cell(ctx, screen, row_y)
            if badge is not None:
                nt = next((t for t in FACTIONS[faction].tiers if t > badge), 0) \
                    if faction in FACTIONS else 0
                pairs[faction] = (badge, nt)
                honest = True
    return pairs, honest


def read_board(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 在场人数}(= ``_board_pairs`` 的 X;向后兼容)。

    每个激活阵营一行:阵营名 + 其下的 "X/Y"(X=在场人数,Y=下个 tier 阈值)。详见 ``_board_pairs``。
    """
    pairs, _honest = _board_pairs(ctx, screen)
    return {f: c for f, (c, _nt) in pairs.items()}


def board_from_tracked(tracked: list) -> dict[str, int] | None:
    """从 tracked_deployed(身份可靠时)**计算** board 羁绊计数(用户 2026-08-16 定:以算为准)。

    OCR 左面板的坑:激活阵营多时**一页显示不全要滚动** → OCR 只读可视区,滚出屏的静默漏
    (board 是 form_progress/pivot/economy 的地基,漏阵营 = 半成型误判)。角色注册表
    (``cw_chars.CHARACTERS``)已有全量阵营数据 → 每个已上场已知身份角色贡献其全部阵营,
    计数天然是全集,不受滚动/遮挡/OCR 误读影响。

    口径(ADR-0312,迁移审计 w50(git 历史)):per-unit 标签单一源 = ``cw_bond_equips.unit_bond_tags``
    ——L1 全集(factions+flows+independent,开拓者按排归一)**+ L2 星徽装备
    羁绊贡献**(``tracked_deployed[].equips``,deploy_bench 读回在案):
    星徽「装备者加入【X】羁绊」/欢愉卡带「已是成员计数+1」装备后左面板
    该羁绊行 +1,是面板真值的一部分(迁移审计 w49(git 历史) §2:此前缺维度 → computed_vs_ocr
    常态化误报 + 星徽局档位系统性低估)。

    Returns:
        {羁绊: 在场人数};**tracked 空 或 含未知身份(char_id 空/'?'/不在注册表)→ None**
        (混合态不切,OCR 兜底——未知角色的阵营贡献算不出,半算比漏算更毒;观察冲突留证会暴露
        混合频率)。**无阵营已知角色不 bail**(2026-08-17):白厄「救世主」复制效果不计人数
        (官方 trait 3005)→ 跳过零贡献即精确;布洛妮娅(factions 空flows 燃血)正常贡献 flows;
        独立羁绊行计入(与左面板显示同口径)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        iter_occupied_deployed,
    )
    _occ = list(iter_occupied_deployed(tracked or []))   # ADR-0392 槽位表滤 None
    if not _occ:
        return None
    from sr_od.application.currency_war.kernel.cw_bond_equips import unit_bond_tags
    counts: dict[str, int] = {}
    for bc in _occ:
        tags = unit_bond_tags(bc)
        if tags:
            for t in tags:
                counts[t] = counts.get(t, 0) + 1
            continue
        # 零标签:区分「合法零贡献」与「身份不可算」——
        cid = getattr(bc, 'char_id', '') or ''
        if not cid or cid == '?':
            return None
        from sr_od.application.currency_war.data.cw_chars import (
            is_trailblazer,
            trailblazer_form,
        )
        _cid = cid
        if is_trailblazer(_cid):
            _cid = trailblazer_form(
                _cid, getattr(bc, 'position_pref', '') or 'back')
        ch = get_char(_cid)
        if ch is None:
            return None   # 注册表无此角色:阵营贡献算不出,保守退 OCR
        if ch.factions or ch.flows or ch.independent:
            continue      # 防御:有角色标签则 tags 非空,理论不可达
        # 三者皆空且装备无贡献 = 注册表数据异常(旧版同判)→ 保守退 OCR
        return None
    return counts


def read_board_next_tier(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 下个 tier 阈值}(= ``_board_pairs`` 的 Y;doc 13 ``FactionState.next_tier``)。

    只含 Y 解析到的阵营(0/未显阈值的不进 dict)。聚焦裁切 OCR 才稳(见 ``_board_pairs``)。
    """
    _bp_pairs, _ = _board_pairs(ctx, screen)
    return {f: nt for f, (_c, nt) in _bp_pairs.items() if nt > 0}


# ===== 商店牌费用徽章数字识别(2星直出缺口闭环,DD-018;merge_mechanics §2.6/§2.7)=====
# 依据:商店每张牌底部名字条右端有金色费用徽章,徽章内白色数字(1-3 位) =
# 该牌当前星级的实付费用(费用倍数体系 merge_mechanics §2.6:费用 = 原费用 ×
# 3^(星级−1),1★=原费、2★=×3、3★=×9;用户 2026-09-02 定稿:数字可为两位,
# 如饮月 2★=6、4费2★=12)。旧链 cost 从 roster 查表派生 → 2星/3星直出按 1星
# 记错星级;改读画面数字即可闭环(§2.7 识别缺口条,2026-09-02 落地)。
#: 数字模板目录(assets/template/ 下子路径)。
_SHOP_COST_TMPL_DIR: str = 'currency_war/shop_cost'
#: 费用 area 名后缀(screen_info「货币战争-备战-开商店」屏,商店牌-N-费用)。
_SHOP_COST_AREA_SUFFIX: str = '-费用'
#: TM 采信阈值(二值掩码 TM_CCOEFF_NORMED)。标定:正确数字最低 0.78(「1」字形
#: 窄,抗锯齿边像素波动大)、错误数字最高 0.59(13 帧 65 槽离线对拍,
#: 产物 .debug/temp/cw_cost_badges/);0.60 居中,两侧余量 ≥0.19。
_SHOP_COST_TM_THRESH: float = 0.60
#: 费用倍数 → 星级(费用倍数体系,merge_mechanics §2.6;用户定稿:星级 =
#: 读数 ÷ roster 原费,倍数 ∈ {1,3,9} → 1/2/3★)。
_SHOP_COST_MULT_TO_STAR: dict[int, int] = {1: 1, 3: 2, 9: 3}
#: 徽章数字合理域上界(3★ 顶格 = 9×5费 = 45,两位数;99 留余量滤 OCR 噪声)。
_SHOP_COST_MAX: int = 99
#: 字形分割过滤:数字字形高 ≥12(实测 22-24)、面积 ≥30(剔白字抗锯齿噪声/
#: 徽章高光残点);低于阈值的连通域不进识别。
_SHOP_COST_GLYPH_MIN_H: int = 12
_SHOP_COST_GLYPH_MIN_AREA: int = 30
#: OCR 二级路径的放大倍数(小裁片 det 天花板,同 ``_ocr_upscaled`` 手法)。
_SHOP_COST_OCR_SCALE: int = 4
#: 数字模板模块级缓存(dict[digit] → 0/255 灰度掩码;None=未加载,{}=目录缺)。
_COST_DIGIT_TEMPLATES: dict[int, MatLike] | None = None

#: roster 费用兜底时的信源标记(ShopCard.cost_source;徽章直读 = 'badge')。
COST_SOURCE_ROSTER_FALLBACK: str = 'roster_fallback'


def _load_cost_digit_templates() -> dict[int, MatLike]:
    """加载费用数字模板(模块级缓存;目录缺 → {})。

    模板 = 白色数字字形的二值掩码(白 ≥235 全通道,最大连通域紧裁),从存档
    开商店帧原 PNG 裁(来源与裁法见 assets/template/currency_war/shop_cost/;
    字体固定,跨帧位置稳定)。**样本覆盖 = 数字 1-4**(存档 13 帧徽章数字
    只出现过 1/2/3/4;5-9 无样本):字形模板只作**一级快路**(全部字形皆
    1-4 可分类时直出),模板外的字形组合走二级 OCR(见 ``read_shop_card_cost``)
    ——多位数徽章(6/9/12/15/18/27)与数字 5-9 均由二级覆盖,不依赖补模板。
    实机采到新数字字形后可重裁扩充模板目录(一级命中率随之升高)。
    """
    global _COST_DIGIT_TEMPLATES
    if _COST_DIGIT_TEMPLATES is None:
        out: dict[int, MatLike] = {}
        base = get_project_root() / 'assets' / 'template' / _SHOP_COST_TMPL_DIR
        for d in range(1, 5):
            p = base / f'cost_digit_{d}.png'
            if p.exists():
                out[d] = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        _COST_DIGIT_TEMPLATES = out
    return _COST_DIGIT_TEMPLATES


def _white_glyph_mask(crop: MatLike) -> MatLike:
    """费用徽章数字 → 二值掩码(数字为纯白 (255,255,255),底=彩色卡条/灰条)。

    白判据 = RGB 三通道最小值 ≥235(白字 vs 蓝绿灰紫各色卡条底,13 帧
    65 槽零误检;输入为框架 RGB crop)。
    """
    return ((crop.min(axis=2) >= 235) * 255).astype(np.uint8)


def _classify_glyph_digits(mask: MatLike) -> list[int | None]:
    """白字形掩码 → 逐字形数字分类(纯函数可测;x 序)。

    连通域分割(过滤 h<``_SHOP_COST_GLYPH_MIN_H``/area<``_SHOP_COST_GLYPH_MIN_AREA``
    的噪声)→ 每字形紧裁对数字模板 TM,≥``_SHOP_COST_TM_THRESH`` 记该数字、
    否则 None(= 模板外字形,如 5-9)。全 None 前置(掩码空/模板缺)→ []。
    调用方语义:**列表含 None 或为空 = 一级路径不采信,走二级 OCR**;全数字
    且 1-3 个 → 拼接成费用读数(多位数支持,'1'+'2' → 12)。
    """
    tmpls = _load_cost_digit_templates()
    if not tmpls or mask.size == 0 or not mask.any():
        return []
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    glyphs = [tuple(int(v) for v in stats[i])
              for i in range(1, n)
              if stats[i][3] >= _SHOP_COST_GLYPH_MIN_H
              and stats[i][4] >= _SHOP_COST_GLYPH_MIN_AREA]
    glyphs.sort(key=lambda g: g[0])                     # x 序
    out: list[int | None] = []
    for x, y, w, h, _area in glyphs:
        local = mask[max(0, y - 1):y + h + 1, max(0, x - 1):x + w + 1]
        best: int | None = None
        best_v = -1.0
        for d, t in tmpls.items():
            if local.shape[0] < t.shape[0] or local.shape[1] < t.shape[1]:
                continue
            v = float(cv2.matchTemplate(local, t, cv2.TM_CCOEFF_NORMED).max())
            if v > best_v:
                best, best_v = d, v
        out.append(best if best_v >= _SHOP_COST_TM_THRESH else None)
    return out


def _ocr_cost_digits(ctx: SrContext, crop: MatLike) -> int | None:
    """费用裁片二级 OCR:白字形掩码反转(黑字白底)→ 放大 → OCR 取整数。

    服务一级模板路径覆盖不到的形态:多位数徽章(6/9/12/15/18/27)、模板外
    数字字形(5-9 无样本)。黑字白底是 paddle rec 的稳态输入(同
    ``_ocr_difficulty_binarized`` 反转先例);二值图无背景干扰,4x 放大破
    小目标 det 天花板。读不到/域外(>``_SHOP_COST_MAX``)→ None。
    """
    if crop.size == 0:
        return None
    mask = _white_glyph_mask(crop)
    if not mask.any():
        return None
    up = cv2.resize(mask, (mask.shape[1] * _SHOP_COST_OCR_SCALE,
                           mask.shape[0] * _SHOP_COST_OCR_SCALE),
                    interpolation=cv2.INTER_NEAREST)
    inv = cv2.cvtColor(255 - up, cv2.COLOR_GRAY2RGB)
    v = _first_int([r.data for r in ctx.ocr_service.get_ocr_result_list(image=inv)])
    if v is None or not (1 <= v <= _SHOP_COST_MAX):
        return None
    return v


def read_shop_card_cost(ctx: SrContext, screen: MatLike, slot: int) -> int | None:
    """商店牌 ``slot``(1-5)费用徽章读数 → 1-``_SHOP_COST_MAX`` | None(失读)。

    裁 screen_info「商店牌-{slot}-费用」area(名字条右端数字窗,坐标单一源)
    → 两级管线:
    1. **字形模板快路**:白字形连通域分割逐字形对模板(数字 1-4 有样本,
       单/多位数同权——'1'+'2' 两字形即 12);全部字形可分类 → 拼接直出;
    2. **OCR 慢路**:快路不采信(掩码空返 None;含模板外字形/模板缺)→
       掩码反转黑字白底放大 OCR(覆盖 5-9 与未采样的多位数渲染)。
    两级皆失读 → None(调用方走 roster 兜底)。空槽(牌区无卡)掩码全黑
    → 快路 [] 慢路即时返 None,零 OCR 成本。
    """
    rect = _area_rect(ctx, f'{A_SHOP_CARD_PREFIX}{slot}{_SHOP_COST_AREA_SUFFIX}',
                      SHOP_SCREEN_NAME)
    if rect is None or screen is None:
        return None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None
    digits = _classify_glyph_digits(_white_glyph_mask(crop))
    if digits and all(d is not None for d in digits) and len(digits) <= 3:
        return int(''.join(str(d) for d in digits))
    return _ocr_cost_digits(ctx, crop)


def resolve_cost_star(badge_cost: int | None, roster_cost: int) -> tuple[int, int, str]:
    """徽章读数 + roster 1星费 → ``(cost, star, cost_source)``(纯函数可单测)。

    语义(费用倍数体系,merge_mechanics §2.6;用户定稿:星级 = 读数 ÷ 原费):
    - badge 缺失 / roster_cost≤0(名字未识别)→ roster 查表兜底,
      cost_source='roster_fallback';
    - badge = roster_cost × 倍数,倍数 ∈ {1,3,9} → star 1/2/3,cost = 读数
      (实付价真值;2/3星直出实锤由调用方 `[cw!]` 留证);
    - 倍数 ∉ {1,3,9}(含 ×27=4★ 超 CW 星级域、非整数倍 = 疑误读)→ 兜底
      roster(按原费用记 1★),cost_source='roster_fallback',调用方留证。
    """
    if badge_cost is None or roster_cost <= 0:
        return roster_cost, 1, COST_SOURCE_ROSTER_FALLBACK
    star = _SHOP_COST_MULT_TO_STAR.get(badge_cost // roster_cost) \
        if badge_cost % roster_cost == 0 else None
    if star is not None:
        return badge_cost, star, 'badge'
    return roster_cost, 1, COST_SOURCE_ROSTER_FALLBACK


def read_shop_cards(ctx: SrContext, screen: MatLike) -> list[ShopCard]:
    """SIFT 商店 5 张牌肖像 → list[ShopCard](x + faction + name + cost)。

    每张牌:裁 screen_info ``商店牌-N``(**肖像区**,D-55 经 VLM 定位改自文字带)→ ``identify_character``
    SIFT 对 ``currency_war/portrait_plaza`` 官方立绘库 → ``resolve_char_name`` 规范名;faction/cost 从 roster 派生。
    未识别(低内点/歧义/不在 roster)→ name='' faction='?' cost=0(仍占位保 5 张,len 不变)。

    **D-55 由 OCR 改 SIFT**:OCR 牌名对开拓者(玩家自定义名,如 "Momojie")等读不到/匹配错;SIFT 看
    肖像更稳。⚠️ 模板目录名须用**规范名**「开拓者·记忆/欢愉」非玩家 ID(2026-08-15 修:旧目录 Momojie/
    → resolve_char_name 落 legacy 路径返 None = 「开拓者 roster 缺」根因;玩家 ID 随账号变,规范名不变);
    肖像更稳(实测 shop_open 5/5 内点 33-68,VLM 定位肖像区)。faction 由 OCR 牌标签 → roster factions[0]
    (SIFT 读不了文字标签;**board OCR 仍是阵营计数权威**)。**faction 语义(2026-08-17)**:
    ``'?'``=未知(name 空/不在注册表);``''``=已知无阵营(白厄「救世主」类)。立绘库经
    ``ensure_portrait_templates`` 按需加载
    (buy 在 deploy 前,CwScreenPrep 备战单轮: buy→deploy,故不依赖 deploy 才加载的缓存)。
    """
    templates = ensure_portrait_templates(ctx)
    # 商店开态前置门(M37/M38 误停机根因,2026-08-16):read_shop_cards 无脑裁牌区 rect 做 SIFT,
    # 商店收起/未展开帧(牌区=节点进度条+功能按钮)上全 miss → 采集钩子把「非商店帧的空读」
    # 误判「真有未识别卡」→ flag → shop.py 停机(实测:存证截图 analyze_screen 命中备战屏非
    # 商店开态,VLM 客观描述证实 y70-260 无卡)。门:商店开态锚「按钮-收起」(text area,框架
    # find_area_in_screen OCR+LCS)不命中 → 返空列表(「没有牌」≠「未识别」,不写 flag)。
    _si = ctx.screen_loader.get_screen(SHOP_SCREEN_NAME)
    _collapse_area = next((a for a in _si.area_list if a.area_name == '按钮-收起'), None) if _si else None
    if _collapse_area is None:
        # r9 review:锚缺失时门被静默跳过(fail-open)→ M37/M38 误停机回归无告警(改名/删 area)。
        from one_dragon.utils import log_utils
        log_utils.log.warning('[cw!] read_shop_cards 商店开态锚「按钮-收起」缺失(fail-open)→ 检查 yml')
    if _collapse_area is not None:
        from one_dragon.base.screen.screen_utils import find_area_in_screen
        # ⚠️ r7 review P0-A:旧 `is not True` 恒真(FindAreaResultEnum.TRUE.value 是 int 1,
        # `1 is not True` 恒成立)→ 门无条件返空 → read_shop_cards 自 e7bbd711(08-16 11:49)
        # 起**全局恒空**(decisions 实证:此前 1031/1031 行 shop 非空,之后 234/234 shop=[]
        # 且 0 BuyCard)——M46 起所有「一张不买」的真根因。改枚举等值比较。
        if find_area_in_screen(ctx, screen, _collapse_area).value != 1:
            return []
    cards: list[ShopCard] = []
    for i in range(1, 6):
        rect = _area_rect(ctx, f'{A_SHOP_CARD_PREFIX}{i}', SHOP_SCREEN_NAME)
        if rect is None:
            continue
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        # r13:空槽检测(六边形占位,SIFT inliers≈3 vs 真卡 30-120)——低等级商店后槽未解锁
        # 是常态,空槽不是「未识别卡」(c1888c7d 帧实证:牌4/5 空槽 inliers=3 触发假 unknown)。
        # r15 review:跳过不可静默(假空槽=买不到该卡且不可见)——55-75 灰带 [cw!] 留证
        # (实测真卡 min 67.4 vs 空槽 19.5,余量 11%;采到暗卡击穿即闭环降阈值)。
        _mean = float(crop.mean())
        if _mean < 60:
            if _mean >= 50:   # 灰带:可能是被特效/裁切偏移压暗的真卡
                from one_dragon.utils import log_utils
                log_utils.log.info(f'[cw!][read_shop_cards] 牌{i} 均值{_mean:.1f}(灰带 50-60,'
                              f'疑暗卡被误判空槽,采到即闭环降阈值)')
            continue
        avatar_id, _inliers = (identify_character(crop, templates)
                               if templates is not None else (None, 0))
        # `w512_obs_surfaces/`(观测自检设计 §2.10/§5-B6 识别置信度遥测):非空槽(亮度≥60,
        # 已过空槽门)SIFT 仍 miss → 「读空」事件带内点数落台账 confidence 面。
        # 零即时告警(纯留证,恒 L2),离线统计「哪个 reader 在哪个画面退化」
        # ——读空率环比翻倍是系统性识别退化的最早信号。写点锚定在既有 miss
        # 事件上(非轮询);写失败不阻断牌面读取。
        if avatar_id is None and templates is not None:
            try:
                # 分包期 4:落账经 kernel/cw_telemetry_exit 出口钩子位(零直依 telemetry)
                from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                    record_defect,
                )
                record_defect(
                    'confidence', 'perception_conflict',
                    expected=f'商店牌{i} SIFT 识别出身份',
                    observed=f'miss(inliers={_inliers})',
                    reader_source='read_shop_cards',
                    confidence=float(_inliers),
                    note='读空事件(置信度分布监控源;非即时告警)')
            except Exception:   # noqa: BLE001  遥测 best-effort
                pass
        name = resolve_char_name(avatar_id) if avatar_id else ''
        ch = get_char(name) if name else None
        # 费用信源(2星/3星直出闭环):画面费用徽章读数优先(read_shop_card_cost,
        # 模板快路+OCR 慢路两级);失读/倍数推不出 → roster 查表兜底(按原费用
        # 记 1★)并标 cost_source='roster_fallback'(金账对账可区分信源)。
        # 读数 ÷ roster 费 = 倍数 ∈ {1,3,9} → 星级 1/2/3(费用倍数体系,
        # merge_mechanics §2.6;×27=4★ 超 CW 星级域,留证兜底)。
        _badge = read_shop_card_cost(ctx, screen, i)
        if ch is not None:
            cost, star, cost_src = resolve_cost_star(_badge, ch.cost)
            if _badge is not None and cost_src == COST_SOURCE_ROSTER_FALLBACK:
                if _badge == ch.cost * 27:
                    log.warning('[cw!] 商店牌%d 费用读数=%s = roster 费 %s 的 27 倍(=4★,'
                                '超 CW 3★ 星级域)→ roster 兜底留证(复现即 gameplay 异常信号)',
                                i, _badge, ch.cost)
                else:
                    log.warning('[cw!] 商店牌%d 费用读数=%s 非 roster 费 %s 的 1/3/9 倍'
                                '(疑误读)→ roster 兜底留证', i, _badge, ch.cost)
            elif star >= 2:
                log.warning('[cw!] 商店牌%d 费用读数=%s ÷ roster 费 %s = %d 倍 → %d星直出'
                            '实锤(费用=星级倍数,merge_mechanics §2.6)',
                            i, _badge, ch.cost, _badge // ch.cost, star)
        else:
            # 名字未识别:徽章可读时费用信徽章(实付价真值),星级保守 1
            # (2星直出+未知名字的形态待实机样本,金账对账兜底)。
            if _badge is not None:
                cost, star, cost_src = _badge, 1, 'badge'
            else:
                cost, star, cost_src = 0, 1, COST_SOURCE_ROSTER_FALLBACK
        cards.append(ShopCard(
            x=(rect.x1 + rect.x2) // 2,
            # '?'=未知(名未识别/不在注册表);''=已知无阵营(白厄类;2026-08-17 与 shop/identity 同语义)
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
            name=name,
            cost=cost,
            star=star,
            cost_source=cost_src,
            # 升星预览✦(迁移审计 w104(git 历史)/迁移审计 w282(git 历史),ADR-0416):与 SIFT 同 crop 只多一次顶部带 mask+TM,零额外裁切
            merge_preview=read_merge_preview(crop),
        ))
    # ~~shop_unknown_card 采集钩子已删(2026-08-17 归因闭环)~~:38 张存档样本离线对拍全识别
    # (73-119 内点,plaza 库)——全部是刷新动画/settle 瞬时帧 miss,非真未知卡;阮·梅/白厄挂账
    # 同归因闭环(瞬时帧,非光照变体/库缺)。flag 写入无消费端(shop.py 停机判定走重读防抖,
    # L287-299,保留作真未知防护),纯积压源,按「采完即删」约定移除。
    return cards


def read_bench_full(ctx: SrContext, screen: MatLike) -> bool | None:
    """~~已退役~~(迁移批次二,设计 §3.2.5):「备战席已满」警告 OCR 不做
    识别——出现太短暂、无法可靠采样(玩家裁定 2026-09-09);席满判定 =
    BoardState 派生(:func:`kernel.cw_board_state.bench_is_full`,占位
    真值一份)。

    本函数保留为**墓碑**(发警告防复活):调用即断言失败。唯一在册
    消费点(cw_screen_prep._bench_full_break_round)已同批改接派生判定。
    """
    raise RuntimeError(
        'read_bench_full 已退役(设计 §3.2.5/迁移批次二):警告 OCR 通道'
        '不复活;席满判定用 kernel.cw_board_state.bench_is_full 派生')


# ===== 组合入口 =====
def _level_from_xp(xp_progress: tuple[int, int] | None) -> int | None:
    """XP 条分母反推当前等级(ADR-0129):"cur/need" 的 need = 当前级→下一级门槛,反查
    ``XP_TO_NEXT_LEVEL``。1-2 级门槛不在表(用户表从 LV.3 起)→ None(调用方不覆盖,安全)。"""
    if not xp_progress:
        return None
    _inv = {v: k for k, v in XP_TO_NEXT_LEVEL.items()}
    return _inv.get(xp_progress[1])


def _resolve_level(
    ocr_raw: int | None,
    heuristic: int,
    xp_level: int | None,
    last_level: int,
) -> tuple[int, list[tuple[str, int, int, str, str]], bool]:
    """等级三源解析(纯函数,2026-08-18 治本重构:live M-cw 乒乓根因)。

    输入:
    - ``ocr_raw``:「文本-等级」区直读(**无兜底**;None=失读);
    - ``heuristic``:``_expected_level`` 启发式(ocr_raw 失读时的兜底值);
    - ``xp_level``:XP 条分母反推(ADR-0129,独立源;None=失读);
    - ``last_level``:session 上次值(``last_level_obs``;0=新局无历史)。

    返回 ``(level, events, authoritative)``:events = [(kind, old, new, verdict, source)]
    (供调用方记 [cw!]/obs_conflict);authoritative = 本帧等级是否来自真实观测
    (OCR 或 XP 至少一源可读;False=纯启发式,**调用方不得写回 last_level_obs** —— 毒化防线)。

    解析序(信源主权从高到低):
    1. 基值 = ocr_raw(可读)否则 heuristic;
    2. XP 覆盖(ADR-0129「信 XP 分母」):xp_level 可读且 ≠ 基值 → 采 XP;
    3. 单调守卫:较 last 下降 → **XP 主权豁免**(live 2026-08-18 实证:OCR 失读→启发式 6
       被写进 last_level_obs 毒化,XP 反推 5 每帧被单调守卫打回 → level 乒乓 6↔5,
       策略全程跑假等级);XP 未确认的下降仍是 OCR 误读 → 保旧;
    4. 跳变守卫:较 last 跳 >+2 且 XP 未确认 → OCR 单源假阳 → 保旧(M38 语义)。
    """
    level = ocr_raw if ocr_raw is not None else heuristic
    events: list[tuple[str, int, int, str, str]] = []
    # XP 覆盖:真实双源分歧(OCR 可读)才留证;OCR 失读时的例行为「兜底让位 XP」
    # (ADR-0129 设计常态,逐帧记 [cw!] 是遥测噪声 —— live 10:47-10:48 每帧 2 冲突实证)。
    if xp_level is not None and xp_level != level and ocr_raw is not None:
        events.append(('xp_override', level, xp_level, '采新-XP分母反推', 'xp_denominator'))
    if xp_level is not None and xp_level != level:
        level = xp_level
    if last_level:
        _xp_sovereign = xp_level is not None and level == xp_level
        if level < last_level:
            if _xp_sovereign:
                # 上次值疑似被启发式/误读毒化,XP 独立源向下校正(乒乓根治)。
                events.append(('xp_down', last_level, level,
                               '采新-XP下行校正(上次值疑似毒化)', 'xp_denominator'))
            else:
                events.append(('mono', last_level, level,
                               '保旧-单调守卫(下降强可疑)', 'ocr'))
                level = last_level
        elif level > last_level + 2:
            if _xp_sovereign:
                events.append(('jump_ok', last_level, level,
                               '采新-XP确认真跳变放行', 'ocr+xp_denominator'))
            else:
                events.append(('jump', last_level, level,
                               '保旧-跳变守卫(单源跳变拒,XP未确认)', 'ocr'))
                level = last_level
    authoritative = ocr_raw is not None or xp_level is not None
    return level, events, authoritative


#: _resolve_level 事件 → 日志格式({o}=旧值,{n}=新值;消费方 read_game_state)
_LV_LOG_FMT: dict[str, str] = {
    'xp_override': '[cw!] level 修正:OCR 读 {o},XP 分母反推 {n}(以 XP 为准)',
    'xp_down': '[cw!] level XP下行校正:上次 {o}(疑似兜底毒化) → XP 反推 {n}(乒乓根治)',
    'mono': '[cw] level 单调守卫:OCR 读 {n} < 上次 {o}(误读)→ 用 {o}',
    'jump': '[cw!] level 跳变守卫:OCR 读 {n} > 上次 {o}+2(疑似 XP 数字混入) → 用 {o}(误读不锁死)',
    'jump_ok': '[cw] level 真跳变放行:{o} → {n}(XP 分母独立确认)',
}


# ===== 规范入口序列:阶段键 + 每阶段字段规格(ADR-0462)=====
# 「先清场、再识别、后动作」:P0 清场期零业务识别 → P1 干净备战期全量基线 →
# P2 动作期(开店/overlay)只读该动作决策所需。字段规格 = read_game_state 的
# 逐字段门单一源(键域与 Snapshot SubstateClassification.name 对齐)。

#: P1 干净备战期(关店备战帧):全量识别基线,含 hp 真读主路径(shop 关帧血量区
#: 可见)。shop_cards/refresh_probs 属开店面板,必空不读。
PHASE_PREP_CLEAN: str = 'prep_clean'
#: P2a 开店动作期:仅买牌决策所需;hp/node_type 结构必空
#: (6fc1fd4c 先例 + shop.py session 拷贝),cap/deployed/难度/连胜以 P1 基线为准。
PHASE_PREP_SHOP_OPEN: str = 'prep_shop_open'
#: 战斗/过渡帧:仅位面轮次(恢复对局检测消费面只有 plane/round)。
PHASE_BATTLE_OR_TRANSIT: str = 'battle_or_transit'

#: 每阶段可读字段集(read_game_state 逐段门;phase=None=全量=现行为)。
#: 字段键与 read_game_state 内各识别段一一对应;hp 段特殊:在集内=真读
#: (read_hp_opt),不在=对账沿用(reconcile,零 OCR)。
PHASE_FIELD_SPEC: dict[str, frozenset[str]] = {
    # ~~'bench_full' 键已删(迁移批次二 §3.2.5 通道退役):该键只辖
    # read_bench_full OCR,通道退役后无辖域,键位删除防复活。
    PHASE_PREP_CLEAN: frozenset({
        'gold', 'phase_round', 'hp', 'node_type', 'xp', 'level',
        'deploy_cap', 'deployed_count', 'enemy_difficulty',
        'level_up_cost', 'streak', 'board',
    }),
    PHASE_PREP_SHOP_OPEN: frozenset({
        'gold', 'phase_round', 'xp', 'level', 'level_up_cost',
        'board', 'shop_cards', 'refresh_probs',
    }),
    PHASE_BATTLE_OR_TRANSIT: frozenset({'phase_round'}),
}


def read_game_state(ctx: SrContext, screen: MatLike,
                    phase: str | None = None) -> GameState:
    """备战屏截图 → GameState(喂 plan;逐字段 gate 单一源 = PHASE_FIELD_SPEC)。

    :param phase: 规范入口序列阶段键(ADR-0462:先清场、再识别、后动作)——
      ``prep_clean``=P1 干净备战期全量基线(含 hp 真读主路径);``prep_shop_open``
      =P2a 开店动作期(仅买牌决策所需);``battle_or_transit``=战斗/过渡帧(仅
      位面轮次)。**None = 全量路径 = 现行为逐行不变**(存量调用点/测试零波及);
      未注册阶段名 → warning + 全量(fail-open:未知态不猜,回退现行为)。

    各字段 OCR 失败 → 安全默认(见各 reader)。level 不可 OCR → ``_expected_level`` 兜底;
    hp 读不到 → ``reconcile_hp`` 对账(ADR-0282:沿用 session.last_hp_real,开局无真值才
    兜底 100)。v1 不读 bench/deployed 身份(buy 决策靠 board+shop+gold;
    deploy 走 CwOpDeploy)。
    """
    from sr_od.application.currency_war.kernel import cw_observe as _obs_mod
    _spec = PHASE_FIELD_SPEC.get(phase) if phase is not None else None
    if phase is not None and _spec is None:
        # fail-open:未知阶段名不猜 → 全量 + 告警(拼错阶段名立即暴露,不静默)
        log.warning('[cw!] read_game_state 未注册阶段 %r → 全量读取(fail-open)', phase)
        _spec = None

    def _w(key: str) -> bool:
        """本阶段是否读该字段(None 阶段=全量恒 True)。"""
        return _spec is None or key in _spec

    if _spec is not None:
        # 只有注册阶段才置位:未注册阶段名(fail-open 探针)置位会把本次全量读取
        # 产生的证据行打上假阶段名。实证:fail-open 探针经共享 obs_conflict 账本
        # 写入 282 行 obs_phase=no_such_phase(分诊报告 §1.3)。
        _obs_mod.set_obs_phase(phase)   # 冲突证据行带阶段(噪声判定位,ADR-0462)
    state = GameState()
    # 金读走稳定门(read_gold_settled):开店帧收入计数器可能在跳,单帧读拿
    # 入账前旧值 = `w489_sim_real_gap/` 感知面「开局金系统性偏低」根因环;gold_readable 语义
    # 不变(None=读不到)。
    # ⚠️ gold 值语义(T-167 gold 值勘误,与指纹消费方对账):``state.gold``
    # 是 **raw 读数**——失读时兜底 0 非 None(下一行),可读帧含 OCR 噪声;
    # 本函数不做可信位过滤。需要可信金判读的消费方走 ``gold_readable``
    # 位或备战观察链的 ``prep_obs_frame.state_gold_trusted``(唯一写点 =
    # cw_screen_prep:仅 heavy ∧ 店开帧可信)——cw_loop 环级守卫的指纹
    # gold 分量即按该可信位钉死「开态可信帧更新、其余帧沿用陈值」。
    _gold_opt = read_gold_settled(ctx, screen) if _w('gold') else None
    state.gold = 0 if _gold_opt is None else _gold_opt
    state.gold_readable = _gold_opt is not None   # r319 保真位(对齐 hp_readable)
    # ADR-0282(hp 三层,用户设计):hp 走对账层 reconcile_hp——读不到(shop 开态
    # 血量区空)≠漂移是读失败,保旧沿用 session.last_hp_real(比假 100 安全,低血
    # 先验触发保血方向对);全无真值(开局)= 初值表先验(实证档 A8/108 → 82/62,
    # readable=False;无实证档 → None 诚实未知;ADR-0559/0491,W823 GameState.hp
    # None 化)。state.hp=决策用值,
    # state.hp_readable=是否真读(遥测分字段记,不混「真 100」)。
    # state.hp_trusted=值可信位(ADR-0428 语义细分;ADR-0431 帧龄门收紧,
    # 派生式见下方帧龄门注释)——FLIP 类谓词据此把「本帧未 OCR 到」与
    # 「值不可信」区分开(消费口径 hp_readable or hp_trusted 零改)。
    # ADR-0431:位面/轮次提前读 —— node_t=(plane-1)*9+round 是下行守卫
    # 帧间事实窗锚与 hp_trusted 帧龄门锚(读取器相互独立,仅次序调整,
    # 语义零漂移)。
    state.plane, state.round_num = (
        read_phase_round(ctx, screen) if _w('phase_round')
        else (state.plane, state.round_num))
    _node_t = ((state.plane - 1) * 9 + state.round_num
               if state.plane is not None and state.round_num is not None
               else None)
    from sr_od.application.currency_war.kernel.cw_reconcile import reconcile_hp
    # hp 跳过/真读的门 = PHASE_FIELD_SPEC('hp' 在集内才 OCR;ADR-0462,
    # 收编 6fc1fd4c 先例为规格单一源,不留两处门控):hp 区物理只在 shop 关态
    # 可见——spec 无 'hp' 的阶段(prep_shop_open 开店面板遮挡/battle_or_transit
    # 非备战)OCR 必然 miss,是每帧必付的死读;_hp_opt=None 走 reconcile 沿用
    # (session.last_hp_real 语义不变,帧龄门 _same_node_stale 照常)。
    # prep_clean(关店备战帧)= 真读主路径,两级放大回退在该阶段才有意义。
    # phase=None = 全量路径,必须与 prep_clean 同读 hp:全量调用方(director
    # heavy 环入口 observe_full/对拍 recorder)的帧多为**关店**备战帧,hp 可见;
    # 曾按 6fc1fd4c 把全量路径也跳过(readable 恒 False),是 2026-08-30 局
    # 位面2 r1 连续 readable=False 的识别根因——画面可见却从未 OCR(ADR-0490)。
    # 代价边界:仅 shop 开态的全量帧落 miss 回退(两级小图 OCR ~百毫秒),
    # 关店常态帧全图 OCR 走帧级缓存零新增。
    _hp_opt = (read_hp_opt(ctx, screen)
               if (_spec is None or 'hp' in _spec) else None)
    _sess_hp = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    _had_real = getattr(_sess_hp, 'last_hp_real', None) is not None
    state.hp, state.hp_readable = reconcile_hp(
        _sess_hp, _hp_opt, screen, source='read_game_state', node_t=_node_t)
    # ADR-0431 帧龄门:同节点内沿用才可信(shop 开态帧间无战斗,值必然
    # 未变);跨节点沿用帧与被下行守卫拒信帧(SUSPECT)降 False;真读且
    # 过守卫的帧可信;全无真值帧(hp=None)恒 False(ADR-0428/0491)。
    _same_node_stale = (_had_real
                        and getattr(_sess_hp, 'last_hp_real_node', None) == _node_t)
    state.hp_trusted = (state.hp_readable and _hp_opt is not None) \
        or _same_node_stale
    # 节点类型台账制消费:查表优先(session 权威表,写入端 = 位面详情采集 +
    # 投资环境后重读;权威依据 = 用户口述「位面内节点类型与数量只有投资环境
    # 选择能改变」)。表缺/该位次未识别 → 退逐帧标签 OCR(旧链,boss 轮次门
    # 等语义门不变);表值与逐帧读**同词汇表**,值语义零变更。
    # 三票校验(纯记账):表可查时逐帧识别降级为校验票,≥2 独立票一致反对
    # 表值才落缺陷台账(投资环境变异窗豁免),不改行为。
    _ledger_session = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    # spec 无 node_type 的阶段(prep_shop_open 节点行被遮恒 None——shop.py
    # session 拷贝是唯一真源;battle_or_transit 无消费)跳过标签 OCR 与三票。
    if _w('node_type'):
        _obs_t = gate_node_type(read_node_type(ctx, screen), state.round_num)
        _ledger_t = ledger_node_type(_ledger_session, state.plane, state.round_num)
        state.node_type = _ledger_t if _ledger_t is not None else _obs_t
        if _ledger_t is not None:
            verify_node_type_votes(ctx, screen, state.plane, state.round_num)
    # session 上次观测等级提前取(XP '1' 拆分收紧的上下文先验 + 等级三源解析共用;
    # 0=新局无历史)。毒化防线保证 last_level_obs 只在 authoritative 帧写入,
    # 可作先验。
    _match = getattr(ctx, 'cw_match', None)
    _last_lv = 0
    if _match is not None and _match.session is not None:
        _last_lv = getattr(_match.session, 'last_level_obs', 0)
    state.xp_progress = (read_xp_progress(ctx, screen, expected_level=(_last_lv or None))
                         if _w('xp') else None)
    if _w('level'):
        # 等级三源解析(2026-08-18 治本重构):OCR 直读(无兜底)/XP 分母反推/启发式兜底
        # 经 ``_resolve_level`` 统一仲裁 —— 旧内联链在「OCR 失读 + XP 可读」态每帧乒乓
        # (XP 采新 5 → 单调守卫用毒化 last 6 打回,live 10:47-10:48 三连发实证),
        # 且把启发式兜底值写回 last_level_obs(毒源)。纯函数语义/事件/防线详见其 docstring。
        _lv_raw = read_level_raw_opt(ctx, screen)
        _xp_lv = _level_from_xp(state.xp_progress)
        state.level, _lv_events, _lv_authoritative = _resolve_level(
            _lv_raw, _expected_level(state.plane, state.round_num), _xp_lv, _last_lv)
        # 保真位(对齐 hp_readable;M2 obs 根因修复):False=纯 _expected_level
        # 启发式兜底(OCR 与 XP 双失读)——「兜底 4」与「真读 4」遥测可分。
        # 阶段 spec 跳过 level 的帧保留缺省 True(sim 恒真读帧约定,同 hp_readable)。
        state.level_readable = _lv_authoritative
        for _kind, _old, _new, _verdict, _src in _lv_events:
            _fmt = _LV_LOG_FMT.get(_kind)
            if _fmt is not None:
                _msg = _fmt.format(o=_old, n=_new)
                if _kind in ('xp_override', 'xp_down', 'jump'):
                    log.warning(_msg)
                else:
                    log.info(_msg)
            else:
                log.warning(f'[cw!] level {_kind}:{_old}->{_new}')
            obs_conflict('level', _old, _new, screen, verdict=_verdict, source=_src,
                         plane=state.plane, round_num=state.round_num)
        # 毒化防线(2026-08-18):纯启发式兜底值(OCR 与 XP 双失读)不写回 last_level_obs
        # —— live 实证:兜底 6 被写入后,XP 反推 5 被单调守卫打回(乒乓),且下一帧继续毒化。
        if _match is not None and _match.session is not None and _lv_authoritative:
            _match.session.last_level_obs = state.level
    # ADR-0286(迁移审计批 F1):cap 真值接线——防抖后写入 state.deploy_cap
    # (决策层 max_units() 优先读真值、level 兜底;读不到/域外拒信 → None
    # 保持兜底语义,与旧恒 level 行为兼容)。生产 cap = level + 宝钻数(D-53)。
    # 阶段 gate 路径 cap 与 deployed_count 合并单读(resolve_paddle_pair,
    # ADR-0462);phase=None 全量路径保持两读不变(零行为变更基线)。
    _paddle_x = None
    if _spec is None:
        state.deploy_cap = read_deploy_cap_debounced(ctx, screen, state.level)
    elif 'deploy_cap' in _spec or 'deployed_count' in _spec:
        _paddle_x, state.deploy_cap = resolve_paddle_pair(ctx, screen, state.level)
    # enemy_difficulty(迁移审计批 F1 裁决·读链翻转):逐帧真读(备战「文本-难度」
    # OCR)优先——session 值来自开局简报(数值≈108 恒定),旧链「session 优先」
    # 把逐帧真读结构性压死(92.7% 覆盖恒 108,难度爬升真值从未落盘)。
    # 翻转后:真读命中 → 用真值+live=True;真读 None(stylized OCR 常空,
    # 已知)→ 回退 session 恒值,live=False;双源皆无 → None。
    # 判读纪律:live=False 帧的值是简报恒值,别当「难度 vs 轮次」曲线样本。
    # spec 无此字段的阶段(prep_shop_open 以 P1 基线为准;battle 帧无旗牌)跳过
    # 两级管线,直接 session 值 + live=False(与「真读 None 回退」同语义)。
    _match = getattr(ctx, 'cw_match', None)
    _ed_session = getattr(getattr(_match, 'session', None), 'enemy_difficulty', None) if _match is not None else None
    if _w('enemy_difficulty'):
        _ed_live = read_enemy_difficulty(ctx, screen)
        if _ed_live is not None:
            state.enemy_difficulty = _ed_live
            state.enemy_difficulty_live = True
        else:
            state.enemy_difficulty = _ed_session
            state.enemy_difficulty_live = False
    else:
        state.enemy_difficulty = _ed_session
        state.enemy_difficulty_live = False
    if _w('level_up_cost'):
        state.level_up_cost = read_level_up_cost(ctx, screen)
    # 刷新实付金 = 基价常量(ADR-0456):「文本-刷新金币数」rect 读到的是
    # 面板徽标(=min(gold//10,5) 利息数值)非刷价,OCR 退出主链(决策热路径
    # 净少一次 OCR);state.shop_refresh_cost 恒 REFRESH_COST_BASE,消费点
    # ``or 2`` 语义不变。(历史旁证读数 read_shop_refresh_cost 现零调用方,
    # 保留纯函数形态供未来复采;见 D88 勘误。)
    state.shop_refresh_cost = REFRESH_COST_BASE
    # streak:优先 session.last_streak(结算「连胜×N」带符号,方向可靠;fixture 核实 2026-08-11);
    # 无 session(离线/测试)→ read_streak 备战 magnitude fallback。
    # 双源留证(观察冲突审计 #8 P2,2026-08-17):结算真值(带符号)与备战 magnitude 独立可对拍
    # —— |结算|≠备战 且 非结算重置边缘(胜→连胜≥1/败→连败≤-1 或 0)→ 一方误读,留证统计毒化率
    # (read_streak magnitude OCR 间歇误读的量化数据,此前无通道)。
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    # spec 无 streak 的阶段(prep_shop_open:连胜整轮不变,session 结算真值为准,
    # 省每帧 ~85ms 纯对拍读;battle 帧无消费)只取 session 值不做备战对拍读。
    if _sess is not None:
        state.streak = _sess.last_streak
        if _w('streak'):
            _prep_streak = read_streak(ctx, screen)
            if (_prep_streak is not None and _sess.last_streak != 0
                    and abs(_sess.last_streak) != _prep_streak):
                obs_conflict('streak', _sess.last_streak, _prep_streak, screen,
                             verdict=('留证-双源不等(结算带符号 vs 备战magnitude,一方误读;'
                                      '处理:单次按噪声忽略,同局 JSONL 频发 >10 行/时'
                                      '→ 排查 read_streak 与结算 streak reader'),
                             source='settlement_vs_prep', plane=state.plane, round_num=state.round_num)
    else:
        state.streak = (read_streak(ctx, screen) or 0) if _w('streak') else 0
    # board 双源(用户 2026-08-16 定:羁绊多时左面板一页显示不全要滚动 → OCR 只读可视区,
    # 滚出屏的静默漏;游戏数据(角色注册表)已全量 → computed 做**全集底座**,不受滚动/遮挡影响;
    # 迁移审计 w287(git 历史) 裁决翻转,ADR-0417):computed(tracked 全已知身份)仍是全集底座(滚出屏的阵营只有它
    # 知道);但**可视区徽标行(左栏 OCR)是画面事实 —— 可视行计数与 computed 不等时以徽标为准
    # 覆写**(迁移审计 w285(git 历史) 抽样 board 3/6 采 computed 错、徽标才是真值实证)。例外(防新错):非备战帧
    # (overlay 遮挡/动画过渡,迁移审计 w285(git 历史) overlay 干扰 2/6 实证)徽标与 computed **均不可靠** →
    # 不裁不覆,保 computed 底座 + 留证(等下一帧备战帧再裁)。
    # - OCR 可见但 computed 无 = tracked 漏该阵营角色(强信号):备战帧同样采徽标覆入;
    #   非备战帧留证不覆。
    # - computed 有而 OCR 不可见 = 滚动截断(正常,不算错)。
    # - tracked 空/含未知 → None → OCR 兜底(现状;混合态半算比漏算更毒)。
    _match = getattr(ctx, 'cw_match', None)
    _exec = getattr(_match, 'exec_state', None) if _match is not None else None
    _tracked_dep = (_exec.tracked_deployed if _exec is not None else None)
    _computed = board_from_tracked(_tracked_dep)
    # spec 无 board 的阶段(battle_or_transit)跳过面板 OCR:空 OCR 侧 + honest=False
    # → 有 tracked 时保 computed 底座、无 tracked 时空板(与「OCR 全 miss」同语义)。
    _bp, _board_honest = (
        _board_pairs(ctx, screen, state.level, expected=_computed)
        if _w('board') else ({}, False))
    state.board_readable = _board_honest   # r319:动画帧(count=1 兜底)显式标注
    _ocr_board = {f: c for f, (c, _nt) in _bp.items()}
    if _computed is not None:
        _needs_arbitration = any(_computed.get(_f) != _c for _f, _c in _ocr_board.items())
        _prep_like = is_prep_like_frame(ctx, screen) if _needs_arbitration else True
        # 裁决迁仲裁注册面(15 号稿批 A;注册键 board_faction_count,标称类
        # 帧态门):内核只产决策,留证行仍在此处按决策发射——行数/field/
        # 新旧值/verdict 文本逐字节不变(零行为验收,T-2 对拍)。
        from sr_od.application.currency_war.obs.cw_arbitration import (
            combine_board_frame_gated,
        )
        _merged, _decisions = combine_board_frame_gated(
            badge_ocr=_ocr_board, computed=_computed,
            prep_like=_prep_like, board_honest=_board_honest)
        for _f, _kind, _take in _decisions:
            _ocr_c = _ocr_board[_f]
            _calc_c = _computed.get(_f)
            if _kind == 'ocr_only':
                if _take:
                    obs_conflict('board', {'ocr': _ocr_board, 'computed': _computed},
                                 f'OCR有computed无:{_f}',
                                 screen, verdict=('采新-badge(备战帧徽标=画面事实,tracked漏该阵营;'
                                                   'W287 裁决翻转:徽标覆入 board;'
                                                   '频发 >10 行/时→排查 tracked 身份漏认(_reconcile 漂移源)'),
                                 source='computed_vs_ocr', faction=_f)
                else:
                    obs_conflict('board', {'ocr': _ocr_board, 'computed': _computed},
                                 f'OCR有computed无:{_f}',
                                 screen, verdict=('留证-双不可信(非备战帧/动画帧,徽标与 computed '
                                                  '均不采信(W285 overlay 干扰 2/6 实证防新错);'
                                                  '保 computed 底座,留等备战帧再裁'),
                                 source='computed_vs_ocr')
            elif _take:
                obs_conflict('board', {'ocr': _ocr_c, 'computed': _calc_c}, f'count不等:{_f}',
                             screen, verdict=('采新-badge(备战帧可视行徽标=画面事实,优先于身份'
                                              ' computed;W287 裁决翻转(旧采 computed,W285 board '
                                              '3/6 采错实证);频发 >10 行/时→排查对账纠漂链'),
                             source='computed_vs_ocr', faction=_f)
            else:
                obs_conflict('board', {'ocr': _ocr_c, 'computed': _calc_c}, f'count不等:{_f}',
                             screen, verdict=('留证-双不可信(非备战帧/动画帧,徽标与 computed '
                                              '均不采信(W285 overlay 干扰 2/6 实证防新错);'
                                              '保 computed 底座,留等备战帧再裁'),
                             source='computed_vs_ocr', faction=_f)
        state.board = _merged
        # next_tier 从注册表 tier 表算(>count 的最小 tier;无更高档 → 0)。
        # 基于 _merged(徽标裁决后的最终计数)而非 computed 底座——否则徽标纠正
        # 上行时 next_tier 仍按旧计数停在前一档(低估修复,DD-021,见 _board_pairs)。
        # kernel 单一源委托(迁移批次二):同式推导收敛到
        # cw_board_state.board_next_tier_of(sim 观测键 ADR-0488 同源)。
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_next_tier_of,
        )
        state.board_next_tier = board_next_tier_of(_merged)
    else:
        state.board = _ocr_board
        state.board_next_tier = {f: nt for f, (_c, nt) in _bp.items() if nt > 0}
    # 旧不填 deployed → 恒 [] → deployed_count() 恒 0 → _saving_for_interest 永不触发(不攒息散买 gold→0)
    # + 买/deploy 门失效。identity/前后排近似(计数门用,实际槽位 CwOpDeploy SIFT 处理)。
    # 不破坏):tracked 漂移时(sell 位置式 / deploy SIFT char_id='?' 未识别)截断多的 / 补 rebuild 无身份差额。
    # active_strategies:session(持久宿主,cw_screen_invest_strategy 写)→ state(_refresh_cap 等消费;
    # live 修复 2026-08-15,原接线只加 GameState 字段无来源恒空)。
    if _match is not None and _match.session is not None:
        state.active_strategies = list(_match.session.active_strategies)
        # `w512_obs_surfaces/`(观测自检设计 §2.9/§5-B6,策略激活态事件级对拍,消费侧):
        # 「声明选中名」暂存槽在此消费——写链已先于暂存发生(handler 先
        # append session 再暂存),故本时点声明名应已在持卡列表;不在 = 写链
        # 断或选择落空 → 台账留证(中相关面,默认 L2;离线按复现分级)。
        # 消费即清,不串轮;无暂存(非投资轮)零开销。handler/策略决策零
        # 改动(纯旁路)。(注:暂存生产端已随 invest_cards 流写入端退役
        # 删除——删除波 1;槽与消费面保留,候 strategy_
        # offer 收编批重接生产端。)
        try:
            # 分包期 4:策略暂存槽迁 kernel/cw_observe、落账经 kernel/cw_telemetry_exit
            # 出口钩子位(零直依 telemetry)
            from sr_od.application.currency_war.kernel.cw_observe import (
                consume_pending_strategy_pick,
            )
            from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                record_defect,
            )
            _pick = consume_pending_strategy_pick()
            if _pick and _pick not in state.active_strategies:
                record_defect(
                    'strategy', 'invariant_break',
                    expected=f"选中的策略 {_pick!r} 进入 active_strategies",
                    observed=f"active_strategies={state.active_strategies}",
                    plane=int(getattr(state, 'plane', 0) or 0),
                    round_num=int(getattr(state, 'round_num', 0) or 0),
                    reader_source='invest_pick_vs_session',
                    note='投资选择事件 vs 持卡终态不一致(写链断/选择落空)')
        except Exception:   # noqa: BLE001  观测 best-effort
            pass
        # r358d(遥测全面性审计接线,ADR-0229 缺口清单):观察了但
        # 未回写决策 state 的恒空字段集中补——复盘(站位/环境/
        # 词缀/巨星/伙伴/连胜)与决策(mechanics_fit/boss_fit/
        # 连胜门)同源。注入点单一(此处),策略器的
        # 方向刷新注入保留(两处都幂等:非空才覆)。
        _sess = _match.session
        if getattr(_sess, 'active_env', ''):
            state.active_env = str(_sess.active_env)
        if getattr(_sess, 'briefing_bosses', None):
            state.plane_bosses = list(_sess.briefing_bosses)
        if getattr(_sess, 'briefing_affixes', None):
            state.enemy_affixes = list(_sess.briefing_affixes)
    # ADR-0392:deployed 是槽位表(定长 10 含 None)——对账/截断/补齐一律
    # 走占用序(紧缩视图),再转回槽位表;len() 恒 10 不可作计数。
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_from_compact,
        iter_occupied_deployed,
    )
    # 迁移审计 w287(git 历史)(治本,ADR-0417):部署对齐/重建目标 = 舞台 paddle「X/Y」的 X
    # (read_deployed_count)——舞台指示几何上只数已上阵角色,不含底部商店行/备战栏。
    # 旧目标 ``min(sum(state.board.values()), level)`` 把**羁绊计数**当部署数(多阵营
    # 角色重复计 + 徽标 OCR 误读放大),再驱动补齐/截断 → 幻影部署(迁移审计 w285(git 历史) deployed_align
    # 3/6 误判 + 5aa9ce34 board_ocr=17 严重误计实证;cw_screen_prep r3 同判早已把 board
    # 移出三源对拍,本处是漏改的最后一处)。paddle 读不到 = 本帧无对齐基准 → 跳过对齐
    # (宁缺勿造:补齐/截断都是用猜的数改写 tracking)。
    # 阶段 gate 路径:deployed_count 已随 cap 合并单读(见上方 resolve_paddle_pair);
    # spec 无 deployed_count 的阶段(prep_shop_open 部署不发生,关店后 CwOpDeploy
    # 另读;battle 帧无消费)_paddle_n=None → 对齐跳过/重建退 level 估,同「读不到」语义。
    _paddle_n = _paddle_x if _spec is not None else read_deployed_count(ctx, screen)
    if _tracked_dep:
        import copy
        _occ = list(iter_occupied_deployed(copy.deepcopy(_tracked_dep)))
        if _paddle_n is not None:
            if len(_occ) > _paddle_n:
                # 观察冲突审计 #10(2026-08-16):截断=双源分歧(tracked 多计于 paddle 实读,
                # 如 deploy SIFT 漂移)—— 静默截断毒化部署近似;留证供毒化率统计。
                obs_conflict('deployed_align', len(_occ), _paddle_n, screen,
                             verdict=('截断-tracked多计(paddle X 为准;处理:裁决已自动;'
                                      '频发 >10 行/时→排查 deploy SIFT 漂移'),
                             source='tracked_vs_paddle')
                _occ = _occ[:_paddle_n]   # 截断(tracked 多计,如 deploy SIFT 漂移)
            elif len(_occ) < _paddle_n:
                obs_conflict('deployed_align', len(_occ), _paddle_n, screen,
                             verdict=('补齐-tracked少计(rebuild 无身份;处理:裁决已自动;'
                                      '频发 >10 行/时→排查 rebuild 身份读取'),
                             source='tracked_vs_paddle')
                _rebuild = list(iter_occupied_deployed(
                    rebuild_deployed_from_board(state.board, state.back_max,
                                                max_count=state.level)))
                _occ = _occ + _rebuild[len(_occ):]   # 补无身份(tracked 少计,如 sell 漂移)
        state.deployed = deployed_from_compact(_occ)
    else:
        # 迁移审计 w287(git 历史)(ADR-0417):重建上限 = min(level, paddle X)——paddle X 是画面部署数
        # 事实,空板帧(paddle=0)徽标/商店行误读不再幻影出部署角色(迁移审计 w285(git 历史) tracking
        # 空板帧幻影 2 张同根);paddle 读不到退 level 估(旧行为)。
        _rebuild_cap = state.level if _paddle_n is None else min(state.level, _paddle_n)
        state.deployed = rebuild_deployed_from_board(state.board, state.back_max,
                                                     max_count=_rebuild_cap)
    # shop_cards:spec 无的阶段(prep_clean 面板未开,收起锚门本就返空 = 「没牌」
    # 观测真值;battle 帧同)直接置空列表,连锚判定都省(ADR-0462)。
    state.shop = read_shop_cards(ctx, screen) if _w('shop_cards') else []
    # r77(轮岗接线):商店开态顺手读概率条真值(60/22/15/3/0 类)——read 失败(None)时
    # 消费方(_sample_cost)自动退基线表;成功时 D 牌蒙特卡洛用实际分布。
    # spec 无的阶段(prep_clean/battle:概率条只印在开店面板,读出恒 None)跳过。
    state.refresh_probs = read_refresh_probs(ctx, screen) if _w('refresh_probs') else None
    # 席满判定 = BoardState 派生(kernel/cw_board_state.bench_is_full,§3.2.5):
    # 「备战席已满」警告出现太短暂无法可靠采样(玩家裁定 2026-09-09),本帧
    # 不产席满警告读数、GameState 亦无警告位字段;防复活墓碑 = 测试锁
    # (调用 read_bench_full 通道即红)。
    if phase is not None:
        from sr_od.application.currency_war.kernel.cw_observe import set_obs_phase
        set_obs_phase(None)   # 冲突行阶段标注随本次读取结束清位(best-effort)
    # [停机钩子·已删(2026-08-17 M72 采全)] star≥3 停机采集:19 位 fixture 已采全
    # (star3_slots/),read_star 全位置断言 3 测试过(test_star3_positions)。⚠️ 教训存档:
    # ①「停 bot 保画面」在备战不成立——备战有倒计时,到期自动出战推进(bot 停游戏不停),
    #   M72 停机后游戏自己打完了 P2-9;此类需当场交互的采集,现场窗口=倒计时前,分小批+
    #   批间验证落位;②事件 overlay(选择伙伴)盖棋盘时拖拽全部静默失败,批次必须验证;
    # ③VLM 看不清星数(开商店帧误报"银狼3星"),定位 3 星用 read_star 全帧扫描。
    # BoardState 观察流接线(迁移批次一;字段级规格正本 =
    # docs/develop/sr_od/application/currency_war/game_state/fields.md §2.1/
    # §8.7):既有读取完成后把本帧真读字段同步记入 BoardState 单例(零新增 OCR,
    # 消费切换归批次二,GameState 消费者行为零变化)。
    _feed_board_state(ctx, state, phase, screen, _spec, had_hp_real=_had_real)
    return state


def _phase_screen_context(phase: str | None, plane: int | None,
                          round_num: int | None,
                          ) -> tuple[str | None, tuple[int, int] | None]:
    """阶段键 → 画面上下域标识 + 顶栏读数(R1 §3.1.4/§3.4;映射单一源)。

    - prep_clean / None(全量路径,调用方 = 备战 heavy 环入口)→ 干净备战帧
      (:data:`SCREEN_PREP_FRAME`)——备战腿触发面;
    - prep_shop_open → 商店面板块('货币战争-备战-开商店',弹窗族成员)——
      顶栏读数 = 缓存 c,弹窗腿缓存守卫输入(判定方案 R3 规则二③);
    - battle_or_transit → 战斗/结算段内相位 token(分支级标识,弹窗腿守卫集
      成员;段内多物理屏无法细分建档名,边界申报见 kernel 常量注释);
    - 未注册阶段名(read_game_state fail-open 态)→ None = 不写(画面身份
      未知禁猜,与「禁拿兜底默认值当观察」同义)。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BATTLE_WAIT_CONTEXT,
        SCREEN_PREP_FRAME,
    )
    if plane is None or round_num is None:
        return None, None
    top: tuple[int, int] | None = (int(plane), int(round_num))
    if phase is None or phase == PHASE_PREP_CLEAN:
        return SCREEN_PREP_FRAME, top
    if phase == PHASE_PREP_SHOP_OPEN:
        from sr_od.application.currency_war.kernel.cw_obs_core import (
            SHOP_SCREEN_NAME,
        )
        return SHOP_SCREEN_NAME, top
    if phase == PHASE_BATTLE_OR_TRANSIT:
        return BATTLE_WAIT_CONTEXT, top
    return None, None   # fail-open 未知阶段:身份不猜不写


def _feed_board_state(ctx: SrContext, state: GameState, phase: str | None,
                      screen: MatLike, spec: frozenset[str] | None, *,
                      had_hp_real: bool) -> None:
    """BoardState 观察流(read_game_state 专属;迁移批次一接线)。

    read_game_state 是全部 phase 观察(prep_clean/prep_shop_open/
    battle_or_transit/全量)的唯一漏斗——本口把「本帧真读到」的字段记入
    BoardState 单例(board_state_of(session)),零新增 OCR:
    - 真读(真值位/非 None)→ observe;失读 → carry(§2.2 失读处置①,
      沿用+来源帧标注);hp 开局先验形态(读不到∧session 无真值)→ prior
      写入(§3.1.6,evidence=prior:adr-0559);
    - 逐字段门 = 本函数的 spec 门(PHASE_FIELD_SPEC 同源):spec 不含的字段
      本帧根本没读,不进 BoardState(禁拿 GameState 兜底默认值当观察——
      gold 失读 raw=0/hp 失读沿用值都不经此口);
    - hp 写入闸(§3.2.13/§8.8):hp 仅 spec 含 'hp' 且 hp_readable(真读)
      才 observe——商店开态帧该区不显示的假值(如旧 100 兜底)结构性进
      不了记录;
    - shop 附加域:spec 含 shop_cards 且读得牌 → observe payload;离开
      商店画面 → leave_screen(None = 结构事实,§2.2 例外);
    - 刷新费通道(§3.3.4/ADR-0622,任务书件 6):商店开态帧现场读刷新钮
      标价(惰性 import 防与 cw_shop_refresh_obs 循环);识别失败 = carried
      (禁兜底改值);免费帧「不写」调用方闸归 §3.3.7 接线批(批次二)。
    - streak:本函数只做 carried 沿用(session 结算带符号真值);备战幅度
      读数无方向,禁覆盖带符号值(§3.2.12)。

    **席位观察通道声明(漏斗单一性的在册边界,与 §3.2.5 观察写端申报
    同源)**:bench/本口外的席位域观察写端 = 备战装配环
    (operations/cw_screen/cw_screen_prep 的 heavy 装配块,bench 喂入先例
    + deployed front_row/back_row 喂入)与装备分配链(prep_actions
    装备区现读)——SIFT/装备区读是重读链,不进逐帧漏斗(防双跑成本);
    spec 门(PHASE_FIELD_SPEC)因此**不加** bench/deployed/equips 键
    (键辖域 = read_game_state 的读段,这些域不经本漏斗读;deploy_cap
    键已在册,容器喂入沿用既有键门)。

    best-effort:任何异常不阻塞 read_game_state 返回(记录层故障不毒化
    决策链;诊断走 [cw!][bs-feed] 日志)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_board_state import (
            ChannelSig,
            NodeKey,
            ShopPayload,
            board_state_of,
        )
        match = getattr(ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return
        bs = board_state_of(session)
        frame = f'p{state.plane}-r{state.round_num}'
        # 渠道①签名(R5 W1 显式签名铺满,ADR-0634;§3.2.1 ①类属 = 观察汇聚
        # 模块):真读/沿用两 mode 各一;hp 等带质量维的专项 sig 在各自写点。
        _sig_read = ChannelSig(family='obs', actor='cw_observation',
                               mode='read')
        _sig_carry = ChannelSig(family='obs', actor='cw_observation',
                                mode='carried')

        def _w(key: str) -> bool:
            """本帧是否读了该字段(spec 同源;None 阶段=全量恒 True)。"""
            return spec is None or key in spec

        # 节点(phase_round 全阶段必读;node_type 仅 spec 门内为帧读值)。
        # P1-1(落地审):kind 未读帧(battle_or_transit spec 无 node_type /
        # 备战帧三源仲裁全空)禁合成 'prep' 占位假值(§2.2 失读口径;与本口
        # 「禁拿兜底默认值当观察」同义)——kind 从 bs.node 现值继承合成新键
        # (plane/round 真读更新),evidence 标继承;无现值且未读 → 不写
        # (禁猜)。kind 的权威写端 = 结算屏三源仲裁(§3.5.2/§3.2.1),批次二
        # 接线;继承窗口内 kind=「上一已知节点类型」,备战帧真读即覆盖。
        node_type = state.node_type if _w('node_type') else None
        if node_type is not None:
            bs.observe(bs.node, NodeKey(plane=int(state.plane or 1),
                                        round_num=int(state.round_num or 1),
                                        kind=str(node_type)),
                       sig=_sig_read)
        else:
            _prev_node = bs.node.value
            if _prev_node is not None:
                bs.observe(bs.node,
                           NodeKey(plane=int(state.plane or 1),
                                   round_num=int(state.round_num or 1),
                                   kind=_prev_node.kind),
                           evidence='kind_inherited', sig=_sig_read)
            # 无现值且未读:node 不写,保持 None(诚实缺位)
        if _w('gold'):
            if state.gold_readable:
                bs.observe(bs.gold, int(state.gold), sig=_sig_read)
            else:
                bs.carry(bs.gold, frame=frame,
                         sig=_sig_carry)   # raw 0 是 miss 兜底,禁入记录
        if _w('level'):
            if state.level_readable:
                bs.observe(bs.level, int(state.level), sig=_sig_read)
            else:
                bs.carry(bs.level, frame=frame,
                         sig=_sig_carry)   # 启发式兜底值不是观察(§2.2)
        if _w('xp') and state.xp_progress is not None:
            bs.observe(bs.xp, tuple(state.xp_progress), sig=_sig_read)
        if _w('hp'):
            # v3.2-G1:判读面质量标记照落 sig.quality(决策可信位
            # hp_readable/hp_trusted 保留 GameState 决策域读面不经流水;
            # 词表 = real_read/same_node_carried/prior,§3.2.1 起步词表)。
            if state.hp_readable:
                bs.observe(bs.hp, int(state.hp), sig=ChannelSig(
                    family='obs', actor='cw_observation', mode='read',
                    quality={'hp': 'real_read'}))
            elif state.hp is not None and not had_hp_real:
                # 对账层开局先验形态(session 无真值,ADR-0559)
                bs.write_prior(bs.hp, int(state.hp), evidence='prior:adr-0559',
                               sig=ChannelSig(
                                   family='obs', actor='cw_observation',
                                   mode='prior', quality={'hp': 'prior'}))
            elif state.hp is not None:
                bs.carry(bs.hp, frame=frame, sig=ChannelSig(
                    family='obs', actor='cw_observation', mode='carried',
                    quality={'hp': 'same_node_carried'}))   # ADR-0431
        if _w('enemy_difficulty'):
            if getattr(state, 'enemy_difficulty_live', False) \
                    and state.enemy_difficulty is not None:
                bs.observe(bs.enemy_difficulty, int(state.enemy_difficulty),
                           sig=_sig_read)
            else:
                bs.carry(bs.enemy_difficulty, frame=frame,
                         sig=_sig_carry)   # session 恒值=沿用
        if _w('level_up_cost') and state.level_up_cost is not None:
            bs.observe(bs.level_up_cost, int(state.level_up_cost),
                       sig=_sig_read)
        if _w('deploy_cap'):
            # deploy_cap 观察写端(W5 入容器,§2.3;spec 键已在册,容器喂入
            # 沿用既有键门):采信门输出才 observe——防抖核
            # (read_deploy_cap_debounced/_debounce_cap,ADR-0420 双帧一致)
            # 已在读取半部,None = 拒信/失读帧 → carry 沿用(§2.2 处置①;
            # 宝钻只增不减,沿用值方向安全),禁拿 None/兜底当观察。
            if state.deploy_cap is not None:
                bs.observe(bs.deploy_cap, int(state.deploy_cap),
                           sig=_sig_read)
            else:
                bs.carry(bs.deploy_cap, frame=frame, sig=_sig_carry)
        if _w('streak') and state.streak is not None:
            bs.carry(bs.streak, frame=frame,
                     sig=_sig_carry)   # 结算带符号真值的跨帧沿用
        if _w('board'):
            if state.board_readable and state.board:
                bs.observe(bs.board, dict(state.board), sig=_sig_read)
            else:
                bs.carry(bs.board, frame=frame, sig=_sig_carry)
        if _w('shop_cards'):
            if state.shop:
                # 牌转换 = kernel 映射单一源(W5 双 ShopCard 归一);
                # cost_source 原值透传不折叠(roster_fallback 的「徽章失读」
                # 证据分级禁丢,词表见 BoardState.ShopCard)
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    shop_card_to_container,
                )
                cards = [shop_card_to_container(c) for c in state.shop]
                probs = ({int(k): float(v) for k, v in
                          (state.refresh_probs or {}).items()}
                         if state.refresh_probs else {})
                bs.observe(bs.shop, ShopPayload(cards=cards,
                                                refresh_probs=probs),
                           sig=_sig_read)
            # 空牌面 = OCR 失读帧:不写(宁缺勿造;§2.2 口径由 carry 通道
            # 不适用于 payload 域,保持现值等下一帧)
        elif bs.shop.value is not None:
            bs.leave_screen(bs.shop,
                            sig=_sig_read)   # 离开商店画面 = 结构事实(§2.2 例外)
        if phase in (PHASE_PREP_SHOP_OPEN,):
            # 刷新费现场识别通道(ADR-0622;§3.3.4 识别失败=None 禁兜底)。
            # 写入口经按钮态 composite(T-13 读链接入):免费态按钮渲染的
            # 剩余次数与标价**同 rect**——免费帧次数数字会被标价解析误读,
            # 「免费帧不写」的免费判定输入 = 按钮态锚命中(结构性满足),
            # 不再依赖「免费帧渲染无数字」旧假设(T-15 实机取证推翻:
            # 免费帧 = 「免费刷新」+次数)。非免费帧 price 语义与旧直读
            # 逐位一致(锚失读/未中分支 composite 内部同源 read_shop_
            # refresh_price);免费帧 → carry 沿旧值(§3.3.4 None≠0 同门)。
            from sr_od.application.currency_war.obs.cw_shop_refresh_obs import (
                read_shop_refresh_button,
            )
            # 灰态判别走逻辑面金价对比(不可用态判别两案比选定谳:暗钮模板
            # =表现层拟合,单帧定阈无鲁棒性证据且 UI 改版即碎,冻结后备;
            # 金价对比 =语义层直编机制规则「置灰⟺金<标价」,price 灰态可读
            # 经归档灰态帧真 OCR 实证)。gold 复用调用方 read_game_state
            # 本帧已读的 state.gold(同帧零新增读);失读保真传 None(禁 0
            # 假值)→ affordable=None 按失读处理,不猜可负担。
            _btn = read_shop_refresh_button(
                ctx, screen,
                gold=(int(state.gold) if state.gold_readable else None))
            if _btn.free is not True and _btn.price is not None:
                bs.observe(bs.shop_refresh_cost, int(_btn.price), sig=_sig_read)
            else:
                bs.carry(bs.shop_refresh_cost, frame=frame, sig=_sig_carry)
        # —— 开局域/持卡/环境镜像(迁移批次二,§3.1/§3.4;任务书件 8)——
        # 载体中继收敛(§2.1,批次二扩单件 3):这些字段的真写端在各自画面
        # (难度确认屏/简报/事件屏 handler),中继只补写**从未写过**的字段
        # (source=logic + evidence='session_carrier',已有正式值一律跳过——
        # 禁把 handler 已写的 logic 翻成 observation);值恒等(同一事实),
        # 归档 bs_prov 按 evidence 可分。
        # 渠道③签名(§3.2.4 relay 契约):中继走 logic_hook 族,actor =
        # 本汇聚模块,行内身份可对账(R5 W1 起签名必填,ADR-0634)。
        from sr_od.application.currency_war.kernel.cw_board_state import (
            ChannelSig as _ChannelSig,
        )
        _relay_sig = _ChannelSig(family='logic_hook', actor='cw_observation',
                                 mode='compute')
        bs.relay(bs.active_strategies, list(state.active_strategies),
                 sig=_relay_sig)
        bs.relay(bs.active_env, str(state.active_env), sig=_relay_sig)
        bs.relay(bs.plane_bosses, list(state.plane_bosses), sig=_relay_sig)
        bs.relay(bs.enemy_affixes, list(state.enemy_affixes), sig=_relay_sig)
        # equips 装备库存(W5 申报面,方案 §2.2):观察写端 = 装备分配链
        # 装备区现读(prep_actions._build_equip_wear_plan 两分支,本漏斗
        # 无装备区读——零新增读原则);本口只做载体中继兜底(session 镜像
        # last_owned_equips,从未写过才补)。**接线滞后窗值冻结申报**:
        # 开箱/穿戴/卖出等动作时点的库存变化先落 session 镜像,bs 只在
        # 下一次装备链现读时刷新——中继「已有正式值跳过」语义使滞后窗内
        # 视图拿到的是上一次观察值(带 logic 源标记),比透传陈值可分。
        _owned_equips: list = getattr(session, 'last_owned_equips', None) or []
        bs.relay(bs.equips, [str(n) for n in _owned_equips],
                 sig=_relay_sig)
        _sel_diff = getattr(session, 'selected_difficulty', '') or ''
        bs.relay(bs.selected_difficulty, str(_sel_diff), sig=_relay_sig)
        # —— 画面上下文 + 节点推进派生(R1 §3.1.4/§3.4;R5 W1 常开)——
        # 本口 = read_game_state 唯一漏斗 = 观察汇聚模块(上下文域唯一写点):
        # 随分派观察写 prev/current 上下文对,同临界区跑四腿派生规则(备战腿
        # 在干净备战帧直读顶栏;弹窗腿在守卫通过时推断;判定规则本体 =
        # 判定方案单一源)。阶段键 → 画面标识映射:battle_or_transit = 战斗/
        # 结算段内相位(多物理屏,按 prev_branch 语义记分支 token,弹窗腿
        # 守卫集成员);phase None(全量路径,调用方 = 备战 heavy 环入口)按
        # 干净备战帧记。写入无条件(journal 常开,R5 W1 影子闸折叠——
        # ADR-0634;行落盘另以 sink/run_id 在场为准)。
        _ctx_name, _ctx_top = _phase_screen_context(
            phase, state.plane, state.round_num)
        if _ctx_name is not None:
            # D2 live 接线(R1 缺口承接):恢复局旗标(session 执行态,
            # 写端 = cw_loop 恢复检测两确认点)透传进派生规则——恢复局
            # 弹窗腿在 hist 空时禁用不猜(判定方案规则六)。
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                exec_state_of as _exec_state_of,
            )
            _resumed = bool(_exec_state_of(session).cw_resumed_match)
            bs.observe_screen_context(
                _ctx_name, phase_round=_ctx_top, resumed=_resumed,
                sig=_ChannelSig(family='obs', actor='cw_observation',
                                screen=_ctx_name, mode='read'))
        bs.mark_frame_obs('view' if spec is not None else 'full')
    except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化决策链
        log.warning('[cw!][bs-feed] BoardState 观察流跳过: %s', e)


# → 无法可靠选 deploy comp 卡 + pref 定位。pixel-diff(buy 前/后 bench 截图 diff)找新占槽 = bought 卡落点,
BENCH_SLOT_DIFF_THRESHOLD: float = 10.0   # absdiff 均值阈值;新 char icon 显著 > 此(校准待实跑)


def new_bench_slots(ctx: SrContext, before: MatLike, after: MatLike) -> list[int]:
    """buy 前/后 bench 哪些物理槽(1..9)新被占(pixel-diff:新 char icon 出现 → 高 absdiff 均值)。

    char→slot 感知根解。返回新占槽 idx 列表(**left-to-right 升序** = buy 顺序,因 bench 从左到右填)。
    调用方(buy op)把本结果与同轮 bought 卡名(buy 顺序)zip → char→slot map。无需角色身份(纯像素,可靠)。
    """
    log.info('[cw-bench-diff] new_bench_slots CALLED')
    si = ctx.screen_loader.get_screen('货币战争-备战')
    if si is None:
        return []
    changed: list[int] = []
    for i in range(1, 10):
        area = next((a for a in si.area_list if a.area_name == f'备战栏-{i}'), None)
        if area is None or area.pc_rect is None:
            continue
        _r = area.pc_rect   # Rect 对象(有 .x1/.y1/.x2/.y2 属性,非可迭代;旧 `x1,y1,x2,y2=pc_rect` 致 TypeError)
        x1, y1, x2, y2 = _r.x1, _r.y1, _r.x2, _r.y2
        b = before[y1:y2, x1:x2]
        a = after[y1:y2, x1:x2]
        if b.size == 0 or a.size == 0:
            continue
        diff = float(cv2.absdiff(b, a).mean())   # 新 icon → 多像素变化 → 高均值
        if diff > 1.0:
            log.info(f'[cw-bench-diff] slot{i} diff={diff:.1f}')
        if diff > BENCH_SLOT_DIFF_THRESHOLD:
            changed.append(i)
    return changed   # 已 left-to-right(slot idx 升序,range 1..9)


# ============================================================ 局终判定面(R5 W2;归层=遥测层)
#
# 对局结束识别的判定核心,唯一落点 = 本节(消费方 = 未来 cw_loop 收口写点/
# 启动扫描补写/判读回放,均判据只读、零新增画面建档)。判定面以现有建档
# 判据为基:胜利/失败复用在产结算观察链判据(killed 显式败局 / 回大厅收口
# 的 plane==3 通关语义),主动停止复用 run_context 停止语义,异常终局 =
# 无收口证据的补写形态(标 abnormal,写口见 kernel ``write_match_final``)。


def runs_result_to_final_type(result: str) -> str | None:
    """现役 runs ``result`` 词表 → 局终类型收编映射(retirement.md §2 runs 行)。

    win/loss/stopped 同名直映;abandoned 及其余非完结值(含空串)= abnormal
    (非完结值域 = 异常终局家族,与档案装配器 ``_TERMINAL_RESULTS`` 的
   完结判定同界);None 不出现——空串也归 abnormal,调用方无须判空。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        FINAL_ABNORMAL,
        FINAL_LOSS,
        FINAL_STOPPED,
        FINAL_WIN,
    )
    if result == 'win':
        return FINAL_WIN
    if result == 'loss':
        return FINAL_LOSS
    if result == 'stopped':
        return FINAL_STOPPED
    return FINAL_ABNORMAL


@dataclass(frozen=True)
class MatchFinalDraft:
    """局终判定产出(段级;喂 :func:`kernel.cw_board_state.write_match_final`
    的判据半)。``ts`` = 判定锚行时间戳(回放对账用);``evidence`` = 命中的
    证据通道名(runs_summary/terminal_closure/no_close_evidence——本函数三
    通道;在线判定面 :func:`resolve_final_type` 不经本通道词表)。
    """

    final_type: str
    plane: int | None = None
    round_num: int | None = None
    hp: int | None = None
    ts: str = ''
    evidence: str = ''


def resolve_final_type(*, stop_requested: bool, saw_defeat: bool,
                       plane_reached: int | None,
                       rounds_played: bool = True) -> str | None:
    """在线判定面核心(回大厅收口/收口兜底共用;纯函数)。

    判定序 = 主动停止 > 失败 > 通关(与在产收口语义同序:cw_loop 3c 分支
    ``won = plane==3 ∧ ¬败局闩``、W75 收口 ``stopped = is_context_stop``):

    - ``stop_requested``(run_context 停止语义)→ 'stopped';
    - ``saw_defeat``(败局闩 = 结算观察链见过显式败局帧)→ 'loss';
    - ``plane_reached == 3`` 精确值(假 win 守卫同口径,ADR-0392 时代实证:
      OCR 难度泄漏会读出 plane=8,禁 >=)且非败局 → 'win';
    - 未打过任何结算轮(``rounds_played=False``)→ None(开局失败形态,
      非终局——与 3c 假局守卫同判,禁拼假终局行);
    - 其余(未停止、无败局、plane<3 的真实结束)→ 'abnormal'。

    消费契约:返回值直接作 ``write_match_final(final_type=…)`` 入参;
    None = 调用方跳过收口。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        FINAL_ABNORMAL,
        FINAL_LOSS,
        FINAL_STOPPED,
        FINAL_WIN,
    )
    if stop_requested:
        return FINAL_STOPPED
    if saw_defeat:
        return FINAL_LOSS
    if plane_reached == 3:
        return FINAL_WIN
    if not rounds_played:
        return None   # 开局失败形态:非终局(假局守卫同判)
    return FINAL_ABNORMAL


def _int_or_none(v: Any) -> int | None:
    """行值 → int(None/bool/畸形 = None,不猜)。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return int(v)


def detect_match_final(*, run_id: str,
                       runs_summary: dict | None = None,
                       outcome_rows: list[dict] | None = None,
                       journal_final: dict | None = None,
                       ) -> MatchFinalDraft | None:
    """段级局终判定(离线回放/判读读面形态;在线消费同判据经
    :func:`resolve_final_type`)。

    证据阶梯(先到先定,通道名记入 ``evidence``):
    1. ``journal_final``(新账局终行在档)→ None(本段已收口,幂等跳过);
    2. ``runs_summary``(现役收口行,收编对象)→ result 经
       :func:`runs_result_to_final_type` 映射,plane/round/hp 取行值;
    3. terminal_closure 结算行(source='terminal_closure',T-185 收口行;
       match_result 值 = 收口时点的对局级结果)→ 同映射;
    4. 无收口证据(断流/进程死亡)→ abnormal(补写形态判据,G8:启动
       扫描按本判定补写,note=recovered 显影)。

    ``outcome_rows`` = 本段结算观察行(现役结算观察链产物;阶梯 3 的证据源)。
    纯读函数,零副作用。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        FINAL_ABNORMAL,
    )
    if journal_final is not None:
        return None   # 新账已收口:幂等跳过
    summary = runs_summary if isinstance(runs_summary, dict) else None
    if summary is not None:
        return MatchFinalDraft(
            final_type=runs_result_to_final_type(str(summary.get('result') or '')),
            plane=_int_or_none(summary.get('plane_reached')),
            round_num=_int_or_none(summary.get('rounds_survived')),
            hp=_int_or_none(summary.get('final_hp')),
            ts=str(summary.get('ts') or ''),
            evidence='runs_summary')
    for r in (outcome_rows or []):
        if str(r.get('source') or '') != 'terminal_closure':
            continue
        return MatchFinalDraft(
            final_type=runs_result_to_final_type(
                str(r.get('match_result') or '')),
            plane=_int_or_none(r.get('plane')),
            round_num=_int_or_none(r.get('round_num')),
            hp=None,
            ts=str(r.get('ts') or ''),
            evidence='terminal_closure')
    return MatchFinalDraft(final_type=FINAL_ABNORMAL, plane=None,
                           round_num=None, hp=None, ts='',
                           evidence='no_close_evidence')
