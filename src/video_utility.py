import os
import json
import warnings
import random
from glob import glob
from io import BytesIO

import ffmpeg
from scipy.fftpack import fft
from scipy.signal import butter, lfilter, correlate
from scipy.io import wavfile
from colors import color
from tqdm import tqdm

START_LOW = 600
START_HIGH = 3000
END_LOW = 2000
END_HIGH = 4000
THRESH = 1e5
MATCH_LENGTH = 150

rate, start_sample = wavfile.read(os.path.join('assets',
                                  'match_start_upsampled.wav'))
_, end_sample = wavfile.read(os.path.join('assets', 'match_end_upsampled.wav'))


def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y


def extract_audio(video):
    out, err = (
        ffmpeg
        .input(video)
        .output('-', format='wav', ac=1, ar=rate)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )
    riff_chunk_size = len(out) - 8
    quotient = riff_chunk_size

    binarray = []
    for _ in range(4):
        quotient, remainder = divmod(quotient, 256)
        binarray.append(remainder)

    riff = out[:4] + bytes(binarray) + out[8:]
    return wavfile.read(BytesIO(riff))


def localize(signal, sample, lowcut, highcut, freq=rate):
    filtered = butter_bandpass_filter(signal, lowcut, highcut, freq)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        corr = abs(correlate(filtered, sample))
    index = corr.argmax()
    return index - sample.size, corr[index]


def tag_video(filename):
    rate, audio = extract_audio(filename)
    start, start_val = localize(audio, start_sample, START_LOW, START_HIGH)
    end, end_val = localize(audio, end_sample, END_LOW, END_HIGH)

    start_time = start / rate
    end_time = end / rate
    if start_val > THRESH > end_val:
        end_time = start_time + MATCH_LENGTH
    elif end_val > THRESH > start_val:
        start_time = end_time - MATCH_LENGTH
    elif start_val < THRESH > end_val:
        start_time = end_time = None

    return {
        'start': start_time,
        'end': end_time
    }


def tag_directory(year='*', event='*', progress=False):
    for folder in glob(os.path.join('..', 'data', 'videos', year, event)):
        if not os.path.isdir(folder):
            continue
        filename = os.path.join(folder, '.metadata')
        if not os.path.exists(filename):
            with open(filename, 'w') as file:
                json.dump({}, file)
        with open(filename, 'r') as file:
            data = json.load(file)

        videos = glob(os.path.join(folder, '*.mp4'))
        if progress == True:
            print("Folder: {}".format(folder))
            videos = tqdm(videos,
                          unit='videos',
                          unit_scale=False,
                          bar_format='{{l_bar}}{}{{r_bar}}'
                          .format(color('{bar}', fg='green')),
                          dynamic_ncols=True)
        for video in videos:
            if video in data:
                continue
            data[video] = tag_video(video)

        with open(filename, 'w') as file:
            json.dump(data, file)


def select_frame(year='*', event='*'):
    videos = glob(os.path.join('..', 'data', 'videos', year, event, '*'))
    video = random.choice(videos)

    folder = os.path.dirname(video)
    data_path = os.path.join(folder, '.metadata')
    if not os.path.exists(data_path):
        raise
    with open(data_path, 'r') as file:
        data = json.load(file)

    match_info = data[video]
    start, end = match_info['start'], match_info['end']
    if start is None or end is None or start > end or start < 0 or end < 0:
        return select_frame(year, event)

    info = ffmpeg.probe(video)['streams'][0]
    framerate = float(info['nb_frames']) / float(info['duration'])
    lower = int(start * framerate)
    upper = int(end * framerate)
    frame_number = random.randint(lower, upper)

    out, err = (
        ffmpeg
        .input(video)
        .filter('select', 'eq(n,{})'.format(frame_number))
        .output('pipe:', format='image2', vcodec='png', vframes=1)
        .run(capture_stdout=True, capture_stderr=True)
    )
    return out
