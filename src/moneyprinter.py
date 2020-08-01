import shutil
from natsort import natsorted
from moviepy.editor import concatenate_videoclips, VideoFileClip
import uuid
import requests
import os
import json
import random
import string
import threading
import time
import praw

import googleapiclient.discovery
from twitch import TwitchClient


def downloadfile(name, url):
    r = requests.get(url)
    f = open(name, 'wb')
    for chunk in r.iter_content(chunk_size=255):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    f.close()


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s


def columbine(path, output):
    L = []

    for root, dirs, files in os.walk(path):

        # files.sort()
        files = natsorted(files)
        for file in files:
            if os.path.splitext(file)[1] == '.mp4':
                filePath = os.path.join(root, file)
                video = VideoFileClip(filePath)
                L.append(video)

    final_clip = concatenate_videoclips(L)
    final_clip.to_videofile(output, fps=24, remove_temp=False)


def tw(client, channel):
    tmp = os.path.join('tmp', channel)
    tmp_clips = os.path.join(tmp, 'clips')
    try:
        os.mkdir(tmp)
    except FileExistsError:
        pass
    if os.path.isfile(tmp_clips):
        clips = json.loads(open(tmp_clips, 'r').read())['clips']
    else:
        clips = client.clips.get_top(channel=channel, limit=25)
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
    for c in clips:
        path = "".join([a for a in c['title'] if a.isalpha()
                        or a.isdigit() or a == ' ']).rstrip()
        path = path + '.mp4'
        path = os.path.join(tmp, path)
        if not os.path.isfile(path):
            url = rchop(c['thumbnails']['medium'],
                        '-preview-480x272.jpg') + '.mp4'
            print(url)
            downloadfile(path, url)

    columbine(tmp, os.path.join('out', channel + '.mp4'))
    time.sleep(5)
    shutil.rmtree(tmp)


def yt():
    api_service_name = "youtube"
    api_version = "v3"
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey='AIzaSyAkZZWZNUsAHm2E-DB-8K0pqhV7Rsa0pKM')

    request = youtube.search().list(
        part="snippet",
        q="vxWgy9x-egw"
    )
    response = request.execute()
    print(response)


try:
    os.mkdir('out')
except FileExistsError:
    pass
try:
    os.mkdir('tmp')
except FileExistsError:
    pass
channels = ['xqcow', 'pokimane', 'loserfruit',
            'loeya', 'itshafu', 'Asmongold', 'nickmercs', 'sodapoppin', 'rubius', 'TheRealKnossi']
client = TwitchClient(client_id='y57j7itk3vsy5m4urko0mwvjske7db')
threads = []
channels.reverse()
for channel in channels:
    if len(threads) < 7:
        threads.append(threading.Thread(target=tw, args=(client, channel, )))
        threads[-1].start()
    time.sleep(5)

for t in threads:
    t.join()
