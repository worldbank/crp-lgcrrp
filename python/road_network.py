# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['road_network']:
    print('run road_network')
    
    import osmnx as ox
    import networkx as nx
    import pandas as pd
    import numpy as np
    from shapely.ops import unary_union
    import geopandas as gpd
    import os
    import matplotlib.pyplot as plt
    import pickle
    from pathlib import Path


    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    AOI_name = city_inputs['city_name']
    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Read AOI shapefile --------
    # transform the input gpkg to correct prj (epsg 4326)
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    features = aoi_file.geometry

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder_s = output_folder_parent / 'spatial'
    output_folder_t = output_folder_parent / 'tabular'
    output_folder_i = output_folder_parent / 'images'
    os.makedirs(output_folder_s, exist_ok=True)
    os.makedirs(output_folder_t, exist_ok=True)
    os.makedirs(output_folder_i, exist_ok=True)
    

    # FUNCTIONS ###################################
    def get_polygon():
        boundary_poly = aoi_file

        pol = [i for i in boundary_poly.geometry]
        boundary_poly = unary_union(pol)
            
        return boundary_poly

    def get_graph():
        print(f'Fetching graph data for {AOI_name}')
        
        poly = get_polygon()
        poly = poly.buffer(0)
        
        try:
            with open(output_folder_s / city_name_l, 'rb') as f:
                G = pickle.load(f)
            
            val = 1
        except FileNotFoundError:
            print("no pickle file found, retrieving new graph via OSMNX")
            G = ox.graph_from_polygon(poly, network_type = 'drive')
            val = 0

        print('Writing graph file')
        
        if val != 1:
            with open(output_folder_s / city_name_l, 'wb') as f:
                pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
        
        return G

    def get_centrality_stats():
        try:
            edges = gpd.read_file(output_folder_s / f"{city_name_l}_nodes_and_edges.gpkg", layer = 'edges')
            
            if 'edge_centr' in edges.columns:
                df = pd.DataFrame()
                df['edge_centr'] = edges.edge_centr.astype(float)
                df['edge_centr_avg'] = np.nansum(df.edge_centr.values)/len(df.edge_centr)
                df.to_csv(output_folder_t / f"{city_name_l}_road_network_extended_stats.csv")
        except FileNotFoundError:
            print("Edges file doesn't exist. Running edge_centrality function.")
            G = get_graph(G)
            extended_stats = ox.extended_stats(G, bc = True)
            dat = pd.DataFrame.from_dict(extended_stats)
            dat.to_csv(output_folder_t / f'{city_name_l}_road_network_extended_stats.csv')
        except Exception as e:
            print('Exception Occurred', e)

    def get_centrality(centrality_type = "both"):
        # centrality_type can be either node, edge, or both
        
        # download and project a street network
        G = get_graph()
        
        G = nx.DiGraph(G)
        
        if centrality_type == "node" or centrality_type == "both": 
            print('Getting node centrality')
            node_centrality = nx.betweenness_centrality(G)

            nx.set_node_attributes(G, node_centrality, 'node_centrality')
        
        if centrality_type == "edge" or centrality_type == "both": 
            print('Getting edge centrality')
            # edge closeness centrality: convert graph to a line graph so edges become nodes and vice versa
            edge_centrality = nx.edge_betweenness_centrality(G)

            new_edge_centrality = {}

            for u,v in edge_centrality:
                new_edge_centrality[(u,v)] = edge_centrality[u,v]
                
            nx.set_edge_attributes(G, new_edge_centrality, 'edge_centrality')
        
        print('Saving output gdf')
        
        G = nx.MultiDiGraph(G)
        graph_gpkg = output_folder_s / f'{city_name_l}_nodes_and_edges.gpkg'
        ox.save_graph_geopackage(G, filepath = graph_gpkg)
        
        print('Getting basic stats')
        
        basic_stats = ox.basic_stats(G)
        dat = pd.DataFrame.from_dict(basic_stats)
        dat.to_csv(output_folder_t / f'{city_name_l}_road_network_basic_stats.csv')
        
        get_centrality_stats()
        
        return

    def get_network_plots():
        G = get_graph()
        
        fig, ax = ox.plot_graph(G, bgcolor = '#ffffff', node_color = '#336699', node_zorder = 2, node_size = 5, show = False)
        
        fig.savefig(output_folder_i / f'{city_name_l}_network_plot.png', dpi = 300)
        
        return 

    def plot_radar():
        G = get_graph()
        
        try:
            if G.graph['crs'].is_projected:
                raise Exception("Graph seems to be projected, bearings will not generated if x and y are not in decimal degrees")
        except:
            print("graph seems to be unprojected, this is ok, continue")
            
        G = ox.add_edge_bearings(G)
        
        bearings = pd.Series([data.get('bearing', np.nan) for u, v, k, data in G.edges(keys=True, data=True)])
        
        # save bearings as csv
        bearings.to_csv(output_folder_t / f'{city_name_l}_road_bearings.csv')
        
        fig = plt.figure()  # an empty figure with no axes
        ax = fig.add_subplot(1, 1, 1, projection='polar')

        polar_plot(ax, bearings)
        
        fig.savefig(output_folder_i / f'{city_name_l}_road_radar_plot.png', dpi = 300)
        
        return

    def count_and_merge(n, bearings):
        # make twice as many bins as desired, then merge them in pairs
        # prevents bin-edge effects around common values like 0° and 90°
        n = n * 2
        bins = np.arange(n + 1) * 360 / n
        count, _ = np.histogram(bearings, bins=bins)
        
        # move the last bin to the front, so that 0° to 5° and 355° to 360° will be binned together
        count = np.roll(count, 1)
        return count[::2] + count[1::2]

    def polar_plot(ax, bearings, n = 36, title = ''):

        bins = np.arange(n + 1) * 360 / n

        count = count_and_merge(n, bearings)
        _, division = np.histogram(bearings, bins=bins)
        frequency = count / count.sum()
        division = division[0:-1]
        width = 2 * np.pi / n
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction('clockwise')

        x = division * np.pi / 180
        ax.bar(x, height=frequency, width=width, align='center', bottom=0, zorder=2,
               color='#003366', edgecolor='k', linewidth=0.5, alpha=0.7)

        ax.set_ylim(top=frequency.max())
        
        title_font = {'family':'DejaVu Sans', 'size':24, 'weight':'bold'}
        xtick_font = {'family':'DejaVu Sans', 'size':10, 'weight':'bold', 'alpha':1.0, 'zorder':3}
        ytick_font = {'family':'DejaVu Sans', 'size': 9, 'weight':'bold', 'alpha':0.2, 'zorder':3}
        
        ax.set_title(title.upper(), y=1.05, fontdict=title_font)
        
        ax.set_yticks(np.linspace(0, max(ax.get_ylim()), 5))
        yticklabels = ['{:.2f}'.format(y) for y in ax.get_yticks()]
        yticklabels[0] = ''
        ax.set_yticklabels(labels=yticklabels, fontdict=ytick_font)
        
        xticklabels = ['N', '', 'E', '', 'S', '', 'W', '']
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(labels=xticklabels, fontdict=xtick_font)
        ax.tick_params(axis='x', which='major', pad=-2)

    def main(centrality_type = "both"):
        # calculate either 'node' centrality, 'edge' centrality, or 'both'
        get_centrality(centrality_type = centrality_type)
        
        # plot the road network
        get_network_plots()
        
        # generate the road bearing polar plots
        plot_radar()
            

    # RUN ############################################
    main(centrality_type = "edge")
