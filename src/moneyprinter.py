import glob
from natsort import natsorted
from moviepy.editor import concatenate_videoclips, VideoFileClip
import uuid
import requests
import os
import json
import random
import string

import googleapiclient.discovery
from twitch import TwitchClient


def downloadfile(name, url):
    r = requests.get(url)
    print("****Connected****")
    f = open(name, 'wb')
    print("Donloading.....")
    for chunk in r.iter_content(chunk_size=255):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    print("Done")
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
    if os.path.isfile('clips.tmp'):
        clips = json.loads(open('clips.tmp', 'r').read())['clips']
    else:
        clips = client.clips.get_top(channel=channel, limit=25)
        open('clips.tmp', 'w').write(json.dumps(
            {'clips': clips}, indent=4, sort_keys=True, default=str))
    for c in clips:
        path = "".join([a for a in c['title'] if a.isalpha()
                        or a.isdigit() or a == ' ']).rstrip()
        path = os.path.join('dl', path) + '.mp4'
        if not os.path.isfile(path):
            url = rchop(c['thumbnails']['medium'],
                        '-preview-480x272.jpg') + '.mp4'
            print(url)
            downloadfile(path, url)

    columbine('dl/', os.path.join('out', channel + '.mp4'))
    os.remove('clips.tmp')
    files = glob.glob('dl/*')
    for f in files:
        os.remove(f)


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
    os.mkdir('dl')
except FileExistsError:
    pass
try:
    os.mkdir('out')
except FileExistsError:
    pass
channels = ['xqcow', 'pokimane', 'loserfruit',
            'loeya', 'kittyplays', 'itshafu', 'OMGitsfirefoxx', 'Rubius', 'auronplay', 'TheRealKnossi']
client = TwitchClient(client_id='y57j7itk3vsy5m4urko0mwvjske7db')
for channel in channels[1:]:
    tw(client, channel)
