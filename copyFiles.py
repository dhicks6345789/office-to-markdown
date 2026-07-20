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

scriptUpdated = False
if not args["scriptTimestamp"] == str(pathlib.Path(__file__).stat().st_mtime):
  scriptUpdated = True

# Copy individual files. If the input given is a folder, recurse into that folder and copy any files (or sub-folders) found.
filesCopied = {}
def copyFiles(theInputPath, theOutputPath):
  outputFilePath = theOutputPath / theInputPath.name
  if theInputPath.is_file:
    if scriptUpdated or (not str(inputPath) in previousInputFileTimestamps) or (not str(inputPath.stat().st_mtime) == previousInputFileTimestamps[str(inputPath)]):
      officeToMarkdownLib.ifVerbose(args["verbose"], "copyFile         - copying: " + str(theInputPath) + " to " + str(outputFilePath))
      shutil.copy(theInputPath, outputFilePath)
      makeModDatesMatch(theInputPath, outputFilePath)
      os.utime(file_path, (timestamp, timestamp))
    filesCopied[str(theInputPath)] = (str(outputFilePath), str(outputFilePath.stat().st_mtime))
  else:
    for item in theInputPath.iterdir():
      copyFiles(item, outputFilePath)
copyFiles(args["input"], args["output"])

# Report the input filenames, with current update timestamp, back to the calling script.
for fileCopied in filesCopied:  
  print(fileCopied + "," + filesCopied[fileCopied][1], flush=True, file=sys.stdout)
print("---", flush=True, file=sys.stdout)
# Report the output filenames back to the calling script.
for fileCopied in filesCopied:
  print(filesCopied[filesCopied][0], flush=True, file=sys.stdout)
