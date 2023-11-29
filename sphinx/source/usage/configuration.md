# *Configuration*

Configuration can be loaded consistent with other SIMBA client tools via an env file. It can
also be passed to `Simba` and `SimbaSync` instances, or by invoking `libsimba.config.settings(**kwargs)`.
The constructors call the `settings()` with any kwargs passed to it. Valid values are documented below.

Values passed to constructors or the settings function override values found in the env file. Note that
values passed to constructors or `settings()` do not take the `SIMBA_` prefix. This prefix is only used for
values in the env file.

The env file is not required if key configuration is passed to constructors. These are typically

 * `AUTH_CLIENT_SECRET`
 * `AUTH_CLIENT_ID`
 * `AUTH_BASE_URL`
 * `API_BASE_URL`

The example below will read from an env file if available and override the two values
passed to the instance of `Simba`.

```shell
from libsimba.simba import Simba

Simba(API_BASE_URL="https://foo", LOG_LEVEL="INFO")

print(settings().model_dump_json(indent=2))
```

When using the env The config file, it should be in dotenv format and should be called `.simbachain.env` or `simbachain.env`
(i.e. a visible variant) or `.env`.

This can be placed in the current working directory, or can be placed anywhere if the
environment variable `SIMBA_HOME` is set. This variable should point to the directory containing the
dotenv file. The `SIMBA_HOME` variable defaults to the user's home directory, e.g. `~/`

The search order for this file is:

* `current working directory/.simbachain.env` 
* `current working directory/simbachain.env`
* `current working directory/.env`
* `SIMBA_HOME/.simbachain.env` 
* `SIMBA_HOME/simbachain.env`
* `SIMBA_HOME/.env`

The config setup supports in memory env vars taking precedence over values in the file.
All environment variables for libsimba are prefixed with `SIMBA_`.

Two auth providers are currently supported: Blocks and KeyCloak. For Blocks the configuration will look something like
below, i.e., the `SIMBA_AUTH_BASE_URL` and `SIMBA_API_BASE_URL` are the same:

```shell
SIMBA_AUTH_CLIENT_SECRET=...
SIMBA_AUTH_CLIENT_ID=...
SIMBA_AUTH_BASE_URL=https://my.blocks.server
SIMBA_API_BASE_URL=https://my.blocks.server
```

The `SIMBA_AUTH_PROVIDER` is correctly configured for Blocks.

For keycloak, the configuration will look more like, below, including a realm ID and setting the `AUTH_PROVIDER` to `KC`:

```shell
SIMBA_AUTH_CLIENT_SECRET=...
SIMBA_AUTH_CLIENT_ID=...
SIMBA_AUTH_REALM=simbachain
SIMBA_API_BASE_URL=https://my.blocks.server
SIMBA_AUTH_BASE_URL=https://my.keycloak.server
SIMBA_AUTH_PROVIDER=KC
```

The `AUTH_FLOW` should currently not be changed as only `client_credentials` is supported.

These values can also be directly set an environment variables if you don't use a dot env file.

When making requests, a Login object can be passed in containing a client ID and secret. If this is not
passed into the methods, a default Login object is created using the environment variables `SIMBA_AUTH_CLIENT_SECRET`
and `SIMBA_AUTH_CLIENT_ID` described above. Alternatively, if a `headers` dict is passed in and this contains
an `Authoroization` key, this is assumed to be a valid bearer token and is used instead of loggin in.

## Additional Configuration Options

Further configuration options available in the simba env file:

* `SIMBA_WRITE_TOKEN_TO_FILE`: boolean. If set to true, this will cache tokens to file. Otherwise they are
    cached in memory. Default is true.
* `SIMBA_TOKEN_DIR`: string. If WRITE_TOKEN_TO_FILE is true, this should be set to where tokens should be stored.
    Default is "./"
* `SIMBA_CONNECTION_TIMEOUT`: float. Connection timeout in seconds for requests. Default is 5 which is the httpx default.
* `SIMBA_LOG_LEVEL`: set the logging level. Can be one of `CRITICAL`, `FATAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, `NOTSET`

## Logging

To configure logging, there are two options:
* For simply changing the log level, set the `SIMBA_LOG_LEVEL` in the env file (see above). This sets the level
  of the loggers in the `libsimba` namespace only. 
* To fully configure logging, set the `SIMBA_LOG_CONFIG` environment variable pointing to a logging file.
  If you don't set that the default `libsimba/logging.conf` configuration will be used. If you provide a logging
  config file that is json and has a `.json` file extension, then it will be loaded as a dictionary config.
  Otherwise `ini` file format is assumed. Ensure there is a `libsimba` logger defined.
