-- DDL : DB 만들기 + 테이블 만들기/삭제하기

-- DB(데이터베이스) 만들기
create database sampledb3;

use sampledb3; -- use 데이터베이스 써서 항상 활성화 꼭 해주기!!

-- member 테이블 만들기
create table member(
mem_id char(8) not null,
mem_name varchar(10) not null,
mem_number tinyint not null,
addr char(2) not null,
phone1 char(3) null,
phone2 char(8) null,
height tinyint null,
debut_date date null);

-- buy 테이블 만들기
create table buy(
num int not null,
mem_id char(8) not null,
prod_name char(6) not null,
group_name char(4) null,
price int not null,
amount smallint not null);

alter table buy add column num int not null auto_increment primary key; 

-- 테이블 목록 조회
show tables;

-- member 테이블, buy 테이블의 속성, 제약조건 보기
desc member;
desc buy;

-- ---------------
-- DML : 만들어진 테이블에 데이터 입력하기

-- 데이터 입력하기 :  insert into 테이블명 (칼럼명1, 칼럼명2) values (자료1, 자료2)
insert into buy (`mem_id` ,`prod_name`,`group_name`,`price`,`amount`)
values ('BLK','지갑',NULL, 30,2),
('BLK','맥북프로','디지털', 1000,1),
('APN','아이폰','디지털',1000,1),
('MMU','아이폰', '디지털',200, 5),
('BLK','청바지','패션', 30,3),
('MMU','에어팟','디지털', 80,10),
('GRL','혼공SQL','서적', 15,5),
('APN','혼공SQL', '서적', 15,2),
('APN','청바지', '패션', 50,1),
('MMU','지갑',NULL, 30,1),
('APN','혼공SQL','서적', 15,1),
('MMU','지갑',NULL, 30,4);
