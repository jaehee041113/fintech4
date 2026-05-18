"""
dbio.py — 데이터베이스 입출력 모듈
====================================
MySQL에 연결하고, pandas DataFrame을 읽고 쓰는 함수를 제공합니다.
프로젝트의 모든 DB 접근은 이 파일을 통해 이루어집니다.

실행 순서 개요:
  1. 환경변수(.env)에서 DB 접속 정보를 읽음
  2. _mysql_url()로 SQLAlchemy 접속 문자열 생성
  3. db_connect()로 DB 연결 + 없으면 DB 자동 생성
  4. to_db() / from_db() 로 데이터 읽기·쓰기
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
import pymysql

# pymysql을 MySQLdb 인터페이스로 등록
# → SQLAlchemy가 내부적으로 MySQLdb를 찾을 때 pymysql로 대체
pymysql.install_as_MySQLdb()

from dotenv import load_dotenv

# .env 파일에서 환경변수를 읽어 os.environ에 등록
load_dotenv()

# 환경변수에서 DB 접속 정보 읽기
# Docker Compose에서 주입된 값 (docker-compose.yml의 environment 블록 참고)
dbid = os.getenv("dbid")       # DB 사용자 이름 (예: root)
dbpw = os.getenv("dbpw")       # DB 비밀번호
host = os.getenv("host")       # DB 호스트 (Docker 내부: "mysql" 컨테이너명)
port = os.getenv("port")       # DB 포트 (기본: 3306)


def _mysql_url(dbname=None):
    """
    SQLAlchemy가 MySQL에 연결할 때 사용하는 접속 문자열(URL)을 반환합니다.

    Args:
        dbname: 특정 데이터베이스 이름. None이면 서버 주소까지만 반환.

    Returns:
        "mysql+pymysql://유저:비번@호스트:포트[/DB이름]" 형태의 문자열

    예시:
        _mysql_url()           → "mysql+pymysql://root:pw@mysql:3306"
        _mysql_url("kb_cards") → "mysql+pymysql://root:pw@mysql:3306/kb_cards"
    """
    if dbname:
        return f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}/{dbname}"
    return f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}"


def db_connect(dbname):
    """
    MySQL에 연결하고, 지정한 데이터베이스가 없으면 자동으로 생성합니다.

    실행 순서:
      1. DB 이름 없이 서버에 먼저 접속 (root 권한)
      2. "CREATE DATABASE IF NOT EXISTS {dbname}" 실행 → 없으면 생성
      3. 이번엔 DB 이름을 포함한 URL로 재접속

    Args:
        dbname: 접속할 데이터베이스 이름 (예: "kb_cards")

    Returns:
        SQLAlchemy Connection 객체
    """
    # 1단계: DB 이름 없이 서버에 접속 (어떤 DB든 상관없이 서버 레벨 작업)
    engine_root = create_engine(_mysql_url())
    conn_root = engine_root.connect()

    # 2단계: 해당 DB가 없으면 생성
    conn_root.execute(text(f"create database if not exists {dbname}"))
    print(f"{dbname} 데이터베이스 확인/생성 완료")
    conn_root.close()

    # 3단계: 목표 DB에 직접 연결
    engine = create_engine(_mysql_url(dbname))
    conn = engine.connect()
    return conn


def to_db(dbname, table_name, df):
    """
    pandas DataFrame을 MySQL 테이블에 저장합니다 (추가 방식).

    - if_exists="append": 기존 테이블에 행을 추가합니다.
      테이블이 없으면 자동으로 생성합니다.

    Args:
        dbname     : 데이터베이스 이름
        table_name : 저장할 테이블 이름
        df         : 저장할 pandas DataFrame
    """
    conn = db_connect(dbname)
    # index=False: DataFrame의 인덱스(0,1,2...)는 저장하지 않음
    df.to_sql(table_name, con=conn, index=False, if_exists="append")
    conn.close()
    print(f"{dbname}.{table_name} 데이터 저장 완료(append)")


def from_db(dbname, table_name):
    """
    MySQL 테이블 전체를 pandas DataFrame으로 읽어옵니다.

    Args:
        dbname     : 데이터베이스 이름
        table_name : 읽을 테이블 이름

    Returns:
        테이블 전체 내용이 담긴 pandas DataFrame

    주의:
        pandas 2.x부터 pd.read_sql()에 테이블 이름을 직접 전달하면
        SQL 문법 오류가 발생합니다. 반드시 SELECT 쿼리 형태로 전달해야 합니다.
    """
    conn = db_connect(dbname)
    # 백틱(`)으로 테이블명을 감싸 MySQL 예약어와 충돌 방지
    df = pd.read_sql(f"SELECT * FROM `{table_name}`", con=conn)
    print(f"{dbname}.{table_name} 데이터 로드 완료")
    conn.close()
    return df
