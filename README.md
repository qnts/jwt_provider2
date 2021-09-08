# JWT Provider v2

This module is a completely rework of the original `jwt_provider`, with a nice and cleaner codebase for developers to easily implement into their app.

**Please note** that this version is only compatible with **odoo `14`**

**Hey there**, We need help fixing/completing the readme. If there are confusions, please do not hesitate to open an issue. Pull requests are welcome, too!

## Prerequisites and Installation

This module requires `pyjwt` and `simplejson` to be installed. See `requirements.txt`.

Download or clone this repo and move it to odoo addons dir. Install it via odoo just like a normal module.

## Environment

By default, `jwt_provider` uses the environment variable `ODOO_JWT_KEY` to hash jwt signature.

## Implementation

Full example, see `middlewares.py` and uncomment all routes in either `api_http.py` (for normal http request) or `api_json.py` (for json rpc) in `controllers`.

### Jwt Auth

To log a user in using (email, password):

```python
from odoo.http import request
from ..JwtRequest import jwt_request

@http.route()
def login(self, email, password, *k, **kw):
    token = jwt_request.login(email, password)
    # access the logged in user via
    #request.env.user
    return jwt_request.response({
        'token': token,
        'user': request.env.user.read(['id']),
    })
```

To log a user in using user model:

```python
token = jwt_request.create_token(user)
```

To require valid jwt in private endpoint, we already registers a middleware `jwt` for us to authenticate user. Just add `jwt` to the middleware decorator:

```python
@http.route()
@jwt_request.middlewares('jwt')
def get_profile(self, *k, **kw):
    ...
```

### Middleware

This version's shipped with a new feature: `middleware`.

> Middleware provide a convenient mechanism for inspecting and filtering HTTP requests entering your application. For example, Laravel includes a middleware that verifies the user of your application is authenticated. If the user is not authenticated, the middleware will redirect the user to your application's login screen. However, if the user is authenticated, the middleware will allow the request to proceed further into the application.
>
> *(from Laravel middleware documentation)*

Okay, this is not laravel, but we had the idea of them and created my own middleware mechanism into this module.

#### Create your own middleware

A middleware is a simple python function, given a `JwtRequest` instance, inside, we check if the request is valid or we raise a `MiddlewareException` to stop the execution and respond the error.

Let's create a simple middleware named `api_key_middleware`, we only allow request with correct api key provided in the request header `X-Api-Key`, otherwise we respond immediately by raising a `MiddlewareException`:

```python
from odoo.addons.jwt_provider2.middleware.MiddlewareData import MiddlewareData
from odoo.addons.jwt_provider2.middleware.MiddlewareException import MiddlewareException
from odoo.addons.jwt_provider2.JwtRequest import jwt_request


def api_key_middleware(req: JwtRequest, data: MiddlewareData, *k, **kw):
    # get api key from headers, note: header keys are always capitalized
    api_key = req.headers.get('X-Api-Key')
    # here we should check for api key (from db, ...)
    if api_key != 'secret':
        raise MiddlewareException('Invalid Api Key', 400, 'invalid_api_key')
    # store data to jwt_request
    data.set('key_info', {
        'client': 'some client name',
        'expiry': '2025-01-01',
    })

# aliasing middleware
jwt_request.register_middleware('api_key', api_key_middleware)
```

As you can see, in the above code, once you have the middleware definition, we alias it with a name `api_key`:

```python
jwt_request.register_middleware('api_key', api_key_middleware)
```

#### Applying middleware

Next, create a controller method and decorate it:

```python
from odoo import http
from odoo.addons.jwt_provider2.JwtRequest import jwt_request


class TestController(http.Controller):

    @http.route('/api/hello', type='http', auth='public', csrf=False, cors='*')
    # decorate middleware
    @jwt_request.middlewares('api_key')
    def hello(self, **kw):
        return jwt_request.response({ 'message': 'hello!', 'key_info': jwt_request.data.get('key_info') })
```

Now when we make a http request to `api/hello`, with no `X-Api-Key` header or invalid one, we should see a response like:

```json
{
    "message": "Invalid Api Key",
    "type": "invalid_api_key",
    "code": 400
}
```

And when we set the header `X-Api-Key`'s value to `secret`, make a request again, and voila!

```json
{
    "message": "hello!",
    "key_info": {
        "client": "some client name",
        "expiry": "2025-01-01"
    }
}
```

We don't need to register a middleware function. Instead, we can add it directly to the decorator `@jwt_request.middlewares()`:

```python
from ....


def api_key_middleware(req: JwtRequest, data: MiddlewareData, *k, **kw):
    ...


class TestController(http.Controller):
    @http.route('/api/hello', type='http', auth='public', csrf=False, cors='*')
    # decorate middleware
    @jwt_request.middlewares(api_key_middleware)
    def hello(self, **kw):
        ...
```

And yes, we can requires as many as middlewares we want:

```python
@jwt_request.middlewares(
  'api_key',
  group_check(['base.group_user']),
  ('age_check', 18),
)
```

Open `middlewares.py`, we already have some examples to write middleware. And uncomment some example endpoints in either `controllers/api_http.py` or `controllers/api_json.py`.

#### Passing and sharing data between middlewares

A middleware function signature is as follow:

```python
def my_middleware(req: JwtRequest, data: MiddlewareData, *kargs, **kwargs):
    ...
```

Let's take a look on the function `require_groups` in `middlewares.py`:

```python
def require_groups(groups=[]):
    def handler(req: JwtRequest, *k, **kw):
        # first need to be authenticated
        req.exec_middleware('jwt')
        # then check groups
        for group in groups:
            if req.odoo_req.env.user.has_group(group):
                req.next()
                return
        raise MiddlewareException('Insufficient privilege', 403, 'no_privilege')
    return handler
```

It returns a middleware function, this tells us how to put it to the middleware decorator:

```python
@http.route(...)
@jwt_request.middlewares(require_groups(['base.group_system']))
def get_admin_privilege(self, *kargs, **kwargs):
    ...
```

Here we actually wrap the middleware function, passing the data `['base.group_system']` into its logic body:

- First, it check if user is already logged in via `jwt`
- Next, `req.odoo_req` is a reference to `odoo.http.request`, get the logged in user, and check if user has any group in `['base.group_system']`.

- Finally, if at least one group satisfies, process to the next middleware by calling `return`. Else, just raise an exception to stop the request (and respond an error).

To share data between middlewares, we can use the param `data`:

```python
from datetime import date

def api_key_middleware(req: JwtRequest, data: MiddlewareData, *k, **kw):
    ...
    # store data to jwt_request
    data.set('key_info', {
        'client': 'some client name',
        'expiry': date(2021, 12, 31),
    })

def api_key_valid(req: JwtRequest, data: MiddlewareData, *k, **kw):
    info = data.get('key_info', {})
    now = date.today()
    # check if key is not expired
    if info.get('expiry') < now:
        raise MiddlewareException()

# controller
# `api_key_valid` must be called after `api_key_middleware`.
@http.route()
@jwt_request.middlewares(api_key_middleware, api_key_valid)
def action(self, *kargs, **kwargs):
    ...
```

#### Global middleware

Global middlewares always run before normal ones when you decorate controller route with `@jwt_request.middlewares()` (empty param is ok).

Examples of global middlewares IRL:

- every request to our routes must provide a valid api key
- log request and response to routes

To register global middleware, call:

```python
jwt_request.middleware_always('logger')
jwt_request.middleware_always(api_key_middleware)


@http.route()
# will run middlewares in the following order:
# logger -> api_key_middleware -> jwt
@jwt_request.middlewares('jwt')
def action(self, *kargs, **kwargs):
    ...
```

Run middleware without global ones? Use:

```python
@jwt_request.pure_middlewares(...)
```

### JwtRequest class

`JwtRequest` comes with a nice `response` method, that auto detects the request type (http or json rpc) and responds the correct one for us.

Documentation coming soon.

### Implement your own jwt auth

Coming soon.
