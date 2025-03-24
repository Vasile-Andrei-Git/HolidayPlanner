import requests
import json
import logging
import os
import sys
from datetime import datetime, timedelta
import re
from helper_functions import logging, print_colored, get_int, error, check_time_in_interval, convert_string_to_time
import time

cwd = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RED = 31
GREEN = 32
YELLOW = 33

class CacheManager:
    cache_expirations_by_subdir = {
        'calendar': timedelta(days=3),
        'location_ids': timedelta(days=30),
        'flights': timedelta(days=7),
        'debug': timedelta(days=100)
    }
    
    @classmethod
    def check_cache_valid(cls, path: str) -> bool:
        dir_name = os.path.basename(os.path.dirname(path))
        return datetime.now() - datetime.fromtimestamp(os.path.getmtime(path)) < cls.cache_expirations_by_subdir[dir_name]
    
    @classmethod
    def get_cache(cls, path: str) -> dict[str, object] | None:
        if os.path.exists(path) and cls.check_cache_valid(path):
            with open(path) as f:
                return json.load(f)
        return
    
    @classmethod
    def store_cache(cls, path: str, data: dict[str, object]) -> None:
        if not os.path.exists(path) or not cls.check_cache_valid(path):
            os.makedirs(os.path.dirname(path), mode=0o750, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)

class FlightsApi:
    def __init__(self):
        try:
            with open(f'{cwd}/credentials.json') as f:
                data = json.load(f)
        except FileNotFoundError:
            error(f'Please create credentials.json in this folder: {cwd}')
            
        try:
            self.url: str = data['url']
            self.credentials = {'x-rapidapi-key': data['x-rapidapi-key'], 'x-rapidapi-host': data['x-rapidapi-host']}
        except KeyError:
            error('One of the required fields is missing in credentials.json: url, x-rapidapi-key, x-rapidapi-host')
                
    def _make_request(self, endpoint: str, params: dict[str, object]) -> dict[str, object]:
        try:
            response = requests.get(self.url + endpoint, headers=self.credentials, params=params)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error(f'HTTP error occurred: {e}', f'Please make sure your credentials are correct and you have not exceeded the monthly requests quota')
        except requests.exceptions.RequestException as e:
            error(f'An error occurred: {e}')
        return response.json()
    
    def send_api_request(self, endpoint: str, params: dict[str, object], cache_path: str, fallback_endpoint: str = None) -> dict[str, object]:
        if cache := CacheManager.get_cache(cache_path):
            return cache
        data = self._make_request(endpoint, params=params)

        if fallback_endpoint:
            soft_retry_count = 0
            hard_retry_count = 0
            sessionId = data['data']['context']['sessionId']
            print(params, endpoint, cache_path, fallback_endpoint, '----', sessionId, data['data']['context']['status'])
            while data['data']['context']['status'] != 'complete':
                time.sleep(2)
                data = self._make_request(fallback_endpoint, params={'sessionId': sessionId, 'stops': params['stops']})
                soft_retry_count += 1
                if hard_retry_count > 2:
                    return {}
                if soft_retry_count > 5:
                    hard_retry_count += 1
                    soft_retry_count = 0
                    data = self._make_request(endpoint, params=params)
                    sessionId = data['data']['context']['sessionId']
                print(sessionId, data['data']['context']['status'], soft_retry_count, hard_retry_count)
                    
            if data['data']['context']['status'] != 'complete':
                CacheManager.store_cache(re.sub(r'flights', 'debug', cache_path), data)
                return {}
        CacheManager.store_cache(cache_path, data)
        return data
    
    def search_airports_in_location(self, location: str) -> str | None:
        return self.send_api_request(
            endpoint='/flights/auto-complete',
            params={'query': location.lower()},
            cache_path=os.path.join(cwd, f'caches/location_ids/{location.lower()}.json')
        )
        
    def get_flight_dates_by_route(self, from_entity: str, to_entity: str, month: int, year: int = datetime.now().year):
        params = {
            "fromEntityId":from_entity,
            "toEntityId":to_entity,
            "yearMonth":f"{year}-{month:02}"
        }
        data = self.send_api_request(
            endpoint='/flights/price-calendar-web',
            params=params,
            cache_path=os.path.join(cwd, f'caches/calendar/{"_".join(map(lambda x: str(x).lower(), params.values()))}.json')
        ).get('data', [])
        
        tracerefs = set()
        dates = set()
        for grids in data['PriceGrids']['Grid']:
            for grid in grids:
                if 'Direct' in grid:
                    tracerefs.add(*grid['Direct']['TraceRefs'])
                
        for traceref in tracerefs:
            
            date = data['Traces'][traceref].split('*')[4]
            dates.add(datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d"))
            
        return sorted(list(dates))
    
    def get_flights_for_date(self, from_entity: str, to_entity: str, date: str, adults: int = 1, stops: str = 'direct', min_departure_hour: str = '00:00:00', max_departure_hour: str = '23:59:59') -> list[dict[str, int | str]]:
        params = {"fromEntityId":from_entity,"toEntityId":to_entity,"departDate":date,"adults":adults,"stops":stops}
        flights = self.send_api_request(
            endpoint='/flights/search-one-way',
            params=params,
            cache_path=os.path.join(cwd, f'caches/flights/{"_".join(map(lambda x: str(x).lower(), params.values()))}.json'),
            fallback_endpoint='/flights/search-incomplete'
        ).get('data', {}).get('itineraries', [])
        
        dates = []
        for flight in flights:
            flight_departure = convert_string_to_time(flight["legs"][0]["departure"])
            condition = check_time_in_interval(
                check_time=flight_departure,
                start_time=convert_string_to_time(min_departure_hour, format='%H:%M:%S'),
                end_time=convert_string_to_time(max_departure_hour, format='%H:%M:%S')
            )
            if condition:
                dates.append(
                    {
                        "price": flight["price"]["raw"],
                        "departure": flight["legs"][0]["departure"],
                        "arrival": flight["legs"][-1]["arrival"],
                    }
                )
        return dates




# all_flights = [
#     {
#         'from_entity': '',
#         'to_entity': '',
#         'flights': [
#             ('date_time_leave1', 'date_time_arrival1', 'price1'),
#             ('date_time_leave2', 'date_time_arrival2', 'price2'),
#         ]
#     }
# ]

