import os
import sys
import pathlib
import subprocess

# Our own Docs To Markdown library.
import officeToMarkdownLib

# Parse and normalise the command-line arguments.
args = officeToMarkdownLib.processCommandLineArgs(defaultArgs={"scriptRoot":str(pathlib.Path.cwd()), "verbose":"false", "validFrontMatterFields":""}, requiredArgs=["scriptTimestamp","inputPath","inputTimestamp","outputPath"], optionalArgs=["scriptRoot", "verbose"])
args["verbose"] = args["verbose"].lower()
inputPath = pathlib.Path(args["inputPath"])
outputPath = pathlib.Path(args["outputPath"])

for inputItem in inputPath.iterdir():
  if inputItem.suffix in [".docx", ".doc"]:
    # Deal with a DOCX / DOC file - pass it up to the processDOCFile script to deal with.
    commandLine = [scriptExec, scriptPath, "--verbose", args["verbose"], "--scriptTimestamp", str(scriptTimestamp), "--inputPath", inputItem, "--inputTimestamp", str(inputTimestamp), "--outputPath", outputItem]
    officeToMarkdownLib.ifVerbose(args["verbose"], "processFAQ       - running: " + " ".join(commandLine))
    commandLineResult = subprocess.run(commandLine, capture_output=True, text=True)
    for outputFile in commandLineResult.stdout.split("\n"):
      outputFile = outputFile.strip()
      if not outputFile == "":
        print(outputFile, flush=True, file=sys.stdout)
      if args["verbose"] == "true":
        stderrOutput = commandLineResult.stderr.strip()
        if not stderrOutput == "":
          print(stderrOutput, flush=True, file=sys.stderr)
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
