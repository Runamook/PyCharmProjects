# coding=utf-8
# https://robotclass.ru/tutorials/opencv-video-rgb-hsv-gray/
# https://robotclass.ru/tutorials/opencv-video-text-drawings/
# https://robotclass.ru/tutorials/opencv-color-range-filter/


import cv2
import numpy as np


if __name__ == '__main__':
    def nothing(*arg):
        pass

    cv2.namedWindow('Original')
    cv2.namedWindow('settings')
    cv2.namedWindow('Color filter')

    cv2.createTrackbar('h1', 'settings', 0, 255, nothing)
    cv2.createTrackbar('s1', 'settings', 0, 255, nothing)
    cv2.createTrackbar('v1', 'settings', 0, 255, nothing)
    cv2.createTrackbar('h2', 'settings', 255, 255, nothing)
    cv2.createTrackbar('s2', 'settings', 255, 255, nothing)
    cv2.createTrackbar('v2', 'settings', 255, 255, nothing)
    crange = [0, 0, 0, 0, 0, 0]

    cap = cv2.VideoCapture(2)

    while True:
        flag, img = cap.read()          # BGR - default
        try:
            # Функция flip 0 (иногда 1, зависит от камеры) переворачивает кадр
            # img2 = cv2.flip(img, 0)
            # COLOR_BGR2GRAY — в оттенки серого;
            # COLOR_RGB2HSV — из RGB в HSV;
            # COLOR_BGR2HSV — из BGR в HSV;
            # COLOR_HSV2BGR — обратно, из HSV в BGR; etc.
            # img3 = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2HLS),0)

            hsv = cv2.GaussianBlur(img, (5, 5), 2)
            hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)

            h1 = cv2.getTrackbarPos('h1', 'settings')
            s1 = cv2.getTrackbarPos('s1', 'settings')
            v1 = cv2.getTrackbarPos('v1', 'settings')
            h2 = cv2.getTrackbarPos('h2', 'settings')
            s2 = cv2.getTrackbarPos('s2', 'settings')
            v2 = cv2.getTrackbarPos('v2', 'settings')

            h_min = np.array((h1, s1, v1), np.uint8)
            h_max = np.array((h2, s2, v2), np.uint8)

            thresh = cv2.inRange(hsv, h_min, h_max)

            """
            text = 'Face'
            color_yellow = (0, 255, 255)
            color_blue = (255, 0, 0)
            color = color_yellow
            position = (200, 200)
            font = cv2.FONT_HERSHEY_PLAIN
            scale = 1
            width = 2

            cv2.putText(img2, text, position, font, scale, color, width)

            center = (400, 230)
            radius = 150
            cv2.circle(img2, center, radius, color)
            """

            cv2.imshow('Original', img)
            cv2.imshow('Color filter', thresh)
        except:
            cap.release()
            raise

        ch = cv2.waitKey(5)
        if ch == ord('q') or ch == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()

