from flights_api import FlightsApi
from arguments import parse_arguments
from helper_functions import print_colored, get_int, error, yes_no_question, get_hour, generate_date_range, validate_itinerary_stay_limits, calculate_total_duration, get_months_from_dates, convert_string_to_time, increase_date_by_days
import os
import json
from datetime import datetime, timedelta, time
import sys
import copy

def main():
    args = parse_arguments()
    if not args.itinerary:
        itinerary = create_itinerary()
        with open('itinerary.json', 'w') as f:
            json.dump(itinerary, f, indent=4)
    else:
        with open(args.itinerary) as f:
            itinerary = json.load(f)
    validate_itinerary_stay_limits(
        start_date=args.start_date,
        end_date=args.end_date,
        max_duration=sum([leg['max_stay_duration'] or 0 for leg in itinerary])
    )
    mutate_itinerary_with_possible_flight_dates(itinerary, args.start_date, args.end_date)
    with open('itinerary_semi.json', 'w') as f:
        pass
    for leg in itinerary:
        available_flight_dates = []
        for month in leg['months']:
            available_flight_dates.extend(
                FlightsApi().get_flight_dates_by_route(
                    from_entity=leg['fromEntityId'],
                    to_entity=leg['toEntityId'],
                    month=month
                )
            )
        leg['flights'] = {flight: [] for flight in leg['flights'] if flight in available_flight_dates}
        
    with open('itinerary_semi.json', 'w') as f:
        json.dump(itinerary, f, indent=4)

    for index in range(len(itinerary) - 1):
        if index == 0:
            legs = list(map(lambda x: [x], itinerary[index]['flights']))
        else:
            legs = possible_itineraries
        possible_itineraries = extend_itinerary_with_leg(legs, itinerary[index + 1]['flights'], itinerary[index]['min_stay_duration'], itinerary[index]['max_stay_duration'])
        
    complete_itineraries = []
    filtered_possible_itineraries = copy.deepcopy(possible_itineraries)
    for possible_itinerary in possible_itineraries:
        if possible_itinerary not in filtered_possible_itineraries: continue
        complete_itinerary = {'total': None, 'legs': []}
        for index, date in enumerate(possible_itinerary):
            flights = FlightsApi().get_flights_for_date(
                from_entity=itinerary[index]['fromEntityId'],
                to_entity=itinerary[index]['toEntityId'],
                date=date,
                min_departure_hour=itinerary[index]['min_departure_hour'],
                max_departure_hour=itinerary[index]['max_departure_hour']
            )
            try: 
                flight = get_cheapest_flight(flights)
            except IndexError:
                filtered_possible_itineraries = [filtered_possible_itinerary for filtered_possible_itinerary in filtered_possible_itineraries if filtered_possible_itinerary[index] != date]
                break
            complete_itinerary['legs'].append({
                'fromEntityId': itinerary[index]['fromEntityId'],
                'toEntityId': itinerary[index]['toEntityId'],
                'date': date,
                'price': flight['price'],
                'departure': flight['departure'],
                'arrival': flight['arrival']
            })
        else:
            complete_itinerary['total'] = int(sum(map(lambda leg: leg['price'], complete_itinerary['legs'])))
            complete_itineraries.append(complete_itinerary)
    
    complete_itineraries.sort(key=lambda itinerary: itinerary['total'])
    with open('final_result.json', 'w') as w:
        json.dump(complete_itineraries, w, indent=4)
            
            

            
def get_airport(location: str) -> str:
    location = location.strip()
    if not location:
        return
    airports = FlightsApi().search_airports_in_location(location)
    if not airports.get('data', []):
            print_colored(YELLOW, f'Did not find any available Airports for your desired location: {location}',
            'Please make sure to input only valid ones!',
            sep='\n')
            return
    print(f'Available Airports for your desired location: {location}')
    for index, entity in enumerate(airports['data']):
        print(f'{index:<2}: {entity["presentation"]["suggestionTitle"]}')
        
    for _ in range(3):
        choice = get_int('Please enter the number for the desired location: ')
        try:
            return airports['data'][choice]['navigation']['relevantFlightParams']['skyId']
        except IndexError:
            print_colored(YELLOW, 'Invalid number, please enter a valid number from the choices list')
    else:
        error('Did not get a valid choice for location')
        
def get_min_max_departure_hours(hour_format: str = '%H:%M:%S') -> tuple[str, str]:
    for _ in range(3):
        min_departure_hour = get_hour("Optional - Earliest departure hour (ex: 13:00, or leave blank if none): ") or '00:00:00'
        max_departure_hour = get_hour("Optional - Latest departure hour (ex: 15:00 leave blank if none): ") or '23:59:59'
        if convert_string_to_time(min_departure_hour, format=hour_format) >= convert_string_to_time(max_departure_hour, format=hour_format):
            print_colored(YELLOW, 'Earliest Departure can not be after or same time as Latest Departure')
        else:
            break
    else:
        error('Could not get valid hours')
    return (min_departure_hour, max_departure_hour)
    
def get_min_max_stay_duration() -> tuple[int, int]:
    for _ in range(3):
        min_stay_duration = get_int("Minimum stay duration at destination (in nights): ")
        max_stay_duration = get_int("Maximum stay duration at destination (in nights): ")
        if min_stay_duration > max_stay_duration:
            print_colored(YELLOW, 'Minimum stay duration can not be longer than Maxim stay duration')
        else:
            return (min_stay_duration, max_stay_duration)
    else:
        error('Could not get valid min/max stay durations')
    
def create_itinerary() -> list[dict[str, str | int | bool | None]]:
    itinerary = []
    while True:
        print('Enter trip details:')
        fromEntityId = get_airport(input("From (Departure Location): "))
        toEntityId = get_airport(input("To (Destination): "))
        min_departure_hour, max_departure_hour = get_min_max_departure_hours() 
        final_destination = yes_no_question("Is this your final destination? (yes/no): ")
        if final_destination:
            min_stay_duration, max_stay_duration = None, None
        else:
            min_stay_duration, max_stay_duration = get_min_max_stay_duration()
            
        leg = {
            "fromEntityId": fromEntityId,
            "toEntityId": toEntityId,
            "final_destination": final_destination,
            "min_stay_duration": min_stay_duration,
            "max_stay_duration": max_stay_duration,
            "min_departure_hour": min_departure_hour,
            "max_departure_hour": max_departure_hour
        }
        itinerary.append(leg)
        if final_destination:
            break
    return itinerary
    
    
def mutate_itinerary_with_possible_flight_dates(itinerary: list[dict[str, str | int | bool | None]], start_date: str, end_date: str, format: str = '%Y-%m-%d')-> None:
    min_date = datetime.strptime(start_date, format)
    max_date = datetime.strptime(end_date, format)

    min_duration = calculate_total_duration(itinerary, 'min_stay_duration')

    for index, leg in enumerate(itinerary):
        if index == 0:
            dates = generate_date_range(start_date, (max_date - min_duration).strftime('%Y-%m-%d'))
        elif not leg['min_stay_duration']:
            dates = generate_date_range((min_date + min_duration).strftime('%Y-%m-%d'), end_date)
        else:
            previous_legs_min_duration = calculate_total_duration(itinerary[:index], 'min_stay_duration')
            future_legs_max_duration = calculate_total_duration(itinerary[index + 1:], 'max_stay_duration')
            dates = generate_date_range((min_date + previous_legs_min_duration).strftime('%Y-%m-%d'), (max_date - future_legs_max_duration).strftime('%Y-%m-%d'))
        dates = list(dates)
        leg.update({'months': get_months_from_dates(dates)})
        leg.update({'flights': {date: [] for date in dates} })
        
def extend_itinerary_with_leg(legs: list[list[str]], availabe_return_dates: list[str], min_stay_duration: int, max_stay_duration: int) -> list[list[str]]:
    extended_legs = []
    for leg in legs:
        start_date = leg[-1]
        for duration in range(min_stay_duration, max_stay_duration + 1):
            if (return_date := increase_date_by_days(start_date, duration)) in availabe_return_dates:
                extended_legs.append(leg + [return_date])
    return extended_legs

def get_cheapest_flight(flights: list[dict]) -> dict[str, str | float]:
    return sorted(flights, key=lambda flight: flight['price'])[0]
    
    
if __name__ == '__main__':
    cwd = os.path.dirname(os.path.abspath(__file__))
    RED = 31
    GREEN = 32
    YELLOW = 33
    main()
