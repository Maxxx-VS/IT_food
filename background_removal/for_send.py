# import os
# from PIL import Image
# import requests
# from io import BytesIO
# from transformers import AutoModelForImageSegmentation
# import torch
# from torchvision import transforms
#
# folder_path = "dirty_images"
#
# # Получаем устройство из переменных окружения (по умолчанию 'cpu')
# DEVICE = os.getenv('DEVICE', 'cpu').lower()
# if DEVICE == 'cuda' and not torch.cuda.is_available():
#     print("Предупреждение: CUDA недоступна, используется CPU")
#     DEVICE = 'cpu'
#
# # Установка режима работы
# torch.set_float32_matmul_precision("high")
# device = torch.device(DEVICE)
# print(f"Используется устройство: {device}")
#
# # Загрузка модели
# birefnet = AutoModelForImageSegmentation.from_pretrained(
#     "ZhengPeng7/BiRefNet", trust_remote_code=True).to(device)
#
# # Трансформации изображения
# transform_image = transforms.Compose([
#     transforms.Resize((1024, 1024)),
#     transforms.ToTensor(),
#     transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),])
#
# def load_img(path):
#     """Загрузка изображения из файла или URL"""
#     if path.startswith(("http://", "https://")):
#         response = requests.get(path)
#         return Image.open(BytesIO(response.content))
#     return Image.open(path)
#
# def process(image):
#     """Обработка изображения и удаление фона"""
#     image_size = image.size
#     input_images = transform_image(image).unsqueeze(0).to(device)
#
#     # Предсказание маски
#     with torch.no_grad():
#         preds = birefnet(input_images)[-1].sigmoid().cpu()
#
#     pred = preds[0].squeeze()
#     pred_pil = transforms.ToPILImage()(pred)
#     mask = pred_pil.resize(image_size)
#
#     # Создание изображения с прозрачным фоном
#     result = image.copy()
#     result.putalpha(mask)
#     return result
#
# def process_and_save(input_path, output_dir="clean_images"):
#     """Обработка и сохранение изображения"""
#     os.makedirs(output_dir, exist_ok=True)
#
#     # Загрузка изображения
#     img = load_img(input_path)
#
#     # Обработка
#     result = process(img)
#
#     # Генерация имени файла
#     if input_path.startswith(("http://", "https://")):
#         filename = f"web_image_{hash(input_path)}.png"
#     else:
#         filename = os.path.basename(input_path).rsplit('.', 1)[0] + ".png"
#
#     # Сохранение
#     output_path = os.path.join(output_dir, filename)
#     result.save(output_path, "PNG")
#     return output_path
#
# if __name__ == "__main__":
#
#     for filename in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, filename)
#         if os.path.isfile(file_path):  # Проверяем, является ли это файлом
#             output_path = process_and_save(file_path)
#             print(f"Обработанное изображение сохранено: {output_path}")

import os
from PIL import Image
from transformers import AutoModelForImageSegmentation
import torch
from torchvision import transforms

folder_path = "dirty_images"

# Получаем устройство из переменных окружения (по умолчанию 'cpu')
DEVICE = os.getenv('DEVICE', 'cpu').lower()
if DEVICE == 'cuda' and not torch.cuda.is_available():
    print("Предупреждение: CUDA недоступна, используется CPU")
    DEVICE = 'cpu'

# Установка режима работы
torch.set_float32_matmul_precision("high")
device = torch.device(DEVICE)
print(f"Используется устройство: {device}")

# Загрузка модели
birefnet = AutoModelForImageSegmentation.from_pretrained(
    "ZhengPeng7/BiRefNet", trust_remote_code=True).to(device)

# Трансформации изображения
transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),])

def process(image):
    """Обработка изображения и удаление фона"""
    image_size = image.size
    input_images = transform_image(image).unsqueeze(0).to(device)

    # Предсказание маски
    with torch.no_grad():
        preds = birefnet(input_images)[-1].sigmoid().cpu()

    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(image_size)

    # Создание изображения с прозрачным фоном
    result = image.copy()
    result.putalpha(mask)
    return result

def process_and_save(input_path, output_dir="clean_images"):
    """Обработка и сохранение изображения"""
    os.makedirs(output_dir, exist_ok=True)

    # Загрузка изображения
    img = Image.open(input_path)

    # Обработка
    result = process(img)

    # Генерация имени файла
    filename = os.path.basename(input_path).rsplit('.', 1)[0] + ".png"

    # Сохранение
    output_path = os.path.join(output_dir, filename)
    result.save(output_path, "PNG")
    return output_path

if __name__ == "__main__":
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):  # Проверяем, является ли это файлом
            output_path = process_and_save(file_path)
            print(f"Обработанное изображение сохранено: {output_path}")