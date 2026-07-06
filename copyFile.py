# Convert a DOCX / DOC (Word, Google Docs, etc) file to Markdown.
# Designed to be called from the scanFolders script, so takes a very simple command line parameter list.

# Standard libraries.
import os
import sys
import shutil

# Our own Docs To Markdown library.
import docsToMarkdownLib

# Usage: copyFile.py inputFile outputFolder
inputFile = sys.argv[1]
outputFolder = sys.argv[2]

# We are passed the output /folder/, so we have to figure out the output file name from the input file name.
outputFile = inputFile
if os.sep in outputFile:
  outputFile = outputFile.rsplit(os.sep, 1)[1]
outputPath = outputFolder + os.sep + outputFile

# Log the name of the file we are going to write to.
docsToMarkdownLib.addToWriteLog(outputPath)
  
# Check and see if we already have an output file that matches the modification
# times of the input, if so, skip - no point copying the same file.
if not docsToMarkdownLib.checkModDatesMatch(inputFile, outputPath):
  print("Copying file: " + inputFile + " to " + outputPath, flush=True)
  shutil.copyfile(inputFile, outputPath)
  docsToMarkdownLib.makeModDatesMatch(inputFile, outputPath)
