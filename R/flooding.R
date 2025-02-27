# Plotting flooding time series line chart
flood_exposure <- fuzzy_read(tabular_dir, "flood_exposure", read_csv)
if (inherits(flood_exposure, "data.frame")) {
  flood_types <- c("fluvial", "pluvial", "coastal", "combined")
  flood_exposure <- flood_exposure %>% 
    select(-ends_with("pct")) %>%
    pivot_longer(cols = any_of(c("fluvial", "pluvial", "coastal", "combined")), names_to = "type", values_to = "area")

  plot_flood_exposure <- function(flood_type) {
    if (flood_type %ni% c("fluvial", "pluvial", "coastal", "combined")) stop(paste("Flood type must be one of", paste(flood_types, collapse = ", "), "not", flood_type))
    if (flood_type != "combined") flood_exposure <- flood_exposure %>% filter(type == flood_type)
    exposure_plot <- flood_exposure %>%
      ggplot(aes(x = year, y = area, color = type, linetype = type)) +
      geom_line(data = \(d) filter(d, type == "combined")) +
      geom_point(data = \(d) filter(d, type != "combined")) +
      scale_x_continuous(
        expand = expansion(c(0,.05)),
        breaks = seq(1985, 2020, 5),
        minor_breaks = seq(1985, 2021, 1)) + 
      scale_y_continuous(labels = scales::comma, limits = c(0, NA), expand = expansion(c(0, 0.05))) +
      scale_color_manual(values = c(fluvial = "#F8766D", pluvial = "#619CFF", coastal = "#00BA38", combined = "black")) +
      scale_linetype_manual(values = c(fluvial = "dashed", pluvial = "dashed", coastal = "dashed", combined = "solid")) +
      scale_size_manual(values = c(fluvial = .5, pluvial = .5, coastal = .5, combined = 0.5)) +
      theme_minimal() +
      labs(
        title = paste0("Exposure of ", city, "'s built-up area to ", flood_type, " flooding"),
        x = "Year",
        y = bquote('Exposed'~km^2),
        color = "Flood type", linetype = "Flood type") +
      theme(
        axis.line = element_line(linewidth = .5, color = "black"),
        axis.title.x = element_blank(),
        legend.position = if (flood_type == "combined") "bottom" else "none",
        plot.background = element_rect(color = NA, fill = "white"))
    ggsave(file.path(charts_dir, paste0("wsf-", flood_type, "-plot.png")), plot = exposure_plot, device = "png",
            width = 6, height = 4, units = "in", dpi = "print")
  }

  plot_flood_exposure("fluvial")
  plot_flood_exposure("pluvial")
  plot_flood_exposure("coastal")
  plot_flood_exposure("combined")
}
