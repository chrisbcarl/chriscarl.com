# TODO
- live display of internet traffic "legitimate" compared to "illegitimate" usage, typical clients, usual attack vectors, frequency, country access, amount of times the actual content in the website is accessed, etc.
    - ooooooh.... quick machine learning project + internet security. access logs alone. process the access logs, add a feature with how far apart each request is from its neighbor, just cluster or classify real and fake requests! interesting... from there you can just "deploy an ml model" on disk and have it running.
    - after assets/paths.js is loaded
    - or setDelay run an api query once to get back statistics and your likelihood of being legitimate
    - philosophically what do I need to do here:
        - i need a way to identify legitimate behavior over time, and the best way is to cluster, and I can from a bunch of data, mangle it and figure out other stuff and extract other features since its temporal
        - identify legimate behavior in-situ, and for that I need a fast model that can work with limited information, probably a tree, and rather than mangle any new data to fit what I'd clustered, I train just on annotated base data.
- github delivery action
    - cron job to pull and move, and if failed, send email?
    - cron job on launch, launch cmatrix to get some cpu action going
- security ideas:
    - ssh stricter timeouts
    - requests may only be one of a few files
    - requests may only be of a certain length or less
- robots.txt / sitemap.xml / atom.xml
- add email icon, maybe sjsu email as well
- links to major projects?
- blog?