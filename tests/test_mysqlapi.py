import pytest
from unittest.mock import Mock, patch
import mysql.connector
from mysql.connector import Error
import mysqlapi
import os

@pytest.fixture
def mock_args():
    """创建模拟的命令行参数"""
    class Args:
        host = 'localhost'
        root_password = 'root_pass'
        db_name = 'test_db'
        db_user = 'test_user'
        db_password = 'test_pass'
        user_host = 'localhost'
        minimal_privileges = False
    return Args()

def test_generate_secure_password():
    """测试密码生成功能"""
    password = mysqlapi.generate_secure_password(length=12)
    assert len(password) == 12
    # 验证密码包含所有必需的字符类型
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in "!@#$%^&*()_+-=[]{}|" for c in password)

@patch('os.geteuid')
def test_check_root_privileges_success(mock_geteuid):
    """测试root权限检查成功的情况"""
    mock_geteuid.return_value = 0
    mysqlapi.check_root_privileges()
    mock_geteuid.assert_called_once()

@patch('os.geteuid')
def test_check_root_privileges_failure(mock_geteuid):
    """测试root权限检查失败的情况"""
    mock_geteuid.return_value = 1000
    with pytest.raises(SystemExit):
        mysqlapi.check_root_privileges()

@patch('mysql.connector.connect')
def test_create_db_user_with_privileges_success(mock_connect, mock_args):
    """测试成功创建数据库和用户的情况"""
    # 设置mock对象
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor
    
    # 执行测试
    mysqlapi.create_db_user_with_privileges(mock_args)
    
    # 验证调用
    mock_connect.assert_called_once()
    mock_cursor.execute.assert_any_call(f"CREATE DATABASE IF NOT EXISTS {mock_args.db_name}")
    mock_cursor.execute.assert_any_call("FLUSH PRIVILEGES")
    mock_connection.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_connection.close.assert_called_once()

@patch('mysql.connector.connect')
def test_create_db_user_with_privileges_minimal(mock_connect, mock_args):
    """测试使用最小权限创建用户的情况"""
    mock_args.minimal_privileges = True
    
    # 设置mock对象
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor
    
    # 执行测试
    mysqlapi.create_db_user_with_privileges(mock_args)
    
    # 验证是否使用了最小权限
    expected_grant = f"GRANT SELECT, INSERT, UPDATE, DELETE ON {mock_args.db_name}.* TO '{mock_args.db_user}'@'localhost'"
    mock_cursor.execute.assert_any_call(expected_grant)

@patch('mysql.connector.connect')
def test_create_db_user_with_privileges_connection_error(mock_connect, mock_args):
    """测试数据库连接错误的情况"""
    mock_connect.side_effect = Error("连接错误")
    
    with pytest.raises(SystemExit):
        mysqlapi.create_db_user_with_privileges(mock_args)

@patch('mysql.connector.connect')
def test_create_db_user_with_privileges_execution_error(mock_connect, mock_args):
    """测试执行SQL语句错误的情况"""
    # 设置mock对象
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor
    
    # 设置执行错误
    mock_cursor.execute.side_effect = Error("执行错误")
    
    with pytest.raises(Error):
        mysqlapi.create_db_user_with_privileges(mock_args)
    
    # 验证是否执行了回滚
    mock_connection.rollback.assert_called_once() 

    