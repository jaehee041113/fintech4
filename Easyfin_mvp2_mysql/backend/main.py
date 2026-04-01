import os
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    ForeignKey,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

# ============================
# 1. DB 설정 (MySQL + SQLAlchemy)
# ============================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://easyfin:easyfin@db:3306/easyfin_db",
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================
# 2. SQLAlchemy ORM 모델
# ============================

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    nickname = Column(String(255), nullable=False)

    accounts = relationship("AccountORM", back_populates="user")
    profile = relationship("ProfileORM", back_populates="user", uselist=False)


class AccountORM(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    balance = Column(Integer, nullable=False)
    institution = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("UserORM", back_populates="accounts")


class MarketItemORM(Base):
    __tablename__ = "market_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    risk_level = Column(String(50), nullable=False)
    expected_yield = Column(Float, nullable=True)


class LiveStreamORM(Base):
    __tablename__ = "live_streams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)  # ongoing, upcoming, replay
    host = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False)


class CommunityPostORM(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    author = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProfileORM(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nickname = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    following_experts = Column(Text, nullable=False)  # 콤마 구분 문자열
    linked_institutions = Column(Text, nullable=False)

    user = relationship("UserORM", back_populates="profile")


# ============================
# 3. Pydantic 모델 (API 스키마)
# ============================

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    nickname: str


class AssetSummary(BaseModel):
    total_amount: int
    currency: str
    breakdown: Dict[str, int]


class Account(BaseModel):
    id: int
    type: str
    name: str
    balance: int
    institution: str

    class Config:
        orm_mode = True


class MarketItem(BaseModel):
    id: int
    category: str
    name: str
    code: str
    description: str
    risk_level: str
    expected_yield: Optional[float] = None

    class Config:
        orm_mode = True


class LiveStream(BaseModel):
    id: int
    title: str
    status: str
    host: str
    start_time: datetime

    class Config:
        orm_mode = True


class CommunityPost(BaseModel):
    id: int
    author: str
    category: str
    title: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True


class NewPost(BaseModel):
    author: str
    title: str
    content: str
    category: Optional[str] = "자유"


class Profile(BaseModel):
    user_id: int
    nickname: str
    email: str
    following_experts: List[str]
    linked_institutions: List[str]

    class Config:
        orm_mode = True


# ============================
# 4. FastAPI 앱 & CORS
# ============================

app = FastAPI(
    title="EasyFin V2.0 API (MySQL)",
    description="자산 통합 & 라이브 금융 콘텐츠 서비스 MVP용 API (MySQL 연동)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP 단계에서는 전체 허용
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================
# 5. DB 초기화 & 더미 데이터 시드
# ============================

def seed_data(db: Session) -> None:
    """테이블이 비어 있을 때만 더미데이터 삽입"""
    if db.query(UserORM).count() > 0:
        return  # 이미 시드되어 있음

    # 1) 사용자
    user = UserORM(
        email="demo@easyfin.app",
        password="1234",  # MVP: 평문 (실서비스에서는 해시 필요)
        nickname="지현",
    )
    db.add(user)
    db.flush()  # user.id 채우기

    # 2) 계좌들
    accounts = [
        AccountORM(
            type="예금",
            name="급여통장",
            balance=12000000,
            institution="KB국민은행",
            user_id=user.id,
        ),
        AccountORM(
            type="주식",
            name="국내주식",
            balance=18000000,
            institution="토스증권",
            user_id=user.id,
        ),
        AccountORM(
            type="ETF",
            name="S&P500 ETF",
            balance=15000000,
            institution="미래에셋증권",
            user_id=user.id,
        ),
        AccountORM(
            type="채권",
            name="국채 3년",
            balance=10000000,
            institution="NH투자증권",
            user_id=user.id,
        ),
        AccountORM(
            type="현금",
            name="현금",
            balance=5000000,
            institution="지갑",
            user_id=user.id,
        ),
    ]
    db.add_all(accounts)

    # 3) 마켓 상품
    market_items = [
        MarketItemORM(
            category="공모주",
            name="에임드바이오",
            code="0009K",
            description="ADC 기반 항암제 바이오 기업",
            risk_level="높음",
            expected_yield=12.5,
        ),
        MarketItemORM(
            category="ETF",
            name="KODEX 미국S&P500",
            code="069500",
            description="미국 S&P500 지수를 추종하는 ETF",
            risk_level="중간",
            expected_yield=6.2,
        ),
        MarketItemORM(
            category="채권",
            name="국채 3년",
            code="KR3Y",
            description="안정적인 국내 만기 3년 국채",
            risk_level="낮음",
            expected_yield=3.1,
        ),
        MarketItemORM(
            category="리츠",
            name="○○ 리츠",
            code="REIT01",
            description="오피스/상가 중심 리츠 상품",
            risk_level="중간",
            expected_yield=5.0,
        ),
    ]
    db.add_all(market_items)

    # 4) 라이브
    lives = [
        LiveStreamORM(
            title="오늘의 공모주 브리핑",
            status="ongoing",
            host="김공모",
            start_time=datetime(2025, 12, 8, 19, 0),
        ),
        LiveStreamORM(
            title="초보자를 위한 ETF 입문",
            status="upcoming",
            host="이ETF",
            start_time=datetime(2025, 12, 9, 20, 0),
        ),
        LiveStreamORM(
            title="미국 S&P500 전략 다시보기",
            status="replay",
            host="박인덱스",
            start_time=datetime(2025, 12, 1, 20, 0),
        ),
    ]
    db.add_all(lives)

    # 5) 커뮤니티 글
    posts = [
        CommunityPostORM(
            author="지현",
            category="공모주",
            title="이번 주 공모주 어떻게 보세요?",
            content="에임드바이오 청약 고민 중입니다. 의견 부탁드려요.",
            created_at=datetime(2025, 12, 8, 10, 0),
        ),
        CommunityPostORM(
            author="인덱스러버",
            category="ETF",
            title="S&P500 장기투자 전략 공유",
            content="3년 이상 들고 가면서 분할매수 하는 전략입니다.",
            created_at=datetime(2025, 12, 7, 22, 30),
        ),
    ]
    db.add_all(posts)

    # 6) 프로필
    profile = ProfileORM(
        user_id=user.id,
        nickname=user.nickname,
        email=user.email,
        following_experts="이ETF,박인덱스",
        linked_institutions="KB국민은행,토스증권,미래에셋증권",
    )
    db.add(profile)

    db.commit()


@app.on_event("startup")
def on_startup():
    # 1) 테이블 생성 (이미 있거나 concurrent DDL이면 무시)
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        msg = str(getattr(e, "orig", e))
        if "already exists" in msg or "concurrent DDL" in msg:
            # gunicorn 멀티워커가 동시에 create_all() 할 때 나오는 정상(?) 상황
            print(f"[DB init] ignore DDL error: {msg}")
        else:
            # 다른 OperationalError 는 진짜 문제일 수 있으니 그대로 올림
            raise

    # 2) 시드 데이터 주입
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


# ============================
# 6. 엔드포인트 구현
# ============================

@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(UserORM)
        .filter(
            UserORM.email == payload.email,
            UserORM.password == payload.password,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return LoginResponse(user_id=user.id, nickname=user.nickname)


@app.get("/assets/summary", response_model=AssetSummary)
def get_asset_summary(db: Session = Depends(get_db), user_id: int = 1):
    """단일 데모 유저 기준 자산 요약"""
    accounts = db.query(AccountORM).filter(AccountORM.user_id == user_id).all()
    if not accounts:
        return AssetSummary(total_amount=0, currency="KRW", breakdown={})

    breakdown: Dict[str, int] = {}
    total = 0
    for acc in accounts:
        breakdown.setdefault(acc.type, 0)
        breakdown[acc.type] += acc.balance
        total += acc.balance

    return AssetSummary(total_amount=total, currency="KRW", breakdown=breakdown)


@app.get("/assets/accounts", response_model=List[Account])
def get_accounts(db: Session = Depends(get_db), user_id: int = 1):
    return db.query(AccountORM).filter(AccountORM.user_id == user_id).all()


@app.get("/market/items", response_model=List[MarketItem])
def get_market_items(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(MarketItemORM)
    if category:
        q = q.filter(MarketItemORM.category == category)
    return q.all()


@app.get("/live/streams", response_model=List[LiveStream])
def get_live_streams(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(LiveStreamORM)
    if status:
        q = q.filter(LiveStreamORM.status == status)
    return q.order_by(LiveStreamORM.start_time.desc()).all()


@app.get("/community/posts", response_model=List[CommunityPost])
def list_posts(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CommunityPostORM)
    if category:
        q = q.filter(CommunityPostORM.category == category)
    return q.order_by(CommunityPostORM.created_at.desc()).all()


@app.post("/community/posts", response_model=CommunityPost)
def create_post(new_post: NewPost, db: Session = Depends(get_db)):
    category = new_post.category or "자유"
    post = CommunityPostORM(
        author=new_post.author,
        category=category,
        title=new_post.title,
        content=new_post.content,
        created_at=datetime.utcnow(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/me/profile", response_model=Profile)
def get_profile(db: Session = Depends(get_db), user_id: int = 1):
    profile = db.query(ProfileORM).filter(ProfileORM.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="프로필이 존재하지 않습니다.")

    following = [s.strip() for s in profile.following_experts.split(",") if s.strip()]
    institutions = [s.strip() for s in profile.linked_institutions.split(",") if s.strip()]

    return Profile(
        user_id=profile.user_id,
        nickname=profile.nickname,
        email=profile.email,
        following_experts=following,
        linked_institutions=institutions,
    )
