FROM python:3.11-slim

RUN pip install --no-cache-dir sfmon

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
