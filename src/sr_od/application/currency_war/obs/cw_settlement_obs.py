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

from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import HP_MAX, HP_MIN
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


def parse_settlement_round(ocr_texts: list[str]) -> tuple[int, int] | None:
    """结算屏头部「X-Y」→ (plane, round)(纯函数;W28 缺陷①修 a)。

    relaunch 残留结算屏场景(W23 定因):run 启动首帧即结算屏(上一进程留下),
    loop 的 last-known plane/round 缓存已被 reset → read_phase_round 兜底 (1,1)
    → 残留屏上的真实轮次(如 r6 结算)被错记成 r1。结算屏**头部自身**带
    「X-Y」轮次标识(实跑 token 形态:['挑战结束','1-6','战斗',...],与
    parse_settlement_node_type 同一窗口),此处直接解析恢复真值。

    - 只在头部(挑战成功/挑战结束)后 5 token 窗口内找(防误中远处数字对);
    - 值域守卫:plane∈1-3、round∈1-9(嵌进正则字符类;位面/轮次越界=OCR 假阳);
    - 前后不得紧邻数字(``(?<!\\d)``/``(?!\\d)``:防「11-6」这类粘连噪声的子串误取)。
    解析不出 → None(调用方保留 last-known 兜底值)。
    """
    _hdr = next((i for i, t in enumerate(ocr_texts)
                 if '挑战成功' in t or '挑战结束' in t), None)
    if _hdr is None:
        return None
    for t in ocr_texts[_hdr:_hdr + 5]:
        m = re.search(r'(?<!\d)([1-3])\s*-\s*([1-9])(?!\d)', t)
        if m:
            return int(m.group(1)), int(m.group(2))
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


# W40:「数据统计」面板伤害列区(结算屏右侧;win/ended 两 fixture 实测校准,
# 2026-08-25)——「数据统计」标题下方右列,每角色一行伤害值(「396.3万」形,
# 实测 token x∈[1196,1280]、行 y 随上阵数下探;区放宽留边)。1080p 坐标
# (项目既有前提,截图像素与游戏空间 1:1)。
_STAT_COL_RECT = (1130, 580, 1310, 860)


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


def parse_settlement_damage(items: list) -> int | None:
    """结算屏「数据统计」面板己方伤害求和 → damage_dealt(纯函数;W40)。

    W23 定谳:结算屏无敌方血量通道,「数据统计」面板的**己方角色伤害明细**
    是 enemy_hp_after 的最接近语义代理(面板求和≈总输出,与敌方剩余血量强
    负相关)。面板**就在结算屏本体右侧列**(win/ended 两 fixture 实锤:
    「数据统计」标题 (~1120,554) 下方,每角色一行「试用」徽标 + 伤害值
    「396.3万」/「137.0万」形,**无需点开放大镜子面板**)——本函数与
    ``parse_settlement_hp`` 消费**同一帧**全图 OCR(``items`` 带坐标,按
    image 缓存零额外识别),读点 = ``_record_round_outcome`` 记录时点
    (继续挑战点击前),零跨帧状态。

    判据(双守卫):① token = 「<数字>万」形(``396.3万`` → 3963000;金币
    明细的裸数字 10/5/4 无「万」后缀,天然区分);② 检测框中心落在右列
    区(``_STAT_COL_RECT``;左侧金币列同形噪声的第二道防线)。求和所有
    命中行;无命中 → None(面板不可见/OCR 未读,不冒认 0)。
    """
    x1, y1, x2, y2 = _STAT_COL_RECT
    total = 0
    hit = False
    for it in items:
        t = (getattr(it, 'data', '') or '').strip()
        m = re.fullmatch(r'(\d+(?:\.\d+)?)万', t)
        if not m:
            continue
        cx = it.x + (getattr(it, 'width', 0) or 0) / 2
        cy = it.y + (getattr(it, 'height', 0) or 0) / 2
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            total += int(round(float(m.group(1)) * 10000))
            hit = True
    return total if hit else None


# ===== W414 结算屏金币明细采集钩子(capture-only,临时,采够删整段) =====
# 采集目标:钉死败轮收入残差成分——败轮发金 2/4 里「基础奖励」与「连胜」分量各占多少
# (评估依据 = .debug/temp/currency_war/w409_streak_calib_eval/REPORT.md §4,支撑 sim
# 收入口径修正批)。主方案 = read_round_outcome 既有 OCR 帧同帧解析明细行(零额外截图);
# 兜底 = 整屏 cw_shot_unique 落盘(内容哈希去重),OCR 解析失败帧离线判读可修复 reader。
# 生命周期(W409 预估 ~30-50 局可读明细钉死):无条件触发、零行为影响(best-effort,
# 异常全吞);**采够后删整段**——从本注释块起,含 _GOLD_DETAIL_JOURNAL /
# _gold_last_row_key / parse_settlement_gold_detail / collect_gold_detail_hook 与
# read_round_outcome 内 collect 调用行(全局搜 collect_gold_detail_hook 定位),不留
# 开关/flag/参数(与 r63 streak_gold 钩子同删法,见下方原删除点注释)。
#: 旁路台账(jsonl,逐轮一行;与 replay/outcomes.jsonl 按 (run_id, plane, round_num) 对拍)
_GOLD_DETAIL_JOURNAL = get_project_root() / '.debug' / 'temp' / 'currency_war' / 'replay' / 'gold_detail.jsonl'
#: 结算停留防重:分支3 在结算屏停留期每轮循环都调 read_round_outcome,同帧只落一行
_gold_last_row_key: tuple | None = None


def parse_settlement_gold_detail(items: list) -> dict[str, int | None]:
    """结算屏「获得金币总览」明细 → {'base'/'streak'/'interest': int|None}(纯函数,可单测)。

    屏面 token 形态(sr-od-test win.webp 实测帧 + docs/game/screens/currency_war_settlement.md
    识别快照):标签在左列(``基础奖励``/``利息``/``连胜×0``,x≈530),数值在右列同 y 行的
    独立 token(x≈1042-1058);偶同 token 粘连(``连胜×N`` 本身即含值)。解析:
    ① 定位「总览」标题 token 作锚(标题区唯一,无歧义词);
    ② 锚**下方**逐标签找标签 token(下方守卫排除头部「火热连胜×N」词缀——那是连胜方向
       显示,parse_streak 消费,不是明细行);
    ③ 取值优先级:同 token 粘连(``标签\\s*[×xX*]?\\s*(\\d+)``)> 同行右侧最近纯数字 token
       (行判据 = 中心 y 差 ≤ 25px,1080p 实测行高 ~28px);
    ④ 值域守卫 0-99(两位数上限 = 明细分量的格式先验;越界/缺 token → None)。
    读不到置 None 不硬猜 0——0 与「没读到」语义必须分开(残差归因靠三分量真值,
    假 0 会把「明细区被折叠/OCR 漏」误记成「该分量为 0 金」)。OCR 形变按分层规则:
    标签词历史上无系统性形变,不做 LCS;数字走值域守卫即够。
    """
    out: dict[str, int | None] = {'base': None, 'streak': None, 'interest': None}
    _anchor = next((it for it in items if '总览' in (getattr(it, 'data', '') or '')), None)
    if _anchor is None:
        return out
    _labels = {'base': '基础奖励', 'streak': '连胜', 'interest': '利息'}
    for key, label in _labels.items():
        _lab = next((it for it in items
                     if label in (getattr(it, 'data', '') or '')
                     and getattr(it, 'y', 0) >= _anchor.y), None)
        if _lab is None:
            continue
        # ①同 token 粘连分层:基础奖励5=金额直连可消费;「连胜×N」的 N 是
        # 连胜计数、金额在同行右侧金额位(败轮实证:×0 行付 1)——×粘连
        # 先记计数再落 ② 取右列;② 空且计数在场则回退用计数(胜局粘连行
        # 无右列金额的历史行为兼容)
        _count: int | None = None
        _count_m = re.search(re.escape(label) + r'\s*[×xX*]\s*(\d{1,2})',
                             getattr(_lab, 'data', '') or '')
        if _count_m:
            _count = int(_count_m.group(1))
        else:
            m = re.search(re.escape(label) + r'\s*(\d{1,2})',
                          getattr(_lab, 'data', '') or '')
            if m:
                out[key] = int(m.group(1))
                continue
        # ②同行右侧最近纯数字 token
        _lcy = _lab.y + (getattr(_lab, 'height', 0) or 0) / 2
        _lcx = _lab.x + (getattr(_lab, 'width', 0) or 0) / 2
        _cands = []
        for it in items:
            t = (getattr(it, 'data', '') or '').strip()
            if not re.fullmatch(r'\d{1,2}', t):
                continue
            _cy = it.y + (getattr(it, 'height', 0) or 0) / 2
            _cx = it.x + (getattr(it, 'width', 0) or 0) / 2
            if abs(_cy - _lcy) <= 25 and _cx > _lcx:
                _cands.append((_cx - _lcx, int(t)))
        if _cands:
            out[key] = min(_cands)[1]
        elif _count is not None:
            out[key] = _count
    return out


def collect_gold_detail_hook(screen: MatLike, ocr_texts: list[str], items: list, *,
                             plane: int, round_num: int, node_type: str,
                             streak_after: int) -> None:
    """金币明细采集(旁路 jsonl + 整屏去重截图;best-effort,异常全吞不碰对局)。

    :param streak_after: 结算屏带符号连胜(parse_streak 产物,与明细行「连胜」分量对拍用)。
    """
    global _gold_last_row_key
    try:
        _key = (plane, round_num, tuple(ocr_texts))
        if _key == _gold_last_row_key:
            return   # 结算停留期同帧重复读:只落一行
        _gold_last_row_key = _key
        _detail = parse_settlement_gold_detail(items)
        from sr_od.application.currency_war.telemetry import cw_telemetry
        try:
            _run_id = cw_telemetry.current_run_id() or '-'
        except Exception:   # noqa: BLE001  run id 拿不到不阻塞落行
            _run_id = '-'
        from sr_od.application.currency_war.kernel.cw_observe import cw_shot_unique
        _shot = cw_shot_unique(screen, 'cw_settle') if screen is not None else None
        import datetime
        import json as _json
        rec = {'ts': datetime.datetime.now().isoformat(timespec='seconds'),
               'run_id': _run_id, 'plane': plane, 'round_num': round_num,
               'node_type': node_type, 'streak_after': streak_after,
               'base': _detail['base'], 'streak': _detail['streak'],
               'interest': _detail['interest'], 'shot': _shot}
        _GOLD_DETAIL_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with _GOLD_DETAIL_JOURNAL.open('a', encoding='utf-8') as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:   # noqa: BLE001  采集钩子零行为影响
        pass


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
    from sr_od.application.currency_war.kernel.cw_performance import RoundOutcome
    _items = ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, crop_first=False)
    ocr_texts = [r.data for r in _items]
    hp = parse_settlement_hp(ocr_texts)
    # W40:damage_dealt 生产(W23 定谳的最大数据缺口 0/239)——「数据统计」
    # 面板就在结算屏本体右侧列,同一帧全图 OCR 即可解析(坐标在 items 里),
    # 无需点开子面板/额外截图。读不到(面板被遮/OCR 漏)→ None 保持旧锁。
    damage = parse_settlement_damage(_items)
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
    # [streak_gold 采集钩子已删(r63 建,2026-08-23 删)]——真值表已从奖励弹窗
    # 规则区判读完成(docs/game/currency_war/research/economy_truth.md),
    # 弹窗底部即完整规则表(与对局状态无关),无需再攒结算屏样本。
    _streak_after = parse_streak(ocr_texts)   # 结算「连胜×N」前缀=方向(C 杠杆 2/3;fixture 核实 2026-08-11)
    # W414 金币明细采集(临时钩子,见本文件头部钩子段生命周期声明;best-effort 零行为影响):
    # 消费同一帧 OCR(零额外截图/零行为变更),明细行解析 + 整屏去重落盘。
    collect_gold_detail_hook(screen, ocr_texts, _items, plane=plane,
                             round_num=round_num, node_type=node_type,
                             streak_after=_streak_after)
    return RoundOutcome(
        round_num=round_num, plane=plane, node_type=node_type, comp_tag=comp_tag,
        hp_after=hp if hp is not None else 0,
        hp_confidence=1.0 if hp is not None else 0.0,
        streak=_streak_after,
        killed=_won,
        progress_delta=parse_settlement_progress(ocr_texts),
        damage_dealt=damage,   # W40:数据统计面板伤害求和(同帧;读不到 None)
    )
