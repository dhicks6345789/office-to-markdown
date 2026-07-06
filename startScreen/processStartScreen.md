# Start Screen

Given a spreadsheet (Excel or CSV format), produces a single-page HTML file that acts as a "start screen", a page of links to other pages.

Handy for creating simple landing pages, or for a list-of-links page. Each URL in the spreadsheet is represented by an icon, with a title and description (as roll-over text), separate icon images can be provided or the site's favicon will be used.

This project consists of a Python script, intended to be run server-side, and a client-side web page component. The client-side web page can be used as a stand-alone component without the server-side script.

## Installation

The server-side script is part of the [Docs To Markdown](https://github.com/dhicks6345789/docs-to-markdown/tree/WebconsoleUpdate) project, and should be installed as part of that project.

## Usage

## Client-Side Slideshow Web Page

The client-side web page component is used by the server-side script, but can also be used as a self-contained, stand-alone slideshow application - as long as you can get your audio files into formats playable by the browser you should be able to use it. The web page should work on most modern web browsers.

### Installation

The web page component can simply be used as a single-page web application in your own projects - just download the "audioCuesIndex.html" file, include it in your own code or repository if you want. It is self-contained, any Javascript code or CSS styles are included in the one file.

### Usage

For stand-alone usage, download the "audioCuesIndex.html" file. You are probably best off placing it in its own sub-folder, along with the resource files you want to use (index.csv, any audio files, optional images for icons), and renaming it "index.html" so your web server will see it as the default index file for that folder. For example, if you created a folder called `audiocues1` in the root folder of your web server's main public folder, the contents of that folder might be:

```
index.html (the downloaded and renamed "audioCuesIndex.html" file)
index.csv
bell.mp3
bang.mp3
```

The public URL of the slideshow might now be something along the lines of `https://example.com/audiocues1`.

Make sure resources are in formats that can be played by the web browser (see the server-side component above if you need a way of doing that).

You can modify the (by default) empty array defined at the start of the web page to contain a list of resources you want to load. Look for the line `var resources = [];` and modify to be a list of your resources:

```
var resources = ["myImage.png", "myVideo.mp4", "myDocument.pdf"];
```

The slides will be displayed in the order defined in the array.

#### Parameters

The web page component accepts parameters passed in as part of the URL string. Using the example from above, we can set the transition time of slides (in seconds):

```
https://example.com/slideshow1/?transition=20
```

There are several user-setable parameters:
- transition: The transition time, in seconds, of each slide.
- fadesteps: The number of "steps" the fade effect uses. Using more steps giveas you a more gradual fade effect.
- fadeinterval: The time, in seconds, that the fade effect takes. Again, a longer time goves youa more gradual fade effect.
- clickRequired: true or false. If set to "true", the slideshow will wait for user input before proceding to the next slide. This can be a keypress, mouse click or (if running on a touch screen) a screen press event.
- refreshAt: The time, given in hours:minutes:seconds, that the page should refresh itself.

The parameters given above all have default values, so any can be left blank. Any values left blank will be filled in by reloading the URL - when you load the web page, you'll see the URL refresh straight away to include the missing values. Therefore, if you were to load the URL `https://example.com/slideshow1/?clickRequired=true` you would find that it would refresh straight away to be something like `https://example.com/slideshow1/?transition=20&fadesteps=20&fadeinterval=0.2&clickRequired=true&refreshAt=12:00:10`.
