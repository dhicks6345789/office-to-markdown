# A script to generate an HTML page showing a gallery of images.

# Standard libraries.
import os
import io
import re
import base64

# The Pillow image-handling library.
import PIL.Image

# Our own Docs To Markdown library.
import docsToMarkdownLib

# Get any arguments given via the command line.
args = docsToMarkdownLib.processCommandLineArgs(defaultArgs={}, requiredArgs=["input","output"])

print("STATUS: processStaffImages: " + args["input"] + " to " + args["output"], flush=True)

# Strips any digits, spaces or hyphens from the start and end of a filename.
def normaliseName(theName):
    result = re.sub("^[0123456789\- ]*", "", theName).strip()
    result = re.sub("[0123456789\- ]*$", "", result).strip()
    return result

# Check through items in the given input folder, recursing into sub-folders.
# Produces an array (in the global "slides" variable) containing tuples of file names and an array of extensions found.
staff = {}
inputFolder = docsToMarkdownLib.normalisePath(args["input"])
outputFile = docsToMarkdownLib.normalisePath(args["output"])
def listFileNames(theSubFolder, theHeading):
    global inputFolder
    global staff
    
    inputPath = inputFolder + os.sep + theSubFolder
    for inputItem in sorted(os.listdir(inputPath)):
        if os.path.isdir(docsToMarkdownLib.normalisePath(inputPath + os.sep + inputItem)):
            listFileNames(docsToMarkdownLib.normalisePath(theSubFolder + os.sep + inputItem), normaliseName(inputItem))
        else:
            if inputItem.lower().endswith(".jpg") or inputItem.lower().endswith(".png"):
                staffName = normaliseName(inputItem[:-4])
                staff[staffName] = (theSubFolder + os.sep + inputItem, theHeading)
listFileNames("", "")

# Load the template HTML for the image and heading rows.
staffRowTemplate = docsToMarkdownLib.getFile("staffRowTemplate.html")
staffHeadingTemplate = docsToMarkdownLib.getFile("staffHeadingTemplate.html")

# Step through the items found by the "listFileNames" function above, arranging any images found within the HTML page template.
# Add any row headings, using folder names as heading names.
rowNum = 0
# We start off ready to start a new column.
colNum = 6
rowHTML = ""
currentHeading = ""

def startNewRow():
    global rowHTML
    global colNum
    
    for pl in range(colNum, 7):
        rowHTML = rowHTML.replace("{{COL-" + str(pl) + "-IMAGETYPE}}", "image/png")
        # We use a white, 1-pixel PNG file as a blank.
        rowHTML = rowHTML.replace("{{COL-" + str(pl) + "-IMAGEDATA}}", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAMSURBVBhXY/j//z8ABf4C/qc1gYQAAAAASUVORK5CYII=")
        rowHTML = rowHTML.replace("{{COL-" + str(pl) + "-NAME}}", "<div></div>")
        
for staffMember in staff.keys():
    colNum = colNum + 1

    # New heading? Start a new row, which means adding some blanks for the rest of this row.
    if currentHeading != staff[staffMember][1]:
        startNewRow()
        currentHeading = staff[staffMember][1]
        rowNum = rowNum + 1
        rowHTML = rowHTML + staffHeadingTemplate.replace("{{ROWNUM}}", str(rowNum)) + "\n"
        rowHTML = rowHTML.replace("{{HEADINGTEXT}}", currentHeading)
        colNum = 7
    
    # Finished this row? Start a new one.
    if colNum == 7:
        colNum = 1
        rowNum = rowNum + 1
        rowHTML = rowHTML + staffRowTemplate.replace("{{ROWNUM}}", str(rowNum)) + "\n"

    # Add the image for this column. Note that image data is embeded in the HTML file as a Base64 encoded PNG, there's no external image files to worry about.
    # First, we read the image into a Pillow image object...
    origImage = PIL.Image.open(inputFolder + os.sep + staff[staffMember][0])
    # ..."thumbnail" the image, which pads it to fit the given aspect ratio...
    thumbImage = docsToMarkdownLib.thumbnailImage(origImage, 14, 14)
    # ...write the Pillow Image to an in-memory buffer as a PNG file...
    imageMembuf = io.BytesIO()
    thumbImage.save(imageMembuf, format="png")
    # ...and write that binary PNG data out as a Base64-encoded string.
    imageData = base64.b64encode(imageMembuf.getvalue())
    
    rowHTML = rowHTML.replace("{{COL-" + str(colNum) + "-IMAGETYPE}}", "image/png")
    rowHTML = rowHTML.replace("{{COL-" + str(colNum) + "-IMAGEDATA}}", imageData.decode("utf-8"))
    
    # Add any text for this image.
    rowHTML = rowHTML.replace("{{COL-" + str(colNum) + "-NAME}}", "<div>" + staffMember + "</div>")

# Clear the rest of the last row.
startNewRow()
    
staffHTML = docsToMarkdownLib.getFile("staffTemplate.html").replace("{{STAFFROWS}}", rowHTML)
docsToMarkdownLib.putFile(outputFile, staffHTML)
