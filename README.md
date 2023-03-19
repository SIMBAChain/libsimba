# libsimba

libsimba is a library simplifying the use of SIMBAChain Blocks APIs. It is a core library intended to be used
by all python client side tools including a more rounded SDK that supports Web3 capabilities and generating
Python classes from contracts.

### [🏠 Homepage](https://github.com/SIMBAChain/libsimba)
### [📝 Documentation](https://simbachain.github.io/libsimba)

## Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [issues page](https://github.com/SIMBAChain/libsimba/issues).

## License

Copyright © 2023 [SIMBAChain Inc](https://simbachain.com/).

This project is [MIT](https://github.com/SIMBAChain/libsimba/blob/main/LICENSE) licensed.

## Documentation generated using Sphinx

To generate the documentation, navigate to the sphinx folder and run
```bash
make github
```

## Testing

to run tests using the CLI:

1. Ensure you have a simbachain.env in the working directory from which you are running the tests.
2. To run local tests, type `poetry run task tests`
3. To run the async API against a live server defined in the simbachain.env file, type `poetry run task live_async`
4. To run the sync API against a live server defined in the simbachain.env file, type `poetry run task live_sync`

