# Shutter Tester

MicroPython shutter tester for the Raspberry Pi Pico. It reads five light sensors arranged in a line, measures shutter timings, and shows the latest results on a small OLED display.

## Files

- `vibe-shutter.py` - main firmware application
- `ssd1306.py` - OLED driver used by the display
- `deploy.sh` - copies the firmware to a Pico with `mpremote`

## Requirements

- Raspberry Pi Pico running MicroPython
- `mpremote` installed on your computer
- OLED display wired to I2C pins `GP16` / `GP17`
- Five `SFH 309` phototransistors wired in a straight line
- Two buttons wired to `GP7` and `GP8`
- One LED driver transistor wired to `GP6`

## Wiring

This build uses five `SFH 309` phototransistors. The Pico's internal pull-up resistors are used, so there are no external resistors in the sensor circuit.

The sensor line is wired like this:

- `GP9`
- `GP10`
- `GP11`
- `GP12`
- `GP13`

Wire each sensor like this:

- `SFH 309` collector -> Pico input pin
- `SFH 309` emitter -> Pico `GND`

The firmware configures the sensor pins with internal pull-ups, so the input reads `HIGH` in the dark and goes `LOW` when light hits the sensor.

Buttons:

- `GP7` -> view button
- `GP8` -> LED / format button

LED driver:

- `GP6` -> transistor base through `1k` to `4.7k`
- transistor emitter -> `GND`
- transistor collector -> LED cathode
- `3V3` -> `220 ohm` -> LED anode

OLED wiring:

- `VCC` -> Pico `3V3`
- `GND` -> Pico `GND`
- `SDA` -> Pico `GP16`
- `SCL` -> Pico `GP17`

## Deploy

Connect the Pico by USB, then run:

```bash
./deploy.sh
```

The deploy script copies:

- `vibe-shutter.py` to `main.py` on the Pico
- `ssd1306.py` to `ssd1306.py` on the Pico

After copying, it resets the board so the updated firmware starts immediately.

## Controls

- Short press `GP7`: switch between time and travel views
- Hold `GP7` for 1 second: reset the last readings
- Short press `GP8`: toggle the LED
- Hold `GP8` for 1 second: switch between leaf shutter, 35mm, and 4x5 modes

## Modes

- Leaf shutter: uses sensor `GP11` and shows a single time view
- 35mm: uses sensors `GP12`, `GP11`, and `GP10`, with time and travel views
- 4x5: uses sensors `GP13`, `GP11`, and `GP9`, with time and travel views
