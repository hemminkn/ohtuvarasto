from html import escape
import math
import re
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from varasto import Varasto


class WarehouseApp:
    def __init__(self):
        self.warehouses = []

    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")

        if method == "GET" and path == "/":
            return self._respond(start_response, "200 OK", self._page())

        if method != "POST":
            return self._respond(start_response, "404 Not Found", "Not found")

        fields = self._read_fields(environ)
        try:
            if path == "/warehouses":
                name = fields.get("name", [""])[0].strip()
                if not name:
                    raise ValueError("Warehouse name is required.")
                capacity = self._number(fields, "capacity")
                self.warehouses.append({
                    "name": name,
                    "stock": Varasto(capacity),
                })
            else:
                match = re.fullmatch(r"/warehouses/(\d+)/(add|remove)", path)
                if not match:
                    return self._respond(
                        start_response, "404 Not Found", "Not found")
                warehouse_id = int(match.group(1))
                if warehouse_id >= len(self.warehouses):
                    return self._respond(
                        start_response, "404 Not Found", "Not found")
                amount = self._number(fields, "amount")
                stock = self.warehouses[warehouse_id]["stock"]
                if match.group(2) == "add":
                    stock.lisaa_varastoon(amount)
                else:
                    stock.ota_varastosta(amount)
        except ValueError as error:
            return self._respond(
                start_response, "400 Bad Request", self._page(str(error)))

        start_response("303 See Other", [
            ("Location", "/"),
            ("Content-Length", "0"),
        ])
        return [b""]

    @staticmethod
    def _read_fields(environ):
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(length).decode("utf-8")
        return parse_qs(body, keep_blank_values=True)

    @staticmethod
    def _number(fields, name):
        try:
            value = float(fields.get(name, [""])[0])
        except ValueError as error:
            raise ValueError("Enter a valid non-negative number.") from error
        if not math.isfinite(value) or value < 0:
            raise ValueError("Enter a valid non-negative number.")
        return value

    def _page(self, error=None):
        message = f"<p role=\"alert\">{escape(error)}</p>" if error else ""
        warehouses = "".join(self._warehouse_section(index, warehouse)
                             for index, warehouse in enumerate(self.warehouses))
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Warehouse inventory</title></head>
<body>
<h1>Warehouse inventory</h1>
{message}
<h2>Create a warehouse</h2>
<form method="post" action="/warehouses">
  <label>Name <input name="name" required></label>
  <label>Capacity
    <input name="capacity" type="number" min="0" step="any" required>
  </label>
  <button type="submit">Create warehouse</button>
</form>
<h2>Warehouses</h2>
{warehouses or "<p>No warehouses yet.</p>"}
</body>
</html>"""

    @staticmethod
    def _warehouse_section(index, warehouse):
        stock = warehouse["stock"]
        name = escape(warehouse["name"])
        return f"""<section>
<h3>{name}</h3>
<p>Balance: {stock.saldo} / {stock.tilavuus}</p>
<p>Available space: {stock.paljonko_mahtuu()}</p>
<form method="post" action="/warehouses/{index}/add">
  <label>Amount to add
    <input name="amount" type="number" min="0" step="any" required>
  </label>
  <button type="submit">Add stock</button>
</form>
<form method="post" action="/warehouses/{index}/remove">
  <label>Amount to remove
    <input name="amount" type="number" min="0" step="any" required>
  </label>
  <button type="submit">Remove stock</button>
</form>
</section>"""

    @staticmethod
    def _respond(start_response, status, body):
        encoded = body.encode("utf-8")
        start_response(status, [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(encoded))),
        ])
        return [encoded]


def serve():
    with make_server("127.0.0.1", 8000, WarehouseApp()) as server:
        print("Serving warehouse app at http://127.0.0.1:8000")
        server.serve_forever()
