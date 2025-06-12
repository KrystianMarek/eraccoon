ARG PYTHON_VERSION="python:3.10"

FROM $PYTHON_VERSION AS compiler
ENV PYTHONUNBUFFERED=1

WORKDIR /app/

RUN python -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

FROM $PYTHON_VERSION AS runner
WORKDIR /app/
COPY --from=compiler /opt/venv /opt/venv

# Enable venv
ENV PATH="/opt/venv/bin:$PATH"
COPY src /app/src
COPY main.py /app/main.py

CMD ["python", "/app/main.py"]