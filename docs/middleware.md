# Middleware

This version's shipped with a new feature: `middleware`.

> Middleware provide a convenient mechanism for inspecting and filtering HTTP requests entering your application. For example, Laravel includes a middleware that verifies the user of your application is authenticated. If the user is not authenticated, the middleware will redirect the user to your application's login screen. However, if the user is authenticated, the middleware will allow the request to proceed further into the application.
>
> *(from Laravel middleware documentation)*

Okay, this is not laravel, but we had the idea of them and created our own middleware mechanism into this module.

![](concept.png?raw=true)

## Creating middleware

> :warning: For the rest of the documentation, we use relative imports in code blocks to demonstrate.
>
> If you want to import `jwt_provider2`'s modules from other addons, use `odoo.addons.jwt_provider2` as base.
>
> Example: `from odoo.addons.jwt_provider2.JwtRequest import jwt_request`

A middleware is a simple python function, with the following signature:

```python
def my_middleware(req: JwtRequest, data: MiddlewareData, *kargs, **kwargs):
    if something is not True:
        raise MiddlewareException()
```

It checks if the request is valid or not, it raises a `MiddlewareException` to stop the execution and respond the error. If nothing happens, the next middleware is going to be executed. If there is no middleware left, the controller method will finally kick in.

> It's best to envision middleware as a series of "layers" HTTP requests must pass through before they hit your application. Each layer can examine the request and even reject it entirely.
>
>  *(from Laravel middleware documentation)*

**Remember**:
- To **stop a middleware**, raise an `Exception`.
- To **continue** to the next middleware/controller execution, do not return anything other than falsy value (`False`, `None`, ...).

Let's create a simple middleware named `api_key_middleware`, we only allow request with correct api key provided in the request header `X-Api-Key`, otherwise we respond with an error immediately by raising a `MiddlewareException`:

```python
from .middleware.MiddlewareData import MiddlewareData
from .middleware.MiddlewareException import MiddlewareException
from .JwtRequest import jwt_request


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

As you can see, in the above code, once we have the middleware definition, we alias it with a name `api_key`:

```python
jwt_request.register_middleware('api_key', api_key_middleware)
```

## Assigning middleware

To assign middlewares to routes, we decorate the controller method with:

```python
@jwt_request.middlewares('first', require_groups(['base.group_user']), other_middleware, ('tuple_middleware', 'additional data to middleware'))
```

Parameter types allowed to pass to decorator:

- '`string`' - aliased middleware using `jwt_request.register_middleware`
- `function(*kargs, **kwargs)`
- tuple `('aliased_name', 'some data, dict, list, ...etc')` - the first item of tuple is the alias of a middleware, the second is addtional data that middleware can uses. Accessing that data by calling `data = kwargs.get('param')`:
    ```python
    def my_middleware(req: JwtRequest, *k, **kwargs):
        data = kwargs.get('param') # should yield 'additional data to middleware' in the above example
        ...
    ```

Let's continue with the api key middleware in the previous section, create a controller method and decorate it:

```python
from odoo import http
from ..JwtRequest import jwt_request


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

It's not necessary to register a middleware function (but is recommended). Instead, we can add it directly to the decorator `@jwt_request.middlewares()`:

```python
def api_key_middleware(req: JwtRequest, data: MiddlewareData, *k, **kw):
    ...


class TestController(http.Controller):
    @http.route('/api/hello', type='http', auth='public', csrf=False, cors='*')
    # decorate middleware
    @jwt_request.middlewares(api_key_middleware)
    def hello(self, **kw):
        ...
```

## Passing external data and sharing data among middlewares

### Passing external data to middleware

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

Here we actually wrap the middleware function (`def handler`), this handler can access the variable `groups`:

- First, it check if user is already logged in via `jwt`
- Next, `req.odoo_req` is a reference to `odoo.http.request`, get the logged in user, and check if user has any group in `['base.group_system']`.
- Finally, if at least one group satisfies, process to the next middleware by calling `return`. Else, just raise an exception to stop the request (and respond an error).


And finally in the controller method, we call the function like this:

```python
@http.route(...)
@jwt_request.middlewares(require_groups(['base.group_system']))
def get_admin_privilege(self, *kargs, **kwargs):
    ...
```

### Sharing data

A middleware might need to get data shared from the revious middlewares. We can use the param `data`:

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
    shared = jwt_request.data.get('key_info')
    ...
```

Controller can also access the shared data too, use: `jwt_request.data.get('some_key')`

## Global middleware

Global middlewares always run before normal ones do, only when you decorate controller route with `@jwt_request.middlewares()` (empty param is ok).

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

## Grouping middleware

Tired of using the same, multiple-middleware decorator for every route?

```python
@http.route()
@jwt_request.middlewares('jwt', 'first', 'second', 'last')
def route_a(*k, **kw):
    pass

@http.route()
@jwt_request.middlewares('jwt', 'first', 'second', 'last')
def route_b(*k, **kw):
    pass
```

Let's write a grouped middleware.

```python
# middlewares
def grouped_middleware(req: JwtRequest, *k, **kw):
    req.exec_middleware('jwt')
    req.exec_middleware('first')
    req.exec_middleware('second')
    req.exec_middleware('last')

jwt_request.register_middleware('all', grouped_middleware)

# controllers
@http.route()
@jwt_request.middlewares('all')
def route_b(*k, **kw):
    pass

@http.route()
@jwt_request.middlewares('all')
def route_b(*k, **kw):
    pass
```

Here we learned that, to execute a middleware inside a middleware, we use `req.exec_middleware`. The param pass to `req.exec_middleware` may be an alias, a function, or a tuple, just like how we call `@jwt_request.middlewares`.

## Middleware exception and response

There are several ways to stop the request and respond the result while executing middleware logic:

- Raise an exception
- Return a Response directly

With `raise MiddlewareException('some error message', 400, 'unauthorized')`, our JwtRequest will respond with the following json data:

```json
// as json RPC
{
    "result": {
        "code": 400,
        "message": "some error message",
        "type": "unauthorized"
    }
}

// as http request, with an http status code of 400
{
    "code": 400,
    "message": "some error message",
    "type": "unauthorized"
}
```

We can return a response directly in middleware:

```python
def some_middleware(req: JwtRequest, *k, **kw):
    return req.response({
        'error': True,
        'message': 'some error message',
    }, status=404)
```

Want consistent response structure from every middleware error? Create a custom exception, with a `response` method:

```python
import .JwtRequest from jwt_request

# you should always raise this exception in your middleware's code logic
class MyAppExcetion(Exception):
    def __init__(self, message=None, status_code=500):
        self.message = message
        self.status_code = status_code

    def response(self):
        return jwt_request.response({
            'message': self.message,
        }, status=self.status_code)

# middleware raise
def my_middleware(req: JwtRequest, *k, **kw):
    raise MyAppException('something went wrong', 500)
    # or
    return jwt_request.response('something went wrong', 500)
```

Don't want our built-in `jwt_request.response()`? Create a custom response method, and an Exception like above (but using your new method).

For the response, you should determine which one is suitable for either Json RPC or http request. Simply, a Json RPC is a request which contains header `Content-Type: application/json`. You get to know this because you are the one who writes endpoint. But, to simplify in some cases you want to change a request type from one to another, without touching much to the response, wrap every case of request in a single response function, with the help of `jwt_request.is_rpc()`.

```python
from odoo.http import Response
import .JwtRequest from jwt_request
from simplejson import dumps


def my_response(data={}, status_code=200):
    # is json rpc request
    if jwt_request.is_rpc():
        return {
            'status_code': status_code,
            'data': data,
        }
    # else, response for a http request
    return Response(dumps(data), status=status_code, headers=[
        ('Content-Type', 'application/json'),
    ])

# using my_response in your custom exception
class MyAppExcetion(Exception):
    def __init__(self, message=None, status_code=500):
        self.message = message
        self.status_code = status_code

    def response(self):
        return my_response({
            'message': self.message,
        }, status_code=self.status_code)
```

> **Attention:** Json RPC cannot respond a custom http status code as you want. It is hard-coded in Odoo as 200, unfortunately. They might change that in the future, who knows?
