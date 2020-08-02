import os
from moviepy.editor import *
from natsort import natsorted


def columbine(path, output):
    for root, dirs, files in os.walk(path):
        files = natsorted(files)
        L = []
        for file in files[:len(files)//2]:
            if os.path.splitext(file)[1] == '.mp4':
                filePath = os.path.join(root, file)
                video = VideoFileClip(filePath)
                L.append(video)
        clipbuf1 = concatenate_videoclips(L, method='compose')
        L = []
        for file in files[len(files)//2:]:
            if os.path.splitext(file)[1] == '.mp4':
                filePath = os.path.join(root, file)
                video = VideoFileClip(filePath)
                L.append(video)
        clipbuf2 = concatenate_videoclips(L, method='compose')

    final_clip = concatenate_videoclips([clipbuf1, clipbuf2], method='compose')
    final_clip.write_videofile(
        output, fps=24, logger=None, write_logfile=False)
    for v in L:
        v.close()
    final_clip.close()


p = os.path.join('E:/', 'Videos', 'tes')
print(p)
columbine(p, os.path.join(p, 'out.mp4'))
