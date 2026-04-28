# Shutter Tester

MicroPython shutter tester for the Raspberry Pi Pico. It reads three light sensors, measures shutter timings, and shows the latest results on a small OLED display.

## Files

- `vibe-shutter.py` - main firmware application
- `ssd1306.py` - OLED driver used by the display
- `deploy.sh` - copies the firmware to a Pico with `mpremote`

## Requirements

- Raspberry Pi Pico running MicroPython
- `mpremote` installed on your computer
- OLED display wired to I2C pins `GP16` / `GP17`
- Three light sensors wired to `GP11`, `GP12`, and `GP13`

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

- Short press BOOTSEL: toggle between the results screen and the diagnostic screen
- Hold BOOTSEL for 1 second: reset the last readings
