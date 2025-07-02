"""
Скрипт для создания фотографий при изменеии (+/-) массы на весах
"""

import RPi.GPIO as GPIO
from hx711 import HX711
from picamera2 import Picamera2
import time
import os
from datetime import datetime

# Configuration
OUTPUT_DIR = "/home/sm/photos"   # Каталог для сохранения фотографий
MAX_RESOLUTION = (4608, 2592)    # Максимальное разрешение камеры
FOCUS_DELAY = 2                  # Задержка фокусировки (секунды
MIN_MASS_THRESHOLD = 100         # Минимальный порог изменения массы (г)
MAX_MASS_THRESHOLD = 500         # Максимальный порог изменения массы (г)
EMPTY_MASS_THRESHOLD = 50        # Порог сброса счетчика (г)
CALIBRATION_FACTOR = 20          # Коэффициент калибровки (подбирается экспериментально)
DT = 5                           # DT-контакт для HX711
SCK = 6                          # SCK-контакт для HX711
PAUSE_BETWEEN_MEAS = 0.5         # Пауза между измерениями

# Создаем каталог, если он не существует
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Фотографии будут сохраняться в: {OUTPUT_DIR}")

# Инициализация GPIO
GPIO.setmode(GPIO.BCM)

# Инициализация HX711
hx = HX711(dout=DT, pd_sck=SCK)
hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(CALIBRATION_FACTOR)
hx.reset()
hx.tare()  # Сбросить до нуля

# Инициализация camera
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": MAX_RESOLUTION})
picam2.configure(config)
picam2.start(show_preview=False)
print(f"Камера запущена с разрешением {MAX_RESOLUTION[0]}x{MAX_RESOLUTION[1]}")

# Глобальные переменные
previous_mass = 0
sushi_counter = 0
last_reset_date = datetime.now().date()

def take_photo(flag):
    """Функция делает снимок с указанным флагом изменения массы («вверх» или «вниз»)"""
    try:
        picam2.set_controls({"AfMode": 0, "AfTrigger": 0})
        print(f"Фокусировка... (ожидание {FOCUS_DELAY} сек)")
        time.sleep(FOCUS_DELAY)
    except Exception as e:
        print(f"Автофокус не поддерживается: {str(e)}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"photo_{timestamp}_{flag}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    picam2.capture_file(filepath)
    print(f"Снимок сохранен как: {filepath}")

def get_weight():
    """Получение текущего веса с весов"""
    try:
        val = hx.get_weight(10)
        return val
    except Exception as e:
        print(f"Ошибка при получении массы: {e}")
        return None

def main():
    global previous_mass, sushi_counter, last_reset_date

    print("Начало измерений. Нажмите Ctrl+C для выхода.")
    try:
        while True:
            current_mass = get_weight()
            if current_mass is None:
                continue

            # Ежедневный сброс счетчика
            current_date = datetime.now().date()
            if current_date > last_reset_date:
                sushi_counter = 0
                last_reset_date = current_date
                print("Счетчик суши-роллов сброшен на начало нового дня.")

            # Сброс счетчика, если весы пустые
            if current_mass < EMPTY_MASS_THRESHOLD:
                sushi_counter = 0
                print("Счетчик суши-роллов сброшен, так как весы пусты.")

            # Расчет изменения массы
            mass_change = current_mass - previous_mass
            if MIN_MASS_THRESHOLD < mass_change < MAX_MASS_THRESHOLD:
                print(f"Масса увеличилась на {mass_change:.1f} г")
                take_photo("up")
                sushi_counter += 1
                print(f"Общий счетчик суши-роллов: {sushi_counter}")
            elif -MAX_MASS_THRESHOLD < mass_change < -MIN_MASS_THRESHOLD:
                print(f"Масса уменьшилась на {-mass_change:.1f} г")
                take_photo("down")

            previous_mass = current_mass
            time.sleep(PAUSE_BETWEEN_MEAS)

    except KeyboardInterrupt:
        print("Выход")
    finally:
        picam2.stop()
        GPIO.cleanup()
        print("Камера остановлена и GPIO очищены")

if __name__ == "__main__":
    main()