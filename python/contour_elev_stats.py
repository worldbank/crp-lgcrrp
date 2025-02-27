# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['raster_processing'] and menu['elevation']:
    print('run contour')
    
    # SET UP ##############################################
    import os
    from os.path import exists
    from pathlib import Path
    import math
    import csv
    import numpy as np
    import matplotlib.pyplot as plt
    from shapely.geometry import LineString
    import geopandas as gpd
    import rasterio

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
        print('cannot generate contour lines or elevantion stats because elevation raster does not exist')
        exit()
    

    # CONTOUR ##############################################
    print('generate contour lines')

    with rasterio.open(output_folder_s / f'{city_name_l}_elevation.tif') as src:
        elevation_data = src.read(1)
        transform = src.transform
        demNan = src.nodata if src.nodata else -9999
    
    # Get min and max elevation values
    demMax = elevation_data.max()
    demMin = elevation_data[elevation_data != demNan].min()
    demDiff = demMax - demMin

    # Generate contour lines
    # Determine contour intervals
    contourInt = 1
    if demDiff > 250:
        contourInt = math.ceil(demDiff / 500) * 10
    elif demDiff > 100:
        contourInt = 5
    elif demDiff > 50:
        contourInt = 2
    
    contourMin = math.floor(demMin / contourInt) * contourInt
    contourMax = math.ceil(demMax / contourInt) * contourInt
    if contourMin < demMin:
        contour_levels = range(contourMin + contourInt, contourMax + contourInt, contourInt)
    else:
        contour_levels = range(contourMin, contourMax + contourInt, contourInt)

    # Generate contour lines using plt.contour
    contours = plt.contour(elevation_data, levels=contour_levels)

    # Convert contours to Shapely geometries (LineStrings)
    contour_lines = []
    for level, segments in zip(contours.levels, contours.allsegs):
        if len(segments) == 0:  # Skip levels with no segments
            continue

        for segment in segments:  # Iterate over line segments at this level
            if len(segment) > 1:  # Ensure valid line strings with enough points
                # Convert segment coordinates from pixel space to geographic coordinates
                geographic_line = [
                    (transform * (x, y)) for x, y in segment
                ]
                line = LineString(geographic_line)
                if line.is_valid:  # Ensure valid geometry before appending
                    contour_lines.append({"geometry": line, "elevation": float(level)})

    # Create a GeoDataFrame from the contour lines
    gdf = gpd.GeoDataFrame(contour_lines, crs="EPSG:4326")

    # Save the GeoDataFrame to a GeoPackage file
    output_path = output_folder_s / f"{city_name_l}_contours.gpkg"
    gdf.to_file(output_path, driver="GPKG", layer="contours")


    # ELEVATION STATS ##############################################
    print('calculate elevation stats')

    try:
        # Calculate equal interval bin edges
        contourLevels = list(contour_levels)
        bin_edges = []
        for i in range(6):
            bin_edges.append(contourLevels[int(((len(contourLevels) - 6) / 5 + 1) * i)])
        
        # Calculate histogram
        hist, _ = np.histogram(elevation_data, bins = bin_edges)
        
        # Write bins and hist to a CSV file
        with open(output_folder_t / f'{city_name_l}_elevation.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Bin', 'Count'])
            for i, count in enumerate(hist):
                bin_range = f"{int(bin_edges[i])}-{int(bin_edges[i+1])}"
                writer.writerow([bin_range, count])
    except:
        print('calculate elevation stats failed')