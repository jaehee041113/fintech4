/**
 * lib/api.ts — API 타입 정의 및 통신 함수
 * =========================================
 * 프론트엔드에서 백엔드와 주고받는 데이터의 타입(TypeScript interface)을 정의하고,
 * 추천 API를 호출하는 함수를 제공합니다.
 *
 * 호출 흐름:
 *   사용자 입력 → fetchRecommendations() → /api/recommend (Next.js API Route)
 *              → http://backend:8000/api/recommend (FastAPI 백엔드)
 *
 * API_URL이 빈 문자열("")인 이유:
 *   브라우저에서 외부 Docker 네트워크(backend:8000)에 직접 접근할 수 없습니다.
 *   대신 같은 오리진(same-origin)의 Next.js API Route(/api/recommend)로 요청하면,
 *   Next.js 서버가 서버 사이드에서 백엔드로 중계(프록시)합니다.
 *   → app/api/recommend/route.ts 참고
 */

// 브라우저 → 같은 오리진의 Next.js API Route로 요청 (프록시 방식)
const API_URL = "";

// ── 카테고리 목록 ────────────────────────────────────────
// as const: 이 배열의 값들을 변경 불가한 리터럴 타입으로 고정
// 백엔드의 BENEFIT_CATEGORIES와 동일하게 유지해야 합니다.
export const CATEGORIES = [
  "전가맹점",
  "음식/카페",
  "주유/교통",
  "쇼핑/간편결제",
  "항공/해외",
  "교육/건강",
  "자동납부",
  "통신",
  "Biz/공공",
] as const;

// CATEGORIES 배열의 각 요소를 타입으로 추출
// 예: Category = "전가맹점" | "음식/카페" | "주유/교통" | ...
export type Category = (typeof CATEGORIES)[number];

// ── 타입 정의 ────────────────────────────────────────────

/** 카드 혜택 1개의 구조 (card_benefits 테이블의 1행) */
export interface Benefit {
  category:    string;                    // 혜택 카테고리 (예: "음식/카페")
  benefit_type: "discount" | "reward";   // 할인 | 적립
  rate_min:    number;                    // 혜택률 최솟값 (%)
  rate_max:    number;                    // 혜택률 최댓값 (%)
  max_amount_1: number | null;           // 1구간 월 최대 혜택 금액
  max_amount_2: number | null;           // 2구간 월 최대 혜택 금액
  max_amount_3: number | null;           // 3구간 월 최대 혜택 금액
  description: string;                   // 혜택 설명
}

/** 카드 기본 정보 구조 (cards 테이블의 1행 + 추천 계산 결과) */
export interface CardInfo {
  cooperation_code:   string;           // 카드 고유 코드 (예: "09060")
  name:               string;           // 카드명
  card_type:          "credit" | "debit"; // 신용 | 체크
  description:        string;           // 카드 설명
  image_url:          string;           // 카드 이미지 URL
  detail_url:         string;           // KB카드 상세 페이지 URL
  annual_fee_domestic: number | null;  // 국내 연회비 (원)
  min_spending_1:     number | null;   // 전월실적 1구간 기준금액
  min_spending_2:     number | null;   // 전월실적 2구간 기준금액
  min_spending_3:     number | null;   // 전월실적 3구간 기준금액
  applicable_tier:    number;          // 사용자가 해당하는 전월실적 구간 (0~3)
}

/** 카테고리별 혜택 세부 내역 (CardResult 하단에 표시) */
export interface BenefitBreakdown {
  category:          string;  // 카테고리 (예: "음식/카페")
  spending:          number;  // 해당 카테고리 지출액
  rate_min:          number;  // 적용된 혜택률 최솟값
  rate_max:          number;  // 적용된 혜택률 최댓값
  benefit_type:      string;  // 할인 | 적립
  spending_tier:     number;  // 적용된 전월실적 구간
  estimated_benefit: number;  // 예상 혜택 금액 (원)
}

/** 카드 추천 결과 1개의 구조 */
export interface RecommendResult {
  rank:               number;            // 순위
  card:               CardInfo;          // 카드 기본 정보
  monthly_benefit:    number;            // 월 예상 혜택 합계 (원)
  annual_benefit:     number;            // 연 예상 혜택 합계 (원)
  net_annual_benefit: number;            // 연 순 혜택 = 연혜택 - 연회비 (원)
  benefit_breakdown:  BenefitBreakdown[]; // 카테고리별 세부 내역
}

/** 추천 API 전체 응답 구조 */
export interface RecommendResponse {
  input_spending:         Record<string, number>; // 사용자가 입력한 지출 금액
  total_monthly_spending: number;                 // 총 월 지출 합계
  recommendations:        RecommendResult[];      // 추천 카드 목록 (순위 순)
}

// ── API 호출 함수 ─────────────────────────────────────────

/**
 * 카드 추천 API를 호출합니다.
 *
 * @param spending  - 카테고리별 월 지출 금액 {"음식/카페": 300000, ...}
 * @param card_type - "credit" | "debit" | null (null이면 전체)
 * @param top_n     - 추천받을 카드 수
 * @returns 추천 결과 (RecommendResponse)
 * @throws 요청 실패 시 Error
 *
 * 호출 경로:
 *   브라우저 → /api/recommend (Next.js 서버) → http://backend:8000/api/recommend (FastAPI)
 */
export async function fetchRecommendations(
  spending:  Record<string, number>,
  card_type: string | null,
  top_n:     number
): Promise<RecommendResponse> {
  const res = await fetch(`${API_URL}/api/recommend`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    // JSON.stringify: JavaScript 객체를 JSON 문자열로 변환
    body: JSON.stringify({ spending, card_type, top_n }),
  });

  if (!res.ok) {
    // 응답이 실패(4xx, 5xx)인 경우 에러 발생
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "추천 요청 실패");
  }

  return res.json(); // JSON 응답을 RecommendResponse 타입으로 반환
}
