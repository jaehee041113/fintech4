-- DDL을 이용해서 DB 만들고 테이블 만들기/삭제하기
-- Create database/schema 데이터베이스 이름;
create database sampledb2;
create database if not exists sampledb2;

-- 데이터베이스 목록 확인 : show databases;
show databases;

-- 데이터베이스 열기/사용 : use 데이터베이스명;
desc sampledb2;

-- 데이터베이스 지우기 : drop database 데이터베이스명;
drop database sampledb2;
drop database if exists sampledb2;

-- sampledb2 다시 만들기
create database if not exists sampledb2;

-- 테이블 만들기 : create table if not exists 테이블명 (컬럼이름1 데이터타입 제약 조건(not null, null, unique),
-- , 컬럼이름2 데이터타입 제약 조건(not null, null, unique))

use sampledb2; -- use 데이터베이스 써서 항상 활성화 꼭 해주기!!
-- businesscard 테이블 만들기
create table businesscard(
name varchar(255) not null, -- name이라는 컬럼 만들기
address varchar(255) not null,
telephone varchar(15) null);

-- 테이블 목록 조회 : show tables;
show tables;

-- 테이블의 속성, 제약조건 보기 : desc 테이블명;
desc businesscard;

-- 이미 만들어진 테이블의 속성 변경하기 : alter + modify(수정)/add(추가)/drop(제거)
-- name 컬럼에 not null에서 null로 변경
alter table businesscard modify name varchar(155) null; -- name 컬럼을 varchar(155) null로 바꾼다businesscard
desc businesscard; -- businesscard 테이블의 name 컬럼의 속성 바뀐 거 확인

-- ----여기까지 DDL
-- DDL : create(만들기), alter(수정), drop(테이블 자체 삭제), truncate(테이블 내용 비우기)

-- DML : 만들어진 테이블에 데이터 입력하기
-- DML : insert, update, delete

-- 데이터 입력하기 :  insert into 테이블명 (칼럼명1, 칼럼명2) values (자료1, 자료2)
insert into businesscard(`name`, `address`, `telephone`)
values ('bob','서초동1', '02-123'),
('sam','서초동2', '02-123'),
('kay','서초동3', '02-123');

-- select로 입력된 자료 조회
select * from businesscard;

-- 컬럼수=자료수, 컬럼명 순서대로 -> insert into 테이블명 까지만 쓰고 컬럼명 생략 가능

insert into businesscard(`address`) values ('서초동4');
select * from businesscard; -- -> 가능

insert into businesscard(`name`, `telephone`) values ('bob3', '02-789');
select * from businesscard; -- -> 불가능

insert into businesscard(`address`, `name`, `telephone`) values ('서초동4', 'bob3', '02-789');
select * from businesscard; -- 컬럼명 3개 순서 다르게 다 쓰고 순서 다르게 지정해주면 가능

-- no(넘버) 컬럼 추가 : int null
alter table businesscard add column no int null; -- 테이블에 no(넘버) 라는 컬럼이 추가 됨 (int 정수형으로 입력)
desc businesscard;

select * from businesscard;
insert into businesscard (`address`, `name`, `no`, `telephone`) values ('서초동4', 'bob3', 8, '02-789');
select * from businesscard;

-- Primary Key Autoincrement 적용하기 (자동 증가) -> 고유키 pk 자동으로 정해짐(여기에선 idx 인덱스 순서)

alter table businesscard add column idx int not null auto_increment primary key; 

-- idx 라는 컬럼 추가한 후 그 컬럼에 int, not null, auto_increment, primary key 속성 있음
-- -> auto_increment= idx는 자동으로 넣어짐
-- auto_increment 설정된 컬럼 있으면 -> 반드시 컬럼명 명시해주어야 함!!

desc businesscard;
select * from businesscard;

insert into businesscard (`address`, `name`, `no`, `telephone`) values ('서초동4', 'bob3', 8, '02-789');
select * from businesscard; -- -> 가능

insert into businesscard values ('서초동4', 'bob3', 8, '02-789');
select * from businesscard; -- -> 불가능! auto_increment 설정된 컬럼 있으면 -> 반드시 컬럼명 명시해주어야 함!!

-- ------------
-- update : 기존 테이블 자료 수정하기
-- update 테이블 명 set 컬럼1=값1, 컬럼2=값2 where 조건; (where 조건 반드시 주어야 함!!)
-- update + set + where 반드시 세 개 다 써주기!!

select * from businesscard;

update businesscard set name='key', address='서초동10' where idx=3; -- 위에서 idx는 자동으로 설정되게 만든 고유값(pk)
select * from businesscard;

-- delete : 데이터 삭제하기
delete from businesscard where idx=4; -- 꼭 where 써주기!!
select * from businesscard;

-- update, delete 쓸 때 -> 꼭 where 쓰기!!

-- ------------
-- 트랜잭션 : 여러 DML을 한 묶음으로 처리,
-- 중간에 문제가 생기면 rollback 써서 되돌리고/ 문제가 없으면 commit 써서 확정, 저장됨!
-- autocommit 확인/전환
select @@autocommit; -- 1=on, 0=off 확인
set autocommit=0; -- 오토커밋(자동저장)=0 , 오토커밋 끔
select @@autocommit;

start transaction;
select * from businesscard;
update businesscard set name='sam2', telephone='02-111' where idx=9;
select * from businesscard;
commit; -- 뒤에서 rollback 해도 안 돌아오도록 중간에 확정, 저장!
rollback; -- DML 명령에서만 rollback 가능 / DDL(create, drop, truncate)은 rollback불가능!!
select * from businesscard;

set autocommit=1; -- 오토커밋(자동저장)=1 , 오토커밋 켬
select @@autocommit;





