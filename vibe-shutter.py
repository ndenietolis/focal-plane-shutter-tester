from machine import Pin, I2C
import time
import ssd1306

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
SENSOR_SPECS = [
    {"pin": 9, "label": "9"},
    {"pin": 10, "label": "10"},
    {"pin": 11, "label": "11"},
    {"pin": 12, "label": "12"},
    {"pin": 13, "label": "13"},
]

BUTTON_VIEW_PIN = 7
BUTTON_MODE_PIN = 8
LED_PIN = 6

sensor_pins = [spec["pin"] for spec in SENSOR_SPECS]
sensors = [Pin(p, Pin.IN, Pin.PULL_UP) for p in sensor_pins]
pin_to_index = {spec["pin"]: i for i, spec in enumerate(SENSOR_SPECS)}
LEAF_INDEX = pin_to_index[11]
THIRTYFIVE_INDICES = [pin_to_index[12], pin_to_index[11], pin_to_index[10]]
FOURFIVE_INDICES = [pin_to_index[13], pin_to_index[11], pin_to_index[9]]

button_view = Pin(BUTTON_VIEW_PIN, Pin.IN, Pin.PULL_UP)
button_mode = Pin(BUTTON_MODE_PIN, Pin.IN, Pin.PULL_UP)
led = Pin(LED_PIN, Pin.OUT)
led_on = False
led.value(0)
buttons = {
    BUTTON_VIEW_PIN: button_view,
    BUTTON_MODE_PIN: button_mode,
}
button_was_pressed = {
    BUTTON_VIEW_PIN: False,
    BUTTON_MODE_PIN: False,
}
button_press_ms = {
    BUTTON_VIEW_PIN: 0,
    BUTTON_MODE_PIN: 0,
}

MODE_LEAF = 0
MODE_35MM = 1
MODE_4X5 = 2
VIEW_TIME = 0
VIEW_TRAVEL = 1
BUTTON_RESET_MS = 1000

MODE_SPECS = [
    {
        "name": "Leaf",
        "title": "Leaf Shutter",
        "indices": [LEAF_INDEX],
        "travel": False,
    },
    {
        "name": "35mm",
        "title": "35mm Shutter",
        "indices": THIRTYFIVE_INDICES,
        "travel": True,
    },
    {
        "name": "4x5",
        "title": "4x5 Shutter",
        "indices": FOURFIVE_INDICES,
        "travel": True,
    },
]

start_us = [0] * len(SENSOR_SPECS)
end_us = [0] * len(SENSOR_SPECS)
measuring = [False] * len(SENSOR_SPECS)
done = [False] * len(SENSOR_SPECS)

last_ms = [None] * len(SENSOR_SPECS)
last_approx = ["---"] * len(SENSOR_SPECS)
last_actual = ["---"] * len(SENSOR_SPECS)
last_start_us = [None] * len(SENSOR_SPECS)
last_end_us = [None] * len(SENSOR_SPECS)

screen_mode = MODE_LEAF
view_mode = VIEW_TIME


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


def format_ms_value(value):
    if value is None:
        return "---"
    return f"{value:.1f}"


def current_mode_spec():
    return MODE_SPECS[screen_mode]


def toggle_led():
    global led_on
    led_on = not led_on
    led.value(1 if led_on else 0)


# --------------------
# Display screens
# --------------------
def draw_time_screen():
    spec = current_mode_spec()
    indices = spec["indices"]

    oled.fill(0)
    oled.text(spec["title"], 0, 0)
    oled.text("Time", 100, 0)

    for row, index in enumerate(indices):
        y = 14 + (row * 16)
        oled.text(f"{SENSOR_SPECS[index]['label']}", 0, y)
        oled.text(f"{format_ms_value(last_ms[index])} ms", 24, y)
        oled.text(last_approx[index], 86, y)

    oled.show()


def draw_travel_screen():
    spec = current_mode_spec()
    indices = spec["indices"]

    oled.fill(0)
    oled.text(spec["title"], 0, 0)
    oled.text("Travel", 92, 0)

    if any(last_start_us[i] is None or last_end_us[i] is None for i in indices):
        oled.text("Spread: ---", 0, 14)
        oled.text("Need sensor data", 0, 32)
        oled.text("Fire shutter", 18, 48)
        oled.show()
        return

    valid = [last_ms[i] for i in indices if last_ms[i] is not None]
    spread_ms = max(valid) - min(valid)
    average_ms = sum(valid) / len(valid)
    spread_pct = (spread_ms / average_ms * 100) if average_ms > 0 else 0

    first = indices[0]
    last = indices[-1]
    travel_ms = time.ticks_diff(last_start_us[last], last_start_us[first]) / 1000

    if travel_ms > 0:
        direction = f"{SENSOR_SPECS[first]['label']} > {SENSOR_SPECS[last]['label']}"
    elif travel_ms < 0:
        direction = f"{SENSOR_SPECS[last]['label']} > {SENSOR_SPECS[first]['label']}"
    else:
        direction = "---"

    oled.text(f"Spread:{spread_pct:.1f}%", 0, 14)

    if spread_pct < 5.0:
        bal = "GOOD"
    elif spread_pct > 20.0:
        bal = "BAD"
    else:
        bal = "OK"

    oled.text(bal, 96, 14)
    oled.text(f"Dir: {direction}", 0, 28)
    oled.text(f"Travel:{abs(travel_ms):.2f}ms", 0, 40)

    for row, index in enumerate(indices):
        y = 52
        oled.text(f"{SENSOR_SPECS[index]['label']} {format_ms_value(last_ms[index])}", row * 40, y)

    oled.show()


def draw_leaf_screen():
    oled.fill(0)

    oled.text("Leaf Shutter", 20, 0)
    oled.text("Sensor 11", 30, 12)

    if last_ms[LEAF_INDEX] is None:
        oled.text("Fire shutter", 18, 30)
        oled.text("Need center data", 0, 42)
        oled.show()
        return

    oled.text(f"{last_ms[LEAF_INDEX]:.1f} ms", 18, 28)
    oled.text(last_approx[LEAF_INDEX], 18, 40)
    oled.text(last_actual[LEAF_INDEX], 70, 40)

    oled.show()


def draw_screen():
    if screen_mode == MODE_LEAF:
        draw_leaf_screen()
    elif view_mode == VIEW_TIME:
        draw_time_screen()
    else:
        draw_travel_screen()

def reset_readings():
    global last_ms, last_approx, last_actual
    global last_start_us, last_end_us

    last_ms = [None] * len(SENSOR_SPECS)
    last_approx = ["---"] * len(SENSOR_SPECS)
    last_actual = ["---"] * len(SENSOR_SPECS)
    last_start_us = [None] * len(SENSOR_SPECS)
    last_end_us = [None] * len(SENSOR_SPECS)

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
oled.text("5 sensors", 28, 22)
oled.text("Ready", 44, 42)
oled.show()
time.sleep(1)
draw_screen()


# --------------------
# Main loop
# --------------------
while True:
    screen_changed = False
    now_ms = time.ticks_ms()

    for pin in (BUTTON_VIEW_PIN, BUTTON_MODE_PIN):
        button_pressed = buttons[pin].value() == 0

        if button_pressed and not button_was_pressed[pin]:
            button_press_ms[pin] = now_ms

        if not button_pressed and button_was_pressed[pin]:
            hold_ms = time.ticks_diff(now_ms, button_press_ms[pin])

            if pin == BUTTON_VIEW_PIN:
                if hold_ms >= BUTTON_RESET_MS:
                    reset_readings()
                elif screen_mode != MODE_LEAF:
                    view_mode = VIEW_TRAVEL if view_mode == VIEW_TIME else VIEW_TIME
                    screen_changed = True
            elif pin == BUTTON_MODE_PIN:
                if hold_ms >= BUTTON_RESET_MS:
                    screen_mode = (screen_mode + 1) % len(MODE_SPECS)
                    if screen_mode == MODE_LEAF:
                        view_mode = VIEW_TIME
                    screen_changed = True
                else:
                    toggle_led()

        button_was_pressed[pin] = button_pressed

    for i in range(len(SENSOR_SPECS)):
        if done[i]:
            duration_us = time.ticks_diff(end_us[i], start_us[i])
            duration_s = duration_us / 1_000_000

            last_ms[i] = duration_us / 1000
            last_approx[i] = nearest_shutter_speed(duration_s)
            last_actual[i] = actual_shutter_speed(duration_s)
            last_start_us[i] = start_us[i]
            last_end_us[i] = end_us[i]

            print(
                f"{SENSOR_SPECS[i]['label']}: "
                f"{last_ms[i]:.3f} ms, "
                f"approx {last_approx[i]}, "
                f"actual {last_actual[i]}"
            )

            done[i] = False
            screen_changed = True

    if screen_changed:
        draw_screen()

    time.sleep(0.01)
