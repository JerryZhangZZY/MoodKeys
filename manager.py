import json, os, sys, importlib.util, schedule, time, threading

from via_lighting_api import ViaLightingAPI

from utils import Logger, LightEntry

NAME = 'Manager'

vid = None
pid = None
true_white = None


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
                Logger.error(NAME, f'Error loading {app_name}: {e}')

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
        Logger.error(NAME, f'Error loading {selected_app_path}: {e}')
        return None


def refresh_lighting(api, app_module):
    Logger.info(NAME, 'Refreshing lighting')
    if hasattr(app_module, 'get_light_entry'):
        apply_light_entry(api, app_module.get_light_entry())


def apply_light_entry(api, light_entry):
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
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    __load_config()
    Logger.info(NAME, "Config loaded")
    api = ViaLightingAPI(vid, pid)
    Logger.info(NAME, "Keyboard connected")
    if true_white:
        api.set_color_correction(true_white)
        Logger.info(NAME, "Color correction enabled")

    """Apply standby light effect"""
    apply_light_entry(api, LightEntry(LightEntry.Effect.STANDBY))

    apps = list_apps()

    print("Available applications:")
    app_list = list(apps.keys())
    for index, app_name in enumerate(app_list):
        print(f"{index + 1}. {app_name}")

    selected_index = input("Please enter the number of the application you want to load: ")

    if selected_index.isdigit() and 1 <= int(selected_index) <= len(app_list):
        selected_app_name = app_list[int(selected_index) - 1]
        app_path = apps[selected_app_name]
        app_module = load_selected_app(app_path)

        if app_module:
            Logger.info(NAME, f"Starting app: {selected_app_name}")
            if hasattr(app_module, 'get_refresh_period'):
                period = int(app_module.get_refresh_period())
                schedule.every(period).minutes.do(refresh_lighting, api, app_module)
                Logger.info(NAME, f"Refresh period set to {period} mins")
                schedule_thread = threading.Thread(target=run_app_schedule)
                """Run refresh immediately"""
                refresh_lighting(api, app_module)
                schedule_thread.start()
            else:
                Logger.error(NAME, f"No 'get_refresh_period()' function found in {selected_app_name}.")
    else:
        print("Invalid application number.")
