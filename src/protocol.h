#ifndef AJZ_PROTOCOL_H
#define AJZ_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

// AJ179 receiver vendor protocol. Byte layouts and their sources are in
// PROTOCOL.md.

#define AJZ_REPORT_LEN 32
#define AJZ_CMD_INFO 0x10
#define AJZ_STATUS_REPORT 0xC0
#define AJZ_STATUS_NO_ANSWER 0x01 // mouse connected but did not answer the relay
#define AJZ_STATUS_ASLEEP 0x02    // reply status while the mouse is not connected

struct ajz_info {
  char id[5];        // device id, e.g. "M179"
  uint8_t sensor;    // selects DPI range and encoding
  uint8_t rate_caps; // report-rate capability
  uint8_t charging;
  uint8_t battery;   // percent
  uint8_t connected; // 0 when only the receiver answers
};

#define AJZ_LIGHT_OFF 0
#define AJZ_LIGHT_FLOWING 1
#define AJZ_LIGHT_BREATHING 2
#define AJZ_LIGHT_CONSTANT 3
#define AJZ_LIGHT_NEON 4
#define AJZ_LIGHT_WAVE 5

int ajz_dpi_encode(uint8_t sensor, int dpi);
int ajz_dpi_decode(uint8_t sensor, int raw);
void ajz_dpi_range(uint8_t sensor, int *min, int *max);
int ajz_rate_flag(int hz);
int ajz_rate_hz(int flag);

int ajz_set_dpi(uint8_t f[AJZ_REPORT_LEN], uint8_t sensor, int index, int count,
                const int dpi[6]);
int ajz_parse_dpi(const uint8_t r[AJZ_REPORT_LEN], uint8_t sensor, int *index,
                  int *count, int dpi[6]);
void ajz_set_rate(uint8_t f[AJZ_REPORT_LEN], uint8_t flag);
int ajz_set_lighting(uint8_t f[AJZ_REPORT_LEN], int mode, int brightness,
                     int speed, const uint8_t rgb[3]);
int ajz_set_sensor(uint8_t f[AJZ_REPORT_LEN], int lod, int motion_sync,
                   int angle_snap);
int ajz_button_code(const char *name, uint8_t code[3]);
// The name ajz_button_code takes for a code ("macro" for macro slots); -1 if unknown.
int ajz_button_name(const uint8_t code[3], char *out, size_t size);

// Macros: payload is split into at most 15 packets of 27 bytes.
#define AJZ_MACRO_MAX_EVENTS 101
#define AJZ_MACRO_GAP_MS 10
int ajz_macro_parse(const char *text, uint8_t events[][4], int max);
int ajz_macro_packets(int slot, const uint8_t events[][4], int n,
                      uint8_t out[15][AJZ_REPORT_LEN]);
void ajz_macro_button(int slot, uint8_t code[3]);
void ajz_set_buttons(uint8_t f[AJZ_REPORT_LEN], const uint8_t keys[6][3]);
void ajz_set_dpi_colours(uint8_t f[AJZ_REPORT_LEN], const uint8_t rgb[6][3]);
void ajz_set_power(uint8_t f[AJZ_REPORT_LEN], uint8_t sleep, uint8_t wake_on_move,
                   uint8_t lights_off_on_move, uint8_t debounce);

int ajz_is_read_cmd(uint8_t cmd);
void ajz_build(uint8_t f[AJZ_REPORT_LEN], uint8_t cmd, uint8_t seq, uint8_t len,
               const uint8_t *payload, int n);
int ajz_parse_info(const uint8_t r[AJZ_REPORT_LEN], struct ajz_info *info);
int ajz_info_battery(const struct ajz_info *info);
int ajz_parse_status(const uint8_t r[AJZ_REPORT_LEN], int *online,
                     int *battery);

#endif
