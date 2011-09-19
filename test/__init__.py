"""
MongoAlchemy tests package.

There's a bunch of tests here, man.

"""

from util import get_session


def setup():
    """
    Destroy the whole damn database before running tests! WOO!

    We would do this afterwards, but sometimes you might need to do a
    post-mortem on the state of the database.

    """
    with get_session() as s:
        colls = s.db.collection_names()
        for coll in colls:
            if coll == 'system.indexes':
                continue
            s.db[coll].drop_indexes()
            s.db[coll].drop()

        s.db.command({'dropDatabase':1})

