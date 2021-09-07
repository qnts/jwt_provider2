
class MiddlewareException(Exception):
    '''
    Attributes
    ----------
    `message`: str
        message to output to response. E.g., `Unauthenticated`
    `status_code`: number
        status code in response. E.g., `401` `403`
    '''

    def __init__(self, message='', status_code=400, type='middleware_exception'):
        self.message = message
        self.status_code = status_code
        self.type = type
        super().__init__(self.message)


    def build_response(self):
        msg = {
            'message': self.message,
            'type': self.type,
            'code': self.status_code,
        }
        return msg, self.status_code


    def __str__(self):
        return self.message
