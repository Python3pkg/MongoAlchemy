# The MIT License
#
# Copyright (c) 2010 Jeffrey Jenkins
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import wraps
from collections import namedtuple
from pymongo import ASCENDING, DESCENDING
from copy import copy, deepcopy

from mongoalchemy.query_expression import QueryExpression, BadQueryException, flatten
from mongoalchemy.update_expression import UpdateExpression, FindAndModifyExpression
from mongoalchemy.exceptions import NoResultFound, MultipleResultsFound, \
        BadValueException, BadResultException


class Query(object):
    ''' A query object has all of the methods necessary to programmatically
        generate a mongo query as well as methods to retrieve results of the
        query or do an update based on it.

        In general a query object should be created via ``Session.query``,
        not directly.
    '''
    def __init__(self, type, session):
        ''' :param type: A subclass of class:`mongoalchemy.document.Document`
            :param db: The :class:`~mongoalchemy.session.Session` which this query is associated with.
        '''
        self.session = session
        self.type = type
        self.__query = {}
        self.sort = []
        self._fields = None
        self._field_order = []
        self._values_only = None
        self.hints = []
        self._limit = None
        self._skip = None
        self._raw_output = False

    def __iter__(self):
        return self.__get_query_result()

    def resolve_name(self, name):
        if not isinstance(name, str) or name[0] == '$':
            return name
        ret = self.type
        for part in name.split('.'):
            ret = getattr(ret, part)
        return ret

    @property
    def query(self):
        return flatten(self.__query)

    def __get_query_result(self):
        return self.session.execute_query(self)

    def raw_output(self):
        self._raw_output = True
        return self

    def get_fields(self):
        return self._fields

    def get_limit(self):
        return self._limit

    def get_skip(self):
        return self._skip

    def limit(self, limit):
        ''' Sets the limit on the number of documents returned

            :param limit: the number of documents to return
        '''
        self._limit = limit
        return self

    def skip(self, skip):
        ''' Sets the number of documents to skip in the result

            :param skip: the number of documents to skip
        '''
        self._skip = skip
        return self

    def clone(self):
        ''' Creates a clone of the current query and all settings.  Further
            updates to the cloned object or the original object will not
            affect each other
        '''
        qclone = Query(self.type, self.session)
        qclone.__query = deepcopy(self.__query)
        qclone.sort = deepcopy(self.sort)
        qclone._fields = deepcopy(self._fields)
        qclone._field_order = copy(self._field_order)
        qclone._values_only = deepcopy(self._values_only)
        qclone._hints = deepcopy(self.hints)
        qclone._limit = deepcopy(self._limit)
        qclone._skip = deepcopy(self._skip)
        qclone._raw_output = deepcopy(self._raw_output)
        return qclone

    def one(self):
        ''' Execute the query and return one result.  If more than one result
            is returned, raises either ``MultipleResultsFound`` or
            ``NoResultFound`` as appropriate.
        '''
        count = -1
        for count, result in enumerate(self):
            if count > 0:
                raise MultipleResultsFound('Too many results for .one()')
        if count == -1:
            raise NoResultFound('Too few results for .one()')
        return result

    def first(self):
        ''' Execute the query and return the first result.  Unlike ``one``, if
            there are multiple documents it simply returns the first one.  If
            there are no documents, first returns ``None``
        '''
        for doc in iter(self):
            return doc
        return None

    def __getitem__(self, index):
        return self.__get_query_result().__getitem__(index)

    def hint_asc(self, qfield):
        ''' Applies a hint for the query that it should use a
            (``qfield``, ASCENDING) index when performing the query.

            :param qfield: the instance of :class:`mongoalchemy.QueryField` to use as the key.
        '''
        return self.__hint(qfield, ASCENDING)

    def hint_desc(self, qfield):
        ''' Applies a hint for the query that it should use a
            (``qfield``, DESCENDING) index when performing the query.

            :param qfield: the instance of :class:`mongoalchemy.QueryField` to use as the key.
        '''
        return self.__hint(qfield, DESCENDING)

    def __hint(self, qfield, direction):
        qfield = self.resolve_name(qfield)
        name = str(qfield)
        for n, _ in self.hints:
            if n == name:
                raise BadQueryException('Already gave hint for %s' % name)
        self.hints.append((name, direction))
        return self

    def explain(self):
        ''' Executes an explain operation on the database for the current
            query and returns the raw explain object returned.
        '''
        return self.__get_query_result().cursor.explain()

    def all(self):
        ''' Return all of the results of a query in a list'''
        return [obj for obj in iter(self)]

    def distinct(self, key):
        ''' Execute this query and return all of the unique values
            of ``key``.

            :param key: the instance of :class:`mongoalchemy.QueryField` to use as the distinct key.
        '''
        return self.__get_query_result().cursor.distinct(str(key))

    def filter(self, *query_expressions):
        ''' Apply the given query expressions to this query object

            **Example**: ``s.query(SomeObj).filter(SomeObj.age > 10, SomeObj.blood_type == 'O')``

            :param query_expressions: Instances of :class:`mongoalchemy.query_expression.QueryExpression`

            .. seealso:: :class:`~mongoalchemy.query_expression.QueryExpression` class
        '''
        for qe in query_expressions:
            if isinstance(qe, dict):
                self._apply_dict(qe)
            else:
                self._apply(qe)
        return self

    def filter_by(self, **filters):
        ''' Filter for the names in ``filters`` being equal to the associated
            values.  Cannot be used for sub-objects since keys must be strings'''
        for name, value in filters.items():
            self.filter(self.resolve_name(name) == value)
        return self

    def count(self, with_limit_and_skip=False):
        ''' Execute a count on the number of results this query would return.

            :param with_limit_and_skip: Include ``.limit()`` and ``.skip()`` arguments in the count?
        '''
        return self.__get_query_result().cursor.count(with_limit_and_skip=with_limit_and_skip)

    def fields(self, *fields, **kwargs):
        ''' Only return the specified fields from the object.  Accessing a \
            field that was not specified in ``fields`` will result in a \
            :class:``mongoalchemy.document.FieldNotRetrieved`` exception being \
            raised.

            If ``values_only`` is ``True`` then instead of the query returning
            partial Documents, it will return named tuples containing the
            values of the fields in the order specified.

            :param fields: Instances of :class:``mongoalchemy.query.QueryField`` specifying \
                which fields to return
            :param values_only: Only return values instead of a Document \
                    (default: False).

        '''
        if self._fields == None:
            self._fields = set()
        vals = kwargs.pop('values_only', None)
        if vals is not None:
            self._values_only = vals
        for f in fields:
            f = self.resolve_name(f)
            if f not in self._field_order:
                self._field_order.append(f)
            self._fields.add(f)
        if not vals:
            self._fields.add(self.type.mongo_id)
        return self

    def _apply(self, qe):
        ''' Apply a raw mongo query to the current raw query object'''
        self._apply_dict(qe.obj)

    def _apply_dict(self, qe_dict):
        ''' Apply a query expression, updating the query object '''
        for k, v in qe_dict.items():
            k = self.resolve_name(k)
            if not k in self.__query:
                self.__query[k] = v
                continue
            if not isinstance(self.__query[k], dict) or not isinstance(v, dict):
                raise BadQueryException('Multiple assignments to a field must all be dicts.')
            self.__query[k].update(**v)


    def ascending(self, qfield):
        ''' Sort the result based on ``qfield`` in ascending order.  These calls
            can be chained to sort by multiple fields.

            :param qfield: Instance of :class:``mongoalchemy.query.QueryField`` \
                specifying which field to sort by.
        '''
        return self.__sort(qfield, ASCENDING)

    def descending(self, qfield):
        ''' Sort the result based on ``qfield`` in ascending order.  These calls
            can be chained to sort by multiple fields.

            :param qfield: Instance of :class:``mongoalchemy.query.QueryField`` \
                specifying which field to sort by.
        '''
        return self.__sort(qfield, DESCENDING)

    def __sort(self, qfield, direction):
        qfield = self.resolve_name(qfield)
        name = str(qfield)
        for n, _ in self.sort:
            if n == name:
                raise BadQueryException('Already sorting by %s' % name)
        self.sort.append((name, direction))
        return self

    def not_(self, *query_expressions):
        ''' Add a $not expression to the query, negating the query expressions
            given.

            **Examples**: ``query.not_(SomeDocClass.age <= 18)`` becomes ``{'age' : { '$not' : { '$gt' : 18 } }}``

            :param query_expressions: Instances of :class:`mongoalchemy.query_expression.QueryExpression`
            '''
        for qe in query_expressions:
            self.filter(qe.not_())
        return self

    def or_(self, first_qe, *qes):
        ''' Add a $not expression to the query, negating the query expressions
            given.  The ``| operator`` on query expressions does the same thing

            **Examples**: ``query.or_(SomeDocClass.age == 18, SomeDocClass.age == 17)`` becomes ``{'$or' : [{ 'age' : 18 }, { 'age' : 17 }]}``

            :param query_expressions: Instances of :class:`mongoalchemy.query_expression.QueryExpression`
        '''
        res = first_qe
        for qe in qes:
            res = (res | qe)
        self.filter(res)
        return self

    def in_(self, qfield, *values):
        ''' Check to see that the value of ``qfield`` is one of ``values``

            :param qfield: Instances of :class:`mongoalchemy.query_expression.QueryExpression`
            :param values: Values should be python values which ``qfield`` \
                understands
        '''
        # TODO: make sure that this field represents a list
        qfield = self.resolve_name(qfield)
        self.filter(QueryExpression({ qfield : { '$in' : [qfield.wrap_value(value) for value in values]}}))
        return self

    def nin(self, qfield, *values):
        ''' Check to see that the value of ``qfield`` is not one of ``values``

            :param qfield: Instances of :class:`mongoalchemy.query_expression.QueryExpression`
            :param values: Values should be python values which ``qfield`` \
                understands
        '''
        # TODO: make sure that this field represents a list
        qfield = self.resolve_name(qfield)
        self.filter(QueryExpression({ qfield : { '$nin' : [qfield.wrap_value(value) for value in values]}}))
        return self

    def find_and_modify(self, new=False, remove=False):
        ''' The mongo "find and modify" command.  Behaves like an update expression
            in that "execute" must be called to do the update and return the
            results.

            :param new: Whether to return the new object or old (default: False)
            :param remove: Whether to remove the object before returning it
        '''
        return FindAndModifyExpression(self, new=new, remove=remove)


    def set(self, *args, **kwargs):
        ''' Refer to: :func:`~mongoalchemy.update_expression.UpdateExpression.set`'''
        return UpdateExpression(self).set(*args, **kwargs)

    def unset(self, qfield):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.unset`'''
        return UpdateExpression(self).unset(qfield)

    def inc(self, *args, **kwargs):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.inc`'''
        return UpdateExpression(self).inc(*args, **kwargs)

    def append(self, qfield, value):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.append`'''
        return UpdateExpression(self).append(qfield, value)

    def extend(self, qfield, *value):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.extend`'''
        return UpdateExpression(self).extend(qfield, *value)

    def remove(self, qfield, value):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.remove`'''
        return UpdateExpression(self).remove(qfield, value)

    def remove_all(self, qfield, *value):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.remove_all`'''
        return UpdateExpression(self).remove_all(qfield, *value)

    def add_to_set(self, qfield, value):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.add_to_set`'''
        return UpdateExpression(self).add_to_set(qfield, value)

    def pop_first(self, qfield):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.pop_first`'''
        return UpdateExpression(self).pop_first(qfield)

    def pop_last(self, qfield):
        ''' Refer to:  :func:`~mongoalchemy.update_expression.UpdateExpression.pop_last`'''
        return UpdateExpression(self).pop_last(qfield)


class QueryResult(object):
    def __init__(self, cursor, type, raw_output=False, fields=None,
            field_order=tuple(), values_only=False):
        self.cursor = cursor
        self.type = type
        self.fields = fields
        self.field_order = field_order
        self.raw_output = raw_output
        self.values_only = values_only

    def _as_tuple(self, value):
        return namedtuple(self.type.__name__, (field._name \
                for field in self.field_order)) \
                ._make(getattr(self.type, field._name) \
                    .unwrap(value[field.db_field]) \
                    for field in self.field_order)

    def __next__(self):
        value = next(self.cursor)
        if not self.raw_output:
            if self.values_only:
                value = self._as_tuple(value)
            else:
                value = self.type.unwrap(value, fields=self.fields)
        return value

    def __getitem__(self, index):
        value = self.cursor.__getitem__(index)
        if not self.raw_output:
            if self.values_only:
                value = self._as_tuple(value)
            else:
                value = self.type.unwrap(value)
        return value

    def rewind(self):
        return self.cursor.rewind()

    def clone(self):
        return QueryResult(self.cursor.clone(), self.type,
            raw_output=self.raw_output, fields=self.fields,
            field_order=self.field_order, values_only=self.values_only)

    def __iter__(self):
        return self


class RemoveQuery(object):
    def __init__(self, type, session):
        ''' Execute a remove query to remove the matched objects from the database

            :param type: A subclass of class:`mongoalchemy.document.Document`
            :param db: The :class:`~mongoalchemy.session.Session` which this query is associated with.
        '''
        self.session = session
        self.type = type
        self.safe = None
        self.get_last_args = {}
        self.__query_obj = Query(type, session)

    @property
    def query(self):
        return self.__query_obj.query

    def set_safe(self, is_safe, **kwargs):
        ''' Set this remove to be safe.  It will call getLastError after the
            remove to make sure it was successful.  ``**kwargs`` are parameters to
            MongoDB's getLastError command (as in pymongo's remove).
        '''
        self.safe = is_safe
        self.get_last_args.update(**kwargs)
        return self

    def execute(self):
        ''' Run the remove command on the session.  Return the result of
            ``getLastError`` if ``safe`` is ``True``'''
        return self.session.execute_remove(self)

    def filter(self, *query_expressions):
        ''' Filter the remove expression with ``*query_expressions``, as in
            the ``Query`` filter method.'''
        self.__query_obj.filter(*query_expressions)
        return self

    def filter_by(self, **filters):
        ''' Filter for the names in ``filters`` being equal to the associated
            values.  Cannot be used for sub-objects since keys must be strings'''
        self.__query_obj.filter_by(**filters)
        return self

    # def not_(self, *query_expressions):
    #     self.__query_obj.not_(*query_expressions)
    #     self.query = self.__query_obj.query
    #     return self

    def or_(self, first_qe, *qes):
        ''' Works the same as the query expression method ``or_``
        '''
        self.__query_obj.or_(first_qe, *qes)
        return self

    def in_(self, qfield, *values):
        ''' Works the same as the query expression method ``in_``
        '''

        self.__query_obj.in_(qfield, *values)
        return self

    def nin(self, qfield, *values):
        ''' Works the same as the query expression method ``nin_``
        '''
        self.__query_obj.nin(qfield, *values)
        return self


