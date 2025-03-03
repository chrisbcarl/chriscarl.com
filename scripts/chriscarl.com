# /etc/nginx/sites-enabled/chriscarl.com

server {
    listen                      80;
    server_name                 chriscarl.com 159.54.179.175;
    # return 301                  https://$host$request_uri;
    root                        /var/www/html/chriscarl.com/src;
    location / {
        # First attempt to serve request as file, then
        # as directory, then fall back to displaying a 404.
        try_files               $uri $uri/ =404;
    }
}

server {
    listen                      443 ssl;
    server_name                 chriscarl.com 159.54.179.175;

    ssl_certificate             "/etc/pki/nginx/chriscarl.com.crt";
    ssl_certificate_key         "/etc/pki/nginx/private/chriscarl.com.key";
    ssl_session_cache           shared:SSL:1m;
    ssl_session_timeout         10m;
    # ssl_ciphers                 PROFILE=SYSTEM;
    ssl_prefer_server_ciphers   on;

    root                        /var/www/html/chriscarl.com/src;
    location / {
        # First attempt to serve request as file, then
        # as directory, then fall back to displaying a 404.
        try_files               $uri $uri/ =404;
    }
    # location / {
    #     proxy_pass              http://127.0.0.1:5000;
    # }
    # error_page   500 502 503 504  /50x.html;
    # location = /50x.html {
    #     root   html;
    # }
}