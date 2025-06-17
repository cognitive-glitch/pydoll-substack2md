# Pydoll - Comprehensive Documentation Summary

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture & Design](#architecture--design)
3. [Installation & Setup](#installation--setup)
4. [Core Concepts](#core-concepts)
5. [Element Finding & Interaction](#element-finding--interaction)
6. [Network Capabilities](#network-capabilities)
7. [Event System](#event-system)
8. [Advanced Features](#advanced-features)
9. [Browser Configuration](#browser-configuration)
10. [Best Practices & Performance](#best-practices--performance)
11. [API Reference](#api-reference)
12. [Use Cases & Examples](#use-cases--examples)

## Introduction

Pydoll is a modern Python browser automation library that revolutionizes web automation by providing direct integration with the Chrome DevTools Protocol (CDP). Unlike traditional WebDriver-based solutions, Pydoll eliminates the middleman, offering:

- **Direct CDP Connection**: No WebDriver server required
- **Async-First Design**: Built on Python's `asyncio` for concurrent operations
- **Minimal Dependencies**: Only essential packages (websockets, aiohttp, aiofiles, bs4)
- **Cross-Browser Support**: Works with Chrome and Edge browsers
- **Event-Driven Architecture**: Real-time reaction to browser events
- **Modern API**: Intuitive method names and patterns

### Key Advantages Over Selenium
- Faster execution due to direct CDP communication
- Native async/await support for better concurrency
- Real-time event monitoring and interception
- Smaller footprint and faster installation
- More granular control over browser behavior

## Architecture & Design

### Domain Hierarchy

```
Browser Domain (Top Level)
│   ├── Lifecycle Management
│   ├── Connection Management
│   └── Global Configuration
│
├── Tab Domain (Page Level)
│   ├── Navigation
│   ├── Content Interaction
│   ├── JavaScript Execution
│   └── Event Handling
│
└── WebElement Domain (Element Level)
    ├── User Interactions
    ├── Property Access
    ├── State Management
    └── Element-specific Operations
```

### Core Components

#### 1. **ConnectionHandler**
- Manages WebSocket connection to browser's CDP endpoint
- Handles command execution and response management
- Processes incoming events and dispatches to callbacks
- Components:
  - `CommandManager`: Tracks pending commands and futures
  - `EventsHandler`: Manages event callbacks and routing
  - `WebSocket Client`: Maintains persistent connection

#### 2. **Browser Process Manager**
- Launches browser executable with proper arguments
- Monitors process health
- Handles graceful shutdown
- Manages browser lifecycle

#### 3. **Options Manager**
- Configures browser launch parameters
- Manages command-line arguments
- Handles browser-specific configurations
- Supports custom binary locations

#### 4. **Proxy Manager**
- Parses proxy settings from options
- Handles proxy authentication
- Manages proxy credentials extraction

#### 5. **Temp Directory Manager**
- Creates temporary directories for user data
- Handles cleanup on browser closure
- Prevents data persistence between sessions

### Communication Flow

```
Python Code → ConnectionHandler → WebSocket → CDP → Browser
                     ↑                              ↓
                     └──────── Events ←─────────────┘
```

## Installation & Setup

### Requirements
- Python ≥ 3.10
- Chrome or Edge browser installed
- No additional drivers needed

### Installation Methods

```bash
# Stable version from PyPI
pip install pydoll-python

# Latest development version
pip install git+https://github.com/autoscrape-labs/pydoll.git
```

### Dependencies
```python
# Minimal dependency set
websockets = "^13.1"     # WebSocket communication
aiohttp = "^3.9.5"       # HTTP client
aiofiles = "^23.2.1"     # Async file operations
bs4 = "^0.0.2"           # HTML parsing
```

## Core Concepts

### Asynchronous Design
All Pydoll operations are asynchronous and must be used with `async`/`await`:

```python
import asyncio
from pydoll.browser.chromium import Chrome

async def main():
    async with Chrome() as browser:
        tab = await browser.start()
        await tab.go_to("https://example.com")

asyncio.run(main())
```

### Context Manager Pattern
Pydoll supports Python's context manager protocol for automatic resource cleanup:

```python
# Automatic cleanup with context manager
async with Chrome() as browser:
    tab = await browser.start()
    # Browser automatically closes when exiting context

# Manual management
browser = Chrome()
tab = await browser.start()
# Must explicitly close
await browser.stop()
```

### Tab Singleton Pattern
Pydoll implements a singleton pattern for Tab instances, ensuring only one Tab object exists per browser tab:

```python
tab1 = await browser.start()
tab2 = Tab(browser, browser._connection_port, tab1._target_id)
# tab1 and tab2 reference the same singleton instance
```

## Element Finding & Interaction

### Modern `find()` Method

The `find()` method provides intuitive element location using keyword arguments:

```python
# Single attribute selectors (optimized)
element = await tab.find(id="username")           # Uses By.ID
element = await tab.find(class_name="button")     # Uses By.CLASS_NAME
element = await tab.find(tag_name="input")        # Uses By.TAG_NAME
element = await tab.find(name="email")            # Uses By.NAME
element = await tab.find(text="Click here")       # Text content

# Multiple attributes (builds XPath)
element = await tab.find(
    tag_name="input",
    type="password",
    name="password"
)
# Generates: //input[@type='password' and @name='password']

# Custom data attributes
element = await tab.find(
    data_testid='submit-button',
    aria_label='Submit form'
)

# Find all matches
elements = await tab.find(class_name="item", find_all=True)

# With timeout and error handling
element = await tab.find(
    id="dynamic-content",
    timeout=10,              # Wait up to 10 seconds
    raise_exc=False          # Return None if not found
)
```

### CSS Selectors and XPath with `query()`

```python
# CSS selectors
element = await tab.query("div.content > p.intro")
element = await tab.query("#login-form input[type='password']")
elements = await tab.query("table tbody tr", find_all=True)

# XPath expressions
element = await tab.query("//div[@id='content']/p[contains(text(), 'Welcome')]")
element = await tab.query("//button[text()='Submit']")
elements = await tab.query("//tr[td[contains(text(), 'Active')]]", find_all=True)

# Automatic detection
element = await tab.query("#username")      # Detected as ID
element = await tab.query(".submit-button") # Detected as class
element = await tab.query("//div[@id='x']") # Detected as XPath
```

### WebElement Operations

#### Interactions
```python
# Mouse operations
await element.click()
await element.click(x_offset=10, y_offset=5)
await element.click(hold_time=1.0)  # Long press
await element.click_using_js()      # JavaScript fallback

# Keyboard operations
await element.type_text("user@example.com", interval=0.15)  # Realistic typing
await element.insert_text("quick text")                      # Fast insertion
await element.press_keyboard_key(Keys.ENTER)

# Complex keyboard combinations
await element.key_down(Keys.SHIFT)
await element.type_text("HELLO")
await element.key_up(Keys.SHIFT)
```

#### Property Access
```python
# Synchronous properties (from initial HTML)
element_id = element.id
element_class = element.class_name
is_enabled = element.is_enabled
tag_name = element.tag_name

# Asynchronous properties (current DOM state)
text = await element.text
html = await element.inner_html
bounds = await element.bounds
value = await element.value
is_visible = await element.is_visible()
```

#### Advanced Operations
```python
# Screenshots
await element.take_screenshot("element.png")
await element.take_screenshot("element.jpg", quality=95)

# Scrolling
await element.scroll_into_view()

# File uploads
await file_input.set_input_files(["file1.pdf", "file2.pdf"])

# JavaScript execution on element
await element._execute_script("this.style.border = '2px solid red';")

# Get specific attributes
placeholder = await element.get_attribute("placeholder")
```

## Network Capabilities

### Network Monitoring

```python
# Enable network monitoring
await tab.enable_network_events()

# Get network logs
all_logs = await tab.get_network_logs()
api_logs = await tab.get_network_logs(filter='api')
js_logs = await tab.get_network_logs(filter='.js')
domain_logs = await tab.get_network_logs(filter='example.com')

# Real-time monitoring with callbacks
async def monitor_requests(tab, event):
    url = event['params']['request']['url']
    method = event['params']['request']['method']
    headers = event['params']['request'].get('headers', {})
    print(f"{method} {url}")

await tab.on(NetworkEvent.REQUEST_WILL_BE_SENT, partial(monitor_requests, tab))
```

### Response Body Extraction

```python
# Capture API responses
captured_responses = {}

async def capture_api_responses(tab, event):
    request_id = event['params']['requestId']
    response = event['params']['response']
    url = response['url']

    if '/api/' in url and response['status'] == 200:
        try:
            body = await tab.get_network_response_body(request_id)
            captured_responses[url] = json.loads(body)
            print(f"Captured: {url}")
        except Exception as e:
            print(f"Failed to capture: {e}")

await tab.on(NetworkEvent.RESPONSE_RECEIVED, partial(capture_api_responses, tab))
```

### Request Interception

```python
# Enable fetch events with filtering
await tab.enable_fetch_events(resource_type=ResourceType.XHR)

async def intercept_requests(tab, event):
    request_id = event['params']['requestId']
    request = event['params']['request']
    url = request['url']
    method = request['method']

    # Block tracking requests
    if any(tracker in url for tracker in ['analytics', 'tracking', 'ads']):
        await browser.fail_request(request_id, NetworkErrorReason.BLOCKED_BY_CLIENT)
        return

    # Modify headers
    if '/api/' in url:
        headers = request.get('headers', {})
        custom_headers = [
            {'name': 'Authorization', 'value': 'Bearer token'},
            {'name': 'X-Custom-Header', 'value': 'Value'},
            {'name': 'User-Agent', 'value': 'Custom Agent'}
        ]
        # Add existing headers
        for name, value in headers.items():
            custom_headers.append({'name': name, 'value': value})

        await browser.continue_request(
            request_id=request_id,
            headers=custom_headers
        )
        return

    # Mock responses
    if '/api/config' in url:
        mock_data = {
            'feature_flags': {'new_ui': True},
            'api_version': '2.0'
        }
        await browser.fulfill_request(
            request_id=request_id,
            response_code=200,
            response_headers=[
                {'name': 'Content-Type', 'value': 'application/json'},
                {'name': 'Cache-Control', 'value': 'no-cache'}
            ],
            body=json.dumps(mock_data)
        )
        return

    # Continue unmodified
    await browser.continue_request(request_id)

await tab.on(FetchEvent.REQUEST_PAUSED, partial(intercept_requests, tab))
```

### Resource Type Filtering

```python
# ResourceType enumeration
ResourceType.DOCUMENT     # HTML pages, iframes
ResourceType.STYLESHEET   # CSS files
ResourceType.IMAGE        # Images (.jpg, .png, .gif)
ResourceType.MEDIA        # Video/audio files
ResourceType.FONT         # Font files
ResourceType.SCRIPT       # JavaScript files
ResourceType.XHR          # XMLHttpRequest/AJAX
ResourceType.FETCH        # Fetch API requests
ResourceType.WEBSOCKET    # WebSocket connections
ResourceType.OTHER        # Miscellaneous

# Filter interception by type
await tab.enable_fetch_events(resource_type=ResourceType.XHR)
await tab.enable_fetch_events(resource_type=ResourceType.DOCUMENT)
```

## Event System

### Event Domain Management

```python
# Enable specific event domains
await tab.enable_page_events()      # Page lifecycle events
await tab.enable_network_events()    # Network activity
await tab.enable_dom_events()        # DOM mutations
await tab.enable_fetch_events()      # Request interception
await tab.enable_runtime_events()    # JavaScript runtime

# Check enablement status
print(f"Page events: {tab.page_events_enabled}")
print(f"Network events: {tab.network_events_enabled}")

# Disable when done (for performance)
await tab.disable_network_events()
```

### Event Registration

```python
# Permanent callbacks
await tab.on(PageEvent.LOAD_EVENT_FIRED, handle_page_load)
await tab.on(NetworkEvent.REQUEST_WILL_BE_SENT, handle_request)

# Temporary callbacks (auto-remove after trigger)
await tab.on(PageEvent.FRAME_NAVIGATED, handle_navigation, temporary=True)

# Using functools.partial for parameters
from functools import partial

async def handle_request(tab, config, event):
    # Access tab and custom config
    pass

config = {"block_ads": True}
await tab.on(
    FetchEvent.REQUEST_PAUSED,
    partial(handle_request, tab, config)
)
```

### Common Events Reference

#### Page Events
- `PageEvent.LOAD_EVENT_FIRED` - Page fully loaded
- `PageEvent.DOM_CONTENT_EVENT_FIRED` - DOM content loaded
- `PageEvent.JAVASCRIPT_DIALOG_OPENING` - Dialog shown
- `PageEvent.FILE_CHOOSER_OPENED` - File picker opened
- `PageEvent.FRAME_NAVIGATED` - Frame navigation

#### Network Events
- `NetworkEvent.REQUEST_WILL_BE_SENT` - Request initiated
- `NetworkEvent.RESPONSE_RECEIVED` - Response headers received
- `NetworkEvent.LOADING_FINISHED` - Request completed
- `NetworkEvent.LOADING_FAILED` - Request failed
- `NetworkEvent.WEBSOCKET_CREATED` - WebSocket created

#### DOM Events
- `DomEvent.DOCUMENT_UPDATED` - Document changed
- `DomEvent.ATTRIBUTE_MODIFIED` - Attribute changed
- `DomEvent.ATTRIBUTE_REMOVED` - Attribute removed
- `DomEvent.SET_CHILD_NODES` - Child nodes updated

#### Fetch Events
- `FetchEvent.REQUEST_PAUSED` - Request intercepted
- `FetchEvent.AUTH_REQUIRED` - Authentication needed

### Custom Event Handlers

```python
# Complex event handler with state
class NetworkMonitor:
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'api_calls': 0,
            'failed_requests': 0
        }

    async def on_request(self, tab, event):
        self.stats['total_requests'] += 1
        url = event['params']['request']['url']
        if '/api/' in url:
            self.stats['api_calls'] += 1

    async def on_failure(self, tab, event):
        self.stats['failed_requests'] += 1

monitor = NetworkMonitor()
await tab.on(NetworkEvent.REQUEST_WILL_BE_SENT, partial(monitor.on_request, tab))
await tab.on(NetworkEvent.LOADING_FAILED, partial(monitor.on_failure, tab))
```

## Advanced Features

### Cloudflare Captcha Bypass

Pydoll includes built-in Cloudflare Turnstile captcha solving:

```python
# Method 1: Context manager (blocks until solved)
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')
    # Code continues after captcha is solved

# Method 2: Background processing
await tab.enable_auto_solve_cloudflare_captcha()
await tab.go_to('https://protected-site.com')
# Captcha solved automatically in background
await tab.disable_auto_solve_cloudflare_captcha()

# Method 3: Custom configuration
await tab.enable_auto_solve_cloudflare_captcha(
    custom_selector=(By.CLASS_NAME, 'custom-captcha-widget'),
    time_before_click=3,      # Wait before solving
    time_to_wait_captcha=10   # Timeout
)
```

### Browser Contexts (Isolation)

Browser contexts provide complete isolation between sessions:

```python
# Create isolated contexts
context1 = await browser.create_browser_context()
context2 = await browser.create_browser_context()

# Create context with proxy
proxy_context = await browser.create_browser_context(
    proxy_server="http://proxy.example.com:8080",
    proxy_bypass_list="localhost,127.0.0.1"
)

# Tabs in different contexts are isolated
tab1 = await browser.new_tab("https://example.com", browser_context_id=context1)
tab2 = await browser.new_tab("https://example.com", browser_context_id=context2)

# Set different cookies/storage
await tab1.execute_script("localStorage.setItem('user', 'Alice')")
await tab2.execute_script("localStorage.setItem('user', 'Bob')")

# Verify isolation
user1 = await tab1.execute_script("return localStorage.getItem('user')")  # Alice
user2 = await tab2.execute_script("return localStorage.getItem('user')")  # Bob

# List all contexts
contexts = await browser.get_browser_contexts()

# Delete context (closes all associated tabs)
await browser.delete_browser_context(context1)
```

### Multi-Tab Management

```python
# Create multiple tabs
tab1 = await browser.start()  # Initial tab
tab2 = await browser.new_tab("https://github.com")
tab3 = await browser.new_tab()  # Empty tab

# Get all opened tabs
all_tabs = await browser.get_opened_tabs()
print(f"Total tabs: {len(all_tabs)}")

# Work with multiple tabs concurrently
await tab1.go_to("https://google.com")
await tab2.find(class_name="header-search-input").type_text("pydoll")
await tab3.go_to("https://example.com")

# Close specific tabs
await tab2.close()
await tab3.close()
```

### iFrame Interaction

```python
# Find iframe element
iframe_element = await tab.find(tag_name="iframe", id="content-frame")

# Get Tab instance for iframe
frame = await tab.get_frame(iframe_element)

# Interact with iframe content
button = await frame.find(id="submit")
await button.click()

# Find elements in iframe
inputs = await frame.find(tag_name="input", find_all=True)
links = await frame.query("a[href*='example']", find_all=True)

# Execute JavaScript in iframe context
result = await frame.execute_script("return document.title")
```

### JavaScript Execution

```python
# Execute in page context
dimensions = await tab.execute_script("""
    return {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio,
        url: window.location.href,
        userAgent: navigator.userAgent
    }
""")

# Execute with element context
heading = await tab.find(tag_name="h1")
await tab.execute_script("""
    // 'argument' refers to the element
    argument.style.color = 'red';
    argument.style.fontSize = '32px';
    argument.textContent = 'Modified by JavaScript';

    // Add event listener
    argument.addEventListener('click', () => {
        alert('Clicked!');
    });
""", heading)

# Return values from scripts
data = await tab.execute_script("""
    const elements = document.querySelectorAll('.item');
    return Array.from(elements).map(el => ({
        text: el.textContent,
        href: el.href || null,
        className: el.className
    }));
""")
```

### File Handling

```python
# Handle file chooser dialogs
async with tab.expect_file_chooser(files="document.pdf"):
    upload_button = await tab.find(id="upload-button")
    await upload_button.click()

# Multiple files
async with tab.expect_file_chooser(files=["file1.pdf", "file2.jpg"]):
    await tab.find(id="multi-upload").click()

# Direct file input
file_input = await tab.find(tag_name="input", type="file")
await file_input.set_input_files(["path/to/file.pdf"])
```

### Dialog Handling

```python
# Set up dialog handler
async def handle_dialog(event):
    if await tab.has_dialog():
        message = await tab.get_dialog_message()
        print(f"Dialog: {message}")
        await tab.handle_dialog(accept=True, prompt_text="Response")

await tab.enable_page_events()
await tab.on('Page.javascriptDialogOpening', handle_dialog)

# Trigger dialogs
await tab.execute_script("alert('Test alert')")
await tab.execute_script("confirm('Confirm action?')")
await tab.execute_script("prompt('Enter value:')")
```

### Screenshots and PDFs

```python
# Page screenshots
await tab.take_screenshot("page.png")
await tab.take_screenshot("page.jpg", quality=95)
screenshot_base64 = await tab.take_screenshot(as_base64=True)

# Element screenshots
element = await tab.find(id="chart")
await element.take_screenshot("chart.png")

# PDF export
await tab.print_to_pdf("page.pdf")
await tab.print_to_pdf(
    "custom.pdf",
    landscape=True,
    print_background=True,
    scale=0.8,
    paper_width=8.5,
    paper_height=11
)
```

### Cookie Management

```python
# Tab-level cookies
cookies_to_set = [
    {
        "name": "session_id",
        "value": "test123",
        "domain": "example.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "Lax"
    }
]
await tab.set_cookies(cookies_to_set)

# Get cookies
all_cookies = await tab.get_cookies()
domain_cookies = await tab.get_cookies(urls=["https://example.com"])

# Delete cookies
await tab.delete_all_cookies()

# Browser-level cookie management
await browser.set_cookies(cookies_to_set)
await browser.delete_all_cookies()
```

## Browser Configuration

### ChromiumOptions

```python
from pydoll.browser.options import ChromiumOptions

options = ChromiumOptions()

# Common options
options.add_argument('--headless=new')              # Headless mode
options.add_argument('--window-size=1920,1080')     # Window size
options.add_argument('--start-maximized')           # Start maximized
options.add_argument('--disable-gpu')               # Disable GPU
options.add_argument('--no-sandbox')               # Disable sandbox
options.add_argument('--disable-dev-shm-usage')    # Memory optimization

# Proxy configuration
options.add_argument('--proxy-server=http://proxy:8080')
# With authentication
options.add_argument('--proxy-server=user:pass@proxy:8080')

# Performance options
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--disable-notifications')
options.add_argument('--disable-extensions')
options.add_argument('--disable-images')  # Don't load images

# Custom binary
options.binary_location = '/usr/bin/google-chrome-stable'

# User data directory
options.add_argument('--user-data-dir=/path/to/profile')

browser = Chrome(options=options)
```

### Window Control

```python
# Get window ID
window_id = await browser.get_window_id()

# Set window bounds
await browser.set_window_bounds({
    'left': 100,
    'top': 100,
    'width': 1024,
    'height': 768
})

# Window states
await browser.set_window_maximized()
await browser.set_window_minimized()
```

### Download Management

```python
# Set download path
download_path = "/path/to/downloads"
await browser.set_download_path(download_path)

# Advanced download configuration
await browser.set_download_behavior(
    behavior=DownloadBehavior.ALLOW,
    download_path=download_path,
    events_enabled=True  # Enable progress events
)

# Context-specific downloads
context_id = await browser.create_browser_context()
await browser.set_download_behavior(
    behavior=DownloadBehavior.ALLOW,
    download_path="/context/downloads",
    browser_context_id=context_id
)
```

### Permission Management

```python
from pydoll.constants import PermissionType

# Grant permissions globally
await browser.grant_permissions([
    PermissionType.GEOLOCATION,
    PermissionType.NOTIFICATIONS,
    PermissionType.CAMERA,
    PermissionType.MICROPHONE
])

# Grant for specific origin
await browser.grant_permissions(
    [PermissionType.GEOLOCATION],
    origin="https://example.com"
)

# Context-specific permissions
await browser.grant_permissions(
    [PermissionType.CAMERA],
    browser_context_id=context_id
)

# Reset permissions
await browser.reset_permissions()
```

## Best Practices & Performance

### Event Management Best Practices

1. **Enable Only What You Need**
   ```python
   # Good: Enable only required events
   await tab.enable_network_events()

   # Bad: Enabling all events
   await tab.enable_page_events()
   await tab.enable_network_events()
   await tab.enable_dom_events()
   await tab.enable_fetch_events()
   await tab.enable_runtime_events()
   ```

2. **Use Temporary Callbacks**
   ```python
   # For one-time events
   await tab.on(PageEvent.LOAD_EVENT_FIRED, handle_load, temporary=True)
   ```

3. **Disable Events When Done**
   ```python
   await tab.enable_network_events()
   # ... do work ...
   await tab.disable_network_events()
   ```

### Element Finding Optimization

1. **Selector Performance Hierarchy**
   - ID selectors (fastest)
   - Class selectors (fast)
   - Tag name (fast)
   - CSS selectors (good)
   - XPath (slower)

2. **Efficient Patterns**
   ```python
   # Good: Use ID when available
   element = await tab.find(id="unique-element")

   # Good: Simple CSS selectors
   element = await tab.query("#form .submit-button")

   # Avoid: Complex XPath when CSS works
   # element = await tab.query("//div[@id='form']//button[@class='submit']")

   # Good: Combine attributes efficiently
   element = await tab.find(tag_name="input", type="email", required=True)
   ```

3. **Handle Optional Elements**
   ```python
   # Good: Graceful handling
   optional = await tab.find(id="optional", timeout=1, raise_exc=False)
   if optional:
       await optional.click()
   ```

### Network Interception Performance

1. **Filter by Resource Type**
   ```python
   # Good: Target specific types
   await tab.enable_fetch_events(resource_type=ResourceType.XHR)

   # Bad: Intercept everything
   await tab.enable_fetch_events()
   ```

2. **Early Filtering in Callbacks**
   ```python
   async def efficient_handler(event):
       url = event['params']['request']['url']
       if '/api/' not in url:
           return  # Early exit
       # Process API requests only
   ```

3. **Always Resolve Requests**
   ```python
   async def safe_handler(tab, event):
       request_id = event['params']['requestId']
       try:
           # Process request
           await process_request(event)
           await browser.continue_request(request_id)
       except Exception as e:
           # Always continue even on error
           await browser.continue_request(request_id)
   ```

### Memory Management

1. **Use Context Managers**
   ```python
   async with Chrome() as browser:
       # Automatic cleanup
       pass
   ```

2. **Close Tabs When Done**
   ```python
   tab = await browser.new_tab()
   # ... use tab ...
   await tab.close()
   ```

3. **Clean Up Event Listeners**
   ```python
   # Remove specific callbacks
   callback_id = await tab.on(event_name, handler)
   await tab.remove_callback(callback_id)
   ```

### Concurrency Patterns

```python
# Process multiple pages concurrently
async def scrape_page(browser, url):
    tab = await browser.new_tab()
    try:
        await tab.go_to(url)
        data = await extract_data(tab)
        return data
    finally:
        await tab.close()

# Run concurrently
urls = ['url1', 'url2', 'url3']
tasks = [scrape_page(browser, url) for url in urls]
results = await asyncio.gather(*tasks)
```

## API Reference

### Core Classes

#### Browser Classes
- `Chrome`: Chrome browser implementation
- `Edge`: Microsoft Edge browser implementation
- `Browser`: Abstract base class

#### Tab Class
Main interface for page interaction:
- Navigation: `go_to()`, `refresh()`, `current_url`
- Finding: `find()`, `query()`
- Execution: `execute_script()`
- Events: `on()`, `enable_*_events()`
- Content: `page_source`, `take_screenshot()`, `print_to_pdf()`

#### WebElement Class
Represents DOM elements:
- Interactions: `click()`, `type_text()`, `press_keyboard_key()`
- Properties: `text`, `inner_html`, `bounds`, `is_visible()`
- Attributes: `get_attribute()`, `id`, `class_name`

### Constants & Enums

#### By (Selector Strategies)
- `By.ID`
- `By.CLASS_NAME`
- `By.TAG_NAME`
- `By.NAME`
- `By.CSS_SELECTOR`
- `By.XPATH`

#### Keys (Keyboard Constants)
- `Keys.ENTER`, `Keys.TAB`, `Keys.ESCAPE`
- `Keys.SHIFT`, `Keys.CONTROL`, `Keys.ALT`
- `Keys.ARROW_UP`, `Keys.ARROW_DOWN`, etc.

#### ResourceType
- `ResourceType.DOCUMENT`
- `ResourceType.STYLESHEET`
- `ResourceType.IMAGE`
- `ResourceType.SCRIPT`
- `ResourceType.XHR`
- `ResourceType.FETCH`

#### NetworkErrorReason
- `NetworkErrorReason.FAILED`
- `NetworkErrorReason.ABORTED`
- `NetworkErrorReason.TIMED_OUT`
- `NetworkErrorReason.ACCESS_DENIED`
- `NetworkErrorReason.CONNECTION_CLOSED`
- `NetworkErrorReason.CONNECTION_RESET`
- `NetworkErrorReason.CONNECTION_REFUSED`
- `NetworkErrorReason.CONNECTION_ABORTED`
- `NetworkErrorReason.CONNECTION_FAILED`
- `NetworkErrorReason.NAME_NOT_RESOLVED`
- `NetworkErrorReason.INTERNET_DISCONNECTED`
- `NetworkErrorReason.ADDRESS_UNREACHABLE`
- `NetworkErrorReason.BLOCKED_BY_CLIENT`
- `NetworkErrorReason.BLOCKED_BY_RESPONSE`

### Exceptions
- `ElementNotFound`: Element not found in DOM
- `WaitElementTimeout`: Element wait timeout exceeded
- `BrowserNotStarted`: Browser not initialized
- `EventNotSupported`: Invalid event for context
- `InvalidCommand`: Invalid CDP command
- `ElementNotVisible`: Element not visible

## Use Cases & Examples

### Web Scraping with Dynamic Content

```python
async def scrape_spa():
    async with Chrome() as browser:
        tab = await browser.start()

        # Navigate and wait for dynamic content
        await tab.go_to('https://spa-website.com')

        # Wait for specific element
        content = await tab.find(id="dynamic-content", timeout=10)

        # Extract data after AJAX loads
        await asyncio.sleep(2)  # Wait for AJAX

        items = await tab.find(class_name="item", find_all=True)
        data = []
        for item in items:
            title = await item.find(class_name="title")
            price = await item.find(class_name="price")
            data.append({
                'title': await title.text,
                'price': await price.text
            })

        return data
```

### API Testing and Mocking

```python
async def test_api_integration():
    async with Chrome() as browser:
        tab = await browser.start()

        # Mock API responses
        async def mock_api(tab, event):
            request_id = event['params']['requestId']
            url = event['params']['request']['url']

            if '/api/users' in url:
                mock_users = [
                    {'id': 1, 'name': 'Alice'},
                    {'id': 2, 'name': 'Bob'}
                ]
                await browser.fulfill_request(
                    request_id=request_id,
                    response_code=200,
                    response_headers=[
                        {'name': 'Content-Type', 'value': 'application/json'}
                    ],
                    body=json.dumps(mock_users)
                )
            else:
                await browser.continue_request(request_id)

        await tab.enable_fetch_events()
        await tab.on(FetchEvent.REQUEST_PAUSED, partial(mock_api, tab))

        # Test the application
        await tab.go_to('https://app.example.com')

        # Verify UI shows mocked data
        users = await tab.find(class_name="user", find_all=True)
        assert len(users) == 2
```

### Multi-Account Testing

```python
async def test_multiple_accounts():
    async with Chrome() as browser:
        accounts = [
            {"email": "user1@test.com", "password": "pass1"},
            {"email": "user2@test.com", "password": "pass2"},
            {"email": "admin@test.com", "password": "admin"}
        ]

        results = {}

        for account in accounts:
            # Create isolated context for each account
            context_id = await browser.create_browser_context()
            tab = await browser.new_tab(
                "https://app.example.com/login",
                browser_context_id=context_id
            )

            # Login
            await tab.find(name="email").type_text(account["email"])
            await tab.find(name="password").type_text(account["password"])
            await tab.find(tag_name="button", type="submit").click()

            # Wait for dashboard
            await tab.find(id="dashboard", timeout=5)

            # Extract user-specific data
            user_data = await tab.execute_script("""
                return {
                    role: document.querySelector('.user-role').textContent,
                    permissions: Array.from(document.querySelectorAll('.permission')).map(p => p.textContent)
                }
            """)

            results[account["email"]] = user_data

            # Cleanup
            await tab.close()
            await browser.delete_browser_context(context_id)

        return results
```

### Performance Monitoring

```python
async def monitor_page_performance():
    async with Chrome() as browser:
        tab = await browser.start()

        # Enable performance monitoring
        await tab.enable_network_events()

        # Track metrics
        metrics = {
            'requests': [],
            'load_time': 0,
            'total_size': 0
        }

        start_time = time.time()

        async def track_request(tab, event):
            request = event['params']['request']
            metrics['requests'].append({
                'url': request['url'],
                'method': request['method'],
                'timestamp': time.time() - start_time
            })

        async def track_response(tab, event):
            response = event['params']['response']
            if 'encodedDataLength' in event['params']:
                metrics['total_size'] += event['params']['encodedDataLength']

        await tab.on(NetworkEvent.REQUEST_WILL_BE_SENT, partial(track_request, tab))
        await tab.on(NetworkEvent.LOADING_FINISHED, partial(track_response, tab))

        # Navigate and measure
        await tab.go_to('https://example.com')
        await tab.find(tag_name="body", timeout=10)  # Wait for load

        metrics['load_time'] = time.time() - start_time
        metrics['request_count'] = len(metrics['requests'])

        return metrics
```

### Form Automation with Validation

```python
async def automated_form_submission():
    async with Chrome() as browser:
        tab = await browser.start()
        await tab.go_to('https://example.com/form')

        # Fill form fields
        fields = {
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'birthDate': '1990-01-01'
        }

        for field_id, value in fields.items():
            field = await tab.find(id=field_id)
            await field.type_text(value, interval=0.05)

        # Handle dropdown
        country_select = await tab.find(id="country")
        await country_select.click()
        await tab.find(tag_name="option", text="United States").click()

        # Handle checkboxes
        terms_checkbox = await tab.find(id="terms")
        is_checked = await terms_checkbox.get_attribute("checked")
        if not is_checked:
            await terms_checkbox.click()

        # Submit and wait for result
        submit_btn = await tab.find(tag_name="button", type="submit")
        await submit_btn.click()

        # Check for validation errors
        errors = await tab.find(class_name="error", find_all=True, raise_exc=False)
        if errors:
            error_texts = []
            for error in errors:
                error_texts.append(await error.text)
            raise Exception(f"Form validation failed: {error_texts}")

        # Wait for success
        success_msg = await tab.find(class_name="success-message", timeout=5)
        return await success_msg.text
```

## Troubleshooting

### Common Issues and Solutions

1. **Browser Not Found**
   ```python
   # Specify custom binary location
   options = ChromiumOptions()
   options.binary_location = '/path/to/chrome'
   ```

2. **Connection Timeout**
   ```python
   # Increase timeout for slow systems
   browser = Chrome(connection_timeout=30)
   ```

3. **Element Not Found**
   ```python
   # Use appropriate timeouts
   element = await tab.find(id="slow-element", timeout=15)

   # Handle gracefully
   element = await tab.find(id="optional", raise_exc=False)
   if element:
       await element.click()
   ```

4. **Stale Element Reference**
   ```python
   # Re-find element after page changes
   button = await tab.find(id="submit")
   await some_action_that_changes_page()
   button = await tab.find(id="submit")  # Re-find
   await button.click()
   ```

5. **Network Interception Issues**
   ```python
   # Always resolve requests
   try:
       # Process request
       pass
   finally:
       await browser.continue_request(request_id)
   ```

## Migration from Selenium

### Key Differences

1. **Async vs Sync**
   ```python
   # Selenium (sync)
   driver.get("https://example.com")
   element = driver.find_element(By.ID, "button")
   element.click()

   # Pydoll (async)
   await tab.go_to("https://example.com")
   element = await tab.find(id="button")
   await element.click()
   ```

2. **Finding Elements**
   ```python
   # Selenium
   element = driver.find_element(By.CLASS_NAME, "button")
   elements = driver.find_elements(By.TAG_NAME, "div")

   # Pydoll
   element = await tab.find(class_name="button")
   elements = await tab.find(tag_name="div", find_all=True)
   ```

3. **Waits**
   ```python
   # Selenium
   wait = WebDriverWait(driver, 10)
   element = wait.until(EC.presence_of_element_located((By.ID, "button")))

   # Pydoll
   element = await tab.find(id="button", timeout=10)
   ```

## Conclusion

Pydoll represents a modern approach to browser automation, leveraging Python's async capabilities and Chrome DevTools Protocol for superior performance and control. Its intuitive API, comprehensive feature set, and efficient architecture make it an excellent choice for web scraping, testing, and automation tasks.

Key takeaways:
- Direct CDP integration eliminates WebDriver overhead
- Async-first design enables efficient concurrent operations
- Event-driven architecture provides real-time browser control
- Minimal dependencies ensure fast installation and updates
- Modern API design makes common tasks simple and intuitive

Whether you're building web scrapers, automated tests, or browser-based tools, Pydoll provides the power and flexibility needed for modern web automation.
