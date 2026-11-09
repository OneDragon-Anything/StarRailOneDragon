"""装备替换列表(光锥/遗器)画面识别器:网格逐格占用者识别。

``analyze_screen`` 精准命中「光锥-替换」/「遗器-替换」后,按网格几何逐格裁
角标区做角色头像匹配(equip_owner_match.match_owner),把「每件装备被哪个
角色占用」作为结构化清单塞进 ``extras``。

卡片上没有装备名称文本(名字只在选中后右侧详情可读)——识别器**不识别
装备身份**,只识别占用者;定位某件装备并装备走 ``EquipLightConeOp`` /
``EquipRelicOp``(解包图标 SIFT 全量清单)。角标匹配对「同源 mini 图」实测
同角色 0.878 / 异角色上限 0.453(阈值 0.75);未列出格 = 未装备 / 空格 /
角标角色不在模板库(不猜测)。

并发安全:recognize 纯读 —— 不写 ``self.``、不写任何全局;模板库缓存为
只读懒加载(equip_owner_match 模块内,幂等)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.operations.equip_owner_match import (
    _MIN_OWNER_SCORE,
    CONE_OWNER_SCORE,
    match_owner,
)
from sr_od.operations.grid_template_locate import cone_grid_cells, relic_grid_cells

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.geometry.point import Point
    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo


class _EquipListRecognizerBase(ScreenRecognizer):
    """网格逐格占用者识别的公共实现;子类声明画面名 + 网格几何 + 角标偏移。"""

    extras_doc: dict[str, str] = {
        'items': '占用件清单 [{cell:[x,y], owner:角色id}],按格坐标(列,行)排序;'
                 '只含有占用者识别的格 —— 未装备/空格/角色不在模板库的格不列出',
        'total_cells': '网格内可见格总数(含未装备/空格)',
        'hint': '卡片上无装备名称文本;定位与装备某件走 EquipLightConeOp/EquipRelicOp',
    }

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        """本画面的网格几何(格中心清单),几何实机标定值见 grid_template_locate。"""
        raise NotImplementedError

    def _badge_rect(self, cell: Point) -> Rect:
        """本画面的角标检测区(相对格中心的实测偏移)。"""
        raise NotImplementedError

    def _list_area_name(self) -> str:
        """本画面列表区 area 名(坐标单一真相源)。"""
        raise NotImplementedError

    def _owner_min_score(self) -> float:
        """角标匹配阈值(光锥界面角标更小,匹配天花板低 → 阈值单独放低)。"""
        raise NotImplementedError

    def recognize(
        self,
        ctx: OneDragonContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """网格逐格裁角标区跑角色头像匹配,返回占用件清单;列表区缺档返 None。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        items: list[dict] = []
        cells = self._grid_cells(list_area.rect)
        for cell in cells:
            owner, _score = match_owner(image, self._badge_rect(cell),
                                        min_score=self._owner_min_score())
            if owner is not None:
                items.append({'cell': [round(cell.x), round(cell.y)], 'owner': owner})
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cells': len(cells)}


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:9 列网格逐格占用者识别。"""

    screen_name = '光锥-替换'

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        return cone_grid_cells(list_rect)

    def _badge_rect(self, cell: Point) -> Rect:
        # 角标区偏移实测(光锥卡):格中心 +18/-83 ~ +78/-33
        return Rect(cell.x + 18, cell.y - 83, cell.x + 78, cell.y - 33)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _owner_min_score(self) -> float:
        return CONE_OWNER_SCORE


class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:4 列网格逐格占用者识别。"""

    screen_name = '遗器-替换'

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        return relic_grid_cells(list_rect)

    def _badge_rect(self, cell: Point) -> Rect:
        # 角标区偏移实测(遗器卡):格中心 +6/-63 ~ +61/-13
        return Rect(cell.x + 6, cell.y - 63, cell.x + 61, cell.y - 13)

    def _list_area_name(self) -> str:
        return '区域-遗器列表'

    def _owner_min_score(self) -> float:
        return _MIN_OWNER_SCORE
