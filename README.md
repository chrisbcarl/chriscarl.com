# [chriscarl.com](http://chriscarl.com)
Incredibly simple website that just gets the point across, but it DOES look cool.

**NOTE:** the original angular implementation is tucked away in tag `refs/tags/2018-angular`.


# Development and Strategy
- Illustration by [Matt](mailto:Mgz1619@gmail.com) &copy; 2018 was conducted in OneNote with a Surface Book 2 laptop and Surface Pen.
- Select all drawings, paste in Adobe Illustrator (this way the brush strokes are registered in order rather than as some optimized mess of beziers)
- Save as SVG
- Develop [a script](./scripts/svg-to-js-test.py) to extract the individual paths, save those as a JSON
- play back the paths one by one by appending a new element to an svg canvas in the [index.html](./src/index.html). Its that stupid.


# "Powered by"
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) - for a VM, no cloud abstractions, any injury is self-inflicted
- [nginx](https://nginx.org/) - webserver, goated
- [Bootstrap](https://getbootstrap.com/) - css styling, i know its overused/lame/whatever
- [FontAwesome](https://getbootstrap.com/) - I actually steal the SVG's directly
- [letsencrypt.org](https://letsencrypt.org) - SSL w/ `certbot` via `Lets Encrypt CA`
- [Matt](mailto:Mgz1619@gmail.com) - original sketch done in 2018


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
- on vm
```bash
git clone git@github.com:chrisbcarl/chriscarl.com.git
sudo mv chriscarl.com/ /var/www/html/
```
- ssl, use [letsencrypt.org](https://letsencrypt.org)
    - letsencrypt is a Certificate Authority just like Comodo, DigiCert, etc, but maintained by donations, does not offer OU validation, etc. For single websites, this is perfect.
    - consult `SSL` in `setup.sh`


# Other Good Articles
- https://www.godaddy.com/help/edit-an-a-record-19239
- https://docs.oracle.com/en/learn/ol-nginx/#enable-and-start-the-nginx-service
- https://linuxconfig.org/how-to-install-nginx-on-linux
- https://linuxnightly.com/allow-port-through-firewall-in-ubuntu/
- https://serverfault.com/questions/985895/how-to-setup-nginx-apache-on-oracle-cloud-instance
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://docs.oracle.com/en/learn/ol-nginx/#update-the-firewall
- https://docs.oracle.com/en-us/iaas/developer-tutorials/tutorials/apache-on-ubuntu/01oci-ubuntu-apache-summary.htm
- https://medium.com/@union_io/swapping-fill-color-on-image-tag-svgs-using-css-filters-fa4818bf7ec6
- https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent?platform=linux
- https://www.tecmint.com/set-ssh-directory-permissions-in-linux/
- https://letsencrypt.org/how-it-works/
- https://certbot.eff.org/instructions?ws=nginx&os=snap
- https://www.feistyduck.com/books/bulletproof-tls-and-pki/


# Credits
- SVG illustration by [Matt](mailto:Mgz1619@gmail.com) &copy; 2018
