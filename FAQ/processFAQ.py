import os
import sys
import subprocess

# Our own Docs To Markdown library.
import docsToMarkdownLib

# Get the command line arguments.
inputFolder = sys.argv[1]
outputFolder = sys.argv[2]

print("Processing FAQ folder: " + inputFolder + " to " + outputFolder, flush=True)
for inputItem in os.listdir(inputFolder):
    fileType = inputItem.rsplit(".", 1)[1].upper()
    if fileType in ["DOCX", "DOC"]:
        # Deal with a DOCX / DOC file - pass it up to the processDOCFile script to deal with.
        subprocess.run(["python3", "../docs-to-markdown/processDOCFile.py", docsToMarkdownLib.normalisePath(inputFolder + "/" + inputItem), docsToMarkdownLib.normalisePath(outputFolder)])
    elif fileType in ["MP4"]:
        # Deal with an MP4 file - use FFmpeg to set the size and format of any videos in this FAQ.
        outputItem = inputItem.rsplit(".", 1)[0] + ".webm"
        # Video files can take time / processing power to deal with, so we check we actually need to update something first before going ahead.
        if not docsToMarkdownLib.checkModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem):
            print("STATUS: Processing FAQ video: " + inputFolder + os.sep + inputItem + " to " + outputFolder + os.sep + outputItem, flush=True)
            
            # Figure out the video's dimensions.
            videoDimensions = os.popen("ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x " + inputFolder + os.sep + inputItem).read().strip()
            videoWidth = int(videoDimensions.split("x")[0])
            videoHeight = int(videoDimensions.split("x")[1])
            
            # Crop the video to a square, centred in the middle, then scale the dimensions to 240x240.
            # Also, normalise the audio - see: http://johnriselvato.com/ffmpeg-how-to-normalize-audio/
            os.system("ffmpeg -i " + inputFolder + os.sep + inputItem + " -filter:v crop=" + str(videoHeight) + ":" + str(videoHeight) + ":" + str(int((videoWidth - videoHeight) / 2)) + ":0,scale=240:240,setsar=1 -filter:a loudnorm=I=-16:LRA=11:TP=-1.5 /tmp/faq.webm > /dev/null 2>&1")
            os.system("mv /tmp/faq.webm " + outputFolder + os.sep + outputItem)
            
            docsToMarkdownLib.makeModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem)
