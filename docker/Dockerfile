FROM python:3.12-slim

# ── System deps: ODBC Driver 18 for SQL Server ──────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg2 \
        apt-transport-https \
        unixodbc \
        unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ──────────────────────────────────────────────────────────────
COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Install context_renderer package (editable) ──────────────────────────────
COPY context_renderer/ /app/context_renderer/
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
RUN pip install --no-cache-dir -e /app

# ── Jupyter config ───────────────────────────────────────────────────────────
RUN jupyter notebook --generate-config \
    && echo "c.NotebookApp.token = ''"             >> /root/.jupyter/jupyter_notebook_config.py \
    && echo "c.NotebookApp.password = ''"          >> /root/.jupyter/jupyter_notebook_config.py \
    && echo "c.NotebookApp.open_browser = False"   >> /root/.jupyter/jupyter_notebook_config.py \
    && echo "c.NotebookApp.ip = '0.0.0.0'"         >> /root/.jupyter/jupyter_notebook_config.py

WORKDIR /notebooks
EXPOSE 8888

CMD ["jupyter", "notebook", "--allow-root"]
