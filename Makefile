CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
LDFLAGS ?= -lusb-1.0
TARGET = ajazz_daemon
SRC = ajazz_daemon.c

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
SYSTEMD_DIR ?= /etc/systemd/system
SYSCONFDIR ?= /etc
UDEV_DIR ?= /etc/udev/rules.d

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

install: $(TARGET)
	install -D -m 755 $(TARGET) $(DESTDIR)$(BINDIR)/$(TARGET)
	install -D -m 644 ajazz-mouse.service $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	install -D -m 644 ajazz-battery.conf $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	install -D -m 644 99-ajazz.rules $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)
	rm -f $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service
	rm -f $(DESTDIR)$(SYSCONFDIR)/conf.d/ajazz-battery
	rm -f $(DESTDIR)$(UDEV_DIR)/99-ajazz.rules

clean:
	rm -f $(TARGET)

.PHONY: all install uninstall clean
