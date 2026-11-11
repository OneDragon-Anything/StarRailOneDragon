"""替换屏候选单屏扫描 op(「筛选 → 逐件看词缀 → 人定 → 替换」流程的取数端)。

职责:对当前视口的替换列表逐卡点选、读词缀详情,产出候选档案 JSON——
**单屏语义**(用户裁定「先给一屏」):只扫当前视口,翻页续扫由调用方滚动后
再调;``bottom_reached`` 告知调用方是否还有下一屏。

前置:已在替换屏 + 部位正确 + **静态排序**(入口检查排序摘要读区 =「遗器
建议排序」时显式失败——建议排序按匹配度动态重排 + 重掷动画滚动自动回顶,
点选→读取会漂移,EquipRelicOp 已档教训;先跑 ``FilterRelicReplaceOp`` 或
手动设静态排序)。

行为事实(2026-11-12 摸底,F17-F21 见迭代设计 design.md §2.1):
- 点选列表卡后右侧详情面板 = 选中件完整词条(F17);点选→详情刷新等待
  1.2s(实机动画标定)。
- masked 卡(重掷动画遮罩)的卡面不可识别(F21),但点选后**右侧详情读区
  正常可读**——件名以详情 OCR 为准(F21),TM 身份仅作先验兜底;masked 卡
  照常进档案。
- owner(穿着者)只在卡面角标上(TMY 识别),详情面板无此信息——档案的
  owner 取列表识别值。

副作用边界:只改列表选中态,不触 卸下/替换/重掷(F17 帧;点击坐标 =
识别输出的卡矩形中心,不在副作用按钮区)。
"""

import json
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.cultivation.relic.relic_detail_reader import read_detail
from sr_od.application.cultivation.relic.relic_list_recognizer import (
    RelicReplaceRecognizer,
)
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_relic_sets import PIECE_TO_SET
from sr_od.operations.sr_operation import SrOperation

_REPLACE_SCREEN: str = '遗器-替换'

#: 点选后详情刷新等待(实机动画标定;测试经 fast_sleep(op) 桩掉 op 模块 time)
_DETAIL_REFRESH_WAIT: float = 1.2

#: 行带聚类间隔阈值(px,识别器 detect_card_anchors 同法;行距 183~200px,
#: 簇内间隔远小于行距)
_BOTTOM_ROW_SPLIT_PX: int = 100


class ScanRelicCandidatesOp(SrOperation):
    """扫描当前视口的替换列表候选,产出逐卡词缀档案(JSON)。

    结果状态:SCANNED(data = ``{"pos", "candidates", "bottom_reached"}``;
    candidates 元素 = ``{cell, piece, set, pos_cn, level, owner, main, subs,
    times_confirmed}``,times_confirmed = 该卡全部副词条次数均已确证——
    有未确证行(角标数字 OCR 失败)时为 False,供约束判定与人审复核)。
    失败:不在替换界面 / 部位不符 / 角色核对失败 / 建议排序动态重排态 /
    列表识别为空。
    """

    def __init__(self, ctx: SrContext, pos: int,
                 expected_character: str | None = None):
        """
        :param pos: 部位号 1-6(1=头部 2=手部 3=躯干 4=脚部 5=位面球
            6=连结绳,与 SrRelicPieceDef.pos 同坐标系)。
        :param expected_character: 目标角色中文名(替换界面「命途/角色名」
            核对,语义与 EquipRelicOp 同源;None = 跳过核对)。
        """
        if pos not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f'部位 pos={pos} 超出 1-6')
        self.pos: int = pos
        self.expected_character: str | None = expected_character
        SrOperation.__init__(self, ctx,
                             op_name=gt('扫描替换列表候选') + f'({RELIC_POS_CN[pos]})',
                             node_max_retry_times=8)

    def _check_character(self) -> OperationRoundResult | None:
        """替换界面「命途/角色名」核对(同源复制 EquipRelicOp._check_character_
        on_replace_screen;防在错误角色的列表上扫描)。核对通过返回 None。"""
        if self.expected_character is None:
            return None  #: 调用方未要求核对,整体跳过(连读区 OCR 也省)
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '读区-角色命途名')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        text = ''.join(str(r.data) for r in results).replace(' ', '')
        if self.expected_character in text:
            return None
        hit = sum(1 for ch in self.expected_character if ch in text)
        if hit / len(self.expected_character) >= 0.5:
            return None
        return self.round_fail(f'替换界面角色核对失败:期望「{self.expected_character}」,'
                               f'实读「{text}」—— 当前角色不符,请先切到目标角色')

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:替换屏 + 部位正确 + 角色核对 + 静态排序前置。扫描是
        只读 op,入口不导航(调用方负责把画面带到筛选后的目标列表)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=[_REPLACE_SCREEN])
        if current != _REPLACE_SCREEN:
            return self.round_fail(
                f'不在替换界面(当前判定: {current});'
                f'前置 = FilterRelicReplaceOp 设好筛选/排序,或手动进入目标部位列表')
        current_pos = RelicReplaceRecognizer()._detect_pos_from_tabs(
            self.ctx, self.last_screenshot)
        if current_pos != self.pos:
            return self.round_fail(
                f'替换列表部位不符(筛选={current_pos},目标={self.pos})')
        check = self._check_character()
        if check is not None:
            return check
        summary_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '读区-排序摘要')
        ocr_list = self.ctx.ocr_service.get_ocr_result_list(
            image=self.last_screenshot, rect=summary_area.rect)
        summary = ''.join(str(r.data) for r in ocr_list).replace(' ', '')
        if '建议排序' in summary:
            return self.round_fail(
                '列表为「遗器建议排序」动态重排态,点选→读取会漂移(EquipRelicOp '
                '已档教训);先跑 FilterRelicReplaceOp 设静态排序或手动设置后再扫描')
        return self.round_success(status='ENTRY_OK')

    @node_from(from_name='入口核对')
    @operation_node(name='单屏扫描', node_max_retry_times=3)
    def scan_candidates(self) -> OperationRoundResult:
        """整屏清单识别 → 按行优先逐卡点选 → 读词缀详情 → 合并档案。

        点选即改选中态(选中卡白框放大渲染)——清单在点选前一次性识别完毕,
        点选不改变后续卡位(静态排序前置保证)。"""
        screen = self.last_screenshot
        recognized = RelicReplaceRecognizer().recognize_for_pos(
            self.ctx, screen, self.pos)
        if recognized is None or not recognized.get('items'):
            return self.round_fail('列表识别为空(无卡或识别失败)')
        items = recognized['items']

        candidates: list[dict] = []
        for item in items:
            cell = item['cell']
            self.ctx.controller.click(
                Point((cell[0] + cell[2]) // 2, (cell[1] + cell[3]) // 2))
            time.sleep(_DETAIL_REFRESH_WAIT)
            detail = read_detail(self.ctx, self.screenshot())
            candidates.append(self._merge_candidate(item, detail))

        result = {
            'pos': self.pos,
            'candidates': candidates,
            'bottom_reached': self._bottom_reached(items),
        }
        return self.round_success(status='SCANNED',
                                  data=json.dumps(result, ensure_ascii=False))

    def _merge_candidate(self, item: dict, detail: dict | None) -> dict:
        """列表识别值与详情读区合并为候选档案。

        件名/主副词条/等级以详情 OCR 为准(F21);详情读不到(点选未生效或
        面板异常)时退列表识别值(TM 身份先验),subs 置空并标 times_confirmed
        =False(无词缀数据,约束判定按不满足)。"""
        candidate: dict = {
            'cell': item['cell'],
            'owner': item.get('owner'),
            'main': None,
            'subs': [],
            'times_confirmed': False,
        }
        if detail is None:
            candidate.update({key: item.get(key)
                              for key in ('piece', 'set', 'pos_cn', 'level')})
            return candidate
        piece = detail.get('piece') or item.get('piece')
        set_def = PIECE_TO_SET.get(piece) if piece else None
        candidate['piece'] = piece
        candidate['set'] = set_def.set_name if set_def else item.get('set')
        candidate['pos_cn'] = detail.get('pos_cn') or item.get('pos_cn')
        candidate['level'] = (detail.get('level')
                              if detail.get('level') is not None
                              else item.get('level'))
        candidate['main'] = detail.get('main')
        candidate['subs'] = detail.get('subs') or []
        candidate['times_confirmed'] = bool(candidate['subs']) and all(
            sub.get('times_confirmed') for sub in candidate['subs'])
        return candidate

    def _bottom_reached(self, items: list[dict]) -> bool:
        """末行带卡数 < 4 列 = 已到列表底(末行不满一行;行带聚类阈值与识别
        器 detect_card_anchors 同法)。末行带的卡全为锚点卡(识别器末行带
        不做轮廓补位),卡数即锚点数。"""
        if not items:
            return True
        ys = sorted((item['cell'][1] + item['cell'][3]) / 2 for item in items)
        bands: list[list[float]] = []
        for y in ys:
            if not bands or y - bands[-1][-1] > _BOTTOM_ROW_SPLIT_PX:
                bands.append([y])
            else:
                bands[-1].append(y)
        return len(bands[-1]) < 4
