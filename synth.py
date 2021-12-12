from pathlib import Path
import simpleaudio
import argparse
from nltk.corpus import stopwords, cmudict
from nltk.tokenize import word_tokenize
import numpy as np

class Synth:
    def __init__(self, wav_folder, diphones_seq):
        self.diphones_seq = diphones_seq
        self.diphones = self.load_diphone_data(wav_folder)

    def load_diphone_data(self, wav_folder):
        diphones = {}
        all_diphone_wav_files = (str(item) for item in Path(wav_folder).glob('*.wav') if item.is_file())
        all_diphone_wav_files_list = []
        for wav_file in all_diphone_wav_files:
            all_diphone_wav_files_list.append(wav_file)

        wave_list = []
        for seq in self.diphones_seq:
            print(seq)
            for wav_file in all_diphone_wav_files_list:
                if ("diphones\\" + seq + ".wav") == wav_file:
                    wave_list.append(wav_file)
            diphones[seq] = wave_list
        return diphones


class Utterance:
    def __init__(self, phrase):
        print(f'Making utterance to synthesise phrase: {phrase}')  # just a hint - can be deleted
        stop_words = set(stopwords.words('english'))
        # words cut
        word_tokens = word_tokenize(phrase)

        # filtered_sentence = [w for w in word_tokens if not w in stop_words]
        # word_sequence = [w.lower() for w in filtered_sentence]
        word_sequence = [w.lower() for w in word_tokens]
        self.word_sequence = word_sequence
        print("words cut complete..." + str(self.word_sequence))


    def get_phone_seq(self):
        phone_seq = []
        for word in self.word_sequence:
            print(cmudict.dict()[word][0])
            phone_seq.append(cmudict.dict()[word][0])
        return phone_seq


    def get_diphone_seq(self, phone_seq_list):
        diphone_seq = []
        diphone_seq.append("pau-{s}".format(s=str(phone_seq_list[0][0]).lower()))
        for phone_seq in phone_seq_list:
            tem = ""
            i = 0
            j = i + 1
            while (i < j & j < len(phone_seq)):
                for s1 in phone_seq[i]:
                    if str(s1) not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                        tem += str(s1).lower()
                tem += "-"
                for s2 in phone_seq[j]:
                    if str(s2) not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                        tem += str(s2).lower()
                diphone_seq.append(tem)
                tem = ""
                i += 1
                j += 1
        # diphone_seq.append(str(phone_seq_list[-1]).lower())
        diphone_seq.append("{s}-pau".format(s=str(phone_seq_list[-1]).lower()))
        return diphone_seq


# NOTE: DO NOT CHANGE ANY OF THE ARGPARSE ARGUMENTS - CHANGE NOTHING IN THIS FUNCTION
def process_commandline():
    parser = argparse.ArgumentParser(
        description='A basic text-to-speech app that synthesises speech using diphone concatenation.')

    # basic synthesis arguments
    parser.add_argument('--diphones', default="./diphones",
                        help="Folder containing diphone wavs")
    parser.add_argument('--play', '-p', action="store_true", default=False,
                        help="Play the output audio")
    parser.add_argument('--outfile', '-o', action="store", dest="outfile",
                        help="Save the output audio to a file", default=None)
    parser.add_argument('phrase', nargs='?',
                        help="The phrase to be synthesised")

    parser.add_argument('--volume', '-v', default=None, type=int,
                        help="An int between 0 and 100 representing the desired volume")
    parser.add_argument('--spell', '-s', action="store_true", default=False,
                        help="Spell the input text instead of pronouncing it normally")
    parser.add_argument('--reverse', '-r', action="store", default=None, choices=['words', 'phones', 'signal'],
                        help="Speak backwards in a mode specified by string argument: 'words', 'phones' or 'signal'")
    parser.add_argument('--fromfile', '-f', action="store", default=None,
                        help="Open file with given name and synthesise all text, which can be multiple sentences.")
    parser.add_argument('--crossfade', '-c', action="store_true", default=False,
                        help="Enable slightly smoother concatenation by cross-fading between diphone units")

    args = parser.parse_args()

    if (args.fromfile and args.phrase) or (not args.fromfile and not args.phrase):
        parser.error('Must supply either a phrase or "--fromfile" to synthesise (but not both)')

    return args


if __name__ == "__main__":
    args = process_commandline()
    print(args)
    utt = Utterance(phrase=args.phrase)     # straightforward sequence of words
    if args.reverse == "words":
        utt.word_sequence = utt.word_sequence[::-1]
        print("reverse word...." + str(utt.word_sequence))

    phone_seq = utt.get_phone_seq()
    print("=============phone_seq===============")
    print(phone_seq)
    if args.reverse == "phones":
        phone_seq = phone_seq[::-1]
    diphone_seq = utt.get_diphone_seq(phone_seq)
    print("=============diphone_seq===============")
    print(diphone_seq)
    print(f'Will load wavs from: {args.diphones}')
    diphone_synth = Synth(wav_folder=args.diphones, diphones_seq=diphone_seq).diphones
    print("=============diphone_synth===============")
    print(diphone_synth)
    out = simpleaudio.Audio(rate=1000)
    out_data = out.data
    out_file_name = "out/" + str(args.outfile)
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

        out.data = out_data[:int(len(out_data)/10)]
        out.close_input_stream()
        if args.volume:
            out.change_speed(args.volume)
        out.change_speed(1)
        out.save(out_file_name)
