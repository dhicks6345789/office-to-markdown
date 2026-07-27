# Standard libraries.
import os
import sys
import pathlib
import argparse

# The Slugify library for making URL-safe strings.
import slugify

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Process the given DOCX input file into a matching Markdown file in the output folder. If a directory is given as the input it will process all DOCX files in the folder, recursing into any sub-folders found.")).parse_args())

# Pick up any additional arguments from a config file if present.
args.update(officeToMarkdownLib.processArgsFile(args["input"], defaultArgs={}))

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself (or associated additional resource or config file) has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdatedFiles = officeToMarkdownLib.generateScriptUpdatedFilesList(args["input"], args["verbose"])
scriptUpdatedFiles.append(__file__)
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(previousInputFileTimestamps, scriptUpdatedFiles, args["verbose"])

# Process individual DOCX files into Markdown. If the input given is a folder, recurse into that folder and process any files (or sub-folders) found.
filesProcessed = {}
def processFiles(theInputPath, theOutputPath):
  if theInputPath.is_file():
    inputPathStr = str(theInputPath)
    inputPathStat = theInputPath.stat()
    inputPathSuffix = theInputPath.suffix.lower()
    if inputPathSuffix in [".docx"]:
      #outputFilePath = args["outputRoot"] / theOutputPath / pathlib.Path(theInputPath.stem + ".md")
      outputFilePath = args["outputRoot"] / pathlib.Path(slugify.slugify(str(theOutputPath.with_suffix("").parent)) + os.sep + theInputPath.stem + ".md")
      if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
        officeToMarkdownLib.ifVerbose(args["verbose"], "processDOCFile   -   " + inputPathSuffix + ": " + inputPathStr + " to " + str(outputFilePath))
        officeToMarkdownLib.ifVerbose(args["verbose"], pathlib.Path(slugify.slugify(str(theOutputPath.with_suffix("").parent))))
        
        # We use our library function to convert from DOCX to Markdown.
        docMarkdown, docFrontmatter = officeToMarkdownLib.docToMarkdown(theInputPath)
        
        # If we don't already have a "title" front matter variable, go through the Markdown line by line,
        # checking for the first defined title string that we can use as a title.
        trimmedMarkdown = ""
        for markdownLine in docMarkdown.split("\n"):
          if markdownLine.startswith("# ") and not "title" in docFrontmatter.keys():
            docFrontmatter["title"] = markdownLine[2:].lstrip()
          else:
            trimmedMarkdown = trimmedMarkdown + markdownLine + "\n"
          
        # Write out the Markdown file, matching the modification date with the original input document so we can skip next time if the input is unmodified.
        officeToMarkdownLib.putFile(outputFilePath, officeToMarkdownLib.frontMatterToString(docFrontmatter) + trimmedMarkdown.strip())
        os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
      filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
  else:
    outputFolderPath = theOutputPath / pathlib.Path(theInputPath.name)
    for item in theInputPath.iterdir():
      processFiles(item, outputFolderPath)
processFiles(args["input"], pathlib.Path("content") / args["output"])

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
officeToMarkdownLib.printFilesProcessed(filesProcessed)
