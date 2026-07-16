# Standard Python libraries.
import os
import re
import sys
import shutil
import pathlib
import subprocess

# Our own Docs To Markdown library.
import officeToMarkdownLib



# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "dataRoot":str(pathlib.Path.cwd()), "verbose":"false", "produceFolderIndexes":"false", "deleteExtraFiles":"false", "validFrontMatterFields":""}, requiredArgs=["input","output"], optionalArgs=["scriptRoot", "verbose", "deleteExtraFiles", "copyIn", "data", "produceFolderIndexes", "baseURL", "validFrontMatterFields"])
args["dataRoot"] = officeToMarkdownLib.normalisePath(args["dataRoot"])
verbose = False
if args["verbose"].lower() == "true":
    verbose = True
args["deleteExtraFiles"] = args["deleteExtraFiles"].lower()
args["produceFolderIndexes"] = args["produceFolderIndexes"].lower()
args["validFrontMatterFields"] = args["validFrontMatterFields"].split(",")

# Print a config summary for the user.
print("OfficeToMarkdown - arguments:", flush=True)
for arg in args:
    print(" - " + arg + ": " + str(args[arg]), flush=True)

# Read the "matches.csv" file, which describes which transform script to run for each file type / sub folder in the input folder structure.
matches = officeToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "matches.csv")
scriptStrings = []
for item in matches:
    scriptString = officeToMarkdownLib.normalisePath(args["scriptRoot"] + "/" + matches[item][1])
    if not scriptString in scriptStrings:
        scriptStrings.append(scriptString)

# Read the matchChanges cache file, and work out if any of the transform scripts have been updated since the last run.
previousMatchChanges = officeToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "matchChanges.csv")
currentMatchChanges = officeToMarkdownLib.getFolderChangeDetails(args["scriptRoot"])
changedMatchPaths = []
for item in currentMatchChanges:
    if item in scriptStrings:
        if item in previousMatchChanges:
            print(str(currentMatchChanges[item]) + " == " + str(previousMatchChanges[item]))
            if not str(currentMatchChanges[item]) == str(previousMatchChanges[item]):
                changedMatchPaths.append(item)
        else:
            print("Append: " + item)
            changedMatchPaths.append(item)
if args["verbose"] == "true":
    print("matches:")
    print(matches)
    print("changedMatchPaths:")
    print(changedMatchPaths)
officeToMarkdownLib.writeDataFile(args["dataRoot"] + os.sep + "matchChanges.csv", currentMatchChanges)

previousInputChanges = officeToMarkdownLib.readDataFile(args["dataRoot"] + os.sep + "inputChanges.csv")

# Start the scanFolders process.
currentInputChanges, outputFiles = officeToMarkdownLib.scanFolder(verbose, args["scriptRoot"], matches, previousMatchChanges, previousInputChanges, pathlib.Path(args["input"]), pathlib.Path(args["output"]))

# Write the updated input file modification timestamps the the "inputChanges" file.
officeToMarkdownLib.writeDataFile(args["dataRoot"] + os.sep + "inputChanges.csv", currentInputChanges)

def copyFolder(inputFolder, outputFolder):
    for inputItem in inputFolder.iterdir():
        outputItem = outputFolder / item
        outputFiles.append(str(outputItem))
        if inputItem.is_file():
            if not inputItem.stat().st_mtime == outputItem.stat().st_mtime:
                if verbose:
                    print("Copying file: " + inputItem + " to " + outputItem, flush=True)
                shutil.copyfile(str(inputItem), str(outputItem))
                officeToMarkdownLib.makeModDatesMatch(str(inputItem), str(outputItem))
        else:
            os.mkdir(str(outputItem))
            copyFolder(inputItem, outputItem)

# If the user has specified a "copy in" folder, copy the contens of that folder over to the destination as well.
# This happens after "scan folders", so for any conflicting filenames, the copy process will take precedence.
if "copyIn" in args and not args["copyIn"] == "":
    copyFolder(pathlib.Path(args["copyIn"]), pathlib.Path(args["output"]))

def deleteExtraFiles(theFolder):
    for item in theFolder.iterdir():
        if item.is_file():
            if not str(item) in outputFiles:
                print("Removing extra file: " + str(item), flush=True)
                os.remove(str(item))
        else:
            deleteExtraFiles(item)

if args["deleteExtraFiles"] == "true":
    #if verbose:
        #print("Deleting extra files - valid output files:")
        #print(outputFiles)
    deleteExtraFiles(pathlib.Path(args["output"]))
