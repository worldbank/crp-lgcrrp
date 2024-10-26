# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['soil_salinity']:
    print('run soil salinity')

    import os
    import pandas as pd
    import geopandas as gpd
    from pathlib import Path
    from os.path import exists
    import rasterio
    import rasterio.mask
    import numpy as np

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Read AOI shapefile --------
    # transform the input shp to correct prj (epsg 4326)
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    features = aoi_file.geometry

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder_s = output_folder_parent / 'spatial'
    output_folder_t = output_folder_parent / 'tabular'
    os.makedirs(output_folder_s, exist_ok=True)
    os.makedirs(output_folder_t, exist_ok=True)


    # PROCESS DATA ##################################
    years = [1986, 1992, 2000, 2002, 2005, 2009, 2016]
    xs = ['0000000000', '0000032768', '0000065536']
    ys = ['0000000000', '0000032768', '0000065536', '0000098304', '0000131072']
    avg_dict = {}

    for year in years:
        i = 0
        for x in xs:
            for y in ys:
                input_raster = Path(global_inputs['soil_salinity_source']) / f"salMap{year}-{x}-{y}.tif.tif"
                try:
                    with rasterio.open(input_raster) as src:
                        out_image, out_transform = rasterio.mask.mask(
                            src, features, all_touched = True, crop = True)
                        out_meta = src.meta.copy()

                    out_meta.update({"driver": "GTiff",
                                    "height": out_image.shape[1],
                                    "width": out_image.shape[2],
                                    "transform": out_transform})

                    with rasterio.open(output_folder_s / f'{city_name_l}_soil_salinity_{year}_{i}.tif', "w", **out_meta) as dest:
                        dest.write(out_image)
                    
                    i += 1
                except:
                    pass
        if exists(output_folder_s / f'{city_name_l}_soil_salinity_{year}_0.tif'):
            if exists(output_folder_s / f'{city_name_l}_soil_salinity_{year}_1.tif'):
                continue
                # TODO: merge rasters
            else:
                os.replace(output_folder_s / f'{city_name_l}_soil_salinity_{year}_0.tif', output_folder_s / f'{city_name_l}_soil_salinity_{year}.tif')

        with rasterio.open(output_folder_s / f'{city_name_l}_soil_salinity_{year}.tif') as src:
            temp_array = src.read(1)
            # temp_array = temp_array[temp_array != 0]
            avg_dict[year] = np.nanmean(temp_array)
    
    with open(f'mnt/02-process-output/tabular/{city_name_l}_soil_salinity.csv', 'w') as f:
        f.write('year,avg\n')
        for year in avg_dict:
            f.write("%s,%s\n"%(year, avg_dict[year]))