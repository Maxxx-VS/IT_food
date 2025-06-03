# import requests
# from io import BytesIO
# from PIL import Image
#
#
# def load_img(path, output_type="pil"):
#     if path.startswith(("http://", "https://")):
#         response = requests.get(path)
#         img = Image.open(BytesIO(response.content))
#     else:
#         img = Image.open(path)
#
#     if output_type == "pil":
#         return img
#     elif output_type == "numpy":
#         return np.array(img)
#     else:
#         raise ValueError("output_type must be 'pil' or 'numpy'")