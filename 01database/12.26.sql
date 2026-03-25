use naver_db;
select * from naver_db.buy;
desc buy;

insert into buy(`mem_id`, `prod_name`, `group_name`, `price`, `amount`)
values ('MMU', '청바지', '패션', 50, 10);
select * from naver_db.buy;

update buy set amount=1 where num=1; -- 제대로 썼지만 권한 부여가 안 돼서 에러 뜸

