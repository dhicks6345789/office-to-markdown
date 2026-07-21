# Standard libraries.
import os
import sys
import shutil
import pathlib
import argparse

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Copy either individual files or whole folders of files, recursing into any sub-folders found.")).parse_args())

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(args["scriptTimestamp"], args["verbose"])

# Copy individual files. If the input given is a folder, recurse into that folder and copy any files (or sub-folders) found.
filesCopied = {}
def copyFiles(theInputPath, theOutputPath):
  outputFilePath = theOutputPath / theInputPath.name
  if theInputPath.is_file:
    inputPathStr = str(theInputPath)
    inputPathStat = theInputPath.stat()
    if scriptUpdated or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
      officeToMarkdownLib.ifVerbose(args["verbose"], "copyFile         - copying: " + str(theInputPath) + " to " + str(outputFilePath))
      shutil.copy(theInputPath, outputFilePath)
      os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
    filesCopied[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
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
  print(filesCopied[fileCopied][0], flush=True, file=sys.stdout)
