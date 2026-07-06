# Standard Python libraries.
import os
import re
import sys
import shutil
import pathlib
import subprocess

# Our own Docs To Markdown library.
import docsToMarkdownLib



# Parse and normalise the command-line arguments.
args = docsToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "dataRoot":str(pathlib.Path.cwd()), "verbose":"false", "produceFolderIndexes":"false", "deleteExtraFiles":"false", "validFrontMatterFields":""}, requiredArgs=["input","output"], optionalArgs=["scriptRoot", "verbose", "deleteExtraFiles", "copyIn", "data", "produceFolderIndexes", "baseURL", "validFrontMatterFields"])
args["dataRoot"] = docsToMarkdownLib.normalisePath(args["dataRoot"])
args["verbose"] = args["verbose"].lower()
args["deleteExtraFiles"] = args["deleteExtraFiles"].lower()
args["produceFolderIndexes"] = args["produceFolderIndexes"].lower()
args["validFrontMatterFields"] = args["validFrontMatterFields"].split(",")

# Print a config summary for the user.
print("DocsToMarkdown - arguments:", flush=True)
for arg in args:
    print(" - " + arg + ": " + str(args[arg]), flush=True)

# Read the "matches.csv" file, which describes which transform script to run for each file type / sub folder in the input folder structure.
matches = docsToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "matches.csv")
scriptStrings = []
for item in matches:
    scriptString = docsToMarkdownLib.normalisePath(args["scriptRoot"] + "/" + matches[item][1])
    if not scriptString in scriptStrings:
        scriptStrings.append(scriptString)

# Read the matchChanges cache file, and work out if any of the transform scripts have been updated since the last run.
previousMatchChanges = docsToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "matchChanges.csv")
currentMatchChanges = docsToMarkdownLib.getFolderChangeDetails(args["scriptRoot"])
changedMatchPaths = []
for item in currentMatchChanges:
    if item in scriptStrings:
        if item in previousMatchChanges:
            if not currentMatchChanges[item] == previousMatchChanges[item]:
                changedMatchPaths.append(item)
        else:
            changedMatchPaths.append(item)
if args["verbose"] == "true":
    print("changedMatchPaths:")
    print(changedMatchPaths)
docsToMarkdownLib.writeDataFile(args["dataRoot"] + os.sep + "matchChanges.csv", currentMatchChanges)

previousInputChanges = docsToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "inputChanges.csv")
currentInputChanges = docsToMarkdownLib.getFolderChangeDetails(docsToMarkdownLib.normalisePath(args["input"]))
changedInputPaths = []
for item in currentInputChanges:
    if item in previousInputChanges:
        if not currentInputChanges[item] == previousInputChanges[item]:
            changedInputPaths.append(item)
    else:
        changedInputPaths.append(item)
if args["verbose"] == "true":
    print("changedInputPaths:")
    print(changedInputPaths)
docsToMarkdownLib.writeDataFile(args["dataRoot"] + os.sep + "inputChanges.csv", currentInputChanges)



# The start-point of the document-processing process. Looks through the contents of the input folder, applying a transform script to each file or folder found.
# A cache of file paths with checksum details is maintained, this is used to avoid processing a file if it (and the associated processing script) hasn't been changed since the last run.
# Folders are recursed into. Some matches might match whole sub-folders, in which case that sub-folder's processing will be handled by the transform script.
def scanFolder(theInput, theOutput):
    inputFolder = docsToMarkdownLib.normalisePath(args["input"] + "/" + theInput)
    if args["verbose"] == "true":
        print("DocsToMarkdown - scanning folder: " + inputFolder, flush=True)
    unmatchedItems = []

    items = os.listdir(inputFolder)
    items.insert(0, "")
    folderMatched = False
    for item in items:
        matched = False
        for match in matches:
            inputItem = inputFolder + "/" + item
            if (matched == False) and (folderMatched == False) and (not re.match(match, inputItem) == None):
                matched = True
                scriptExec = docsToMarkdownLib.platformPath(matches[match][0])
                scriptPath = docsToMarkdownLib.platformPath(args["scriptRoot"] + "/" + matches[match][1])
                inputItem = docsToMarkdownLib.platformPath(inputItem)
                if item == "":
                    folderMatched = True
                outputItem = docsToMarkdownLib.normalisePath(args["output"] + "/" + theOutput + "/" + item)
                if os.path.isfile(inputItem):
                    outputItem = outputItem.rsplit("/", 1)[0]
                outputItem = docsToMarkdownLib.platformPath(outputItem)
                
                if args["verbose"] == "true":
                    print("DocsToMarkdown - matched: " + inputItem + " with " + match, flush=True)

                if scriptPath in changedMatchPaths or inputItem in changedInputPaths:
                    commandLine = [scriptExec, scriptPath, inputItem, outputItem]
                    if args["verbose"] == "true":
                        print("DocsToMarkdown - running: " + " ".join(commandLine), flush=True)
                    subprocess.run(commandLine)
        if (matched == False) and (folderMatched == False) and (not item == ""):
            unmatchedItems.append(item)
    for item in unmatchedItems:
        if os.path.isdir(inputFolder + os.sep + item):
            scanFolder(docsToMarkdownLib.normalisePath(theInput + os.sep + item), docsToMarkdownLib.normalisePath(theOutput + os.sep + item))

def copyFolder(inputFolder, outputFolder):
    print("copyFolder: " + inputFolder + " -> " + outputFolder)
    for item in os.listdir(inputFolder):
        inputItem = inputFolder + "/" + item
        outputItem = outputFolder + "/" + item
        docsToMarkdownLib.addToWriteLog(outputItem)
        if os.path.isfile(inputItem):
            if not docsToMarkdownLib.checkModDatesMatch(inputItem, outputItem):
                print("Copying file: " + inputItem + " to " + outputItem, flush=True)
                shutil.copyfile(inputItem, outputItem)
                docsToMarkdownLib.makeModDatesMatch(inputItem, outputItem)
        else:
            os.mkdir(outputItem)
            copyFolder(inputItem, outputItem)

def deleteExtraFiles(theFolder, theFilenames):
    for item in os.listdir(theFolder):
        fileItem = theFolder + "/" + item
        if os.path.isfile(fileItem):
            if not fileItem in theFilenames:
                print("Removing extra file: " + fileItem, flush=True)
                os.remove(fileItem)
        else:
            deleteExtraFiles(fileItem, theFilenames)

# Start the scanFolders process.
scanFolder("", "")

# If the user has specified a "copy in" folder, copy the contens of that folder over to the destination as well.
# This happens after "scan folders", so for any conflicting filenames, the copy process will take precedence.
if "copyIn" in args and not args["copyIn"] == "":
    copyFolder(docsToMarkdownLib.normalisePath(args["copyIn"]), docsToMarkdownLib.normalisePath(args["output"]))

if args["deleteExtraFiles"] == "true" and os.path.isfile("/tmp/docsToMarkdownWriteLog.txt"):
    with open("/tmp/docsToMarkdownWriteLog.txt", "r", encoding="utf-8") as writeLogFile:
        deleteExtraFiles(docsToMarkdownLib.normalisePath(args["output"]), writeLogFile.readlines())

# Clear out the write log file.
#os.remove("/tmp/docsToMarkdownWriteLog.txt")
