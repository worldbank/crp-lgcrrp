# Plotting fire weather index seasonality line chart
fwi <- fuzzy_read(tabular_dir, "fwi.csv", read_csv)
if (inherits(fwi, "tibble")) {
  month_starts <- cumsum(c("Jan" = 31, "Feb" = 28, "Mar"= 31, "Apr" = 30, "May" = 31, "Jun" = 30,
    "Jul" = 31, "Aug" = 31, "Sep"= 30, "Oct" = 31, "Nov" = 30, "Dec" = 31)/7) - 31/7
  ggplot(fwi, aes(x = week - 1, y = pctile_95)) +
    geom_line() +
    scale_x_continuous(
      breaks = month_starts + 31/7/2, labels = names(month_starts),
      minor_breaks = month_starts, expand = c(0,0)) +
    scale_y_continuous(limits = c(0, NA), expand = expansion(c(0, .1))) +
    theme_minimal() +
    labs(
      title = paste("FWI in", city, "2016-2021"),
      y = "95th percentile FWI") +
    theme(
      axis.line = element_line(linewidth = .5, color = "black"),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_line(linewidth = .125, color = "dark gray"),
      axis.title.x = element_blank(),
      plot.background = element_rect(color = NA, fill = "white"))
  ggsave(
    file.path(charts_dir, "nasa-fwi.png"), device = "png",
    width = 4, height = 3.5, units = "in", dpi = "print")
}
