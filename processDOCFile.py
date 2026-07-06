# Convert a DOCX / DOC (Word, Google Docs, etc) file to Markdown.
# Designed to be called from the scanFolders script, so takes a very simple command line parameter list.

# Standard libraries.
#import os
import sys
import pathlib

# Our own Docs To Markdown library.
import officeToMarkdownLib


# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "dataRoot":str(pathlib.Path.cwd()), "verbose":"false", "validFrontMatterFields":""}, requiredArgs=["inputPath","inputTimestamp","outputPath","outputTimestamp"], optionalArgs=["scriptRoot", "dataRoot", "verbose"])
args["dataRoot"] = officeToMarkdownLib.normalisePath(args["dataRoot"])
args["verbose"] = args["verbose"].lower()
inputPath = pathlib.Path(args["input"])
outputPath = pathlib.Path(args["output"])

# Check we are trying to convert a DOCX / DOC file.
if inputPath.suffix() in ["DOCX", "DOC"]:
  # We are passed the output /folder/, so we have to figure out the output file name from the input file name.
  outputFilePath = outputPath / outputPath.name
  
  # Report the output filename to the calling script.
  print(outputFilePath, flush=True, file=sys.stdout))
  
  # Check and see if we already have an output file that matches the modification times of the input, if so, skip - no
  # point processing the same file for the same output.
  if not officeToMarkdownLib.checkModDatesMatch(inputFile, outputPath):
    print("Processing " + docType + " file: " + inputFile + " to " + outputPath, flush=True, file=sys.stderr)

    # Our library "function" here calls Pandoc to do the conversion.
    docMarkdown, docFrontmatter = officeToMarkdownLib.docToMarkdown(inputFile)

    # If we don't already have a "title" front matter variable, go through the Markdown line by line,
    # checking for the first defined title string that we can use as a title.
    trimmedMarkdown = ""
    for markdownLine in docMarkdown.split("\n"):
      if markdownLine.startswith("# ") and not "title" in docFrontmatter.keys():
        docFrontmatter["title"] = markdownLine[2:].lstrip()
      else:
        trimmedMarkdown = trimmedMarkdown + markdownLine + "\n"

    # Write out the Markdown file, matching the modification date with the original input document so we can skip next time if the input is unmodified.
    officeToMarkdownLib.putFile(outputPath, officeToMarkdownLib.frontMatterToString(docFrontmatter) + trimmedMarkdown.strip())
    officeToMarkdownLib.makeModDatesMatch(inputFile, outputPath)
