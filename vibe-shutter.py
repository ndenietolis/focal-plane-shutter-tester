from machine import Pin, I2C
import time
import ssd1306
import rp2

# --------------------
# OLED setup
# --------------------
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# --------------------
# Sensor setup
# Using internal pullups:
# dark  = HIGH
# light = LOW
# --------------------
sensor_pins = [11, 12, 13]  # A, B, C
sensors = [Pin(p, Pin.IN, Pin.PULL_UP) for p in sensor_pins]

start_us = [0, 0, 0]
end_us = [0, 0, 0]
measuring = [False, False, False]
done = [False, False, False]

last_ms = [None, None, None]
last_approx = ["---", "---", "---"]
last_actual = ["---", "---", "---"]
last_start_us = [None, None, None]
last_end_us = [None, None, None]

screen_mode = 0
button_was_pressed = False
button_press_ms = 0
BUTTON_RESET_MS = 1000
BUTTON_LEAF_MS = 2000


# --------------------
# Formatting
# --------------------
def nearest_shutter_speed(seconds):
    if seconds <= 0:
        return "---"

    speeds = [
        1/8000, 1/4000, 1/2000, 1/1000, 1/500, 1/250,
        1/125, 1/60, 1/30, 1/15, 1/8, 1/4,
        1/2, 1, 1.4, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30
    ]

    nearest = min(speeds, key=lambda x: abs(x - seconds))

    if nearest >= 1:
        if nearest == int(nearest):
            return f"{int(nearest)}"
        return f"{nearest:.1f}"

    denom = round(1 / nearest)
    return f"1/{denom}"


def actual_shutter_speed(seconds):
    if seconds <= 0:
        return "---"

    if seconds >= 1:
        return f"{seconds:.1f}s"

    return f"1/{1 / seconds:.0f}"


# --------------------
# Display screens
# --------------------
def draw_results_screen():
    oled.fill(0)

    oled.text("Shutter Tester", 8, 0)

    oled.text("A", 14, 12)
    oled.text("B", 56, 12)
    oled.text("C", 98, 12)

    for i in range(3):
        x = i * 42

        if last_ms[i] is None:
            ms_text = "---"
            approx_text = "---"
            actual_text = "---"
        else:
            ms_text = f"{last_ms[i]:.1f}"
            approx_text = last_approx[i]
            actual_text = last_actual[i]

        oled.text(ms_text, x, 26)
        oled.text(approx_text, x, 38)
        oled.text(actual_text, x, 50)

    oled.show()


def draw_diagnostic_screen():
    oled.fill(0)

    if None in last_start_us or None in last_end_us:
        oled.text("Spread: ---", 0, 0)
        oled.text("Need A B C data", 4, 22)
        oled.text("Fire shutter", 18, 38)
        oled.show()
        return

    # Start-time travel across sensors
    ab_ms = time.ticks_diff(last_start_us[1], last_start_us[0]) / 1000
    bc_ms = time.ticks_diff(last_start_us[2], last_start_us[1]) / 1000
    ac_ms = time.ticks_diff(last_start_us[2], last_start_us[0]) / 1000

    # Exposure consistency across sensors
    valid = [m for m in last_ms if m is not None]
    spread_ms = max(valid) - min(valid)
    average_ms = sum(valid) / len(valid)
    spread_pct = (spread_ms / average_ms * 100) if average_ms > 0 else 0

    if ac_ms > 0:
        direction = "A > C"
    elif ac_ms < 0:
        direction = "C > A"
    else:
        direction = "---"

    oled.text(f"Spread:{spread_pct:.1f}%", 0, 0)

    if spread_pct < 5.0:
        bal = "GOOD"
    elif spread_pct > 20.0:
        bal = "BAD"
    else:
        bal = "OK"

    oled.text(bal, 96, 0)
    oled.text(f"Dir: {direction}", 0, 12)
    oled.text(f"A-B:{abs(ab_ms):.2f}ms", 0, 24)
    oled.text(f"B-C:{abs(bc_ms):.2f}ms", 0, 36)
    oled.text(f"Travel:{abs(ac_ms):.2f}ms", 0, 48)

    oled.show()


def draw_leaf_screen():
    oled.fill(0)

    oled.text("Leaf Shutter", 20, 0)
    oled.text("Center / B", 28, 12)

    if last_ms[1] is None:
        oled.text("Fire shutter", 18, 30)
        oled.text("Need B data", 24, 42)
        oled.show()
        return

    oled.text(f"{last_ms[1]:.1f} ms", 18, 28)
    oled.text(last_approx[1], 18, 40)
    oled.text(last_actual[1], 70, 40)

    oled.show()


def draw_screen():
    if screen_mode == 0:
        draw_results_screen()
    elif screen_mode == 1:
        draw_diagnostic_screen()
    else:
        draw_leaf_screen()

def reset_readings():
    global last_ms, last_approx, last_actual
    global last_start_us, last_end_us

    last_ms = [None, None, None]
    last_approx = ["---", "---", "---"]
    last_actual = ["---", "---", "---"]
    last_start_us = [None, None, None]
    last_end_us = [None, None, None]

    draw_screen()
    

# --------------------
# Interrupt handling
# --------------------
def make_irq(index):
    def handler(pin):
        value = pin.value()

        # Light starts: falling edge
        if value == 0 and not measuring[index]:
            start_us[index] = time.ticks_us()
            measuring[index] = True
            done[index] = False

        # Light ends: rising edge
        elif value == 1 and measuring[index]:
            end_us[index] = time.ticks_us()
            measuring[index] = False
            done[index] = True

    return handler


for i, sensor in enumerate(sensors):
    sensor.irq(
        trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
        handler=make_irq(i)
    )


# --------------------
# Startup screen
# --------------------
oled.fill(0)
oled.text("Shutter Tester", 8, 0)
oled.text("A B C sensors", 12, 22)
oled.text("Ready", 44, 42)
oled.show()
time.sleep(1)
draw_screen()


# --------------------
# Main loop
# --------------------
while True:
    screen_changed = False

    button_pressed = rp2.bootsel_button()
    now_ms = time.ticks_ms()

    if button_pressed and not button_was_pressed:
        button_press_ms = now_ms

    if not button_pressed and button_was_pressed:
        hold_ms = time.ticks_diff(now_ms, button_press_ms)

        if hold_ms >= BUTTON_LEAF_MS:
            if screen_mode == 2:
                screen_mode = 0
            else:
                screen_mode = 2
            screen_changed = True
        elif hold_ms >= BUTTON_RESET_MS:
            reset_readings()
        else:
            if screen_mode != 2:
                screen_mode = 1 - screen_mode
                screen_changed = True

    button_was_pressed = button_pressed

    for i in range(3):
        if done[i]:
            duration_us = time.ticks_diff(end_us[i], start_us[i])
            duration_s = duration_us / 1_000_000

            last_ms[i] = duration_us / 1000
            last_approx[i] = nearest_shutter_speed(duration_s)
            last_actual[i] = actual_shutter_speed(duration_s)
            last_start_us[i] = start_us[i]
            last_end_us[i] = end_us[i]

            print(
                f"{chr(65+i)}: "
                f"{last_ms[i]:.3f} ms, "
                f"approx {last_approx[i]}, "
                f"actual {last_actual[i]}"
            )

            done[i] = False
            screen_changed = True

    if screen_changed:
        draw_screen()

    time.sleep(0.01)
