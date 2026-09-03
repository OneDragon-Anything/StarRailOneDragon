
"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CwLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ ``decide_encounter`` 选卡 → 点卡身选中 + 点选择确认。
2026-08-04 实测交互模型(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

✅ 分支刷新执行链(dd-004):``decide_encounter`` 建议刷新(pick.refresh,全分支词缀克
  comp 时)→ OCR「剩余次数:N」>0 且本局未用 → 文本锚定点刷新圆钮 → **重读选项 →
  refresh_used=True 重新决策 → 按新决策选**。分支刷新能力 = 优势布局「分支刷新」授予
  (每局 1 次重置两卡难度/奖励;bwiki 优势布局表);session 级单次标志
  (``session._encounter_refresh_used``,与补给 ``_supply_refresh_used`` 同款)——
  发出刷新点击即置位,不等验效(点偏不重试,失败安全按原评分选,防重入反复尝试)。
  ⚠️ **触发源缺位挂账**:``read_encounter_options`` 的 affixes 恒空(卡面 UI 不显词缀,
  词缀在未建档的「敌方信息覆盖层」里)→ decide_encounter 的全克判定当前恒不触发,
  本执行链就绪但待词缀读数通道建立后才可能开火(dd-004 §约束)。

✅ Stage C2 已接:``decide_encounter``(按 comp 成型度选:未成型→低难保生存 /
  成型+词缀利→高难拿奖励 / 全分支克→刷新换批;用 pick.idx 选卡,**非默认选左**)。
  ⚠️ affix 避开分支 N/A(选项 UI 不显词缀,战后才显)。
坐标(screen_info 化债):卡身/选择经 ``cw_obs_core.area_center`` 读 screen_info
  ``currency_war_encounter``(``遭遇卡-其一/其二`` + ``按钮-选择``);缺失才用兜底常量。
  档案帧回验:sr-od-test/screens/货币战争-遭遇节点/default.webp 上 标识-遭遇节点 /
  按钮-选择 均 conf≈0.999 命中。卡身 rect center 未单独实锤(历史实测点 (665,500)/(1288,550)
  保留作兜底;rect 覆盖同卡身带)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_events import EncounterOption
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_node_obs import (
    read_encounter_options,
    read_encounter_refresh_count,
)
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.application.currency_war.telemetry.recorder import record_event_choice
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenEncounter(SrOperation):
    """遭遇节点二选一:decide_encounter 选卡(必要时先分支刷新)→ 点卡选中 + 选择确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-遭遇节点'   # screen_info 画面(currency_war_encounter.yml)
    # 遭遇卡卡身中心。左卡=遭遇其一(难度低,金币×2);右卡=遭遇其四(难度高,随机4费角色×3)。
    # 常量=screen_info 缺失兜底;首选 area_center('遭遇卡-其一/其二')。
    CARD_LEFT: ClassVar[Point] = Point(665, 500)
    CARD_RIGHT: ClassVar[Point] = Point(1288, 550)
    # 底部「选择」按钮中心(未选中卡时灰置禁用,选中后才可点)。常量=兜底;首选 area_center('按钮-选择')。
    SELECT_BTN: ClassVar[Point] = Point(1082, 898)
    # 分支刷新圆钮 = 「剩余次数:N」文本左侧固定偏移(dd-004)。归档帧
    # sr-od-test/screens/货币战争-遭遇节点/default.webp CV 双法实测:圆钮 ≈(671,899)、
    # 文本锚中心 ≈(771,899) → 偏移 = -100px;偏移错 → 验效失败走失败安全分支(照常选卡)。
    _REFRESH_BTN_DX: ClassVar[int] = -100

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')

    def _card_signature(self, options: list[EncounterOption]) -> list[tuple]:
        """卡面签名(难度+奖励元组列表)——刷新验效的「卡面变了」判据。"""
        return [(o.difficulty, tuple(o.rewards)) for o in options]

    def _try_refresh(self, text_pt: tuple[int, int], old_sig: list[tuple],
                     old_count: int) -> tuple[bool, list[EncounterOption]]:
        """点分支刷新圆钮 + 验效。

        Returns: (是否生效, 刷新后选项;未生效时为空列表)。
        验效双通道(与投资策略 ADR-0146 同款):①剩余次数扣减(权威——次数由游戏扣,
        卡面碰巧同签名也认);②卡面签名变化(次数读失败时的兜底)。双输 = 未生效
        (点偏/无布局)→ 调用方按原评分选(失败安全,不重试)。
        """
        target = Point(text_pt[0] + CwScreenEncounter._REFRESH_BTN_DX, text_pt[1])
        log.info(f'[cw-encounter] 建议刷新 → 圆钮@({target.x},{target.y})(文本锚定)')
        self.ctx.controller.mouse_move(target)   # bug#1 缓解
        self.ctx.controller.click(target)
        # 用户口述口径(#23,2026-09-02):遭遇屏刷新后 2s 画面稳定——
        # 原 1.2s 会在重掷尾帧读次数/卡面,误判「刷新未生效」(失败安全
        # = 白白浪费一次刷新)。等满 2s 再验效。
        time.sleep(2.0)
        after = self.screenshot()
        _cnt2 = read_encounter_refresh_count(self.ctx, after)
        if _cnt2 is not None and _cnt2[0] < old_count:
            log.info(f'[cw-encounter] 刷新生效(剩余次数 {old_count}→{_cnt2[0]})')
            return True, []
        _new = read_encounter_options(self.ctx, after)
        if _new and self._card_signature(_new) != old_sig:
            log.info(f'[cw-encounter] 刷新生效(卡面变化,次数读数={_cnt2})')
            return True, _new
        log.warning(f'[cw-encounter] 刷新未生效(次数 {old_count}→{_cnt2},卡面未变;'
                    f'点偏或未激活分支刷新布局)→ 按原评分选(失败安全)')
        return False, []

    @operation_node(name='遭遇节点', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, CwScreenEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
            return self.round_fail('非遭遇节点屏')
        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #23,2026-09-02):遭遇节点右上「返回备战界面」出现后 2s 画面才稳定
        # ——入口帧可能在稳定期内,立即读难度卡有读缺风险(default 盲选左)。
        # 等 2s 重截稳定帧再读再决策(与 #3/#11 overlay 入口修复同型,时长按
        # 本屏用户口径 2s)。
        time.sleep(2.0)
        screen = self.screenshot()
        # (difficulty + comp 成型度:formed→高难度拿好奖励,未成型→低难度保生存)→ 选 idx。替代硬编码「选左」。
        options = read_encounter_options(self.ctx, screen)
        match = self.ctx.cw_match
        idx, reason = 0, 'default(no-options/match)'
        pick = None
        _state = GameState()
        if match is not None and options:
            _state = match.session.last_state or GameState()   # overlay 时 board 不可读 → 用上次备战快照
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_encounter(options, _state, match.session, _cfg)
            if 0 <= pick.idx < len(options):
                idx = pick.idx
            reason = pick.reason
        # ===== 分支刷新执行链(dd-004):建议刷新 → 有次数且未用 → 点钮 → 重读重决策 =====
        refreshed = False
        if match is not None and pick is not None and pick.refresh:
            sess_used = getattr(match.session, '_encounter_refresh_used', False)
            cnt = read_encounter_refresh_count(self.ctx, screen)
            if sess_used:
                log.info('[cw-encounter] 建议刷新但本局已用(分支刷新每局1次)→ 按原评分选')
            elif cnt is None or cnt[0] <= 0:
                log.info(f'[cw-encounter] 建议刷新但无剩余次数(读数={cnt})→ 按原评分选')
            else:
                # 发出点击即置位(不等验效):防「点偏未生效 → 重入屏再试」的反复尝试;
                # 优势布局每局只授 1 次,单次尝试语义与游戏规则对齐。
                match.session._encounter_refresh_used = True
                refreshed, new_opts = self._try_refresh(
                    cnt[1], self._card_signature(options), cnt[0])
                if refreshed:
                    if not new_opts:   # 验效走了次数通道,卡面未读 → 补读一次
                        new_opts = read_encounter_options(self.ctx, self.screenshot())
                    if new_opts:
                        options = new_opts
                        pick = match.strategy.decide_encounter(
                            new_opts, _state, match.session, _cfg, refresh_used=True)
                        if 0 <= pick.idx < len(new_opts):
                            idx = pick.idx
                        reason = pick.reason
        if refreshed:
            reason = f'{reason}+分支刷新'
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} '
                 f'pick=idx{idx} refreshed={refreshed} {reason}')
        # 遥测:选项选择落账本(exogenous kind='event_choice')。
        # 此前只 log——「选了其几/两卡奖励/reason」跨局归因在遥测上断链。
        record_event_choice('encounter',
                            [{'difficulty': o.difficulty, 'rewards': o.rewards}
                             for o in options],
                            idx, reason)
        # 卡身/选择坐标从 screen_info 读;缺失走历史实测兜底常量。
        card_left = area_center(self.ctx, '遭遇卡-其一', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.CARD_LEFT
        card_right = area_center(self.ctx, '遭遇卡-其二', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.CARD_RIGHT
        select_btn = area_center(self.ctx, '按钮-选择', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.SELECT_BTN
        card = card_left if idx == 0 else card_right
        safe_click(self, card, tag='cw-encounter')
        time.sleep(0.8)
        # 选择 + 验关(遭遇其一 消失 = overlay 关)。原「点了就 success」不验 → bug#1/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;docstring 已记「插空白点击取消选中→死循环」风险)。
        # 验关用标题「遭遇节点」(4 字 vs 备战「遭遇」标签 2 字,LCS 0.5<0.8 不误匹配;live 2026-08-15)
        return confirm_and_verify(self, confirm_point=select_btn,
                                  entry_keyword='遭遇节点', lcs_percent=0.8, tag='cw-encounter')
