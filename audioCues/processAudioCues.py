# A script to generate an audio cues page (a folder containing index.html and a set of normalised assets) from a folder of assets (audio clips).

# Standard libraries.
import os
import io
import re
import sys
import html
import shutil
import hashlib
import datetime

# The Pillow image-handling library.
import PIL

# The Pandas data-rpocessing library. Actually just used here for loading the config file - overkill, but Pandas is likely to be installed anyway.
import pandas

# The eyeD3 library for getting information from MP3 files.
import eyed3

# Our own Docs To Markdown library.
import docsToMarkdownLib



devnullString = ">/dev/null 2>&1"
if os.sep == "\\":
    devnullString = " > NUL 2>&1"

# Get a timestamp of when we started.
dateTimeNow = datetime.datetime.now()
timestamp = int(round(dateTimeNow.timestamp()))
dateTimeFormatted = dateTimeNow.strftime("%d-%m-%Y, %H:%M:%S")

# Get any arguments given via the command line.
args = docsToMarkdownLib.processCommandLineArgs(defaultArgs={"processAudio":"true"}, requiredArgs=["input","output"])

print("STATUS: processAudioCues: " + args["input"] + " to " + args["output"], flush=True)
print("Timestamp: " + str(timestamp) + ", Date / Time: " + dateTimeFormatted)

doProcessAudio = False
if args["processAudio"] == "true":
    doProcessAudio = True

# Make sure the output folder exists.
os.makedirs(args["output"], exist_ok=True)



def systemPrint(theCommandLine):
    print(theCommandLine, flush=True)
    os.system(theCommandLine)

def getMD5(theFilename):
    infile = open(theFilename, "rb")
    result = hashlib.md5(infile.read()).hexdigest()
    infile.close()
    return(result)
    
# Check through items in the given input folder, recursing into sub-folders.
# Produces an array (in the global "files" variable) containing tuples of file names and an array of extensions found.
files = {}
inputFolder = docsToMarkdownLib.normalisePath(args["input"])
def listFileNames(theSubFolder):
    global inputFolder
    global files
    
    inputPath = inputFolder + os.sep + theSubFolder
    for inputItem in sorted(os.listdir(inputPath)):
        if os.path.isdir(docsToMarkdownLib.normalisePath(inputPath + os.sep + inputItem)):
            listFileNames(docsToMarkdownLib.normalisePath(theSubFolder + os.sep + inputItem))
        else:
            fileType = ""
            fileSplit = inputItem.rsplit(".", 1)
            fileName = fileSplit[0]
            fileTitle = fileName.strip()
            if re.match("^[0-9]+ *- *.*", fileTitle) != None:
                fileTitle = fileTitle.split("-", 1)[1].strip()
            if not theSubFolder == "":
                fileName = theSubFolder + os.sep + fileName
            if len(fileSplit) == 2:
                fileType = fileSplit[1]
            if not fileName in files.keys():
                files[fileName] = []
            files[fileName].append(fileType)
listFileNames("")

config = []
# Check through the files found above to see if the special "config" file is found anywhere, and if so deal with it and remove it from the list.
for file in files:
    if file.lower() == "config" or file.lower().endswith("/config"):
        for fileType in files.pop(file):
            fullPath = file + "." + fileType
            if fileType.lower() in ["xls", "xlsx", "csv"]:
                print("Config file found: " + fullPath, flush=True)
                config = docsToMarkdownLib.processArgsFile(inputFolder + os.sep + fullPath)

# Check through the files found above to see if the special "items" file is found anywhere, and if so deal with it and remove it from the list.
itemsFiles = []
for file in files:
    if file.lower() == "items" or file.lower().endswith("/items"):
        itemsFiles.append(file)
itemsList = []
for file in itemsFiles:
    for fileType in files.pop(file):
        fullPath = file + "." + fileType
        if fileType.lower() in ["xls", "xlsx", "csv"]:
            print("Items file found: " + fullPath, flush=True)
            if fileType.lower() in ["xls", "xlsx"]:
                itemsSheet = pandas.read_excel(inputFolder + os.sep + fullPath)
            else:
                itemsSheet = pandas.read_csv(inputFolder + os.sep + fullPath)
            # Convert the Pandas dataframe to an array of dicts, lowercasing all the keys and replacing all "NaN" values with empty string.
            for itemsIndex, itemsRow in itemsSheet.iterrows():
                newItem = {}
                for colName in itemsRow.keys():
                    if pandas.isna(itemsRow[colName]):
                        newItem[colName.lower()] = ""
                    else:
                        newItem[colName.lower()] = itemsRow[colName]
                itemsList.append(newItem)

print("Items:", flush=True)
print(itemsList, flush=True)

inputFiles = []
outputFiles = []
outputMD5s = []
outputFolder = docsToMarkdownLib.normalisePath(args["output"])

# Set up the column headings for the data to be included in the front end.
cueList = [["MD5", "Filename", "Title", "Description", "Icon", "Start", "End", "Volume", "Key"]]

# Process any audio files found, in any supported format, into standardised MP3 files ready to be played from the browser.
print("STATUS: processAudioCues - processing found audio files.", flush=True)
for file in files:
    for fileType in files[file]:
        if fileType.lower() in docsToMarkdownLib.audioTypes:
            inputFile = inputFolder + os.sep + file + "." + fileType
            outputFile = outputFolder + os.sep + file + ".mp3"
            if not os.path.exists(outputFile) or not os.path.getmtime(inputFile) == os.path.getmtime(outputFile):
                print("Processing audio file: " + inputFile, flush=True)
                # Process the input audio file with FFMPEG and write out to an MP3, so the output audio is in a consistant format. If the input is an MP3 file, we use the following filters:
                #     silenceremove - remove any silence at the start of the track.
                #     compand - apply some Dynamic Range Compression to the audio to better level out any differences between low and high volume parts of the track.
                #     dynaudnorm - set the loudest part of the track to max volume, try and have a reasonably consistant sound level.
                # Otherwise, the input file is left unprocessed (other than being re-written as an MP3 file).
                ffmpegCommand = "ffmpeg -y -i \"" + inputFile + "\" "
                #if inputFile.lower().endswith(".mp3"):
                ffmpegCommand = ffmpegCommand + "-filter:a \"silenceremove=1:0:-45dB,compand=0|0:1|1:-90/-900|-70/-70|-30/-9|0/-3:6:0:0:0,dynaudnorm=peak=1\" "
                ffmpegCommand = ffmpegCommand + "-vn -ar 44100 -ac 2 -b:a 192k \"" + outputFile + "\"" + devnullString
                systemPrint(ffmpegCommand)
                # Set file modification time so we can skip the conversion next time if the input file hasn't changed.
                inputFileStats = os.stat(inputFile)
                os.utime(outputFile, (inputFileStats.st_atime, inputFileStats.st_mtime))
            if os.path.exists(outputFile):
                inputFiles.append(file + "." + fileType)
                outputFiles.append(file)
                outputMD5s.append(getMD5(inputFile))
            else:
                print("ERROR: Could not process audio input file: " + file + "." + fileType, flush=True)

# Clear out any extranious files from the output folder (left over from previous runs / changes).
for outputItem in os.listdir(args["output"]):
    if not outputItem.endswith(".mp3") or not outputItem[:-4] in outputFiles:
        if os.path.isdir(args["output"] + os.sep + outputItem):
            shutil.rmtree(args["output"] + os.sep + outputItem)
        else:
            os.remove(args["output"] + os.sep + outputItem)

# Step through each output file, assigning information about each one so the front end can see it.
for pl in range(0, len(outputFiles)):
    file = outputFiles[pl]
    inputFile = inputFiles[pl]
    iconOutputFile = outputFolder + os.sep + file + ".png"
    
    iconInputFile = ""

    # Figure out the files' title - this is the file's filename without any leading numerals.
    fileTitle = file.strip()
    if re.match("^[0-9]+ *- *.*", fileTitle) != None:
        fileTitle = fileTitle.split("-", 1)[1].strip()
    
    # Figure out if the file has a matching image file to use as an icone...
    for fileType in docsToMarkdownLib.imageTypes:
        if os.path.exists(inputFolder + os.sep + file + "." + fileType):
            iconInputFile = file + "." + fileType
        elif os.path.exists(inputFolder + os.sep + fileTitle + "." + fileType):
            iconInputFile = fileTitle + "." + fileType
    
    # ...if not, see if there's an image included in the MP3 data we can use.
    if iconInputFile == "":
        print("Extracting any album art as icon from: " + inputFile, flush=True)
        systemPrint("ffmpeg -y -i \"" + inputFolder + os.sep + inputFile + "\" -an -vcodec copy \"" + iconOutputFile + "\"" + devnullString)
    else:
        print("Processing image file as icon: " + iconInputFile, flush=True)
        systemPrint("ffmpeg -y -i \"" + inputFolder + os.sep + iconInputFile + "\" \"" + iconOutputFile + "\"" + devnullString)

    fileDescription = ""
    audioFileData = eyed3.load(inputFolder + os.sep + inputFile)
    if (not audioFileData == None) and (not audioFileData.tag == None):
        if not audioFileData.tag.title == None:
            fileTitle = html.escape(audioFileData.tag.title)
        if len(audioFileData.tag.comments) > 0:
            fileDescription = audioFileData.tag.comments[0].text
    
    fileIcon = ""
    if os.path.exists(iconOutputFile):
        # If we have an icon file, make sure it's a square, thumbnailed image...
        iconImage = PIL.Image.open(iconOutputFile)
        iconWidth, iconHeight = iconImage.size
        cropLeft = 0
        cropRight = iconWidth
        cropTop = 0
        cropBottom = iconHeight
        if iconWidth > iconHeight:
            cropLeft = int((iconWidth - iconHeight) / 2)
            cropRight = iconWidth - cropLeft
        else:
            cropTop = int((iconHeight - iconWidth) / 2)
            cropBottom = iconHeight - cropTop
        croppedIcon = iconImage.crop((cropLeft, cropTop, cropRight, cropBottom))
        croppedIcon.thumbnail((1024,1024))
        croppedIcon.save(iconOutputFile)
        # ...and that we tell the front end we have it.
        fileIcon = file + ".png"
    
    # Fields: 0:Input file MD5 Hash, 1:Audio file name, 2:Title, 3:Description, 4:Icon File name, 5:Start, 6:End, 7:Volume, 8:Key
    # Append the row of CSV data for the front end.
    cueList.append([outputMD5s[pl], file + ".mp3", fileTitle, fileDescription, fileIcon, 0, 0, 0, ""])

# Write the index.html file for the zip-ed version.
indexHTML = docsToMarkdownLib.getFile("audioCuesIndex.html").replace("var resources = [];", str("var resources = " + str(cueList) + ";")).replace("<<TIMESTAMP>>",str(timestamp)).replace("<<DATETIMEFORMATTED>>",dateTimeFormatted).replace("\'", "\"")
docsToMarkdownLib.putFile(args["output"] + os.sep + "index.html", indexHTML.replace("/bootstrap/","bootstrap/").replace("/bootstrap-icons/","bootstrap-icons/").replace("/popper/","popper/"))

# Create the zip file.
print("STATUS: processAudioCues - creating zip file for local download...", flush=True)
shutil.copy(".." + os.sep + "assets" + os.sep + "silence.mp3", args["output"])
shutil.copytree(".." + os.sep + "assets" + os.sep + "popper", args["output"] + os.sep + "popper")
shutil.copytree(".." + os.sep + "assets" + os.sep + "bootstrap", args["output"] + os.sep + "bootstrap")
shutil.copytree(".." + os.sep + "assets" + os.sep + "bootstrap-icons", args["output"] + os.sep + "bootstrap-icons")
shutil.make_archive("audioCues", "zip", args["output"])
shutil.move("audioCues.zip", args["output"])
shutil.rmtree(args["output"] + os.sep + "popper")
shutil.rmtree(args["output"] + os.sep + "bootstrap")
shutil.rmtree(args["output"] + os.sep + "bootstrap-icons")

# Re-write index.html as the final version.
docsToMarkdownLib.putFile(args["output"] + os.sep + "index.html", indexHTML)
