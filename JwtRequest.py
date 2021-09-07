from simplejson import dumps
import datetime
import traceback
import functools
from odoo import http
from odoo.http import request, Response
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from .middleware.MiddlewareData import MiddlewareData
from .middleware.MiddlewareException import MiddlewareException
from . import util

import logging
_logger = logging.getLogger(__name__)


class InvalidTokenException(Exception):
    pass


class JwtRequest:
    body = {}
    method = 'get'
    headers = {}
    token = ''
    data: MiddlewareData
    # list of main middlewares
    middleware_list = {}
    # list of innate middlewares
    innate = []

    def __init__(self):
        self.odoo_req = request
        self.data = MiddlewareData()


    def parse_request(self):
        '''
        This can only be called inside controller method.

        Parse and store request info { method, body, headers, token }
        '''

        method = str(request.httprequest.method).lower()
        try:
            body = http.request.params
        except Exception:
            body = {}
        headers = dict(list(request.httprequest.headers.items()))
        token = ''
        # checking headers
        if 'wsgi.input' in headers:
            del headers['wsgi.input']
        if 'wsgi.errors' in headers:
            del headers['wsgi.errors']
        if 'HTTP_AUTHORIZATION' in headers:
            headers['Authorization'] = headers['HTTP_AUTHORIZATION']
        if 'Authorization' in headers:
            try:
                # Bearer token_string
                token = headers['Authorization'].split(' ')[1]
            except Exception:
                pass
        self.method = method
        self.headers = headers
        self.body = body
        self.token = token


    def register_middleware(self, alias: str, handler):
        '''
        Register middleware handler.

        Parameters
        ----------
        `alias` : str
            alias of handler, e.g., `jwt`
        `handler` : callable(request Request)
            a handler to be execute. Must have **kw
        '''
        self.middleware_list[alias] = handler

    def middleware_always(self, handler):
        self.innate.append(handler)

    def _run_handler(self, handler, param=None, alias=''):
        try:
            if callable(handler):
                handler(req=self, data=self.data, param=param)
        except MiddlewareException as e:
            _logger.warning(f'Middleware [{str(alias or handler)}]: {str(e)}')
            message, code = e.build_response()
            return self.response(data=message, status=code)
        except Exception as e:
            _logger.warning(f'Middleware-generic [{str(alias or handler)}]: {str(e)}')
            # custom exception
            if getattr(e, 'response'):
                return e.response()
            # bad request
            return self.response({}, 400)


    def _parse_handler(self, handler):
        if callable(handler): return handler, None
        if type(handler) is tuple:
            h = self.middleware_list.get(handler[0])
            p = handler[1] if len(handler) > 1 else None
            return h, p
        if type(handler) is str:
            # look up middleware_list
            h = self.middleware_list.get(handler)
            if h and callable(h): return h, None
        return None, None


    def _requires_innate(self):
        for m in self.innate:
            handler, param = self._parse_handler(m)
            if handler:
                error = self._run_handler(handler, param)
                if error: return error


    def exec_middleware(self, alias):
        handler, param = self._parse_handler(alias)
        if handler:
            handler(req=self, data=self.data, param=param)


    def _requires_middlewares(self, *alias_list):
        '''
        Iterates each middleware to validate. Can only be called inside controller method.

        @return Response if any validation errors. Else none.
        '''
        for alias in alias_list:
            handler, param = self._parse_handler(alias)
            if handler:
                error = self._run_handler(handler, param, alias)
                if error: return error


    def _requires(self, *alias_list):
        '''
        Iterates each middleware to validate. Can only be called inside controller method.

        @return Response if any validation errors. Else none.
        '''
        error = self._requires_innate()
        if error: return error
        error = self._requires_middlewares(*alias_list)
        if error: return error


    def start(self):
        '''
        init events
        '''
        self.end_events = []
        self.parse_request()

    def end(self, response=None):
        '''
        trigger events
        '''
        for handler in self.end_events:
            if callable(handler):
                handler(req=self, res=response)

    def on_end(self, handler):
        self.end_events.append(handler)


    def middlewares(self, *alias_list):
        '''
        decorator for http controller
        '''
        def exec_http(handler):
            @functools.wraps(handler)
            def execute_all(*k, **kw):
                self.start()
                error = self._requires(*alias_list)
                # middleware error response
                if error:
                    self.end(error)
                    return error
                # controller response
                try:
                    response = handler(*k, **kw)
                    self.end(response)
                    return response
                except Exception as e:
                    self.end(e)
                    raise e
            return execute_all
        return exec_http


    def pure_middlewares(self, *alias_list):
        '''
        decorator for http controller, run middlewares without innate
        '''
        def exec_http(handler):
            @functools.wraps(handler)
            def execute_all(*k, **kw):
                self.start()
                error = self._requires_middlewares(*alias_list)
                # middleware error response
                if error:
                    self.end(error)
                    return error
                # controller response
                try:
                    response = handler(*k, **kw)
                    self.end(response)
                    return response
                except Exception as e:
                    self.end(e)
                    raise e
            return execute_all
        return exec_http


    def is_rpc(self):
        return 'application/json' in request.httprequest._parsed_content_type


    def is_ok_response(self, status=200):
        return status >= 200 and status < 300


    def http_response(self, data={}, status=200):
        '''
        Response normal http request (with controller type='http')
        '''
        return Response(dumps(data), status=status, headers=[
            ('Content-Type', 'application/json'),
        ])


    def rpc_response(self, data={}, status=200):
        '''
        Response json rpc request (with controller type='json')
        '''
        r = {
            'success': True if self.is_ok_response(status) else False,
            'code': status,
        }
        if not self.is_ok_response(status):
            return { **r, **data }
        return { **r, 'data': data }


    def response(self, data={}, status=200):
        '''
        Create a response to either http or rpc request
        '''
        if self.is_rpc():
            return self.rpc_response(data, status)
        return self.http_response(data, status)

    def response_500(self, data={}):
        return self.response(data, 500)

    def response_404(self, data={}):
        return self.response(data, 404)

    def create_token(self, user):
        '''
        Create a token based on user model
        '''
        try:
            exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            payload = {
                'exp': exp,
                'iat': datetime.datetime.utcnow(),
                'sub': user.id,
                'lgn': user.login,
            }
            token = util.sign_token(payload)
            self.save_token(token, user.id, exp)
            return token
        except Exception as ex:
            _logger.error(traceback.format_exc())
            raise


    def save_token(self, token, uid, exp):
        '''Save token to database
        '''
        request.env['jwt_provider.access_token'].sudo().create({
            'user_id': uid,
            'expires': exp.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'token': token,
        })


    def get_state(self):
        '''
        get database state
        '''
        return {
            'd': request.session.db
        }


    def login(self, login, password, with_token=True):
        '''
        Try logging user in use their login & password.

        If `with_token` is `True`, will create a jwt token and return it on success or `false` on failure

        You can access the logged in user through `request.env.user`
        '''
        state = self.get_state()
        uid = request.session.authenticate(state['d'], login, password)
        if not uid:
            return False
        if with_token:
            return self.create_token(request.env.user)
        return True


    def logout(self, token=''):
        try:
            request.session.logout()
            if token:
                request.env['jwt_provider.access_token'].sudo().search([
                    ('token', '=', token)
                ]).unlink()
        except:
            pass


    def cleanup(self):
        # Clean up things after success request
        # use logout here to make request as stateless as possible

        request.session.logout()


    def verify(self, token):
        '''
        Check if jwt token existed in db and is not expired
        '''
        record = request.env['jwt_provider.access_token'].sudo().search([
            ('token', '=', token)
        ])

        if len(record) != 1 or record.is_expired:
            return False

        return record.user_id


    def validate_token(self, token, auth=False):
        '''
        Validate a given jwt token.

        Return True on success or raise exceptions on failure.

        If auth=True, will also log user in with that token.
        '''
        # first token must be in our db
        if not self.verify(token):
            raise InvalidTokenException()

        # decode token, will raise exceptions
        payload = util.decode_token(token)

        if auth:
            # signature: https://github.com/odoo/odoo/blob/14.0/odoo/http.py#L987
            uid = request.session.authenticate(
                request.session.db, login=payload['lgn'], password=token)
            if not uid:
                raise InvalidTokenException()

        return True


jwt_request = JwtRequest()
