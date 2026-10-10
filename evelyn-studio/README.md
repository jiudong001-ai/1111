# Evelyn Brooks online prototype

Chinese workbench; English deterministic readings. No login. Each export has a random URL; there is no client list. Do not commit real customer data.

Application source in this directory is offered under AGPL-3.0-only. Third-party code retains its original licenses. This scope does not relicense Maya or any other repository directory. Preserve licenses/ and dependency-licenses.json. Exact dependency source releases are available from PyPI using versions in requirements.txt; retrieve their source archives with pip download --no-deps --no-binary=:all: -r requirements.txt. The application /source endpoint offers this application's exact source and build instructions. No commercial-license grant is represented.

Build: docker build -t evelyn .
Run: docker run -p 10000:10000 -e ALLOWED_HOSTS=localhost:10000 evelyn
Render: deploy Dockerfile with this directory as context, free plan, PORT provided by Render. RENDER_EXTERNAL_HOSTNAME is automatically permitted. Additional hostnames require ALLOWED_HOSTS. All code and licenses are separate from customer exports.

The free service uses ephemeral disk; exported customer files can disappear on a restart and should be downloaded immediately. One worker serializes calculations. The free service can sleep and generation may exceed its memory limit; paid upgrades require owner approval. This is not an availability guarantee. No billing or AI API is included.
