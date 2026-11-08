"""生成光锥晋阶材料表(分段):BWIKI 逐光锥页面 → src/sr_od/config 常量文件。

数据流:BWIKI 逐光锥页(每把光锥自己的晋阶材料表) → 本脚本(拉取+解析)
→ light_cone_ascension_const.py。版本更新后重跑刷新(数据块禁手改)。

为什么源是 BWIKI 而非官方 wiki:官方光锥页实证只有等级属性模板,无突破
材料组件(probe 2026-11-08);BWIKI 逐光锥页的分段表与实机对账吻合
(锚点见 _ASCENSION_ANCHORS:惊魂夜 60+70 级段累计 = 计数条实读 永恒之花
15/永寿荣枝 14)。历史注意:BWIKI 的「材料→光锥」聚合反查页是旧口径,
与逐光锥分段表不是一回事,勿混用。

表结构(实测):含 cailiaoxiao div 的 table,「X～Y级」行 = 经验段
(稀薄以太+信用点),「Y级」行 = 突破段(突破材料+信用点);行组为
<th>阶段</th> + <td>材料格</td> 交替,一格含多组
`class="cailiaoxiao"><a title=材料名>…<div>数量</div>`。

用法:PYTHONPATH=src 下 uv run python tools/game_data/generate_light_cone_ascension_const.py
"""
import json
import re
import time
import urllib.parse
import urllib.request

DELAY = 0.8
BWIKI_BASE = 'https://wiki.biligame.com/sr/'
LC_CONST_PATH = 'src/sr_od/config/light_cone_ascension_const.py'
WIKI_CHANNEL_LIGHT_CONE = 19

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')

#: 生成锚点:光锥 → (段名列表, {材料: 累计数});与实机计数条不符即拒绝生成。
#: 锚点来源 2026-11-08 惊魂夜晋阶画面实读(50 级卡点,可提升至 80 级,
#: 材料栏 永恒之花 0/15、永寿荣枝 x/14)
_ASCENSION_ANCHORS: dict[str, tuple[list[str], dict[str, int]]] = {
    '惊魂夜': (['60级', '70级'], {'永恒之花': 15, '永寿荣枝': 14}),
}

#: 解析成功的光锥数下限(结构 sanity:170 把源里绝大多数应有分段表)
_MIN_PARSED_CONES = 140


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    if payload.get('retcode') != 0:
        raise RuntimeError(f'retcode={payload.get("retcode")} url={url}')
    return payload


def channel_items(channel_id: int) -> list[dict]:
    resp = get_json(
        f'https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1'
        f'/home/content/list?app_sn=sr_wiki&channel_id={channel_id}&lang=zh-cn')
    items: list[dict] = []
    for group in resp['data']['list']:
        items.extend(group.get('list') or [])
    return items


def fetch_bwiki_page(title: str) -> str:
    """BWIKI 页面 HTML;567(EdgeOne 临时封禁)/5xx 退避重试 3 次。"""
    url = BWIKI_BASE + urllib.parse.quote(title)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'fetch failed: {url}')


_MAT_DIV_RE = re.compile(
    r'class="cailiaoxiao"><a[^>]*title="([^"]+)"[^>]*>.*?<div>([\d,]+)</div>', re.S)
_STAGE_TH_RE = re.compile(r'<th>(.*?)</th>', re.S)
_TD_RE = re.compile(r'<td.*?</td>', re.S)
_TR_RE = re.compile(r'<tr.*?</tr>', re.S)
_TABLE_RE = re.compile(r'<table.*?</table>', re.S)
_STRIP_TAG_RE = re.compile(r'<[^>]+>|\s+')


def _strip(text: str) -> str:
    return _STRIP_TAG_RE.sub('', text)


def parse_ascension_stages(html: str) -> dict[str, dict[str, int]] | None:
    """BWIKI 页 HTML → {段名: {材料: 数量}};无晋阶表返回 None。"""
    stages: dict[str, dict[str, int]] = {}
    for table in _TABLE_RE.findall(html):
        if 'cailiaoxiao' not in table:
            continue
        pending_stages: list[str] = []
        for row in _TR_RE.findall(table):
            ths = _STAGE_TH_RE.findall(row)
            if ths:
                pending_stages = [_strip(t) for t in ths]
                continue
            cells = _TD_RE.findall(row)
            # 容错取短边:个别行阶段格/材料格错位时宁缺勿错(完整性由锚点与
            # 解析数下限兜底)
            for stage, cell in zip(pending_stages, cells, strict=False):
                mats: dict[str, int] = {}
                for chunk in cell.split('class="cailiaoxiao"')[1:]:
                    tm = re.search(r'title="([^"]+)"', chunk)
                    cm = re.search(r'<div>([\d,]+)</div>', chunk)
                    if tm and cm:
                        mats[tm.group(1)] = int(cm.group(1).replace(',', ''))
                if mats:
                    stages[stage] = mats
    return stages or None


def fetch_all() -> dict[str, dict[str, dict[str, int]]]:
    """全部光锥的分段晋阶材料;失败页跳过并记警告。"""
    cones = channel_items(WIKI_CHANNEL_LIGHT_CONE)
    print(f'光锥条目: {len(cones)}')
    result: dict[str, dict[str, dict[str, int]]] = {}
    skipped: list[str] = []
    for idx, item in enumerate(cones):
        title = str(item.get('title') or '').strip()
        if not title:
            continue
        try:
            html = fetch_bwiki_page(title)
            stages = parse_ascension_stages(html)
        except Exception as exc:
            skipped.append(f'{title}: {exc}')
            stages = None
        if stages:
            result[title] = stages
        else:
            skipped.append(f'{title}: 页面无晋阶表')
        time.sleep(DELAY)
        if (idx + 1) % 20 == 0:
            print(f'  进度 {idx + 1}/{len(cones)},成功 {len(result)}')
    if len(result) < _MIN_PARSED_CONES:
        raise RuntimeError(
            f'解析成功 {len(result)} 把 < 下限 {_MIN_PARSED_CONES},疑似封禁/改版,拒绝生成;'
            f'跳过明细: {skipped[:10]}')
    for warn in skipped:
        print(f'  [跳过] {warn}')
    return result


def _check_anchors(data: dict[str, dict[str, dict[str, int]]]) -> None:
    """锚点校验:指定段累计材料与实机计数条不符即拒绝生成。"""
    for cone, (stage_names, expected) in _ASCENSION_ANCHORS.items():
        stages = data.get(cone)
        if stages is None:
            raise RuntimeError(f'锚点光锥 {cone} 无解析结果')
        cum: dict[str, int] = {}
        for stage_name in stage_names:
            for name, cnt in stages.get(stage_name, {}).items():
                cum[name] = cum.get(name, 0) + cnt
        for name, want in expected.items():
            got = cum.get(name)
            if got != want:
                raise RuntimeError(
                    f'锚点不符: {cone} {stage_names} 累计 {name} 期望 {want}, 实得 {got}')


def main() -> None:
    data = fetch_all()
    _check_anchors(data)
    write_const(data)
    print('完成')


def write_const(data: dict[str, dict[str, dict[str, int]]]) -> None:
    head = '''"""光锥晋阶材料表(分段):每段为一次晋阶(等级上限提升)的材料消耗。

本文件由 tools/game_data/generate_light_cone_ascension_const.py 从 BWIKI
逐光锥页面生成,**禁手改**(数据修正走重新生成)。源与口径:
- 官方 wiki 光锥页无结构化突破数据(实证),故源用 BWIKI 逐光锥页;
- 准确性锚点:惊魂夜 60+70 级段累计(永恒之花 15/永寿荣枝 14)与实机
  晋阶画面计数条(2026-11-08 实读)一致;
- 段名口径:「Y级」= 突破段(突破材料+信用点),「X～Y级」= 经验段
  (稀薄以太+信用点;稀薄以太为最低档经验材料,界面按所持书籍折算显示);
- 副本归属查询走 dungeon_drop_const.find_missions_by_material(材料级,
  与具体光锥无关)。
"""
'''
    body = json.dumps(data, ensure_ascii=False, indent=1)
    tail = '''

class LightConeStage:
    """单次晋阶(一段)的材料需求。"""

    def __init__(self, name: str, materials: dict[str, int]):
        self.name: str = name
        """段名(BWIKI 口径:「30级」=突破段,「20～30级」=经验段)"""
        self.materials: dict[str, int] = materials
        """该段材料需求 {材料名: 数量}"""


class LightConeAscension:
    """一把光锥的完整晋阶材料表(含经验段与突破段)。"""

    def __init__(self, cn_name: str, stages: list[LightConeStage]):
        self.cn_name: str = cn_name
        """光锥中文名"""
        self.stages: list[LightConeStage] = stages
        """段列表(按游戏内顺序)"""

    @property
    def total(self) -> dict[str, int]:
        """满晋阶总量(各段合并)——判材料缺口用"""
        result: dict[str, int] = {}
        for stage in self.stages:
            for name, amount in stage.materials.items():
                result[name] = result.get(name, 0) + amount
        return result

    def total_between(self, stage_names: list[str]) -> dict[str, int]:
        """指定段名集合的累计材料(段名与 stages[].name 精确匹配)。"""
        result: dict[str, int] = {}
        for stage in self.stages:
            if stage.name in stage_names:
                for name, amount in stage.materials.items():
                    result[name] = result.get(name, 0) + amount
        return result


def get_light_cone_ascension(cn_name: str) -> LightConeAscension | None:
    """光锥中文名 → 晋阶材料表;表内无该光锥返回 None。"""
    stages = _LC_ASCENSION_DATA.get(cn_name)
    if stages is None:
        return None
    return LightConeAscension(
        cn_name, [LightConeStage(name, mats) for name, mats in stages.items()])


def find_material_totals_by_light_cone(cn_name: str) -> dict[str, int]:
    """光锥中文名 → 满晋阶材料总量;表内无该光锥返回空 dict。"""
    ascension = get_light_cone_ascension(cn_name)
    return ascension.total if ascension is not None else {}
'''
    with open(LC_CONST_PATH, 'w', encoding='utf-8') as f:
        f.write(head)
        f.write('\n_LC_ASCENSION_DATA: dict[str, dict[str, dict[str, int]]] = ')
        f.write(body)
        f.write('\n')
        f.write(tail)
    print(f'已生成 {LC_CONST_PATH} ({len(data)} 把光锥)')


if __name__ == '__main__':
    main()
