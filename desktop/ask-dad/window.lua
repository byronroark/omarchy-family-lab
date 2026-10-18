-- Only the learner popup; parent approval panels have a different app ID.
-- Coordinates are relative to the monitor where this window opens.
o.window({ class = "^org[.]familylab[.]Help$" }, {
  float = true,
  move = { "(monitor_w-window_w-16)", "48" },
})
