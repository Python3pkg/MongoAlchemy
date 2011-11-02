
class MongoAlchemyException(Exception):
    ''' Base class for all mongo alchemy related exceptions. '''
    pass


class BadValueException(MongoAlchemyException):
    ''' An exception which is raised when there is something wrong with a
        value'''
    def __init__(self, name, value, reason, cause=None):
        self.name = name
        self.value = value
        self.cause = cause
        message = 'Bad value for field of type "%s".  Reason: "%s".' % (name, reason)
        if cause != None:
            message = '%s Cause: %s' % (message, cause)
        Exception.__init__(self, message)


class InvalidConfigException(MongoAlchemyException):
    ''' Raised when a bad value is passed in for a configuration that expects
        its values to obey certain constraints.'''
    pass


class DocumentException(MongoAlchemyException):
    ''' Base for all document-related exceptions'''
    pass


class MissingValueException(DocumentException):
    ''' Raised when a required field isn't set '''
    pass


class ExtraValueException(DocumentException):
    ''' Raised when a value is passed in with no corresponding field '''
    pass


class FieldNotRetrieved(DocumentException):
    ''' If a partial document is loaded from the database and a field which
        wasn't retrieved is accessed this exception is raised'''
    pass


class BadFieldSpecification(MongoAlchemyException):
    ''' An exception that is raised when there is an error in creating a
        field'''
    pass


class BadResultException(MongoAlchemyException):
    ''' Raised when .one() finds more than one result or no results. '''
    pass


class BadQueryException(MongoAlchemyException):
    ''' Raised when a method would result in a query which is not well-formed.
    '''
    pass


class UpdateException(MongoAlchemyException):
    ''' Base class for exceptions related to updates '''
    pass


class InvalidModifierException(UpdateException):
    ''' Exception raised if a modifier was used which isn't valid for a 
        field '''
    def __init__(self, field, op):
        UpdateException.__init__(self, 'Invalid modifier for %s field: %s' % \
                (field.__class__.__name__, op))


class ConflictingModifierException(UpdateException):
    ''' Exception raised if conflicting modifiers are being used in the
        update expression '''
    pass
