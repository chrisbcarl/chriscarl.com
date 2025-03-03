# [chriscarl.com](http://chriscarl.com)
Incredibly simple website that just gets the point across, but it DOES look cool.

**NOTE:** the original angular implementation is tucked away in tag `refs/tags/2018-angular`.


# Development and Strategy
- Illustration by [Matt](mailto:Mgz1619@gmail.com) &copy; 2018 was conducted in OneNote with a Surface Book 2 laptop and Surface Pen.
- Select all drawings, paste in Adobe Illustrator (this way the brush strokes are registered in order rather than as some optimized mess of beziers)
- Save as SVG
- Develop [a script](./scripts/svg-to-js-test.py) to extract the individual paths, save those as a JSON
- play back the paths one by one by appending a new element to an svg canvas in the [index.html](./src/index.html). Its that stupid.


# Deployment
To be clear, this is where things get dangerous, tricky, and unclear. I do not claim to hold all of the correct answers, but here's what I've done to date to get this website deployed.
- on laptop
    - GoDaddy domain name like [4d2e15071500.com](https://www.godaddy.com/domainsearch/find?domainToCheck=4d2e15071500.com)
    - Oracle Cloud [free tier](https://www.oracle.com/cloud/free/)
        - [the actual dashboard](https://cloud.oracle.com/compute/instances)
        - create instance `VM.Standard.E2.1.Micro`
            - change image to `Ubuntu` for this exact step by step, but the difference is immaterial and down to licensing
            - **add an ssh key** you NEED to know how to use ssh at this point. otherwise there's no going forward.
        - wait about 5 minutes
        - ssh login to confirm
- on laptop
    - GoDaddy [change DNS A record](https://www.godaddy.com/help/edit-an-a-record-19239)
        - a @ `<ip address of instance>`
        - that will take 1hr to propagate, and you wont be able to access it yet unless you run the following setup script
    - change VM to permit firewall from the hypervisor's side. see [3. Enable Internet Access](https://docs.oracle.com/en-us/iaas/developer-tutorials/tutorials/apache-on-ubuntu/01oci-ubuntu-apache-summary.htm#add-ingress-rules)
        - you create "ingress rules"
    - log in via ssh
- on vm, run `setup.sh`
    1. install dependencies
    2. connect to github
    3. AFTER SETTING UP INGRESS RULES
    4. test HTTP nginx
    5. make self-signed SSL, replace fields as necessary
    6. add `chriscarl.com` config to `sites-enabled`
    7. now watch as the probes and attacks come flooding in...
- on laptop, test `http://chriscarl.com` and `https://chriscarl.com`, and the HTTPS should give you that usual "attacker" bullshit. you can check the certificate itself to see what's written and you'll see its exactly what you put in there.
- on vm, clone this repository w/ ``




# Credits
- SVG illustration by [Matt](mailto:Mgz1619@gmail.com) &copy; 2018
