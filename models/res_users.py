import werkzeug
from odoo.exceptions import AccessDenied
from odoo import api, models, fields
from ..JwtRequest import jwt_request

class Users(models.Model):
    _inherit = "res.users"

    access_token_ids = fields.One2many(
        string='Access Tokens',
        comodel_name='jwt_provider.access_token',
        inverse_name='user_id',
    )

    avatar = fields.Char(compute='_compute_avatar')

    # new in odoo 14, the last param is user_agent_env
    @classmethod
    def _login(cls, db, login, password, user_agent_env={}):
        user_id = super(Users, cls)._login(db, login, password, user_agent_env)
        if user_id:
            return user_id

        uid = jwt_request.verify(password)

        return uid

    @api.model
    def _check_credentials(self, password, user_agent_env={}):
        try:
            super(Users, self)._check_credentials(password, user_agent_env)
        except AccessDenied:
            # verify password as token
            if not jwt_request.verify(password):
                raise

    @api.depends()
    def _compute_avatar(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for u in self:
            u.avatar = werkzeug.urls.url_join(base, 'web/avatar/%d' % u.id)

    def to_dict(self, single=True):
        res = []
        for u in self:
            d = u.read(['email', 'name', 'avatar', 'company_id'])[0]
            res.append(d)

        return res[0] if single else res
