CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
TARGET = ajazz_daemon
CTL = ajazzctl
COMMON = src/protocol.c src/hidraw.c
HEADERS = src/protocol.h src/hidraw.h

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/share/man
DATADIR ?= $(PREFIX)/share
APPDIR = $(DATADIR)/aj179-linux/gui
USERUNITDIR ?= $(PREFIX)/lib/systemd/user
SYSTEMD_DIR ?= /etc/systemd/system
SYSCONFDIR ?= /etc
UDEV_DIR ?= /etc/udev/rules.d

all: $(TARGET) $(CTL)

$(TARGET): src/ajazz_daemon.c $(COMMON) $(HEADERS)
	$(CC) $(CFLAGS) $(LDFLAGS) src/ajazz_daemon.c $(COMMON) -o $@ $(LDLIBS)

$(CTL): src/ajazzctl.c $(COMMON) $(HEADERS)
	$(CC) $(CFLAGS) $(LDFLAGS) src/ajazzctl.c $(COMMON) -o $@ $(LDLIBS)

install: $(TARGET) $(CTL)
	install -D -m 755 $(TARGET) $(DESTDIR)$(BINDIR)/$(TARGET)
	install -D -m 755 $(CTL) $(DESTDIR)$(BINDIR)/$(CTL)
	install -D -m 644 docs/ajazzctl.1 $(DESTDIR)$(MANDIR)/man1/ajazzctl.1
	install -D -m 644 packaging/ajazz-mouse.service $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	install -D -m 644 packaging/ajazz-battery.conf $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	install -D -m 644 packaging/70-ajazz.rules $(DESTDIR)$(UDEV_DIR)/70-ajazz.rules
	# uaccess tags only work before 73-seat-late.rules; drop the old name
	rm -f $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules
	# the desktop app: plain Python, run on the distro's PyQt6
	install -d $(DESTDIR)$(APPDIR)/icons
	install -m 644 $(wildcard gui/*.py) $(DESTDIR)$(APPDIR)/
	install -m 644 gui/icons/*.svg $(DESTDIR)$(APPDIR)/icons/
	printf '#!/bin/sh\nexec python3 %s/ajazz_gui.py "$$@"\n' '$(APPDIR)' > $(DESTDIR)$(BINDIR)/aj179
	chmod 755 $(DESTDIR)$(BINDIR)/aj179
	# the low-battery notification, a per-user service
	printf '#!/bin/sh\nexec python3 %s/alert.py "$$@"\n' '$(APPDIR)' > $(DESTDIR)$(BINDIR)/aj179-battery-alert
	chmod 755 $(DESTDIR)$(BINDIR)/aj179-battery-alert
	install -d $(DESTDIR)$(USERUNITDIR)
	sed 's|@BINDIR@|$(BINDIR)|' packaging/aj179-battery-alert.service > $(DESTDIR)$(USERUNITDIR)/aj179-battery-alert.service
	install -D -m 644 packaging/aj179.desktop $(DESTDIR)$(DATADIR)/applications/aj179.desktop
	install -D -m 644 gui/icons/aj179.svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/aj179.svg

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)
	rm -f $(DESTDIR)$(BINDIR)/$(CTL)
	rm -f $(DESTDIR)$(MANDIR)/man1/ajazzctl.1
	rm -f $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	rm -f $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	rm -f $(DESTDIR)$(UDEV_DIR)/70-ajazz.rules $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules
	rm -f $(DESTDIR)$(BINDIR)/aj179 $(DESTDIR)$(DATADIR)/applications/aj179.desktop
	rm -f $(DESTDIR)$(BINDIR)/aj179-battery-alert $(DESTDIR)$(USERUNITDIR)/aj179-battery-alert.service
	rm -f $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/aj179.svg
	rm -rf $(DESTDIR)$(DATADIR)/aj179-linux

test: tests/test_protocol tests/test_hidraw
	./tests/test_protocol
	./tests/test_hidraw

tests/test_protocol: tests/test_protocol.c src/protocol.c src/protocol.h
	$(CC) $(CFLAGS) tests/test_protocol.c src/protocol.c -o $@

tests/test_hidraw: tests/test_hidraw.c src/hidraw.c src/hidraw.h src/protocol.c src/protocol.h
	$(CC) $(CFLAGS) tests/test_hidraw.c src/hidraw.c src/protocol.c -o $@

clean:
	rm -f $(TARGET) $(CTL) tests/test_protocol tests/test_hidraw

.PHONY: all install uninstall clean test
