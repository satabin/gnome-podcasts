bin_SCRIPTS = gnome-podcasts

gnome-podcasts: gnome-podcasts.in
	@$(MKDIR_P) bin
	$(AM_V_GEN)$(SED)                       \
		-e s!\@localedir\@!$(localedir)!    \
		-e s!\@pkgdatadir\@!$(pkgdatadir)!    \
		-e s!\@datadir\@!$(datadir)!    \
		-e s!\@pythondir\@!$(pythondir)!    \
		-e s!\@PYTHON\@!$(PYTHON)!          \
		< $< > $@
	@chmod a+x $@

BUILD_SOURCES = $(bin_SCRIPTS)
EXTRA_DIST = gnome-podcasts.in

-include $(top_srcdir)/git.mk

