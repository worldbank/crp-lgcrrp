tryCatch_named("elevation", {
  elevation_breaks <- fuzzy_read(process_output_dir, "elevation.csv", read_csv, col_types = "cd")$Bin %>%
    str_extract_all("\\d+") %>% unlist() %>% unique() %>% as.numeric()
  elevation_data <- fuzzy_read(spatial_dir, layer_params$elevation$fuzzy_string) %>%
          # aggregate_if_too_fine(threshold = 1e6, fun = \(x) Mode(x, na.rm = T)) %>%
          vectorize_if_coarse(threshold = 1e6)
  plots$elevation <- plot_layer(
    data = elevation_data, yaml_key = "elevation", breaks = elevation_breaks,
    plot_aoi = T, plot_wards = !is.null(wards))
})