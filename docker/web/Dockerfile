# Web app: FastAPI backend (runs in the taskgen/Sage image, imports taskgen
# from the bind-mounted repo) + the React SPA built in a node stage.
#
# Targets: `backend` (API only; used by `make web-dev` and `make test-web`)
#          `web`     (API + built SPA; `make web`)

FROM node:22-bookworm-slim AS spa
WORKDIR /src
COPY webapp/frontend/package.json webapp/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY webapp/frontend/ ./
RUN npm run build

FROM ca-course/taskgen:latest AS backend
USER root
COPY webapp/backend/requirements.txt /tmp/web-requirements.txt
RUN sage -pip install --no-cache-dir -r /tmp/web-requirements.txt \
 && sage -pip check
ENV PYTHONPATH=/work:/work/webapp/backend \
    TASKGEN_REPO=/work
EXPOSE 8000
ENTRYPOINT ["sage", "-python", "-m", "uvicorn", "taskgen_web.app:create_app", "--factory", \
            "--host", "0.0.0.0", "--port", "8000"]

FROM backend AS web
COPY --from=spa /src/dist /opt/webapp/dist
ENV WEB_STATIC_DIR=/opt/webapp/dist
