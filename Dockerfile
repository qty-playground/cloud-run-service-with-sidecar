FROM python:3.12-slim

# Install gost for TCP port forwarding through SOCKS5 proxy
ADD https://github.com/ginuerzh/gost/releases/download/v2.12.0/gost_2.12.0_linux_amd64.tar.gz /tmp/gost.tar.gz
RUN tar -xzf /tmp/gost.tar.gz -C /usr/local/bin/ gost && rm /tmp/gost.tar.gz

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "start.sh"]
