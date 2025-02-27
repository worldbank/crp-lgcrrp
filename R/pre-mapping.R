# pre-mapping.R

# Combine infrastructure base points
combine_infrastructure_points <- function() {
  health_points <- fuzzy_read(spatial_dir, "osm_health(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "Hospital or clinic") %>% tryCatch(error = \(e) {return(NULL)})
  school_points <- fuzzy_read(spatial_dir, "osm_schools(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "School") %>% tryCatch(error = \(e) {return(NULL)})
  fire_points <- fuzzy_read(spatial_dir, "osm_fire(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "Fire station") %>% tryCatch(error = \(e) {return(NULL)})
  police_points <- fuzzy_read(spatial_dir, "osm_police(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "Police station") %>% tryCatch(error = \(e) {return(NULL)})
  rbind_if_non_null <- \(...) Reduce(rbind, unlist(list(...)))
  infrastructure_points <- rbind_if_non_null(health_points, school_points, fire_points, police_points)
  if (!is.null(infrastructure_points)) writeVector(select(infrastructure_points, !contains("fid")), filename = file.path(spatial_dir, "infrastructure.gpkg"), overwrite = T)
}
combine_infrastructure_points()

combine_flood_types <- function() {
  flood_files <- str_subset(list.files(spatial_dir, full.names = T), "(fluvial|pluvial|coastal)_2020.tif$")
  if (length(flood_files) > 0) {
    combined_flooding <- flood_files %>%
      lapply(rast) %>% 
      reduce(\(x, y) max(x, resample(y, x), na.rm = T))    
    writeRaster(combined_flooding, filename = file.path(spatial_dir, paste0(city, "_combined_flooding_2020.tif")), overwrite = T)
  }
}
combine_flood_types()

# Road network centrality
assign_road_types <- function() {
  roads <- fuzzy_read(spatial_dir, "edges(?=.shp$|.gpkg$|$)", layer = "edges")
  if (inherits(roads, "SpatVector")) {
    roads <- roads %>%
      mutate(
        primary = highway %in% c("motorway", "trunk", "primary"),
        road_type = case_when(primary ~ "Primary", T ~ "Secondary"),
        edge_centrality = edge_centrality * 100) %>%
      select(edge_centrality, road_type)
    writeVector(roads, filename = file.path(spatial_dir, "edges-edit.gpkg"), overwrite = T)
  }
}
assign_road_types()

# Combine school zones
combine_school_zones <- function() {
  schools_800 <- fuzzy_read(spatial_dir, "schools_800m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  schools_1600 <- fuzzy_read(spatial_dir, "schools_1600m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  schools_2400 <- fuzzy_read(spatial_dir, "schools_2400m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  schools_2400_only <- if (inherits(schools_2400, "SpatVector") & inherits(schools_1600, "SpatVector")) erase(schools_2400, schools_1600) else NULL
  schools_1600_only <- if (inherits(schools_1600, "SpatVector") & inherits(schools_800, "SpatVector")) erase(schools_1600, schools_800) else NULL
  school_layers <- c(schools_800, schools_1600_only, schools_2400_only)
  if (!is.na(school_layers)) {
    school_zones <- reduce(school_layers, rbind) %>%
      select(-level_1, -nodez) %>%
      select(!contains("fid"))
    writeVector(school_zones, filename = file.path(spatial_dir, "school-journeys.gpkg"), overwrite = T)
  }
}
combine_school_zones()
rename_school_points <- function() {
  school_points <- fuzzy_read(spatial_dir, "schools(?=.shp$|.gpkg$|$)", FUN = vect)
  if (inherits(school_points, "SpatVector")) {
    school_points <- school_points %>%
    # rename(School = amenity)
    mutate(Feature = "School") %>%
    select(!contains("fid"))
  writeVector(school_points, filename = file.path(spatial_dir, "school-points.gpkg"), overwrite = T)
  }
}
rename_school_points()

combine_health_zones <- function() {
  health_1000 <- fuzzy_read(spatial_dir, "health_1000m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  health_2000 <- fuzzy_read(spatial_dir, "health_2000m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  health_3000 <- fuzzy_read(spatial_dir, "health_3000m(?=.shp$|.gpkg$|$)", FUN = vect) %>% tryCatch(error = \(e) {return(NULL)})
  health_3000_only <- if (inherits(health_3000, "SpatVector") & inherits(health_2000, "SpatVector")) erase(health_3000, health_2000) else NULL
  health_2000_only <- if (inherits(health_2000, "SpatVector") & inherits(health_1000, "SpatVector")) erase(health_2000, health_1000) else NULL
  health_layers <- c(health_1000, health_2000_only, health_3000_only)
  if (!is.na(health_layers)) {
    health_zones <- reduce(health_layers, rbind) %>%
      select(-level_1, -nodez) %>%
      select(!contains("fid"))
    writeVector(health_zones, filename = file.path(spatial_dir, "health-journeys.gpkg"), overwrite = T)
  }
}
combine_health_zones()
rename_health_points <- function() {
  health_points <- fuzzy_read(spatial_dir, "health(?=.shp$|.gpkg$|$)", FUN = vect)
  if (inherits(health_points, "SpatVector")) {
    health_points <- health_points %>%
    # rename(`Health Facility` = amenity)
    mutate(Feature = "Health facility") %>%
    select(!contains("fid"))
  writeVector(health_points, filename = file.path(spatial_dir, "health-points.gpkg"), overwrite = T)
  }
}
rename_health_points()

wsf <- fuzzy_read(spatial_dir, "wsf_evolution.tif$")
if (inherits(wsf, "SpatRaster")) {
  # # Projecting to 3857 causes problems for leaflet; necessary for ggplot2?
  # wsf_new <- project(wsf, "epsg:3857")
  wsf_new <- wsf
  # Using <- NA changes the datatype to unsigned, which ultimately results
  # in huge values when wsf is re-projected in maps-static.R
  # values(wsf_new)[values(wsf_new) == 0] <- NA
  classify(wsf_new, cbind(0, NA))
  NAflag(wsf_new) <- NA
  writeRaster(wsf_new, file.path(spatial_dir, "wsf-edit.tif"), overwrite = T)
}

wsf_tracker <- fuzzy_read(spatial_dir, "wsf_tracker_utm.tif$")
if (inherits(wsf_tracker, "SpatRaster")) {
  # # Projecting to 3857 causes problems for leaflet; necessary for ggplot2?
  # wsf_tracker_new <- project(wsf_tracker, "epsg:3857")
  wsf_tracker_new <- wsf_tracker
  wsf_tracker_new <- 2016 + wsf_tracker_new/2
  # values(wsf_tracker_new)[values(wsf_tracker_new) == 0] <- NA
  # NAflag(wsf_tracker_new) <- NA
  writeRaster(wsf_tracker_new, file.path(spatial_dir, "wsf-tracker-edit.tif"), overwrite = T)
}

burn <- fuzzy_read(spatial_dir, "lc_burn.tif$")
if (inherits(burn, "SpatRaster")) {
  values(burn)[values(burn) < 0] <- NaN
  writeRaster(burn, file.path(spatial_dir, "burn-edit.tif"), overwrite = T)
}

intersection_nodes <- fuzzy_read(spatial_dir, "nodes_and_edges(?=.shp$|.gpkg$|$)", layer = "nodes")
if (inherits(intersection_nodes, "SpatVector")) {
  intersection_density <- density_rast(intersection_nodes, n = 200)
  writeRaster(intersection_density, file.path(spatial_dir, "intersection-density.tif"), overwrite = T)
}

historical_fire_data <- fuzzy_read(spatial_dir, "globfire")
if (inherits(historical_fire_data, c("SpatVector", "SpatRaster")) && length(historical_fire_data) > 0) {
  historical_fire_density <- density_rast(historical_fire_data, n = 200, aoi = aoi)
  writeRaster(historical_fire_density, file.path(spatial_dir, "burnt-area-density.tif"), overwrite = T)
}
