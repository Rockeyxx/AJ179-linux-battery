#define _GNU_SOURCE
#include "hidraw.h"

#include <dirent.h>
#include <limits.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define AJZ_INTERFACE ":1.2/"
// The vendor waits 50 x 30 ms, but relayed replies were seen after 1.55 s.
#define AJZ_REPLY_TRIES 100
#define AJZ_REPLY_WAIT_MS 30

static int has_hid_id(const char *uevent_path, uint16_t vid, uint16_t pid) {
  char want[64], line[256];
  int found = 0;
  FILE *f = fopen(uevent_path, "r");

  if (!f)
    return 0;
  snprintf(want, sizeof(want), "HID_ID=0003:0000%04X:0000%04X\n", vid, pid);
  while (!found && fgets(line, sizeof(line), f))
    found = strcmp(line, want) == 0;
  fclose(f);
  return found;
}

int ajz_find_hidraw(const char *sysfs, uint16_t vid, uint16_t pid, char *path,
                    size_t size) {
  char dir[PATH_MAX], entry[PATH_MAX], real[PATH_MAX];
  struct dirent *d;
  DIR *dp;
  int ret = -1;

  snprintf(dir, sizeof(dir), "%s/class/hidraw", sysfs);
  dp = opendir(dir);
  if (!dp)
    return -1;

  while (ret != 0 && (d = readdir(dp))) {
    if (strncmp(d->d_name, "hidraw", 6) != 0)
      continue;

    if (snprintf(entry, sizeof(entry), "%s/%s/device/uevent", dir,
                 d->d_name) >= (int)sizeof(entry) ||
        !has_hid_id(entry, vid, pid))
      continue;

    // The resolved device path ends in .../1-1:1.2/0003:VVVV:PPPP.NNNN
    if (snprintf(entry, sizeof(entry), "%s/%s/device", dir, d->d_name) >=
            (int)sizeof(entry) ||
        !realpath(entry, real) || !strstr(real, AJZ_INTERFACE))
      continue;

    snprintf(path, size, "/dev/%s", d->d_name);
    ret = 0;
  }

  closedir(dp);
  return ret;
}

int ajz_transact(int fd, const uint8_t req[AJZ_REPORT_LEN],
                 uint8_t reply[AJZ_REPORT_LEN]) {
  uint8_t out[AJZ_REPORT_LEN + 1] = {0}; // leading 0 = no report id
  uint8_t in[64];

  memcpy(&out[1], req, AJZ_REPORT_LEN);
  if (write(fd, out, sizeof(out)) != (ssize_t)sizeof(out))
    return -1;

  for (int i = 0; i < AJZ_REPLY_TRIES; i++) {
    struct pollfd p = {.fd = fd, .events = POLLIN};
    ssize_t n;

    if (poll(&p, 1, AJZ_REPLY_WAIT_MS) <= 0)
      continue;
    n = read(fd, in, sizeof(in));
    if (n < 0)
      return -1;
    // Replies echo the command; other reports (C0 status frames) are skipped.
    if (n >= AJZ_REPORT_LEN && in[0] == req[0]) {
      memcpy(reply, in, AJZ_REPORT_LEN);
      return in[1];
    }
  }
  return -1;
}
