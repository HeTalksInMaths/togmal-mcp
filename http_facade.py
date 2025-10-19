"""
HTTP Facade for ToGMAL MCP (stdio) server

Exposes minimal HTTP endpoints to interact with MCP tools:
- POST /list-tools-dynamic { conversation_history, user_context }
- POST /call-tool { name, arguments }

This wraps the MCP tool functions directly and returns their outputs.
No authentication is implemented; use locally only.
"""

import json
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Import MCP tool functions and input models
from togmal_mcp import (
    togmal_list_tools_dynamic,
    get_recommended_checks,
    analyze_prompt,
    analyze_response,
    get_taxonomy,
    get_statistics,
    AnalyzePromptInput,
    AnalyzeResponseInput,
    GetTaxonomyInput,
    ResponseFormat,
)


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "ToGMALHTTP/0.1"

    def _write_json(self, status: int, payload: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """
<!doctype html>
<html>
<head><title>ToGMAL HTTP Facade</title></head>
<body>
<h1>ToGMAL HTTP Facade</h1>
<p>This server exposes MCP tools over HTTP for local development.</p>
<ul>
  <li>POST /list-tools-dynamic - body: {\"conversation_history\": [...], \"user_context\": {...}}</li>
  <li>POST /call-tool - body: {\"name\": \"togmal_analyze_prompt\", \"arguments\": {...}}</li>
</ul>
<p>Supported names for /call-tool: togmal_analyze_prompt, togmal_analyze_response, togmal_get_taxonomy, togmal_get_statistics, togmal_list_tools_dynamic, togmal_get_recommended_checks.</p>
</body>
</html>
"""
            self.wfile.write(html.encode("utf-8"))
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
        except Exception:
            content_len = 0
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._write_json(400, {"error": "Invalid JSON body"})

        # Ensure an event loop exists for async tool calls
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if path == "/list-tools-dynamic":
                conversation_history = data.get("conversation_history")
                user_context = data.get("user_context")
                result = loop.run_until_complete(
                    togmal_list_tools_dynamic(conversation_history, user_context)
                )
                # result is a JSON string
                try:
                    return self._write_json(200, json.loads(result))
                except Exception:
                    return self._write_json(200, {"result": result})

            elif path == "/call-tool":
                name = data.get("name")
                arguments = data.get("arguments", {})
                if not name:
                    return self._write_json(400, {"error": "Missing 'name'"})

                # Route to specific tool functions
                if name == "togmal_analyze_prompt":
                    params = AnalyzePromptInput(**arguments)
                    output = loop.run_until_complete(analyze_prompt(params))
                    return self._write_json(200, {"result": output})

                elif name == "togmal_analyze_response":
                    params = AnalyzeResponseInput(**arguments)
                    output = loop.run_until_complete(analyze_response(params))
                    return self._write_json(200, {"result": output})

                elif name == "togmal_get_taxonomy":
                    params = GetTaxonomyInput(**arguments)
                    output = loop.run_until_complete(get_taxonomy(params))
                    return self._write_json(200, {"result": output})

                elif name == "togmal_get_statistics":
                    fmt = arguments.get("response_format", "markdown")
                    output = loop.run_until_complete(get_statistics(ResponseFormat(fmt)))
                    return self._write_json(200, {"result": output})

                elif name == "togmal_list_tools_dynamic":
                    conversation_history = arguments.get("conversation_history")
                    user_context = arguments.get("user_context")
                    result = loop.run_until_complete(
                        togmal_list_tools_dynamic(conversation_history, user_context)
                    )
                    try:
                        return self._write_json(200, json.loads(result))
                    except Exception:
                        return self._write_json(200, {"result": result})

                elif name == "togmal_get_recommended_checks":
                    conversation_history = arguments.get("conversation_history")
                    user_context = arguments.get("user_context")
                    result = loop.run_until_complete(
                        get_recommended_checks(conversation_history, user_context)
                    )
                    try:
                        return self._write_json(200, json.loads(result))
                    except Exception:
                        return self._write_json(200, {"result": result})

                else:
                    return self._write_json(404, {"error": f"Unknown tool: {name}"})

            else:
                return self._write_json(404, {"error": "Not Found"})

        except Exception as e:
            return self._write_json(500, {"error": str(e)})
        finally:
            try:
                loop.close()
            except Exception:
                pass


def run(port: int = 6274):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, MCPHTTPRequestHandler)
    print(f"HTTP MCP facade listening on http://{server_address[0]}:{server_address[1]}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
