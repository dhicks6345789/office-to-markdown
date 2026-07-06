#!/usr/bin/python3

# Standard libraries.
import os
import re
import sys
import math
import shutil
import subprocess

# Handle JSON-formatted files.
import json

# DocsToMarkdown: Converts a set of Word / Excel files (compatability with those produced by Mircosoft Office, Office 365,
# Google Docs or, hopefully, pretty much any other tool) to the Govspeak varient of Markdown as specified by GOV.UK. Can also
# convert some data to CSV format. The Markdown output is intended to be used as the input for static site generation tools such
# as Jeykll, Hugo or Hyde, and various options / assumtions exist to ensure the files produced are suitible for those tools.

# We use the Pandas library, which in turn uses the XLRD library, to read Excel data.
import xlrd
import pandas

# Compares two version-number style string, i.e. "numbers" with multiple decimal points (w.x.y.z), returns true if the left version is greater than or equal to
# the right. Inputs are strings, version number parts can't include letters.
def verMoreThanOrEqual(verLeft, verRight):
    if verLeft == verRight:
        return True
    splitIndex = 0
    rightSplit = verRight.split(".")
    for leftItem in verLeft.split("."):
        if int(leftItem) > int(rightSplit[splitIndex]):
            return True
        splitIndex = splitIndex + 1
    return False

# This utility depends on the Ruby-based utility Pandoc, version 2.7 or higher, released Monday, 4th March 2019.
# Earlier versions (as generally packaged in Debian's repositories, for instance) have a bug which stops them parsing DOCX files
# created with Office 365.
pandocVersion = ""
pandocHandle = os.popen("pandoc --version 2>&1")
pandocOutput = pandocHandle.readlines()
pandocHandle.close()
pandocMatchResult = re.match("pandoc (\d.*)", pandocOutput[0])
if not pandocMatchResult == None:
    pandocVersion = pandocMatchResult.group(1).strip()
if pandocVersion == "" or not verMoreThanOrEqual(pandocVersion, "2.7"):
    print("ERROR: Pandoc v2.7 or higher not found.")
    sys.exit(1)

globalValues = {}

# Pandoc escapes Markdown control characters embedded in Word documents, but we want to let people embed chunks of Markdown in
# a document if they want, so we un-escape the Markdown back again - we simply use Python's string.replace to replace characters
# in strings.
markdownReplace = {"\\[":"[","\\]":"]","\\!":"!","\\`\\`\\`":"```","\`\`\`":"```"}

# A utility function to return the contents of the given file.
def getFile(theFilename):
    infile = open(theFilename)
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
    
# A utility function to return a given path string in normalised format, i.e. without any double os.sep characters.
def normalisePath(thePath):
    if thePath == "":
        return "/"
    return(thePath.replace("//","/"))

# A utility function to determine whether a variable has a value of "NaN" or not.
# Checks if a string has a value of "NaN" (any case) as well as float values.
def isnan(theVal):
    if isinstance(theVal, str):
        if theVal.lower() == "nan":
            return True
        return False
    return math.isnan(theVal)

# A utility function to convert from a floating-point number to a string. Python (or Pandas, anyway) converts blank Excel cells into floats
# with a value of NaN. Converting those to a string results in the string "nan". We just want a blank string.
def valueToString(theVal):
    if isinstance(theVal, str):
        if theVal.lower() == "nan":
            return ""
        else:
            return theVal
    if isinstance(theVal, float):
        if math.isnan(theFloat):
            return ""
    return(str(theVal))

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

# Takes a file path string pointing to a document file (.DOC, .DOCX, .TXT, etc) file, loads that file and coverts the contents to a Markdown / Govspeak string.
# Returns a tuple of a string of the converted data and a dict of any front matter variables specified in the input file.
def documentToGovspeak(inputFile):
    baseURL = ""
    if "baseURL" in globalValues.keys():
        baseURL = globalValues["baseURL"]
    markdown = ""
    frontMatter = {}
    
    # As of around Monday, 4th March 2019, Pandoc 2.7 now seems to work correctly for parsing DOCX files produced by Word Online.
    # Debian's Pandoc package is still on version 2.5, so Pandoc needs to be installed via the .deb file provided on their website.
    pandocProcess = subprocess.Popen("pandoc --wrap=none -s \"" + inputFile + "\" -t gfm -o -", shell=True, stdout=subprocess.PIPE)
    for markdownLine in pandocProcess.communicate()[0].decode("utf-8").split("\n"):
        for markdownReplaceKey in markdownReplace.keys():
            markdownLine = markdownLine.replace(markdownReplaceKey, markdownReplace[markdownReplaceKey])
        lineIsFrontMatter = False
        for validFrontMatterField in args["validFrontMatterFields"]:
            if markdownLine.lower().startswith(validFrontMatterField.lower() + ":"):
                frontMatter[validFrontMatterField] = markdownLine.split(":")[1].strip()
                lineIsFrontMatter = True
        if not lineIsFrontMatter:
            markdown = markdown + markdownLine.replace(baseURL, "") + "\n"
    return(markdown, frontMatter)
    
# Takes an input Excel / CSV file, loads that as a Pandas dataframe and returns a Markdown / Govspeak string.
def spreadsheetToGovspeak(inputFile):
    inputDataFrame = pandas.read_excel(io=inputFile)
    # First, the header row...
    rowString = ""
    for header in inputDataframe.headers:
        rowString = rowString + "| " + header + " "
    result = rowString + "|\n"
    # ...then a simple line to split the headers from the data...
    rowString = ""
    for header in inputDataframe.headers:
        rowString = rowString + "| --- "
    result = result + rowString + "|\n"
    # ...then add in each row of data.
    for index, row in inputDataframe.iterrows():
        rowString = ""
        for header in inputDataframe.headers:
            rowString = rowString + "| " + valueToString(row[header]) + " "
        result = result + rowString + "|\n"
    return(result)

# Removes the given file from the global filesToProcess array, if it's listed in there in the first place.
def removeFromFilesToProcess(theFile):
    theFile = normalisePath(theFile)
    if theFile in filesToProcess:
        filesToProcess.remove(theFile)

# Recursivly check each sub-folder in the given input folder, returning an array of input files with full paths.
def processInputFolder(rootPath, subPath):
    result = []
    for item in os.listdir(rootPath + os.sep + subPath):
        if os.path.isdir(rootPath + os.sep + subPath + os.sep + item):
            result = result + processInputFolder(rootPath, subPath + os.sep + item)
        else:
            result.append((normalisePath(rootPath + os.sep + subPath + os.sep + item)))
    return(result)

# Copy each file from srcFolder to destFolder, and recurse down sub-folders.
# Removes each encountered file from the filesToProcess list as it goes.
def copyFolder(srcFolder, destFolder):
    os.makedirs(destFolder, exist_ok=True)
    for item in os.listdir(srcFolder):
        if os.path.isdir(srcFolder + os.sep + item):
            copyFolder(srcFolder + os.sep + item, destFolder + os.sep + item)
        else:
            # Skip copying if the file already exists and is up-to-date.
            copyFile = True
            if os.path.exists(destFolder + os.sep + item):
                if os.stat(srcFolder + os.sep + item).st_mtime == os.stat(destFolder + os.sep + item).st_mtime:
                    copyFile = False
            if copyFile:
                shutil.copyfile(srcFolder + os.sep + item, destFolder + os.sep + item)
                shutil.copystat(srcFolder + os.sep + item, destFolder + os.sep + item)
            removeFromFilesToProcess(srcFolder + os.sep + item)
                
# Takes a chunk of Govspeak Markdown text as input, returns that text with any ordered lists converted to legislative lists,
# i.e. lists where numbering is explicitly specified, not restarted from scratch as is the Kramdown / Govspeak default.
def makeLegislativeLists(theGovspeak):
    result = ""
    for theGovspeakLine in theGovspeak.split("\n"):
        searchResult = re.search(r'^(\d[\d \.]*)\. *>', theGovspeakLine)
        if not searchResult == None:
            result = result + "{:start=\"" + searchResult.group(1).replace(" ", "") + "\"}\n"
        result = result + theGovspeakLine.rstrip() + "\n"
    return(result)

# Takes a chunk of Govspeak Markdown text as input, returns that text normalised - multiple blank lines removed, any extra
# whitespace at the end of lines removed.
def normaliseGovspeak(theGovspeak):
    result = ""
    previousLineWasBlank = True
    for theGovspeakLine in theGovspeak.split("\n"):
        theGovspeakLine = theGovspeakLine.rstrip()
        if theGovspeakLine == "":
            if not previousLineWasBlank:
                result = result + "\n"
            previousLineWasBlank = True
        else:
            result = result + theGovspeakLine + "\n"
            previousLineWasBlank = False
    return(result.rstrip())



requiredArgs = ["input","output"]
optionalArgs = ["data","template","baseURL"]
optionalLists = ["validFrontMatterFields"]

userFunctions = []
functionArgs = {"convertToMarkdown":["inputFiles","outputFiles","frontMatter"],"filesToMarkdown":["inputFiles","outputFile","frontMatter"],"folderToPlaceholderFile":["inputFolder","outputFile"],"filesToCSV":["inputFiles","outputFile","jekyllHeaders"],"listFilesToData":["inputFolder","outputFile"],"copyFolder":["source","destination"]}

args = {}
args["data"] = ""
args["template"] = ""
args["baseURL"] = "http://localhost"

# When we examine a Word document, if it starts with what looks like YAML-style variables then we will treat that as Hugo / Jeykll
# front matter values. We only check for the variables as given below, otherwise every document that starts with a colon in the
# first line would get treated as front matter.
args["validFrontMatterFields"] = ["title","lastUpdated"]
#args["defaultFrontMatter"] = {"layout":"default"}

# Process the command-line arguments.
currentArgName = None
for argItem in sys.argv[1:]:
    if argItem.startswith("--"):
        currentArgName = argItem[2:]
    elif not currentArgName == None:
        args[currentArgName] = argItem
        currentArgName = None
    else:
        print("ERROR: unknown argument, " + argItem)
        sys.exit(1)

if "config" in args.keys():
    if args["config"].endswith(".csv"):
        argsData = pandas.read_csv(args["config"], header=0)
    else:
        argsData = pandas.read_excel(args["config"], header=0)
    for argsDataIndex, argsDataValues in argsData.iterrows():
        if argsDataValues[0] in requiredArgs + optionalArgs:
            args[argsDataValues[0]] = valueToString(argsDataValues[1])
        elif argsDataValues[0] in optionalLists:
            for argsDataValue in argsDataValues[1:].values:
                if not isnan(argsDataValue):
                    args[argsDataValues[0]].append(argsDataValue)
        elif argsDataValues[0] in functionArgs.keys():
            userFunction = {}
            userFunction["function"] = argsDataValues[0]
            functionArgIndex = 1
            for functionArg in functionArgs[argsDataValues[0]]:
                userFunction[functionArg] = argsDataValues[functionArgIndex]
                functionArgIndex = functionArgIndex + 1
            userFunctions.append(userFunction)

for requiredArg in requiredArgs:
    if not requiredArg in args.keys():
        print("ERROR: Missing value for argument " + requiredArg)
        print("Usage: docsToMarkdown --config --input --output --template")
        sys.exit(1)
    
# A quick output message for the user.
print("Config file: " + args["config"])
print("Input folder: " + args["input"])
print("Output folder: " + args["output"])
if not args["data"] == "":
    print("Data folder: " + args["data"])
if not args["template"] == "":
    print("Template folder: " + args["template"])

# Make sure the defined output folder exists...
os.makedirs(args["output"], exist_ok=True)
# ...then copy any template files to the output folder.
if not args["template"] == "":
    os.system("cp -r " + args["template"] + "/* " + args["output"])

# Get a list of all the input files to process...
filesToProcess = processInputFolder(args["input"], "")
# ...and produce a matching list of all folders.
foldersToProcess = {}
for fileToProcess in filesToProcess:
    foldersToProcess[fileToProcess.rsplit("/",1)[0]] = ""
foldersToProcess = foldersToProcess.keys()

# Step through each user-defined function.
for userFunction in userFunctions:
    if userFunction["function"] == "convertToMarkdown":
        inputOutputFiles = {}
        for fileToProcess in filesToProcess:
            userFileMatchResult = re.match(userFunction["inputFiles"], fileToProcess)
            if not userFileMatchResult == None:
                inputOutputFiles[fileToProcess] = re.sub(userFunction["inputFiles"], userFunction["outputFiles"], fileToProcess[len(args["input"]):])
        for inputFile in sorted(inputOutputFiles.keys()):
            outputFile = inputOutputFiles[inputFile]
            outputPath = normalisePath(args["output"] + os.sep + outputFile)
            print("convertToMarkdown " + inputFile + " to " + outputPath, flush=True)
            if inputFile.lower().endswith(".docx"):
                (fileGovspeak, fileFrontMatter) = documentToGovspeak(inputFile)
                outputGovspeak = normaliseGovspeak(frontMatterToString(fileFrontMatter) + "\n\n" + fileGovspeak)
            elif inputFile.lower().endswith(".xlsx"):
                outputGovspeak = outputGovspeak + spreadsheetToGovspeak(inputFile) + "\n\n"
            putFile(outputPath, outputGovspeak.rstrip())
            removeFromFilesToProcess(inputFile)
    elif userFunction["function"] == "concatToMarkdown":
        logMessage = "fileToMarkdown - inputs: "
        outputGovspeak = ""
        outputFrontMatter = {}
        subRootPath = ""
        for inputFile in inputFiles:
            logMessage = logMessage + inputFile[len(args["input"]):] + ", "
            if inputFile.lower().endswith(".docx"):
                (fileGovspeak, fileFrontMatter) = documentToGovspeak(inputFile)
                outputGovspeak = outputGovspeak + fileGovspeak + "\n\n"
                for frontMatterItem in fileFrontMatter.keys():
                    outputFrontMatter[frontMatterItem] = fileFrontMatter[frontMatterItem]
            elif inputFile.lower().endswith(".xlsx"):
                outputGovspeak = outputGovspeak + spreadsheetToGovspeak(inputFile) + "\n\n"
            removeFromFilesToProcess(inputFile)
        #if "produceLegislativeLists" in configItem.keys():
        #    if configItem["produceLegislativeLists"] == "true":
        #        outputGovspeak = makeLegislativeLists(outputGovspeak)
        outputGovspeak = normaliseGovspeak(outputGovspeak)
        outputPath = normalisePath(args["output"] + os.sep + outputFile)
        putFile(outputPath, outputGovspeak.rstrip())
        logMessage = logMessage + "output: " + outputPath[len(args["output"]):]
        print(logMessage, flush=True)
    elif userFunction["function"] == "listFilesToData":
        for folderToProcess in foldersToProcess:
            userFolderMatchResult = re.match(userFunction["inputFolder"], folderToProcess)
            if not userFolderMatchResult == None:
                outputFile = re.sub(userFunction["inputFolder"], userFunction["outputFile"], normalisePath(folderToProcess[len(args["input"]):]))
                outputPath = normalisePath(args["data"] + os.sep + outputFile)
                print("listFilesToData " + folderToProcess + " to " + outputPath, flush=True)
                output = "["
                for item in sorted(os.listdir(folderToProcess)):
                    if os.path.isfile(folderToProcess + os.sep + item):
                        output = output + "\"" + item + "\","
                putFile(outputPath, output[:-1] + "]")
    elif userFunction["function"] == "folderToPlaceholderFile":
        for folderToProcess in foldersToProcess:
            userFolderMatchResult = re.match(userFunction["inputFolder"], folderToProcess)
            if not userFolderMatchResult == None:
                outputFile = re.sub(userFunction["inputFolder"], userFunction["outputFile"], folderToProcess[len(args["input"]):])
                outputPath = normalisePath(args["output"] + os.sep + outputFile)
                print("folderToPlaceholderFile " + outputPath, flush=True)
                putFile(outputPath, "")
