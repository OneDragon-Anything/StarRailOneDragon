from typing import Optional

from one_dragon.base.config.yaml_config import YamlConfig


class TrickSnackConfig(YamlConfig):

    def __init__(self, instance_idx: Optional[int] = None):
        YamlConfig.__init__(self, 'trick_snack', instance_idx=instance_idx)


    @property
    def route_yll6_xzq(self) -> bool:
        return self.get('route_yll6_xzq', True)

    @route_yll6_xzq.setter
    def route_yll6_xzq(self, new_value: bool) -> None:
        self.update('route_yll6_xzq', new_value)

    @property
    def route_xzlf_xchzs(self) -> bool:
        return self.get('route_xzlf_xchzs', True)

    @route_xzlf_xchzs.setter
    def route_xzlf_xchzs(self, new_value: bool) -> None:
        self.update('route_xzlf_xchzs', new_value)

    @property
    def synthesize_trick_snack(self) -> bool:
        return self.get('synthesize_trick_snack', True)

    @synthesize_trick_snack.setter
    def synthesize_trick_snack(self, new_value: bool) -> None:
        self.update('synthesize_trick_snack', new_value)
