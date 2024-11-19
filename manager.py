import json, os, sys, importlib.util, schedule, time, threading

from via_lighting_api import ViaLightingAPI

from utils import Logger, LightEntry
from typing import Optional

TAG = 'Manager'

vid = None
pid = None
true_white = None

api: Optional[ViaLightingAPI] = None


def __load_config():
    global vid, pid, true_white
    with open('config.json', 'r') as f:
        config = json.load(f)
        vid = config.get('VENDOR_ID')
        pid = config.get('PRODUCT_ID', None)
        true_white = config.get('COLOR_CORRECTION_TRUE_WHITE', None)


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


def load_selected_app(selected_app_path):
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


def refresh_lighting(app_module):
    Logger.info(TAG, 'Refreshing lighting')
    if hasattr(app_module, 'get_light_entry'):
        apply_light_entry(app_module.get_light_entry())


def apply_light_entry(light_entry):
    global api
    if not light_entry:
        """Apply warning light effect"""
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
    max_retries = 5
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
            time.sleep(1)

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

    """User selection"""
    selected_index = input("Please enter the number of the application you want to load: ")

    """Run selected app"""
    if selected_index.isdigit() and 1 <= int(selected_index) <= len(app_list):
        selected_app_name = app_list[int(selected_index) - 1]
        app_path = apps[selected_app_name]
        app_module = load_selected_app(app_path)
        if app_module:
            Logger.info(TAG, f"Starting app: {selected_app_name}")
            if hasattr(app_module, 'get_refresh_period'):
                period = int(app_module.get_refresh_period())
                schedule.every(period).minutes.do(refresh_lighting, app_module)
                Logger.info(TAG, f"Refresh period set to {period} mins")
                schedule_thread = threading.Thread(target=run_app_schedule)
                """Run refresh immediately"""
                refresh_lighting(app_module)
                schedule_thread.start()
            else:
                Logger.error(TAG, f"No 'get_refresh_period()' function found in {selected_app_name}.")
    else:
        print("Invalid application number.")
