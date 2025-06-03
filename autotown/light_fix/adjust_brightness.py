import cv2
import numpy as np
import os
# import matplotlib.pyplot as plt


def gamma_correction(image, gamma):
    gamma = max(gamma, 0.01)
    lookup_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype='uint8')
    corrected_image = cv2.LUT(image, lookup_table)
    return corrected_image


def calculate_average_brightness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)


def determine_gamma(image, target_brightness=128):
    average_brightness = calculate_average_brightness(image)
    gamma = average_brightness / target_brightness
    return max(gamma, 0.01)


"""
if __name__ == '__main__':
    image_folder = '/data/autotown_dump/subfolder_0'
    save_folder = '/data/autotown_dump/light_fix_vis'

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    brightness_values = []
    for filename in os.listdir(image_folder)[:300]:
        if filename.endswith('.jpeg') or filename.endswith('.png'):
            img_path = os.path.join(image_folder, filename)
            image = cv2.imread(img_path)
            b_val = calculate_average_brightness(image)
            brightness_values.append(b_val)
    plt.figure()
    plt.hist(brightness_values)
    plt.show()

    target_brightness = 130
    for filename in os.listdir(image_folder)[:20]:
        if filename.endswith('.jpeg') or filename.endswith('.png'):
            img_path = os.path.join(image_folder, filename)
            image = cv2.imread(img_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            gamma = determine_gamma(image, target_brightness)
            original_br = round(calculate_average_brightness(image), 1)
            corrected_image = gamma_correction(image, gamma)
            corrected_br = round(calculate_average_brightness(corrected_image), 1)
            fig, axes = plt.subplots(2, 1)
            axes[0].imshow(image)
            axes[0].set_title(f'Original, br {original_br}')
            axes[1].imshow(corrected_image)
            axes[1].set_title(f'Corrected, br {corrected_br}, gamma {round(gamma, 2)}')
            fig.tight_layout()
            save_path = os.path.join(save_folder, f'{filename[:-4]}_light_fix.png')
            fig.savefig(save_path)
    plt.show()
"""
