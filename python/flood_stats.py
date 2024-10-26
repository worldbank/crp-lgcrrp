# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['flood_stats']:
    print('run flood_stats')
    
    import os
    import pandas as pd
    import geopandas as gpd
    import numpy as np
    import rasterio.mask
    import rasterio
    from pathlib import Path
    from os.path import exists
    from rasterio.warp import reproject, Resampling

    # SET UP ##############################################

    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Read AOI shapefile --------
    print('read AOI shapefile')
    # transform the input shp to correct prj (epsg 4326)
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    features = aoi_file.geometry
    aoi_bounds = aoi_file.bounds

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder_s = output_folder_parent / 'spatial'
    output_folder_t = output_folder_parent / 'tabular'
    os.makedirs(output_folder_s, exist_ok=True)
    os.makedirs(output_folder_t, exist_ok=True)

    
    # SET PARAMETERS #########################################
    flood_types = ['coastal', 'fluvial', 'pluvial']
    

    # FLOOD WSF STATS ###################################
    if exists(output_folder_s / f'{city_name_l}_wsf_utm.tif'):
        # Reproject flood raster -------------------
        with rasterio.open(output_folder_s / f'{city_name_l}_wsf_utm.tif') as wsf:
            tgt_crs = wsf.crs
            tgt_transform = wsf.transform
            tgt_width = wsf.width
            tgt_height = wsf.height
            
        for ft in flood_types:
            if exists(output_folder_s / f'{city_name_l}_{ft}_2020_lt1.tif'):
                with rasterio.open(output_folder_s / f'{city_name_l}_{ft}_2020_lt1.tif') as src:
                    src_crs = src.crs
                    src_transform = src.transform
                    src_width = src.width
                    src_height = src.height
                    src_dtype = src.dtypes[0]
                    src_data = src.read(1)

                # Prepare the array to store resampled data
                resampled_data = np.empty((tgt_height, tgt_width), dtype = src_dtype)

                # Perform the resampling
                reproject(
                    source=src_data,
                    destination=resampled_data,
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=tgt_transform,
                    dst_crs=tgt_crs,
                    resampling=Resampling.nearest
                )

                # Write the resampled raster to file
                with rasterio.open(
                    output_folder_s / f'{city_name_l}_{ft}_2020_lt1_utm.tif',
                    'w',
                    driver='GTiff',
                    height=tgt_height,
                    width=tgt_width,
                    count=1,
                    dtype=resampled_data.dtype,
                    crs=tgt_crs,
                    transform=tgt_transform
                ) as dst:
                    dst.write(resampled_data, 1)
        
        # Combine flood raster -----------------------------------
        flood_arrays = []

        for ft in flood_types:
            if exists(output_folder_s / f'{city_name_l}_{ft}_2020_lt1_utm.tif'):
                with rasterio.open(output_folder_s / f'{city_name_l}_{ft}_2020_lt1_utm.tif') as src:
                    flood_arrays.append(src.read(1))
                    out_meta = src.meta.copy()
        
        if len(flood_arrays) >= 2:
            comb_flood_array = np.maximum(flood_arrays[0], flood_arrays[1])
            if len(flood_arrays) == 3:
                comb_flood_array = np.maximum(comb_flood_array, flood_arrays[2])
            with rasterio.open(output_folder_s / f'{city_name_l}_combined_2020_lt1_utm.tif', 'w', **out_meta) as dst:
                dst.write(comb_flood_array, 1)
            flood_types.append('combined')

        # Compute zonal stats --------------------------------
        flood_stats = {}

        with rasterio.open(output_folder_s / f'{city_name_l}_wsf_utm.tif') as wsf:
            wsf_array = wsf.read(1)
            pixelSizeX, pixelSizeY = wsf.res

            for ft in flood_types:
                if exists(output_folder_s / f'{city_name_l}_{ft}_2020_lt1_utm.tif'):
                    flood_stats[ft] = {}

                    with rasterio.open(output_folder_s / f'{city_name_l}_{ft}_2020_lt1_utm.tif') as fld:
                        flood_array = fld.read(1)
                        for year in range(1985, 2016):
                            exposed_sqkm = np.nansum(flood_array[wsf_array == year]) * pixelSizeX * pixelSizeY / 1e6
                            flood_stats[ft][year] = exposed_sqkm + flood_stats[ft].get(year - 1, 0)
        
        # Write to csv -------------------------
        flood_df = []
        for ft in flood_types:
            if not flood_stats.get(ft, None) is None:
                flood_df.append(pd.DataFrame(list(flood_stats[ft].items()), columns=['year', ft]))

        merged_df = pd.read_csv(output_folder_t / f'{city_name_l}_wsf_stats.csv')
        merged_df.rename(columns={'cumulative sq km': 'total_built_up_area'}, inplace=True)
        i = 0
        while i < len(flood_df):
            merged_df = pd.merge(merged_df, flood_df[i], on='year')
            merged_df[f'{flood_df[i].keys()[1]}_exposed_pct'] = merged_df[f'{flood_df[i].keys()[1]}'] / merged_df['total_built_up_area'] * 100
            i += 1
        merged_df.to_csv(output_folder_t / f'{city_name_l}_built_up_flood_exposure.csv', index = False)
    else:
        print('WSF UTM raster does not exist')