"""
============================================
💾 Database Connection Module
Driver Drowsiness Detection System
Singleton Pattern for MySQL Connection
============================================
"""

import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, Any, List, Tuple
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config


class DatabaseConnection:
    """
    Singleton class for managing MySQL database connections.
    Uses connection pooling for better performance.
    """
    
    _instance: Optional['DatabaseConnection'] = None
    _pool: Optional[pooling.MySQLConnectionPool] = None
    
    def __new__(cls) -> 'DatabaseConnection':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool (Supports both Local and Railway/URL)"""
        try:
            from src.config.database import DATABASE_URL
            from urllib.parse import urlparse
            
            # Parse settings from DATABASE_URL
            # Expected format: mysql+mysqlconnector://user:pass@host:port/dbname
            # We strip 'mysql+mysqlconnector://' to simple 'mysql://' for parsing transparency if needed,
            # but urlparse handles schemes fine.
            
            parsed = urlparse(DATABASE_URL)
            
            # Extract params
            _host = parsed.hostname
            _port = parsed.port or 3306
            _user = parsed.username
            _password = parsed.password
            _db_name = parsed.path.lstrip('/')
            
            self._pool = pooling.MySQLConnectionPool(
                pool_name="drowsiness_pool",
                pool_size=5,
                pool_reset_session=True,
                host=_host,
                port=_port,
                database=_db_name,
                user=_user,
                password=_password,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                autocommit=False
            )
            print(f"✅ Database connection pool created successfully! (Host: {_host})")
        except Error as e:
            print(f"❌ Error creating connection pool: {e}")
            self._pool = None
        except Exception as ex:
             print(f"❌ config error: {ex}. Falling back to config.py defaults...")
             # Fallback logic could go here if needed
             self._pool = None
    
    def get_connection(self):
        """Get a connection from the pool"""
        if self._pool is None:
            self._initialize_pool()
        
        try:
            connection = self._pool.get_connection()
            return connection
        except Error as e:
            print(f"❌ Error getting connection from pool: {e}")
            return None
    
    def execute_query(self, query: str, params: Tuple = None, fetch: bool = False) -> Optional[List[Dict]]:
        """
        Execute a query with optional parameters.
        
        Args:
            query: SQL query string
            params: Tuple of parameters for the query
            fetch: If True, return fetched results
            
        Returns:
            List of dictionaries if fetch=True, None otherwise
        """
        connection = None
        cursor = None
        result = None
        
        try:
            connection = self.get_connection()
            if connection is None:
                return None
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
                
        except Error as e:
            print(f"❌ Database error: {e}")
            if connection:
                connection.rollback()
            result = None
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
                
        return result
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> bool:
        """
        Execute multiple queries with parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            True if successful, False otherwise
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            if connection is None:
                return False
            
            cursor = connection.cursor()
            cursor.executemany(query, params_list)
            connection.commit()
            return True
            
        except Error as e:
            print(f"❌ Database error: {e}")
            if connection:
                connection.rollback()
            return False
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def call_procedure(self, proc_name: str, params: Tuple = None) -> Optional[List[Dict]]:
        """
        Call a stored procedure.
        
        Args:
            proc_name: Name of the stored procedure
            params: Tuple of parameters
            
        Returns:
            List of dictionaries with results
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            if connection is None:
                return None
            
            cursor = connection.cursor(dictionary=True)
            cursor.callproc(proc_name, params or ())
            
            # Fetch results from stored procedure
            results = []
            for result in cursor.stored_results():
                results.extend(result.fetchall())
            
            connection.commit()
            return results
            
        except Error as e:
            print(f"❌ Error calling procedure {proc_name}: {e}")
            if connection:
                connection.rollback()
            return None
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            connection = self.get_connection()
            if connection is None:
                return False
            
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()
            
            print("✅ Database connection test successful!")
            return True
            
        except Error as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def close_pool(self) -> None:
        """Close all connections in the pool"""
        if self._pool:
            # Note: MySQLConnectionPool doesn't have a direct close method
            # Connections are closed when returned to pool
            print("✅ Connection pool cleanup completed")


# Create singleton instance
db = DatabaseConnection()


# Utility functions for easy access
def get_db() -> DatabaseConnection:
    """Get database instance"""
    return db


def execute_query(query: str, params: Tuple = None, fetch: bool = False):
    """Execute query using singleton instance"""
    return db.execute_query(query, params, fetch)


def execute_many(query: str, params_list: List[Tuple]) -> bool:
    """Execute multiple queries using singleton instance"""
    return db.execute_many(query, params_list)


# Test connection when module is run directly
if __name__ == "__main__":
    print("🔍 Testing database connection...")
    db.test_connection()
