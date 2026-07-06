# Standard libraries.
import os
import io
import sys
import yaml
import base64
import subprocess

# The Pillow image-handling library.
import PIL.Image

# We use the Pandas library, which in turn uses the XLRD library, to read Excel data.
import pandas



# Pandoc escapes Markdown control characters embedded in Word documents, but we want to let people embed chunks of Markdown in
# a document if they want, so we un-escape the Markdown back again - we simply use Python's string.replace to replace characters
# in strings.
markdownReplace = {"\\[":"[","\\]":"]","\\!":"!","\\`\\`\\`":"```"}

# An array of "image file" types.
bitmapTypes = ["jpg", "jpeg", "png", "ico"]
imageTypes =  bitmapTypes + ["svg"]

# An array of "video file" types.
videoTypes = ["mp4"]

# An array of "url file" types.
urlTypes = ["url", "txt"]

# An array of "audio file" types.
audioTypes = ["mp3", "ogg", "wav"]

# Files / folders to exclude from directory listings.
fileIgnores = [".git", ".gitignore", "__pycache__", ".venv", "assets"]

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
    if os.sep in theFilename:
        parentFolderName = theFilename.rsplit(os.sep, 1)[0]
        if not os.path.exists(parentFolderName):
            os.makedirs(parentFolderName)
    outfile = open(theFilename, "wt", encoding="utf-8")
    outfile.write(theContent)
    outfile.close()

# A utility function to return a given path string in normalised format, i.e. with a consistant path separator ("/") accross platforms,
# and without any doubled path separators / no path separator at the end of the string.
def normalisePath(thePath):
    result = thePath.strip()
    if result == "":
        return ""
    result = result.replace(os.sep, "/")
    result = result.replace("//", "/")
    result = result.replace("/./", "/")
    if result[len(result)-1] == "/":
        result = result[:-1]
    return result

# Normalise the given path string, then replace any path separators with the platform-specific os.sep.
def platformPath(thePath):
    return normalisePath(thePath).replace("/", os.sep)

# A utility function to determine whether a variable has a value of "NaN" or not.
# Checks if a string has a value of "NaN" (any case) as well as float values.
def isnan(theVal):
    if isinstance(theVal, str):
        if theVal.lower() == "nan":
            return True
        return False
    return math.isnan(theVal)

def checkModDatesMatch(theInputItem, theOutputItem):
    if os.path.isfile(theOutputItem):
        inputItemDetails = os.stat(theInputItem)
        outputItemDetails = os.stat(theOutputItem)
        if inputItemDetails.st_mtime == outputItemDetails.st_mtime:
            return True
    return False

def makeModDatesMatch(theInputItem, theOutputItem):
    inputItemDetails = os.stat(theInputItem)
    os.utime(theOutputItem, (inputItemDetails.st_atime, inputItemDetails.st_mtime))

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
def docToMarkdown(inputFile, baseURL="", markdownType="gfm", validFrontMatterFields=[]):
    markdown = ""
    frontMatter = {}

    parsingFrontMatter = True
    blankLineCount = 0
    pandocProcess = subprocess.Popen("pandoc --wrap=none -s \"" + inputFile + "\" -t " + markdownType + " -o -", shell=True, stdout=subprocess.PIPE)
    for markdownLine in pandocProcess.communicate()[0].decode("utf-8").split("\n"):
        markdownLine = markdownLine.strip()
        # Un-escape Markdown control characters embedded in Word documents.
        for markdownReplaceKey in markdownReplace.keys():
            markdownLine = markdownLine.replace(markdownReplaceKey, markdownReplace[markdownReplaceKey])
        if parsingFrontMatter:
            if markdownLine == "":
                blankLineCount = blankLineCount + 1
            else:
                if blankLineCount < 2:
                    parsingFrontMatter = False
                    if ":" in markdownLine:
                        markdownSplit = markdownLine.split(":", 1)
                        frontMatterName = markdownSplit[0].strip()
                        if not " " in frontMatterName:
                            parsingFrontMatter = True
                            if (frontMatterName in validFrontMatterFields) or (validFrontMatterFields == []):
                                frontMatter[markdownSplit[0].strip()] = markdownSplit[1].strip()
                    else:
                        markdown = markdown + markdownLine.replace(baseURL, "") + "\n"
                blankLineCount = 0
        else:
            markdown = markdown + markdownLine.replace(baseURL, "") + "\n"
    return(markdown, frontMatter)

# Takes an input file and coverts it to Markdown, writing that Markdown to the given output file.
def docToMarkdownFile(inputFile, outputFile, baseURL="", markdownType="gfm", validFrontMatterFields=["title"]):
    outputMarkdown, outputFrontmatter = docToMarkdown(inputFile, baseURL=baseURL, markdownType=markdownType, validFrontMatterFields=validFrontMatterFields)
    putFile(outputFile, frontMatterToString(outputFrontmatter) + outputMarkdown)

# Parse any command line arguments passed.
def processCommandLineArgs(defaultArgs={}, requiredArgs=[], optionalArgs=[], optionalArgLists=[]):
    # Step through the system-provided command line arguments - remember sys.argv[0] is the script's path, so we skip that.
    args = {}
    currentArgName = None
    for argItem in sys.argv[1:]:
        if argItem.startswith("--"):
            currentArgName = argItem[2:]
        elif not currentArgName == None:
            args[currentArgName] = str(argItem)
            currentArgName = None
        else:
            print("ERROR: unknown argument, " + argItem)
            sys.exit(1)
    
    # If we have an argument of "config", treat that as a location to load a config file from, and go and process any further arguments given there.
    # If arguments defined on the command line are also present in the given config file, the command line arguments take precedence.
    if "config" in args.keys():
        fileArgs = processArgsFile(args["config"], optionalArgs=optionalArgs+requiredArgs, optionalArgLists=optionalArgLists)
        for argName in fileArgs.keys():
            args[argName] = fileArgs[argName]
    
    # If we have any default argument values defined, and those arguments
    # aren't already present, add the default values in to the result.
    for argName in defaultArgs.keys():
        if not argName in args.keys():
            args[argName] = defaultArgs[argName]

    # If any required arguments are missing, stop.
    for argName in requiredArgs:
        if not argName in args:
            print("ERROR: Required argument not present: " + argName, flush=True)
            sys.exit(1)
    return args

# Reads a CSV or Excel file, returns the contents of that file as an associative array, with the first column as the key and the second column as the data. If more than two columns are present, each data item will be an array.
def readDataFile(theFilename):
    result = {}
    if os.path.isfile(theFilename):
        # Figure out what format the file is in and use the appropriate loader.
        if theFilename.endswith(".csv"):
            pandasData = pandas.read_csv(theFilename, header=None)
        elif theFilename.endswith(".xlsx") or theFilename.endswith(".xls"):
            pandasData = pandas.read_excel(theFilename, header=None)
        returnScalars = False
        if pandasData.shape[1] == 2:
            returnScalars = True
        for index, row in pandasData.iterrows():
            if returnScalars:
                result[row[0]] = row[1]
            else:
                result[row[0]] = row.values.flatten().tolist()[1:]
        return(result)
    return result

# Writes the data contained in a dict to a CSV or Excel file.
def writeDataFile(theFilename, theData):
    pandasData = []
    for item in theData:
            pandasData.append([item, theData[item]])
    outputDataframe = pandas.DataFrame(pandasData)
    
    # Figure out what format the file is in and use the appropriate writer.
    if theFilename.endswith(".csv"):
        outputDataframe.to_csv(theFilename, index=False, header=False)
    elif theFilename.endswith(".xlsx") or theFilename.endswith(".xls"):
        outputDataframe.to_excel(theFilename, index=False, header=False)

# Parse arguments from a config file. Accepts CSV, Excel and YAML formats.
def processArgsFile(theFilename, defaultArgs={}, requiredArgs=[], optionalArgs=[], optionalArgLists=[]):
    args = {}
    argsData = {}
    # Figure out what format the file is in and use the appropriate loader.
    if theFilename.endswith(".csv"):
        argsData = pandas.read_csv(theFilename, header=0).to_dict(index=False)
    elif theFilename.endswith(".xlsx") or theFilename.endswith(".xls"):
        argsData = pandas.read_excel(theFilename, header=0).to_dict(index=False)
    elif theFilename.endswith(".yaml"):
        argsData = yaml.safe_load(getFile(theFilename))
    
    # Process any read arguments - check each key/value pair is a valid argument name.
    for argName in argsData.keys():
        argName = argName.strip()
        if argName in requiredArgs + optionalArgs:
            if not argName in args:
                args[argName] = str(argsData[argName])
                
    # If we have any default argument values defined, and those arguments
    # aren't already present, add the default values in to the result.
    for argName in defaultArgs.keys():
        if not argName in args.keys():
            args[argName] = defaultArgs[argName]

    # If any required arguments are missing, stop.
    for argName in requiredArgs:
        if not argName in args:
            print("ERROR: Required argument not present: " + argName, flush=True)
            quit
    return args

def getFolderChangeDetails(thePath):
    changes = {}
    for item in os.listdir(thePath):
        if not item in fileIgnores:
            itemPath = thePath + "/" + item
            if os.path.isdir(itemPath):
                subChanges = getFolderChangeDetails(itemPath)
                if not subChanges == {}:
                    changes.update(subChanges)
                    changes[itemPath] = sorted(subChanges.values())[0]
            else:
                changes[itemPath] = os.path.getmtime(itemPath)
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

def thumbnailVideo(theInputVideo, theOutputVideo, theBlockWidth, theBlockHeight):
    # Figure out the video's dimensions.
    videoDimensions = os.popen("ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x \"" + theInputVideo + "\" 2>&1").read().strip()
    videoWidth = int(videoDimensions.split("x")[0])
    videoHeight = int(videoDimensions.split("x")[1])
    print("Thumbnailing video: " + theInputVideo + ", Width: " + str(videoWidth) + ", Height: " + str(videoHeight))
    
    # Scale the dimensions given as the output to match the input video.
    width, height = getRatioedDimensions(videoWidth, videoHeight, theBlockWidth, theBlockHeight)
    print("Scaling video to Width: " + str(width) + ", Height: " + str(height))
    
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

    ffmpegLine = "ffmpeg -hide_banner -loglevel error -y -i \"" + theInputVideo + "\" -vf \"scale=" + str(scaledWidth) + ":" + str(scaledHeight) + ",pad=" + str(resultWidth) + ":" + str(resultHeight) + ":" + str(pasteX) + ":" + str(pasteY) + ":#FFFFFF@1,format=rgb24\" -vcodec libx264 -crf 18 \"" + theOutputVideo + "\" 2>&1"
    print(ffmpegLine)
    os.system(ffmpegLine)
    
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
