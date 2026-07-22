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



# Parse command-line arguments.
parser = officeToMarkdownLib.setArgsForGeneral(argparse.ArgumentParser(description="Scans a folder structure and runs transform scripts on matched files and sub-folders."))
parser.add_argument("--copyIn", type=pathlib.Path, default="", help="Copy in the contents of the given folder to the output folder.")
parser.add_argument("--deleteExtraFiles", action="store_true", help="Remove any extra files from the output folder not egnerated by this script.")
parser.add_argument("--dryRunExtraFiles", action="store_true", help="Does a dry-run of the deleteExtraFiles option, just displaying which files would be deleted by this action.")
args = vars(parser.parse_args())

# Print a config summary for the user.
print("OfficeToMarkdown - arguments:", flush=True)
for arg in args:
    print(" - " + arg + ": " + str(args[arg]), flush=True)

# Read the "matches.csv" file, which describes which transform script to run for each file type / sub folder in the input folder structure.
matches = officeToMarkdownLib.readDataFile(args["dataRoot"] / pathlib.Path("matches.csv"))

# Read the matchChanges cache file, a list of the script files used to do the transforms along with their last-updated timestamps...
matchChangesPath = args["dataRoot"] / pathlib.Path("matchChanges.csv")
previousMatchChanges = officeToMarkdownLib.readChangesFile(matchChangesPath)
# ...then get the current last-updated timestamps of the script files so we can work out if any of the transform scripts have been updated since the last run...
currentMatchChanges = officeToMarkdownLib.getFolderChangeDetails(args["scriptRoot"])
# ...and save those new update timestamps.
officeToMarkdownLib.writeChangesFile(matchChangesPath, currentMatchChanges)

# If the main scripts or library have been updated we want all scripts to be re-run.
for item in ["scanFolders.py", "officeToMarkdownLib.py"]:
    itemPath = args["scriptRoot"] / pathlib.Path(item)
    itemPathStr = str(itemPath)
    if (not itemPathStr in previousMatchChanges) or (not previousMatchChanges[itemPathStr] == currentMatchChanges[itemPathStr]):
        officeToMarkdownLib.ifVerbose(args["verbose"], itemPathStr + " updated - re-running all scripts.")
        previousMatchChanges = {}

# Read the inputChanges cache file, a list of previously-seen input files and their last-updated filestamps.
inputChangesPath = args["dataRoot"] / pathlib.Path("inputChanges.csv")
previousInputChanges = officeToMarkdownLib.readChangesFile(inputChangesPath)

# Start the scanFolders process. This scans the given folder, using the passed-in dicts of last-updated timestamps to spot any changed files so we can avoid re-doing work if we don't need to.
# The function returns a dict of updated last-updated timestamps for input files and a list of output files.
currentInputChanges, outputFiles = officeToMarkdownLib.scanFolder(args["verbose"], args["scriptRoot"], matches, previousMatchChanges, previousInputChanges, args["input"], args["output"])

# Write the updated last-updated file timestamps the the "inputChanges" file.
officeToMarkdownLib.writeChangesFile(inputChangesPath, currentInputChanges)

# If the user has specified a "copy in" folder, copy the contens of that folder over to the destination as well.
# This happens after "scan folders", so for any conflicting filenames, the copy process will take precedence.
# This is an inline function which adds files copied to the "outputFiles" list.
def copyFolder(inputFolder, outputFolder):
    for inputItem in inputFolder.iterdir():
        outputItem = outputFolder / item
        outputFiles.append(str(outputItem))
        if inputItem.is_file():
            if not inputItem.stat().st_mtime == outputItem.stat().st_mtime:
                officeToMarkdownLib.ifVerbose(args["verbose"], "ScanFolder       - copyIn: " + inputItem + " to " + outputItem, flush=True)
                shutil.copyfile(str(inputItem), str(outputItem))
                officeToMarkdownLib.makeModDatesMatch(str(inputItem), str(outputItem))
        else:
            os.mkdir(str(outputItem))
            copyFolder(inputItem, outputItem)
if "copyIn" in args and not str(args["copyIn"]) == "":
    copyFolder(args["copyIn"], args["output"])

# If the user has specified the "deleteExtraFiles" option then we clear any extra files out of the output destination. We define "extra files" as any files that could not have been produced as output files
# this run, i.e. the contents of the "outputFiles" list. Note that this list should include files that would have been oputput by any sub-script, even if they weren't updated this run because non of their inputs
# were updated. Sub-scripts should always return a list of all output file paths even if they don't actually output that file on a particular run.
def deleteExtraFiles(theFolder):
    for item in theFolder.iterdir():
        if item.is_file():
            if not str(item) in outputFiles:
                officeToMarkdownLib.ifVerbose(args["verbose"], "ScanFolder       -  delete: " + str(item))
                os.remove(str(item))
        else:
            deleteExtraFiles(item)
if args["deleteExtraFiles"] == True:
    deleteExtraFiles(args["output"])
