import argparse
import os
from helper_functions import logging, print_colored, get_int, error, validate_date_format, is_date_greater_or_equal
from datetime import datetime

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--leave',
        dest='start_date',
        required=True,
        help="""
        Earliest departure date in format YYYY-MM-DD
        ex: --leave 2025-05-02
        """
    )
    parser.add_argument(
        '--return',
        dest='end_date',
        required=True,
        help="""
        Latest return date in format YYYY-MM-DD
        ex: --leave 2025-05-25
        """
    )
    parser.add_argument(
        '--itinerary',
        dest='itinerary',
        help="""
        Path of the file containing the itinerary
        ex: --itinerary itinerary.json
        """
    )

    args = parser.parse_args()
    for date in args.start_date, args.end_date:
        if not validate_date_format(date, '%Y-%m-%d'):
            parser.error(f'{date} does not respect the correct format "YYYY-MM-DD"')
        
        if not is_date_greater_or_equal(date):
            parser.error(f'Invalid date: {date}. Please enter a date that is today or in the future.')
    if not is_date_greater_or_equal(args.end_date, args.start_date):
        parser.error(f'--return argument({args.end_date}) is earlier than --leave argument({args.start_date})')
        
    if args.itinerary and not os.path.isfile(args.itinerary):
        parser.error(f'File not found: {args.itinerary}')

    return args