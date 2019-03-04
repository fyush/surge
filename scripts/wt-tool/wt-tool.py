#!/usr/bin/env python3
#
# A tool for creating, destructing, and querying surge WT files
# Run wt-tool.py --help for instructions

from optparse import OptionParser
from itertools import tee
from os import listdir
from os.path import isfile, join
import wave


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def read_wt_header(fn):
    with open(fn, "rb") as f:
        header = {}
        header["ident"] = f.read(4)
        # FIXME: Check that this is actually vawt

        header["wavsz"] = f.read(4)
        header["wavct"] = f.read(2)
        header["flags"] = f.read(2)

    ws = header["wavsz"]
    sz = 0
    mul = 1
    for b in ws:
        sz += b * mul
        mul *= 256

    wc = header["wavct"]
    ct = 0
    mul = 1
    for b in wc:
        ct += b * mul
        mul *= 256

    header["wavsz"] = sz
    header["wavct"] = ct

    fl = header["flags"]
    flags = {}
    flags["is_sample"] = (fl[0] & 0x01 != 0)
    flags["loop_sample"] = (fl[0] & 0x02 != 0)
    flags["format"] = "int16" if (fl[0] & 0x04 != 0) else "float32"
    flags["samplebytes"] = 2 if (fl[0] & 0x04 != 0) else 4

    header["flags"] = flags

    header["filesize"] = header["flags"]["samplebytes"] * header["wavsz"] * header["wavct"] + 12

    return header


def explode(fn, wav_dir):
    print("Exploding '" + fn + "' into '" + wav_dir + "'")
    header = read_wt_header(fn)
    if(header["flags"]["samplebytes"] != 2):
        raise RuntimeError("Can only handle 16 bit wt files right now")

    with open(fn, "rb") as f:
        f.read(12)
        for i in range(0, header["wavct"]):
            # 3 is fine since we are limited to 512 tables
            fn = "{0}//wt_sample_{1:03d}.wav".format(wav_dir, i)
            print("Creating " + fn)

            with wave.open(fn, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setframerate(44100)
                wav_file.setsampwidth(header["flags"]["samplebytes"])
                wav_file.setnframes(header["wavsz"])

                bdata = f.read(header["wavsz"] * header["flags"]["samplebytes"])

                wav_file.writeframes(bdata)


def create(fn, wavdir):
    onlyfiles = [f for f in listdir(wavdir) if (isfile(join(wavdir, f)) and f.endswith(".wav"))]
    onlyfiles.sort()

    with wave.open(join(wavdir, onlyfiles[0]), "rb") as wf:
        c0 = wf.getnchannels()
        fr = wf.getframerate()
        sw = wf.getsampwidth()
        nf = wf.getnframes()

    if (c0 != 1):
        raise RuntimeError("wt-tool only processes mono inputs")
    if (fr != 44100):
        raise RuntimeError("Please use 44.1k mono 16bit PCM wav files")
    if (sw != 2):
        raise RuntimeError("Please use 44.1k mono 16bit PCM wav files")

    print("Creating '{0}' with {1} tables of length {2}".format(fn, len(onlyfiles), nf))

    with open(fn, "wb") as outf:
        outf.write(b'vawt')
        outf.write(nf.to_bytes(4, byteorder='little'))
        outf.write((len(onlyfiles)).to_bytes(2, byteorder='little'))
        outf.write(bytes([4, 0]))
        for inf in onlyfiles:
            with wave.open(join(wavdir, inf), "rb") as wav_file:
                content = wav_file.readframes(nf * sw)
                outf.write(content)


def info(fn):
    print("WT :'" + fn + "'")
    header = read_wt_header(fn)
    print("  contains  %d samples" % header["wavct"])
    print("  of length %d" % header["wavsz"])
    print("  in format %s" % header["flags"]["format"])
    if(header["flags"]["is_sample"]):
        print("   is a sample")
    if(header["flags"]["loop_sample"]):
        print("   loop_sample = true")


def main():
    parser = OptionParser(usage="usage: % prog [options]")
    parser.add_option("-a", "--action", dest="action",
                      help="undertake action. One of 'info', 'create' or 'explode'", metavar="ACTION")
    parser.add_option("-f", "--file", dest="file",
                      help="wt_file being inspected or created", metavar="FILE")
    parser.add_option("-d", "--wav_dir", dest="wav_dir",
                      help="Directory containing or recieving wav files for wt", metavar="DIR")
    (options, args) = parser.parse_args()

    act = options.action
    if act == "create":
        create(options.file, options.wav_dir)
    elif act == "explode":
        explode(options.file, options.wav_dir)
    elif act == "info":
        info(options.file)
    else:
        print("Unknown action")


if __name__ == "__main__":
    main()
