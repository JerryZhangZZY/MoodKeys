import json, os

from apps.aqi_indicator import APP_NAME
from apps.aqi_indicator.aqi_fetcher import fetch_aqi
from utils import LightEntry, Logger
from via_lighting_api import ViaLightingAPI

"""Colors"""
COLOR_1 = [0, 120, 126]
COLOR_2 = [5, 154, 101]
COLOR_3 = [133, 189, 75]
COLOR_4 = [255, 221, 51]
COLOR_5 = [255, 186, 51]
COLOR_6 = [254, 150, 51]
COLOR_7 = [228, 73, 51]
COLOR_8 = [202, 0, 53]
COLOR_9 = [151, 0, 104]
COLOR_10 = [120, 0, 63]
COLOR_11 = [78, 0, 22]

api_token = None
location = None
refresh_period_min = None


def __load_config():
    global api_token, location, refresh_period_min
    current_dir = os.path.dirname(__file__)
    config_path = os.path.join(current_dir, 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
        api_token = config.get('API_TOKEN')
        location = config.get('LOCATION', 'here')  # IP location by default
        refresh_period_min = config.get('REFRESH_PERIOD_MIN')  # 5 mins by default


def get_refresh_period():
    __load_config()
    Logger.info(APP_NAME, "Config loaded")
    return refresh_period_min


def get_light_entry():
    aqi = fetch_aqi(api_token, location)
    if aqi:
        """Get AQI successfully"""
        Logger.info(APP_NAME, f"AQI={aqi}")
        light_entry = LightEntry()
        light_entry.effect = 1
        if aqi < 25:
            light_entry.color_abs = COLOR_1
        elif aqi < 50:
            light_entry.color_abs = COLOR_2
        elif aqi < 75:
            light_entry.color_abs = COLOR_3
        elif aqi < 100:
            light_entry.color_abs = COLOR_4
        elif aqi < 125:
            light_entry.color_abs = COLOR_5
        elif aqi < 150:
            light_entry.color_abs = COLOR_6
        elif aqi < 175:
            light_entry.color_abs = COLOR_7
        elif aqi < 200:
            light_entry.color_abs = COLOR_8
        elif aqi < 300:
            light_entry.color_abs = COLOR_9
        else:
            """Insane AQI, apply breathing effect"""
            light_entry.effect = 5
            light_entry.effect_speed = 127
            if aqi < 400:
                light_entry.color_abs = COLOR_10
            else:
                light_entry.color_abs = COLOR_11
        return light_entry
    """Get AQI failed"""
    Logger.warning(APP_NAME, "Get AQI failed")
    return None


if __name__ == '__main__':
    api = ViaLightingAPI(17498, None)
    api.set_color_correction([150, 240, 60])

    """This is a simple light applying method that should be implemented in Manager.py"""
    get_refresh_period()
    light_entry = get_light_entry()
    if not light_entry:
        light_entry = LightEntry(LightEntry.Effect.WARNING)
    brightness, effect, effect_speed, color, color_abs = light_entry.get_entries()
    if effect:
        api.set_effect(effect)
    if effect_speed:
        api.set_effect_speed(effect_speed)
    if color_abs:
        api.set_color_abs(color_abs)
    else:
        if color:
            api.set_color(color)
        if brightness:
            api.set_brightness(brightness)

    """This is a simple light applying method that should be implemented in Manager.py"""
