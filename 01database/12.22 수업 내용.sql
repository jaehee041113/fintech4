-- 실행 : 컨트롤+엔터
-- 데이터 베이스 목록 조회
show databases;

-- 데이터 베이스 열기
use sakila;

-- 테이블 목록 조회
show tables;

-- 테이블 컬럼명, 속성 조회 desc 테이블명
desc film;

-- (film)테이블에서 원하는 컬럼명 조회하기
select * from film;

-- film 테이블에서 tile과 release_year 컬럼만 보고 싶을 때
select title, release_year from film;

-- 컬럼 별명, as로 별칭 주기 (as 생략 가능)
select title as 영화제목, rental_rate 대여요금 from film;

-- 특정 조건을 만족하는 행만 출력하기 where절
-- select 컬럼명 from 테이블명 where 조건

-- 문자 조건 where 컬럼명 = "조건"
-- rating이 PG인 행만 조회하고 싶으면
select * from film where rating="PG";

-- 숫자 조건 where 컬럼명 = 숫자, > 숫자(초과), <숫자(미만), ≥(이상), ≤(이하)
-- rental_rate가 3 초과인 행 조회
select * from film where rental_rate>3;

-- 2가지 이상의 조건을 만족하는 행 조회 and, or
-- and : 조건 1과 조건2를 모두 만족해야 가져오는 경우
-- or : 조건 1 혹은 조건 2 중에서 하나만 충족해도 조회 가능

-- film 테이블에서 rental_rate가 2 이상이고, rating이 PG-13인 행 조회 ~이고(and)
select * from film where rental_rate≥2 and rating=”PG-13”;

-- film 테이블에서 rating이 ‘PG’ 혹은 ‘G’인 행 조회 ~혹은 ~또는 ~이거나(or)
select * from film where rating=”PG” or rating = “G”; -- 컬럼명이 같더라도 한 번 더 써주기

-- 부정조건 ~가 아닌 경우 <>, !=
-- film 테이블에서 rating이 ‘PG’가 아닌 행 조회
select * from film where rating <>’PG’;
select * from film where rating != ‘PG’;

-- 컬럼끼리 비교하기
-- replacement_cost가 rental_rate보다 큰 영화만 보기
select title, rental_rate, replacement_cost
from film
where replacement_cost> rental_rate;

-- 사칙연산으로 계산한 결과를 조건에 넣을 수 있음
-- replacement_cost - rental_rate 가 ≥ 10 행만 조회
select title, rental_rate, replacement_cost
from film where (replacement_cost - rental_rate)>=10; -- 컬럼과 컬럼을 계산한 값

-- 날짜 조건 주기 (날짜도 문자처럼 따옴표로 감싸서 조건 줌)
-- rental_rate가 2005-07-01보다 큰 행만 조회

select * from rental where rental_date >= "2005-07-01"; -- rental테이블에서 가져옴

-- between : 시작과 끝 값을 포함하는 범위로 조회할 때 (이상, 이하)
-- rental_rate≥2 and rental_rate ≤4 (2,3,4)
-- rental_rate가 2 이상 4 이하인 데이터 조회
select * from film where rental_rate >= 2 and rental_rate <= 4;
select * from film where rental_rate between 2 and 4;  -- between은 이상 이하일 때만 사용 가능

-- in : 여러 값 중에서 하나라도 같으면 포함되는 조건 or을 여러 번 쓴 것과 같음
-- rating이 ‘PG’,’G’, ‘PG-13’일 경우 조회
select * from film where rating=’PG’ or rating=’G’ or rating=’PG-13’;
select * from film where rating in (’PG’, ’G’, PG-13’);

-- like : 문자열에 특정 글자가 포함되어 있는지 확인하는 기능
select * from film;
-- description 컬럼에서 drama 라는 단어가 포함된 행을 조회
select * from film where description ="drama";
-- like "%단어%" : 앞뒤에 무엇이든 와도 되고 단어가 들어있는 것 모두
-- like "%단어" : 단어로 끝나는 모든 것
-- like "단어%" : 단어로 시작하는 모든 것alter
select * from film where description like "%drama%"; -- film 테이블 안에서 distription열에서 drama가 포함된 모든 것 가져오기
select * from film where description like "A Epic%"; 
select * from film where description like "%India%"; 

-- null 조회, 값이 없는 경우 찾기 : is null, where original_language_id=null (x) 안됨!! is null 로 써야 함!
select * from film where original_language_id is null;

-- null이 아닌 것만 조회 : is not null
select * from film where original_language_id is not null;

-- 순서 정렬하기(order by), 제한된 숫자의 행만 보기(limit)
-- 정렬 (order by asc(오름차순), order by desc(내림차순))
-- rental_rate 컬럼을 기준으로 내림차순 정렬
select * from film order by rental_rate desc;
select * from film order by rental_rate asc; -- order by 안 쓰면 기본으로는 오름차순(asc)

-- 두 개 이상의 기준으로 정렬하고 싶을 때
-- rating 을 기준으로 오름차순 정렬한 것을 rental_rate 기준으로 내림차순해서 보기
select * from film order by rating asc, rental_rate desc;

-- 전체 데이터에서 임의의 10행을 추출할 때 : rand(), limit 10
-- film 테이블에서 10개의 데이터를 무작위로 추출하세요
select * from film order by rand() limit 10;

-- film 데이터를 3개만 출력 : limit 3
select * from film limit 3;

-- 중복 값을 한 번만 출력하는 기능 : distinct (고유값만 1개씩 출력)
select distinct rating from film;

-- 집계 함수 : 개수, 평균, 최대, 최소값 구할 때 사용
-- count 개수
-- sum 합계
-- avg 평균
-- max 최대
-- min 최소
-- 영화 개수 구하기 count
select count(*) as 영화수 from film; -- 전체 행 개수 세기

-- rental_rate의 평균, 최고, 최소 요금 계산하기
select avg(rental_rate) as 평균요금, max(rental_rate) as 최고요금, min(rental_rate) as 최저요금
from film;

select * from payment;
-- payment 테이블의 amount 총합
select sum(amount) 총결제금액 from payment;
 
 -- group by, having
 
 -- group by : 같은 값끼리 묶는 기능, 같은 종류끼리 묶어서 통계를 보고 싶을 때
 -- 영화 평점이 같은 영화의 수를 세고 싶을 때
 select rating, count(*) as 영화수 from film group by rating;
 -- select *, count(*) as 영화수 from film group by rating; -> 불가능!!
 -- group by 할 때는 select에 all(*) 안 되고, group by로 묶은 것들로 select 해주기
 
 -- having : group by를 한 결과에서 원하는 조건 줄 때
 -- (where과의 차이 : having은 group by 먼저 한 후에 having 조건 걸어줌)
 select rating, count(*) as 영화수 from film group by rating having count(*)>=200;
 
 -- join :  서로 다른 테이블을 하나의 결과처럼 연결하는 방법. 공통된 컬럼을 기준으로 연결 -> 공간 낭비x, 합쳐서 조회할 때
 -- 공통된 컬럼은 보통 primary key, foreign key 으로 연결되어 있음
 -- inner join : 합치는 테이블 양쪽에 공통적으로 모두 있는 데이터만 합침 -> 교집합 
 -- left join : 합치는 테이블 중 왼쪽 테이블을 기준으로 왼쪽에 있는 것만 오른쪽에서 가져옴, 왼쪽 테이블 내용은 다 나옴+겹치는 오른쪽 테이블 내용
 -- right join : 합치는 테이블 중 오른쪽 테이블을 기준으로 오른쪽에 있는 것만 왼쪽에서 가져옴, 오른쪽 테이블 내용은 다 나옴+겹치는 왼쪽 테이블 내용
 -- outer join : 테이블 합집합 (mysql에는 없음)
 
select * from customer;
select * from rental;
-- customer 테이블과 rental 테이블을 합쳐서 이름, 성, 대여일 조회
select c.first_name, c.last_name, r.rental_date
from customer c
inner join rental r
on c.customer_id=r.customer_id;

select c.customer_id, c.first_name, c.last_name, r.rental_date -- 어디서 가져오는지 표시해주기
from customer c
inner join rental r
on c.customer_id=r.customer_id;

select c.customer_id, c.first_name, c.last_name, r.rental_date -- 어디서 가져오는지 표시해주기
from customer c
left join rental r
on c.customer_id=r.customer_id;

select c.customer_id, c.first_name, c.last_name, r.rental_date -- 어디서 가져오는지 표시해주기
from customer c
right join rental r
on c.customer_id=r.customer_id;

-- 테이블 합친 후 조건 주어 필터링 하기
select c.customer_id, c.first_name, c.last_name, r.rental_date -- 어디서 가져오는지 표시해주기
from customer c
right join rental r
on c.customer_id=r.customer_id -- 테이블 2개가 합쳐져서 여기까지 하나의 테이블이 됨
where r.rental_date >= "2005-07-01"; -- 합쳐져서 하나가 된 위의 테이블에 조건 주기 (테이블에 where 조건 주기)

-- join 후에 고객별 대여 횟수 구하기
select c.customer_id, count(r.rental_id) as 대여횟수
from customer c left join rental r on c.customer_id=r.customer_id -- join과 on조건은 세트
group by c.customer_id -- c.customer_id에 따른 집계함수 구함
having count(r.rental_id) >=10 -- r.rental_id 개수가 10개 이상인 경우만
order by 대여횟수 desc; -- 내림차순으로 정렬(많은 것부터)

-- 서브쿼리
-- 평균 대여 요금보다 비싼 영화만 보기
select avg(rental_rate) as 대여요금 from film; -- 2.98(평균 대여 요금)
select title, rental_rate from film where rental_rate>2.98;
-- 위의 두 개 합치기, 서브쿼리 먼저 실행됨
select title, rental_rate from film
where rental_rate > (select avg(rental_rate) as 대여요금 from film);

-- 서브쿼리 실행 결과가 여러 개일 때 IN, any, all을 사용해야 함
-- 영화 category가 'Comedy' 또는 'Action' 장르의 제목 보기
select * from film;
select * from category;
select * from film_category;
-- 방법 2개 : 조인, 서브쿼리
-- 서브쿼리로 풀기
select title from film where film_id
in (select film_id from film_category
where category_id in (select category_id from category
where name in ('Comedy', 'Action'))); -- in=or

select category_id from category where name in ('Comedy', 'Action');
select film_id from film_category where category_id in (1,5);
select title from film where film_id in (19,21,29);

-- 같음. 위치만 정확히 표시해둔 거임
select f.title from film f where f.film_id
in (select fc.film_id from film_category fc
where fc.category_id in (select c.category_id from category c
where c.name in ('Comedy', 'Action'))); -- in=or

select f.film_id, f.title, c.name from film f
inner join film_category fc on f.film_id=fc.film_id
inner join category c on fc.category_id=c.category_id
where c.name in ('Comedy', 'Action');


-- SQL 순서 : FROM-JOIN-WHERE-GROUP BY-HAVING-SELECT-ORDER BY-LIMIT



