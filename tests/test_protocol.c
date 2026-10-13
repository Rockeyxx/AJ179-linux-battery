#include "../src/protocol.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      printf("FAIL %s:%d: %s\n", __func__, __LINE__, #cond);                   \
      failures++;                                                              \
    }                                                                          \
  } while (0)

// Captured from the Windows driver (old daemon "frame 111", payload after the
// USBPcap header): the get-info request is the command byte and 31 zeros.
static void test_read_request_is_command_then_zeros(void) {
  uint8_t f[AJZ_REPORT_LEN];
  uint8_t expected[AJZ_REPORT_LEN] = {0x10};

  memset(f, 0xAA, sizeof(f));
  ajz_build(f, AJZ_CMD_INFO, 0, 0, NULL, 0);

  CHECK(memcmp(f, expected, AJZ_REPORT_LEN) == 0);
}

// Checksum is the low byte of data[4..30]; the header bytes are not included.
static void test_checksum_sums_payload_only(void) {
  const uint8_t payload[] = {0x02, 0x42, 0x07, 0xff, 0x00, 0x00, 0x00, 0xff,
                             0x00, 0x00, 0x00, 0xff, 0x00, 0xff, 0xff, 0xff,
                             0xff, 0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff};
  uint8_t f[AJZ_REPORT_LEN];

  ajz_build(f, 0x05, 0x01, 0x18, payload, sizeof(payload));

  CHECK(f[0] == 0x05);
  CHECK(f[1] == 0x00);
  CHECK(f[2] == 0x01);
  CHECK(f[3] == 0x18);
  CHECK(memcmp(&f[4], payload, sizeof(payload)) == 0);
  CHECK(f[31] == 0x3f); // 3135 & 0xff
}

static void test_parse_info_reads_id_sensor_and_battery(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0x10, 0x00, 0x00, 0x0b, 'M',  '1',  '7', '9',
                               0x34, 0x12, 0x95, 0x10, 0x01, 57,   0x01};
  struct ajz_info info;

  CHECK(ajz_parse_info(r, &info) == 0);
  CHECK(strcmp(info.id, "M179") == 0);
  CHECK(info.sensor == 0x95);
  CHECK(info.rate_caps == 0x10);
  CHECK(info.charging == 1);
  CHECK(info.battery == 57);
  CHECK(info.connected == 1);
}

static void test_parse_info_rejects_error_status(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0x10, 0x01, 0x00, 0x0b, 'M', '1', '7', '9'};
  struct ajz_info info;

  CHECK(ajz_parse_info(r, &info) == -1);
}

// A status frame must not be mistaken for the info reply.
static void test_parse_info_rejects_non_ascii_id(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0xc0, 0x00, 0x00};
  struct ajz_info info;

  CHECK(ajz_parse_info(r, &info) == -1);
}

static void test_parse_status_online_frame(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0xc0, 0x01, 85};
  int online = -1, battery = -1;

  CHECK(ajz_parse_status(r, &online, &battery) == 0);
  CHECK(online == 1);
  CHECK(battery == 85);
}

static void test_parse_status_offline_frame(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0xc0, 0x00, 0x00};
  int online = -1, battery = -1;

  CHECK(ajz_parse_status(r, &online, &battery) == 0);
  CHECK(online == 0);
}

static void test_parse_status_rejects_impossible_battery(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0xc0, 0x01, 0xff};
  int online = -1, battery = 0;

  CHECK(ajz_parse_status(r, &online, &battery) == 0);
  CHECK(battery == -1);
}

static void test_parse_status_ignores_other_reports(void) {
  uint8_t r[AJZ_REPORT_LEN] = {0x10, 0x00};
  int online = -1, battery = -1;

  CHECK(ajz_parse_status(r, &online, &battery) == -1);
}

// Only reads decoded from the vendor's sync routine may be sent freely.
static void test_is_read_cmd_allows_only_known_reads(void) {
  const uint8_t reads[] = {0x10, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x20};
  const uint8_t others[] = {0x00, 0x02, 0x05, 0x09, 0x0d, 0x0e,
                            0x0f, 0x11, 0x18, 0xc0, 0xff};

  for (size_t i = 0; i < sizeof(reads); i++)
    CHECK(ajz_is_read_cmd(reads[i]));
  for (size_t i = 0; i < sizeof(others); i++)
    CHECK(!ajz_is_read_cmd(others[i]));
}

// Live replies (2026-10-13): awake ...51 01..., asleep ...52 00.... The vendor
// app shows byte 13 either way (0x4317ba runs before the byte-14 check).
static void test_info_battery_kept_while_mouse_sleeps(void) {
  struct ajz_info awake = {.battery = 81, .connected = 1};
  struct ajz_info asleep = {.battery = 82, .connected = 0};

  CHECK(ajz_info_battery(&awake) == 81);
  CHECK(ajz_info_battery(&asleep) == 82);
}

static void test_info_battery_unknown_when_never_reported(void) {
  struct ajz_info none = {.battery = 0, .connected = 0};
  struct ajz_info bogus = {.battery = 150, .connected = 1};

  CHECK(ajz_info_battery(&none) == -1);
  CHECK(ajz_info_battery(&bogus) == -1);
}

// sub_41e330 / sub_41e490. 0x95 is this mouse's PAW3395 (live info reply).
static void test_dpi_codec_paw3395(void) {
  CHECK(ajz_dpi_encode(0x95, 50) == 0);
  CHECK(ajz_dpi_encode(0x95, 800) == 15);
  CHECK(ajz_dpi_encode(0x95, 26000) == 519);
  CHECK(ajz_dpi_decode(0x95, 15) == 800);
  CHECK(ajz_dpi_decode(0x95, 519) == 26000);
}

static void test_dpi_codec_segmented_sensor(void) {
  CHECK(ajz_dpi_encode(0x11, 800) == 16);
  CHECK(ajz_dpi_encode(0x11, 10000) == 200);
  CHECK(ajz_dpi_encode(0x11, 13000) == 221);
  CHECK(ajz_dpi_decode(0x11, 16) == 800);
  CHECK(ajz_dpi_decode(0x11, 200) == 10000);
  CHECK(ajz_dpi_decode(0x11, 221) == 13000);
}

static void test_dpi_range_by_sensor(void) {
  int min, max;

  ajz_dpi_range(0x95, &min, &max);
  CHECK(min == 50 && max == 26000);
  ajz_dpi_range(0x26, &min, &max);
  CHECK(min == 200 && max == 10000);
}

// 0x434bcf: 03 00 01 25 <(index << 4) | count> then 6 x <lo hi lo hi>.
static void test_set_dpi_packet(void) {
  const int dpi[6] = {400, 800, 1200, 1600, 2400, 3200};
  const uint8_t expected[] = {0x03, 0x00, 0x01, 0x25, 0x16, 0x07, 0x00, 0x07,
                              0x00, 0x0f, 0x00, 0x0f, 0x00, 0x17, 0x00, 0x17,
                              0x00, 0x1f, 0x00, 0x1f, 0x00, 0x2f, 0x00, 0x2f,
                              0x00, 0x3f, 0x00, 0x3f, 0x00};
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_dpi(f, 0x95, 1, 6, dpi) == 0);
  CHECK(memcmp(f, expected, sizeof(expected)) == 0);
  CHECK(f[31] == ((0x16 + 2 * (7 + 15 + 23 + 31 + 47 + 63)) & 0xff));
}

static void test_set_dpi_clamps_to_sensor_range(void) {
  const int dpi[6] = {10, 800, 1200, 1600, 2400, 30000};
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_dpi(f, 0x95, 0, 6, dpi) == 0);
  CHECK(f[5] == 0 && f[6] == 0);                  // 10 -> 50
  CHECK(f[25] == (519 & 0xff) && f[26] == 519 >> 8); // 30000 -> 26000
}

static void test_set_dpi_rejects_bad_stage(void) {
  const int dpi[6] = {400, 800, 1200, 1600, 2400, 3200};
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_dpi(f, 0x95, 6, 6, dpi) == -1);
  CHECK(ajz_set_dpi(f, 0x95, 0, 7, dpi) == -1);
  CHECK(ajz_set_dpi(f, 0x95, 0, 0, dpi) == -1);
}

// Read reply mirrors the write payload (0x431984).
static void test_parse_dpi_reply(void) {
  const int dpi[6] = {400, 800, 1200, 1600, 2400, 3200};
  uint8_t r[AJZ_REPORT_LEN];
  int index, count, got[6];

  ajz_set_dpi(r, 0x95, 1, 6, dpi);
  r[0] = 0x13;
  CHECK(ajz_parse_dpi(r, 0x95, &index, &count, got) == 0);
  CHECK(index == 1 && count == 6);
  CHECK(memcmp(got, dpi, sizeof(dpi)) == 0);
}

// List builder 0x41d989: the rate value is a bit flag.
static void test_report_rate_flags(void) {
  CHECK(ajz_rate_flag(125) == 0x08);
  CHECK(ajz_rate_flag(250) == 0x04);
  CHECK(ajz_rate_flag(500) == 0x02);
  CHECK(ajz_rate_flag(1000) == 0x01);
  CHECK(ajz_rate_flag(300) == -1);
  CHECK(ajz_rate_hz(0x01) == 1000);
  CHECK(ajz_rate_hz(0x08) == 125);
  CHECK(ajz_rate_hz(0x03) == -1);
}

static void test_set_rate_packet(void) {
  const uint8_t expected[] = {0x02, 0x00, 0x01, 0x01, 0x08};
  uint8_t f[AJZ_REPORT_LEN];

  ajz_set_rate(f, 0x08);
  CHECK(memcmp(f, expected, sizeof(expected)) == 0);
  CHECK(f[31] == 0x08);
}

// 0x434690. Off / constant / breathing are the modes the AJ179 enables.
static void test_set_lighting_packets(void) {
  const uint8_t red[3] = {0xff, 0x00, 0x00};
  const uint8_t off[] = {0x05, 0x00, 0x01, 0x02, 0x00, 0x42};
  const uint8_t constant[] = {0x05, 0x00, 0x01, 0x05, 0x03, 0x42, 0xff, 0x00, 0x00};
  const uint8_t breathing[] = {0x05, 0x00, 0x01, 0x18, 0x02, 0x42, 0x07,
                               0xff, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00,
                               0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff,
                               0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff};
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_lighting(f, AJZ_LIGHT_OFF, 4, 2, NULL) == 0);
  CHECK(memcmp(f, off, sizeof(off)) == 0);
  CHECK(ajz_set_lighting(f, AJZ_LIGHT_CONSTANT, 4, 2, red) == 0);
  CHECK(memcmp(f, constant, sizeof(constant)) == 0);
  CHECK(ajz_set_lighting(f, AJZ_LIGHT_BREATHING, 4, 2, NULL) == 0);
  CHECK(memcmp(f, breathing, sizeof(breathing)) == 0);
  CHECK(f[31] == 0x3f);
}

static void test_set_lighting_rejects_unsupported(void) {
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_lighting(f, 1, 4, 2, NULL) == -1); // flowing: disabled on AJ179
  CHECK(ajz_set_lighting(f, AJZ_LIGHT_OFF, 5, 2, NULL) == -1);
  CHECK(ajz_set_lighting(f, AJZ_LIGHT_OFF, 4, 5, NULL) == -1);
}

// 0x435706: 06 00 01 05 <lod> <motion_sync> <angle_snap>
static void test_set_sensor_packet(void) {
  const uint8_t expected[] = {0x06, 0x00, 0x01, 0x05, 0x02, 0x01, 0x00, 0x00, 0x00};
  uint8_t f[AJZ_REPORT_LEN];

  CHECK(ajz_set_sensor(f, 2, 1, 0) == 0);
  CHECK(memcmp(f, expected, sizeof(expected)) == 0);
  CHECK(f[31] == 0x03);
  CHECK(ajz_set_sensor(f, 3, 0, 0) == -1);
}

// 0x432d9c factory table.
static void test_set_buttons_factory_table(void) {
  const uint8_t keys[6][3] = {{0x10, 0x01, 0x00}, {0x10, 0x02, 0x00},
                              {0x10, 0x04, 0x00}, {0x10, 0x08, 0x00},
                              {0x10, 0x10, 0x00}, {0x40, 0x01, 0x00}};
  const uint8_t header[] = {0x09, 0x00, 0x01, 0x0f};
  uint8_t f[AJZ_REPORT_LEN];

  ajz_set_buttons(f, keys);
  CHECK(memcmp(f, header, sizeof(header)) == 0);
  CHECK(memcmp(&f[4], keys, sizeof(keys)) == 0);
  CHECK(f[31] == 0xb0);
}

// Live 0x14 reply: "14 00 01 12 ff0000 0000ff ffff00 00ff00 00ffff ff00ff ... f7".
// Writing the same colours must produce the same payload and checksum.
static void test_set_dpi_colours_matches_live_reply(void) {
  const uint8_t rgb[6][3] = {{0xff, 0x00, 0x00}, {0x00, 0x00, 0xff},
                             {0xff, 0xff, 0x00}, {0x00, 0xff, 0x00},
                             {0x00, 0xff, 0xff}, {0xff, 0x00, 0xff}};
  const uint8_t header[] = {0x04, 0x00, 0x01, 0x12};
  uint8_t f[AJZ_REPORT_LEN];

  ajz_set_dpi_colours(f, rgb);
  CHECK(memcmp(f, header, sizeof(header)) == 0);
  CHECK(memcmp(&f[4], rgb, sizeof(rgb)) == 0);
  CHECK(f[31] == 0xf7);
}

// Live 0x17 reply: "17 00 01 05 1e 00 00 08 00 ... 26". The write declares 4
// payload bytes (0x4359bb) but carries the same values.
static void test_set_power_matches_live_reply(void) {
  const uint8_t expected[] = {0x07, 0x00, 0x01, 0x04, 0x1e, 0x00, 0x00, 0x08};
  uint8_t f[AJZ_REPORT_LEN];

  ajz_set_power(f, 30, 0, 0, 8);
  CHECK(memcmp(f, expected, sizeof(expected)) == 0);
  CHECK(f[31] == 0x26);
}

static int code_is(const char *name, uint8_t b0, uint8_t b1, uint8_t b2) {
  uint8_t c[3];
  return ajz_button_code(name, c) == 0 && c[0] == b0 && c[1] == b1 && c[2] == b2;
}

// Function codes from the key-mapping switch (0x432e4b..0x433377).
static void test_button_codes(void) {
  CHECK(code_is("left", 0x10, 0x01, 0x00));
  CHECK(code_is("right", 0x10, 0x02, 0x00));
  CHECK(code_is("middle", 0x10, 0x04, 0x00));
  CHECK(code_is("back", 0x10, 0x08, 0x00));
  CHECK(code_is("forward", 0x10, 0x10, 0x00));
  CHECK(code_is("scroll-up", 0x20, 0x01, 0x00));
  CHECK(code_is("scroll-down", 0x20, 0xff, 0x00));
  CHECK(code_is("dpi-loop", 0x40, 0x01, 0x00));
  CHECK(code_is("play-pause", 0x80, 0xcd, 0x00));
  CHECK(code_is("volume-up", 0x80, 0xe9, 0x00));
  CHECK(code_is("mute", 0x80, 0xe2, 0x00));
}

// Keyboard: 70 <modifier bits> <HID usage> (0x432ea2; VK->HID table 0x44e130).
static void test_button_key_codes(void) {
  CHECK(code_is("key:a", 0x70, 0x00, 0x04));
  CHECK(code_is("key:ctrl+c", 0x70, 0x01, 0x06));
  CHECK(code_is("key:super+tab", 0x70, 0x08, 0x2b));
  CHECK(code_is("key:ctrl+shift+esc", 0x70, 0x03, 0x29));
  CHECK(code_is("key:f5", 0x70, 0x00, 0x3e));
  CHECK(code_is("key:0", 0x70, 0x00, 0x27));
}

static void test_button_code_rejects_unknown(void) {
  uint8_t c[3];

  CHECK(ajz_button_code("bogus", c) == -1);
  CHECK(ajz_button_code("key:", c) == -1);
  CHECK(ajz_button_code("key:ctrl+", c) == -1);
  CHECK(ajz_button_code("key:f13", c) == -1);
}

// Macro events (0x41cc90): <type> <delay lo> <delay hi> <code>, delay after.
static void test_macro_parse_tap(void) {
  uint8_t ev[8][4];
  const uint8_t expected[2][4] = {{0x30, 0x0a, 0x00, 0x04}, {0xb0, 0x0a, 0x00, 0x04}};

  CHECK(ajz_macro_parse("a", ev, 8) == 2);
  CHECK(memcmp(ev, expected, sizeof(expected)) == 0);
}

static void test_macro_parse_modifier_and_wait(void) {
  uint8_t ev[8][4];
  const uint8_t expected[6][4] = {{0x20, 0x0a, 0x00, 0x01}, {0x30, 0x0a, 0x00, 0x06},
                                  {0xb0, 0x0a, 0x00, 0x06}, {0xa0, 0x2c, 0x01, 0x01},
                                  {0x30, 0x0a, 0x00, 0x04}, {0xb0, 0x0a, 0x00, 0x04}};

  CHECK(ajz_macro_parse("ctrl+c wait:300 a", ev, 8) == 6);
  CHECK(memcmp(ev, expected, sizeof(expected)) == 0);
}

static void test_macro_parse_rejects_bad_input(void) {
  uint8_t ev[4][4];

  CHECK(ajz_macro_parse("wait:5 a", ev, 4) == -1);   // nothing to wait after
  CHECK(ajz_macro_parse("bogus+x", ev, 4) == -1);
  CHECK(ajz_macro_parse("a b c", ev, 4) == -1);      // 6 events > 4
  CHECK(ajz_macro_parse("a wait:70000", ev, 4) == -1);
  CHECK(ajz_macro_parse("", ev, 4) == -1);
}

// 0x433ed0: payload = slot + events, 27-byte chunks, data[2] = (i<<4)|count.
static void test_macro_single_packet(void) {
  const uint8_t ev[2][4] = {{0x30, 0x0a, 0x00, 0x04}, {0xb0, 0x0a, 0x00, 0x04}};
  const uint8_t expected[] = {0x08, 0x00, 0x01, 0x09, 0x03, 0x30, 0x0a,
                              0x00, 0x04, 0xb0, 0x0a, 0x00, 0x04};
  uint8_t out[15][AJZ_REPORT_LEN];

  CHECK(ajz_macro_packets(3, ev, 2, out) == 1);
  CHECK(memcmp(out[0], expected, sizeof(expected)) == 0);
  CHECK(out[0][31] == 0xff);
}

static void test_macro_chunks(void) {
  uint8_t ev[10][4], payload[41], out[15][AJZ_REPORT_LEN];

  for (int i = 0; i < 10; i++) {
    ev[i][0] = 0x30;
    ev[i][1] = 0x0a;
    ev[i][2] = 0x00;
    ev[i][3] = 0x04 + i;
  }
  payload[0] = 3;
  memcpy(&payload[1], ev, 40);

  CHECK(ajz_macro_packets(3, ev, 10, out) == 2);
  CHECK(out[0][0] == 0x08 && out[0][2] == 0x02 && out[0][3] == 27);
  CHECK(memcmp(&out[0][4], payload, 27) == 0);
  CHECK(out[1][0] == 0x08 && out[1][2] == 0x12 && out[1][3] == 14);
  CHECK(memcmp(&out[1][4], &payload[27], 14) == 0);
}

static void test_macro_button_plays_once(void) {
  uint8_t code[3];

  ajz_macro_button(3, code);
  CHECK(code[0] == 0x90 && code[1] == 0x23 && code[2] == 0x01);
}

int main(void) {
  test_macro_parse_tap();
  test_macro_parse_modifier_and_wait();
  test_macro_parse_rejects_bad_input();
  test_macro_single_packet();
  test_macro_chunks();
  test_macro_button_plays_once();
  test_button_codes();
  test_button_key_codes();
  test_button_code_rejects_unknown();
  test_set_dpi_colours_matches_live_reply();
  test_set_power_matches_live_reply();
  test_dpi_codec_paw3395();
  test_dpi_codec_segmented_sensor();
  test_dpi_range_by_sensor();
  test_set_dpi_packet();
  test_set_dpi_clamps_to_sensor_range();
  test_set_dpi_rejects_bad_stage();
  test_parse_dpi_reply();
  test_report_rate_flags();
  test_set_rate_packet();
  test_set_lighting_packets();
  test_set_lighting_rejects_unsupported();
  test_set_sensor_packet();
  test_set_buttons_factory_table();
  test_info_battery_kept_while_mouse_sleeps();
  test_info_battery_unknown_when_never_reported();
  test_is_read_cmd_allows_only_known_reads();
  test_read_request_is_command_then_zeros();
  test_checksum_sums_payload_only();
  test_parse_info_reads_id_sensor_and_battery();
  test_parse_info_rejects_error_status();
  test_parse_info_rejects_non_ascii_id();
  test_parse_status_online_frame();
  test_parse_status_offline_frame();
  test_parse_status_rejects_impossible_battery();
  test_parse_status_ignores_other_reports();

  if (failures) {
    printf("%d check(s) failed\n", failures);
    return 1;
  }
  printf("all protocol tests passed\n");
  return 0;
}
