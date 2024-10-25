# Generating LGCRRP Maps

source("R/setup.R")
source("R/pre-mapping.R")

# Set static map visualization parameters
layer_alpha <- 0.7
map_width <- 6.9
map_height <- 5.9
aspect_ratio <- map_width / map_height

# Define map extent and zoom level
static_map_bounds <- aspect_buffer(aoi, aspect_ratio, buffer_percent = 0.05)
zoom <- round(14.6 + -0.00015 * (sqrt(expanse(aoi)))) + 1
tiles <- annotation_map_tile(type = "cartolight", zoom = zoom, progress = "none")

# Initiate plots list ----------------------------------------------------------
plots <- list()

# Plot AOI & wards -------------------------------------------------------------
if(is.null(wards)) {
  plots$aoi <- plot_layer(aoi_only = T, plot_aoi = T)
} else {
  ward_labels <- site_labels(wards, simplify = F)
  plots$aoi <- plot_layer(aoi_only = T, plot_aoi = F, plot_wards = T) +
    # geom_spatvector_text(data = wards, aes(label = as.numeric(str_extract(WARD_NO, "\\d*$"))))
    geom_spatvector_text(data = ward_labels, aes(label = WARD_NO), size = 2, fontface = "bold")
  save_plot(plot = plots$aoi, filename = "aoi.png",
            directory = styled_maps_dir)
}

# Plot landmarks ---------------------------------------------------------------
landmarks <- fuzzy_read(user_input_dir, "Landmark")
if (inherits(landmarks, "SpatVector")) {
  landmarks <- landmarks %>% project("epsg:4326") %>% select(Name)
  landmarks_df <- mutate(landmarks, x = geom(landmarks)[,"x"], y = geom(landmarks)[,"y"])

  # Combine landmark labels, ward labels, and ward lines, to reduce text overlaps
  landmarks_and_points_to_avoid <-
    rbind(
      mutate(landmarks, label = Name, type = "landmark", fface = "italic", fsize = 1.5),
      mutate(ward_labels, label = WARD_NO, type = "ward", fface = "bold", fsize = 2),
      mutate(as.points(wards) %>% .[rep(c(T, F, F), nrow(.))], label = "", type = "perimeter")
      ) %>%
    mutate(x = geom(.)[,"x"], y = geom(.)[,"y"])
  plots$landmarks <- plot_layer(aoi_only = T, plot_aoi = F, plot_wards = T) +
    geom_spatial_point(data = landmarks_df, crs = "epsg:4326", aes(x = x, y = y), size = 0.25) +
    geom_spatial_text_repel(data = landmarks_and_points_to_avoid, crs = "epsg:4326",
      aes(
        x = x, y = y, fontface = fface, size = fsize,
        label = break_lines(label, width = 12, newline = "\n")),
      segment.size = 0.1, box.padding = 0.1, min.segment.length = 0.2, max.time = 2,
      force_pull = 0.8, max.overlaps = 40,
      lineheight = 0.9) +
    scale_size(range = c(1.5, 2), guide = "none")
  save_plot(plot = plots$landmarks, filename = "landmarks.png",
            directory = styled_maps_dir)
}

# Standard plots ---------------------------------------------------------------
unlist(lapply(layer_params, \(x) x$fuzzy_string)) %>%
  # keep_at("land_cover") %>%
  map2(names(.), \(fuzzy_string, yaml_key) {
    tryCatch({
      data <- fuzzy_read(spatial_dir, fuzzy_string) %>% vectorize_if_coarse()
      plot <- plot_layer(
        data = data, yaml_key = yaml_key,
        plot_aoi = is.null(wards), plot_wards = !is.null(wards))
      plots[[yaml_key]] <<- plot
      message(paste("Success:", yaml_key))
    },
    error = \(e) {
      warning(glue("Error on {yaml_key}: {e}"))
    })
  }) %>% unlist() -> plot_log

# Non-standard plots -----------------------------------------------------------
# source("R/map-elevation.R")
# source("R/map-deforestation.R")
source("R/map-flooding.R")
# source("R/map-historical-burnt-area.R")

# Save plots -------------------------------------------------------------------
plots %>% walk2(names(.), \(plot, name) {
  save_plot(plot, filename = glue("{name}.png"), directory = styled_maps_dir)
})

# See which layers weren't successfully mapped
unmapped <- setdiff(c(names(layer_params), "aoi", "forest_deforest", "burnt_area"), names(plots))
if (length(unmapped) > 0) warning(paste(length(unmapped), "layers not mapped (not counting flood overlays):\n-", paste(unmapped, collapse = "\n- ")))
