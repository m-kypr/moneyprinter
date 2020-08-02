import os
import json


DIR = os.path.dirname(os.path.realpath(__file__))


def gen(name, meta):
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
    template = f"""({name} Top Twitch Clips)
    
Follow {name}!

Twitch: http://twitch.tv/{name}
Twitter: http://twitter.com/{twitter_name}
Instagram: http://instagram.com/{instagram_name}

Thanks for watching! :D
Subscribe for more clips of {nick}!

#{name} #{nick} #{name}highlights #twitch #clips

{nick},{name},{name}highlights,highlights,{nick}highlights,clips,best of

"""
    if write:
        open(metadir, 'w').write(json.dumps(meta))
    return template


metadir = os.path.join(DIR, 'meta.json')
if not os.path.isfile(metadir):
    open(metadir, 'w+').write('{}')
meta = json.loads(open(metadir, 'r').read())
configdir = os.path.join(DIR, 'config.json')
config = json.loads(open(configdir, 'r').read())
channels = config['channels']
for channel in channels:
    r = gen(channel, meta)
    print(r)
