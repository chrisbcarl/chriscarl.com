EXPECTED_ROUTES = set(
    # omitting '/', '/favicon.ico', '/files/favicon.ico' because everyone has those routes
    [
        # # way too common ones
        # '/',
        # '/favicon.ico',
        # '/files/favicon.ico',
        # less common
        '/assets/fontawesome/file-pdf-solid.svg',
        '/assets/fontawesome/linkedin-in-brands-solid.svg',
        '/assets/fontawesome/github-brands-solid.svg',
        '/assets/fontawesome/youtube-brands-solid.svg',
        '/assets/paths.js',
    ]
)
EXPECTED_PROTOCOLS = set(['HTTP/1.1', 'HTTP/1.0'])
EXPECTED_VERBS = set(['GET'])
EXPECTED_REFERERS = set(['http://chriscarl.com', 'http://www.chriscarl.com', 'http://159.54.179.175'])
EXPECTED_REFERERS.update([f'{uri}/' for uri in EXPECTED_REFERERS])
EXPECTED_REFERERS.update([ele.replace('http:', 'https:') for ele in EXPECTED_REFERERS])
EXPECTED_REFERERS.update(['https://www.google.com/', 'https://www.bing.com/', 'https://duckduckgo.com/'])
