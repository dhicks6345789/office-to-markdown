import os
import sys
import pathlib
import subprocess

# Our own Office To Markdown library.
import officeToMarkdownLib

# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "verbose":"false", "validFrontMatterFields":""}, requiredArgs=["scriptTimestamp","inputPath","outputPath"], optionalArgs=["scriptRoot", "verbose"])
args["verbose"] = args["verbose"].lower()
inputPath = pathlib.Path(args["inputPath"])
outputPath = pathlib.Path(args["outputPath"])
outputFilePaths = []

# Read the list of input files with last-modified timestamps from stdin...
previousInputChanges = {}
for line in sys.stdin:
  if not line.strip() == "":
    lineSplit = line.strip().split(",")
    previousInputChanges[lineSplit[0]] = lineSplit[1]
# ...and read the current input file modification times to compare those with.
currentInputChanges = officeToMarkdownLib.getFolderChangeDetails(args["inputPath"])

for inputItem in inputPath.iterdir():
  if inputItem.suffix in [".docx", ".doc"]:
    outputFilePath = outputPath / pathlib.Path(inputItem.stem + ".md")
    outputFilePaths.append(outputFilePath)
    doTransform = False
    if not officeToMarkdownLib.checkTimestampsMatch(args["scriptTimestamp"], pathlib.Path(__file__)):
      doTransform = True
    elif (not str(inputItem) in previousInputChanges) or (not previousInputChanges[str(inputItem)] == currentInputChanges[str(inputItem)]):
      doTransform = True
    if doTransform:
      officeToMarkdownLib.ifVerbose(args["verbose"], "processFAQ       - " + inputItem.suffix + "  : " + str(inputItem) + " to " + str(outputFilePath))
      docMarkdown, docFrontmatter = officeToMarkdownLib.docToMarkdown(inputItem)
  
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
      officeToMarkdownLib.makeModDatesMatch(inputPath, outputFilePath)
    #elif fileType in ["MP4"]:
        ## Deal with an MP4 file - use FFmpeg to set the size and format of any videos in this FAQ.
        #outputItem = inputItem.rsplit(".", 1)[0] + ".webm"
        ## Video files can take time / processing power to deal with, so we check we actually need to update something first before going ahead.
        #if not officeToMarkdownLib.checkModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem):
            #print("STATUS: Processing FAQ video: " + inputFolder + os.sep + inputItem + " to " + outputFolder + os.sep + outputItem, flush=True)
            
            ## Figure out the video's dimensions.
            #videoDimensions = os.popen("ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x " + inputFolder + os.sep + inputItem).read().strip()
            #videoWidth = int(videoDimensions.split("x")[0])
            #videoHeight = int(videoDimensions.split("x")[1])
            
            ## Crop the video to a square, centred in the middle, then scale the dimensions to 240x240.
            ## Also, normalise the audio - see: http://johnriselvato.com/ffmpeg-how-to-normalize-audio/
            #os.system("ffmpeg -i " + inputFolder + os.sep + inputItem + " -filter:v crop=" + str(videoHeight) + ":" + str(videoHeight) + ":" + str(int((videoWidth - videoHeight) / 2)) + ":0,scale=240:240,setsar=1 -filter:a loudnorm=I=-16:LRA=11:TP=-1.5 /tmp/faq.webm > /dev/null 2>&1")
            #os.system("mv /tmp/faq.webm " + outputFolder + os.sep + outputItem)
            
            #officeToMarkdownLib.makeModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem)



# We expect the output (on stdout) from a sub-script to be a list of input file filename,timestamp pairs, then a "---", then a list of output files.
for item in currentInputChanges:
  print(item + "," + currentInputChanges[item])
print("---")
for item in outputFilePaths:
  print(item)
