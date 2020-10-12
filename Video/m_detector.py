import datetime
import imutils
import time
import sqlite3
import cv2
import os
import logging

# https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
# https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/

"""
Main loop continuously scans target dir for videos.
Videos are processed to find motion and result is recorded to DB.

"""
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Detector:

    min_area = 500
    db_name = 'videofiles.db'
    storage = '2 hour'

    def __init__(self, filename):
        self.filename = filename
        self.vs = cv2.VideoCapture(self.filename)
        self.firstFrame = None
        self.start = time.time()
        self.status = 0         # No motion
        self.db_full_name = "{}/{}".format(os.path.dirname(self.filename), self.db_name)

    def _decode(self):
        while True:
            # grab the current frame and initialize the occupied/unoccupied text
            frame = self.vs.read()
            frame = frame[1]

            # if the frame could not be grabbed, then we have reached the end of the video
            if frame is None:
                return

            # resize the frame, convert it to grayscale, and blur it
            frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the first frame is None, initialize it
            if self.firstFrame is None:
                self.firstFrame = gray
                continue

            # Reset first frame every 10 seconds
            if time.time() - self.start > 10:
                logging.info('firstFrame change {}'.format(datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")))
                self.firstFrame = gray
                self.start = time.time()

            # compute the absolute difference between the current frame and first frame
            frameDelta = cv2.absdiff(self.firstFrame, gray)
            thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

            # dilate the thresholded image to fill in holes, then find contours on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)

            # loop over the contours

            for c in cnts:
                # if the contour is too small, ignore it
                if cv2.contourArea(c) < Detector.min_area:
                    continue

                # compute the bounding box for the contour, draw it on the frame, and update the text
                # (x, y, w, h) = cv2.boundingRect(c)
                # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                self.status = 1         # Motion

        # cleanup the camera and close any open windows
        self.vs.release()
        cv2.destroyAllWindows()

    def find_motion(self):
        self._decode()
        self._process_metadata()
        if self.status == 0:            # No motion in video
            return False
        elif self.status == 1:          # Motion in video
            return True

    def _process_metadata(self):
        try:
            conn = sqlite3.connect(self.db_full_name)
            cursor = conn.cursor()
            now = int(time.time())
            insert_metadata = "INSERT INTO processed_videos VALUES ('{}', '{}', '{}', '0')".format(now, self.filename, self.status)
            cursor.execute(insert_metadata)
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error('{}, file: {}'.format(e, self.filename))
            pass


if __name__ == '__main__':
    counter = 0
    m_counter = 0
    while True:
        db_full_name = '/tmp/videofiles.db'
        conn = sqlite3.connect(db_full_name)
        cursor = conn.cursor()
        create_table = 'CREATE TABLE IF NOT EXISTS processed_videos (dt INTEGER,filename TEXT NOT NULL, motion INTEGER, sent INTEGER, PRIMARY KEY(dt, filename));'
        delete_metadata = 'DELETE FROM processed_videos WHERE dt < strftime("%s", "now", "-{}");'.format(Detector.storage)
        cursor.execute(create_table)
        cursor.execute(delete_metadata)
        conn.commit()
        q = "SELECT filename from videos WHERE NOT EXISTS (SELECT * FROM processed_videos WHERE filename = videos.filename) AND filename LIKE '%.mp4';"
        unprocessed_videos_list = [x[0] for x in cursor.execute(q).fetchall()]
        logging.info('{} unprocessed videos found'.format(len(unprocessed_videos_list)))

        try:
            for unprocessed_video in unprocessed_videos_list:
                d = Detector(unprocessed_video)
                if d.find_motion():
                    logging.info('Motion detected in {}'.format(unprocessed_video))
                    m_counter += 1
                counter += 1
            logging.info('{} videos processed. Motion found in {}'.format(counter, m_counter))
            time.sleep(15)
        except KeyboardInterrupt:
            logging.info('{} videos processed'.format(counter))
            break
