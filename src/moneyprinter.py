from oauth2client.tools import argparser, run_flow
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import httplib2
import http.client
import shutil
from natsort import natsorted
from moviepy.editor import *
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
VIDEOLENGTH = config['videolength']
THREADS = config['threads']
TWITCH_CLIENT_ID = config['twitch_client_id']
THREADING = bool(config['threading'])
reddit_client = Reddit(client_id='G0sWd3t4MfZuqg', client_secret="pI-xHd4HnMe8TXHXtIV_SHQH5ig",
                       user_agent='Mozilla/5.0')
twitch_client = TwitchClient(client_id=TWITCH_CLIENT_ID)
s = reddit_client.subreddit('xqcow')
IMAGEMAGICK_BINARY = os.getenv(
    'IMAGEMAGICK_BINARY', 'C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\magick.exe')


httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(DIR, CLIENT_SECRETS_FILE))
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    resumable_upload(insert_request)


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print("Video id '%s' was successfully uploaded." %
                          response['id'])
                else:
                    exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)


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


def columbine(path, output, chat=False):
    L = []
    for root, dirs, files in os.walk(path):
        files = natsorted(files)
        for file in files:
            if os.path.splitext(file)[1] == '.mp4':
                print(file)
                filePath = os.path.join(root, file)
                video = VideoFileClip(filePath)
                if chat:
                    chatters = json.loads(open(os.path.join(root, os.path.splitext(file)
                                                            [0] + '.json'), 'r').read())
                    comments = chatters['comments']
                    txt = '\n'.join([c['message']['body'] for c in comments])
                    # print(txt)
                    duration = int(comments[-1]['content_offset_seconds'] -
                                   comments[0]['content_offset_seconds']) - 1
                    print(duration)
                    text = TextClip(txt='foo', fontsize=12, color='white').set_position(
                        ("right", "bottom")).set_duration(duration)
                    video = CompositeVideoClip(clips=[text, video])
                # print(video)
                L.append(video)

    print(L)
    final_clip = concatenate_videoclips(L, method='compose')
    final_clip.write_videofile(
        output, fps=24, logger=None, write_logfile=False)
    for v in L:
        v.close()
    final_clip.close()


def comments(client_id, videoid, offset):
    url = f'https://api.twitch.tv/v5/videos/{videoid}/comments?content_offset_seconds={offset}'
    r = json.loads(requests.get(url, headers={'Client-ID': client_id}).text)
    return r


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
        print('**loading clips from cache**', end=':', flush=True)
        start = time.time()
        clips = json.loads(open(tmp_clips, 'r').read())['clips']
        print(str(time.time() - start))
    else:
        print('**downloading top clips meta info**', end=':', flush=True)
        start = time.time()
        length = 0
        clips = []
        clipsbuf = client.clips.get_top(channel=channel, limit=LIMIT)
        for clip in clipsbuf:
            if length < VIDEOLENGTH:
                clips.append(clip)
                length += int(clip['duration'])
            else:
                break
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
        print(str(time.time() - start))
    print('**downloading top clips**', end=':', flush=True)
    start = time.time()
    for clip in clips:
        path = os.path.join(tmp, "".join([a for a in clip['title'] if a.isalpha()
                                          or a.isdigit() or a == ' ']).rstrip())
        if not os.path.isfile(path + '.mp4'):
            vod = clip['vod']
            comms = comments(TWITCH_CLIENT_ID, vod['id'], vod['offset'])
            url = rchop(clip['thumbnails']['medium'],
                        '-preview-480x272.jpg') + '.mp4'
            downloadfile(path + '.mp4', url)
            open(path + '.json', 'w').write(json.dumps(comms))
    print(str(time.time() - start), flush=True)
    print('**combining clips**', end=':', flush=True)
    start = time.time()
    columbine(tmp, os.path.join('out', channel + '_twitch.mp4'), chat=False)
    print(str(time.time() - start))
    time.sleep(5)
    print('**deleting cache**', end=':', flush=True)
    start = time.time()
    shutil.rmtree(tmp)
    print(str(time.time() - start))
    if THREADING:
        del ts[pid]


def get_authenticated_service(args):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                                   scope=YOUTUBE_UPLOAD_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


def gentwitch(name, meta):
    write = False
    try:
        meta[name]
    except KeyError as e:
        meta[name] = {}
    try:
        nick = meta[name]['nick']
    except KeyError as e:
        nick = input(f'Nick name of {name}: ')
        meta[name]['nick'] = nick
        write = True
    try:
        twitter_name = meta[name]['twitter_name']
    except KeyError as e:
        twitter_name = input(f'Twitter name of {name}: ')
        meta[name]['twitter_name'] = twitter_name
        write = True
    try:
        instagram_name = meta[name]['instagram_name']
    except KeyError as e:
        instagram_name = input(f'Instagram name of {name}: ')
        meta[name]['instagram_name'] = instagram_name
        write = True
    if write:
        open(metadir, 'w').write(json.dumps(meta))
    return f'({name} Top Twitch Clips)', f"""Follow {name}!

Twitch: http://twitch.tv/{name}
Twitter: http://twitter.com/{twitter_name}
Instagram: http://instagram.com/{instagram_name}

Thanks for watching! :D
Subscribe for more clips of {nick}!

# {name} #{nick} #{name}highlights #twitch #clips #best of
    """, f'{nick},{name},{name}highlights,highlights,{nick}highlights,clips,best of'


def genreddit(reddit):
    return f'(Best r/{reddit} Compilation)', f"""Source:
https://www.reddit.com/r/{reddit}/

# reddit #livestreamfail #fail #compilation #best of #clips""", f'{reddit},highlights,{reddit}highlights,clips,best of,compilation'


def youtube(category='22', privacyStatus='public'):
    metadir = os.path.join(DIR, 'meta.json')
    if not os.path.isfile(metadir):
        open(metadir, 'w+').write('{}')
    meta = json.loads(open(metadir, 'r').read())
    twitchmeta = meta['twitch']
    from argparse import Namespace
    for subdir, dirs, files in os.walk('out'):
        for file in files:
            filepath = os.path.join('out', file)
            buf = file.split('.')[0].split('_')
            name = buf[0]
            if buf[1] == 'reddit':
                title, description, tags = genreddit(name)
            elif buf[1] == 'twitch':
                title, description, tags = gentwitch(name, twitchmeta)
            title = input(f'Title for {file}: ') + ' ' + title
            args = Namespace(
                auth_host_name='localhost',
                auth_host_port=[8080, 8090],
                category=category,
                description=description,
                file=filepath,
                keywords=tags,
                logging_level='ERROR',
                noauth_local_webserver=False,
                privacyStatus=privacyStatus,
                title=title
            )
            youtube = get_authenticated_service(args)
            try:
                initialize_upload(youtube, args)
            except HttpError as e:
                print("An HTTP error %d occurred:\n%s" %
                      (e.resp.status, e.content))
            os.remove(filepath)


def reddit(subreddit='LivestreamFail', chat=False):
    tmp = os.path.join('tmp', subreddit)
    tmp_clips = os.path.join(tmp, 'clips')
    try:
        os.mkdir(tmp)
    except FileExistsError:
        pass
    if os.path.isfile(tmp_clips):
        print('**loading clips from cache**', end=':', flush=True)
        start = time.time()
        clips = json.loads(open(tmp_clips, 'r').read())['clips']
        print(str(time.time() - start))
    else:
        print('**downloading top clips meta info**', end=':', flush=True)
        start = time.time()
        length = 0
        clips = []
        subr = reddit_client.subreddit(subreddit)
        top = subr.top('day')
        top = [next(top) for _ in range(LIMIT)]
        clipsbuf = [twitch_client.clips.get_by_slug(
            s.url.split('/')[-1]) for s in top]
        for clip in clipsbuf:
            if length < VIDEOLENGTH:
                clips.append(clip)
                length += int(clip['duration'])
            else:
                break
        open(tmp_clips, 'w').write(json.dumps(
            {'clips': clips}, default=str))
        print(str(time.time() - start))
    print('**downloading top clips**', end=':', flush=True)
    start = time.time()
    for clip in clips:
        path = os.path.join(tmp, "".join([a for a in clip['title'] if a.isalpha()
                                          or a.isdigit() or a == ' ']).rstrip())
        if not os.path.isfile(path + '.mp4'):
            if chat:
                vod = clip['vod']
                comms = comments(TWITCH_CLIENT_ID, vod['id'], vod['offset'])
                open(path + '.json', 'w').write(json.dumps(comms))
            url = rchop(clip['thumbnails']['medium'],
                        '-preview-480x272.jpg') + '.mp4'
            downloadfile(path + '.mp4', url)
    print(str(time.time() - start), flush=True)
    print('**combining clips**', end=':', flush=True)
    start = time.time()
    columbine(tmp, os.path.join(
        'out', subreddit + '_reddit.mp4'), chat=chat)
    print(str(time.time() - start))


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
    # reddit()
    twitch()
    youtube()
