# Packages ----

# Map Functions ----
fuzzy_read <- function(dir, fuzzy_string, FUN = NULL, path = T, convert_to_vect = F, ...) {
  file <- list.files(dir) %>% str_subset(fuzzy_string) #%>%
  if (length(file) > 1) warning(paste("Too many", fuzzy_string, "files in", dir))
  if (length(file) < 1) {
    file <- list.files(dir, recursive = T) %>% str_subset(fuzzy_string)
    if (length(file) > 1) warning(paste("Too many", fuzzy_string, "files in", dir))
    if (length(file) < 1) warning(paste("No", fuzzy_string, "file in", dir))
  }
  if (length(file) == 1) {
    if (is.null(FUN)) {
      FUN <- if (tolower(str_sub(file, -4, -1)) == ".tif") rast else vect
    }
    if (!path) {
      content <- suppressMessages(FUN(dir, file, ...))
    } else {
      file_path <- file.path(dir, file)
      content <- suppressMessages(FUN(file_path, ...))
    }
    if (convert_to_vect && class(content)[1] %in% c("SpatRaster", "RasterLayer")) {
      content <- rast_as_vect(content)
    }
    return(content)
  } else {
    return(NA)
  }
}

rast_as_vect <- function(x, digits = 8, ...) {
  if (class(x) == "SpatVector") return(x)
  if (is.character(x)) x <- rast(x, ...)
  out <- as.polygons(x, digits = digits)
  return(out)
}

exists_and_true <- \(x) !is.null(x) && is.logical(x) && x

# Functions for making the maps

prepare_parameters <- function(yaml_key, ...) {
  # Override the layers.yaml parameters with arguments provided to ...
  # Parameters include bins, breaks, center, color_scale, domain, labFormat, and palette
  layer_params <- read_yaml(layer_params_file)
  if (yaml_key %ni% names(layer_params)) stop(paste(yaml_key, "is not a key in", layer_params_file))
  yaml_params <- layer_params[[yaml_key]]
  new_params <- list(...)
  kept_params <- yaml_params[!names(yaml_params) %in% names(new_params)]
  params <- c(new_params, kept_params)

  params$breaks <- unlist(params$breaks) # Necessary for some color scales
  if (is.null(params$bins)) {
    params$bins <- if(is.null(params$breaks)) 0 else length(params$breaks)
  }
  if (is.null(params$stroke)) params$stroke <- NA
  if (exists_and_true(params$factor) & is.null(params$breaks)) {
    params$breaks <- params$labels
  }

  # Apply layer transparency to palette
  params$palette <- sapply(params$palette, \(p) {
    # If palette has no alpha, add
    if (nchar(p) == 7 | substr(p, 1, 1) != "#") return(scales::alpha(p, layer_alpha))
    # If palette already has alpha, multiply
    if (nchar(p) == 9) {
      alpha_hex <- as.hexmode(substr(p, 8, 9))
      new_alpha_hex <- as.character(alpha_hex * layer_alpha)
      # At one point I used the following; what was I trying to solve for? This
      # could make colors with alpha < 1 more opaque than colors with alpha = 1
      # new_alpha_hex <- as.character(as.hexmode("ff") - (as.hexmode("ff") - alpha_hex) * layer_alpha)
      if (nchar(new_alpha_hex) == 1) new_alpha_hex <- paste0(0, new_alpha_hex)
      new_p <- paste0(substr(p, 1, 7), new_alpha_hex)
      return(new_p)
    }
    warning(paste("Palette value", p, "is not of length 6 or 8"))
  }, USE.NAMES = F)

  return(params)
}

plot_layer <- function(data, yaml_key, baseplot = NULL, plot_aoi = T, aoi_only = F, plot_wards = F, ...) {
  if (aoi_only) {
    layer <- NULL
  } else { 
    params <- prepare_parameters(yaml_key = yaml_key, ...)
    if (!is.null(params$data_variable)) data <- data[params$data_variable]
    if (exists_and_true(params$factor)) {
      data <- 
        set_layer_values(
          data = data,
          values = ordered(get_layer_values(data),
                          levels = params$breaks,
                          labels = params$labels))
      params$palette <- setNames(params$palette, params$labels)
    }
    if(params$bins > 0 && is.null(params$breaks)) {
      params$breaks <- break_pretty2(
        data = get_layer_values(data), n = params$bins + 1, FUN = signif,
        method = params$breaks_method %>% {if(is.null(.)) "quantile" else .})
    }
    geom <- create_geom(data, params)
    data_type <- type_data(data)
    scales <- list(
      fill_scale(data_type, params),
      color_scale(data_type, params),
      linewidth_scale(data_type, params)) %>%
      .[lengths(.) > 1]
    theme <- theme_legend(data, params)
    layer <- list(geom = geom, scale = scales, theme = theme)
  }

  baseplot <- if (is.null(baseplot)) {
    ggplot() +
      geom_spatvector(data = static_map_bounds, fill = NA, color = NA) +
      tiles 
  } else { baseplot + ggnewscale::new_scale_fill() }
  p <- baseplot +
    layer + 
    annotation_north_arrow(style = north_arrow_minimal, location = "br", height = unit(1, "cm")) +
    annotation_scale(style = "ticks", aes(unit_category = "metric", width_hint = 0.33), height = unit(0.25, "cm")) +        
    theme_custom()
  if (plot_aoi) p <- p + geom_spatvector(data = aoi, fill = NA, linetype = "solid", linewidth = .25)
  if (plot_wards) p <- p + geom_spatvector(data = wards, color = "grey30", fill = NA, linetype = "solid", linewidth = .25)
  p <- p + coord_3857_bounds()
  return(p)
}

type_data <- function(data) {
  data_class <- class(data)[1]
  if (data_class %ni% c("SpatVector", "SpatRaster")) {
    stop(glue("On {yaml_key} data is neither SpatVector or SpatRaster, but {data_class}"))
  }
  data_type <- if (data_class == "SpatRaster") "raster" else geomtype(data)
  if (data_type %ni% c("raster", "points", "lines", "polygons")) {
    stop(glue("On {yaml_key} data is not of type 'raster', 'points', 'lines', or 'polygons'"))
  }
  return(data_type)
}

create_geom <- function(data, params) {
  data_type <- type_data(data)
  layer_values <- get_layer_values(data)
  if (data_type == "points") {
    geom_spatvector(data = data, aes(color = layer_values), size = 1)
  } else if (data_type == "polygons") {
    geom_spatvector(data = data, aes(fill = layer_values), color = params$stroke)
  } else if (data_type == "lines") {
    stroke_variable <- if (length(params$stroke) > 1) params$stroke$variable else NULL
    weight_variable <- if (length(params$weight) > 1) params$weight$variable else NULL
    # I could use aes_list in a safer way
    # aes_list2 <- c(
    #   aes(color = .data[[stroke_variable]]))
    #   aes(linewidth = (.data[[weight_variable]])))
    aes_list <- aes(color = .data[[stroke_variable]], linewidth = (.data[[weight_variable]]))
    if (is.null(weight_variable)) aes_list <- aes_list[-2]
    if (is.null(stroke_variable)) aes_list <- aes_list[-1]
    geom_spatvector(data = data, aes_list)
  } else if (data_type == "raster") {
    geom_spatraster(data = data)
  }
}

fill_scale <- function(data_type, params) {
  # data_type <- if (data_type %ni% c("raster", "points", "lines", "polygons")) type_data(data_type))
  if (length(params$palette) == 0 | data_type %in% c("points", "line")) {
    NULL 
  } else if (exists_and_true(params$factor)) {
    # Switched to na.translate = F because na.value = "transparent" includes
    # NA in legend for forest. Haven't tried with non-raster.
    scale_fill_manual(
      values = params$palette,
      name = format_title(params$title, params$subtitle),
      na.translate = F,
      na.value = "transparent")
  } else if (params$bins == 0) {
    scale_fill_gradientn(
      colors = params$palette,
      limits = if (is.null(params$domain)) NULL else params$domain,
      rescaler = if (!is.null(params$center)) ~ scales::rescale_mid(.x, mid = params$center) else scales::rescale,
      na.value = "transparent",
      name = format_title(params$title, params$subtitle))
  } else if (params$bins > 0) {
    scale_fill_stepsn(
      colors = params$palette,
      # Length of labels is one less than breaks when we want a discrete legend
      breaks = if (is.null(params$breaks)) waiver() else if (diff(lengths(list(params$labels, params$breaks))) == 1) params$breaks[-1] else params$breaks,
      # breaks_midpoints() is important for getting the legend colors to match the specified colors
      values = if (is.null(params$breaks)) NULL else breaks_midpoints(params$breaks, rescaler = if (!is.null(params$center)) scales::rescale_mid else scales::rescale, mid = params$center),
      labels = if (is.null(params$labels)) waiver() else params$labels,
      limits = if (is.null(params$breaks)) NULL else range(params$breaks),
      rescaler = if (!is.null(params$center)) ~ scales::rescale_mid(.x, mid = params$center) else scales::rescale,
      na.value = "transparent",
      oob = scales::oob_squish,
      name = format_title(params$title, params$subtitle),
      guide = if (diff(lengths(list(params$labels, params$breaks))) == 1) "legend" else "colorsteps")
  }
}

color_scale <- function(data_type, params) {
  if (data_type == "points") {
    scale_color_manual(values = params$palette, name = format_title(params$title, params$subtitle))
  } else if (length(params$stroke) < 2 || is.null(params$stroke$palette)) {
    NULL
  } else {
    scale_color_stepsn(
      colors = params$stroke$palette,
      name = format_title(params$stroke$title, params$stroke$subtitle))
  }
}

linewidth_scale <- function(data_type, params) {
  if (length(params$weight) < 2 || is.null(params$weight$range)) {
    NULL
  } else if (params$weight$factor) {
    scale_linewidth_manual(
      name = format_title(params$weight$title, params$weight$subtitle),
      values = unlist(setNames(params$weight$palette, params$weight$labels)))
  } else {
    scale_linewidth(
      range = c(params$weight$range[[1]], params$weight$range[[2]]),
      name = format_title(params$weight$title, params$weight$subtitle))
  }
}

theme_legend <- function(data, params) {
  layer_values <- get_layer_values(data)
  is_legend_text <- function() {
    !is.null(params$labels) && is.character(params$labels) | is.character(layer_values)
  }
  legend_text_alignment <- if (is_legend_text()) 0 else 1

  legend_theme <- theme(
    legend.title = ggtext::element_markdown(),
    legend.text = element_text(hjust = legend_text_alignment))
  return(legend_theme)
}

theme_custom <- function(...) {
  theme(
  # legend.key = element_rect(fill = "#FAFAF8"),
  legend.justification = c("left", "bottom"),
  legend.box.margin = margin(0, 0, 0, 12, unit = "pt"),
  legend.margin = margin(4,0,4,0, unit = "pt"),
  axis.title = element_blank(),
  axis.text = element_blank(),
  axis.ticks = element_blank(),
  axis.ticks.length = unit(0, "pt"),
  plot.margin = margin(0,0,0,0),
  ...)
}

coord_3857_bounds <- function(..., expansion = 1) {
  bbox_3857 <- st_bbox(st_transform(static_map_bounds, crs = "epsg:3857"))
  coord_sf(
    crs = "epsg:3857",
    expand = F,
    xlim = bbox_3857[c(1,3)] %>% { (. - mean(.)) * expansion + mean(.)},
    ylim = bbox_3857[c(2,4)] %>% { (. - mean(.)) * expansion + mean(.)},
    ...)
}

save_plot <- function(plot = NULL, filename, directory, rel_widths = c(3, 1)) {
  # Saves plots with set legend widths
  plot_layout <- plot_grid(
      plot + theme(legend.position = "none"),
      # Before ggplot2 3.5 was get_legend(plot); still works but with warning;
      # there are now multiple guide-boxes
      get_plot_component(plot, "guide-box-right"),
      rel_widths = rel_widths,
      nrow = 1) +
    theme(plot.background = element_rect(fill = "white", colour = NA))
  cowplot::save_plot(
    plot = plot_layout,
    filename = file.path(directory, filename),
    base_height = map_height, base_width = sum(rel_widths)/rel_widths[1] * map_width)
}

get_layer_values <- function(data) {
  if (class(data)[1] %in% c("SpatRaster")) {
      values <- values(data)
    } else if (class(data)[1] %in% c("SpatVector")) {
      values <- pull(values(data))
    } else if (class(data)[1] == "sf") {
      values <- data$values
    } else stop("Data is not of class SpatRaster, SpatVector or sf")
  return(values)
}

set_layer_values <- function(data, values) {
  if (class(data)[1] %in% c("SpatRaster")) {
      values(data) <- values
    } else if (class(data)[1] %in% c("SpatVector")) {
      values(data)[[1]] <- values
    } else if (class(data)[1] == "sf") {
      data$values <- values
    } else stop("Data is not of class SpatRaster, SpatVector or sf")
  return(data)
}

breaks_midpoints <- \(breaks, rescaler = scales::rescale, ...) {
  scaled_breaks <- rescaler(breaks, ...)
  midpoints <- head(scaled_breaks, -1) + diff(scaled_breaks)/2
  midpoints[length(midpoints)] <- midpoints[length(midpoints)] + .Machine$double.eps
  return(midpoints)
}

aspect_buffer <- function(x, aspect_ratio, buffer_percent = 0) {
  # I should fully refactor to use terra
  if (class(x)[1] %in% "SpatVector") x <- st_zm(as_sf(x))
  bounds_proj <- st_transform(st_as_sfc(st_bbox(x)), crs = "EPSG:3857")
  center_proj <- st_coordinates(st_centroid(bounds_proj))

  long_distance <-max(c(
    st_distance(
      st_point(st_bbox(bounds_proj)[c("xmin", "ymin")]),
      st_point(st_bbox(bounds_proj)[c("xmax", "ymin")]))[1],
    st_distance(
      st_point(st_bbox(bounds_proj)[c("xmin", "ymax")]),
      st_point(st_bbox(bounds_proj)[c("xmax", "ymax")]))[1]))
  lat_distance <- max(c(
    st_distance(
      st_point(st_bbox(bounds_proj)[c("xmin", "ymin")]),
      st_point(st_bbox(bounds_proj)[c("xmin", "ymax")]))[1],
    st_distance(
      st_point(st_bbox(bounds_proj)[c("xmax", "ymin")]),
      st_point(st_bbox(bounds_proj)[c("xmax", "ymax")]))[1]))

  if (long_distance/lat_distance < aspect_ratio) long_distance <- lat_distance * aspect_ratio
  if (long_distance/lat_distance > aspect_ratio) lat_distance <- long_distance/aspect_ratio

  new_bounds_proj <-
  c(center_proj[,"X"] + (c(xmin = -1, xmax = 1) * long_distance/2 * (1 + buffer_percent)),
  center_proj[,"Y"] + (c(ymin = -1, ymax = 1) * lat_distance/2 * (1 + buffer_percent)))

  new_bounds <- st_bbox(new_bounds_proj, crs = "EPSG:3857") %>%
    st_as_sfc() %>%
    st_transform(crs = st_crs(x))

  return(new_bounds)
}

# Alternatively could be two separate functions: pretty_interval() and pretty_quantile()
break_pretty2 <- function(data, n = 6, method = "quantile", FUN = signif, 
                          digits = NULL, threshold = 1/(n-1)/4) {
  divisions <- seq(from = 0, to = 1, length.out = n)

  if (method == "quantile") breaks <- unname(stats::quantile(data, divisions, na.rm = T))
  if (method == "interval") breaks <- divisions *
    (max(data, na.rm = T) - min(data, na.rm = T)) +
    min(data, na.rm = T)

  if (is.null(digits)) {
    digits <- if (all.equal(FUN, signif)) 1 else if (all.equal(FUN, round)) 0
  }

  distribution <- ecdf(data)
  discrepancies <- 100
  while (any(abs(discrepancies) > threshold) & digits < 6) {
    if (all.equal(FUN, signif) == TRUE) {
      pretty_breaks <- FUN(breaks, digits = digits)
      if(all(is.na(str_extract(tail(pretty_breaks, -1), "\\.[^0]*$")))) pretty_breaks[1] <- floor(pretty_breaks[1])
    }
    if (all.equal(FUN, round) == TRUE) {
      pretty_breaks <- c(
        floor(breaks[1] * 10^digits) / 10^digits,
        FUN(tail(head(breaks, -1), -1), digits = digits),
        ceiling(tail(breaks, 1) * 10^digits) / 10^digits)
    }
    if (method == "quantile") discrepancies <- distribution(pretty_breaks) - divisions
    if (method == "interval") {
      discrepancies <- (pretty_breaks - breaks)/ifelse(breaks != 0, breaks, pretty_breaks)
      discrepancies[breaks == 0 & pretty_breaks == 0] <- 0
    }
    digits <- digits + 1
  }
  return(pretty_breaks)
}

break_lines <- function(x, width = 20, newline = "<br>") {
  str_replace_all(x, paste0("(.{", width, "}[^\\s]*)\\s"), paste0("\\1", newline))
}

format_title <- function(title, subtitle, width = 20) {
  title_broken <- break_lines(title, width = width, newline = "<br>")
  subtitle_broken <- break_lines(subtitle, width = width, newline = "<br>")
  formatted_title <- paste0(title_broken, "<br><br><br><em>", subtitle_broken, "</em><br>")
  return(formatted_title)
}

count_aoi_cells <- function(data, aoi) {
  aoi_area <- if ("sf" %in% class(aoi)) {
    units::drop_units(st_area(aoi))
  } else if ("SpatVector" %in% class(aoi)) {
    expanse(aoi)
  }
  cell_count <- (aoi_area / cellSize(data)[1,1])[[1]]
  return(cell_count)
}

vectorize_if_coarse <- function(data, threshold = 7000) {
  if (class(data)[1] %in% c("sf", "SpatVector")) return(data)
  cell_count <- count_aoi_cells(data, aoi)
  if (cell_count < threshold) data <- rast_as_vect(data)
  return(data)
}

aggregate_if_too_fine <- function(data, threshold = 1e5, fun = "modal") {
  if (class(data)[1] %in% c("sf", "SpatVector")) return(data)
  cell_count <- count_aoi_cells(data, aoi)
  if (cell_count > threshold) {
    factor <- round(sqrt(cell_count / threshold))
    if (factor > 1) data <- terra::aggregate(data, fact = factor, fun = fun)
  }
  return(data)
}

center_max_circle <- \(x, simplify = T, tolerance = 0.0001) {
  if (simplify) s <- simplifyGeom(x, tolerance = tolerance) else s <- x
  p <- as.points(s)
  v <- voronoi(p)
  vp <- as.points(v)
  vp <- vp[is.related(vp, s, "within")]
  # Using vp[which.max(nearest(vp, p)$distance)] is 60x slower
  vppd <- distance(vp, p)

  center <- vp[which.max(apply(vppd, 1, min))]
  radius <- vppd[which.max(apply(vppd, 1, min))]
  return(list(center = center, radius = radius))
}

site_labels <- function(x, simplify = T, tolerance = 0.0001) {
  sites <- list()
  for (i in 1:nrow(x)) {
    sites[i] <- center_max_circle(x[i], simplify = simplify, tolerance = tolerance)["center"]
  }
  label_sites <- Reduce(rbind, unlist(sites))
  return(label_sites)
}

`%ni%` <- Negate(`%in%`)

which_not <- function(v1, v2, swap = F, both = F) {
  if (both) {
    list(
      "In V1, not in V2" = v1[v1 %ni% v2],
      "In V2, not in V1" = v2[v2 %ni% v1]
    )
  } else
  if (swap) {
    v2[v2 %ni% v1]
  } else {
    v1[v1 %ni% v2]
  }
}

paste_and <- function(v) {
    if (length(v) == 1) {
    string <- paste(v)
  } else {
    # l[1:(length(l)-1)] %>% paste(collapse = ", ")
    paste(head(v, -1), collapse = ", ") %>%
    paste("and", tail(v, 1))
  }
}

duplicated2way <- duplicated_all <- function(x) {
  duplicated(x) | duplicated(x, fromLast = T)
}

tolatin <- function(x) stringi::stri_trans_general(x, id = "Latin-ASCII")

ggdonut <- function(data, category_column, quantities_column, colors, title) {
  data <- as.data.frame(data) # tibble does weird things with data frame, not fixing now
  data <- data[!is.na(data[,quantities_column]),]
  data <- data[data[,quantities_column] > 0,]
  # data <- data[rev(order(data[,quantities_column])),]
  data$decimal <- data[,quantities_column]/sum(data[,quantities_column], na.rm = T)
  data$max <- cumsum(data$decimal) 
  data$min <- lag(data$max)
  data$min[1] <- 0
  data$label <- paste(scales::label_percent(0.1)(data$decimal))
  data$label[data$decimal < .02] <- "" 
  data$label_position <- (data$max + data$min) / 2
  data[,category_column] <- factor(data[,category_column], levels = data[,category_column])
  breaks <- data[data[,"decimal"] > 0.2,] %>%
    { setNames(.$label_position, .[,category_column]) }

  donut_plot <- ggplot(data) +
    geom_rect(
      aes(xmin = .data[["min"]], xmax = .data[["max"]], fill = .data[[category_column]],
      ymin = 0, ymax = 1),
      color = "white") +
    geom_text(y = 0.5, aes(x = label_position, label = label)) +
    # theme_void() +
    # scale_x_continuous(guide = "none", name = NULL) +
    scale_y_continuous(guide = "none", name = NULL) +
    scale_fill_manual(values = colors) +
    scale_x_continuous(breaks = breaks, name = NULL) +
    coord_radial(expand = F, inner.radius = 0.3) +
    guides(theta = guide_axis_theta(angle = 0)) +
    labs(title = paste(city, title)) +
    theme(axis.ticks = element_blank())
  return(donut_plot)
}

generate_generic_paths <- function() {
    cmip6_paths <- paste0(
      "cmip6-x0.25/{codes}/ensemble-all-ssp", scenario_numbers,
      "/timeseries-{codes}-annual-mean_cmip6-x0.25_ensemble-all-ssp", scenario_numbers,
      "_timeseries-smooth_") %>%
    lapply(\(x) paste0(x, c("median", "p10", "p90"))) %>%
    unlist() %>%
    paste0("_2015-2100.nc")

  era5_paths <- "era5-x0.25/{codes}/era5-x0.25-historical/timeseries-{codes}-annual-mean_era5-x0.25_era5-x0.25-historical_timeseries_mean_1950-2022.nc"

  paths <- c(cmip6_paths, era5_paths)
  return(paths)
}

# Extract time series data
extract_ts <- \(file) {
    r <- rast(file)
    terra::extract(r, aoi, snap = "out", exact = T) %>%
      mutate(fraction = fraction/sum(fraction)) %>%
      mutate(across(-c(ID, fraction), \(x) fraction * x)) %>%
      summarize(across(-c(ID, fraction), \(x) sum(x))) %>%
      unlist() %>%
      { tibble(date = as.Date(names(r)), value = ., file = file) }
}

Mode <- \(x, na.rm = F) {
  if (na.rm) x <- na.omit(x)
  unique_values <- unique(x)
  unique_values[which.max(tabulate(match(x, unique_values)))]
}

theme_cckp_chart <- function(...) {
  theme(
    ...,
    legend.title = element_text(size = rel(0.7)), legend.text = element_text(size = rel(0.7)),
    plot.caption = element_text(color = "grey30", size = rel(0.7), hjust = 0),
    axis.line = element_line(color = "black"),
    plot.background = element_rect(color = NA, fill = "white")) 
}

annotation_height <- function(x, lower_limit = NULL) {
  if (is.null(lower_limit)) lower_limit <- min(x)
  .95*diff(range(x)) + lower_limit
}
