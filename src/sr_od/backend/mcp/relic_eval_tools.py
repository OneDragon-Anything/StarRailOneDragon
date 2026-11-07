"""遗器有效词条评估纯计算模块（``mys_evaluate_relic_substats`` 的计算层）。

设计出处：docs/develop/sr_od/backend/changes/relic-substat-eval/design.md
§2.2（出参 schema）/§2.3（计算规则 1-10）/§2.4（归一表与口径包表）/
§2.5（模块路径与「纯函数+常量+注册分离」取舍，同构 character_tools.py 先例）。
零 IO、零副作用：名册明细与口径均由调用方传入；MCP 注册层在 ``mys_tools.py``
（缺省名册经控制器自拉 + 非 success 信封原样透传），本模块不 import 任何
MCP / backend 依赖。

标准名口径（规则 1 要求的名册核对定稿结论；依据 = 两份在库真实名册产物：
``sr_od.mys.sr_codes.PROPERTY_INFO_SNAPSHOT``（实测词典 56 码词条名快照）与
真实响应 fixture ``sr-od-test/test/fixtures/mys/hkrpg_avatar_info_detail_sample.json``
的 property_info 词条侧名及其经 ``sr_mys_client`` 映射的断言样例）：

- 生命值/攻击力/防御力三词在名册词条名（name_cn）中**平坦与百分比同名**
  （词条码 27/32 同名「生命值」、29/33 同名「攻击力」、31/34 同名「防御力」；
  fixture pt=33 词条侧名实证「攻击力」）——flat/% 只能由 value 的 ``%``
  后缀判别。名册侧标准名按「name_cn + % 后缀」消歧：带 % → 「生命值提高/
  攻击力提高/防御力提高」（design §2.4 的百分比标准名），不带 % → 名词
  本体（平坦）。命中分桶与求和按消歧后标准名，flat 与 % 因此不混
  （规则 2 语义）。
- 名册词条 name_cn 全集（relics/ornaments 六件域，据上两源核对定稿）：
  生命值/攻击力/防御力/速度/暴击率/暴击伤害/效果命中/效果抵抗/击破特攻/
  能量恢复效率/治疗量加成/七属性伤害提高（物理/火/冰/雷/风/量子/虚数）。
  未入标准名全集的词一律 warnings 显式报告（规则 1），不静默错数。

verdict 短句格式（规则 8 模板中留白的摘要段）：主核对段
「主词条穿错 N 件；」执行了核对即输出（N=0 也输出）；阈值摘要段
「达标 X 项、差线 Y 项；」。
"""

#: 词条标准名全集（别名/口径包展开与同名直通的命中判据；全集核对出处见
#: 模块 docstring）
STANDARD_STAT_NAMES: frozenset[str] = frozenset({
    '生命值', '攻击力', '防御力',  # 平坦值（名册同名直通）
    '生命值提高', '攻击力提高', '防御力提高',  # 百分比值（名册侧经 % 后缀消歧）
    '速度', '暴击率', '暴击伤害', '效果命中', '效果抵抗', '击破特攻',
    '能量恢复效率', '治疗量加成',
    '物理属性伤害提高', '火属性伤害提高', '冰属性伤害提高',
    '雷属性伤害提高', '风属性伤害提高', '量子属性伤害提高', '虚数属性伤害提高',
})

#: 平坦/百分比同名异义的三词（名册 name_cn 无法区分，靠 value 的 % 后缀
#: 消歧；出处见模块 docstring 名册核对结论）
FLAT_PERCENT_HOMONYM_NAMES: frozenset[str] = frozenset({'生命值', '攻击力', '防御力'})

#: 同名异义三词的百分比标准名（design.md §2.4 百分比标准名）
PERCENT_STANDARD_BY_NAME: dict[str, str] = {
    '生命值': '生命值提高',
    '攻击力': '攻击力提高',
    '防御力': '防御力提高',
}

#: 速记别名表：口径入参用词 → 标准名（定义出处 = design.md §2.4；
#: 用词依据 = mys_get_roster_detail 字段名与 game-coach 角色档措辞）
STAT_NAME_ALIASES: dict[str, str | list[str]] = {
    '攻击%': '攻击力提高',
    '大攻击': '攻击力提高',
    '攻击力百分比': '攻击力提高',
    '生命%': '生命值提高',
    '大生命': '生命值提高',
    '防御%': '防御力提高',
    '大防御': '防御力提高',
    '暴击': '暴击率',
    '暴伤': '暴击伤害',
    '爆伤': '暴击伤害',
    '命中': '效果命中',
    '抵抗': '效果抵抗',
    '击破': '击破特攻',
    '充能': '能量恢复效率',
    '回能': '能量恢复效率',
    '治疗': '治疗量加成',
    '双暴': ['暴击率', '暴击伤害'],
    '速度': '速度',  # 同名直通（design §2.4 原文）
}

#: 口径包表：速记 → 标准名集合（定义出处 = design.md §2.4；定稿判据 =
#: 验收名单 12 人角色档口径行实际用到的包，与名册词条名全集无关）
STAT_PACKS: dict[str, list[str]] = {
    '双暴攻': ['暴击率', '暴击伤害', '攻击力提高'],
    '速双暴': ['速度', '暴击率', '暴击伤害'],
    '双暴生': ['暴击率', '暴击伤害', '生命值提高'],
    '击破速': ['击破特攻', '速度'],
    '命中速': ['效果命中', '速度'],
    '生命双暴': ['生命值提高', '暴击率', '暴击伤害'],
}

#: 主词条核对参与的部位（规则 5：头部/手部主词条物理恒定，不核对不进
#: main_stat_check，头/手副词条照常计数）
MAIN_CHECK_SLOTS: frozenset[str] = frozenset({'躯干', '脚部', '位面球', '连结绳'})

#: roster_data 结构非法信封文案（规则 10 定死语义）
ROSTER_STRUCTURE_ERROR_MESSAGE: str = (
    'roster_data 结构非法，应传 mys_get_roster_detail 返回的 data 字段内容（角色明细数组）'
)


def _resolve_criteria_word(word: object) -> list[str] | None:
    """口径入参词条词 → 标准名列表（口径包 → 别名 → 标准名直通，规则 1）。

    返回 None = 三表都归不上（未识别词；调用方 warnings 追加并按无效处理）。
    """
    if not isinstance(word, str):
        return None
    pack = STAT_PACKS.get(word)
    if pack is not None:
        return list(pack)
    alias = STAT_NAME_ALIASES.get(word)
    if alias is not None:
        return [alias] if isinstance(alias, str) else list(alias)
    if word in STANDARD_STAT_NAMES:
        return [word]
    return None


def _resolve_roster_stat(name_cn: object, value: object) -> str | None:
    """名册词条名 → 标准名（规则 1；同名异义三词按 value 的 % 后缀消歧）。

    返回 None = 未识别词条名（调用方 warnings；该条不进命中/浪费分布）。
    """
    if not isinstance(name_cn, str):
        return None
    if name_cn in FLAT_PERCENT_HOMONYM_NAMES:
        value_text = value if isinstance(value, str) else str(value)
        if value_text.endswith('%'):
            return PERCENT_STANDARD_BY_NAME[name_cn]
        return name_cn
    if name_cn in STANDARD_STAT_NAMES:
        return name_cn
    return None


def _parse_stat_value(value: object) -> tuple[float, str | None]:
    """词条数值字符串 → (数值, 警告文案 | None)（规则 2）。

    带 % 结尾 → 去后缀按百分数值；无 % → flat 数值；解析失败按 0 计并返回
    警告文案（由调用方追加进该角色 warnings）。
    """
    text = value if isinstance(value, str) else ('' if value is None else str(value))
    try:
        if text.endswith('%'):
            return float(text[:-1]), None
        return float(text), None
    except ValueError:
        return 0.0, f'数值「{text}」解析失败，按 0 计'


def _criteria_structure_error(criteria: object) -> str | None:
    """criteria 整体与逐元素结构校验（规则 9/10 同族防御分支，缺一项必填
    字段无法产出可归属结果，按 error 拒绝而非静默跳过）。

    返回 None = 合法；否则返回 error 信封文案。
    """
    if not isinstance(criteria, list):
        return 'criteria 需为列表'
    if len(criteria) == 0:
        return 'criteria 为空列表，无可评估角色'
    for element in criteria:
        if not isinstance(element, dict):
            return 'criteria 元素结构非法：每项需为对象，含 character_name 与 effective_substats'
        if not isinstance(element.get('character_name'), str):
            return 'criteria 元素结构非法：每项需含 character_name（str）'
        if not isinstance(element.get('effective_substats'), list):
            return 'criteria 元素结构非法：每项需含 effective_substats（list[str]）'
    return None


def _duplicate_names_error(criteria: list[dict]) -> str | None:
    """criteria 内重复 character_name 检查（规则 9：整体 error，message 列出
    重复名）。返回 None = 无重复。"""
    counts: dict[str, int] = {}
    for element in criteria:
        name = element['character_name']
        counts[name] = counts.get(name, 0) + 1
    duplicated = [name for name, count in counts.items() if count > 1]
    if duplicated:
        return 'criteria 存在重复 character_name：' + '、'.join(duplicated)
    return None


def _roster_structure_error(roster_data: object) -> str | None:
    """roster_data 结构防御（规则 10）：非 list、元素非 dict、缺
    name/relics/ornaments 键或明细数组本身非 list → error 信封，不得当空
    名册静默产出空报告。返回 None = 合法。"""
    if not isinstance(roster_data, list):
        return ROSTER_STRUCTURE_ERROR_MESSAGE
    for element in roster_data:
        if not isinstance(element, dict):
            return ROSTER_STRUCTURE_ERROR_MESSAGE
        for key in ('name', 'relics', 'ornaments'):
            if key not in element:
                return ROSTER_STRUCTURE_ERROR_MESSAGE
        if not isinstance(element['relics'], list) or not isinstance(element['ornaments'], list):
            return ROSTER_STRUCTURE_ERROR_MESSAGE
    return None


def _evaluate_one(entry: dict, criteria_entry: dict) -> dict:
    """单角色评估（规则 1-8 逐条；warnings 随评估照常进行，不中断计数）。"""
    warnings: list[str] = []

    # 规则 1：口径词展开为有效标准名集合（补集一律无效）
    effective: set[str] = set()
    for word in criteria_entry['effective_substats']:
        resolved = _resolve_criteria_word(word)
        if resolved is None:
            warnings.append(f'未识别词条词「{word}」，按无效词条处理')
        else:
            effective.update(resolved)

    pieces: list[dict] = list(entry['relics']) + list(entry['ornaments'])

    total_rolls = 0
    effective_hits = 0
    hits_by_stat: dict[str, dict[str, float]] = {}
    wasted_rolls_by_stat: dict[str, int] = {}
    # (标准名, 解析值) 全量收集：阈值求和（规则 6）与命中分桶共用一次解析
    parsed_values: list[tuple[str, float]] = []
    piece_wasted: list[int] = []
    piece_effective: list[int] = []
    piece_slots: list[str] = []
    main_stat_by_slot: dict[str, str | None] = {}

    for piece in pieces:
        slot = piece.get('pos_cn') if isinstance(piece.get('pos_cn'), str) else '未知部位'
        piece_slots.append(slot)
        wasted_here = 0
        effective_here = 0

        # 主词条：不进命中/总次数（规则 4 只数副词条）；进阈值求和与主核对
        main_entry = piece.get('main')
        if isinstance(main_entry, dict):
            main_name = main_entry.get('name_cn')
            main_standard = _resolve_roster_stat(main_name, main_entry.get('value'))
            if main_standard is None:
                warnings.append(f'未识别主词条名「{main_name}」（{slot}），不参与求和与核对')
            else:
                value, parse_warning = _parse_stat_value(main_entry.get('value'))
                if parse_warning is not None:
                    warnings.append(f'主词条「{main_standard}」（{slot}）{parse_warning}')
                parsed_values.append((main_standard, value))
            # 核对用 actual：识别成功放标准名，未识别放原名（保持可见性）
            main_stat_by_slot[slot] = main_standard if main_standard is not None else (
                main_name if isinstance(main_name, str) else None
            )

        subs = piece.get('subs')
        for sub in subs if isinstance(subs, list) else []:
            if not isinstance(sub, dict):
                continue
            times = sub.get('times')
            if not isinstance(times, int) or isinstance(times, bool):
                times = 0
            standard = _resolve_roster_stat(sub.get('name_cn'), sub.get('value'))
            total_rolls += times
            if standard is None:
                # 规则 1：未识别词按无效处理并显式告警；无标准名可键，只计
                # 总次数（不进浪费分布，避免用非标准名污染出参键）
                warnings.append(
                    f'未识别副词条名「{sub.get("name_cn")}」（{slot}），按无效词条处理'
                )
                continue
            value, parse_warning = _parse_stat_value(sub.get('value'))
            if parse_warning is not None:
                warnings.append(f'副词条「{standard}」（{slot}）{parse_warning}')
            parsed_values.append((standard, value))
            if standard in effective:
                # 规则 4：命中按强化次数累计，解析值按标准名累加
                effective_hits += times
                effective_here += times
                bucket = hits_by_stat.setdefault(standard, {'rolls': 0, 'value_sum': 0.0})
                bucket['rolls'] += times
                bucket['value_sum'] += value
            else:
                wasted_here += times
                wasted_rolls_by_stat[standard] = wasted_rolls_by_stat.get(standard, 0) + times
        piece_wasted.append(wasted_here)
        piece_effective.append(effective_here)

    # 规则 5：主词条核对（仅四部位；分母 = 传入期望的部位数；缺件 actual=null）
    main_stat_check: list[dict] = []
    mismatch_count = 0
    expectations = criteria_entry.get('main_stat_expectations')
    if isinstance(expectations, dict) and len(expectations) > 0:
        for slot_key, expected_raw in expectations.items():
            if slot_key not in MAIN_CHECK_SLOTS:
                warnings.append(f'主词条期望部位「{slot_key}」不参与核对，已跳过')
                continue
            expected: set[str] = set()
            if isinstance(expected_raw, list):
                for word in expected_raw:
                    resolved = _resolve_criteria_word(word)
                    if resolved is None:
                        warnings.append(f'主词条期望「{word}」（{slot_key}）未识别，已忽略')
                    else:
                        expected.update(resolved)
            else:
                warnings.append(f'主词条期望（{slot_key}）需为字符串数组，已跳过')
            actual = main_stat_by_slot.get(slot_key)
            matches = actual is not None and actual in expected
            main_stat_check.append({
                'slot': slot_key,
                'actual': actual,
                'expected': sorted(expected),
                'matches': matches,
            })
            if not matches:
                mismatch_count += 1
    elif expectations is not None and not isinstance(expectations, dict):
        warnings.append('main_stat_expectations 需为对象（部位 → 标准名数组），已跳过')

    # 规则 6：毕业线对照（current = 同标准名的主词条（若同名）+ 副词条求和）
    threshold_report: list[dict] = []
    threshold_pass = 0
    threshold_miss = 0
    thresholds = criteria_entry.get('stat_thresholds')
    if isinstance(thresholds, dict) and len(thresholds) > 0:
        for key, line in thresholds.items():
            resolved = _resolve_criteria_word(key)
            if resolved is None:
                warnings.append(f'毕业线词条「{key}」未识别，已跳过')
                continue
            if len(resolved) != 1:
                warnings.append(f'毕业线词条「{key}」展开为多个标准名，无法对照，已跳过')
                continue
            if isinstance(line, bool) or not isinstance(line, (int, float)):
                warnings.append(f'毕业线「{key}」需为数值，已跳过')
                continue
            standard = resolved[0]
            current = round(sum(v for name, v in parsed_values if name == standard), 2)
            gap = current - line
            if gap >= 0:
                threshold_pass += 1
                gap_text = f'达标 +{gap:.1f}'
            else:
                threshold_miss += 1
                gap_text = f'差 {abs(gap):.1f}'
            threshold_report.append(
                {'stat': standard, 'current': current, 'line': line, 'gap_text': gap_text}
            )
    elif thresholds is not None and not isinstance(thresholds, dict):
        warnings.append('stat_thresholds 需为对象（词条 → 数值），已跳过')

    # 规则 7：最弱件（浪费最高，并列取命中更低，仍并列取遍历序先者；
    # 无副词条数据置 null）
    weakest_piece: dict | None = None
    if pieces and total_rolls > 0:
        best = 0
        for idx in range(1, len(pieces)):
            if piece_wasted[idx] > piece_wasted[best] or (
                piece_wasted[idx] == piece_wasted[best]
                and piece_effective[idx] < piece_effective[best]
            ):
                best = idx
        set_name = pieces[best].get('set_name')
        weakest_piece = {
            'set_name': set_name if isinstance(set_name, str) else None,
            'slot': piece_slots[best],
            'effective_hits': piece_effective[best],
            'wasted_rolls': piece_wasted[best],
        }

    hit_ratio: float | None = effective_hits / total_rolls if total_rolls > 0 else None

    # 规则 8：verdict 模板（无主核对/无阈值时省略对应短句）
    if total_rolls == 0:
        verdict = '无遗器数据'
    else:
        verdict = f'命中 {effective_hits}/{total_rolls}（{hit_ratio:.0%}）'
        if isinstance(expectations, dict) and len(expectations) > 0:
            verdict += f'主词条穿错 {mismatch_count} 件；'
        if isinstance(thresholds, dict) and len(thresholds) > 0:
            verdict += f'达标 {threshold_pass} 项、差线 {threshold_miss} 项；'
        if weakest_piece is not None:
            verdict += f'最弱件：{weakest_piece["slot"]}（浪费 {weakest_piece["wasted_rolls"]} 条）'

    return {
        'total_rolls': total_rolls,
        'effective_hits': effective_hits,
        'hit_ratio': hit_ratio,
        'hits_by_stat': {
            name: {'rolls': bucket['rolls'], 'value_sum': round(bucket['value_sum'], 2)}
            for name, bucket in hits_by_stat.items()
        },
        'wasted_rolls_by_stat': wasted_rolls_by_stat,
        'main_stat_check': main_stat_check,
        'threshold_report': threshold_report,
        'weakest_piece': weakest_piece,
        'warnings': warnings,
        'verdict': verdict,
    }


def evaluate(roster_data: list[dict], criteria: list[dict]) -> dict:
    """评估遗器有效词条命中（统一信封；design.md §2.2/§2.3）。

    Args:
        roster_data: ``mys_get_roster_detail`` 返回的 data（角色明细数组，
            元素结构 = CharacterDetail 的 asdict；本函数只读
            name/relics/ornaments 及遗器词条字段）。
        criteria: 每角色口径列表（元素字段见 design.md §2.2 字段表）。

    Returns:
        ``{"status","message","data"}``：
        - ``success``：data = {results, not_found, team_summary}，message
          「共评估 N 名角色，M 名未命中名册」；
        - ``error``：criteria 为空列表 / 元素结构非法 / 存在重复
          character_name（message 列出重复名）/ roster_data 结构非法
          （规则 9/10）。
    """
    criteria_error = _criteria_structure_error(criteria)
    if criteria_error is not None:
        return {'status': 'error', 'message': criteria_error, 'data': None}
    duplicate_error = _duplicate_names_error(criteria)
    if duplicate_error is not None:
        return {'status': 'error', 'message': duplicate_error, 'data': None}
    roster_error = _roster_structure_error(roster_data)
    if roster_error is not None:
        return {'status': 'error', 'message': roster_error, 'data': None}

    roster_by_name: dict[str, dict] = {}
    for element in roster_data:
        name = element['name']
        if isinstance(name, str) and name not in roster_by_name:
            roster_by_name[name] = element

    results: dict[str, dict] = {}
    not_found: list[str] = []
    team_summary: list[dict] = []
    for criteria_entry in criteria:
        name = criteria_entry['character_name']
        entry = roster_by_name.get(name)
        if entry is None:
            # 规则 9：名册缺名记入 not_found，不影响其他角色
            not_found.append(name)
            continue
        result = _evaluate_one(entry, criteria_entry)
        results[name] = result
        team_summary.append({'character_name': name, 'hit_ratio': result['hit_ratio']})

    # team_summary 按命中占比升序，无数据（null）排最后；同值保持 criteria
    # 顺序（稳定排序）
    team_summary.sort(key=lambda item: (
        item['hit_ratio'] is None,
        item['hit_ratio'] if item['hit_ratio'] is not None else 0.0,
    ))
    return {
        'status': 'success',
        'message': f'共评估 {len(results)} 名角色，{len(not_found)} 名未命中名册',
        'data': {'results': results, 'not_found': not_found, 'team_summary': team_summary},
    }
