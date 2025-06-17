TITLE: Install html-to-markdown Python Library
DESCRIPTION: This command installs the `html-to-markdown` library using pip, the Python package installer. It ensures all necessary dependencies are downloaded and made available for use in your Python projects.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_0

LANGUAGE: shell
CODE:
```
pip install html-to-markdown
```

----------------------------------------

TITLE: Convert HTML to Markdown using html-to-markdown
DESCRIPTION: This snippet demonstrates the basic usage of `html-to-markdown` to convert a multi-line HTML string into Markdown. It imports the `convert_to_markdown` function and prints the resulting Markdown output.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_1

LANGUAGE: python
CODE:
```
from html_to_markdown import convert_to_markdown

html = """
<article>
    <h1>Welcome</h1>
    <p>This is a <strong>sample</strong> with a <a href="https://example.com">link</a>.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
</article>
"""

markdown = convert_to_markdown(html)
print(markdown)
```

LANGUAGE: markdown
CODE:
```
# Welcome

This is a **sample** with a [link](https://example.com).

* Item 1
* Item 2
```

----------------------------------------

TITLE: Customize HTML to Markdown Conversion Options
DESCRIPTION: This snippet illustrates how to apply various configuration options when converting HTML to Markdown. It demonstrates setting heading styles, strong/emphasis symbols, bullet characters, text wrapping, and default code block language.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_3

LANGUAGE: python
CODE:
```
from html_to_markdown import convert_to_markdown

html = "<div>Your content here...</div>"
markdown = convert_to_markdown(
    html,
    heading_style="atx",  # Use # style headers
    strong_em_symbol="*",  # Use * for bold/italic
    bullets="*+-",  # Define bullet point characters
    wrap=True,  # Enable text wrapping
    wrap_width=100,  # Set wrap width
    escape_asterisks=True,  # Escape * characters
    code_language="python",  # Default code block language
)
```

----------------------------------------

TITLE: Configuration Options for HTML to Markdown Conversion
DESCRIPTION: Details the various configuration parameters available for customizing HTML to Markdown conversion, including link handling, list styles, code blocks, and content stripping. These options allow fine-grained control over the output Markdown.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_9

LANGUAGE: APIDOC
CODE:
```
Configuration Options:
  autolinks: Convert valid URLs to Markdown links automatically
  bullets: Characters to use for bullet points in lists
  code_language: Default language for fenced code blocks
  code_language_callback: Function to determine code block language
  convert: List of HTML tags to convert (None = all supported tags)
  default_title: Use default titles for elements like links
  escape_asterisks: Escape * characters
  escape_misc: Escape miscellaneous Markdown characters
  escape_underscores: Escape _ characters
  heading_style: Header style (underlined/atx/atx_closed)
  keep_inline_images_in: Tags where inline images should be kept
  newline_style: Style for handling newlines (spaces/backslash)
  strip: Tags to remove from output
  strong_em_symbol: Symbol for strong/emphasized text (* or _)
  sub_symbol: Symbol for subscript text
  sup_symbol: Symbol for superscript text
  wrap: Enable text wrapping
  wrap_width: Width for text wrapping
  convert_as_inline: Treat content as inline elements
  custom_converters: A mapping of HTML tag names to custom converter functions
```

----------------------------------------

TITLE: html-to-markdown Configuration Options Reference
DESCRIPTION: This section provides a reference for the various configuration options available in `html-to-markdown`. These options allow fine-grained control over the HTML to Markdown conversion process, affecting aspects like heading styles, bullet characters, and text wrapping.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_5

LANGUAGE: APIDOC
CODE:
```
Option: autolinks
  Type: bool
  Default: True
  Description: Auto-convert URLs to Markdown links

Option: bullets
  Type: str
  Default: '*+-'
  Description: Characters to use for bullet points

Option: code_language
  Type: str
  Default: ''
  Description: Default language for code blocks

Option: heading_style
  Type: str
  Default: 'underlined'
  Description: Header style ('underlined', 'atx', 'atx_closed')

Option: escape_asterisks
  Type: bool
  Default: True
  Description: Escape * characters

Option: escape_underscores
  Type: bool
  Default: True
  Description: Escape _ characters

Option: wrap
  Type: bool
  Default: False
  Description: Enable text wrapping

Option: wrap_width
  Type: int
  Default: 80
  Description: Text wrap width
```

----------------------------------------

TITLE: Define Custom Converters for HTML Tags
DESCRIPTION: This example shows how to implement custom conversion logic for specific HTML tags. It defines a function `custom_bold_converter` for the `<b>` tag, which overrides the default behavior and demonstrates how to pass it to `convert_to_markdown`.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_4

LANGUAGE: python
CODE:
```
from bs4.element import Tag
from html_to_markdown import convert_to_markdown

# Define a custom converter for the <b> tag
def custom_bold_converter(*, tag: Tag, text: str, **kwargs) -> str:
    return f"IMPORTANT: {text}"

html = "<p>This is a <b>bold statement</b>.</p>"
markdown = convert_to_markdown(html, custom_converters={"b": custom_bold_converter})
print(markdown)
# Output: This is a IMPORTANT: bold statement.
```

----------------------------------------

TITLE: Convert HTML with Pre-configured BeautifulSoup Instance
DESCRIPTION: This example shows how to integrate `html-to-markdown` with BeautifulSoup for more control over HTML parsing. It passes a pre-configured BeautifulSoup object, allowing custom parsers like `lxml` to be used before conversion.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_2

LANGUAGE: python
CODE:
```
from bs4 import BeautifulSoup
from html_to_markdown import convert_to_markdown

# Configure BeautifulSoup with your preferred parser
soup = BeautifulSoup(html, "lxml")  # Note: lxml requires additional installation
markdown = convert_to_markdown(soup)
```

----------------------------------------

TITLE: Convert HTML Files from Command Line
DESCRIPTION: These commands demonstrate how to use the `html_to_markdown` CLI tool to convert HTML content. It shows examples for converting a file, processing input from stdin, and applying custom conversion options directly via command-line arguments.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_6

LANGUAGE: shell
CODE:
```
# Convert a file
html_to_markdown input.html > output.md

# Process stdin
cat input.html | html_to_markdown > output.md

# Use custom options
html_to_markdown --heading-style atx --wrap --wrap-width 100 input.html > output.md
```

----------------------------------------

TITLE: View html-to-markdown CLI Help Options
DESCRIPTION: This command displays all available options and usage instructions for the `html_to_markdown` command-line interface. It's useful for discovering supported arguments and their functionalities.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_7

LANGUAGE: shell
CODE:
```
html_to_markdown --help
```

----------------------------------------

TITLE: Migrate from Markdownify to html-to-markdown
DESCRIPTION: This snippet illustrates the compatibility layer provided for users migrating from the `markdownify` library. It shows that the `markdownify` function from `html_to_markdown` can be used as a direct replacement, ensuring backward compatibility.
SOURCE: https://github.com/goldziher/html-to-markdown/blob/main/README.md#_snippet_8

LANGUAGE: python
CODE:
```
# Old code
from markdownify import markdownify as md

# New code - works the same way
from html_to_markdown import markdownify as md
```
