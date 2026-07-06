# Convert a DOCX / DOC (Word, Google Docs, etc) file to Markdown.

# Standard Python libraries.
import sys
import pathlib

# Our own Office To Markdown library.
import officeToMarkdownLib

# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "verbose":"false", "validFrontMatterFields":""}, requiredArgs=["scriptTimestamp","inputPath","inputTimestamp","outputPath"], optionalArgs=["scriptRoot", "verbose"])
args["verbose"] = args["verbose"].lower()
inputPath = pathlib.Path(args["inputPath"])
outputPath = pathlib.Path(args["outputPath"])

# Check we are trying to convert a DOCX / DOC file.
if inputPath.suffix.lower() in [".docx", ".doc"]:
  # We are passed the output /folder/, so we have to figure out the output file name from the input file name.
  outputFilePath = outputPath / inputPath.name
  
  # Report the output filename back to the calling script.
  print(outputFilePath, flush=True, file=sys.stdout)

  # Check and see if either the input file or the script itself have changed since the last
  # run - there's no point doing any work if neither have changed.
  doTransform = False
  if not officeToMarkdownLib.checkTimestampsMatch(arg["scriptTimestamp"], pathlib.Path(__file__)):
    doTransform = True
  elif not officeToMarkdownLib.checkTimestampsMatch(args["inputTimestamp"], inputPath):
    doTransform = True
  if doTransform:
    officeToMarkdownLib.ifVerbose(args["verbose"], "processDOCFile - Processing " + docType + " file: " + str(inputFile) + " to " + str(outputPath))

    # Our library function here calls Pandoc to do the conversion.
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
    officeToMarkdownLib.putFile(outputFilePath, officeToMarkdownLib.frontMatterToString(docFrontmatter) + trimmedMarkdown.strip())
    officeToMarkdownLib.makeModDatesMatch(inputFile, outputPath)
