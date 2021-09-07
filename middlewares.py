# -*- coding: utf-8 -*-

from .middleware.MiddlewareData import MiddlewareData
import jwt
from .JwtRequest import JwtRequest, jwt_request, InvalidTokenException
from .middleware.MiddlewareException import MiddlewareException

import logging
_logger = logging.getLogger(__name__)

def jwt_auth(req: JwtRequest, *k, **kw):
    try:
        req.validate_token(token=req.token, auth=True)
    except jwt.ExpiredSignatureError:
        raise MiddlewareException('Token expired', 401)
    except (InvalidTokenException, jwt.InvalidTokenError, Exception) as e:
        raise MiddlewareException('Invalid token', 401)


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


def require_groups_alias(req: JwtRequest, *k, **kw):
    groups = kw.get('param', [])
    # first need to be authenticated
    req.exec_middleware('jwt')
    # then check groups
    for group in groups:
        if req.odoo_req.env.user.has_group(group):
            return
    raise MiddlewareException('Insufficient privilege', 403, 'no_privilege')


# sample middleware
def api_key_middleware(req: JwtRequest, data: MiddlewareData, *k, **kw):
    # get api key from headers, note: header keys are always capitalized
    api_key = req.headers.get('X-Api-Key')
    if api_key != 'secret':
        raise MiddlewareException('Invalid Api Key', 400, 'invalid_api_key')
    # store data to jwt_request
    data.set('key_info', {
        'client': 'some client name',
        'expiry': '2025-01-01',
    })


def logger(req: JwtRequest, *k, **kw):
    _logger.info('---Begin Request---')
    req.on_end(lambda req, res: _logger.info(f'---End Response: {str(res)}'))


# example of registering middleware handler
jwt_request.register_middleware('api_key', api_key_middleware)
jwt_request.register_middleware('jwt', jwt_auth)
jwt_request.register_middleware('group', require_groups_alias)
jwt_request.register_middleware('logger', logger)

# these middleware will always run
# but you need to decorate http method with @jwt_request.middlewares()
# jwt_request.middleware_always('logger')
