# Standard libraries.
import os
import sys
import pathlib
import argparse
import subprocess

# The Pillow bitmap-image-handling library.
import PIL

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Process the given folder and turn any images files (PNG, SVG), videos (MP4) or presentations (PPTX) into a slideshow (a folder containing index.html and a set of normalised assets).")).parse_args())

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(__file__, args["scriptTimestamp"], args["verbose"])

# Process individual files. If the input given is a folder, recurse into that folder and process any files (or sub-folders) found.
slideCount = 1
filesProcessed = {}
def processFiles(theInputPath, theOutputPath):
    global slideCount
    
    if theInputPath.is_file():
        outputPath = theOutputPath
        if theOutputPath.name == "slideshow":
            outputPath = theOutputPath.parent
        inputPathStr = str(theInputPath)
        inputPathStat = theInputPath.stat()
        inputPathSuffix = theInputPath.suffix.lower()
        # Handle any bitmap image, converting it to a PNG file.
        if inputPathSuffix in officeToMarkdownLib.bitmapSuffixes:
            outputFilePath = outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".png")
            if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
                with PIL.Image.open(theInputPath) as img:
                    # Ensure image is RGB if converting formats that don't support alpha/transparency
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(outputFilePath)
                    os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
                officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow - " + officeToMarkdownLib.prePadWithSpaces(inputPathSuffix, 7) + ": " + inputPathStr + " to " + str(outputFilePath))
            filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
            slideCount = slideCount + 1
        elif inputPathSuffix in [".pptx"]:
            if scriptUpdated or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
                # Try standard command; adjust executable name if on Windows/macOS if needed.
                libreofficeExec = "soffice" if sys.platform != "win32" else "libreoffice"
                libreofficeCmd = [libreofficeExec, "--headless", "--convert-to", "pdf", "--outdir", str(outputPath, inputPathStr]
                try:
                    libreofficeResult = subprocess.run(libreofficeCmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                except FileNotFoundError:
                    raise RuntimeError("LibreOffice command line tool ('soffice' or 'libreoffice') not found in PATH.")
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"LibreOffice conversion failed:\n{e.stderr}")
                tempPDFPath = theOutputPath / pathlib.Path(theInputPath.stem) + ".pdf"
                if not tempPDFPath.exists():
                    raise FileNotFoundError("Expected intermediate PDF was not created: " + str(tempPDFPath))
        elif inputPathSuffix in officeToMarkdownLib.videoSuffixes:
            print("Video...", flush=True, file=sys.stderr)
    else:
        officeToMarkdownLib.ifVerbose(args["verbose"], "ProcessSlideshow -  folder: " + str(theInputPath))
        outputFolderPath = theOutputPath / pathlib.Path(theInputPath.name)
        for item in theInputPath.iterdir():
            processFiles(item, outputFolderPath)
processFiles(args["input"], args["output"])

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
officeToMarkdownLib.printFilesProcessed(filesProcessed)

sys.exit(0)






# Check through items in the given input folder, recursing into sub-folders.
# Produces an array (in the global "slides" variable) containing tuples of file names and an array of extensions found.
slides = {}
inputFolder = docsToMarkdownLib.normalisePath(args["input"])
def listFileNames(theSubFolder):
    global inputFolder
    global slides
    
    inputPath = inputFolder + os.sep + theSubFolder
    for inputItem in sorted(os.listdir(inputPath)):
        if os.path.isdir(docsToMarkdownLib.normalisePath(inputPath + os.sep + inputItem)):
            listFileNames(docsToMarkdownLib.normalisePath(theSubFolder + os.sep + inputItem))
        else:
            fileType = ""
            fileSplit = inputItem.rsplit(".", 1)
            fileName = fileSplit[0]
            if not theSubFolder == "":
                fileName = theSubFolder + os.sep + fileName
            if len(fileSplit) == 2:
                fileType = fileSplit[1]
            if not fileName in slides.keys():
                slides[fileName] = []
            slides[fileName].append(fileType)
listFileNames("")
print("List of slides:")
print(slides)

config = []
# Check through the files found above to see if the special "config" file is found anywhere, and if so deal with it and remove it from the list.
for slide in slides:
    if slide.lower() == "config" or slide.lower().endswith("/config"):
        for fileType in slides.pop(slide):
            fullPath = slide + "." + fileType
            if fileType.lower() in ["xls", "xlsx", "csv"]:
                print("Config file found: " + fullPath, flush=True)
                docsToMarkdownLib.processArgsFile(fullPath, defaultArgs=args)

itemsList = []
# Check through the files found above to see if the special "items" file is found anywhere, and if so deal with it and remove it from the list.
for slide in slides:
    if slide.lower() == "items" or slide.lower().endswith("/items"):
        for fileType in slides.pop(slide):
            fullPath = slide + "." + fileType
            if fileType.lower() in ["xls", "xlsx", "csv"]:
                print("Items file found: " + fullPath, flush=True)
                if fileType.lower() in ["xls", "xlsx"]:
                    itemsSheet = pandas.read_excel(fullPath)
                else:
                    itemsSheet = pandas.read_csv(fullPath)
                # Convert the Pandas dataframe to an array of dicts, lowercasing all the keys and replacing all "NaN" values with empty string.
                for itemsIndex, itemsRow in itemsSheet.iterrows():
                    newItem = {}
                    for colName in itemsRow.keys():
                        if pandas.isna(itemsRow[colName]):
                            newItem[colName.lower()] = ""
                        else:
                            newItem[colName.lower()] = itemsRow[colName]
                    itemsList.append(newItem)

slideCount = 1
slideList = []
for slide in slides:
    for fileType in slides[slide]:
        # We add a timestamp string to each filename so that the browser reloads images / videos.
        fileName = str(slideCount) + "-" + str(timestamp)
        inputFile = inputFolder + os.sep + slide + "." + fileType
        if fileType in docsToMarkdownLib.bitmapTypes:
            SVGContent = docsToMarkdownLib.embedBitmapInSVG(inputFile, args["width"], args["height"])
            docsToMarkdownLib.putFile(args["output"] + os.sep + fileName + ".svg", SVGContent)
            slideList.append(fileName + ".svg")
        elif doProcessVideo and fileType in docsToMarkdownLib.videoTypes:
            docsToMarkdownLib.thumbnailVideo(inputFile, args["output"] + os.sep + fileName + ".mp4", args["width"], args["height"])
            slideList.append(fileName + ".mp4")
        else:
            outputFile = args["output"] + os.sep + fileName + "." + fileType.lower()
            print("Copying unprocessed file: " + inputFile + " to " + outputFile)
            shutil.copyfile(inputFile, outputFile)
            slideList.append(fileName + "." + fileType.lower())
        slideCount = slideCount + 1

docsToMarkdownLib.putFile(args["output"] + os.sep + "index.html", docsToMarkdownLib.getFile("slideshow/slideshowIndex.html").replace("var resources = [];", str("var resources = " + str(slideList) + ";")).replace("<<TIMESTAMP>>",str(timestamp)).replace("<<DATETIMEFORMATTED>>",dateTimeFormatted).replace("\'", "\""))
