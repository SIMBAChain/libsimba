import json

from typing import TYPE_CHECKING, AsyncGenerator, List, Optional

from libsimba.param_checking import ParamChecking
from libsimba.schemas import (
    ConnectionConfig,
    FileDict,
    Login,
    MethodCallArgs,
    SearchFilter,
)


if TYPE_CHECKING:
    from libsimba import Simba


class SimbaContract(ParamChecking):
    def __init__(self, simba: "Simba", app_name: str, contract_name: str):
        super().__init__(app_name, contract_name)
        self.simba = simba

    async def call_method(
        self,
        method_name: str,
        args: Optional[MethodCallArgs] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Call a getter contract method

        :param method_name: The method name
        :type method_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: getter response
        :rtype: dict
        """
        self.validate_params(method_name=method_name, inputs=args.args)
        return await self.simba.call_contract_method(
            app_id=self.app_name,
            contract_name=self.contract_name,
            method_name=method_name,
            args=args,
            login=login,
            config=config,
        )

    async def submit_method(
        self,
        method_name: str,
        inputs: Optional[dict],
        files: Optional[FileDict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Submit a transaction to a method

        :param method_name: The method name
        :type method_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **inputs** (`Optional[dict]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the created transaction
        :rtype: dict
        """
        self.validate_params(method_name=method_name, inputs=inputs)
        return await self.simba.submit_contract_method(
            app_id=self.app_name,
            contract_name=self.contract_name,
            method_name=method_name,
            inputs=inputs,
            login=login,
            config=config,
            files=files,
        )

    async def submit_method_sync(
        self,
        method_name: str,
        inputs: Optional[dict],
        files: Optional[FileDict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Submit a transaction to a method

        :param method_name: The method name
        :type method_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **inputs** (`Optional[dict]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the created transaction
        :rtype: dict
        """
        self.validate_params(method_name=method_name, inputs=inputs)
        return await self.simba.submit_contract_method_sync(
            app_id=self.app_name,
            contract_name=self.contract_name,
            method_name=method_name,
            inputs=inputs,
            login=login,
            config=config,
            files=files,
        )

    async def list_method_transactions(
        self,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        """
        Query transactions by method and page through all results.

        :param method_name: The method name
        :type method_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of application information
        :rtype: Generator[List[dict]]
        """
        return await self.simba.list_transactions_by_method(
            app_id=self.app_name,
            contract_name=self.contract_name,
            method_name=method_name,
            query_args=query_args,
            login=login,
            config=config,
        )

    async def get_method_transactions(
        self,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        Query transactions by method and get a single page back as a list.

        :param method_name: The method name
        :type method_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A list of transactions
        :rtype: List[dict]
        """
        return await self.simba.get_transactions_by_method(
            app_id=self.app_name,
            contract_name=self.contract_name,
            method_name=method_name,
            query_args=query_args,
            login=login,
            config=config,
        )

    async def list_events(
        self,
        event_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        """
        Query events and page through all results.

        :param event_name: The method name
        :type event_name: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of application information
        :rtype: Generator[List[dict]]
        """
        return await self.simba.list_events_by_contract(
            app_id=self.app_name,
            contract_name=self.contract_name,
            event_name=event_name,
            query_args=query_args,
            login=login,
            config=config,
        )

    async def validate_bundle_hash(
        self, bundle_hash: str, login: Login = None, config: ConnectionConfig = None
    ) -> dict:
        """
        Validate a previously created bundle using the contract name and bundle hash.
        This will examine the bundle manifest and the file hashes defined in it against the files in off chain storage,
        ensuring that all the referenced data has not been tampered with.
        The errors element will contain any validation errors encountered.

        :param bundle_hash: The hash or UUID of the bundle
        :type bundle_hash: str

        :param \**kwargs:
            See below

        :Keyword Arguments:
            * *login* (``Login``) - Optional
            * *config* (``ConnectionConfig``) - Optional
        :return: An object containing any errors if the validation has failed.
        :rtype: json
        """
        return await self.simba.validate_bundle(
            app_id=self.app_name,
            contract_name=self.contract_name,
            bundle_hash=bundle_hash,
            login=login,
            config=config,
        )

    async def get_bundle(
        self,
        bundle_hash: str,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> None:
        """
        Download a bundle tar.gz.

        :param bundle_hash: The hash or UUID of the bundle
        :type bundle_hash: str
        :param download_location: local file location to write to
        :type download_location: str

        :param \**kwargs:
            See below

        :Keyword Arguments:
            * *login* (``Login``) - Optional
            * *config* (``ConnectionConfig``) - Optional
        :return: An object containing any errors if the validation has failed.
        :rtype: json
        """
        return await self.simba.get_bundle(
            app_id=self.app_name,
            contract_name=self.contract_name,
            bundle_hash=bundle_hash,
            download_location=download_location,
            login=login,
            config=config,
        )

    async def get_bundle_manifest(
        self, bundle_hash: str, login: Login = None, config: ConnectionConfig = None
    ) -> dict:
        """
        Get the JSON manifest for a bundle.

        :param bundle_hash: The hash or UUID of the bundle
        :type bundle_hash: str

        :param \**kwargs:
            See below

        :Keyword Arguments:
            * *login* (``Login``) - Optional
            * *config* (``ConnectionConfig``) - Optional
        :return: An object containing any errors if the validation has failed.
        :rtype: json
        """
        return await self.simba.get_manifest_for_bundle_from_bundle_hash(
            app_id=self.app_name,
            contract_name=self.contract_name,
            bundle_hash=bundle_hash,
            login=login,
            config=config,
        )

    async def get_bundle_file(
        self,
        bundle_hash: str,
        file_name: str,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> None:
        """
        Get a named file from a bundle.

        :param bundle_hash: The hash or UUID of the bundle
        :type bundle_hash: str
        :param file_name: the name of the file in the bundle
        :type file_name: str
        :param download_location: local file location to write to
        :type download_location: str
        :param \**kwargs:
            See below

        :Keyword Arguments:
            * *login* (``Login``) - Optional
            * *config* (``ConnectionConfig``) - Optional
        :return: An object containing any errors if the validation has failed.
        :rtype: json
        """
        return await self.simba.get_bundle_file(
            app_id=self.app_name,
            contract_name=self.contract_name,
            bundle_hash=bundle_hash,
            file_name=file_name,
            download_location=download_location,
            login=login,
            config=config,
        )
