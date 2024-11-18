import requests


def fetch_aqi(api_token, location):
    url = f"http://api.waqi.info/feed/{location}/?token={api_token}"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        air_quality_data = response.json()
        if air_quality_data['status'] == 'ok':
            return air_quality_data['data']['aqi']
    return None
