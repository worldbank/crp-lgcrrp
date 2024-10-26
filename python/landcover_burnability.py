# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['landcover_burn']:
    print('run landcover_burnability')
    
    import os
    import geopandas as gpd
    import rasterio.mask
    import rasterio
    from pathlib import Path
    from os.path import exists

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

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder = output_folder_parent / 'spatial'
    os.makedirs(output_folder, exist_ok=True)


    # PROCESSING ########################################
    if not exists(output_folder / f'{city_name_l}_lc_burn.tif'):
        with rasterio.open(global_inputs['lc_burn_source']) as src:
            # shapely presumes all operations on two or more features exist in the same Cartesian plane.
            out_image, out_transform = rasterio.mask.mask(
                src, features, all_touched = True, crop = True)
            out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform})
        
        ls000 = [190, 200, 201, 202, 210, 220]
        ls016 = [151]
        ls033 = [12, 140, 152, 153]
        ls050 = [11, 82, 110, 150, 180]
        ls066 = [10, 20, 30, 40, 70, 71, 81, 90, 121, 130]
        ls083 = [50, 61, 80, 100, 120, 122, 160, 170]
        ls100 = [60, 62]

        output_input_dict = {0: ls000,
                            0.16: ls016,
                            0.33: ls033,
                            0.5: ls050,
                            0.66: ls066,
                            0.83: ls083,
                            1: ls100}

        for i in range(len(out_image[0])):
            for j in range(len(out_image[0, i])):
                for out_val in output_input_dict:
                    if out_image[0, i, j] in output_input_dict[out_val]:
                        out_image[0, i, j] = out_val
                        
        out_image[(out_image < 0) | (out_image > 1)] = 0

        with rasterio.open(output_folder / f'{city_name_l}_lc_burn.tif', "w", **out_meta) as dest:
            dest.write(out_image)