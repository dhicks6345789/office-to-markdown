# Standard Python libraries.
import os
import re
import sys
import shutil
import pathlib
import argparse
import subprocess

# Our own Docs To Markdown library.
import officeToMarkdownLib

# Parse input arguments.
parser = argparse.ArgumentParser(description="Scans a folder structure and runs transform scripts on matched files and sub-folders.")
parser.add_argument("--copyIn", type=pathlib.Path, default="", help="A folder to copy the contents of directly into the defined output folder.")
parser.add_argument("--deleteExtraFiles", action="store_true", help="Delete any files from the defined output folder not produced by this script.")
parser.add_argument("--dryRunExtraFiles", action="store_true", help="Do a dry run of the delete extra files operation - just list the files that would be deleted.")
parser.add_argument("--produceFolderIndexes", action="store_true", help="")
parser.add_argument("--validFrontMatterFields", action="store_true", help="")
args = officeToMarkdownLib.parseArgs(parser)

# Print a config summary for the user.
print("OfficeToMarkdown - arguments:", flush=True)
for arg in args:
    print(" - " + arg + ": " + str(args[arg]), flush=True)

sys.exit(0)

# Read the "matches.csv" file, which describes which transform script to run for each file type / sub folder in the input folder structure.
matches = officeToMarkdownLib.readDataFile(dataRoot + os.sep + "matches.csv")
scriptStrings = []
for item in matches:
    scriptString = officeToMarkdownLib.normalisePath(args["scriptRoot"] + "/" + matches[item][1])
    if not scriptString in scriptStrings:
        scriptStrings.append(scriptString)

# Read the matchChanges cache file, a list of the script files used to do the transforms along with their last-updated timestamps...
previousMatchChanges = officeToMarkdownLib.readChangesFile(dataRoot + os.sep + "matchChanges.csv")
# ...then get the current last-updated timestamps of the script files so we can work out if any of the transform scripts have been updated since the last run...
currentMatchChanges = officeToMarkdownLib.getFolderChangeDetails(args["scriptRoot"])
# ...and save those new update timestamps.
officeToMarkdownLib.writeChangesFile(dataRoot + os.sep + "matchChanges.csv", currentMatchChanges)

# If the main scripts or library have been updated we want all scripts to be re-run.
for item in ["scanFolders.py", "officeToMarkdownLib.py"]:
    itemPathStr = args["scriptRoot"] + os.sep + item
    if (not itemPathStr in previousMatchChanges) or (not previousMatchChanges[itemPathStr] == currentMatchChanges[itemPathStr]):
        officeToMarkdownLib.ifVerbose(verbose, itemPathStr + " updated - re-running all scripts.")
        previousMatchChanges = {}

# Read the inputChanges cache file, a list of previously-seen input files and their last-updated filestamps.
previousInputChanges = officeToMarkdownLib.readChangesFile(dataRoot + os.sep + "inputChanges.csv")

# Start the scanFolders process. This scans the given folder, using the passed-in dicts of last-updated timestamps to spot any changed files so we can avoid re-doing work if we don't need to.
# The function returns a dict of updated last-updated timestamps for input files and a list of output files.
currentInputChanges, outputFiles = officeToMarkdownLib.scanFolder(verbose, args["scriptRoot"], matches, previousMatchChanges, previousInputChanges, pathlib.Path(args["input"]), pathlib.Path(args["output"]))

# Write the updated last-updated file timestamps the the "inputChanges" file.
officeToMarkdownLib.writeChangesFile(dataRoot + os.sep + "inputChanges.csv", currentInputChanges)

# If the user has specified a "copy in" folder, copy the contens of that folder over to the destination as well.
# This happens after "scan folders", so for any conflicting filenames, the copy process will take precedence.
# This is an inline function which adds files copied to the "outputFiles" list.
def copyFolder(inputFolder, outputFolder):
    for inputItem in inputFolder.iterdir():
        outputItem = outputFolder / item
        outputFiles.append(str(outputItem))
        if inputItem.is_file():
            if not inputItem.stat().st_mtime == outputItem.stat().st_mtime:
                officeToMarkdownLib.ifVerbose(verbose, "Copying file: " + inputItem + " to " + outputItem, flush=True)
                shutil.copyfile(str(inputItem), str(outputItem))
                officeToMarkdownLib.makeModDatesMatch(str(inputItem), str(outputItem))
        else:
            os.mkdir(str(outputItem))
            copyFolder(inputItem, outputItem)
if "copyIn" in args and not args["copyIn"] == "":
    copyFolder(pathlib.Path(args["copyIn"]), pathlib.Path(args["output"]))

# If the user has specified the "deleteExtraFiles" option then we clear any extra files out of the output destination. We define "extra files" as any files that could not have been produced as output files
# this run, i.e. the contents of the "outputFiles" list. Note that this list should include files that would have been oputput by any sub-script, even if they weren't updated this run because non of their inputs
# were updated. Sub-scripts should always return a list of all output file paths even if they don't actually output that file on a particular run.
def deleteExtraFiles(theFolder):
    for item in theFolder.iterdir():
        if item.is_file():
            if not str(item) in outputFiles:
                officeToMarkdownLib.ifVerbose(verbose, "Removing extra file: " + str(item), flush=True)
                os.remove(str(item))
        else:
            deleteExtraFiles(item)
if args["deleteExtraFiles"] == "true":
    deleteExtraFiles(pathlib.Path(args["output"]))
