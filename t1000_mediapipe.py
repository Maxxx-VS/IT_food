import cv2
import mediapipe as mp
import os
import time
import math
import subprocess
import threading
import queue

# ========== КОНСТАНТЫ И НАСТРОЙКИ ==========
# Настройки Mediapipe
MAX_NUM_HANDS = 4
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5

# Настройки жестов
GESTURE_HOLD_TIME = 3.0  # секунды
ACTION_COOLDOWN = 5.0    # пауза после срабатывания жеста
RING_GESTURE_DISTANCE_THRESHOLD = 0.05  # порог расстояния для жеста "кольцо"
FIST_GESTURE_THRESHOLD = 0.08  # порог для распознавания кулака

# Настройки системы
PHOTOS_DIR = "photos"
SOUNDS_DIR = "sounds"
SHOW_IMAGE = True
SOUND_DEVICE = "plughw:3,0"

# Звуковые файлы
RUN_SOUND = "run_sound.wav"
COUNTDOWN_SOUND = "new_sound.wav"  # Переименован для ясности
ENDING_SOUND = "ending_sound.wav"

# Инициализация Mediapipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Создание директорий
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(SOUNDS_DIR, exist_ok=True)

# Очередь для управления звуковыми файлами
sound_queue = queue.Queue()

def sound_worker():
    """Фоновый поток для последовательного воспроизведения звуков"""
    while True:
        sound_file = sound_queue.get()
        try:
            full_path = os.path.join(SOUNDS_DIR, sound_file)
            if not os.path.exists(full_path):
                print(f"⚠ Файл звука не найден: {full_path}")
                continue
                
            cmd = f"aplay -D {SOUND_DEVICE} {full_path}"
            subprocess.run(
                cmd, 
                shell=True, 
                executable="/bin/bash",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✓ Воспроизведен звук: {sound_file}")
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
        finally:
            sound_queue.task_done()

# Запуск фонового потока для звуков
threading.Thread(target=sound_worker, daemon=True).start()

def play_sound(sound_file):
    """Добавление звука в очередь воспроизведения"""
    try:
        sound_queue.put_nowait(sound_file)
    except queue.Full:
        print(f"Очередь звуков переполнена, пропуск: {sound_file}")

class GestureController:
    def __init__(self):
        self.hands = mp_hands.Hands(
            max_num_hands=MAX_NUM_HANDS,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE
        )
        
        # Таймеры для управления жестами
        self.gesture_start_time = None
        self.last_photo_path = None
        self.cooldown_end = 0
        self.last_sound_time = 0
        self.sound_counter = 0
        self.active_gesture = None

    def detect_gesture(self, landmarks):
        """Определение жестов по ключевым точкам руки"""
        # Кончики пальцев и суставы
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        middle_mcp = landmarks[9]
        
        # Жест "кольцо" (большой и указательный палец соединены)
        thumb_index_distance = math.sqrt(
            (thumb_tip.x - index_tip.x)**2 + 
            (thumb_tip.y - index_tip.y)**2
        )
        
        # Проверяем что остальные пальцы разогнуты
        other_fingers_extended = (
            middle_tip.y < middle_mcp.y and
            ring_tip.y < landmarks[13].y and
            pinky_tip.y < landmarks[17].y
        )
        
        if thumb_index_distance < RING_GESTURE_DISTANCE_THRESHOLD and other_fingers_extended:
            return "ring"
        
        # Жест "кулак" (все пальцы сжаты)
        fist_gesture = (
            index_tip.y > landmarks[6].y and   # Указательный
            middle_tip.y > landmarks[10].y and # Средний
            ring_tip.y > landmarks[14].y and   # Безымянный
            pinky_tip.y > landmarks[18].y and  # Мизинец
            thumb_tip.y > landmarks[2].y       # Большой
        )
        
        if fist_gesture:
            return "fist"
        
        return None

    def take_photo(self, frame):
        """Сохранение фотографии в директорию и воспроизведение звука"""
        photo_name = f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        photo_path = os.path.join(PHOTOS_DIR, photo_name)
        cv2.imwrite(photo_path, frame)
        self.last_photo_path = photo_path
        print(f"✓ Фотография сохранена: {photo_path}")
        play_sound(ENDING_SOUND)
        return photo_path

    def process_frame(self, frame):
        """Обработка кадра и распознавание жестов"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        current_gesture = None
        current_time = time.time()
        
        # Проверяем паузу после предыдущего жеста
        if current_time < self.cooldown_end:
            cooldown_remaining = self.cooldown_end - current_time
            cv2.putText(frame, f"Cooldown: {cooldown_remaining:.1f}s", 
                       (frame.shape[1] - 200, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame, None
        
        # Обработка жестов только при одной руке в кадре
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            
            if num_hands == 1:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                landmarks = hand_landmarks.landmark
                current_gesture = self.detect_gesture(landmarks)
                
                # Обработка жестов "кольцо" и "кулак"
                if current_gesture in ["ring", "fist"]:
                    if self.gesture_start_time is None:
                        # Начало нового жеста
                        self.gesture_start_time = current_time
                        self.last_sound_time = current_time
                        self.sound_counter = 1
                        self.active_gesture = current_gesture
                        play_sound(COUNTDOWN_SOUND)
                    else:
                        # Жест продолжается
                        elapsed = current_time - self.gesture_start_time
                        
                        # Воспроизведение звука каждую секунду
                        if current_time - self.last_sound_time >= 1.0 and self.sound_counter < 3:
                            play_sound(COUNTDOWN_SOUND)
                            self.last_sound_time = current_time
                            self.sound_counter += 1
                        
                        # Срабатывание после 3 секунд
                        if elapsed >= GESTURE_HOLD_TIME:
                            self.take_photo(frame)
                            self.gesture_start_time = None
                            self.cooldown_end = current_time + ACTION_COOLDOWN
                else:
                    # Жест прервался
                    self.gesture_start_time = None
                    self.active_gesture = None
            else:
                # В кадре больше одной руки - сбрасываем таймер
                self.gesture_start_time = None
                self.active_gesture = None
        
        # Отображение информации о жестах
        if self.active_gesture:
            cv2.putText(frame, f"Gesture: {self.active_gesture}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if self.gesture_start_time:
                countdown = GESTURE_HOLD_TIME - (current_time - self.gesture_start_time)
                cv2.putText(frame, f"Photo: {countdown:.1f}s", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Отображение количества рук
        hands_status = f"Hands: {len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0}"
        cv2.putText(frame, hands_status, (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return frame, self.active_gesture

def main():
    controller = GestureController()
    cap = cv2.VideoCapture(0)
    
    # Проверка доступности камеры
    if not cap.isOpened():
        print("Ошибка: Камера не доступна")
        return
    
    print("Инициализация системы...")
    play_sound(RUN_SOUND)
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Пропущен кадр")
                continue
            
            frame, current_gesture = controller.process_frame(frame)
            
            if SHOW_IMAGE:
                cv2.imshow('Gesture Photo Controller', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        if SHOW_IMAGE:
            cv2.destroyAllWindows()
        print("Система остановлена")

if __name__ == "__main__":
    main()