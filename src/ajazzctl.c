#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "hidraw.h"
#include "protocol.h"

#define VENDOR_ID 0x249a
#define PRODUCT_ID 0x5c2f
#define WAKE_WAIT_SECONDS 300
#define IDLE_RETRIES 20

static void print_hex(const uint8_t *b, int n) {
  for (int i = 0; i < n; i++)
    printf("%02x%c", b[i], i == n - 1 ? '\n' : ' ');
}

static int via_cable;

// Uses the USB cable when plugged in, otherwise the 2.4 GHz receiver.
static int open_receiver(void) {
  char path[64];
  int fd;

  if (ajz_find_mouse("/sys", VENDOR_ID, PRODUCT_ID, path, sizeof(path), &via_cable) != 0) {
    fprintf(stderr, "AJ179 not found: no USB cable connection and no receiver %04x:%04x\n",
            VENDOR_ID, PRODUCT_ID);
    return -1;
  }
  fd = open(path, O_RDWR);
  if (fd < 0)
    perror(path);
  return fd;
}

// Waits for the status frame the mouse pushes when it wakes up.
static int wait_for_mouse(int fd, int seconds) {
  uint8_t frame[64];
  int online, bat;

  for (int ms = 0; ms < seconds * 1000; ms += 100) {
    struct pollfd p = {.fd = fd, .events = POLLIN};

    if (poll(&p, 1, 100) == 1 && read(fd, frame, sizeof(frame)) >= AJZ_REPORT_LEN &&
        ajz_parse_status(frame, &online, &bat) == 0 && online)
      return 0;
  }
  return -1;
}

// Sends one request. Settings only reach the mouse while it is active, so if
// it is asleep (0x02) or idle (0x01) this asks for movement and retries. Every
// write sets absolute values, so repeating one is harmless.
static int exchange(int fd, const uint8_t req[AJZ_REPORT_LEN],
                    uint8_t reply[AJZ_REPORT_LEN]) {
  int st = ajz_transact(fd, req, reply);

  for (int tries = 0; tries < IDLE_RETRIES &&
                      (st == AJZ_STATUS_ASLEEP || st == AJZ_STATUS_NO_ANSWER);
       tries++) {
    if (tries == 0)
      fprintf(stderr, "mouse is %s - move it\n",
              st == AJZ_STATUS_ASLEEP ? "asleep" : "idle");
    if (st == AJZ_STATUS_ASLEEP && wait_for_mouse(fd, WAKE_WAIT_SECONDS) != 0)
      break;
    st = ajz_transact(fd, req, reply);
  }
  if (st != 0) {
    if (st < 0)
      fprintf(stderr, "no reply to 0x%02x\n", req[0]);
    else
      fprintf(stderr, "0x%02x failed with status 0x%02x\n", req[0], st);
    return -1;
  }
  return 0;
}

// Sends one read command; only reads decoded from the vendor driver are allowed.
static int do_read(int fd, uint8_t cmd, uint8_t reply[AJZ_REPORT_LEN]) {
  uint8_t req[AJZ_REPORT_LEN];

  if (!ajz_is_read_cmd(cmd)) {
    fprintf(stderr, "0x%02x is not a known read command\n", cmd);
    return -1;
  }
  ajz_build(req, cmd, 0, 0, NULL, 0);
  return exchange(fd, req, reply);
}

static int cmd_info(int fd) {
  uint8_t reply[AJZ_REPORT_LEN];
  struct ajz_info info;

  if (do_read(fd, AJZ_CMD_INFO, reply) != 0)
    return 1;
  printf("raw:       ");
  print_hex(reply, AJZ_REPORT_LEN);
  if (ajz_parse_info(reply, &info) != 0) {
    fprintf(stderr, "reply is not a device-info report\n");
    return 1;
  }
  printf("link:      %s\n", via_cable ? "USB cable" : "2.4 GHz receiver");
  printf("device id: %s\n", info.id);
  printf("sensor:    0x%02x\n", info.sensor);
  printf("rate caps: 0x%02x\n", info.rate_caps);
  printf("connected: %s\n", info.connected ? "yes" : "no (mouse asleep)");
  if (ajz_info_battery(&info) >= 0)
    printf("battery:   %d%%%s%s\n", info.battery, info.charging ? " (charging)" : "",
           info.connected ? "" : " (last reported)");
  return 0;
}

static int cmd_read(int fd, const char *arg) {
  uint8_t reply[AJZ_REPORT_LEN];

  if (do_read(fd, (uint8_t)strtol(arg, NULL, 16), reply) != 0)
    return 1;
  print_hex(reply, AJZ_REPORT_LEN);
  return 0;
}

static int read_sensor_id(int fd, uint8_t *sensor) {
  uint8_t reply[AJZ_REPORT_LEN];
  struct ajz_info info;

  if (do_read(fd, AJZ_CMD_INFO, reply) != 0 || ajz_parse_info(reply, &info) != 0)
    return -1;
  *sensor = info.sensor;
  return 0;
}

static void load_buttons(uint8_t keys[6][3]);
static void load_macros(char macros[6][512]);

// Macro text is ajazzctl's own tokens; anything else (a hand-edited file) is left
// out of the JSON rather than escaped.
static int plain_macro(const char *s) {
  return strspn(s, "abcdefghijklmnopqrstuvwxyz0123456789+: ") == strlen(s);
}

// A button's function name, for show.
static const char *button_label(const uint8_t code[3], char *out, size_t size) {
  return ajz_button_name(code, out, size) == 0 ? out : "unknown";
}

// Prints every readable setting, as text or (json) as one JSON line for the GUI.
// Buttons have no read command, so they come from the map ajazzctl last wrote.
static int cmd_show(int fd, int json) {
  static const char *lights[] = {"off", "flowing", "breathing", "constant", "neon", "wave"};
  uint8_t sensor, rate[AJZ_REPORT_LEN], stages[AJZ_REPORT_LEN], col[AJZ_REPORT_LEN],
      light[AJZ_REPORT_LEN], sens[AJZ_REPORT_LEN], power[AJZ_REPORT_LEN], fw[AJZ_REPORT_LEN];
  uint8_t keys[6][3];
  char name[64], macros[6][512];
  int first = 1;
  int index, count, dpi[6], have_fw;
  const char *mode;

  if (read_sensor_id(fd, &sensor) != 0 || do_read(fd, 0x12, rate) != 0 ||
      do_read(fd, 0x13, stages) != 0 || ajz_parse_dpi(stages, sensor, &index, &count, dpi) != 0 ||
      do_read(fd, 0x14, col) != 0 || do_read(fd, 0x15, light) != 0 ||
      do_read(fd, 0x16, sens) != 0 || do_read(fd, 0x17, power) != 0)
    return 1;
  have_fw = do_read(fd, 0x20, fw) == 0;
  mode = light[4] < 6 ? lights[light[4]] : "?";
  load_buttons(keys);
  load_macros(macros);
  if (count > 6)
    count = 6;

  if (json) {
    printf("{\"rate\":%d,\"dpi\":{\"active\":%d,\"stages\":[", ajz_rate_hz(rate[4]), index + 1);
    for (int i = 0; i < count; i++)
      printf("%s%d", i ? "," : "", dpi[i]);
    printf("],\"colours\":[");
    for (int i = 0; i < 6; i++)
      printf("%s\"#%02x%02x%02x\"", i ? "," : "", col[4 + 3 * i], col[5 + 3 * i], col[6 + 3 * i]);
    printf("]},\"lighting\":{\"mode\":\"%s\",\"colour\":", mode);
    if (light[4] == AJZ_LIGHT_CONSTANT) // only constant mode has one colour after brightness/speed
      printf("\"#%02x%02x%02x\"", light[6], light[7], light[8]);
    else
      printf("null");
    printf(",\"brightness\":%d,\"speed\":%d},", light[5] >> 4, light[5] & 0x0f);
    printf("\"lod\":%d,\"motion_sync\":%s,\"angle_snap\":%s,", sens[4],
           sens[5] ? "true" : "false", sens[6] ? "true" : "false");
    printf("\"power\":{\"sleep\":%d,\"wake_on_move\":%d,\"lights_off_on_move\":%d,"
           "\"debounce\":%d},",
           power[4], power[5], power[6], power[7]);
    printf("\"buttons\":[");
    for (int i = 0; i < 6; i++)
      printf("%s\"%s\"", i ? "," : "", button_label(keys[i], name, sizeof(name)));
    printf("],\"macros\":{");
    for (int i = 0; i < 6; i++)
      if (macros[i][0] && plain_macro(macros[i])) {
        printf("%s\"%d\":\"%s\"", first ? "" : ",", i + 1, macros[i]);
        first = 0;
      }
    printf("},");
    if (have_fw)
      printf("\"receiver_fw\":\"%x.%02x\"}\n", fw[4], fw[5]);
    else
      printf("\"receiver_fw\":null}\n");
    return 0;
  }

  printf("report rate:  %d Hz\n", ajz_rate_hz(rate[4]));
  printf("dpi stages:  ");
  for (int i = 0; i < count; i++)
    printf(" %s%d", i == index ? "*" : "", dpi[i]);
  printf("\n");
  printf("dpi colours: ");
  for (int i = 0; i < 6; i++)
    printf(" #%02x%02x%02x", col[4 + 3 * i], col[5 + 3 * i], col[6 + 3 * i]);
  printf("\n");
  printf("lighting:     %s, brightness %d, speed %d\n", mode, light[5] >> 4, light[5] & 0x0f);
  printf("lift-off:     %s\n",
         sens[4] == 1 ? "low (1 mm)" : sens[4] == 2 ? "high (2 mm)" : "?");
  printf("motion sync:  %s\n", sens[5] ? "on" : "off");
  printf("angle snap:   %s\n", sens[6] ? "on" : "off");
  printf("power:        sleep after %d s, debounce %d ms, wake-on-move %d, "
         "lights-off-on-move %d\n",
         power[4] * 10, power[7], power[5], power[6]);
  printf("buttons:     ");
  for (int i = 0; i < 6; i++)
    printf(" %s", button_label(keys[i], name, sizeof(name)));
  printf("  (as last set by ajazzctl)\n");
  for (int i = 0; i < 6; i++)
    if (macros[i][0])
      printf("macro %d:      %s\n", i + 1, macros[i]);
  if (have_fw)
    printf("receiver fw:  %x.%02x\n", fw[4], fw[5]);
  return 0;
}

// Writes a setting, then reads it back and compares the first n payload bytes.
static int apply(int fd, const uint8_t req[AJZ_REPORT_LEN], uint8_t read_cmd, int n) {
  uint8_t reply[AJZ_REPORT_LEN];

  if (exchange(fd, req, reply) != 0 || do_read(fd, read_cmd, reply) != 0)
    return 1;
  if (memcmp(&req[4], &reply[4], n) != 0) {
    printf("read-back mismatch\n  wrote: ");
    print_hex(&req[4], n);
    printf("  read:  ");
    print_hex(&reply[4], n);
    return 1;
  }
  printf("ok (verified by read-back)\n");
  return 0;
}

static int cmd_rate(int fd, const char *arg) {
  uint8_t req[AJZ_REPORT_LEN];
  int flag = ajz_rate_flag(atoi(arg));

  if (flag < 0 || flag > 0x08) { // the AJ179 dual mode tops out at 1000 Hz
    fprintf(stderr, "rate must be 125, 250, 500 or 1000\n");
    return 2;
  }
  ajz_set_rate(req, flag);
  return apply(fd, req, 0x12, 1);
}

// "dpi <stage> <value>" or "dpi select <stage>"; stages count from 1.
static int cmd_dpi(int fd, const char *a, const char *b) {
  uint8_t req[AJZ_REPORT_LEN], r[AJZ_REPORT_LEN], sensor;
  int index, count, dpi[6];
  int select = strcmp(a, "select") == 0;
  int stage = atoi(select ? b : a);

  if (read_sensor_id(fd, &sensor) != 0 || do_read(fd, 0x13, r) != 0 ||
      ajz_parse_dpi(r, sensor, &index, &count, dpi) != 0)
    return 1;
  if (stage < 1 || stage > count) {
    fprintf(stderr, "stage must be 1..%d\n", count);
    return 2;
  }
  if (select)
    index = stage - 1;
  else
    dpi[stage - 1] = atoi(b);

  if (ajz_set_dpi(req, sensor, index, count, dpi) != 0)
    return 2;
  return apply(fd, req, 0x13, 25);
}

// "lighting off|breathing|constant [#RRGGBB] [brightness speed]" (0..4 each).
static int cmd_lighting(int fd, int argc, char *argv[]) {
  uint8_t req[AJZ_REPORT_LEN], r[AJZ_REPORT_LEN], rgb[3] = {0xff, 0x00, 0x00};
  int mode, arg = 1, brightness, speed;

  if (strcmp(argv[0], "off") == 0)
    mode = AJZ_LIGHT_OFF;
  else if (strcmp(argv[0], "breathing") == 0)
    mode = AJZ_LIGHT_BREATHING;
  else if (strcmp(argv[0], "constant") == 0)
    mode = AJZ_LIGHT_CONSTANT;
  else
    return 2;

  if (mode == AJZ_LIGHT_CONSTANT && argc > arg && argv[arg][0] == '#') {
    if (sscanf(argv[arg] + 1, "%2hhx%2hhx%2hhx", &rgb[0], &rgb[1], &rgb[2]) != 3)
      return 2;
    arg++;
  }

  if (do_read(fd, 0x15, r) != 0)
    return 1;
  brightness = argc > arg + 1 ? atoi(argv[arg]) : r[5] >> 4;
  speed = argc > arg + 1 ? atoi(argv[arg + 1]) : r[5] & 0x0f;

  if (ajz_set_lighting(req, mode, brightness, speed, rgb) != 0) {
    fprintf(stderr, "brightness and speed must be 0..4\n");
    return 2;
  }
  // A write that changes the mode only switches it: the mouse brings back that
  // mode's saved brightness, speed and colour. Writing again applies ours.
  if (r[4] != mode && exchange(fd, req, r) != 0)
    return 1;
  // The 0x15 reply carries the colour for constant mode ("03 40 ff 00 ff").
  return apply(fd, req, 0x15, mode == AJZ_LIGHT_CONSTANT ? 5 : 2);
}

// "sensor lod 1|2", "sensor motion-sync on|off", "sensor angle-snap on|off".
static int cmd_sensor(int fd, const char *what, const char *value) {
  uint8_t req[AJZ_REPORT_LEN], r[AJZ_REPORT_LEN];
  int lod, motion_sync, angle_snap, on = strcmp(value, "on") == 0;

  if (do_read(fd, 0x16, r) != 0)
    return 1;
  lod = r[4];
  motion_sync = r[5];
  angle_snap = r[6];

  if (strcmp(what, "lod") == 0)
    lod = atoi(value);
  else if (strcmp(what, "motion-sync") == 0)
    motion_sync = on;
  else if (strcmp(what, "angle-snap") == 0)
    angle_snap = on;
  else
    return 2;

  if (ajz_set_sensor(req, lod, motion_sync, angle_snap) != 0) {
    fprintf(stderr, "lod must be 1 (1 mm) or 2 (2 mm)\n");
    return 2;
  }
  return apply(fd, req, 0x16, 3);
}

// "dpi-colour <stage> #RRGGBB"; stages count from 1.
static int cmd_dpi_colour(int fd, const char *a, const char *b) {
  uint8_t req[AJZ_REPORT_LEN], r[AJZ_REPORT_LEN], rgb[6][3];
  int stage = atoi(a);

  if (stage < 1 || stage > 6 || b[0] != '#') {
    fprintf(stderr, "stage must be 1..6 and the colour #RRGGBB\n");
    return 2;
  }
  if (do_read(fd, 0x14, r) != 0)
    return 1;
  memcpy(rgb, &r[4], sizeof(rgb));
  if (sscanf(b + 1, "%2hhx%2hhx%2hhx", &rgb[stage - 1][0], &rgb[stage - 1][1],
             &rgb[stage - 1][2]) != 3)
    return 2;

  ajz_set_dpi_colours(req, rgb);
  return apply(fd, req, 0x14, 18);
}

// "power sleep <10 s steps>", "power debounce <ms>" or
// "power wake-on-move|lights-off-on-move on|off". The official app offers sleep
// 1, 3, 6, 12, 30, 60, 120, 180 (10 s .. 30 min; factory 30 = 5 min) and clamps
// debounce to 0..20 ms (factory 8).
static int cmd_power(int fd, const char *what, const char *value) {
  uint8_t req[AJZ_REPORT_LEN], r[AJZ_REPORT_LEN];
  int v = atoi(value), on = strcmp(value, "on") == 0;
  int number = *value && value[strspn(value, "0123456789")] == '\0';

  if (do_read(fd, 0x17, r) != 0)
    return 1;
  if (strcmp(what, "sleep") == 0 && number && v >= 1 && v <= 255)
    r[4] = v;
  else if (strcmp(what, "wake-on-move") == 0)
    r[5] = on;
  else if (strcmp(what, "lights-off-on-move") == 0)
    r[6] = on;
  else if (strcmp(what, "debounce") == 0 && number && v <= 20)
    r[7] = v;
  else
    return 2;

  ajz_set_power(req, r[4], r[5], r[6], r[7]);
  return apply(fd, req, 0x17, 4);
}

// Buttons have no read command, so the last mapping written is kept here.
static const uint8_t factory_buttons[6][3] = {{0x10, 0x01, 0x00}, {0x10, 0x02, 0x00},
                                              {0x10, 0x04, 0x00}, {0x10, 0x08, 0x00},
                                              {0x10, 0x10, 0x00}, {0x40, 0x01, 0x00}};

static void config_file(char *path, size_t size, const char *name) {
  const char *xdg = getenv("XDG_CONFIG_HOME"), *home = getenv("HOME");

  if (xdg && *xdg)
    snprintf(path, size, "%s/ajazzctl", xdg);
  else
    snprintf(path, size, "%s/.config/ajazzctl", home ? home : ".");
  mkdir(path, 0755);
  strncat(path, "/", size - strlen(path) - 1);
  strncat(path, name, size - strlen(path) - 1);
}

static void load_buttons(uint8_t keys[6][3]) {
  char path[512];
  FILE *f;

  memcpy(keys, factory_buttons, sizeof(factory_buttons));
  config_file(path, sizeof(path), "buttons");
  f = fopen(path, "r");
  if (!f)
    return;
  for (int i = 0; i < 6; i++)
    if (fscanf(f, "%hhx %hhx %hhx", &keys[i][0], &keys[i][1], &keys[i][2]) != 3) {
      memcpy(keys, factory_buttons, sizeof(factory_buttons));
      break;
    }
  fclose(f);
}

// Macro text per button as last uploaded ("ctrl+c wait:50 ctrl+v"); the mouse cannot
// report its macros, so show reads them from here.
static void load_macros(char macros[6][512]) {
  char path[512], line[512], *text;
  FILE *f;
  long n;

  memset(macros, 0, 6 * sizeof(macros[0]));
  config_file(path, sizeof(path), "macros");
  f = fopen(path, "r");
  if (!f)
    return;
  while (fgets(line, sizeof(line), f)) {
    n = strtol(line, &text, 10);
    if (n < 1 || n > 6 || *text != ' ')
      continue;
    text[strcspn(text, "\n")] = '\0';
    snprintf(macros[n - 1], sizeof(macros[0]), "%s", text + 1);
  }
  fclose(f);
}

static void save_macro(int n, const char *text) {
  char macros[6][512], path[512];
  FILE *f;

  load_macros(macros);
  snprintf(macros[n - 1], sizeof(macros[0]), "%s", text);
  config_file(path, sizeof(path), "macros");
  f = fopen(path, "w");
  if (!f)
    return;
  for (int i = 0; i < 6; i++)
    if (macros[i][0])
      fprintf(f, "%d %s\n", i + 1, macros[i]);
  fclose(f);
}

static int write_buttons(int fd, const uint8_t keys[6][3]) {
  uint8_t req[AJZ_REPORT_LEN], reply[AJZ_REPORT_LEN];
  char path[512];
  FILE *f;

  ajz_set_buttons(req, keys);
  if (exchange(fd, req, reply) != 0)
    return 1;

  config_file(path, sizeof(path), "buttons");
  f = fopen(path, "w");
  if (f) {
    for (int i = 0; i < 6; i++)
      fprintf(f, "%02x %02x %02x\n", keys[i][0], keys[i][1], keys[i][2]);
    fclose(f);
  }
  printf("ok (acknowledged - the mouse has no read-back for buttons)\n");
  return 0;
}

// "button <2-6> <function>"; button 1 (left click) stays locked like in the
// vendor app, so the mouse can always be used to undo a mistake.
static int cmd_button(int fd, const char *num, const char *function) {
  uint8_t keys[6][3], code[3];
  int n = atoi(num);

  if (n < 2 || n > 6) {
    fprintf(stderr, "button must be 2..6 (1 = left click is locked)\n");
    return 2;
  }
  if (ajz_button_code(function, code) != 0) {
    fprintf(stderr, "unknown function '%s'\n", function);
    return 2;
  }
  load_buttons(keys);
  memcpy(keys[n - 1], code, 3);
  return write_buttons(fd, keys);
}

// "macro <2-6> <token>..."; the macro is stored in the slot of that button and
// the button is set to play it once.
static int cmd_macro(int fd, int argc, char *argv[]) {
  uint8_t events[AJZ_MACRO_MAX_EVENTS][4], out[15][AJZ_REPORT_LEN];
  uint8_t reply[AJZ_REPORT_LEN], keys[6][3];
  char text[512] = "";
  int n = atoi(argv[0]), count, ev;

  if (n < 2 || n > 6) {
    fprintf(stderr, "button must be 2..6 (1 = left click is locked)\n");
    return 2;
  }
  for (int i = 1; i < argc; i++) {
    strncat(text, argv[i], sizeof(text) - strlen(text) - 2);
    strcat(text, " ");
  }
  ev = ajz_macro_parse(text, events, AJZ_MACRO_MAX_EVENTS);
  if (ev < 0) {
    fprintf(stderr, "cannot parse macro '%s'\n", text);
    return 2;
  }

  count = ajz_macro_packets(n - 1, events, ev, out);
  for (int i = 0; i < count; i++)
    if (exchange(fd, out[i], reply) != 0)
      return 1;

  load_buttons(keys);
  ajz_macro_button(n - 1, keys[n - 1]);
  if (write_buttons(fd, keys) != 0)
    return 1;
  text[strlen(text) - 1] = '\0'; // drop the trailing space
  save_macro(n, text);
  return 0;
}

static int usage(void) {
  fprintf(stderr,
          "usage: ajazzctl info | show [--json]\n"
          "       ajazzctl rate 125|250|500|1000\n"
          "       ajazzctl dpi <stage> <value> | dpi select <stage>\n"
          "       ajazzctl lighting off|breathing|constant [#RRGGBB] [brightness speed]\n"
          "       ajazzctl dpi-colour <stage> #RRGGBB\n"
          "       ajazzctl sensor lod 1|2 | sensor motion-sync|angle-snap on|off\n"
          "       ajazzctl power sleep <10 s steps> | power debounce <0-20 ms>\n"
          "       ajazzctl power wake-on-move|lights-off-on-move on|off\n"
          "       ajazzctl button <2-6> <function> | buttons reset\n"
          "         buttons: 1 left (locked) 2 right 3 middle 4 back 5 forward 6 dpi\n"
          "         functions: left right middle back forward scroll-up scroll-down\n"
          "           dpi-loop dpi-up dpi-down play-pause stop previous next volume-up\n"
          "           volume-down mute\n"
          "           key:[ctrl+][shift+][alt+][super+]<a-z|0-9|f1-f12|enter|esc|tab|space|backspace>\n"
          "       ajazzctl macro <2-6> <[mod+]key|wait:ms>...  e.g. macro 4 ctrl+c wait:50 ctrl+v\n"
          "       ajazzctl read <cmd-hex>   (10 12 13 14 15 16 17 20)\n");
  return 2;
}

int main(int argc, char *argv[]) {
  const char *c = argc > 1 ? argv[1] : "";
  int fd, ret;

  if (!((argc == 2 && (strcmp(c, "info") == 0 || strcmp(c, "show") == 0)) ||
        (argc == 3 && strcmp(c, "show") == 0 && strcmp(argv[2], "--json") == 0) ||
        (argc == 3 && (strcmp(c, "read") == 0 || strcmp(c, "rate") == 0 ||
                       (strcmp(c, "buttons") == 0 && strcmp(argv[2], "reset") == 0))) ||
        (argc == 4 && strcmp(c, "button") == 0) ||
        (argc == 4 && (strcmp(c, "dpi") == 0 || strcmp(c, "sensor") == 0 ||
                       strcmp(c, "dpi-colour") == 0 || strcmp(c, "power") == 0)) ||
        (argc >= 3 && strcmp(c, "lighting") == 0) ||
        (argc >= 4 && strcmp(c, "macro") == 0)))
    return usage();

  fd = open_receiver();
  if (fd < 0)
    return 1;

  if (strcmp(c, "info") == 0)
    ret = cmd_info(fd);
  else if (strcmp(c, "show") == 0)
    ret = cmd_show(fd, argc == 3);
  else if (strcmp(c, "read") == 0)
    ret = cmd_read(fd, argv[2]);
  else if (strcmp(c, "rate") == 0)
    ret = cmd_rate(fd, argv[2]);
  else if (strcmp(c, "dpi") == 0)
    ret = cmd_dpi(fd, argv[2], argv[3]);
  else if (strcmp(c, "sensor") == 0)
    ret = cmd_sensor(fd, argv[2], argv[3]);
  else if (strcmp(c, "dpi-colour") == 0)
    ret = cmd_dpi_colour(fd, argv[2], argv[3]);
  else if (strcmp(c, "power") == 0)
    ret = cmd_power(fd, argv[2], argv[3]);
  else if (strcmp(c, "button") == 0)
    ret = cmd_button(fd, argv[2], argv[3]);
  else if (strcmp(c, "buttons") == 0)
    ret = write_buttons(fd, factory_buttons);
  else if (strcmp(c, "macro") == 0)
    ret = cmd_macro(fd, argc - 2, argv + 2);
  else
    ret = cmd_lighting(fd, argc - 2, argv + 2);

  close(fd);
  if (ret == 2)
    usage();
  return ret;
}
