import os
import pandas as pd
from sqlalchemy import create_engine, text
import pymysql
pymysql.install_as_MySQLdb()
from dotenv import load_dotenv
load_dotenv()

dbid=os.getenv("dbid")
dbpw=os.getenv("dbpw")
dbpw=os.getenv("dbpw")
port=os.getenv("port")

def _mysql_url(dbname=None):
    '''
    dbname이 있으면 db이름을 포함한 접속 주소 출력
    dbname이 없으면 port까지만 포함해서 출력
    '''
    if dbname:
        return f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}/{dbname}"
    return f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}"

def db_connect(dbname):
    engine_root=create_engine(_mysql_url())
    conn_root=engine_root.connect() #db에 접속해서 쿼리창 열어줌
    conn_root.execute(text(f"create database if not exists {dbname}")) # dbname 없으면 만들기
    print(f"{dbname} 데이터베이스 확인/생성 완료")
    conn_root.close()
    
    engine=create_engine(_mysql_url(dbname))
    conn=engine.connect() #db에 접속해서 쿼리창 리턴
    return conn

def to_db(dbname, table_name, df):
    conn=db_connect(dbname)
    df.to_sql(table_name, con=conn, index=False, if_exists="append")
    conn.close()
    print(f"{dbname}.{table_name} 데이터 저장 완료(append)")

def from_db(dbname, table_name):
    conn=db_connect(dbname)
    df=pd.read_sql(f"{dbname}.{table_name} 데이터 로드 완료")
    conn.close()
    return df