import json
import shapefile
import os
import netCDF4
import pygrib
import numpy as np
import rasterio

__all__ = ['geojson_to_shapefile', 'netcdf_to_geotiff', 'grib_to_geotiff']


def geojson_to_shapefile(geojson, savepath):
    """
    Turns a valid dict, json, or geojson containing polygon data in a geographic coordinate system into a shapefile

    Args:
        geojson: a valid geojson as a dictionary or json python object
        savepath: the full file path to save the shapefile to, including the file_name.shp

    Returns:
        None
    """
    # turn the geojson into a dictionary if it isn't
    if not isinstance(geojson, dict):
        try:
            geojson = json.loads(geojson)
        except json.JSONDecodeError:
            raise Exception('Unable to extract a dictionary or json like object from the argument geojson')

    # create the shapefile
    fileobject = shapefile.Writer(target=savepath, shpType=shapefile.POLYGON, autoBalance=True)

    # label all the columns in the .dbf
    geomtype = geojson['features'][0]['geometry']['type']
    if geojson['features'][0]['properties']:
        for attribute in geojson['features'][0]['properties']:
            fileobject.field(str(attribute), 'C', '30')
    else:
        fileobject.field('Name', 'C', '50')

    # add the geometry and attribute data
    for feature in geojson['features']:
        # record the geometry
        if geomtype == 'Polygon':
            fileobject.poly(polys=feature['geometry']['coordinates'])
        elif geomtype == 'MultiPolygon':
            for i in feature['geometry']['coordinates']:
                fileobject.poly(polys=i)

        # record the attributes in the .dbf
        if feature['properties']:
            fileobject.record(**feature['properties'])
        else:
            fileobject.record('unknown')

    # close writing to the shapefile
    fileobject.close()

    # create a prj file
    with open(savepath + '.prj', 'w') as prj:
        prj.write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
                  'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')

    return


# todo
def netcdf_to_geotiff(path, variable, **kwargs):
    """
    Converts a certain variable in netcdf files to a geotiff. Assumes WGS1984 GCS.

    Args:
        path: Either 1) the absolute path to a directory containing netcdfs named by date or 2) the absolute path to
            a single netcdf containing many time values for a specified variable
        variable: The name of a variable as it is stored in the netcdf e.g. 'temp' instead of Temperature

    Keyword Args:
        xvar: Name of the x coordinate variable used to spatial reference the netcdf array. Default: 'lon' (longitude)
        yvar: Name of the y coordinate variable used to spatial reference the netcdf array. Default: 'lat' (latitude)
        save_dir: The directory to store the geotiffs to. Default: directory containing the netcdfs.
        fill_value: The value used for filling no_data spaces in the array. Default: -9999
        crs: Coordinate Reference System used by rasterio.open(). An EPSG ID string such as 'EPSG:4326' or
            '+proj=latlong'
        delete_source: Allows you to delete the source netcdfs as they are converted. Default: False

    Returns:
        1. A list of paths to the geotiff files created
        2. A rasterio affine transformation used on the geotransform
    """
    files = path_to_file_list(path, 'nc')

    # parse the optional argument from the kwargs
    x_var = kwargs.get('xvar', 'lon')
    y_var = kwargs.get('yvar', 'lat')
    save_dir = kwargs.get('save_dir', os.path.dirname(files[0]))
    fill_value = kwargs.get('fill_value', -9999)
    crs = kwargs.get('crs', 'EPSG:4326')
    delete_sources = kwargs.get('delete_sources', False)

    # open the first netcdf and collect georeferencing information
    nc_obj = netCDF4.Dataset(files[0], 'r')
    lat = nc_obj.variables[x_var][:]
    lon = nc_obj.variables[y_var][:]
    lon_min = lon.min()
    lon_max = lon.max()
    lat_min = lat.min()
    lat_max = lat.max()
    data = nc_obj[variable][:][0]
    height = data.shape[0]
    width = data.shape[1]
    nc_obj.close()

    # Geotransform for each of the netcdf files
    affine = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)

    # A list of all the files that get written which can be returned
    output_files = []

    # Create a geotiff for each netcdf in the list of files
    for file in files:
        # set the files to open/save
        save_path = os.path.join(save_dir, os.path.basename(file) + '.tif')
        output_files.append(save_path)

        # open the netcdf and get the data array
        nc_obj = netCDF4.Dataset(file, 'r')
        array = np.asarray(nc_obj[variable][:])
        array = array[0]
        array[array == fill_value] = np.nan  # If you have fill values, change the comparator to git rid of it
        array = np.flip(array, axis=0)
        nc_obj.close()

        # if you want to delete the source netcdfs as you go
        if delete_sources:
            os.remove(file)

        # write it to a geotiff
        with rasterio.open(
                save_path,
                'w',
                driver='GTiff',
                height=data.shape[0],
                width=data.shape[1],
                count=1,
                dtype=data.dtype,
                nodata=np.nan,
                crs=crs,
                transform=affine,
        ) as dst:
            dst.write(array, 1)

    return output_files, affine


# todo
def grib_to_geotiff(path, band_number, **kwargs):
    """
    Converts a certain band number in grib files to geotiffs. Assumes WGS1984 GCS.

    Args:
        path: Either 1) the absolute path to a directory containing netcdfs named by date or 2) the absolute path to
            a single netcdf containing many time values for a specified variable
        band_number: The band number for your variable. Try using QGIS, ArcGIS, or pygrib.open().read()

    Keyword Args:
        save_dir: The directory to store the geotiffs to. Default: directory containing the gribs.
        fill_value: The value used for filling no_data spaces in the array. Default: -9999
        crs: Coordinate Reference System used by rasterio.open(). An EPSG ID string such as 'EPSG:4326' or
            '+proj=latlong'
        delete_source: Allows you to delete the source gribs as they are converted. Default: False

    Returns:
        1. A list of paths to the geotiff files created
        2. A rasterio affine transformation used on the geotransform
    """
    files = path_to_file_list(path, 'nc')

    # parse the optional argument from the kwargs
    save_dir = kwargs.get('save_dir', os.path.dirname(files[0]))
    fill_value = kwargs.get('fill_value', -9999)
    delete_sources = kwargs.get('delete_sources', False)
    crs = kwargs.get('crs', 'EPSG:4326')

    # Read raster dimensions only once to apply to all rasters
    raster_dim = rasterio.open(files[0])
    width = raster_dim.width
    height = raster_dim.height
    lon_min = raster_dim.bounds.left
    lon_max = raster_dim.bounds.right
    lat_min = raster_dim.bounds.bottom
    lat_max = raster_dim.bounds.top
    # Geotransform for each 24-hr raster (east, south, west, north, width, height)
    affine = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)

    # A list of all the files that get written which can be returned
    output_files = []

    for file in files:
        save_path = os.path.join(save_dir, os.path.basename(file) + '.tif')
        output_files.append(save_path)
        grib = pygrib.open(file)
        grib.seek(0)
        array = grib[band_number].values
        array[array == fill_value] = np.nan  # If you have fill values, change the comparator to git rid of it

        with rasterio.open(
                save_path,
                'w',
                driver='GTiff',
                height=array.shape[0],
                width=array.shape[1],
                count=1,
                dtype=array.dtype,
                nodata=np.nan,
                crs=crs,
                transform=affine,
        ) as dst:
            dst.write(array, 1)

        # if you want to delete the source gribs as you go
        if delete_sources:
            os.remove(file)

    return output_files, affine


# todo
def grib_to_netcdf():
    return
