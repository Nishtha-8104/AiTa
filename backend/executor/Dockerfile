FROM python:3.11-slim

RUN printf 'Acquire::Retries "15";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' \
      > /etc/apt/apt.conf.d/80-retries \
 && for attempt in 1 2 3 4 5; do \
      apt-get update && apt-get install -y --no-install-recommends gcc g++ && break; \
      echo "apt attempt $attempt failed, retrying"; sleep $((attempt * 10)); \
    done \
 && command -v gcc \
 && command -v g++ \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./executor

RUN useradd --create-home --uid 10001 sandbox
USER sandbox

EXPOSE 8080
CMD ["uvicorn", "executor.main:app", "--host", "0.0.0.0", "--port", "8080"]
