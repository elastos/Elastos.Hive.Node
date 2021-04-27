# -*- coding: utf-8 -*-

"""
For /api/v2/vault/scripting .
"""

import unittest
import requests


@unittest.skip
class ScriptingTestCase(unittest.TestCase):
    def __get_url(self, relative_url):
        return 'http://localhost:5000/api/v2/vault/scripting' + relative_url

    def __get_token(self):
        return 'eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aW9SbjNlRW9wUmpBN0NCUnJyV1FXenR0QWZYQWp6dktNeCNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3Rvczppb1JuM2VFb3BSakE3Q0JScnJXUVd6dHRBZlhBanp2S014Iiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppWllEVVY3R3ZoWXB2UHAxYWljMXBlcU1WZDNyYXF0SGkyIiwiZXhwIjoxNjIyMTAxNTI5LCJwcm9wcyI6IntcImFwcERpZFwiOiBcImFwcElkXCIsIFwidXNlckRpZFwiOiBcImRpZDplbGFzdG9zOmlxazNLTGViZ2lpUDQ2dXlvS2V2WVFKQjdQWmNzMmlUTHpcIiwgXCJub25jZVwiOiBcIjcyOTRlMjE0LWE3MmMtMTFlYi1hOGU0LWFjZGU0ODAwMTEyMlwifSJ9.Xox6tzUd3FXIqtv8J1S_nylL0tdy-IaYTDAB5JoHLLdXxIA6h917KQm1s8l8Rx5lPh7PXVQu-p3Zkuu6ym5DfA'

    def __http_delete(self, relative_url):
        return requests.delete(self.__get_url(relative_url), headers={'Authorization': 'token ' + self.__get_token()})

    def test_delete_script(self):
        response = self.__http_delete('/get_group_message2')
        assert(response.status_code == 204)


if __name__ == '__main__':
    unittest.main()
