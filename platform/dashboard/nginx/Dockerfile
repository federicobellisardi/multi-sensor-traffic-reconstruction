FROM nginx:1.21-alpine

RUN apk add openssl;

RUN mkdir -p /etc/ssl/private/
RUN openssl req -x509 -nodes \
  -days 365 -subj "/C=CA/ST=QC/O=mover, Inc./CN=mover.com" \
  -addext "subjectAltName=DNS:mover.com" \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/mover-selfsigned.key \
  -out /etc/ssl/certs/mover-selfsigned.crt;

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d


