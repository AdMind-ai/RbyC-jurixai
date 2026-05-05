# GitHub Actions Secrets

Create these repository secrets before enabling the workflows:

## Shared

- `LIGHTSAIL_HOST`: Public IP or domain of the Lightsail instance
- `LIGHTSAIL_USERNAME`: SSH user, for example `ubuntu`
- `LIGHTSAIL_SSH_PRIVATE_KEY`: Private SSH key used by GitHub Actions

## Backend

- `LIGHTSAIL_APP_PATH`: Absolute path of the cloned repository on the server

## Notes

- The frontend workflow publishes files to `/var/www/rbyc-frontend`
- The backend workflow runs `docker compose -f infra/docker-compose.yml up -d --build`
- Keep the application `.env` only on the server, not in GitHub secrets, unless you later want fully remote provisioning
