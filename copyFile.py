# Convert a DOCX / DOC (Word, Google Docs, etc) file to Markdown.
# Designed to be called from the scanFolders script, so takes a very simple command line parameter list.

# Standard libraries.
import sys
import shutil
import pathlib

# Our own Office To Markdown library.
import officeToMarkdownLib

# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "verbose":"false", "validFrontMatterFields":""}, requiredArgs=["scriptTimestamp","inputPath","inputTimestamp","outputPath"], optionalArgs=["scriptRoot", "verbose"])
args["dataRoot"] = officeToMarkdownLib.normalisePath(args["dataRoot"])
args["verbose"] = args["verbose"].lower()
inputPath = pathlib.Path(args["inputPath"])
outputPath = pathlib.Path(args["outputPath"])

# We are passed the output /folder/, so we have to figure out the output file name from the input file name.
outputFilePath = outputPath / outputPath.name

# Report the output filename back to the calling script.
print(outputFilePath, flush=True, file=sys.stdout)

# Check and see if either the input file or the script itself have changed since the last
# run - there's no point doing any work if neither have changed.
doTransform = False
if not officeToMarkdownLib.checkTimestampsMatch(scriptTimestamp, pathlib.Path(__file__)):
  doTransform = True
elif not officeToMarkdownLib.checkTimestampsMatch(inputTimestamp, inputPath):
  doTransform = True
if doTransform:
  officeToMarkdownLib.ifVerbose(args["verbose"], "Copying file: " + inputPath + " to " + outputPath)
  shutil.copyfile(inputPath, outputPath)
  officeToMarkdownLib.makeModDatesMatch(inputPath, outputPath)
