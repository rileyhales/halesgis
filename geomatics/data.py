import datetime
import json
import os

import netCDF4 as nc
import pygrib
import requests

__all__ = ['download_noaa_gfs', 'get_livingatlas_geojson', 'inspect_netcdf', 'inspect_grib']


def download_noaa_gfs(save_path: str, steps: int) -> list:
    """
    Downloads Grib files containing the latest NOAA GFS forecast. The files are saved to a specified directory and are
    named for the timestamp of the forecast and the time that the forecast is predicting for. The timestamps are in
    YYYYMMDDHH time format. E.G a file named gfs_2020010100_2020010512.grb means that the file contains data from the
    forecast created Jan 1 2020 at 00:00:00 for the time Jan 5 2020 at 12PM.

    Args:
        save_path: an absolute file path to the directory where you want to save the gfs files
        steps: the number of 6 hour forecast steps to download. E.g. 4 steps = 1 day

    Returns:
        List of absolute paths to the files that were downloaded
    """
    # determine which forecast we should be looking for
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
    if now.hour >= 18:
        fc_hour = '18'
    elif now.hour >= 12:
        fc_hour = '12'
    elif now.hour >= 6:
        fc_hour = '06'
    else:
        fc_hour = '00'
    fc_date = now.strftime('%Y%m%d')
    timestamp = datetime.datetime.strptime(fc_date + fc_hour, '%Y%m%d%H')

    # create a list of the 3 digit string forecast time steps/intervals
    fc_time_steps = []
    for step in range(steps):
        step = str(6 * (step + 1))
        while len(step) < 3:
            step = '0' + step
        fc_time_steps.append(step)

    # actually downloading the data
    downloaded_files = []
    for step in fc_time_steps:
        # build the url to download the file from
        url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t' + fc_hour + 'z.pgrb2.0p25.f' + \
              step + '&all_lev=on&all_var=on&dir=%2Fgfs.' + fc_date + '%2F' + fc_hour

        # set the file name: gfs_DATEofFORECAST_TIMESTEPofFORECAST.grb
        file_timestep = timestamp + datetime.timedelta(hours=int(step))
        filename = 'gfs_{0}_{1}.grb'.format(timestamp.strftime('%Y%m%d%H'), file_timestep.strftime("%Y%m%d%H"))
        filepath = os.path.join(save_path, filename)
        downloaded_files.append(filepath)

        # download the file
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=10240):
                    if chunk:
                        f.write(chunk)
    return downloaded_files


def get_livingatlas_geojson(location: str) -> dict:
    """
    Requests a geojson from the ESRI living atlas services for World Regions or Generalized Country Boundaries

    Args:
        location: the name of the Country or World Region, properly spelled and capitalized

    Returns:
        a json python object, dict like
    """
    countries = [
        'Afghanistan', 'Albania', 'Algeria', 'American Samoa', 'Andorra', 'Angola', 'Anguilla', 'Antarctica',
        'Antigua and Barbuda', 'Argentina', 'Armenia', 'Aruba', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas',
        'Bahrain', 'Baker Island', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bermuda',
        'Bhutan', 'Bolivia', 'Bonaire', 'Bosnia and Herzegovina', 'Botswana', 'Bouvet Island', 'Brazil',
        'British Indian Ocean Territory', 'British Virgin Islands', 'Brunei Darussalam', 'Bulgaria', 'Burkina Faso',
        'Burundi', 'Cambodia', 'Cameroon', 'Canada', 'Cape Verde', 'Cayman Islands', 'Central African Republic',
        'Chad', 'Chile', 'China', 'Christmas Island', 'Cocos Islands', 'Colombia', 'Comoros', 'Congo', 'Congo DRC',
        'Cook Islands', 'Costa Rica', "Côte d'Ivoire", 'Croatia', 'Cuba', 'Curacao', 'Cyprus', 'Czech Republic',
        'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador',
        'Equatorial Guinea', 'Eritrea', 'Estonia', 'Ethiopia', 'Falkland Islands', 'Faroe Islands', 'Fiji',
        'Finland', 'France', 'French Guiana', 'French Polynesia', 'French Southern Territories', 'Gabon', 'Gambia',
        'Georgia', 'Germany', 'Ghana', 'Gibraltar', 'Glorioso Island', 'Greece', 'Greenland', 'Grenada',
        'Guadeloupe', 'Guam', 'Guatemala', 'Guernsey', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti',
        'Heard Island and McDonald Islands', 'Honduras', 'Howland Island', 'Hungary', 'Iceland', 'India',
        'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Isle of Man', 'Israel', 'Italy', 'Jamaica', 'Jan Mayen', 'Japan',
        'Jarvis Island', 'Jersey', 'Johnston Atoll', 'Jordan', 'Juan De Nova Island', 'Kazakhstan', 'Kenya',
        'Kiribati', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya',
        'Liechtenstein', 'Lithuania', 'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta',
        'Marshall Islands', 'Martinique', 'Mauritania', 'Mauritius', 'Mayotte', 'Mexico', 'Micronesia',
        'Midway Islands', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Montserrat', 'Morocco', 'Mozambique',
        'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Caledonia', 'New Zealand', 'Nicaragua', 'Niger',
        'Nigeria', 'Niue', 'Norfolk Island', 'North Korea', 'Northern Mariana Islands', 'Norway', 'Oman',
        'Pakistan', 'Palau', 'Palestinian Territory', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru',
        'Philippines', 'Pitcairn', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Réunion', 'Romania',
        'Russian Federation', 'Rwanda', 'Saba', 'Saint Barthelemy', 'Saint Eustatius', 'Saint Helena',
        'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Martin', 'Saint Pierre and Miquelon',
        'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia',
        'Senegal', 'Serbia', 'Seychelles', 'Sierra Leone', 'Singapore', 'Sint Maarten', 'Slovakia', 'Slovenia',
        'Solomon Islands', 'Somalia', 'South Africa', 'South Georgia', 'South Korea', 'South Sudan', 'Spain',
        'Sri Lanka', 'Sudan', 'Suriname', 'Svalbard', 'Swaziland', 'Sweden', 'Switzerland', 'Syria', 'Tajikistan',
        'Tanzania', 'Thailand', 'The Former Yugoslav Republic of Macedonia', 'Timor-Leste', 'Togo', 'Tokelau',
        'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Turks and Caicos Islands', 'Tuvalu',
        'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Uruguay',
        'US Virgin Islands', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 'Wake Island',
        'Wallis and Futuna', 'Yemen', 'Zambia', 'Zimbabwe']
    regions = ('Antarctica', 'Asiatic Russia', 'Australia/New Zealand', 'Caribbean', 'Central America', 'Central Asia',
               'Eastern Africa', 'Eastern Asia', 'Eastern Europe', 'European Russia', 'Melanesia', 'Micronesia',
               'Middle Africa', 'Northern Africa', 'Northern America', 'Northern Europe', 'Polynesia', 'South America',
               'Southeastern Asia', 'Southern Africa', 'Southern Asia', 'Southern Europe', 'Western Africa',
               'Western Asia', 'Western Europe')

    # get the geojson data from esri
    base = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/'
    if location in regions:
        url = base + 'World_Regions/FeatureServer/0/query?f=pgeojson&outSR=4326&where=REGION+%3D+%27' + location + '%27'
    elif location in countries:
        url = base + 'World__Countries_Generalized_analysis_trim/FeatureServer/0/query?f=pgeojson&outSR=4326&where=NAME+%3D+%27' + location + '%27'
    else:
        raise Exception('Country or World Region not recognized')

    req = requests.get(url=url)
    return json.loads(req.text)


def inspect_netcdf(path: str) -> None:
    """
    Prints lots of messages showing information about variables, dimensions, and metadata

    Args:
        path: The path to a single netcdf file.
    """
    nc_obj = nc.Dataset(path, 'r', clobber=False, diskless=True, persist=False)

    print("This is your netCDF python object")
    print(nc_obj)
    print()

    print("There are " + str(len(nc_obj.variables)) + " variables")       # The number of variables
    print("There are " + str(len(nc_obj.dimensions)) + " dimensions")     # The number of dimensions
    print()

    print('These are the global attributes of the netcdf file')
    print(nc_obj.__dict__)                                    # access the global attributes of the netcdf file
    print()

    print("Detailed view of each variable")
    print()
    for variable in nc_obj.variables.keys():                  # .keys() gets the name of each variable
        print('Variable Name:  ' + variable)              # The string name of the variable
        print('The view of this variable in the netCDF python object')
        print(nc_obj[variable])                               # How to view the variable information (netcdf obj)
        print('The data array stored in this variable')
        print(nc_obj[variable][:])                            # Access the numpy array inside the variable (array)
        print('The dimensions associated with this variable')
        print(nc_obj[variable].dimensions)                    # Get the dimensions associated with a variable (tuple)
        print('The metadata associated with this variable')
        print(nc_obj[variable].__dict__)                      # How to get the attributes of a variable (dictionary)
        print()

    for dimension in nc_obj.dimensions.keys():
        print(nc_obj.dimensions[dimension].size)              # print the size of a dimension

    nc_obj.close()                                            # close the file connection to the file
    return


def inspect_grib(path: str, band_number=0) -> None:
    """
    Prints lots of messages showing information about variables, dimensions, and metadata

    Args:
        path: The path to a netcdf file.
        band_number: (optional) An integer corresponding to the band number you want more information for
    """
    grib = pygrib.open(path)
    grib.seek(0)
    print('This is a summary of all the information in your grib file')
    print(grib.read())

    if band_number:
        print()
        print('The keys for this variable are:')
        print(grib[band_number].keys())
        print()
        print('The data stored in this variable are:')
        print(grib[band_number].values)

    return
