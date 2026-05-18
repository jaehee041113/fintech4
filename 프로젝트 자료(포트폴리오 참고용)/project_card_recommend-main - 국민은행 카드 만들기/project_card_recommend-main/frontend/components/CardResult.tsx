/**
 * components/CardResult.tsx — 추천 카드 결과 카드 컴포넌트
 * ==========================================================
 * 추천 카드 1개의 정보를 카드(Card) 형태로 표시합니다.
 *
 * 화면 구성:
 *   ┌─────────────────────────────────────────────────────┐
 *   │ [순위] [카드이미지] [카드유형 뱃지] [전월실적 구간]    │
 *   │                   카드명                             │
 *   │                   카드 설명                          │
 *   │                   연회비 | 전월실적 조건              │
 *   │                                       [월 예상 혜택] │
 *   │                                       [연 순 혜택]   │
 *   ├─────────────────────────────────────────────────────┤
 *   │ 카테고리별 혜택 세부 내역 (chip 형태)                  │
 *   ├─────────────────────────────────────────────────────┤
 *   │                            KB국민카드 상세 보기 →    │
 *   └─────────────────────────────────────────────────────┘
 *
 * Material Design 3 Outlined Card 스타일을 사용합니다.
 */

import Image from "next/image";
import { RecommendResult } from "@/lib/api";

// Props 타입: 추천 결과 1개를 받습니다
interface Props {
  result: RecommendResult;
}

/**
 * 숫자를 한국 원화 형식으로 표시합니다.
 * null/undefined인 경우 "-"를 반환합니다.
 * 예: 15000 → "15,000원", null → "-"
 */
function formatKRW(n: number | null | undefined) {
  if (n == null) return "-";
  return n.toLocaleString() + "원";
}

/**
 * 혜택률을 표시 문자열로 변환합니다.
 * - 단일 값: "5%" (min === max일 때)
 * - 범위 값: "5~30%" (min !== max일 때)
 */
function rateLabel(min: number, max: number) {
  return min === max ? `${min}%` : `${min}~${max}%`;
}

export default function CardResult({ result }: Props) {
  // props에서 필요한 값을 구조 분해 할당
  const { card, monthly_benefit, net_annual_benefit, benefit_breakdown } = result;

  // 전월실적 구간 표시 텍스트
  // applicable_tier: 0=실적미달, 1~3=해당 구간
  const tierLabel =
    card.applicable_tier === 0
      ? "실적 미달"
      : `${card.applicable_tier}구간 적용`;

  // 전월실적 조건 표시 텍스트
  // min_spending_1/2/3 중 값이 있는 것만 표시
  // 예: "30만원 / 50만원 / 100만원" 또는 "조건 없음"
  const minSpending = card.min_spending_1
    ? [card.min_spending_1, card.min_spending_2, card.min_spending_3]
        .filter(Boolean)              // null/undefined 제거
        .map((v) => formatKRW(v))    // 숫자 → "원" 형식으로 변환
        .join(" / ")                  // "/"로 구분
    : "조건 없음";

  return (
    // M3 Outlined Card: 테두리 있음, 그림자 없음
    <div className="rounded-xl border border-black/[0.16] bg-white overflow-hidden">

      {/* ── 상단: 카드 기본 정보 ──────────────────────────── */}
      <div className="flex items-start gap-4 p-5">

        {/* 순위 뱃지 (1, 2, 3 ...) */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#ffcc00] text-sm font-bold text-zinc-900">
          {result.rank}
        </div>

        {/* 카드 이미지 */}
        {card.image_url ? (
          // fill: 부모 div 크기에 맞게 이미지를 채움
          // unoptimized: Next.js 이미지 최적화 API를 거치지 않고 원본 URL 직접 사용
          <div className="relative h-16 w-24 shrink-0">
            <Image
              src={card.image_url}
              alt={card.name}
              fill
              className="rounded-lg object-contain"
              unoptimized
            />
          </div>
        ) : (
          // 이미지 URL이 없는 경우 플레이스홀더 표시
          <div className="flex h-16 w-24 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-xs text-zinc-400">
            이미지 없음
          </div>
        )}

        {/* 카드명 / 연회비 / 전월실적 정보 */}
        <div className="flex-1 min-w-0">
          {/* 카드 유형 뱃지 + 전월실적 구간 */}
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                card.card_type === "credit"
                  ? "bg-[#fff9cc] text-[#a38800]"  // 신용카드: 노란 계열
                  : "bg-green-50 text-green-700"    // 체크카드: 초록 계열
              }`}
            >
              {card.card_type === "credit" ? "신용" : "체크"}
            </span>
            <span className="text-xs text-zinc-400">{tierLabel}</span>
          </div>

          {/* 카드명 */}
          <h3 className="mt-1 font-semibold text-zinc-900 leading-tight">
            {card.name}
          </h3>

          {/* 카드 설명 (너무 길면 ... 처리) */}
          <p className="mt-0.5 text-xs text-zinc-500 truncate">
            {card.description}
          </p>

          {/* 연회비 + 전월실적 조건 */}
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-zinc-500">
            <span>연회비 {formatKRW(card.annual_fee_domestic)}</span>
            <span>전월실적 {minSpending}</span>
          </div>
        </div>

        {/* 혜택 요약 (PC에서만 표시, 모바일은 하단에 따로 표시) */}
        {/* hidden: 기본 숨김, sm:block: 소형 이상에서 표시 */}
        <div className="hidden shrink-0 text-right sm:block">
          <p className="text-xs text-zinc-400">월 예상 혜택</p>
          <p className="text-xl font-bold text-[#ffcc00]">
            {monthly_benefit.toLocaleString()}원
          </p>
          <p className="text-xs text-zinc-400 mt-1">연 순 혜택</p>
          {/* 연 순 혜택이 양수면 어두운 색, 음수(연회비가 혜택보다 큰 경우)면 빨간색 */}
          <p
            className={`text-sm font-semibold ${
              net_annual_benefit >= 0 ? "text-zinc-800" : "text-red-500"
            }`}
          >
            {net_annual_benefit >= 0 ? "+" : ""}
            {net_annual_benefit.toLocaleString()}원
          </p>
        </div>
      </div>

      {/* ── 모바일 혜택 요약 (sm 미만에서만 표시) ─────────── */}
      <div className="flex justify-between border-t border-zinc-100 px-5 py-2 sm:hidden">
        <span className="text-xs text-zinc-500">
          월 예상 혜택{" "}
          <span className="font-semibold text-[#ffcc00]">
            {monthly_benefit.toLocaleString()}원
          </span>
        </span>
        <span className="text-xs text-zinc-500">
          연 순 혜택{" "}
          <span
            className={`font-semibold ${
              net_annual_benefit >= 0 ? "text-zinc-800" : "text-red-500"
            }`}
          >
            {net_annual_benefit >= 0 ? "+" : ""}
            {net_annual_benefit.toLocaleString()}원
          </span>
        </span>
      </div>

      {/* ── 카테고리별 혜택 세부 내역 ───────────────────────── */}
      {/* benefit_breakdown이 있을 때만 표시 */}
      {benefit_breakdown.length > 0 && (
        <div className="border-t border-zinc-100 px-5 py-3">
          <p className="mb-2 text-xs font-medium text-zinc-400">카테고리별 혜택</p>
          <div className="flex flex-wrap gap-2">
            {benefit_breakdown.map((b) => (
              // 각 카테고리 혜택을 chip(태그) 형태로 표시
              <div
                key={b.category}
                className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs"
              >
                {/* 카테고리명 */}
                <span className="font-medium text-zinc-700">{b.category}</span>
                {/* 혜택률 (예: "5%" 또는 "5~30%") */}
                <span className="ml-1.5 text-zinc-400">
                  {rateLabel(b.rate_min, b.rate_max)}
                </span>
                {/* 예상 혜택 금액 */}
                <span className="ml-1.5 font-semibold text-[#ffcc00]">
                  +{b.estimated_benefit.toLocaleString()}원
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── KB카드 상세 페이지 링크 ─────────────────────────── */}
      <div className="border-t border-zinc-100 px-5 py-2.5 text-right">
        <a
          href={card.detail_url}
          target="_blank"               // 새 탭에서 열기
          rel="noopener noreferrer"     // 보안: 새 탭에서 원본 탭에 접근 불가
          className="text-xs font-medium text-[#ffcc00] hover:underline"
        >
          KB국민카드 상세 보기 →
        </a>
      </div>
    </div>
  );
}
