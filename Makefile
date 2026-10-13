CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
TARGET = ajazz_daemon
CTL = ajazzctl
COMMON = src/protocol.c src/hidraw.c
HEADERS = src/protocol.h src/hidraw.h

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
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
	install -D -m 644 packaging/ajazz-mouse.service $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	install -D -m 644 packaging/ajazz-battery.conf $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	install -D -m 644 packaging/99-ajazz.rules $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)
	rm -f $(DESTDIR)$(BINDIR)/$(CTL)
	rm -f $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	rm -f $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	rm -f $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules

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
