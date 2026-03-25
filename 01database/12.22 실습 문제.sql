use sakila;

select * from actor;
select first_name, last_name from actor;
select title from film;
select first_name, last_name, email from customer;
select * from payment;

select * from film where rating='PG';
select * from film where rental_rate>3;
select * from film where rental_rate>=2 and rating='PG-13';
select * from film where rating='PG' or rating='G';
select * from film where rental_rate between 2 and 4;
select * from film where rating in ('PG', 'G', 'PG-13');
select * from customer where email is null; -- =null 아님!! is null 이라고 써야 함!!

select title from film where title like "%LOVE%";
select title from film where title like "A%";
select title from film where title like "%MAN";
select * from costomer where last_name like "% %";
select * from actor where first_name like "%JO%";

select title, rental_rate from film order by rental_rate desc;
select title, rating, rental_rate from film order by rating asc, rental_rate desc;
select title, rental_rate from film order by rental_rate desc limit 5;
select * from actor limit 10;
select * from customer order by first_name asc limit 20;
select * from film order by rental_rate asc limit 3;

select distinct rating from film;
select count(*) 영화수 from film;
select avg(rental_rate) from film;
select max(rental_rate) 최고요금 from film;
select min(rental_rate) 최저요금 from film;
select sum(amount) 총결제금액 from payment;
select avg(amount) 평균결제금액 from payment;

select rating, count(*) 영화개수 from film group by rating;
select rating, avg(rental_rate) 평균대여요금 from film group by rating;
select rating, count(*) 영화개수 from film group by rating having count(*)>=200 ;
select staff_id, sum(amount) 총결제금액 from payment group by staff_id;
select staff_id, sum(amount) 총결제금액 from payment group by staff_id having sum(amount)>5000;
select customer_id, count(*) 결제횟수 from payment group by customer_id;
select customer_id, count(*) 결제횟수 from payment group by customer_id having count(*)>=30;
select customer_id, sum(amount) 총결제금액 from payment group by customer_id;

-- 고객 이름과 대여 날짜(rental_date)를 함께 조회
SELECT c.first_name, c.last_name, r.rental_date
FROM customer c JOIN rental r
ON c.customer_id = r.customer_id;

-- 고객별 대여 횟수 조회
SELECT c.customer_id, count(r.rental_id) 대여횟수
FROM customer c left JOIN rental r
ON c.customer_id = r.customer_id
GROUP BY c.customer_id;

-- 대여 횟수가 20회 이상인 고객만 조회
SELECT c.customer_id, count(r.rental_id) 대여횟수
FROM customer c left JOIN rental r
ON c.customer_id = r.customer_id
GROUP BY c.customer_id
having count(r.rental_id)>=20;

-- 고객 이름과 총 결제 금액을 함께 조회
SELECT c.first_name, c.last_name, SUM(p.amount) AS 총결제금액
FROM customer c JOIN payment p
ON c.customer_id = p.customer_id
GROUP BY c.customer_id;

-- 총 결제 금액이 100 이상인 고객만 조회
SELECT c.customer_id, SUM(p.amount) AS 총결제금액
FROM customer c JOIN payment p
ON c.customer_id = p.customer_id
GROUP BY c.customer_id
having SUM(p.amount)>=100;

-- 가장 많은 결제 금액을 낸 고객 5명을 조회
SELECT c.customer_id, SUM(p.amount) AS 총결제금액
FROM customer c JOIN payment p
ON c.customer_id = p.customer_id
GROUP BY c.customer_id
ORDER BY SUM(p.amount) DESC LIMIT 5;

-- 대여 기록이 없는 고객도 모두 포함하여 조회
SELECT c.customer_id, r.rental_id
FROM customer c  left JOIN rental r
ON c.customer_id = r.customer_id;

-- 대여 기록이 없는 고객만 조회
-- join과 on은 세트!!
SELECT c.customer_id
FROM customer c  left JOIN rental r ON c.customer_id = r.customer_id
where r.rental_id is null;

-- 결제 금액이 1 미만이거나 NULL인 데이터를 조회
SELECT *
FROM payment p
where p.amount <1 or p.amount is null;

-- 고객별 대여 횟수와 총 결제 금액을 함께 조회
SELECT c.customer_id, COUNT(r.rental_id) AS 대여횟수, SUM(p.amount) AS 총결제금액
FROM customer c -- 고객테이블
LEFT JOIN rental r ON c.customer_id = r.customer_id -- 고객테이블과 대여테이블 조인
LEFT JOIN payment p ON r.rental_id = p.rental_id -- 대여테이블과 결제테이블 조인
GROUP BY c.customer_id;

-- 대여 횟수가 10회 이상이고 총 결제 금액이 50 이상인 고객을 조회
SELECT c.customer_id, COUNT(r.rental_id) AS 대여횟수, SUM(p.amount) AS 총결제금액
FROM customer c
LEFT JOIN rental r ON c.customer_id = r.customer_id -- 고객테이블과 대여테이블 조인
LEFT JOIN payment p ON r.rental_id = p.rental_id -- 대여테이블과 결제테이블 조인
GROUP BY c.customer_id
HAVING COUNT(r.rental_id) >= 10 AND SUM(p.amount) >= 50;

-- 대여 횟수 내림차순, 총 결제 금액 내림차순으로 정렬하여 상위 10명을 조회
SELECT c.customer_id, COUNT(r.rental_id) AS 대여횟수, SUM(p.amount) AS 총결제금액
FROM customer c
LEFT JOIN rental r ON c.customer_id = r.customer_id
LEFT JOIN payment p ON r.rental_id = p.rental_id
GROUP BY c.customer_id
ORDER BY COUNT(r.rental_id) DESC, SUM(p.amount) DESC LIMIT 10;



