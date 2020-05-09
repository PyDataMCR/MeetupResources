"""
Author: Angeliki Loukatou, April 2020

This script is used to extract temperature data for a certain period from MERRA-2 data with nc4 format.

The data can be downloaded from this link: https://goldsmr4.gesdisc.eosdis.nasa.gov/data/MERRA2/M2T1NXSLV.5.12.4/ after
creating an Earthdata account and follow the instructions here: https://urs.earthdata.nasa.gov/home.

The data are extracted into a pandas dataframe and saved into an excel file.

In the MERRA-2 dataset(s), there are different atmospheric variables and each of those has three different dimensions:
- time: 24-hour time series
- latitude: length 361 (0.5 degrees resolution)
- longitude: length 576 (0.625 degrees resolution)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset


def find_index_value(coord, search_value, type):
    """
    This function takes as input the list of latitudes (or longitudes) as x along with the user's latitude (or longitude)
    as the search_value and returns back the index of the selected latitude (or longitude).
    """

    for i in range(len(coord)):
        if coord.loc[i] == search_value:
            return i, 0

    if type == 'lat':
        step = 0.5
    else:
        step = 0.625

    floor_rem = search_value // step
    new_search_value = floor_rem * step

    for i in range(len(coord)):
        epsilon = 1e-12
        # check if the difference is smaller than a low value rather than checking the equality (coord.loc[i] == new_search_value)
        # the value of latitude at index 180 is -1.797510e-13 
        # the value of longitude at index 288 is -5.920304e-13
        if np.abs(coord.loc[i] - new_search_value) < epsilon:
            return i, i+1


def plot_daily_cycle(T2Mextracted, day):
    """
    This function plots the average daily cycle of the temperature for a given day.
    """
    T2Mextracted.plot()
    plt.xlabel('Time t(h)')
    plt.ylabel('Temperature (degC)')
    plt.title('Average hourly daily temperature for day: {}'.format(day))
    plt.show()


def bilinear_interpolation(lat, lon, lat1, lat2, lon1, lon2, T2Mextracted11, T2Mextracted12, T2Mextracted21, T2Mextracted22):
    """
    This function computes the interpolated temperature values for a given set of latitude and longitude.
    """
    x1 = lat1
    x2 = lat2
    y1 = lon1
    y2 = lon2
    I = (x2-x1)*(y2-y1)
    T2Mextracted = pd.DataFrame(index=range(0, 24), columns=['Value'])

    for i in range(len(T2Mextracted11)):
        q11 = T2Mextracted11.loc[i, 'Value']
        q12 = T2Mextracted12.loc[i, 'Value']
        q21 = T2Mextracted21.loc[i, 'Value']
        q22 = T2Mextracted22.loc[i, 'Value']
        T2Mextracted.loc[i] = ((x2-lat)*(y2-lon))/I * q11 + ((lat-x1)*(y2-lon))/I * q21 + ((x2-lat)*(lon-y1))/I * q12 +\
                              ((lat-x1)*(lon-y1))/I * q22

    return T2Mextracted


def MERRA2_extractor(base_name, days, lat, lon):
    """
    This function extracts the temperature profiles from the MERRA-2 data and saves them either in a square format with
    time-rows and day-columns or in a time series with time resolution 3600 seconds.
    """

    time = range(0, 24)
    all_temperatures = pd.DataFrame(index=time, columns=days)

    for day in days:
        # specify the filename for the day
        filename = base_name + day + '.nc4'
        # read the data
        data = Dataset(filename, "r", format="NETCDF4")
        # uncomment below to explore the data structure, resolution etc.
        # print(data)
        # print(data.variables)

        # extract the longitude, latitude and temperature at 2 meters
        lons = data.variables['lon'][:]
        lats = data.variables['lat'][:]
        T2M = data.variables['T2M'][:, :, :]

        # convert the arrays of lons and lats to dataframes after retrieving valid entries from masked arrays with
        # the compressed() function
        lons = pd.DataFrame(lons.compressed(), columns=['Value'])
        lats = pd.DataFrame(lats.compressed(), columns=['Value'])

        # find the indices before and after the given latitude and longitude
        lat_index1, lat_index2 = find_index_value(lats['Value'], lat, 'lat')
        lon_index1, lon_index2 = find_index_value(lons['Value'], lon, 'lon')

        # find the location of the above indices
        lat1 = (lat // 0.5) * 0.5
        lat2 = lat1 + 0.5
        lon1 = (lon // 0.625) * 0.625
        lon2 = lon1 + 0.625

        # if the given coordinates coincide with values in lats or lons, use them directly to extract the temperature data
        if lat_index2 == 0 and lon_index2 == 0:
            T2Mextracted = pd.DataFrame(T2M[:, lat_index1, lon_index1])
            T2Mextracted.columns = ['Value' if x == 0 else x for x in T2Mextracted.columns]
        else:
            # interpolate to get the requested temperature data
            T2Mextracted11 = pd.DataFrame(T2M[:, lat_index1, lon_index1], columns=['Value'])
            T2Mextracted12 = pd.DataFrame(T2M[:, lat_index1, lon_index2], columns=['Value'])
            T2Mextracted21 = pd.DataFrame(T2M[:, lat_index2, lon_index1], columns=['Value'])
            T2Mextracted22 = pd.DataFrame(T2M[:, lat_index2, lon_index2], columns=['Value'])
            T2Mextracted = bilinear_interpolation(lat, lon, lat1, lat2, lon1, lon2,
                                                  T2Mextracted11, T2Mextracted12, T2Mextracted21, T2Mextracted22)

        # convert from Kelvin to Celsius
        T2Mextracted = T2Mextracted['Value'] - 273.15

        # uncomment below to plot the daily cycle for a certain day
        #plot_daily_cycle(T2Mextracted, day)

        # save the temperature time series for this day in the dataframe
        all_temperatures.loc[:, day] = T2Mextracted

    # convert all_daily temperature profiles a into time series
    temperature_time_series = all_temperatures.loc[:, days[0]]
    for i in range(len(days)-1):
        temperature_time_series = pd.concat([temperature_time_series, all_temperatures.loc[:, days[i+1]]], axis=0)
    temperature_time_series = pd.DataFrame(temperature_time_series, columns=['Temperature (degC)'])
    temperature_time_series['Time (s)'] = range(0, 3600*(len(days)*24), 3600)
    temperature_time_series['Date'] = pd.date_range('2018-02-22', periods=len(days) * 24, freq='H')
    temperature_time_series = temperature_time_series.set_index('Time (s)')

    return all_temperatures, temperature_time_series


def plot_all_temperature_profiles(all_temperatures_EA, all_temperatures_Br, all_temperatures_Or, all_temperatures_So):
    """
    This function is used to plot all the daily temperature profiles for different locations.
    """
    # plot all daily cycles
    fig, axs = plt.subplots(2, 2)
    fig.suptitle('Beast from the East hourly temperature profile for the period 22/02/18-04/03/18')
    axs[0, 0].plot(all_temperatures_EA)
    axs[0, 0].set_title('East Anglia')
    axs[0, 1].plot(all_temperatures_Br)
    axs[0, 1].set_title('Bridgend')
    axs[1, 0].plot(all_temperatures_Or)
    axs[1, 0].set_title('Orkney islands')
    axs[1, 1].plot(all_temperatures_So)
    axs[1, 1].set_title('Southampton')

    # set labels
    for ax in axs.flat:
        ax.set(xlabel='Time t(hours)', ylabel='Temperature T(degC)')

    # hide x labels and tick labels for top plots and y ticks for right plots
    for ax in axs.flat:
        ax.label_outer()

    # show the plot
    plt.show()


def plot_ts_temperature_profiles(temperature_ts_EA, temperature_ts_Br, temperature_ts_Or, temperature_ts_So):
    """
    This function is used to plot the time series of the daily temperature profiles for different locations.
    """
    # create resolution for x-axis
    x_range_axis = np.arange(24)
    x_range_axis = np.tile(x_range_axis, 11)
    lab_x = [i for i in range(len(x_range_axis))]
    fig, axs = plt.subplots(2, 2)
    fig.suptitle('Beast from the East hourly temperature profile for the period 22/02/18-04/03/18')
    axs[0, 0].plot(lab_x, temperature_ts_EA['Temperature (degC)'])
    axs[0, 0].set_title('East Anglia')
    axs[0, 1].plot(lab_x, temperature_ts_Br['Temperature (degC)'], 'tab:orange')
    axs[0, 1].set_title('Bridgend')
    axs[1, 0].plot(lab_x, temperature_ts_Or['Temperature (degC)'], 'tab:green')
    axs[1, 0].set_title('Orkney islands')
    axs[1, 1].plot(lab_x, temperature_ts_So['Temperature (degC)'], 'tab:red')
    axs[1, 1].set_title('Southampton')

    # set labels
    for ax in axs.flat:
        ax.set(xlabel='Time t(hours)', ylabel='Temperature T(degC)')

    # hide x labels and tick labels for top plots and y ticks for right plots
    for ax in axs.flat:
        ax.label_outer()

    # show plot
    plt.show()


if __name__ == '__main__':

    # specify tha base name and the selected dates
    base_name = 'MERRA2_400.tavg1_2d_slv_Nx.2018'
    days = ['0222', '0223', '0224', '0225', '0226', '0227', '0228', '0301', '0302', '0303', '0304']

    # specify latitude and longitude of the selected location: East Anglia, Bridgend, Orkney island, Southampton
    coordinates = {'EA': (52.242, 0.692), 'Br': (51.5043, 3.5769), 'Or': (58.9809, 2.9605), 'So': (50.9097, 1.4044)}

    # call the MERRA2_extractor for all locations
    all_temperatures_EA, temperature_ts_EA = MERRA2_extractor(base_name, days, coordinates['EA'][0], coordinates['EA'][1])
    all_temperatures_Or, temperature_ts_Or = MERRA2_extractor(base_name, days, coordinates['Br'][0], coordinates['Br'][1])
    all_temperatures_So, temperature_ts_So = MERRA2_extractor(base_name, days, coordinates['Or'][0], coordinates['Or'][1])
    all_temperatures_Br, temperature_ts_Br = MERRA2_extractor(base_name, days, coordinates['So'][0], coordinates['So'][1])

    # plot all daily temperature profiles
    plot_all_temperature_profiles(all_temperatures_EA, all_temperatures_Br, all_temperatures_Or, all_temperatures_So)

    # plot time series of temperature profiles
    plot_ts_temperature_profiles(temperature_ts_EA, temperature_ts_Br, temperature_ts_Or, temperature_ts_So)

    # write data of two different formats to excel file
    with pd.ExcelWriter(path='temperature_data_all_locations.xlsx', engine='xlsxwriter') as writer:
        all_temperatures_EA.to_excel(writer, sheet_name='square_East-Anglia')
        temperature_ts_EA.to_excel(writer, sheet_name='long_East-Anglia')
        all_temperatures_Br.to_excel(writer, sheet_name='square_Bridgend')
        temperature_ts_Br.to_excel(writer, sheet_name='long_Bridgend')
        all_temperatures_Or.to_excel(writer, sheet_name='square_Orkney-islands')
        temperature_ts_Or.to_excel(writer, sheet_name='long_Orkney-islands')
        all_temperatures_So.to_excel(writer, sheet_name='square_Southampton')
        temperature_ts_So.to_excel(writer, sheet_name='long_Southampton')
