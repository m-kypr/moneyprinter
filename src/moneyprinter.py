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
import sys

import googleapiclient.discovery
from twitch import TwitchClient
from praw import Reddit

DIR = os.path.dirname(os.path.realpath(__file__))

configdir = os.path.join(DIR, 'config.json')
config = json.loads(open(configdir, 'r').read())
CHANNELS = config['channels']
LIMIT = config['limit']
THREADS = config['threads']
THREADING = bool(config['threading'])
reddit_client = Reddit(client_id='G0sWd3t4MfZuqg', client_secret="pI-xHd4HnMe8TXHXtIV_SHQH5ig",
                       user_agent='Mozilla/5.0')
twitch_client = TwitchClient(client_id='y57j7itk3vsy5m4urko0mwvjske7db')
s = reddit_client.subreddit('xqcow')


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

    final_clip = concatenate_videoclips(L, method='compose')
    final_clip.write_videofile(
        output, fps=24, logger=None, write_logfile=False)
    for v in L:
        v.close()
    final_clip.close()


def tw(client, channel, pid=None):
    if THREADING:
        log = os.path.join('log', channel)

        def printlog(str, end='\n'):
            open(log, 'a').write(str + end)

    tmp = os.path.join('tmp', channel)
    tmp_clips = os.path.join(tmp, 'clips')

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
        clips = client.clips.get_top(channel=channel, limit=LIMIT)
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
        print(' : ' + str(time.time() - start))
    dlClips(clips, tmp)
    print('**combining clips**', end='')
    start = time.time()
    columbine(tmp, os.path.join('out', channel + '.mp4'))
    print(' : ' + str(time.time() - start))
    time.sleep(5)
    print('**deleting cache**', end='')
    start = time.time()
    shutil.rmtree(tmp)
    print(' : ' + str(time.time() - start))
    if THREADING:
        del ts[pid]


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


def dlClips(clips, tmp):
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


def reddit(subreddit='LivestreamFail'):
    tmp = os.path.join('tmp', subreddit)
    tmp_clips = os.path.join(tmp, 'clips')

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
        subr = reddit_client.subreddit(subreddit)
        top = subr.top('day')
        top = [next(top) for _ in range(LIMIT)]
        start = time.time()
        clips = [twitch_client.clips.get_by_slug(
            s.url.split('/')[-1]) for s in top]
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
        print(' : ' + str(time.time() - start))
    dlClips(clips, tmp)
    print('**combining clips**', end='')
    start = time.time()
    columbine(tmp, os.path.join('out', subreddit + '.mp4'))
    print(' : ' + str(time.time() - start))


def twitch():
    print('THREADING: '+str(THREADING))
    if THREADING:
        ts = []
    for channel in CHANNELS:
        if THREADING:
            while True:
                if len(ts) < THREADS:
                    pid = len(ts)
                    ts.append(threading.Thread(
                        target=tw, args=(twitch_client, channel, pid, )))
                    ts[-1].start()
                    break
                time.sleep(5)
        else:
            tw(twitch_client, channel)

    if THREADING:
        for t in ts:
            t.join()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        THREADS = int(sys.argv[1])
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
    reddit()
    #twitch()
