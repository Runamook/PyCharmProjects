from rq import Queue
from redis import Redis
import capture
import time

video_filename_dir = '/home/egk/PycharmProjects/Video'
vide_filename_base = 'vid'
video_length = 10         # Seconds

redis_conn = Redis()
q = Queue(connection=redis_conn, name='video')

while True:
    print("Inside while loop 1")
    video_filename = '{}/{}-{}.avi'.format(video_filename_dir, vide_filename_base, int(time.time()))
    vf = capture.VideoFiles(video_filename, video_length)
    job = q.enqueue(vf.make_video)

    while job.result is None:
        time.sleep(2)
    print(job.result)
