# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['raster_processing'] and menu['slope']:
    print('run slope')
    
    # SET UP ##############################################

    from os.path import exists
    from pathlib import Path

    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder_s = output_folder_parent / 'spatial'
    output_folder_t = output_folder_parent / 'tabular'
    os.makedirs(output_folder_t, exist_ok=True)

    # Check if elevation raster exists ------------
    if not exists(output_folder_s / f'{city_name_l}_elevation.tif'):
        print('cannot generate slope because elevation raster does not exist')
        exit()
    
    import os
    import csv
    import numpy as np
    import richdem as rd
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    try:
        print('process slope')

        # Reproject elevation raster to a projected coordinate system
        with rasterio.open(output_folder_s / f'{city_name_l}_elevation.tif') as src:
            dst_crs = 'EPSG:3857'  # Web Mercator projection
            transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
            out_meta = src.meta.copy()
            out_meta.update({
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            with rasterio.open(output_folder_s / f'{city_name_l}_elevation_3857.tif', 'w', **out_meta) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.nearest)

        # Calculate slope
        elev = rd.LoadGDAL(str(output_folder_s / f'{city_name_l}_elevation_3857.tif'))
        slope = rd.TerrainAttribute(elev, attrib = 'slope_degrees')
        rd.SaveGDAL(str(output_folder_s / f'{city_name_l}_slope_3857.tif'), slope)

        # Reproject slope raster to WGS84
        with rasterio.open(output_folder_s / f'{city_name_l}_slope_3857.tif') as src:
            dst_crs = 'EPSG:4326'
            transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
            out_meta = src.meta.copy()
            out_meta.update({
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            with rasterio.open(output_folder_s / f'{city_name_l}_slope.tif', 'w', **out_meta) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.nearest)

        # Calculate slope stats
        print('calculate slope stats')
        
        with rasterio.open(output_folder_s / f'{city_name_l}_slope.tif') as src:
            # Read raster data
            raster_data = src.read(1)
            
            # Define the bins
            bins = [0, 2, 5, 10, 20, 90]
            
            # Calculate histogram
            hist, _ = np.histogram(raster_data, bins=bins)
            
            # Write bins and hist to a CSV file
            with open(output_folder_t / f'{city_name_l}_slope.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Bin', 'Count'])
                for i, count in enumerate(hist):
                    bin_range = f"{bins[i]}-{bins[i+1]}"
                    writer.writerow([bin_range, count])
    except:
        print('process slope failed')
    
    # Remove intermediate outputs
    try:
        os.remove(output_folder_s / f'{city_name_l}_elevation_3857.tif')
        os.remove(output_folder_s / f'{city_name_l}_slope_3857.tif')

        if not menu['elevation']:
            os.remove(output_folder_s / f'{city_name_l}_elevation.tif')
    except:
        print('remove intermediate slope outputs failed')
