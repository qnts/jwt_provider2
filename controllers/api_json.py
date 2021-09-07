# -*- coding: utf-8 -*-
from ..middlewares import require_groups
from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.models.res_users import SignupError
from ..JwtRequest import jwt_request
from ..util import is_valid_email


import logging
_logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ['password', 'password_crypt', 'new_password', 'create_uid', 'write_uid']


class JwtRPCController(http.Controller):

    @http.route('/api/rpc/hello', type='json', auth='public', csrf=False, cors='*')
    @jwt_request.middlewares()
    def hello(self, **kw):
        '''
        example usage of middleware
        '''
        # error = jwt_request.requires(
        #     # passing params=[['base.group_system']] to middleware group
        #     # ('group', ['base.group_system']),
        #     # the following is the same as above, but different approach
        #     # call this will return an handler, thus satisfy middleware signature
        #     # require_groups(['base.group_system']),
        # )
        # if error: return error
        return jwt_request.response({ 'message': 'hello!', 'key_info': jwt_request.data.get('key_info') })


    # @http.route('/api/rpc/login', type='json', auth='public', csrf=False, cors='*', methods=['POST'])
    # def login(self, email, password, **kw):
    #     token = jwt_request.login(email, password)
    #     return self._response_auth(token)


    # @http.route('/api/rpc/me', type='json', auth='public', csrf=False, cors='*')
    # @jwt_request.middlewares('jwt')
    # def me(self, **kw):
    #     return jwt_request.response(request.env.user.to_dict())


    # @http.route('/api/rpc/logout', type='json', auth='public', csrf=False, cors='*')
    # def logout(self, **kw):
    #     error = jwt_request.requires('jwt')
    #     if error: return error

    #     jwt_request.logout()
    #     return jwt_request.response()


    # @http.route('/api/rpc/register', type='json', auth='public', csrf=False, cors='*', methods=['POST'])
    # def register(self, email=None, name=None, password=None, **kw):
    #     '''
    #     In previous version, we use auth_signup to register an external (portal) user.
    #     For this demo, we use res.users.create instead, this will create an internal user
    #     '''
    #     if not is_valid_email(email):
    #         return jwt_request.response(status=400, data={'message': 'Invalid email address'})
    #     if not name:
    #         return jwt_request.response(status=400, data={'message': 'Name cannot be empty'})
    #     if not password:
    #         return jwt_request.response(status=400, data={'message': 'Password cannot be empty'})

    #     # sign up
    #     try:
    #         if request.env['res.users'].sudo().search([('login', '=', email)]):
    #             return jwt_request.response(status=400, data={'message': 'Email address is not available'})
    #         user = request.env['res.users'].sudo().create({
    #             'login': email,
    #             'password': password,
    #             'name': name,
    #             'email': email,
    #         })
    #         if user:
    #             # no need to authenticate user here
    #             # cuz we just respond data right away
    #             # if you really need to authenticate user, use jwt_request.login(email, password)
    #             # token can be used instead of password
    #             # create token
    #             token = jwt_request.create_token(user)
    #             return jwt_request.response({
    #                 'user': user.to_dict(),
    #                 'token': token
    #             })
    #     except Exception as e:
    #         _logger.error(str(e))
    #         return jwt_request.response_500({
    #             'message': 'Server error'
    #         })


    # @http.route('/api/rpc/signup', type='json', auth='public', csrf=False, cors='*', methods=['POST'])
    # def register(self, email=None, name=None, password=None, **kw):
    #     '''
    #     Sign up using auth_signup modules
    #     '''
    #     if not is_valid_email(email):
    #         return jwt_request.response(status=400, data={'message': 'Invalid email address'})
    #     if not name:
    #         return jwt_request.response(status=400, data={'message': 'Name cannot be empty'})
    #     if not password:
    #         return jwt_request.response(status=400, data={'message': 'Password cannot be empty'})

    #     # sign up
    #     try:
    #         model = request.env['res.users'].sudo()
    #         signup = getattr(model, 'signup')
    #         if signup:
    #             if request.env['res.users'].sudo().search([('login', '=', email)]):
    #                 return jwt_request.response(status=400, data={'message': 'Email address is not available'})
    #             data = {
    #                 'login': email,
    #                 'password': password,
    #                 'name': name,
    #                 'email': email,
    #             }
    #             # signup return a tuple (db, login, password)
    #             # you can use that to call jwt_request.login(login, password)
    #             signup(data)
    #             # but, we just need to retrieve the newly created user
    #             user = model.search([
    #                 ('login', '=', email)
    #             ])
    #             if user:
    #                 token = jwt_request.create_token(user)
    #                 return jwt_request.response({
    #                     'user': user.to_dict(),
    #                     'token': token
    #                 })
    #             raise Exception()
    #     except SignupError:
    #         return jwt_request.response({
    #             'message': 'Signup is currently disabled',
    #         }, 400)
    #     except Exception as e:
    #         _logger.error(str(e))
    #         return jwt_request.response_500({
    #             'message': 'Cannot create user'
    #         })

    # def _response_auth(self, token: str):
    #     return jwt_request.response({
    #         'user': request.env.user.to_dict(),
    #         'token': token,
    #     })
