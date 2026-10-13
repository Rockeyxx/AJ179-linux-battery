#define _GNU_SOURCE
#include "../src/hidraw.h"
#include "../src/protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int failures = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      printf("FAIL %s:%d: %s\n", __func__, __LINE__, #cond);                   \
      failures++;                                                              \
    }                                                                          \
  } while (0)

static void sh(const char *fmt, const char *root) {
  char cmd[1024];
  snprintf(cmd, sizeof(cmd), fmt, root, root, root, root, root, root);
  if (system(cmd) != 0)
    printf("setup failed: %s\n", cmd);
}

// Mirrors the real receiver: mouse on :1.0, vendor channel on :1.2, plus an
// unrelated device that also sits on a :1.2 interface.
static void make_fake_sysfs(const char *root) {
  sh("d=%s/devices/usb1/1-1; "
     "mkdir -p $d/1-1:1.0/0003:249A:5C2F.0001 $d/1-1:1.2/0003:249A:5C2F.0003 "
     "%s/devices/usb1/1-2/1-2:1.2/0003:046D:C52B.0007 %s/class/hidraw; "
     "echo HID_ID=0003:0000249A:00005C2F > $d/1-1:1.0/0003:249A:5C2F.0001/uevent; "
     "echo HID_ID=0003:0000249A:00005C2F > $d/1-1:1.2/0003:249A:5C2F.0003/uevent; "
     "echo HID_ID=0003:0000046D:0000C52B > "
     "%s/devices/usb1/1-2/1-2:1.2/0003:046D:C52B.0007/uevent",
     root);
  sh("cd %s/class/hidraw && mkdir hidraw0 hidraw3 hidraw5 && "
     "ln -s ../../../devices/usb1/1-1/1-1:1.0/0003:249A:5C2F.0001 hidraw0/device && "
     "ln -s ../../../devices/usb1/1-1/1-1:1.2/0003:249A:5C2F.0003 hidraw3/device && "
     "ln -s ../../../devices/usb1/1-2/1-2:1.2/0003:046D:C52B.0007 hidraw5/device",
     root);
}

static void test_find_hidraw_picks_vendor_interface(void) {
  char root[] = "/tmp/ajz-sysfs-XXXXXX";
  char path[64] = "";

  CHECK(mkdtemp(root) != NULL);
  make_fake_sysfs(root);

  CHECK(ajz_find_hidraw(root, 0x249a, 0x5c2f, path, sizeof(path)) == 0);
  CHECK(strcmp(path, "/dev/hidraw3") == 0);

  sh("rm -rf %s", root);
}

static void test_find_hidraw_fails_for_absent_device(void) {
  char root[] = "/tmp/ajz-sysfs-XXXXXX";
  char path[64] = "";

  CHECK(mkdtemp(root) != NULL);
  make_fake_sysfs(root);

  CHECK(ajz_find_hidraw(root, 0x249a, 0x1234, path, sizeof(path)) == -1);

  sh("rm -rf %s", root);
}

// The receiver keeps pushing C0 status frames; the reply is the first report
// with data[1] == 0x00 (vendor rule, PROTOCOL.md "Framing").
static void test_transact_skips_status_frames_until_reply(void) {
  int sv[2];
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  uint8_t status[AJZ_REPORT_LEN] = {0xc0, 0x01, 77};
  uint8_t answer[AJZ_REPORT_LEN] = {0x10, 0x00, 0x00, 0x0b, 'M', '1', '7', '9'};
  uint8_t sent[64];

  CHECK(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv) == 0);
  CHECK(write(sv[1], status, sizeof(status)) == AJZ_REPORT_LEN);
  CHECK(write(sv[1], answer, sizeof(answer)) == AJZ_REPORT_LEN);

  ajz_build(req, AJZ_CMD_INFO, 0, 0, NULL, 0);
  CHECK(ajz_transact(sv[0], req, reply) == 0);
  CHECK(memcmp(reply, answer, AJZ_REPORT_LEN) == 0);

  // hidraw needs the report id (0) in front of the 32 data bytes.
  CHECK(read(sv[1], sent, sizeof(sent)) == AJZ_REPORT_LEN + 1);
  CHECK(sent[0] == 0x00);
  CHECK(memcmp(&sent[1], req, AJZ_REPORT_LEN) == 0);

  close(sv[0]);
  close(sv[1]);
}

// Live capture 2026-10-13: the receiver pushed "c0 00 51" (mouse fell asleep,
// 81 %) right after a request. Its byte 1 is 0 but it is not the reply; real
// replies echo the command in byte 0.
static void test_transact_ignores_sleep_frame(void) {
  int sv[2];
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  uint8_t sleep_frame[AJZ_REPORT_LEN] = {0xc0, 0x00, 0x51};
  uint8_t answer[AJZ_REPORT_LEN] = {0x10, 0x00, 0x01, 0x0b, 'M', '1', '7', '9'};

  CHECK(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv) == 0);
  CHECK(write(sv[1], sleep_frame, sizeof(sleep_frame)) == AJZ_REPORT_LEN);
  CHECK(write(sv[1], answer, sizeof(answer)) == AJZ_REPORT_LEN);

  ajz_build(req, AJZ_CMD_INFO, 0, 0, NULL, 0);
  CHECK(ajz_transact(sv[0], req, reply) == 0);
  CHECK(reply[0] == 0x10);

  close(sv[0]);
  close(sv[1]);
}

// Live capture: reading the report rate while the mouse sleeps returns
// "12 02 ff" at once. The status byte is passed back to the caller.
static void test_transact_returns_device_status(void) {
  int sv[2];
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  uint8_t answer[AJZ_REPORT_LEN] = {0x12, 0x02, 0xff};

  CHECK(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv) == 0);
  CHECK(write(sv[1], answer, sizeof(answer)) == AJZ_REPORT_LEN);

  ajz_build(req, 0x12, 0, 0, NULL, 0);
  CHECK(ajz_transact(sv[0], req, reply) == 0x02);

  close(sv[0]);
  close(sv[1]);
}

// Live capture: with the mouse idle, "12 01 00..." (no answer from the mouse)
// arrived 1.553 s after the request - later than the vendor's 1.5 s window.
static void test_transact_waits_for_slow_relay_status(void) {
  int sv[2];
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  uint8_t answer[AJZ_REPORT_LEN] = {0x12, 0x01};

  CHECK(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv) == 0);
  if (fork() == 0) {
    usleep(1600000);
    if (write(sv[1], answer, sizeof(answer)) != AJZ_REPORT_LEN)
      _exit(1);
    _exit(0);
  }

  ajz_build(req, 0x12, 0, 0, NULL, 0);
  CHECK(ajz_transact(sv[0], req, reply) == AJZ_STATUS_NO_ANSWER);
  wait(NULL);

  close(sv[0]);
  close(sv[1]);
}

static void test_transact_times_out_without_reply(void) {
  int sv[2];
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  uint8_t status[AJZ_REPORT_LEN] = {0xc0, 0x01, 77};

  CHECK(socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv) == 0);
  CHECK(write(sv[1], status, sizeof(status)) == AJZ_REPORT_LEN);

  ajz_build(req, AJZ_CMD_INFO, 0, 0, NULL, 0);
  CHECK(ajz_transact(sv[0], req, reply) == -1);

  close(sv[0]);
  close(sv[1]);
}

int main(void) {
  test_find_hidraw_picks_vendor_interface();
  test_find_hidraw_fails_for_absent_device();
  test_transact_skips_status_frames_until_reply();
  test_transact_times_out_without_reply();
  test_transact_ignores_sleep_frame();
  test_transact_returns_device_status();
  test_transact_waits_for_slow_relay_status();

  if (failures) {
    printf("%d check(s) failed\n", failures);
    return 1;
  }
  printf("all hidraw tests passed\n");
  return 0;
}
