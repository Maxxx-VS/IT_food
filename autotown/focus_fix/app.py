import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import os

app = FastAPI()


def unsharp_mask(image, sigma=1.0, strength=1.5):
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    return sharpened


@app.post("/deblur/")
async def deblur_image(file: UploadFile = File(...), sigma: float = 1.5, strength: float = 1.5):
    image_data = await file.read()
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    deblurred_image = unsharp_mask(image, sigma, strength)

    save_path = "/tmp/deblurred_image.png"
    cv2.imwrite(save_path, deblurred_image)

    return FileResponse(save_path, media_type="image/png", filename="deblurred_image.png")
