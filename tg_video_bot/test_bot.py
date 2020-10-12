from telegram.ext import Updater
from telegram import Bot
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
import logging
import os
import time
import glob

# https://stackoverflow.com/questions/47615956/send-video-through-telegram-python-api
updater = Updater(token='1063510617:AAHCceqJw11iGR8v688XRnA5zZBGxKWJLAw',
                  use_context=True,
                  request_kwargs={'read_timeout': 1000, 'connect_timeout': 1000})

dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def send_message():
    bot = Bot(token='1063510617:AAHCceqJw11iGR8v688XRnA5zZBGxKWJLAw')

    # Отправить сообщение в канал
    # bot.send_message(chat_id='@test_chn123', text="I'm sorry Dave I'm afraid I can't do that.")

    # Отправить сообщение пользователю, где chat_id:
    # Post one message from User to the Bot.
    # Open https://api.telegram.org/bot<Bot_token>/getUpdates page.
    # Find this message and navigate to the result->message->chat->id key.
    # Use this ID as the [chat_id] parameter to send personal messages to the User.
    bot.send_message(chat_id='258294154', text="asdфывфыв")


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Talk to the bot!')


def video(update, context):
    # Only H264 can be played inside the client
    # Extension .mp4 treated as a GIF in client
    # Extension .avi treated as video
    fn = '/home/egk/PycharmProjects/Video/tg-vid-1577189450.avi'
    context.bot.send_video(chat_id=update.effective_chat.id, video=open(fn, 'rb'), supports_streaming=True)


# def document(update, context):
#     fn = '/home/egk/PycharmProjects/Video/vid-1577055747.avi'
#     context.bot.send_document(chat_id=update.effective_chat.id, document=open(fn, 'rb'))

def find_latest_video():
    vid_dir = '/home/egk/PycharmProjects/Video'
    vid_start = 'tg-vid'

    # -2, cause -1 is unfinished usually
    latest_video_file = sorted(glob.glob('{}/{}*'.format(vid_dir, vid_start)))[-2]
    latest_video_file_renamed = os.path.splitext(latest_video_file)[0] + '.avi'
    os.rename(latest_video_file, latest_video_file_renamed)
    # return max(video_files, key=os.path.getctime)
    return latest_video_file_renamed


def echo(update, context):
    if update.message.text == 'test':
        reply = ''
        reply += f'effective_user = {update.effective_user}\n\n'
        reply += f'effective_message = {update.effective_message}\n\n'
        reply += f'update_id = {update.update_id}\n\n'
        reply += f'to_json = {update.to_json}\n\n'
        reply += f'from_user = {update.message.from_user}\n\n'
        reply += f'media_group_id = {update.message.media_group_id}\n\n'
        reply += f'chat_id = {update.message.chat_id}\n\n'
        context.bot.send_message(chat_id=update.effective_chat.id, text=reply)
    elif update.message.text.lower().startswith('mirror'):
        context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
    elif update.message.text.lower() in ['video last', 'lastvid', 'last']:
        last_vid_name = find_latest_video()
        vid_size = round(os.stat(last_vid_name).st_size / 1024, 2)
        print('Sending {}, {} KB'.format(last_vid_name, vid_size))
        context.bot.send_video(chat_id=update.effective_chat.id, video=open(last_vid_name, 'rb'), supports_streaming=False)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Else')


if __name__ == '__main__':
    # Handler for /start command
    start_handler = CommandHandler('start', start)
    # Handler for /video command
    video_handler = CommandHandler('video', video)
    # Handler for messages, id only = Rnnmk
    echo_handler = MessageHandler(Filters.text & Filters.user(username=['Rnnmk']), echo)
    # echo_handler = MessageHandler(Filters.user(username='Rnnmk'), echo)

    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(video_handler)
    dispatcher.add_handler(start_handler)

    print('1')
    updater.start_polling()
    print('2')

    while True:
        send_message()
        time.sleep(10)
