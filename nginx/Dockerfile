FROM docker.io/node AS node_modules
RUN yarn add jquery@3.7.0 html5-qrcode@2.3.8

FROM docker.io/nginx
COPY --from=node_modules --chmod=755 node_modules /usr/share/nginx/js
