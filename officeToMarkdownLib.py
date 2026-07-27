# Standard libraries.
import os
import io
import re
import sys
import yaml
import base64
import shutil
import pathlib
import subprocess
import concurrent.futures

# The Pillow image-handling library.
import PIL.Image

# The ffmpeg video-handling library.
import ffmpeg

# The Slugify library for making URL-safe strings.
import slugify

# Mammoth converts .DOCX file to HTML...
import mammoth
# ...and Markdownify can convert HTML to Markdown.
import markdownify

# We use the Pandas library, which in turn uses the XLRD library, to read Excel data.
import pandas



# Pandoc escapes Markdown control characters embedded in Word documents, but we want to let people embed chunks of Markdown in
# a document if they want, so we un-escape the Markdown back again - we simply use Python's string.replace to replace characters
# in strings.
markdownReplace = {"\\[":"[","\\]":"]","\\!":"!","\\`\\`\\`":"```"}

# An array of "image file" types.
bitmapSuffixes = [".jpg", ".jpeg", ".png", ".ico"]
imageSuffixes =  bitmapSuffixes + [".svg"]

# An array of "video file" types.
videoSuffixes = [".mp4"]

# An array of "url file" types.
urlSuffixes = [".url", ".txt"]

# An array of "audio file" types.
audioSuffixes = [".mp3", ".ogg", ".wav"]

# Files / folders to exclude from directory listings.
fileIgnores = [".git", ".gitignore", "__pycache__", ".venv", "assets"]

# Valid config file filenames.
configFileNames = ["config.yaml", "config.xlsx", "config.csv"]

# A utility function to return the contents of the given file.
def getFile(theFilename):
    infile = open(theFilename)
    result = infile.read()
    infile.close()
    return(result)

# A utility function to return the contents of the given binary file.
def getBinaryFile(theFilename):
    infile = open(theFilename, "rb")
    result = infile.read()
    infile.close()
    return(result)
    
# A utility function to write the contents of the given string to the given file.
def putFile(theFilename, theContent):
    filePath = pathlib.Path(str(theFilename))
    filePath.parent.mkdir(parents=True, exist_ok=True)
    outfile = open(filePath, "wt", encoding="utf-8")
    outfile.write(theContent)
    outfile.close()

# Parse command-line input arguments. Since we have a set of scripts that take the same baseline arguments we have a central library function that adds our standard
# arguments to an argparse.ArgumentParser object.
def setArgsForGeneral(theParser):
    theParser.add_argument("--input", type=pathlib.Path, help="Input folder. Absolute path.")
    theParser.add_argument("--output", type=pathlib.Path, help="Output folder.")
    theParser.add_argument("--scriptRoot", type=pathlib.Path, default=str(pathlib.Path.cwd()), help="The root of the script folder. Defaults to the current working directory.")
    theParser.add_argument("--dataRoot", type=pathlib.Path, default=str(pathlib.Path.cwd()), help="The root of the script folder. Defaults to the current working directory.")
    theParser.add_argument("--verbose", action="store_true", help="Turn on verbose output.")
    return theParser

# Add arguments to an argparse.ArgumentParser object to handle the options for a Python sub-script.
def setArgsForSubScript(theParser):
    theParser = setArgsForGeneral(theParser)
    #theParser.add_argument("--scriptTimestamp", help="The previous last-modified timestamp value (as a floating point number) for this script.")
    theParser.add_argument("--outputRoot", help="The root output folder, tpyically a 'Hugo' folder.")
    return theParser

# Read the list of input files, along with last-modified timestamps, from stdin. Returns as a dict of filename:timestamp values, with all values as strings.
def readInputFilesAndTimestamps():
    result = {}
    for line in sys.stdin:
        lineSplit = line.strip().split(",")
        result[lineSplit[0]] = lineSplit[1]
    return result

def generateScriptUpdatedFilesList(inputPath, verbose):
    scriptUpdatedFiles = []
    for item in configFileNames:
        itemPath = inputPath / pathlib.Path(item)
        if itemPath.is_file():
            ifVerbose(verbose, postPadWithSpaces(pathlib.Path(sys.argv[0]).stem, 16) + " -  config: " + str(itemPath))
            scriptUpdatedFiles.append(str(itemPath))
    return scriptUpdatedFiles

# Returns True if the current executing script has been updated, when compared to the given timestamp value.
def checkIfScriptUpdated(timestamps, filenames, verbose=False):
    result = False
    for item in filenames:
        itemPath = pathlib.Path(item)
        if (itemPath.exists()) and ((not item in timestamps) or (not str(itemPath.stat().st_mtime) == timestamps[item])):
            ifVerbose(verbose, "script           - updated: " + item)
            result = True
    return result

def prePadWithSpaces(theString, theLength):
    result = ""
    for pl in range(0, theLength - len(theString)):
        result = result + " "
    return result + theString

def postPadWithSpaces(theString, theLength):
    result = theString
    while len(result) < theLength:
        result = result + " "
    return result

def printFilesProcessed(theFilesProcessed):
    # Report the input filenames, with current update timestamp, back to the calling script.
    for fileProcessed in theFilesProcessed:
        print(fileProcessed + "," + theFilesProcessed[fileProcessed][1], flush=True, file=sys.stdout)
    print("---", flush=True, file=sys.stdout)
    # Report the output filenames back to the calling script.
    for fileProcessed in theFilesProcessed:
        if isinstance(theFilesProcessed[fileProcessed][0], str):
            print(theFilesProcessed[fileProcessed][0], flush=True, file=sys.stdout)
        else:
            for item in theFilesProcessed[fileProcessed][0]:
                print(item, flush=True, file=sys.stdout)

def checkModDatesMatch(theInputItem, theOutputItem):
    if os.path.isfile(theOutputItem):
        inputItemDetails = os.stat(theInputItem)
        outputItemDetails = os.stat(theOutputItem)
        if inputItemDetails.st_mtime == outputItemDetails.st_mtime:
            return True
    return False

def makeModDatesMatch(theInputItem, theOutputItem):
    inputItemDetails = os.stat(str(theInputItem))
    os.utime(str(theOutputItem), (inputItemDetails.st_atime, inputItemDetails.st_mtime))

# Given an integer and a length, returns the int converted to a string, with the string length made up to the given
# length with "0"s appended to the front of the string as needed.
def padInt(theInt, theLength):
    result = str(theInt)
    while len(result) < theLength:
        result = "0" + result
    return result

# Given a string, if the first word (defined by space in the string) of the string is purely numeric, returns the string with that word removed.
# Basically, given a string like "0001 One Two Three.doc", returns "One Two Three.doc". If no spaces are found, just returns the input.
def removeNumericWord(theString):
    stringSplit = theString.strip().split(" ", 1)
    if stringSplit[0].isnumeric() and len(stringSplit) == 2:
        return stringSplit[1]
    return stringSplit[0]
    
# Given a dict, returns a YAML string, e.g.:
# ---
# variableName: value
# ---
def frontMatterToString(theFrontMatter):
    if theFrontMatter == {}:
        return ""
    result = "---\n"
    for frontMatterField in theFrontMatter.keys():
        result = result + frontMatterField + ": " + theFrontMatter[frontMatterField] + "\n"
    return(result + "---\n")

# Takes a file path string pointing to a document file (.DOC, .DOCX, .TXT, etc) file, loads that file and coverts the contents to a Markdown string using Pandoc.
# Returns a tuple of a string of the converted data and a dict of any front matter variables specified in the input file.
# Note: previously, a bug prevented Pandoc correctly parsing DOCX files produced by Word Online. As of around Monday, 4th March 2019, Pandoc 2.7 now seems to work.
# The Debian 11 (Bullseye) Pandoc package version is 2.9, previous versions are 2.5 or earlier, so you either need to make sure Debian is up-to-date or install
# Pandoc via the .deb file provided on their website.
#def docToMarkdown(inputFile, baseURL="", markdownType="gfm", validFrontMatterFields=[]):
#    markdown = ""
#    frontMatter = {}
#
#    parsingFrontMatter = True
#    blankLineCount = 0
#    pandocProcess = subprocess.Popen("pandoc --wrap=none -s \"" + str(inputFile) + "\" -t " + markdownType + " -o -", shell=True, stdout=subprocess.PIPE)
#    for markdownLine in pandocProcess.communicate()[0].decode("utf-8").split("\n"):
#        markdownLine = markdownLine.strip()
#        # Un-escape Markdown control characters embedded in Word documents.
#        for markdownReplaceKey in markdownReplace.keys():
#            markdownLine = markdownLine.replace(markdownReplaceKey, markdownReplace[markdownReplaceKey])
#        if parsingFrontMatter:
#            if markdownLine == "":
#                blankLineCount = blankLineCount + 1
#            else:
#                if blankLineCount < 2:
#                    parsingFrontMatter = False
#                    if ":" in markdownLine:
#                        markdownSplit = markdownLine.split(":", 1)
#                        frontMatterName = markdownSplit[0].strip()
#                        if not " " in frontMatterName:
#                            parsingFrontMatter = True
#                            if (frontMatterName in validFrontMatterFields) or (validFrontMatterFields == []):
#                                frontMatter[markdownSplit[0].strip()] = markdownSplit[1].strip()
#                    else:
#                        markdown = markdown + markdownLine.replace(baseURL, "") + "\n"
#                blankLineCount = 0
#        else:
#            markdown = markdown + markdownLine.replace(baseURL, "") + "\n"
#    return(markdown, frontMatter)
    
def docToMarkdown(inputFile, baseURL="", markdownType="gfm", validFrontMatterFields=[]):
    frontMatter = {}
    
    inputDOCXFile = open(inputFile, "rb")
    result = mammoth.convert_to_html(inputDOCXFile)
    inputDOCXFile.close()
    html = result.value
    return(markdownify.markdownify(html), frontMatter)
        
# Takes an input file and coverts it to Markdown, writing that Markdown to the given output file.
def docToMarkdownFile(inputFile, outputFile, baseURL="", markdownType="gfm", validFrontMatterFields=["title"]):
    outputMarkdown, outputFrontmatter = docToMarkdown(inputFile, baseURL=baseURL, markdownType=markdownType, validFrontMatterFields=validFrontMatterFields)
    putFile(outputFile, frontMatterToString(outputFrontmatter) + outputMarkdown)

# Reads a CSV or Excel file, returns the contents of that file as an associative array, with the first column as the key and the second column as the data. If more than two columns are present, each data item will be an array.
def readDataFile(theFilePath):
    result = {}
    if theFilePath.is_file():
        # Figure out what format the file is in and use the appropriate loader.
        fileSuffix = theFilePath.suffix.lower()
        if fileSuffix == ".csv":
            pandasData = pandas.read_csv(theFilePath, header=None)
        elif fileSuffix in [".xlsx", ".xls"]:
            pandasData = pandas.read_excel(theFilePath, header=None)
        returnScalars = False
        if pandasData.shape[1] == 2:
            returnScalars = True
        for index, row in pandasData.iterrows():
            if returnScalars:
                result[row[0]] = row[1]
            else:
                result[row[0]] = []
                for px in range(1, pandasData.shape[1]):
                    result[row[0]].append(row[px])
                #result[row[0]] = row.values.flatten().tolist()[1:]
    return result
    
# Reads a CSV file containing filenames along with their last-modified timetsamps.
def readChangesFile(theFilename):
    result = {}
    if os.path.isfile(theFilename):
        for line in getFile(theFilename).split("\n"):
            if not line.strip() == "":
                lineSplit = line.strip().split(",")
                result[lineSplit[0]] = lineSplit[1]
    return result
    
# Writes the data contained in a dict to a CSV or Excel file.
def writeDataFile(theFilename, theData):
    pandasData = []
    for item in theData:
            pandasData.append([item, theData[item]])
    outputDataframe = pandas.DataFrame(pandasData)
    
    # Figure out what format the file is in and use the appropriate writer.
    if theFilename.endswith(".csv"):
        outputDataframe.to_csv(theFilename, float_format='%.7f', index=False, header=False)
    elif theFilename.endswith(".xlsx") or theFilename.endswith(".xls"):
        outputDataframe.to_excel(theFilename, index=False, header=False)

# Writes the data contained in a dict holdings filenames with last-modified timesstamps to a CSV file.
def writeChangesFile(theFilename, theData):
    outputString = ""
    for item in theData:
        outputString = outputString + item + "," + theData[item] + "\n"
    putFile(theFilename, outputString[:-1])

## Parse arguments from a config file. Accepts CSV, Excel and YAML formats.
#def processArgsFile(theFilename, defaultArgs={}, requiredArgs=[], optionalArgs=[], optionalArgLists=[]):
#    args = {}
#    argsData = {}
#    # Figure out what format the file is in and use the appropriate loader.
#    if theFilename.endswith(".csv"):
#        argsData = pandas.read_csv(theFilename, header=0).to_dict(index=False)
#    elif theFilename.endswith(".xlsx") or theFilename.endswith(".xls"):
#        argsData = pandas.read_excel(theFilename, header=0).to_dict(index=False)
#    elif theFilename.endswith(".yaml"):
#        argsData = yaml.safe_load(getFile(theFilename))
#    
#    # Process any read arguments - check each key/value pair is a valid argument name.
#    for argName in argsData.keys():
#        argName = argName.strip()
#        if argName in requiredArgs + optionalArgs:
#            if not argName in args:
#                args[argName] = str(argsData[argName])
#                
#    # If we have any default argument values defined, and those arguments
#    # aren't already present, add the default values in to the result.
#    for argName in defaultArgs.keys():
#        if not argName in args.keys():
#            args[argName] = defaultArgs[argName]
#
#    # If any required arguments are missing, stop.
#    for argName in requiredArgs:
#        if not argName in args:
#            print("ERROR: Required argument not present: " + argName, flush=True)
#            quit
#    return args



# Parse arguments from a config file. Accepts CSV, Excel and YAML formats.
def processArgsFile(theInputPath, defaultArgs={}):
    args = {}
    argsData = {}
    
    inputPath = None
    if theInputPath.is_file():
        inputPath = theInputPath
    if theInputPath.is_dir():
        for item in theInputPath.iterdir():
            if item.is_file() and item.name in configFileNames:
                inputPath = item
                
    if not inputPath == None:
        # Figure out what format the file is in and use the appropriate loader.
        if inputPath.suffix.lower() == ".csv":
            argsData = pandas.read_csv(item, header=0).to_dict(index=False)
        elif inputPath.suffix.lower() in [".xlsx", ".xls"]:
            argsData = pandas.read_excel(item, header=0).to_dict(index=False)
        if inputPath.suffix.lower() == ".yaml":
            argsData = yaml.safe_load(getFile(item))
        
    # Process any read arguments - check each key/value pair is a valid argument name.
    for argName in argsData.keys():
        argName = argName.strip()
        args[argName] = str(argsData[argName])

    # If we have any default argument values defined, and those arguments
    # aren't already present, add the default values in to the result.
    for argName in defaultArgs.keys():
        if not argName in args.keys():
            args[argName] = defaultArgs[argName]
    return args



# Returns a dict of filePath:last-updated values for the given path. Both the file path value and the last-updated value are stored as strings. Sub-folders are
# recursed into, the last-updated value for a folder will simply be the most recent value of all the files and sub-folders found in that folder.
def getFolderChangeDetails(thePath):
    changes = {}
    for item in thePath.iterdir():
        if not item.name in fileIgnores:
            if item.is_dir():
                changes.update(getFolderChangeDetails(item))
            else:
                changes[str(item)] = str(item.stat().st_mtime)
    if len(changes) > 0:
        changes[str(thePath)] = sorted(changes.values())[0]
    return changes

# Given two ints, returns those two ints divided by their highest common divisor, or simply
# returns the two same ints if there is no common divisor. Checks from the given range downwards.
def reduceInts(theRange, leftInt, rightInt):
    for pl in range(theRange, 2, -1):
        leftDivide = float(leftInt) / float(pl)
        rightDivide = float(rightInt) / float(pl)
        if leftDivide == float(int(leftDivide)) and rightDivide == float(int(rightDivide)):
            return (int(leftDivide), int(rightDivide))
    return (leftInt, rightInt)



# Given an input video file, produce an output MP4 version thumbnailed to the given width and height. If the original video is of a different aspect ratio
# the sides will be padded with blank space accordingly to fit the given output dimensions.
def thumbnailVideo(theInputVideo, theOutputVideo, theBlockWidth, theBlockHeight):
    # Figure out the video's dimensions.
    probe = ffmpeg.probe(theInputVideo)
    videoStream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    if videoStream:
        videoWidth = int(videoStream['width'])
        videoHeight = int(videoStream['height'])
        
        # Scale the dimensions given as the output to match the input video.
        width, height = getRatioedDimensions(videoWidth, videoHeight, theBlockWidth, theBlockHeight)
        
        # Figure out the ratio of width to height of the input video clip...
        pictureRatio = float(videoWidth) / float(videoHeight)
        # ...and of the output video.
        outputRatio = float(width) / float(height)
        
        resultWidth = videoWidth
        scaledWidth = resultWidth
        resultHeight = videoHeight
        scaledHeight = resultHeight
        pasteX = 0
        pasteY = 0
        if pictureRatio < outputRatio:
            padHeightRatio = 1 + (outputRatio - pictureRatio)
            resultHeight = int(videoHeight / padHeightRatio)
            scaledWidth = int(videoWidth / padHeightRatio)
            pasteX = int((resultWidth - scaledWidth) / 2)
        elif pictureRatio > outputRatio:
            padWidthRatio = 1 + (pictureRatio - outputRatio)
            resultWidth = int(videoWidth / padWidthRatio)
            scaledHeight = int(videoHeight / padWidthRatio)
            pasteX = int((resultHeight - scaledHeight) / 2)
        
        if (scaledWidth % 2) == 1:
            scaledWidth = scaledWidth - 1
        if (scaledHeight % 2) == 1:
            scaledHeight = scaledHeight - 1
    
        if resultWidth < videoWidth:
            resultWidth = videoWidth
            scaledWidth = videoWidth
        if resultHeight < videoHeight:
            resultHeight = videoHeight
            scaledHeight = videoHeight

        #print("Video width,height: " + str(videoWidth) + "," + str(videoHeight), flush=True, file=sys.stderr)
        #print("Block width,height: " + str(theBlockWidth) + "," + str(theBlockHeight), flush=True, file=sys.stderr)
        #print("Scaled width,height: " + str(scaledWidth) + "," + str(scaledHeight), flush=True, file=sys.stderr)
        
        # Use ffmpeg to do the video conversion.
        (
            ffmpeg
            .input(str(theInputVideo))
            .filter("scale", scaledWidth, scaledHeight)
            .filter("pad", resultWidth, resultHeight, pasteX, pasteY, color="#FFFFFF@1")
            .filter("format", "rgb24")
            .output(
                str(theOutputVideo),
                vcodec="libx264",
                crf=18,
                loglevel="error",
                hide_banner=None
            )
            .overwrite_output()
            .run(capture_stderr=True)
        )

# Produce a thumbnail of an image. Differs from PIL.thumbnail() in that thumbnails are returned in a new image padded to match the aspect ratio of
# the given block width and height.
def thumbnailImage(theImage, theBlockWidth, theBlockHeight):
    imageWidth, imageHeight = theImage.size
    imageRatio = float(imageWidth) / float(imageHeight)
    
    blockWidth, blockHeight = reduceInts(12, theBlockWidth, theBlockHeight)
    blockRatio = float(blockWidth) / float(blockHeight)
    
    resultWidth = imageWidth
    resultHeight = imageHeight
    if imageRatio < blockRatio:
        padWidthRatio = 1 + (blockRatio - imageRatio)
        resultWidth = int(imageWidth * padWidthRatio)
    elif imageRatio > blockRatio:
        padHeightRatio = 1 + (imageRatio - blockRatio)
        resultHeight = int(imageHeight * padHeightRatio)
        
    result = PIL.Image.new(mode="RGB", size=(resultWidth, resultHeight), color="WHITE")
    pasteX = 0
    if not resultWidth == imageWidth:
        pasteX = int((resultWidth-imageWidth)/2)
    pasteY = 0
    if not resultHeight == imageHeight:
        pasteY = int((resultHeight-imageHeight)/2)
    result.paste(theImage, (pasteX, pasteY))
    
    return result

def getRatioedDimensions(objectWidth, objectHeight, ratioWidth, ratioHeight):
    if int(ratioWidth) > objectWidth:
        width = int(ratioWidth)
        height = int((float(ratioWidth) / float(objectWidth)) * float(objectHeight))
    else:
        width = int(objectWidth)
        height = int((float(objectWidth) / float(ratioWidth)) * float(ratioHeight))
    return width, height

def embedBitmapInSVG(theBitmap, theWidth, theHeight):
    bitmapObject = PIL.Image.open(theBitmap)
    width, height = getRatioedDimensions(bitmapObject.width, bitmapObject.height, theWidth, theHeight)
    print("Embedding bitmap in SVG: " + theBitmap + ", Width: " + str(width) + " Height: " + str(height))
    
    bitmapObject = thumbnailImage(bitmapObject, width, height)
    bitmapData = io.BytesIO()
    bitmapObject.save(bitmapData, format="PNG")
    
    result = "<svg version=\"1.1\" viewBox=\"0 0 " + str(width) + " " + str(height) + "\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">\n"
    result = result + "    <image width=\"" + str(width) + "\" height=\"" + str(height) + "\" preserveAspectRatio=\"none\" xlink:href=\"data:image/png;base64," + base64.b64encode(bitmapData.getvalue()).decode("utf-8") + "\"/>\n"
    result = result + "</svg>"
    return result

def addToWriteLog(theFilename, theLogLocation="/tmp/docsToMarkdownWriteLog.txt"):
    with open(theLogLocation, "a", encoding="utf-8") as file:
        file.write(theFilename + "\n")

def checkTimestampsMatch(theTimestamp, thePath):
    if str(thePath.stat().st_mtime) == str(theTimestamp):
        return True
    return False

def filePathSlugify(thePath):
    print("filePathSlugify:")
    print(thePath.with_suffix(""), flush=True, file=sys.stderr)
    if thePath.is_file():
        return pathlib.Path(slugify.slugify(str(thePath.with_suffix(""))) + thePath.suffix)
    return pathlib.Path(slugify.slugify(str(thePath)))

def ifVerbose(theVerbose, theOutput):
    if type(theVerbose).__name__ == "str":
        if theVerbose.lower() == "true":
            print(theOutput, flush=True, file=sys.stderr)
    elif theVerbose == True:
        print(theOutput, flush=True, file=sys.stderr)

# Looks through the contents of the input folder, applying a transform script to each file or folder found.
# A cache of file paths with checksum details is maintained, this is used to avoid processing a file if it (and the associated processing script) hasn't been changed since the last run.
# Folders are recursed into. Some matches might match whole sub-folders, in which case that sub-folder's processing will be handled by the transform script.
def scanFolder(verbose, theScriptRoot, theMatches, theMatchTimestamps, thePreviousInputFileTimestamps, theInputFolder, theOutputRoot, theOutputFolder):
    ifVerbose(verbose, "ScanFolder       -  folder: " + str(theInputFolder))
    outputFiles = []
    unmatchedItems = []
    newInputFileTimestamps = {}
    for item in theInputFolder.iterdir():
        matched = False
        itemStr = str(item)
        if item.is_dir():
            itemStr = itemStr + "/"
        for match in theMatches:
            if (matched == False) and (not re.match(match, itemStr) == None):
                matched = True
                ifVerbose(verbose, "ScanFolder       - matched: " + itemStr + " with " + match)
                scriptExec = (theMatches[match])[0]
                scriptPath = theScriptRoot / pathlib.Path((theMatches[match])[1])
                scriptPathStr = str(scriptPath)
                scriptPathParentStr = str(scriptPath.parent)
                scriptTimestamp = "0"
                if scriptPathStr in theMatchTimestamps:
                    scriptTimestamp = theMatchTimestamps[scriptPathStr]
                inputTimestamp = "0"
                if str(item) in thePreviousInputFileTimestamps:
                    inputTimestamp = thePreviousInputFileTimestamps[str(item)]
                commandLine = [scriptExec, scriptPathStr, "--input", str(item), "--outputRoot", str(theOutputRoot), "--output", str(theOutputFolder) + os.sep + item.name]
                if verbose:
                    commandLine.append("--verbose")
                matchInputItems = {}
                if item.is_file():
                    if str(item) in thePreviousInputFileTimestamps:
                        matchInputItems[itemStr] = thePreviousInputFileTimestamps[itemStr]
                else:
                    for matchInputItem in thePreviousInputFileTimestamps:
                        if matchInputItem.startswith(itemStr):
                            matchInputItems[matchInputItem] = thePreviousInputFileTimestamps[matchInputItem]
                for matchScriptItem in theMatchTimestamps:
                    if matchScriptItem.startswith(scriptPathParentStr):
                        matchInputItems[matchScriptItem] = theMatchTimestamps[matchScriptItem]
                ifVerbose(verbose, "ScanFolder       - running: " + " ".join([f"{value}" for value in commandLine]))

                # We expect the output (on stdout) from a sub-script to be a list of input file filename,timestamp pairs, then a "---", then a list of output files.
                def streamOutPipe(pipe, label):
                    state = 0
                    for outputLine in pipe:
                        outputLine = outputLine.strip()
                        if not outputLine == "":
                            if state == 0:
                                if outputLine == "---":
                                    state = 1
                                else:
                                    outputLineSplit = outputLine.split(",")
                                    newInputFileTimestamps[outputLineSplit[0]] = outputLineSplit[1]
                            elif state == 1:
                                outputFiles.append(outputLine)
                
                # Any output on stderr from a child process we simply re-write to the main stdout.
                def streamErrPipe(pipe, label):
                    for line in pipe:
                        if verbose:
                            if not line.strip() == "":
                                sys.stdout.write(line)

                # Start a sub-process script, streaming its stdout and stderr concurrently in background threads.
                commandLineProcess = subprocess.Popen(commandLine, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    executor.submit(streamOutPipe, commandLineProcess.stdout, "STDOUT")
                    executor.submit(streamErrPipe, commandLineProcess.stderr, "STDERR")
                    # Pass the matchInputItems data to the sub-process.
                    commandLineProcess.stdin.write("\n".join([f"{key},{value}" for key, value in matchInputItems.items()]))
                    commandLineProcess.stdin.flush()
                    # Signal EOF (End of File) to child process.
                    commandLineProcess.stdin.close()
                # Wait for the process to exit.
                commandLineProcess.wait()
        if (matched == False):
            unmatchedItems.append(item)
    for item in unmatchedItems:
        if item.is_dir():
            matchInputItems = {}
            for matchInputItem in thePreviousInputFileTimestamps:
                if matchInputItem.startswith(str(item)):
                    matchInputItems[matchInputItem] = thePreviousInputFileTimestamps[matchInputItem]
            subNewInputFileTimestamps, subOutputFiles = scanFolder(verbose, theScriptRoot, theMatches, theMatchTimestamps, matchInputItems, item, theOutputRoot, theOutputFolder / pathlib.Path(item.name))
            newInputFileTimestamps.update(subNewInputFileTimestamps)
            outputFiles.extend(subOutputFiles)
    return newInputFileTimestamps, outputFiles
