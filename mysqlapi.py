#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error
import argparse
import os
import sys
import getpass
import string
import random

def check_root_privileges():
    """检查是否具有root权限"""
    if os.geteuid() != 0:
        print("错误: 此脚本需要root权限才能执行")
        print("请使用 sudo 运行此脚本")
        sys.exit(1)

def create_db_user_with_privileges(args):
    """创建数据库、用户并分配权限"""
    try:
        # 如果未提供root密码，则交互式获取
        if not args.root_password:
            root_password = getpass.getpass("请输入MySQL root密码: ")
        else:
            root_password = args.root_password

        # 连接MySQL服务器
        connection = mysql.connector.connect(
            host=args.host,
            user='root',
            password=root_password,
            auth_plugin='mysql_native_password'
        )
        
        cursor = connection.cursor()
        
        try:
            # 开始事务
            connection.start_transaction()
            
            # 1. 创建数据库
            print(f"正在创建数据库 {args.db_name}...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {args.db_name}")
            
            # 2. 创建用户，根据不同的主机地址
            for host in args.user_host.split(','):
                print(f"正在创建用户 '{args.db_user}'@'{host}'...")
                cursor.execute(f"CREATE USER IF NOT EXISTS '{args.db_user}'@'{host}' "
                             f"IDENTIFIED BY '{args.db_password}'")
                
                # 3. 授予权限
                print(f"正在为用户 '{args.db_user}'@'{host}' 授予权限...")
                if args.minimal_privileges:
                    # 只授予基本权限
                    cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {args.db_name}.* "
                                 f"TO '{args.db_user}'@'{host}'")
                else:
                    # 授予所有权限
                    cursor.execute(f"GRANT ALL PRIVILEGES ON {args.db_name}.* "
                                 f"TO '{args.db_user}'@'{host}'")
            
            # 4. 刷新权限
            cursor.execute("FLUSH PRIVILEGES")
            
            # 提交事务
            connection.commit()
            print("成功完成所有操作！")
            
        except Error as e:
            # 如果发生错误，回滚事务
            print(f"发生错误，执行回滚: {e}")
            connection.rollback()
            raise
        
    except Error as e:
        print(f"连接数据库时发生错误: {e}")
        sys.exit(1)
        
    finally:
        # 关闭游标和连接
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("数据库连接已关闭")

def generate_secure_password(length=8):
    """生成安全的随机密码"""
    # 定义字符集
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    # 使用较安全的特殊字符集
    special = "!@#$%^&*()_+-=[]{}|"
    
    # 确保密码包含所有类型的字符
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # 填充剩余长度
    remaining_length = length - len(password)
    all_chars = lowercase + uppercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(remaining_length))
    
    # 打乱密码字符顺序
    random.shuffle(password)
    return ''.join(password)

def main():
    parser = argparse.ArgumentParser(description='MySQL数据库和用户管理工具')
    parser.add_argument('--host', default='localhost',
                      help='MySQL服务器地址 (默认: localhost)')
    parser.add_argument('--root-password',
                      help='MySQL root密码 (如果不提供将交互式询问)')
    parser.add_argument('--db-name', required=True,
                      help='要创建的数据库名')
    parser.add_argument('--db-user', required=True,
                      help='要创建的数据库用户名')
    parser.add_argument('--password-length', type=int, default=8,
                      help='生成密码的长度 (默认: 8)')
    parser.add_argument('--user-host', default='localhost',
                      help='允许用户连接的主机地址，多个地址用逗号分隔 (默认: localhost)')
    parser.add_argument('--minimal-privileges', action='store_true',
                      help='只授予基本权限（SELECT,INSERT,UPDATE,DELETE）')

    args = parser.parse_args()
    
    # 生成随机密码
    generated_password = generate_secure_password(args.password_length)
    args.db_password = generated_password
    
    # 检查root权限
    check_root_privileges()
    
    # 执行主要操作
    create_db_user_with_privileges(args)
    
    # 输出生成的密码信息
    print("\n=== 数据库访问信息 ===")
    print(f"数据库名: {args.db_name}")
    print(f"用户名: {args.db_user}")
    print(f"密码: {generated_password}")
    print(f"主机: {args.user_host}")
    print("=====================")

if __name__ == "__main__":
    main()