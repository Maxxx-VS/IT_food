# import gradio as gr
# from gradio_imageslider import ImageSlider
# from loadimg import load_img
# import spaces
# from transformers import AutoModelForImageSegmentation
# import torch
# from torchvision import transforms
#
# torch.set_float32_matmul_precision(["high", "highest"][0])
#
# birefnet = AutoModelForImageSegmentation.from_pretrained(
#     "ZhengPeng7/BiRefNet", trust_remote_code=True
# )
# birefnet.to("cpu") # замените на birefnet.to("cuda")
#
# transform_image = transforms.Compose(
#     [
#         transforms.Resize((1024, 1024)),
#         transforms.ToTensor(),
#         transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
#     ]
# )
#
# def fn(image):
#     im = load_img(image, output_type="pil")
#     im = im.convert("RGB")
#     origin = im.copy()
#     processed_image = process(im)
#     return (processed_image, origin)
#
# @spaces.GPU
# def process(image):
#     image_size = image.size
#     input_images = transform_image(image).unsqueeze(0).to("cuda")
#     # Prediction
#     with torch.no_grad():
#         preds = birefnet(input_images)[-1].sigmoid().cpu()
#     pred = preds[0].squeeze()
#     pred_pil = transforms.ToPILImage()(pred)
#     mask = pred_pil.resize(image_size)
#     image.putalpha(mask)
#     return image
#
# def process_file(f):
#     name_path = f.rsplit(".", 1)[0] + ".png"
#     im = load_img(f, output_type="pil")
#     im = im.convert("RGB")
#     transparent = process(im)
#     transparent.save(name_path)
#     return name_path
#
# slider1 = ImageSlider(label="Processed Image", type="pil")
# slider2 = ImageSlider(label="Processed Image from URL", type="pil")
# image_upload = gr.Image(label="Upload an image")
# image_file_upload = gr.Image(label="Upload an image", type="filepath")
# url_input = gr.Textbox(label="Paste an image URL")
# output_file = gr.File(label="Output PNG File")
#
# # Example images
# chameleon = load_img("butterfly.jpg", output_type="pil")
# url_example = "https://hips.hearstapps.com/hmg-prod/images/gettyimages-1229892983-square.jpg"
#
# tab1 = gr.Interface(fn, inputs=image_upload, outputs=slider1, examples=[chameleon], api_name="image")
# tab2 = gr.Interface(fn, inputs=url_input, outputs=slider2, examples=[url_example], api_name="text")
# tab3 = gr.Interface(process_file, inputs=image_file_upload, outputs=output_file, examples=["butterfly.jpg"], api_name="png")
#
# demo = gr.TabbedInterface(
#     [tab1, tab2, tab3], ["Image Upload", "URL Input", "File Output"], title="Background Removal Tool"
# )
#
#
# if __name__ == "__main__":
#     demo.launch(show_error=True)

import gradio as gr
from gradio_imageslider import ImageSlider
from PIL import Image
import requests
from io import BytesIO
import os
from transformers import AutoModelForImageSegmentation
import torch
from torchvision import transforms

# Установка режима работы на CPU
torch.set_float32_matmul_precision("high")
device = "cpu"  # Принудительно используем CPU

# Загрузка модели
birefnet = AutoModelForImageSegmentation.from_pretrained(
    "ZhengPeng7/BiRefNet",
    trust_remote_code=True
).to(device)

# Трансформации изображения
transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def load_img(path, output_type="pil"):
    """Загрузка изображения из файла или URL"""
    if path.startswith(("http://", "https://")):
        response = requests.get(path)
        img = Image.open(BytesIO(response.content))
    else:
        img = Image.open(path)

    if output_type == "pil":
        return img
    elif output_type == "numpy":
        return np.array(img)
    else:
        raise ValueError("output_type must be 'pil' or 'numpy'")


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


def process_and_save(input_image, output_dir="results"):
    """Обработка и сохранение изображения"""
    os.makedirs(output_dir, exist_ok=True)

    # Загрузка изображения
    if isinstance(input_image, str):
        if input_image.startswith(("http://", "https://")):
            img = load_img(input_image)
            filename = f"web_image_{hash(input_image)}.png"
        else:
            img = Image.open(input_image)
            filename = os.path.basename(input_image).rsplit('.', 1)[0] + ".png"
    else:
        img = input_image
        filename = f"processed_{hash(str(input_image))}.png"

    # Обработка
    result = process(img)

    # Сохранение
    output_path = os.path.join(output_dir, filename)
    result.save(output_path, "PNG")

    return result, output_path


def process_upload(image):
    """Обработка загруженного изображения"""
    img = load_img(image.name)
    processed, saved_path = process_and_save(img)
    return (processed, img, saved_path)


def process_url(url):
    """Обработка изображения по URL"""
    img = load_img(url)
    processed, saved_path = process_and_save(img)
    return (processed, img, saved_path)


# Создание интерфейса
with gr.Blocks(title="Background Removal Tool") as demo:
    gr.Markdown("# 🖼️ Инструмент для удаления фона")
    gr.Markdown("Загрузите изображение или укажите URL для удаления фона")

    with gr.Tabs():
        with gr.Tab("Загрузка изображения"):
            with gr.Row():
                image_input = gr.UploadButton("Выберите изображение", type="filepath")
            with gr.Row():
                original_image = gr.Image(label="Исходное изображение", interactive=False)
                result_image = gr.Image(label="Результат", interactive=False)
            save_info = gr.Textbox(label="Сохранено в", interactive=False)

            image_input.upload(
                process_upload,
                inputs=[image_input],
                outputs=[result_image, original_image, save_info]
            )

        with gr.Tab("Изображение по URL"):
            with gr.Row():
                url_input = gr.Textbox(label="URL изображения", placeholder="https://example.com/image.jpg")
                url_submit = gr.Button("Обработать")
            with gr.Row():
                url_original = gr.Image(label="Исходное изображение", interactive=False)
                url_result = gr.Image(label="Результат", interactive=False)
            url_save_info = gr.Textbox(label="Сохранено в", interactive=False)

            url_submit.click(
                process_url,
                inputs=[url_input],
                outputs=[url_result, url_original, url_save_info]
            )

# Запуск приложения
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )