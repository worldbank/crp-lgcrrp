# pre-mapping.R

# Combine infrastructure base points
combine_infrastructure_points <- function() {
  health_points <- fuzzy_read(spatial_dir, "osm_health(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "School") %>% tryCatch(error = \(e) {return(NULL)})
  school_points <- fuzzy_read(spatial_dir, "osm_schools(?=.shp$|.gpkg$|$)") %>% mutate(Feature = "Hospital or clinic") %>% tryCatch(error = \(e) {return(NULL)})
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
      reduce(\(x, y) max(x, y, na.rm = T))
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
tryCatch({
  schools_800 <- fuzzy_read(spatial_dir, "schools_800m(?=.shp$|.gpkg$|$)", FUN = vect)
  schools_1600 <- fuzzy_read(spatial_dir, "schools_1600m(?=.shp$|.gpkg$|$)", FUN = vect)
  schools_2400 <- fuzzy_read(spatial_dir, "schools_2400m(?=.shp$|.gpkg$|$)", FUN = vect)
  schools_2400_only <- erase(schools_2400, schools_1600)
  schools_1600_only <- erase(schools_1600, schools_800)
  school_zones <- reduce(c(schools_800, schools_1600_only, schools_2400_only), rbind) %>%
    select(-level_1, -nodez) %>%
    select(!contains("fid"))
  writeVector(school_zones, filename = file.path(spatial_dir, "school-journeys.gpkg"), overwrite = T)
}, error = \(e) warning(e))
tryCatch({
  school_points <- fuzzy_read(spatial_dir, "schools(?=.shp$|.gpkg$|$)", FUN = vect) %>%
    # rename(School = amenity)
    mutate(Feature = "School") %>%
    select(!contains("fid"))
  writeVector(school_points, filename = file.path(spatial_dir, "school-points.gpkg"), overwrite = T)
}, error = \(e) warning(e))

# Combine health zones
tryCatch({
  health_1000 <- fuzzy_read(spatial_dir, "health_1000m(?=.shp$|.gpkg$|$)", FUN = vect)
  health_2000 <- fuzzy_read(spatial_dir, "health_2000m(?=.shp$|.gpkg$|$)", FUN = vect)
  health_3000 <- fuzzy_read(spatial_dir, "health_3000m(?=.shp$|.gpkg$|$)", FUN = vect)
  health_3000_only <- erase(health_3000, health_2000)
  health_2000_only <- erase(health_2000, health_1000)
  health_zones <- reduce(c(health_1000, health_2000_only, health_3000_only), rbind) %>%
    select(-level_1, -nodez) %>%
    select(!contains("fid"))
  writeVector(health_zones, filename = file.path(spatial_dir, "health-journeys.gpkg"), overwrite = T)
}, error = \(e) warning(e))
tryCatch({
  health_points <- fuzzy_read(spatial_dir, "health(?=.shp$|.gpkg$|$)", FUN = vect) %>%
    # rename(`Health Facility` = amenity)
    mutate(Feature = "Health facility") %>%
    select(!contains("fid"))
  writeVector(health_points, filename = file.path(spatial_dir, "health-points.gpkg"), overwrite = T)
}, error = \(e) warning(e))