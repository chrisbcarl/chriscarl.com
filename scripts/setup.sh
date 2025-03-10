# login
ssh ubuntu@159.54.179.175  # default username is `ubuntu` not `root`




# install dependencies
sudo apt update -y
sudo apt install net-tools nginx nmap netfilter-persistent tree -y -y


# connect to github
ssh-keygen
cat ~/.ssh/id_ed25519.pub  # add this to github
ssh-add -i ~/.ssh/id_ed25519
sudo chmod -R 700 ~/.ssh  # # correct the permissions of your ssh keys, should be access only to yourself.
ll ~/.ssh  # THIS DOESNT WORK ANYMORE
sudo ls -lah ~/.ssh  # this does
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519



# AFTER SETTING UP INGRESS RULES
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save


# test HTTP nginx
netstat -lntu  # you should see ports 53 (DNS), 68 (DHCP) 111 (Sun/Oracle Remote Protocol) and 80/443
nmap localhost -p 80
nmap localhost -p 443
sudo systemctl restart nginx
sudo systemctl status nginx
curl http://$(hostname -i)  # yes youre querying localhost, it still proves the same point


# make self-signed SSL, replace fields as necessary
domain="chriscarl.com"
openssl req -new -x509 -days 30 -nodes -newkey rsa:2048 \
    -keyout /etc/pki/nginx/$domain.key \
    -out /etc/pki/nginx/private/$domain.crt \
    -subj "/C=US/O=Oracle/OU=null/ST=CA/L=San Jose/CN=$domain"
sudo chown -R www-data:www-data /etc/pki/nginx/$domain.crt /etc/pki/nginx/private/$domain.key  # this username comes from the nginx conf
sudo chmod 755 /etc/pki/nginx/$domain.crt /etc/pki/nginx/private/$domain.key  # ubuntu can mod, everyone else can read only


# add `chriscarl.com` to `/etc/nginx/sites-enabled/chriscarl.com` in this repo to the same location
sudo nginx -t  # make sure it works
sudo systemctl restart ngnix
sudo systemctl status nginx
curl -k https://$(hostname -i)  # ignore ssl safe


# clone the respository in one of your own folders (since ssh demands it)
mkdir ~/src
cd ~/src
git clone git@github.com:chrisbcarl/chriscarl.com.git
sudo mv chriscarl.com/ /var/www/html/


# SSL
sudo apt remove certbot -y  # install certbot
sudo apt update -y
sudo apt install snapd -y
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot  # put it on the path with a shortcut
which certbot
# sudo certbot --nginx  # self modify the nginx conf
sudo certbot certonly --nginx  # generate certs to disk, careful, it is interactive.
sudo ls -lah /etc/letsencrypt/live/chriscarl.com
sudo certbot renew --dry-run  # setup renewal
systemctl list-timers --all  # list out all cron jobs
sudo vim /etc/nginx/sites-enabled/chriscarl.com  # edit and use cert.pem and privkey.pem
sudo systemctl restart nginx


# now watch as the probes and attacks come flooding in...
tail -f /var/log/nginx/access.log
