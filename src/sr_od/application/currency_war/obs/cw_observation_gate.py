"""货币战争 观测统一入口(ADR-0213 批次1;方案 v4)。

「等待画面稳定 → 一次全面识别」的稳定门原语——替代散布
4+ 层的等待实现(连续 3s 锚窗/单锚探/轮询消失/固定 sleep;
见 ADR-0213 Context)。设计定案(四轮对抗 review 收敛):

- wait_stable_frame: min_stable_s 连续稳定窗(首尾帧一致,
  非相邻对——慢动画假稳定)+ 先 park_cursor;一致性基元=
  锚命中向量 + per-area 像素指纹(OCR 只用于锚);
- 三 profile(关态/开态/弹窗态),锚常量收敛不参数化分裂;
- 离线契约:截图异常→放行旧路径(环级测试依赖);
- None 返回语义 per-callsite(director=同因 bail 计数/
  shop=round_retry/钩子=skip+log);
- 消化门失败走既有 _bail 3-strike(session 计数),不引入
  round_fail 路径(cw_loop 忽略返回值→ping-pong)。

flag(终审③文档漂移修→r347 已删):gate 曾以
gate_director / gate_shop_close / gate_shop_open / gate_hook
四个 CurrencyWarConfig flag 双轨对拍;对拍期结束后无条件化
(ADR-0216),flag 与旧路径分支已删——gate 是唯一路径。锚
判定=框架 screen_utils.get_match_screen_name(id_mark 体系;
r324);指纹基元= cv2_utils.fingerprint_in_rects/same(r324
下沉)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_overlay_registry import derive_clearable

if TYPE_CHECKING:
    from sr_od.operations.sr_operation import SrOperation

# ===== profile 常量(两态+弹窗;锚/读区/超时收敛于此,调用方只选套) =====

#: 关态(备战+商店关)。
#: 锚设计(用户指路+r324 轮子审查修法1):**删自拼 presence/
#: absence 双锚**——用框架 screen_match 精准判定一次搞定:
#: get_match_screen_name(['备战','开商店'])精准命中「备战」
#: = 关态(id_mark 全中体系:备战屏 id_mark=购买经验/出战/
#: 前台/后台,开商店屏精准命中时必然不是关态)。
#: 圆数门弃用(局35 误杀奖励面板帧)。
PROFILE_CLOSED: dict = {
    'screen_list': ('货币战争-备战', '货币战争-备战-开商店'),
    'expect_screen': '货币战争-备战',
    # 读区像素指纹(1080p;排除表:立绘 idle 呼吸区/球区 VFX)
    'fingerprint_rects': (
        Rect(1408, 23, 1498, 103),  # HP 数字区(关态右上真值)
        Rect(60, 895, 320, 975),     # LV/XP
        Rect(250, 30, 520, 120),     # 阶段区(位面-轮次)
    ),
    'timeout_s': 12.0,              # r344:全图 OCR poll ~5s/轮(首区
                                    # 触发后同帧余区缓存命中)——预算须
                                    # ≥2 轮 poll(首轮设指纹+次轮比对,
                                    # 相邻 poll 间隔已>min_stable_s)+
                                    # 余量;旧 4.5s<单轮成本=结构性饿死
                                    #(局37 ping-pong 停机根因)。
                                    # ADR-0264 终裁:fast_confirm 下确认
                                    # 轮免 OCR(纯 CV ~50ms/轮),预算
                                    # 只覆盖首锚轮更绰绰有余
    # 稳定窗 0.6s=三 profile 统一下限(弹窗态既有同值):稳定的
    # 真守门是「指纹变化即重置重 poll」机制,0.6s 首尾一致窗
    # (2-3 个 poll)足以拒绝动画中间帧;单局 gate stable 调用
    # 30-84 次(耗时审计报告 .debug/temp/currency_war/
    # w417_duration_audit/REPORT.md「需验证」表),每处省 0.2s。
    'min_stable_s': 0.6,
    'fast_confirm': True,           # ADR-0264 终裁骨架:锚命中后稳定
                                    # 确认轮跳过全图 OCR 只比指纹;
                                    # 置 False 关回旧行为(A/B 回退)
}

#: 开态(商店开):同用框架精准判定——精准命中「开商店屏」
#: (其 id_mark=收起/购买经验 全中)。
PROFILE_OPEN: dict = {
    'screen_list': ('货币战争-备战-开商店',),
    'expect_screen': '货币战争-备战-开商店',
    'fingerprint_rects': (
        Rect(1620, 890, 1700, 945),   # gold 数字区(开态右下)
        Rect(300, 228, 1560, 326),    # 商店牌行
    ),
    'timeout_s': 12.0,               # r344:同 PROFILE_CLOSED 成本口径
    'min_stable_s': 0.6,             # 与关态统一 0.6s 下限(见关态注)
    'fast_confirm': True,            # ADR-0264 终裁骨架(同 CLOSED 注)
}

#: 弹窗态(奖励采集钩子点六边形后):锚=弹窗标题区 OCR「金币说明」。
PROFILE_POPUP: dict = {
    # r324 修法3:弹窗改走建档(upsert_screen_area「标识-金币
    # 说明」id_mark 待建)——ocr_keyword 特例是绕过建档的平行
    # 通道,审查标重复。建档前此 profile 不接线(钩子仍走
    # r304 流程;钩子本身「采完删」,见方案 v4)。
    'screen_list': ('货币战争-金币说明弹窗',),
    'expect_screen': '货币战争-金币说明弹窗',
    'fingerprint_rects': (
        Rect(1000, 580, 1560, 1010),  # 节点预计收入明细区
    ),
    'timeout_s': 12.0,               # r344:同 CLOSED/OPEN 成本口径
    'min_stable_s': 0.6,
    'fast_confirm': True,            # ADR-0264 终裁骨架(同 CLOSED 注)
}

#: 战后收起商店后的关店态 stable 等待超时(cw_screen_prep 环入口
#: 「预收开商店」专用,其余 gate 调用不用)。背景:战斗胜利后新回合
#: 游戏常自动开商店,环入口若直接等关店态锚会永不命中、打满
#: PROFILE_CLOSED 的 12s 超时(实机每局 16 轮 × ~12s 纯等;依据
#: 实机单局耗时深挖报告 .debug/temp/currency_war/w358_time_depth/
#: REPORT.md「可压缩清单 #1」)。修法=入口先收起再等 stable:实测
#: 收起后 ~2.0-2.2s 即达成关店态 stable(同报告各间隙「收起→
#: stable」段),收紧到 4.0s(≈2 倍实测余量,覆盖首轮全图 OCR 锚
#: poll 抖动);下限 1s(不低于单轮 poll + min_stable_s 成本),
#: 超时后由调用方落回原 12s 完整门兜底(有界,不引入无界等待)。
GATE_POST_COLLAPSE_TIMEOUT_S: float = 4.0

#: 帧间隔(方案 v4:0.2-0.3s)
_POLL_S: float = 0.25

# ===== 规范入口序列:阶段键 + 每阶段字段规格(ADR-0462)=====
# 「先清场、再识别、后动作」:P0 清场期零业务识别 → P1 干净备战期全量基线 →
# P2 动作期(开店/overlay)只读该动作决策所需。字段规格 = read_game_state 的
# 逐字段 gate 单一源;键域与 Snapshot SubstateClassification.name 对齐(W583
# 快照契约;阶段1 子态注册表落地时随注册表收拢,纯搬家)。

#: P1 干净备战期(gate PROFILE_CLOSED stable 帧):全量识别基线,含 hp 真读
#: 主路径(shop 关帧血量区可见)。shop_cards/refresh_probs 属开店面板,必空不读。
PHASE_PREP_CLEAN: str = 'prep_clean'
#: P2a 开店动作期(gate PROFILE_OPEN):仅买牌决策所需;hp/node_type 结构必空
#: (6fc1fd4c 先例 + shop.py session 拷贝),cap/deployed/难度/连胜以 P1 基线为准。
PHASE_PREP_SHOP_OPEN: str = 'prep_shop_open'
#: 战斗/过渡帧:仅位面轮次(恢复对局检测消费面只有 plane/round)。
PHASE_BATTLE_OR_TRANSIT: str = 'battle_or_transit'

#: 每阶段可读字段集(read_game_state 逐段 gate;phase=None=全量=现行为)。
#: 字段键与 read_game_state 内各识别段一一对应;hp 段特殊:在集内=真读
#: (read_hp_opt),不在=对账沿用(reconcile,零 OCR)。
PHASE_FIELD_SPEC: dict[str, frozenset[str]] = {
    PHASE_PREP_CLEAN: frozenset({
        'gold', 'phase_round', 'hp', 'node_type', 'xp', 'level',
        'deploy_cap', 'deployed_count', 'enemy_difficulty',
        'level_up_cost', 'streak', 'board', 'bench_full',
    }),
    PHASE_PREP_SHOP_OPEN: frozenset({
        'gold', 'phase_round', 'xp', 'level', 'level_up_cost',
        'board', 'shop_cards', 'refresh_probs', 'bench_full',
    }),
    PHASE_BATTLE_OR_TRANSIT: frozenset({'phase_round'}),
}

#: P0 清场段:环入口可一键关闭的 overlay 注册表(画面名 → 关闭按钮 area 名)。
#: **A 面切换后 = 注册表派生桥接**(单一源 =
#: ``cw_overlay_registry.derive_clearable()``,激活 ∧ closable;消费方
#: ``cw_screen_prep._clear_entry_overlays`` 遍历本映射,循环逻辑未变):
#: 只收「无决策语义的弹窗/面板」——星徽秘典/补给已 decision 化(关闭即丢
#: 决策内容,C1 红线;设计定案 5),从清场集消失,改走 event_overlay bail
#: → 0i 选卡 / CwScreenSupplyNode 消化;投资环境/投资策略/选择伙伴/盛会之星/
#: 祈愿试炼等交互 overlay 同理,不进派生集。
ENTRY_OVERLAY_CLOSE: dict[str, str] = {
    spec.screen_name: spec.close_area for spec in derive_clearable()
}
#: 清场轮数上限(每轮:逐屏锚探 → 命中点关闭 → settle;无命中即出)。
ENTRY_OVERLAY_CLEAR_ROUNDS: int = 4
#: 点关闭后的画面过渡等待(秒)。
ENTRY_OVERLAY_SETTLE_S: float = 1.0

#: 操作段(op_settle)预估等待(ADR-0264 终裁加速器②;用户口述
#: 定调 2026-08-24:「备战期间的特效/overlay(买角色/部署特效)
#: 是短暂的,预估 2 秒等待就好了」)。语义=**指纹基线重置点**:
#: 特效后先等一段再取指纹基线(防特效中间帧当基线),随后指纹
#: 快 poll 正常确认稳定窗。
#: 1.2s 的边界依据:买牌特效实测 0.5-1s(单局耗时审计报告
#: .debug/temp/currency_war/w417_duration_audit/REPORT.md
#: 「需验证」表),取实测上限 + 0.2s 余量(w781 自 1.5 核减:
#: 用户裁定决策周期压缩,核减依据=低估不致误读——基线取在
#: 特效中间帧时,下一 poll 指纹变化即重置重 poll,仅多付一次
#: poll 成本,正确性由指纹机制保证)。
#: 1.0s(2026-09-02 二次核减):用户口述口径(screen_flow_timing.md
#: #15)商店收起过场动画 ~1s 即备战画面稳定——预等对齐动画时长,
#: 动画尾帧仍由指纹重 poll 兜(低估安全论证同上)。
_OP_SETTLE_S: float = 1.0

#: 最近一次 op_settle 预估等待的时长(测试内省 seam;None=本进程
#: 未走过 op_settle 段)。
_LAST_SETTLE_WAIT: float | None = None

#: 操作段(op_settle)稳定窗地板:涉动画段(开/关店)在预估等待
#: 等待 + 指纹基线重置后,动画尾帧已被基线机制排除(指纹变化即
#: 重置重poll),稳定确认窗只需最短档——取三 profile 既有下限
#: 0.6s(PROFILE_POPUP 同值;实机单局耗时深挖报告
#: .debug/temp/currency_war/w358_time_depth/REPORT.md「风险声明」
#: 明示稳定窗下限 0.6s,防特效帧误读的红线地板,不再低)。
#: 三 profile 原值 0.8s 已统一降到该地板(见 PROFILE_CLOSED 注)
#: ——入口帧同样由指纹变化重置机制守门,不需要额外 0.2s 抗特效
#: 消化。
_OP_SETTLE_MIN_STABLE_S: float = 0.6

# r324(轮子审查修法2):指纹原语下沉 one_dragon.utils.cv2_utils
# (fingerprint_in_rects/fingerprint_same,与 is_same_image 并列)——
# gate 不再私有实现;阈值语义注解见 cv2_utils(局36 diag 实证)。

# ADR-0264 方案 B:overlay 关闭后预置的稳定基线
# {expect_screen: (指纹, 单调时钟时间)}——单次消费(pop),由
# wait_stable_frame 在首次锚命中时取用;最新预置覆盖旧值。
_PRESET_BASELINE: dict[str, tuple] = {}


def preset_stable_baseline(frame: MatLike, *, profile: dict,
                           clock=None) -> None:
    """overlay 成功关闭后预置稳定基线(ADR-0264 方案 B)。

    用户口述流程规律(设计依据):进节点 → 备战 → 按节点类型弹
    大 overlay(补给/遭遇/投资策略/环境)→ overlay 完成后进内
    备战 → 动画开商店,**次序固定**——overlay 关闭本身是流程推进
    的确定性信号,关闭后的首帧即稳定候选。调用方(overlay
    handler 收尾助手)在验关成功后调本函数预置基线,下一次
    wait_stable_frame 跳过「从零等 2 轮」;**只预置基线,不裸
    跳**——gate 仍须过一次「锚命中 + 指纹一致」确认才放行。

    best-effort:指纹计算失败静默跳过(离线 mock 帧不阻塞调用方)。
    """
    from one_dragon.utils import cv2_utils
    try:
        fp = cv2_utils.fingerprint_in_rects(
            frame, profile['fingerprint_rects'])
        _PRESET_BASELINE[profile['expect_screen']] = (
            fp, (clock or time.monotonic)())
    except Exception:   # noqa: BLE001  best-effort(离线契约)
        pass


def wait_stable_frame(
        op: SrOperation, *, profile: dict,
        timeout_s: float | None = None,
        fast_confirm: bool | None = None,
        segment: str | None = None,
        clock=None) -> MatLike | None:
    """等待画面稳定(r324 重构:框架能力复用版)。

    - 锚判定=**框架 screen_match 精准判定**(id_mark 全中):
      get_match_screen_name(profile['screen_list'])精准命中
      expect_screen——删自拼 presence/absence(轮子审查 A2)
      与 ocr_keyword 特例(A5);
    - 帧一致=**cv2_utils.is_same_in_rects**(审查 A3:指纹
      下沉框架,与 is_same_image 并列);
    - 时间维度稳定窗(min_stable_s 首尾帧)+异常/超时分流
      (raise vs None)是本模块仅存的净增量(审查 D);
    - 截图异常→raise(调用方 except=放行旧路径);
      超时→None(per-callsite 语义表);
    - clock 可注入(测试 seam)。
    - r344(实机首验 bug,局37 停机根因):**poll 成本模型**——
      超时预算必须按「单轮 poll 实际成本」设定。全图 OCR
      (crop_first=False,~5s/帧实机)按 id(image) 缓存,同帧
      多消费者(gate 判 4 个 id_mark 区首区触发、后续全缓存
      命中;gate 末帧传 _observe 后 heavy 观察全部命中)共享
      一次全图 OCR——这是项目统一口径(用户定调 2026-08-22:
      尽量 crop_first=False 复用 OCR 缓存)。旧 timeout 4.5s
      < 单轮 poll 成本 → 首轮 poll 后 deadline 已过,稳定窗
      结构性不可能达成(diag {'screen':0,'fp':1,'ok':0});
      修法=timeout 调 12s(≥2 轮 poll+余量),而非改 cropped
      口径(cropped 丢弃缓存复用且小 area 易漏字)。另加
      one-shot grace poll:首轮已取到指纹样本但从未比对过
      一次时,超时后允许一次额外 poll(有界),防更慢机器下
      预算仍不足的同类饿死。
    - (ADR-0264 方案 A,fast_confirm 指纹-only 确认轮):
      实测 poll=截图+全图 OCR 锚判定 avg 0.38s/轮(GPU
      DirectML),min_stable_s=0.8 被流程成本淹没(②备战相位
      →稳定帧中位 50.4s、④纯稳定门 8.1s)。锚命中 1 次
      (get_match_screen_name 确认目标屏)后,后续稳定确认轮
      跳过全图 OCR,只做「截图+指纹比对」(纯 CV 毫秒级);
      **指纹变化即回锚定模式**(指纹-only 看不见屏切换,变化
      = 可能已离屏,下一轮重做全图 OCR 锚判定;指纹 rects 已
      排除呼吸区/VFX,静止屏上指纹漂移罕见)。r327 锚 miss
      重置语义保留。fast_confirm 显式传参 > profile 键,默认
      开;置 False 关回旧行为做 A/B。
    - (ADR-0264 方案 B,overlay 完成预置基线):overlay
      handler 验关成功后调 preset_stable_baseline 预置「关闭
      后首帧指纹」——gate 首次锚命中时消费(pop),指纹一致则
      稳定窗从预置时刻起算,预置距今 ≥ min_stable_s 即一轮
      达标;**不裸跳**(仍须锚命中 + 指纹一致确认一次)。
    - (ADR-0264 终裁,融合:指纹快 poll = 测量驱动骨架,用户
      流程知识 = 加速器;**不做「锚命中即推进」的纯信任放行**
      ——测量驱动对未知画面形态鲁棒,纯先验信任在游戏版本
      更新加新特效时有带噪观察的失效面;速度上融合收益≈两者
      之和,稳定性上完胜)——用户口述定调 2026-08-24:「节点
      结束后流程是稳定的,这部分可以优化;备战期间的特效/
      overlay 是短暂的,预估 2 秒等待就好了」。两个应用点:
      1. 节点结束段加速(隐含于骨架):锚命中后**立即**进指纹
         快 poll,不等额外的全图 OCR 轮——锚命中帧即设指纹
         基线,后续确认轮全部纯 CV(min_stable_s 从「被 ~5s
         OCR poll 量化」变为真实测量);
      2. 操作段(``segment='op_settle'``,买/部署/装备特效后):
         **预估等待(``_OP_SETTLE_S``)作为指纹基线重置点**——
         先等再取
         基线(防特效中间帧当基线),随后指纹快 poll 确认稳定窗
         (settle 段窗取地板 ``_OP_SETTLE_MIN_STABLE_S``=0.6s,
         三 profile 原值已统一该地板;非单校验放行);校验不过
         (特效意外拖长)→ 循环内回锚定/重设基线(完整门语义)。
      回退开关 = ``fast_confirm``(profile 键,显式传参优先;
      False = 每轮 poll 都做全图 OCR 锚判定的旧完整门)。
    """
    from one_dragon.base.screen import screen_utils
    from one_dragon.utils import cv2_utils
    _now = clock or time.monotonic
    _sleep = (lambda s: None) if clock else time.sleep
    t0 = _now()
    deadline = t0 + (timeout_s if timeout_s is not None
                     else profile['timeout_s'])
    import contextlib
    with contextlib.suppress(Exception):   # 离线无控制器
        op.park_cursor()
    # ADR-0264 终裁加速器②:操作段预估等待(_OP_SETTLE_S)= 指纹基线重置点
    #(先等再取基线,防特效中间帧当基线;随后正常快 poll 确认窗)
    global _LAST_SETTLE_WAIT
    _settle_waited = False
    _min_stable = profile['min_stable_s']
    if segment == 'op_settle':
        _sleep(_OP_SETTLE_S)
        _LAST_SETTLE_WAIT = _OP_SETTLE_S
        _settle_waited = True
        # 稳定窗分级(地板常量注):settle 段动画尾帧由「指纹变化
        # 即重置基线重poll」机制排除,确认窗取最短档 0.6s
        _min_stable = _OP_SETTLE_MIN_STABLE_S
    stable_since = None
    first_fp = None
    _diag = {'screen': 0, 'fp': 0, 'ok': 0, 'fast': 0}
    _grace_used = False   # r344:超时后的一次额外 poll(见函数头注)
    _compared = False     # 是否完成过至少一次指纹比对
    # ADR-0264 方案 A:fast 开关(显式传参 > profile 键;缺省开)
    _fast = (fast_confirm if fast_confirm is not None
             else profile.get('fast_confirm', True))
    _fast_active = False  # 当前轮是否跳过锚 OCR(指纹-only 确认)
    while True:
        if _now() >= deadline:
            # r344:已有指纹样本但从未比对过 → 允许一次额外 poll
            #(首轮 poll 成本可能已吞掉整个预算;无样本/已比对过/
            # grace 已用 → 正常超时退出,保持有界)
            if _compared or _grace_used or first_fp is None:
                break
            _grace_used = True
        frame = op.screenshot()   # 异常直传(调用方 except=放行旧路径)
        if not _fast_active:
            # 画面判定:框架 is_target_screen(id_mark 体系;一次调用
            # 替代自拼 presence/absence 双锚与 ocr_keyword 特例)。
            # r344(用户定调):crop_first=False=全图 OCR 按 id(image)
            # 缓存——首 id_mark 区触发(~5s),同屏其余区/同帧后续
            # 消费者(_observe heavy 等)全部缓存命中;poll 成本由
            # timeout_s 预算吸收(见 profile 常量注)
            _name = screen_utils.get_match_screen_name(
                ctx=op.ctx, screen=frame,
                screen_name_list=list(profile['screen_list']),
                crop_first=False)
            if _name != profile['expect_screen']:
                _diag['screen'] += 1
                _sleep(_POLL_S)
                # r327(终审 B):锚 miss 连 first_fp 一起重置——
                # 只重置 stable_since 会在「锚短暂 miss 后恢复且
                # 指纹未变」时卡死:L139 same 成立跳过重设分支,
                # stable_since 恒 None → 稳定窗永不达成 → 必超时
                # →(director 站)同因 3 次 3-strike 停机——瞬时锚
                # miss 被放大成停局,违背时间稳定窗初衷。
                stable_since = None
                first_fp = None
                continue
        else:
            # ADR-0264 方案 A:指纹-only 确认轮(跳过全图 OCR)
            _diag['fast'] += 1
        # 帧一致:框架 per-rect(与全图 is_same_image 并列的增量)
        fp = cv2_utils.fingerprint_in_rects(
            frame, profile['fingerprint_rects'])
        if first_fp is not None and not cv2_utils.fingerprint_same(
                fp, first_fp):
            _diag['fp'] += 1
            first_fp = fp
            stable_since = _now()
            # ADR-0264 方案 A 兜底:指纹变化即回锚定模式——指纹-only
            # 确认轮看不见屏切换,变化(无论动画残留还是已离屏)后
            # 下一轮重做全图 OCR 锚判定再决定是否恢复快确认。
            _fast_active = False
            _sleep(_POLL_S)
            continue
        if first_fp is None:
            # ADR-0264 方案 B:消费 overlay 预置基线(单次 pop)——
            # 指纹一致则稳定窗从预置时刻起算(仍须本次锚命中,
            # 非裸跳);预置距今 ≥ min_stable_s 即一轮达标。
            _preset = _PRESET_BASELINE.pop(
                profile['expect_screen'], None)
            if _preset is not None and cv2_utils.fingerprint_same(
                    fp, _preset[0]):
                first_fp = _preset[0]
                stable_since = _preset[1]
            else:
                _diag['fp'] += 1
                first_fp = fp
                stable_since = _now()
                _sleep(_POLL_S)
                # 锚已命中(本轮做过 OCR 判定)→ 后续确认轮可跳 OCR
                _fast_active = _fast
                continue
        _compared = True
        if stable_since is not None and \
                _now() - stable_since >= _min_stable:
            log.info(f'[cw][gate] stable frame ({profile["expect_screen"]}, {_now() - t0:.1f}s'
                     f'{", settle" if _settle_waited else ""}'
                     f'{", fast" if _diag["fast"] else ""}'
                     f'{", preset" if stable_since is not None and stable_since < t0 else ""})')
            return frame
        _diag['ok'] += 1
        _sleep(_POLL_S)
        # 锚命中后的后续确认轮跳过全图 OCR(ADR-0264 方案 A)
        _fast_active = _fast
    log.info(f'[cw][gate] timeout ({_now() - t0:.1f}s) '
             f'profile={profile["expect_screen"]} '
             f'diag={_diag} grace={_grace_used}')
    return None
