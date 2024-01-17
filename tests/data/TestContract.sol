pragma solidity ^0.8.11;

import '@openzeppelin/contracts/token/ERC721/ERC721.sol';
import '@openzeppelin/contracts/access/Ownable.sol';
import '@openzeppelin/contracts/utils/Counters.sol';
import './Dev.sol';

contract TestContract is Dev, ERC721("DevToken", "DVT"), Ownable {

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;

    struct TestData {
        string data;
        string moreData;
    }

    struct Person{
        string name;
        uint age;
        Addr addr;
    }

    struct Addr{
        string street;
        uint number;
        string town;
    }

    struct AddressPerson{
        string name;
        uint age;
        Addr[] addrs;
    }

    mapping(uint256 => TestData) private _tests;

    constructor() public {}

    function getTestData(uint256 tokenId) public view returns (string memory data, string memory moreData){
        TestData memory _test = _tests[tokenId];
        data = _test.data;
        moreData = _test.moreData;
    }

    function mint(string memory data, string memory moreData) external payable onlyOwner {
        uint256 tokenId = _tokenId.current();
        TestData memory _test = TestData({data : data, moreData : moreData});
        _mint(msg.sender, tokenId);
        _tests[tokenId] = _test;
        _tokenId.increment();
    }

    function an_arr(uint[] memory first)
    public {}

    function two_arrs(uint[] memory first, uint[] memory second)
    public {}

    function address_arr(address[] memory first)
    public {}

    function nested_arr_0(uint[][] memory first)
    public {}

    function nested_arr_1(uint[][5] memory first)
    public {}

    function nested_arr_2(uint[4][] memory first)
    public {}

    function nested_arr_3(uint[3][3] memory first)
    public {}

    function nested_arr_4(uint[3][3] memory first,
        string memory _bundleHash)
    public {}

    function structTest_1 (
        Person[] memory people,
        bool test_bool
        )
    public {}

    function structTest_2 (
        Person memory person,
        bool test_bool
        )
    public {}

    function structTest_3 (
        AddressPerson memory person,
        string memory _bundleHash
        )
    public {}

    function structTest_4 (
        AddressPerson[] memory persons,
        string memory _bundleHash
        )
    public {}

    function structTest_5 (
        Person memory person,
        string memory _bundleHash
        )
    public {}

    function nowt(
        )
    public {}

    function clientContainer (
        Person memory person,
        string memory _bundleHash,
        string memory _bundlePath
        )
    public {}

}
