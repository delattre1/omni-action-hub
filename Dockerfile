FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-51f83158a70a383f03a4d03dbd8b6ea102cf0361@sha256:253d7ed3409effa7fa59113d93b4b79bb731d8264cdaf4cd60294924d0110a2e

COPY pyproject.toml /opt/omni/pyproject.toml
COPY src/ /opt/omni/src/
# Install only into the inherited interpreter; pinned direct dependencies.
RUN uv pip install --python /opt/hermes/.venv/bin/python /opt/omni \
 && /opt/hermes/.venv/bin/python -c 'from omni.gateway import load_transport; load_transport(); from gateway.platforms.base import get_image_cache_dir'
COPY runtime/persona.md /opt/hermes/plow-seed/persona.md
# Reuse plow-init and the bundled transport, replacing only general-agent
# dispatch with the deterministic queue. No image-owned credential bootstrap.
COPY --chmod=0755 runtime/gateway-run /etc/s6-overlay/s6-rc.d/hermes-gateway/run
COPY vendor/client.pin /opt/omni/client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/omni/client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/omni/client.pin)"; \
    curl -fsS --max-time 60 -o /opt/omni/agent_index_client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/standalone/agent_index_client.py"; \
    echo "$want  /opt/omni/agent_index_client.py" | sha256sum -c -; \
    chmod 0644 /opt/omni/agent_index_client.py
COPY runtime/s6-overlay/ /etc/s6-overlay/
COPY LICENSE NOTICE /usr/share/doc/omni-action-hub/
COPY LICENSES/ /usr/share/doc/omni-action-hub/LICENSES/
RUN chmod 0755 /etc/s6-overlay/s6-rc.d/omni-index/run
