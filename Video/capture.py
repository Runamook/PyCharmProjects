# coding=utf-8
import cv2
import time
from redis import Redis
import sqlite3
import os

# https://gist.github.com/vscv/f7ef0f688fdf5e888dadfb8440830a3d
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
        video_fourcc = cv2.VideoWriter_fourcc(*'XVID')
        capture = cv2.VideoCapture(2)
        # Check frame.shape to get the read frame size
        video_file = cv2.VideoWriter(self.filename, video_fourcc, 25, (640, 480), 1)
        start = time.time()
        counter = 0

        while True:
            check, frame = capture.read()
            video_file.write(frame)

            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)            # Black/white video
            # print(check)
            # print(frame)
            """
            cv2.imshow("Capturing", frame)                            # Show video in realtime
            key = cv2.waitKey(1)
        
            if key == ord('q'):
                break
            """

            counter += 1

            if counter % 25 == 0:
                print("In progress {} seconds".format(time.time() - start))
                if time.time() - start > self.length:
                    break

        capture.release()
        video_file.release()
        cv2.destroyAllWindows()
        self.remove_lock()
        print("Finished in {} seconds".format(time.time() - start))
        self.process_metadata()
        return "Finished"

    def process_metadata(self):

        db_full_name = "{}/{}".format(os.path.dirname(self.filename), self.db_name)
        conn = sqlite3.connect(db_full_name)
        cursor = conn.cursor()
        now = int(time.time())

        create_table = 'CREATE TABLE IF NOT EXISTS videos (dt INTEGER PRIMARY KEY,filename TEXT NOT NULL);'
        insert_metadata = "INSERT INTO videos VALUES ('{}', '{}')".format(now, self.filename)

        cursor.execute(create_table)
        cursor.execute(insert_metadata)

        conn.commit()

        self.remove_old_videos(conn)
        conn.close()
        return

    def remove_old_videos(self, conn):

        cursor = conn.cursor()
        select_old_videos = 'SELECT filename FROM videos WHERE dt < strftime("%s", "now", "-1 hour");'
        delete_metadata = 'DELETE FROM videos WHERE dt < strftime("%s", "now", "-1 hour");'

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
