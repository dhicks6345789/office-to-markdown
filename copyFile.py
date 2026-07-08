# Convert a DOCX / DOC (Word, Google Docs, etc) file to Markdown.
# Designed to be called from the scanFolders script, so takes a very simple command line parameter list.

# Standard libraries.
import sys
import shutil
import pathlib

# Our own Office To Markdown library.
import officeToMarkdownLib

# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "validFrontMatterFields":"", "verbose":"false"}, requiredArgs=["scriptTimestamp","inputPath","outputPath"], optionalArgs=["scriptRoot", "verbose"])
verbose = False
if args["verbose"].lower() == "true":
  verbose = True
inputPath = pathlib.Path(args["inputPath"])
inputPathTimestamp = str(inputPath.stat().st_mtime)
outputPath = pathlib.Path(args["outputPath"])

# The calling script provides a list of any input files, along with file update timestamps, via stdin.
previousInputFileTimestamps = {}
for line in sys.stdin:
  lineSplit = line.strip().split(",")
  previousInputFileTimestamps[lineSplit[0]] = lineSplit[1]

# We are passed the output /folder/, so we have to figure out the output file name from the input file name.
outputFilePath = outputPath / inputPath.name

# Report the input filename, with current update timestamp, back to the calling script.
print(str(inputPath) + "," + inputPathTimestamp, flush=True, file=sys.stdout)
print("---", flush=True, file=sys.stdout)
# Report the output filename back to the calling script.
print(outputFilePath, flush=True, file=sys.stdout)

# Check and see if either the input file or the script itself have changed since the last
# run - there's no point doing any work if neither have changed.
doTransform = False
if not officeToMarkdownLib.checkTimestampsMatch(args["scriptTimestamp"], pathlib.Path(__file__)):
  doTransform = True
elif not officeToMarkdownLib.checkTimestampsMatch(args["inputTimestamp"], inputPath):
  doTransform = True
if doTransform:
  officeToMarkdownLib.ifVerbose(args["verbose"], "copyFile         - Copying file: " + str(inputPath) + " to " + str(outputPath))
  shutil.copyfile(str(inputPath), str(outputFilePath))
  officeToMarkdownLib.makeModDatesMatch(inputPath, outputPath)
