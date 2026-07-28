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
        officeToMarkdownLib.ifVerbose(args["verbose"], "ScanFolders      -  update: " + itemPathStr + " - re-running all scripts.")
        previousMatchChanges = {}

# Read the inputChanges cache file, a list of previously-seen input files and their last-updated filestamps.
inputChangesPath = args["dataRoot"] / pathlib.Path("inputChanges.csv")
previousInputChanges = officeToMarkdownLib.readChangesFile(inputChangesPath)

# Looks through the contents of the input folder, applying a transform script to each file or folder found.
# A cache of file paths with checksum details is maintained, this is used to avoid processing a file if it (and the associated processing script) hasn't been changed since the last run.
# Folders are recursed into. Some matches might match whole sub-folders, in which case that sub-folder's processing will be handled by the transform script.
currentInputChanges = {}
outputFiles = []
def scanFolder(theInputFolder, theOutputFolder):
    if args["verbose"]:
        print("ScanFolder       -  folder: " + str(theInputFolder))
    unmatchedItems = []
    for item in theInputFolder.iterdir():
        matched = False
        itemStr = str(item)
        if item.is_dir():
            itemStr = itemStr + "/"
        for match in matches:
            if (matched == False) and (not re.match(match, itemStr) == None):
                matched = True
                if args["verbose"]:
                    print(verbose, "ScanFolder       - matched: " + itemStr + " with " + match)
                scriptExec = (matches[match])[0]
                scriptPath = args["scriptRoot"] / pathlib.Path((matches[match])[1])
                scriptPathStr = str(scriptPath)
                scriptPathParentStr = str(scriptPath.parent)
                scriptTimestamp = "0"
                if scriptPathStr in previousMatchChanges:
                    scriptTimestamp = previousMatchChanges[scriptPathStr]
                inputTimestamp = "0"
                if str(item) in previousInputChanges:
                    inputTimestamp = previousInputChanges[str(item)]
                commandLine = [scriptExec, scriptPathStr, "--input", str(item), "--outputRoot", str(args["output"]), "--output", str(theOutputFolder) + os.sep + item.name]
                if verbose:
                    commandLine.append("--verbose")
                matchInputItems = {}
                if item.is_file():
                    if str(item) in previousInputChanges:
                        matchInputItems[itemStr] = previousInputChanges[itemStr]
                else:
                    for matchInputItem in previousInputChanges:
                        if matchInputItem.startswith(itemStr):
                            matchInputItems[matchInputItem] = previousInputChanges[matchInputItem]
                for matchScriptItem in previousMatchChanges:
                    if matchScriptItem.startswith(scriptPathParentStr):
                        matchInputItems[matchScriptItem] = previousMatchChanges[matchScriptItem]
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
                                    currentInputChanges[outputLineSplit[0]] = outputLineSplit[1]
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
            for matchInputItem in previousInputChanges:
                if matchInputItem.startswith(str(item)):
                    matchInputItems[matchInputItem] = previousInputChanges[matchInputItem]
            subCurrentInputChanges, subOutputFiles = scanFolder(item, theOutputFolder / pathlib.Path(item.name))
            currentInputChanges.update(subCurrentInputChanges)
            outputFiles.extend(subOutputFiles)
# Start the scanFolders process.
scanFolder(args["input"], pathlib.Path(""))

# Write the updated last-updated file timestamps the the "inputChanges" file.
officeToMarkdownLib.writeChangesFile(inputChangesPath, currentInputChanges)

# If the user has specified a "copy in" folder, copy the contens of that folder over to the destination as well.
# This happens after "scan folders", so for any conflicting filenames, the copy process will take precedence.
# This is an inline function which adds files copied to the "outputFiles" list.
def copyFolder(inputFolder, outputFolder):
    for inputItem in inputFolder.iterdir():
        outputItem = outputFolder / pathlib.Path(inputItem.name)
        outputFiles.append(str(outputItem))
        if inputItem.is_file():
            if (not outputItem.is_file()) or (not inputItem.stat().st_mtime == outputItem.stat().st_mtime):
                officeToMarkdownLib.ifVerbose(args["verbose"], "ScanFolder       -  copyIn: " + str(inputItem) + " to " + str(outputItem))
                shutil.copyfile(str(inputItem), str(outputItem))
                officeToMarkdownLib.makeModDatesMatch(str(inputItem), str(outputItem))
        else:
            outputItem.mkdir(parents=True, exist_ok=True)
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
