# JWT Provider v2

This module is a completely rework of the original `jwt_provider`, with a nice and cleaner codebase for developers to easily implement into their app.

**Please note** that this version is only compatible with **odoo `14`** (and above, maybe).

---

Quick link: [Documentation](https://qnts.github.io/jwt_provider2/)

---
What's included?

- Basic JWT auth that you can extend or write your own
- Middleware mechanism - keep your controller logic nice and clean

```python
# middleware
from odoo.addons.jwt_provider2.JwtRequest import JwtRequest, jwt_request
from odoo.addons.jwt_provider2.middleware.MiddlewareException import MiddlewareException

def require_api_key(req: JwtRequest, *kargs, **kwargs):
    api_key = req.headers.get('X-Api-Key')
    if api_key != 'secret':
        raise MiddlewareException('Invalid Api Key', 400, 'invalid_api_key')

# alias middleware
jwt_request.register_middleware('api_key', require_api_key)


# controller
from odoo import http
from odoo.addons.jwt_provider2.JwtRequest import jwt_request

class MyController(http.Controller):
    @http.route('/api/hello-world', type='json')
    @jwt_request.middlewares('api_key', 'middleware_first', '...')
    def hello(self, *kargs, **kwargs):
        return jwt_request.response({ 'message': 'hello world!' })

```
