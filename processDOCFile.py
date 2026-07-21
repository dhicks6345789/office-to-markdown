# Standard libraries.
import os
import sys
import shutil
import pathlib
import argparse

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Process the given DOCX input file into a matching Markdown file in the output folder. If a directory is given as the input it will process all DOCX files in the folder, recursing into any sub-folders found.")).parse_args())

# The calling script provides a list of any input files, along with file update timestamps, via stdin.
previousInputFileTimestamps = {}
for line in sys.stdin:
  lineSplit = line.strip().split(",")
  previousInputFileTimestamps[lineSplit[0]] = lineSplit[1]

# Check we are trying to convert a DOCX / DOC file.
if args["input"].suffix.lower() in [".docx", ".doc"]:
  # Figure ut the last-modified time of the input file.
  inputFileTimestamp = str(args["input"].stat().st_mtime)
  
  # We are passed the output /folder/, so we have to figure out the output file name from the input file name.
  outputFilePath = args["output"] / pathlib.Path(args["input"].stem + ".md")
  
  # Report the input filename, with current update timestamp, back to the calling script.
  print(str(args["input"]) + "," + inputFileTimestamp, flush=True, file=sys.stdout)
  print("---", flush=True, file=sys.stdout)
  # Report the output filename back to the calling script.
  print(outputFilePath, flush=True, file=sys.stdout)

  # Check and see if either the input file or the script itself have changed since the last
  # run - there's no point doing any work if neither have changed.
  doTransform = False
  if not officeToMarkdownLib.checkTimestampsMatch(args["scriptTimestamp"], pathlib.Path(__file__)):
    doTransform = True
  elif (not str(args["input"]) in previousInputFileTimestamps) or (not str(args["input"].stat().st_mtime) == previousInputFileTimestamps[str(args["input"])]):
    doTransform = True
  if doTransform:
    officeToMarkdownLib.ifVerbose(args["verbose"], "processDOCFile   -   " + args["input"].suffix + ": " + str(args["input"]) + " to " + str(outputFilePath))

    # We use our library function to convert from DOCX to Markdown.
    docMarkdown, docFrontmatter = officeToMarkdownLib.docToMarkdown(args["input"])

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
    officeToMarkdownLib.makeModDatesMatch(args["input"], outputFilePath)
