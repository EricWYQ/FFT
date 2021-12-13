from tkinter import *
from winsound import *
import synth
import simpleaudio
import numpy as np

root = Tk()
root.title("EE629 Text to Speak")
root.geometry('400x400+200+20')

text = Text(root, width=50, height=24)
scroll = Scrollbar(root)

scroll.pack(side=RIGHT, fill=Y)

def transfor(input_text):

    utt = synth.Utterance(phrase=input_text)
    input_text = input_text.replace(" ", "_")
    input_text = input_text.strip("").replace("\n", "")

    phone_seq = utt.get_phone_seq()
    print("=============phone_seq===============")
    print(phone_seq)
    diphone_seq = utt.get_diphone_seq(phone_seq)
    print("=============diphone_seq===============")
    print(diphone_seq)
    diphone_synth = synth.Synth(wav_folder="./diphones", diphones_seq=diphone_seq).diphones
    print("=============diphone_synth===============")
    print(diphone_synth)
    out = simpleaudio.Audio(rate=1000)
    out_data = out.data
    out_file_name = "out/" + str(input_text) + ".wav"
    n = 0
    diphone = list(diphone_synth.keys())
    print("=============keys===============")
    print(diphone)
    diphone_file_list = diphone_synth[diphone[0]]
    print("=============values===============")
    print(diphone_file_list)
    for diphone, diphone_file_list in diphone_synth.items():
        out.open_input_stream()
        for file in diphone_file_list:
            out.load(file)
            out_data = np.append(out_data, out.data)

        out.data = out_data[:int(len(out_data) / 10)]
        out.close_input_stream()
        out.change_speed(1)
        out.save(out_file_name)
    return out_file_name


scroll.config(command=text.yview)
text.config(yscrollcommand=scroll.set)

text.pack()
str1 = 'please clear here text\n' \
       'input your text need to transform to speech\n'

text.insert(INSERT, str1)

def play():
    input_text = text.get('0.0','end')
    print(input_text)
    out_file_name = transfor(input_text)
    return PlaySound(out_file_name, SND_FILENAME)

button = Button(root, text = 'Play Voice', command = play, width=50, height=1)
button.pack()
root.mainloop()
