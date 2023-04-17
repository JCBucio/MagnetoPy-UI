import pandas as pd
import numpy as np

def columns_exist(df, columns):
    # Check if columns are in dataframe
    for column in columns:
        if column not in df.columns:
            return False
    return True

def format_time(val):
    try:
        if len(str(val)) != 6 or str(val).isdigit() == False:
            if '/' in str(val):
                time = str(val).split('/')
            elif '-' in str(val):
                time = str(val).split('-')
            elif ':' in str(val):
                time = str(val).split(':')
            elif ' ' in str(val):
                time = str(val).split(' ')
            elif '.' in str(val):
                time = str(val).split('.')
            else:
                return int(val)

            if len(time) == 3:
                h = time[0]
                m = time[1]
                s = time[2]
                if len(h) == 2 and len(m) == 2 and len(s) == 2:
                    return int(h + m + s)
                else:
                    raise Exception('The time format is not correct')
            else:
                raise Exception('Check that your date format has hours, minutes and seconds')
        else:
            return int(val)
    except:
        raise Exception('Check that your time format is correct')