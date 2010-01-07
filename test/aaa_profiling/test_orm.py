from sqlalchemy.test.testing import eq_, assert_raises, assert_raises_message
from sqlalchemy import exc as sa_exc, util, Integer, String, ForeignKey
from sqlalchemy.orm import exc as orm_exc, mapper, relation, sessionmaker

from sqlalchemy.test import testing, profiling
from test.orm import _base
from sqlalchemy.test.schema import Table, Column


class MergeTest(_base.MappedTest):
    @classmethod
    def define_tables(cls, metadata):
        parent = Table('parent', metadata,
            Column('id', Integer, primary_key=True, test_needs_autoincrement=True),
            Column('data', String(20))
        )

        child = Table('child', metadata,
            Column('id', Integer, primary_key=True, test_needs_autoincrement=True),
            Column('data', String(20)),
            Column('parent_id', Integer, ForeignKey('parent.id'), nullable=False)
        )


    @classmethod
    def setup_classes(cls):
        class Parent(_base.BasicEntity):
            pass
        class Child(_base.BasicEntity):
            pass

    @classmethod
    @testing.resolve_artifact_names
    def setup_mappers(cls):
        mapper(Parent, parent, properties={
            'children':relation(Child, backref='parent')
        })
        mapper(Child, child)

    @classmethod
    @testing.resolve_artifact_names
    def insert_data(cls):
        parent.insert().execute(
            {'id':1, 'data':'p1'},
        )
        child.insert().execute(
            {'id':1, 'data':'p1c1', 'parent_id':1},
        )
    
    @testing.resolve_artifact_names
    def test_merge_no_load(self):
        sess = sessionmaker()()
        sess2 = sessionmaker()()
        
        p1 = sess.query(Parent).get(1)
        p1.children
        
        # down from 185 on this
        # this is a small slice of a usually bigger
        # operation so using a small variance
        @profiling.function_call_count(106, variance=0.001)
        def go():
            p2 = sess2.merge(p1, load=False)
            
        go()

    @testing.resolve_artifact_names
    def test_merge_load(self):
        sess = sessionmaker()()
        sess2 = sessionmaker()()

        p1 = sess.query(Parent).get(1)
        p1.children

        # preloading of collection took this down from 1728
        # to 1192 using sqlite3
        @profiling.function_call_count(1192)
        def go():
            p2 = sess2.merge(p1)
        go()
        
        # one more time, count the SQL
        sess2 = sessionmaker()()
        self.assert_sql_count(testing.db, go, 2)
            