#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "hidraw.h"
#include "protocol.h"

#define OUTPUT_FILE "/tmp/ajazz_battery"
#define RETRY_SECONDS 2

int running = 1;

// --- PROTOTYPES ---
int query_battery(int fd);
void watch_receiver(int fd);
void write_status(int bat_level, const char *class_name);

void handle_sig(int sig) {
  (void)sig;
  running = 0;
}

int main(int argc, char *argv[]) {
  signal(SIGINT, handle_sig);
  signal(SIGTERM, handle_sig);

  uint16_t vendor_id = 0x249a;
  uint16_t product_id = 0x5c2f;
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
    int fd = -1;

    if (ajz_find_hidraw("/sys", vendor_id, product_id, path, sizeof(path)) == 0)
      fd = open(path, O_RDWR);

    if (fd >= 0) {
      watch_receiver(fd);
      close(fd);
      write_status(-1, "disconnected");
    }

    if (running)
      sleep(RETRY_SECONDS);
  }

  return 0;
}

// Asks the receiver for the battery level; -1 if it has none to report.
int query_battery(int fd) {
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  struct ajz_info info;

  ajz_build(req, AJZ_CMD_INFO, 0, 0, NULL, 0);
  if (ajz_transact(fd, req, reply) != 0 || ajz_parse_info(reply, &info) != 0)
    return -1;
  return ajz_info_battery(&info);
}

// Reads the battery once, then listens to the status frames the mouse pushes
// until the receiver goes away. The kernel driver stays bound throughout.
void watch_receiver(int fd) {
  uint8_t frame[64];
  int online, bat;

  bat = query_battery(fd);
  if (bat >= 0)
    write_status(bat, "mouse");

  while (running) {
    struct pollfd p = {.fd = fd, .events = POLLIN};
    int r = poll(&p, 1, 5000);
    ssize_t n;

    if (r < 0 && errno == EINTR)
      continue;
    if (r < 0 || (p.revents & (POLLERR | POLLHUP | POLLNVAL)))
      return;
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
    if (bat_level >= 0)
      fprintf(f,
              "{\"text\": \"🖱️ %d%%\", \"tooltip\": \"Ajazz Mouse\", "
              "\"class\": \"%s\"}\n",
              bat_level, class_name);
    else
      fprintf(f, "{\"text\": \"🖱️ ...\", \"tooltip\": \"Sleeping\", \"class\": "
                 "\"disconnected\"}\n");
    fclose(f);
  }
}
