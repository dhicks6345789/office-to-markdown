# Copy a file.

# Standard libraries.
import sys
import shutil
import pathlib
import argparse

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
parser = argparse.ArgumentParser(description="Scans a folder structure and runs transform scripts on matched files and sub-folders.")
parser.add_argument("--scriptTimestamp", help="The previous last-modified timestamp value (as a floating point number) for this script.")
args = officeToMarkdownLib.parseArgs(parser)

# The calling script provides a list of any input files, along with file update timestamps, via stdin.
previousInputFileTimestamps = {}
for line in sys.stdin:
  lineSplit = line.strip().split(",")
  previousInputFileTimestamps[lineSplit[0]] = lineSplit[1]

# We are passed the output /folder/, so we have to figure out the output file name from the input file name.
outputFilePath = args["output"] / inputPath.name

# Report the input filename, with current update timestamp, back to the calling script.
print(str(args["input"]) + "," + inputPathTimestamp, flush=True, file=sys.stdout)
print("---", flush=True, file=sys.stdout)
# Report the output filename back to the calling script.
print(outputFilePath, flush=True, file=sys.stdout)

# Check and see if either the input file or the script itself have changed since the last
# run - there's no point doing any work if neither have changed.
doTransform = False
if not args["scriptTimestamp"] == str(pathlib.Path(__file__).stat().st_mtime):
  doTransform = True
elif (not str(inputPath) in previousInputFileTimestamps) or (not str(inputPath.stat().st_mtime) == previousInputFileTimestamps[str(inputPath)]):
  doTransform = True
if doTransform:
  officeToMarkdownLib.ifVerbose(args["verbose"], "copyFile         - copying: " + str(inputPath) + " to " + str(outputPath))
  shutil.copyfile(str(inputPath), str(outputFilePath))
  officeToMarkdownLib.makeModDatesMatch(inputPath, outputPath)
