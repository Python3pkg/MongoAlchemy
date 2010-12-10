
class BadValueException(Exception):
    '''An exception which is raised when there is something wrong with a 
        value'''
    def __init__(self, name, value, reason, cause=None):
        self.name = name
        self.value = value
        self.cause = cause
        Exception.__init__(self, 'Bad value for field of type "%s".  Reason: "%s".  Cause: %s' % (name, reason, cause))

class InvalidConfigException(Exception):
    pass

class DocumentException(Exception):
    ''' Base for all document-related exceptions'''
    pass

class MissingValueException(DocumentException):
    ''' Raised when a required field isn't set '''
    pass

class ExtraValueException(DocumentException):
    ''' Raised when a value is passed in with no corresponding field '''
    pass

class FieldNotRetrieved(DocumentException):
    '''If a partial document is loaded from the database and a field which 
        wasn't retrieved is accessed this exception is raised'''
    pass