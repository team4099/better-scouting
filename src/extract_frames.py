import os
from io import BytesIO

import tkinter as tk
from PIL import Image, ImageTk

from video_utility import select_frame

year = input("Year: ")
valid_path = os.path.join('..', 'data', 'images', year, 'valid')
invalid_path = os.path.join('..', 'data', 'images', year, 'invalid')

if not os.path.isdir(valid_path):
    os.makedirs(valid_path)
if not os.path.isdir(invalid_path):
    os.makedirs(invalid_path)

while True:
    root = tk.Tk()
    image = Image.open(BytesIO(select_frame()))
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(root, image=photo)
    label.image = photo
    label.pack()
    root.mainloop()

    if input("[Enter any key to stop/press enter to continue] "):
        break