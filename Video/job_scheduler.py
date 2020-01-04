from rq import Queue
from redis import Redis
import capture
import time

# Only H264 can be played inside the TG client
# Extension .mp4 treated as a GIF in TG client
# Extension .avi treated as video
# video_filename_dir = '/home/egk/PycharmProjects/Video'
video_filename_dir = '/tmp'
video_filename_base = 'tg-vid'
video_ext = 'mp4'
video_length = 12         # Seconds

redis_conn = Redis()
q = Queue(connection=redis_conn, name='video')

while True:
    print("Inside while loop 1")
    video_filename = '{}/{}-{}.{}'.format(video_filename_dir, video_filename_base, int(time.time()), video_ext)
    vf = capture.VideoFiles(video_filename, video_length)
    job = q.enqueue(vf.make_video)

    while job.result is None:
        time.sleep(2)
    print(job.result)
