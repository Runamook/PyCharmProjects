# coding=utf-8
import cv2
import time
from redis import Redis
import sqlite3
import os
import datetime

# https://gist.github.com/vscv/f7ef0f688fdf5e888dadfb8440830a3d
# https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
'''
Скажем пару слов о кодеке mjpeg - видео формируется из последовательности картинок.
Mjpeg имеет очень плохую степень сжатия в сравнении с h.264 и h.265 при формировании которых
отправляется не каждый последующий кадр, а только изменения в предыдущем. 
Благодаря высокотехнологичным алгоритмам сжатия видео потоков кодеки: h264 и h265 являются лучшими на 2018 год.
Несмотря на все выше сказанное mjpeg иногда применяется в конкретных случаях: там где важна четкость каждого кадра,
например для распознавания номеров автотранспорта, а размер архива и загруженный канал имеют второстепенное значение.
'''


class VideoFiles:
    lock_name = "video_capture_in_progress"
    db_name = 'videofiles.db'
    storage = '2 hour'
    # four_cc = 'XVID'
    # four_cc = 'X264'
    four_cc = 'H264'
    fps = 4
    resolution = (640, 480)
    camera_index = 0

    def __init__(self, filename, length):
        self.filename = filename
        self.length = length

    def set_lock(self):
        max_time = int(int(self.length) * 1.2)
        r = Redis()
        lock_start = time.time()
        counter = 0
        while r.get(VideoFiles.lock_name):
            time.sleep(1)
            if counter % 3 == 0:
                print("Camera locked, waiting")
            counter += 1

            if time.time() - lock_start > max_time:
                raise IOError("Unable to acquire lock in 10 seconds")
        try:
            r.set(VideoFiles.lock_name, "1", ex=max_time)
            return True
        except Exception as e:
            raise e

    def remove_lock(self):
        try:
            r = Redis()
            r.delete(VideoFiles.lock_name)
            return True
        except Exception as e:
            raise e

    def make_video(self):
        """
        :param filename: path to the result .avi file
        :param length: desired length of the video in seconds (approximate)
        :return: str
        """

        self.set_lock()
        video_fourcc = cv2.VideoWriter_fourcc(*VideoFiles.four_cc)
        capture = cv2.VideoCapture(VideoFiles.camera_index)
        # Check frame.shape to get the read frame size
        print('File = {}, Format = {}, FPS = {}, Resolution = {}'.format(
            self.filename, VideoFiles.four_cc, VideoFiles.fps, VideoFiles.resolution)
        )
        video_file = cv2.VideoWriter(self.filename, video_fourcc, VideoFiles.fps, VideoFiles.resolution, 1)
        start = time.time()
        counter = 0

        while True:
            check, frame = capture.read()
            cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %H:%M:%S"),
                        (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
            video_file.write(frame)

            """
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)            # Black/white video
            print(check)
            print(frame)
            cv2.imshow("Capturing", frame)                            # Show video in realtime
            key = cv2.waitKey(1)
        
            if key == ord('q'):
                break
            """

            counter += 1

            if counter % VideoFiles.fps == 0:
                d = time.time() - start
                print("{} frames in {} seconds. FPS = {}".format(counter, d, counter/d))
                if time.time() - start > self.length:
                    break
            time.sleep(0.25)

        capture.release()
        video_file.release()
        cv2.destroyAllWindows()
        self.remove_lock()
        print("Finished in {} seconds".format(time.time() - start))
        self.process_metadata()
        return "Finished"

    def process_metadata(self):

        db_full_name = "{}/{}".format(os.path.dirname(self.filename), self.db_name)
        try:
            conn = sqlite3.connect(db_full_name)
            cursor = conn.cursor()
            now = int(time.time())

            create_table = 'CREATE TABLE IF NOT EXISTS videos (dt INTEGER PRIMARY KEY,filename TEXT NOT NULL);'
            insert_metadata = "INSERT INTO videos VALUES ('{}', '{}')".format(now, self.filename)
            # Insert .avi filename, in is changed to .avi if video is sent to Telegram
            insert_metadata_2 = "INSERT INTO videos VALUES ('{}', '{}')".format(now + 1, os.path.splitext(self.filename)[0] + '.avi')

            cursor.execute(create_table)
            cursor.execute(insert_metadata)
            cursor.execute(insert_metadata_2)

            conn.commit()

            self.remove_old_videos(conn)
            conn.close()
        except Exception as e:
            print('ERROR {}'.format(e))
            pass
        return

    def remove_old_videos(self, conn):

        cursor = conn.cursor()
        select_old_videos = 'SELECT filename FROM videos WHERE dt < strftime("%s", "now", "-1 hour");'
        delete_metadata = 'DELETE FROM videos WHERE dt < strftime("%s", "now", "-{}");'.format(VideoFiles.storage)

        for video_filename in cursor.execute(select_old_videos).fetchall():
            # [(file1,), (file2,), (file3,)]
            try:
                os.remove(video_filename[0])
            except OSError:
                pass

        cursor.execute(delete_metadata)
        cursor.execute('VACUUM;')
        conn.commit()
        return
