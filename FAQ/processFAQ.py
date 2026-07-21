# Standard libraries.
import os
import sys
import pathlib
import argparse

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Process the given input folder into an FAQ.")).parse_args())

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(__file__, args["scriptTimestamp"], args["verbose"])

# Process individual DOCX files into Markdown. If the input given is a folder, recurse into that folder and process any files (or sub-folders) found.
filesProcessed = {}
def processFiles(theInputPath, theOutputPath):
  if theInputPath.is_file():
    inputPathStr = str(theInputPath)
    inputPathStat = theInputPath.stat()
    inputPathSuffix = theInputPath.suffix.lower()
    if inputPathSuffix in [".docx"]:
      outputFilePath = theOutputPath / pathlib.Path(args["input"].stem + ".md")
      if scriptUpdated or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
        officeToMarkdownLib.ifVerbose(args["verbose"], "processFAQ       -   " + inputPathSuffix + ": " + inputPathStr + " to " + str(outputFilePath))
        
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
    # Deal with video files - use FFmpeg to convert to a common format (webm) and size.
    elif inputPathSuffix in [".mp4"]:
      outputFilePath = theOutputPath / pathlib.Path(args["input"].stem + ".webm")
      if scriptUpdated or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
        officeToMarkdownLib.ifVerbose(args["verbose"], "processFAQ       -   " + inputPathSuffix + ": " + inputPathStr + " to " + str(outputFilePath))
        ## Figure out the video's dimensions.
        #videoDimensions = os.popen("ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x " + inputFolder + os.sep + inputItem).read().strip()
        #videoWidth = int(videoDimensions.split("x")[0])
        #videoHeight = int(videoDimensions.split("x")[1])
            
        ## Crop the video to a square, centred in the middle, then scale the dimensions to 240x240.
        ## Also, normalise the audio - see: http://johnriselvato.com/ffmpeg-how-to-normalize-audio/
        #os.system("ffmpeg -i " + inputFolder + os.sep + inputItem + " -filter:v crop=" + str(videoHeight) + ":" + str(videoHeight) + ":" + str(int((videoWidth - videoHeight) / 2)) + ":0,scale=240:240,setsar=1 -filter:a loudnorm=I=-16:LRA=11:TP=-1.5 /tmp/faq.webm > /dev/null 2>&1")
        #os.system("mv /tmp/faq.webm " + outputFolder + os.sep + outputItem)
            
        #officeToMarkdownLib.makeModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem)
      filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
  else:
    officeToMarkdownLib.ifVerbose(verbose, "ProcessFAQ       -  folder: " + str(theInputPath))
    outputFolderPath = theOutputPath / pathlib.Path(theInputPath.name)
    for item in theInputPath.iterdir():
      processFiles(item, outputFolderPath)
processFiles(args["input"], args["output"])

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
officeToMarkdownLib.printFilesProcessed(filesProcessed)
