# GNOME Podcasts

A podcast player and manager for GNOME, inspired by Music and News applications.

## Dependencies

Podcasts requires python3 to run.
It uses Gtk+3 and Tracker as its core technologies.
It also requires following python dependencies:
 - python3-feedparser
 - python3-schedule

## Tracker

Podcasts are handled by the application via a custom miner. It discovers all
`mfo:FeedChannel`s with keyword `podcast`.
