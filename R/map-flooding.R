plot_flooding <- function(flood_type) {
  file <- fuzzy_read(spatial_dir, glue("{flood_type}_2020.tif$"), paste)
  if (is.na(file)) return(NULL)
  flood_data <- terra::crop(rast(file), vect(static_map_bounds))
  # Temporary fix for if layer is all NAs
  if (all(is.na(values(flood_data)))) values(flood_data)[1] <- 0
  plots[[flood_type]] <<- plot_layer(
    flood_data, yaml_key = flood_type,
    plot_aoi = T, plot_wards = !is.null(wards))
  if (!is.null(plots$population)) plots[[glue("{flood_type}_population")]] <<-
    plot_layer(flood_data, yaml_key = flood_type, baseplot = plots$population)
  if (!is.null(plots$wsf)) plots[[glue("{flood_type}_wsf")]] <<-
    plot_layer(flood_data, yaml_key = flood_type, baseplot = plots$wsf)
  if (!is.null(plots$infrastructure)) plots[[glue("{flood_type}_infrastructure")]] <<-
    plot_layer(flood_data, yaml_key = flood_type, baseplot = plots$infrastructure)
}

flooding_yaml_keys <- c("fluvial", "pluvial", "coastal", "combined_flooding")
walk(flooding_yaml_keys, plot_flooding)
