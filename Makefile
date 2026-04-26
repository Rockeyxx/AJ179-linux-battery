CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
LDFLAGS ?= -lusb-1.0
TARGET = ajazz_daemon
SRC = ajazz_daemon.c

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
SYSTEMD_DIR ?= /etc/systemd/system

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

install: $(TARGET)
	install -D -m 755 $(TARGET) $(DESTDIR)$(BINDIR)/$(TARGET)
	install -D -m 644 ajazz-mouse.service $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)
	rm -f $(DESTDIR)$(SYSTEMD_DIR)/ajazz-mouse.service

clean:
	rm -f $(TARGET)

.PHONY: all install uninstall clean
