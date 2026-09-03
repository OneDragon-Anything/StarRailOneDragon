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

import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
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


def parse_settlement_assets(ocr_texts: list[str]) -> dict[str, int | None]:
    """结算屏金币存量/等级/经验读数 → {'gold','level','xp_cur','xp_next'}
    (纯函数,可单测;W971 05-battle §1「结算屏 hp/gold/level 写 session」的
    gold/level 读口,期望态结算覆盖点消费)。

    证据口径(EXPECTED_STATE.md §1 节引 win 帧亲读):结算页含「金币总览
    <获得>」与「存量 <当前>」两组金币数——**存量**才是当前金币(总览=本
    节点获得量);等级形「Lv.5」,经验形「4/20」。失败结算页无等级/经验
    (败局链读数口径,05-battle §1)→ 对应键 None。全部 best-effort:
    读不到 = None(宁缺勿造,不冒认)。
    """
    out: dict[str, int | None] = {'gold': None, 'level': None,
                                  'xp_cur': None, 'xp_next': None}
    for t in ocr_texts:
        if out['gold'] is None:
            m = re.search(r'存量\s*[:：]?\s*(\d+)', t)
            if m:
                out['gold'] = int(m.group(1))
        if out['level'] is None:
            m = re.search(r'Lv\.?\s*(\d{1,2})', t)
            if m:
                out['level'] = int(m.group(1))
        if out['xp_cur'] is None:
            m = re.search(r'(\d{1,3})\s*/\s*(\d{1,3})', t)
            if m and out['level'] is not None:
                out['xp_cur'] = int(m.group(1))
                out['xp_next'] = int(m.group(2))
    return out


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


# ===== 结算屏金币明细三分量解析(纯函数形态保留) =====
# 口径权威 = STREAK_GOLD_TABLE/REWARD_BASE_GOLD_BY_ROUND(cw_economy)+ ADR-0439
# (败轮金走下一轮轮首补发,败轮结算屏无收入面板为预期形态);视觉抽检定谳档案
# = .debug/temp/currency_war/w414_gold_detail_conclusion.md。本函数是该口径的
# 可执行规格与未来复采的阅读器:生产链已无调用方(每结算屏帧的采集触发段已删,
# 按 SR 约定整段不留开关/flag;回归锁在 sr-od-test/test_cw_telemetry_collect.py
# 纯函数节),保留纯函数+测试形态。台账 streak 数值列带解析偏差,消费须按
# STREAK_GOLD_TABLE[计数] 重算,不得直读(见定谳档案 §2.2)。


def _gold_token_cy(it: object) -> float:
    """OCR token 中心 y(纯函数辅助)。

    生产 items 是 ``OcrMatchResult``(字段名 ``w``/``h``),测试桩常用
    ``width``/``height``——两套字段名都支持,取不到按 0 退化为顶边 y。
    历史 bug 教训:只写 ``height`` 时生产路径恒 getattr 默认 0,行对齐
    实际在比 token 顶边而非中心,静默劣化同行数值的命中判断。
    """
    h = getattr(it, 'h', None)
    if h is None:
        h = getattr(it, 'height', 0) or 0
    return it.y + h / 2  # type: ignore[attr-defined]


def _gold_token_cx(it: object) -> float:
    """OCR token 中心 x(字段名兼容同 ``_gold_token_cy``)。"""
    w = getattr(it, 'w', None)
    if w is None:
        w = getattr(it, 'width', 0) or 0
    return it.x + w / 2  # type: ignore[attr-defined]


#: 明细金额列 x 下缘(1080p 实测):右列数值 token x∈[1040,1070](总览行与三分量行)。
#: 金额候选中心必须落在该列——把「计数列」(标签 token 右侧 x≈645,粘连拆分形态
#: 「连胜×」+「3」)与金额列定位分离,计数数字永不被当金额落账。
_GOLD_VAL_COL_MIN_X = 1000

#: 分量金额值域守卫(画面实况先验,来自 2026-09 结算金币明细 10 帧视觉抽检):
#: 利息恒 2-9(208 行读取分布);连胜金额 1-9(×0/×1=1、×2/×3=2 实证,n≥4 未见
#: 可信帧但游戏显示必为个位);基础奖励维持 0-99 宽守(实测恒 3/5,无收紧依据)。
#: 连胜**计数**不设值域门——计数只喂 ×0/×1 口径规则,不当金额消费。
_GOLD_AMT_RANGE = {'base': (0, 99), 'streak': (1, 9), 'interest': (2, 9)}

#: 「连胜×0/×1」行画面金额恒为 1(视觉抽检 ×0 4/4 帧、×1 1 帧实证)——右列
#: 金额漏读时按此口径落账(记录的是画面实况,非公式猜测)。计数 ≥2 的金额
#: 公式未钉死(×2/×3→2 实证,但 floor(n/2)+1 与 min(n,2) 不可分,n≥4 无帧):
#: 右列读不到 → None(宁缺勿造,禁拿计数顶账)。
_GOLD_STREAK_PINNED = {0: 1, 1: 1}


def parse_settlement_gold_detail(items: list) -> dict[str, int | None]:
    """结算屏「获得金币总览」明细 → {'base'/'streak'/'interest': int|None}(纯函数,可单测)。

    屏面 token 形态(实盘 shot 离线 OCR 实测):标签在左列(``基础奖励``/``利息G``
    (↻ 图标偶被 OCR 读成 G/C)/``连胜×N``,x≈524-642),金额在右列金额位独立
    token(x≈1040-1070);计数列(x≈645)与金额列定位分离。解析:
    ① 定位「总览」标题 token 作锚(标题区唯一,无歧义词);
    ② 锚**下方**逐标签找标签 token(下方守卫排除头部「火热连胜×N」词缀——那是连胜方向
       显示,parse_streak 消费,不是明细行);
    ③ 取值:基础奖励/利息的同 token 粘连(``基础奖励5``)可直读金额;连胜 token
       上的数字(含 × 粘连与粘连拆分)一律是**计数**,不是金额。金额统一取
       同行右列金额位最近纯数字 token(行判据 = 中心 y 差 ≤ 25px + 金额列 x 门);
    ④ 值域守卫按分量分设(见 ``_GOLD_AMT_RANGE``);右列读不到时:连胜计数
       ∈{0,1} → 1(画面实况钉死口径),其余 → None。
    读不到置 None 不硬猜 0——0 与「没读到」语义必须分开(残差归因靠三分量真值,
    假值会把「OCR 漏」误记成「该分量为 0/计数值金」)。
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
        _lab_txt = getattr(_lab, 'data', '') or ''
        # 同 token 粘连分层:基础奖励5=金额直连;「连胜×N」/「连胜N」的数字是
        # 连胜**计数**(金额在同行右侧金额位)——计数只喂 ×0/×1 钉死口径。
        _count: int | None = None
        if key == 'streak':
            _count_m = re.search(re.escape(label) + r'\s*[×xX*]?\s*(\d{1,2})', _lab_txt)
            if _count_m:
                _count = int(_count_m.group(1))
        else:
            m = re.search(re.escape(label) + r'\s*(\d{1,2})', _lab_txt)
            if m:
                out[key] = int(m.group(1))
                continue
        # 同行右列金额位最近纯数字 token(行 = 中心 y 差 ≤25px + 金额列 x 门)
        _lcy = _gold_token_cy(_lab)
        _lcx = _gold_token_cx(_lab)
        _lo, _hi = _GOLD_AMT_RANGE[key]
        _cands = []
        for it in items:
            t = (getattr(it, 'data', '') or '').strip()
            if not re.fullmatch(r'\d{1,2}', t):
                continue
            _cy = _gold_token_cy(it)
            _cx = _gold_token_cx(it)
            if abs(_cy - _lcy) <= 25 and _cx >= _GOLD_VAL_COL_MIN_X:
                _cands.append((_cx - _lcx, int(t)))
        if _cands:
            _v = min(_cands)[1]
            if _lo <= _v <= _hi:   # 值域守卫:越界(OCR 误读)→ None,不落账
                out[key] = _v
        elif key == 'streak' and _count in _GOLD_STREAK_PINNED:
            out[key] = _GOLD_STREAK_PINNED[_count]
    return out


# ===== 结算屏三项遥测读数器(挑战进度填充率 / 基础伤害 / 未完成进度伤害) =====
# 设计出处 = docs/develop/currency_war/strategy/05_observation.md §3.1(持久落点;迭代工作原稿=SETTLE_OCR_DESIGN §1.5/§2/§3(离线设计批,
# 坐标为帧实测提案,窗口标定 C1-C6 待实机复核)。
# 背景:λ 基座攻击点名「OCR 前置零进展」——P15 脱删失 / P12 幅度授权需要结算屏
# 三项真值(进度幅度绝对值 + 伤害两分量),本段建真值通道;读不到 = None(删失
# 显式可辨,不造假值)。

#: 掉血说明 tooltip「小队生命值结算说明」整体区域(1080p;帧实测 =
#: fixtures/settle_ocr/end_boss_win_with_breakdown_panel.png)。tooltip 为**进页瞬态**
#: 子件(REAL_MACHINE_COLLECTION_1.md:新批 40 帧 2s 后 0 命中,首批 4/7 系进页瞬窗)
#: → 读点必须在进页窗口内(页1 即读 / 钩子帧即读),miss 记 None 不阻塞。
_SETTLE_DMG_PANEL_RECT = Rect(1237, 485, 1702, 682)
#: 挑战进度条全槽(1080p;帧实测,end_loss/end_final_fail 两帧条槽左右端一致)。
#: 总格数(每位面满条对应进度上限)未在帧内暴露,只产出 fill_ratio,格数换算
#: 由读端在校准(C2)后乘——避免 schema 绑死总格数。
_SETTLE_PROGRESS_BAR_RECT = Rect(710, 422, 1210, 444)
#: 列扫描判「该列已填充」的红像素占比阈值(条体 y 高 ~18px,抗边缘半红/压缩噪声)。
_PROGRESS_COL_FILL_RATIO = 0.3


def settle_page1_progress_sign(ocr_texts: list[str]) -> str | None:
    """结算页 1「挑战进度 ±N」符号三态('pos'/'neg'/None=OCR 未读到;纯函数;DD-006)。

    三用途:① boss 胜局页1 判别(='pos',见 ``is_boss_win_settle_page1``);
    ② 失败页分支置闩门(='neg' 显式负增量才认败局——None 是 OCR 偶漏,两种
    形态页都可能漏,拿漏读当败局真值置闩会把 boss 胜局 run 判废,真通关永不
    判 win);③ 页1 暂存消费方自读。调用方要几种判定就自己拿 sign 比较,勿按
    bool 再读一遍 OCR。

    符号论域边界(审计补:为何无 'zero' 态):``parse_settlement_progress``
    的正则语法上允许 0(``[+-]\\d+`` 可匹配 '+0'/'-0'),但游戏进度 UI **只
    渲染增量绝对值 ≥1 的带符号行**——0 变化不渲染增量行,屏上不存在 '±0'
    形态可被 OCR 读到,故 0 归入 neg 桶无实际触发面;None(整行漏读)已单列,
    是唯一真实存在的「非 pos 非 neg」态。
    """
    _pg = parse_settlement_progress(ocr_texts)
    if _pg is None:
        return None
    return 'pos' if _pg > 0 else 'neg'


def is_boss_win_settle_page1(ocr_texts: list[str]) -> bool:
    """结算页 1 的 boss 胜局形态判定(纯函数;DD-006)。

    boss 胜局页 1 与战败结算页 1 同构(「挑战结束」标题 + 挑战进度条 +
    「点击空白加速」,均无「继续挑战」按钮)——失败链分支 1f 的模板门在
    boss 胜局页 1 误命中(夜间语料批 3 局实证),把页 1 从分支 2(三项
    遥测暂存通道)整条抢走。判别语义 = **挑战进度带符号增量 > 0**:节点
    胜利进度 +N(实跑 token 形态 ['挑战进度','+2']),战败为负增量或读不
    到;OCR 漏读 '+' 时退化为 None → 判 False(回旧行为,不劣化)。
    """
    return settle_page1_progress_sign(ocr_texts) == 'pos'


def parse_settle_damage_breakdown(items: list) -> dict:
    """掉血说明 tooltip 三行 → 结算伤害分量(纯函数,可单测)。

    输入 = tooltip 区域 OCR 结果(``items`` 带坐标;生产走区域裁剪 OCR,禁全屏)。
    输出 ``{'visible': bool, 'damage_base': int|None,
    'damage_unfinished_progress': int|None, 'heal_longline': int|None}``。

    - 行定位 = 标签词(「基础伤害」「未完成进度伤害」「长线作战」;长词抗噪,
      「未完成进度伤害」允许 OCR 断词,按「未完成」+「伤害」双锚匹配);
    - 值 = 同行右侧最近带符号数字 token(行判据 y 中心差 ≤ 20px,帧实测行距 ~33px)
      或同 token 粘连(「基础伤害-10」);
    - 值域先验:基础伤害/未完成进度伤害恒 ≤ 0(负=扣血)——无符号正值 = OCR
      丢负号 → 拒信记 None(docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §3);「0」裸数字合法(进度打满
      游戏可显 0);长线作战为正(回血);
    - visible = 标题「结算说明」命中 ∨ 任一行标签命中(标题偶 garble,行标签
      在场即面板在场;False = 面板不在场,可分「不在场」vs「在场解析失败」);
    - 符号形变:OCR 常见 −(U+2212)/— 归一到 '-'。
    """
    out: dict = {'visible': False, 'damage_base': None,
                 'damage_unfinished_progress': None, 'heal_longline': None}
    _rows = (('damage_base', ('基础伤害',), False),
             ('damage_unfinished_progress', ('未完成进度伤害', '未完成'), False),
             ('heal_longline', ('长线作战',), True))
    _title_hit = any('结算说明' in (getattr(it, 'data', '') or '') for it in items)
    _any_row = False
    for key, labels, _allow_positive in _rows:
        _lab = next((it for it in items
                     if any(lb in (getattr(it, 'data', '') or '') for lb in labels)), None)
        if _lab is None:
            continue
        _any_row = True
        # ① 同 token 粘连(基础伤害-10 / 长线作战+2):数字必须紧贴标签词尾
        _lab_txt = (getattr(_lab, 'data', '') or '').strip()
        _tail = re.search(r'(?:' + '|'.join(re.escape(lb) for lb in labels) + r')\s*([+−-]?)\s*(\d{1,3})$', _lab_txt)
        if _tail is not None:
            out[key] = _signed_value(_tail.group(1), _tail.group(2), _allow_positive)
            continue
        # ② 同行右侧最近带符号数字 token
        _lcy = _lab.y + (getattr(_lab, 'height', 0) or 0) / 2
        _lcx = _lab.x + (getattr(_lab, 'width', 0) or 0) / 2
        _cands = []
        for it in items:
            t = (getattr(it, 'data', '') or '').strip().replace('−', '-').replace('—', '-')
            _vm = re.fullmatch(r'([+]?)(-?)(\d{1,3})', t)
            if _vm is None:
                continue
            _cy = it.y + (getattr(it, 'height', 0) or 0) / 2
            _cx = it.x + (getattr(it, 'width', 0) or 0) / 2
            if abs(_cy - _lcy) <= 20 and _cx > _lcx:
                _cands.append((_cx - _lcx, _vm.group(2), _vm.group(3)))
        if _cands:
            _, _sign, _num = min(_cands)
            out[key] = _signed_value(_sign, _num, _allow_positive)
    out['visible'] = _title_hit or _any_row
    return out


def _signed_value(sign: str, digits: str, allow_positive: bool) -> int | None:
    """带符号数字 token → int(值域先验守卫;纯函数)。

    ``allow_positive=False`` 的行(基础伤害/未完成进度伤害)应恒 ≤ 0:显式
    '-' → 负值;无符号正数 = OCR 丢负号 → 拒信 None(docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §3);
    显式 '+' 同拒(游戏该行不显正);裸「0」合法。
    """
    v = int(digits)
    if sign == '-':
        return -v
    if allow_positive:
        return v
    return None if v > 0 else 0


def read_settle_damage_breakdown(ctx: SrContext, screen: MatLike | None) -> dict:
    """掉血说明 tooltip 区域裁剪 OCR → 三分量读数(区域读;禁全屏)。

    screen None(测试注入态/无帧)→ 全 None + visible False,不冒认。
    """
    if screen is None:
        return {'visible': False, 'damage_base': None,
                'damage_unfinished_progress': None, 'heal_longline': None}
    try:
        items = ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=_SETTLE_DMG_PANEL_RECT, crop_first=True)
        return parse_settle_damage_breakdown(items)
    except Exception as e:   # noqa: BLE001  观测读数失败不阻塞调用方
        log.warning('[cw-settle] 伤害分量 tooltip 读取失败(不阻塞): %s', e)
        return {'visible': False, 'damage_base': None,
                'damage_unfinished_progress': None, 'heal_longline': None}


def parse_progress_fill_ratio(screen: MatLike | None) -> float | None:
    """挑战进度条红色填充列扫描 → fill_ratio ∈ [0,1](纯像素,无 OCR;可单测)。

    判据:进度条槽 ``_SETTLE_PROGRESS_BAR_RECT`` 内,列的红像素占比 ≥
    ``_PROGRESS_COL_FILL_RATIO`` 记该列已填充;fill_ratio = 最右填充列的右缘
    占全槽宽比(进度条为**连续填充**(C2 定谳:连续条,总长=位面节点数),
    前缀列扫描对刻度分隔免疫)。红 = RGB 通道 R 显著高于 G/B(条体为红填充,
    槽底为暗色)。条不可见(红像素质量过低)/帧缺 → None,不冒认 0。

    **只对页 1 帧调用**(DD-006):进度条只在页 1(「点击空白加速」帧)存在;
    页 2 帧的同一矩形罩在 HP 心形图标上,橙金色像素满足红色判据 → 恒定假值
    (夜间语料批 3 局 boss 行同读 0.392 = 页 2 心形的确定性读数)。调用方
    (``read_round_outcome``)用页 1 标记词「点击空白加速」做帧态门。
    """
    if screen is None:
        return None
    try:
        r = _SETTLE_PROGRESS_BAR_RECT
        bar = np.asarray(screen)[r.y1:r.y2, r.x1:r.x2, :3]
        if bar.size == 0:
            return None
        red = ((bar[:, :, 0].astype(int) - bar[:, :, 1].astype(int) > 50)
               & (bar[:, :, 0].astype(int) - bar[:, :, 2].astype(int) > 50)
               & (bar[:, :, 0].astype(int) > 100))
        col_frac = red.mean(axis=0)
        filled = col_frac >= _PROGRESS_COL_FILL_RATIO
        if not filled.any() or red.sum() < 30:
            return None
        last = int(np.max(np.nonzero(filled)[0]))
        return round((last + 1) / filled.shape[0], 4)
    except Exception:   # noqa: BLE001  像素读数 best-effort
        return None


def parse_settle_hp_anchor(ocr_texts: list[str]) -> bool:
    """结算页 HP 锚(「小队生命值」行 ∨「继续挑战」按钮在场;纯函数)。

    用途:三项读数的页态门——锚在 = 结算常驻页(读数有效);锚不在 =
    动画期/过渡帧(读数帧态不成立,读 None 不算 miss)。锚判据出处 =
    docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §1.5(HP 锚可靠,页 2 整版布局常驻)。
    """
    return any(('小队生命值' in t or '命值' in t or '继续挑战' in t) for t in ocr_texts)


def read_round_outcome(ctx: SrContext, screen: MatLike, *, plane: int, round_num: int,
                       comp_tag: str, node_type: str = '普通战斗'):
    """结算屏 → ``RoundOutcome``(观测回路 P1.5;``on_round_end`` 输入)。

    OCR 全屏 → ``parse_settlement_hp`` 得 hp_after;解析成功 hp_confidence=1.0(进 trend),失败 0.0
    (< ``HP_CONFIDENCE_THRESHOLD`` 不进 trend,防噪声)。plane/round_num/comp_tag 由调用方
    (loop)传入。node_type:**结算屏自身解析优先**(r366/ADR-0239——局48 实锤 prep 流
    RunBuyPhase 下 EnsureShopClosed 零执行,node_type 生产链全死,传参恒回退普通战斗);
    解析不出再退调用方传入值(备战期 nodeseq 链,当前流下常 None→普通战斗)。

    ✅ 已接线(2026-08-07 起):cw_loop._record_round_outcome(分支3)每轮胜结算屏调用 →
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
    # r366b(review B3):传参='boss'(cw_loop 专项 OCR '首领',证据更强)
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
    # 结算三项遥测(docs/develop/.../05_observation.md §3.1):挑战进度填充率(纯像素列扫描,
    # 零 OCR 成本)+ 伤害两分量(tooltip 区域裁剪 OCR)。填充率**只对页 1 帧读**
    # (DD-006):页 2 帧矩形罩在 HP 心形上会恒定读出假值(0.392 三局同值实证)
    # ——「点击空白加速」是页 1 帧态标记词。本函数读点 = 调用帧:败局链(1f/3b)在
    # 挑战结束页1 调 → tooltip 瞬窗内可捕获;胜轮在页2 调 → tooltip 大概率已离屏,
    # None 由 cw_loop 页1 暂存合并兜底(_settle_page1_settle,同 progress 合并法)。
    _fill = (parse_progress_fill_ratio(screen)
             if any('点击空白加速' in t for t in ocr_texts) else None)
    _panel = read_settle_damage_breakdown(ctx, screen)
    return RoundOutcome(
        round_num=round_num, plane=plane, node_type=node_type, comp_tag=comp_tag,
        hp_after=hp if hp is not None else 0,
        hp_confidence=1.0 if hp is not None else 0.0,
        streak=_streak_after,
        killed=_won,
        progress_delta=parse_settlement_progress(ocr_texts),
        damage_dealt=damage,   # W40:数据统计面板伤害求和(同帧;读不到 None)
        progress_fill_ratio=_fill,   # 结算三项遥测:进度条填充率(读不到 None,不冒认 0)
        damage_base=_panel['damage_base'],
        damage_unfinished_progress=_panel['damage_unfinished_progress'],
        damage_breakdown_visible=_panel['visible'],
    )
