#define _POSIX_C_SOURCE 200809L
#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define AJZ_PAYLOAD_MAX 27

// Seven colours the official driver sends for breathing (captured traffic).
static const uint8_t breathing_palette[21] = {
    0xff, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 0xff, 0x00, 0xff,
    0xff, 0xff, 0xff, 0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff};

// sub_41e330. 0x95 (PAW3395) and unknown sensors use the default.
int ajz_dpi_encode(uint8_t sensor, int dpi) {
  switch (sensor) {
  case 0x11:
    if (dpi >= 13000)
      return (dpi - 13000) / 1000 + 221;
    return dpi > 10000 ? (dpi - 10000) / 100 + 200 : dpi / 50;
  case 0x05:
    return dpi > 6400 ? (dpi - 6400) / 100 + 128 : dpi / 50;
  case 0x25:
    return dpi > 5000 ? (dpi - 5000) / 500 + 50 : dpi / 100;
  case 0x26:
    return dpi > 5000 ? (dpi - 5000) / 500 + 50 : dpi / 100 - 1;
  case 0x96:
    return dpi > 26000 ? (dpi - 26000) / 1000 + 519 : dpi / 50 - 1;
  case 0x04:
  case 0x10:
  case 0x12:
  case 0x35:
    return dpi / 100;
  default:
    return dpi / 50 - 1;
  }
}

// sub_41e490, including its quirks for 0x26 and 0x96.
int ajz_dpi_decode(uint8_t sensor, int raw) {
  switch (sensor) {
  case 0x11:
    if (raw < 200)
      return raw * 50;
    return raw <= 220 ? (raw - 100) * 100 : (raw - 208) * 1000;
  case 0x05:
    return raw >= 129 ? (raw - 64) * 100 : raw * 50;
  case 0x25:
    return raw >= 50 ? (raw - 40) * 500 : raw * 100;
  case 0x26:
    return raw >= 50 ? (raw - 39) * 500 : raw * 100;
  case 0x96:
    return raw >= 521 ? (raw - 494) * 1000 : (raw + 1) * 50;
  case 0x04:
  case 0x10:
  case 0x12:
  case 0x35:
    return raw * 100;
  default:
    return (raw + 1) * 50;
  }
}

// Sensor table in the vendor's sync routine (0x431350).
void ajz_dpi_range(uint8_t sensor, int *min, int *max) {
  *min = 50;
  *max = 26000;
  switch (sensor) {
  case 0x11: *max = 18000; break;
  case 0x05: *max = 12000; break;
  case 0x96: *max = 32000; break;
  case 0x04: *min = 100; *max = 8000; break;
  case 0x10:
  case 0x12: *min = 100; *max = 4800; break;
  case 0x25: *min = 100; *max = 10000; break;
  case 0x26: *min = 200; *max = 10000; break;
  case 0x35: *min = 100; *max = 16000; break;
  }
}

// Report-rate list builder 0x41d989.
static const int rate_table[][2] = {{125, 0x08},  {250, 0x04},  {500, 0x02},
                                    {1000, 0x01}, {2000, 0x10}, {4000, 0x20},
                                    {8000, 0x40}};

int ajz_rate_flag(int hz) {
  for (size_t i = 0; i < sizeof(rate_table) / sizeof(rate_table[0]); i++)
    if (rate_table[i][0] == hz)
      return rate_table[i][1];
  return -1;
}

int ajz_rate_hz(int flag) {
  for (size_t i = 0; i < sizeof(rate_table) / sizeof(rate_table[0]); i++)
    if (rate_table[i][1] == flag)
      return rate_table[i][0];
  return -1;
}

int ajz_set_dpi(uint8_t f[AJZ_REPORT_LEN], uint8_t sensor, int index, int count,
                const int dpi[6]) {
  uint8_t p[25];
  int min, max;

  if (count < 1 || count > 6 || index < 0 || index >= count)
    return -1;

  ajz_dpi_range(sensor, &min, &max);
  p[0] = (index << 4) | count;
  for (int i = 0; i < 6; i++) {
    int v = dpi[i] < min ? min : dpi[i] > max ? max : dpi[i];
    int raw = ajz_dpi_encode(sensor, v);

    p[1 + 4 * i] = p[3 + 4 * i] = raw & 0xff;
    p[2 + 4 * i] = p[4 + 4 * i] = raw >> 8;
  }
  ajz_build(f, 0x03, 0x01, 0x25, p, sizeof(p));
  return 0;
}

int ajz_parse_dpi(const uint8_t r[AJZ_REPORT_LEN], uint8_t sensor, int *index,
                  int *count, int dpi[6]) {
  if (r[1] != 0)
    return -1;
  *index = r[4] >> 4;
  *count = r[4] & 0x0f;
  for (int i = 0; i < 6; i++)
    dpi[i] = ajz_dpi_decode(sensor, r[5 + 4 * i] | r[6 + 4 * i] << 8);
  return 0;
}

void ajz_set_rate(uint8_t f[AJZ_REPORT_LEN], uint8_t flag) {
  ajz_build(f, 0x02, 0x01, 0x01, &flag, 1);
}

int ajz_set_lighting(uint8_t f[AJZ_REPORT_LEN], int mode, int brightness,
                     int speed, const uint8_t rgb[3]) {
  uint8_t p[24];

  if (brightness < 0 || brightness > 4 || speed < 0 || speed > 4)
    return -1;
  p[0] = mode;
  p[1] = (brightness << 4) | speed;

  switch (mode) {
  case AJZ_LIGHT_OFF:
    ajz_build(f, 0x05, 0x01, 2, p, 2);
    return 0;
  case AJZ_LIGHT_CONSTANT:
    if (!rgb)
      return -1;
    memcpy(&p[2], rgb, 3);
    ajz_build(f, 0x05, 0x01, 5, p, 5);
    return 0;
  case AJZ_LIGHT_BREATHING:
    p[2] = 7;
    memcpy(&p[3], breathing_palette, sizeof(breathing_palette));
    ajz_build(f, 0x05, 0x01, 0x18, p, sizeof(p));
    return 0;
  default:
    return -1; // flowing / neon / wave are disabled for the AJ179
  }
}

int ajz_set_sensor(uint8_t f[AJZ_REPORT_LEN], int lod, int motion_sync,
                   int angle_snap) {
  uint8_t p[5] = {0};

  if (lod != 1 && lod != 2)
    return -1;
  p[0] = lod;
  p[1] = motion_sync != 0;
  p[2] = angle_snap != 0;
  ajz_build(f, 0x06, 0x01, 0x05, p, sizeof(p));
  return 0;
}

// Button functions from the key-mapping switch (0x432e4b..0x433377). Only
// codes whose meaning is certain are listed.
static const struct {
  const char *name;
  uint8_t code[3];
} button_names[] = {
    {"left", {0x10, 0x01, 0x00}},       {"right", {0x10, 0x02, 0x00}},
    {"middle", {0x10, 0x04, 0x00}},     {"back", {0x10, 0x08, 0x00}},
    {"forward", {0x10, 0x10, 0x00}},    {"scroll-up", {0x20, 0x01, 0x00}},
    {"scroll-down", {0x20, 0xff, 0x00}}, {"dpi-loop", {0x40, 0x01, 0x00}},
    {"play-pause", {0x80, 0xcd, 0x00}}, {"stop", {0x80, 0xb7, 0x00}},
    {"previous", {0x80, 0xb6, 0x00}},   {"next", {0x80, 0xb5, 0x00}},
    {"volume-up", {0x80, 0xe9, 0x00}},  {"volume-down", {0x80, 0xea, 0x00}},
    {"mute", {0x80, 0xe2, 0x00}},
};

static const struct {
  const char *name;
  int usage;
} named_keys[] = {{"enter", 0x28}, {"esc", 0x29}, {"backspace", 0x2a},
                  {"tab", 0x2b},   {"space", 0x2c}};

// HID keyboard usage for a key name; same table as the vendor's 0x44e130.
static int key_usage(const char *k) {

  if (k[0] && !k[1]) {
    if (k[0] >= 'a' && k[0] <= 'z')
      return 0x04 + k[0] - 'a';
    if (k[0] >= '1' && k[0] <= '9')
      return 0x1e + k[0] - '1';
    if (k[0] == '0')
      return 0x27;
  }
  if (k[0] == 'f' && atoi(k + 1) >= 1 && atoi(k + 1) <= 12)
    return 0x3a + atoi(k + 1) - 1;
  for (size_t i = 0; i < sizeof(named_keys) / sizeof(named_keys[0]); i++)
    if (strcmp(k, named_keys[i].name) == 0)
      return named_keys[i].usage;
  return -1;
}

// The key name for a HID usage: the inverse of key_usage.
static int key_name(int usage, char *out, size_t size) {
  if (usage >= 0x04 && usage <= 0x1d)
    snprintf(out, size, "%c", 'a' + usage - 0x04);
  else if (usage >= 0x1e && usage <= 0x26)
    snprintf(out, size, "%c", '1' + usage - 0x1e);
  else if (usage == 0x27)
    snprintf(out, size, "0");
  else if (usage >= 0x3a && usage <= 0x45)
    snprintf(out, size, "f%d", usage - 0x3a + 1);
  else {
    for (size_t i = 0; i < sizeof(named_keys) / sizeof(named_keys[0]); i++)
      if (named_keys[i].usage == usage) {
        snprintf(out, size, "%s", named_keys[i].name);
        return 0;
      }
    return -1;
  }
  return 0;
}

// "left", "dpi-loop", "volume-up", ... or "key:[ctrl+][shift+][alt+][super+]<key>".
int ajz_button_code(const char *name, uint8_t code[3]) {
  char buf[64], *save;
  int mods = 0, usage = -1;

  for (size_t i = 0; i < sizeof(button_names) / sizeof(button_names[0]); i++)
    if (strcmp(name, button_names[i].name) == 0) {
      memcpy(code, button_names[i].code, 3);
      return 0;
    }

  if (strncmp(name, "key:", 4) != 0 || strlen(name) >= sizeof(buf))
    return -1;
  strcpy(buf, name + 4);
  for (char *t = strtok_r(buf, "+", &save); t; t = strtok_r(NULL, "+", &save)) {
    if (usage >= 0)
      return -1; // the key must come last
    if (strcmp(t, "ctrl") == 0)
      mods |= 0x01;
    else if (strcmp(t, "shift") == 0)
      mods |= 0x02;
    else if (strcmp(t, "alt") == 0)
      mods |= 0x04;
    else if (strcmp(t, "super") == 0)
      mods |= 0x08;
    else if ((usage = key_usage(t)) < 0)
      return -1;
  }
  if (usage < 0)
    return -1;

  code[0] = 0x70;
  code[1] = mods;
  code[2] = usage;
  return 0;
}

static void put_event(uint8_t ev[4], uint8_t type, uint8_t code) {
  ev[0] = type;
  ev[1] = AJZ_MACRO_GAP_MS;
  ev[2] = 0;
  ev[3] = code;
}

// "ctrl+c wait:300 a": each key is pressed and released (modifiers first and
// last); wait:N sets the pause after the previous event in ms (0x41cc90).
int ajz_macro_parse(const char *text, uint8_t events[][4], int max) {
  char buf[512], spec[80], *save;
  int n = 0;

  if (strlen(text) >= sizeof(buf))
    return -1;
  strcpy(buf, text);

  for (char *t = strtok_r(buf, " ", &save); t; t = strtok_r(NULL, " ", &save)) {
    uint8_t code[3];
    int mods;

    if (strncmp(t, "wait:", 5) == 0) {
      int ms = atoi(t + 5);

      if (n == 0 || ms < 1 || ms > 0xffff)
        return -1;
      events[n - 1][1] = ms & 0xff;
      events[n - 1][2] = ms >> 8;
      continue;
    }

    snprintf(spec, sizeof(spec), "key:%s", t);
    if (ajz_button_code(spec, code) != 0)
      return -1;
    mods = code[1];
    if (n + 2 + 2 * __builtin_popcount(mods) > max)
      return -1;

    for (int b = 0; b < 8; b++)
      if (mods & (1 << b))
        put_event(events[n++], 0x20, 1 << b);
    put_event(events[n++], 0x30, code[2]);
    put_event(events[n++], 0xb0, code[2]);
    for (int b = 7; b >= 0; b--)
      if (mods & (1 << b))
        put_event(events[n++], 0xa0, 1 << b);
  }
  return n > 0 ? n : -1;
}

int ajz_macro_packets(int slot, const uint8_t events[][4], int n,
                      uint8_t out[15][AJZ_REPORT_LEN]) {
  uint8_t payload[1 + 4 * AJZ_MACRO_MAX_EVENTS];
  int total = 1 + 4 * n, count = (total + 26) / 27;

  if (n < 1 || n > AJZ_MACRO_MAX_EVENTS)
    return -1;
  payload[0] = slot;
  memcpy(&payload[1], events, 4 * n);

  for (int i = 0; i < count; i++) {
    int len = i == count - 1 ? total - 27 * i : 27;

    ajz_build(out[i], 0x08, (i << 4) | count, len, &payload[27 * i], len);
  }
  return count;
}

// Button code that plays the macro in this slot once (0x433013).
int ajz_button_name(const uint8_t code[3], char *out, size_t size) {
  static const char *mods[] = {"ctrl+", "shift+", "alt+", "super+"};
  char buf[64] = "key:", key[16];

  for (size_t i = 0; i < sizeof(button_names) / sizeof(button_names[0]); i++)
    if (memcmp(code, button_names[i].code, 3) == 0) {
      snprintf(out, size, "%s", button_names[i].name);
      return 0;
    }
  if (code[0] == 0x90) { // a macro slot (ajz_macro_button)
    snprintf(out, size, "macro");
    return 0;
  }
  if (code[0] != 0x70 || (code[1] & 0xf0) || key_name(code[2], key, sizeof(key)) != 0)
    return -1;
  for (int b = 0; b < 4; b++)
    if (code[1] & (1 << b))
      strcat(buf, mods[b]);
  strcat(buf, key);
  snprintf(out, size, "%s", buf);
  return 0;
}

void ajz_macro_button(int slot, uint8_t code[3]) {
  code[0] = 0x90;
  code[1] = slot | 0x20;
  code[2] = 1;
}

// Length byte is 0x0F although all six buttons are sent (0x433445).
void ajz_set_buttons(uint8_t f[AJZ_REPORT_LEN], const uint8_t keys[6][3]) {
  ajz_build(f, 0x09, 0x01, 0x0f, &keys[0][0], 18);
}

// 0x4351f0: six R G B triplets, one per DPI stage.
void ajz_set_dpi_colours(uint8_t f[AJZ_REPORT_LEN], const uint8_t rgb[6][3]) {
  ajz_build(f, 0x04, 0x01, 0x12, &rgb[0][0], 18);
}

// 0x4359bb: sleep_light, move_wakeup, move_closelight, button_respond_time.
void ajz_set_power(uint8_t f[AJZ_REPORT_LEN], uint8_t sleep, uint8_t wake_on_move,
                   uint8_t lights_off_on_move, uint8_t debounce) {
  const uint8_t p[4] = {sleep, wake_on_move, lights_off_on_move, debounce};

  ajz_build(f, 0x07, 0x01, 0x04, p, sizeof(p));
}

// Reads issued by the vendor's sync routine (0x431350) plus get-info.
int ajz_is_read_cmd(uint8_t cmd) {
  return cmd == 0x10 || (cmd >= 0x12 && cmd <= 0x17) || cmd == 0x20;
}

void ajz_build(uint8_t f[AJZ_REPORT_LEN], uint8_t cmd, uint8_t seq, uint8_t len,
               const uint8_t *payload, int n) {
  int sum = 0;

  memset(f, 0, AJZ_REPORT_LEN);
  f[0] = cmd;
  f[2] = seq;
  f[3] = len;
  if (n > AJZ_PAYLOAD_MAX)
    n = AJZ_PAYLOAD_MAX;
  if (n > 0)
    memcpy(&f[4], payload, n);

  for (int i = 4; i < AJZ_REPORT_LEN - 1; i++)
    sum += f[i];
  f[AJZ_REPORT_LEN - 1] = sum & 0xff;
}

int ajz_parse_info(const uint8_t r[AJZ_REPORT_LEN], struct ajz_info *info) {
  if (r[1] != 0)
    return -1;

  for (int i = 0; i < 4; i++) {
    if (r[4 + i] < 0x20 || r[4 + i] > 0x7e)
      return -1;
    info->id[i] = r[4 + i];
  }
  info->id[4] = '\0';

  info->sensor = r[10];
  info->rate_caps = r[11];
  info->charging = r[12];
  info->battery = r[13];
  info->connected = r[14] != 0;
  return 0;
}

// While the mouse sleeps the receiver still reports its last battery level;
// 0 then means it has not reported one yet.
int ajz_info_battery(const struct ajz_info *info) {
  if (info->battery > 100 || (!info->connected && info->battery == 0))
    return -1;
  return info->battery;
}

int ajz_parse_status(const uint8_t r[AJZ_REPORT_LEN], int *online,
                     int *battery) {
  if (r[0] != AJZ_STATUS_REPORT)
    return -1;

  *online = r[1] == 1;
  *battery = r[2] <= 100 ? r[2] : -1;
  return 0;
}
