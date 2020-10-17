import random

from ..exceptions import DriverNotFound
from .BaseConnection import BaseConnection
from ..query.grammars import MSSQLGrammar
from ..schema.platforms import MSSQLPlatform


CONNECTION_POOL = []


class MSSQLConnection(BaseConnection):
    """Postgres Connection class."""

    name = "mssql"

    def __init__(
        self,
        host=None,
        database=None,
        user=None,
        port=None,
        password=None,
        prefix=None,
        options={},
    ):

        self.host = host
        if port:
            self.port = int(port)
        else:
            self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.prefix = prefix
        self.options = options
        self._cursor = None
        self.transaction_level = 0
        self.closed = 0

    def make_connection(self):
        """This sets the connection on the connection class"""
        try:
            import pyodbc
        except ModuleNotFoundError:
            raise DriverNotFound(
                "You must have the 'pyodbc' package installed to make a connection to Microsoft SQL Server. Please install it using 'pip install pyodbc'"
            )

        self._connection = pyodbc.connect(
            f"DRIVER={'ODBC Driver 17 for SQL Server'};SERVER={self.host},{self.port};DATABASE={self.database};UID={self.user};PWD={self.password}",
            autocommit=True,
        )

        return self

    def get_database_name(self):
        return self.database

    @classmethod
    def get_default_query_grammar(cls):
        return MSSQLGrammar

    @classmethod
    def get_default_platform(cls):
        return MSSQLPlatform

    def reconnect(self):
        pass

    def commit(self):
        """Transaction"""
        if self.get_transaction_level() == 1:
            self._connection.commit()
            self._connection.autocommit = True

        self.transaction_level -= 1

    def begin(self):
        """Postgres Transaction"""
        self._connection.autocommit = False
        self.transaction_level += 1
        return self._connection

    def rollback(self):
        """Transaction"""
        if self.get_transaction_level() == 1:
            self._connection.rollback()
            self._connection.autocommit = True

        self.transaction_level -= 1

    def get_transaction_level(self):
        """Transaction"""
        return self.transaction_level

    def get_cursor(self):
        return self._cursor

    def query(self, query, bindings=(), results="*"):
        """Make the actual query that will reach the database and come back with a result.

        Arguments:
            query {string} -- A string query. This could be a qmarked string or a regular query.
            bindings {tuple} -- A tuple of bindings

        Keyword Arguments:
            results {str|1} -- If the results is equal to an asterisks it will call 'fetchAll'
                    else it will return 'fetchOne' and return a single record. (default: {"*"})

        Returns:
            dict|None -- Returns a dictionary of results or None
        """

        try:
            if self.closed:
                self.make_connection()
            self._cursor = self._connection.cursor()
            with self._cursor as cursor:
                if isinstance(query, list) and not self._dry:
                    for q in query:
                        self.statement(q, ())
                    return
                query = query.replace("'?'", "?")
                self.statement(query, bindings)
                if results == 1:
                    if not cursor.description:
                        return {}
                    columnNames = [column[0] for column in cursor.description]
                    result = cursor.fetchone()
                    return dict(zip(columnNames, result))
                else:
                    columnNames = [column[0] for column in cursor.description]
                    results = []
                    for record in cursor.fetchall():
                        results.append(dict(zip(columnNames, record)))
                    return results

                return {}
        except Exception as e:
            raise e
        finally:
            pass
            # if self.get_transaction_level() <= 0:
            #     self._connection.close()
