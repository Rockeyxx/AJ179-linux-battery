#ifndef AJZ_HIDRAW_H
#define AJZ_HIDRAW_H

#include <stddef.h>
#include <stdint.h>

#include "protocol.h"

// Finds the hidraw node of the receiver's vendor interface (USB interface 2)
// and stores "/dev/hidrawN" in path. sysfs is normally "/sys".
int ajz_find_hidraw(const char *sysfs, uint16_t vid, uint16_t pid, char *path,
                    size_t size);

// Finds the mouse: its USB cable connection if plugged in (sets *wired = 1),
// otherwise the receiver with the given ids.
int ajz_find_mouse(const char *sysfs, uint16_t vid, uint16_t pid, char *path,
                   size_t size, int *wired);

// Sends one request and waits for the reply that echoes its command. Returns
// the reply's status byte (0 = OK, 2 = mouse asleep) or -1 if none arrived.
int ajz_transact(int fd, const uint8_t req[AJZ_REPORT_LEN],
                 uint8_t reply[AJZ_REPORT_LEN]);

#endif
