import os
import sys

# Our own Docs To Markdown library.
import docsToMarkdownLib

inputFolder = sys.argv[1]
outputFolder = sys.argv[2]

def processPage(thePageFolder):
    for inputItem in os.listdir(thePageFolder):
        print("STATUS: Processing Yearbook page: " + thePageFolder)
    
    sys.exit(0)
    if inputItem.rsplit(".", 1)[1].lower() in ["docx", "doc"]:
        outputItem = inputItem.rsplit(".", 1)[0] + ".md"
        if not docsToMarkdownLib.checkModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem):
            print("STATUS: Processing Yearbook page: " + inputFolder + os.sep + inputItem + " to " + outputFolder + os.sep + outputItem)
            docMarkdown, docFrontmatter = docsToMarkdownLib.docToMarkdown(inputFolder + os.sep + inputItem)
            trimmedMarkdown = ""
            for markdownLine in docMarkdown.split("\n"):
                if markdownLine.startswith("# ") and not "title" in docFrontmatter.keys():
                    docFrontmatter["title"] = markdownLine[2:].lstrip()
                else:
                    trimmedMarkdown = trimmedMarkdown + markdownLine + "\n"
            docsToMarkdownLib.putFile(outputFolder + os.sep + outputItem, docsToMarkdownLib.frontMatterToString(docFrontmatter) + trimmedMarkdown.strip())
            docsToMarkdownLib.makeModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem)
    elif inputItem.rsplit(".", 1)[1].lower() in ["mp4"]:
        # Use FFmpeg to set the size and format of any FAQ videos.
        outputItem = inputItem.rsplit(".", 1)[0] + ".webm"
        if not docsToMarkdownLib.checkModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem):
            print("STATUS: Processing FAQ video: " + inputFolder + os.sep + inputItem + " to " + outputFolder + os.sep + outputItem)
            
            # Figure out the video's dimensions.
            videoDimensions = os.popen("ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x " + inputFolder + os.sep + inputItem).read().strip()
            videoWidth = int(videoDimensions.split("x")[0])
            videoHeight = int(videoDimensions.split("x")[1])
            
            # Crop the video to a square, centred in the middle, then scale the dimensions to 240x240.
            # Also, normalise the audio - see: http://johnriselvato.com/ffmpeg-how-to-normalize-audio/
            os.system("ffmpeg -i " + inputFolder + os.sep + inputItem + " -filter:v crop=" + str(videoHeight) + ":" + str(videoHeight) + ":" + str(int((videoWidth - videoHeight) / 2)) + ":0,scale=240:240,setsar=1 -filter:a loudnorm=I=-16:LRA=11:TP=-1.5 /tmp/faq.webm > /dev/null 2>&1")
            os.system("mv /tmp/faq.webm " + outputFolder + os.sep + outputItem)
            
            docsToMarkdownLib.makeModDatesMatch(inputFolder + os.sep + inputItem, outputFolder + os.sep + outputItem)


print("STATUS: processYearbook: " + inputFolder + " to " + outputFolder)
for page in os.listdir(inputFolder):
    if os.path.isdir(inputFolder + os.sep + inputItem):
        processPage(inputItem)
