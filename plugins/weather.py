import requests
 
from cloudbot import hook
from cloudbot.util import web
from cloudbot.util.web import try_shorten
 
# Settings
source = 'wunderground' # 'darksky' or 'wunderground'

class APIError(Exception):
    pass
 
# Define some constants
google_base = 'https://maps.googleapis.com/maps/api/'
geocode_api = google_base + 'geocode/json'

api_sources = { 
    'darksky': 'https://api.darksky.net/forecast/{}/{}',
    'wunderground': 'http://api.wunderground.com/api/{}/forecast/geolookup/conditions/q/{}.json'
}

weather_base = api_sources[source]
 
# Wunderground specific:
# Change this to a ccTLD code (eg. uk, nz) to make results more targeted towards that specific country.
# <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
bias = None
 
 
def check_status(status):
    """
    A little helper function that checks an API error code and returns a nice message.
    Returns None if no errors found
    """
    if status == 'REQUEST_DENIED':
        return 'The geocode API is off in the Google Developers Console.'
    elif status == 'ZERO_RESULTS':
        return 'No results found.'
    elif status == 'OVER_QUERY_LIMIT':
        return 'The geocode API quota has run out.'
    elif status == 'UNKNOWN_ERROR':
        return 'Unknown Error.'
    elif status == 'INVALID_REQUEST':
        return 'Invalid Request.'
    elif status == 'OK':
        return None
 
def to_c(ftemp):
    return (ftemp - 32) * (5/9)

def find_location(location):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :return: dict
    """
    params = {"address": location, "key": dev_key}
    if bias:
        params['region'] = bias
 
    json = requests.get(geocode_api, params=params).json()
 
    error = check_status(json['status'])
    if error:
        raise APIError(error)
 
    return json['results'][0]['geometry']['location']

@hook.on_start
def on_start(bot):
    """ Loads API keys """
    global dev_key, weatherapi_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    weatherapi_key = bot.config.get("api_keys", {}).get(source, None) 
 
@hook.command("weather", "we")
def weather(text, reply):
    """weather <location> -- Gets weather data for <location>."""
    if not weatherapi_key:
        return 'No API key found for {}'.format(source)
    if not dev_key:
        return "This command requires a Google Developers Console API key."
 
    # use find_location to get location data from the user input
    try:
        location_data = find_location(text)
    except APIError as e:
        return e
 
    formatted_location = "{lat},{lng}".format(**location_data)
 
    url = weather_base.format(weatherapi_key, formatted_location)
    
    response = requests.get(url).json()
    nice_url = 'https://darksky.net/forecast/{}'.format(formatted_location)
 
    if source == 'darksky':
        weather_data = {
            "current": '{} {}F/{}C'.format(
                response['currently']['summary'], 
                int(round(response['currently']['temperature'])),
                int(round(to_c(response['currently']['temperature'])))
                ),
            "today": response['daily']['data'][0]['summary'],
            "high": '{}F/{}C'.format(
                int(round(response['daily']['data'][0]['temperatureMax'])),
                int(round(to_c(response['daily']['data'][0]['temperatureMax'])))
                ),
            "low": '{}F/{}C'.format(
                int(round(response['daily']['data'][0]['temperatureMin'])),
                int(round(to_c(response['daily']['data'][0]['temperatureMin'])))
                )
        }
        output = '({}) \x02Current:\x02 {}. {} [ High: {} Low: {} || {} ]'.format(
            text,weather_data['current'],weather_data['today'], 
            weather_data['high'], weather_data['low'], 
            web.shorten(nice_url)
            )

    if source == 'wunderground':
        if response['response'].get('error'):
            return "{}".format(response['response']['error']['description'])
     
        #forecast_today = response["forecast"]["simpleforecast"]["forecastday"][0]
        #forecast_tomorrow = response["forecast"]["simpleforecast"]["forecastday"][1]
     
        # put all the stuff we want to use in a dictionary for easy formatting of the output
        weather_data = {
            "place": response['current_observation']['display_location']['full'],
            "conditions": response['current_observation']['weather'],
            "temp_f": response['current_observation']['temp_f'],
            "temp_c": response['current_observation']['temp_c']
        }
        if "?query=," in response["current_observation"]['ob_url']:
            weather_data['url'] = web.shorten(response["current_observation"]['forecast_url'])
        else:
            weather_data['url'] = web.shorten(response["current_observation"]['ob_url'])
        output = "{place} - \x02Current:\x02 {conditions}, {temp_f}F/{temp_c}C".format(**weather_data)

    reply(output)