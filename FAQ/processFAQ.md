# processFAQ.py

## Descrption
Takes a folder containing text content (Word documents or Markdown), one FAQ question/answer per document, and produces Markdown files ready for processing with a static site generation tool (templates for Hugo are included). Audio and video content can be added for each section and will be suitibly processed and appear alongside the text content in a single HTML document with collapsable question/answer sections.

## Requirements
Needs the Pandas Python module, which should be installable via Pip.

For processing Word documents, needs [Pandoc](https://pandoc.org/).

For processing audio / video content, needs [ffmpeg](https://www.ffmpeg.org/).

## Usage

```
processFAQ.py inputFolder outputFolder
```
