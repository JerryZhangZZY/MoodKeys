import logging

from enum import Enum


class LightEntry:
    brightness = None
    effect = None
    effect_speed = None
    color = None
    color_abs = None

    class Color(Enum):
        WHITE = [255, 255, 255]
        RED = [255, 0, 0]
        GREEN = [0, 255, 0]
        BLUE = [0, 0, 255]

    class Effect(Enum):
        STANDBY = 1
        WARNING = 2

    def __init__(self, light_effect=None):
        if light_effect:
            if light_effect == LightEntry.Effect.STANDBY:
                self.effect = 5
                self.effect_speed = 100
                self.color_abs = LightEntry.Color.WHITE.value
            elif light_effect == LightEntry.Effect.WARNING:
                self.effect = 5
                self.effect_speed = 255
                self.color_abs = LightEntry.Color.RED.value

    def get_entries(self):
        return [self.brightness, self.effect, self.effect_speed, self.color, self.color_abs]

    def __repr__(self):
        return f"Light entries:\nbrightness = {self.brightness},\neffect = {self.effect},\neffect_speed = {self.effect_speed},\ncolor = {self.color},\ncolor_abs = {self.color_abs})"


class Logger:
    _logger = None

    @classmethod
    def _initialize(cls):
        if cls._logger is None:
            logging.basicConfig(level=logging.INFO,
                                format='%(asctime)s %(levelname)s %(message)s',
                                handlers=[logging.StreamHandler()])
            cls._logger = logging.getLogger()

    @classmethod
    def debug(cls, caller, message):
        cls._initialize()
        cls._logger.debug(cls.__format(caller, message))

    @classmethod
    def info(cls, caller, message):
        cls._initialize()
        cls._logger.info(cls.__format(caller, message))

    @classmethod
    def warning(cls, caller, message):
        cls._initialize()
        cls._logger.warning(cls.__format(caller, message))

    @classmethod
    def error(cls, caller, message):
        cls._initialize()
        cls._logger.error(cls.__format(caller, message))

    @classmethod
    def critical(cls, caller, message):
        cls._initialize()
        cls._logger.critical(cls.__format(caller, message))

    @classmethod
    def __format(cls, caller, message):
        return f"[{caller}] {message}"