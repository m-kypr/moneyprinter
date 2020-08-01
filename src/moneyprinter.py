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
import sys

import googleapiclient.discovery
from twitch import TwitchClient


THREADS = 3


if len(sys.argv) > 1:
    THREADS = int(sys.argv[1])


def downloadfile(name, url):
    r = requests.get(url)
    f = open(name, 'wb')
    for chunk in r.iter_content(chunk_size=255):
        if chunk:
            f.write(chunk)
    f.close()


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s


def columbine(path, output):
    L = []
    for root, dirs, files in os.walk(path):
        files = natsorted(files)
        for file in files:
            if os.path.splitext(file)[1] == '.mp4':
                filePath = os.path.join(root, file)
                video = VideoFileClip(filePath)
                L.append(video)

    final_clip = concatenate_videoclips(L)
    final_clip.write_videofile(
        output, fps=24, logger=None, write_logfile=False)


def tw(client, channel):
    log = os.path.join('log', channel)
    tmp = os.path.join('tmp', channel)
    tmp_clips = os.path.join(tmp, 'clips')

    def print(str, end='\n'):
        open(log, 'a').write(str + end)

    try:
        os.mkdir(tmp)
    except FileExistsError:
        pass
    if os.path.isfile(tmp_clips):
        print('**loading clips from cache**', end='')
        start = time.time()
        clips = json.loads(open(tmp_clips, 'r').read())['clips']
        print(' : ' + str(time.time() - start))
    else:
        print('**downloading top clips meta info**', end='')
        start = time.time()
        clips = client.clips.get_top(channel=channel, limit=1)
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
        print(' : ' + str(time.time() - start))
    print('**downloading top clips**', end='')
    start = time.time()
    for c in clips:
        path = "".join([a for a in c['title'] if a.isalpha()
                        or a.isdigit() or a == ' ']).rstrip()
        path = path + '.mp4'
        path = os.path.join(tmp, path)
        if not os.path.isfile(path):
            url = rchop(c['thumbnails']['medium'],
                        '-preview-480x272.jpg') + '.mp4'
            downloadfile(path, url)
    print(' : ' + str(time.time() - start))
    print('**combining clips**', end='')
    start = time.time()
    columbine(tmp, os.path.join('out', channel + '.mp4'))
    print(' : ' + str(time.time() - start))
    time.sleep(5)
    print('**deleting cache**', end='')
    start = time.time()
    shutil.rmtree(tmp)
    print(' : ' + str(time.time() - start))


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
try:
    os.mkdir('log')
except FileExistsError:
    pass
channels = ['xqcow', 'pokimane', 'loserfruit',
            'loeya', 'itshafu', 'Asmongold', 'nickmercs', 'sodapoppin', 'rubius', 'TheRealKnossi']
client = TwitchClient(client_id='y57j7itk3vsy5m4urko0mwvjske7db')
ts = []
for channel in channels:
    while True:
        if len(ts) < THREADS:
            ts.append(threading.Thread(
                target=tw, args=(client, channel, )))
            ts[-1].start()
            break
        time.sleep(5)

for t in ts:
    t.join()
    ts.remove(t)
