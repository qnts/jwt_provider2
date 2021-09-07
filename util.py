import os
import jwt
import re
from dateutil.parser import parse


addons_path = os.path.join(os.path.dirname(os.path.abspath(__file__))).replace('jwt_provider2', '')

regex = r"^[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"

def is_valid_email(email):
    return re.search(regex, email)


def to_date(pg_time_string):
    return parse(pg_time_string)


def get_path(*paths):
    ''' Make a path
    '''
    return os.path.join(addons_path, *paths)

def key():
    return os.environ.get('ODOO_JWT_KEY') or ''


def sign_token(payload):
    '''
    Generally sign a jwt token
    '''
    token = jwt.encode(
        payload,
        key(),
        algorithm='HS256'
    )

    return token.decode('utf-8')


def decode_token(token):
    '''
    decode a given jwt token.

    Return True on success or raise exceptions on failure.

    '''
    # decode token, will raise exceptions
    return jwt.decode(token, key())
