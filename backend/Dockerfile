FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN --mount=type=secret,id=build_ca if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; pip install --no-cache-dir -r requirements.lock && useradd -m -u 10001 careerorbit
COPY --chown=careerorbit:careerorbit backend/app ./app
RUN mkdir /data && chown careerorbit:careerorbit /data
USER careerorbit
ENV STORAGE_DIR=/data/resumes
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
