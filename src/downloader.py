"""
A simple CLI application intended for batch downloads of FRC match
videos. Videos download to `data/videos/{year}/{event}`.

Depends on pytube to download YouTube videos - however, there seems to
be a bug in the current release of pytube. As a workaround, I made the
change proposed on https://github.com/nficano/pytube/pull/395 to my
local pytube version, and would advise doing the same until the pull
request is merged into pytube.
"""

import json
import random
import os
from glob import glob
from datetime import datetime

import requests
import pytube
from colors import color
from tqdm import tqdm


class Progress(tqdm):
    received = 0

    def update_remaining(self, stream, chunk, file_handle, bytes_remaining):
        self.update(self.total - bytes_remaining - self.received)
        self.received = self.total - bytes_remaining


with open("tba.json", "r") as auth:
    headers = json.load(auth)
api_url = 'https://www.thebluealliance.com/api/v3'

response = requests.get('{}/status'.format(api_url), headers=headers)
if response.status_code != 200:
    print(color("The Blue Alliance API is currently down. " \
                "Please try again later.", fg='red'))
    raise SystemExit

while True:
    print()

    event_key = input("Event key: ")
    response = requests.get('{}/event/{}'.format(api_url, event_key),
                            headers=headers)
    if response.status_code != 200:
        print(color("Event key invalid.", fg='red'))
        continue
    body = json.loads(response.text)
    year = body['year']
    event_code = body['event_code']

    response = requests.get('{}/event/{}/matches'.format(api_url, event_key),
                            headers=headers)
    assert response.status_code == 200
    all_matches = json.loads(response.text)
    matches = [match for match in all_matches
               if any(video['type'] == 'youtube' for video in match['videos'])]

    total = len(matches)
    if total == 0:
        print(color("No matches with video found.", fg='red'))
        continue
    print(color("{} match(es) with video loaded ({} total)."
                .format(total, len(all_matches)), fg='green'))

    while True:
        number = input("Number of matches (blank to download all): ")
        if number == '':
            n = total
            break
        elif number.isdigit():
            n = int(number)
            if n <= 0:
                print(color("Number of matches must be positive.", fg='red'))
                continue
            elif n > total:
                n = total
            break
        else:
            print(color("Invalid number.", fg='red'))

    path = os.path.join('..', 'data', 'videos', str(year), event_code)
    if not os.path.isdir(path):
        os.makedirs(path)

    print("Downloading {} match(es).".format(n))
    random.shuffle(matches)
    i = 0
    index = -1
    while i < n:
        index += 1
        match = matches[index]
        key = match['key']
        if any(glob(os.path.join(path, key) + "*")):
            continue
        print("Current match: {}".format(key))

        videos = [v for v in match['videos'] if v['type'] == 'youtube']
        for j, video in enumerate(videos):
            url = pytube.extract.watch_url(video['key'])
            print("YouTube URL: {}".format(url))

            print("Downloading...")
            start = datetime.now()
            yt = pytube.YouTube(url)
            stream = yt.streams.first()
            with Progress(total=stream.filesize,
                          unit='B',
                          unit_scale=True,
                          bar_format='{{l_bar}}{}{{r_bar}}'
                          .format(color('{bar}', fg='green')),
                          dynamic_ncols=True) as progress:
                yt.register_on_progress_callback(progress.update_remaining)
                stream.download(output_path=path, filename=key + '_' + str(j))

            elapsed = datetime.now() - start
            print(color("Download complete. ", fg='green') +
                  "({} elapsed)".format(elapsed))

        i += 1