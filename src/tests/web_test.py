from io import BytesIO
import unittest
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from web import WarehouseApp


class TestWarehouseApp(unittest.TestCase):
    def setUp(self):
        self.app = WarehouseApp()

    def request(self, path="/", method="GET", fields=None):
        body = urlencode(fields or {}).encode("utf-8")
        environ = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        })
        response = {}

        def start_response(status, headers):
            response["status"] = status
            response["headers"] = dict(headers)

        response["body"] = b"".join(
            self.app(environ, start_response)).decode("utf-8")
        return response

    def test_create_and_list_warehouses(self):
        response = self.request("/warehouses", "POST", {
            "name": "Main",
            "capacity": "20",
        })

        self.assertEqual(response["status"], "303 See Other")
        self.request("/warehouses", "POST", {
            "name": "Second",
            "capacity": "30",
        })
        page = self.request()["body"]
        self.assertIn("Main", page)
        self.assertIn("Balance: 0.0 / 20.0", page)
        self.assertIn("Second", page)
        self.assertIn("Balance: 0.0 / 30.0", page)

    def test_add_and_remove_stock(self):
        self.request("/warehouses", "POST", {"name": "Main", "capacity": "20"})
        self.request("/warehouses/0/add", "POST", {"amount": "8"})
        page = self.request()["body"]
        self.assertIn("Balance: 8.0 / 20.0", page)

        self.request("/warehouses/0/remove", "POST", {"amount": "3"})
        self.assertIn("Balance: 5.0 / 20.0", self.request()["body"])

    def test_warehouse_name_is_escaped(self):
        self.request("/warehouses", "POST", {
            "name": "<script>alert(1)</script>",
            "capacity": "10",
        })

        page = self.request()["body"]
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>", page)

    def test_invalid_capacity_does_not_create_warehouse(self):
        response = self.request("/warehouses", "POST", {
            "name": "Main",
            "capacity": "-1",
        })

        self.assertEqual(response["status"], "400 Bad Request")
        self.assertIn("No warehouses yet.", response["body"])
