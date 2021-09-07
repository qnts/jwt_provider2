
class MiddlewareData:
    '''
    Just a simple class for conveniently manipulate and share data between middleware
    '''
    data = {}

    def set(self, key: any, data = None):
        '''
        Set shared data
        '''
        if type(key) is dict:
            self.data.update(key)
        else:
            self.data[key] = data


    def get(self, key: str, default = None):
        '''
        Get shared data from key
        '''
        return self.data.get(key, default)
