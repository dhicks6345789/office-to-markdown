# A script to generate an audio cues page (a folder containing index.html and a set of normalised assets) from a folder of assets (audio clips).

# Standard libraries.
import os
import io
import re
import sys
import json
import shutil
import datetime

# The Pillow image-handling library.
import PIL

# The Pandas data-handling library.
import pandas

# The Requests library, for retriving web documents (images).
import requests

# A library to get favicons from websites. See:
# https://github.com/AlexMili/extract_favicon/
import extract_favicon

# Our own Docs To Markdown library.
import docsToMarkdownLib

# Our own library to handle interactions with rclone.
import rcloneLib



# Returns either the element of the row given by the index, or an empty string if that item doesn't exist.
# Also returns an empty string instead of a float value of "nan".
def itemOrBlank(theRow, theIndex):
    if theRow.shape[0] > theIndex:
        item = theRow.iloc[theIndex]
        if not str(item) == "nan":
            return item
    return ""

# Resizes a given PIL image to a standard (256 by 256) size and saves out to a filename given as a URL hash.
# There's several possible options to resize images - plain resize (with basic anti-aliasing) seems about best. Could add AI upscaling, but that seems slightly like overkill here.
def resizeAndSavePILImage(theImage, theURLHash):
    IMAGESIZE = 1024
    originalWidth, originalHeight = theImage.size
    resizedImage = PIL.ImageOps.contain(theImage, (IMAGESIZE, IMAGESIZE))
    resizedWidth, resizedHeight = resizedImage.size
    resizedX = 0
    if resizedWidth != IMAGESIZE:
        resizedX = int((IMAGESIZE - resizedWidth) / 2)
    resizedY = 0
    if resizedHeight != IMAGESIZE:
        resizedY = int((IMAGESIZE - resizedHeight) / 2)
    outputImage = PIL.Image.new('RGBA', (IMAGESIZE, IMAGESIZE), (255, 0, 0, 0))
    outputImage.paste(resizedImage, (resizedX, resizedY))
    outputImage.save(args["output"] + os.sep + theURLHash + ".png", "PNG")
    return theURLHash + ".png"

# Do a Javascript-style (>>>) unsigned right shift, treating the input number as if it is a 32-bit unsigned integer.
def unsigned_right_shift(theNum, theShift):
    # Apply mask to ensure the number is treated as unsigned, then perform the right shift.
    return (theNum & 0xFFFFFFFF) >> theShift

# Do a Javascript-style "imul" operation: multiply two numbers as if they are both 32-bit unsigned integers.
def imul(a, b):
    return (a*b) & 0xFFFFFFFF
    
# Generate a simple "cyrb53" hash from a given string. Non-cryptographic, we're just using
# this hash to name favicon images. See the original Javascript version: https://stackoverflow.com/a/52171480/20530257
# And the Python conversion: https://stackoverflow.com/a/79643222/20530257
def cyrb53(theStr, seed=0):
    h1 = 0xdeadbeef ^ seed
    h2 = 0x41c6ce57 ^ seed
    for i,ch in enumerate(theStr):
        h1 = imul(h1 ^ ord(ch), 2654435761)
        h2 = imul(h2 ^ ord(ch), 1597334677)
    h1  = imul(h1 ^ unsigned_right_shift(h1 , 16), 2246822507)
    h1 ^= imul(h2 ^ unsigned_right_shift(h2 , 13), 3266489909)
    h2  = imul(h2 ^ unsigned_right_shift(h2 , 16), 2246822507)
    h2 ^= imul(h1 ^ unsigned_right_shift(h1 , 13), 3266489909)
    return 4294967296 * (2097151 & h2) + (h1 & 0xFFFFFFFF)



# Get a timestamp of when we started.
dateTimeNow = datetime.datetime.now()
timestamp = int(round(dateTimeNow.timestamp()))
dateTimeFormatted = dateTimeNow.strftime("%d-%m-%Y, %H:%M:%S")

# Get any arguments given via the command line.
args = docsToMarkdownLib.processCommandLineArgs(defaultArgs={"processAudio":"true"}, requiredArgs=["input","output"])

print("STATUS: processStartScreen: " + args["input"] + " to " + args["output"], flush=True)
print("Timestamp: " + str(timestamp) + ", Date / Time: " + dateTimeFormatted, flush=True)

# Make sure the output folder exists.
os.makedirs(args["output"], exist_ok=True)

inputFolder = docsToMarkdownLib.normalisePath(args["input"])
print("Input folder: " + inputFolder, flush=True)

dataTuples = []
inputImages = {}
for inputItem in os.listdir(inputFolder):
    inputSplit = inputItem.rsplit(".", 1)
    inputTitle = inputSplit[0]
    inputFileType = ""
    if len(inputSplit) == 2:
        inputFileType = inputSplit[1].lower()
    inputItemPath = inputFolder + os.sep + inputItem
    if inputItem.endswith(".xls") or inputItem.endswith(".xlsx"):
        dataFrameMap = pandas.read_excel(inputItemPath, sheet_name=None)
        for dataFrameName in dataFrameMap:
            dataTuples.append((dataFrameName, dataFrameMap[dataFrameName]))
    elif inputItem.endswith(".csv"):
        dataTuples.append((frameTitle, pandas.read_csv(inputItemPath)))
    elif inputFileType in docsToMarkdownLib.imageTypes:
        inputImages[inputTitle.lower()] = [inputItemPath, inputFileType]

# Get a list of images from the output folder.
outputImages = {}
for outputImage in os.listdir(args["output"]):
    imageSplit = outputImage.lower().rsplit(".", 1)
    if len(imageSplit) > 1:
        if imageSplit[1] in docsToMarkdownLib.imageTypes:
            outputImages[imageSplit[0]] = imageSplit[1]

resources = []
validFiles = ["index.html"]
for dataTuple in dataTuples:
    resourceTable = [["URL", "Title", "Description", "Icon"]]
    for index, row in dataTuple[1].iterrows():
        URL = itemOrBlank(row, 0)
        title = itemOrBlank(row, 1)
        description = itemOrBlank(row, 2)
        icon = itemOrBlank(row, 3)
        if not icon == "":
            URLHash = str(cyrb53(URL)) + str(cyrb53(icon))
        elif not title == "":
            URLHash = str(cyrb53(URL)) + str(cyrb53(title))
        else:
            URLHash = str(cyrb53(URL)) + str(cyrb53(URL[::-1]))
        
        downloadIcon = True
        # To do: add date check (expire after one week?).
        if URLHash in outputImages.keys():
            icon = URLHash + "." + outputImages[URLHash]
            downloadIcon = False
        
        if downloadIcon:
            localIconFound = False
            if icon == "":
                if not title == "":
                    if title.lower() in inputImages:
                        localIconFound = True
                        print("Item " + title + " - found local icon image.", flush=True)
                        iconPath = inputImages[title.lower()][0]
                        iconType = inputImages[title.lower()][1]
                        if iconType in docsToMarkdownLib.bitmapTypes:
                            iconImage = PIL.Image.open(iconPath)
                            icon = resizeAndSavePILImage(iconImage, URLHash)
                        elif iconType in ["svg+xml"]:
                            icon = theURLHash + ".svg"
                            shutil.copyfile(iconPath, args["output"] + os.sep + icon)
                if not localIconFound:
                    print("Item " + title + " - trying to retreive / refresh favicon...", flush=True)
                    bestFavicon = None
                    # The "Extract Favicon" library is very useful, but seems to have a bug that sometimes results in a ValueError being thrown from somewhere inside its own dependancy
                    # of the Python PIL image library (seems to be an issue trying to retrive the sizes of some icon files). Therefore, we try a plain "get Favicon from site" operation,
                    # and if that fails (including if it throws an exception) we move on to the "download from DuckDuckGo / Google cache" option.
                    try:
                        bestFavicon = extract_favicon.get_best_favicon(URL,  strategy = ["content"])
                    except ValueError:
                        print("Favicon - ValueError raised.", flush=True)
                    # If there was a problem getting the Favicon, try a couple of different caches.
                    if bestFavicon == None:
                        bestFavicon = extract_favicon.get_best_favicon(URL, strategy = ["duckduckgo", "google"])
                    # Now, we hopefully have a downloaded Favicon.
                    if bestFavicon:
                        icon = resizeAndSavePILImage(bestFavicon.image, URLHash)
                    else:
                        print("No Favicon found for this URL.", flush=True)
            else:
                print("Item " + title + " - trying to retreive / refresh icon " + icon + "...", flush=True)
                URLType, docReference = rcloneLib.URLToTypeAndReference(icon)
                if URLType == "googleFile":
                    #print("Icon is a Google Drive file - downloading with rclone...")
                    downloadedFilename = rcloneLib.downloadGoogleFile(docReference, args["output"])
                    if downloadedFilename.lower().endswith(".svg"):
                        os.rename(args["output"] + os.sep + downloadedFilename, args["output"] + os.sep + URLHash + ".svg")
                    else:
                        iconImage = PIL.Image.open(args["output"] + os.sep + downloadedFilename)
                        icon = resizeAndSavePILImage(iconImage, URLHash)
                else:
                    iconResponse = requests.get(icon)
                    iconType = iconResponse.headers["Content-Type"].split("/")[1].lower()
                    if iconType in docsToMarkdownLib.bitmapTypes:
                        iconImage = PIL.Image.open(io.BytesIO(iconResponse.content))
                        icon = resizeAndSavePILImage(iconImage, URLHash)
                    elif iconType in ["svg+xml"]:
                        iconOut = open(args["output"] + os.sep + URLHash + ".svg", "wb")
                        iconOut.write(iconResponse.content)
                        iconOut.close()
                        icon = URLHash + ".svg"
        resourceTable.append([URL, title, description, icon])
        if not icon == "":
            validFiles.append(icon)
    resource = (dataTuple[0], resourceTable)
    resources.append(resource)

# Write the index.html file.
indexHTML = docsToMarkdownLib.getFile("/etc/docs-to-markdown/startScreen/startScreenIndex.html")
indexHTML = indexHTML.replace("var resources = [];", "var resources = " + json.dumps(resources) + ";")
indexHTML = indexHTML.replace("<<TIMESTAMP>>", str(timestamp))
indexHTML = indexHTML.replace("<<DATETIMEFORMATTED>>", dateTimeFormatted)
indexHTML = indexHTML.replace("\'", "\"")
docsToMarkdownLib.putFile(args["output"] + os.sep + "index.html", indexHTML)

# Clear out any unwanted files from the output folder.
for item in os.listdir(args["output"]):
    if not item in validFiles:
        print("Removing unwanted output file: " + item, flush=True)
        os.remove(args["output"] + os.sep + item)
