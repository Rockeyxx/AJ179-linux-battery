#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "hidraw.h"
#include "protocol.h"

#ifndef OUTPUT_FILE
#define OUTPUT_FILE "/tmp/ajazz_battery"
#endif
#define RETRY_SECONDS 2
#define CHECK_SECONDS 30 // look for a plugged / pulled cable; refresh while wired

int running = 1;
uint16_t vendor_id = 0x249a;
uint16_t product_id = 0x5c2f;

// --- PROTOTYPES ---
void report_battery(int fd);
void watch_mouse(int fd, const char *path, int wired);
void write_status(int bat_level, const char *class_name);

void handle_sig(int sig) {
  (void)sig;
  running = 0;
}

int main(int argc, char *argv[]) {
  signal(SIGINT, handle_sig);
  signal(SIGTERM, handle_sig);

  char path[64];

  if (argc >= 3) {
    vendor_id = (uint16_t)strtol(argv[1], NULL, 16);
    product_id = (uint16_t)strtol(argv[2], NULL, 16);
  } else {
    printf("No IDs provided, defaulting to Vendor: %04x, Product: %04x\n", vendor_id, product_id);
  }

  // Start with blank status
  write_status(-1, "disconnected");

  while (running) {
    int fd = -1, wired;

    if (ajz_find_mouse("/sys", vendor_id, product_id, path, sizeof(path), &wired) == 0)
      fd = open(path, O_RDWR);

    if (fd >= 0) {
      watch_mouse(fd, path, wired);
      close(fd);
      write_status(-1, "disconnected");
    }

    if (running)
      sleep(RETRY_SECONDS);
  }

  return 0;
}

// Asks for the battery level (get-info) and writes it if there is one.
void report_battery(int fd) {
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  struct ajz_info info;
  int bat;

  ajz_build(req, AJZ_CMD_INFO, 0, 0, NULL, 0);
  if (ajz_transact(fd, req, reply) != 0 || ajz_parse_info(reply, &info) != 0)
    return;
  bat = ajz_info_battery(&info);
  if (bat >= 0)
    write_status(bat, info.charging ? "charging" : "mouse");
}

// Reads the battery, then listens to the status frames the mouse pushes until
// its node goes away. While wired the battery is re-read every CHECK_SECONDS,
// and a cable being plugged in or pulled makes us switch nodes. The kernel
// driver stays bound throughout.
void watch_mouse(int fd, const char *path, int wired) {
  uint8_t frame[64];
  int online, bat;
  time_t next_check = time(NULL) + CHECK_SECONDS;

  report_battery(fd);

  while (running) {
    struct pollfd p = {.fd = fd, .events = POLLIN};
    int r = poll(&p, 1, 1000 * CHECK_SECONDS);
    ssize_t n;

    if (r < 0 && errno == EINTR)
      continue;
    if (r < 0 || (p.revents & (POLLERR | POLLHUP | POLLNVAL)))
      return;

    if (time(NULL) >= next_check) {
      char now[64];
      int now_wired;

      if (ajz_find_mouse("/sys", vendor_id, product_id, now, sizeof(now), &now_wired) != 0 ||
          strcmp(now, path) != 0)
        return;
      if (wired)
        report_battery(fd);
      next_check = time(NULL) + CHECK_SECONDS;
    }
    if (r == 0)
      continue;

    n = read(fd, frame, sizeof(frame));
    if (n < 0)
      return;
    if (n < AJZ_REPORT_LEN || ajz_parse_status(frame, &online, &bat) != 0)
      continue;
    if (online && bat >= 0)
      write_status(bat, "mouse");
  }
}

// --- UTILS ---

void write_status(int bat_level, const char *class_name) {
  FILE *f = fopen(OUTPUT_FILE, "w");
  if (f) {
    int charging = strcmp(class_name, "charging") == 0;

    if (bat_level >= 0)
      fprintf(f,
              "{\"text\": \"🖱️ %s%d%%\", \"tooltip\": \"Ajazz Mouse%s\", "
              "\"class\": \"%s\"}\n",
              charging ? "⚡" : "", bat_level, charging ? " (charging)" : "",
              class_name);
    else
      fprintf(f, "{\"text\": \"🖱️ ...\", \"tooltip\": \"Sleeping\", \"class\": "
                 "\"disconnected\"}\n");
    fclose(f);
  }
}
