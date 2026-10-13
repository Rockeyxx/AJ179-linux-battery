# AJ179 dual-mode — 2.4 GHz receiver protocol

Reverse engineered from the official **AJAZZ Driver (X) 1.0.7.0** (`AJAZZ Driver (X).exe`,
sha256 `db33308a…efafe`) by static decompilation. Addresses below are in that binary.

Status legend: **[code]** read directly from decompiled code · **[code+wire]** code agrees
with captured traffic · **[open]** not yet resolved.

## Device

| Mode | VID:PID | Config interface | Device type (app) |
|---|---|---|---|
| 2.4 GHz receiver | `249A:5C2F` | MI_02 (`hidraw` on `:1.2`) | 105, dev_id `M179` or `M603` |
| USB cable | `248A:5C2E` / `5D2E` / `5E2E` | MI_02 (same descriptor) | 105; same protocol, verified on `5C2E` |

Source: `config.xml`, `device/mouse_aj179.xml`. Interface 2 has no report IDs:
32-byte input, 32-byte output.

The app statically links **hidapi** (`hid_init` 0x44d6a0, `hid_enumerate` 0x44d7b0,
`hid_open_path` 0x44dc30, `hid_write` 0x44ddd0, `hid_read_timeout` 0x44deb0).
Device types > 200 use a different feature-report (`0x0C`) protocol — not this mouse.

## Framing [code]

Every request and reply is one 32-byte report (`data[0..31]`; on Linux write 33 bytes
with a leading `00` report ID). Replies to read commands use the same payload layout
as the matching write command.

```
data[0]      command
data[1]      0x00 in requests; 0x00 in a reply means OK
data[2]      (chunk_index << 4) | chunk_count   — 0x01 for single-packet writes,
                                                  0x00 for reads
data[3]      payload length
data[4..30]  payload (max 27 bytes), zero padded
data[31]     checksum = sum(data[4..30]) & 0xFF
```

Checksum: `sub_44b790` 0x44b790. Chunking: macro upload 0x433ed0.

Transaction (`sub_44b790`): write, then read up to 50 × 30 ms until a report arrives with
**`data[1] == 0x00`**; that report is the reply. `data[0]` is not checked.

Live behaviour (2026-10-13) **[wire]** — our implementation differs from the vendor here:
- Replies echo the command in `data[0]`. Match on that: the receiver also pushes
  `c0 00 <bat>` when the mouse falls asleep, which the vendor rule would take as a reply.
- `data[1]` is a status: `00` OK, `01` the mouse is connected but did not answer the
  relayed request (arrived 1.55 s after the request, mouse idle), `02` mouse asleep /
  not connected (immediate). Only `0x10` is answered by the receiver itself; everything
  else needs the mouse awake and active. Wait ≥ 3 s for a reply.
- Reply lengths can differ from the write: `0x13` reports `len 0x19`, `0x17` `len 5`.
- Over the USB cable every command is answered by the mouse in ~2 ms; there is no idle
  or asleep status. The receiver then reports the mouse as not connected (info byte 14 = 0).
- Cable and receiver share one set of settings: a stage-6 colour written over the cable
  (`#ff00fe`) read back unchanged through the receiver after unplugging.

## Status frames [code]

Unsolicited input reports with `data[0] == 0xC0` (pollers 0x44b8d0, 0x44bb10, 0x44bc60):
`data[1] == 1` → mouse online, otherwise offline. When it goes online the app sends `0x10`.
Battery in `data[2]` **[code+wire]** (existing daemon; not read by the app).

## Commands

### Live verification (2026-10-13, AJ179 dual mode, receiver fw 41.01)

All reads below returned valid replies. These writes were acknowledged and confirmed by
read-back, then reverted: `0x02` (1000→500→1000 Hz), `0x03` (stage select, stage value),
`0x05` (constant colour), `0x06` (LOD, Motion Sync, Angle Snap), `0x04` (stage colour),
`0x07` (wake-on-move, lights-off-on-move; sleep/debounce rewritten unchanged).
`0x09` verified through evdev: button 4 (rear side) remapped to `20 01 00` produced
REL_WHEEL +1, factory table restored BTN_SIDE (rear) / BTN_EXTRA (front). `0x08` + button
code `90 23 01`: macro "a b" in slot 3 played KEY_A, KEY_B on the rear button. Factory-state readback:
1000 Hz · DPI 400/800/1200/1600/2400/3200 · constant light · LOD 2 · sleep 30 · debounce 8.

### Reads (sync from mouse, 0x431350)

All reads are `<cmd> 00 00 00 …` (zero payload). The app only issues them when the
`0x10` reply says the mouse is connected (byte 14 ≠ 0).

| cmd | reply payload | source |
|---|---|---|
| 0x10 | device info, see below | 0x44b510, 0x44c16c |
| 0x11 | sent first; reply not used **[open]** | 0x431876 |
| 0x12 | `[4]` report rate | 0x4318b4 |
| 0x13 | `[4]` `(index << 4) \| count`; stage *i* raw DPI = `[5+4i] \| [6+4i] << 8` | 0x431984 |
| 0x14 | stage *i* colour = `R G B` at `[4+3i]` | 0x431db2 |
| 0x15 | `[4]` lighting mode, `[5]` `(brightness << 4) \| speed` | 0x432076 |
| 0x16 | `[4]` lift-off, `[5]` flag bit 8, `[6]` flag bit 4 (1 = set) | 0x432136 |
| 0x17 | `[4]` sleep_light `[5]` move_wakeup `[6]` move_closelight `[7]` button_respond_time | 0x432231 |
| 0x20 | receiver firmware `"%x.%02x"` from `[4]`,`[5]`; 2.4 GHz only | 0x4323e6 |

### 0x10 — get device info [code]

Request `10 00 00 00 …`. Sent by the app whenever the receiver opens or the mouse comes
online, so it is safe to send.

Live replies from this mouse (2026-10-13), asleep then awake:

```
10 00 01 0b 4d 31 37 39 00 00 95 01 00 52 00 00 … 00 d6   (82 %, mouse asleep)
10 00 01 0b 4d 31 37 39 00 00 95 01 00 51 01 00 … 00 d6   (81 %, mouse awake)
```

Replies echo the command in byte 0, use the request header layout (`seq` 01, `len` 0x0b)
and carry a valid checksum in byte 31.

| byte | meaning | source |
|---|---|---|
| 1 | `00` = OK | 0x44b510 **[code+wire]** |
| 4..7 | device id, 4 ASCII chars: `M179` | 0x44c190 **[code+wire]** |
| 8..9 | `41 01` over the cable, `00 00` via the receiver — likely the mouse firmware version (41.01) **[wire, meaning inferred]** | 0x431460 |
| 10 | **sensor id**: `0x95` = PAW3395 (selects DPI range and encoding) | 0x431477 **[code+wire]** |
| 11 | rate capability, `0x01` here; the app maps `0x10`→4 options, `0x20`→6, `0x40`→7, else 5 **[open]** | 0x43178b |
| 12 | charging: `01` with the cable plugged in, `00` on battery | 0x4317ba **[code+wire]** |
| 13 | **battery %**, still reported while the mouse sleeps | 0x4317ba **[code+wire]** |
| 14 | wireless mouse connected; 0 = asleep / out of range (app logs "无线设备未连接", *wireless device not connected*, and skips the settings sync) | 0x431807 **[code+wire]** |

Sensor id → DPI range (0x431350): `0x95` 50–26000 (PAW3395) · `0x96` 50–32000 ·
`0x11` 50–18000 · `0x05` 50–12000 · `0x35` 100–16000 · `0x25` 100–10000 ·
`0x26` 200–10000 · `0x04` 100–8000 · `0x10`/`0x12` 100–4800 · other 50–26000.

### 0x02 — set report rate [code] (0x435555)
`02 00 01 01 <rate>`. Rate is a bit flag (list builder 0x41d989):

| value | 0x08 | 0x04 | 0x02 | 0x01 | 0x10 | 0x20 | 0x40 |
|---|---|---|---|---|---|---|---|
| rate | 125 Hz | 250 Hz | 500 Hz | 1000 Hz | 2 kHz | 4 kHz | 8 kHz |

AJ179 dual mode: 125–1000 Hz only (info byte 11 = `0x10`), default `0x01`.

### 0x03 — set DPI stages [code] (0x434bcf)
`03 00 01 25 <(index << 4) | count>` then 6 × `<lo hi lo hi>` (X then Y, same value).
`index` is 0-based. Each DPI is clamped to the sensor range and encoded by
`sub_41e330(sensor_id, dpi)`; `sub_41e490` decodes:

| sensor id | encode | decode |
|---|---|---|
| 0x95, unknown | `dpi/50 - 1` | `(raw+1)*50` |
| 0x96 | `dpi/50 - 1`; > 26000 → `519 + (dpi-26000)/1000` | `(raw+1)*50`; raw ≥ 521 → `(raw-494)*1000` (vendor off-by-one) |
| 0x11 | `dpi/50`; > 10000 → `200 + (dpi-10000)/100`; ≥ 13000 → `221 + (dpi-13000)/1000` | inverse |
| 0x05 | `dpi/50`; > 6400 → `128 + (dpi-6400)/100` | inverse |
| 0x25 | `dpi/100`; > 5000 → `50 + (dpi-5000)/500` | inverse |
| 0x26 | `dpi/100 - 1`; > 5000 → `50 + (dpi-5000)/500` | inverse |
| 4, 16, 18, 53 | `dpi/100` | `raw*100` |

### 0x04 — set DPI stage colours [code] (0x4351f0)
`04 00 01 12` then 6 × `R G B`.

### 0x05 — set lighting [code] (0x434690)
`05 00 01 <len> <mode> <(brightness << 4) | speed> …`

| mode | len | extra payload |
|---|---|---|
| 0, 4, 5 | 2 | — |
| 1 | 3 | one zero byte |
| 2 | 0x18 | `07` + 7 × `R G B` |
| 3 | 5 | `R G B` |

Modes: 0 off, 1 flowing, 2 breathing, 3 constant, 4 neon, 5 colour wave. 0/2/3 are
**[code+wire]** (match captured traffic); 1/4/5 inferred from the XML `light_N` order and
disabled for the AJ179. Brightness and speed are 0–4 each.

### 0x06 — set lift-off distance / sensor flags [code] (0x435706)
`06 00 01 05 <lod> <motion_sync> <angle_snap>` (each 0/1)

- `lod`: 1 = low (1 mm), 2 = high (2 mm) (UI 0x41dff3)
- `motion_sync` = `sensor_flag` bit 8, `angle_snap` = bit 4. Labels from checkbox
  string ids 0x205 / 0x204 (0x43c676, 0x43c700). Bit 0x10 (third checkbox) is never sent
  for this device type.

### 0x07 — set power and debounce [code] (0x4359bb)
`07 00 01 04 <sleep_light> <move_wakeup> <move_closelight> <button_respond_time>`

Units of `sleep_light` and `button_respond_time` **[open]** (XML default sleep 30;
read the current values with `0x17`).

### 0x08 — upload macro [code] (0x433ed0, serializer 0x41cc90)
Payload = `<slot>` + 4 bytes per event; `slot` = the button index the macro is bound to.
≤ 6 events: one packet, `len = 4n+1`. Longer: split into 27-byte chunks with
`data[2] = (i << 4) | chunk_count`.

Event = `<type> <delay_lo> <delay_hi> <code>`; delay (ms, ≥ 1) is the pause *after* the event.

| type | event | code |
|---|---|---|
| 0x10 / 0x90 | mouse button down / up | button mask (`01` L, `02` R, `04` M, `08` back, `10` fwd) |
| 0x30 / 0xB0 | key down / up | HID keyboard usage (VK→HID table 0x44e130) |
| 0x20 / 0xA0 | modifier down / up | HID modifier bit (`01` LCtrl `02` LShift `04` LAlt `08` LGui `10` RCtrl `20` RShift `40` RAlt `80` RGui; 0x44e740) |

Vendor bug: the Windows keys (VK 0x5B/0x5D) release is emitted as `0x20` (press).

### 0x09 — set button mapping [code] (0x432d9c)
`09 00 01 0F` + 3 bytes per button, buttons 0–5, zero padded. (Length byte is 0x0F
even though button 5's bytes follow — replicate exactly.) Factory table:
`10 01 00 · 10 02 00 · 10 04 00 · 10 08 00 · 10 10 00 · 40 01 00`
(left, right, middle, back, forward, DPI button).

| byte 0 | function | bytes 1–2 |
|---|---|---|
| 0x10 | mouse button | mask (as above); scroll left/right `00 F5` / `00 F6` |
| 0x20 | wheel | `01` up / `FF` down |
| 0x30 | repeat ("fire") | count, interval |
| 0x40 | DPI | `01`, `02`, `03` (loop / + / − — which is which **[open]**) |
| 0x60 | special | `04`, `01`; `00 00` = disabled **[open]** |
| 0x70 | keyboard | modifier mask, HID usage |
| 0x80 | consumer | 16-bit LE usage (`CD` play, `B5` next, `B6` prev, `B7` stop, `E9` vol+, `EA` vol−, `E2` mute, `0183` player, `0192` calculator, `0194` my computer, `0223` web, `018A` mail, `6F`/`70` brightness) |
| 0x90 | macro | `slot \| mode`, loops: mode `0x10` until release, `0x40` until any click, `0x20` + count = N times |

No read-back command for buttons exists; the app keeps them in its local database.

### Resets [code]
| packet | effect | source |
|---|---|---|
| `0D 00 01 01 01` | report rate to default, then app reads `0x12` | 0x4363ea |
| `0E 00 01 01 01` | lighting to default, then app reads `0x15` | 0x435c35 |
| `0F 00 01 01 FF` | **factory reset**, then app re-reads everything | 0x4366d2 |

### Still open
- `0x11` purpose (sent before reads, reply ignored)
- units of sleep / debounce; DPI-button and `0x60` code meanings
- info bytes 8–9

## Never send
Firmware flasher: 0x412700–0x412980 (64-byte reports via 0x44cdc0, UI string 592
"Writing device data", `%s: %d%%` progress). Not implemented, by design. Unknown command
bytes are never probed.
