# Office To Markdown
A collection of scripts to pre-process folders of content, often in common Office formats (DOCX, XLSX, PPTX, etc) into a form ready for further processing with common static site generation tools ([Hugo](https://gohugo.io/), [Jekyll](https://jekyllrb.com/), [Eleventy](https://www.11ty.dev/), etc).

The "scanFolders.py" Python script acts as an overall starting point, triggering other scripts to run conversions on a folder tree containing various content. Each script should also be able to be used as a stand-alone application should you want.

## Quickstart
Download / clone the Git repository. These scripts are written in Python 3 and, as such, should be cross-platform. On Linux, there's a Bash script that will set up and activate a Python venv to run the script:

```
bash scanFolders.sh --input ~/Documents/www --output ~/.cache/Hugo --verbose
```

## Requirements
There's a Python requirements.txt file that should be installed into a Python venv (handled by the helper Bash script above if you use that).

The scripts used for each item might have further individual requirements, possibly including supporting applications (such as ffmpeg to handle videos), see the relevant script's documentation for details.

The scripts are intended to be run over a simple folder tree. They should work with pretty much anything that looks to the operating system like a local tree of folders, so if you have a utility that maps a cloud-based file system of some kind to a local path (say you're using one of the Windows Google Drive / OneDrive / Dropbox clients) you should be able to run the scripts on that path (either as input or output location) in the same way. In this way, you can set up a content publishing pipeline that allows your users to edit content directly in their usual Office editor (desktop Microsoft Word, Office 365 Word, Google Docs, Libre Office, etc) and publish directly to a website.

If you're on a Linux or MacOS system (or Windows), we can recommend [rclone](https://rclone.org/) as being an excellent way of mounting / cloning over 50 cloud provider's filesystems as a local filesystem.

## Usage
You are probably best off running the scanFolders.sh script, which sets up the Python environment (venv and environment settings variables) before passing any arguments to the scanFolders.py script.

`scanFolders.py [-h] [--input INPUT] [--output OUTPUT] [--scriptRoot SCRIPTROOT] [--dataRoot DATAROOT] [--verbose] [--copyIn SRC DEST] [--deleteExtraFiles] [--dryRunExtraFiles]`

Scans a folder structure and runs transform scripts on matched files and sub-folders.

### Command-line Options
<table>
  <tr>
    <td style="white-space:nowrap;">-h, --help</span></td>
    <td>Show this help message and exit.</td>
  </tr>
  <tr>
    <td style="white-space:nowrap;">--input INPUT</td>
    <td>Input folder. Absolute path</td>
  </tr>
  <tr>
    <td style="white-space:nowrap;">--output OUTPUT</td>
    <td>Output folder.</td>
  </tr>
  <tr>
    <td style="white-space:nowrap;">--scriptRoot SCRIPTROOT</td>
    <td>The root of the script folder. Defaults to the current working directory.</td>
  </tr>
</table>

| Option                         | Action                                                                                                                |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `--dataRoot DATAROOT`          | The root of the script folder. Defaults to the current working directory.                                             |
| `--verbose`                    | Turn on verbose output.                                                                                               |
| `--copyIn SRC DEST`            | Copy in the contents of the given folder (SRC) to the given output folder (DEST), relative to the root output folder. |
| `--deleteExtraFiles`           | Remove any extra files from the output folder not egnerated by this script.                                           |
| `--dryRunExtraFiles`           | Does a dry-run of the deleteExtraFiles option, just displaying which files would be deleted by this action.           |

## The Scripts
- [Documents](documents/processDocuments.md)
- [FAQ](FAQ/processFAQ.md)
- [Slideshow](slideshow/processSlideshow.md)
- [Dashboard](dashboard/processDashboard.md)
- [Image Gallery](imageGallery/processImageGallery.md)

## Extending
If you want to extend the functionality of this project, just write a script that accepts the same set of paramaeters at the command line. There is a docsToMarkdownLib Python library that contains handy functions if you happen to be writing your script in Python, but really you can write a command line application in any language you prefer.

The scripts should all work just fine from the command line, but as an added feature they might be used with the [Web Console](https://github.com/dhicks6345789/web-console) project to produce a very simple front end. Therefore, when writing additional scripts it would be best to include formatting in any output (progress / error messages, progress bars, etc) suitible for Web Console to use - see the project's page for more details.
