#!/usr/bin/env python3
import os
import time
from datetime import datetime, timezone
import board
import busio
import adafruit_vl53l0x
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# Настройки
# Пороги расстояния (мм)
THRESHOLD_LOW = 300    # Объект приблизился
THRESHOLD_HIGH = 1000  # Объект удалился

# Параметры фотосъемки
PHOTO_COUNT = 3        # Количество фотографий
PHOTO_DELAY = 1.0      # Задержка между фото (сек)
RESOLUTION = (3280, 2464)  # Разрешение камеры
OUTPUT_DIR = "photos"  # Папка для сохранения фото

# Пины GPIO (нумерация BCM)
RGB_RED_PIN = 17       # GPIO 17 (пин 11) - красный
RGB_GREEN_PIN = 27     # GPIO 27 (пин 13) - зеленый
RGB_BLUE_PIN = 22      # GPIO 22 (пин 15) - синий
BUZZER_PIN = 23        # GPIO 23 (пин 16) - зуммер

# Настройки PWM
PWM_FREQ = 100         # Частота PWM для светодиодов и зуммера (Гц)
LED_BRIGHTNESS = 50    # Яркость светодиодов (0-100, в процентах)
BUZZER_VOLUME = 50     # "Громкость" зуммера (0-100, влияет на длительность импульсов)
BUZZER_BEEP_COUNT = 3  # Количество сигналов зуммера
BUZZER_BEEP_DURATION = 0.1  # Длительность одного сигнала (сек)
BUZZER_BEEP_PAUSE = 0.1     # Пауза между сигналами (сек)

def setup_components():
    """Инициализация оборудования"""
    try:
        # Инициализация I2C и датчика расстояния
        i2c = busio.I2C(board.SCL, board.SDA)
        vl53 = adafruit_vl53l0x.VL53L0X(i2c)

        # Инициализация камеры
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": RESOLUTION})
        picam2.configure(config)
        picam2.start()

        # Инициализация GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RGB_RED_PIN, GPIO.OUT)
        GPIO.setup(RGB_GREEN_PIN, GPIO.OUT)
        GPIO.setup(RGB_BLUE_PIN, GPIO.OUT)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

        # Настройка PWM для светодиодов
        red_pwm = GPIO.PWM(RGB_RED_PIN, PWM_FREQ)
        green_pwm = GPIO.PWM(RGB_GREEN_PIN, PWM_FREQ)
        blue_pwm = GPIO.PWM(RGB_BLUE_PIN, PWM_FREQ)
        red_pwm.start(0)
        green_pwm.start(0)
        blue_pwm.start(0)

        # Настройка PWM для зуммера
        buzzer_pwm = GPIO.PWM(BUZZER_PIN, PWM_FREQ)
        buzzer_pwm.start(0)

        # Создание папки для фото
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        return vl53, picam2, red_pwm, green_pwm, blue_pwm, buzzer_pwm
    except Exception as e:
        print(f"Ошибка инициализации: {str(e)}")
        return None, None, None, None, None, None

def set_rgb_color(red_pwm, green_pwm, blue_pwm, red, green, blue, brightness=LED_BRIGHTNESS):
    """Управление цветом RGB-светодиода с учетом яркости"""
    red_pwm.ChangeDutyCycle(red * brightness / 100)
    green_pwm.ChangeDutyCycle(green * brightness / 100)
    blue_pwm.ChangeDutyCycle(blue * brightness / 100)

def activate_buzzer(buzzer_pwm, volume=BUZZER_VOLUME):
    """Активация зуммера с заданной громкостью"""
    duty_cycle = volume / 100 * 50  # Ограничиваем до 50% для активного зуммера
    for _ in range(BUZZER_BEEP_COUNT):
        buzzer_pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(BUZZER_BEEP_DURATION)
        buzzer_pwm.ChangeDutyCycle(0)
        time.sleep(BUZZER_BEEP_PAUSE)

def capture_photos(camera, red_pwm, green_pwm, blue_pwm, buzzer_pwm, count, delay):
    """Создание серии фотографий с активацией зуммера и красного светодиода"""
    for i in range(count):
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S-UTC')
        filename = f"{OUTPUT_DIR}/{timestamp}.jpg"
        camera.capture_file(filename)
        print(f"Сделано фото {i+1}/{count}: {filename}")
        if i < count - 1:
            time.sleep(delay)
    # После съемки включаем красный светодиод и зуммер
    set_rgb_color(red_pwm, green_pwm, blue_pwm, 100, 0, 0)  # Красный
    activate_buzzer(buzzer_pwm)

def main():
    vl53, picam2, red_pwm, green_pwm, blue_pwm, buzzer_pwm = setup_components()
    if vl53 is None or picam2 is None:
        return

    print("Система активирована. Ожидание объекта...")
    state = "waiting_low"  # Начальное состояние
    set_rgb_color(red_pwm, green_pwm, blue_pwm, 0, 100, 0)  # Зеленый при старте

    try:
        while True:
            distance = vl53.range

            if state == "waiting_low":
                if 0 < distance < THRESHOLD_LOW:
                    print(f"Обнаружено приближение: {distance} мм < {THRESHOLD_LOW} мм")
                    capture_photos(picam2, red_pwm, green_pwm, blue_pwm, buzzer_pwm, PHOTO_COUNT, PHOTO_DELAY)
                    state = "waiting_high"
                    set_rgb_color(red_pwm, green_pwm, blue_pwm, 100, 100, 0)  # Желтый

            elif state == "waiting_high":
                if distance > THRESHOLD_HIGH:
                    print(f"Объект удалился: {distance} мм > {THRESHOLD_HIGH} мм")
                    state = "waiting_low"
                    set_rgb_color(red_pwm, green_pwm, blue_pwm, 0, 100, 0)  # Зеленый

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        picam2.stop()
        red_pwm.stop()
        green_pwm.stop()
        blue_pwm.stop()
        buzzer_pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
