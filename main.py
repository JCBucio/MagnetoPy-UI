import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import time
import requests


from utils import *

st.set_page_config(page_title='MagnetoPy', page_icon=':earth_americas:', layout="wide")

'''
# MagnetoPy
_Created by [Juan Carlos Bucio Tejeda](https://jcbucio.github.io/about/)_

Python web app that calculates diurnal variation and requests total magnetic field intensity from an IGRF API using field data and base stations.
- Source code: [GitHub](https://github.com/JCBucio/MagnetoPy-UI)
'''
st.write('---')

stations_columns = []
base_stations_columns = []



with st.container():

    '''
    ### Upload data
    In this section you can upload the field stations and base stations files. This files are needed
    in order to made the calculations. The files should be in CSV format.
    '''

    upload_col1, upload_col2 = st.columns(2)

    uploaded_stations_file = upload_col1.file_uploader("Choose a field stations file", type="csv", key="uploaded_stations_file")

    if uploaded_stations_file is not None:
        # Can be used wherever a "file-like" object is accepted:
        stations_dataframe = pd.read_csv(uploaded_stations_file)
        stations_columns = stations_dataframe.columns.tolist() + [None]
        upload_col1.write(stations_dataframe)

    uploaded_base_stations_file = upload_col2.file_uploader("Choose a base stations file", type="csv", key="uploaded_base_stations_file")

    if uploaded_base_stations_file is not None:
        # Can be used wherever a "file-like" object is accepted:
        base_stations_dataframe = pd.read_csv(uploaded_base_stations_file)
        base_stations_columns = base_stations_dataframe.columns.tolist() + [None]
        upload_col2.write(base_stations_dataframe)


with st.container():

    '''
    ### Station data
    In this section you can select the columns of the field stations file that you want to use. All the columns are required,
    except for the elevation column, if your data does not have it, you can set a default value for the IGRF correction in the
    IGRF configuration section.
    '''

    stations_dropdowns_col1, stations_dropdowns_col2 = st.columns(2)

    stations_date = stations_dropdowns_col1.selectbox(
        'Date column',
        stations_columns,
        key="stations_date"
    )

    stations_magfield = stations_dropdowns_col1.selectbox(
        'Magnetic field column',
        # The options should be the columns of the uploaded file
        stations_columns,
        key="stations_magfield"
    )

    stations_latitude = stations_dropdowns_col1.selectbox(
        'Latitude column in geographic coordinates',
        stations_columns,
        key="stations_latitude"
    )

    stations_time = stations_dropdowns_col2.selectbox(
        'Time column',
        stations_columns,
        key="stations_time"
    )

    stations_elevation = stations_dropdowns_col2.selectbox(
        'Elevation column in meters (set to None if your data does not have it)',
        stations_columns,
        key="stations_elevation"
    )

    stations_longitude = stations_dropdowns_col2.selectbox(
        'Longitude column in geographic coordinates',
        stations_columns,
        key="stations_longitude"
    )


with st.container():

    '''
    ### Base station data
    In this section you can select the columns of the base stations file that you want to use. All the columns are required.
    '''

    base_stations_dropdowns_col1, base_stations_dropdowns_col2 = st.columns(2)

    base_stations_date = base_stations_dropdowns_col1.selectbox(
        'Date column',
        base_stations_columns,
        key="base_stations_date"
    )

    base_stations_magfield = base_stations_dropdowns_col1.selectbox(
        'Magnetic field column',
        # The options should be the columns of the uploaded file
        base_stations_columns,
        key="base_stations_magfield"
    )

    base_stations_time = base_stations_dropdowns_col2.selectbox(
        'Time column',
        base_stations_columns,
        key="base_stations_time"
    )


with st.container():

    '''
    ### IGRF Configuration
    In order to request data from the IGRF API, **you need to 
    register** on the following [page](https://www.ngdc.noaa.gov/geomag/CalcSurvey.shtml), 
    a key to use the API will be sent to your email and you can use it on this page to access IGRF data.
    '''

    igrf_dropdowns_col1, igrf_dropdowns_col2 = st.columns(2)

    igrf_reference_model = igrf_dropdowns_col1.selectbox(
        'IGRF reference model',
        ['IGRF', 'WMM'],
        key="igrf_reference_model"
    )

    # Input for using a default value for elevation
    igrf_elevation = igrf_dropdowns_col2.number_input(
        'Elevation in meters (set a default if your data does not have it)',
        value=0,
        key="igrf_elevation"
    )

    igrf_api_key = igrf_dropdowns_col1.text_input('IGRF API key (if not provided the IGRF correction will not be made)', value='')

    process_button = st.button('Process data', type="primary")

if process_button:

    if uploaded_stations_file is None or uploaded_base_stations_file is None:
        st.error('Please upload the stations and base stations files')
    else:
        # Create a list of the selected columns for the stations, if there is a None value, remove it
        stations_selected_columns = [stations_date, stations_magfield, stations_latitude, stations_elevation, stations_time, stations_longitude]
        stations_selected_columns = [x for x in stations_selected_columns if x is not None]

        base_stations_selected_columns = [base_stations_date, base_stations_magfield, base_stations_time]

        if columns_exist(stations_dataframe, stations_selected_columns) and columns_exist(base_stations_dataframe, base_stations_selected_columns):
            st.write('All columns exist')

            try:
                stations_dataframe[stations_time] = stations_dataframe[stations_time].apply(lambda x: format_time(x))
                base_stations_dataframe[base_stations_time] = base_stations_dataframe[base_stations_time].apply(lambda x: format_time(x))
            except:
                st.error('Could not format the time column')
                st.stop()

            base_stations_dataframe = base_stations_dataframe[base_stations_selected_columns]
            base_stations_dataframe.rename(columns={
                base_stations_date: 'base_date',
                base_stations_magfield: 'base_magfield',
                base_stations_time: 'base_time',
            }, inplace=True)
            base_stations_dataframe.insert(0, 'diff_time', np.nan)
            base_stations_dataframe.insert(0, 'base_magfield_mean', np.nan)

            final_df = stations_dataframe.copy()
            final_df.rename(columns={
                stations_date: 'sta_date',
                stations_magfield: 'sta_magfield',
                stations_latitude: 'latitude',
                stations_longitude: 'longitude',
                stations_elevation: 'elevation',
                stations_time: 'sta_time',
            }, inplace=True)

            final_df = final_df.assign(**dict.fromkeys(base_stations_dataframe.columns, np.nan))

            ######################## CLOSEST MATCHES IN TIME ########################
            # Show the progress bar
            time_match_progress_text = "Finding closest matches in time between field stations and base stations."
            time_match_bar = st.progress(0, text=time_match_progress_text)

            for i in range(len(final_df)):
                for date in base_stations_dataframe['base_date']:
                    if final_df['sta_date'][i] == date:
                        # Select the data from base_stations_dataframe that has the same date
                        base_stations_dataframe_date = base_stations_dataframe[base_stations_dataframe['base_date'] == date]
                        closest_time = base_stations_dataframe_date.iloc[np.argmin(np.abs(base_stations_dataframe_date['base_time'] - final_df.loc[i, 'sta_time'])), :]
                        final_df.loc[i, 'base_date'] = closest_time['base_date']
                        final_df.loc[i, 'base_time'] = closest_time['base_time']
                        final_df.loc[i, 'base_magfield'] = closest_time['base_magfield']
                        final_df.loc[i, 'diff_time'] = final_df.loc[i, 'sta_time'] - final_df.loc[i, 'base_time']
                        final_df.loc[i, 'base_magfield_mean'] = np.mean(base_stations_dataframe_date['base_magfield'])

                # Update the progress bar
                time_match_bar.progress((i + 1) / len(final_df), text=time_match_progress_text + f" {i + 1}/{len(final_df)} completed.")


            ######################## DAY VARIATION PROCESSING ########################
            final_df['diurnal_var'] = final_df['base_magfield'] - final_df['base_magfield_mean']
            final_df['diurnal_var_corr'] = final_df['sta_magfield'] - final_df['diurnal_var']

            st.success('Diurnal variation processing completed')

            ######################## IGRF PROCESSING ########################
            if igrf_api_key != '':
                igrf_progress_text = "Requesting IGRF values."
                igrf_bar = st.progress(0, text=igrf_progress_text)
                try:
                    print('\nRequesting IGRF data...\n')
                    api_url = 'https://www.ngdc.noaa.gov/geomag-web/calculators/calculateIgrfwmm'
                    req_number = 0
                    # Loop through the data and request the IGRF data
                    for i in range(len(final_df)):
                        req_number += 1

                        date = final_df['base_date'][i]
                        day, month, year = date.split('/')

                        # Set the parameters for the request
                        params = {
                            'lat1': final_df['latitude'][i],
                            'lon1': final_df['longitude'][i],
                            'coordinateSystem': 'D',
                            'model': 'IGRF',
                            'startYear': int(year),
                            'startMonth': int(month),
                            'startDay': int(day),
                            'endYear': int(year),
                            'endMonth': int(month),
                            'endDay': int(day),
                            'resultFormat': 'json',
                            'key': str(igrf_api_key)
                        }
                        # Request the data
                        response = requests.get(api_url, params=params)
                        # Check if the request was successful and print the number of the request every 10 requests
                        if response.status_code == 200:
                            if req_number % 10 == 0:
                                # print('{} requests completed...'.format(req_number))
                                time.sleep(1)
                        else:
                            st.error(f'Error in request #{req_number}. Check your data and try again.')
                            st.stop()

                        # Add the response data to the final_df dataframe
                        response = response.json()
                        igrf_intensity = response['result'][0]['totalintensity']
                        final_df.loc[i, 'igrf_intensity'] = igrf_intensity

                        # Update the progress bar
                        igrf_bar.progress((i + 1) / len(final_df), text=igrf_progress_text + f" {i + 1}/{len(final_df)} requests completed.")


                except:
                    st.error('IGRF service is not available. Please try again later.')
                    st.stop()

                st.success('IGRF processing completed')

            st.write(final_df)

            @st.cache_data
            def convert_df(df):
                # IMPORTANT: Cache the conversion to prevent computation on every rerun
                return df.to_csv().encode('utf-8')

            csv = convert_df(final_df)

            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f'magnetopy_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
            )
        
        else:
            st.error('Some columns do not exist')