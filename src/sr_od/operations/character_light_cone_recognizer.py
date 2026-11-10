"""「角色-光锥」TAB 页的画面额外识别器(backend analyze 精准命中后自动调用)。

读取右栏当前装备光锥的结构化信息(名/命途/等级/叠影阶/技能名/三围),
供 MCP ``analyze_screen`` 的 ``extras`` 输出——agent 查看角色当前光锥不用
再靠视觉目检截图。

读区全部来自 screen_info 建档(character_light_cone.yml),坐标单一真相源。
OCR 失败的字段返回 None(extras 稀疏,不猜测)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

# 「等级80/80」→ 前段数字 = 当前等级
_LEVEL_RE = re.compile(r'等级\s*(\d{1,3})')
# 「叠影1阶」→ 叠影数
_RANK_RE = re.compile(r'叠影\s*(\d)\s*阶')


class CharacterLightConeRecognizer(ScreenRecognizer):

    screen_name = '角色-光锥'

    extras_doc: dict[str, str] = {
        'cone_name': '当前装备光锥名(OCR,识别失败为 null)',
        'path_cn': '光锥命途(OCR)',
        'level': '光锥当前等级(「等级80/80」前段数字,1-80)',
        'rank': '叠影数(「叠影N阶」,1-5)',
        'skill_name': '光锥技能名(OCR)',
        'hp': '生命值白值(OCR 数字)',
        'atk': '攻击力白值(OCR 数字)',
        'def': '防御力白值(OCR 数字)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """OCR 右栏各读区 → 当前装备光锥的结构化信息(字段失败时缺省)。"""
        result: dict = {}
        cone_name = self._ocr(ctx, image, '读区-光锥名')
        if cone_name is not None:
            result['cone_name'] = cone_name
        path_cn = self._ocr(ctx, image, '读区-命途')
        if path_cn is not None:
            result['path_cn'] = path_cn

        level_text = self._ocr(ctx, image, '读区-等级')
        if level_text is not None:
            m = _LEVEL_RE.search(level_text)
            if m is not None:
                result['level'] = int(m.group(1))

        rank_text = self._ocr(ctx, image, '读区-叠影')
        if rank_text is not None:
            m = _RANK_RE.search(rank_text)
            if m is not None:
                result['rank'] = int(m.group(1))

        skill_name = self._ocr(ctx, image, '读区-光锥技能名')
        if skill_name is not None:
            result['skill_name'] = skill_name

        for key, area_name in (('hp', '读区-生命值'), ('atk', '读区-攻击力'),
                               ('def', '读区-防御力')):
            num = self._ocr(ctx, image, area_name)
            if num is not None:
                digits = re.sub(r'[^\d]', '', num)
                if digits:
                    result[key] = int(digits)
        return result or None

    @staticmethod
    def _ocr(ctx: SrContext, image: MatLike, area_name: str) -> str | None:
        """按画面名 + area 名裁剪 OCR,合并该读区全部文本行(取区域唯一读数)。"""
        area = ctx.screen_loader.get_area('角色-光锥', area_name)
        results = ctx.ocr_service.get_ocr_result_list(
            image=image, rect=area.pc_rect, crop_first=True)
        texts = [str(r.data).strip() for r in results if str(r.data).strip()]
        return ''.join(texts) if texts else None
