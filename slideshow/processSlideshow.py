# Standard libraries.
import os
import sys
import shutil
import pathlib
import argparse
import subprocess

# The Pillow bitmap-image-handling library.
import PIL

# The PDF2Image library for handling conversions from PDF to images.
import pdf2image

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description="Process the given folder and turn any images files (PNG, SVG), videos (MP4) or presentations (PPTX) into a slideshow (a folder containing index.html and a set of normalised assets).")).parse_args())

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(__file__, args["scriptTimestamp"], args["verbose"])

officeToMarkdownLib.ifVerbose(args["verbose"], "ProcessSlideshow -  folder: " + str(args["input"]))

outputPath = args["output"]
if outputPath.name == "slideshow":
    outputPath = outputPath.parent

slideCount = 1
filesProcessed = {}

# Recursivly copy the contents of the input folder to the output folder. Replicates last-modified times on files.
# Note: shutil's copy2 function fails on rclone-mounted volumes (Google Drive, etc) which don't implement all metadata
# features (chmod / chown permissions in particular), hence we use shutil.copy and set the last-modified attribute
# separatly. We also add each item to the fileProcessed dict.
def copyFolder(theInputPath, theOutputPath):
    theOutputPath.mkdir(parents=True, exist_ok=True)
    for item in theInputPath.iterdir():
        outputFilePath = theOutputPath / pathlib.Path(item.name)
        if item.is_file():
            itemStr = str(item)
            itemStat = item.stat()
            if scriptUpdated or (not outputFilePath.is_file()) or (not itemStr in previousInputFileTimestamps) or (not str(itemStat.st_mtime) == previousInputFileTimestamps[itemStr]):
                officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow -    copy: " + itemStr + " to " + str(outputFilePath))
                shutil.copy(item, outputFilePath)
                os.utime(outputFilePath, (itemStat.st_atime, itemStat.st_mtime))
            filesProcessed[itemStr] = (str(outputFilePath), str(itemStat.st_mtime))
        else:
            copyFolder(item, outputFilePath)

for inputPath in args["input"].iterdir():
    outputPath.mkdir(parents=True, exist_ok=True)
    inputPathStr = str(inputPath)
    inputPathStat = inputPath.stat()
    inputPathSuffix = inputPath.suffix.lower()
    # Handle any sub-folders - simply copy them, maintaining permissions and adding them to the output items list.
    if inputPath.is_dir():
        copyFolder(inputPath, outputPath / pathlib.Path(inputPath.name))
    # Handle any bitmap image, converting it to a PNG file.
    elif inputPathSuffix in officeToMarkdownLib.bitmapSuffixes:
        outputFilePath = outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".png")
        if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
            with PIL.Image.open(inputPath) as img:
                # Ensure image is RGB if converting formats that don't support alpha/transparency
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(outputFilePath)
                os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
            officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow - " + officeToMarkdownLib.prePadWithSpaces(inputPathSuffix, 7) + ": " + inputPathStr + " to " + str(outputFilePath))
        filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
        slideCount = slideCount + 1
    # Handle PowerPoint (PPTX) files - convert to a series of images.
    elif inputPathSuffix in [".pptx"]:
        # Use (external application) LibreOffice (this can be the headless or GUI version) to convert the PPTX file to PDF...
        libreofficeExec = "soffice" if sys.platform != "win32" else "libreoffice"
        libreofficeCmd = [libreofficeExec, "--headless", "--convert-to", "pdf", "--outdir", str(outputPath), inputPathStr]
        officeToMarkdownLib.ifVerbose(args["verbose"], "ProcessSlideshow - running: " + " ".join([f"{value}" for value in libreofficeCmd]))
        try:
            libreofficeResult = subprocess.run(libreofficeCmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            raise RuntimeError("LibreOffice command line tool ('soffice' or 'libreoffice') not found in PATH.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LibreOffice conversion failed:\n{e.stderr}")
        tempPDFPath = outputPath / pathlib.Path(inputPath.stem + ".pdf")
        if not tempPDFPath.exists():
            raise FileNotFoundError("Expected intermediate PDF was not created: " + str(tempPDFPath))

        # ...then render PDF pages as individual PNG images using the pdf2image Python library.
        slideshowImages = pdf2image.convert_from_path(str(tempPDFPath), dpi=300)
        slideshowOutputs = []
        for slideshowImage in slideshowImages:
            outputFilePath = outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".png")
            if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
                officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow - " + officeToMarkdownLib.prePadWithSpaces(inputPathSuffix, 7) + ": " + inputPathStr + " to " + str(outputFilePath))
                slideshowImage.save(outputFilePath)
                os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
            slideshowOutputs.append(str(outputFilePath))
            slideCount = slideCount + 1
        filesProcessed[inputPathStr] = (slideshowOutputs, str(inputPathStat.st_mtime))

        # Cleanup intermediate PDF file.
        if tempPDFPath.exists():
            tempPDFPath.unlink()
    # Handle video files - use FFMpeg to convert to a common format before saving to the destination.
    elif inputPathSuffix in officeToMarkdownLib.videoSuffixes:
        print("Video...", flush=True, file=sys.stderr)
    # Handle any other file type - simply copy the original file, but with a rename to "slide-xxxxxx".
    else:
        outputFilePath = outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + inputPathSuffix)
        if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
            officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow -    copy: " + str(inputPath) + " to " + str(outputFilePath))
            outputPath.mkdir(parents=True, exist_ok=True)
            shutil.copy(inputPath, outputFilePath)
            os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
        filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
        slideCount = slideCount + 1

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
