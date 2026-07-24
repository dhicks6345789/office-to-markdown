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

# The Slugify library for making URL-safe strings.
import slugify

# Our own Office To Markdown library.
import officeToMarkdownLib



# Parse command-line arguments.
args = vars(officeToMarkdownLib.setArgsForSubScript(argparse.ArgumentParser(description=(
    "Process the given folder and add any files found into a slideshow (a folder containing index.html and a set of normalised assets). Some files will "
    "be normalised: bitmap images (" + ", ".join(officeToMarkdownLib.bitmapSuffixes) + ") will be converted to PNG, "
    "videos (" + ", ".join(officeToMarkdownLib.bitmapSuffixes) + ") will be convert3d to MP4, "
    "PowerPoint files (.PPTX) will be converted to a set of PNG images. All other files at the top folder level will be copied bvut renamed as slides, "
    "sub-folders and their files will simply be copied unchanged."
))).parse_args())

# Pick up any additional arguments from a config file if present.
args.update(officeToMarkdownLib.processArgsFile(args["input"], defaultArgs={"width":1024, "height":768}))

# The calling script provides a list of any input files, along with last-modified timestamps, via stdin as simple set of comma-separated "filename,timestamp" values.
previousInputFileTimestamps = officeToMarkdownLib.readInputFilesAndTimestamps()

# If this script itself (or associated additional resource or config file) has been updated we re-run the operation, just to make sure all output is up to date.
scriptUpdatedFiles = generateScriptUpdatedFilesList(args["input"], args["verbose"])
scriptUpdatedFiles.append(__file__.replace("processSlideshow.py", "slideshowIndex.html"))
scriptUpdated = officeToMarkdownLib.checkIfScriptUpdated(previousInputFileTimestamps, scriptUpdatedFiles, args["verbose"])

# A message for the user.
officeToMarkdownLib.ifVerbose(args["verbose"], "ProcessSlideshow -  folder: " + str(args["input"]))

outputPath = args["output"]
if outputPath.name == "slideshow":
    outputPath = outputPath.parent
outputPath = pathlib.Path("static") / outputPath

slideCount = 1
slideList = []
filesProcessed = {}

# Recursivly copy the contents of the input folder to the output folder. Replicates last-modified times on files.
# Note: shutil's copy2 function fails on rclone-mounted volumes (Google Drive, etc) which don't implement all metadata
# features (chmod / chown permissions in particular), hence we use shutil.copy and set the last-modified attribute
# separatly. We also add each item to the fileProcessed dict.
def copyFolder(theInputPath, theOutputPath):
    theOutputPath.mkdir(parents=True, exist_ok=True)
    for item in theInputPath.iterdir():
        if item.is_file():
            outputFilePath = args["outputRoot"] / theOutputPath / pathlib.Path(item.name)
            itemStr = str(item)
            itemStat = item.stat()
            if scriptUpdated or (not outputFilePath.is_file()) or (not itemStr in previousInputFileTimestamps) or (not str(itemStat.st_mtime) == previousInputFileTimestamps[itemStr]):
                officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow -    copy: " + itemStr + " to " + str(outputFilePath))
                shutil.copy(item, outputFilePath)
                os.utime(outputFilePath, (itemStat.st_atime, itemStat.st_mtime))
            filesProcessed[itemStr] = (str(outputFilePath), str(itemStat.st_mtime))
        else:
            copyFolder(item, args["outputRoot"] / theOutputPath / pathlib.Path(slugify.slugify(item.name)))

for inputPath in args["input"].iterdir():
    (args["outputRoot"] / outputPath).mkdir(parents=True, exist_ok=True)
    inputPathStr = str(inputPath)
    inputPathStat = inputPath.stat()
    inputPathSuffix = inputPath.suffix.lower()
    # Handle any sub-folders - simply copy them, maintaining permissions and adding them to the output items list.
    if inputPath.is_dir():
        copyFolder(inputPath, args["outputRoot"] / outputPath / pathlib.Path(slugify.slugify(inputPath.name)))
    # Handle any bitmap image, converting it to a PNG file.
    elif inputPathSuffix in officeToMarkdownLib.bitmapSuffixes:
        outputFilePath = args["outputRoot"] / outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".png")
        slideList.append(outputFilePath.name)
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
            outputFilePath = args["outputRoot"] / outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".png")
            slideList.append(outputFilePath.name)
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
        outputFilePath = args["outputRoot"] / outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + ".mp4")
        slideList.append(outputFilePath.name)
        if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
            officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow -   video: " + str(inputPath) + " to " + str(outputFilePath))
            (args["outputRoot"] / outputPath).mkdir(parents=True, exist_ok=True)
            officeToMarkdownLib.thumbnailVideo(inputPath, outputFilePath, args["width"], args["height"])
            os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
        filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
        slideCount = slideCount + 1
    elif inputPath.name.lower() in officeToMarkdownLib.configFileNames:
        filesProcessed[inputPathStr] = (str(args["outputRoot"]), str(inputPathStat.st_mtime))
    # Handle any other file type - simply copy the original file, but with a rename to "slide-xxxxxx".
    else:
        outputFilePath = args["outputRoot"] / outputPath / pathlib.Path("slide-" + officeToMarkdownLib.padInt(slideCount, 5) + inputPathSuffix)
        slideList.append(outputFilePath.name)
        if scriptUpdated or (not outputFilePath.is_file()) or (not inputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[inputPathStr]):
            officeToMarkdownLib.ifVerbose(args["verbose"], "processSlideshow -    copy: " + str(inputPath) + " to " + str(outputFilePath))
            (args["outputRoot"] / outputPath).mkdir(parents=True, exist_ok=True)
            shutil.copy(inputPath, outputFilePath)
            os.utime(outputFilePath, (inputPathStat.st_atime, inputPathStat.st_mtime))
        filesProcessed[inputPathStr] = (str(outputFilePath), str(inputPathStat.st_mtime))
        slideCount = slideCount + 1

# Copy the "index.html" single-page, self-contained slideshow viewer to the output folder, adding in a list of the slides generated.
indexFileInputPath = pathlib.Path.cwd() / pathlib.Path("slideshow/slideshowIndex.html")
indexFileInputPathStr = str(indexFileInputPath)
indexFileInputPathStat = indexFileInputPath.stat()
indexFileOutputPath = args["outputRoot"] / outputPath / pathlib.Path("index.html")
if scriptUpdated or (not indexFileOutputPath.is_file()) or (not indexFileInputPathStr in previousInputFileTimestamps) or (not str(inputPathStat.st_mtime) == previousInputFileTimestamps[indexFileInputPathStr]):
    officeToMarkdownLib.putFile(indexFileOutputPath, officeToMarkdownLib.getFile(indexFileInputPath).replace("var resources = [];", str("var resources = " + str(slideList) + ";")))
filesProcessed[indexFileInputPathStr] = (str(indexFileOutputPath), str(indexFileInputPathStat.st_mtime))

# Report the input filenames, with current update timestamp, back to the calling script, along with the output filenames.
officeToMarkdownLib.printFilesProcessed(filesProcessed)

sys.exit(0)








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
            
docsToMarkdownLib.putFile(args["output"] + os.sep + "index.html", docsToMarkdownLib.getFile("slideshow/slideshowIndex.html").replace("var resources = [];", str("var resources = " + str(slideList) + ";")).replace("<<TIMESTAMP>>",str(timestamp)).replace("<<DATETIMEFORMATTED>>",dateTimeFormatted).replace("\'", "\""))
