# A script to generate a "start screen" web page (a folder containing index.html and a set of normalised assets) from a folder of resources.
# A spreadsheet (Excel or CSV) file in the input folder defines the resources to display, along with any optional local icon images.

# Standard libraries.
import os
import io
import sys
import json
import shutil
import pathlib
import argparse

# The Pillow image-handling library.
import PIL.Image
from PIL import ImageOps

# The Pandas data-handling library.
import pandas

# The Requests library, for retrieving web documents (images).
import requests

# A library to get favicons from websites. See:
# https://github.com/AlexMili/extract_favicon/
import extract_favicon

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description=(
    "Process the given folder and generate a start-screen web page (a folder containing index.html and a set of normalised assets). "
    "A spreadsheet (Excel or CSV) file in the folder defines the resources to display; each resource is a URL, plus an optional title, "
    "description and icon image. Where no icon is provided, the site's favicon will be downloaded, or any local image with a matching title "
    "will be used instead."
))).parse_args())

# Pick up any additional arguments from a config file if present.
args.update(officeToMarkdownLib.processArgsFile(args["input"]))

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as a simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself (or associated additional resource or config file) has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdatedFiles = officeToMarkdownLib.generateScriptUpdatedFilesList(args["input"], args["verbose"])
scriptUpdatedFiles.append(__file__)
scriptUpdatedFiles.append(__file__.replace("processStartScreen.py", "startScreenIndex.html"))
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(previousInputFileTimestamps, scriptUpdatedFiles, args["verbose"])

# A message for the user.
officeToMarkdownLib.printIfVerbose(args["verbose"], "ProcessStartScreen - folder: " + str(args["input"]))

outputPath = args["output"]
if outputPath.name == "startScreen":
    outputPath = outputPath.parent
outputPath = pathlib.Path("static") / outputPath

# Make sure the output folder exists.
outputDir = args["outputRoot"] / outputPath
outputDir.mkdir(parents=True, exist_ok=True)

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
    resizedImage = ImageOps.contain(theImage, (IMAGESIZE, IMAGESIZE))
    resizedWidth, resizedHeight = resizedImage.size
    resizedX = 0
    if resizedWidth != IMAGESIZE:
        resizedX = int((IMAGESIZE - resizedWidth) / 2)
    resizedY = 0
    if resizedHeight != IMAGESIZE:
        resizedY = int((IMAGESIZE - resizedHeight) / 2)
    outputImage = PIL.Image.new('RGBA', (IMAGESIZE, IMAGESIZE), (255, 0, 0, 0))
    outputImage.paste(resizedImage, (resizedX, resizedY))
    outputImagePath = outputDir / pathlib.Path(theURLHash + ".png")
    outputImage.save(outputImagePath, "PNG")
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

# A list of all the output files generated by this script, reported back to the calling script.
outputFilesList = []
inputFiles = []

# Read the input folder: any spreadsheet files (Excel / CSV) become the resource tables, any bitmap / SVG images become a bank of local icons.
dataTuples = []
inputImages = {}
for inputItem in args["input"].iterdir():
    if not inputItem.is_file():
        continue
    inputItemPath = str(inputItem)
    inputItemStat = inputItem.stat()
    inputSplit = inputItem.name.rsplit(".", 1)
    inputTitle = inputSplit[0]
    inputFileType = ""
    if len(inputSplit) == 2:
        inputFileType = inputSplit[1].lower()
    inputFiles.append(inputItemPath)
    if inputFileType in ["xls", "xlsx"]:
        try:
            dataFrameMap = pandas.read_excel(inputItemPath, sheet_name=None)
        except Exception as theError:
            officeToMarkdownLib.printIfVerbose(args["verbose"], "Unable to read spreadsheet " + inputItemPath + " - " + str(theError))
        else:
            for dataFrameName in dataFrameMap:
                dataTuples.append((dataFrameName, dataFrameMap[dataFrameName]))
    elif inputFileType == "csv":
        try:
            dataTuples.append((inputTitle, pandas.read_csv(inputItemPath)))
        except Exception as theError:
            officeToMarkdownLib.printIfVerbose(args["verbose"], "Unable to read CSV " + inputItemPath + " - " + str(theError))
    elif ("." + inputFileType) in officeToMarkdownLib.imageSuffixes:
        inputImages[inputTitle.lower()] = [inputItemPath, inputFileType]

# Get a list of images already present in the output folder.
outputImages = {}
for outputImage in outputDir.iterdir():
    if outputImage.is_file():
        imageSplit = outputImage.name.lower().rsplit(".", 1)
        if len(imageSplit) > 1:
            if ("." + imageSplit[1]) in officeToMarkdownLib.imageSuffixes:
                outputImages[imageSplit[0]] = imageSplit[1]

# Build the resources list, one entry per row of each spreadsheet, downloading any required icon images.
resources = []
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
        # If we've already downloaded this icon, just re-use it.
        if URLHash in outputImages.keys():
            icon = URLHash + "." + outputImages[URLHash]
            downloadIcon = False

        if downloadIcon:
            if icon == "":
                localIconFound = False
                if not title == "" and title.lower() in inputImages:
                    localIconFound = True
                    officeToMarkdownLib.printIfVerbose(args["verbose"], "Item " + title + " - found local icon image.")
                    iconPath = inputImages[title.lower()][0]
                    iconType = inputImages[title.lower()][1]
                    if ("." + iconType) in officeToMarkdownLib.bitmapSuffixes:
                        iconImage = PIL.Image.open(iconPath)
                        icon = resizeAndSavePILImage(iconImage, URLHash)
                    elif iconType in ["svg+xml", "svg"]:
                        icon = URLHash + ".svg"
                        shutil.copyfile(iconPath, outputDir / pathlib.Path(icon))
                if not localIconFound:
                    officeToMarkdownLib.printIfVerbose(args["verbose"], "Item " + title + " - trying to retrieve / refresh favicon...")
                    bestFavicon = None
                    # The "Extract Favicon" library is very useful, but seems to have a bug that sometimes results in a ValueError being thrown from somewhere inside its own dependency
                    # of the Python PIL image library (seems to be an issue trying to retrieve the sizes of some icon files). Therefore, we try a plain "get Favicon from site" operation,
                    # and if that fails (including if it throws an exception) we move on to the "download from DuckDuckGo / Google cache" option.
                    try:
                        bestFavicon = extract_favicon.get_best_favicon(URL, strategy=["content"])
                    except ValueError:
                        officeToMarkdownLib.printIfVerbose(args["verbose"], "Favicon - ValueError raised.")
                    # If there was a problem getting the Favicon, try a couple of different caches.
                    if bestFavicon == None:
                        bestFavicon = extract_favicon.get_best_favicon(URL, strategy=["duckduckgo", "google"])
                    # Now, we hopefully have a downloaded Favicon.
                    if bestFavicon:
                        icon = resizeAndSavePILImage(bestFavicon.image, URLHash)
                    else:
                        officeToMarkdownLib.printIfVerbose(args["verbose"], "No Favicon found for this URL.")
            else:
                iconIsLocal = not (icon.startswith("http://") or icon.startswith("https://"))
                if iconIsLocal:
                    # A local icon may be a plain path or a "file://" URI (e.g. "file://desktop.png"). Relative paths are
                    # resolved against the input folder (the folder that holds the spreadsheet).
                    iconLocalPath = icon
                    if iconLocalPath.startswith("file://"):
                        iconLocalPath = iconLocalPath[len("file://"):]
                    iconPath = pathlib.Path(iconLocalPath)
                    if not iconPath.is_absolute():
                        iconPath = args["input"] / iconPath
                    officeToMarkdownLib.printIfVerbose(args["verbose"], "Item " + title + " - using local icon file " + str(iconPath) + "...")
                    iconSplit = iconPath.name.rsplit(".", 1)
                    iconType = ""
                    if len(iconSplit) == 2:
                        iconType = iconSplit[1].lower()
                    if ("." + iconType) in officeToMarkdownLib.bitmapSuffixes:
                        iconImage = PIL.Image.open(iconPath)
                        icon = resizeAndSavePILImage(iconImage, URLHash)
                    elif iconType in ["svg", "svg+xml"]:
                        icon = URLHash + ".svg"
                        shutil.copyfile(iconPath, outputDir / pathlib.Path(icon))
                    else:
                        icon = ""
                        officeToMarkdownLib.printIfVerbose(args["verbose"], "Unsupported local icon file type: " + iconPath.name)
                else:
                    officeToMarkdownLib.printIfVerbose(args["verbose"], "Item " + title + " - trying to retrieve / refresh icon " + icon + "...")
                    iconResponse = requests.get(icon)
                    iconType = iconResponse.headers["Content-Type"].split("/")[1].lower()
                    if ("." + iconType) in officeToMarkdownLib.bitmapSuffixes:
                        iconImage = PIL.Image.open(io.BytesIO(iconResponse.content))
                        icon = resizeAndSavePILImage(iconImage, URLHash)
                    elif iconType in ["svg+xml"]:
                        iconOutPath = outputDir / pathlib.Path(URLHash + ".svg")
                        iconOut = open(iconOutPath, "wb")
                        iconOut.write(iconResponse.content)
                        iconOut.close()
                        icon = URLHash + ".svg"
        resourceTable.append([URL, title, description, icon])
        if not icon == "":
            outputFilesList.append(str(outputDir / pathlib.Path(icon)))
    resources.append((dataTuple[0], resourceTable))

# Work out if any input file (spreadsheet or icon image) has been updated since the last run, in which case we need to re-generate the index.html.
inputUpdated = False
for inputFile in inputFiles:
    inputFileTimestamp = str(pathlib.Path(inputFile).stat().st_mtime)
    if (not inputFile in previousInputFileTimestamps) or (not inputFileTimestamp == previousInputFileTimestamps[inputFile]):
        inputUpdated = True

# Write the index.html file, based on the single-page start-screen viewer template, embedding the resources list.
indexFileInputPath = pathlib.Path(args["scriptRoot"]) / pathlib.Path("startScreen/startScreenIndex.html")
indexFileInputPathStr = str(indexFileInputPath)
indexFileInputPathStat = indexFileInputPath.stat()
indexFileOutputPath = outputDir / pathlib.Path("index.html")
if scriptUpdated or inputUpdated or (not indexFileOutputPath.is_file()):
    indexHTML = officeToMarkdownLib.getFile(indexFileInputPath)
    indexHTML = indexHTML.replace("var resources = [];", "var resources = " + json.dumps(resources) + ";")
    officeToMarkdownLib.putFile(indexFileOutputPath, indexHTML)
outputFilesList.append(str(indexFileOutputPath))

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
filesProcessed = {}
for inputFile in inputFiles:
    filesProcessed[inputFile] = (outputFilesList, str(pathlib.Path(inputFile).stat().st_mtime))
filesProcessed[indexFileInputPathStr] = (outputFilesList, str(indexFileInputPathStat.st_mtime))
officeToMarkdownLib.printFilesProcessed(filesProcessed)
