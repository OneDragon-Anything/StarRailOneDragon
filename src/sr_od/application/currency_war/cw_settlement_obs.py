"""货币战争 结算屏观测(P1.5 观测回路):战后小队 HP。

结算屏(战斗后「挑战结束/数据统计/继续挑战」)展示战后小队 HP「小队生命值<N>」+ 总伤害等
(2026-08-05 实跑 OCR 确认形态:['挑战结束','战斗','小队生命值71i','数据统计','连胜×0','继续挑战'])。
``parse_settlement_hp`` 纯函数(可单测);``read_round_outcome`` OCR 全屏调它 → ``RoundOutcome``
(``on_round_end`` 输入,性能 trend 用)。node_type/comp_tag/plane/round 由调用方(loop)传入
(结算屏不暴露这些)。

共享常量(HP_MIN/HP_MAX)在 ``cw_obs_core``。本模块被 ``cw_observation`` re-export。
"""
from __future__ import annotations

import re

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_obs_core import HP_MAX, HP_MIN
from sr_od.context.sr_context import SrContext


def parse_settlement_node_type(ocr_texts: list[str]) -> str | None:
    """结算屏节点类型(纯函数;r366,ADR-0239)→ 中文标准词或 None。

    权威源 = 结算屏自身头部:``挑战成功/挑战结束`` 后 1-4 个 token 内
    出现的类型词(奖励/战斗/遭遇/补给/首领)。实跑 token 形态(2026-08-22
    局48 七轮实锤):
    - reward: ['挑战成功','奖励','Lv.3',...]
    - battle: ['挑战成功','1-3X点','战斗','火热连胜×1',...]('1-N'带 OCR 噪声)
    - encounter: ['挑战结束','遭遇','火热连胜×0',...]
    精确 token 匹配(非包含):'基础奖励'≠'奖励' 不会误中(r260 弃结算屏
    OCR 的旧顾虑是全屏搜'奖励'误中金币区——邻位窗口+精确匹配根除)。
    读时点 = record outcome 那一刻的同一张屏,零跨帧状态,首节点覆盖。
    """
    _TYPES = {'战斗': '普通战斗', '奖励': '奖励', '遭遇': '遭遇',
              '补给': '补给', '首领': 'boss', '巨星': '巨星'}
    _hdr = next((i for i, t in enumerate(ocr_texts)
                 if '挑战成功' in t or '挑战结束' in t), None)
    if _hdr is None:
        return None
    # r366b(review B1):窗口扩到 hdr 自身(OCR 把头部与类型词粘成
    # '挑战成功战斗' 的形态)+ 带前缀形态匹配(emoji/词缀 '👩首领')。
    # 前缀白名单(而非长度门——'基础奖励' 4 字也过长度门,实测误中):
    # 允许 = 头部词本身(粘着)与 ≤1 个装饰字符(emoji/点号);修饰词
    # 前缀('基础''火热'等)不在白名单 → 拒。
    _ALLOWED_PREFIX = ('挑战成功', '挑战结束', '👩', '●', '★')
    _TYPES = {'战斗': '普通战斗', '奖励': '奖励', '遭遇': '遭遇',
              '补给': '补给', '首领': 'boss', '巨星': '巨星'}

    def _match(t: str) -> str | None:
        if t in _TYPES:
            return _TYPES[t]
        for k in _TYPES:
            if t.endswith(k):
                _pre = t[:-len(k)]
                if _pre in ('',) or any(_pre.startswith(p) for p in _ALLOWED_PREFIX):
                    return _TYPES[k]
        return None
    for t in ([ocr_texts[_hdr]] + ocr_texts[_hdr + 1:_hdr + 5]):
        _m = _match(t)
        if _m is not None:
            return _m
    return None


def parse_settlement_hp(ocr_texts: list[str]) -> int | None:
    """结算屏「小队生命值<N>」→ hp_after(纯函数,可单测;P1.5)。

    取含「生命值」的文本,解析其**紧邻后方**的数字(``生命值\\s*(\\d+)``)—— 紧邻而非首部/尾部,
    防「每损失20点小队生命值获得5」(投资策略描述,偶同屏)误取 20/5。越界(HP_MIN..HP_MAX)→ 丢弃。
    """
    for t in ocr_texts:
        # OCR 偶 garble「生命值」→「命值」(missing 生);两形态都匹配(2026-08-07 实跑 on_round_end hp=0 根因)。
        for kw in ('生命值', '命值'):
            if kw in t:
                m = re.search(kw + r'\s*(\d+)', t)
                if m:
                    v = int(m.group(1))
                    if HP_MIN <= v <= HP_MAX:
                        return v
    return None


def parse_streak(ocr_texts: list[str]) -> int:
    """结算屏「连胜×N」/「连败×N」→ 带符号 streak(连胜 + / 连败 − / 未读到 0;纯函数可单测)。

    fixture 核实(2026-08-11):结算屏 OCR 含 '连胜×0' 形态,**前缀连胜/连败 = 方向**(read_streak
    备战只读 magnitude 无方向)。OCR 偶把 × 读成 x/X/*;前缀与尾随数字在同一 token。
    """
    for t in ocr_texts:
        if '连胜' in t or '连败' in t:
            m = re.search(r'(\d+)', t)
            if m:
                n = int(m.group(1))
                return n if '连胜' in t else -n
    return 0


def parse_node_type(ocr_texts: list[str]) -> str:
    """结算屏节点类型(r260/r265;纯函数):节点名行「X-Y遭遇/奖励/战斗」
    → 遭遇/奖励/普通战斗。

    防误判(r265 实锤:胜利结算被误判奖励):金币区 token
    「基础奖励」「获得金币总览」含「奖励」——排除词表拦下;
    节点名行形态 = 独立短 token「遭遇」/「奖励」或「X-Y遭遇」
    粘连形态(实锤:局16 r1 '遭遇' 独立块 / r3 误判帧含
    '基础奖励')。
    """
    _EXCLUDE = ('基础奖励', '金币', '总览', '奖励已')
    for t in ocr_texts:
        if any(w in t for w in _EXCLUDE):
            continue
        if '遭遇' in t:
            return '遭遇'
        if t.strip() == '奖励' or re.match(r'^\d-\d奖励', t.strip()):
            return '奖励'
    return '普通战斗'


def parse_settlement_progress(ocr_texts: list[str]) -> int | None:
    """结算屏「挑战进度 ±N」→ 带符号进度增量(纯函数;2026-08-18 用户点破接)。

    **胜负+扣血的游戏内真值记录**(用户 2026-08-18:「扣血其实就是战斗失败,这个玩法里
    应该有记录」):赢 = 正进度(挑战进度 +2,live 11:32 样本),输 = 负进度(M41 实锤
    「2-1战斗 -22 挑战进度」——**数字前置**形态)。OCR 三形态:
    ① 同 token 粘连('挑战进度+2');
    ② 后随分离 token('挑战进度' '+2';注意「挑战成功」屏另有**无符号累计值**形态
      '挑战进度' '46' —— 裸数字无号 = 累计进度非 delta,不取,防 -22 被记成 +46);
    ③ 前置分离 token('-22' '挑战进度',战败屏)。
    未读到 → None。
    """
    for i, t in enumerate(ocr_texts):
        if '挑战进度' not in t:
            continue
        # 形态①:同 token 粘连(挑战进度+2 / 挑战进度-22)
        m = re.search(r'挑战进度\s*([+-]\d+)', t)
        if m:
            return int(m.group(1))
        # 形态②:后随分离 token —— 仅带符号数(裸数字=累计值不取)
        if i + 1 < len(ocr_texts):
            m2 = re.search(r'^\s*([+-]\d+)$', ocr_texts[i + 1].strip())
            if m2:
                return int(m2.group(1))
        # 形态③:前置分离 token('-22' '挑战进度',战败屏;同样要求独立带符号 token)
        if i > 0:
            m3 = re.search(r'^\s*([+-]\d+)$', ocr_texts[i - 1].strip())
            if m3:
                return int(m3.group(1))
    return None


def parse_settlement_won(ocr_texts: list[str]) -> bool | None:
    """结算屏胜负真值(纯函数;2026-08-18):「挑战成功」→ 赢;「挑战进度」负 → 输;
    其余(无法判定)→ None。输轮结算屏形态 = 「挑战结束」+ 前往结算(无「挑战成功」)。"""
    if any('挑战成功' in t for t in ocr_texts):
        return True
    if any('挑战失败' in t for t in ocr_texts):
        return False   # 团灭终局
    if parse_settlement_progress(ocr_texts) is not None:
        return parse_settlement_progress(ocr_texts) > 0
    return None


def read_round_outcome(ctx: SrContext, screen: MatLike, *, plane: int, round_num: int,
                       comp_tag: str, node_type: str = '普通战斗'):
    """结算屏 → ``RoundOutcome``(观测回路 P1.5;``on_round_end`` 输入)。

    OCR 全屏 → ``parse_settlement_hp`` 得 hp_after;解析成功 hp_confidence=1.0(进 trend),失败 0.0
    (< ``HP_CONFIDENCE_THRESHOLD`` 不进 trend,防噪声)。plane/round_num/comp_tag 由调用方
    (loop)传入。node_type:**结算屏自身解析优先**(r366/ADR-0239——局48 实锤 prep 流
    RunBuyPhase 下 EnsureShopClosed 零执行,node_type 生产链全死,传参恒回退普通战斗);
    解析不出再退调用方传入值(备战期 nodeseq 链,当前流下常 None→普通战斗)。

    ✅ 已接线(2026-08-07 起):battle_loop._record_round_outcome(分支3)每轮胜结算屏调用 →
    strategy.on_round_end → performance.record + telemetry.record_outcome(2026-08-16 补)。
    """
    from sr_od.application.currency_war.cw_performance import RoundOutcome
    ocr_texts = [r.data for r in ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, crop_first=False)]
    hp = parse_settlement_hp(ocr_texts)
    # r366(ADR-0239):结算屏头部类型词 = 节点类型权威源(读时点=记录时点,
    # 零跨帧状态;首节点/备战流变化均免疫)。解析出即覆盖传参。
    # r366b(review B3):传参='boss'(battle_loop 专项 OCR '首领',证据更强)
    # 不被屏面解析降级覆盖——屏面误读'战斗'会把 boss 3.0 期望拉到 1.0。
    _st_node = parse_settlement_node_type(ocr_texts)
    if (_st_node is not None and _st_node != node_type
            and node_type != 'boss'):
        log.info('[cw-settle] node_type 结算屏真值「%s」覆盖传入「%s」(r366)',
                 _st_node, node_type)
        node_type = _st_node
    # 失败结算屏(「挑战失败」= 团灭)→ hp_after=0 确定(parse_settlement_hp 在失败屏常读到
    # 「生命值❤!」等非数字 → None,但失败 = hp 0 是 ground truth)。boss 结算屏「挑战结束」无
    # 「生命值」前缀(只裸数字)→ 暂 conf=0(后续实机核实 boss 结算屏 hp 位置 refine)。
    if hp is None and any('挑战失败' in t for t in ocr_texts):
        hp = 0
    # 胜负+进度真值(2026-08-18 用户点破:「扣血=战斗失败,游戏内有记录」):
    # killed = 「挑战成功」/负进度判定;progress_delta = 挑战进度带符号值(赢 +2/输 -22)。
    # 旧版 killed 恒 None + 输轮(挑战结束+前往结算,走 loop 3b)从不产生 outcome 行 →
    # telemetry 只见赢轮,「P2 输给谁/扣多少」全盲。
    _won = parse_settlement_won(ocr_texts)
    # [采集钩子·临时,采完删(r63)]连胜档金真值:结算屏「获得金币总览」分行(基础奖励/
    # 利息/连胜)只在整屏 OCR 可见 —— read_round_outcome 的调用方传的 screen 是整屏,此处
    # 连胜 ≥5 时存整屏(去重),离线拆「连胜 ×N → 连胜金」真值表,替换 _refresh_cap 的保守门。
    # (r72-73 收窄:3/4 档已 VLM 双样本验证完毕,只缺 5/6 档样本 → 条件 3→5)
    try:
        _streak_raw = parse_streak(ocr_texts)
        if _streak_raw >= 5:
            from sr_od.application.currency_war.cw_observe import cw_shot_unique
            cw_shot_unique(screen, f'streak_gold_st{_streak_raw}')
    except Exception:   # noqa: BLE001  采集 best-effort
        pass
    return RoundOutcome(
        round_num=round_num, plane=plane, node_type=node_type, comp_tag=comp_tag,
        hp_after=hp if hp is not None else 0,
        hp_confidence=1.0 if hp is not None else 0.0,
        streak=parse_streak(ocr_texts),   # 结算「连胜×N」前缀=方向(C 杠杆 2/3;fixture 核实 2026-08-11)
        killed=_won,
        progress_delta=parse_settlement_progress(ocr_texts),
    )
