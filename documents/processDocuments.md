# DocsToMarkdown.py

## Descrption
Converts a folder of Word / Excel files (compatability is with those produced by Microsoft Office / Office 365, exported from Google Workspace, LibreOffice, or, hopefully, pretty much any other tool) to the Github varient of Markdown (or to CSV in the case of spreadsheets files). The output is intended to be used as the input for static site generation tools such as Hugo, Jeykll, etc, and the script will handle appropriate metadata headers.

## Requirements
Needs the Pandas Python module, which should be installable via Pip.

DocsToMarkdown.py depends on the Ruby-based utility [Pandoc](https://pandoc.org/), version 2.7 or higher (released March 2019). If you're in a Linux environment, this should be installable via your distribution's usual mechanism (apt-get, etc). Note that earlier versions (as packaged in Debian 9 "Stretch" / Debian 10 "Buster" repositories, for instance) have a bug which stops them parsing DOCX files created with Office 365 - for older Linux distributions and for Windows environments, check the [Pandoc installation instructions](https://pandoc.org/installing.html).

## Usage

```
docsToMarkdown --input inputFolder --output outputFolder
```

Converts all DOC/DOCX files (using Pandoc) to Markdown. Basic formatting from Word documents should be retained in output Markdown - titles, bold / italic text, bullet points, tables and similar features.

Converts all XLS/XLSX files to CSV. Formulas, tables and so on will be lost, just values will be retained.

## Example 1
So, if you had a single folder with some files in:

```
inputFolder/index.docx
inputFolder/about.docx
inputFolder/contact.docx
inputFolder/data.xlsx
```

Running ``docsToMarkdown.py -i inputFolder -o outputFolder`` would produce:

```
outputFolder/index.md
outputFolder/about.md
outputFolder/contact.md
outputFolder/data.csv
```

## Example 2
You can better define the conversion process with a JSON-formatted config file:

```
docsToMarkdown.py -c config.json -i inputFolder -o outputFolder
```

The configuration file is written as a JSON-formatted ordered array of associative arrays:

```
[
    {"global/function":"name", data},
    {"global/function":"name", data}...
]
```

You can define global parameters, some of which can be used by DocsToMarkdown, or call functions. The configuration file will be processed in the order given for each file in the folder tree.

### global:baseURL
Sets a global variable later passed to various functions to define the base URL of your site.

### function:filesToMarkdown
inputFiles: array
outputFile: string
frontMatter: associative array
Takes the given input files and converts them, using Pandoc, to Markdown. Note that you can define multiple input files for one output Markdown file. You can also define front matter fields that will be inserted at the head of the Markdown document after conversion.

### function:filesToCSV
inputFiles: array
outputFile: string
jekyllHeaders: boolean
Takes the given input Excel files and converts them to CSV. Note that you can define multiple input files for the one output CSV file. If you are using these CSV files as data sources in Jekyll's \_data folder you will need to have Jekyll-style headers placed at the head of the files, so set the "jekyllHeaders" option to "true".

### function:copyFolder
src: string
dest: string
Simply copies a folder in the input folder to a folder in the output folder. Note that the roots of both locations are defined by the input and output options given at runtime, these are both relative arguments. The copy process checks for updates before copying, no file is copied unless the previous version is changed - this should make this process suitible for use in copying files from network-mounted storage repositories.

## Templates
You can define a "templates" folder that will be copied over to the output folder along with the Markdown output, this is to accomodate applications such as Jekyll that expect a certain folder structure.

```
docsToMarkdown.py -c config.json -i inputDocs -o jekyll -t jekyllTemplates
```
