# JWT Provider v2

This module is a completely rework of the original `jwt_provider`, with a nice and cleaner codebase for developers to easily implement into their app.

**Please note** that this version is only compatible with **`odoo 14`**

**Hey there**, We need help fixing/completing the readme. If there are confusions, please do not hesitate to open an issue. Pull requests are welcome, too!

## Prerequisites and Installation

This module requires `pyjwt` and `simplejson` to be installed. See `requirements.txt`.

Download or clone this repo and move it to odoo addons dir. Install it via odoo just like a normal module.

## Environment

By default, `jwt_provider2` uses the environment variable `ODOO_JWT_KEY` to hash jwt signature.

## Example

Full example, see `middlewares.py` and uncomment all routes in either `api_http.py` (for normal http request) or `api_json.py` (for json rpc) in `controllers` directory.

<!-- ### JwtRequest class

`JwtRequest` comes with a nice `response` method, that auto detects the request type (http or json rpc) and responds the correct one for us.

Documentation coming soon.

### Implement your own jwt auth

Coming soon. -->
