from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from io import BytesIO
from adjust_brightness import gamma_correction, determine_gamma


app = FastAPI()


@app.post("/adjust-brightness/")
async def adjust_brightness(file: UploadFile = File(...)):
    contents = await file.read()

    # Convert the image to a NumPy array
    image = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    # Adjust brightness
    target_brightness = 130  # You can make this dynamic if needed
    gamma = determine_gamma(image, target_brightness)
    corrected_image = gamma_correction(image, gamma)

    # Encode image as PNG to return
    _, buffer = cv2.imencode('.png', corrected_image)
    io_buf = BytesIO(buffer)

    return StreamingResponse(io_buf, media_type="image/png")