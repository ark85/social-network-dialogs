# social-network-dialogs

## How to start

* Fill `.env` file (see `.env.example`)
  * Generate `JWT_SECRET` by e.g. `Encoders.BASE64.encode(Jwts.SIG.HS256.key().build().getEncoded())` (or any other way)
* Call `docker compose -f ./docker-compose.yml -p social-network-dialogs up -d`
  * Add `--build` option to recreate image after application changes

## How to migrate dialog messages from social-network to social-network-dialogs

Migration must be done on stopped tarantool instances

* Copy the volume. Run this from either repository
  * Call `docker run --rm --user root -v social-network_tarantool_data:/from:ro -v social-network-dialogs_tarantool_data:/to tarantool/tarantool:3.3.5 sh -c "find /to -mindepth 1 -delete && cp -a /from/. /to/ && chown -R tarantool:tarantool /to"`
