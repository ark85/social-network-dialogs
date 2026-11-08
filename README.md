# social-network-dialogs

## How to migrate dialog messages from social-network to social-network-dialogs

Migration must be done on stopped tarantool instances

* Copy the volume. Run this from either repository
  * Call `docker run --rm --user root -v social-network_tarantool_data:/from:ro -v social-network-dialogs_tarantool_data:/to tarantool/tarantool:3.3.5 sh -c "find /to -mindepth 1 -delete && cp -a /from/. /to/ && chown -R tarantool:tarantool /to"`
    * The container runs as user `tarantool`, so the copied files are given back to that user
