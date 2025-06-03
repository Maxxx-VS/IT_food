import cv2
import os
import matplotlib.pyplot as plt


def estimate_blurriness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance_of_laplacian = laplacian.var()
    return variance_of_laplacian


if __name__ == '__main__':
    n_files_limit = 500
    folder_path = '/data/autotown_dump/subfolder_0'
    # folder_path = '/home/siba/Downloads/Плохие фото/Размытие'

    report_path = '/home/siba/PycharmProjects/segment-and-enhancement/data/focus_fix_vis'
    if not os.path.exists(report_path):
        os.makedirs(report_path)

    blur_dict = {}
    for filename in os.listdir(folder_path)[:n_files_limit]:
        file_path = os.path.join(folder_path, filename)

        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = cv2.imread(file_path)
            blur_value = estimate_blurriness(img)
            blur_dict[filename] = blur_value

    blur_values = list(blur_dict.values())

    plt.hist(blur_values, bins=range(0, 2000, 100), alpha=0.75, color='blue')
    plt.title('Blurriness Histogram (Variance of Laplacian)')
    plt.xlabel('Blurriness')
    plt.ylabel('Frequency')
    plt.savefig(os.path.join(report_path, 'hist.png'))
    plt.show()

    blurry_images = {filename: value for filename, value in blur_dict.items() if value < 40}
    for filename, value in blurry_images.items():
        file_path = os.path.join(folder_path, filename)
        img = cv2.imread(file_path)
        plt.figure(dpi=200)
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title(f'Blurriness: {value}')
        plt.savefig(os.path.join(report_path, f'{filename[:-4]}_blurry.png'))
        plt.show()
