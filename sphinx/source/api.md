# API Notes

This page describes aspects of the API that may need explanation.

## *Contract Deployment*

*NOTE: Angle brackets (`<` and `>`) are used to designate variables.*

SIMBA has the concept of contract designs, contract artifacts and deployed contracts. In addition, it has the
concept of supporting artifacts such as libraries.

* Contract Design - a design represents code that is compiled to binary and potentially lined with libraries.
    Contract designs are mutable, that is you can change the code and update the contract.
* Contract Artifact - an artifact is a snapshot of a design at a point in time. Artifacts are what are deployed.
* Deployed Contract - these are artifacts that are bound to a blockchain, i.e., they have an address and can be invoked.
    Contracts are deployed to an Application. An application is simply an umbrella component to group deployed
    contracts. To create an application send an HTTP `POST` request to `v2/organisations/<MY_ORG>/applications/`.
    The JSON payload is:
    * `name`: A globally unique name for the application.
    * `display_name`: An optional display name for the application.

### Compiling Contracts

The following will assume a solidity contract. 

To compile a contract, send an HTTP `POST` to `v2/organisations/<MY_ORG>/contract_designs/`
where `<MY_ORG>` is an organisation you have write access to.

The JSON payload is:

* `code`: base64 encoded contract solidity source code
* `language`: 'solidity'
* `name`: A non-unique name for the design. This does not have to match the name of the contract in the solidity.
* `target_contract`: `<CONTRACT_NAME>`. This field identifies the contract you want an HTTP API for. In the case
    of a simple contract deployment, this is not required as there is only a single contract. However, if there
    are related contracts in the compilation, this ensures the correct contract is the primary contract to be exposed
    via the Blocks API.
* `binary_targets`: A list containing the <CONTRACT_NAME>. Again, this is optional, but worth including if you want to
    restrict the artifacts that should be deployed at deployment time. It defines
    the contracts for which binary info should be returned. Without this info, the artifact cannot be deployed. Consider
    a contract that depends on external libraries, for which you already know the addresses. In this case you want to
    not have those deployed when deploying the contract as they are already deployed. In this case, the binary targets
    list can be used to restrict deployment to only the main contract.
* `libraries`: Optional dictionary of external libraries that are already deployed and should be linked to the contract.
    The key values of the dictionary are `<LIBRARY_NAME>` key and value of `<ADDRESS>`. If libraries are included, they
    are linked into the binary content of the compiled contract.

A return status of 200/201 signifies successful compilation.

The return value is a contract design object. This includes generated metadata that is used to create the API as well
as compilation information such as the binary contract. The `id` field is important as it is used to create an
artifact from the design.

### Creating a Contract Artifact

Using the contract design ID in the `id` field of the returned design, send an HTTP `POST` to
`v2/organisations/%s/contract_artifacts/`. The JSON payload is:

* `design_id`: `<CONTRACT_DESIGN_ID>`

A return value of 200/201 signifies success.

The return value is a contract artifact object. This is virtually identical to a design.
The `id` field is important as it is used to deploy the contract.

### Deploying a Contract Artifact

Using the contract artifact ID in the `id` field of the returned artifact, send an HTTP `POST` to
`v2/organisations/<MY_ORG>/deployments/`. The JSON payload is:

* `blockchain`: the blockchain name as known to Blocks, e.g. `mumbai`, or `Quorum`. The available blockchains
    can be retrieved from the `v2/organisations/<MY_ORG>/blockchain/` endpoint.
* `storage`: the name of the off chain storage. Defaults to `no_storage`. The available stores
    can be retrieved from the `v2/organisations/<MY_ORG>/storage/` endpoint.
* `api_name`: deployed contract API name. This is used in the URL once it is deployed and therefore is restricted
    to alphanumeric characters, dashes and underscores. It needs to be unique within an application.
* `artifact_id`: the artifact ID
* `display_name`: an optional display name
* `app_name`: the containing Application to deploy to
* `args`: optional arguments for deploying. This is only needed for contracts that take arguments in the constructor.
    The args are a dictionary where the keys are the constructor parameter names and the values are parameter values.

A return status of 200/201 response means all went well.

The return value is a deployment object.

Important fields are:

* `id`: the id of the deployment object. This can also be used to wait for deployment.
* `state`: the current state of the deployment. For a simple deployment the state is likely to be `COMPLETED`.
    For more complex deployments, it may still be in the `EXECUTING` state. If it has failed for some reason,
    it will be in a `FAILED` state. In this case, the `error` field should be populated with the reason.

If the deployment is not in a `COMPLETED` state, you can wait for the deployment to complete.
Poll the `/v2/organisations/<MY_ORG>/deployments/<DEPLOYMENT_ID/` endpoint with HTTP `GET`
and wait for the `state` field to be `COMPLETED` or `FAILED`.

If in a `COMPLETED` state, the deployment's field `primary` can be queried.
This is a JSON object that contains an `address` field. This should be populated once the deployment has finished.
The primary field `deployed_artifact_id` contains the ID of the deployed contract. Using this ID, you call
inspect the deployed contract object by sending an HTTP `GET` to
`/v2/organisations/<MY_ORG>/deployed_contracts/<DEPLOYED_CONTRACT_ID>/`.

The contract will be available under the name of the Application it was deployed to, and the api
name when deploying. E.g., to send transactions to methods use:
`/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/<METHOD_NAME>/`


## Calling and Querying Contract Methods 

Smart contract methods come in two flavours:

* Methods that send data to the contract and change the state of the contract and/or result in a transaction being 
  added to the chain. These are sometimes called `setters`. These are invoked using the HTTP `POST` method.
  The API allows you to query for transactions
  created by these methods using HTTP `GET` along with query filters.
* Methods that are accessors, also known as `getters`.
  These call the contract but do not change its state and do not result in a transaction
  being added to the chain. In Solidity terms these are modified with either `view` or `pure`.
  These are invoked using the HTTP `GET` method. You cannot query for transactions from these
  methods because they do not create transactions.

As a result, HTTP `GET` is used for two purposes, depending on the nature of the method and `POST` can only be used
against methods that are not getters.

### Calling Methods

When submitting a transaction to a contract method via `POST`, the payload is dependent on the method parameters.
The payload is a JSON object where the keys are the method parameter names and the values are the method parameters.
The endpoint is `/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/<METHOD_NAME>/` where `<METHOD_NAME>` is the name
of the contract method being called.

For example, given a function defined as below:

```solidity
function myFunction (
    address myAddress,
    uint16 myInt
    )
public {
    ...
}
```

The JSON payload would be as follows:

```
{
  "myAddress": "0xa508dd875f10c33c52a8abb20e16fc68e981f186",
  "myInt": 12
}
```

Note that Solidity address types as well as byte arrays are encoded as hex strings.

When calling a getter, the request goes to the chain to get the current state form the contract and return the requested
value. The endpoint is the same as for `POST`ing:
`/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/<METHOD_NAME>/`.
Any parameters are turned into HTTP query parameters. Note this restricts the nature of the values a little, although
URL encoded JSON is valid for complex types.

### Off Chain Data

The special `_bundleHash` parameter name is used to determine whether a method has been defined to accept file uploads.
This field should not be populated by the client side. Instead, if files are present in the current
request and the field is defined on the method, then the files are written to off-chain storage
with the JSON manifest being constructed and written out alongside the files.
The manifest contains the content hashes of the files along with metadata and timestamp.
The content hash of the JSON manifest is then set to be the value of the `_bundleHash` field.
This hash value is then what ends up on the chain in the transaction.

For example, given a function defined as below:

Note that these transactions must be submitted using `multipart/form-data` rather than `application/json` in order
to upload files.

When the transaction completes, the `_bundleHash` field will be populated with a hash value. This value can then
be used to query for the JSON manifest, the gzipped bundle, or files within the bundle.

```solidity
function myFunction (
    address myAddress,
    uint16 myInt,
    string memory _bundleHash
    )
public {
    ...
}
```

The payload would be a multipart message containing `myAddress` as a string, `myInt` as a string, as multipart
interprets everything as strings, and then file uploads. The `_bundleHash` field is left blank.

When looking at the `inputs` of the completed transaction, the `_bundleHash` field will be populated with the
content hash of the JSON manifest, e.g.:

```
{
  "myAddress": "0xa508dd875f10c33c52a8abb20e16fc68e981f186",
  "myInt": 12
  "_bundleHash": "7a0e488c12c6fdcc67cbf4fc47b61607034157929cd0842eb23adc1e8f199fdf"
}
```
This `_bundleHash` value can then be used to in queries to the bundle endpoint for the contract.

The structure of the manifest is as follows:

```
{
  "alg": "sha256",
  "digest": "hex",
  "files": [
    {
      "alg": "sha256",
      "digest": "hex",
      "uid": "76a5de1f-2a90-41f3-9a55-40278d3e1f8d.gz",
      "mime": "text/plain",
      "name": "file1.txt",
      "hash": "7a0e488c12c6fdcc67cbf4fc47b61607034157929cd0842eb23adc1e8f199fdf",
      "size": 14
    },
    ...
  ],
  "time": 1607169707
}
```

To query for the manifest send a `GET` to

`/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/bundle/<BUNDLE_HASH>/manifest/`

To query for a file inside a bundle send a `GET` to

`/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/bundle/<BUNDLE_HASH>/filename/<FILE_NAME>/`

The response with be a binary stream of the file which can be written to memory or file.

To query for a bundle send a `GET` to

`/v2/apps/<APP_NAME>/contract/<CONTRACT_API_NAME>/bundle/<BUNDLE_HASH>/`

The response with be a binary stream of the tar.gz which can be written to memory or file.

## Querying Transaction Methods

### Selecting Fields

Specify fields you would like to be returned in the model using the field query parameter.

Example:
```
fields=method,inputs,transaction_hash,finalized_on
```

### Filtering

**Basics**

The basic format for filtering is of the form `?filter[FIELD]=VALUE`, where `FIELD` is the field you'd like to match on,
and `VALUE` is the value you'd like to match,
e.g. - GET `/v2/apps/myapp/contract/mycontract/comments?filter[inputs.post]=1`.

In this case, inputs. specifies that the value to match on is within the inputs list for this transaction/method call.

**Modifiers**

Filters can have modifiers applied. These use dot notation. These allow you to perform more complex filtering.
GET `/v2/apps/myapp/contract/mycontract/comments?filter[inputs.post.gte]=1`
for example, will return comments where post is greater than or equal to (gte) 1.

**Operators**

Different data types have different operators that are applicable to them. The default operator is `exact`.

**Numbers**

* `lt`
* `gt`
* `lte`
* `gte`
* `equals`
* `in` (for arrays of numbers)

**Strings**

* `exact`
* `contains`
* `icontains` (case-insensitive contains)
* `startswith`
* `endswith`
* `in` (for arrays of strings)


**Boolean**

* `is`

**Structs, Arrays, and Complex Objects**

Consider the snippet below. `foo()` accepts an `AddressPerson` object, which is a struct, containing an array of structs.

```solidity
struct Addr{
    string street;
    string town;
}

struct AddressPerson{
    string name;
    uint age;
    Addr[] addrs;
}

function foo(AddressPerson memory person) public {}

```

The data sent to this method may look like the following:
```
{
  "person":
  {
    "age":  88,
    "name": "a_name_001",
    "addrs":
    [
      {
        "town":   "Nowheresville",
        "street": "Whatever Road"
      }
    ]
  }
}
```

In order to query on, for example, the street address, you'd construct a query such
as `?filter[inputs.person.addrs.0.street.icontains]=whatever`.

This would return all transactions, where the street for the address at index 0 contains
the string whatever, using a case insensitive match.

**Property Access**

As seen in the above query, accessing properties is through dot-notation.
So accessing a persons age is just inputs.person.age.

**Array Item Access**

As also seen in the above query, accessing array indices is through dot notation.
Accessing index 1 of the addrs array is `inputs.person.addrs.1`.

**Putting it all together**

You want to query for a person with the name "Bob" living on a street with "Whatever" in the name.

`?filter[inputs.person.name.exact]=Bob&filter[inputs.person.addrs.0.street.icontains]=whatever`

In addition to filtering on the transaction inputs field, the following fields support string comparison operators:

* transaction_type
* request_id
* state
* error
* transaction_hash
* from_address
* to_address
* origin
* transaction_type

The following fields support numeric/datetime comparison operators:

* created_on
* finalized_on
* confirmations
* value
* nonce

The following fields support the exact comparison operator on their UUID identifiers:

* blockchain
* app
* contract






