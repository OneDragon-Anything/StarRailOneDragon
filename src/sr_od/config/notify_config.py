from one_dragon.base.config.basic_notify_config import BasicNotifyConfig


class NotifyConfig(BasicNotifyConfig):

    @property
    def app_list(self) -> dict:
        sr_app_list = {
        'assignments': '委托',
        'echo_of_war': '历战余响',
        'trailblaze_power': '开拓力',
        'world_patrol': '锄大地',
        'sim_universe': '模拟宇宙',
        'relic_salvage': '遗器分解',
        'email': '邮件',
        'buy_xianzhou_parcel': '仙舟过期邮包',
        'trick_snack': '奇巧零食',
        'memory_crystal_shard': '记忆残晶',
        'support_character': '支援角色奖励',
        'daily_training': '每日实训',
        'nameless_honor': '无名勋礼',
        }
        return self.get('app_list', sr_app_list)
