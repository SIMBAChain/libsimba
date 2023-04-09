# Documentation

## *Prerequisites*

* Python >= 3.9
* Poetry (https://python-poetry.org/docs/)


## *Installation*


```
pip install libsimba
```

### *Install for development*

```
git clone https://github.com/SIMBAChain/libsimba.git
cd libsimba
poetry install
```

## *Configuration*

Configuration is loaded consistent with other SIMBA client tools.
The config file should be in dotenv format and should be called `.simbachain.env` or `simbachain.env`
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

### Additional Configuration Options

Further configuration options available in the simba env file:

* `SIMBA_WRITE_TOKEN_TO_FILE`: boolean. If set to true, this will cache tokens to file. Otherwise they are
    cached in memory. Default is true.
* `SIMBA_TOKEN_DIR`: string. If WRITE_TOKEN_TO_FILE is true, this should be set to where tokens should be stored.
    Default is "./"
* `SIMBA_CONNECTION_TIMEOUT`: float. Connection timeout in seconds for requests. Default is 5 which is the httpx default.
* `SIMBA_LOG_LEVEL`: set the logging level. Can be one of `CRITICAL`, `FATAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, `NOTSET`

### Logging

To configure logging, there are two options:
* For simply changing the log level, set the `SIMBA_LOG_LEVEL` in the env file (see above). This sets the level
  of the loggers in the `libsimba` namespace only. 
* To fully configure logging, set the `SIMBA_LOG_CONFIG` environment variable pointing to a logging file.
  If you don't set that the default `libsimba/logging.conf` configuration will be used. If you provide a logging
  config file that is json and has a `.json` file extension, then it will be loaded as a dictionary config.
  Otherwise `ini` file format is assumed. Ensure there is a `libsimba` logger defined.

## *Instantiate the SIMBA client*

```python
from libsimba.simba import Simba

simba = Simba() 
```

The Simba client object runs asynchronously by default, so if you would like to run synchronous code instead, you should use the SimbaSync client:

```python
from libsimba.simba import SimbaSync

simba_async = SimbaSync()
```

All method signatures for both sync and async clients are the same except the async client functions are largely async and should be awaited.

```python
from libsimba import Simba

simba = Simba()

# Using Simba's default async behavior

# Using Simba and async/await
class Example:
    async def get_me(self):
        me = await simba.whoami()
        print(me)

```

```python
from libsimba import SimbaSync

simba_sync = SimbaSync()

# Using SimbaSync with synchronous behavior
class SyncExample:
    def get_me(self):
        me = simba_sync.whoami()
        print(me)

```

returned objects are currently not typed, i.e., the SDK returns `dict` instances.

## *User and Account Functions*

The Simba class provides some functions focussed on users and accounts:

* Get the current user (`def whoami`)
* Get the balance of an address (`def balance`)
* Fund an address (`def fund`)
* Set the current user custodial wallet for a blockchain (`def set_wallet`)
* Get the current user custodial wallet (`def get_wallet`). *NOTE: This currently returns a JSON blob.*
  *You can use the parse_wallet function to extract the address for a given blockchain type and blockchain.*
  *`blockchain_type` is typically `ethereum` for EVM chains, and `blockchain` is the name of the network, e.g.,*
  *`Quorum` or `mumbai` for example. The full list of blockchains is returned from the `get_blockchain` method (see below).* 

## *Platform Functions*

The Simba class provides functions to list platform capabilities:

* List available blockchains (`def get_blockchains`)
* List available off chain storage (`def get_storage`)

## *Deploying Smart Contracts*

Smart contracts have a lifecycle. They atart out as contract designs. These are basically code. You can update
the code and the design, along with its metadata will change. Before deployment, a contract artifact is created.
This is a snapshot of the design at a given point in time. Given the frozen artifact, a deployed contract can be
created. This deploys the code to a specific chain.

The example below compiles a contract. The parameters are as follows:

* `org` - the org name
* `name` - a name for the contract
* `code` - the contract code
* `target_contract` - typically the name of the contract.
   This ensures this contract will be the one that API metadata will be generated.
* `binary_targets` - this is a list of contracts to return binary code for. This allows
  then to be deployed. In the case of a simple deployment of a single contract this can be
  set to the contract name, same as 'target_contract'.
* `libraries` - a dictionary with keys defining library names and values being their deployed addresses. Used for
  linking external libraries.
* `encode` - whether to base64 encode the code string. Default is true. Leave this if the input code has not
  been Base64 encoded.
* `model` - this should be set to `aat`

```python
# Read a contract from file
with open("./TestContract.sol", "r") as sol:
    code = sol.read()
saved_data = await simba.save_design(
    org="my-org",
    name="my-contract",
    code=code,
    target_contract="TestContract",
    model="aat",
    binary_targets=["TestContract"],
)
```

Next we can create an artifact from the design and deploy it.
* `org` - the org name
* `api_name` - field defines the url path component that will be used for the deployed contract. This can be used
  when invoking the contract as the `contract_name` field to identify the target contract.
* `app` - the application to deploy to.
* `storage` - used to define a storage backend for saving off chain data.
* `blockchain` - the name of the blockchain to deploy to. 


```python
artifact_data = await simba.create_artifact(org="my-org", design_id=saved_data.get("id"))
address, contract_id = await simba.wait_for_deploy_artifact(
    org="my-org",
    app="my-app",
    api_name="my-contract-api",
    artifact_id=artifact_data["id"],
    storage="azure",
    blockchain="Quorum",
)
```
This returns the address of the newly deployed contract along with the uuid of the deployed contract in the database.


## *Invoking Smart Contract Methods*

Smart contract methods come in two flavours:

* Methods that send data to the contract and change the state of the contract and/or result in a transaction being 
  added to the chain. These are sometimes called `setters`. These are invoked using the HTTP `POST` method.
  The API allows you to query for transactions
  created by these methods using HTTP `GET` along with query filters.
* Methods that are accessors, also known as `getters`.
  These call the contract but do not change its state and do not result in a transaction
  being added to the chain. These are invoked using the HTTP `GET` method. You cannot query for transactions from these
  methods because they do not create transactions.

The Simba class provides several methods for calling methods in smart contracts. These take the SIMBA `app` name,
the contract API name and the method name. The `inputs` parameter contains a dict of method parameter values
keyed to their parameter names.

```python
inputs = {
    "person": {
        "name": "The Laughing Gnome",
        "age": 32,
        "addr": {
            "street": "Happy Street",
            "number": 10,
            "town": "Funsville",
        },
    }
}
txn = await simba.submit_contract_method(
    app_id="my-app",
    contract_name="my-contract",
    method_name="myMethod",
    inputs=inputs,
)
```
To submit a call to the method that accepts files, you add the `files` parameter and pass in a `FileDict` object. A
`FileDict` takes one or more `File` objects. These encapsulate files on the local file system. `File` objects have
a name, a mime type, and a path or file pointer. Typically, a path is passed in from which the file name, mime type
are derived with the file pointer being opened before sending and closed after sending by the request object. If
the `close_on_complete` field is set to false, the file pointer is not closed and should be closed by the application.

```python
files = FileDict(
    files=[
        File(path="./data/file1.txt", name="f1.txt", mime="text/plain"),
        File(path="./data/file2.txt", name="f2.txt", mime="text/plain"),
    ]
)

txn = await simba.submit_contract_method(
    app_id="my-app",
    contract_name="my-contract",
    method_name="myMethod",
    inputs=inputs,
    files=files
)
```

Methods that allow file uploads have a special `_bundleHash` parameter. This should be left empty when submitting the
transaction along with files. Blocks takes the files and sends them to the configured off chain storage, hashing
them along the way and producing a JSON manifest file of all files uploaded. This manifest file is then hashed, and
that hash is put in the `_bundleHash` field before writing to chain. This provides verifiability of file content.


As we well as methods that create transactions, some contract methods are getter functions that return values
from the contract and do not add to the chain. These can be called using HTTP GET:

```python
getter_result = simba.call_contract_method(
        app_id=app,
        contract_name=api_name,
        method_name="tokenUri",
        args=MethodCallArgs(args={"tokenId": "349873423984143"}),
    )
```
The MethodCallArgs class is a simple wrapper around a dict of args that is appended to the query string of the request.

## *Querying Smart contract Methods*

For methods that are not getters, you can query for past transactions created by submitting transactions to the method.
Query calls optionally take a SearchFilter object that has various fields that can filter responses.

* The `filters` field is a list of `FieldFilter` objects that point to a field, contain a value and an operator.
  For JSON field inputs, dotted paths can be used to target elements within the JSON.
* The `fields` field allows you to specify the fields to return.
* The `limit` and `offset` fields can be used to specify page size and start offset.

Below we create a filter that filters on the `person.age` field of the transaction inputs, asking for results
where that value is greater than 2. We limit page size to 2 and ask only for the `state`, `transaction_hash`
and `inputs` fields.

```python
query = SearchFilter(
    filters=[
        FieldFilter(field="inputs.person.age", op=FilterOp.GT, value=2),
    ],
    fields=["state", "transaction_hash", "inputs"],
    limit=2,
    offset=0,
)

generator = await simba.list_transactions_by_method(
        app_id=app,
        contract_name=api_name,
        method_name=self.query_function(),
        query_args=query,
    )
async for result in generator:
    # automatically pages
    print(result)
```

Note that this call returns a generator that can be iterated. Functions that start with
the prefix `list_` return generators that call the next page
until no more results are available.

Methods that retrieve multiple objects and start with the prefix `get_` return a list from a single page, and hence
the number of results is limited to a single page size.

## *Getting File Bundle Information* 

The API allows you get a JSON manifest for a bundle, to download the bundle as a `tar.gz` file, or to download
a particular file inside a bundle.

```python
bundle_hash = "348374328746324783642343241"

# download the manifest JSON using the bundle hash
manifest = await simba.get_manifest_for_bundle_from_bundle_hash(
    app_id=app, contract_name=api_name, bundle_hash=bundle_hash
)

# download the bundle using the bundle hash
await simba.get_bundle(
    app_id=app,
    contract_name=api_name,
    bundle_hash=bundle_hash,
    download_location="./bundle.tar.gz",
)

# download a file using the bundle hash and the file name
await simba.get_bundle_file(
    app_id=app,
    contract_name=api_name,
    bundle_hash=bundle_hash,
    file_name="my_file.txt",
    download_location="./my_file.txt",
)
```

## *Contract Client Classes*

The library provides utilities that represent a single contract API via the `SimbaContractSync` and `SimbaContract`
classes. These can be created via the respective sync and async Simba classes passing in the Simba instance
as well as the contract app name and api name. As well as simplifyng calls to contract methods, they also
perform validation on method inputs based on the contract metadata before making calls.


