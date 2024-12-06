import importlib.util
import json
import os
import sys
import threading
import time
from typing import Optional

import schedule
from via_lighting_api import ViaLightingAPI

from utils import Logger, LightEntry

TAG = 'Manager'

vid = None
pid = None
true_white = None
reconnect_timeout = 5

api: Optional[ViaLightingAPI] = None


def __load_config():
    global vid, pid, true_white, reconnect_timeout
    with open('config.json', 'r') as f:
        config = json.load(f)
        vid = config.get('VENDOR_ID')
        pid = config.get('PRODUCT_ID', None)
        true_white = config.get('COLOR_CORRECTION_TRUE_WHITE', None)
        reconnect_timeout = int(config.get('RECONNECT_TIMEOUT', 5))


def list_apps():
    apps = {}
    apps_dir = os.path.join(os.path.dirname(__file__), 'apps')

    for app_name in os.listdir(apps_dir):
        app_path = os.path.join(apps_dir, app_name)

        if os.path.isdir(app_path) and os.path.isfile(os.path.join(app_path, '__init__.py')):
            try:
                init_file_path = os.path.join(app_path, '__init__.py')
                with open(init_file_path, 'r') as f:
                    for line in f:
                        if line.startswith('APP_NAME'):
                            app_name_value = line.split('=')[1].strip().strip('\'')
                            apps[app_name_value] = app_path
                            break

            except Exception as e:
                Logger.error(TAG, f'Error loading {app_name}: {e}')

    return apps


def load_selected(selected_app_path):
    try:
        main_module_path = os.path.join(selected_app_path, 'main.py')
        spec = importlib.util.spec_from_file_location("main", main_module_path)
        main_module = importlib.util.module_from_spec(spec)
        sys.modules["main"] = main_module
        spec.loader.exec_module(main_module)
        return main_module
    except Exception as e:
        Logger.error(TAG, f'Error loading {selected_app_path}: {e}')
        return None


def list_automations():
    automations = {}
    automations_dir = os.path.join(os.path.dirname(__file__), 'automations')

    for automation_name in os.listdir(automations_dir):
        automation_path = os.path.join(automations_dir, automation_name)

        if os.path.isdir(automation_path) and os.path.isfile(os.path.join(automation_path, '__init__.py')):
            try:
                init_file_path = os.path.join(automation_path, '__init__.py')
                with open(init_file_path, 'r') as f:
                    for line in f:
                        if line.startswith('AUTOMATION_NAME'):
                            automation_name_value = line.split('=')[1].strip().strip('\'')
                            automations[automation_name_value] = automation_path
                            break
            except Exception as e:
                Logger.error(TAG, f'Error loading {automation_name}: {e}')

    return automations


def refresh_lighting(app_module, automation_module=None):
    Logger.info(TAG, 'Refresh lighting ..........')

    if not hasattr(app_module, 'get_light_entry'):
        Logger.error(TAG, "No 'get_light_entry()' function found in app")
        exit(1)

    if automation_module:
        if not hasattr(automation_module, 'get_light_entry'):
            Logger.error(TAG, "No 'get_light_entry()' function found in automation")
            exit(1)
        automation_light_entry = automation_module.get_light_entry()
        if automation_light_entry and automation_light_entry.effect == 0:
            final_light_entry = automation_light_entry
        else:
            app_light_entry = app_module.get_light_entry()
            final_light_entry = merge_light_entries(app_light_entry, automation_light_entry)
    else:
        final_light_entry = app_module.get_light_entry()

    apply_light_entry(final_light_entry)


def merge_light_entries(app_light_entry, automation_light_entry):
    if automation_light_entry:
        if automation_light_entry.brightness is not None:
            if app_light_entry.color_abs is not None:
                new_color_abs = [int(c * automation_light_entry.brightness / 255) for c in app_light_entry.color_abs]
                app_light_entry.color_abs = new_color_abs
            elif app_light_entry.brightness is not None:
                new_brightness = int(app_light_entry.brightness * automation_light_entry.brightness / 255)
                app_light_entry.brightness = new_brightness
    return app_light_entry


def apply_light_entry(light_entry):
    Logger.info(TAG, 'Applying light entry')
    global api
    if not light_entry:
        """Apply warning light effect"""
        light_entry = LightEntry(LightEntry.Effect.WARNING)
    brightness, effect, effect_speed, color, color_abs = light_entry.get_entries()
    if effect is not None:
        api.set_effect(effect)
        if effect == 0:
            return
    if effect_speed is not None:
        api.set_effect_speed(effect_speed)
    if color_abs:
        api.set_color_abs(color_abs)
    else:
        if color:
            api.set_color(color)
        if brightness:
            api.set_brightness(brightness)


def run_app_schedule():
    while True:
        try:
            schedule.run_pending()
        except OSError:
            Logger.warning(TAG, "Connection lost, trying to reconnect")
            init()
        time.sleep(1)


def init():
    global api
    retry_interval = 1
    max_retries = int(reconnect_timeout / retry_interval)
    for attempt in range(max_retries):
        try:
            api = ViaLightingAPI(vid, pid)
            Logger.info(TAG, "Keyboard connected")
            if true_white:
                api.set_color_correction(true_white)
                Logger.info(TAG, "Color correction enabled")
            return
        except Exception as e:
            Logger.warning(TAG, f"Failed to connect: {e} Retrying {attempt + 1}/{max_retries}...")
            time.sleep(retry_interval)

    Logger.error(TAG, "Max retries reached. Could not connect to keyboard.")
    sys.exit(1)


if __name__ == '__main__':
    """Load config"""
    __load_config()
    Logger.info(TAG, "Config loaded")

    """Init api"""
    init()

    """Apply standby light effect"""
    apply_light_entry(LightEntry(LightEntry.Effect.STANDBY))

    """Show apps"""
    apps = list_apps()
    print("Available Apps:")
    app_list = list(apps.keys())
    for index, app_name in enumerate(app_list):
        print(f"{index + 1}. {app_name}")
    """User app selection"""
    selected_app_index = input("Please select the application you want to load: ")

    """Show automations"""
    automations = list_automations()
    print("Available Automations:")
    automations_list = list(automations.keys())
    for index, automation_name in enumerate(automations_list):
        print(f"{index + 1}. {automation_name}")
    """User automation selection"""
    selected_automation_index = input("Please select the automation you want to load, type 0 to disable automation: ")

    """Run selected app"""
    if selected_app_index.isdigit() and 1 <= int(selected_app_index) <= len(app_list):
        selected_app_name = app_list[int(selected_app_index) - 1]
        app_path = apps[selected_app_name]
        app_module = load_selected(app_path)
        if app_module:
            Logger.info(TAG, f"App selected: {selected_app_name}")
            if hasattr(app_module, 'get_refresh_period'):
                automation_module = None
                if selected_automation_index.isdigit() and 1 <= int(selected_automation_index) <= len(automations_list):
                    selected_automation_name = automations_list[int(selected_automation_index) - 1]
                    automation_path = automations[selected_automation_name]
                    automation_module = load_selected(automation_path)
                    if automation_module:
                        Logger.info(TAG, f"Automation selected: {selected_automation_name}")
                else:
                    Logger.info(TAG, "Automation disabled")
                period = int(app_module.get_refresh_period())
                schedule.every(period).minutes.do(refresh_lighting, app_module, automation_module)
                Logger.info(TAG, f"Refresh period set to {period} mins")
                schedule_thread = threading.Thread(target=run_app_schedule)
                """Run refresh immediately"""
                refresh_lighting(app_module, automation_module)
                schedule_thread.start()
            else:
                Logger.error(TAG, f"No 'get_refresh_period()' function found in {selected_app_name}")
    else:
        print("Invalid app number.")
