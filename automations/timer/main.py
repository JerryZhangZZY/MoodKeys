import json
import os
from datetime import datetime

from automations.timer import AUTOMATION_NAME
from automations.timer.duty_fetcher import workday
from utils import LightEntry, Logger

config_loaded = False

start_time = None
end_time = None
workday_mode = None

light_entry_off = LightEntry()
light_entry_off.effect = 0


def __load_config():
    global start_time, end_time, workday_mode
    current_dir = os.path.dirname(__file__)
    config_path = os.path.join(current_dir, 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
        start_time = datetime.strptime(config.get('START_TIME', '08:00'), '%H:%M').time()
        end_time = datetime.strptime(config.get('END_TIME', '20:00'), '%H:%M').time()
        workday_mode = bool(config.get('WORKDAY_MODE', False))


def get_light_entry():
    global config_loaded
    if not config_loaded:
        __load_config()
        config_loaded = True
        Logger.info(AUTOMATION_NAME, "Config loaded")

    now = datetime.now()

    if (not workday_mode) or (workday_mode and workday(now)):
        if start_time <= now.time() <= end_time:
            Logger.info(AUTOMATION_NAME, "Now is on duty")
            return None

    Logger.info(AUTOMATION_NAME, "Now is off duty")
    return light_entry_off
