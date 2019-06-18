import os
from io import BytesIO
from glob import glob

import tkinter as tk
from PIL import Image, ImageTk

from video_utility import select_frame


def valid(event):
    global valid_count

    valid_count += 1
    filename = hex(valid_count)[2:].zfill(5) + '.png'
    with open(os.path.join(valid_path, filename), 'wb') as file:
        file.write(data)
    root.destroy()


def invalid(event):
    global invalid_count

    invalid_count += 1
    filename = hex(invalid_count)[2:].zfill(5) + '.png'
    with open(os.path.join(invalid_path, filename), 'wb') as file:
        file.write(data)
    root.destroy()


year = input("Year: ")
event = input("Event: ")
valid_path = os.path.join('..', 'data', 'images', year, 'valid')
invalid_path = os.path.join('..', 'data', 'images', year, 'invalid')
valid_count = len(glob(os.path.join(valid_path, '*')))
invalid_count = len(glob(os.path.join(invalid_path, '*')))

if not os.path.isdir(valid_path):
    os.makedirs(valid_path)
if not os.path.isdir(invalid_path):
    os.makedirs(invalid_path)

number = int(input("Number of images: "))

for _ in range(number):
    root = tk.Tk()
    data = select_frame(year, event)
    image = Image.open(BytesIO(data))
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(root, image=photo)
    label.image = photo
    label.pack()
    root.bind('<Right>', valid)
    root.bind('<Left>', invalid)

    root.mainloop()

    del data
    del image
    del photo
    del label
    del root
