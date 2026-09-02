FROM node:20-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    NODE_ENV=production

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 10000

CMD ["./start.sh"]
