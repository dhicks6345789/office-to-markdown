# Standard libraries.
import os
import sys
import shutil
import pathlib
import argparse

# The Slugify library for making URL-safe strings.
import slugify

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Copy either individual files or whole folders of files, recursing into any sub-folders found.")).parse_args())

# Pick up any additional arguments from a config file if present.
args.update(officeToMarkdownLib.processArgsFile(args["input"], defaultArgs={}))

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself (or associated additional resource or config file) has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdatedFiles = officeToMarkdownLib.generateScriptUpdatedFilesList(args["input"], args["verbose"])
scriptUpdatedFiles.append(__file__)
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(previousInputFileTimestamps, scriptUpdatedFiles, args["verbose"])

# Copy individual files. If the input given is a folder, recurse into that folder and copy any files (or sub-folders) found.
filesProcessed = {}
def copyFiles(theInputPath, theOutputPath):
  if theInputPath.is_file():
    outputFilePath = args["outputRoot"] / theOutputPath / theInputPath.name
    inputPathStr = str(theInputPath)
    inputPathStat = theInputPath.stat()
    if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
      officeToMarkdownLib.printIfVerbose(args["verbose"], "copyFile         - copying: " + str(theInputPath) + " to " + str(outputFilePath))
      outputFilePath.parent.mkdir(parents=True, exist_ok=True)
      # Note: shutil's copy2 function does preserve file attributes, but breaks on some cloud filesystems (e.g. Google Drive) mounted as volumes by rclone as copy2 tries to copy
      # over chmod / chown attributes, which aren't supported and the operation fails. Instead, we copy the file and copy over just the last-modified attribute instead.
      shutil.copy(theInputPath, outputFilePath)
      os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
    filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
  else:
    outputFolderPath = theOutputPath / pathlib.Path(slugify.slugify(theInputPath.name))
    for item in theInputPath.iterdir():
      copyFiles(item, outputFolderPath)
copyFiles(args["input"], pathlib.Path("content") / args["output"])

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
officeToMarkdownLib.printIfVerbose(args["verbose"], str(filesProcessed))
officeToMarkdownLib.printFilesProcessed(filesProcessed)
