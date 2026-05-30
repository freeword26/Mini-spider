FROM python:3.12-slim

LABEL maintainer="System Manager"
LABEL version="2.0.0"
LABEL description="MAX ROOM — Virtual collaboration space for agents and humans"

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && rm -rf /root/.cache/pip

RUN python -c "from spidermax_room import RoomEngine, Room, Member; print('Build OK')"

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from spidermax_room import RoomEngine; print('OK')" || exit 1

CMD ["python"]
