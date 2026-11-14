# 警告:本文件由 skills/sr-od-dev-currency-war/scripts/gen_traits.py 生成(v4.7 帖子聚合 + config 骨架 + wiki 交叉),勿手编;
# 版本更新重跑生成。重跑: uv run python skills/sr-od-dev-currency-war/scripts/gen_traits.py
"""货币战争 羁绊(trait)数据(官方口径镜像;生成器产物,勿手编)。

29 条(trait_type 0/1/2;type 3 主角光环专属不进本域)。
TRAITS 键 = trait_id(稳定机器键:跨版本 diff/对拍/资产映射);
trait_by_name 键 = trait_name(消费侧标签键型)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraitLayer:
    """羁绊分层效果条目(官方 layers[] 镜像)。"""
    layer: int        # 官方 layers[].layer:激活所需人数档
    quality: int      # 官方 layers[].quality:档品质
    trait_desc: str   # 官方 layers[].trait_desc:分层效果全文(富文本已渲染为纯文本)


@dataclass(frozen=True)
class Trait:
    """单个羁绊条目(官方口径镜像;生成器产物,修正进设计后重跑生成器)。"""
    trait_id: str                  # 官方 trait_id(稳定机器键:跨版本 diff/对拍/资产映射)
    trait_name: str                # 官方 trait_name(消费侧标签键型)
    trait_type: int                # 官方 trait_type:0 阵营 / 1 流派 / 2 独立
    layers: tuple[TraitLayer, ...] # 官方 layers[] 投影(layer 升序)
    members: tuple[str, ...]       # 成员角色规范名(官方 role_ids 经角色注册表翻译;同名多档合并)
    simple_desc: str               # 官方总效果简述
    trait_icon: str                # 官方 trait_icon URL
    count_mode: str = "TOTAL"      # 激活计数控:TOTAL=总上场人数 / STAR3=三星上场人数

    @property
    def tiers(self) -> tuple[int, ...]:
        """激活阈值投影(官方 layers[].layer;兼容既有激活判定消费键型)。"""
        return tuple(layer.layer for layer in self.layers)


TRAITS: dict[str, Trait] = {
    '100102': Trait(
        trait_id='100102',
        trait_name='仙舟舰队',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='变化1件简易装备。'),
            TraitLayer(layer=4, quality=1, trait_desc='变化3件简易装备为推荐装备。【星槎】基于【仙舟舰队】队员累计总伤害造成真实伤害。'),
            TraitLayer(layer=6, quality=2, trait_desc='变化所有简易装备。'),
            TraitLayer(layer=9, quality=3, trait_desc='所有简易装备都会变为特权装备！'),
        ),
        members=('云璃', '寒鸦', '桂乃芬', '椒丘', '灵砂', '雪衣', '飞霄'),
        simple_desc='【仙舟舰队】召唤【星槎】攻击敌人。战斗开始前，【仙舟舰队】队员的部分简易装备临时变为进阶装备！\n我方队员携带更多装备时，可提升【舰队等级】强化【星槎】和【仙舟舰队】队员，每件装备还会使【星槎】速度提高20，【仙舟舰队】队员伤害增幅提高4%。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/8e33e8688f74275077af0a224a43c3ce.png',
        count_mode='TOTAL',
    ),
    '100202': Trait(
        trait_id='100202',
        trait_name='奇兽花园',
        trait_type=0,
        layers=(
            TraitLayer(layer=3, quality=0, trait_desc='30%前/后台强度。每4点【奇美能量】可招聘奇美拉。'),
            TraitLayer(layer=5, quality=1, trait_desc='60%。每3点【奇美能量】可招聘更多种奇美拉，并可刷新1次。'),
            TraitLayer(layer=7, quality=2, trait_desc='120%。每2点【奇美能量】可招聘奇美拉。每个奇美拉星级额外提高倍率和速度。'),
            TraitLayer(layer=10, quality=3, trait_desc='300%。奇美拉全体集结！'),
        ),
        members=('万敌', '海瑟音', '赛飞儿', '那刻夏', '长夜月', '阿格莱雅', '风堇'),
        simple_desc='每节点获得【奇美能量】，用于招聘奇美拉入住【奇兽花园】，角色专属奇美拉还可以二合一升星！【奇兽花园】角色获得前/后台强度。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/55ced9b489792a141d4288903315d1e7.png',
        count_mode='TOTAL',
    ),
    '100302': Trait(
        trait_id='100302',
        trait_name='幻月游戏',
        trait_type=0,
        layers=(
            TraitLayer(layer=3, quality=0, trait_desc='幻月游戏'),
            TraitLayer(layer=5, quality=1, trait_desc='幻月游戏'),
            TraitLayer(layer=7, quality=2, trait_desc='幻月游戏'),
            TraitLayer(layer=10, quality=3, trait_desc='幻月游戏'),
        ),
        members=('不死途', '千冶·刃', '星期日', '火花', '真珠', '绯英', '银狼LV.999'),
        simple_desc='每局游戏开始时，【幻月游戏】将为你带来不同的游戏规则。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/020319b765d0c0e325cf9a2d77203a84.png',
        count_mode='TOTAL',
    ),
    '100402': Trait(
        trait_id='100402',
        trait_name='星间旅人',
        trait_type=0,
        layers=(
            TraitLayer(layer=1, quality=0, trait_desc='100%加成。'),
            TraitLayer(layer=2, quality=0, trait_desc='120%加成。'),
            TraitLayer(layer=3, quality=1, trait_desc='140%加成。'),
            TraitLayer(layer=4, quality=1, trait_desc='170%加成。'),
            TraitLayer(layer=5, quality=2, trait_desc='200%加成。'),
            TraitLayer(layer=6, quality=2, trait_desc='240%加成。'),
            TraitLayer(layer=7, quality=2, trait_desc='290%加成。'),
            TraitLayer(layer=8, quality=2, trait_desc='350%加成。'),
        ),
        members=('克拉拉', '大黑塔', '娜塔莎', '忘归人', '波提欧', '砂金', '罗刹'),
        simple_desc='【星间旅人】角色会为你的小队提高特定属性，随场上【星间旅人】角色数量而提升。\n【星间旅人】队员获得双倍收益。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/476eb61290a95257c3f3825a01dcce58.png',
        count_mode='TOTAL',
    ),
    '100502': Trait(
        trait_id='100502',
        trait_name='开拓银轨',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='20【开拓力】。星穹列车，启动！'),
            TraitLayer(layer=4, quality=1, trait_desc='45【开拓力】。商品变得更好。'),
            TraitLayer(layer=6, quality=2, trait_desc='75【开拓力】。商品变得更好，并出现羁绊专属改件。'),
            TraitLayer(layer=8, quality=2, trait_desc='125【开拓力】。'),
            TraitLayer(layer=10, quality=3, trait_desc='225【开拓力】！列车进化！'),
        ),
        members=('三月七', '丹恒·饮月', '姬子·启行', '帕姆王', '开拓者', '星期日', '瓦尔特'),
        simple_desc='每个战斗阶段后积攒【开拓力】，可在【开拓商店】内购买角色和道具。随着羁绊层级提升，【开拓商店】还会解锁更稀有的商品！',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/3960bd6e5d75f938bf31c041da55dbed.png',
        count_mode='TOTAL',
    ),
    '100602': Trait(
        trait_id='100602',
        trait_name='千星商会',
        trait_type=0,
        layers=(
            TraitLayer(layer=1, quality=0, trait_desc='每次花费金币刷新商店时，获得1点经验。'),
            TraitLayer(layer=2, quality=1, trait_desc='进入新节点时，获得1次免费刷新。'),
            TraitLayer(layer=3, quality=1, trait_desc='进入新节点时，商店中出现1个【千星商会】角色。星级提供的属性加成提高100%。'),
            TraitLayer(layer=4, quality=2, trait_desc='开启千星宝库，从中挑选战利品!'),
            TraitLayer(layer=5, quality=2, trait_desc='获得【千星·特权赋予卡】。根据本局商店刷新次数充值该卡，每15次可用次数+1。'),
            TraitLayer(layer=6, quality=3, trait_desc='商店中的角色随机升星为2/3/4星，但只需要1星的价格即可购买！'),
        ),
        members=('托帕&账账', '爻光', '真珠', '知更鸟·晴歌', '砂金·戏浪', '翡翠'),
        simple_desc='每上场1位3星【千星商会】角色，将激活1级羁绊效果。\n每位【千星商会】角色为羁绊内队员提供2%幸运一击率和幸运一击伤害，加成随星级提高。\n【千星商会】角色的出现概率不会随着商店等级提升而下降。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/d2838735fca282c94b0a664576221c6a.png',
        count_mode='STAR3',
    ),
    '100702': Trait(
        trait_id='100702',
        trait_name='云上五骁',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='【五骁连携】造成等同于300%基础伤害的【云上五骁】队员对应属性伤害，并使我方小队获得10%伤害增幅，可叠加。'),
            TraitLayer(layer=3, quality=1, trait_desc='速度提高至250，倍率提高至600%，20%。'),
            TraitLayer(layer=4, quality=2, trait_desc='速度提高至300，倍率提高至1200%，40%。'),
            TraitLayer(layer=5, quality=2, trait_desc='五骁聚首！【云上五骁】队员获得120%，70%，50%，50%。速度提高至400，倍率提高至2400%，60%。'),
        ),
        members=('丹恒·饮月', '刃', '景元', '白露', '镜流'),
        simple_desc='【云上五骁】队员的伤害增幅提高，并在行动条上召唤【五骁连携】，行动时攻击敌方全体，并在攻击后使我方小队伤害增幅提高，可叠加。【云上五骁】队员行动后，使【五骁连携】行动提前。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/0cb741fe47937abbef057e91e089568b.png',
        count_mode='TOTAL',
    ),
    '100802': Trait(
        trait_id='100802',
        trait_name='星核猎手',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='解锁并发放1件装备。剧本装备提供20%/8%伤害增幅。'),
            TraitLayer(layer=3, quality=1, trait_desc='解锁并发放2件装备。'),
            TraitLayer(layer=5, quality=2, trait_desc='解锁并发放3件装备。剧本装备提供30%/12%。'),
            TraitLayer(layer=7, quality=3, trait_desc='羁绊发放的装备全部变为特权装备，剧本装备提供60%/24%。'),
        ),
        members=('千冶·刃', '卡芙卡', '开拓者', '流萤', '银狼LV.999'),
        simple_desc='艾利欧为【星核猎手】揭示3件进阶装备为本局剧本装备，并随羁绊等级解锁并发放。\n不同类型的剧本装备，将为装备者/我方小队将提供伤害增幅，【星核猎手】穿戴时双倍生效。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/f448aaeb024e3bb3dd9ec09038f76674.png',
        count_mode='TOTAL',
    ),
    '100902': Trait(
        trait_id='100902',
        trait_name='小小巨人',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='获得1点【身高】。敌人受到的伤害提高12%，造成的伤害降低6%。'),
            TraitLayer(layer=3, quality=1, trait_desc='获得2点。敌人受到的伤害提高24%，造成的伤害降低12%。'),
            TraitLayer(layer=4, quality=2, trait_desc='获得3点。敌人受到的伤害提高36%，造成的伤害降低18%。'),
            TraitLayer(layer=5, quality=2, trait_desc='获得4点。敌人受到的伤害提高48%，造成的伤害降低24%。'),
            TraitLayer(layer=6, quality=2, trait_desc='获得6点。敌人受到的伤害提高60%，造成的伤害降低30%。'),
        ),
        members=('刻律德菈', '符玄', '缇宝', '花火', '藿藿'),
        simple_desc='敌人受到的伤害提高，造成的伤害降低。\n【小小巨人】可随羁绊层数不断提升【身高】，以强化技能效果！',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/23ff056ccda2ef7c993e197569b2a4c8.png',
        count_mode='TOTAL',
    ),
    '101002': Trait(
        trait_id='101002',
        trait_name='梦境交织',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='总计行动12次后将触发【共舞】。'),
            TraitLayer(layer=3, quality=1, trait_desc='战斗中，舞伴互相提供40%和20%，取较高项。'),
            TraitLayer(layer=4, quality=2, trait_desc='【共舞】效果提高。80%和40%转化。'),
            TraitLayer(layer=5, quality=2, trait_desc='【共舞】效果提高。120%和60%转化。'),
        ),
        members=('大丽花', '花火', '长夜月', '黄泉', '黑天鹅'),
        simple_desc='选择两位【梦境交织】角色，总计行动12次后触发【共舞】，共同进行攻击。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/8bcabf666c41ad1aa1358539a7befc24.png',
        count_mode='TOTAL',
    ),
    '101102': Trait(
        trait_id='101102',
        trait_name='少女乐队',
        trait_type=0,
        layers=(
            TraitLayer(layer=1, quality=0, trait_desc='独奏，获得该队员的效果。'),
            TraitLayer(layer=4, quality=2, trait_desc='全员大合奏！所有队员提供三倍效果！'),
        ),
        members=('乱破', '希露瓦', '火花', '知更鸟'),
        simple_desc='【少女乐队】进行独奏或全员大合奏：仅在上场恰好1/4名【少女乐队】角色时激活羁绊。\n每位【少女乐队】队员都可为我方小队提供独特效果。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/6f79d3d77fb01b7f22ce2a9b67d72b97.png',
        count_mode='TOTAL',
    ),
    '101202': Trait(
        trait_id='101202',
        trait_name='黄金大饭店',
        trait_type=0,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='获得第一道餐品。'),
            TraitLayer(layer=3, quality=1, trait_desc='获得第二道餐品。'),
            TraitLayer(layer=4, quality=2, trait_desc='餐品激活额外加成，变得更好吃！'),
        ),
        members=('万敌', '昔涟', '白厄', '遐蝶'),
        simple_desc='每局游戏中，根据今日菜单，获得仅供【黄金大饭店】角色穿戴的招牌菜改件。【黄金大饭店】角色的总星级计为【饭店星级】。【饭店星级】越高，餐品效果越好！',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/1abc74368838f82fde1eb56e2e128439.png',
        count_mode='TOTAL',
    ),
    '200102': Trait(
        trait_id='200102',
        trait_name='追击',
        trait_type=1,
        layers=(
            TraitLayer(layer=3, quality=0, trait_desc='20%前/后台强度。伤害的20%累积为【KO值】。'),
            TraitLayer(layer=5, quality=1, trait_desc='50%。30%累积比例。'),
            TraitLayer(layer=7, quality=2, trait_desc='80%。50%累积比例。触发【KO】时，对相邻敌人造成附加伤害。'),
            TraitLayer(layer=10, quality=3, trait_desc='160%。100%累积比例，附加伤害倍率大幅提高。触发【KO】时，额外造成大量量子属性伤害。'),
        ),
        members=('三月七', '不死途', '托帕&账账', '知更鸟', '砂金', '缇宝', '飞霄'),
        simple_desc='敌人受到伤害后，可累积【KO值】以触发斩杀。\n【追击】队员前/后台强度提高，攻击后额外累积【KO值】。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/cb1110dc8d36afef6b5120b23bbe40f0.png',
        count_mode='TOTAL',
    ),
    '200202': Trait(
        trait_id='200202',
        trait_name='持续伤害',
        trait_type=1,
        layers=(
            TraitLayer(layer=3, quality=0, trait_desc='20%持续伤害增幅。'),
            TraitLayer(layer=5, quality=1, trait_desc='50%。【深红荆棘】速度提高至300。'),
            TraitLayer(layer=7, quality=2, trait_desc='100%。【深红荆棘】行动时，额外结算1次持续伤害。'),
            TraitLayer(layer=9, quality=3, trait_desc='180%。【深红荆棘】速度提高至500，基础伤害提高至2000%，结算倍率提高至600%。'),
        ),
        members=('卡芙卡', '娜塔莎', '希露瓦', '桂乃芬', '椒丘', '海瑟音', '黑天鹅'),
        simple_desc='【持续伤害】队员的持续伤害增幅提高，召唤【深红荆棘】攻击敌人，施加并结算持续伤害。\n我方行动中使敌人陷入持续伤害时，【深红荆棘】的结算倍率提高且行动提前。\n我方小队获得伤害减免。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/62749197e606c42451e43b06de19015d.png',
        count_mode='TOTAL',
    ),
    '200302': Trait(
        trait_id='200302',
        trait_name='群攻',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='15%伤害增幅。【灵魂】的转移效率为15%。'),
            TraitLayer(layer=4, quality=1, trait_desc='30%。20%转移效率。使首领敌人受到的伤害提高50%。'),
            TraitLayer(layer=6, quality=2, trait_desc='60%。转移效率提高至25%。【灵魂】记录受到的伤害，并在本体被消灭或行动时基于记录值造成伤害。使首领敌人受到的伤害提高50%。'),
            TraitLayer(layer=8, quality=2, trait_desc='120%。30%转移效率，记录比例提高至50%。使首领敌人受到的伤害提高50%。'),
        ),
        members=('千冶·刃', '大黑塔', '灵砂', '瓦尔特', '翡翠', '赛飞儿', '黄泉'),
        simple_desc='【群攻】队员的伤害增幅提高。战斗中，为生命上限最高的敌人创造能够转移伤害的【灵魂】。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/438ecca139441155cf93da47c1656773.png',
        count_mode='TOTAL',
    ),
    '200402': Trait(
        trait_id='200402',
        trait_name='连击',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='15%幸运一击率。10%【连击率】。'),
            TraitLayer(layer=4, quality=1, trait_desc='30%。20%，后台1号位额外生成【连击地格】。【连击地格】上的角色在消耗获得的额外回合内额外造成30%真实伤害，首次施放普攻或战技后必定连击。'),
            TraitLayer(layer=6, quality=2, trait_desc='45%。30%，连击时额外造成60%真实伤害。'),
            TraitLayer(layer=8, quality=2, trait_desc='60%。40%，连击时额外造成90%真实伤害。'),
        ),
        members=('刻律德菈', '寒鸦', '星期日', '白露', '那刻夏', '镜流', '阿格莱雅'),
        simple_desc='【连击】队员的幸运一击率提高。在场上生成【连击地格】，可提供普攻/战技伤害增幅和【连击率】。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/3306c48f615c29c427be9ffc5c8abe16.png',
        count_mode='TOTAL',
    ),
    '200502': Trait(
        trait_id='200502',
        trait_name='击破',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='20%击破伤害增幅，10%速度增幅。【多重韧性条】为初始值的60%。'),
            TraitLayer(layer=4, quality=1, trait_desc='40%，20%。52%【多重韧性条】。'),
            TraitLayer(layer=6, quality=2, trait_desc='60%，30%。44%【多重韧性条】。'),
            TraitLayer(layer=8, quality=3, trait_desc='100%，50%。36%【多重韧性条】。'),
        ),
        members=('乱破', '大丽花', '忘归人', '波提欧', '流萤', '雪衣'),
        simple_desc='【击破】队员的击破伤害增幅和速度增幅提高。\n敌人获得【多重韧性条】：初始韧性被削减至0后可继续削减，被削减至0时再次受到弱点击破伤害。敌人被击破时还会受到额外伤害。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/06a79656fbf13329ce0ee6c2cf4bd048.png',
        count_mode='TOTAL',
    ),
    '200602': Trait(
        trait_id='200602',
        trait_name='召唤',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='20%前/后台强度。1点【召唤力】。'),
            TraitLayer(layer=4, quality=1, trait_desc='40%前/后台强度。2点【召唤力】。'),
            TraitLayer(layer=6, quality=2, trait_desc='80%前/后台强度。3点【召唤力】。'),
            TraitLayer(layer=8, quality=2, trait_desc='180%前/后台强度。4点【召唤力】。'),
        ),
        members=('昔涟', '景元', '知更鸟·晴歌', '遐蝶', '长夜月', '风堇'),
        simple_desc='【召唤】队员的前/后台强度提高，并获得20%生命增幅。\n激活【召唤】专属角色赋能。根据【召唤力】增强其效果。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/9ca54424af8db57fa98fc29a079c4b14.png',
        count_mode='TOTAL',
    ),
    '200702': Trait(
        trait_id='200702',
        trait_name='欢愉',
        trait_type=1,
        layers=(
            TraitLayer(layer=3, quality=0, trait_desc='10%幸运一击率，6%速度增幅。'),
            TraitLayer(layer=5, quality=1, trait_desc='20%，12%。二星阿哈，2个装备栏，出现【阿哈小道具】。'),
            TraitLayer(layer=6, quality=2, trait_desc='30%，18%。三星阿哈，3个装备栏，更妙妙的【阿哈小道具】。'),
            TraitLayer(layer=8, quality=3, trait_desc='40%，24%。四星阿哈，竟然能穿4件装备？！有较高概率掉落棱彩晶矿。'),
        ),
        members=('星神★阿哈', '火花', '爻光', '砂金·戏浪', '花火', '银狼LV.999'),
        simple_desc='【欢愉】队员的幸运一击率和速度增幅提高。\n备战阶段召唤【阿哈】为小队提供增益，【阿哈】拥有初始属性并穿戴3件随机简易装备，可从商店购买【阿哈装备】拖拽给【阿哈】，依次合成对应进阶装备。\n商店中也有概率刷出【阿哈小道具】！【阿哈】会参演阿哈时刻，并有概率掉落晶矿奖励！',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/69f83217bc9f68c03f8c05283d8c91aa.png',
        count_mode='TOTAL',
    ),
    '200802': Trait(
        trait_id='200802',
        trait_name='反击',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='反伤造成500%基础反击伤害。【挑衅】使敌方全体受到的伤害提高20%。'),
            TraitLayer(layer=4, quality=1, trait_desc='800%倍率反伤。【挑衅】使敌方全体受到的伤害提高40%。'),
            TraitLayer(layer=6, quality=2, trait_desc='1200%倍率反伤。【挑衅】使敌方全体受到的伤害提高80%。'),
        ),
        members=('万敌', '云璃', '克拉拉', '刃', '符玄'),
        simple_desc='装备最多的前台【反击】角色成为【反击王】：更易受到攻击并【反伤】。\n进入战斗时，每个后台【反击】角色为其提供30%伤害增幅，10%生命增幅。【反击】队员可以【挑衅】敌方目标。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/bbe5df1fcc8b8c4a81e3e34b4d4e94b8.png',
        count_mode='TOTAL',
    ),
    '200902': Trait(
        trait_id='200902',
        trait_name='能量',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='激活2名【能量】角色的终结技，【能量】队员获得25%伤害增幅。'),
            TraitLayer(layer=4, quality=1, trait_desc='激活所有【能量】角色的终结技，50%。'),
            TraitLayer(layer=6, quality=2, trait_desc='激活我方小队全体的终结技！100%。'),
        ),
        members=('姬子·启行', '开拓者', '知更鸟·晴歌', '绯英', '藿藿'),
        simple_desc='我方小队获得10%伤害增幅，并在施放终结技后积攒充能。首次充满5点后，【能量】队员立即激活终结技，并获得额外伤害增幅。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/c17221a6cca3abde0d1d2e831ebb7b28.png',
        count_mode='TOTAL',
    ),
    '201002': Trait(
        trait_id='201002',
        trait_name='治疗',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='治疗强度提高20%。'),
            TraitLayer(layer=4, quality=1, trait_desc='提高40%。'),
            TraitLayer(layer=6, quality=2, trait_desc='60%，我方小队获得60%伤害增幅。'),
        ),
        members=('娜塔莎', '灵砂', '白露', '罗刹', '藿藿', '风堇'),
        simple_desc='我方小队伤害减免12%。【治疗】队员的治疗强度提高。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/21edb47ee01463dd31899bd99eb809bf.png',
        count_mode='TOTAL',
    ),
    '201102': Trait(
        trait_id='201102',
        trait_name='守护',
        trait_type=1,
        layers=(
            TraitLayer(layer=2, quality=0, trait_desc='20%护盾强度。50%生命上限+100%防御力。'),
            TraitLayer(layer=3, quality=1, trait_desc='40%。90%生命上限+160%防御力。'),
        ),
        members=('真珠', '砂金', '符玄'),
        simple_desc='我方小队护盾强度提高。【守护】队员施放终结技后，基于自身生命上限和防御力，为我方前台回复生命值。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/235d8c536a7bff8e09252221047501d6.png',
        count_mode='TOTAL',
    ),
    '300102': Trait(
        trait_id='300102',
        trait_name='双龙吟',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='进入战斗时，在后台区域召唤【丹恒•腾荒】。'),
            TraitLayer(layer=2, quality=4, trait_desc='1/2/3星时，可为【丹恒•腾荒】穿戴1/2/3件装备。'),
        ),
        members=('丹恒·饮月',),
        simple_desc='【丹恒•饮月】在后台区域召唤星级相同的【丹恒•腾荒】，并复制其穿戴的装备以获得相应效果，可穿戴数量随星级提高。\n【丹恒•饮月】/【丹恒•腾荒】行动后为【双龙吟】充能，充能满时合击敌人并提供护盾。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/5a0c1a67a05d18adba7c14f4d3395916.png',
        count_mode='TOTAL',
    ),
    '300202': Trait(
        trait_id='300202',
        trait_name='盗火行者',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='每个备战阶段，可将1个角色持续拖动给白厄以转化为火种，根据其价值永久获得【薪火】点数，黄金裔能转化更多。'),
        ),
        members=('白厄',),
        simple_desc='可将角色持续拖动给白厄以吸收火种转化为【薪火】，为自身或小队提供增益。黄金裔能转化更多。\n战斗中出现【盗火行者】，可盗取挑战进度上限，并在进度达到上限时发动【灭世】，获得战斗胜利。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/a1bc491a1938ab7c340c25d59637b4c5.png',
        count_mode='TOTAL',
    ),
    '300302': Trait(
        trait_id='300302',
        trait_name='巡海游侠',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='任命1名前台角色为【巡海游侠】。'),
            TraitLayer(layer=2, quality=4, trait_desc='每名【巡海游侠】提供12%伤害增幅，12%速度增幅，2/3/4星角色提供2/4/8倍。'),
        ),
        members=('不死途',),
        simple_desc='不死途在场时，选择1名前台角色，将其任命为【巡海游侠】，【巡海游侠】们的星级会提高他们的伤害增幅和速度增幅。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/65343a5ae2627977158aa9c1278f0a81.png',
        count_mode='TOTAL',
    ),
    '300402': Trait(
        trait_id='300402',
        trait_name='黑市主理人',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='1/2/3星翡翠会出售1/2/3种随节点刷新的普通商品。'),
        ),
        members=('翡翠',),
        simple_desc='作为货币战争主理人，翡翠利用职务之便，为你打开可购买各类道具的黑市商店。\n黑市商店出售一款可无限次购买的招牌商品，和一些随节点刷新的轮换商品。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/110b153228307f0f1db2243513694248.png',
        count_mode='TOTAL',
    ),
    '300502': Trait(
        trait_id='300502',
        trait_name='机心巧匠',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='克拉拉为史瓦罗提供多种改装模组，拥有任意颜色的改装模组时，同色改装出现的概率会提高。\n每拥有1个改装，克拉拉的伤害增幅提高6%。'),
        ),
        members=('克拉拉',),
        simple_desc='每进入2个新节点，克拉拉就可对史瓦罗进行强化改装，提供多种方向的强力效果。\n克拉拉心灵手巧，上场时立即进行首次强化改装，前3次改装仅需进入1个新节点就可触发。',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/b7c53156722a67f789f652e22cd65f65.png',
        count_mode='TOTAL',
    ),
    '300602': Trait(
        trait_id='300602',
        trait_name='幻乐之主',
        trait_type=2,
        layers=(
            TraitLayer(layer=1, quality=4, trait_desc='星神★阿哈提升费用时，祂在商店中的神迹效果也逐渐变强。'),
        ),
        members=('星神★阿哈',),
        simple_desc='获取星神★阿哈可积攒【幻月之力】，以提高祂的费用。借助【幻月游戏】或【欢愉】的角色总星级，阿哈寻回属于祂的星神之力，升格为7费的欢愉星神！\n\n星神★阿哈的目光垂落于商店，欢愉神迹随之降临：商店中出现阿哈的神迹、更幸运的阿哈小道具与更高费用的角色！',
        trait_icon='https://act-webstatic.mihoyo.com/darkmatter/hkrpg/prod_gf_cn/item_icon_ubd4re/5a25c6a8aad4ecb6664140756dff3932.png',
        count_mode='TOTAL',
    ),
}

# members 口径(可组队员,B2):官方 role_ids 经角色注册表翻译,is_hide=True
# 条目过滤(召唤物不算成员——腾荒类隐藏随从帖内 role_ids 有名但不入玩家
# 编队),同名多档合并为角色;与官方 role_ids 的差集进成员对拍例外清单人裁。
# 召唤型激活特例(双龙吟类激活 = 上场成员 + 后台召唤物,通用人数计数不适用)
# 与 count_mode 接线同批归策略批,板面计数接线批须按羁绊特例处理。
trait_by_name: dict[str, Trait] = {t.trait_name: t for t in TRAITS.values()}
