import logging
import sys
from datetime import datetime, timedelta, time

RED = 31
GREEN = 32
YELLOW = 33
    
def error(*args):
    for message in args:
        logging.error(message)
    sys.exit(1)
    
def print_colored(color_code: int, *args, **kwargs):
    
    print(*[f"\033[{color_code}m{arg}\033[0m" for arg in args], **kwargs)
    
def get_int(message: str) -> int:
    for _ in range(3):
        try:
            return int(input(message).strip())
        except ValueError:
            print_colored(YELLOW, 'Write only numbers and press ENTER')
    else:
        error('Failed to get int')
        
def get_hour(message: str) -> str:
    for _ in range(3):
        try:
            hour = input(message).strip()
            return None if not hour else datetime.strptime(hour, '%H:%M').strftime('%H:%M:%S')
        except ValueError:
            print_colored(YELLOW, 'Invalid time format! Please enter time in HH:MM format (e.g., 08:00).')
    else:
        error('Failed to get valid hour')

def validate_date_format(date: str, format: str) -> bool:
    try:
        datetime.strptime(date, format)
        return True
    except ValueError:
        return False

def is_date_greater_or_equal(target_date: str, reference_date: str | None = None) -> bool:
    reference = datetime.today().date() if reference_date is None else datetime.strptime(reference_date, "%Y-%m-%d").date()
    target = datetime.strptime(target_date, "%Y-%m-%d").date()

    return target >= reference
        
def yes_no_question(message: str) -> bool:
    for _ in range(3):
        answer = input(message).strip()
        if answer in ['y', 'ye', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        else:
            print_colored(YELLOW, 'Answer only with [yes/no]')
    else:
        error(f'Failed to get [y/n] answer to question: {message}')
        
def generate_date_range(start_date: str, end_date: str, input_format: str = '%Y-%m-%d', output_format: str = '%Y-%m-%d', step: timedelta = timedelta(days=1)) -> iter:
    date = datetime.strptime(start_date, input_format)
    end_date = datetime.strptime(end_date, input_format)
    while date <= end_date:
        yield datetime.strftime(date, output_format)
        date = date + step
    
def validate_itinerary_stay_limits(start_date: str, end_date: str, max_duration: str, format: str = '%Y-%m-%d') -> None:
    if datetime.strptime(start_date, format) + timedelta(max_duration) > datetime.strptime(end_date, format):
        error(f'The max holiday duration exceeds the interval of days between the specified earliest leave date and latest return date')
        
def calculate_total_duration(itinerary: list[dict[str, str | int | bool | None]] , key: str) -> timedelta:
    return timedelta(days=sum([leg[key] or 1 for leg in itinerary]))

def get_months_from_dates(dates: list, func: callable = None) -> list:
    if not func:
        func = lambda x: x.split('-')[1]
    return list({func(date) for date in dates})

def convert_string_to_time(date: str, format: str = '%Y-%m-%dT%H:%M:%S') -> time:
    return datetime.strptime(date, format).time()
    
def check_time_in_interval(check_time: time, start_time: time = time(0, 0), end_time: time = time(23, 59)) -> bool:
    return start_time <= check_time <= end_time

def increase_date_by_days(date: str, days: int, format: str = '%Y-%m-%d') -> str:
    return (datetime.strptime(date, format) + timedelta(days=days)).strftime(format)