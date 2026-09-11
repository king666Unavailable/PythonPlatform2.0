"""Django project configuration package."""

# PyMySQL provides the DB-API module expected by Django's MySQL backend.
# Keeping this shim here avoids requiring a native compiler for mysqlclient.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    # Commands that only use the testing/SQLite settings can still start and
    # report the missing optional dependency in the normal import path.
    pass
