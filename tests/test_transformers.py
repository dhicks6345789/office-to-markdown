# Unit tests for the Office To Markdown document transform scripts.
#
# The transformer sub-scripts depend on several heavy third-party libraries (Pandas, Pillow, Requests,
# extract-favicon, ffmpeg, mammoth, etc.) that are not always installed in the test environment. To keep
# the tests runnable anywhere, these dependencies are replaced with lightweight stubs registered before
# the scripts are imported. The tests verify the sub-script contract: given an input folder, the script
# produces the expected output files and reports them back on stdout.

import io
import sys
import types
import pathlib
import importlib.util

import pytest


# The repository root and the transformer script under test.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent.parent
START_SCREEN_SCRIPT = REPO_ROOT / "startScreen" / "processStartScreen.py"
START_SCREEN_TEMPLATE = REPO_ROOT / "startScreen" / "startScreenIndex.html"

# Make the repository and the stub packages importable.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests" / "_stubs"))


# --------------------------------------------------------------------------- #
# Stub modules for third-party libraries not guaranteed to be installed.
# --------------------------------------------------------------------------- #
def register_stub_module(theName):
    """Create (or fetch) a placeholder module and register it in sys.modules."""
    if theName not in sys.modules:
        sys.modules[theName] = types.ModuleType(theName)
    return sys.modules[theName]


def register_pandas_stub():
    """A minimal Pandas stub: read_csv returns a DataFrame-like object whose rows we can iterate."""
    pandas = register_stub_module("pandas")

    class SeriesIndexer:
        def __init__(self, theData):
            self._data = theData

        def __getitem__(self, theIndex):
            return self._data[theIndex]

    class FakeSeries:
        def __init__(self, theData):
            self._data = theData
            self.shape = (len(theData),)
            self.iloc = SeriesIndexer(theData)

    class FakeDataFrame:
        def __init__(self, theRows):
            self.rows = theRows

        def iterrows(self):
            for theIndex, theRow in enumerate(self.rows):
                yield theIndex, FakeSeries(theRow)

    def read_csv(theFilename, **kwargs):
        rows = []
        lines = pathlib.Path(theFilename).read_text().splitlines()
        for line in lines[1:]:
            if line.strip():
                rows.append(line.split(","))
        return FakeDataFrame(rows)

    pandas.read_csv = read_csv
    pandas.read_excel = lambda *args, **kwargs: (_ for _ in ()).throw(NotImplementedError("Excel not stubbed"))
    return pandas


def register_office_to_markdown_stubs():
    """Register stubs for everything that officeToMarkdownLib / the scripts import at the top level."""
    # Pandas.
    register_pandas_stub()

    # PyYAML.
    yaml = register_stub_module("yaml")
    yaml.safe_load = lambda *args, **kwargs: {}

    # ffmpeg-python.
    ffmpeg = register_stub_module("ffmpeg")
    ffmpeg.probe = lambda *args, **kwargs: {"streams": []}

    # mammoth.
    mammoth = register_stub_module("mammoth")
    mammoth.convert_to_html = lambda *args, **kwargs: types.SimpleNamespace(value="<p>test</p>")

    # markdownify.
    markdownify = register_stub_module("markdownify")
    markdownify.markdownify = lambda theHTML, **kwargs: "test"

    # Requests.
    requests = register_stub_module("requests")
    requests.get = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("requests.get should not be called in tests"))

    # extract-favicon.
    extract_favicon = register_stub_module("extract_favicon")
    extract_favicon.get_best_favicon = lambda *args, **kwargs: None


register_office_to_markdown_stubs()


# --------------------------------------------------------------------------- #
# A helper to execute a transformer sub-script in-process and capture its output.
# --------------------------------------------------------------------------- #
def run_sub_script(theScriptPath, theInputDir, theOutputRoot, theOutput, theScriptRoot, **extraArgs):
    """Execute a transformer script with the given arguments, returning its stdout (contract data)."""
    sys.argv = [str(theScriptPath), "--input", str(theInputDir), "--outputRoot", str(theOutputRoot),
                "--output", str(theOutput), "--scriptRoot", str(theScriptRoot)]
    for key, value in extraArgs.items():
        sys.argv.extend(["--" + key, str(value)])

    originalStdin = sys.stdin
    originalStdout = sys.stdout
    originalStderr = sys.stderr
    capturedOut = io.StringIO()
    capturedErr = io.StringIO()
    try:
        sys.stdin = io.StringIO("")
        sys.stdout = capturedOut
        sys.stderr = capturedErr
        moduleName = "sub_script_" + theScriptPath.stem + "_" + str(hash(theScriptPath))
        spec = importlib.util.spec_from_file_location(moduleName, theScriptPath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.stdin = originalStdin
        sys.stdout = originalStdout
        sys.stderr = originalStderr
    return capturedOut.getvalue()


def write_start_screen_input(theRoot, theCsv, theImages=()):
    """Create an input folder named 'startScreen' containing an index.csv and any local icon images."""
    inputDir = theRoot / "startScreen"
    inputDir.mkdir(parents=True, exist_ok=True)
    (inputDir / "index.csv").write_text(theCsv)
    for imageName in theImages:
        (inputDir / imageName).touch()
    return inputDir


# --------------------------------------------------------------------------- #
# Tests.
# --------------------------------------------------------------------------- #
def test_start_screen_generates_index(tmp_path):
    """A folder with an index.csv produces a start-screen index.html with the resources embedded."""
    inputDir = write_start_screen_input(tmp_path, "URL,Title,Description,Icon\n"
                                                 "https://example.com/foo,Foo,First resource,\n"
                                                 "https://example.com/bar,Bar,Second resource,\n")

    stdout = run_sub_script(START_SCREEN_SCRIPT, inputDir, tmp_path / "out", "startScreen", SCRIPT_ROOT)

    outputFile = tmp_path / "out" / "static" / "index.html"
    assert outputFile.is_file(), "index.html should be generated under static/"
    html = outputFile.read_text()
    assert 'var resources = [' in html
    assert "https://example.com/foo" in html
    assert "https://example.com/bar" in html

    # The script must report its input files and the output file back to the calling script (the contract).
    assert "index.csv" in stdout
    assert "---" in stdout
    assert "static" in stdout and "index.html" in stdout


def test_start_screen_uses_local_icon(tmp_path):
    """A resource with a blank icon but a matching local image gets that image normalised as its icon."""
    inputDir = write_start_screen_input(tmp_path, "URL,Title,Description,Icon\n"
                                                 "https://example.com/cat,Cat,Local icon,\n",
                                        theImages=["cat.png"])

    stdout = run_sub_script(START_SCREEN_SCRIPT, inputDir, tmp_path / "out", "startScreen", SCRIPT_ROOT)

    outputDir = tmp_path / "out" / "static"
    html = (outputDir / "index.html").read_text()
    assert "https://example.com/cat" in html
    # A normalised icon should have been written next to the index.html and referenced in it.
    iconFiles = [item for item in outputDir.iterdir() if item.suffix == ".png"]
    assert len(iconFiles) == 1, "the local icon should have been normalised to a single PNG"
    assert iconFiles[0].name in html
    assert str(iconFiles[0]) in stdout


def test_start_screen_uses_explicit_local_icon_path(tmp_path):
    """A resource whose Icon column holds a local file path (not a URL) is loaded from the local file system."""
    inputDir = tmp_path / "startScreen"
    inputDir.mkdir(parents=True, exist_ok=True)
    (inputDir / "index.csv").write_text("URL,Title,Description,Icon\n"
                                        "https://example.com/dog,Dog,Local icon,local_icon.png\n")
    import PIL.Image
    PIL.Image.new("RGB", (64, 64), (255, 0, 0)).save(inputDir / "local_icon.png")

    stdout = run_sub_script(START_SCREEN_SCRIPT, inputDir, tmp_path / "out", "startScreen", SCRIPT_ROOT)

    outputDir = tmp_path / "out" / "static"
    html = (outputDir / "index.html").read_text()
    assert "https://example.com/dog" in html

    # The explicit local icon should have been normalised to a PNG and referenced in the page.
    iconFiles = [item for item in outputDir.iterdir() if item.suffix == ".png"]
    assert len(iconFiles) == 1, "the explicit local icon should have been normalised to a single PNG"
    assert iconFiles[0].name in html
    assert str(iconFiles[0]) in stdout


def test_start_screen_uses_file_uri_local_icon(tmp_path):
    """A resource whose Icon column holds a file:// URI is loaded from the local file system."""
    inputDir = tmp_path / "startScreen"
    inputDir.mkdir(parents=True, exist_ok=True)
    (inputDir / "index.csv").write_text("URL,Title,Description,Icon\n"
                                        "https://example.com/bird,Bird,File URI icon,file://bird.png\n")
    (inputDir / "bird.png").touch()

    stdout = run_sub_script(START_SCREEN_SCRIPT, inputDir, tmp_path / "out", "startScreen", SCRIPT_ROOT)

    outputDir = tmp_path / "out" / "static"
    html = (outputDir / "index.html").read_text()
    assert "https://example.com/bird" in html

    # The file:// icon should have been normalised to a PNG and referenced in the page.
    iconFiles = [item for item in outputDir.iterdir() if item.suffix == ".png"]
    assert len(iconFiles) == 1, "the file:// icon should have been normalised to a single PNG"
    assert iconFiles[0].name in html
    assert str(iconFiles[0]) in stdout
