import os
import json
import warnings
from glob import glob
from io import BytesIO

import ffmpeg
import numpy as numpy
from scipy.fftpack import fft
from scipy.signal import butter, lfilter, correlate
from scipy.io import wavfile
from colors import color
from tqdm import tqdm

START_LOW = 600
START_HIGH = 3000
END_LOW = 2000
END_HIGH = 4000

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


def localize(signal, sample, lowcut, highcut, freq):
    filtered = butter_bandpass_filter(signal, lowcut, highcut, freq, order=6)
    with warnings.catchwarnings():
        corr = correlate(filtered, sample)
    return abs(corr).argmax() - sample.size


def tag_video(filename):
    rate, audio = extract_audio(filename)
    start = localize(audio, start_sample, START_LOW, START_HIGH, rate)
    end = localize(audio, end_sample, END_LOW, END_HIGH, rate)
    return {
        'start': start / rate,
        'end': end / rate
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