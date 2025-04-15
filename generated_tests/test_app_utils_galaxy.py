Okay, I need to write comprehensive pytest tests for the galaxy.py module in the Galaxy NG project. Let me start by understanding the functions in the module and what each does.

First, the functions to test are:

- generate_unverified_email
- uuid_to_int
- int_to_uuid
- safe_fetch
- paginated_results
- find_namespace
- get_namespace_owners_details
- upstream_namespace_iterator
- upstream_collection_iterator
- upstream_role_iterator

I'll need to create tests for each of these. Since some functions make HTTP requests, I should mock those to avoid real network calls. The tests should use pytest fixtures and mocks, especially for requests.get and logging.

Starting with generate_unverified_email. This function takes a github_id and returns an email string. Test cases should include normal inputs and maybe edge cases like empty strings or numbers. But since the input is a github_id, which is probably a string, maybe test with a string like '123' and check the output is '123@GALAXY.GITHUB.UNVERIFIED.COM'.

Next, uuid_to_int and int_to_uuid. These functions convert between UUID strings and integers. Need to test that converting a UUID to an int and back gives the same UUID. Also test invalid UUIDs, but the function just removes hyphens and converts to hex, so maybe test with a valid UUID like '123e4567-e89b-12d3-a456-426614174000' and ensure the conversion works. Also check that int_to_uuid handles numbers that are too short by padding with zeros.

safe_fetch makes a GET request and retries on 500 errors. Need to mock requests.get to return different status codes. Test cases: successful response (200), retry on 500 up to 5 times, then return the last response. Also test that it stops after 5 retries. Also check logging messages.

paginated_results iterates through pages. Mock the responses so that each call to safe_fetch returns a page with 'next' or 'next_link'. Test that all pages are fetched and results are combined. Edge cases: no next page, next_link with relative URL, or absolute URL.

find_namespace: tests for when name or id is provided. Mock safe_fetch to return a response with the correct JSON. Test when name is given, when id is given, and when neither is given (should it raise an error? The code seems to require either name or id, but the function allows both to be None. Wait, looking at the code, if neither name nor id is provided, the function proceeds but then tries to get ns_info from ds['results'][0], which might be an error. Hmm, maybe that's a bug, but the test should check that case. But perhaps the function expects at least one of them. Need to test that when both are None, it might fail, but according to the code, it proceeds but then ns_info is None, leading to KeyError. So maybe the test should check that when neither is provided, it raises an error? Or maybe the function is supposed to require one. The code as written may have a bug here, but for testing, perhaps we should test the cases where name or id is provided.

get_namespace_owners_details: tests for old and new galaxy responses. Mock the safe_fetch to return a response with 'results' (old) or a list (new). Test that owners are collected correctly in both cases.

upstream_namespace_iterator: a generator that yields namespaces. Need to mock the paginated calls. Test with limit, start_page, require_content. Also test error handling when a page returns 500.

upstream_collection_iterator: similar to the above, but with parameters like collection_namespace and collection_name. Need to test different scenarios like when only namespace is given, both, neither. Also test the case where get_versions is True/False.

upstream_role_iterator: tests with parameters like github_user, role_name, etc. Mock the responses for roles and their versions.

Now, setting up fixtures. Since many functions use requests.get, I'll need a fixture that patches requests.get. Also, logging can be mocked to check log messages.

Possible fixtures:

- mock_requests: a fixture that patches requests.get to return a mock response.
- mock_logger: to capture log messages.

Each test function will use these fixtures. For example, testing safe_fetch would set up mock_requests to return a response with a certain status code and check that the function retries correctly.

For the uuid functions, no mocks needed, just unit tests with sample UUIDs and integers.

Edge cases to consider:

- For uuid_to_int: UUID with hyphens, UUID without hyphens (though the function removes them anyway)
- int_to_uuid: numbers that when converted to hex are shorter than 32 characters (so padding is needed)
- safe_fetch: 500 errors exactly 5 times, then returns the 5th response
- paginated_results: next_url is None, or next_link is empty, or next_link is a relative path
- find_namespace: when the query returns no results (maybe return empty?), but the code assumes there's at least one result. Need to test that scenario.
- get_namespace_owners_details: when next_link is missing, or when the response has no 'next_link' key
- upstream_namespace_iterator: when limit is 0, or when the first page has enough items to hit the limit
- upstream_collection_iterator: when collection_namespace is given but no collection_name, but the code has an if condition for that. Wait, in the code, there's a part where if collection_namespace and not collection_name, it proceeds, but then later if collection_name and not namespace, it raises an exception. So need to test that exception is raised when name is given without namespace.

Now, structuring the test file. The test file should be in galaxy_ng/tests/unit/app/utils/test_galaxy.py.

Import statements:

from unittest.mock import patch, MagicMock
import pytest
from galaxy_ng.app.utils.galaxy import (
    generate_unverified_email,
    uuid_to_int,
    int_to_uuid,
    safe_fetch,
    paginated_results,
    find_namespace,
    get_namespace_owners_details,
    upstream_namespace_iterator,
    upstream_collection_iterator,
    upstream_role_iterator,
)
import logging

Maybe also from django.utils import timezone, but not sure. Since the code uses time.sleep, but in tests, we can mock that.

Wait, the code uses time.sleep(60) in safe_fetch. To avoid waiting in tests, we can mock time.sleep.

So fixtures:

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def mock_sleep():
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep

@pytest.fixture
def mock_logger():
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger

Now, writing tests for each function.

Starting with generate_unverified_email:

def test_generate_unverified_email():
    assert generate_unverified_email('123') == '123@GALAXY.GITHUB.UNVERIFIED.COM'
    assert generate_unverified_email('abc') == 'abc@GALAXY.GITHUB.UNVERIFIED.COM'

uuid_to_int and int_to_uuid:

def test_uuid_conversion():
    uuid_str = '123e4567-e89b-12d3-a456-426614174000'
    num = uuid_to_int(uuid_str)
    assert int_to_uuid(num) == uuid_str

    # Test a UUID that when converted to hex is shorter than 32 chars
    short_uuid = '12345678-1234-1234-1234-1234567890ab'
    num_short = uuid_to_int(short_uuid)
    # The hex of this should be 32 chars after padding
    # Let's see: the UUID without hyphens is 32 chars (since UUID is 32 hex chars)
    # Wait, UUID is 32 hex chars (128 bits). So maybe the test case is redundant here.

Wait, the function removes hyphens, so the input must be a valid UUID. So perhaps the test is okay.

Testing int_to_uuid with a number that's too short:

def test_int_to_uuid_padding():
    num = 0x1234567890abcdef
    uuid_str = int_to_uuid(num)
    # The hex of num is 1234567890abcdef (16 chars), so padded to 32 with leading zeros
    expected = '00000000000000001234567890abcdef'
    assert uuid_str == '00000000-0000-0000-1234-567890abcdef'

Wait, the function does:

d = hex(num).replace('0x', '')
if len(d) <32: pad with 0s to 32.

So for num=0x1234567890abcdef (16 hex digits), d is '1234567890abcdef', length 16. So padding with 16 zeros, making it '00000000000000001234567890abcdef', then split into UUID parts.

So the test case should check that.

Now, safe_fetch:

def test_safe_fetch_success(mock_requests, mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.return_value = mock_response
    result = safe_fetch('http://test.com')
    assert result == mock_response
    mock_sleep.assert_not_called()

def test_safe_fetch_retry(mock_requests, mock_sleep):
    mock_responses = [MagicMock(status_code=500) for _ in range(5)]
    mock_responses[4].status_code = 500  # 5th try still 500
    mock_requests.side_effect = mock_responses
    result = safe_fetch('http://test.com')
    assert result == mock_responses[4]
    assert mock_sleep.call_count == 4  # sleeps after first 4 failures

def test_safe_fetch_max_retries(mock_requests, mock_sleep):
    mock_requests.side_effect = [MagicMock(status_code=500) for _ in range(5)]
    result = safe_fetch('http://test.com')
    assert result.status_code == 500
    assert mock_sleep.call_count == 4

Testing paginated_results:

def test_paginated_results(mock_requests):
    mock_responses = [
        MagicMock(json=lambda: {'results': [1,2], 'next_link': '/next'}),
        MagicMock(json=lambda: {'results': [3,4], 'next_link': None}),
    ]
    mock_requests.get.side_effect = mock_responses
    results = paginated_results('http://test.com')
    assert results == [1,2,3,4]

Wait, but in the code, the safe_fetch is called, which uses requests.get. So in the mock, need to set mock_requests.get to return the mock responses. Wait, in the fixture, mock_requests is the patch of requests.get. So in the test, mock_requests() would be the get method. Wait, perhaps I need to adjust the mock setup.

Wait, in the fixture, mock_requests is a patch of requests.get. So in the test, when we call safe_fetch, it calls requests.get(url), which is mocked by mock_requests. So in the test for paginated_results, the mock_requests should be set to return the mock responses when called with the URLs.

Hmm, perhaps better to structure the test as:

def test_paginated_results(mock_requests):
    first_response = MagicMock()
    first_response.json.return_value = {'results': [1,2], 'next_link': '/api/v1/next'}
    second_response = MagicMock()
    second_response.json.return_value = {'results': [3,4], 'next_link': None}
    mock_requests.get.side_effect = [first_response, second_response]

    results = paginated_results('http://base/api/v1/initial')
    assert results == [1,2,3,4]

    # Check that the URLs were fetched correctly
    mock_requests.get.assert_any_call('http://base/api/v1/initial')
    mock_requests.get.assert_any_call('http://base/api/v1/next')

Wait, but in the code, the _baseurl is parsed from the next_url. So the next_url in the first call is 'http://base/api/v1/initial', then the next_link is '/api/v1/next', so the next_url becomes _baseurl + next_link. The _baseurl is the parsed scheme and netloc from the initial URL. So if the initial URL is 'http://base/api/v1/initial', then the next_url would be 'http://base/api/v1/next'.

So the test should ensure that the next URLs are correctly formed.

Another edge case: next_link is a relative path without /api/v1 prefix. The code checks if next_url starts with _baseurl + '/api/v1', and if not, prepends it. So test that scenario.

def test_paginated_results_relative_next_link(mock_requests):
    first_response = MagicMock()
    first_response.json.return_value = {'results': [1], 'next_link': '/next'}
    second_response = MagicMock()
    second_response.json.return_value = {'results': [2], 'next_link': None}
    mock_requests.get.side_effect = [first_response, second_response]

    results = paginated_results('http://base/api/v1/start')
    assert results == [1,2]

    # The next_url after first is http://base/api/v1/next
    mock_requests.get.assert_any_call('http://base/api/v1/next')

Another case where next_link is absolute but missing the base URL's path:

Wait, perhaps the code handles that. The code checks if next_url starts with _baseurl, and if not, prepends it. So if next_link is '/api/v2/something', then the code would prepend the base URL's scheme and netloc, but the baseurl is parsed from the initial URL. Let me think through an example.

Suppose the initial URL is 'https://example.com/api/v1/collections', then _baseurl is 'https://example.com'. The next_link is '/api/v2/next', then next_url becomes _baseurl + next_link → 'https://example.com/api/v2/next', which is correct.

Another test case where next_link is a full URL to another domain (should not happen, but code should handle it by not modifying it? Or maybe it's an error. The code only appends if it doesn't start with _baseurl. So if next_link is 'http://another.com', then next_url remains as is, but the code would proceed, but that's probably an error in the API. The test can check that.

But perhaps that's beyond the scope. Focus on the cases covered by the code.

Now, find_namespace tests:

def test_find_namespace_by_name(mock_requests):
    mock_response = MagicMock()
    mock_response.json.return_value = {'results': [{'id': 1, 'name': 'test'}]}
    mock_requests.get.return_value = mock_response

    name, info = find_namespace(baseurl='http://test', name='test')
    assert name == 'test'
    assert info['id'] == 1

    # Also check that owners are fetched
    # Need to mock get_namespace_owners_details
    with patch('galaxy_ng.app.utils.galaxy.get_namespace_owners_details') as mock_owners:
        mock_owners.return_value = ['owner1']
        name, info = find_namespace(baseurl='http://test', name='test')
        assert info['summary_fields']['owners'] == ['owner1']

Testing when id is provided:

def test_find_namespace_by_id(mock_requests):
    mock_response = MagicMock()
    mock_response.json.return_value = {'id': 2, 'name': 'test_id'}
    mock_requests.get.return_value = mock_response

    name, info = find_namespace(baseurl='http://test', id=2)
    assert name == 'test_id'
    assert info['id'] == 2

Testing when neither name nor id is provided:

def test_find_namespace_no_params():
    with pytest.raises(ValueError, match='Either name or id must be provided'):
        find_namespace(baseurl='http://test')  # Neither name nor id given

Wait, looking at the code, the function doesn't raise an error. It proceeds, but then in the code, if neither is provided, the code skips the name and id checks, and then tries to get ns_info from ds['results'][0], which would be an error if the query wasn't made. Wait, let me check the code again.

Looking at the code for find_namespace:

if name:
    ... query by name
elif id:
    ... query by id
else:
    # neither is provided, so the code proceeds to get ns_info which is None, leading to KeyError in the next steps.

Wait, in the code:

if name:
    ... set ns_info to ds['results'][0]
elif id:
    ... set ns_info to ds
else:
    # neither, so ns_info remains None
    # then later, ns_id = ns_info['id'] → KeyError

So the function will crash if neither name nor id is provided. So the test should check that it raises an error. But the code doesn't have an explicit check. So perhaps the test should trigger that KeyError, but that's a bit messy. Alternatively, maybe the function should have a check. But given the code as is, the test can check that when neither is provided, it raises KeyError. But that's not a clean test. Alternatively, maybe the test should ensure that the function requires at least one parameter.

Alternatively, perhaps the test can check that when neither is provided, the code proceeds but then the ns_info is None, leading to an error. So in the test:

def test_find_namespace_no_params(mock_requests):
    with pytest.raises(KeyError):
        find_namespace(baseurl='http://test')

But that's a bit fragile. Alternatively, the code should have a check, but since it's not there, the test can just note that it's a problem.

Moving on to get_namespace_owners_details:

def test_get_namespace_owners_old_galaxy(mock_requests):
    mock_response = MagicMock()
    mock_response.json.return_value = {'results': [{'user': 'owner1'}], 'next_link': '/next'}
    mock_requests.get.return_value = mock_response

    owners = get_namespace_owners_details('http://test', 1)
    assert owners == [{'user': 'owner1'}]

    # next page
    mock_response2 = MagicMock()
    mock_response2.json.return_value = {'results': [{'user': 'owner2'}], 'next_link': None}
    mock_requests.get.side_effect = [mock_response, mock_response2]

    owners = get_namespace_owners_details('http://test', 1)
    assert owners == [{'user':